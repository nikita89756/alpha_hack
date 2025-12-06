from pydantic import BaseModel, Field
from typing import Optional
class DocumentParseResponse(BaseModel):
    """Схема ответа от сервиса парсинга документов"""
    
    filename: str = Field(..., description="Имя файла")
    content_type: Optional[str] = Field(None, description="MIME тип документа")
    text: str = Field(..., description="Извлеченный текст из документа")
    text_length: int = Field(..., description="Длина извлеченного текста")
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "text": "Извлеченный текст из документа...",
                "text_length": 1250
            }
        }