from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SendMessageRequest(BaseModel):
    message: str
    chat_id: str
    chat_type: str
    photo_description: Optional[str] = None
    photo_url: Optional[str] = None
    business_id: Optional[str] = None
    parsed_document: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Привет! Как дела?",
                "chat_type": "support",
                "chat_id": "550e8400-e29b-41d4-a716-446655440000",
                "business_id": "1234567890",
                "photo_url": "https://example.com/image.jpg",
                "photo_description": "Описание фотографии",
                "parsed_document": "Текст из документа"
            }
        }


class MessageResponse(BaseModel):
    message_id: str
    user_id: str
    chat_id: str
    message: str
    timestamp: datetime
    status: str
