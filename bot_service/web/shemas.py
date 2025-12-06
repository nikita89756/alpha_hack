"""Pydantic-схемы, используемые публичным API."""

from typing import Any, Dict, Literal, Sequence, Union,List

from pydantic import BaseModel, Field


class DialogueMessageMemory(BaseModel):
    """Элемент диалога, используемый для записи памяти."""

    role: str = Field(..., description="The role of the speaker (e.g., 'user', 'operator').")
    content: str = Field(..., description="The content of the message.")


class MemorizeRequest(BaseModel):
    """Запрос на сохранение фактов в долгосрочную память."""

    user_id: str = Field(..., description="The unique identifier for the user.")
    dialogue: Sequence[DialogueMessageMemory] = Field(
        ..., description="The sequence of messages in the dialogue."
    )


class AnswerRequest(BaseModel):
    """Запрос генерации ответа пользователя."""

    query: str = Field(..., description="User query text.")
    history: Sequence[Dict[str, str]] = Field(
        default_factory=list,
        description="Conversation history as list of messages.",
    )
    user_id: str = Field(default=1, description="User ID.")


class AnswerContextItem(BaseModel):
    """Контекстный фрагмент, возвращаемый в ответе."""

    id: Union[str, int]
    title: str = ""
    knowledge: str = ""
    score: float | None = None


class AnswerResponse(BaseModel):
    """Ответ API /answer."""

    answer: str = Field(..., description="Generated answer text.")
    next_action: Literal["exit", "continue"] = Field(..., description="`exit` or `continue` flag.")
    source: Literal["rag", "web-search", "llm-only"] = Field(
        ..., description="Primary source used to assemble the answer."
    )
    source_links: Sequence[str] = Field(
        default_factory=list,
        description="Web links used when source is web-search.",
    )
    kb: Sequence[AnswerContextItem] = Field(
        default_factory=list,
        description="Knowledge base fragments.",
    )
    ltm: Sequence[AnswerContextItem] = Field(
        default_factory=list,
        description="Long-term memory fragments.",
    )


class ContractAnalysisRequest(BaseModel):
    """Запрос на запуск пайплайна анализа договоров."""

    request: str = Field(..., description="User request or excerpt to analyze.")
    history: Sequence[Dict[str, str]] = Field(
        default_factory=list,
        description="Conversation history between user and assistant.",
    )
    user_id: str = Field(default=0, description="Numeric identifier of the user.")


class ContractIntentPayload(BaseModel):
    """Распознанное намерение документа."""

    action: Literal["analyze", "draft"] = Field(..., description="Requested operation.")
    document_type: str = Field(..., description="Document type mentioned by the intent agent.")
    key_requirements: Sequence[str] = Field(
        default_factory=list,
        description="Key requirements extracted from the prompt.",
    )
    notes: str = Field("", description="Additional notes detected by the intent agent.")
    raw: Dict[str, Any] | None = Field(
        default=None,
        description="Raw response payload returned by the intent agent.",
    )


class ContractContextItem(BaseModel):
    """Контекстный фрагмент, возвращаемый пайплайном contract_analysis."""

    id: Union[str, int, None] = Field(default=None, description="Identifier of the fragment.")
    title: str = Field("", description="Title or summary of the fragment.")
    knowledge: str = Field("", description="Full text of the fragment.")
    source: str | None = Field(default=None, description="Source label (DocAnalysis, web, etc.).")
    score: float | None = Field(default=None, description="Optional relevance score.")


class ContractContextPayload(BaseModel):
    """Описание источника и стратегии формирования контекста."""

    source: str = Field(..., description="Primary source used for context (kb, web_search, llm_only).")
    strategy: str = Field(..., description="Strategy label returned by the validator.")
    notes: str = Field("", description="Additional notes from the validator.")
    items: Sequence[ContractContextItem] = Field(
        default_factory=list,
        description="List of supporting fragments.",
    )


class ContractAnalysisResponse(BaseModel):
    """Ответ API для пайплайна анализа документов."""

    intent: ContractIntentPayload
    context: ContractContextPayload
    result: str = Field(..., description="Generated review or draft.")
    disclaimer: str = Field(..., description="Disclaimer appended to model responses.")

class KnowledgeDocument(BaseModel):
    """Represents a single document chunk that can be stored in Qdrant."""
    knowledge: str = Field(..., min_length=1, description="Plain text content that should be indexed.")
    title: str | None = Field(default=None, description="Optional human readable title for the chunk.")

class KnowledgeUploadRequest(BaseModel):
    """Defines the structure for the /knowledge/upload endpoint request."""
    source: str = Field(..., min_length=1, description="Identifier of the data source (e.g., file name).")
    documents: Sequence[KnowledgeDocument] = Field(..., description="Documents that must be ingested.")


class KnowledgeUploadResponse(BaseModel):
    """Response model for the /knowledge/upload endpoint."""
    source: str = Field(..., description="The source whose documents were ingested.")
    imported: int = Field(..., ge=0, description="How many documents were saved.")
    message: str = Field(..., description="Status message describing the ingestion result.")
    

class OnboardingPayload(BaseModel):
    user_id: str
    business_id: str
    
    business_goals: List[str]
    business_description: str
    
    daily_tasks: List[str]
    daily_routine_description: str
    
    business_type: str
    business_name: str
    city: str
    
    primary_pain_point: List[str]
    pain_description: str
