from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_config, Config
from app.core.dependencies import verify_token
from app.schemas.wb import WBKeyRequest, WBPnLResponse
from app.services.wb_client import WBServiceClient

router = APIRouter(prefix="/wb", tags=["Wildberries Analytics"])

def get_wb_client(config: Config = Depends(get_config)) -> WBServiceClient:
    return WBServiceClient(config)

@router.post(
    "/build_pnl",
    response_model=WBPnLResponse,
    summary="Запрос на построение PnL (с расчетом)"
)
async def build_pnl_proxy(
    request: WBKeyRequest,
    user: dict = Depends(verify_token),
    wb_client: WBServiceClient = Depends(get_wb_client)
):
    """
    Инициирует расчет PnL на микросервисе.
    Если API ключ передан - он обновится.
    Если нет - используется сохраненный.
    """
    return await wb_client.build_pnl(user["user_id"], request)

@router.get(
    "/get_cached_pnl/{business_id}",
    summary="Получение кэшированного PnL"
)
async def get_cached_pnl_proxy(
    business_id: str,
    user: dict = Depends(verify_token),
    wb_client: WBServiceClient = Depends(get_wb_client)
):
    """
    Пытается получить уже готовые данные из кэша Redis.
    Очень быстрый метод, не нагружает WB API.
    Возвращает 404, если кэш пуст или просрочен.
    """
    return await wb_client.get_cached_pnl(user["user_id"], business_id)
