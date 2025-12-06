from fastapi import APIRouter, Depends , BackgroundTasks, Response

from app.core.config import get_config, Config
from app.core.dependencies import verify_token
from app.schemas.message import SendMessageRequest, MessageResponse
from app.services.message_client import MessageServiceClient

router = APIRouter(prefix="/messages", tags=["Messages"])


def get_message_client(config: Config = Depends(get_config)) -> MessageServiceClient:
    return MessageServiceClient(config)


@router.post(
    "/send",
    response_model=MessageResponse,
    summary="Отправка сообщения боту"
)
async def send_message(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    return await message_client.send_message(user["user_id"], request,background_tasks)


@router.get(
    "/history/{chat_id}",
    summary="История сообщений"
)
async def get_message_history(
    chat_id: str,
    limit: int = 50,
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    if limit < 1:
        limit = 1
    return await message_client.get_message_history(chat_id, user["user_id"], limit)


@router.get(
    "/{message_id}/export",
    summary="Экспорт и скачивание сообщения"
)
async def export_message(
    message_id: str,
    format: str = "md",
    user: dict = Depends(verify_token),
    message_client: MessageServiceClient = Depends(get_message_client)
):
    """Экспортирует сообщение в указанный формат и возвращает файл для скачивания"""
    resp = await message_client.export_message(message_id, user["user_id"], format)

    headers = {}
    cd = resp.headers.get("content-disposition")
    if cd:
        headers["Content-Disposition"] = cd

    return Response(content=resp.content, media_type=resp.headers.get("content-type"), headers=headers, status_code=resp.status_code)
