from fastapi import FastAPI, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from confluent_kafka import Producer
from redis.asyncio import Redis
import json
import os
import uuid

app = FastAPI(title="Message Service")

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "chatbot_db")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "chat-messages")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
REDIS_HISTORY_MAX_MESSAGES = int(os.getenv("REDIS_HISTORY_MAX_MESSAGES", "200"))
REDIS_HISTORY_TTL_SECONDS = int(os.getenv("REDIS_HISTORY_TTL_SECONDS", str(7 * 24 * 3600)))

def _chat_messages_key(chat_id: str) -> str:
    return f"chat:{chat_id}:messages"

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]
messages_collection = db["messages"]
chats_collection = db["chats"]  
folders_collection = db["folders"] 

redis: Redis | None = None

producer_config = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'message-service',
    'acks': 'all',
    'retries': 3,
    'max.in.flight.requests.per.connection': 5
}
kafka_producer = Producer(producer_config)

class CreateChatRequest(BaseModel):
    title: Optional[str] = Field(None, description="Название чата")
    folder_id: Optional[str] = Field(None, description="ID папки для чата")

class ChatResponse(BaseModel):
    chat_id: str
    user_id: str
    title: Optional[str]
    folder_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    is_active: bool = True

class CreateFolderRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Название папки")
    description: Optional[str] = Field(None, max_length=500, description="Описание папки")
    target_date: Optional[datetime] = Field(None, description="Целевая дата для папки")

class FolderResponse(BaseModel):
    folder_id: str
    user_id: str
    name: str
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    chat_count: int = 0
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

class UpdateFolderRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class MoveChatRequest(BaseModel):
    folder_id: Optional[str] = Field(None, description="ID папки для перемещения (None для корня)")

class MessageRequest(BaseModel):
    user_id: str
    chat_type: str
    message: str
    chat_id: str
    photo_description: Optional[str] = None
    photo_url: Optional[str] = None
    parsed_document: Optional[str] = None
    business_id: Optional[str] = None

class MessageResponse(BaseModel):
    message_id: str
    user_id: str
    chat_id: str
    message: str
    timestamp: datetime
    status: str
    bot_response: Optional[str] = None

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    chat_id: str
    chat_type: Optional[str] = None
    message: str
    message_type: str  # "user" or "bot"
    business_id: Optional[str] = None
    photo_description: Optional[str] = None
    photo_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "sent"
    parsed_document: Optional[str] = None

class Chat(BaseModel):
    chat_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: Optional[str] = None
    folder_id: Optional[str] = None  # ID папки
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None
    message_count: int = 0
    is_active: bool = True

class Folder(BaseModel):
    folder_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    chat_count: int = 0
    is_active: bool = True

