"""
Контроллер для взаимодействия с векторной базой данных Qdrant с использованием плотных эмбеддингов
как для коллекции базы знаний, так и для долгосрочной памяти.
"""

import contextlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import uuid
import torch
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct
from sentence_transformers import SentenceTransformer
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from ai_assistant.agent_system.utils.logger import logger

try:
    from tqdm import tqdm as _tqdm
except Exception:
    _tqdm = None


def _mean_pool(hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """
    Среднее по токеновым эмбеддингам с учётом attention mask.

    Аргументы:
        hidden_states: Эмбеддинги токенов [batch_size, seq_len, hidden_dim]
        attention_mask: Attention mask [batch_size, seq_len]

    Возвращает:
        Усреднённые эмбеддинги [batch_size, hidden_dim]
    """
    mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
    sum_embeddings = torch.sum(hidden_states * mask_expanded, dim=1)
    sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
    return sum_embeddings / sum_mask


def _l2_normalize_torch(tensor: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
    """
    L2-нормализация для тензоров torch.

    Аргументы:
        tensor: Входной тензор для нормализации
        eps: Маленькое значение эпсилон для избежания деления на ноль

    Возвращает:
        L2-нормализованный тензор
    """
    norm = torch.norm(tensor, p=2, dim=-1, keepdim=True)
    return tensor / torch.clamp(norm, min=eps)


def _nullcontext() -> contextlib.AbstractContextManager[None]:
    """Пустой контекстный менеджер для совместимости."""
    from contextlib import nullcontext
    return nullcontext()


class BertSentenceEncoder:
    """Обёртка над Transformer-энкодером, ведущая себя как SentenceTransformer."""
    def __init__(
        self,
        model_and_tokenizer: Tuple[PreTrainedModel, PreTrainedTokenizerBase],
        device: str | None = None,
        pooling: str = "mean",
        normalize: bool = True,
        max_length: int = 256,
        default_batch_size: int = 32,
        use_fp16: bool = True,
        pad_to_multiple_of: int | None = 8,
    ) -> None:
        model, tokenizer = model_and_tokenizer
        self.model: PreTrainedModel = model
        self.tokenizer: PreTrainedTokenizerBase = tokenizer

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        self.pooling = pooling.lower()
        if self.pooling not in {"mean", "cls"}:
            raise ValueError("pooling должен быть 'mean' или 'cls'")

        self.normalize = normalize
        self.max_length = int(max_length)
        self.default_batch_size = int(default_batch_size)
        self.use_fp16 = bool(use_fp16 and self.device.type == "cuda")
        self.pad_to_multiple_of = pad_to_multiple_of

        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def encode(
        self,
        sentences: str | Sequence[str],
        batch_size: int | None = None,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
        **_: dict,
    ) -> np.ndarray | torch.Tensor:
        """Вернёт массив эмбеддингов: (N, D) или (D,) для одиночной строки."""
        single_input = isinstance(sentences, str)
        if single_input:
            sentences = [sentences]

        sentences = list(sentences)
        if len(sentences) == 0:
            out = np.zeros((0, self.get_sentence_embedding_dimension()), dtype="float32")
            return out if convert_to_numpy else torch.from_numpy(out)

        bs = batch_size or self.default_batch_size
        rng = range(0, len(sentences), bs)

        if show_progress_bar and _tqdm is not None:
            rng = _tqdm(rng, desc="Encoding (BERT)")

        chunks = []
        amp_ctx = (lambda: torch.amp.autocast("cuda")) if self.use_fp16 else _nullcontext

        for i in rng:
            batch = sentences[i : i + bs]
            toks = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
                pad_to_multiple_of=self.pad_to_multiple_of,
            )
            toks = {k: v.to(self.device) for k, v in toks.items()}

            with amp_ctx():
                outputs = self.model(**toks, return_dict=True)
                if self.pooling == "cls" and getattr(outputs, "pooler_output", None) is not None:
                    pooled = outputs.pooler_output
                else:
                    pooled = _mean_pool(outputs.last_hidden_state, toks["attention_mask"])

            pooled = pooled.detach().to("cpu", dtype=torch.float32)

            if self.normalize:
                pooled = _l2_normalize_torch(pooled)

            chunks.append(pooled)

        embs = torch.vstack(chunks)

        if single_input:
            embs = embs[0]

        if convert_to_numpy:
            return embs.numpy()
        return embs

    def __call__(self, *args: object, **kwargs: object) -> torch.Tensor | np.ndarray:
        return self.encode(*args, **kwargs)

    def get_sentence_embedding_dimension(self) -> int:
        """Размерность эмбеддинга (обычно hidden_size модели)."""
        hidden = getattr(getattr(self.model, "config", None), "hidden_size", None)
        if hidden:
            return int(hidden)
        v = self.encode("ping", batch_size=1, show_progress_bar=False)
        return int(np.asarray(v).reshape(-1).shape[0])


class RetrieverController:
    """Контроллер для управления поиском в Qdrant с помощью плотных энкодеров."""

    def __init__(
        self,
        client: QdrantClient,
        dense_encoder: SentenceTransformer | Tuple[PreTrainedModel, PreTrainedTokenizerBase],
    ) -> None:
        """
        Инициализация контроллера поиска.

        Аргументы:
            client: Клиент для подключения к Qdrant.
            dense_encoder: Модель для создания плотных векторов.
        """
        self.client = client
        if isinstance(dense_encoder, tuple):
            self.dense_encoder = BertSentenceEncoder(dense_encoder)
        else:
            self.dense_encoder = dense_encoder

        self.kb_collection = "knowledge_base"
        self.ltm_collection = "long_term_memory"
        self.ltm_vector_name = self._detect_ltm_vector_name()
        self._title_weight = 0.8

        logger.info("RetrieverController initialized.")

    def _encode_weighted_text(self, title: str | None, body: str | None) -> List[float]:
        """
        Комбинирует эмбеддинги заголовка и тела с использованием взвешенных сумм.

        Аргументы:
            title: Необязательный текст заголовка.
            body: Необязательный основной текст.

        Возвращает:
            Плотный вектор в виде Python-списка.
        """
        components: List[Tuple[str, float]] = []
        if title:
            components.append((title, self._title_weight))
        if body:
            body_weight = 1.0 - self._title_weight if components else 1.0
            components.append((body, body_weight))

        if not components:
            components.append(("", 1.0))
        elif len(components) == 1:
            text, _ = components[0]
            components = [(text, 1.0)]

        combined: np.ndarray | None = None
        for text, weight in components:
            vec = self.dense_encoder.encode(text).astype(np.float32)
            weighted_vec = vec * weight
            combined = weighted_vec if combined is None else combined + weighted_vec

        if combined is None:
            raise RuntimeError("Failed to compute combined vector in _encode_weighted_text")
        return combined.tolist()

    def _detect_ltm_vector_name(self) -> str | None:
        """
        Анализирует конфиг коллекции и выбирает имя вектора при необходимости.

        Возвращает:
            Предпочтительное имя вектора или ``None``, если используются безымянные векторы.
        """

        preferred_order = ("dense", "default")
        try:
            collection = self.client.get_collection(collection_name=self.ltm_collection)
            vectors_cfg = collection.config.params.vectors
            if isinstance(vectors_cfg, dict):
                available_names = list(vectors_cfg.keys())
                for name in preferred_order:
                    if name in available_names:
                        logger.info("Using '%s' vector name for long-term memory.", name)
                        return name
                if available_names:
                    chosen = available_names[0]
                    logger.info("Using detected vector name '%s' for long-term memory.", chosen)
                    return chosen
            else:
                logger.info(
                    "Коллекция долгосрочной памяти использует один безымянный вектор; запросы будут без указания имени вектора."
                )
                return None
        except Exception as exc:
            logger.warning("Не удалось проанализировать конфиг векторов LTM коллекции: %s", exc)
        return "dense"

    def _ltm_upsert_payload(self, vector: List[float]) -> dict | List[float]:
        """
        Возвращает структуру payload, ожидаемую Qdrant при upsert.

        Аргументы:
            vector: Плотный вектор, вычисленный для записи памяти.

        Возвращает:
            Сопоставление с ключом-именем вектора или обычный вектор при отсутствии имени.
        """

        if self.ltm_vector_name:
            return {self.ltm_vector_name: vector}
        return vector

    def _ltm_query_vector(self, vector: List[float]) -> models.NamedVector | List[float]:
        """
        Подготавливает вектор запроса для поиска по долгосрочной памяти.

        Аргументы:
            vector: Плотный вектор для поиска.

        Возвращает:
            NamedVector, если коллекция мультиевекторная; иначе обычный вектор.
        """

        if self.ltm_vector_name:
            return models.NamedVector(name=self.ltm_vector_name, vector=vector)
        return vector

    @staticmethod
    def _format_ltm_results(points: Sequence[models.ScoredPoint]) -> List[Dict[str, Any]]:
        """
        Нормализует результаты поиска LTM в списки словарей.
        """

        formatted: List[Dict[str, Any]] = []
        for point in points:
            payload = point.payload or {}
            formatted.append(
                {
                    "id": payload.get("id") or point.id,
                    "title": payload.get("title") or "",
                    "knowledge": payload.get("knowledge") or payload.get("content") or "",
                    "score": point.score,
                    "user_id": payload.get("user_id"),
                    "source": payload.get("source") or "memory",
                    "payload": payload,
                }
            )
        return formatted

    def add_to_knowledge_base(self, documents: List[Dict[str, str]], source: str) -> None:
        """
        Adds documents to the knowledge base, checking for duplicates based on content.
        Only encodes and inserts documents that do not already exist.
        """
        doc_map: Dict[str, Dict[str, str]] = {}
        
        for doc in documents:
            content = doc.get("knowledge", "")
            if not content:
                continue
                
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, content))
            doc_map[doc_id] = doc

        if not doc_map:
            return

        try:
            existing_records = self.client.retrieve(
                collection_name=self.kb_collection,
                ids=list(doc_map.keys())
            )
            existing_ids = {record.id for record in existing_records}
        except Exception as e:
            logger.error(f"Failed to check duplicates: {e}")
            existing_ids = set()

        points_to_upsert: List[PointStruct] = []
        
        for doc_id, doc in doc_map.items():
            if doc_id in existing_ids:
                continue

            document_payload: Dict[str, Any] = {
                "knowledge": doc.get("knowledge", ""),
                "source": source,
                "id": doc_id,
            }

            doc_title = doc.get("title") or document_payload["knowledge"][:80]
            document_payload["title"] = doc_title

            dense_vector = self._encode_weighted_text(doc_title, document_payload["knowledge"])

            points_to_upsert.append(PointStruct(
                id=doc_id,
                vector={"default": dense_vector},
                payload=document_payload,
            ))

        if points_to_upsert:
            self.client.upsert(collection_name=self.kb_collection, points=points_to_upsert, wait=True)
            logger.info(f"Upserted {len(points_to_upsert)} new documents from '{source}'. Skipped {len(existing_ids)} duplicates.")
        else:
            logger.info(f"No new documents to add from '{source}'. All {len(documents)} were duplicates.")
    def search_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Выполняет поиск по базе знаний с помощью плотного векторного поиска.

        Аргументы:
            query: Текст запроса для поиска.
            limit: Максимальное количество возвращаемых результатов.

        Возвращает:
            Отсортированный список результатов поиска.
        """
        logger.debug(f"Searching knowledge base for query: '{query[:50]}...' with limit {limit}")
        dense_vector = self._encode_weighted_text(query, query)
        search_results = self.client.search(
            collection_name=self.kb_collection,
            query_vector=models.NamedVector(name="default", vector=dense_vector),
            limit=limit,
            with_payload=True,
        )
        logger.debug(f"Found {len(search_results)} results using dense search.")

        formatted_results: List[Dict[str, Any]] = []
        for point in search_results:
            payload = point.payload or {}
            formatted_results.append(
                {
                    "id": payload.get("id") or point.id,
                    "title": payload.get("title") or "",
                    "knowledge": payload.get("knowledge") or "",
                    "source": payload.get("source") or "",
                    "score": point.score,
                    "payload": payload,
                }
            )
        return formatted_results

    def add_to_long_term_memory(self, memories: List[Dict[str, Any]]) -> None:
        """
        Добавляет структурированные воспоминания в коллекцию долгосрочной памяти.

        Аргументы:
            memories: Список словарей payload.

        Возвращает:
            None. Эффект — upsert в Qdrant.
        """

        try:
            initial_count = self.client.count(
                collection_name=self.ltm_collection,
                exact=True
            ).count
        except Exception:
            initial_count = 0

        points: List[models.PointStruct] = []
        for i, mem in enumerate(memories):
            m = dict(mem)
            m.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            m.setdefault("id", initial_count + 1 + i)

            if "user_id" in m:
                m["user_id"] = str(m["user_id"])
                logger.debug(f"Storing memory with user_id: {m['user_id']} (type: {type(m['user_id']).__name__})")

            title_text = m.get("title") or m.get("knowledge") or m.get("content") or ""
            body_text = m.get("knowledge") or m.get("content") or ""
            vec = self._encode_weighted_text(title_text, body_text)

            pt = models.PointStruct(
                id=m["id"],
                vector=self._ltm_upsert_payload(vec),
                payload=m,
            )
            points.append(pt)

        if points:
            self.client.upsert(
                collection_name=self.ltm_collection,
                points=points,
                wait=True,
            )
            logger.info(f"Upserted {len(points)} memories to long-term memory.")


    def search_long_term_memory(self, query: str, user_id: str | int | None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Поиск в долгосрочной памяти с фильтрацией по идентификатору пользователя.

        Аргументы:
            query: Строка запроса для embed'а.
            user_id: Идентификатор пользователя для фильтрации.
            limit: Максимальное число результатов.

        Возвращает:
            Список нормализованных словарей payload, возвращаемых Qdrant.
        """

        if not user_id:
            user_id = 999
        logger.info(
            "[LTM SEARCH] Starting search for user_id='%s' (type: %s), query: '%s...'",
            user_id,
            type(user_id).__name__,
            query[:50],
        )

        try:
            collection_info = self.client.get_collection(collection_name=self.ltm_collection)
            logger.info(
                "[LTM SEARCH] Collection '%s' has %s points",
                self.ltm_collection,
                collection_info.points_count,
            )
        except Exception as e:
            logger.error(f"[LTM SEARCH] Failed to get collection info: {e}")

        if not query:
            return []

        query_vector = self._encode_weighted_text(query, None)
        user_id_for_filter = str(user_id)
        user_filter = models.Filter(
            must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id_for_filter))]
        )

        try:
            vector_param = self._ltm_query_vector(query_vector)
            (search_results,) = self.client.search_batch(
                collection_name=self.ltm_collection,
                requests=[
                    models.SearchRequest(
                        vector=vector_param,
                        filter=user_filter,
                        limit=limit,
                        with_payload=True,
                    )
                ],
            )
            logger.info("[LTM SEARCH] Found %d results in LTM for user '%s'", len(search_results), user_id)

            return self._format_ltm_results(search_results)
        except Exception as e:
            logger.exception(f"[LTM SEARCH] Error during search: {e}")
            return []

    def delete_knowledge_by_id(self, knowledge_id: int) -> bool:
        """
        Удаляет запись из базы знаний по её ID.

        Аргументы:
            knowledge_id: Идентификатор записи для удаления.

        Возвращает:
            True, если запись удалена; False в противном случае.
        """
        logger.info(f"Attempting to delete knowledge record with ID: {knowledge_id}")
        try:
            result = self.client.delete(
                collection_name=self.kb_collection,
                points_selector=models.PointIdsList(points=[knowledge_id]),
                wait=True
            )

            if result.status == models.UpdateStatus.COMPLETED:
                logger.info(f"Record with ID {knowledge_id} deleted from knowledge base.")
                return True

            logger.warning(f"Failed to delete record with ID {knowledge_id} from knowledge base. Status: {result.status}")
            return False

        except Exception as e:
            logger.exception(f"Error deleting record with ID {knowledge_id} from knowledge base: {e}")
            return False

    def delete_memory_by_id(self, memory_id: int) -> bool:
        """
        Удаляет запись из долгосрочной памяти по её ID.

        Аргументы:
            memory_id: Идентификатор записи для удаления.

        Возвращает:
            True, если запись удалена; False в противном случае.
        """
        logger.info(f"Attempting to delete memory record with ID: {memory_id}")
        try:
            result = self.client.delete(
                collection_name=self.ltm_collection,
                points_selector=models.PointIdsList(points=[memory_id]),
                wait=True
            )

            if result.status == models.UpdateStatus.COMPLETED:
                logger.info(f"Record with ID {memory_id} deleted from long-term memory.")
                return True

            logger.warning(f"Failed to delete record with ID {memory_id} from long-term memory. Status: {result.status}")
            return False

        except Exception as e:
            logger.exception(f"Error deleting record with ID {memory_id} from long-term memory: {e}")
            return False

    def clear_knowledge_base(self) -> None:
        """
        Очищает всю базу знаний.
        """
        logger.warning("Clearing the entire knowledge base.")
        try:
            self.client.delete(
                collection_name=self.kb_collection,
                points_selector=models.FilterSelector(filter=models.Filter()),
                wait=True
            )
            logger.info("Knowledge base cleared successfully.")
        except Exception as e:
            logger.exception(f"Error clearing the knowledge base: {e}")

    def clear_long_term_memory(self) -> None:
        """
        Очищает всю долгосрочную память.
        """
        logger.warning("Clearing the entire long-term memory.")
        try:
            self.client.delete(
                collection_name=self.ltm_collection,
                points_selector=models.FilterSelector(filter=models.Filter()),
                wait=True
            )
            logger.info("Long-term memory cleared successfully.")
        except Exception as e:
            logger.exception(f"Error clearing the long-term memory: {e}")
    
    def save_complete_onboarding(
        self,
        user_id: str,
        business_goals: List[str],
        business_description: str,
        daily_tasks: List[str],
        daily_routine_description: str,
        business_type: str,
        business_name: str,
        city: str,
        primary_pain_point: List[str],
        pain_description: str,
    ) -> None:

        goals_text = ", ".join(business_goals)
        tasks_text = ", ".join(daily_tasks)
        pain_text = ", ".join(primary_pain_point)
        
        business_type_ru = {
            "marketplace": "маркетплейс",
            "offline": "оффлайн",
            "online": "онлайн"
        }.get(business_type, business_type)
        
        knowledge_text = (
            f"Business Profile: {business_name} ({business_type_ru}) located in {city}. "
            f"Goals: {goals_text}. "
            f"Business Description: {business_description} "
            f"Daily Routine: {tasks_text}. {daily_routine_description} "
            f"Primary Pain Point: {pain_text}. {pain_description}"
        )
        
        memory_payload = {
            "user_id": user_id,
            "title": f"Onboarding Profile: {business_name}",
            "knowledge": knowledge_text,
            "source": "onboarding_complete",
            "metadata": {

                "business_goals": business_goals,
                "business_description": business_description,

                "daily_tasks": daily_tasks,
                "daily_routine_description": daily_routine_description,

                "business_type": business_type,
                "business_name": business_name,
                "city": city,

                "primary_pain_point": primary_pain_point,
                "pain_description": pain_description,

                "onboarding_completed": True,
                "completion_date": datetime.now(timezone.utc).isoformat()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(
            f"Saving complete onboarding for user {user_id}: "
            f"business='{business_name}', type={business_type}, "
            f"goals={len(business_goals)}, tasks={len(daily_tasks)}, pains={len(primary_pain_point)}"
        )
        self.add_to_long_term_memory([memory_payload])
