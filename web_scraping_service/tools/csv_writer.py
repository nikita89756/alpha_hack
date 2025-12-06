import csv
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import sys
import re

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    Нормализует текст для сохранения в CSV:
    - Убирает лишние пробелы и переносы строк
    - Заменяет множественные пробелы на один
    - Нормализует переносы строк
    - Убирает пробелы в начале и конце
    - Убирает Markdown разметку (###, **, -, HASHTAGS:)
    
    Args:
        text: Исходный текст
        
    Returns:
        Нормализованный текст
    """
    if not text:
        return ""

    text = re.sub(r'^###\s+', '', text, flags=re.MULTILINE)

    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)

    text = re.sub(r'^[-•]\s+', '', text, flags=re.MULTILINE)

    text = re.sub(r'HASHTAGS:\s*', '', text, flags=re.IGNORECASE)

    text = re.sub(r'\*\*(Контекст|Путь|Выжимка|Ключевые факты):\*\*\s*', '', text, flags=re.IGNORECASE)
    
    text = re.sub(r'[\r\n]+', ' ', text)

    text = re.sub(r' +', ' ', text)

    text = text.strip()
    
    return text


def get_csv_path() -> str:
    """
    Возвращает путь к CSV файлу для сохранения результатов.
    Сохраняет в bot_service/agent_system/service/base.csv
    
    Returns:
        Путь к CSV файлу
    """

    csv_path = Path("/opt/airflow/bot_service_data/service/base.csv")
    
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    return str(csv_path)


def save_fragments_to_csv(
    documents: List[Dict[str, Any]],
    csv_path: str = None
) -> Dict[str, Any]:
    """
    Потокобезопасно сохраняет документы в CSV файл.
    Все DAG файлы записывают в один CSV файл.
    
    Args:
        documents: Список словарей с ключами "knowledge" и "title"
        csv_path: Путь к CSV файлу (если не указан, используется дефолтный)
    
    Returns:
        Словарь с результатом операции
    """
    if csv_path is None:
        csv_path = get_csv_path()
    
    if not documents:
        logger.warning("Нет документов для сохранения в CSV")
        return {
            "status": "empty",
            "message": "Нет документов для сохранения",
            "saved_count": 0
        }
    
    valid_documents = []
    for doc in documents:
        knowledge = normalize_text(doc.get("knowledge", ""))
        title = normalize_text(doc.get("title", ""))

        if knowledge: 
            valid_documents.append({
                "title": title,
                "knowledge": knowledge
            })
    
    if not valid_documents:
        logger.warning("После фильтрации не осталось валидных документов")
        return {
            "status": "empty",
            "message": "После фильтрации не осталось валидных документов",
            "saved_count": 0
        }
    
    file_exists = os.path.exists(csv_path)
    
    try:
        mode = 'a' if file_exists else 'w'
        
        with open(csv_path, mode, encoding='utf-8-sig', newline='') as f:
            if HAS_FCNTL and sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            try:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["title", "knowledge"],
                    quoting=csv.QUOTE_ALL
                )
                
                if not file_exists:
                    writer.writeheader()
                
                for doc in valid_documents:
                    writer.writerow(doc)
                
                logger.info(f"Сохранено {len(valid_documents)} документов в CSV: {csv_path}")
                
            finally:
                if HAS_FCNTL and sys.platform != 'win32':
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        return {
            "status": "success",
            "message": f"Сохранено {len(valid_documents)} документов",
            "saved_count": len(valid_documents),
            "csv_path": csv_path
        }
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении в CSV: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Ошибка при сохранении в CSV: {str(e)}",
            "saved_count": 0
        }

