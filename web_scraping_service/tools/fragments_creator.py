from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = """
Ты — редактор, который превращает документы в аккуратные карточки знаний.
Сначала мы определяем заголовки и короткие контексты, затем делаем выжимку.
Всегда отвечай на русском и строго следуй формату, который просит пользователь.
""".strip()

SEMANTIC_CHUNKING_PROMPT = """
Разбей документ на логические фрагменты. Опирайся на структуру текста
(подзаголовки, списки, смысловые переходы). Каждый фрагмент должен быть
достаточно цельным: 700–2000 символов. Верни JSON-массив вида:
[
  {{
    "title": "краткое название блока",
    "path": "Название раздела > подраздел",
    "text": "полный текст фрагмента"
  }}
]
Если подходящих заголовков нет, сформируй понятный title на основе содержания.
Документ для разметки:
<<<
{document}
>>>
""".strip()

TITLE_PROMPT = """
Нужно выбрать короткий заголовок (до 90 символов) для фрагмента и, при наличии,
обновить путь (иерархию). Ответ должен быть JSON-объектом
{{"title": "...", "path": "..."}} без Markdown и комментариев.

Текущий контекст: {context_header}
Текущий путь: {path}
Текст фрагмента:
<<<
{fragment}
>>>
""".strip()

SUMMARY_PROMPT = """
Ты оформляешь карточку знаний. Ответ строго в формате JSON:
{{
  "summary": "2-3 предложения, объясняющие важное",
  "key_points": ["краткий факт 1", "краткий факт 2"],
  "body": "переписанный фрагмент на 2-4 абзаца",
  "hashtags": ["#ключевое", "#еще"]
}}

Правила: не выдумывай факты, не используй Markdown в значениях, хэштеги максимально
2-3 штуки. Текст для обработки:
Контекст: {context_header}
<<<
{fragment}
>>>
""".strip()


