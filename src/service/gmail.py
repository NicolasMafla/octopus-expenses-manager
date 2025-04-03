import os
from typing import Literal
from config import logger
from pydantic import BaseModel
from typing import List, Optional
from .model import MailService
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class Header(BaseModel):
    name: str
    value: str


class Body(BaseModel):
    data: Optional[str] = None


class Part(BaseModel):
    mimeType: str
    body: Body


class Payload(BaseModel):
    mimeType: Literal["text/html", "multipart/related"]
    headers: List[Header]
    body: Body
    parts: Optional[List[Part]] = None

    def extract_headers(self, header_names: List[str]) -> dict:
        header_map = {h.name.lower(): h.value for h in self.headers}
        return {name: header_map.get(name.lower()) for name in header_names}


class Email(BaseModel):
    id: str
    mimeType: Literal["text/html", "multipart/related"]
    sender: Optional[str] = None
    recipient: Optional[str] = None
    date: Optional[str] = None
    subject: Optional[str] = None
    content_type: Optional[str] = None
    data: Optional[str] = None


class Response(BaseModel):
    id: str
    payload: Payload

    def parse(self) -> Email:
        headers_needed = ["From", "To", "Date", "Subject", "Content-Type"]
        extracted_headers = self.payload.extract_headers(headers_needed)

        email = Email(
            id=self.id,
            mimeType=self.payload.mimeType,
            sender=extracted_headers.get("From"),
            recipient=extracted_headers.get("To"),
            date=extracted_headers.get("Date"),
            subject=extracted_headers.get("Subject"),
            content_type=extracted_headers.get("Content-Type")
        )

        if self.payload.mimeType == "text/html":
            email.data = self.payload.body.data
            return email

        elif self.payload.mimeType == "multipart/related":
            if len(self.payload.parts) > 1:
                logger.warning(f"[Gmail] {self.payload.mimeType} email: {self.id} with more than one parts")
            email.data = self.payload.parts[0].body.data
            return email

        else:
            return email


class GmailService(MailService):
    def __init__(self, credentials_path: str, token_path: str, scopes: List[str]):
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._scopes = scopes
        self._credentials = None
        self._service = None

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
                logger.info("[Gmail] New authentication token generated")

        logger.success("[Gmail] Authentication process completed")
        self._credentials = creds

    def build_service(self) -> None:
        logger.info("[Gmail] Initializing building service...")
        service = None
        if self._credentials:
            service = build(serviceName="gmail", version="v1", credentials=self._credentials)
            logger.success("[Gmail] Service built successfully")
        else:
            logger.error("[Gmail] Credentials not found, building service process failed")
        self._service = service

    def get_emails(self, max_results: int = 10) -> List[Email] | None:

        # filters = "category:primary from:servicios@tarjetasbancopichincha.com"
        filters = "category:primary from:bancaenlinea@produbanco.com"

        if self._service:
            try:
                results = self._service.users().messages().list(
                    userId="me",
                    labelIds=["INBOX"],
                    q=filters,
                    maxResults=max_results
                ).execute()

                messages = results.get("messages", [])

                if not messages:
                    logger.warning(f"[Gmail] No mails found with filters: {filters}")
                    return None

                else:
                    logger.info(f"[Gmail] Getting {max_results} emails information...")
                    responses = [
                        self._service.users().messages().get(userId="me", id=msj.get("id"), format="full").execute() for
                        msj
                        in messages
                    ]
                    emails = [Response.model_validate(rsp).parse() for rsp in responses]
                    logger.success(f"[Gmail] Information successfully extracted for {max_results} emails")
                    return emails

            except HttpError as error:
                logger.error(f"[Gmail] Error obtaining mails: {error}")
                return None

        else:
            logger.error(f"[Gmail] Couldn't find any mail service built")
            return None
