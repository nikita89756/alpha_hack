from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import uuid
from datetime import datetime

from app.core.config import config
from app.core.security import verify_password, get_password_hash
from app.schemas.user import UserInDB, UserRegister


class AuthService:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.users_collection = None
    
    async def initialize(self):
        self.client = AsyncIOMotorClient(config.MONGODB_URL)
        self.db = self.client[config.DB_NAME]
        self.users_collection = self.db["users"]
        
        await self.users_collection.create_index("username", unique=True)
        await self.users_collection.create_index("email", unique=True)
        await self.users_collection.create_index("user_id", unique=True)
        print("MongoDB indexes initialized")
    
    async def cleanup(self):
        if self.client:
            self.client.close()
    
    async def authenticate_user(self, username_or_email: str, password: str) -> Optional[UserInDB]:
        """Аутентификация пользователя по email или username"""
        user = await self.get_user_by_email(username_or_email)
        if not user:
            user = await self.get_user_by_username(username_or_email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    async def register_user(self, user_data: UserRegister) -> UserInDB:
        user_id = str(uuid.uuid4())
        user_dict = {
            "user_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": get_password_hash(user_data.password),
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        await self.users_collection.insert_one(user_dict)
        return UserInDB(**user_dict)
    
    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        user = await self.users_collection.find_one({"username": username})
        if user:
            user["_id"] = str(user["_id"])
            return UserInDB(**user)
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Получение пользователя по email"""
        user = await self.users_collection.find_one({"email": email})
        if user:
            user["_id"] = str(user["_id"])
            return UserInDB(**user)
        return None


auth_service = AuthService()
