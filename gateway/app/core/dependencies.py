from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import httpx
import logging
from functools import lru_cache

from app.core.config import get_config, Config

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def verify_token(
    token: str = Depends(oauth2_scheme),
    config: Config = Depends(get_config)
) -> dict:
    async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{config.AUTH_SERVICE_URL}/auth/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            logger.warning("Token verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service unavailable"
            )


@lru_cache()
def get_http_client() -> httpx.AsyncClient:
    """Get cached HTTP client for service communication"""
    config = get_config()
    return httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT)
