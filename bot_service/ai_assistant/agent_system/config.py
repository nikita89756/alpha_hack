"""Конфигурационные модели для агентной системы."""

from dataclasses import dataclass, field
import dotenv

dotenv.load_dotenv()

@dataclass
class AgentLLMConfig:
    """Базовые параметры взаимодействия агента с LLM."""

    name: str
    temperature: float
    max_tokens: int


@dataclass
class AnswerAgentConfig(AgentLLMConfig):
    name: str = "answer"
    temperature: float = 1.2
    max_tokens: int = 2000


@dataclass
class ValidatorAgentConfig(AgentLLMConfig):
    name: str = "validator"
    temperature: float = 0.5
    max_tokens: int = 800


@dataclass
class IntentAgentConfig(AgentLLMConfig):
    name: str = "intent_rewrite"
    temperature: float = 0.2
    max_tokens: int = 1500


@dataclass
class RagValidatorAgentConfig(AgentLLMConfig):
    name: str = "rag_validator"
    temperature: float = 0.15
    max_tokens: int = 600


@dataclass
class WebSearcherAgentConfig(AgentLLMConfig):
    name: str = "web_searcher"
    temperature: float = 0.4
    max_tokens: int = 900
    max_steps: int = 5
    max_runtime_seconds: int = 20
    task_template: str = (
        "Ты веб-аналитик. Найди актуальные данные по запросу: \"{query}\". "
        "Сначала используй поисковую систему, затем открой минимум 3 релевантных источников. "
        "Если DuckDuckGo вернул пустой результат, немедленно завершай работу и сообщи, что свежих данных нет. "
        "В финальной сводке перечисли резюме и добавь ссылки."
    )
    max_search_results: int = 5


@dataclass
class RetrievalAgentConfig:
    kb_limit: int = 5


@dataclass
class AgentsConfig:
    """Сводная конфигурация для специализированных агентов."""
    model: str = "deepseek/deepseek-chat-v3.1"
    answer: AnswerAgentConfig = field(default_factory=AnswerAgentConfig)
    validator: ValidatorAgentConfig = field(default_factory=ValidatorAgentConfig)
    intent: IntentAgentConfig = field(default_factory=IntentAgentConfig)
    rag_validator: RagValidatorAgentConfig = field(default_factory=RagValidatorAgentConfig)
    web_search: WebSearcherAgentConfig = field(default_factory=WebSearcherAgentConfig)
    retrieval: RetrievalAgentConfig = field(default_factory=RetrievalAgentConfig)


AGENTS_CONFIG = AgentsConfig()
