import logging
from pathlib import Path
from typing import Optional
import requests
import io
from .html_pdf import HTMLToPDFConverter

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PDFParser:
    """Парсер PDF файлов с поддержкой множества методов извлечения текста"""
    
    def __init__(self):
        """Инициализация парсера"""
        self.available_methods = []
        
        if PDFPLUMBER_AVAILABLE:
            self.available_methods.append('pdfplumber')
        if PDFMINER_AVAILABLE:
            self.available_methods.append('pdfminer')
        if PYPDF2_AVAILABLE:
            self.available_methods.append('pypdf2')
        
        if not self.available_methods:
            logger.warning("Ни одна библиотека для парсинга PDF не установлена!")
            logger.warning("Установите: pip install pdfplumber PyPDF2 pdfminer.six")
        else:
            logger.info(f"Доступные методы парсинга: {', '.join(self.available_methods)}")
        
        try:
            self.html_converter = HTMLToPDFConverter()
        except Exception as e:
            logger.warning(f"HTML to PDF конвертер недоступен: {e}")
            self.html_converter = None
    
    def download_pdf(self, url: str, timeout: int = 30) -> Optional[bytes]:
        """
        Скачивает PDF по URL
        
        Args:
            url: URL PDF файла
            timeout: Таймаут запроса
            
        Returns:
            Байты PDF файла или None если это не PDF
        """
        try:
            logger.info(f"Скачиваем PDF: {url}")
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            pdf_bytes = response.content
            
            if pdf_bytes[:4] != b'%PDF':
                logger.warning(f"Это не PDF файл (Content-Type: {content_type})")
                return None
            
            logger.info(f"Скачано {len(pdf_bytes)} байт")
            return pdf_bytes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка скачивания PDF: {e}")
            return None
    
    def extract_text_pdfplumber(self, pdf_bytes: bytes) -> str:
        """
        Извлекает текст используя pdfplumber (лучший метод)
        
        Args:
            pdf_bytes: Байты PDF файла
            
        Returns:
            Извлечённый текст
        """
        try:
            text_parts = []
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                logger.info(f"Страниц в PDF: {len(pdf.pages)}")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    
                    if page_num % 10 == 0:
                        logger.info(f"Обработано страниц: {page_num}/{len(pdf.pages)}")
            
            full_text = '\n\n'.join(text_parts)
            logger.info(f"Извлечено символов: {len(full_text)}")
            return full_text
            
        except Exception as e:
            logger.error(f"Ошибка pdfplumber: {e}")
            return ""
    
    def extract_text_pdfminer(self, pdf_bytes: bytes) -> str:
        """
        Извлекает текст используя pdfminer (альтернативный метод)
        
        Args:
            pdf_bytes: Байты PDF файла
            
        Returns:
            Извлечённый текст
        """
        try:
            text = pdfminer_extract_text(io.BytesIO(pdf_bytes))
            logger.info(f"Извлечено символов: {len(text)}")
            return text
            
        except Exception as e:
            logger.error(f"Ошибка pdfminer: {e}")
            return ""
    
    def extract_text_pypdf2(self, pdf_bytes: bytes) -> str:
        """
        Извлекает текст используя PyPDF2 (базовый метод)
        
        Args:
            pdf_bytes: Байты PDF файла
            
        Returns:
            Извлечённый текст
        """
        try:
            text_parts = []
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            logger.info(f"Страниц в PDF: {len(pdf_reader.pages)}")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                
                if page_num % 10 == 0:
                    logger.info(f"Обработано страниц: {page_num}/{len(pdf_reader.pages)}")
            
            full_text = '\n\n'.join(text_parts)
            logger.info(f"Извлечено символов: {len(full_text)}")
            return full_text
            
        except Exception as e:
            logger.error(f"Ошибка PyPDF2: {e}")
            return ""
    
    def extract_text(self, pdf_bytes: bytes, method: str = 'auto') -> str:
        """
        Извлекает текст из PDF используя указанный или автоматический метод
        
        Args:
            pdf_bytes: Байты PDF файла
            method: Метод извлечения ('auto', 'pdfplumber', 'pdfminer', 'pypdf2')
            
        Returns:
            Извлечённый текст
        """
        if method == 'auto':
            for method_name in self.available_methods:
                logger.info(f"Пробуем метод: {method_name}")
                
                if method_name == 'pdfplumber':
                    text = self.extract_text_pdfplumber(pdf_bytes)
                elif method_name == 'pdfminer':
                    text = self.extract_text_pdfminer(pdf_bytes)
                elif method_name == 'pypdf2':
                    text = self.extract_text_pypdf2(pdf_bytes)
                else:
                    continue
                
                if text and len(text.strip()) > 100:
                    logger.info(f"Успешно извлечён текст методом {method_name}")
                    return text
                else:
                    logger.warning(f"Метод {method_name} извлёк мало текста, пробуем следующий...")
            
            logger.error("Все методы не смогли извлечь достаточно текста")
            return ""
        else:
            if method == 'pdfplumber' and PDFPLUMBER_AVAILABLE:
                return self.extract_text_pdfplumber(pdf_bytes)
            elif method == 'pdfminer' and PDFMINER_AVAILABLE:
                return self.extract_text_pdfminer(pdf_bytes)
            elif method == 'pypdf2' and PYPDF2_AVAILABLE:
                return self.extract_text_pypdf2(pdf_bytes)
            else:
                logger.error(f"Метод {method} недоступен")
                return ""
    
    def parse_pdf_from_url(self, url: str, method: str = 'auto') -> Optional[str]:
        """
        Скачивает и парсит PDF по URL
        Если это не PDF, конвертирует HTML в PDF
        
        Args:
            url: URL PDF файла или HTML страницы
            method: Метод извлечения текста
            
        Returns:
            Извлечённый текст или None при ошибке
        """

        pdf_bytes = self.download_pdf(url)
        
        if not pdf_bytes and self.html_converter:
            logger.info("Конвертируем HTML страницу в PDF...")
            pdf_bytes = self.html_converter.convert_url_to_pdf(url)
        
        if not pdf_bytes:
            logger.error("Не удалось получить PDF")
            return None
        
        text = self.extract_text(pdf_bytes, method=method)
        return text if text else None
    
    def clean_text(self, text: str) -> str:
        """
        Очищает текст от лишних символов и служебной информации
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст
        """

        footer_patterns = [
            "07016, Москва, ул. Неглинная, д. 12, к. В, Банк России",
            "8 800 300-30-00",
            "www.cbr.ru"
        ]
        
        for pattern in footer_patterns:
            text = text.replace(pattern, '')
        
        text = ' '.join(text.split())
    
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        return text
