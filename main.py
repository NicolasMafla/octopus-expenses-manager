import uvicorn
import json
import base64
from typing import Optional
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, status, Response, Request
from config.config import (
    logger, GOOGLE_TOKEN_JSON, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OAUTH_REDIRECT_URI, GOOGLE_TOPIC_ID
)
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

@app.get("/refresh")
def get_refresh():
    service.authenticate()
    service.build_service()
    return Response(content=service.token, media_type="application/json")

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


@app.post("/setup-watch")
def setup_gmail_watch():
    try:
        result = service.service.users().watch(
            userId="me",
            body={
                "topicName": GOOGLE_TOPIC_ID,
                "labelIds": ["INBOX"],
                "labelFilterBehavior": "INCLUDE"
            }
        ).execute()

        watch_expiration = result.get("expiration")
        history_id = result.get("historyId")

        logger.info(f"[Gmail] Watch setup successful. Expires: {watch_expiration}, History ID: {history_id}")
        return {
            "status": "success",
            "expiration": watch_expiration,
            "historyId": history_id
        }

    except Exception as e:
        logger.error(f"[Gmail] Error setting up watch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting up Gmail watch: {str(e)}"
        )


@app.post("/notifications")
async def receive_notification(request: Request):
    try:
        data = await request.json()

        if "message" in data and "data" in data["message"]:
            message_data = json.loads(base64.b64decode(data["message"]["data"]).decode("utf-8"))

            if message_data.get("emailId"):
                email_id = message_data.get("emailId")

                email = service.get_email_by_id(email_id=email_id)

                logger.info(f"[Gmail] New email received: {email.subject}")

                return {"status": "success", "message": "Email processed", "data": data, "email": email.model_dump()}

        return {"status": "ignored", "message": "Not a valid email notification"}

    except Exception as e:
        logger.error(f"[Gmail] Error processing notification: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/renew-watch")
def renew_gmail_watch():
    setup_gmail_watch()
    return {"status": "success", "message": "Gmail watch renewed"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
