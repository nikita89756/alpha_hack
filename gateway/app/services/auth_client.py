import httpx
import logging
from fastapi import HTTPException, status

from app.core.config import Config
from app.schemas.auth import UserRegister, UserResponse, Token

logger = logging.getLogger(__name__)


class AuthServiceClient:
    
    def __init__(self, config: Config):
        self.base_url = config.AUTH_SERVICE_URL
        self.timeout = config.REQUEST_TIMEOUT
    
    async def register_user(self, user_data: UserRegister) -> UserResponse:
        """Register new user"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/auth/register",
                    json=user_data.model_dump()
                )
                response.raise_for_status()
                logger.info(f"User registered: {user_data.username}")
                return UserResponse(**response.json())
            except httpx.HTTPStatusError as e:
                error_detail = e.response.json().get("detail", "Registration failed")
                logger.error(f"Registration failed: {error_detail}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=error_detail
                )
    
    async def login(self, username: str, password: str) -> Token:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/auth/login",
                    data={"username": username, "password": password}
                )
                response.raise_for_status()
                logger.info(f"User logged in: {username}")
                return Token(**response.json())
            except httpx.HTTPStatusError:
                logger.warning(f"Login failed for user: {username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password"
                )
    
    async def refresh_token(self, refresh_token: str) -> Token:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/auth/refresh",
                    params={"refresh_token": refresh_token}
                )
                response.raise_for_status()
                return Token(**response.json())
            except:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token"
                )
    
    async def get_user_profile(self, token: str) -> UserResponse:
        """Получение профиля пользователя"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/auth/profile",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                return UserResponse(**response.json())
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get user profile: {e}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail="Failed to get user profile"
                )
    
    async def check_health(self) -> bool:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
            except:
                return False
