import sys
import os
from pathlib import Path
import logging
from typing import List, Dict

sys.path.append(str(Path(__file__).parent.parent.parent))

from parsers.centralbank.cbr_title import CBRAnalyticsParser
from parsers.centralbank.cbr_qdrant import init_collection, is_document_exists, add_to_qdrant
from tools.llm import LLMClient, DocumentRelevanceChecker
from tools.pdf import PDFParser
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CBRDocumentReviewer:
    """Класс для проверки и загрузки документов ЦБ в Qdrant"""
    
    def __init__(self, qdrant_url: str = "qdrant", qdrant_port: int = 6333, collection_name: str = "cbr_documents") -> None:
        self.parser = CBRAnalyticsParser()
        self.pdf_parser = PDFParser()
        
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.llm_client = LLMClient(api_key=api_key)
        self.relevance_checker = DocumentRelevanceChecker(self.llm_client)
        
        self.qdrant_client = QdrantClient(host=qdrant_url, port=qdrant_port)
        self.collection_name = collection_name
        
        init_collection(self.qdrant_client, self.collection_name)
    
    def parse_documents_from_site(self, max_docs: int = 30) -> List[Dict]:
        """
        Парсит документы с сайта ЦБ
        
        Args:
            max_docs: Максимальное количество документов для обработки
            
        Returns:
            Список документов
        """
        logger.info("Парсинг документов с сайта ЦБ")
        documents = self.parser.parse_all(max_items=max_docs, delay=1)
        logger.info(f"Спарсено {len(documents)} документов")
        return documents
    
    def filter_new_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Фильтрует новые документы и добавляет их в Qdrant
        
        Args:
            documents: Список документов
            
        Returns:
            Список новых документов
        """
        new_docs = []
        for idx, doc in enumerate(documents, 1):
            if not is_document_exists(self.qdrant_client, self.collection_name, doc['url']):
                new_docs.append(doc)
                add_to_qdrant(self.qdrant_client, self.collection_name, doc)
            else:
                logger.info(f"Пропуск {idx}/{len(documents)}: уже в базе")
        
        logger.info(f"Новых документов: {len(new_docs)}")
        return new_docs
    
    def filter_relevant_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Фильтрует релевантные документы через LLM
        
        Args:
            documents: Список документов
            
        Returns:
            Список релевантных документов
        """
        if not documents:
            logger.info("Нет документов для проверки релевантности")
            return []
        
        logger.info("Проверка релевантности через LLM")
        relevant_docs = []
        for idx, doc in enumerate(documents, 1):
            logger.info(f"Проверка {idx}/{len(documents)}: {doc['title'][:60]}...")
            is_relevant = self.relevance_checker.check_relevance(
                title=doc['title'],
                source=doc.get('source', ''),
                category=doc.get('data_zoom_referer_title', '')
            )
            if is_relevant:
                relevant_docs.append(doc)
        
        logger.info(f"Релевантных документов: {len(relevant_docs)}")
        return relevant_docs
    
    def parse_pdfs(self, documents: List[Dict]) -> List[str]:
        """
        Парсит PDF файлы для списка документов
        
        Args:
            documents: Список документов с URL
            
        Returns:
            Список распарсенных текстов
        """
        logger.info(f"Парсинг {len(documents)} PDF файлов")
        pdf_texts = []
        
        for idx, doc in enumerate(documents, 1):
            logger.info(f"PDF {idx}/{len(documents)}: {doc['title'][:60]}...")
            
            pdf_text = self.pdf_parser.parse_pdf_from_url(doc['url'])
            
            if pdf_text:
                pdf_text = self.pdf_parser.clean_text(pdf_text)
                pdf_texts.append(pdf_text)
                logger.info(f"Успешно распарсен ({len(pdf_text)} символов)")
            else:
                logger.warning(f"Не удалось распарсить PDF")
        
        logger.info(f"Успешно распарсено: {len(pdf_texts)}/{len(documents)}")
        return pdf_texts

