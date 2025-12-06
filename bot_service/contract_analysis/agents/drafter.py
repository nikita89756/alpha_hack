"""Агент, который составляет черновики договоров и актов."""

from __future__ import annotations

from typing import Iterable

from ai_assistant.agent_system.agents.base import BaseAgent
from ai_assistant.agent_system.utils.llm_client import AsyncLLMClient

from contract_analysis.config import ContractAgentConfig
from contract_analysis.prompts import (
    DISCLAIMER_TEXT,
    DRAFT_SYSTEM_PROMPT,
    DRAFT_USER_TEMPLATE,
)


class ContractDraftAgent(BaseAgent):
    """Генерирует черновики документов с обязательным дисклеймером."""

    def __init__(self, llm: AsyncLLMClient, config: ContractAgentConfig) -> None:
        super().__init__(
            llm,
            DRAFT_SYSTEM_PROMPT,
            name=config.name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    async def run(
        self,
        document_type: str,
        requirements: Iterable[str],
        context_block: str,
    ) -> str:
        """Создаёт черновик и гарантирует наличие дисклеймера."""

        requirements_list = "\n".join(
            f"- {item.strip()}" for item in requirements if str(item).strip()
        ) or "- нет дополнительных требований, опирайся на стандартную структуру."

        prompt = DRAFT_USER_TEMPLATE.format(
            document_type=document_type.strip() or "договор",
            requirements=requirements_list,
            context_block=context_block.strip() or "Контекст не найден.",
        )
        draft = (await self.ainvoke(prompt)).strip()
        
        while DISCLAIMER_TEXT in draft:
            draft = draft.replace(DISCLAIMER_TEXT, "").strip()
        
        while "\n\n\n" in draft:
            draft = draft.replace("\n\n\n", "\n\n")
        
        draft = f"{draft.rstrip()}\n\n{DISCLAIMER_TEXT}"
        return draft
