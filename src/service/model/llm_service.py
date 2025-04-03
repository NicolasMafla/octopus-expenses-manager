from typing import List
from abc import ABC, abstractmethod


class LLMService(ABC):

    @abstractmethod
    def invoke(self, messages: List[dict]) -> dict:
        pass
