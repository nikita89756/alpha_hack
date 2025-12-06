from fastapi import FastAPI, HTTPException, status, Header
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, BeforeValidator
from datetime import datetime, date, time
from typing import List, Optional, Annotated
from bson import ObjectId
import os
import uuid

app = FastAPI(title="Calendar Service")

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "chatbot_db")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]
events_collection = db["calendar_events"]

PyObjectId = Annotated[str, BeforeValidator(str)]

class EventBase(BaseModel):
    """Базовая модель события календаря"""
    title: str = Field(..., min_length=1, max_length=200, description="Название события")
    description: Optional[str] = Field(None, max_length=2000, description="Описание события")
    start_date: datetime = Field(..., description="Дата и время начала")
    end_date: datetime = Field(..., description="Дата и время окончания")
    category: Optional[str] = Field(None, description="Категория (работа, отдых, встреча, и т.д.)")
    color: Optional[str] = Field("#3b82f6", description="Цвет события (hex)")
    reminder_minutes: Optional[int] = Field(None, description="Напоминание за N минут")
    is_all_day: bool = Field(False, description="Событие на весь день")
    burnout_prevention: bool = Field(False, description="Метка для анти-выгорания")
    linked_chat_id: Optional[str] = Field(None, description="ID привязанного чата")
    linked_folder_id: Optional[str] = Field(None, description="ID папки привязанного чата")

class EventCreate(EventBase):
    """Модель для создания события"""
    pass

class EventUpdate(BaseModel):
    """Модель для обновления события (все поля опциональны)"""
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

class EventResponse(EventBase):
    """Модель ответа с событием"""
    id: str = Field(alias="event_id")
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "calendar_service"}

@app.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    x_user_id: Annotated[str, Header()]
):
    """
    Создать новое событие в календаре
    - **title**: Название события
    - **start_date**: Дата и время начала
    - **end_date**: Дата и время окончания
    - **burnout_prevention**: Метка для антивыгорания
    """
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
  
    if event.end_date <= event.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    event_dict = event.model_dump()
    event_dict["event_id"] = str(uuid.uuid4())
    event_dict["user_id"] = x_user_id
    event_dict["created_at"] = datetime.utcnow()
    event_dict["updated_at"] = datetime.utcnow()
    
    await events_collection.insert_one(event_dict)
    
    return EventResponse(**event_dict)

@app.get("/events", response_model=List[EventResponse])
async def list_events(
    x_user_id: Annotated[str, Header()],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    burnout_prevention: Optional[bool] = None
):
    """
    Получить список событий пользователя с фильтрацией
    - **start_date**: Фильтр по дате начала (ISO format)
    - **end_date**: Фильтр по дате окончания (ISO format)
    - **category**: Фильтр по категории
    - **burnout_prevention**: Показывать только события с антивыгоранием
    """
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    
    query = {"user_id": x_user_id}

    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        query["start_date"] = date_filter

    if category:
        query["category"] = category

    if burnout_prevention is not None:
        query["burnout_prevention"] = burnout_prevention
    
    events = await events_collection.find(query).sort("start_date", 1).to_list(1000)

    for event in events:
        event["_id"] = str(event["_id"])
    
    return [EventResponse(**event) for event in events]

@app.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    x_user_id: Annotated[str, Header()]
):
    """Получить конкретное событие по ID"""
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    
    event = await events_collection.find_one({
        "event_id": event_id,
        "user_id": x_user_id
    })
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event["_id"] = str(event["_id"])
    return EventResponse(**event)

@app.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    update_data: EventUpdate,
    x_user_id: Annotated[str, Header()]
):
    """Обновить событие"""
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")

    existing_event = await events_collection.find_one({
        "event_id": event_id,
        "user_id": x_user_id
    })
    
    if not existing_event:
        raise HTTPException(status_code=404, detail="Event not found")

    update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "start_date" in update_dict or "end_date" in update_dict:
        start = update_dict.get("start_date", existing_event["start_date"])
        end = update_dict.get("end_date", existing_event["end_date"])
        if end <= start:
            raise HTTPException(status_code=400, detail="End date must be after start date")
    
    update_dict["updated_at"] = datetime.utcnow()
    
    await events_collection.update_one(
        {"event_id": event_id, "user_id": x_user_id},
        {"$set": update_dict}
    )
    
    updated_event = await events_collection.find_one({"event_id": event_id})
    updated_event["_id"] = str(updated_event["_id"])
    
    return EventResponse(**updated_event)

@app.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    x_user_id: Annotated[str, Header()]
):
    """Удалить событие"""
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    
    result = await events_collection.delete_one({
        "event_id": event_id,
        "user_id": x_user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found or access denied")
    
    return

@app.get("/events/stats/burnout")
async def get_burnout_stats(
    x_user_id: Annotated[str, Header()],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Получить статистику по антивыгоранию
    Возвращает количество событий с меткой burnout_prevention и общее время отдыха
    """
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    
    query = {"user_id": x_user_id, "burnout_prevention": True}
    
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        query["start_date"] = date_filter
    
    events = await events_collection.find(query).to_list(1000)
    
    total_minutes = 0
    for event in events:
        duration = (event["end_date"] - event["start_date"]).total_seconds() / 60
        total_minutes += duration
    
    return {
        "total_burnout_events": len(events),
        "total_minutes": int(total_minutes),
        "total_hours": round(total_minutes / 60, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)

