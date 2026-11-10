"""Revenue-cycle KPIs (HFMA-style definitions, simplified for demonstration)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def outstanding_ar(claims: pd.DataFrame, as_of: pd.Timestamp) -> pd.Series:
    """Open balance per claim at a date: expected reimbursement not yet paid or written off."""
    submitted = claims["submitted_date"] <= as_of
    paid = claims["paid_date"].notna() & (claims["paid_date"] <= as_of)
    wo = claims["written_off"] & ((claims["submitted_date"] + pd.Timedelta(days=90)) <= as_of)
    return np.where(submitted & ~paid & ~wo, claims["expected_reimbursement_sar"], 0.0)


def days_in_ar(claims: pd.DataFrame, as_of: pd.Timestamp, window_days: int = 90) -> float:
    """Days in A/R = outstanding A/R ÷ average daily net revenue over the trailing window."""
    ar = outstanding_ar(claims, as_of).sum()
    w = claims[(claims["service_date"] > as_of - pd.Timedelta(days=window_days)) & (claims["service_date"] <= as_of)]
    adr = w["expected_reimbursement_sar"].sum() / window_days
    return float(ar / adr) if adr else float("nan")


def ar_aging(claims: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    bal = outstanding_ar(claims, as_of)
    age = (as_of - claims["submitted_date"]).dt.days
    buckets = pd.cut(age, [-1, 30, 60, 90, 120, 10_000], labels=["0–30", "31–60", "61–90", "91–120", "120+"])
    t = pd.DataFrame({"bucket": buckets, "balance": bal, "payer": claims["payer"]})
    return t[t["balance"] > 0].groupby(["bucket", "payer"], observed=False)["balance"].sum().reset_index()


def headline(claims: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    c = claims
    collectible = c.loc[~c["written_off"] | c["overturned"], "expected_reimbursement_sar"]
    paid_mature = c[(c["submitted_date"] + pd.Timedelta(days=120)) <= as_of]
    ncr = paid_mature["paid_sar"].sum() / max(paid_mature.loc[~paid_mature["denied"] | paid_mature["overturned"],
                                                               "expected_reimbursement_sar"].sum(), 1) * 100
    denied = c[c["denied"]]
    return {
        "claims": len(c),
        "gross_charges": float(c["gross_charge_sar"].sum()),
        "net_revenue": float(c["expected_reimbursement_sar"].sum()),
        "cash_collected": float(c["paid_sar"].sum()),
        "clean_claim_rate": float(c["first_pass_clean"].mean() * 100),
        "denial_rate": float(c["denied"].mean() * 100),
        "denied_value": float(denied["expected_reimbursement_sar"].sum()),
        "preventable_denial_pct": float(denied["denial_reason"].isin(config.PREVENTABLE).mean() * 100) if len(denied) else 0.0,
        "appeal_success_rate": float(c.loc[c["appealed"], "overturned"].mean() * 100) if c["appealed"].any() else 0.0,
        "days_in_ar": days_in_ar(c, as_of),
        "net_collection_rate": float(min(ncr, 100.0)),
        "collectible": float(collectible.sum()),
    }


def by_payer(claims: pd.DataFrame) -> pd.DataFrame:
    g = claims.groupby("payer")
    out = g.agg(claims=("claim_id", "count"), net_revenue=("expected_reimbursement_sar", "sum"),
                denial_rate=("denied", "mean"), clean_claim_rate=("first_pass_clean", "mean")).reset_index()
    out["denial_rate"] *= 100
    out["clean_claim_rate"] *= 100
    paid = claims[claims["paid_date"].notna()]
    out = out.merge((paid["paid_date"] - paid["submitted_date"]).dt.days.groupby(paid["payer"]).mean()
                    .rename("avg_days_to_pay").reset_index(), on="payer", how="left")
    out["payer_mix_pct"] = out["net_revenue"] / out["net_revenue"].sum() * 100
    return out.sort_values("net_revenue", ascending=False).reset_index(drop=True)


def denial_reasons(claims: pd.DataFrame) -> pd.DataFrame:
    d = claims[claims["denied"]]
    t = d.groupby("denial_reason").agg(count=("claim_id", "count"), value_sar=("expected_reimbursement_sar", "sum"),
                                       overturned=("overturned", "mean")).reset_index()
    t["preventable"] = t["denial_reason"].isin(config.PREVENTABLE)
    t["overturned"] *= 100
    return t.sort_values("count", ascending=False).reset_index(drop=True)


def service_line_profitability(claims: pd.DataFrame) -> pd.DataFrame:
    """Contribution margin = cash-basis expected net revenue (excluding unrecovered denials) − direct cost."""
    c = claims.assign(realised=np.where(claims["denied"] & ~claims["overturned"], 0.0,
                                        claims["expected_reimbursement_sar"]))
    g = c.groupby("service_line").agg(encounters=("claim_id", "count"), gross_charges=("gross_charge_sar", "sum"),
                                      net_revenue=("realised", "sum"), direct_cost=("direct_cost_sar", "sum")).reset_index()
    g["contribution_margin"] = g["net_revenue"] - g["direct_cost"]
    g["margin_pct"] = g["contribution_margin"] / g["net_revenue"] * 100
    return g.sort_values("contribution_margin", ascending=False).reset_index(drop=True)


def monthly_trend(claims: pd.DataFrame) -> pd.DataFrame:
    c = claims.assign(month=claims["service_date"].dt.to_period("M").dt.to_timestamp())
    g = c.groupby("month").agg(claims=("claim_id", "count"), net_revenue=("expected_reimbursement_sar", "sum"),
                               denial_rate=("denied", "mean"), clean_claim_rate=("first_pass_clean", "mean")).reset_index()
    g["denial_rate"] *= 100
    g["clean_claim_rate"] *= 100
    return g


def monthly_cash(claims: pd.DataFrame) -> pd.Series:
    paid = claims[claims["paid_date"].notna()]
    return paid.groupby(paid["paid_date"].dt.to_period("M").dt.to_timestamp())["paid_sar"].sum()


def whatif(claims: pd.DataFrame, prevent_pct: float = 0.0, appeal_gain_pts: float = 0.0,
           ar_days_cut: float = 0.0, as_of: pd.Timestamp | None = None) -> dict:
    """Revenue-integrity scenario.

    prevent_pct      share of PREVENTABLE denials avoided by front-end fixes (eligibility, authorisation, coding)
    appeal_gain_pts  extra percentage points of appeal success on the remaining unrecovered denials
    ar_days_cut      days removed from the payment cycle (faster follow-up); converted to one-off cash acceleration
    """
    c = claims
    lost = c["denied"] & ~c["overturned"]
    prev_mask = lost & c["denial_reason"].isin(config.PREVENTABLE)
    recovered_prevention = float(c.loc[prev_mask, "expected_reimbursement_sar"].sum() * prevent_pct / 100)
    remaining_lost = float(c.loc[lost, "expected_reimbursement_sar"].sum()) - recovered_prevention
    recovered_appeals = max(remaining_lost, 0.0) * appeal_gain_pts / 100
    days = max((c["service_date"].max() - c["service_date"].min()).days, 1)
    daily_net = float(c["expected_reimbursement_sar"].sum()) / days
    n_prev_avoided = int(round(prev_mask.sum() * prevent_pct / 100))
    new_denials = int(c["denied"].sum()) - n_prev_avoided
    months = days / 30.4
    return {
        "recovered_prevention_sar": recovered_prevention,
        "recovered_appeals_sar": recovered_appeals,
        "total_recovered_sar": recovered_prevention + recovered_appeals,
        "annualised_recovered_sar": (recovered_prevention + recovered_appeals) * 12 / max(months, 1),
        "cash_acceleration_sar": daily_net * ar_days_cut,
        "baseline_denial_rate": float(c["denied"].mean() * 100),
        "scenario_denial_rate": new_denials / max(len(c), 1) * 100,
        "denials_avoided": n_prev_avoided,
    }


def payer_month(claims: pd.DataFrame) -> pd.DataFrame:
    """Per payer and month: denial rate, average days to pay and net revenue (frames for the animated chart)."""
    c = claims.assign(month=claims["service_date"].dt.to_period("M").dt.to_timestamp(),
                      days_to_pay=(claims["paid_date"] - claims["submitted_date"]).dt.days)
    g = c.groupby(["month", "payer"]).agg(net_revenue=("expected_reimbursement_sar", "sum"),
                                          denial_rate=("denied", "mean"), days_to_pay=("days_to_pay", "mean"),
                                          claims=("claim_id", "count")).reset_index()
    g["denial_rate"] *= 100
    return g


def month_over_month(claims: pd.DataFrame) -> dict:
    """Last complete service month vs the month before, for KPI deltas."""
    t = monthly_trend(claims).sort_values("month")
    if len(t) < 3:
        return {}
    last, prev = t.iloc[-2], t.iloc[-3]   # the final month may be partial
    return {"month": last["month"], "net_revenue": last["net_revenue"] - prev["net_revenue"],
            "clean_claim_rate": last["clean_claim_rate"] - prev["clean_claim_rate"],
            "denial_rate": last["denial_rate"] - prev["denial_rate"]}
