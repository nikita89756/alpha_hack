"""Агент для веб-поиска через LangChain 1.1.0 и кастомный LLM."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..config import AGENTS_CONFIG
from ..utils.llm_client import AsyncLLMClient
from ..utils.logger import logger

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun
from pydantic import Field, ConfigDict

LANGCHAIN_AVAILABLE = True


class _LangChainAsyncAdapter(BaseChatModel):
    """Адаптер LangChain поверх AsyncLLMClient."""
    
    client: Any = Field(default=None, exclude=True)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=1024)
    model_name: str = Field(default="custom-llm")
    
    model_config = ConfigDict(
        extra='allow',
        arbitrary_types_allowed=True,
    )

    def __init__(self, client: AsyncLLMClient, *, temperature: float, max_tokens: int) -> None:
        if not LANGCHAIN_AVAILABLE:
            raise RuntimeError("LangChain недоступен, установите 'langchain>=1.1.0 langchain-community'")
        super().__init__(
            client=client,
            temperature=temperature,
            max_tokens=max_tokens,
            model_name=client.model,
        )

    @property
    def _llm_type(self) -> str:
        return "custom-async-llm"

    def _serialize_message(self, message: BaseMessage) -> Dict[str, str]:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            parts: List[str] = []
            for chunk in content:
                if isinstance(chunk, dict):
                    parts.append(chunk.get("text") or chunk.get("value") or "")
                else:
                    parts.append(str(chunk))
            text = "\n".join(filter(None, parts))
        else:
            text = str(content)
        
        role_map = {
            "human": "user",
            "ai": "assistant",
            "system": "system",
        }
        msg_type = getattr(message, "type", "user")
        role = role_map.get(msg_type, "user")
        
        return {"role": role, "content": text}

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Основной метод для асинхронной генерации ответов."""
        payload = [self._serialize_message(msg) for msg in messages]
        response = await self.client.ainvoke(
            payload,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        text = response.content or ""
        if stop:
            for token in stop:
                if token and token in text:
                    text = text.split(token)[0]
                    break
        generation = ChatGeneration(message=AIMessage(content=text))
        return ChatResult(generations=[generation])

    def _generate(self, *args: Any, **kwargs: Any) -> ChatResult:
        """Синхронный метод не поддерживается."""
        raise NotImplementedError("Используйте асинхронный интерфейс LangChain.")


class WebSearcherAgent:
    """Fallback-агент, который ищет свежие факты через LangChain."""

    def __init__(self, llm: AsyncLLMClient) -> None:
        self.llm = llm
        self.config = AGENTS_CONFIG.web_search
        if not LANGCHAIN_AVAILABLE:
            logger.warning(
                "LangChain недоступен. Установите 'pip install langchain-classic langchain-community duckduckgo-search', чтобы включить веб-поиск."
            )

    async def search(self, query: str) -> Dict[str, Any]:
        """Запускает LangChain-агента с инструментом DuckDuckGo.
        
        Returns:
            Dict with keys:
            - 'items': List[Dict[str, Any]] - search results
            - 'source_links': List[str] - list of source URLs
        """
        if not LANGCHAIN_AVAILABLE:
            return {
                'items': [],
                'source_links': []
            }

        task = self.config.task_template.format(query=query.strip())
        max_iterations = max(1, int(self.config.max_steps))
        adapter = _LangChainAsyncAdapter(
            client=self.llm,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        
        source_links = []
        try:
            search_tool = DuckDuckGoSearchRun(max_results=self.config.max_search_results)
        except Exception as exc:
            logger.error("Ошибка инициализации DuckDuckGoSearchRun: %s", exc)
            return {
                'items': [],
                'source_links': []
            }

        tools = [
            Tool(
                name="duckduckgo_search",
                description="Поиск по вебу для актуальных фактов и ссылок.",
                func=search_tool.run,
                coroutine=search_tool.arun,
            )
        ]

        try:
            prompt = PromptTemplate.from_template(
                "Ты аналитик-расследователь. Отвечай на русском языке, цитируй ссылки из результатов DuckDuckGo.\n\n"
                "Используй следующий формат:\n"
                "Question: {input}\n"
                "Thought: рассуждение о следующем шаге\n"
                "Action: одно из [{tool_names}]\n"
                "Action Input: аргументы для инструмента\n"
                "Observation: результат действия\n"
                "... (повторяй блоки Thought/Action/Action Input/Observation при необходимости)\n"
                "Thought: I now know the final answer\n"
                "Final Answer: краткая сводка с фактами и ссылками\n\n"
                "Имеешь доступ к инструментам:\n"
                "{tools}\n\n"
                "История:\n"
                "{agent_scratchpad}"
            )
            agent = create_react_agent(adapter, tools, prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=False,
                handle_parsing_errors=True,
                max_iterations=max_iterations,
                max_execution_time=max(5, int(self.config.max_runtime_seconds)),
            )
            result = await executor.ainvoke({"input": task})
        except Exception as exc:
            logger.error("Не удалось выполнить веб-поиск через LangChain: %s", exc, exc_info=True)
            return []

        output_text = (result.get("output") or "").strip()
        fallback_triggered = (
            not output_text
            or "Agent stopped due to iteration limit" in output_text
            or "time limit" in output_text.lower()
        )
        if fallback_triggered:
            fallback_source = "agent-fallback"
            try:
                direct_response = search_tool.run(query).strip()
            except Exception as fallback_exc:
                logger.warning(
                    "Direct DuckDuckGo fallback failed: %s",
                    fallback_exc,
                    exc_info=True,
                )
                direct_response = ""

            if direct_response:
                output_text = direct_response
                fallback_source = "direct-search"
                if hasattr(search_tool, 'sources'):
                    source_links = getattr(search_tool, 'sources', [])
        else:
            output_text = (
                "DuckDuckGo не вернул свежих результатов по этому запросу. "
                "Попробуйте уточнить дату, добавить ключевые бренды или изменить формулировку."
            )
            fallback_source = "agent"

        result = {
            'items': [
                {
                    "id": f"web_{uuid4().hex[:8]}",
                    "title": f"Веб-поиск: {query[:80]}",
                    "knowledge": output_text,
                    "score": 0.0,
                    "source": "langchain-web",
                    "metadata": {
                        "task": task,
                        "tool": "DuckDuckGoSearchRun",
                        "result_source": fallback_source,
                    },
                }
            ],
            'source_links': source_links
        }

        logger.info(
            "Web search completed",
            extra={
                "title": result['items'][0]["title"],
                "knowledge_preview": output_text[:200],
                "query": query,
                "task": task,
                "tool": "DuckDuckGoSearchRun",
                "result_source": fallback_source,
                "fallback_triggered": fallback_triggered,
            },
        )
        return result
