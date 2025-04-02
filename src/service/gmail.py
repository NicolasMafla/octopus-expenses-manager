import os
from typing import List
from config import logger
from .model.mail_service import MailService
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


class GmailService(MailService):
    def __init__(self, credentials_path: str, token_path: str, scopes: List[str]):
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._scopes = scopes
        self._credentials = None

    def authenticate(self) -> None:
        logger.info("[Gmail] Initializing authentication process...")
        creds = None

        if os.path.isfile(self._token_path):
            creds = Credentials.from_authorized_user_file(self._token_path, self._scopes)
            logger.info("[Gmail] Authentication token loaded")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("[Gmail] Authentication token refreshed")
            else:
                if os.path.isfile(self._credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(self._credentials_path, self._scopes)
                    creds = flow.run_local_server(port=0)
                else:
                    logger.error("[Gmail] Credentials JSON file not found")
                    return creds

            with open(self._token_path, "w") as token:
                token.write(creds.to_json())
                logger.info("[Gmail] New authentication token generated and saved")

        logger.success("[Gmail] Authentication process completed")
        self._credentials = creds

    def build_service(self) -> None:
        logger.info("[Gmail] Building service...")
        service = None
        if self._credentials:
            service = build(serviceName="gmail", version="v1", credentials=self._credentials)
            logger.success("[Gmail] Service built successfully")
        else:
            logger.error("[Gmail] Credentials not found, service failed")
        return service

    def get_emails(self, n: int):
        pass
