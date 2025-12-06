import logging
import time
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


class HTMLToPDFConverter:
    """Конвертер HTML страниц в PDF"""
    
    def __init__(self):
        """Инициализация конвертера"""
        logger.info("Инициализирован HTML to PDF конвертер")
    
    def convert_url_to_pdf(self, url: str, wait_time: int = 1) -> Optional[bytes]:
        """
        Конвертирует HTML страницу в PDF (возвращает bytes напрямую)
        
        Args:
            url: URL страницы для конвертации
            wait_time: Время ожидания после загрузки (секунды)
            
        Returns:
            PDF как bytes или None при ошибке
        """
        try:
            logger.info(f"Конвертируем HTML в PDF: {url}")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(url, wait_until='networkidle', timeout=60000)
                logger.info("Страница загружена")

                if wait_time > 0:
                    time.sleep(wait_time)

                pdf_bytes = page.pdf(format='A4')
                
                browser.close()
                
                logger.info(f"PDF сгенерирован: {len(pdf_bytes)} байт")
                return pdf_bytes
                
        except Exception as e:
            logger.error(f"Ошибка конвертации HTML в PDF: {e}")
            return None

