"""
DAG для парсинга сайта Альфа-Банка
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
import sys
from pathlib import Path
import os

sys.path.append(str(Path(__file__).parent.parent))

from parsers.alfabank.sme_check import check_urls
from parsers.alfabank.sme import AlfaBankParser
from parsers.parser_wrapper import create_fragments
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
    'alfabank_parser',
    default_args=default_args,
    description='Парсинг сайта Альфа-Банка для SME',
    schedule_interval=None,  # Только вручную
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['alfabank', 'parsing'],
)


with dag:
    @task
    def check_alfabank_urls():
        """Этап 1: Проверка URL Альфа-Банка"""
        print("Проверка URL Альфа-Банка...")
        result = check_urls()
        if result:
            print("URL проверены успешно")
        else:
            print("Проблема с URL")
        return result

    @task
    def parse_page_1():
        """Этап 2: Парсинг страницы /sme/start/"""
        print("Парсинг страницы /sme/start/...")
        try:
            parser = AlfaBankParser()
            result = parser.parse_page_1_start()
            if not result or len(result.strip()) < 100:
                raise ValueError(f"Получен слишком короткий результат: {len(result)} символов")
            print(f"Получен текстовый блок с первой страницы, длина: {len(result)} символов")
            return result
        except Exception as e:
            print(f"Ошибка при парсинге страницы 1: {e}")
            raise

    @task
    def parse_page_2():
        """Этап 3: Парсинг страницы /sme/raschetnyj-schet/"""
        print("Парсинг страницы /sme/raschetnyj-schet/...")
        try:
            parser = AlfaBankParser()
            result = parser.parse_page_2_raschetnyj_schet()
            if not result or len(result.strip()) < 100:
                raise ValueError(f"Получен слишком короткий результат: {len(result)} символов")
            print(f"Получен текстовый блок со второй страницы, длина: {len(result)} символов")
            return result
        except Exception as e:
            print(f"Ошибка при парсинге страницы 2: {e}")
            raise

    @task
    def combine_results(result_1, result_2):
        """Этап 4: Объединение результатов в список текстовых блоков"""
        print("Объединение результатов...")
        combined = [result_1, result_2]
        print(f"Создано {len(combined)} текстовых документа для обработки")
        return combined

    @task
    def create_fragments_task(text_data):
        """Этап 5: Создание фрагментов через fragments_creator"""
        if not text_data:
            print("Нет данных для обработки")
            return {"status": "empty", "fragments": [], "metadata": {}}

        print(f"Получено {len(text_data)} текстовых документа от парсера")

        filtered_data = [text.strip() for text in text_data if text and text.strip()]
        
        print(f"После фильтрации осталось {len(filtered_data)} документов")
        
        if not filtered_data:
            print("После фильтрации не осталось данных")
            return {"status": "empty", "fragments": [], "metadata": {}}
        
        # Выводим информацию о размере документов
        for idx, doc in enumerate(filtered_data, 1):
            print(f"Документ {idx}: {len(doc)} символов, {len(doc.split())} слов")
        
        result = asyncio.run(create_fragments(
            parser_name='alfabank',
            text_data=filtered_data, 
            source='alfabank_sme'
        ))
        
        if result.get("status") == "success":
            print(f"Создано {len(result.get('fragments', []))} фрагментов")
        else:
            print(f"Статус: {result.get('status')}")
        
        return result

    @task
    def save_to_csv(fragments_data):
        """Этап 6: Сохранение фрагментов в CSV файл"""
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
        """Этап 7: Отправка фрагментов в бот-сервис для ML"""
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
            "source": "alfabank_sme",
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
                "source": result.get("source", "alfabank_sme")
            }
        except httpx.HTTPError as e:
            error_msg = f"Ошибка HTTP при отправке в бот-сервис: {e}"
            print(error_msg)
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Ошибка при отправке в бот-сервис: {e}"
            print(error_msg)
            return {"status": "error", "message": error_msg}

    urls_ok = check_alfabank_urls()

    page1_data = parse_page_1()
    page2_data = parse_page_2()

    urls_ok >> [page1_data, page2_data]
    
    combined_data = combine_results(page1_data, page2_data)
    fragments_data = create_fragments_task(combined_data)
    csv_result = save_to_csv(fragments_data)
    upload_result = upload_to_bot_service(fragments_data)
