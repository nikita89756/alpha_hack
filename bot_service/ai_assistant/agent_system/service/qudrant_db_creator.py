"""Utilities for populating Qdrant collections from CSV files."""

import logging
import sys
from pathlib import Path
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  
from qdrant_client import QdrantClient, models  

from ai_assistant.agent_system.rag.controller import RetrieverController  
from ai_assistant.agent_system.utils.model_loader import load_deeppavlov_bert  


logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_COLLECTION = "knowledge_base"
LONG_TERM_MEMORY_COLLECTION = "long_term_memory"

VECTOR_PARAMS = models.VectorParams(
    size=768,
    distance=models.Distance.COSINE
)


def setup_knowledge_base(client: QdrantClient, collection_name: str) -> None:
    """Create the dense knowledge-base collection.

    Args:
        client: Connected Qdrant client.
        collection_name: Name of the knowledge-base collection.

    Returns:
        None. The function creates or recreates the target collection.
    """


    try:
        collections_response = client.get_collections()
        existing_collections = [c.name for c in collections_response.collections]

        if collection_name in existing_collections:
            logger.info("Коллекция '%s' уже существует, пересоздаем", collection_name)
            client.delete_collection(collection_name=collection_name)

        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "default": VECTOR_PARAMS
            },
            hnsw_config=models.HnswConfigDiff(m=16, ef_construct=200)
        )
        logger.info("Коллекция '%s' создана с поддержкой гибридного поиска", collection_name)

        logger.info("Настройка индексов для коллекции '%s'", collection_name)
        client.create_payload_index(
            collection_name=collection_name,
            field_name="key",
            field_schema=models.PayloadSchemaType.INTEGER
        )
        logger.info("Индекс для поля 'key' создан")



        client.create_payload_index(
            collection_name=collection_name,
            field_name="knowledge",
            field_schema=models.TextIndexParams(
                type="text",
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                max_token_len=500,
                lowercase=True
            )
        )
        logger.info("Индекс для поля 'knowledge' создан")

        client.create_payload_index(
            collection_name=collection_name,
            field_name="title",
            field_schema=models.TextIndexParams(
                type="text",
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                max_token_len=200,
                lowercase=True
            )
        )
        logger.info("Индекс для поля 'title' создан")

        client.create_payload_index(
            collection_name=collection_name,
            field_name="source",
            field_schema=models.TextIndexParams(
                type="text",
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                max_token_len=100,
                lowercase=True
            )
        )
        logger.info("Индекс для поля 'source' создан")

        client.create_payload_index(
            collection_name=collection_name,
            field_name="id",
            field_schema=models.PayloadSchemaType.INTEGER
        )
        logger.info("Индекс для поля 'id' создан")

    except Exception as e:
        logger.error("Ошибка при настройке коллекции '%s': %s", collection_name, e)


def setup_long_term_memory(client: QdrantClient, collection_name: str) -> None:
    """Create the long-term memory collection using dense embeddings only.

    Args:
        client: Connected Qdrant client.
        collection_name: Name of the collection for long-term memory.

    Returns:
        None. The function creates or recreates the target collection.
    """


    try:
        collections_response = client.get_collections()
        existing_collections = [c.name for c in collections_response.collections]

        if collection_name not in existing_collections:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VECTOR_PARAMS,
                quantization_config=models.ScalarQuantization(
                    scalar=models.ScalarQuantizationConfig(
                        type=models.ScalarType.INT8,
                        always_ram=True
                    )
                ),
                hnsw_config=models.HnswConfigDiff(m=16, ef_construct=100)
            )
            logger.info("Коллекция '%s' успешно создана", collection_name)
        else:
            logger.info("Коллекция '%s' уже существует", collection_name)

        logger.info("Настройка индексов для коллекции '%s'", collection_name)

        client.create_payload_index(
            collection_name=collection_name,
            field_name="knowledge",
            field_schema=models.TextIndexParams(
                type="text",
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                max_token_len=500,
                lowercase=True
            )
        )
        logger.info("Индекс для поля 'knowledge' создан")
        client.create_payload_index(
            collection_name=collection_name,
            field_name="title",
            field_schema=models.TextIndexParams(
                type="text",
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                max_token_len=200,
                lowercase=True
            )
        )
        logger.info("Индекс для поля 'title' создан")
        client.create_payload_index(
            collection_name=collection_name,
            field_name="user_id",
            field_schema=models.PayloadSchemaType.INTEGER
        )
        logger.info("Индекс для поля 'user_id' создан")

        client.create_payload_index(
            collection_name=collection_name,
            field_name="id",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        logger.info("Индекс для поля 'id' создан")

    except Exception as e:
        logger.error("Ошибка при настройке коллекции '%s': %s", collection_name, e)


def download_to_base() -> None:
    """Load data from ``base.csv`` and populate the knowledge base.

    Returns:
        None. Populates the KB and logs progress.
    """


    dense_encoder = load_deeppavlov_bert()
    logger.info("Loading data and initializing dense encoder...")
    excel_file_path = "ai_assistant/agent_system/service/base.csv"
    try:
        df = pd.read_csv(excel_file_path, dtype=str)
        df.fillna("", inplace=True)
    except FileNotFoundError:
        logger.error(f"Excel file not found at: {excel_file_path}")
        return
    except Exception as exc:
        logger.error("Failed to load base.csv: %s", exc)
        return

    if len(df.columns) < 2:
        logger.error("base.csv must contain at least two columns (title, knowledge).")
        return

    title_col, knowledge_col = df.columns[:2]
    df[title_col] = df[title_col].astype(str).str.strip()
    df[knowledge_col] = df[knowledge_col].astype(str).str.strip()

    controller = RetrieverController(
        client=client,
        dense_encoder=dense_encoder,
    )

    logger.warning("Clearing the knowledge base before population.")
    controller.clear_knowledge_base()

    documents_to_add = []
    for _, row in df.iterrows():
        knowledge = str(row.get(knowledge_col, "")).strip()
        title = str(row.get(title_col, "")).strip()
        if not knowledge:
            continue
        documents_to_add.append(
            {
                "knowledge": knowledge,
                "title": title or knowledge[:120],
            }
        )

    if documents_to_add:
        total_docs = len(documents_to_add)
        batch_size = 20
        logger.info(f"Adding {total_docs} documents to the knowledge base in batches of {batch_size}.")

        batch_iter = range(0, total_docs, batch_size)
        total_batches = (total_docs + batch_size - 1) // batch_size
        for start in tqdm(batch_iter, total=total_batches, desc="Uploading to Qdrant", disable=total_docs == 0):
            batch = documents_to_add[start:start + batch_size]
            controller.add_to_knowledge_base(documents=batch, source="BuisnessKnowledge")

        logger.info("Knowledge base population complete.")


if __name__ == "__main__":

    try:
        client = QdrantClient(host="localhost", port=6333, timeout=3600.0)
        client.get_collections()
        logger.info("Успешное подключение к Qdrant")
    except Exception as e:
        logger.error("Не удалось подключиться к Qdrant: %s", e)
        exit(1)

    logger.info("Запуск процесса создания/обновления коллекций в Qdrant")
    setup_knowledge_base(client=client, collection_name=KNOWLEDGE_BASE_COLLECTION)
    setup_long_term_memory(client=client, collection_name=LONG_TERM_MEMORY_COLLECTION)
    download_to_base()
    logger.info("Знания загружены в Qdrant")
    logger.info("Процесс завершен")
