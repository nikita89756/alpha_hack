import httpx
from fastapi import HTTPException
from app.core.config import Config
from app.schemas.wb import WBKeyRequest

class WBServiceClient:
    def __init__(self, config: Config):
        self.base_url = config.WB_SERVICE_URL 
        self.timeout = config.REQUEST_TIMEOUT

    async def build_pnl(self, user_id: str, request: WBKeyRequest):
        """
        Отправляет запрос к внешнему микросервису /build_pnl
        """
        url = f"{self.base_url}/build_pnl"

        payload = {
            "user_id": user_id,
            "business_id": request.business_id,
            "api_key": request.api_key
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=self.timeout)
                
                if response.status_code != 200:
                    try:
                        error_detail = response.json().get("detail", response.text)
                    except:
                        error_detail = response.text
                        
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_detail
                    )
                
                return response.json()
                
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Service build_pnl unavailable: {str(e)}"
                )

    async def get_cached_pnl(self, user_id: str, business_id: str):
        """
        Получает кэшированные данные из /get_cached_pnl/{user_id}/{business_id}
        """
        url = f"{self.base_url}/get_cached_pnl/{user_id}/{business_id}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=self.timeout)
                
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=404,
                        detail="Cache miss"
                    )
                
                if response.status_code != 200:
                    try:
                        error_detail = response.json().get("detail", response.text)
                    except:
                        error_detail = response.text

                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_detail
                    )
                
                return response.json()
                
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Service get_cached_pnl unavailable: {str(e)}"
                )
