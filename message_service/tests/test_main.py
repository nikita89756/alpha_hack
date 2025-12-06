import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid
import json

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_mongo_collections():
    """Мок для MongoDB коллекций"""
    collections = {
        "messages": Mock(),
        "chats": Mock(),
        "folders": Mock()
    }
    
    for collection in collections.values():
        collection.insert_one = AsyncMock()
        collection.find_one = AsyncMock()
        collection.find = Mock()
        collection.update_one = AsyncMock()
        collection.update_many = AsyncMock()
        collection.delete_one = AsyncMock()
        collection.count_documents = AsyncMock()
        collection.create_index = AsyncMock()
    
    return collections


@pytest.fixture
def mock_redis():
    """Мок для Redis"""
    redis = Mock()
    redis.ping = AsyncMock()
    redis.pipeline = Mock(return_value=Mock())
    redis.lrange = AsyncMock(return_value=[])
    redis.close = AsyncMock()
    return redis


@pytest.fixture
def sample_chat():
    """Создает тестовый чат"""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "chat_id": str(uuid.uuid4()),
        "user_id": "test_user_id",
        "title": "Test Chat",
        "folder_id": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "message_count": 0,
        "is_active": True
    }


@pytest.fixture
def sample_message():
    """Создает тестовое сообщение"""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "id": str(uuid.uuid4()),
        "user_id": "test_user_id",
        "chat_id": "test_chat_id",
        "message": "Test message",
        "message_type": "user",
        "timestamp": datetime.utcnow(),
        "status": "sent"
    }


