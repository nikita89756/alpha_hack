import hashlib
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)


def generate_doc_id(url: str) -> str:
    """
    Генерирует уникальный ID для документа на основе URL
    
    Args:
        url: URL документа
        
    Returns:
        Уникальный ID (hash)
    """
    return hashlib.md5(url.encode()).hexdigest()


def init_collection(qdrant_client: QdrantClient, collection_name: str) -> None:
    """
    Проверяет существование коллекции в Qdrant.
    Коллекции создаются в отдельном сервисе qdrant-init.
    
    Args:
        qdrant_client: Клиент Qdrant
        collection_name: Имя коллекции
    """
    try:
        collections = qdrant_client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        
        if exists:
            logger.info(f"Коллекция '{collection_name}' найдена и готова к использованию")
        else:
            logger.warning(f"Коллекция '{collection_name}' не найдена! Убедитесь, что qdrant-init сервис выполнился успешно.")
    except Exception as e:
        logger.error(f"Ошибка при проверке коллекции: {e}")


def is_document_exists(qdrant_client: QdrantClient, collection_name: str, url: str) -> bool:
    """
    Проверяет существует ли документ в Qdrant
    
    Args:
        qdrant_client: Клиент Qdrant
        collection_name: Имя коллекции
        url: URL документа
        
    Returns:
        True если документ уже есть в базе
    """
    try:
        doc_id = generate_doc_id(url)
        result = qdrant_client.retrieve(
            collection_name=collection_name,
            ids=[doc_id]
        )
        return len(result) > 0
    except Exception as e:
        logger.error(f"Ошибка проверки существования: {e}")
        return False


def add_to_qdrant(qdrant_client: QdrantClient, collection_name: str, document: dict) -> bool:
    """
    Добавляет документ в Qdrant
    
    Args:
        qdrant_client: Клиент Qdrant
        collection_name: Имя коллекции
        document: Словарь с данными документа
        
    Returns:
        True если успешно добавлен
    """
    try:
        doc_id = generate_doc_id(document['url'])

        point = PointStruct(
            id=doc_id,
            vector=[0.0], 
            payload={
                'title': document.get('title', ''),
                'url': document['url'],
                'source': document.get('source', ''),
            }
        )
        
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[point]
        )
        
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления в Qdrant: {e}")
        return False

