"""Вспомогательные утилиты для работы с фрагментами БЗ."""

from typing import Any, Dict, List


def render_kb_block(items: List[Dict[str, Any]], tag: str = "KB") -> str:
    """Формирует текстовый блок из фрагментов базы знаний.

    Args:
        items: Фрагменты с ключами id/title/knowledge/score.
        tag: Префикс для ссылок (например, KB, WEB и т.д.).

    Returns:
        Строку, готовую для подстановки в промпт агента.
    """
    if not items:
        return "(empty)"

    lines: List[str] = []
    for it in items:
        ref = f"[{tag}#{it.get('id', '?')}]"
        score = it.get("score")
        score_repr = f"{score:.2f}" if isinstance(score, (int, float)) else "n/a"
        title = it.get("title") or ""
        prefix = f"{ref} score={score_repr}"
        if title:
            prefix = f"{prefix} title={title}"
        knowledge = it.get("knowledge") or it.get("content") or ""
        lines.append(f"{prefix}\n{knowledge}")

    return "\n".join(lines)


__all__ = ["render_kb_block"]
