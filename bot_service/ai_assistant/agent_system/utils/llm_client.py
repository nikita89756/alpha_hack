"""Async client for interacting with DeepSeek through OpenRouter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from ai_assistant.agent_system.utils.logger import logger

Message = Dict[str, str]


@dataclass
class LLMResponse:
    """Normalized response returned by the LLM client."""

    content: str
    raw: Optional[Dict[str, Any]] = None


class AsyncLLMClient:
    """Thin async wrapper around the OpenRouter chat completions endpoint."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        *,
        timeout: float,
        verify: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=timeout, verify=verify)

    async def ainvoke(
        self,
        messages: List[Message],
        *,
        temperature: Optional[float],
        max_tokens: Optional[int],
        n: int = 1,
    ) -> LLMResponse:
        """Send a chat completion request to OpenRouter."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [self._format_message(msg) for msg in messages],
            "n": n,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            response = await self.client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            texts = self._extract_texts(data)
            return LLMResponse(content=texts[0] if texts else "", raw=data)
        except httpx.HTTPStatusError as exc:
            body = exc.response.text if exc.response is not None else "no response body"
            logger.error(
                "OpenRouter request failed with status %s: %s",
                exc.response.status_code if exc.response is not None else "unknown",
                body,
            )
        except httpx.RequestError as exc:
            logger.error("OpenRouter request error: %s", exc)
        except Exception as exc:
            logger.exception("Unexpected OpenRouter client error: %s", exc)

        return LLMResponse(content="")

    async def aclose(self) -> None:
        """Close underlying HTTPX client."""

        await self.client.aclose()

    @staticmethod
    def _format_message(message: Message) -> Dict[str, str]:
        """Ensure OpenRouter-compatible role/content message structure."""

        return {
            "role": (message.get("role") or "user"),
            "content": message.get("content") or "",
        }

    @staticmethod
    def _extract_texts(data: Dict[str, Any]) -> List[str]:
        """Return all text completions from OpenRouter response payload."""

        results: List[str] = []
        for choice in data.get("choices", []):
            message = choice.get("message") or {}
            content = message.get("content")
            if isinstance(content, str) and content:
                results.append(content)
        return results


__all__ = ["AsyncLLMClient", "LLMResponse", "Message"]
