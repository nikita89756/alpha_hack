from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from confluent_kafka import Consumer, KafkaError
from typing import Dict, Set
import json
import asyncio
import os
import jwt
import httpx
from datetime import datetime

app = FastAPI(title="WebSocket Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_BOT_RESPONSE_TOPIC = os.getenv("KAFKA_BOT_RESPONSE_TOPIC", "bot-responses")
KAFKA_TITLE_TOPIC = os.getenv("KAFKA_TITLE_TOPIC", "chat_title_generated")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
MESSAGE_SERVICE_URL = os.getenv("MESSAGE_SERVICE_URL", "http://message-service:8001")
CHAT_AUTO_DELETE_DELAY = int(os.getenv("CHAT_AUTO_DELETE_DELAY", "15"))  

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, chat_id: str):
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        if chat_id not in self.active_connections[user_id]:
            self.active_connections[user_id][chat_id] = set()
        
        self.active_connections[user_id][chat_id].add(websocket)
        print(f"User {user_id} connected to chat {chat_id}")

    def disconnect(self, websocket: WebSocket, user_id: str, chat_id: str):
        if user_id in self.active_connections:
            if chat_id in self.active_connections[user_id]:
                self.active_connections[user_id][chat_id].discard(websocket)
                if not self.active_connections[user_id][chat_id]:
                    del self.active_connections[user_id][chat_id]
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        print(f"User {user_id} disconnected from chat {chat_id}")

    async def send_to_user_chat(self, message: dict, user_id: str, chat_id: str):
        """Отправка сообщения конкретному пользователю в конкретной сессии"""
        if user_id in self.active_connections:
            if chat_id in self.active_connections[user_id]:
                disconnected = set()
                for connection in self.active_connections[user_id][chat_id]:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        print(f"Error sending message: {e}")
                        disconnected.add(connection)
                
                for conn in disconnected:
                    self.active_connections[user_id][chat_id].discard(conn)

manager = ConnectionManager()

async def schedule_chat_deletion(chat_id: str, user_id: str, delay_seconds: int = CHAT_AUTO_DELETE_DELAY):
    """Удаление чата через заданное время"""
    await asyncio.sleep(delay_seconds)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{MESSAGE_SERVICE_URL}/chats/{chat_id}",
                params={"user_id": user_id},
                timeout=10.0
            )
            if response.status_code == 200:
                print(f"Chat {chat_id} deleted successfully after {delay_seconds} seconds")
            else:
                print(f"Failed to delete chat {chat_id}: {response.status_code}")
    except Exception as e:
        print(f"Error deleting chat {chat_id}: {e}")

def verify_ws_token(token: str) -> dict:
    """Верификация JWT токена для WebSocket"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {"user_id": user_id, "username": payload.get("username")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

consumer_config = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'ws-service-group',
    'auto.offset.reset': 'latest',
    'enable.auto.commit': True
}

async def consume_bot_responses():
    """Фоновая задача для чтения ответов бота из Kafka"""
    consumer = Consumer(consumer_config)
    consumer.subscribe([KAFKA_BOT_RESPONSE_TOPIC])
    
    print(f"Started consuming from {KAFKA_BOT_RESPONSE_TOPIC}")
    
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"Consumer error: {msg.error()}")
                    continue
            
            try:
                message_data = json.loads(msg.value().decode('utf-8'))
                chat_id = message_data.get("chat_id")
                user_id = message_data.get("user_id")
                message_type = message_data.get("type")
                next_action = message_data.get("next_action")
                
                print(f"Message data: {message_data}")
                if chat_id and user_id:
                    await manager.send_to_user_chat(message_data, user_id, chat_id)
                    print(f"Sent bot response to user {user_id}, chat {chat_id}")

                    if next_action == "exit" or message_type == "exit":
                        print(f"Bot initiated exit for chat {chat_id}. Sending close notification.")

                        close_message = {
                            "type": "chat_closed",
                            "chat_id": chat_id,
                            "user_id": user_id,
                            "message": f"Тикет закрыт. Чат будет удален через {CHAT_AUTO_DELETE_DELAY} секунд.",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        await manager.send_to_user_chat(close_message, user_id, chat_id)
                        print(f"Sent close notification to user {user_id}, chat {chat_id}")

                        asyncio.create_task(schedule_chat_deletion(chat_id, user_id, CHAT_AUTO_DELETE_DELAY))
                    
            except json.JSONDecodeError as e:
                print(f"Error decoding message: {e}")
            except Exception as e:
                print(f"Error processing message: {e}")
                
    except Exception as e:
        print(f"Consumer exception: {e}")
    finally:
        consumer.close()

async def consume_title_updates():
    """Фоновая задача для чтения обновлений заголовков из Kafka"""
    consumer = Consumer(consumer_config)
    consumer.subscribe([KAFKA_TITLE_TOPIC])
    
    print(f"Started consuming from {KAFKA_TITLE_TOPIC}")
    
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"Title consumer error: {msg.error()}")
                    continue
            
            try:
                message_data = json.loads(msg.value().decode('utf-8'))
                user_id = message_data.get("user_id")
                chat_id = message_data.get("chat_id")
                title = message_data.get("title")

                if chat_id and user_id and title:
                    title_update = {
                        "type": "title_updated",
                        "chat_id": chat_id,
                        "title": title,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await manager.send_to_user_chat(title_update, user_id, chat_id)
                    print(f"Sent title update to user {user_id}, chat {chat_id}: '{title}'")
                    
            except json.JSONDecodeError as e:
                print(f"Error decoding title message: {e}")
            except Exception as e:
                print(f"Error processing title message: {e}")
                
    except Exception as e:
        print(f"Title consumer exception: {e}")
    finally:
        consumer.close()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume_bot_responses())
    asyncio.create_task(consume_title_updates())
    print("WebSocket service started")

@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    chat_id: str,
    token: str = Query(...)
):
    """WebSocket эндпоинт с JWT аутентификацией"""

    try:
        user_data = verify_ws_token(token)
        user_id = user_data["user_id"]
    except HTTPException:
        await websocket.close(code=1008) 
        return
    
    await manager.connect(websocket, user_id, chat_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id, chat_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id, chat_id)

@app.get("/health")
async def health():
    total_connections = sum(
        len(sessions)
        for user_sessions in manager.active_connections.values()
        for sessions in user_sessions.values()
    )
    return {
        "status": "healthy",
        "service": "ws-service",
        "active_users": len(manager.active_connections),
        "total_connections": total_connections
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
