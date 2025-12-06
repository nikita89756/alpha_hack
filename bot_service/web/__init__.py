"""Пакет веб-слоя для Support Hints Agent System."""

from __future__ import annotations

from importlib import import_module
from typing import Any, List

__all__ = (
    "app",
    "InferenceConfig",
    "AnswerContextItem",
    "AnswerRequest",
    "AnswerResponse",
    "DialogueMessageMemory",
    "MemorizeRequest",
)

_lazy_imports = {
    "app": ("web.api", "app"),
    "InferenceConfig": ("web.config", "InferenceConfig"),
    "AnswerContextItem": ("web.shemas", "AnswerContextItem"),
    "AnswerRequest": ("web.shemas", "AnswerRequest"),
    "AnswerResponse": ("web.shemas", "AnswerResponse"),
    "DialogueMessageMemory": ("web.shemas", "DialogueMessageMemory"),
    "MemorizeRequest": ("web.shemas", "MemorizeRequest"),
}


def __getattr__(name: str) -> Any:
    if name not in _lazy_imports:
        raise AttributeError(f"module 'web' has no attribute '{name}'")
    module_name, attr_name = _lazy_imports[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> List[str]:
    return sorted(set(__all__))
