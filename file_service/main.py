from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import logging
from typing import Optional
import io

from document_parser import DocumentParser  

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(title="Document Parser API", version="1.0.0")


@app.post("/parse")
async def parse_document(file: UploadFile = File(...)):
    """
    Endpoint для загрузки и парсинга документа.
    
    Поддерживаемые форматы: PDF, DOCX, DOC, TXT, MD, CSV
    
    Возвращает извлеченный текст из документа.
    """
    try:
        contents = await file.read()
        
        if not contents:
            raise HTTPException(status_code=400, detail="Файл пустой")

        parser = DocumentParser(source=file.filename)

        extracted_text = parser.parse_content(contents)
        
        if not extracted_text:
            raise HTTPException(
                status_code=422, 
                detail=f"Не удалось извлечь текст из файла {file.filename}. Проверьте формат файла."
            )
        
        logging.info(f"Успешно извлечен текст из файла: {file.filename}, длина: {len(extracted_text)} символов")
        
        return JSONResponse(
            status_code=200,
            content={
                "filename": file.filename,
                "content_type": file.content_type,
                "text": extracted_text,
                "text_length": len(extracted_text)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Ошибка при обработке файла {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
    finally:
        await file.close()


@app.get("/")
async def root():
    """Информация об API"""
    return {
        "message": "Document Parser API",
        "endpoints": {
            "/parse": "POST - Загрузить документ и получить текст",
            "/health": "GET - Проверка здоровья сервиса"
        },
        "supported_formats": ["PDF", "DOCX", "DOC", "TXT", "MD", "CSV"]
    }


@app.get("/health")
async def health_check():
    """Endpoint для проверки работоспособности сервиса"""
    return {"status": "healthy", "service": "document-parser"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
