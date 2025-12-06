from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ChatResponse(BaseModel):
    chat_id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int
    is_active: bool
    folder_id: Optional[str] = None
