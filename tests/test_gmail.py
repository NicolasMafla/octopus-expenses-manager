from config.config import TOKEN_PATH, CREDENTIALS_PATH, GMAIL_SCOPES
from src.service.gmail import GmailService
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource

def test_gmail_service():
    gmail = GmailService(credentials_path=CREDENTIALS_PATH, token_path=TOKEN_PATH, scopes=GMAIL_SCOPES)

    gmail.authenticate()
    assert isinstance(gmail._credentials, Credentials)

    gmail.build_service()
    assert isinstance(gmail._service, Resource)

    emails = gmail.get_emails(max_results=5)
    assert len(emails) == 5