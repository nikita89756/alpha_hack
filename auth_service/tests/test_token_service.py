import pytest
from unittest.mock import patch
from app.services.token_service import TokenService
from app.core.security import decode_token


@pytest.fixture
def token_service():
    """Создает экземпляр TokenService"""
    return TokenService()


class TestTokenService:
    """Тесты для TokenService"""
    
    def test_create_tokens(self, token_service):
        """Тест создания токенов"""
        user_id = "test_user_id"
        username = "testuser"
        
        tokens = token_service.create_tokens(user_id, username)
        
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        
        # Проверяем содержимое access токена
        access_payload = decode_token(tokens.access_token)
        assert access_payload["sub"] == user_id
        assert access_payload["username"] == username
        assert access_payload["type"] == "access"
        
        # Проверяем содержимое refresh токена
        refresh_payload = decode_token(tokens.refresh_token)
        assert refresh_payload["sub"] == user_id
        assert refresh_payload["type"] == "refresh"

