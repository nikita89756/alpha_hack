import httpx
import logging
from typing import List, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel

from app.core.config import Config

from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

class BusinessBase(BaseModel):
    name: str
    description: str
    industry: Optional[str] = None

class BusinessCreate(BusinessBase):
    pass

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None

class BusinessResponse(BusinessBase):

    id: str = Field(alias="_id", serialization_alias="id") 
    user_id: str

    model_config = ConfigDict(
        populate_by_name=True, 
        extra='ignore'        
    )

logger = logging.getLogger(__name__)

class BusinessServiceClient:
    def __init__(self, config: Config):
        self.base_url = config.BUSINESS_SERVICE_URL 
        self.timeout = config.REQUEST_TIMEOUT

    def _get_headers(self, user_id: str) -> dict:
        """Helper to generate headers with auth context"""
        return {
            "X-User-Id": user_id,
            "Content-Type": "application/json"
        }

    async def create_business(self, user_id: str, request: BusinessCreate) -> BusinessResponse:
        """Create a new business profile for the user."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/businesses/",
                    headers=self._get_headers(user_id),
                    json=request.model_dump()
                )
                response.raise_for_status()
                logger.info(f"Business created for user: {user_id}")
                return BusinessResponse(**response.json())
            except Exception as e:
                logger.error(f"Business creation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create business"
                )

    async def list_businesses(self, user_id: str) -> List[BusinessResponse]:
        """List all businesses owned by the user."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/businesses/",
                    headers=self._get_headers(user_id)
                )
                response.raise_for_status()
                return [BusinessResponse(**biz) for biz in response.json()]
            except Exception as e:
                logger.error(f"Failed to fetch businesses for user {user_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch businesses"
                )

    async def get_business(self, business_id: str, user_id: str) -> BusinessResponse:
        """Get details of a specific business."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/businesses/{business_id}",
                    headers=self._get_headers(user_id)
                )
                response.raise_for_status()
                return BusinessResponse(**response.json())
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Business not found"
                    )
                if e.response.status_code == 403:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access to this business is denied"
                    )
                logger.error(f"Failed to fetch business {business_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch business details"
                )

    async def update_business(self, business_id: str, user_id: str, request: BusinessUpdate) -> BusinessResponse:
        """Update an existing business."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.patch(
                    f"{self.base_url}/businesses/{business_id}",
                    headers=self._get_headers(user_id),
                    json=request.model_dump(exclude_unset=True)
                )
                response.raise_for_status()
                logger.info(f"Business {business_id} updated by user {user_id}")
                return BusinessResponse(**response.json())
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Business to update not found"
                    )
                if e.response.status_code == 403:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to update this business"
                    )
                logger.error(f"Failed to update business {business_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update business"
                )

    async def delete_business(self, business_id: str, user_id: str) -> None:
        """Delete a business."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/businesses/{business_id}",
                    headers=self._get_headers(user_id)
                )
                response.raise_for_status()
                logger.info(f"Business {business_id} deleted by user {user_id}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Business to delete not found"
                    )
                if e.response.status_code == 403:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to delete this business"
                    )
                logger.error(f"Failed to delete business {business_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete business"
                )

    async def check_health(self) -> bool:
        """Check if the business service is alive."""
        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                response = await client.get(f"{self.base_url}/docs") 
                return response.status_code == 200
            except Exception:
                return False