"""Общие абстракции, которыми пользуются все специализированные агенты."""

from typing import List

from ..utils.llm_client import AsyncLLMClient, Message


class BaseAgent:
    """Базовый класс для всех специализированных агентов.

    Attributes:
        llm (AsyncLLMClient): Клиент, выполняющий обращения к LLM.
        system_prompt (str): Системный промт для конкретного агента.
        name (str): Условное имя агента для логирования.
        temperature (float): Параметры сэмплинга модели.
        max_tokens (int): Ограничение на длину ответа.
    """

    def __init__(
        self,
        llm: AsyncLLMClient,
        system_prompt: str,
        name: str = "agent",
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> None:
        """Сохраняет общие параметры общения с моделью.

        Args:
            llm (AsyncLLMClient): Клиент для отправки сообщений.
            system_prompt (str): Системная инструкция.
            name (str): Имя агента.
            temperature (float): Значение температуры выборки.
            max_tokens (int): Лимит токенов для ответа.
        """
        self.llm = llm
        self.system_prompt = system_prompt
        self.name = name
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def ainvoke(self, user_prompt: str) -> str:
        """Отправляет промпт с учётом настроек конкретного агента.

        Args:
            user_prompt (str): Сообщение пользователя без системной части.

        Returns:
            str: Текстовый ответ модели с учётом системного промта.
        """
        msgs: List[Message] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        resp = await self.llm.ainvoke(
            msgs,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return resp.content or ""