@app.on_event("startup")
async def startup_event():
    """Создание индексов и инициализация Redis при запуске"""
    await messages_collection.create_index([("chat_id", 1), ("timestamp", -1)])
    await messages_collection.create_index([("user_id", 1)])
    await chats_collection.create_index([("chat_id", 1)], unique=True)
    await chats_collection.create_index([("user_id", 1), ("created_at", -1)])
    await chats_collection.create_index([("user_id", 1), ("folder_id", 1)])
    
    await folders_collection.create_index([("folder_id", 1)], unique=True)
    await folders_collection.create_index([("user_id", 1), ("created_at", -1)])
 
    global redis
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    await redis.ping()
    print("MongoDB indexes created, Redis ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Закрытие соединений"""
    kafka_producer.flush()
    client.close()
    if redis:
        await redis.close()

def delivery_report(err, msg):
    """Callback для отчета о доставке в Kafka"""
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

async def send_to_kafka(message_data: dict):
    """Отправка сообщения в Kafka"""
    try:
        kafka_producer.produce(
            KAFKA_TOPIC,
            key=message_data["chat_id"].encode('utf-8'),
            value=json.dumps(message_data).encode('utf-8'),
            callback=delivery_report
        )
        kafka_producer.poll(0)
    except Exception as e:
        print(f"Error sending to Kafka: {e}")
        raise

@app.post("/chats/create", response_model=ChatResponse, status_code=201)
async def create_chat(user_id: str, request: CreateChatRequest):
    """
    Создание нового чата для пользователя
    - **user_id**: ID пользователя
    - **title**: Опциональное название чата
    - **folder_id**: Опциональный ID папки для чата
    """

    if request.folder_id:
        folder = await folders_collection.find_one({
            "folder_id": request.folder_id,
            "user_id": user_id,
            "is_active": True
        })
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

    title = request.title
    if not title:
        chat_count = await chats_collection.count_documents({"user_id": user_id})
        title = f"Чат #{chat_count + 1}"

    chat = Chat(
        user_id=user_id,
        title=title,
        folder_id=request.folder_id
    )

    chat_dict = chat.model_dump()
    await chats_collection.insert_one(chat_dict)

    if request.folder_id:
        await folders_collection.update_one(
            {"folder_id": request.folder_id},
            {"$inc": {"chat_count": 1}}
        )

    print(f"Created chat {chat.chat_id} for user {user_id} in folder {request.folder_id}")

    welcome_message = Message(
        user_id=user_id,
        chat_id=chat.chat_id,
        message="Добро пожаловать в ИИ-Ассистента АльфаБанк для микробизнеса! Я ваш виртуальный помощник. Опишите ваш вопрос или проблему, и я помогу найти решение.",
        message_type="bot"
    )

    await messages_collection.insert_one(welcome_message.model_dump())

    await chats_collection.update_one(
        {"chat_id": chat.chat_id},
        {
            "$set": {
                "last_message_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            "$inc": {"message_count": 1}
        }
    )

    if redis:
        try:
            key = _chat_messages_key(chat.chat_id)
            welcome_for_cache = welcome_message.model_dump()
            if isinstance(welcome_for_cache.get("timestamp"), datetime):
                welcome_for_cache["timestamp"] = welcome_for_cache["timestamp"].isoformat()
            pipe = redis.pipeline()
            pipe.rpush(key, json.dumps(welcome_for_cache, ensure_ascii=False))
            pipe.ltrim(key, -REDIS_HISTORY_MAX_MESSAGES, -1)
            pipe.expire(key, REDIS_HISTORY_TTL_SECONDS)
            await pipe.execute()
        except Exception as e:
            print(f"Redis welcome cache error: {e}")

    print(f"Welcome message added to chat {chat.chat_id}")

    return ChatResponse(
        chat_id=chat.chat_id,
        user_id=chat.user_id,
        title=chat.title,
        folder_id=chat.folder_id,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=1,
        is_active=True
    )

@app.get("/chats/list", response_model=List[ChatResponse])
async def list_chats(user_id: str, limit: int = 20, skip: int = 0):
    """
    Получение списка всех чатов пользователя
    - **user_id**: ID пользователя
    - **limit**: Количество чатов (по умолчанию 20)
    - **skip**: Пропустить чатов (для пагинации)
    """
    chats = await chats_collection.find(
        {"user_id": user_id, "is_active": True}
    ).sort("updated_at", -1).skip(skip).limit(limit).to_list(length=limit)

    result = []
    for chat in chats:
        chat["_id"] = str(chat["_id"])
        result.append(ChatResponse(**chat))

    return result

@app.get("/chats/{chat_id}", response_model=ChatResponse)
async def get_chat(chat_id: str, user_id: str):
    """
    Получение информации о конкретном чате
    - **chat_id**: ID чата
    - **user_id**: ID пользователя (для проверки доступа)
    """
    chat = await chats_collection.find_one({
        "chat_id": chat_id,
        "user_id": user_id
    })

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat["_id"] = str(chat["_id"])
    return ChatResponse(**chat)

@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, user_id: str):
    """
    Удаление чата (мягкое удаление - устанавливает is_active=False)
    - **chat_id**: ID чата
    - **user_id**: ID пользователя
    """
    result = await chats_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {"status": "deleted", "chat_id": chat_id}

@app.post("/messages/send", response_model=MessageResponse)
async def send_message(request: MessageRequest, background_tasks: BackgroundTasks):
    """Обработка входящего сообщения от пользователя"""
    chat = await chats_collection.find_one({"chat_id": request.chat_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found. Create a chat first using /chats/create")

    user_message = Message(
        user_id=request.user_id,
        chat_id=request.chat_id,
        chat_type=request.chat_type,
        business_id=request.business_id,
        message=request.message,
        message_type="user",
        photo_url=request.photo_url,
        photo_description=request.photo_description,
        parsed_document=request.parsed_document
    )

    await messages_collection.insert_one(user_message.model_dump())
    await chats_collection.update_one(
        {"chat_id": request.chat_id},
        {
            "$set": {
                "last_message_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            "$inc": {"message_count": 1}
        }
    )

    if redis:
        try:
            key = _chat_messages_key(user_message.chat_id)
            msg_for_cache = {
                "id": user_message.id,
                "user_id": user_message.user_id,
                "chat_id": user_message.chat_id,
                "business_id": user_message.business_id,
                "message": user_message.message,
                "message_type": user_message.message_type,
                "photo_url": user_message.photo_url,
                "photo_description": user_message.photo_description,
                "timestamp": user_message.timestamp.isoformat(),
                "status": user_message.status,
                "parse_document": user_message.parse_document,
            }
            pipe = redis.pipeline()
            pipe.rpush(key, json.dumps(msg_for_cache, ensure_ascii=False))
            pipe.ltrim(key, -REDIS_HISTORY_MAX_MESSAGES, -1)
            pipe.expire(key, REDIS_HISTORY_TTL_SECONDS)
            await pipe.execute()
        except Exception as e:
            print(f"Redis cache error: {e}")

    message_data = {
        "message_id": user_message.id,
        "chat_type": user_message.chat_type,
        "user_id": user_message.user_id,
        "chat_id": user_message.chat_id,
        "business_id": user_message.business_id,
        "message": user_message.message,
        "timestamp": user_message.timestamp.isoformat()
    }
    if user_message.photo_description:
        message_data["message"] = message_data["message"] + f"\nОписание фото: {user_message.photo_description}"
    if user_message.parsed_document:
        message_data["message"] = message_data["message"] + f"\nДокумент: {user_message.parse_document}"

    background_tasks.add_task(send_to_kafka, message_data)

    return MessageResponse(
        message_id=user_message.id,
        user_id=user_message.user_id,
        chat_id=user_message.chat_id,
        message=user_message.message,
        timestamp=user_message.timestamp,
        status="processing"
    )

@app.get("/messages/history/{chat_id}")
async def get_message_history(chat_id: str, limit: int = 50):
    """Получение истории сообщений сессии"""
    messages = []

    key = _chat_messages_key(chat_id)

    if redis:
        try:
            raw_items = await redis.lrange(key, -limit, -1)
            if raw_items:
                messages = [json.loads(i) for i in raw_items]
        except Exception as e:
            print(f"Redis read error: {e}")

    if len(messages) < limit:
        mongo_msgs = await messages_collection.find(
            {"chat_id": chat_id}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)

        for m in mongo_msgs:
            m["_id"] = str(m["_id"])
            if isinstance(m.get("timestamp"), datetime):
                m["timestamp"] = m["timestamp"].isoformat()

        mongo_msgs.reverse()
        messages = mongo_msgs

        if redis:
            try:
                pipe = redis.pipeline()
                pipe.delete(key)
                for m in messages:
                    pipe.rpush(key, json.dumps(m, ensure_ascii=False))
                pipe.ltrim(key, -REDIS_HISTORY_MAX_MESSAGES, -1)
                pipe.expire(key, REDIS_HISTORY_TTL_SECONDS)
                await pipe.execute()
            except Exception as e:
                print(f"Redis warmup error: {e}")

    return {"chat_id": chat_id, "messages": messages, "count": len(messages)}

@app.get("/messages/{message_id}/export")
async def export_message(message_id: str, user_id: str, format: str = "md"):
    """
    Экспорт одного сообщения в удобном формате и скачивание как файл
    - **message_id**: ID сообщения
    - **user_id**: ID пользователя (для проверки доступа)
    - **format**: Формат экспорта: `md`, `json`, `txt`, `pdf` (по умолчанию `md`)
    """

    message = await messages_collection.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    chat = await chats_collection.find_one({"chat_id": message.get("chat_id"), "user_id": user_id})
    if not chat:
        raise HTTPException(status_code=403, detail="Access denied to this message")

    message["_id"] = str(message["_id"])
    if isinstance(message.get("timestamp"), datetime):
        message["timestamp"] = message["timestamp"].isoformat()

    fmt = format.lower()
    if fmt == "json":
        content = json.dumps({"message_id": message_id, "message": message}, ensure_ascii=False, indent=2)
        media_type = "application/json"
        ext = "json"
    elif fmt == "txt":
        role = message.get("message_type") or message.get("role") or "user"
        ts = message.get("timestamp", "")
        text = message.get("message") or message.get("content") or ""
        content = f"[{ts}] {role.upper()}: {text}"
        media_type = "text/plain; charset=utf-8"
        ext = "txt"
    elif fmt == "md":
        role = message.get("message_type") or message.get("role") or "user"
        ts = message.get("timestamp", "")
        text = message.get("message") or message.get("content") or ""
        content = f"# Сообщение\n\n**{role.title()}** — {ts}\n\n{text}"
        media_type = "text/markdown; charset=utf-8"
        ext = "md"
    elif fmt == "pdf":
        try:
            import io
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except Exception:
            raise HTTPException(status_code=501, detail="PDF export requires the 'reportlab' package to be installed on the server")

        font_name = "DejaVuSans"
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        except Exception:

            raise HTTPException(status_code=501, detail=f"PDF export requires the DejaVuSans TTF font at {font_path} to be installed in the container")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('ExportTitle', parent=styles.get('Title', styles['Normal']), fontName=font_name, fontSize=18)
        heading_style = ParagraphStyle('ExportHeading', parent=styles.get('Heading4', styles['Normal']), fontName=font_name, fontSize=12)
        body_style = ParagraphStyle('ExportBody', parent=styles.get('BodyText', styles['Normal']), fontName=font_name, fontSize=10)

        story = []
        story.append(Paragraph("Экспорт сообщения", title_style))
        story.append(Spacer(1, 12))
        
        role = message.get("message_type") or message.get("role") or "user"
        ts = message.get("timestamp", "")
        text = message.get("message") or message.get("content") or ""
        story.append(Paragraph(f"<b>{role.title()}</b> — {ts}", heading_style))

        story.append(Paragraph(text.replace('\n', '<br/>'), body_style))
        story.append(Spacer(1, 12))
        
        try:
            doc.build(story)
            buffer.seek(0)
            content = buffer.getvalue()
            buffer.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to build PDF: {e}")

        media_type = "application/pdf"
        ext = "pdf"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    from fastapi.responses import Response
    filename = f"message_{message_id}.{ext}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)


@app.post("/folders/create", response_model=FolderResponse, status_code=201)
async def create_folder(user_id: str, request: CreateFolderRequest):
    """
    Создание новой папки для пользователя
    - **user_id**: ID пользователя
    - **name**: Название папки
    - **description**: Описание папки (опционально)
    """

    existing_folder = await folders_collection.find_one({
        "user_id": user_id,
        "name": request.name,
        "is_active": True
    })
    if existing_folder:
        raise HTTPException(status_code=400, detail="Folder with this name already exists")

    folder = Folder(
        user_id=user_id,
        name=request.name,
        description=request.description,
        target_date=request.target_date
    )

    folder_dict = folder.model_dump()
    await folders_collection.insert_one(folder_dict)
    
    print(f"Created folder {folder.folder_id} for user {user_id}")
    
    return FolderResponse(
        folder_id=folder.folder_id,
        user_id=folder.user_id,
        name=folder.name,
        description=folder.description,
        target_date=folder.target_date,
        chat_count=0,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        is_active=True
    )

@app.get("/folders/list", response_model=List[FolderResponse])
async def list_folders(user_id: str, limit: int = 20, skip: int = 0):
    """
    Получение списка всех папок пользователя
    - **user_id**: ID пользователя
    - **limit**: Количество папок (по умолчанию 20)
    - **skip**: Пропустить папок (для пагинации)
    """
    folders = await folders_collection.find(
        {"user_id": user_id, "is_active": True}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)

    result = []
    for folder in folders:
        folder["_id"] = str(folder["_id"])
        result.append(FolderResponse(**folder))

    return result

@app.get("/folders/{folder_id}", response_model=FolderResponse)
async def get_folder(folder_id: str, user_id: str):
    """
    Получение информации о конкретной папке
    - **folder_id**: ID папки
    - **user_id**: ID пользователя (для проверки доступа)
    """
    folder = await folders_collection.find_one({
        "folder_id": folder_id,
        "user_id": user_id,
        "is_active": True
    })

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    folder["_id"] = str(folder["_id"])
    return FolderResponse(**folder)

@app.get("/folders/{folder_id}/chats", response_model=List[ChatResponse])
async def get_folder_chats(folder_id: str, user_id: str, limit: int = 20, skip: int = 0):
    """
    Получение всех чатов в папке
    - **folder_id**: ID папки
    - **user_id**: ID пользователя
    - **limit**: Количество чатов
    - **skip**: Пропустить чатов
    """

    folder = await folders_collection.find_one({
        "folder_id": folder_id,
        "user_id": user_id,
        "is_active": True
    })
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    chats = await chats_collection.find({
        "folder_id": folder_id,
        "user_id": user_id,
        "is_active": True
    }).sort("updated_at", -1).skip(skip).limit(limit).to_list(length=limit)

    result = []
    for chat in chats:
        chat["_id"] = str(chat["_id"])
        result.append(ChatResponse(**chat))

    return result

@app.put("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(folder_id: str, user_id: str, request: UpdateFolderRequest):
    """
    Обновление информации о папке
    - **folder_id**: ID папки
    - **user_id**: ID пользователя
    - **name**: Новое название папки (опционально)
    - **description**: Новое описание папки (опционально)
    """
    update_data = {}
    
    if request.name:
        existing_folder = await folders_collection.find_one({
            "user_id": user_id,
            "name": request.name,
            "folder_id": {"$ne": folder_id},
            "is_active": True
        })
        if existing_folder:
            raise HTTPException(status_code=400, detail="Folder with this name already exists")
        update_data["name"] = request.name
    
    if request.description is not None:
        update_data["description"] = request.description
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await folders_collection.update_one(
        {"folder_id": folder_id, "user_id": user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Folder not found")

    folder = await folders_collection.find_one({"folder_id": folder_id})
    folder["_id"] = str(folder["_id"])
    
    return FolderResponse(**folder)

@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, user_id: str):
    """
    Удаление папки (мягкое удаление - устанавливает is_active=False)
    Все чаты в папке остаются, но перемещаются в корень
    - **folder_id**: ID папки
    - **user_id**: ID пользователя
    """
    folder = await folders_collection.find_one({
        "folder_id": folder_id,
        "user_id": user_id
    })
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
 
    await chats_collection.update_many(
        {"folder_id": folder_id, "user_id": user_id},
        {"$set": {"folder_id": None, "updated_at": datetime.utcnow()}}
    )

    result = await folders_collection.update_one(
        {"folder_id": folder_id, "user_id": user_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Folder not found")

    return {"status": "deleted", "folder_id": folder_id}

@app.put("/chats/{chat_id}/move")
async def move_chat_to_folder(chat_id: str, user_id: str, request: MoveChatRequest):
    """
    Перемещение чата между папками или в корень
    - **chat_id**: ID чата для перемещения
    - **user_id**: ID пользователя
    - **folder_id**: ID папки назначения (None для перемещения в корень)
    """

    chat = await chats_collection.find_one({
        "chat_id": chat_id,
        "user_id": user_id
    })
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    old_folder_id = chat.get("folder_id")
    new_folder_id = request.folder_id

    if new_folder_id:
        folder = await folders_collection.find_one({
            "folder_id": new_folder_id,
            "user_id": user_id,
            "is_active": True
        })
        if not folder:
            raise HTTPException(status_code=404, detail="Target folder not found")

    await chats_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {
            "$set": {
                "folder_id": new_folder_id,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if old_folder_id:
        await folders_collection.update_one(
            {"folder_id": old_folder_id},
            {"$inc": {"chat_count": -1}}
        )
    
    if new_folder_id:
        await folders_collection.update_one(
            {"folder_id": new_folder_id},
            {"$inc": {"chat_count": 1}}
        )
    
    print(f"Moved chat {chat_id} from folder {old_folder_id} to {new_folder_id}")

    updated_chat = await chats_collection.find_one({"chat_id": chat_id})
    updated_chat["_id"] = str(updated_chat["_id"])
    
    return {
        "status": "moved",
        "chat_id": chat_id,
        "old_folder_id": old_folder_id,
        "new_folder_id": new_folder_id,
        "chat": ChatResponse(**updated_chat)
    }


@app.get("/chats/{chat_id}/export")
async def export_chat(chat_id: str, user_id: str, format: str = "md"):
    """
    Экспорт диалога в удобном формате и скачивание как файл
    - **chat_id**: ID чата
    - **user_id**: ID пользователя (для проверки доступа)
    - **format**: Формат экспорта: `md`, `json`, `txt` (по умолчанию `md`)
    """
    chat = await chats_collection.find_one({"chat_id": chat_id, "user_id": user_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    mongo_msgs = await messages_collection.find({"chat_id": chat_id}).sort("timestamp", 1).to_list(length=None)

    messages_out = []
    for m in mongo_msgs:
        m["_id"] = str(m["_id"])
        if isinstance(m.get("timestamp"), datetime):
            m["timestamp"] = m["timestamp"].isoformat()
        messages_out.append(m)

    fmt = format.lower()
    if fmt == "json":
        content = json.dumps({"chat_id": chat_id, "messages": messages_out}, ensure_ascii=False, indent=2)
        media_type = "application/json"
        ext = "json"
    elif fmt == "txt":
        parts = []
        for m in messages_out:
            role = m.get("message_type") or m.get("role") or "user"
            ts = m.get("timestamp", "")
            text = m.get("message") or m.get("content") or ""
            parts.append(f"[{ts}] {role.upper()}: {text}")
        content = "\n".join(parts)
        media_type = "text/plain; charset=utf-8"
        ext = "txt"
    elif fmt == "pdf":
        try:
            import io
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except Exception:
            raise HTTPException(status_code=501, detail="PDF export requires the 'reportlab' package to be installed on the server")

        font_name = "DejaVuSans"
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        except Exception:
            raise HTTPException(status_code=501, detail=f"PDF export requires the DejaVuSans TTF font at {font_path} to be installed in the container")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()

       
        title_style = ParagraphStyle('ExportTitle', parent=styles.get('Title', styles['Normal']), fontName=font_name, fontSize=18)
        heading_style = ParagraphStyle('ExportHeading', parent=styles.get('Heading4', styles['Normal']), fontName=font_name, fontSize=12)
        body_style = ParagraphStyle('ExportBody', parent=styles.get('BodyText', styles['Normal']), fontName=font_name, fontSize=10)

        story = []
        title = chat.get('title') or chat_id
        story.append(Paragraph(f"Chat export — {title}", title_style))
        story.append(Spacer(1, 12))
        for m in messages_out:
            role = m.get("message_type") or m.get("role") or "user"
            ts = m.get("timestamp", "")
            text = m.get("message") or m.get("content") or ""
            story.append(Paragraph(f"<b>{role.title()}</b> — {ts}", heading_style))

            story.append(Paragraph(text.replace('\n', '<br/>'), body_style))
            story.append(Spacer(1, 12))
        try:
            doc.build(story)
            buffer.seek(0)
            content = buffer.getvalue()
            buffer.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to build PDF: {e}")

        media_type = "application/pdf"
        ext = "pdf"


    from fastapi.responses import Response
    filename = f"chat_{chat_id}.{ext}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "message-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
