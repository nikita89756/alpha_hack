"""Calendar endpoints"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from app.core.config import get_config, Config
from app.core.dependencies import verify_token
from app.schemas.calendar import EventCreate, EventUpdate, EventResponse
from app.services.calendar_client import CalendarServiceClient

router = APIRouter(prefix="/calendar", tags=["Calendar"])


def get_calendar_client(config: Config = Depends(get_config)) -> CalendarServiceClient:
    return CalendarServiceClient(config)


@router.post(
    "/events",
    response_model=EventResponse,
    status_code=201,
    summary="Создание нового события"
)
async def create_event(
    event: EventCreate,
    user: dict = Depends(verify_token),
    calendar_client: CalendarServiceClient = Depends(get_calendar_client)
):
    """Создает новое событие в календаре пользователя"""
    return await calendar_client.create_event(user["user_id"], event)


@router.get(
    "/events",
    response_model=List[EventResponse],
    summary="Список событий"
)
async def list_events(
    start_date: Optional[str] = Query(None, description="Фильтр по дате начала (ISO format)"),
    end_date: Optional[str] = Query(None, description="Фильтр по дате окончания (ISO format)"),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    burnout_prevention: Optional[bool] = Query(None, description="Только события с антивыгоранием"),
    user: dict = Depends(verify_token),
    calendar_client: CalendarServiceClient = Depends(get_calendar_client)
):
    """Получает список всех событий пользователя с возможностью фильтрации"""
    return await calendar_client.list_events(
        user["user_id"],
        start_date=start_date,
        end_date=end_date,
        category=category,
        burnout_prevention=burnout_prevention
    )


@router.get(
    "/events/{event_id}",
    response_model=EventResponse,
    summary="Информация о событии"
)
async def get_event(
    event_id: str,
    user: dict = Depends(verify_token),
    calendar_client: CalendarServiceClient = Depends(get_calendar_client)
):
    """Получает детальную информацию о конкретном событии"""
    return await calendar_client.get_event(user["user_id"], event_id)


@router.put(
    "/events/{event_id}",
    response_model=EventResponse,
    summary="Обновление события"
)
async def update_event(
    event_id: str,
    update_data: EventUpdate,
    user: dict = Depends(verify_token),
    calendar_client: CalendarServiceClient = Depends(get_calendar_client)
):
    """Обновляет информацию о событии"""
    return await calendar_client.update_event(user["user_id"], event_id, update_data)


@router.delete(
    "/events/{event_id}",
    status_code=204,
    summary="Удаление события"
)
async def delete_event(
    event_id: str,
    user: dict = Depends(verify_token),
    calendar_client: CalendarServiceClient = Depends(get_calendar_client)
):
    """Удаляет событие из календаря"""
    await calendar_client.delete_event(user["user_id"], event_id)


@router.get(
    "/stats/burnout",
    summary="Статистика по антивыгоранию"
)
async def get_burnout_stats(
    start_date: Optional[str] = Query(None, description="Начало периода (ISO format)"),
    end_date: Optional[str] = Query(None, description="Конец периода (ISO format)"),
    user: dict = Depends(verify_token),
    calendar_client: CalendarServiceClient = Depends(get_calendar_client)
):
    """Получает статистику по событиям антивыгорания"""
    return await calendar_client.get_burnout_stats(
        user["user_id"],
        start_date=start_date,
        end_date=end_date
    )