class TestHealthCheck:
    """Тесты для health check"""
    
    def test_health_check(self, client):
        """Тест health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "message-service"


class TestCreateChat:
    """Тесты для создания чата"""
    
    @pytest.mark.asyncio
    async def test_create_chat_success(self, client, mock_mongo_collections, sample_chat):
        """Тест успешного создания чата"""
        with patch('main.chats_collection', mock_mongo_collections["chats"]), \
             patch('main.messages_collection', mock_mongo_collections["messages"]), \
             patch('main.folders_collection', mock_mongo_collections["folders"]), \
             patch('main.redis', None):
            
            mock_mongo_collections["chats"].insert_one = AsyncMock()
            mock_mongo_collections["chats"].count_documents = AsyncMock(return_value=0)
            mock_mongo_collections["messages"].insert_one = AsyncMock()
            mock_mongo_collections["chats"].update_one = AsyncMock()
            
            response = client.post(
                "/chats/create",
                params={"user_id": "test_user_id"},
                json={"title": "Test Chat"}
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "chat_id" in data
            assert data["user_id"] == "test_user_id"


class TestListChats:
    """Тесты для получения списка чатов"""
    
    @pytest.mark.asyncio
    async def test_list_chats_success(self, client, mock_mongo_collections, sample_chat):
        """Тест успешного получения списка чатов"""
        with patch('main.chats_collection', mock_mongo_collections["chats"]):
            mock_cursor = Mock()
            mock_cursor.sort = Mock(return_value=mock_cursor)
            mock_cursor.skip = Mock(return_value=mock_cursor)
            mock_cursor.limit = Mock(return_value=mock_cursor)
            mock_cursor.to_list = AsyncMock(return_value=[sample_chat])
            mock_mongo_collections["chats"].find = Mock(return_value=mock_cursor)
            
            response = client.get(
                "/chats/list",
                params={"user_id": "test_user_id"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestSendMessage:
    """Тесты для отправки сообщения"""
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, client, mock_mongo_collections, sample_chat):
        """Тест успешной отправки сообщения"""
        with patch('main.chats_collection', mock_mongo_collections["chats"]), \
             patch('main.messages_collection', mock_mongo_collections["messages"]), \
             patch('main.redis', None), \
             patch('main.send_to_kafka', AsyncMock()):
            
            mock_mongo_collections["chats"].find_one = AsyncMock(return_value=sample_chat)
            mock_mongo_collections["messages"].insert_one = AsyncMock()
            mock_mongo_collections["chats"].update_one = AsyncMock()
            
            response = client.post(
                "/messages/send",
                json={
                    "user_id": "test_user_id",
                    "chat_id": sample_chat["chat_id"],
                    "chat_type": "support",
                    "message": "Test message"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "message_id" in data
            assert data["status"] == "processing"
    
    @pytest.mark.asyncio
    async def test_send_message_chat_not_found(self, client, mock_mongo_collections):
        """Тест отправки сообщения в несуществующий чат"""
        with patch('main.chats_collection', mock_mongo_collections["chats"]):
            mock_mongo_collections["chats"].find_one = AsyncMock(return_value=None)
            
            response = client.post(
                "/messages/send",
                json={
                    "user_id": "test_user_id",
                    "chat_id": "nonexistent_chat_id",
                    "chat_type": "support",
                    "message": "Test message"
                }
            )
            
            assert response.status_code == 404
            assert "Chat not found" in response.json()["detail"]


class TestGetMessageHistory:
    """Тесты для получения истории сообщений"""
    
    @pytest.mark.asyncio
    async def test_get_message_history_from_redis(self, client, mock_redis):
        """Тест получения истории из Redis"""
        with patch('main.redis', mock_redis), \
             patch('main.messages_collection', Mock()):
            
            mock_message = {
                "id": "msg_id",
                "message": "Test message",
                "timestamp": datetime.utcnow().isoformat()
            }
            mock_redis.lrange = AsyncMock(return_value=[json.dumps(mock_message)])
            
            response = client.get(
                "/messages/history/test_chat_id",
                params={"limit": 50}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "messages" in data
            assert "chat_id" in data
    
    @pytest.mark.asyncio
    async def test_get_message_history_from_mongo(self, client, mock_mongo_collections, sample_message):
        """Тест получения истории из MongoDB"""
        with patch('main.redis', None), \
             patch('main.messages_collection', mock_mongo_collections["messages"]):
            
            mock_cursor = Mock()
            mock_cursor.sort = Mock(return_value=mock_cursor)
            mock_cursor.limit = Mock(return_value=mock_cursor)
            mock_cursor.to_list = AsyncMock(return_value=[sample_message])
            mock_mongo_collections["messages"].find = Mock(return_value=mock_cursor)
            
            response = client.get(
                "/messages/history/test_chat_id",
                params={"limit": 50}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "messages" in data


class TestCreateFolder:
    """Тесты для создания папки"""
    
    @pytest.mark.asyncio
    async def test_create_folder_success(self, client, mock_mongo_collections):
        """Тест успешного создания папки"""
        with patch('main.folders_collection', mock_mongo_collections["folders"]):
            mock_mongo_collections["folders"].find_one = AsyncMock(return_value=None)
            mock_mongo_collections["folders"].insert_one = AsyncMock()
            
            response = client.post(
                "/folders/create",
                params={"user_id": "test_user_id"},
                json={
                    "name": "Test Folder",
                    "description": "Test Description"
                }
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "folder_id" in data
            assert data["name"] == "Test Folder"
    
    @pytest.mark.asyncio
    async def test_create_folder_duplicate_name(self, client, mock_mongo_collections):
        """Тест создания папки с дублирующимся именем"""
        with patch('main.folders_collection', mock_mongo_collections["folders"]):
            existing_folder = {
                "folder_id": str(uuid.uuid4()),
                "name": "Test Folder",
                "user_id": "test_user_id"
            }
            mock_mongo_collections["folders"].find_one = AsyncMock(return_value=existing_folder)
            
            response = client.post(
                "/folders/create",
                params={"user_id": "test_user_id"},
                json={
                    "name": "Test Folder",
                    "description": "Test Description"
                }
            )
            
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]

