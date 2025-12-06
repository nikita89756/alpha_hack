"""Health check endpoints"""
from fastapi import APIRouter, Depends

from app.core.config import get_config, Config
from app.services.auth_client import AuthServiceClient
from app.services.message_client import MessageServiceClient

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(config: Config = Depends(get_config)):
    auth_client = AuthServiceClient(config)
    message_client = MessageServiceClient(config)
    
    services_status = {
        "auth": "healthy" if await auth_client.check_health() else "unavailable",
        "message": "healthy" if await message_client.check_health() else "unavailable",
    }
    
    all_healthy = all(status == "healthy" for status in services_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "service": "api-gateway",
        "version": "1.0.0",
        "services": services_status
    }
