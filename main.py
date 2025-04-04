import uvicorn
from fastapi import FastAPI, Request
from config import logger
from config.config import GMAIL_SCOPES, CREDENTIALS_JSON
from src.service.gmail import GmailService

app = FastAPI()


@app.post("/gmail/auth")
async def gmail_auth(request: Request):
    body = await request.body()
    gmail = GmailService(scopes=GMAIL_SCOPES)
    gmail.authenticate_web(credentials_json=CREDENTIALS_JSON)
    gmail.build_service()
    return f"OK: {body}"


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
