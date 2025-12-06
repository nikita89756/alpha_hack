"""
Callback функции для отправки уведомлений в Telegram при ошибках в Airflow
"""
import sys
import logging
from pathlib import Path
from airflow.models import TaskInstance
from airflow.utils.context import Context

sys.path.append(str(Path(__file__).parent.parent))

from tools.telegram_notifier import send_telegram_message, format_airflow_error_message

logger = logging.getLogger(__name__)


def telegram_on_failure_callback(context: Context):
    """
    Callback функция, вызываемая при ошибке задачи в Airflow
    
    Args:
        context: Контекст Airflow с информацией о задаче
    """
    try:
        task_instance: TaskInstance = context.get('task_instance')
        dag = context.get('dag')
        dag_run = context.get('dag_run')
        
        dag_id = dag.dag_id if dag else 'unknown'
        task_id = task_instance.task_id if task_instance else 'unknown'
       
        execution_date = context.get('execution_date') or context.get('data_interval_start')
        if execution_date:
            exec_date_str = execution_date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            exec_date_str = 'N/A'
        
        exception = context.get('exception')
        error_message = "Неизвестная ошибка"
        
        if exception:
            error_message = str(exception)
        elif task_instance:
            try:
                log_lines = task_instance.log.read()
                if log_lines:
                    lines = log_lines.split('\n')
                    error_lines = [line for line in lines if 'ERROR' in line or 'Exception' in line or 'Traceback' in line]
                    if error_lines:
                        error_message = '\n'.join(error_lines[-10:])
                    else:
                        error_message = log_lines[-500:] if len(log_lines) > 500 else log_lines
            except Exception as e:
                logger.warning(f"Не удалось прочитать логи: {e}")
                error_message = f"Ошибка при чтении логов: {str(e)}"
        
        message = format_airflow_error_message(
            dag_id=dag_id,
            task_id=task_id,
            execution_date=exec_date_str,
            error_message=error_message
        )
        
        success = send_telegram_message(message)
        
        if success:
            logger.info(f"Уведомление об ошибке отправлено в Telegram для задачи {dag_id}.{task_id}")
        else:
            logger.warning(f"Не удалось отправить уведомление в Telegram для задачи {dag_id}.{task_id}")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления в Telegram: {e}", exc_info=True)

