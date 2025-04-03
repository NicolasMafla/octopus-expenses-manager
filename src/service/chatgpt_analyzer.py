import json
import tiktoken
from typing import List
from config import logger
from openai import OpenAI
from .model import LLMService


class ChatGptAnalyzer(LLMService):
    def __init__(self, model: str, api_key: str):
        self._model = model
        self._client = OpenAI(api_key=api_key)
        logger.info(f"[ChatGpt] OpenAI client created with model: {self._model}")

    def invoke(self, messages: List[dict]) -> dict:
        logger.info(f"[ChatGpt] Calculating prompt number of tokens...")
        tokens = self.count_tokens(messages=messages, model=self._model)
        logger.info(f"[ChatGpt] Prompt of {tokens} tokens requested to the AI service")
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={"type": "json_object"}
        )
        logger.info(f"[ChatGpt] Answer received from the AI service")
        try:
            answer = json.loads(completion.choices[0].message.content)
            logger.success(f"[ChatGpt] Answer successfully parsed in JSON format")
            return answer

        except (json.JSONDecodeError, KeyError, IndexError) as error:
            logger.error(f"[ChatGpt] Error parsing the answer in JSON format: {error}")
            return {}

    @staticmethod
    def count_tokens(messages: List[dict], model: str) -> int:
        encoding = tiktoken.encoding_for_model(model)
        messages_text = json.dumps(messages, ensure_ascii=False)
        return len(encoding.encode(messages_text))
