import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import uuid

from app.services.user_service import UserService
from app.schemas.user import UserInDB


@pytest.fixture
def mock_auth_service():
    """Мок для auth_service"""
    with patch('app.services.user_service.auth_service') as mock:
        mock.users_collection = Mock()
        yield mock


@pytest.fixture
def user_service():
    """Создает экземпляр UserService"""
    return UserService()


class TestUserService:
    """Тесты для UserService"""
    
    @pytest.mark.asyncio
    async def test_get_by_user_id_success(self, user_service, mock_auth_service):
        """Тест успешного получения пользователя по user_id"""
        user_id = str(uuid.uuid4())
        user_dict = {
            "_id": "507f1f77bcf86cd799439011",
            "user_id": user_id,
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "hashed",
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        mock_auth_service.users_collection.find_one = AsyncMock(return_value=user_dict)
        
        user = await user_service.get_by_user_id(user_id)
        
        assert user is not None
        assert user.user_id == user_id
        assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_by_user_id_not_found(self, user_service, mock_auth_service):
        """Тест получения несуществующего пользователя"""
        mock_auth_service.users_collection.find_one = AsyncMock(return_value=None)
        
        user = await user_service.get_by_user_id("nonexistent_id")
        
        assert user is None

