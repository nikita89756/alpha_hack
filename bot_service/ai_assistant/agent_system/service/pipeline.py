"""Мультиагентный конвейер, который управляет намерением, поиском, ответом и валидацией."""

from typing import Any, Dict, List, TypedDict
from textwrap import shorten

from langgraph.graph import END, StateGraph

from ..agents.answer import AnswerAgent
from ..agents.intent_rewrite import IntentRewriteAgent
from ..agents.rag_validator import RagValidatorAgent
from ..agents.retrieval import RetrievalAgent
from ..agents.validator import ValidationAgent
from ..agents.web_searcher import WebSearcherAgent
from ..rag import RetrieverController
from ..utils.llm_client import AsyncLLMClient
from ..utils.logger import logger


class PipelineState(TypedDict, total=False):
    """Типизированное состояние для LangGraph."""

    user_text: str
    user_id: int
    history: List[Dict[str, str]]
    history_block: str
    intent: Dict[str, Any]
    exit_intent: bool
    off_topic_intent: bool
    kb_query: str
    memory_query: str
    answer_query: str
    kb_items: List[Dict[str, Any]]
    ltm_items: List[Dict[str, Any]]
    validated_items: List[Dict[str, Any]]
    validated_ltm_items: List[Dict[str, Any]]
    strategy: str
    notes: str
    context_items: List[Dict[str, Any]]
    context_ltm_items: List[Dict[str, Any]]
    context_source: str
    draft: str
    final_answer: str
    response: Dict[str, Any]


