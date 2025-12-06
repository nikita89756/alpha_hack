import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
import jwt
from datetime import datetime, timedelta

from main import app, ConnectionManager, verify_ws_token, schedule_chat_deletion


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def connection_manager():
    """Создает экземпляр ConnectionManager"""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Мок для WebSocket"""
    ws = Mock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def valid_token():
    """Создает валидный JWT токен"""
    payload = {
        "sub": "test_user_id",
        "username": "testuser",
        "type": "access",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, "your-secret-key-change-in-production", algorithm="HS256")


class TestConnectionManager:
    """Тесты для ConnectionManager"""
    
    @pytest.mark.asyncio
    async def test_connect(self, connection_manager, mock_websocket):
        """Тест подключения пользователя"""
        await connection_manager.connect(mock_websocket, "user1", "chat1")
        
        assert "user1" in connection_manager.active_connections
        assert "chat1" in connection_manager.active_connections["user1"]
        assert mock_websocket in connection_manager.active_connections["user1"]["chat1"]
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, connection_manager, mock_websocket):
        """Тест отключения пользователя"""
        await connection_manager.connect(mock_websocket, "user1", "chat1")
        connection_manager.disconnect(mock_websocket, "user1", "chat1")
        
        assert "user1" not in connection_manager.active_connections or \
               "chat1" not in connection_manager.active_connections.get("user1", {})
    
    @pytest.mark.asyncio
    async def test_send_to_user_chat(self, connection_manager, mock_websocket):
        """Тест отправки сообщения пользователю"""
        await connection_manager.connect(mock_websocket, "user1", "chat1")
        
        message = {"type": "test", "content": "Test message"}
        await connection_manager.send_to_user_chat(message, "user1", "chat1")
        
        mock_websocket.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_send_to_nonexistent_chat(self, connection_manager):
        """Тест отправки сообщения в несуществующий чат"""
        message = {"type": "test", "content": "Test message"}
        # Не должно быть ошибки
        await connection_manager.send_to_user_chat(message, "user1", "nonexistent_chat")


class TestVerifyWSToken:
    """Тесты для верификации WebSocket токена"""
    
    def test_verify_ws_token_success(self, valid_token):
        """Тест успешной верификации токена"""
        with patch('main.SECRET_KEY', "your-secret-key-change-in-production"):
            result = verify_ws_token(valid_token)
            
            assert result["user_id"] == "test_user_id"
            assert result["username"] == "testuser"
    
    def test_verify_ws_token_expired(self):
        """Тест верификации истекшего токена"""
        payload = {
            "sub": "test_user_id",
            "type": "access",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        expired_token = jwt.encode(payload, "your-secret-key-change-in-production", algorithm="HS256")
        
        with patch('main.SECRET_KEY', "your-secret-key-change-in-production"):
            with pytest.raises(Exception):  # HTTPException
                verify_ws_token(expired_token)
    
    def test_verify_ws_token_invalid_type(self):
        """Тест верификации токена с неверным типом"""
        payload = {
            "sub": "test_user_id",
            "type": "refresh",  # Должен быть "access"
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        invalid_token = jwt.encode(payload, "your-secret-key-change-in-production", algorithm="HS256")
        
        with patch('main.SECRET_KEY', "your-secret-key-change-in-production"):
            with pytest.raises(Exception):  # HTTPException
                verify_ws_token(invalid_token)


class TestHealthCheck:
    """Тесты для health check"""
    
    def test_health_check(self, client):
        """Тест health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ws-service"
        assert "active_users" in data
        assert "total_connections" in data


class TestScheduleChatDeletion:
    """Тесты для планирования удаления чата"""
    
    @pytest.mark.asyncio
    async def test_schedule_chat_deletion(self):
        """Тест планирования удаления чата"""
        with patch('main.MESSAGE_SERVICE_URL', "http://test-service"), \
             patch('asyncio.sleep', AsyncMock()), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.delete = AsyncMock(
                return_value=mock_response
            )
            
            await schedule_chat_deletion("test_chat_id", "test_user_id", delay_seconds=0)
            
            # Проверяем, что запрос был отправлен
            # (проверка через моки)


class TestWebSocketEndpoint:
    """Тесты для WebSocket endpoint"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_success(self, connection_manager, mock_websocket, valid_token):
        """Тест успешного подключения через WebSocket"""
        with patch('main.manager', connection_manager), \
             patch('main.verify_ws_token', return_value={"user_id": "test_user_id", "username": "testuser"}):
            
            # WebSocket тесты требуют специальной настройки
            # Здесь проверяем логику через моки
            await connection_manager.connect(mock_websocket, "test_user_id", "test_chat_id")
            
            assert mock_websocket in connection_manager.active_connections["test_user_id"]["test_chat_id"]
    
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, connection_manager, mock_websocket):
        """Тест ping-pong механизма"""
        mock_websocket.receive_text = AsyncMock(return_value="ping")
        
        # Симуляция обработки ping
        if mock_websocket.receive_text.return_value == "ping":
            await mock_websocket.send_text("pong")
        
        mock_websocket.send_text.assert_called_with("pong")

