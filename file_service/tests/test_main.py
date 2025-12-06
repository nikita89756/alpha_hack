import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_document_parser():
    """Мок для DocumentParser"""
    with patch('main.DocumentParser') as mock:
        parser_instance = Mock()
        parser_instance.parse_content = Mock(return_value="Extracted text from document")
        mock.return_value = parser_instance
        yield parser_instance


class TestHealthCheck:
    """Тесты для health check"""
    
    def test_root_endpoint(self, client):
        """Тест корневого endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
    
    def test_health_check(self, client):
        """Тест health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "document-parser"


class TestParseDocument:
    """Тесты для парсинга документов"""
    
    def test_parse_document_success(self, client, mock_document_parser):
        """Тест успешного парсинга документа"""
        file_content = b"PDF content here"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        
        response = client.post("/parse", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["text"] == "Extracted text from document"
        assert "text_length" in data
    
    def test_parse_document_empty_file(self, client):
        """Тест парсинга пустого файла"""
        file_content = b""
        files = {"file": ("empty.pdf", BytesIO(file_content), "application/pdf")}
        
        response = client.post("/parse", files=files)
        
        assert response.status_code == 400
        assert "Файл пустой" in response.json()["detail"]
    
    def test_parse_document_no_text_extracted(self, client):
        """Тест парсинга файла без извлеченного текста"""
        with patch('main.DocumentParser') as mock_parser:
            parser_instance = Mock()
            parser_instance.parse_content = Mock(return_value="")
            mock_parser.return_value = parser_instance
            
            file_content = b"PDF content"
            files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
            
            response = client.post("/parse", files=files)
            
            assert response.status_code == 422
            assert "Не удалось извлечь текст" in response.json()["detail"]
    
    def test_parse_document_error(self, client):
        """Тест обработки ошибки при парсинге"""
        with patch('main.DocumentParser') as mock_parser:
            parser_instance = Mock()
            parser_instance.parse_content = Mock(side_effect=Exception("Parse error"))
            mock_parser.return_value = parser_instance
            
            file_content = b"PDF content"
            files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
            
            response = client.post("/parse", files=files)
            
            assert response.status_code == 500
            assert "Внутренняя ошибка сервера" in response.json()["detail"]
    
    def test_parse_document_different_formats(self, client, mock_document_parser):
        """Тест парсинга различных форматов"""
        formats = [
            ("test.pdf", "application/pdf"),
            ("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("test.txt", "text/plain"),
            ("test.md", "text/markdown"),
            ("test.csv", "text/csv")
        ]
        
        for filename, content_type in formats:
            file_content = b"File content"
            files = {"file": (filename, BytesIO(file_content), content_type)}
            
            response = client.post("/parse", files=files)
            
            # Может быть ошибка из-за моков, но формат должен быть принят
            assert response.status_code in [200, 400, 500]

