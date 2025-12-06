import httpx
import logging
from typing import Optional
from fastapi import HTTPException, UploadFile

from app.core.config import Config
from app.schemas.analyze_image import ImageAnalysisResponse


logger = logging.getLogger(__name__)


class ImageAnalysisServiceClient:
    
    def __init__(self, config: Config):
        self.base_url = config.IMAGE_ANALYSIS_SERVICE_URL
        self.timeout = config.REQUEST_TIMEOUT or 30.0
    
    async def analyze_image(
        self, 
        file: UploadFile,
    ) -> ImageAnalysisResponse:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {
                    "file": (file.filename, file.file, file.content_type)
                }
                
                response = await client.post(
                    f"{self.base_url}/analyze",
                    files=files
                )
                
                await file.seek(0)
                
                response.raise_for_status()
                logger.info(f"Image analyzed successfully: {file.filename}")
                
                return ImageAnalysisResponse(**response.json())
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.json().get("detail", "Image analysis failed")
                logger.error(f"Image analysis failed: {error_detail}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=error_detail
                )
            except httpx.TimeoutException:
                logger.error(f"Image analysis timeout for: {file.filename}")
                raise HTTPException(
                    status_code=504,
                    detail="Image analysis service timeout"
                )
            except Exception as e:
                logger.error(f"Unexpected error during image analysis: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to analyze image: {str(e)}"
                )
    
    async def analyze_image_from_bytes(
        self,
        image_bytes: bytes,
        filename: str = "image.jpg",
        content_type: str = "image/jpeg"
    ) -> ImageAnalysisResponse:

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {
                    "file": (filename, image_bytes, content_type)
                }
                
                response = await client.post(
                    f"{self.base_url}/analyze",
                    files=files
                )
                
                response.raise_for_status()
                logger.info(f"Image analyzed from bytes: {filename}")
                
                return ImageAnalysisResponse(**response.json())
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.json().get("detail", "Image analysis failed")
                logger.error(f"Image analysis failed: {error_detail}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=error_detail
                )
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to analyze image: {str(e)}"
                )
    
    async def check_health(self) -> bool:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
            except Exception as e:
                logger.warning(f"Health check failed: {str(e)}")
                return False
