"""HTTP client wrappers for Wildberries APIs used by the P&L service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final

import httpx
import pandas as pd

_COLUMN_MAPPING: Final[dict[str, str]] = {
    "subject_name": "Предмет",
    "sa_name": "Артикул поставщика",
    "nm_id": "Код номенклатуры",
    "brand_name": "Бренд",
    "supplier_oper_name": "Обоснование для оплаты",
    "doc_type_name": "Тип документа",
    "sale_dt": "Дата продажи",
    "quantity": "Кол-во",
    "retail_price_withdisc_rub": "Цена розничная с учетом согласованной скидки",
    "commission_percent": "Размер кВВ, %",
    "retail_amount": "Вайлдберриз реализовал Товар (Пр)",
    "delivery_rub": "Услуги по доставке товара покупателю",
    "storage_fee": "Хранение",
    "acceptance": "Платная приемка",
    "penalty": "Общая сумма штрафов",
    "deduction": "Удержания",
    "acquiring_fee": "Эквайринг/Комиссии за организацию платежей",
    "bonus_type_name": "Виды логистики, штрафов и доплат",
    "additional_payment": "Доплаты",
}


@dataclass(frozen=True)
class WBApiConfig:
    """Configuration for Wildberries API endpoints."""

    statistics_base_url: str = "https://statistics-api.wildberries.ru/api/"
    timeout_seconds: float = 60.0
    limit: int = 200_000


class WBStatisticsClient:
    """Sync-only client for the WB statistics API (realization detail)."""

    def __init__(self, api_token: str, config: WBApiConfig | None = None) -> None:
        self.api_token = api_token
        self.config = config or WBApiConfig()
        self._client = httpx.Client(
            base_url=self.config.statistics_base_url,
            timeout=self.config.timeout_seconds,
        )

    def fetch_realization_report(
        self, *, date_from: date, date_to: date, limit: int | None = None
    ) -> pd.DataFrame:
        """Return realization detail as DataFrame; empty DataFrame on non-list payloads."""

        effective_limit = limit or self.config.limit
        params = {"dateFrom": date_from, "dateTo": date_to, "limit": effective_limit}
        headers = {"Authorization": self.api_token}

        with self._client as client:
            response = client.get("v5/supplier/reportDetailByPeriod", params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()

        if isinstance(payload, list):
            df = pd.DataFrame(payload)
        elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
            df = pd.DataFrame(payload["data"])
        else:
            return pd.DataFrame()

        return self._rename_columns(df)

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename known columns to the internal Russian naming."""

        renamed = df.rename(columns={src: dst for src, dst in _COLUMN_MAPPING.items() if src in df.columns})
        return renamed


def fetch_realization_report(
    api_token: str, *, date_from: date, date_to: date, limit: int | None = None
) -> pd.DataFrame:
    """Convenience function to fetch detail without instantiating the class."""

    client = WBStatisticsClient(api_token)
    return client.fetch_realization_report(date_from=date_from, date_to=date_to, limit=limit)
