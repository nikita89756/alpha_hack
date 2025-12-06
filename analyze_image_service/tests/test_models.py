import pytest
from models import ImageAnalysisRequest, ImageAnalysisResponse, HealthResponse


class TestImageAnalysisRequest:
    """Тесты для ImageAnalysisRequest"""
    
    def test_default_values(self):
        """Тест значений по умолчанию"""
        request = ImageAnalysisRequest()
        assert request.model == "google/gemini-flash-1.5-8b"
        assert request.prompt == "Опиши всё, что видишь на этом изображении."
        assert request.max_tokens == 2048
    
    def test_custom_values(self):
        """Тест с пользовательскими значениями"""
        request = ImageAnalysisRequest(
            model="custom-model",
            prompt="Custom prompt",
            max_tokens=1024
        )
        assert request.model == "custom-model"
        assert request.prompt == "Custom prompt"
        assert request.max_tokens == 1024


class TestImageAnalysisResponse:
    """Тесты для ImageAnalysisResponse"""
    
    def test_success_response(self):
        """Тест успешного ответа"""
        response = ImageAnalysisResponse(
            success=True,
            description="Описание",
            error="",
            image_url="http://example.com/image.jpg"
        )
        assert response.success is True
        assert response.description == "Описание"
        assert response.error == ""
        assert response.image_url == "http://example.com/image.jpg"
    
    def test_error_response(self):
        """Тест ответа с ошибкой"""
        response = ImageAnalysisResponse(
            success=False,
            description="",
            error="Error message",
            image_url=""
        )
        assert response.success is False
        assert response.error == "Error message"
    
    def test_optional_fields(self):
        """Тест опциональных полей"""
        response = ImageAnalysisResponse(
            success=True,
            description="Описание"
        )
        assert response.error is None
        assert response.image_url is None


class TestHealthResponse:
    """Тесты для HealthResponse"""
    
    def test_health_response(self):
        """Тест health response"""
        response = HealthResponse(
            status="ok",
            version="1.0.0"
        )
        assert response.status == "ok"
        assert response.version == "1.0.0"

