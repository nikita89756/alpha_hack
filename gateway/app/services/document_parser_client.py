import httpx
import logging
from typing import Optional
from fastapi import HTTPException, UploadFile

from app.core.config import Config
from app.schemas.document_parser import DocumentParseResponse


logger = logging.getLogger(__name__)


class DocumentParserServiceClient:
    
    def __init__(self, config: Config):
        self.base_url = config.DOCUMENT_PARSER_SERVICE_URL
        self.timeout = config.REQUEST_TIMEOUT or 30.0
    
    async def parse_document(
        self, 
        file: UploadFile,
    ) -> DocumentParseResponse:
        """
        Отправляет документ на парсинг и возвращает извлеченный текст.
        
        Args:
            file: UploadFile объект с документом
            
        Returns:
            DocumentParseResponse с извлеченным текстом
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:

                files = {
                    "file": (file.filename, file.file, file.content_type)
                }
                
                response = await client.post(
                    f"{self.base_url}/parse",
                    files=files
                )

                await file.seek(0)
                
                response.raise_for_status()
                logger.info(f"Document parsed successfully: {file.filename}")
                
                return DocumentParseResponse(**response.json())
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.json().get("detail", "Document parsing failed")
                logger.error(f"Document parsing failed: {error_detail}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=error_detail
                )
            except httpx.TimeoutException:
                logger.error(f"Document parsing timeout for: {file.filename}")
                raise HTTPException(
                    status_code=504,
                    detail="Document parsing service timeout"
                )
            except Exception as e:
                logger.error(f"Unexpected error during document parsing: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse document: {str(e)}"
                )
    
    async def parse_document_from_bytes(
        self,
        document_bytes: bytes,
        filename: str = "document.pdf",
        content_type: str = "application/pdf"
    ) -> DocumentParseResponse:

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {
                    "file": (filename, document_bytes, content_type)
                }
                
                response = await client.post(
                    f"{self.base_url}/parse",
                    files=files
                )
                
                response.raise_for_status()
                logger.info(f"Document parsed from bytes: {filename}")
                
                return DocumentParseResponse(**response.json())
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.json().get("detail", "Document parsing failed")
                logger.error(f"Document parsing failed: {error_detail}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=error_detail
                )
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse document: {str(e)}"
                )
    
    async def parse_document_from_url(
        self,
        document_url: str,
        filename: Optional[str] = None
    ) -> DocumentParseResponse:

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                download_response = await client.get(document_url)
                download_response.raise_for_status()

                if not filename:
                    filename = document_url.split("/")[-1] or "document.pdf"

                content_type = download_response.headers.get(
                    "content-type", 
                    "application/octet-stream"
                )

                return await self.parse_document_from_bytes(
                    document_bytes=download_response.content,
                    filename=filename,
                    content_type=content_type
                )
                
            except Exception as e:
                logger.error(f"Failed to download or parse document from URL: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process document from URL: {str(e)}"
                )
    
    async def check_health(self) -> bool:
        """
        Проверяет доступность сервиса парсинга документов.
        
        Returns:
            bool: True если сервис доступен
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
            except Exception as e:
                logger.warning(f"Document parser health check failed: {str(e)}")
                return False
