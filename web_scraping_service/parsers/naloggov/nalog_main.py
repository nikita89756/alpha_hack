import logging
import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Set

sys.path.append(str(Path(__file__).parent.parent.parent))

from parsers.naloggov.nalog_urls import NalogGovParser
from parsers.naloggov.nalog_gov import NalogPageParser

logger = logging.getLogger(__name__)


class NalogAsyncParser:
    """Асинхронный парсер страниц nalog.gov.ru"""
    
    def __init__(self, concurrent_limit: int = 5):
        """
        Инициализация парсера
        
        Args:
            concurrent_limit: Количество одновременно парсящихся страниц
        """
        self.concurrent_limit = concurrent_limit
        self.parser = NalogPageParser()
        logger.info(f"Инициализирован асинхронный парсер (лимит: {concurrent_limit})")
    
    async def parse_urls(self, urls) -> List[str]:
        """
        Асинхронно парсит список URL
        
        Args:
            urls: Список или множество URL для парсинга
            
        Returns:
            Список текстов
        """
        logger.info(f"Начинаем парсинг {len(urls)} страниц (по {self.concurrent_limit} одновременно)")
        
        texts = []
        
        with ThreadPoolExecutor(max_workers=self.concurrent_limit) as executor:
            loop = asyncio.get_event_loop()
            
            tasks = []
            url_list = list(urls) if isinstance(urls, set) else urls
            for idx, url in enumerate(sorted(url_list), 1):
                task = loop.run_in_executor(
                    executor,
                    self._parse_with_log,
                    url,
                    idx,
                    len(urls)
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            texts = [text for text in results if text]
        
        logger.info(f"Успешно распарсено: {len(texts)}/{len(urls)}")
        return texts
    
    def _parse_with_log(self, url: str, index: int, total: int) -> str:
        """
        Парсит страницу с логированием прогресса
        
        Args:
            url: URL страницы
            index: Номер страницы
            total: Всего страниц
            
        Returns:
            Текст страницы
        """
        logger.info(f"[{index}/{total}] Парсим: {url}")
        text = self.parser.parse_page(url)
        
        if text:
            logger.info(f"[{index}/{total}] ✓ Извлечено {len(text)} символов")
        else:
            logger.warning(f"[{index}/{total}] ✗ Не удалось извлечь текст")
        
        return text


def main() -> List[str]:
    """
    Основная функция - получает URL и парсит все страницы
    
    Returns:
        Список текстов со всех страниц
    """

    logger.info("Получаем список URL...")
    url_parser = NalogGovParser()
    urls = url_parser.parse_all()
    
    if not urls:
        logger.error("Не найдено URL для парсинга")
        return []
    
    logger.info(f"Найдено {len(urls)} URL")
    
    async_parser = NalogAsyncParser(concurrent_limit=5)
    texts = asyncio.run(async_parser.parse_urls(urls))
    
    logger.info(f"Готово! Распарсено {len(texts)} страниц")
    return texts


