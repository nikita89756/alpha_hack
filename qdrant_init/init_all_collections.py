import logging
import os
import sys
import time
import uuid
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, PointStruct

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("CRITICAL ERROR: sentence-transformers not installed.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def wait_for_qdrant(qdrant_url: str, max_retries: int = 60, delay: int = 2):
    logger.info(f"Ожидание Qdrant: {qdrant_url}")
    for attempt in range(max_retries):
        try:
            client = QdrantClient(url=qdrant_url, timeout=30)
            client.get_collections()
            logger.info("Qdrant готов!")
            return client
        except Exception:
            time.sleep(delay)
    raise Exception("Qdrant недоступен")


def create_collection_safe(client: QdrantClient, collection_name: str, vectors_config: dict, sparse_vectors_config: dict = None, recreate: bool = False):
    try:
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        
        if exists:
            if recreate:
                logger.info(f"!!! ПЕРЕСОЗДАНИЕ коллекции {collection_name} (удаляем старую) !!!")
                client.delete_collection(collection_name=collection_name)
                time.sleep(1)
            else:
                logger.info(f"Коллекция {collection_name} уже есть, пропускаем.")
                return
        
        logger.info(f"Создаем коллекцию {collection_name}...")
        create_params = {
            "collection_name": collection_name,
            "vectors_config": vectors_config
        }
        if sparse_vectors_config:
            create_params["sparse_vectors_config"] = sparse_vectors_config
        
        client.create_collection(**create_params)
        logger.info(f"Коллекция {collection_name} создана.")
        
    except Exception as e:
        logger.error(f"Ошибка создания {collection_name}: {e}")
        raise


def load_knowledge_base_data(client: QdrantClient, csv_path: str = "base.csv"):
    if not os.path.exists(csv_path):
        logger.error(f"ФАЙЛ {csv_path} НЕ НАЙДЕН! Текущая папка: {os.getcwd()}")
        logger.error(f"Файлы рядом: {os.listdir(os.getcwd())}")
        return

    count = client.count(collection_name="knowledge_base").count
    if count > 0:
        logger.info(f"В базе уже {count} записей. Пропускаем загрузку.")
        return

    logger.info(f"Читаем файл {csv_path}...")
    
    try:
        df = pd.read_csv(csv_path)

        if 'source' not in df.columns: df['source'] = ""
        df['source'] = df['source'].fillna("")

        if 'title' not in df.columns or 'knowledge' not in df.columns:
            logger.error(f"НЕВЕРНЫЕ КОЛОНКИ! Найдены: {df.columns.tolist()}. Нужны: title, knowledge")
            return

        df = df.dropna(subset=['knowledge'])
        logger.info(f"Найдено {len(df)} строк для загрузки.")

        logger.info("Загрузка модели эмбеддингов...")
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
        
        logger.info("Генерация векторов (это может занять время)...")
        embeddings = model.encode(df['knowledge'].tolist(), show_progress_bar=True)

        points = []
        for i, row in df.iterrows():
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector={"default": embeddings[i].tolist()},
                payload={
                    "title": row['title'],
                    "knowledge": row['knowledge'],
                    "source": str(row['source'])
                }
            ))

        logger.info(f"Загрузка {len(points)} точек в Qdrant...")
        batch_size = 100
        for i in range(0, len(points), batch_size):
            client.upsert(collection_name="knowledge_base", points=points[i:i+batch_size])
            logger.info(f"Загружено {min(i+batch_size, len(points))}/{len(points)}")

        logger.info("УСПЕХ! Данные загружены.")

    except Exception as e:
        logger.error(f"Ошибка загрузки CSV: {e}", exc_info=True)


def init_bot_service_collections(client: QdrantClient):
    logger.info("=== Инициализация Bot Service ===")

    create_collection_safe(
        client=client,
        collection_name="knowledge_base",
        vectors_config={"default": VectorParams(size=768, distance=Distance.COSINE)},
        sparse_vectors_config={"bm25": SparseVectorParams()},
        recreate=False # <--- ВОТ ЭТО ИСПРАВЛЕНИЕ
    )
    
    load_knowledge_base_data(client)
    
    create_collection_safe(
        client=client,
        collection_name="long_term_memory",
        vectors_config={"dense": VectorParams(size=768, distance=Distance.COSINE)},
        recreate=False
    )
    try:
        client.create_payload_index("long_term_memory", "user_id", "keyword")
    except: pass


def init_airflow_collections(client: QdrantClient):
    logger.info("=== Инициализация Airflow ===")
    for name in ["pravo_documents", "cbr_microbusiness"]:
        create_collection_safe(
            client=client,
            collection_name=name,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
            recreate=False
        )


def main():
    try:
        client = wait_for_qdrant(os.getenv("QDRANT_URL", "http://qdrant:6333"))
        init_bot_service_collections(client)
        init_airflow_collections(client)
        
        logger.info("=== ФИНАЛЬНЫЙ ОТЧЕТ ===")
        for col in client.get_collections().collections:
            cnt = client.count(col.name).count
            logger.info(f"Коллекция {col.name}: {cnt} точек")
            
    except Exception as e:
        logger.error(f"FATAL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
