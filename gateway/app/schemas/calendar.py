"""Calendar schemas"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class EventCreate(BaseModel):
    """Схема для создания события"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_date: datetime
    end_date: datetime
    category: Optional[str] = None
    color: Optional[str] = "#3b82f6"
    reminder_minutes: Optional[int] = None
    is_all_day: bool = False
    burnout_prevention: bool = False
    linked_chat_id: Optional[str] = None
    linked_folder_id: Optional[str] = None

class EventUpdate(BaseModel):
    """Схема для обновления события"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category: Optional[str] = None
    color: Optional[str] = None
    reminder_minutes: Optional[int] = None
    is_all_day: Optional[bool] = None
    burnout_prevention: Optional[bool] = None
    linked_chat_id: Optional[str] = None
    linked_folder_id: Optional[str] = None

class EventResponse(BaseModel):
    """Схема ответа с событием"""
    id: str = Field(alias="event_id")
    user_id: str
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    category: Optional[str] = None
    color: Optional[str] = None
    reminder_minutes: Optional[int] = None
    is_all_day: bool = False
    burnout_prevention: bool = False
    linked_chat_id: Optional[str] = None
    linked_folder_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

