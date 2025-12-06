"""Оркестрация сессии общения для агентного конвейера."""

from typing import Any, Dict, List

from .rag import RetrieverController
from .service.pipeline import AgentPipeline
from .utils.llm_client import AsyncLLMClient


class InterviewSession:
    """Оркестратор агентной системы без долговременной памяти."""

    def __init__(
        self,
        llm: AsyncLLMClient,
        retriever: RetrieverController,
    ) -> None:
        """Создает конвейер на основе общих компонентов.

        Args:
            llm (AsyncLLMClient): Клиент LLM, используемый агентами.
            retriever (RetrieverController): Контроллер поиска по базе знаний.
        """
        self.pipeline = AgentPipeline(llm_for_agents=llm, retriever=retriever)

    async def run(
        self,
        *,
        query: str,
        history: List[Dict[str, str]],
        user_id: str,
    ) -> Dict[str, Any]:
        """Выполняет один ход диалога поверх базы знаний.

        Args:
            query (str): Актуальный запрос пользователя.
            history (List[Dict[str, str]]): Контекст предыдущих сообщений.
            user_id (int): Идентификатор пользователя.

        Returns:
            Dict[str, Any]: Финальный ответ, источники и признак завершения диалога.
        """

        return await self.pipeline.run(user_text=query, user_id=user_id, history=history)
