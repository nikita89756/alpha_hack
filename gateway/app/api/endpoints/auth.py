from fastapi import APIRouter, Depends, status, Form

from app.core.config import get_config, Config
from app.core.dependencies import verify_token
from app.schemas.auth import UserRegister, UserResponse, Token
from app.services.auth_client import AuthServiceClient

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_client(config: Config = Depends(get_config)) -> AuthServiceClient:
    return AuthServiceClient(config)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создание аккаунта с уникальным username и email"
)
async def register(
    user_data: UserRegister,
    auth_client: AuthServiceClient = Depends(get_auth_client)
):
    return await auth_client.register_user(user_data)


@router.post(
    "/login",
    response_model=Token,
    summary="Вход в систему",
    description="Получение JWT токенов для доступа к API. Можно использовать email или username"
)
async def login(
    username: str = Form(..., description="Email или username пользователя"),
    password: str = Form(...),
    auth_client: AuthServiceClient = Depends(get_auth_client)
):
    """Вход по email или username"""
    return await auth_client.login(username, password)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Обновление access токена"
)
async def refresh_token(
    refresh_token: str,
    auth_client: AuthServiceClient = Depends(get_auth_client)
):
    return await auth_client.refresh_token(refresh_token)


@router.get(
    "/profile",
    response_model=UserResponse,
    summary="Информация о текущем пользователе"
)
async def get_current_user(user: dict = Depends(verify_token)):
    """Получение профиля текущего пользователя"""
    from datetime import datetime
    return UserResponse(
        user_id=user["user_id"],
        username=user["username"],
        email=user.get("email", ""),
        full_name=user.get("full_name"),
        created_at=user.get("created_at", datetime.utcnow().isoformat()),
        is_active=user.get("is_active", True)
    )
