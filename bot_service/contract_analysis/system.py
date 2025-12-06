"""Оркестрация агента анализа контрактов на базе LangGraph."""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass
from textwrap import shorten
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from typing import Any, Dict, List, Sequence, TypedDict

from langgraph.graph import END, StateGraph

from ai_assistant.agent_system.agents.rag_validator import RagValidatorAgent
from ai_assistant.agent_system.agents.web_searcher import WebSearcherAgent
from ai_assistant.agent_system.rag import RetrieverController
from ai_assistant.agent_system.utils.llm_client import AsyncLLMClient
from ai_assistant.agent_system.utils.logger import logger

from contract_analysis.agents import (
    ContractDraftAgent,
    ContractIntentAgent,
    ContractReviewerAgent,
)
from contract_analysis.config import CONTRACT_CONFIG, RetrievalConfig
from contract_analysis.prompts import DISCLAIMER_TEXT


@dataclass
class ContextBundle:
    """
    Контейнер для описания всех артефактов контекста, передаваемых агентам.

    Args:
        items (List[Dict[str, Any]]): Список фрагментов контекста.
        source (str): Источник данных (например, 'kb', 'web_search', 'llm_only').
        strategy (str): Стратегия извлечения ('kb', 'web_search', 'llm_only').
        notes (str): Примечания о контексте и его сборе.
    """
    items: List[Dict[str, Any]]
    source: str
    strategy: str
    notes: str


class ContractGraphState(TypedDict, total=False):
    """
    Состояние, передающееся между узлами легковесного пайплайна LangGraph.

    request: str - Исходный запрос пользователя.
    user_id: int - Идентификатор пользователя.
    history_block: str - История диалога (обрезанная строка).
    history: Sequence[Dict[str, str]] - Список сообщений в истории.
    intent: Dict[str, Any] - Объект, определяющий намерение пользователя.
    context_bundle: ContextBundle - Контекст для обработки.
    context_block: str - Строка с контекстом для передачи в агенты.
    result: str - Результат работы агента.
    output: Dict[str, Any] - Окончательная выходная структура.
    """

    request: str
    user_id: int
    history_block: str
    history: Sequence[Dict[str, str]]
    intent: Dict[str, Any]
    context_bundle: ContextBundle
    context_block: str
    result: str
    output: Dict[str, Any]


