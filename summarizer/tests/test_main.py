import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json


@pytest.fixture
def mock_mongo_db():
    """Мок для MongoDB базы данных"""
    db = Mock()
    chats_collection = Mock()
    chats_collection.update_one = AsyncMock()
    db.chats = chats_collection
    return db


@pytest.fixture
def mock_kafka_producer():
    """Мок для Kafka producer"""
    producer = Mock()
    producer.send_and_wait = AsyncMock()
    return producer


class TestUpdateChatTitle:
    """Тесты для обновления названия чата"""
    
    @pytest.mark.asyncio
    async def test_update_chat_title_success(self, mock_mongo_db):
        """Тест успешного обновления названия по user_id"""
        import main
        main.db = mock_mongo_db
        mock_mongo_db.chats.update_one = AsyncMock(
            return_value=Mock(modified_count=1)
        )
        
        result = await main.update_chat_title("test_user_id", "Новое название")
        
        assert result is True
        mock_mongo_db.chats.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_chat_title_not_found(self, mock_mongo_db):
        """Тест обновления несуществующего чата"""
        import main
        main.db = mock_mongo_db
        mock_mongo_db.chats.update_one = AsyncMock(
            return_value=Mock(modified_count=0)
        )
        
        result = await main.update_chat_title("nonexistent_user_id", "Новое название")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_chat_title_by_id_success(self, mock_mongo_db):
        """Тест успешного обновления названия по chat_id"""
        import main
        main.db = mock_mongo_db
        mock_mongo_db.chats.update_one = AsyncMock(
            return_value=Mock(modified_count=1)
        )
        
        result = await main.update_chat_title_by_id("test_chat_id", "Новое название")
        
        assert result is True
        mock_mongo_db.chats.update_one.assert_called_once()


class TestProcessTitleRequest:
    """Тесты для обработки запроса на генерацию названия"""
    
    @pytest.mark.asyncio
    async def test_process_title_request_success(self, mock_kafka_producer):
        """Тест успешной обработки запроса"""
        import main
        
        with patch.object(main, 'update_chat_title_by_id', AsyncMock(return_value=True)), \
             patch.object(main, 'send_title_to_kafka', AsyncMock()), \
             patch.object(main, 'generate_chat_title', AsyncMock(return_value="Сгенерированное название")):
            
            message = {
                "chat_id": "test_chat_id",
                "user_id": "test_user_id",
                "first_message": "Первое сообщение пользователя"
            }
            
            await main.process_title_request(message, mock_kafka_producer)
            
            # Проверяем, что функции были вызваны
            main.update_chat_title_by_id.assert_called_once()
            main.send_title_to_kafka.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_title_request_incomplete_data(self, mock_kafka_producer):
        """Тест обработки запроса с неполными данными"""
        import main
        
        message = {
            "chat_id": "test_chat_id"
            # Отсутствуют user_id и first_message
        }
        
        # Должно обработаться без ошибок (логирование предупреждения)
        await main.process_title_request(message, mock_kafka_producer)

