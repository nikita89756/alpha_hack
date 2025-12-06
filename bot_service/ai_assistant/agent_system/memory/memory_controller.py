"""Контроллер памяти для извлечения и дедупликации знаний из диалогов.

Класс MemoryController отвечает за извлечение фактов из диалогов,
их оценку, фильтрацию и дедупликацию перед сохранением в векторную базу.
Также он умеет проверять память на дубликаты и заменять устаревшие знания новыми.
"""

import json
import re
import time
from difflib import SequenceMatcher
from typing import Any, Dict, List, Literal, Sequence

from pydantic import BaseModel, Field, field_validator

from ..rag import RetrieverController
from ..config import AGENTS_CONFIG as config
from ..utils.logger import logger

from .promts import build_system_prompt, build_user_prompt

try:
    from langchain_openai import ChatOpenAI
    _HAS_LANGCHAIN = True
except ImportError:
    ChatOpenAI = object
    _HAS_LANGCHAIN = False

RoleLiteral = Literal["user", "operator"]


class KnowledgeItem(BaseModel):
    """Модель данных единицы знаний, извлеченной из диалога."""

    key: int = Field(..., description="Index of the fragment in the original dialogue")
    role: RoleLiteral = Field(..., description="Role of the fragment's author")
    title: str = Field(..., description="A short title for the knowledge")
    knowledge: str = Field(..., description="The formulation of the extracted knowledge")
    user_id: str = Field(..., description="User ID for grouping")

    @field_validator("title", "knowledge")
    @classmethod
    def _strip_spaces(cls, v: str) -> str:
        """Удаляет пробелы в начале и конце строковых полей.

        Аргументы:
            v: Исходная строка.

        Возвращает:
            Обрезанную строку.
        """
        return v.strip()

    @field_validator("key")
    @classmethod
    def _non_negative_key(cls, v: int) -> int:
        """Убеждается, что ключ — неотрицательное целое число.

        Аргументы:
            v: Проверяемое значение ключа.

        Возвращает:
            То же значение, гарантированно неотрицательное.

        Исключения:
            ValueError: Если ``v`` отрицательно.
        """
        if v < 0:
            raise ValueError("key cannot be negative")
        return v


class _LLMCandidate(BaseModel):
    """Внутренняя модель для представления кандидата знаний из LLM."""

    key: int
    role: RoleLiteral
    title: str
    knowledge: str
    keep: bool = Field(..., description="Recommendation to keep the knowledge")
    score: int = Field(..., ge=0, le=100, description="Suitability score")
    reason: str = Field(..., description="Justification for the score")


