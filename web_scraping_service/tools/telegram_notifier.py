import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


def send_telegram_message(
    message: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None
) -> bool:
    """
    Отправляет сообщение в Telegram чат через бота
    
    Args:
        message: Текст сообщения
        bot_token: Токен Telegram бота (если не указан, берется из TG_BOT_API)
        chat_id: ID чата (если не указан, берется из TG_CHAT_ID)
    
    Returns:
        True если сообщение отправлено успешно, False в противном случае
    """
    bot_token = bot_token or os.getenv("TG_BOT_API")
    chat_id = chat_id or os.getenv("TG_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.warning("TG_BOT_API или TG_CHAT_ID не установлены, уведомление не отправлено")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            logger.info("Уведомление успешно отправлено в Telegram")
            return True
    except httpx.HTTPError as e:
        logger.error(f"Ошибка HTTP при отправке в Telegram: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при отправке в Telegram: {e}")
        return False


def format_airflow_error_message(
    dag_id: str,
    task_id: str,
    execution_date: str,
    error_message: str,
    log_url: Optional[str] = None
) -> str:
    """
    Форматирует сообщение об ошибке для отправки в Telegram
    
    Args:
        dag_id: ID DAG'а
        task_id: ID задачи
        execution_date: Дата выполнения
        error_message: Сообщение об ошибке
        log_url: URL логов (опционально)
    
    Returns:
        Отформатированное сообщение
    """
    message = f"<b>Ошибка в Airflow</b>\n\n"
    message += f"<b>DAG:</b> {dag_id}\n"
    message += f"<b>Задача:</b> {task_id}\n"
    message += f"<b>Дата выполнения:</b> {execution_date}\n\n"
    message += f"<b>Ошибка:</b>\n<code>{error_message[:1000]}</code>"
    
    if log_url:
        message += f"\n\n<a href='{log_url}'>Посмотреть логи</a>"
    
    return message

