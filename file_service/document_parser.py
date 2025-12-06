import io
import logging
from pathlib import Path
from typing import Optional, Union, Callable
import requests
from urllib.parse import urlparse
from pathlib import Path 
 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
 
 
import io
import logging
from pathlib import Path
from typing import Optional, Union, Callable
import requests
from urllib.parse import urlparse
 
try:
    from PyPDF2 import PdfReader
except ImportError:
    logging.warning("PyPDF2 не установлен. Для парсинга PDF выполните: pip install PyPDF2")
    PdfReader = None
 
try:
    from docx import Document
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl
    from docx.table import Table
    from docx.text.paragraph import Paragraph
except ImportError:
    logging.warning("python-docx не установлен. Для парсинга DOCX выполните: pip install python-docx")
    Document = None
 
try:
    import win32com.client
    DOC_SUPPORT = True
except ImportError:
    DOC_SUPPORT = False
 
 
class DocumentParser:
    def __init__(self, source: Union[str, Path], request_timeout: int = 15):
        self.source = str(source)
        self.request_timeout = request_timeout
        self.content: Optional[str] = None
        self._source_is_url = self._check_is_url()
 
    def _check_is_url(self) -> bool:
        try:
            result = urlparse(self.source)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False
 
    def parse_content(self, data: bytes) -> str:
        parser_func = self._get_parser_for_source()
        if not parser_func:
            logging.warning(f"Не найден подходящий парсер для источника: {self.source}")
            return ""
        
        try:
            parsed_text = parser_func(data)
            self.content = parsed_text
            return parsed_text
        except Exception as e:
            logging.error(f"Ошибка при парсинге байтового содержимого для {self.source}: {e}")
            return ""
 
    def _get_parser_for_source(self) -> Optional[Callable]:
        source_lower = self.source.lower()
        if source_lower.endswith('.pdf'):
            return self._parse_pdf
        if source_lower.endswith('.docx'):
            return self._parse_docx
        if source_lower.endswith('.doc'):
            if not DOC_SUPPORT:
                logging.warning(
                    "Парсинг .doc файлов на данный момент поддерживается только в Windows с "
                    "установленным MS Office и библиотекой pywin32."
                )
                return None
            return self._parse_doc
        if source_lower.endswith(('.txt', '.md', '.csv')):
            return self._parse_text
        
        if not self._source_is_url:
            return self._parse_text
            
        return None
 
    @staticmethod
    def _parse_pdf(data: Union[bytes, Path]) -> str:
        if not PdfReader: return "Ошибка: библиотека PyPDF2 не установлена."
        stream = io.BytesIO(data) if isinstance(data, bytes) else open(data, 'rb')
        text_parts = []
        with stream:
            reader = PdfReader(stream)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts).strip()
 
    @staticmethod
    def _parse_docx(data: Union[bytes, Path]) -> str:
        if not Document: return "Ошибка: библиотека python-docx не установлена."
        stream = io.BytesIO(data) if isinstance(data, bytes) else data
        document = Document(stream)
        text_parts = []
        for block in document.element.body:
            if isinstance(block, CT_P):
                para = Paragraph(block, document)
                if para.text.strip(): text_parts.append(para.text.strip())
            elif isinstance(block, CT_Tbl):
                table = Table(block, document)
                for row in table.rows:
                    cell_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    unique_texts_in_row = list(dict.fromkeys(cell_texts).keys())
                    if unique_texts_in_row: text_parts.append(" | ".join(unique_texts_in_row))
        return "\n".join(text_parts).strip()
    @staticmethod
    def _parse_text(data: Union[bytes, Path]) -> str:
        """Парсинг текстовых файлов"""
        if isinstance(data, bytes):
            try:
                return data.decode('utf-8').strip()
            except UnicodeDecodeError:
                try:
                    return data.decode('cp1251').strip()
                except UnicodeDecodeError:
                    logging.warning("Не удалось декодировать текст с utf-8 или cp1251")
                    return ""
        else:
            with open(data, 'r', encoding='utf-8') as f:
                return f.read().strip()
    @staticmethod
    def _parse_doc(data: Union[bytes, Path]) -> str:
        if isinstance(data, bytes):
            logging.warning("Парсинг .doc из байтов не поддерживается. Требуется сохранить файл на диск.")
            return "Парсинг .doc из байтов не поддерживается."
 
        word = None
        doc = None
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(data.resolve()))
            return doc.Content.Text.strip()
        except Exception as e:
            logging.error(f"Ошибка конвертации DOC через COM: {e}")
            return ""
        finally:
            if doc: doc.Close(False)
            if word: word.Quit()
            
        return None
 
    
if __name__ == "__main__":
    script_dir = Path(__file__).parent.resolve()
    file_to_parse = script_dir / "1.pdf"
    logging.info(f"Пробуем открыть файл: {file_to_parse}")
    if not file_to_parse.exists():
        logging.error(f"Файл не найден по пути {file_to_parse}")
    else:
        parser = DocumentParser(source=file_to_parse)
        content = parser.get_content()
        if content:
            logging.info("Текст успешно извлечен")
            output_filename = "output_from_docx.txt"
            logging.info(f"Сохраняем результат в файл: {output_filename}")
            parser.save_as_txt(output_filename)
        else:
            logging.error("Не удалось извлечь содержимое из файла")
