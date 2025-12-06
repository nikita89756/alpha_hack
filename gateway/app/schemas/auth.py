from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "username": "nikitos",
                "email": "shu@example.com",
                "password": "string",
                "full_name": "nikitos shush"
            }
        }


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime
    is_active: bool


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
