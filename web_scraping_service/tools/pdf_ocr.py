import logging
import os
from typing import Optional
import io
from dotenv import load_dotenv

load_dotenv()

try:
    from pdf2image import convert_from_bytes
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract_text_ocr(pdf_bytes: bytes) -> Optional[str]:
    """
    Извлекает текст из PDF используя OCR (для PDF с изображениями)
    Конвертирует все страницы PDF в изображения и прогоняет через OCR
    
    Args:
        pdf_bytes: Байты PDF файла
        
    Returns:
        Извлечённый текст или None при ошибке
    """
    if not OCR_AVAILABLE:
        logger.error("OCR библиотеки не установлены. Установите: pip install pdf2image pytesseract pillow")
        return None
    
    try:
        logger.info("Конвертируем PDF страницы в изображения...")
        
        poppler_path = os.getenv('POPPLER_PATH', None)
        if poppler_path:
            if os.name == 'nt': 
                poppler_bin = os.path.join(poppler_path, 'bin')
                if os.path.exists(poppler_bin):
                    logger.info(f"Используем poppler из: {poppler_bin}")
                    images = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=poppler_bin)
                else:
                    logger.warning(f"Poppler bin не найден по пути: {poppler_bin}, используем системный")
                    images = convert_from_bytes(pdf_bytes, dpi=300)
            else:
                if os.path.exists(poppler_path):
                    logger.info(f"Используем poppler из: {poppler_path}")
                    images = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=poppler_path)
                else:
                    logger.warning(f"Poppler не найден по пути: {poppler_path}, используем системный")
                    images = convert_from_bytes(pdf_bytes, dpi=300)
        else:
            images = convert_from_bytes(pdf_bytes, dpi=300)
        
        logger.info(f"Конвертировано страниц: {len(images)}")
        
        tesseract_cmd = os.getenv('TESSERACT_CMD', None)
        if tesseract_cmd:
            if os.path.exists(tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                logger.info(f"Используем Tesseract из: {tesseract_cmd}")
            else:
                logger.warning(f"Tesseract не найден по пути: {tesseract_cmd}, используем системный")
        
        text_parts = []
        for page_num, image in enumerate(images, 1):
            logger.info(f"OCR обработка страницы {page_num}/{len(images)}...")
            page_text = pytesseract.image_to_string(image, lang='rus+eng')
            if page_text:
                text_parts.append(page_text.strip())
                logger.info(f"Страница {page_num}: извлечено {len(page_text)} символов")
        
        full_text = '\n\n'.join(text_parts)
        logger.info(f"OCR извлечено символов: {len(full_text)}")
        return full_text if full_text else None
        
    except Exception as e:
        error_msg = str(e)
        if "poppler" in error_msg.lower() or "Unable to get page count" in error_msg:
            logger.error("Ошибка Poppler!")
            if os.name == 'nt':  
                logger.error("Для локальной разработки на Windows добавьте путь в .env:")
                logger.error("POPPLER_PATH=C:\\путь\\к\\папке\\poppler-XX.XX.XX")
            else:
                logger.error("В Docker poppler должен быть установлен через apt-get")
                logger.error("Проверьте Dockerfile.airflow - должна быть строка: poppler-utils")
        elif "tesseract" in error_msg.lower() or "not installed" in error_msg.lower():
            logger.error("Ошибка Tesseract OCR!")
            if os.name == 'nt': 
                logger.error("Для локальной разработки на Windows добавьте путь в .env:")
                logger.error("TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
            else:
                logger.error("В Docker tesseract должен быть установлен через apt-get")
                logger.error("Проверьте Dockerfile.airflow - должны быть строки: tesseract-ocr tesseract-ocr-rus")
        else:
            logger.error(f"Ошибка OCR: {error_msg}")
        return None

