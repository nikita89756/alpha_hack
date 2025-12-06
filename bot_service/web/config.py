"""Значения по умолчанию для веб-слоя инференса."""

from dataclasses import dataclass


@dataclass
class InferenceConfig:
    """Параметры инференса по умолчанию для публичного API.

    Attributes:
        OPENROUTER_MODEL (str): Имя модели OpenRouter.
        OPENROUTER_BASE (str): URL шлюза генерации.
        TEMPERATURE (float): Температура выборки.
        MAX_TOKENS (int): Ограничение токенов на ответ.
        TIMEOUT (int): Таймаут HTTP-запроса в секундах.
    """

    OPENROUTER_MODEL: str = "deepseek/deepseek-chat-v3.1"
    OPENROUTER_BASE: str = "https://openrouter.ai/api/v1/chat/completions"
    TEMPERATURE: float = 1.2
    MAX_TOKENS: int = 1200
    TIMEOUT: int = 90
