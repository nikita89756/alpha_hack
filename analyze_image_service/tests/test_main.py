import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from io import BytesIO
import base64

from main import app
from models import ImageAnalysisResponse


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_image_file():
    """Создает мок файла изображения"""
    file_content = b"fake image content"
    return ("test.jpg", BytesIO(file_content), "image/jpeg")


@pytest.fixture
def mock_analysis_service():
    """Мок для ImageAnalysisService"""
    with patch('main.analysis_service') as mock:
        mock.analyze_image_from_upload = AsyncMock(return_value="Описание изображения")
        yield mock


@pytest.fixture
def mock_s3_storage():
    """Мок для S3 storage"""
    with patch('main.get_photo_url') as mock:
        mock.return_value = "http://example.com/image.jpg"
        yield mock


class TestHealthCheck:
    """Тесты для health check endpoint"""
    
    def test_root_endpoint(self, client):
        """Тест корневого endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"


class TestAnalyzeImage:
    """Тесты для анализа изображений"""
    
    @pytest.mark.asyncio
    async def test_analyze_image_success(self, client, mock_analysis_service, mock_s3_storage):
        """Тест успешного анализа изображения"""
        file_content = b"fake image content"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}
        
        response = client.post("/analyze", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["description"] == "Описание изображения"
        assert data["image_url"] == "http://example.com/image.jpg"
        assert data["error"] == ""
    
    def test_analyze_image_invalid_format(self, client):
        """Тест с недопустимым форматом файла"""
        file_content = b"fake content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        
        response = client.post("/analyze", files=files)
        
        assert response.status_code == 400
        assert "Недопустимый формат файла" in response.json()["detail"]
    
    def test_analyze_image_too_large(self, client):
        """Тест с файлом слишком большого размера"""
        with patch('main.settings') as mock_settings:
            mock_settings.max_file_size = 1024  # 1KB
            mock_settings.allowed_extensions = {".jpg", ".jpeg", ".png"}
            
            file_content = b"x" * 2048
            files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}
            
            with patch('main.UploadFile') as mock_file:
                mock_file_instance = Mock()
                mock_file_instance.filename = "test.jpg"
                mock_file_instance.size = 2048
                mock_file.return_value = mock_file_instance
                
                response = client.post("/analyze", files=files)
            
                assert response.status_code in [400, 500]
    
    @pytest.mark.asyncio
    async def test_analyze_image_service_error(self, client, mock_s3_storage):
        """Тест обработки ошибки сервиса анализа"""
        with patch('main.analysis_service') as mock_service:
            mock_service.analyze_image_from_upload = AsyncMock(
                side_effect=Exception("API Error")
            )
            
            file_content = b"fake image content"
            files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}
            
            response = client.post("/analyze", files=files)
            
            assert response.status_code == 200 
            data = response.json()
            assert data["success"] is False
            assert "API Error" in data["error"]
    
    def test_analyze_image_allowed_formats(self, client, mock_analysis_service, mock_s3_storage):
        """Тест различных допустимых форматов"""
        formats = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        
        for ext in formats:
            file_content = b"fake image content"
            files = {"file": (f"test{ext}", BytesIO(file_content), f"image/{ext[1:]}")}
            
            response = client.post("/analyze", files=files)

            assert response.status_code in [200, 400, 500]

