import sys
import os
import re
from pathlib import Path
import logging
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import asyncio
import httpx

sys.path.append(str(Path(__file__).parent.parent))

from tools.pdf import PDFParser
from tools.pdf_ocr import extract_text_ocr

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PravoDocumentParser:
    """Парсер документов с pravo.gov.ru"""
    
    def __init__(self, base_url: str = "http://publication.pravo.gov.ru"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.pdf_parser = PDFParser()
    
    def _clean_pravo_text(self, text: str) -> str:
        """
        Очищает текст от служебных строк и штампов
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            is_service = False
            
            if len(line) < 3:
                is_service = True
            
            if '|' in line:
                is_service = True
            
            if line.startswith('МИНИСТЕРСТВО'):
                is_service = True
            
            if '(МЧС РОССИИ)' in line:
                is_service = True
            
            if 'Регистрационный' in line:
                is_service = True
            
            if re.match(r'^№\s*\d+.*т\.\s*\|?$', line):
                is_service = True
            
            if re.match(r'^\d+$', line) and len(line) <= 6:
                is_service = True
            
            if re.search(r'[A-Z]{5,}', line) and re.search(r'[А-Я]{2,}', line):
                is_service = True
            
            if not is_service:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _make_absolute_url(self, url: str) -> str:
        """
        Преобразует относительные URL в абсолютные
        """
        if url.startswith('http'):
            return url
        elif url.startswith('/'):
            return f"{self.base_url}{url}"
        else:
            return f"{self.base_url}/{url}"
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Получает HTML-контент страницы
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            logger.error(f"Ошибка при загрузке страницы {url}: {e}")
            return None
    
    def _find_pdf_link(self, html: str) -> Optional[str]:
        """
        Находит ссылку на PDF файл на странице документа
        
        Args:
            html: HTML контент страницы
            
        Returns:
            URL PDF файла или None
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        pdf_link = soup.select_one('body > div > div > main > div:nth-child(3) > div.row.notforprint > div.col-6.text-right > a:nth-child(1)')
        
        if not pdf_link:
            logger.warning("Кнопка скачивания PDF не найдена")
            return None
        
        href = pdf_link.get('href', '')
        if not href:
            logger.warning("Ссылка на PDF не найдена")
            return None
        
        pdf_url = self._make_absolute_url(href)
        logger.info(f"Найдена ссылка на PDF: {pdf_url}")
        return pdf_url
    
    def parse_document(self, url: str) -> Optional[str]:
        """
        Парсит один документ: находит PDF ссылку и извлекает текст
        
        Args:
            url: URL страницы документа
            
        Returns:
            Текст документа или None при ошибке
        """
        logger.info(f"Парсинг документа: {url}")
        
        html = self._fetch_page(url)
        if not html:
            return None
        
        pdf_url = self._find_pdf_link(html)
        if not pdf_url:
            return None
        
        pdf_bytes = self.pdf_parser.download_pdf(pdf_url)
        if not pdf_bytes:
            return None
        
        ocr_text = extract_text_ocr(pdf_bytes)
        if ocr_text:
            ocr_text = self._clean_pravo_text(ocr_text)
            logger.info(f"Успешно распарсен через OCR ({len(ocr_text)} символов)")
            return ocr_text
        
        return None
    
    async def _fetch_page_async(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        """
        Асинхронно получает HTML-контент страницы
        """
        try:
            response = await client.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except httpx.RequestError as e:
            logger.error(f"Ошибка при загрузке страницы {url}: {e}")
            return None
    
    async def _download_pdf_async(self, client: httpx.AsyncClient, pdf_url: str) -> Optional[bytes]:
        """
        Асинхронно скачивает PDF файл
        """
        try:
            response = await client.get(pdf_url, headers=self.headers, timeout=60.0)
            response.raise_for_status()
            return response.content
        except httpx.RequestError as e:
            logger.error(f"Ошибка при скачивании PDF {pdf_url}: {e}")
            return None
    
    async def parse_document_async(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        """
        Асинхронно парсит один документ: находит PDF ссылку и извлекает текст
        
        Args:
            client: httpx.AsyncClient для асинхронных запросов
            url: URL страницы документа
            
        Returns:
            Текст документа или None при ошибке
        """
        logger.info(f"Парсинг документа: {url}")
        
        html = await self._fetch_page_async(client, url)
        if not html:
            return None
        
        pdf_url = self._find_pdf_link(html)
        if not pdf_url:
            return None
        
        pdf_bytes = await self._download_pdf_async(client, pdf_url)
        if not pdf_bytes:
            return None
        
        ocr_text = extract_text_ocr(pdf_bytes)
        if ocr_text:
            ocr_text = self._clean_pravo_text(ocr_text)
            logger.info(f"Успешно распарсен через OCR ({len(ocr_text)} символов)")
            return ocr_text
        
        return None
    
    async def parse_documents_async(self, urls: List[str], max_concurrent: int = 5) -> List[str]:
        """
        Асинхронно парсит список документов
        
        Args:
            urls: Список URL документов
            max_concurrent: Максимальное количество одновременных запросов
            
        Returns:
            Список текстов документов (каждый элемент - спаршенный текст)
        """
        logger.info(f"Асинхронный парсинг {len(urls)} документов (макс. {max_concurrent} одновременно)")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def parse_with_semaphore(url: str) -> Optional[str]:
            async with semaphore:
                async with httpx.AsyncClient() as client:
                    return await self.parse_document_async(client, url)
        
        tasks = [parse_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        texts = []
        for idx, result in enumerate(results, 1):
            if isinstance(result, Exception):
                logger.error(f"Ошибка при парсинге документа {idx}: {result}")
            elif result:
                texts.append(result)
            else:
                logger.warning(f"Не удалось распарсить документ {idx}")
        
        logger.info(f"Успешно распарсено: {len(texts)}/{len(urls)}")
        return texts