class MemoryController:
    """Контроллер для извлечения и дедупликации знаний из диалогов."""

    def __init__(
        self,
        llm: ChatOpenAI | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        api_key: str | None = None,
        model: str = config.model,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        request_timeout: int = 30,
        delay_between_requests: float = 0.5,
        max_retries: int = 3,
        min_keep_score: int = 70,
        rag_controller: RetrieverController | None = None,
    ) -> None:
        """Инициализирует MemoryController.

        Аргументы:
            llm: Необязательный заранее сконфигурированный экземпляр LangChain ChatOpenAI.
            base_url: Базовый URL API OpenRouter.
            api_key: API-ключ для OpenRouter.
            model: Имя модели, используемой для обработки.
            temperature: Температура генерации.
            max_tokens: Максимальное число токенов в ответе.
            request_timeout: Таймаут запроса в секундах.
            delay_between_requests: Пауза между повторными попытками.
            max_retries: Максимальное количество повторов.
            min_keep_score: Минимальный балл, чтобы сохранить знание.
            rag_controller: Контроллер RAG для работы с памятью.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_timeout = request_timeout
        self.delay_between_requests = delay_between_requests
        self.max_retries = max_retries
        self.min_keep_score = min_keep_score
        self.rag_controller = rag_controller

        if llm:
            self.llm = llm
        else:
            if not _HAS_LANGCHAIN:
                logger.error("langchain-openai is not installed. Please install it with 'pip install langchain-openai'")
                raise ImportError("langchain-openai is required. Please install it with 'pip install langchain-openai'")
            self.llm = ChatOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.request_timeout,
            )
        logger.info(f"MemoryController initialized with model: {self.model}")

    def extract_and_validate(self, dialogue: Sequence[Dict[str, str]], user_id: int = 0) -> List[KnowledgeItem]:
        """Извлекает, валидирует и дедуплицирует знания из диалога.

        Аргументы:
            dialogue: Набор сообщений в виде словарей с ключами ``role`` и ``content``.
            user_id: Идентификатор пользователя для группировки знаний.

        Возвращает:
            Список проверенных и отфильтрованных объектов KnowledgeItem.
        """
        if not dialogue:
            logger.warning("extract_and_validate called with an empty dialogue.")
            return []

        logger.info(f"Starting knowledge extraction user_id: {user_id} from a dialogue of {len(dialogue)} messages.")

        norm_dialogue = self._normalize_roles(dialogue)
        candidates = self._llm_extract_candidates(norm_dialogue)
        kept_candidates = self._filter_candidates(candidates)

        user_id_str = str(user_id) if user_id is not None else ""
        items = [KnowledgeItem(user_id=user_id_str, **k) for k in kept_candidates]
        logger.info(f"Extracted {len(items)} high-quality knowledge items.")

        if self.rag_controller and items:
            self._deduplicate_and_update_memory(items, user_id)

        return items

    def _deduplicate_and_update_memory(self, new_items: List[KnowledgeItem], user_id: int) -> None:
        """Ищет дубликаты в памяти и при необходимости заменяет старые знания новыми.

        Аргументы:
            new_items: Список новых элементов знаний для проверки.
            user_id: Идентификатор пользователя для фильтрации поиска в памяти.

        Возвращает:
            None. Побочные эффекты: добавление или удаление точек памяти.
        """
        if not self.rag_controller:
            logger.warning("RAG controller not set, skipping deduplication.")
            return

        logger.info(f"Starting memory deduplication for user_id: {user_id}")

        items_to_add: List[KnowledgeItem] = []

        for item in new_items:
            try:
                similar_records = self.rag_controller.search_long_term_memory(
                    query=item.knowledge,
                    user_id=user_id,
                    limit=5,
                )
                candidates = self._prepare_candidate_payloads(similar_records)[:3]
                heuristic_duplicates = set(self._find_heuristic_duplicates(item, candidates))

                remaining_candidates = [
                    candidate for candidate in candidates if candidate.get("id") not in heuristic_duplicates
                ]
                llm_duplicates = set(self._detect_duplicates_with_llm(item, remaining_candidates))
                duplicate_ids = heuristic_duplicates | llm_duplicates

                for duplicate_id in duplicate_ids:
                    if duplicate_id is None:
                        continue
                    deleted = self.rag_controller.delete_memory_by_id(duplicate_id)
                    if deleted:
                        logger.info(
                            "Deleted duplicate memory with ID %s before inserting '%s'",
                            duplicate_id,
                            item.title,
                        )
                    else:
                        logger.warning("Failed to delete duplicate memory with ID %s", duplicate_id)

                items_to_add.append(item)

            except Exception as e:
                logger.exception(
                    f"Error during knowledge deduplication for user_id {user_id}: {e}"
                )
                items_to_add.append(item)

        if not items_to_add:
            logger.info(
                "No new knowledge items to insert for user_id=%s (all filtered out).",
                user_id,
            )
            return

        try:
            payloads = [
                {
                    "user_id": user_id,
                    "title": it.title,
                    "knowledge": it.knowledge,
                    "key": it.key,
                    "role": it.role,
                }
                for it in items_to_add
            ]
            self.rag_controller.add_to_long_term_memory(payloads)
            logger.info(
                "Inserted %d new memories for user_id=%s",
                len(payloads),
                user_id,
            )
        except Exception as e:
            logger.exception(f"Failed to insert new memories: {e}")

    def _detect_duplicates_with_llm(
        self,
        new_item: KnowledgeItem,
        candidates: Sequence[Dict[str, Any]],
    ) -> List[int]:
        """Запрашивает у LLM, дублируют ли кандидаты новое знание."""

        if not candidates:
            return []

        candidate_blocks: List[str] = []
        candidate_id_by_index: Dict[int, int] = {}
        candidate_id_by_str: Dict[str, int] = {}

        for idx, candidate in enumerate(candidates, start=1):
            cand_id = self._coerce_int(candidate.get("id"))
            if cand_id is None:
                continue
            title = candidate.get("title") or ""
            knowledge = candidate.get("knowledge") or ""
            candidate_id_by_index[idx] = cand_id
            candidate_id_by_str[str(cand_id)] = cand_id
            candidate_blocks.append(
                f"{idx}. id={cand_id}\n   title: {title}\n   knowledge: {knowledge}"
            )

        if not candidate_blocks:
            return []

        prompt = (
            "Ты определяешь, дублирует ли новое знание уже сохранённые факты. "
            "Если существующий факт описывает то же самое, что и новое знание "
            "(или отличается незначительно по формулировке), пометь его как дубликат.\n\n"
            f"НОВОЕ ЗНАНИЕ:\n- title: {new_item.title}\n- knowledge: {new_item.knowledge}\n\n"
            "СУЩЕСТВУЮЩИЕ ЗНАНИЯ:\n"
            f"{chr(10).join(candidate_blocks)}\n\n"
            "Ответь строго JSON вида {\"duplicate_indices\": [<номера>]} где номера соответствуют списку выше. "
            "Если дубликатов нет, верни пустой список."
        )

        try:
            response = self.llm.invoke(
                [
                    {
                        "role": "system",
                        "content": "Ты аккуратно определяешь дубликаты фактов и отвечаешь только JSON.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )
            raw_text = getattr(response, "content", "") or (response if isinstance(response, str) else "")
            parsed = self._safe_json_extract(raw_text)
            duplicate_indices = (
                parsed.get("duplicate_indices")
                or parsed.get("duplicates")
                or parsed.get("duplicate_ids")
                or []
            )
        except Exception as e:
            logger.warning("LLM duplicate check failed: %s", e)
            return []

        resolved_ids: List[int] = []
        if not isinstance(duplicate_indices, (list, tuple)):
            logger.debug("LLM returned unexpected duplicate format: %s", duplicate_indices)
            return resolved_ids

        for entry in duplicate_indices:
            idx = self._coerce_int(entry)
            if idx in candidate_id_by_index:
                resolved_ids.append(candidate_id_by_index[idx])
                continue
            entry_str = str(entry).strip()
            if entry_str in candidate_id_by_str:
                resolved_ids.append(candidate_id_by_str[entry_str])

        return resolved_ids

    @staticmethod
    def _find_heuristic_duplicates(
        new_item: KnowledgeItem,
        candidates: Sequence[Dict[str, Any]],
    ) -> List[int]:
        """Использует детерминированные эвристики до обращения к LLM, чтобы поймать явные дубликаты."""

        duplicates: List[int] = []
        new_title_norm = MemoryController._normalize_text(new_item.title)
        new_knowledge_norm = MemoryController._normalize_text(new_item.knowledge)

        for candidate in candidates:
            candidate_id = MemoryController._coerce_int(candidate.get("id"))
            if candidate_id is None:
                continue

            candidate_title_norm = MemoryController._normalize_text(candidate.get("title") or "")
            candidate_knowledge_norm = MemoryController._normalize_text(candidate.get("knowledge") or "")

            exact_title_match = bool(candidate_title_norm and candidate_title_norm == new_title_norm)
            exact_knowledge_match = bool(candidate_knowledge_norm and candidate_knowledge_norm == new_knowledge_norm)

            overlap_ratio = MemoryController._token_overlap(new_knowledge_norm, candidate_knowledge_norm)
            similarity_ratio = MemoryController._string_similarity(new_knowledge_norm, candidate_knowledge_norm)

            if (
                exact_title_match
                or exact_knowledge_match
                or similarity_ratio >= 0.65
                or overlap_ratio >= 0.8
            ):
                duplicates.append(candidate_id)

        return duplicates

    @staticmethod
    def _extract_record_payload(record: Any) -> Dict[str, Any]:
        """Возвращает полезную нагрузку из результата поиска независимо от его структуры."""

        if record is None:
            return {}

        if isinstance(record, dict):
            payload = record.get("payload")
            if isinstance(payload, dict) and payload:
                return payload
            return record

        payload = getattr(record, "payload", None)
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _prepare_candidate_payloads(
        records: Sequence[Any],
    ) -> List[Dict[str, Any]]:
        """Нормализует результаты поиска перед проверкой дубликатов в LLM."""

        prepared: List[Dict[str, Any]] = []
        for record in records:
            payload = MemoryController._extract_record_payload(record)
            if not payload:
                continue
            candidate_id = payload.get("id")
            if candidate_id is None:
                if isinstance(record, dict):
                    candidate_id = record.get("id")
                else:
                    candidate_id = getattr(record, "id", None)
            if candidate_id is None:
                continue
            prepared.append(
                {
                    "id": candidate_id,
                    "title": payload.get("title") or "",
                    "knowledge": payload.get("knowledge") or payload.get("content") or "",
                }
            )
        return prepared

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        """По возможности преобразует произвольное значение в целочисленный идентификатор."""

        if value is None:
            return None
        if isinstance(value, int):
            return value
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Нормализует текст перед сравнением."""

        if not text:
            return ""
        lowered = text.lower()
        cleaned = re.sub(r"[^0-9a-z\u0400-\u04ff ]+", " ", lowered)
        return " ".join(cleaned.split())

    @staticmethod
    def _token_overlap(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        left_tokens = set(left.split())
        right_tokens = set(right.split())
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))

    @staticmethod
    def _string_similarity(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left, right).ratio()

    @staticmethod
    def _normalize_roles(dialogue: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
        """Приводит исходный диалог к паре ``role``/``content``.

        Аргументы:
            dialogue: Последовательность словарей роль/контент.

        Возвращает:
            Очищенный список, где роли ограничены ``user`` и ``operator``, а пустые сообщения удалены.
        """
        role_map = {
            "user": "user", "client": "user",
            "operator": "operator", "assistant": "operator",
            "agent": "operator", "support": "operator", "system": "operator",
        }
        result = []
        for m in dialogue:
            role = (m.get("role") or "").strip().lower()
            content = (m.get("content") or "").strip()
            if not content:
                continue
            role_norm = role_map.get(role, "operator")
            result.append({"role": role_norm, "content": content})
        return result

    def _llm_extract_candidates(self, dialogue: Sequence[Dict[str, str]]) -> List[_LLMCandidate]:
        """Получает от LLM кандидатов знаний вместе с оценкой пригодности.

        Аргументы:
            dialogue: Нормализованный диалог, добавляемый в промпт.

        Возвращает:
            Список структурированных кандидатов, предложенных LLM.

        Исключения:
            RuntimeError: Если LLM не ответил после всех повторных попыток.
        """
        sys_prompt = build_system_prompt()
        user_prompt = build_user_prompt(dialogue)
        logger.debug("Sending request to LLM for knowledge extraction.")

        attempt = 0
        last_error: Exception | None = None
        while attempt < self.max_retries:
            try:
                resp = self.llm.invoke([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ])

                raw_text = getattr(resp, "content", "") or (resp if isinstance(resp, str) else "")
                data = self._safe_json_extract(raw_text)

                candidates_data = data.get("candidates", [])
                if not isinstance(candidates_data, list):
                    logger.warning(f"LLM returned 'candidates' not as a list: {type(candidates_data)}")
                    return []

                return [_LLMCandidate(**c) for c in candidates_data]
            except Exception as e:
                last_error = e
                attempt += 1
                logger.warning(f"LLM extraction attempt {attempt}/{self.max_retries} failed: {e}")
                time.sleep(self.delay_between_requests * (attempt + 1))

        logger.error(f"Failed to get candidates from LLM after {self.max_retries} attempts.")
        raise RuntimeError(f"Could not get candidates from LLM after {self.max_retries} attempts: {last_error}") \
        from last_error

    def _filter_candidates(self, candidates: Sequence[_LLMCandidate]) -> List[Dict[str, Any]]:
        """Фильтрует кандидатов по качеству и релевантности.

        Аргументы:
            candidates: Последовательность, возвращенная LLM.

        Возвращает:
            Кандидатов, прошедших пороги keep/score и базовые эвристики.
        """
        kept = []
        for c in candidates:
            if not c.keep or c.score < self.min_keep_score:
                logger.debug(f"Filtering out candidate '{c.title}' with score {c.score} and keep={c.keep}.")
                continue

            if not all([c.title, c.knowledge]):
                logger.debug(f"Filtering out candidate with missing fields: {c.title}")
                continue

            text_lower = c.knowledge.lower()
            title_lower = c.title.lower()

            business_keywords = [
                "налогообложени", "усп", "осно", "патент", "ип", "ооо", "самозанят",
                "выручка", "доход", "оборот", "налог", "ставка", "система налого",
                "тип бизнеса", "статус бизнеса", "деятельность"
            ]
            is_business_info = any(keyword in text_lower or keyword in title_lower for keyword in business_keywords)

            ephemeral_markers = ["сейчас", "прямо сейчас", "в данный момент", "сегодня"]
            evergreen_markers = ["кажд", "обычно", "регулярно", "как правило"]

            is_ephemeral = any(mark in text_lower for mark in ephemeral_markers)
            is_evergreen = any(mark in text_lower for mark in evergreen_markers)


            if is_ephemeral and not is_evergreen and not is_business_info:
                logger.debug(f"Filtering out ephemeral candidate: {c.title}")
                continue

            kept.append({
                "key": c.key,
                "role": c.role,
                "title": c.title.strip()[:120],
                "knowledge": c.knowledge.strip(),
            })
        return kept

    @staticmethod
    def _safe_json_extract(text: str) -> Dict[str, Any]:
        """Безопасно извлекает JSON из текста ответа модели.

        Аргументы:
            text: Исходная строка ответа LLM.

        Возвращает:
            Словарь с ключом ``candidates`` (пустой при ошибке парсинга).
        """
        if not text:
            return {"candidates": []}

        json_match = re.search(r"\s*(\{.*\}|\[.*\])\s*", text, re.DOTALL)
        if not json_match:
            logger.warning("No JSON object or array found in the LLM response.")
            return {"candidates": []}

        json_str = json_match.group(1)

        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                return {"candidates": data}
            if isinstance(data, dict):
                return data if "candidates" in data else {"candidates": [data]}
            return {"candidates": []}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from LLM response: {e}. Content: '{json_str[:200]}...'",
            extra={"raw_text": text})
            repaired_str = json_str.replace("\n", " ").replace("\r", " ").replace("True", "true"). \
            replace("False", "false")
            try:
                data = json.loads(repaired_str)
                if isinstance(data, list):
                    return {"candidates": data}
                return data if isinstance(data, dict) and "candidates" in data else {"candidates": []}
            except json.JSONDecodeError:
                logger.error("JSON repair failed.", extra={"raw_text": text})

        return {"candidates": []}

__all__ = ["MemoryController", "KnowledgeItem"]
