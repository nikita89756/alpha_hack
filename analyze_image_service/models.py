from pydantic import BaseModel, Field
from typing import Optional


class ImageAnalysisRequest(BaseModel):
    model: Optional[str] = Field(
        default="google/gemini-flash-1.5-8b",
        description="Модель для анализа изображения"
    )
    prompt: Optional[str] = Field(
        default="Опиши всё, что видишь на этом изображении.",
        description="Пользовательский промпт для анализа"
    )
    max_tokens: Optional[int] = Field(
        default=2048,
        description="Максимальное количество токенов в ответе"
    )


class ImageAnalysisResponse(BaseModel):
    success: bool
    description: str
    error: Optional[str] = None
    image_url: Optional[str] = None 


class HealthResponse(BaseModel):
    status: str
    version: str