def _default_llm() -> ChatOpenAI:
    """Create ChatOpenAI instance from OpenRouter env variables.

    Returns:
        Configured ChatOpenAI instance ready for async invocations.

    Raises:
        RuntimeError: If the ``OPENROUTER_API_KEY`` is not present.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY не найден. Добавьте ключ в .env перед использованием фрагментатора."
        )

    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("FRAGMENTS_LLM_MODEL", os.getenv("OPENROUTER_MODEL", "qwen/qwen3-32b"))
    temperature = float(os.getenv("FRAGMENTS_LLM_TEMPERATURE", "0.2"))
    max_tokens = int(os.getenv("FRAGMENTS_LLM_MAX_TOKENS", "900"))

    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=90,
        temperature=temperature,
        max_tokens=max_tokens,
    )


@dataclass
class ChunkingParams:
    """Configuration for semantic chunking."""

    max_chunk_size: int = 2800
    min_chunk_size: int = 200
    semantic_chunking: bool = True


@dataclass
class PreparedChunk:
    """Intermediate container before summarisation."""

    raw_text: str
    context_header: str
    path: str

    def best_context(self) -> str:
        """Return the most informative context label for logging or display."""
        return self.context_header or self.path or "Фрагмент документа"


class AsyncDocumentProcessor:
    """Chunker + summariser built on top of ChatOpenAI."""

    def __init__(
        self,
        llm: ChatOpenAI | None = None,
        *,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        chunk_title_prompt: str = TITLE_PROMPT,
        chunking_prompt: str = SEMANTIC_CHUNKING_PROMPT,
        chunking_params: ChunkingParams | None = None,
    ) -> None:
        """Configure the asynchronous document processor.

        Args:
            llm: Optional preconfigured ChatOpenAI instance.
            system_prompt: System instruction used for summarisation.
            chunk_title_prompt: Prompt used to derive chunk titles.
            chunking_prompt: Prompt used to perform semantic chunking.
            chunking_params: Optional overrides for chunk size settings.
        """
        self.llm = llm or _default_llm()
        self.system_prompt = system_prompt
        self.chunk_title_prompt = chunk_title_prompt
        self.chunking_prompt = chunking_prompt
        self.chunking_params = chunking_params or ChunkingParams()

    async def process_text_chunks(
        self,
        chunks: List[str],
        doc_prefix: str,
        source: str = "Загруженный документ",
        link: str | None = None,
        max_concurrent_tasks: int = 4,
    ) -> List[Dict[str, Any]]:
        """Process a batch of text chunks and return knowledge fragments.

        Args:
            chunks: Raw text slices to process.
            doc_prefix: Identifier prefix used for chunk keys.
            source: Human-readable source name.
            link: Optional original document link.
            max_concurrent_tasks: Semaphore limit for concurrent LLM calls.

        Returns:
            List of dictionaries ready to be ingested into the KB.
        """

        prepared = await self._prepare_chunks(chunks)
        if not prepared:
            return []

        sem = asyncio.Semaphore(max_concurrent_tasks)
        tasks: List[asyncio.Task[Dict[str, Any] | None]] = []

        for idx, chunk_data in enumerate(prepared, start=1):
            tasks.append(
                asyncio.create_task(
                    self._run_with_semaphore(
                        sem,
                        self._process_single_chunk,
                        chunk_data,
                        idx,
                        len(prepared),
                        doc_prefix,
                        source,
                        link,
                    )
                )
            )

        results = await asyncio.gather(*tasks)
        return [item for item in results if item]

    async def _run_with_semaphore(
        self,
        sem: asyncio.Semaphore,
        coro: callable,
        *args: object,
        **kwargs: object,
    ) -> Dict[str, Any] | None:
        """Run coroutine while honoring the concurrency semaphore.

        Args:
            sem: Semaphore enforcing concurrency limits.
            coro: Coroutine function to invoke.
            *args: Positional arguments for the coroutine.
            **kwargs: Keyword arguments for the coroutine.

        Returns:
            Result of the coroutine invocation.
        """

        async with sem:
            return await coro(*args, **kwargs)

    async def _prepare_chunks(self, chunks: List[str]) -> List[PreparedChunk]:
        """Normalize raw text chunks and optionally perform semantic splitting.

        Args:
            chunks: List of raw text fragments.

        Returns:
            Prepared chunk descriptors with inferred context.
        """

        prepared: List[PreparedChunk] = []
        for chunk_text in chunks:
            text = (chunk_text or "").strip()
            if not text:
                continue

            if self.chunking_params.semantic_chunking and len(text) > self.chunking_params.max_chunk_size:
                semantic_chunks = await self._semantic_chunk_document(text)
                if semantic_chunks:
                    prepared.extend(semantic_chunks)
                    continue

            prepared.append(self._build_chunk_payload(text))
        return prepared

    def _build_chunk_payload(self, text: str) -> PreparedChunk:
        """Create a PreparedChunk object for a given text block.

        Args:
            text: Raw chunk text.

        Returns:
            PreparedChunk with context header and path.
        """

        context = self._extract_heading(text)
        return PreparedChunk(raw_text=text, context_header=context, path=context)

    @staticmethod
    def _extract_heading(text: str) -> str:
        """Extract a representative heading from the text content.

        Args:
            text: Raw chunk text.

        Returns:
            Heuristic heading used as context header.
        """

        for line in text.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            if len(candidate) <= 140 and (candidate.isupper() or re.match(r"^\d+[\.\)]", candidate)):
                return candidate
            if len(candidate.split()) <= 16:
                return candidate
            return candidate[:140]
        return ""

    async def _process_single_chunk(
        self,
        chunk_data: PreparedChunk,
        index: int,
        total_chunks: int,
        doc_prefix: str,
        source: str,
        link: str | None,
    ) -> Dict[str, Any] | None:
        """Process a single prepared chunk into a KB fragment.

        Args:
            chunk_data: Prepared chunk payload.
            index: 1-based chunk index.
            total_chunks: Total number of chunks in the document.
            doc_prefix: Identifier prefix.
            source: Source name.
            link: Optional document link.

        Returns:
            Fragment dictionary or ``None`` if the chunk is empty.
        """

        text = chunk_data.raw_text.strip()
        if not text:
            return None

        key = f"{doc_prefix}_chunk_{index:03d}_of_{total_chunks:03d}"
        base_context = chunk_data.best_context()
        title_data = await self._generate_chunk_title(text, base_context, chunk_data.path)
        title = title_data.get("title") or base_context or f"Фрагмент #{index}"
        resolved_path = title_data.get("path") or chunk_data.path or base_context

        summary_payload = await self._summarise_chunk(text, base_context)
        display_body = self._build_display_body(title, base_context, resolved_path, summary_payload)
        attrs = json.dumps(
            {
                "context_path": resolved_path,
                "hashtags": summary_payload.get("hashtags", []),
            },
            ensure_ascii=False,
        )

        return {
            "KEY": key,
            "TITLE": title,
            "DISPLAY_BODY": display_body,
            "SOURCE": source,
            "LINK": link or "",
            "ATTRS": attrs,
        }

    async def _semantic_chunk_document(self, document_text: str) -> List[PreparedChunk]:
        """Ask the LLM to propose semantic chunk boundaries.

        Args:
            document_text: Large text to split semantically.

        Returns:
            Prepared chunks derived from the semantic chunking prompt.
        """

        prompt = self.chunking_prompt.format(document=document_text[:12000])
        raw = await self._call_llm(prompt)
        chunks = self._parse_semantic_chunks(raw)
        if not chunks:
            return [self._build_chunk_payload(document_text)]
        return [PreparedChunk(raw_text=item["text"], context_header=item["title"], path=item["path"]) for item in chunks]

    async def _generate_chunk_title(self, text: str, context_header: str, path: str | None) -> Dict[str, str]:
        """Generate a concise title/path for a chunk via LLM call.

        Args:
            text: Body of the chunk.
            context_header: Heading extracted from the chunk.
            path: Existing context path, if any.

        Returns:
            Dictionary with ``title`` and ``path`` keys.
        """

        prompt = self.chunk_title_prompt.format(
            context_header=context_header or "Нет заголовка",
            path=path or "Не указан",
            fragment=text[:3000],
        )
        raw = await self._call_llm(prompt)
        try:
            parsed = json.loads(raw)
            return {
                "title": (parsed.get("title") or "").strip(),
                "path": (parsed.get("path") or "").strip(),
            }
        except Exception:
            logger.debug("Не удалось распарсить ответ для заголовка: %s", raw)
            return {"title": context_header, "path": path}

    async def _summarise_chunk(self, text: str, context_header: str) -> Dict[str, Any]:
        """Summarise a chunk into title, summary, key points, and hashtags.

        Args:
            text: Chunk body.
            context_header: Heading for the chunk.

        Returns:
            Dictionary containing summary metadata.
        """

        prompt = SUMMARY_PROMPT.format(context_header=context_header or "Нет контекста", fragment=text[:6000])
        raw = await self._call_llm(prompt)
        try:
            parsed = json.loads(raw)
            parsed.setdefault("summary", "")
            parsed.setdefault("body", text)
            parsed.setdefault("key_points", [])
            parsed.setdefault("hashtags", [])
            return parsed
        except Exception:
            logger.warning("Не удалось распарсить JSON при суммаризации, использую исходный текст.")
            return {"summary": "", "body": text, "key_points": [], "hashtags": []}

    def _parse_semantic_chunks(self, response: str) -> List[Dict[str, str]]:
        """Parse the semantic chunking response into a normalized structure.

        Args:
            response: Raw response string from the LLM.

        Returns:
            Normalized chunk dictionaries.
        """

        try:
            payload = json.loads(response)
            if isinstance(payload, dict):
                payload = [payload]
            normalized: List[Dict[str, str]] = []
            for item in payload or []:
                text = (item.get("text") or "").strip()
                if not text or len(text) < self.chunking_params.min_chunk_size:
                    continue
                title = (item.get("title") or self._extract_heading(text) or "Фрагмент").strip()
                path = (item.get("path") or title).strip()
                normalized.append({"text": text, "title": title, "path": path})
            return normalized
        except Exception:
            logger.debug("Semantic chunk response is not JSON, fallback to heuristic split.")
            return []

    async def _call_llm(self, prompt: str) -> str:
        """Send a prompt to the configured ChatOpenAI instance.

        Args:
            prompt: Text prompt to send.

        Returns:
            Raw text content from the model response.
        """

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        response = await self.llm.ainvoke(messages)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            return "".join(
                part.get("text", "") if isinstance(part, dict) else getattr(part, "text", str(part)) for part in content
            ).strip()
        return str(content).strip()

    @staticmethod
    def _build_display_body(
        title: str,
        context_header: str,
        path: str | None,
        summary_payload: Dict[str, Any],
    ) -> str:
        """Render the chunk summary as Markdown.

        Args:
            title: Chunk title.
            context_header: Extracted heading.
            path: Optional navigation path.
            summary_payload: Dictionary returned by ``_summarise_chunk``.

        Returns:
            Markdown-formatted text block.
        """

        blocks: List[str] = [f"### {title}"]
        if context_header and context_header != title:
            blocks.append(f"**Контекст:** {context_header}")
        if path and path not in {title, context_header}:
            blocks.append(f"**Путь:** {path}")
        summary = summary_payload.get("summary")
        if summary:
            blocks.append(f"**Выжимка:** {summary}")
        key_points = [point for point in summary_payload.get("key_points", []) if point]
        if key_points:
            blocks.append("Ключевые факты:")
            blocks.extend(f"- {point}" for point in key_points)
        body = summary_payload.get("body")
        if body:
            blocks.append(body.strip())
        hashtags = summary_payload.get("hashtags") or []
        if hashtags:
            blocks.append("HASHTAGS: " + ", ".join(hashtags))
        return "\n".join(blocks).strip()


async def process_text_chunks(
    text_chunks: List[str],
    doc_prefix: str,
    source: str,
    link: str | None = None,
) -> List[Dict[str, Any]]:
    """Public helper mirroring the legacy API."""
    """Legacy-compatible helper mirroring the previous public API.

    Args:
        text_chunks: Raw text fragments.
        doc_prefix: Identifier prefix for generated fragments.
        source: Source identifier stored in the fragment.
        link: Optional source link.

    Returns:
        List of processed fragments.
    """

    processor = AsyncDocumentProcessor()
    try:
        return await processor.process_text_chunks(
            chunks=text_chunks,
            doc_prefix=doc_prefix,
            source=source,
            link=link,
        )
    except Exception as exc:
        logger.error("Ошибка при нарезке документа: %s", exc, exc_info=True)
        return []
