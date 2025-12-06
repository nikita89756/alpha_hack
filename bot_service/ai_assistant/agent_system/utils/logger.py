"""Вспомогательные инструменты логирования с расширенной метаинформацией."""

import json
import logging
from typing import Any

logger = logging.getLogger("agents")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.propagate = False


class DetailedFormatter(logging.Formatter):
	"""Форматтер, который добавляет структурированную метаинформацию к логам."""

	def format(self, record: logging.LogRecord) -> str:
		"""Форматирует запись лога и добавляет выбранные extra-поля.

		Args:
			record (logging.LogRecord): Текущий лог, переданный обработчиком.

		Returns:
			str: Строка сообщения вместе с дополнительными атрибутами.
		"""
		msg = super().format(record)

		if hasattr(record, "title") or hasattr(record, "knowledge_preview") or hasattr(record, "user_id"):
			extra_parts = []
			if hasattr(record, "title"):
				extra_parts.append(f"title='{record.title}'")
			if hasattr(record, "knowledge_preview"):
				extra_parts.append(f"knowledge='{record.knowledge_preview}'")
			if hasattr(record, "user_id"):
				extra_parts.append(f"user_id={record.user_id}")

			if extra_parts:
				msg += f" | {' | '.join(extra_parts)}"

		try:
			standard = {
				"args","asctime","created","exc_info","exc_text","filename","funcName","levelname","levelno",
				"lineno","module","msecs","message","msg","name","pathname","process","processName","relativeCreated",
				"stack_info","thread","threadName"
			}
			extra_all = {
				k: v for k, v in record.__dict__.items()
				if k not in standard and not k.startswith("_") and k not in ("title","knowledge_preview","user_id")
			}
			if extra_all:
				def safe(val: Any) -> Any:
					"""Сериализует произвольные значения для JSON-логирования.

					Args:
						val (Any): Произвольное значение из extra-полей.

					Returns:
						Any: JSON-совместимое представление входа.
					"""
					try:
						json.dumps(val)
						return val
					except Exception:
						return str(val)
				extra_json = {k: safe(v) for k, v in extra_all.items()}
				msg += f" | extra={json.dumps(extra_json, ensure_ascii=False)}"
		except Exception:
			pass

		return msg

handler.setFormatter(DetailedFormatter("[%(asctime)s] %(levelname)s: %(message)s"))
logger.addHandler(handler)
