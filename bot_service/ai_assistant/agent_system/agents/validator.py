"""Агент, который проверяет и шлифует черновики ответов."""

import json

from ..config import AGENTS_CONFIG
from ..service.prompts import Prompts
from ..utils.llm_client import AsyncLLMClient

from .base import BaseAgent


class ValidationAgent(BaseAgent):
    """Проверяет и дорабатывает черновик ответа."""

    def __init__(self, llm: AsyncLLMClient) -> None:
        """Настраивает валидатор с детерминированными параметрами сэмплинга.

        Args:
            llm (AsyncLLMClient): Клиент LLM для проверки ответов.
        """
        settings = AGENTS_CONFIG.validator
        super().__init__(
            llm,
            Prompts.VALIDATOR_SYSTEM,
            name=settings.name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    async def run(self, draft: str) -> str:
        """Проверяет черновик и улучшает его при необходимости.

        Args:
            draft (str): Исходный текст, подготовленный AnswerAgent.

        Returns:
            str: Исправленный или исходный текст при ошибках парсинга.
        """
        raw = await self.ainvoke(Prompts.VALIDATOR_USER_TEMPLATE.format(draft=draft))
        try:
            data = json.loads(raw)
            return data.get("final_answer", draft)
        except Exception:
            return draft
