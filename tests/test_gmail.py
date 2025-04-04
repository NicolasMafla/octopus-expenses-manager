from config.config import TOKEN_PATH, CREDENTIALS_PATH, GMAIL_SCOPES, CREDENTIALS_JSON, TOKEN_JSON
from src.service.gmail import GmailService, Email
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource

def test_gmail_get_emails_auth_paths():
    gmail = GmailService(scopes=GMAIL_SCOPES)

    gmail.authenticate_from_paths(credentials_path=CREDENTIALS_PATH, token_path=TOKEN_PATH)
    assert isinstance(gmail._credentials, Credentials)

    gmail.build_service()
    assert isinstance(gmail._service, Resource)

    filters = {
        "f1": "category:primary from:servicios@tarjetasbancopichincha.com",
        "f2": "category:primary from:bancaenlinea@produbanco.com",
        "f3": "noreply@uber.com"
    }
    emails = gmail.get_emails(max_results=5, filters=filters.get("f2"))
    assert len(emails) == 5

def test_gmail_get_email_by_id_auth_paths():
    gmail = GmailService(scopes=GMAIL_SCOPES)

    gmail.authenticate_from_paths(credentials_path=CREDENTIALS_PATH, token_path=TOKEN_PATH)
    assert isinstance(gmail._credentials, Credentials)

    gmail.build_service()
    assert isinstance(gmail._service, Resource)

    email_id = "195fb04a9e1294a5"
    one_email = gmail.get_email_by_id(email_id=email_id)
    assert isinstance(one_email, Email)


def test_gmail_get_emails_auth_envs():
    gmail = GmailService(scopes=GMAIL_SCOPES)

    gmail.authenticate_from_envs(credentials_json=CREDENTIALS_JSON, token_json=TOKEN_JSON)
    assert isinstance(gmail._credentials, Credentials)

    gmail.build_service()
    assert isinstance(gmail._service, Resource)

    filters = {
        "f1": "category:primary from:servicios@tarjetasbancopichincha.com",
        "f2": "category:primary from:bancaenlinea@produbanco.com",
        "f3": "noreply@uber.com"
    }
    emails = gmail.get_emails(max_results=5, filters=filters.get("f2"))
    assert len(emails) == 5

def test_gmail_get_email_by_id_auth_envs():
    gmail = GmailService(scopes=GMAIL_SCOPES)

    gmail.authenticate_from_envs(credentials_json=CREDENTIALS_JSON, token_json=TOKEN_JSON)
    assert isinstance(gmail._credentials, Credentials)

    gmail.build_service()
    assert isinstance(gmail._service, Resource)

    email_id = "195fb04a9e1294a5"
    one_email = gmail.get_email_by_id(email_id=email_id)
    assert isinstance(one_email, Email)