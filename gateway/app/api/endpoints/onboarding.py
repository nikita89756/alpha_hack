from fastapi import APIRouter, Depends, status
from app.core.config import get_config, Config
from app.core.dependencies import verify_token
from app.schemas.onboarding import OnboardingCompleteRequest
from app.services.onboarding_client import OnboardingServiceClient

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

def get_onboarding_client(config: Config = Depends(get_config)) -> OnboardingServiceClient:
    """Dependency injection для клиента AI-сервиса"""
    return OnboardingServiceClient(config)

@router.post(
    "/complete",
    status_code=status.HTTP_200_OK, 
    summary="Завершить онбординг",
    description="Отправляет данные онбординга в AI-сервис для формирования памяти ассистента"
)
async def complete_onboarding(
    onboarding_data: OnboardingCompleteRequest,
    user: dict = Depends(verify_token),
    client: OnboardingServiceClient = Depends(get_onboarding_client)
):
    user_id = user["user_id"]
    
    result = await client.send_onboarding_data(
        user_id=user_id, 
        request=onboarding_data
    )
    
    return {
        "status": "success",
        "detail": "Onboarding data saved to AI memory",
        "ai_service_response": result
    }
