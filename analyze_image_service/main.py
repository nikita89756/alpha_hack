import logging
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from models import (
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    HealthResponse
)
from s3_storage import get_photo_url
from services import ImageAnalysisService
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Image Analysis Service",
    description="Сервис для анализа изображений с помощью OpenRouter API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analysis_service = ImageAnalysisService()


def validate_file(file: UploadFile) -> None:
    """Валидация загружаемого файла."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый формат файла. Разрешены: {settings.allowed_extensions}"
        )
    if file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {settings.max_file_size / (1024*1024)}MB"
        )


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0"
    )


@app.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(..., description="Изображение для анализа"),
):
    """
    Анализирует загруженное изображение и возвращает текстовое описание.
    
    Args:
        file: Файл изображения
        model: Модель для анализа
        prompt: Промпт для анализа
        max_tokens: Максимальное количество токенов в ответе
        
    Returns:
        Результат анализа изображения
    """
    try:
        validate_file(file)
        
        logger.info(f"Processing image: {file.filename}")
        description = await analysis_service.analyze_image_from_upload(
            file=file,
        )
        await file.seek(0)
        contents = await file.read()
        
        image_url = get_photo_url(
                image_data=contents,
                filename=file.filename,
                folder="analyzed-images"
            )
        
        return ImageAnalysisResponse(
            success=True,
            description=description,
            error = "",
            image_url=image_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return ImageAnalysisResponse(
            success=False,
            description="",
            error=str(e),
            image_url=""
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
