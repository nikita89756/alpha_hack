"""FastAPI-приложение для Support Hints Agent System с интеграцией Kafka.

Модуль объединяет логику Support Hints Agent System и Contract Analysis System
с инфраструктурой Kafka/MongoDB. Обеспечивает асинхронную обработку сообщений
через шину данных с маршрутизацией по типу чата.

Атрибуты:
    interview_session (InterviewSession | None): Глобальный экземпляр для управления сессиями.
    contract_system (ContractAnalysisSystem | None): Система анализа контрактов.
    retriever_controller (RetrieverController | None): Контроллер операций поиска.
    memory_controller (MemoryController | None): Контроллер управления памятью.
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Sequence

import dotenv
from bson import ObjectId, errors as bson_errors
from confluent_kafka import Consumer, KafkaError, Producer
from fastapi import FastAPI, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient
from qdrant_client import QdrantClient

from ai_assistant.agent_system.app import InterviewSession
from ai_assistant.agent_system.memory import MemoryController
from ai_assistant.agent_system.rag import BertSentenceEncoder, RetrieverController
from ai_assistant.agent_system.utils.llm_client import AsyncLLMClient
from ai_assistant.agent_system.utils.model_loader import load_deeppavlov_bert
from contract_analysis.system import ContractAnalysisSystem
from web.config import InferenceConfig
from web.shemas import (
    AnswerRequest,
    AnswerResponse,
    ContractAnalysisRequest,
    ContractAnalysisResponse,
    ContractContextItem,
    ContractContextPayload,
    ContractIntentPayload,
    KnowledgeUploadRequest,
    KnowledgeUploadResponse,
    MemorizeRequest,
    OnboardingPayload,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

dotenv.load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "chatbot_db")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_INPUT_TOPIC = os.getenv("KAFKA_INPUT_TOPIC", "chat-messages")
KAFKA_OUTPUT_TOPIC = os.getenv("KAFKA_OUTPUT_TOPIC", "bot-responses")

interview_session: InterviewSession | None = None
contract_system: ContractAnalysisSystem | None = None
retriever_controller: RetrieverController | None = None
memory_controller: MemoryController | None = None

mongo_client: AsyncIOMotorClient | None = None
db: Any = None
messages_collection: Any = None
business_collection: Any = None
kafka_producer: Producer | None = None


def _env_bool(key: str, default: bool = False) -> bool:
    """Вернуть булево значение для флага окружения."""
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(key: str, default: int) -> int:
    """Безопасно считать целочисленное значение из переменной окружения."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Некорректное целое для %s='%s'. Используется значение по умолчанию %d.", key, raw, default)
        return default


def _build_qdrant_client() -> QdrantClient:
    """Создать экземпляр клиента Qdrant из переменных окружения."""
    api_key = os.getenv("QDRANT_API_KEY")
    prefer_grpc = _env_bool("QDRANT_PREFER_GRPC", False)
    url = os.getenv("QDRANT_URL")
    if url:
        logger.info("Подключение к Qdrant по URL %s", url)
        return QdrantClient(url=url, api_key=api_key, prefer_grpc=prefer_grpc)

    host = os.getenv("QDRANT_HOST", "localhost")
    port = _env_int("QDRANT_PORT", 6333)
    grpc_port = os.getenv("QDRANT_GRPC_PORT")
    client_kwargs: Dict[str, object] = {
        "host": host,
        "port": port,
        "prefer_grpc": prefer_grpc,
    }
    if api_key:
        client_kwargs["api_key"] = api_key
    if grpc_port:
        client_kwargs["grpc_port"] = _env_int("QDRANT_GRPC_PORT", 6334)

    logger.info("Подключение к Qdrant host=%s port=%s", host, port)
    return QdrantClient(**client_kwargs)


