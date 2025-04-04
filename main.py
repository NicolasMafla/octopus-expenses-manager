import uvicorn
from fastapi import FastAPI, Request
from config import logger

app = FastAPI()

@app.post("/gmail/notifications")
async def gmail_notifications(request: Request):
    body = await request.body()
    logger.info(f"📩 Notificación recibida: {body}")
    return "OK"

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)