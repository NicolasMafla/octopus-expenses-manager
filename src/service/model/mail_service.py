from typing import Any
from abc import ABC, abstractmethod

class MailService(ABC):
    @abstractmethod
    def authenticate(self) -> None:
        pass

    @abstractmethod
    def build_service(self) -> None:
        pass

    @abstractmethod
    def get_emails(self, n: int):
        pass