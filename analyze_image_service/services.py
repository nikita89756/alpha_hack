import base64
import logging
from openai import OpenAI
from fastapi import UploadFile, HTTPException
from config import settings

logger = logging.getLogger(__name__)


class ImageAnalysisService:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
        self.model = settings.default_model
        self.prompt = settings.prompt
        self.max_tokens = settings.max_tokens
    
    async def analyze_image_from_upload(
        self,
        file: UploadFile,
    ) -> str:
        """
        Анализирует загруженное изображение.
        
        Args:
            file: Загруженный файл
            prompt: Промпт для анализа
            model: Модель для использования
            max_tokens: Максимальное количество токенов
            
        Returns:
            Текстовое описание изображения
        """
        try:

            contents = await file.read()
            base64_image = base64.b64encode(contents).decode('utf-8')

            mime_type = file.content_type or "image/png"
            
            logger.info(f"Analyzing image with model: {self.model}")
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens
            )
            
            if not completion.choices or not completion.choices[0].message.content:
                logger.error("Empty response from API")
                raise ValueError("Пустой ответ от API")
            
            result = completion.choices[0].message.content
            return result
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при анализе изображения: {str(e)}"
            )