class AgentPipeline:
    """Координирует поток запросов между отдельными агентами через LangGraph."""

    def __init__(
        self,
        llm_for_agents: AsyncLLMClient,
        retriever: RetrieverController,
    ) -> None:
        """Инициализирует конвейер с общими зависимостями.

        Args:
            llm_for_agents (AsyncLLMClient): Клиент, используемый всеми LLM-агентами.
            retriever: Контроллер поиска, передаваемый RetrievalAgent.
        """
        self.intent = IntentRewriteAgent(llm_for_agents)
        self.retrieve = RetrievalAgent(retriever)
        self.retriever = retriever
        self.rag_validator = RagValidatorAgent(llm_for_agents)
        self.web_search = WebSearcherAgent(llm_for_agents)
        self.answer = AnswerAgent(llm_for_agents)
        self.validator = ValidationAgent(llm_for_agents)
        self._graph = self._build_graph()

    @staticmethod
    def _history_to_text(history: List[Dict[str, str]] | None, limit: int = 8) -> str:
        """Формирует человекочитаемый блок истории для промптов."""
        if not history:
            return "История пуста."

        window = history[-limit:]
        lines: List[str] = []
        for idx, message in enumerate(window, start=1):
            role = (message.get("role") or "").lower()
            role_label = "Пользователь" if role == "user" else "Ассистент" if role == "assistant" else (role or "роль")
            content = (message.get("content") or "").strip().replace("\n", " ")
            if not content:
                continue
            lines.append(f"{idx}. {role_label}: {content}")

        return "\n".join(lines) if lines else "История пуста."

    @staticmethod
    def _log_retrieval(items: List[Dict[str, Any]], user_id: int) -> None:
        """Записывает структурированные логи для каждого найденного фрагмента БЗ."""
        if not items:
            logger.info(
                "Retrieval returned no knowledge base items",
                extra={"user_id": user_id, "source": "kb"},
            )
            return

        total = len(items)
        for idx, item in enumerate(items, start=1):
            knowledge_text = (item.get("knowledge") or "").replace("\n", " ")
            preview = shorten(knowledge_text, width=160, placeholder="...") if knowledge_text else ""
            score = item.get("score")
            score_repr = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
            logger.info(
                "Retrieved KB item %d/%d (score=%s)",
                idx,
                total,
                score_repr,
                extra={
                    "user_id": user_id,
                    "title": item.get("title") or "",
                    "knowledge_preview": preview,
                    "source": "kb",
                },
            )

    @staticmethod
    def _log_memory(items: List[Dict[str, Any]], user_id: int) -> None:
        """Логирует результаты поиска в долговременной памяти."""

        if not items:
            logger.info(
                "Memory retrieval returned no items",
                extra={"user_id": user_id, "source": "ltm"},
            )
            return

        total = len(items)
        for idx, item in enumerate(items, start=1):
            knowledge_text = (item.get("knowledge") or "").replace("\n", " ")
            preview = shorten(knowledge_text, width=160, placeholder="...") if knowledge_text else ""
            score = item.get("score")
            score_repr = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
            logger.info(
                "Retrieved LTM item %d/%d (score=%s)",
                idx,
                total,
                score_repr,
                extra={
                    "user_id": user_id,
                    "title": item.get("title") or "",
                    "knowledge_preview": preview,
                    "source": "ltm",
                },
            )

    def _build_graph(self):
        """Собирает LangGraph для агентного контура."""
        graph = StateGraph(PipelineState)

        async def intent_node(state: PipelineState) -> PipelineState:
            history_block = state.get("history_block") or "История пуста."
            user_text = state.get("user_text") or ""
            intent = await self.intent.run(user_text=user_text, history_block=history_block)
            kb_query = intent.get("kb_query") or user_text
            answer_query = intent.get("answer_query") or user_text
            return {
                "intent": intent,
                "kb_query": kb_query,
                "memory_query": intent.get("ltm_query") or kb_query,
                "answer_query": answer_query,
                "exit_intent": bool(intent.get("exit")),
                "off_topic_intent": bool(intent.get("off_topic")),
            }

        async def exit_node(state: PipelineState) -> PipelineState:
            draft = "Спасибо за обращение! Если появятся ещё вопросы — я на связи."
            final = await self.validator.run(draft)
            return {
                "draft": draft,
                "final_answer": final,
                "response": {"final": final, "kb": [], "exit": True},
            }

        async def alignment_node(state: PipelineState) -> PipelineState:
            user_id = state.get("user_id", 0)
            logger.info(
                "Intent agent flagged off-topic request; responding with alignment message",
                extra={"user_id": user_id, "source": "intent"},
            )
            draft = (
                "Сейчас я сфокусирован на бизнес-задачах и вопросах по продукту. "
                "Поделитесь, пожалуйста, чем могу помочь в рамках работы или сервиса."
            )
            final = await self.validator.run(draft)
            return {
                "draft": draft,
                "final_answer": final,
                "response": {
                    "final": final,
                    "kb": [],
                    "exit": False,
                    "context_source": "alignment",
                },
            }

        async def retrieval_node(state: PipelineState) -> PipelineState:
            kb_query = state.get("kb_query") or ""
            user_id = state.get("user_id", 0)
            kb_items = self.retrieve.run(kb_query)
            self._log_retrieval(kb_items, user_id)
            return {"kb_items": kb_items}

        def _fetch_memory(query: str, user_id: int, limit: int = 3) -> List[Dict[str, Any]]:
            if not query or not user_id:
                return []
            return self.retriever.search_long_term_memory(query, user_id=user_id, limit=limit)

        async def memory_retrieval_node(state: PipelineState) -> PipelineState:
            memory_query = state.get("memory_query") or ""
            user_id = state.get("user_id", 0)
            ltm_items = _fetch_memory(memory_query, user_id)
            self._log_memory(ltm_items, user_id)
            return {"ltm_items": ltm_items}

        async def rag_validator_node(state: PipelineState) -> PipelineState:
            history_block = state.get("history_block") or "История пуста."
            answer_query = state.get("answer_query") or ""
            kb_items = state.get("kb_items") or []
            ltm_items = state.get("ltm_items") or []
            user_id = state.get("user_id", 0)
            validation = await self.rag_validator.run(
                answer_query,
                kb_items,
                ltm_items=ltm_items,
                history_block=history_block,
            )
            validated_items = validation.get("kb_items") or []
            validated_ltm_items = validation.get("ltm_items") or []
            strategy = (validation.get("strategy") or "kb").lower()
            notes = validation.get("notes") or ""
            logger.info(
                "RAG validator kept %d/%d KB fragments and %d/%d LTM fragments (strategy=%s)",
                len(validated_items),
                len(kb_items),
                len(validated_ltm_items),
                len(ltm_items),
                strategy,
                extra={"user_id": user_id, "source": "rag_validator"},
            )
            return {
                "strategy": strategy,
                "notes": notes,
                "validated_items": validated_items,
                "validated_ltm_items": validated_ltm_items,
            }

        async def web_search_node(state: PipelineState) -> PipelineState:
            answer_query = state.get("answer_query") or ""
            user_id = state.get("user_id", 0)
            memory_context = state.get("validated_ltm_items") or []
            
            web_search_result = await self.web_search.search(answer_query)
            web_items = web_search_result.get('items', [])
            source_links = web_search_result.get('source_links', [])
            
            logger.info(
                "Web search strategy executed (results=%d, links=%d)",
                len(web_items),
                len(source_links),
                extra={"user_id": user_id, "source": "web_search"},
            )
            
            if web_items:
                return {
                    "context_items": web_items,
                    "context_source": "web",
                    "context_ltm_items": memory_context,
                    "source_links": source_links,
                }
            logger.info(
                "Web search returned no results; switching to llm-only strategy",
                extra={"user_id": user_id, "source": "web_search"},
            )
            return {
                "context_items": [],
                "context_source": "history",
                "context_ltm_items": memory_context,
                "strategy": "llm_only",
            }

        async def history_context_node(state: PipelineState) -> PipelineState:
            user_id = state.get("user_id", 0)
            notes = state.get("notes") or ""
            logger.info(
                "Validator selected LLM-only strategy (%s)",
                notes,
                extra={"user_id": user_id, "source": "history"},
            )
            return {
                "context_items": [],
                "context_source": "history",
                "context_ltm_items": state.get("validated_ltm_items") or [],
            }

        def prepare_context_node(state: PipelineState) -> PipelineState:
            user_id = state.get("user_id", 0)
            existing_source = state.get("context_source")
            if existing_source:
                normalized_source = existing_source.lower()
                if normalized_source != "kb" or state.get("context_items"):
                    return {
                        "context_items": state.get("context_items") or [],
                        "context_source": existing_source,
                        "context_ltm_items": state.get("context_ltm_items")
                        or state.get("validated_ltm_items")
                        or [],
                    }
            strategy = (state.get("strategy") or "kb").lower()
            context_items = state.get("validated_items") or []
            context_source = "kb"
            if not context_items and strategy != "llm_only":
                kb_items = state.get("kb_items") or []
                if kb_items:
                    logger.info(
                        "Context items empty after validation; using original KB fragments",
                        extra={"user_id": user_id, "source": "kb"},
                    )
                context_items = kb_items
            return {
                "context_items": context_items,
                "context_source": context_source,
                "context_ltm_items": state.get("validated_ltm_items") or [],
            }

        async def answer_node(state: PipelineState) -> PipelineState:
            answer_query = state.get("answer_query") or ""
            history_block = state.get("history_block") or "История пуста."
            context_items = state.get("context_items") or []
            memory_context = state.get("context_ltm_items") or []
            draft = await self.answer.run(
                answer_query,
                context_items,
                history_block=history_block,
                memory_items=memory_context,
            )
            return {"draft": draft}

        async def validator_node(state: PipelineState) -> PipelineState:
            draft = state.get("draft") or ""
            final_answer = await self.validator.run(draft)
            return {"final_answer": final_answer}

        def assemble_response_node(state: PipelineState) -> PipelineState:
            final_answer = state.get("final_answer") or ""
            context_source = state.get("context_source") or "kb"
            context_items = state.get("context_items") or []
            context_ltm_items = state.get("context_ltm_items") or []
            source_links = state.get("source_links", [])
            history_block = state.get("history_block") or "История пуста."
            user_id = state.get("user_id", 0)
            response_kb = (
                [{"id": "history", "title": "История диалога", "knowledge": history_block}]
                if context_source == "history"
                else context_items
            )
            
            source_map = {
                "web": "web-search",
                "kb": "rag",
                "history": "llm-only"
            }
            response_source = source_map.get(context_source, "llm-only")
            
            logger.info(
                "Response assembled using %s context (%d fragments, %d links) -> mapped to %s",
                context_source,
                len(context_items),
                len(source_links),
                response_source,
                extra={"user_id": user_id, "source": context_source},
            )
            return {
                "response": {
                    "final": final_answer,
                    "kb": response_kb,
                    "ltm": context_ltm_items,
                    "exit": False,
                    "context_source": response_source,
                    "source_links": source_links,
                }
            }

        graph.add_node("intent", intent_node)
        graph.add_node("exit_response", exit_node)
        graph.add_node("alignment_response", alignment_node)
        graph.add_node("retrieval", retrieval_node)
        graph.add_node("memory_retrieval", memory_retrieval_node)
        graph.add_node("rag_validator", rag_validator_node)
        graph.add_node("web_search", web_search_node)
        graph.add_node("history_context", history_context_node)
        graph.add_node("prepare_context", prepare_context_node)
        graph.add_node("answer", answer_node)
        graph.add_node("validator", validator_node)
        graph.add_node("assemble_response", assemble_response_node)

        def route_intent(state: PipelineState) -> str:
            if state.get("exit_intent"):
                return "exit"
            if state.get("off_topic_intent"):
                return "off_topic"
            return "retrieval"

        def route_strategy(state: PipelineState) -> str:
            strategy = (state.get("strategy") or "kb").lower()
            if strategy == "web_search":
                return "web_search"
            if strategy == "llm_only":
                return "llm_only"
            return "prepare_context"

        graph.set_entry_point("intent")
        graph.add_conditional_edges(
            "intent",
            route_intent,
            {
                "exit": "exit_response",
                "off_topic": "alignment_response",
                "retrieval": "retrieval",
            },
        )
        graph.add_edge("exit_response", END)
        graph.add_edge("alignment_response", END)
        graph.add_edge("retrieval", "memory_retrieval")
        graph.add_edge("memory_retrieval", "rag_validator")
        graph.add_conditional_edges(
            "rag_validator",
            route_strategy,
            {
                "web_search": "web_search",
                "llm_only": "history_context",
                "prepare_context": "prepare_context",
            },
        )
        graph.add_edge("web_search", "prepare_context")
        graph.add_edge("history_context", "prepare_context")
        graph.add_edge("prepare_context", "answer")
        graph.add_edge("answer", "validator")
        graph.add_edge("validator", "assemble_response")
        graph.add_edge("assemble_response", END)

        return graph.compile()

    async def run(
        self,
        user_text: str,
        user_id: int,
        history: List[Dict[str, str]] | None = None,
        dialogue: List[Dict[str, str]] | None = None,
    ) -> Dict[str, Any]:
        """Запускает мультиагентный конвейер для одного шага диалога."""
        history_list = history or dialogue or []
        history_block = self._history_to_text(history_list)
        initial_state: PipelineState = {
            "user_text": user_text,
            "user_id": user_id or 999,
            "history": history_list,
            "history_block": history_block,
        }
        result_state = await self._graph.ainvoke(initial_state)
        response = result_state.get("response")
        if not response:
            raise RuntimeError("Pipeline завершился без итогового ответа")
        return response
