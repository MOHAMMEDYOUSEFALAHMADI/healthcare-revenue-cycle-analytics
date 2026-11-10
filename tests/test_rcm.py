import pandas as pd
import pytest

from rcm import charts, config, forecast, metrics
from rcm.data import generate_claims


@pytest.fixture(scope="module")
def claims():
    return generate_claims(months=10, claims_per_month=600, seed=4)


AS_OF = pd.Timestamp("2025-05-01")


def test_schema_and_ids(claims):
    assert claims["claim_id"].str.startswith("SYN-").all()
    assert set(claims["payer"]) <= set(config.PAYERS)
    assert (claims["submitted_date"] > claims["service_date"]).all()


def test_denied_claims_have_reason(claims):
    assert (claims.loc[claims["denied"], "denial_reason"] != "").all()
    assert (claims.loc[~claims["denied"], "denial_reason"] == "").all()
    assert not (claims["denied"] & claims["first_pass_clean"]).any()


def test_unrecovered_denials_not_paid(claims):
    lost = claims["denied"] & ~claims["overturned"]
    assert (claims.loc[lost, "paid_sar"] == 0).all()


def test_headline_ranges(claims):
    k = metrics.headline(claims, AS_OF)
    for key in ["clean_claim_rate", "denial_rate", "net_collection_rate", "preventable_denial_pct"]:
        assert 0 <= k[key] <= 100
    assert k["days_in_ar"] > 0


def test_days_in_ar_simple():
    df = pd.DataFrame({
        "service_date": pd.to_datetime(["2025-01-01"] * 90),
        "submitted_date": pd.to_datetime(["2025-01-02"] * 90),
        "expected_reimbursement_sar": [100.0] * 90,
        "paid_date": pd.NaT, "written_off": False,
    })
    # all 9,000 open, avg daily revenue over 90 d = 100 -> 90 days
    assert metrics.days_in_ar(df, pd.Timestamp("2025-01-31")) == pytest.approx(90.0)


def test_payer_mix_sums_to_100(claims):
    assert metrics.by_payer(claims)["payer_mix_pct"].sum() == pytest.approx(100)


def test_service_line_margin(claims):
    s = metrics.service_line_profitability(claims)
    assert (s["contribution_margin"] == s["net_revenue"] - s["direct_cost"]).all()


def test_holt_forecast_linear_series():
    y = pd.Series([10.0, 20, 30, 40, 50, 60], index=pd.date_range("2025-01-01", periods=6, freq="MS"))
    fc = forecast.holt_linear(y, horizon=3, alpha=0.9, beta=0.9)
    assert len(fc) == 3
    assert fc["forecast"].iloc[0] == pytest.approx(70, rel=0.05)
    assert (fc["upper"] >= fc["forecast"]).all() and (fc["lower"] <= fc["forecast"]).all()


def test_pipeline_after_as_of(claims):
    p = forecast.pipeline_collections(claims, AS_OF)
    assert (p["month"] >= AS_OF.to_period("M").to_timestamp()).all()


def test_charts_build(claims):
    assert charts.revenue_trend(metrics.monthly_trend(claims)).data
    assert charts.denial_pareto(metrics.denial_reasons(claims)).data
    assert charts.aging_chart(metrics.ar_aging(claims, AS_OF)).data
    assert charts.service_line_chart(metrics.service_line_profitability(claims)).data


def test_whatif_zero_is_neutral(claims):
    w = metrics.whatif(claims, 0, 0, 0)
    assert w["total_recovered_sar"] == 0
    assert w["scenario_denial_rate"] == pytest.approx(w["baseline_denial_rate"])


def test_whatif_full_prevention_recovers_preventable_value(claims):
    w = metrics.whatif(claims, 100, 0, 0)
    lost = claims["denied"] & ~claims["overturned"] & claims["denial_reason"].isin(config.PREVENTABLE)
    assert w["recovered_prevention_sar"] == pytest.approx(claims.loc[lost, "expected_reimbursement_sar"].sum())
    assert w["scenario_denial_rate"] < w["baseline_denial_rate"]


def test_whatif_monotonic(claims):
    a = metrics.whatif(claims, 20, 5, 2)
    b = metrics.whatif(claims, 60, 15, 10)
    assert b["total_recovered_sar"] > a["total_recovered_sar"]
    assert b["cash_acceleration_sar"] > a["cash_acceleration_sar"]


def test_payer_month_and_mom(claims):
    pm = metrics.payer_month(claims)
    assert set(pm["payer"]) <= set(config.PAYERS)
    assert pm["denial_rate"].between(0, 100).all()
    assert {"net_revenue", "clean_claim_rate", "denial_rate"} <= set(metrics.month_over_month(claims))


def test_new_rcm_charts_build(claims):
    charts.payer_bubble_animation(metrics.payer_month(claims))
    charts.denial_sunburst(claims)
    charts.recovery_waterfall(metrics.whatif(claims, 30, 5, 3))
