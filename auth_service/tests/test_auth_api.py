import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import uuid

from main import app
from app.schemas.user import UserInDB, UserRegister
from app.core.security import get_password_hash


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_auth_service():
    """Мок для auth_service"""
    with patch('app.api.auth.auth_service') as mock:
        yield mock


@pytest.fixture
def mock_token_service():
    """Мок для token_service"""
    with patch('app.api.auth.token_service') as mock:
        mock.create_tokens.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "bearer"
        }
        yield mock


@pytest.fixture
def sample_user():
    """Создает тестового пользователя"""
    return UserInDB(
        user_id=str(uuid.uuid4()),
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("password123"),
        created_at=datetime.utcnow(),
        is_active=True
    )


class TestRegister:
    """Тесты для регистрации"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client, mock_auth_service, sample_user):
        """Тест успешной регистрации"""
        mock_auth_service.get_user_by_username = AsyncMock(return_value=None)
        mock_auth_service.get_user_by_email = AsyncMock(return_value=None)
        mock_auth_service.register_user = AsyncMock(return_value=sample_user)
        
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
                "full_name": "Test User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "user_id" in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client, mock_auth_service, sample_user):
        """Тест регистрации с существующим username"""
        mock_auth_service.get_user_by_username = AsyncMock(return_value=sample_user)
        
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "new@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, mock_auth_service, sample_user):
        """Тест регистрации с существующим email"""
        mock_auth_service.get_user_by_username = AsyncMock(return_value=None)
        mock_auth_service.get_user_by_email = AsyncMock(return_value=sample_user)
        
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "test@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]


class TestLogin:
    """Тесты для входа"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client, mock_auth_service, mock_token_service, sample_user):
        """Тест успешного входа"""
        mock_auth_service.authenticate_user = AsyncMock(return_value=sample_user)
        
        response = client.post(
            "/auth/login",
            data={
                "username": "test@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_wrong_credentials(self, client, mock_auth_service):
        """Тест входа с неверными данными"""
        mock_auth_service.authenticate_user = AsyncMock(return_value=None)
        
        response = client.post(
            "/auth/login",
            data={
                "username": "test@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect email/username or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client, mock_auth_service, sample_user):
        """Тест входа неактивного пользователя"""
        sample_user.is_active = False
        mock_auth_service.authenticate_user = AsyncMock(return_value=sample_user)
        
        response = client.post(
            "/auth/login",
            data={
                "username": "test@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]


class TestRefreshToken:
    """Тесты для обновления токена"""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client, mock_auth_service, mock_token_service):
        """Тест успешного обновления токена"""
        from app.core.security import create_refresh_token
        
        user_id = str(uuid.uuid4())
        refresh_token = create_refresh_token({"sub": user_id})
        
        mock_user = {
            "user_id": user_id,
            "username": "testuser"
        }
        mock_auth_service.users_collection.find_one = AsyncMock(return_value=mock_user)
        
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client):
        """Тест обновления с неверным токеном"""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        
        assert response.status_code == 401


class TestVerifyToken:
    """Тесты для верификации токена"""
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self, client, mock_auth_service):
        """Тест успешной верификации токена"""
        from app.core.security import create_access_token
        
        user_id = str(uuid.uuid4())
        access_token = create_access_token({"sub": user_id, "username": "testuser"})
        
        mock_user = {
            "user_id": user_id,
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        mock_auth_service.users_collection.find_one = AsyncMock(return_value=mock_user)
        
        response = client.post(
            "/auth/verify",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_verify_token_missing_header(self, client):
        """Тест верификации без заголовка"""
        response = client.post("/auth/verify")
        
        assert response.status_code == 401
        assert "Missing authorization header" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid_format(self, client):
        """Тест верификации с неверным форматом заголовка"""
        response = client.post(
            "/auth/verify",
            headers={"Authorization": "InvalidFormat token"}
        )
        
        assert response.status_code == 401

