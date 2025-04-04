import os
import sys
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENV = os.getenv("ENV")
logger.info(f"Working environment: {ENV}")

if ENV == "prod":
    CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

else:
    CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
    TOKEN_JSON = os.getenv("GOOGLE_TOKEN_JSON")
    CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
    TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH")

GMAIL_SCOPES = os.getenv("GMAIL_SCOPES").split(",")
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
DEBUG_LEVEL = os.getenv("DEBUG_LEVEL")

logger.remove()
logger.add(
    sys.stdout,
    format="<cyan>{time:YYYY-MM-DD HH:mm:ss}</cyan> | "
           "<level>{level: <8}</level> | "
           "<white>{name}</white>:<white>{function}</white>:<white>{line}</white> - "
           "<level>{message}</level>",
    level=DEBUG_LEVEL,
    colorize=True,
)