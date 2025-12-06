from fastapi import APIRouter, Depends, UploadFile, File
from app.services.document_parser_client import DocumentParserServiceClient
from app.schemas.document_parser import DocumentParseResponse
from app.core.config import Config
from app.core.dependencies import verify_token

router = APIRouter(tags=["documents"])
async def get_document_parser_client() -> DocumentParserServiceClient:
    config = Config()
    return DocumentParserServiceClient(config)


@router.post("/parse", response_model=DocumentParseResponse)
async def parse_uploaded_document(
    user: dict = Depends(verify_token),
    file: UploadFile = File(...),
    client: DocumentParserServiceClient = Depends(get_document_parser_client)
):
    """Загрузить и распарсить документ"""
    return await client.parse_document(file)