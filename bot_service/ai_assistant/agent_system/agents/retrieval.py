"""Агент, который получает фрагменты из базы знаний."""

from typing import Any, Dict, List, Optional

from ..config import AGENTS_CONFIG
from ..rag import RetrieverController


class RetrievalAgent:
    """Обращается к RetrieverController и подготавливает контекст базы знаний."""

    def __init__(self, retriever: RetrieverController, kb_limit: Optional[int] = None) -> None:
        """Сохраняет ссылку на контроллер и лимит выдачи из БЗ.

        Args:
            retriever (RetrieverController): Контроллер удалённой базы знаний.
            kb_limit (int): Количество возвращаемых фрагментов.
        """
        self.retriever = retriever
        default_limit = AGENTS_CONFIG.retrieval.kb_limit
        self.kb_limit = kb_limit if kb_limit is not None else default_limit

    def run(self, kb_query: str) -> List[Dict[str, Any]]:
        """Возвращает нормализованные результаты БЗ для переданного запроса.

        Args:
            kb_query (str): Поисковый запрос.

        Returns:
            List[Dict[str, Any]]: Фрагменты базы знаний или пустой список.
        """
        if not kb_query:
            return []
        return self.retriever.search_knowledge_base(kb_query, limit=self.kb_limit)
