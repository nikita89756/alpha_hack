from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.core.config import get_config
from app.services.analyze_image_client import ImageAnalysisServiceClient
from app.core.dependencies import verify_token

router = APIRouter(tags=["Image Analysis"])

async def get_image_client() -> ImageAnalysisServiceClient:
    config = get_config()
    return ImageAnalysisServiceClient(config)

@router.post("/process-image")
async def process_image(
    user: dict = Depends(verify_token),
    file: UploadFile = File(...),
    image_client: ImageAnalysisServiceClient = Depends(get_image_client)
):
    result = await image_client.analyze_image(file)
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    
    return {"description": result.description,"image_url": result.image_url}