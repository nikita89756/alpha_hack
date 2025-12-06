"""Calendar Service Client"""
import httpx
from typing import List, Optional
from fastapi import HTTPException, status
import logging

from app.schemas.calendar import EventCreate, EventUpdate, EventResponse

logger = logging.getLogger(__name__)


class CalendarServiceClient:
    """Клиент для взаимодействия с Calendar Service"""

    def __init__(self, config):
        self.base_url = config.CALENDAR_SERVICE_URL.rstrip("/")
        self.timeout = httpx.Timeout(30.0)

    async def create_event(self, user_id: str, event: EventCreate) -> EventResponse:
        """Создать новое событие"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/events",
                    json=event.model_dump(mode='json'),
                    headers={"X-User-Id": user_id}
                )
                response.raise_for_status()
                return EventResponse(**response.json())
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to create event: {e}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=e.response.json().get("detail", "Failed to create event")
                )
            except Exception as e:
                logger.error(f"Unexpected error creating event: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create event"
                )

    async def list_events(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        burnout_prevention: Optional[bool] = None
    ) -> List[EventResponse]:
        """Получить список событий с фильтрацией"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                params = {}
                if start_date:
                    params["start_date"] = start_date
                if end_date:
                    params["end_date"] = end_date
                if category:
                    params["category"] = category
                if burnout_prevention is not None:
                    params["burnout_prevention"] = str(burnout_prevention).lower()

                response = await client.get(
                    f"{self.base_url}/events",
                    params=params,
                    headers={"X-User-Id": user_id}
                )
                response.raise_for_status()
                return [EventResponse(**event) for event in response.json()]
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to list events: {e}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=e.response.json().get("detail", "Failed to list events")
                )
            except Exception as e:
                logger.error(f"Unexpected error listing events: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to list events"
                )

    async def get_event(self, user_id: str, event_id: str) -> EventResponse:
        """Получить конкретное событие"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/events/{event_id}",
                    headers={"X-User-Id": user_id}
                )
                response.raise_for_status()
                return EventResponse(**response.json())
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Event not found"
                    )
                logger.error(f"Failed to get event: {e}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=e.response.json().get("detail", "Failed to get event")
                )
            except Exception as e:
                logger.error(f"Unexpected error getting event: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get event"
                )

    async def update_event(self, user_id: str, event_id: str, update_data: EventUpdate) -> EventResponse:
        """Обновить событие"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.put(
                    f"{self.base_url}/events/{event_id}",
                    json=update_data.model_dump(mode='json', exclude_unset=True),
                    headers={"X-User-Id": user_id}
                )
                response.raise_for_status()
                return EventResponse(**response.json())
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Event not found"
                    )
                logger.error(f"Failed to update event: {e}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=e.response.json().get("detail", "Failed to update event")
                )
            except Exception as e:
                logger.error(f"Unexpected error updating event: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update event"
                )

    async def delete_event(self, user_id: str, event_id: str) -> None:
        """Удалить событие"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/events/{event_id}",
                    headers={"X-User-Id": user_id}
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Event not found or access denied"
                    )
                logger.error(f"Failed to delete event: {e}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=e.response.json().get("detail", "Failed to delete event")
                )
            except Exception as e:
                logger.error(f"Unexpected error deleting event: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete event"
                )

    async def get_burnout_stats(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """Получить статистику по антивыгоранию"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                params = {}
                if start_date:
                    params["start_date"] = start_date
                if end_date:
                    params["end_date"] = end_date

                response = await client.get(
                    f"{self.base_url}/events/stats/burnout",
                    params=params,
                    headers={"X-User-Id": user_id}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get burnout stats: {e}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=e.response.json().get("detail", "Failed to get burnout stats")
                )
            except Exception as e:
                logger.error(f"Unexpected error getting burnout stats: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get burnout stats"
                )