def _build_retriever_controller() -> RetrieverController:
    """Создать RetrieverController с плотным энкодером."""
    client = _build_qdrant_client()
    kb_collection = os.getenv("QDRANT_KB_COLLECTION", "knowledge_base")
    ltm_collection = os.getenv("QDRANT_LTM_COLLECTION", "long_term_memory")

    logger.info("Загрузка чекпойнта энкодера для retriever...")
    model, tokenizer = load_deeppavlov_bert()
    dense_encoder = BertSentenceEncoder((model, tokenizer))

    controller = RetrieverController(
        client=client,
        dense_encoder=dense_encoder,
    )
    controller.kb_collection = kb_collection
    controller.ltm_collection = ltm_collection
    return controller


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Инициализирует общие зависимости при старте приложения.

    Аргументы:
        app (FastAPI): Текущий экземпляр FastAPI (не используется, требуется интерфейсом).

    Возвращает:
        None: Управление возвращается в событийный цикл после инициализации.

    Исключения:
        ValueError: Отсутствует необходимый ключ OpenRouter.
        HTTPException: Не удалось создать контроллеры или сессию.
    """
    global mongo_client, db, messages_collection, business_collection, kafka_producer
    global interview_session, contract_system, retriever_controller, memory_controller

    OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
    if OPENROUTER_KEY is None:
        raise ValueError("API-ключ OpenRouter не найден в переменных окружения")

    llm = AsyncLLMClient(
        api_key=OPENROUTER_KEY,
        base_url=InferenceConfig.OPENROUTER_BASE,
        model=InferenceConfig.OPENROUTER_MODEL,
        timeout=InferenceConfig.TIMEOUT,
    )

    logger.info("Инициализация RetrieverController...")
    try:
        retriever = _build_retriever_controller()
        logger.info("RetrieverController успешно инициализирован")
    except Exception as e:
        logger.error(f"Ошибка инициализации RetrieverController: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка инициализации RetrieverController: {str(e)}"
        )

    logger.info("Инициализация MemoryController...")
    try:
        memory = MemoryController(
            api_key=OPENROUTER_KEY,
            base_url=os.getenv("OPENROUTER_CHAT_BASE", "https://openrouter.ai/api/v1"),
            model=InferenceConfig.OPENROUTER_MODEL,
            rag_controller=retriever,
        )
        logger.info("MemoryController успешно инициализирован")
    except Exception as e:
        logger.error(f"Ошибка инициализации MemoryController: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка инициализации MemoryController: {str(e)}"
        )

    try:
        interview_session = InterviewSession(
            llm=llm,
            retriever=retriever,
        )
        contract_system = ContractAnalysisSystem(
            llm_for_agents=llm,
            retriever=retriever,
        )
        retriever_controller = retriever
        memory_controller = memory
        logger.info("Инициализация AI-компонентов завершена успешно")
    except Exception as e:
        logger.error(f"Ошибка инициализации AI-компонентов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка инициализации AI-компонентов: {str(e)}"
        )

    logger.info("Подключение к MongoDB...")
    mongo_client = AsyncIOMotorClient(MONGODB_URL)
    db = mongo_client[DB_NAME]
    messages_collection = db["messages"]
    business_collection = db["businesses"]

    logger.info("Инициализация Kafka producer...")
    producer_config = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'bot-service-producer',
        'acks': 'all'
    }
    kafka_producer = Producer(producer_config)

    logger.info("Запуск Kafka consumer task...")
    consumer_task = asyncio.create_task(consume_messages())

    logger.info("Инициализация приложения завершена успешно")
    yield

    logger.info("Завершение работы приложения...")
    consumer_task.cancel()
    if kafka_producer:
        kafka_producer.flush()
    if mongo_client:
        mongo_client.close()
    logger.info("Очистка ресурсов завершена.")


app = FastAPI(
    title="Support Hints Agent System (Kafka Integrated)",
    description="API для управления работой retrieval workflow агентной системы с интеграцией Kafka.",
    version="1.1.0",
    lifespan=lifespan,
)


async def get_chat_history(chat_id: str, limit: int = 20) -> List[Dict[str, str]]:
    """Получить историю чата из MongoDB.
    
    Аргументы:
        chat_id (str): Идентификатор чата.
        limit (int): Максимальное количество сообщений.
        
    Возвращает:
        List[Dict[str, str]]: История сообщений в формате [{role, content}].
    """
    try:
        cursor = messages_collection.find(
            {"chat_id": chat_id}
        ).sort("timestamp", -1).limit(limit)

        messages = await cursor.to_list(length=limit)
        messages.reverse()

        history = []
        for msg in messages:
            role = "assistant" if msg.get("message_type") == "bot" else "user"
            history.append({
                "role": role,
                "content": msg.get("message", "")
            })
        return history
    except Exception as e:
        logger.error(f"Ошибка получения истории для {chat_id}: {e}")
        return []


async def get_business_context_from_db(business_id: str) -> str:
    """Получить контекст бизнеса из MongoDB по ObjectId.
    
    Аргументы:
        business_id (str): Идентификатор бизнеса.
        
    Возвращает:
        str: Текстовое описание бизнеса или пустая строка.
    """
    if not business_id:
        return ""

    try:
        oid = ObjectId(business_id)
        doc = await business_collection.find_one({"_id": oid})
        
        if doc:
            name = doc.get('name', 'Unknown Business')
            desc = doc.get('description', 'No description provided')
            industry = doc.get('industry', 'General')
            
            info = (
                f"Business Name: {name}. "
                f"Industry: {industry}. "
                f"Description: {desc}"
            )
            logger.info(f"Найден контекст бизнеса для {business_id}: {name}")
            return info
            
        logger.warning(f"Документ бизнеса не найден для id: {business_id}")
        return ""

    except bson_errors.InvalidId:
        logger.error(f"Некорректный формат ObjectId: {business_id}")
        return ""
    except Exception as e:
        logger.error(f"Ошибка получения данных бизнеса для {business_id}: {e}")
        return ""


async def generate_support_answer(
    user_message: str,
    chat_id: str,
    user_id: str,
    business_id: str
) -> Dict[str, Any]:
    """Генерирует ответ поддержки через InterviewSession.
    
    Аргументы:
        user_message (str): Сообщение пользователя.
        chat_id (str): Идентификатор чата.
        user_id (str): Идентификатор пользователя.
        business_id (str): Идентификатор бизнеса.
        
    Возвращает:
        Dict[str, Any]: Словарь с answer, next_action, user_id_used.
    """
    if interview_session is None:
        logger.error("Interview session не инициализирован.")
        return {"answer": "Система временно недоступна.", "next_action": "continue"}

    try:
        business_context = ""
        if business_id:
            business_context = await get_business_context_from_db(business_id)

        if business_context:
            full_query = (
                f"ИНФОРМАЦИЯ О БИЗНЕСЕ:\n{business_context}\n\n"
                f"СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:\n{user_message}"
            )
        else:
            full_query = user_message

        history = await get_chat_history(chat_id)
        unique_user_id = f"{user_id}-{business_id}" if business_id else str(user_id)

        result = await interview_session.run(
            query=full_query,
            history=history,
            user_id=unique_user_id,
        )

        final_text = result.get("final") or result.get("answer") or ""
        source=result.get("context_source", "llm-only"),
        source_links=result.get("source_links", []),
        if not final_text:
            final_text = "Не удалось сгенерировать ответ."

        exit_detected = bool(result.get("exit"))
        next_action = "exit" if exit_detected else "continue"

        return {"answer": final_text,"source": source,"source_links":source_links, "next_action": next_action, "user_id_used": unique_user_id}

    except Exception as e:
        logger.error(f"Ошибка генерации ответа для {chat_id}: {e}", exc_info=True)
        return {"answer": "Произошла ошибка.", "next_action": "continue"}


async def run_contract_analysis(
    request: ContractAnalysisRequest,
) -> ContractAnalysisResponse:
    """Запускает пайплайн contract_analysis и формирует ContractAnalysisResponse."""

    if contract_system is None:
        error_msg = "Contract analysis pipeline не инициализирован."
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_msg,
        )

    try:
        logger.info(
            "Обработка запроса анализа контракта для user_id=%s (история=%d)",
            request.user_id,
            len(request.history),
        )

        result = await contract_system.run(
            request=request.request,
            user_id=request.user_id,
            history=request.history,
        )

        intent_raw = result.get("intent") or {}
        raw_requirements = intent_raw.get("key_requirements") or []
        if isinstance(raw_requirements, (str, int, float)):
            normalized_requirements = [str(raw_requirements)]
        elif isinstance(raw_requirements, Sequence):
            normalized_requirements = [
                str(item) for item in raw_requirements if str(item).strip()
            ]
        else:
            normalized_requirements = []

        action_value = str(intent_raw.get("action") or "analyze").lower()
        if action_value not in {"analyze", "draft"}:
            action_value = "analyze"
        raw_section = intent_raw.get("raw")
        raw_payload = raw_section if isinstance(raw_section, dict) else None

        intent_model = ContractIntentPayload(
            action=action_value,
            document_type=intent_raw.get("document_type") or "",
            key_requirements=normalized_requirements,
            notes=intent_raw.get("notes") or "",
            raw=raw_payload,
        )

        context_raw = result.get("context") or {}
        context_items_raw = context_raw.get("items") or []
        context_items: List[ContractContextItem] = []
        for item in context_items_raw:
            if not isinstance(item, dict):
                continue
            context_items.append(
                ContractContextItem(
                    id=item.get("id"),
                    title=item.get("title") or "",
                    knowledge=item.get("knowledge") or "",
                    source=item.get("source"),
                    score=item.get("score"),
                )
            )

        context_model = ContractContextPayload(
            source=context_raw.get("source") or "",
            strategy=context_raw.get("strategy") or "",
            notes=context_raw.get("notes") or "",
            items=context_items,
        )

        return ContractAnalysisResponse(
            intent=intent_model,
            context=context_model,
            result=result.get("result") or "",
            disclaimer=result.get("disclaimer") or "",
        )

    except Exception as exc:
        error_msg = f"Contract analysis pipeline ошибка: {exc}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from exc



async def memorize_conversation(chat_id: str, user_id: str) -> None:
    """Извлечь и сохранить знания из завершенного разговора.
    
    Аргументы:
        chat_id (str): Идентификатор чата.
        user_id (str): Идентификатор пользователя.
    """
    if memory_controller is None:
        logger.warning(f"Memory controller отсутствует для {chat_id}")
        return

    try:
        dialogue_history = await get_chat_history(chat_id, limit=20)
        if len(dialogue_history) < 2:
            return

        logger.info(f"Сохранение диалога для пользователя {user_id} в чате {chat_id}")
        
        items = await asyncio.to_thread(
            memory_controller.extract_and_validate,
            dialogue_history,
            user_id=user_id,
        )
        logger.info(f"Memory controller сохранил {len(items)} элементов для {user_id}")

    except Exception as e:
        logger.error(f"Ошибка сохранения диалога для {chat_id}: {e}", exc_info=True)


async def process_message(message_data: dict) -> None:
    """Обработать входящее сообщение Kafka с маршрутизацией по chat_type.
    
    Аргументы:
        message_data (dict): Данные сообщения из Kafka.
    """
    try:
        user_message = message_data.get("message")
        chat_id = message_data.get("chat_id")
        user_id = message_data.get("user_id")
        business_id = message_data.get("business_id")
        message_id = message_data.get("message_id")
        chat_type = message_data.get("chat_type", "support")
        
        if not all([user_message, chat_id, user_id]):
            logger.error(f"Некорректные данные сообщения: {message_data}")
            return

        logger.info(f"Обработка сообщения типа '{chat_type}' от {user_id} в {chat_id}")

        response_data = {}
        
        if chat_type == "contract":
            try:
                unique_user_id = f"{user_id}-{business_id}" if business_id else str(user_id)
                
                history = await get_chat_history(chat_id)
                print(user_message)
                if len(history) >0:
                    history = history[1:]
                request_model = ContractAnalysisRequest(
                    request=user_message,
                    user_id=unique_user_id,
                    history=history
                )
                
                analysis_result = await run_contract_analysis(request_model)
                print(analysis_result)
                final_text = analysis_result.result
                if not final_text:
                    final_text = "Анализ завершен, но текстовый результат пуст."

                if analysis_result.disclaimer:
                    final_text += f"\n\n_{analysis_result.disclaimer}_"

                response_data = {
                    "answer": final_text,
                    "next_action": "continue",
                    "user_id_used": unique_user_id
                }

            except HTTPException as e:
                logger.error(f"HTTP ошибка в логике контракта: {e.detail}")
                response_data = {
                    "answer": f"Ошибка анализа контракта: {e.detail}", 
                    "next_action": "continue",
                    "user_id_used": unique_user_id
                }
            except Exception as e:
                logger.error(f"Непредвиденная ошибка в логике контракта: {e}", exc_info=True)
                response_data = {
                    "answer": "Произошла внутренняя ошибка при обработке контракта.", 
                    "next_action": "continue",
                    "user_id_used": unique_user_id
                }
            
        else:
            response_data = await generate_support_answer(user_message, chat_id, user_id, business_id)


        bot_text = response_data.get("answer", "")
        source = response_data.get("source","")
        source_links = response_data.get("source_links",[])
        next_action = response_data.get("next_action", "continue")
        unique_user_id = response_data.get("user_id_used", user_id)


        bot_msg_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        await messages_collection.insert_one({
            "id": bot_msg_id,
            "user_id": "bot",
            "chat_id": chat_id,
            "source": source,
            "source_links": source_links,
            "message": bot_text,
            "message_type": "bot",
            "chat_type": chat_type,
            "timestamp": timestamp,
            "status": "sent",
            "in_reply_to": message_id
        })


        kafka_payload = {
            "message_id": bot_msg_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "source": source,
            "source_links": source_links,
            "bot_response": bot_text,
            "chat_type": chat_type,
            "timestamp": timestamp.isoformat(),
            "type": "bot_response",
            "next_action": next_action
        }
        
        if kafka_producer:
            kafka_producer.produce(
                KAFKA_OUTPUT_TOPIC,
                key=chat_id.encode('utf-8'),
                value=json.dumps(kafka_payload).encode('utf-8'),
                headers=[('chat_type', chat_type.encode('utf-8'))]
            )
            kafka_producer.poll(0)


        if next_action == "exit" and chat_type == "support":
            asyncio.create_task(memorize_conversation(chat_id, unique_user_id))


    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)


async def consume_messages() -> None:
    """Фоновая задача для потребления сообщений из Kafka."""
    consumer_config = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'bot-service-group',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True
    }
    consumer = Consumer(consumer_config)
    consumer.subscribe([KAFKA_INPUT_TOPIC])
    logger.info(f"Kafka Consumer подписан на {KAFKA_INPUT_TOPIC}")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue

            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.error(f"Ошибка Kafka: {msg.error()}")
                continue

            try:
                data = json.loads(msg.value().decode('utf-8'))
                print(data)
                await process_message(data)
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")

    except asyncio.CancelledError:
        logger.info("Kafka consumer task отменена.")
    finally:
        consumer.close()


@app.post("/answer", response_model=AnswerResponse)
async def answer(request: AnswerRequest) -> AnswerResponse:
    """Генерирует ответ на запрос пользователя через агентный конвейер.

    Аргументы:
        request (AnswerRequest): Тело запроса c текстом пользователя, историей и ID.

    Возвращает:
        AnswerResponse: Финальный ответ, контекст и флаг продолжения диалога.

    Исключения:
        HTTPException: Возникает при отсутствии сессии или внутренних ошибках.
    """
    if interview_session is None:
        error_msg = "Interview session не инициализирован. Система может быть в процессе запуска."
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_msg
        )

    try:
        logger.info(f"Обработка запроса на ответ для пользователя: {request.user_id}")
        logger.info(f"Запрос: {request.query[:100]}...")

        history: List[Dict[str, str]] = list(request.history)
        query: str = request.query
        user_id: int = request.user_id

        result = await interview_session.run(
            query=query,
            history=history,
            user_id=user_id,
        )

        final_text = result.get("final") or result.get("answer") or ""
        kb_items = result.get("kb") or []
        ltm_items = result.get("ltm") or []
        logger.debug(f"Длина сгенерированного ответа: {len(final_text)} символов")

        exit_detected = bool(result.get("exit"))
        next_action = "exit" if exit_detected else "continue"
        logger.debug(f"Следующее действие: {next_action}")

        return AnswerResponse(
            answer=final_text,
            next_action=next_action,
            source=result.get("context_source", "llm-only"),
            source_links=result.get("source_links", []),
            kb=kb_items,
            ltm=ltm_items,
        )

    except Exception as e:
        error_msg = f"Ошибка генерации ответа: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        ) from e


@app.post("/contract/analyze", response_model=ContractAnalysisResponse)
async def analyze_contract(request: ContractAnalysisRequest) -> ContractAnalysisResponse:
    """Запускает пайплайн contract_analysis и возвращает структуру с намерением и контекстом.
    
    Аргументы:
        request (ContractAnalysisRequest): Запрос на анализ контракта.
        
    Возвращает:
        ContractAnalysisResponse: Результат анализа контракта.
        
    Исключения:
        HTTPException: Возникает при отсутствии системы или внутренних ошибках.
    """
    if contract_system is None:
        error_msg = "Contract analysis pipeline не инициализирован."
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_msg,
        )

    try:
        logger.info(
            "Обработка запроса анализа контракта для user_id=%s (история=%d)",
            request.user_id,
            len(request.history),
        )
        result = await contract_system.run(
            request=request.request,
            user_id=request.user_id,
            history=request.history,
        )

        intent_raw = result.get("intent") or {}
        raw_requirements = intent_raw.get("key_requirements") or []
        if isinstance(raw_requirements, (str, int, float)):
            normalized_requirements = [str(raw_requirements)]
        elif isinstance(raw_requirements, Sequence):
            normalized_requirements = [str(item) for item in raw_requirements if str(item).strip()]
        else:
            normalized_requirements = []

        action_value = str(intent_raw.get("action") or "analyze").lower()
        if action_value not in {"analyze", "draft"}:
            action_value = "analyze"
        raw_section = intent_raw.get("raw")
        raw_payload = raw_section if isinstance(raw_section, dict) else None

        intent_model = ContractIntentPayload(
            action=action_value,
            document_type=intent_raw.get("document_type") or "",
            key_requirements=normalized_requirements,
            notes=intent_raw.get("notes") or "",
            raw=raw_payload,
        )

        context_raw = result.get("context") or {}
        context_items_raw = context_raw.get("items") or []
        context_items: List[ContractContextItem] = []
        for item in context_items_raw:
            if not isinstance(item, dict):
                continue
            context_items.append(
                ContractContextItem(
                    id=item.get("id"),
                    title=item.get("title") or "",
                    knowledge=item.get("knowledge") or "",
                    source=item.get("source"),
                    score=item.get("score"),
                )
            )

        context_model = ContractContextPayload(
            source=context_raw.get("source") or "",
            strategy=context_raw.get("strategy") or "",
            notes=context_raw.get("notes") or "",
            items=context_items,
        )

        return ContractAnalysisResponse(
            intent=intent_model,
            context=context_model,
            result=result.get("result") or "",
            disclaimer=result.get("disclaimer") or "",
        )
    except Exception as exc:
        error_msg = f"Contract analysis pipeline ошибка: {exc}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from exc


@app.post("/memory/memorize")
async def memorize(request: MemorizeRequest) -> Dict[str, object]:
    """Извлекает факты из диалога и сохраняет их в долговременную память.
    
    Аргументы:
        request (MemorizeRequest): Запрос с диалогом для сохранения.
        
    Возвращает:
        Dict[str, object]: Количество сохраненных элементов и их список.
        
    Исключения:
        HTTPException: Возникает при отсутствии контроллера или внутренних ошибках.
    """
    if memory_controller is None or retriever_controller is None:
        error_msg = "Memory controller не инициализирован. Система может быть в процессе запуска."
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_msg,
        )

    dialogue_payload: List[Dict[str, str]] = [
        {"role": msg.role, "content": msg.content}
        for msg in request.dialogue
    ]
    user_id = request.user_id or "999"

    try:
        logger.info("Обработка memorize-запроса для user_id=%s (сообщений=%d)", user_id, len(dialogue_payload))
        items = await asyncio.to_thread(
            memory_controller.extract_and_validate,
            dialogue_payload,
            user_id=user_id,
        )
        stored = [item.model_dump() for item in items]
        logger.info("Memory controller сохранил %d фрагментов для user_id=%s", len(stored), user_id)
        return {"inserted": len(stored), "items": stored}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Ошибка при сохранении диалога: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from e


@app.post("/knowledge/upload", response_model=KnowledgeUploadResponse)
async def upload_knowledge(request: KnowledgeUploadRequest) -> KnowledgeUploadResponse:
    """Загрузить внешние документы в базу знаний.
    
    Аргументы:
        request (KnowledgeUploadRequest): Запрос с документами для загрузки.
        
    Возвращает:
        KnowledgeUploadResponse: Результат загрузки документов.
        
    Исключения:
        HTTPException: Возникает при отсутствии контроллера или внутренних ошибках.
    """
    if retriever_controller is None:
        raise HTTPException(status_code=503, detail="RetrieverController не инициализирован.")

    if not request.documents:
        raise HTTPException(status_code=400, detail="Список документов не может быть пустым.")

    try:
        documents_payload = [doc.model_dump(exclude_none=True) for doc in request.documents]
        retriever_controller.add_to_knowledge_base(
            documents=documents_payload,
            source=request.source,
        )
        msg = f"Загружено {len(documents_payload)} документов из '{request.source}'."
        return KnowledgeUploadResponse(
            source=request.source,
            imported=len(documents_payload),
            message=msg,
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/onboarding/complete",
    tags=["Onboarding"],
    status_code=status.HTTP_201_CREATED,
    summary="Сохранение данных онбординга пользователя"
)
def handle_complete_onboarding(payload: OnboardingPayload) -> Dict[str, str]:
    """Сохранить данные онбординга в базу знаний.
    
    Аргументы:
        payload (OnboardingPayload): Данные онбординга пользователя.
        
    Возвращает:
        Dict[str, str]: Статус операции.
        
    Исключения:
        HTTPException: Возникает при отсутствии контроллера или внутренних ошибках.
    """
    if retriever_controller is None:
        raise HTTPException(status_code=503, detail="RetrieverController не инициализирован.")

    unique_id = payload.user_id + "-" + payload.business_id
    retriever_controller.save_complete_onboarding(
        user_id=unique_id,
        business_goals=payload.business_goals,
        business_description=payload.business_description,
        daily_tasks=payload.daily_tasks,
        daily_routine_description=payload.daily_routine_description,
        business_type=payload.business_type,
        business_name=payload.business_name,
        city=payload.city,
        primary_pain_point=payload.primary_pain_point,
        pain_description=payload.pain_description,
    )
    
    return {
        "status": "success",
        "message": f"Данные онбординга для пользователя '{payload.user_id}' успешно сохранены."
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Проверить состояние системы.
    
    Возвращает:
        Dict[str, Any]: Статус здоровья компонентов системы.
    """
    status_map = {
        "mongodb": mongo_client is not None,
        "kafka": kafka_producer is not None,
        "ai_session": interview_session is not None,
        "contract_system": contract_system is not None,
    }
    is_healthy = all(status_map.values())
    return {
        "status": "healthy" if is_healthy else "degraded",
        "components": status_map
    }
