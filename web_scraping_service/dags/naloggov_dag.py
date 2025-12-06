"""
DAG для парсинга сайта nalog.gov.ru
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
import sys
from pathlib import Path
import asyncio

sys.path.append(str(Path(__file__).parent.parent))

from parsers.naloggov.nalog_urls import NalogGovParser
from parsers.naloggov.nalog_main import NalogAsyncParser
from parsers.parser_wrapper import create_fragments, send_to_api
from dags.telegram_callbacks import telegram_on_failure_callback
import os
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
    'naloggov_parser',
    default_args=default_args,
    description='Парсинг сайта nalog.gov.ru',
    schedule_interval=None,  # Только вручную
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['naloggov', 'parsing', 'tax'],
)


with dag:
    @task
    def get_urls():
        """Этап 1: Получение списка URL с nalog.gov.ru"""
        print("Получение списка URL с nalog.gov.ru...")
        url_parser = NalogGovParser()
        urls = url_parser.parse_all()
        
        if not urls:
            print("Не найдено URL для парсинга")
            return []
        
        url_list = list(urls) if isinstance(urls, set) else urls
        print(f"Найдено {len(url_list)} URL")
        return url_list

    @task
    def parse_urls(urls):
        """Этап 2: Парсинг всех страниц"""
        if not urls:
            print("Нет URL для парсинга")
            return []
        
        print(f"Парсинг {len(urls)} страниц...")
        async_parser = NalogAsyncParser(concurrent_limit=5)
        texts = asyncio.run(async_parser.parse_urls(urls))
        print(f"Распарсено {len(texts)} страниц")
        return texts

    @task
    def create_fragments_task(text_data):
        """Этап 3: Создание фрагментов через fragments_creator"""
        if not text_data:
            print("Нет данных для обработки")
            return {"status": "empty", "fragments": [], "metadata": {}}
        
        print(f"Обработка {len(text_data)} документов через fragments_creator...")
        result = asyncio.run(create_fragments(
            parser_name='naloggov',
            text_data=text_data,
            source='nalog_gov_ru'
        ))
        
        if result.get("status") == "success":
            print(f"Создано {len(result.get('fragments', []))} фрагментов")
        else:
            print(f"Статус: {result.get('status')}")
        
        return result

    @task
    def save_to_csv(fragments_data):
        """Этап 4: Сохранение фрагментов в CSV файл"""
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
        """Этап 5: Отправка фрагментов в бот-сервис для ML"""
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
            "source": "nalog_gov_ru",
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
                "source": result.get("source", "nalog_gov_ru")
            }
        except httpx.HTTPError as e:
            error_msg = f"Ошибка HTTP при отправке в бот-сервис: {e}"
            print(error_msg)
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Ошибка при отправке в бот-сервис: {e}"
            print(error_msg)
            return {"status": "error", "message": error_msg}

    urls = get_urls()
    parsed_texts = parse_urls(urls)
    fragments_data = create_fragments_task(parsed_texts)
    csv_result = save_to_csv(fragments_data)
    upload_result = upload_to_bot_service(fragments_data)
