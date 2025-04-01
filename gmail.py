import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config.config import CREDENTIALS_PATH, TOKEN_PATH, GMAIL_SCOPES, OPEN_AI_API_KEY
from loguru import logger

def authenticate_gmail():
    """Autentica con Google y devuelve un cliente para Gmail API."""
    creds = None

    # Verifica si ya hay un token guardado
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)
        logger.info("Token de autenticación cargado.")

    # Si no hay credenciales o están vencidas, iniciar sesión
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("Token refrescado.")
        else:
            logger.info("No se encontró token, iniciando autenticación con Google...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)

        # Guardar el token para futuras ejecuciones
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
            logger.info("Nuevo token guardado en config/token.json")

    return creds

def get_gmail_service():
    """Devuelve un cliente autenticado para la API de Gmail."""
    creds = authenticate_gmail()
    service = build("gmail", "v1", credentials=creds)
    logger.info("Servicio de Gmail autenticado con éxito.")
    return service

# creds = authenticate_gmail()
# serv = get_gmail_service()

import base64
from googleapiclient.errors import HttpError
from loguru import logger

def decode_body(encoded_body):
    """Decodifica el cuerpo del mensaje de base64url a texto plano."""
    decoded_bytes = base64.urlsafe_b64decode(encoded_body.encode('ASCII'))
    return decoded_bytes.decode('utf-8')

from bs4 import BeautifulSoup
import re

def clean_html(html_content):
    # Parsear el HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Obtener el texto del HTML, pero eliminando múltiples espacios y saltos de línea
    text = soup.get_text()

    # Eliminar los saltos de línea y espacios adicionales
    text = re.sub(r'\s+', ' ', text)  # Reemplazar múltiples espacios y saltos por uno solo
    text = text.strip()  # Eliminar espacios al principio y final

    return text

from openai import OpenAI
import json

def extract_expense(text):
    client = OpenAI(api_key=OPEN_AI_API_KEY)
    prompt = f"""
    I want you to extract the amount, merchant, and date of the following expense description received in my mail: {text}.

    Please return the information in JSON format with the following keys:
    - "amount" (float)
    - "merchant" (string)
    - "date" (string, in YYYY-MM-DD format)
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a expert in analyzing expenses made with credit cards"},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    try:
        return json.loads(completion.choices[0].message.content)
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Error parsing JSON: {e}")
        return {"error": "Could not extract expense information."}

def get_latest_email():
    """Obtiene el correo más reciente con información de la tarjeta de crédito."""
    try:
        service = get_gmail_service()

        # Buscar correos que contengan la palabra "compra" o "gasto"
        query = 'subject:compra OR subject:gasto OR subject="estado de cuenta"'
        results = service.users().messages().list(
            userId="me",
            labelIds=['INBOX'],
            q="category:primary from:servicios@tarjetasbancopichincha.com",
            maxResults=10
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            logger.info("No se encontraron correos recientes con información de gastos.")
            return None

        message_id = messages[0]["id"]
        email_data = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        data = email_data["payload"]["parts"][0]["body"]["data"]
        info = decode_body(data)
        clean_info = clean_html(info)
        final = extract_expense(clean_info)

        logger.info(f"Correo encontrado con ID: {message_id}")
        return email_data

    except HttpError as error:
        logger.error(f"Error al obtener correos: {error}")
        return None

email = get_latest_email()