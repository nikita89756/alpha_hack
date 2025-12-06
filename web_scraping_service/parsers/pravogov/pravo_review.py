import sys
import os
from pathlib import Path
import logging
from typing import List, Dict

sys.path.append(str(Path(__file__).parent.parent))

from parsers.pravogov.pravo_qdrant import init_collection, is_document_exists, add_to_qdrant
from parsers.pravogov.pravo_title import PravoReviewParser
from tools.llm import LLMClient, DocumentRelevanceChecker
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PravoDocumentReviewer:
    """Класс для проверки и загрузки документов pravo.gov.ru в Qdrant"""
    
    def __init__(self, qdrant_url: str = "qdrant", qdrant_port: int = 6333, collection_name: str = "pravo_documents") -> None:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.llm_client = LLMClient(api_key=api_key)
        self.relevance_checker = DocumentRelevanceChecker(self.llm_client)
        
        self.qdrant_client = QdrantClient(
            host=qdrant_url, 
            port=qdrant_port,
            timeout=20  
        )
        self.collection_name = collection_name
        
        try:
            self.qdrant_client.get_collections()
            logger.info(f"Подключение к Qdrant успешно: {qdrant_url}:{qdrant_port}")
        except Exception as e:
            logger.error(f"Не удалось подключиться к Qdrant {qdrant_url}:{qdrant_port}: {e}")
            raise ConnectionError(f"Не удалось подключиться к Qdrant {qdrant_url}:{qdrant_port}: {e}") from e
        
        init_collection(self.qdrant_client, self.collection_name)
    
    def filter_new_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Фильтрует новые документы и добавляет их в Qdrant
        
        Args:
            documents: Список документов с 'title' и 'url'
            
        Returns:
            Список новых документов
        """
        if not documents:
            logger.info("Нет документов для фильтрации")
            return []
        
        logger.info(f"Начало фильтрации {len(documents)} документов...")
        
        from parsers.pravogov.pravo_qdrant import generate_doc_id
        logger.info("Генерация ID для документов...")
        doc_ids = [generate_doc_id(doc['url']) for doc in documents]
        logger.info(f"Сгенерировано {len(doc_ids)} ID")
        
        batch_size = 100
        existing_ids = set()
        total_batches = (len(doc_ids) + batch_size - 1) // batch_size
        
        logger.info(f"Начало проверки существования документов ({total_batches} батчей по {batch_size})...")
        connection_errors = 0
        for i in range(0, len(doc_ids), batch_size):
            batch_ids = doc_ids[i:i + batch_size]
            batch_num = i // batch_size + 1
            try:
                logger.info(f"Проверка батча {batch_num}/{total_batches} ({len(batch_ids)} документов)...")
                results = self.qdrant_client.retrieve(
                    collection_name=self.collection_name,
                    ids=batch_ids
                )
                existing_ids.update([r.id for r in results])
                logger.info(f"Батч {batch_num}/{total_batches}: найдено {len(results)} существующих (всего: {len(existing_ids)})")
                connection_errors = 0  
            except Exception as e:
                connection_errors += 1
                logger.error(f"Ошибка при проверке батча {batch_num}/{total_batches}: {e}", exc_info=True)
                if connection_errors >= total_batches:
                    raise ConnectionError(f"Не удалось подключиться к Qdrant после {connection_errors} попыток: {e}") from e
        
        logger.info(f"Проверка завершена. Всего существующих: {len(existing_ids)}/{len(doc_ids)}")
        
        logger.info("Начало фильтрации и добавления новых документов...")
        new_docs = []
        points_to_add = []
        upsert_batch_size = 50
        upsert_errors = 0
        
        for idx, doc in enumerate(documents):
            doc_id = doc_ids[idx]
            if doc_id not in existing_ids:
                new_docs.append(doc)
                
                from qdrant_client.models import PointStruct
                point = PointStruct(
                    id=doc_id,
                    vector=[0.0],
                    payload={
                        'title': doc.get('title', ''),
                        'url': doc['url'],
                        'source': doc.get('source', ''),
                    }
                )
                points_to_add.append(point)
                
                if len(points_to_add) >= upsert_batch_size:
                    try:
                        logger.info(f"Добавление батча из {len(points_to_add)} документов в Qdrant...")
                        self.qdrant_client.upsert(
                            collection_name=self.collection_name,
                            points=points_to_add
                        )
                        logger.info(f"Добавлено {len(points_to_add)} документов в Qdrant (всего новых: {len(new_docs)})")
                        points_to_add = []
                        upsert_errors = 0  
                    except Exception as e:
                        upsert_errors += 1
                        logger.error(f"✗ Ошибка при добавлении батча в Qdrant: {e}", exc_info=True)
                        if upsert_errors >= 3:
                            raise ConnectionError(f"Не удалось добавить данные в Qdrant после {upsert_errors} попыток: {e}") from e
            else:
                if (idx + 1) % 100 == 0:
                    logger.info(f"Проверено {idx + 1}/{len(documents)} документов, новых: {len(new_docs)}")
        
        if points_to_add:
            try:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points_to_add
                )
                logger.info(f"Добавлено {len(points_to_add)} документов в Qdrant (всего новых: {len(new_docs)})")
            except Exception as e:
                logger.error(f"Ошибка при добавлении последнего батча в Qdrant: {e}")
                raise ConnectionError(f"Не удалось добавить последний батч в Qdrant: {e}") from e
        
        logger.info(f"Фильтрация завершена. Новых документов: {len(new_docs)}/{len(documents)}")
        return new_docs
    
    def filter_relevant_documents_batch(self, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Фильтрует релевантные документы через LLM батчами по 10 титульников
        
        Args:
            documents: Список документов
            
        Returns:
            Список релевантных документов
        """
        if not documents:
            logger.info("Нет документов для проверки релевантности")
            return []
        
        logger.info(f"Проверка релевантности {len(documents)} документов через LLM (батчами по 10)")
        relevant_docs = []
        
        batch_size = 10
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            titles = [doc['title'] for doc in batch]
            
            logger.info(f"Проверка батча {i//batch_size + 1}: {len(batch)} титульников")
            
            indices = self.relevance_checker.check_relevance_batch(
                titles=titles,
                source="pravo.gov.ru",
                category=""
            )
            
            if indices is not None:
                for idx in indices:
                    if idx < len(batch):
                        relevant_docs.append(batch[idx])
                        logger.info(f"Подходит: {batch[idx]['title'][:60]}...")
            else:
                logger.info(f"Батч {i//batch_size + 1}: ни один документ не подходит")
        
        logger.info(f"Релевантных документов: {len(relevant_docs)}")
        return relevant_docs
    
    def process_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Обрабатывает документы: фильтрует новые, добавляет в Qdrant, проверяет релевантность
        
        Args:
            documents: Список документов с 'title' и 'url'
            
        Returns:
            Список документов, которые прошли проверку и были новыми
        """
        new_docs = self.filter_new_documents(documents)
        relevant_docs = self.filter_relevant_documents_batch(new_docs)
        
        return relevant_docs