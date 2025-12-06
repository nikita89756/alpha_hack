"""Pure P&L calculations on a prepared WB detail DataFrame."""

from __future__ import annotations

from typing import Dict, Iterable

import numpy as np
import pandas as pd

from .types import PnLResult

COL_DOC_TYPE = "Тип документа"
COL_QUANTITY = "Кол-во"
COL_PRICE = "Цена розничная с учетом согласованной скидки"
COL_GMV_RAW = "Вайлдберриз реализовал Товар (Пр)"
COL_COMMISSION_PCT = "Размер кВВ, %"
COL_DELIVERY = "Услуги по доставке товара покупателю"
COL_STORAGE = "Хранение"
COL_ACCEPTANCE = "Платная приемка"
COL_PENALTY = "Общая сумма штрафов"
COL_DEDUCTION = "Удержания"
COL_ACQUIRING = "Эквайринг/Комиссии за организацию платежей"
COL_BONUS_TYPE = "Виды логистики, штрафов и доплат"
COL_ADDITIONAL_PAYMENT = "Доплаты"
COL_NAME = "Название"
COL_SUBJECT = "Предмет"
COL_SRID = "Srid"
COL_SKU_CODE = "Код номенклатуры"

DOC_SALE = "продажа"
DOC_RETURN = "возврат"


def _ensure_columns(df: pd.DataFrame, required: Iterable[str]) -> pd.DataFrame:
    """Create missing columns with zeros to make arithmetic safe."""

    result = df.copy()
    for col in required:
        if col not in result.columns:
            result[col] = 0
    return result


def _prepare_numeric(series: pd.Series) -> pd.Series:
    """Convert to numeric with NaNs replaced by zeros."""

    return pd.to_numeric(series, errors="coerce").fillna(0)


def _sign_by_doc_type(doc_type_series: pd.Series) -> pd.Series:
    """Return +1 for sales, -1 for returns, 0 otherwise."""

    normalized = doc_type_series.astype(str).str.strip().str.lower()
    return np.where(normalized == DOC_SALE, 1, np.where(normalized == DOC_RETURN, -1, 0))


def _build_sku_keys(df: pd.DataFrame) -> pd.Series:
    """Choose SKU identifier pair (code, name) with fallbacks."""

    codes = df.get(COL_SKU_CODE, pd.Series([], dtype="object")).astype(str).str.strip()
    names = df.get(COL_NAME, pd.Series([], dtype="object")).astype(str).str.strip()

    has_code = codes.notna() & codes.ne("") & codes.ne("nan")
    has_name = names.notna() & names.ne("") & names.ne("nan")

    sku_keys = pd.Series(["unknown"] * len(df), index=df.index, dtype="object")
    sku_keys.loc[has_code] = codes[has_code]
    sku_keys.loc[~has_code & has_name] = names[~has_code & has_name]
    return sku_keys


def _aggregate_sku_gmv(df: pd.DataFrame) -> Dict[str, float]:
    """Aggregate GMV by SKU key (code + name) and return as key -> gmv dict."""

    sku_gmv = df.groupby("_sku_key")["gmv_net"].sum().sort_values(ascending=False)
    sku_gmv = sku_gmv[sku_gmv != 0]
    if ("unknown", "unknown") in sku_gmv.index and len(sku_gmv) > 1:
        sku_gmv = sku_gmv.drop(labels=[("unknown", "unknown")])
    return {k: float(v) for k, v in sku_gmv.items()}


def compute_pnl(df_raw: pd.DataFrame) -> PnLResult:
    """Compute the requested P&L slice from WB detail."""

    required_cols = [
        COL_DOC_TYPE,
        COL_QUANTITY,
        COL_PRICE,
        COL_GMV_RAW,
        COL_COMMISSION_PCT,
        COL_DELIVERY,
        COL_STORAGE,
        COL_ACCEPTANCE,
        COL_PENALTY,
        COL_DEDUCTION,
        COL_ACQUIRING,
        COL_BONUS_TYPE,
        COL_ADDITIONAL_PAYMENT,
        COL_NAME,
        COL_SUBJECT,
        COL_SRID,
        COL_SKU_CODE,
    ]
    df = _ensure_columns(df_raw, required_cols)

    qty = _prepare_numeric(df[COL_QUANTITY])
    price = _prepare_numeric(df[COL_PRICE])
    gmv_raw = _prepare_numeric(df[COL_GMV_RAW])
    commission_pct = _prepare_numeric(df[COL_COMMISSION_PCT])
    delivery = _prepare_numeric(df[COL_DELIVERY])
    storage = _prepare_numeric(df[COL_STORAGE])
    acceptance = _prepare_numeric(df[COL_ACCEPTANCE])
    penalties = _prepare_numeric(df[COL_PENALTY])
    deductions = _prepare_numeric(df[COL_DEDUCTION])
    acquiring = _prepare_numeric(df[COL_ACQUIRING])
    additional_payment = _prepare_numeric(df[COL_ADDITIONAL_PAYMENT])
    doc_sign = _sign_by_doc_type(df[COL_DOC_TYPE])

    sales_mask = doc_sign == 1
    returns_mask = doc_sign == -1
    sales_qty = float(qty[sales_mask].sum())
    returns_qty = float(qty[returns_mask].sum())
    total_qty = sales_qty + returns_qty

    line_gmv = np.where(gmv_raw != 0, gmv_raw, price * qty)
    gmv = float((line_gmv * doc_sign).sum())

    commission = float((price * qty * (commission_pct / 100.0) * doc_sign).sum())

    cost_logistic = float(delivery.sum())

    cost_saving = float((storage + acceptance).sum())

    other_mp = commission + float(penalties.sum()) + float(deductions.sum()) + float(acquiring.sum())

    bonus_type = df[COL_BONUS_TYPE].astype(str).str.lower()
    ad_mask = bonus_type.str.contains("реклам", na=False) | bonus_type.str.contains("продвиж", na=False)
    wb_ad_cost = float(additional_payment[ad_mask].sum())

    total_costs = cost_logistic + cost_saving + other_mp + wb_ad_cost
    net_revenue = gmv - total_costs
    marginality = float(net_revenue / gmv) if gmv != 0 else 0.0

    coef_returns = float(returns_qty / total_qty) if total_qty > 0 else 0.0

    df_enriched = df.copy()
    df_enriched["_sku_key"] = _build_sku_keys(df_enriched)
    df_enriched["gmv_net"] = line_gmv * doc_sign
    sku_gmv = _aggregate_sku_gmv(df_enriched)

    sorted_items = list(sku_gmv.items())
    top_5 = dict(sorted_items[:5])
    bot_5 = dict(sorted_items[-5:]) if sorted_items else {}

    return PnLResult(
        gmv=float(gmv),
        marginality=marginality,
        number_of_sales=int(sales_qty),
        coef_returns=coef_returns,
        top_5_sku=top_5,
        bot_5_sku=bot_5,
        cost_logistic=cost_logistic,
        cost_saving=cost_saving,
        cost_marketplace=float(other_mp),
        wb_ad_cost=wb_ad_cost,
    )
