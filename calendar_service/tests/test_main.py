import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import uuid

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_events_collection():
    """Мок для MongoDB коллекции events"""
    collection = Mock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.find = Mock()
    collection.update_one = AsyncMock()
    collection.delete_one = AsyncMock()
    return collection


@pytest.fixture
def sample_event():
    """Создает тестовое событие"""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "event_id": str(uuid.uuid4()),
        "user_id": "test_user_id",
        "title": "Test Event",
        "description": "Test Description",
        "start_date": datetime.utcnow(),
        "end_date": datetime.utcnow() + timedelta(hours=1),
        "category": "work",
        "color": "#3b82f6",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


class TestHealthCheck:
    """Тесты для health check"""
    
    def test_health_check(self, client):
        """Тест health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "calendar_service"


class TestCreateEvent:
    """Тесты для создания события"""
    
    @pytest.mark.asyncio
    async def test_create_event_success(self, client, mock_events_collection, sample_event):
        """Тест успешного создания события"""
        with patch('main.events_collection', mock_events_collection):
            mock_events_collection.insert_one = AsyncMock()
            
            event_data = {
                "title": "Test Event",
                "description": "Test Description",
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                "category": "work"
            }
            
            response = client.post(
                "/events",
                json=event_data,
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["title"] == "Test Event"
            assert "event_id" in data
    
    def test_create_event_invalid_dates(self, client):
        """Тест создания события с неверными датами"""
        event_data = {
            "title": "Test Event",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": datetime.utcnow().isoformat()  # end_date <= start_date
        }
        
        response = client.post(
            "/events",
            json=event_data,
            headers={"X-User-Id": "test_user_id"}
        )
        
        assert response.status_code == 400
        assert "End date must be after start date" in response.json()["detail"]


class TestListEvents:
    """Тесты для получения списка событий"""
    
    @pytest.mark.asyncio
    async def test_list_events_success(self, client, mock_events_collection, sample_event):
        """Тест успешного получения списка событий"""
        with patch('main.events_collection', mock_events_collection):
            mock_cursor = Mock()
            mock_cursor.sort = Mock(return_value=mock_cursor)
            mock_cursor.to_list = AsyncMock(return_value=[sample_event])
            mock_events_collection.find = Mock(return_value=mock_cursor)
            
            response = client.get(
                "/events",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_list_events_with_filters(self, client, mock_events_collection, sample_event):
        """Тест получения событий с фильтрами"""
        with patch('main.events_collection', mock_events_collection):
            mock_cursor = Mock()
            mock_cursor.sort = Mock(return_value=mock_cursor)
            mock_cursor.to_list = AsyncMock(return_value=[sample_event])
            mock_events_collection.find = Mock(return_value=mock_cursor)
            
            response = client.get(
                "/events",
                params={
                    "category": "work",
                    "burnout_prevention": True
                },
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 200


class TestGetEvent:
    """Тесты для получения события"""
    
    @pytest.mark.asyncio
    async def test_get_event_success(self, client, mock_events_collection, sample_event):
        """Тест успешного получения события"""
        with patch('main.events_collection', mock_events_collection):
            mock_events_collection.find_one = AsyncMock(return_value=sample_event)
            
            event_id = sample_event["event_id"]
            response = client.get(
                f"/events/{event_id}",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Test Event"
    
    @pytest.mark.asyncio
    async def test_get_event_not_found(self, client, mock_events_collection):
        """Тест получения несуществующего события"""
        with patch('main.events_collection', mock_events_collection):
            mock_events_collection.find_one = AsyncMock(return_value=None)
            
            event_id = str(uuid.uuid4())
            response = client.get(
                f"/events/{event_id}",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 404


class TestUpdateEvent:
    """Тесты для обновления события"""
    
    @pytest.mark.asyncio
    async def test_update_event_success(self, client, mock_events_collection, sample_event):
        """Тест успешного обновления события"""
        with patch('main.events_collection', mock_events_collection):
            updated_event = sample_event.copy()
            updated_event["title"] = "Updated Event"
            
            mock_events_collection.find_one = AsyncMock(return_value=sample_event)
            mock_events_collection.update_one = AsyncMock()
            mock_events_collection.find_one = AsyncMock(return_value=updated_event)
            
            event_id = sample_event["event_id"]
            response = client.put(
                f"/events/{event_id}",
                json={"title": "Updated Event"},
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Updated Event"


class TestDeleteEvent:
    """Тесты для удаления события"""
    
    @pytest.mark.asyncio
    async def test_delete_event_success(self, client, mock_events_collection):
        """Тест успешного удаления события"""
        with patch('main.events_collection', mock_events_collection):
            mock_events_collection.delete_one = AsyncMock(
                return_value=Mock(deleted_count=1)
            )
            
            event_id = str(uuid.uuid4())
            response = client.delete(
                f"/events/{event_id}",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_delete_event_not_found(self, client, mock_events_collection):
        """Тест удаления несуществующего события"""
        with patch('main.events_collection', mock_events_collection):
            mock_events_collection.delete_one = AsyncMock(
                return_value=Mock(deleted_count=0)
            )
            
            event_id = str(uuid.uuid4())
            response = client.delete(
                f"/events/{event_id}",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 404


class TestBurnoutStats:
    """Тесты для статистики антивыгорания"""
    
    @pytest.mark.asyncio
    async def test_get_burnout_stats(self, client, mock_events_collection, sample_event):
        """Тест получения статистики антивыгорания"""
        with patch('main.events_collection', mock_events_collection):
            sample_event["burnout_prevention"] = True
            mock_cursor = Mock()
            mock_cursor.to_list = AsyncMock(return_value=[sample_event])
            mock_events_collection.find = Mock(return_value=mock_cursor)
            
            response = client.get(
                "/events/stats/burnout",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "total_burnout_events" in data
            assert "total_minutes" in data
            assert "total_hours" in data

