"""Folder management endpoints"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from app.core.config import get_config, Config
from app.core.dependencies import verify_token
from app.schemas.folder import FolderResponse, CreateFolderRequest, UpdateFolderRequest, MoveChatRequest
from app.services.message_client import MessageServiceClient

router = APIRouter(prefix="/folders", tags=["Folders"])


def get_message_client(config: Config = Depends(get_config)) -> MessageServiceClient:
    return MessageServiceClient(config)


@router.post(
    "/create",
    response_model=FolderResponse,
    status_code=201,
    summary="Создание новой папки"
)
async def create_folder(
    request: CreateFolderRequest,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    """Создает новую папку для организации чатов"""
    return await message_client.create_folder(user["user_id"], request)


@router.get(
    "/list",
    response_model=List[FolderResponse],
    summary="Список папок пользователя"
)
async def list_folders(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    """Получает список всех папок пользователя с поддержкой пагинации"""
    return await message_client.list_folders(user["user_id"], limit, skip)


@router.get(
    "/{folder_id}",
    response_model=FolderResponse,
    summary="Информация о папке"
)
async def get_folder(
    folder_id: str,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    """Получает детальную информацию о конкретной папке"""
    return await message_client.get_folder(folder_id, user["user_id"])


@router.get(
    "/{folder_id}/chats",
    summary="Список чатов в папке"
)
async def get_folder_chats(
    folder_id: str,
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    """Получает все чаты из конкретной папки"""
    return await message_client.get_folder_chats(folder_id, user["user_id"], limit, skip)


@router.put(
    "/{folder_id}",
    response_model=FolderResponse,
    summary="Обновление информации папки"
)
async def update_folder(
    folder_id: str,
    request: UpdateFolderRequest,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    """Обновляет название и описание папки"""
    return await message_client.update_folder(folder_id, user["user_id"], request)


@router.delete(
    "/{folder_id}",
    status_code=200,
    summary="Удаление папки"
)
async def delete_folder(
    folder_id: str,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    """Удаляет папку (мягкое удаление). Все чаты в папке перемещаются в корневую папку"""
    return await message_client.delete_folder(folder_id, user["user_id"])
