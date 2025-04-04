import uvicorn
from fastapi import FastAPI, Request
from config import logger
from config.config import GMAIL_SCOPES, CREDENTIALS_JSON, TOKEN_JSON
from src.service.gmail import GmailService

app = FastAPI()


@app.post("/gmail/notifications")
async def gmail_notifications(request: Request):
    body = await request.body()
    logger.info(f"📩 Notificación recibida: {body}")
    return "OK"


@app.post("/gmail/auth")
async def gmail_auth(request: Request):
    body = await request.body()
    gmail = GmailService(scopes=GMAIL_SCOPES)
    gmail.authenticate_from_envs(credentials_json=CREDENTIALS_JSON, token_json=TOKEN_JSON)
    gmail.build_service()
    return "OK"


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
