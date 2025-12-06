"""Агент, определяющий тип задачи: анализ или подготовка договора."""

from __future__ import annotations

import json
from typing import Any, Dict

from ai_assistant.agent_system.agents.base import BaseAgent
from ai_assistant.agent_system.utils.llm_client import AsyncLLMClient
from ai_assistant.agent_system.utils.logger import logger

from contract_analysis.config import ContractAgentConfig
from contract_analysis.prompts import INTENT_SYSTEM_PROMPT, INTENT_USER_TEMPLATE


class ContractIntentAgent(BaseAgent):
    """Интерпретатор пользовательских запросов contract_analysis."""

    def __init__(self, llm: AsyncLLMClient, config: ContractAgentConfig) -> None:
        super().__init__(
            llm,
            INTENT_SYSTEM_PROMPT,
            name=config.name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    async def run(self, request: str, history_block: str) -> Dict[str, Any]:
        """Определяет требуемое действие и ключевые требования."""

        prompt = INTENT_USER_TEMPLATE.format(
            request=(request or "").strip(),
            history_block=history_block.strip() or "История пуста.",
        )
        raw = await self.ainvoke(prompt)
        return self._parse_response(raw, request)

    @staticmethod
    def _parse_response(raw: str, request: str) -> Dict[str, Any]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("ContractIntentAgent вернул невалидный JSON, используется fallback.")
            payload = {}

        action = str(payload.get("action") or "").strip().lower()
        if action not in {"analyze", "draft"}:
            action = "analyze"

        document_type = (payload.get("document_type") or "").strip() or "договор"
        notes = (payload.get("notes") or "").strip()
        requirements = payload.get("key_requirements") or []
        if isinstance(requirements, str):
            requirements = [requirements]
        elif not isinstance(requirements, list):
            requirements = []

        safe_requirements = [str(item).strip() for item in requirements if str(item).strip()]
        if not safe_requirements and request:
            safe_requirements = [request.strip()]

        return {
            "action": action,
            "document_type": document_type,
            "key_requirements": safe_requirements,
            "notes": notes,
            "raw": payload,
        }
