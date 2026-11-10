"""Simple cash-flow forecast: payer lag-based expected collections + Holt linear trend baseline."""
from __future__ import annotations

import numpy as np
import pandas as pd


def holt_linear(y: pd.Series, horizon: int = 6, alpha: float = 0.5, beta: float = 0.3) -> pd.DataFrame:
    """Holt's linear exponential smoothing with a simple ±1.96·σ residual band."""
    y = y.astype(float)
    level, trend = y.iloc[0], (y.iloc[1] - y.iloc[0]) if len(y) > 1 else 0.0
    fitted = []
    for v in y:
        fitted.append(level + trend)
        new_level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level
    resid = y.values - np.array(fitted)
    sigma = float(np.std(resid[1:])) if len(resid) > 2 else 0.0
    idx = pd.date_range(y.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    fc = np.array([level + (h + 1) * trend for h in range(horizon)])
    band = 1.96 * sigma * np.sqrt(np.arange(1, horizon + 1))
    return pd.DataFrame({"month": idx, "forecast": fc, "lower": np.maximum(fc - band, 0), "upper": fc + band})


def pipeline_collections(claims: pd.DataFrame, as_of: pd.Timestamp, horizon: int = 3) -> pd.DataFrame:
    """Expected cash from currently open, non-denied claims, using each payer's historical days-to-pay."""
    paid = claims[claims["paid_date"].notna() & (claims["paid_date"] <= as_of)]
    lag = (paid["paid_date"] - paid["submitted_date"]).dt.days.groupby(paid["payer"]).median()
    open_c = claims[(claims["submitted_date"] <= as_of) & ~(claims["paid_date"].notna() & (claims["paid_date"] <= as_of))
                    & ~claims["denied"]].copy()
    open_c["expected_pay"] = open_c["submitted_date"] + pd.to_timedelta(open_c["payer"].map(lag).fillna(45), unit="D")
    open_c.loc[open_c["expected_pay"] <= as_of, "expected_pay"] = as_of + pd.Timedelta(days=15)
    open_c["month"] = open_c["expected_pay"].dt.to_period("M").dt.to_timestamp()
    t = open_c.groupby("month")["expected_reimbursement_sar"].sum().rename("pipeline_sar").reset_index()
    return t.head(horizon)
