import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import UploadFile
from io import BytesIO

from services import ImageAnalysisService


@pytest.fixture
def mock_openai_client():
    """Мок для OpenAI клиента"""
    with patch('services.OpenAI') as mock:
        client_instance = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message = Mock()
        mock_completion.choices[0].message.content = "Описание изображения"
        
        client_instance.chat.completions.create = Mock(return_value=mock_completion)
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def image_service(mock_openai_client):
    """Создает экземпляр ImageAnalysisService с моками"""
    with patch('services.settings') as mock_settings:
        mock_settings.openrouter_api_key = "test_key"
        mock_settings.default_model = "test-model"
        mock_settings.prompt = "Опиши изображение"
        mock_settings.max_tokens = 2048
        service = ImageAnalysisService()
        service.client = mock_openai_client
        return service


class TestImageAnalysisService:
    """Тесты для ImageAnalysisService"""
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_upload_success(self, image_service, mock_openai_client):
        """Тест успешного анализа изображения"""
        file_content = b"fake image content"
        file = UploadFile(
            filename="test.jpg",
            file=BytesIO(file_content)
        )
        file.content_type = "image/jpeg"
        
        result = await image_service.analyze_image_from_upload(file)
        
        assert result == "Описание изображения"
        mock_openai_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_upload_empty_response(self, image_service, mock_openai_client):
        """Тест обработки пустого ответа от API"""
        mock_completion = Mock()
        mock_completion.choices = []
        mock_openai_client.chat.completions.create.return_value = mock_completion
        
        file_content = b"fake image content"
        file = UploadFile(
            filename="test.jpg",
            file=BytesIO(file_content)
        )
        file.content_type = "image/jpeg"
        
        with pytest.raises(Exception):
            await image_service.analyze_image_from_upload(file)
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_upload_api_error(self, image_service, mock_openai_client):
        """Тест обработки ошибки API"""
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        file_content = b"fake image content"
        file = UploadFile(
            filename="test.jpg",
            file=BytesIO(file_content)
        )
        file.content_type = "image/jpeg"
        
        with pytest.raises(Exception):
            await image_service.analyze_image_from_upload(file)
    
    @pytest.mark.asyncio
    async def test_analyze_image_base64_encoding(self, image_service, mock_openai_client):
        """Тест правильного кодирования изображения в base64"""
        file_content = b"fake image content"
        file = UploadFile(
            filename="test.jpg",
            file=BytesIO(file_content)
        )
        file.content_type = "image/jpeg"
        
        await image_service.analyze_image_from_upload(file)

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args is not None
        messages = call_args[1]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "image_url" in messages[0]["content"][1]
        assert "data:image/jpeg;base64" in messages[0]["content"][1]["image_url"]["url"]

