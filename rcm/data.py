"""Synthetic claims generator. SYNTHETIC ONLY: not real patients, insurers or financials."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def generate_claims(start: str = "2024-07-01", months: int = 15, claims_per_month: int = 2500,
                    seed: int = 21, as_of: str | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start_ts = pd.Timestamp(start)
    end_ts = start_ts + pd.DateOffset(months=months)
    as_of_ts = pd.Timestamp(as_of) if as_of else end_ts
    n = claims_per_month * months
    payers = list(config.PAYERS)
    p_share = np.array([config.PAYERS[p]["share"] for p in payers])
    sls = list(config.SERVICE_LINES)
    sl_w = np.array([config.SERVICE_LINES[s]["w"] for s in sls])
    reasons = list(config.DENIAL_REASONS)
    r_w = np.array(list(config.DENIAL_REASONS.values()))

    service = start_ts + pd.to_timedelta(rng.integers(0, (end_ts - start_ts).days, n), unit="D")
    payer = rng.choice(payers, n, p=p_share / p_share.sum())
    sl = rng.choice(sls, n, p=sl_w / sl_w.sum())
    base = np.array([config.SERVICE_LINES[s]["charge"] for s in sl])
    charge = np.round(base * rng.lognormal(0, 0.35, n), 2)
    rate = np.array([config.PAYERS[p]["rate"] for p in payer])
    expected = np.round(charge * rate * 0.85, 2)  # contractual allowance
    cost = np.round(charge * np.array([config.SERVICE_LINES[s]["cost_ratio"] for s in sl]) * rng.normal(1, 0.08, n), 2)
    submit_lag = rng.gamma(2.0, 2.0, n).astype(int) + 1
    submitted = service + pd.to_timedelta(submit_lag, unit="D")

    # improvement in denial rate over time (front-end authorisation initiative)
    month_idx = ((service - start_ts).days / 30.4).astype(int)
    trend = np.where(month_idx >= 8, 0.75, 1.0)
    p_deny = np.array([config.PAYERS[p]["denial"] for p in payer]) * trend
    denied = rng.random(n) < p_deny
    reason = np.where(denied, rng.choice(reasons, n, p=r_w), "")
    # some non-denied claims still need rework (rejected/edits) -> not clean
    rework = (~denied) & (rng.random(n) < 0.03)
    appealed = denied & (rng.random(n) < 0.65)
    overturned = appealed & (rng.random(n) < 0.55)

    pay_days = np.array([config.PAYERS[p]["pay_days"] for p in payer]) * rng.lognormal(0, 0.3, n)
    pay_days = pay_days + np.where(overturned, rng.integers(25, 60, n), 0)
    paid_date = submitted + pd.to_timedelta(pay_days.astype(int), unit="D")
    final_paid = np.where(denied & ~overturned, 0.0, expected * rng.uniform(0.94, 1.0, n))
    is_paid = (paid_date <= as_of_ts) & (final_paid > 0)
    written_off = denied & ~overturned & ((submitted + pd.Timedelta(days=90)) <= as_of_ts)

    df = pd.DataFrame({
        "claim_id": [f"SYN-CLM-{i:07d}" for i in range(1, n + 1)],
        "service_date": service, "submitted_date": submitted, "payer": payer, "service_line": sl,
        "gross_charge_sar": charge, "expected_reimbursement_sar": expected, "direct_cost_sar": cost,
        "denied": denied, "denial_reason": reason, "first_pass_clean": ~denied & ~rework,
        "appealed": appealed, "overturned": overturned,
        "paid_date": pd.Series(paid_date).where(is_paid), "paid_sar": np.where(is_paid, np.round(final_paid, 2), 0.0),
        "written_off": written_off,
    })
    return df.sort_values("service_date").reset_index(drop=True)
