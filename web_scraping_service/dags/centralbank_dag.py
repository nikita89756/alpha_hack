"""
DAG для парсинга документов Центрального Банка
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
import sys
from pathlib import Path
import os

sys.path.append(str(Path(__file__).parent.parent))

from parsers.centralbank.cbr_review import CBRDocumentReviewer
from parsers.parser_wrapper import create_fragments, send_to_api
from dags.telegram_callbacks import telegram_on_failure_callback
import asyncio
import httpx

default_args = {
    'owner': 'parser_service',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,  
    'on_failure_callback': telegram_on_failure_callback,  
}

dag = DAG(
    'centralbank_parser',
    default_args=default_args,
    description='Парсинг документов Центрального Банка',
    schedule_interval='0 22 * * *',  # Каждый день в 22:00
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['centralbank', 'parsing', 'cbr'],
)


with dag:
    @task
    def parse_documents():
        """Этап 1: Парсинг документов с сайта ЦБ"""
        print("Инициализация парсера ЦБ...")
        qdrant_url = os.getenv("QDRANT_URL", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        
        print(f"Подключение к Qdrant: {qdrant_url}:{qdrant_port}")
        
        reviewer = CBRDocumentReviewer(
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            collection_name="cbr_microbusiness"
        )
        
        print("Парсинг документов с сайта ЦБ...")
        documents = reviewer.parse_documents_from_site(max_docs=30)
        print(f"Спарсено {len(documents)} документов")
        return {"documents": documents}

    @task
    def filter_new_docs(data):
        """Этап 2: Фильтрация новых документов"""
        documents = data["documents"]
        
        if not documents:
            print("Нет документов для фильтрации")
            return {"new_docs": []}
        
        print("Инициализация парсера для фильтрации...")
        qdrant_url = os.getenv("QDRANT_URL", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        
        reviewer = CBRDocumentReviewer(
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            collection_name="cbr_microbusiness"
        )
        
        print("Фильтрация новых документов...")
        new_docs = reviewer.filter_new_documents(documents)
        print(f"Найдено {len(new_docs)} новых документов")
        return {"new_docs": new_docs}

    @task
    def filter_relevant_docs(data):
        """Этап 3: Фильтрация релевантных документов через LLM"""
        new_docs = data["new_docs"]
        
        if not new_docs:
            print("Нет новых документов для проверки релевантности")
            return {"relevant_docs": []}
        
        print("Инициализация парсера для проверки релевантности...")
        qdrant_url = os.getenv("QDRANT_URL", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        
        reviewer = CBRDocumentReviewer(
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            collection_name="cbr_microbusiness"
        )
        
        print("Проверка релевантности через LLM...")
        relevant_docs = reviewer.filter_relevant_documents(new_docs)
        print(f"Найдено {len(relevant_docs)} релевантных документов")
        return {"relevant_docs": relevant_docs}

    @task
    def parse_pdfs(data):
        """Этап 4: Парсинг PDF файлов"""
        relevant_docs = data["relevant_docs"]
        
        if not relevant_docs:
            print("Нет релевантных документов для парсинга PDF")
            return []
        
        print("Инициализация парсера для парсинга PDF...")
        qdrant_url = os.getenv("QDRANT_URL", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        
        reviewer = CBRDocumentReviewer(
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            collection_name="cbr_microbusiness"
        )
        
        print(f"Парсинг {len(relevant_docs)} PDF файлов...")
        pdf_texts = reviewer.parse_pdfs(relevant_docs)
        print(f"Распарсено {len(pdf_texts)} PDF файлов")
        return pdf_texts

    @task
    def create_fragments_task(text_data):
        """Этап 6: Создание фрагментов через fragments_creator"""
        if not text_data:
            print("Нет данных для обработки")
            return {"status": "empty", "fragments": [], "metadata": {}}
        
        print(f"Обработка {len(text_data)} документов через fragments_creator...")
        result = asyncio.run(create_fragments(
            parser_name='centralbank',
            text_data=text_data,
            source='cbr_microbusiness'
        ))
        
        if result.get("status") == "success":
            print(f"Создано {len(result.get('fragments', []))} фрагментов")
        else:
            print(f"Статус: {result.get('status')}")
        
        return result

    @task
    def save_to_csv(fragments_data):
        """Этап 7: Сохранение фрагментов в CSV файл"""
        from tools.csv_writer import save_fragments_to_csv
        
        if fragments_data.get("status") in ["empty", "no_fragments"]:
            print("Нет фрагментов для сохранения")
            return {"status": "skipped", "message": "Нет фрагментов для сохранения"}
        
        fragments = fragments_data.get("fragments", [])
        
        if not fragments:
            print("Список фрагментов пуст")
            return {"status": "skipped", "message": "Список фрагментов пуст"}

        documents = []
        for fragment in fragments:
            title = fragment.get("TITLE", "")
            display_body = fragment.get("DISPLAY_BODY", "")
            
            doc = {
                "knowledge": display_body.strip() if display_body else "",
                "title": title if title else ""
            }
            documents.append(doc)
        
        print(f"Сохранение {len(documents)} документов в CSV...")
        
        result = save_fragments_to_csv(documents)
        
        if result.get("status") == "success":
            print(f"Успешно сохранено {result.get('saved_count', 0)} документов в CSV: {result.get('csv_path', '')}")
        else:
            print(f"Ошибка при сохранении: {result.get('message', '')}")
        
        return result

    @task
    def upload_to_bot_service(fragments_data):
        """Этап 8: Отправка фрагментов в бот-сервис для ML"""
        from tools.csv_writer import normalize_text
        
        bot_service_url = os.getenv("BOT_SERVICE_URL", "http://bot-service:8003")
        upload_endpoint = f"{bot_service_url}/knowledge/upload"
        
        if fragments_data.get("status") in ["empty", "no_fragments"]:
            print("Нет фрагментов для отправки в бот-сервис")
            return {"status": "skipped", "message": "Нет фрагментов для отправки"}
        
        fragments = fragments_data.get("fragments", [])
        
        if not fragments:
            print("Список фрагментов пуст")
            return {"status": "skipped", "message": "Список фрагментов пуст"}

        documents = []
        for fragment in fragments:
            title = normalize_text(fragment.get("TITLE", ""))
            display_body = normalize_text(fragment.get("DISPLAY_BODY", ""))

            if not display_body or not isinstance(display_body, str) or len(display_body.strip()) == 0:
                continue

            doc = {
                "knowledge": display_body.strip() 
            }

            if title and isinstance(title, str) and len(title.strip()) > 0:
                doc["title"] = title.strip()
            
            documents.append(doc)
        
        if not documents:
            print("После фильтрации не осталось документов для отправки")
            return {"status": "skipped", "message": "Нет валидных документов"}

        payload = {
            "source": "cbr_microbusiness",
            "documents": documents
        }
        
        try:
            print(f"Отправка {len(documents)} документов в бот-сервис: {upload_endpoint}")
            response = httpx.post(
                upload_endpoint,
                json=payload,
                timeout=300.0
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"Успешно отправлено в бот-сервис: {result.get('imported', 0)} документов")
            print(f"Сообщение: {result.get('message', '')}")
            
            return {
                "status": "success",
                "imported": result.get("imported", 0),
                "message": result.get("message", ""),
                "source": result.get("source", "cbr_microbusiness")
            }
        except httpx.HTTPError as e:
            error_msg = f"Ошибка HTTP при отправке в бот-сервис: {e}"
            print(error_msg)
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Ошибка при отправке в бот-сервис: {e}"
            print(error_msg)
            return {"status": "error", "message": error_msg}

    documents_data = parse_documents()
    new_docs_data = filter_new_docs(documents_data)
    relevant_docs_data = filter_relevant_docs(new_docs_data)
    pdf_texts = parse_pdfs(relevant_docs_data)
    fragments_data = create_fragments_task(pdf_texts)
    csv_result = save_to_csv(fragments_data)
    upload_result = upload_to_bot_service(fragments_data)
