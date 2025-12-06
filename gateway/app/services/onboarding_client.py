import httpx
from fastapi import HTTPException, status
from app.core.config import Config
from app.schemas.onboarding import OnboardingCompleteRequest

class OnboardingServiceClient:
    def __init__(self, config: Config):
        self.base_url = config.BOT_SERVICE_URL
        self.timeout = config.REQUEST_TIMEOUT or 30.0

    async def send_onboarding_data(self, user_id: str, request: OnboardingCompleteRequest) -> dict:

        url = f"{self.base_url}/onboarding/complete"
        
        payload = request.model_dump()
        payload["user_id"] = user_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"AI Service Error: {e.response.text}"
                )
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"AI Service is unavailable: {str(e)}"
                )
