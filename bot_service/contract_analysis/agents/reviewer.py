"""Агент, который проверяет договоры и выделяет риски."""

from __future__ import annotations

from ai_assistant.agent_system.agents.base import BaseAgent
from ai_assistant.agent_system.utils.llm_client import AsyncLLMClient

from contract_analysis.config import ContractAgentConfig
from contract_analysis.prompts import REVIEW_SYSTEM_PROMPT, REVIEW_USER_TEMPLATE


class ContractReviewerAgent(BaseAgent):
    """Формирует юридический обзор и подсвечивает сомнительные места."""

    def __init__(self, llm: AsyncLLMClient, config: ContractAgentConfig) -> None:
        super().__init__(
            llm,
            REVIEW_SYSTEM_PROMPT,
            name=config.name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    async def run(self, request: str, context_block: str) -> str:
        """Возвращает структурированный анализ договора."""

        prompt = REVIEW_USER_TEMPLATE.format(
            request=(request or "").strip(),
            context_block=context_block.strip() or "Контекст не найден.",
        )
        return await self.ainvoke(prompt)
