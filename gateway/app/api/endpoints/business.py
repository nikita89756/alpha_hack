from typing import List
from fastapi import APIRouter, Depends, status, Path, Body, HTTPException

from app.core.config import get_config, Config
from app.core.dependencies import verify_token
from app.schemas.business import BusinessCreate, BusinessUpdate, BusinessResponse
from app.services.business_client import BusinessServiceClient

router = APIRouter(prefix="/businesses", tags=["Businesses"])

def get_business_client(config: Config = Depends(get_config)) -> BusinessServiceClient:
    """Dependency injection для клиента бизнес-сервиса"""
    return BusinessServiceClient(config)

@router.post(
    "/",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать бизнес",
    description="Создает новый профиль бизнеса для текущего пользователя"
)
async def create_business(
    business_data: BusinessCreate,
    user: dict = Depends(verify_token),
    client: BusinessServiceClient = Depends(get_business_client)
):
    return await client.create_business(
        user_id=user["user_id"], 
        request=business_data
    )

@router.get(
    "/",
    response_model=List[BusinessResponse],
    summary="Список бизнесов",
    description="Получить все бизнесы, принадлежащие текущему пользователю"
)
async def list_my_businesses(
    user: dict = Depends(verify_token),
    client: BusinessServiceClient = Depends(get_business_client)
):
    return await client.list_businesses(user_id=user["user_id"])

@router.get(
    "/{business_id}",
    response_model=BusinessResponse,
    summary="Детали бизнеса",
    description="Получить информацию о конкретном бизнесе по ID"
)
async def get_business_details(
    business_id: str = Path(..., description="ID бизнеса"),
    user: dict = Depends(verify_token),
    client: BusinessServiceClient = Depends(get_business_client)
):
    return await client.get_business(
        business_id=business_id, 
        user_id=user["user_id"]
    )

@router.patch(
    "/{business_id}",
    response_model=BusinessResponse,
    summary="Обновить бизнес",
    description="Частичное обновление данных бизнеса (только для владельца)"
)
async def update_business(
    business_data: BusinessUpdate,
    business_id: str = Path(..., description="ID бизнеса"),
    user: dict = Depends(verify_token),
    client: BusinessServiceClient = Depends(get_business_client)
):
    return await client.update_business(
        business_id=business_id,
        user_id=user["user_id"],
        request=business_data
    )

@router.delete(
    "/{business_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить бизнес",
    description="Удаляет бизнес профиль. Действие необратимо."
)
async def delete_business(
    business_id: str = Path(..., description="ID бизнеса"),
    user: dict = Depends(verify_token),
    client: BusinessServiceClient = Depends(get_business_client)
):
    await client.delete_business(
        business_id=business_id, 
        user_id=user["user_id"]
    )
    return None