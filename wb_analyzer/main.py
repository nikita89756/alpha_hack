import os
import logging
import json
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet
from redis import asyncio as aioredis 

from wb_service import build_pnl_from_wb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379") 

DB_NAME = "chatbot_db"
COLLECTION_NAME = "users_keys"

SECRET_KEY = os.getenv("ENCRYPTION_KEY")
if not SECRET_KEY:
    logger.warning("ENCRYPTION_KEY не найден! Генерирую временный.")
    SECRET_KEY = Fernet.generate_key().decode()

cipher_suite = Fernet(SECRET_KEY.encode())

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Подключение к MongoDB...")
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    app.users_collection = db[COLLECTION_NAME]
    
    logger.info("Подключение к Redis...")
    app.redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

    yield

    logger.info("Закрытие соединений...")
    mongo_client.close()
    await app.redis.close()

app = FastAPI(lifespan=lifespan, title="WB PnL Service")

class WBKeyRequest(BaseModel):
    user_id: str
    business_id: str
    api_key: Optional[str] = None 

def encrypt_key(key: str) -> str:
    return cipher_suite.encrypt(key.encode()).decode()

def decrypt_key(encrypted_token: str) -> str:
    return cipher_suite.decrypt(encrypted_token.encode()).decode()

def get_redis_key(user_id: str, business_id: str) -> str:
    """Формирует уникальный ключ для Redis"""
    return f"pnl:{user_id}:{business_id}"

@app.post("/build_pnl")
async def build_pnl_endpoint(request: WBKeyRequest):
    """
    Считает PnL, сохраняет ключи в Mongo и кэширует результат в Redis.
    """
    try:
        working_api_key = request.api_key
        source_type = "provided_in_request"

        if working_api_key:
            encrypted_key = encrypt_key(working_api_key)
            await app.users_collection.update_one(
                {"user_id": request.user_id, "business_id": request.business_id},
                {"$set": {
                    "wb_api_key_encrypted": encrypted_key,
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
        else:
            source_type = "loaded_from_db"
            user_doc = await app.users_collection.find_one({
                "user_id": request.user_id, 
                "business_id": request.business_id
            })
            
            if not user_doc or "wb_api_key_encrypted" not in user_doc:
                raise HTTPException(status_code=400, detail="API ключ не найден.")
            
            try:
                working_api_key = decrypt_key(user_doc["wb_api_key_encrypted"])
            except Exception:
                raise HTTPException(status_code=500, detail="Ошибка дешифровки ключа.")

        pnl_data = build_pnl_from_wb(working_api_key)

        redis_key = get_redis_key(request.user_id, request.business_id)

        await app.redis.set(redis_key, json.dumps(pnl_data, default=str), ex=3600)

        return {
            "status": "success",
            "user_id": request.user_id,
            "business_id": request.business_id,
            "key_source": source_type,
            "data": pnl_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in build_pnl: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.get("/get_cached_pnl/{user_id}/{business_id}")
async def get_cached_pnl(user_id: str, business_id: str):
    """
    Возвращает сохраненные данные PnL из Redis без обращения к API WB.
    """
    try:
        redis_key = get_redis_key(user_id, business_id)

        cached_data = await app.redis.get(redis_key)
        
        if not cached_data:
            raise HTTPException(
                status_code=404, 
                detail="Данные не найдены в кэше. Сначала выполните расчет через /build_pnl"
            )

        data = json.loads(cached_data)
        
        return {
            "status": "success",
            "source": "redis_cache",
            "user_id": user_id,
            "business_id": business_id,
            "data": data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при чтении кэша")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
