from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import logging
from starlette.middleware.sessions import SessionMiddleware

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Añadir colores al logger (opcional)
class LoggerWithColors:
    def info(self, message):
        logger.info(message)

    def error(self, message):
        logger.error(message)

    def success(self, message):
        logger.info(f"✅ {message}")


logger = LoggerWithColors()

app = FastAPI(title="Gmail API", description="API para consultar correos de Gmail por ID")

# Añadir soporte para sesiones (necesario para el flujo OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "un_secreto_muy_seguro_para_desarrollo")
)

# Configuración para la autenticación con Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


# Modelos
class EmailResponse(BaseModel):
    id: str
    from_email: str
    to: str
    subject: str
    date: str
    body: str


# Clase para gestionar la autenticación con Gmail
class GmailAuth:
    def __init__(self):
        self._credentials = None
        self._scopes = SCOPES
        self._service = None

        # Cargar credenciales desde el entorno
        self._client_id = os.environ.get("GOOGLE_CLIENT_ID")
        self._client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        self._redirect_uri = os.environ.get("OAUTH_REDIRECT_URI", "https://tu-app-railway.app/oauth2callback")

        # Intentar cargar token si existe
        token_json = os.environ.get("GMAIL_TOKEN")
        if token_json:
            try:
                token_info = json.loads(token_json)
                self._credentials = Credentials.from_authorized_user_info(token_info, self._scopes)
                logger.info("[Gmail] Loaded credentials from environment")
            except Exception as e:
                logger.error(f"[Gmail] Error loading token: {e}")

    def get_authorization_url(self):
        """Genera una URL para la autorización OAuth"""
        if not self._client_id or not self._client_secret:
            logger.error("[Gmail] Missing OAuth client credentials")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth client credentials not configured"
            )

        # Crear el flujo OAuth
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self._redirect_uri]
                }
            },
            scopes=self._scopes,
            redirect_uri=self._redirect_uri
        )

        # Generar URL con acceso offline para obtener refresh token
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Forzar el consentimiento para obtener refresh token
        )

        return auth_url, flow

    def process_oauth_callback(self, code, state=None):
        """Procesa la respuesta del callback OAuth"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self._redirect_uri]
                }
            },
            scopes=self._scopes,
            redirect_uri=self._redirect_uri,
            state=state
        )

        # Intercambiar el código por credenciales
        flow.fetch_token(code=code)

        # Guardar las credenciales
        self._credentials = flow.credentials

        # Guardar token para uso futuro (esto debería guardarse en una base de datos)
        token_json = self._credentials.to_json()
        logger.info(f"[Gmail] Obtained new credentials. Token: {token_json}")

        # En un entorno de desarrollo, puedes mostrar este token para configurarlo como variable de entorno
        return token_json

    def get_service(self):
        # Si no tenemos credenciales válidas, necesitamos reautorizar
        if not self._credentials or not self._credentials.valid:
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                logger.info("[Gmail] Refreshing expired token")
                try:
                    self._credentials.refresh(Request())
                    logger.success("[Gmail] Token refreshed successfully")
                except Exception as e:
                    logger.error(f"[Gmail] Error refreshing token: {e}")
                    self._credentials = None

            if not self._credentials:
                logger.error("[Gmail] No valid credentials available")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization required",
                    headers={"WWW-Authenticate": "Bearer"}
                )

        if not self._service:
            try:
                self._service = build('gmail', 'v1', credentials=self._credentials)
                logger.info("[Gmail] Service created successfully")
            except Exception as e:
                logger.error(f"[Gmail] Error creating service: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error creating Gmail service: {str(e)}"
                )

        return self._service


# Instancia global para la autenticación
gmail_auth = GmailAuth()

# API Key para proteger los endpoints (opcional)
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header == os.environ.get("API_KEY"):
        return api_key_header
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate API KEY"
        )


# Función para procesar el contenido del correo
def process_email(email_data):
    email = {}
    email['id'] = email_data['id']

    headers = email_data['payload']['headers']
    email['from_email'] = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
    email['to'] = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'Unknown')
    email['subject'] = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
    email['date'] = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown')

    # Obtener el cuerpo del correo
    body = ''
    if 'parts' in email_data['payload']:
        parts = email_data['payload']['parts']
        for part in parts:
            if part['mimeType'] == 'text/plain':
                body = base64.urlsafe_b64decode(part['body'].get('data', '')).decode('utf-8')
                break
    elif 'body' in email_data['payload'] and 'data' in email_data['payload']['body']:
        body = base64.urlsafe_b64decode(email_data['payload']['body']['data']).decode('utf-8')

    email['body'] = body

    return EmailResponse(**email)


# Endpoints
@app.get("/")
def read_root():
    return {"message": "Gmail API está funcionando. Utiliza /authorize para comenzar el proceso de autenticación."}


# Endpoint para iniciar la autenticación OAuth
@app.get("/authorize")
async def authorize():
    auth_url, flow = gmail_auth.get_authorization_url()
    logger.info(f"[OAuth] Authorization URL: {auth_url}")
    return RedirectResponse(url=auth_url)


# Endpoint para recibir la respuesta OAuth
@app.get("/oauth2callback")
async def oauth2callback(code: str, state: Optional[str] = None):
    token_json = gmail_auth.process_oauth_callback(code, state)
    return {
        "message": "Autorización completada con éxito. Configura el siguiente token como variable de entorno GMAIL_TOKEN en Railway:",
        "token": token_json
    }


@app.get("/emails/{email_id}", response_model=EmailResponse, dependencies=[Depends(get_api_key)])
def get_email_by_id(email_id: str):
    try:
        service = gmail_auth.get_service()
        email_data = service.users().messages().get(userId="me", id=email_id, format='full').execute()
        return process_email(email_data)
    except Exception as e:
        logger.error(f"[Gmail] Error al obtener el correo: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error al obtener el correo: {str(e)}"
        )


# Endpoint para listar correos recientes
@app.get("/emails", response_model=List[dict], dependencies=[Depends(get_api_key)])
def list_emails(max_results: Optional[int] = 10):
    try:
        service = gmail_auth.get_service()
        results = service.users().messages().list(userId="me", maxResults=max_results).execute()
        messages = results.get('messages', [])

        email_list = []
        for message in messages:
            msg_id = message['id']
            email_min = service.users().messages().get(
                userId="me",
                id=msg_id,
                format='metadata',
                metadataHeaders=['Subject', 'From']
            ).execute()
            headers = email_min['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')

            email_list.append({
                'id': msg_id,
                'subject': subject,
                'from': sender
            })

        return email_list
    except Exception as e:
        logger.error(f"[Gmail] Error al listar correos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar correos: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    # Cargar configuración desde el entorno
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)