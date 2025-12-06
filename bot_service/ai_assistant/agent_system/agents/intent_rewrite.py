"""Агент для классификации и переформулировки пользовательских намерений."""

import json

from ..config import AGENTS_CONFIG
from ..service.prompts import Prompts
from ..utils.llm_client import AsyncLLMClient

from .base import BaseAgent

from typing import Dict


class IntentRewriteAgent(BaseAgent):
    """Агент, который классифицирует и переписывает запросы пользователя."""

    def __init__(self, llm: AsyncLLMClient) -> None:
        """Инициализирует агент переписывания намерений.

        Args:
            llm (AsyncLLMClient): LLM client shared across agents.
        """
        settings = AGENTS_CONFIG.intent
        super().__init__(
            llm,
            Prompts.INTENT_SYSTEM,
            name=settings.name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    async def run(self, user_text: str, history_block: str | None = None) -> Dict:
        """Переформулирует намерение в сообщении пользователя.

        Args:
            user_text (str): Оригинальный текст пользователя.
            history_block (str | None): История диалога для учёта контекста.

        Returns:
            Dict: JSON-структура с флагом выхода и перефразированными запросами.
        """
        prompt = Prompts.INTENT_USER_TEMPLATE.format(
            history_block=history_block or "История пуста.",
            user_text=user_text,
        )
        raw = await self.ainvoke(prompt)
        try:
            data = json.loads(raw)
        except Exception:
            data = {
                "exit": False,
                "kb_query": user_text,
                "ltm_query": user_text,
                "answer_query": user_text,
                "off_topic": False,
            }
        off_topic = bool(data.get("off_topic"))
        data["off_topic"] = off_topic
        if off_topic:
            data["kb_query"] = ""
            data["ltm_query"] = ""
            data["answer_query"] = ""
        else:
            data["kb_query"] = data.get("kb_query") or user_text
            data["ltm_query"] = data.get("ltm_query") or data["kb_query"]
            data["answer_query"] = data.get("answer_query") or user_text
        return data
