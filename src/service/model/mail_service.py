from typing import Any
from abc import ABC, abstractmethod


class MailService(ABC):
    @abstractmethod
    def authenticate(self, **kwargs) -> None:
        pass

    @abstractmethod
    def build_service(self) -> None:
        pass

    @abstractmethod
    def get_emails(self, max_results: int, filters: str) -> Any | None:
        pass

    @abstractmethod
    def get_email_by_id(self, email_id: str) -> Any | None:
        pass
