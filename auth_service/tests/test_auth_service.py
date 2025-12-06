import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import uuid

from app.services.auth_service import AuthService
from app.schemas.user import UserRegister, UserInDB
from app.core.security import get_password_hash, verify_password


@pytest.fixture
def mock_mongo_collection():
    """Мок для MongoDB коллекции"""
    collection = Mock()
    collection.find_one = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.create_index = AsyncMock()
    return collection


@pytest.fixture
def mock_mongo_db(mock_mongo_collection):
    """Мок для MongoDB базы данных"""
    db = Mock()
    db.__getitem__ = Mock(return_value=mock_mongo_collection)
    return db


@pytest.fixture
def mock_mongo_client(mock_mongo_db):
    """Мок для MongoDB клиента"""
    client = Mock()
    client.__getitem__ = Mock(return_value=mock_mongo_db)
    client.close = Mock()
    return client


@pytest.fixture
async def auth_service(mock_mongo_client, mock_mongo_collection):
    """Создает экземпляр AuthService с моками"""
    service = AuthService()
    service.client = mock_mongo_client
    service.db = mock_mongo_client["test_db"]
    service.users_collection = mock_mongo_collection
    return service


class TestAuthService:
    """Тесты для AuthService"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, auth_service, mock_mongo_collection):
        """Тест инициализации сервиса"""
        await auth_service.initialize()
        assert mock_mongo_collection.create_index.call_count == 3
    
    @pytest.mark.asyncio
    async def test_authenticate_user_by_email_success(self, auth_service, mock_mongo_collection):
        """Тест успешной аутентификации по email"""
        password = "testpass123"
        hashed_password = get_password_hash(password)
        
        user_dict = {
            "user_id": str(uuid.uuid4()),
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": hashed_password,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        mock_mongo_collection.find_one = AsyncMock(return_value=user_dict)
        
        user = await auth_service.authenticate_user("test@example.com", password)
        
        assert user is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_by_username_success(self, auth_service, mock_mongo_collection):
        """Тест успешной аутентификации по username"""
        password = "testpass123"
        hashed_password = get_password_hash(password)
        
        user_dict = {
            "user_id": str(uuid.uuid4()),
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": hashed_password,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        # Сначала не найден по email, потом найден по username
        async def find_one_side_effect(query):
            if "email" in query:
                return None
            return user_dict
        
        mock_mongo_collection.find_one = AsyncMock(side_effect=find_one_side_effect)
        
        user = await auth_service.authenticate_user("testuser", password)
        
        assert user is not None
        assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, auth_service, mock_mongo_collection):
        """Тест аутентификации с неверным паролем"""
        user_dict = {
            "user_id": str(uuid.uuid4()),
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": get_password_hash("correctpass"),
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        mock_mongo_collection.find_one = AsyncMock(return_value=user_dict)
        
        user = await auth_service.authenticate_user("test@example.com", "wrongpass")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service, mock_mongo_collection):
        """Тест аутентификации несуществующего пользователя"""
        mock_mongo_collection.find_one = AsyncMock(return_value=None)
        
        user = await auth_service.authenticate_user("nonexistent@example.com", "password")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_register_user(self, auth_service, mock_mongo_collection):
        """Тест регистрации пользователя"""
        user_data = UserRegister(
            username="newuser",
            email="newuser@example.com",
            password="password123",
            full_name="New User"
        )
        
        inserted_id = Mock()
        mock_mongo_collection.insert_one = AsyncMock(return_value=Mock(inserted_id=inserted_id))
        
        user = await auth_service.register_user(user_data)
        
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.is_active is True
        assert verify_password("password123", user.hashed_password)
        mock_mongo_collection.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self, auth_service, mock_mongo_collection):
        """Тест получения пользователя по username"""
        user_dict = {
            "_id": "507f1f77bcf86cd799439011",
            "user_id": str(uuid.uuid4()),
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed",
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        mock_mongo_collection.find_one = AsyncMock(return_value=user_dict)
        
        user = await auth_service.get_user_by_username("testuser")
        
        assert user is not None
        assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, auth_service, mock_mongo_collection):
        """Тест получения несуществующего пользователя"""
        mock_mongo_collection.find_one = AsyncMock(return_value=None)
        
        user = await auth_service.get_user_by_username("nonexistent")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, auth_service, mock_mongo_collection):
        """Тест получения пользователя по email"""
        user_dict = {
            "_id": "507f1f77bcf86cd799439011",
            "user_id": str(uuid.uuid4()),
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed",
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        mock_mongo_collection.find_one = AsyncMock(return_value=user_dict)
        
        user = await auth_service.get_user_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_cleanup(self, auth_service):
        """Тест очистки ресурсов"""
        await auth_service.cleanup()
        auth_service.client.close.assert_called_once()

