"""
Lightweight WB P&L service built on top of the Wildberries statistics API.

Public surface:
- `build_pnl_from_wb` – fetches realization detail by token and date range and returns a P&L snapshot.
- `compute_pnl_from_dataframe` – pure calculation on an already prepared DataFrame (useful for tests).
"""

from .service import build_pnl_from_wb, compute_pnl_from_dataframe
from .types import PnLResult

__all__ = ["build_pnl_from_wb", "compute_pnl_from_dataframe", "PnLResult"]
