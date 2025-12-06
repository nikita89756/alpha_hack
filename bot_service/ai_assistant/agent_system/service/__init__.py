"""Сервисные объекты (pipeline и промпты) для агентной системы."""

from .pipeline import AgentPipeline
from .prompts import Prompts

__all__ = [
    "AgentPipeline",
    "Prompts",
]
