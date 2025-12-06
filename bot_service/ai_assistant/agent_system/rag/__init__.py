"""
RAG (Retrieval-Augmented Generation) система.

Этот пакет содержит компоненты для обработки документов,
создания векторных представлений и поиска по базе знаний.
"""

from .controller import BertSentenceEncoder, RetrieverController

__all__ = [
    "RetrieverController",
    "BertSentenceEncoder"
]
