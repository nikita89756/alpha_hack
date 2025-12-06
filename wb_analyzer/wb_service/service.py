"""High-level entrypoints for building WB P&L snapshots."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd

from .calculator import compute_pnl
from .client import fetch_realization_report
from .types import PnLResult


def _default_date_range() -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=30), today


def compute_pnl_from_dataframe(df: pd.DataFrame) -> PnLResult:
    """Pure calculation wrapper for dependency injection/testing."""

    return compute_pnl(df)


def build_pnl_from_wb(
    api_token: str, *, date_from: Optional[date] = None, date_to: Optional[date] = None, limit: int | None = None
) -> PnLResult:
    """Fetch realization detail from WB API by token and compute the P&L slice."""

    start, end = _default_date_range()
    df = fetch_realization_report(
        api_token,
        date_from=date_from or start,
        date_to=date_to or end,
        limit=limit,
    )
    return compute_pnl(df)