class ContractAnalysisSystem:
    """
    Класс-координатор агентов для определения намерения, подготовки контекста и генерации ответа.

    Args:
        llm_for_agents (AsyncLLMClient): Клиент LLM для агентов.
        retriever (RetrieverController | None): Контроллер поиска по базе знаний.

    Raises:
        RuntimeError: Если граф LangGraph завершился без выходных данных.
    """

    def __init__(
        self,
        llm_for_agents: AsyncLLMClient,
        retriever: RetrieverController | None,
    ) -> None:
        self.config = CONTRACT_CONFIG
        self.retrieval_cfg: RetrievalConfig = self.config.retrieval

        self.intent_agent = ContractIntentAgent(llm_for_agents, self.config.intent)
        self.reviewer_agent = ContractReviewerAgent(llm_for_agents, self.config.reviewer)
        self.draft_agent = ContractDraftAgent(llm_for_agents, self.config.drafter)
        self.rag_validator = RagValidatorAgent(llm_for_agents)
        self.web_searcher = WebSearcherAgent(llm_for_agents)
        self.retriever = retriever
        self._graph = self._build_graph()

    async def run(
        self,
        request: str,
        *,
        user_id: int = 0,
        history: Sequence[Dict[str, str]] | None = None,
    ) -> Dict[str, Any]:
        """
        Запуск пайплайна LangGraph и возврат итогового результата.

        Args:
            request (str): Запрос пользователя.
            user_id (int, optional): Идентификатор пользователя. По умолчанию 0.
            history (Sequence[Dict[str, str]], optional): История сообщений. По умолчанию None.

        Returns:
            Dict[str, Any]: Словарь с итоговым результатом обработки.

        Raises:
            RuntimeError: Если завершение пайплайна произошло без выходных данных.
        """
        history_list = list(history or [])
        history_block = self._history_block(history_list, self.retrieval_cfg.history_limit)
        initial_state: ContractGraphState = {
            "request": request,
            "user_id": user_id,
            "history": history_list,
            "history_block": history_block,
        }
        result_state = await self._graph.ainvoke(initial_state)
        output = result_state.get("output")
        if not output:
            raise RuntimeError("ContractAnalysisSystem graph completed without output.")
        return output

    async def _prepare_context(self, query: str, user_id: int) -> ContextBundle:
        """
        Извлекает контекст из DocAnalysis и валидирует его через RagValidator.

        Args:
            query (str): Вопрос пользователя для поиска знаний.
            user_id (int): Идентификатор пользователя.

        Returns:
            ContextBundle: Валидированный пакет контекста.
        """
        kb_items = self._search_docanalysis(query, user_id)
        logger.info(
            "Found %d DocAnalysis candidates for user %s",
            len(kb_items),
            user_id,
        )

        validation = await self.rag_validator.run(
            question=query,
            kb_items=kb_items,
            ltm_items=[],
            history_block=None,
        )
        strategy = validation.get("strategy") or "kb"
        notes = validation.get("notes") or ""
        filtered_kb = validation.get("kb_items") or []

        if strategy == "llm_only":
            logger.info("RAG validator selected llm_only strategy, skipping context.")
            return ContextBundle(items=[], source="llm_only", strategy="llm_only", notes=notes)

        if strategy == "web_search":
            logger.info("RAG validator switched strategy to web_search.")
            search_results = await self.web_searcher.search(query)
            # web_searcher.search() возвращает Dict с ключом 'items', а не список напрямую
            if search_results and isinstance(search_results, dict):
                items = search_results.get("items", [])
                if items:
                    return ContextBundle(
                        items=items,
                        source="web_search",
                        strategy="web_search",
                        notes=notes or "Context pulled via external search.",
                    )
            logger.warning("Web search returned no results; continuing without snippets.")
            return ContextBundle(items=[], source="web_search", strategy="web_search", notes="No web results.")

        if filtered_kb:
            return ContextBundle(
                items=filtered_kb,
                source=self.retrieval_cfg.source_filter,
                strategy="kb",
                notes=notes,
            )

        logger.info("RAG validator returned empty KB, falling back to llm_only strategy.")
        return ContextBundle(items=[], source="llm_only", strategy="llm_only", notes="No relevant knowledge found.")

    def _search_docanalysis(self, query: str, user_id: int) -> List[Dict[str, Any]]:
        """
        Выполняет поиск знаний по DocAnalysis.

        Args:
            query (str): Исходный запрос.
            user_id (int): Идентификатор пользователя (зарезервировано на будущее).

        Returns:
            List[Dict[str, Any]]: Отфильтрованный список фрагментов знаний.
        """
        if not self.retriever or not query:
            return []
        try:
            raw_items = self.retriever.search_knowledge_base(
                query=query,
                limit=max(1, self.retrieval_cfg.kb_limit * 2),
            )
        except Exception as exc:
            logger.error("Error during DocAnalysis search: %s", exc, exc_info=True)
            return []

        allowed_source = self.retrieval_cfg.source_filter.lower()
        filtered = [
            item for item in raw_items
            if str(item.get("source") or "").lower() == allowed_source
        ]
        preview = ", ".join(
            shorten((item.get("title") or item.get("knowledge") or "")[:120], width=80, placeholder="...")
            for item in filtered[:3]
        )
        if preview:
            logger.debug("DocAnalysis preview: %s", preview)
        return filtered[: self.retrieval_cfg.kb_limit]

    @staticmethod
    def _history_block(history: Sequence[Dict[str, str]] | None, limit: int) -> str:
        """
        Формирует строку с фрагментом истории диалога заданной длины.

        Args:
            history (Sequence[Dict[str, str]] | None): Исходная история сообщений.
            limit (int): Максимальное число сообщений для включения в историю.

        Returns:
            str: Сформированная история для агента.
        """
        if not history:
            return "History is empty."
        window = history[-limit:] if limit > 0 else history
        lines: List[str] = []
        for idx, message in enumerate(window, start=1):
            role = (message.get("role") or "").lower()
            role_label = "User" if role == "user" else "Assistant"
            content = (message.get("content") or "").strip().replace("\n", " ")
            if content:
                lines.append(f"{idx}. {role_label}: {content}")
        return "\n".join(lines) or "History is empty."

    @staticmethod
    def _context_block(items: List[Dict[str, Any]]) -> str:
        """
        Формирует строку для передачи контекста агенту (отформатированные выдержки знаний).

        Args:
            items (List[Dict[str, Any]]): Список фрагментов контекста.

        Returns:
            str: Готовая строка для prompt агента.
        """
        if not items:
            return "No supporting context available. Fall back to general knowledge."
        lines: List[str] = []
        for idx, item in enumerate(items, start=1):
            # Обработка случая, когда item может быть строкой вместо словаря
            if isinstance(item, str):
                title = f"Fragment {idx}"
                knowledge = item.strip()
            elif isinstance(item, dict):
                title = item.get("title") or f"Fragment {idx}"
                knowledge = (item.get("knowledge") or "").strip()
            else:
                # Fallback для других типов
                title = f"Fragment {idx}"
                knowledge = str(item).strip()
            lines.append(f"{idx}. {title}\n{knowledge}")
        return "\n\n".join(lines)

    def _build_graph(self):
        """
        Построение пайплайна LangGraph с последовательными шагами оркестрации.

        Returns:
            StateGraph: Скомпилированный объект графа для асинхронного запуска.
        """
        graph = StateGraph(ContractGraphState)

        async def intent_node(state: ContractGraphState) -> ContractGraphState:
            """
            Узел детекции намерения пользователя.

            Args:
                state (ContractGraphState): Входное состояние графа.

            Returns:
                ContractGraphState: Изменённое состояние с распознанным намерением.
            """
            request = state.get("request") or ""
            history_block = state.get("history_block") or "History is empty."
            intent = await self.intent_agent.run(request, history_block)
            logger.info(
                "Intent agent predicted action '%s' for user %s",
                intent.get("action"),
                state.get("user_id"),
            )
            return {"intent": intent}

        async def context_node(state: ContractGraphState) -> ContractGraphState:
            """
            Узел подготовки контекста.

            Args:
                state (ContractGraphState): Состояние с запросом и намерением.

            Returns:
                ContractGraphState: Дополненное состояние с контекстом.
            """
            request = state.get("request") or ""
            user_id = state.get("user_id") or 0
            context_bundle = await self._prepare_context(request, user_id)
            context_block = self._context_block(context_bundle.items)
            return {
                "context_bundle": context_bundle,
                "context_block": context_block,
            }

        async def action_node(state: ContractGraphState) -> ContractGraphState:
            """
            Узел выполнения действия (генерация или рецензирование).

            Args:
                state (ContractGraphState): Состояние с контекстом и намерением.

            Returns:
                ContractGraphState: Состояние с результатом работы подходящего агента.
            """
            intent = state.get("intent") or {}
            request = state.get("request") or ""
            context_block = state.get("context_block") or "No supporting context available."
            action = (intent.get("action") or "analyze").lower()
            if action == "draft":
                response = await self.draft_agent.run(
                    intent.get("document_type") or "Document",
                    intent.get("key_requirements") or [intent.get("notes") or request],
                    context_block,
                )
            else:
                response = await self.reviewer_agent.run(request, context_block)
            return {"result": response}

        def assemble_node(state: ContractGraphState) -> ContractGraphState:
            """
            Узел сборки финального ответа.

            Args:
                state (ContractGraphState): Состояние после агентов.

            Returns:
                ContractGraphState: Словарь с итоговым выходом.
            """
            context_bundle = state.get("context_bundle") or ContextBundle([], "llm_only", "llm_only", "")
            output = {
                "intent": state.get("intent") or {},
                "context": {
                    "items": context_bundle.items,
                    "source": context_bundle.source,
                    "strategy": context_bundle.strategy,
                    "notes": context_bundle.notes,
                },
                "result": state.get("result") or "",
                "disclaimer": DISCLAIMER_TEXT,
            }
            return {"output": output}

        graph.add_node("intent", intent_node)
        graph.add_node("context", context_node)
        graph.add_node("action", action_node)
        graph.add_node("assemble", assemble_node)
        graph.set_entry_point("intent")
        graph.add_edge("intent", "context")
        graph.add_edge("context", "action")
        graph.add_edge("action", "assemble")
        graph.add_edge("assemble", END)
        return graph.compile()
