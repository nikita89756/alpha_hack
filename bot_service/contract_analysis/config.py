"""Конфигурация агентной системы contract_analysis."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _env_str(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass
class ContractAgentConfig:
    """Параметры отдельного LLM-агента."""

    name: str
    temperature: float
    max_tokens: int


@dataclass
class RetrievalConfig:
    """Настройки RAG-поиска внутри contract_analysis."""

    kb_limit: int = field(default_factory=lambda: _env_int("CONTRACT_ANALYSIS_KB_LIMIT", 6))
    source_filter: str = field(default_factory=lambda: _env_str("CONTRACT_ANALYSIS_SOURCE", "DocAnalysis"))
    history_limit: int = field(default_factory=lambda: _env_int("CONTRACT_ANALYSIS_HISTORY_LIMIT", 5))


@dataclass
class ContractAnalysisConfig:
    """Глобальная конфигурация новой агентной системы."""

    intent: ContractAgentConfig = field(
        default_factory=lambda: ContractAgentConfig(
            name=_env_str("CONTRACT_INTENT_AGENT_NAME", "contract_intent"),
            temperature=_env_float("CONTRACT_INTENT_TEMPERATURE", 0.15),
            max_tokens=_env_int("CONTRACT_INTENT_MAX_TOKENS", 800),
        )
    )
    reviewer: ContractAgentConfig = field(
        default_factory=lambda: ContractAgentConfig(
            name=_env_str("CONTRACT_REVIEW_AGENT_NAME", "contract_reviewer"),
            temperature=_env_float("CONTRACT_REVIEW_TEMPERATURE", 0.35),
            max_tokens=_env_int("CONTRACT_REVIEW_MAX_TOKENS", 1800),
        )
    )
    drafter: ContractAgentConfig = field(
        default_factory=lambda: ContractAgentConfig(
            name=_env_str("CONTRACT_DRAFT_AGENT_NAME", "contract_drafter"),
            temperature=_env_float("CONTRACT_DRAFT_TEMPERATURE", 0.65),
            max_tokens=_env_int("CONTRACT_DRAFT_MAX_TOKENS", 2400),
        )
    )
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)


CONTRACT_CONFIG = ContractAnalysisConfig()

__all__ = ["CONTRACT_CONFIG", "ContractAgentConfig", "ContractAnalysisConfig", "RetrievalConfig"]
