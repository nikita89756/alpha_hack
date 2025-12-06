"""Chat management endpoints"""
from fastapi import APIRouter, Depends, Response
from typing import List, Optional

from app.core.config import get_config, Config
from app.core.dependencies import verify_token
from app.schemas.chat import  ChatResponse
from app.schemas.folder import MoveChatRequest
from app.services.message_client import MessageServiceClient

router = APIRouter(prefix="/chats", tags=["Chats"])


def get_message_client(config: Config = Depends(get_config)) -> MessageServiceClient:
    return MessageServiceClient(config)


@router.post(
    "/create",
    response_model=ChatResponse,
    status_code=201,
    summary="Создание нового чата"
)
async def create_chat(
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    return await message_client.create_chat(user["user_id"])


@router.get(
    "/list",
    response_model=List[ChatResponse],
    summary="Список всех чатов пользователя"
)
async def list_chats(
    limit: int = 20,
    skip: int = 0,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    return await message_client.list_chats(user["user_id"], limit, skip)


@router.get(
    "/{chat_id}",
    response_model=ChatResponse,
    summary="Информация о чате"
)
async def get_chat(
    chat_id: str,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    return await message_client.get_chat(chat_id, user["user_id"])

@router.delete(
    "/{chat_id}",
    status_code=200,
    summary="Удаление чата"
)
async def delete_chat(
    chat_id: str,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    return await message_client.delete_chat(chat_id, user["user_id"])


@router.put(
    "/{chat_id}/move",
    status_code=200,
    summary="Перемещение чата в папку"
)
async def move_chat(
    chat_id: str,
    request: MoveChatRequest,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    """Перемещает чат в указанную папку или в корневую папку"""
    return await message_client.move_chat_to_folder(chat_id, user["user_id"], request.folder_id)


@router.get(
    "/{chat_id}/export",
    summary="Экспорт и скачивание диалога"
)
async def export_chat(
    chat_id: str,
    format: str = "md",
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    """Экспортирует диалог в указанный формат и возвращает файл для скачивания"""
    resp = await message_client.export_chat(chat_id, user["user_id"], format)

    headers = {}
    cd = resp.headers.get("content-disposition")
    if cd:
        headers["Content-Disposition"] = cd

    return Response(content=resp.content, media_type=resp.headers.get("content-type"), headers=headers, status_code=resp.status_code)
