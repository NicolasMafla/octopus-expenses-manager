import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "../config")

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH")
GMAIL_SCOPES = os.getenv("GMAIL_SCOPES", "https://www.googleapis.com/auth/gmail.readonly").split(",")
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY", "XXXXXXX")
