"""LLM-агент, который проверяет релевантность найденных фрагментов RAG."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from ..config import AGENTS_CONFIG
from ..service.prompts import Prompts
from ..utils.llm_client import AsyncLLMClient

from .base import BaseAgent
from .utils import render_kb_block

_HISTORY_KEYWORDS = (
    "предыдущ",
    "прошл",
    "последн",
    "что я спраш",
    "что я говорил",
    "что мы обсуж",
    "как я спраш",
    "какой был",
    "напомни",
    "мы говорили",
    "наш разговор",
    "что ты ответ",
    "история",
)


def _about_history(question: str) -> bool:
    if not question:
        return False
    text = question.lower()
    return any(token in text for token in _HISTORY_KEYWORDS)


class RagValidatorAgent(BaseAgent):
    """Отсекает нерелевантные чанки и решает, нужен ли fallback к веб-поиску."""

    def __init__(self, llm: AsyncLLMClient) -> None:
        settings = AGENTS_CONFIG.rag_validator
        super().__init__(
            llm,
            Prompts.RAG_VALIDATOR_SYSTEM,
            name=settings.name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    async def run(
        self,
        question: str,
        kb_items: List[Dict[str, Any]],
        ltm_items: List[Dict[str, Any]] | None = None,
        history_block: str | None = None,
    ) -> Dict[str, Any]:
        """Возвращает решение о том, какие фрагменты использовать и нужна ли подмена стратегии."""
        ltm_items = ltm_items or []
        history_based = bool(history_block) and _about_history(question)
        if not kb_items and not ltm_items:
            if history_based:
                return {
                    "kb_items": [],
                    "ltm_items": [],
                    "strategy": "llm_only",
                    "notes": "Ответ есть в истории диалога",
                }
            return {
                "kb_items": [],
                "ltm_items": [],
                "strategy": "web_search",
                "notes": "Нет фрагментов в БЗ/памяти",
            }

        kb_block = render_kb_block(kb_items, "KB")
        ltm_block = render_kb_block(ltm_items, "LTM")
        user_prompt = Prompts.RAG_VALIDATOR_USER_TEMPLATE.format(
            question=question,
            kb_block=kb_block,
            ltm_block=ltm_block,
            history_block=history_block or "История пуста.",
        )
        raw = await self.ainvoke(user_prompt)

        try:
            decision = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "kb_items": kb_items,
                "ltm_items": ltm_items,
                "strategy": "kb",
                "notes": "Ошибка парсинга JSON",
            }

        kb_ids = decision.get("kb_ids")
        ltm_ids = decision.get("ltm_ids")
        if kb_ids is None and ltm_ids is None:
            kb_ids = decision.get("relevant_ids")
            ltm_ids = []
        if not isinstance(kb_ids, list):
            kb_ids = []
        if not isinstance(ltm_ids, list):
            ltm_ids = []

        kb_id_set = {str(_id) for _id in kb_ids if _id is not None}
        ltm_id_set = {str(_id) for _id in ltm_ids if _id is not None}

        filtered_kb = [item for item in kb_items if str(item.get("id")) in kb_id_set] if kb_id_set else kb_items
        filtered_ltm = [item for item in ltm_items if str(item.get("id")) in ltm_id_set] if ltm_id_set else ltm_items
        strategy = (decision.get("strategy") or "kb").lower()
        notes = decision.get("notes") or ""

        if strategy not in {"kb", "web_search", "llm_only"}:
            strategy = "kb"

        if history_based and strategy in {"web_search", "kb"} and not filtered_kb:
            strategy = "llm_only"

        if strategy == "llm_only":
            return {
                "kb_items": [],
                "ltm_items": filtered_ltm,
                "strategy": "llm_only",
                "notes": notes,
            }

        if strategy == "web_search":
            return {
                "kb_items": [],
                "ltm_items": filtered_ltm,
                "strategy": "web_search",
                "notes": notes or "Нужен веб-поиск",
            }

        if not filtered_kb:
            if filtered_ltm:
                return {
                    "kb_items": [],
                    "ltm_items": filtered_ltm,
                    "strategy": "llm_only",
                    "notes": notes or "Только память покрывает вопрос",
                }

            fallback_strategy = "llm_only" if history_based else "web_search"
            return {
                "kb_items": [],
                "ltm_items": [],
                "strategy": fallback_strategy,
                "notes": notes or "Нет релевантных фрагментов",
            }

        return {
            "kb_items": filtered_kb,
            "ltm_items": filtered_ltm,
            "strategy": "kb",
            "notes": notes,
        }
