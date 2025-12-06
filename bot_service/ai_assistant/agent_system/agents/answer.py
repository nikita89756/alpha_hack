"""Агент, формирующий черновики ответов на основе фактов из базы знаний."""

from typing import Any, Dict, List

from ..config import AGENTS_CONFIG
from ..service.prompts import Prompts
from ..utils.llm_client import AsyncLLMClient

from .base import BaseAgent
from .utils import render_kb_block


class AnswerAgent(BaseAgent):
    """Агент, отвечающий за генерацию черновика ответа на основе фрагментов базы знаний."""

    def __init__(self, llm: AsyncLLMClient) -> None:
        """Инициализирует AnswerAgent с подобранными параметрами сэмплирования.

        Args:
            llm (AsyncLLMClient): Клиент, отправляющий запрос в LLM.
        """
        settings = AGENTS_CONFIG.answer
        super().__init__(
            llm,
            Prompts.ANSWER_SYSTEM,
            name=settings.name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    async def run(
        self,
        answer_query: str,
        kb_items: List[Dict[str, Any]],
        history_block: str | None = None,
        memory_items: List[Dict[str, Any]] | None = None,
    ) -> str:
        """Генерирует черновик ответа, обоснованный данными из базы знаний и памяти.

        Args:
            answer_query (str): Перефразированный запрос.
            kb_items (List[Dict[str, Any]]): Фрагменты базы знаний.
            history_block (str | None): Часть истории диалога.
            memory_items (List[Dict[str, Any]] | None): Персональные факты из памяти.

        Returns:
            str: Черновик ответа от модели.
        """
        kb_block = render_kb_block(kb_items, "KB")
        ltm_block = render_kb_block(memory_items or [], "LTM")
        return await self.ainvoke(
            Prompts.ANSWER_USER_TEMPLATE.format(
                answer_query=answer_query,
                kb_block=kb_block,
                ltm_block=ltm_block,
                history_block=history_block or "История пуста.",
            )
        )
