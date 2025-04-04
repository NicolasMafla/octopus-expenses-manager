import uvicorn
from fastapi import FastAPI, Request, HTTPException
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


@app.get("/email/{email_id}")
def get_email(email_id: str):
    service = GmailService(scopes=GMAIL_SCOPES)
    service.authenticate_web(credentials_json=CREDENTIALS_JSON)
    service.build_service()

    email = service.get_email_by_id(email_id=email_id)

    if not email:
        raise HTTPException(status_code=404, detail=f"Email with ID {email_id} not found")

    return email.model_dump()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
