"""Typed contracts for the WB P&L service."""

from __future__ import annotations

from typing import Dict, TypedDict


class PnLResult(TypedDict):
    gmv: float
    marginality: float
    number_of_sales: int
    coef_returns: float
    top_5_sku: Dict[str, float]
    bot_5_sku: Dict[str, float]
    cost_logistic: float
    cost_saving: float
    cost_marketplace: float
    wb_ad_cost: float
