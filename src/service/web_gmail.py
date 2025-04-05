import json
from typing import Literal
from config import logger
from pydantic import BaseModel
from typing import List, Optional
from .model import MailService
from ..utils import bs64_to_utf8, process_html
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import HTTPException, status


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
    html: Optional[str] = None
    text: Optional[str] = None


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

        elif self.payload.mimeType == "multipart/related":
            if len(self.payload.parts) > 1:
                logger.warning(f"[Gmail] {self.payload.mimeType} email: {self.id} with more than one parts")
            email.data = self.payload.parts[0].body.data

        email.html = bs64_to_utf8(encoded_data=email.data)
        email.text = process_html(html=email.html)
        return email


class WebGmailService(MailService):
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, token: str, scopes: List[str]):
        self._scopes = scopes
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._token = token
        self._credentials = None
        self._service = None

    def get_authorization_url(self):
        if not self._client_id or not self._client_secret:
            logger.error("[Gmail] Missing OAuth client credentials")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth client credentials not configured"
            )

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self._redirect_uri]
                }
            },
            scopes=self._scopes,
            redirect_uri=self._redirect_uri
        )

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )

        return auth_url, flow

    def process_oauth_callback(self, code, state=None):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self._redirect_uri]
                }
            },
            scopes=self._scopes,
            redirect_uri=self._redirect_uri,
            state=state
        )
        flow.fetch_token(code=code)
        self._credentials = flow.credentials
        token_json = self._credentials.to_json()
        logger.info(f"[Gmail] Obtained new credentials. Token: {token_json}")
        return token_json

    def authenticate(self) -> None:
        logger.info("[Gmail] Initializing authentication process...")

        try:
            token = json.loads(self._token)
            self._credentials = Credentials.from_authorized_user_info(token, self._scopes)
            logger.info("[Gmail] Loaded credentials from environment")

        except Exception as e:
            logger.error(f"[Gmail] Error loading token from environment: {e}")

        if not self._credentials or not self._credentials.valid:
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                logger.info("[Gmail] Refreshing expired token...")
                try:
                    self._credentials.refresh(Request())
                    logger.success("[Gmail] Token refreshed successfully")
                except Exception as e:
                    logger.error(f"[Gmail] Error refreshing token: {e}")
                    self._credentials = None

            if not self._credentials:
                logger.error("[Gmail] No valid credentials available")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization required",
                    headers={"WWW-Authenticate": "Bearer"}
                )

        logger.success("[Gmail] Authentication process completed")

    def build_service(self) -> None:
        logger.info("[Gmail] Initializing building service...")
        service = None
        if self._credentials:
            service = build(serviceName="gmail", version="v1", credentials=self._credentials)
            logger.success("[Gmail] Service built successfully")
        else:
            logger.error("[Gmail] Credentials not found, building service process failed")
        self._service = service

    def get_emails(self, max_results: int, filters: str) -> List[Email] | None:
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
            logger.error(f"[Gmail] No service found. Call authenticate() and build_service() first")
            return None

    def get_email_by_id(self, email_id: str) -> Email | None:
        if self._service:
            try:
                logger.info(f"[Gmail] Getting email: {email_id}")
                response = self._service.users().messages().get(
                    userId="me",
                    id=email_id,
                    format="full"
                ).execute()
                email = Response.model_validate(response).parse()
                logger.success(f"[Gmail] Email {email_id} retrieved and parsed successfully")
                return email

            except HttpError as error:
                logger.error(f"[Gmail] Error obtaining email {email_id}: {error}")
                return None
        else:
            logger.error(f"[Gmail] No service found. Call authenticate() and build_service() first")
            return None
