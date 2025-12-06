from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    """Схема регистрации пользователя"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "securepass123",
                "full_name": "John Doe"
            }
        }


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя"""
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    is_active: bool


class UserInDB(BaseModel):
    """Схема пользователя в БД"""
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    hashed_password: str
    created_at: datetime
    is_active: bool = True
