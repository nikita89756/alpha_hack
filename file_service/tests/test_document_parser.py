import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from pathlib import Path

from document_parser import DocumentParser


class TestDocumentParser:
    """Тесты для DocumentParser"""
    
    def test_init_with_filename(self):
        """Тест инициализации с именем файла"""
        parser = DocumentParser(source="test.pdf")
        assert parser.source == "test.pdf"
        assert parser._source_is_url is False
    
    def test_init_with_url(self):
        """Тест инициализации с URL"""
        parser = DocumentParser(source="http://example.com/document.pdf")
        assert parser._source_is_url is True
    
    def test_check_is_url(self):
        """Тест проверки URL"""
        parser = DocumentParser(source="http://example.com/file.pdf")
        assert parser._source_is_url is True
        
        parser = DocumentParser(source="file.pdf")
        assert parser._source_is_url is False
    
    def test_get_parser_for_pdf(self):
        """Тест получения парсера для PDF"""
        parser = DocumentParser(source="test.pdf")
        parser_func = parser._get_parser_for_source()
        assert parser_func == parser._parse_pdf
    
    def test_get_parser_for_docx(self):
        """Тест получения парсера для DOCX"""
        parser = DocumentParser(source="test.docx")
        parser_func = parser._get_parser_for_source()
        assert parser_func == parser._parse_docx
    
    def test_get_parser_for_txt(self):
        """Тест получения парсера для TXT"""
        parser = DocumentParser(source="test.txt")
        parser_func = parser._get_parser_for_source()
        assert parser_func == parser._parse_text
    
    @patch('document_parser.PdfReader')
    def test_parse_pdf(self, mock_pdf_reader):
        """Тест парсинга PDF"""
        mock_reader = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Page text"
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader
        
        data = b"PDF content"
        result = DocumentParser._parse_pdf(data)
        
        assert result == "Page text"
    
    @patch('document_parser.Document')
    def test_parse_docx(self, mock_document):
        """Тест парсинга DOCX"""
        from docx.oxml.text.paragraph import CT_P
        from docx.text.paragraph import Paragraph
        
        mock_doc = Mock()
        mock_para = Mock()
        mock_para.text = "Paragraph text"
        mock_para_element = Mock()
        
        mock_doc.element.body = [mock_para_element]
        mock_document.return_value = mock_doc
        
        # Мокаем Paragraph
        with patch('document_parser.Paragraph') as mock_paragraph_class:
            mock_paragraph = Mock()
            mock_paragraph.text = "Paragraph text"
            mock_paragraph_class.return_value = mock_paragraph
            
            data = b"DOCX content"
            result = DocumentParser._parse_docx(data)
            
            # Проверяем, что парсер был вызван
            assert isinstance(result, str)
    
    def test_parse_text_utf8(self):
        """Тест парсинга текстового файла в UTF-8"""
        data = "Текст на русском языке".encode('utf-8')
        result = DocumentParser._parse_text(data)
        
        assert result == "Текст на русском языке"
    
    def test_parse_text_cp1251(self):
        """Тест парсинга текстового файла в CP1251"""
        data = "Текст на русском".encode('cp1251')
        result = DocumentParser._parse_text(data)
        
        assert isinstance(result, str)
    
    def test_parse_content_success(self):
        """Тест успешного парсинга содержимого"""
        parser = DocumentParser(source="test.txt")
        
        with patch.object(parser, '_get_parser_for_source') as mock_get_parser:
            mock_parser_func = Mock(return_value="Parsed text")
            mock_get_parser.return_value = mock_parser_func
            
            data = b"File content"
            result = parser.parse_content(data)
            
            assert result == "Parsed text"
            assert parser.content == "Parsed text"
    
    def test_parse_content_no_parser(self):
        """Тест парсинга без подходящего парсера"""
        parser = DocumentParser(source="test.unknown")
        
        with patch.object(parser, '_get_parser_for_source') as mock_get_parser:
            mock_get_parser.return_value = None
            
            data = b"File content"
            result = parser.parse_content(data)
            
            assert result == ""
    
    def test_parse_content_error(self):
        """Тест обработки ошибки при парсинге"""
        parser = DocumentParser(source="test.txt")
        
        with patch.object(parser, '_get_parser_for_source') as mock_get_parser:
            mock_parser_func = Mock(side_effect=Exception("Parse error"))
            mock_get_parser.return_value = mock_parser_func
            
            data = b"File content"
            result = parser.parse_content(data)
            
            assert result == ""

