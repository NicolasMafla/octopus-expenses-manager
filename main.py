import uvicorn
from typing import Optional
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, status
from config.config import logger, GOOGLE_TOKEN_JSON, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OAUTH_REDIRECT_URI
from src.service.web_gmail import WebGmailService

app = FastAPI()
service = WebGmailService(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    redirect_uri=OAUTH_REDIRECT_URI,
    token=GOOGLE_TOKEN_JSON,
    scopes=["https://www.googleapis.com/auth/gmail.readonly"]
)


@app.get("/ping")
def read_root():
    return {"message": "pong"}


@app.get("/authorize")
async def authorize():
    auth_url, flow = service.get_authorization_url()
    logger.info(f"[OAuth] Authorization URL: {auth_url}")
    return RedirectResponse(url=auth_url)


@app.get("/oauth2callback")
async def oauth2callback(code: str, state: Optional[str] = None):
    token = service.process_oauth_callback(code, state)
    return {
        "message": "Autorización completada con éxito. Configura el siguiente token como variable de entorno GOOGLE_TOKEN_JSON en Railway:",
        "token": token
    }

@app.get("/emails/{email_id}")
def get_email_by_id(email_id: str):
    try:
        service.authenticate()
        service.build_service()
        email = service.get_email_by_id(email_id=email_id)
        return email.model_dump()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error al obtener el correo: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
