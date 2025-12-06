"""
Обертка для парсеров, которая обрабатывает результаты через fragments_creator
и отправляет во внешний API
"""
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
import httpx
import os

sys.path.append(str(Path(__file__).parent.parent))

from tools.fragments_creator import process_text_chunks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_fragments(
    parser_name: str,
    text_data: List[str],
    source: str = None
) -> Dict[str, Any]:
    """
    Создает фрагменты из текстовых данных через fragments_creator
    
    Args:
        parser_name: Имя парсера (например, 'alfabank', 'centralbank', 'naloggov')
        text_data: Список текстовых данных от парсера
        source: Источник данных (опционально)
    
    Returns:
        Словарь с фрагментами и метаданными
    """
    if not text_data:
        logger.warning(f"Парсер {parser_name} вернул пустые данные")
        return {
            "status": "empty",
            "parser_name": parser_name,
            "fragments": [],
            "metadata": {
                "source": source or f"{parser_name}_parser",
                "original_documents_count": 0
            }
        }
    
    logger.info(f"Обработка {len(text_data)} документов от парсера {parser_name}")
    
    source_name = source or f"{parser_name}_parser"
    fragments = await process_text_chunks(
        text_chunks=text_data,
        doc_prefix=parser_name,
        source=source_name,
        link=None
    )
    
    if not fragments:
        logger.warning(f"fragments_creator не создал фрагменты для {parser_name}")
        return {
            "status": "no_fragments",
            "parser_name": parser_name,
            "fragments": [],
            "metadata": {
                "source": source_name,
                "original_documents_count": len(text_data)
            }
        }
    
    logger.info(f"Создано {len(fragments)} фрагментов для {parser_name}")
    
    return {
        "status": "success",
        "parser_name": parser_name,
        "fragments": fragments,
        "metadata": {
            "source": source_name,
            "original_documents_count": len(text_data)
        }
    }


async def process_and_send(
    parser_name: str,
    text_data: List[str],
    source: str = None,
    api_url: str = None
) -> Dict[str, Any]:
    """
    Обрабатывает текстовые данные через fragments_creator и отправляет во внешний API
    
    Args:
        parser_name: Имя парсера (например, 'alfabank', 'centralbank', 'naloggov')
        text_data: Список текстовых данных от парсера
        source: Источник данных (опционально)
        api_url: URL API сервиса (если не указан, берется из переменных окружения)
    
    Returns:
        Результат обработки и отправки
    """
    if not text_data:
        logger.warning(f"Парсер {parser_name} вернул пустые данные")
        return {
            "status": "empty",
            "parser_name": parser_name,
            "fragments_count": 0
        }
    
    logger.info(f"Обработка {len(text_data)} документов от парсера {parser_name}")
    
    source_name = source or f"{parser_name}_parser"
    fragments = await process_text_chunks(
        text_chunks=text_data,
        doc_prefix=parser_name,
        source=source_name,
        link=None
    )
    
    if not fragments:
        logger.warning(f"fragments_creator не создал фрагменты для {parser_name}")
        return {
            "status": "no_fragments",
            "parser_name": parser_name,
            "fragments_count": 0
        }
    
    logger.info(f"Создано {len(fragments)} фрагментов для {parser_name}")
    
    api_url = api_url or os.getenv("PARSER_SERVICE_API_URL", "http://parser_service:8000/api/v1/parser/result")
    
    result = await send_to_api(
        api_url=api_url,
        parser_name=parser_name,
        fragments=fragments,
        metadata={
            "source": source_name,
            "original_documents_count": len(text_data)
        }
    )
    
    return {
        "status": "success",
        "parser_name": parser_name,
        "fragments_count": len(fragments),
        "api_response": result
    }


async def send_to_api(
    api_url: str,
    parser_name: str,
    fragments: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Отправляет фрагменты в API сервис
    
    Args:
        api_url: URL API endpoint
        parser_name: Имя парсера
        fragments: Список фрагментов
        metadata: Метаданные
    
    Returns:
        Ответ от API
    """
    payload = {
        "parser_name": parser_name,
        "fragments": fragments,
        "metadata": metadata
    }
    
    timeout = int(os.getenv("API_TIMEOUT", "300"))
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"Отправка {len(fragments)} фрагментов в API: {api_url}")
            response = await client.post(api_url, json=payload)
            response.raise_for_status()
            
            result = response.json() if response.content else {"status": "ok"}
            logger.info(f"Успешно отправлено. Статус: {response.status_code}")
            return result
    except httpx.HTTPError as e:
        logger.error(f"Ошибка HTTP при отправке в API: {e}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при отправке в API: {e}")
        raise


def run_parser_with_processing(
    parser_main_func,
    parser_name: str,
    source: str = None,
    api_url: str = None
) -> Dict[str, Any]:
    """
    Синхронная обертка для запуска парсера и обработки результатов
    
    Args:
        parser_main_func: Функция main() парсера, которая возвращает List[str]
        parser_name: Имя парсера
        source: Источник данных
        api_url: URL API
    
    Returns:
        Результат обработки
    """
    logger.info(f"Запуск парсера: {parser_name}")
    text_data = parser_main_func()
    
    return asyncio.run(process_and_send(
        parser_name=parser_name,
        text_data=text_data,
        source=source,
        api_url=api_url
    ))

