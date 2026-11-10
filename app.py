"""Healthcare Revenue Cycle Analytics - Streamlit app (synthetic data)."""
from pathlib import Path

import pandas as pd
import streamlit as st

from rcm import charts, config, forecast, metrics, ui
from rcm.data import generate_claims

DATA = Path(__file__).parent / "data" / "synthetic_claims.csv"
st.set_page_config(page_title="Revenue Cycle Analytics", page_icon="💳", layout="wide")
ui.inject_css()


@st.cache_data
def load() -> pd.DataFrame:
    if DATA.exists():
        return pd.read_csv(DATA, parse_dates=["service_date", "submitted_date", "paid_date"],
                           keep_default_na=True).fillna({"denial_reason": ""})
    return generate_claims()


claims_all = load()
AS_OF = claims_all["service_date"].max().normalize() + pd.Timedelta(days=1)

ui.sidebar_brand("Revenue Cycle", f"Claims as of {AS_OF:%d %b %Y}")
st.sidebar.markdown("---")
payers = st.sidebar.multiselect("Payers", list(config.PAYERS), default=list(config.PAYERS))
lines = st.sidebar.multiselect("Service lines", list(config.SERVICE_LINES), default=list(config.SERVICE_LINES))
horizon = st.sidebar.slider("Forecast horizon (months)", 3, 12, 6)
st.sidebar.markdown("---")
st.sidebar.markdown("**Definitions**  \nClean-claim rate: accepted first pass  \nDays in A/R: open A/R ÷ avg daily "
                    "net revenue (90 d)  \nNet collection rate: paid ÷ collectible (claims ≥ 120 d old)")

claims = claims_all[claims_all["payer"].isin(payers) & claims_all["service_line"].isin(lines)]

ui.hero("Healthcare Revenue Cycle Analytics",
        "Claims, denials, accounts receivable and service-line margin for a hospital revenue cycle, with a "
        "cash-flow forecast and a revenue-integrity scenario model.",
        ["Claims & denials", "Days in A/R", "Clean-claim rate", "Payer mix", "Service-line margin",
         "Cash forecast", "Scenario model", "Synthetic data"])

if claims.empty:
    st.warning("No claims match the filters.")
    st.stop()

k = metrics.headline(claims, AS_OF)
mom = metrics.month_over_month(claims)
T = config.TARGETS
c = st.columns(6)
ui.kpi(c[0], "Net revenue", f"SAR {k['net_revenue'] / 1e6:.1f}m", f"{k['claims']:,} claims · gross SAR {k['gross_charges'] / 1e6:.0f}m",
       "info")
ui.kpi(c[1], "Clean-claim rate", f"{k['clean_claim_rate']:.1f}%", f"target ≥ {T['clean_claim_rate']:.0f}% · last month vs prior",
       ui.status_for(k["clean_claim_rate"], T["clean_claim_rate"], T["clean_claim_rate"] - 5),
       ui.fmt_delta(mom.get("clean_claim_rate"), "", 1, True))
ui.kpi(c[2], "Denial rate", f"{k['denial_rate']:.1f}%", f"SAR {k['denied_value'] / 1e6:.1f}m denied",
       ui.status_for(k["denial_rate"], T["denial_rate"], T["denial_rate"] * 2, False),
       ui.fmt_delta(mom.get("denial_rate"), "", 1, False))
ui.kpi(c[3], "Days in A/R", f"{k['days_in_ar']:.0f}", f"target ≤ {T['days_in_ar']:.0f} days",
       ui.status_for(k["days_in_ar"], T["days_in_ar"], T["days_in_ar"] * 1.25, False))
ui.kpi(c[4], "Net collection rate", f"{k['net_collection_rate']:.1f}%", f"target ≥ {T['net_collection_rate']:.0f}%",
       ui.status_for(k["net_collection_rate"], T["net_collection_rate"], T["net_collection_rate"] - 4))
ui.kpi(c[5], "Preventable denials", f"{k['preventable_denial_pct']:.0f}%",
       f"appeal success {k['appeal_success_rate']:.0f}%", "warn")
st.write("")

tabs = st.tabs(["Overview", "Denials", "Payers & A/R", "Service lines", "Cash forecast", "Scenario model",
                "Claims data"])

with tabs[0]:
    ui.synthetic_banner()
    st.write("")
    a, b, cc = st.columns(3)
    ui.card(a, "Front end", "Eligibility checks, prior authorisation and registration accuracy drive most "
            "<b>preventable denials</b>.")
    ui.card(b, "Mid cycle", "Coding and documentation quality determine the <b>clean-claim rate</b> and "
            "first-pass acceptance.")
    ui.card(cc, "Back end", "Follow-up, appeals and payer performance determine <b>days in A/R</b> and the "
            "<b>net collection rate</b>.")
    st.write("")
    top = metrics.denial_reasons(claims).head(1)
    if len(top):
        t0 = top.iloc[0]
        ui.insight(f"The largest denial driver is <b>{t0.denial_reason}</b> ({t0['count']:,} claims, "
                   f"SAR {t0.value_sar / 1e6:.1f}m). {k['preventable_denial_pct']:.0f}% of denials are preventable "
                   "with front-end controls.")
    l, r = st.columns([1.6, 1])
    l.plotly_chart(charts.revenue_trend(metrics.monthly_trend(claims)), width="stretch")
    r.plotly_chart(charts.payer_mix(metrics.by_payer(claims)), width="stretch")
    st.caption("The synthetic data includes a simulated front-end authorisation initiative from month 9, which lowers denials.")

with tabs[1]:
    dr = metrics.denial_reasons(claims)
    l, r = st.columns([1.2, 1])
    l.plotly_chart(charts.denial_pareto(dr), width="stretch")
    r.plotly_chart(charts.denial_sunburst(claims), width="stretch")
    st.dataframe(dr.rename(columns={"overturned": "overturned_on_appeal_%"})
                 .style.format({"value_sar": "SAR {:,.0f}", "overturned_on_appeal_%": "{:.0f}%"}),
                 hide_index=True, width="stretch")

with tabs[2]:
    bp = metrics.by_payer(claims)
    l, r = st.columns(2)
    l.plotly_chart(charts.payer_denials(bp, T["denial_rate"]), width="stretch")
    r.plotly_chart(charts.aging_chart(metrics.ar_aging(claims, AS_OF)), width="stretch")
    st.plotly_chart(charts.payer_bubble_animation(metrics.payer_month(claims)), width="stretch")
    st.dataframe(bp.style.format({"net_revenue": "SAR {:,.0f}", "denial_rate": "{:.1f}%", "clean_claim_rate": "{:.1f}%",
                                  "avg_days_to_pay": "{:.0f}", "payer_mix_pct": "{:.1f}%"}),
                 hide_index=True, width="stretch")

with tabs[3]:
    sl = metrics.service_line_profitability(claims)
    st.plotly_chart(charts.service_line_chart(sl), width="stretch")
    st.dataframe(sl.style.format({c: "SAR {:,.0f}" for c in ["gross_charges", "net_revenue", "direct_cost",
                                                              "contribution_margin"]} | {"margin_pct": "{:.1f}%"}),
                 hide_index=True, width="stretch")
    st.caption("Contribution margin = realised net revenue (unrecovered denials excluded) − direct cost. "
               "Overheads are not allocated.")

with tabs[4]:
    hist = metrics.monthly_cash(claims)
    hist = hist[hist.index < AS_OF.to_period("M").to_timestamp()]
    fc = forecast.holt_linear(hist.iloc[2:], horizon)  # skip ramp-up months
    pipe = forecast.pipeline_collections(claims, AS_OF)
    st.plotly_chart(charts.cash_forecast(hist, fc, pipe), width="stretch")
    l, r = st.columns(2)
    l.markdown("#### Trend forecast")
    l.dataframe(fc.assign(month=fc["month"].dt.strftime("%b %Y")).style.format(
        {"forecast": "SAR {:,.0f}", "lower": "SAR {:,.0f}", "upper": "SAR {:,.0f}"}), hide_index=True, width="stretch")
    r.markdown("#### Expected collections from open claims")
    r.dataframe(pipe.assign(month=pipe["month"].dt.strftime("%b %Y")).style.format({"pipeline_sar": "SAR {:,.0f}"}),
                hide_index=True, width="stretch")
    st.caption("Method: Holt linear exponential smoothing on monthly cash, plus open non-denied claims scheduled by "
               "each payer's median historical days-to-pay. Illustrative only.")

with tabs[5]:
    ui.section("Revenue-integrity scenario", "Estimate the value of front-end denial prevention, stronger appeals "
               "and faster follow-up on the filtered claims.")
    a, b, cc = st.columns(3)
    prevent = a.slider("Preventable denials avoided (%)", 0, 100, 40, 5,
                       help="Eligibility checks, prior-authorisation tracking, coding edits before submission.")
    appeal = b.slider("Extra appeal success (pts)", 0, 30, 10)
    ar_cut = cc.slider("Days removed from the payment cycle", 0, 20, 5)
    w = metrics.whatif(claims, prevent, appeal, ar_cut)
    k1, k2, k3, k4 = st.columns(4)
    ui.kpi(k1, "Revenue recovered", f"SAR {w['total_recovered_sar'] / 1e6:.2f}m", "over the data period")
    ui.kpi(k2, "Annualised", f"SAR {w['annualised_recovered_sar'] / 1e6:.2f}m", "per year at current volume")
    ui.kpi(k3, "Denial rate", f"{w['scenario_denial_rate']:.1f}%", f"from {w['baseline_denial_rate']:.1f}% · "
           f"{w['denials_avoided']:,} denials avoided",
           ui.status_for(w["scenario_denial_rate"], T["denial_rate"], T["denial_rate"] * 2, False))
    ui.kpi(k4, "Cash acceleration", f"SAR {w['cash_acceleration_sar'] / 1e6:.2f}m", "one-off working-capital release",
           "info")
    st.write("")
    st.plotly_chart(charts.recovery_waterfall(w), width="stretch")
    st.caption("Recovered value uses expected reimbursement on denied claims that were not overturned. Cash acceleration "
               "= average daily net revenue × days removed. Illustrative only.")

with tabs[6]:
    st.dataframe(claims.head(500), hide_index=True, width="stretch")
    st.download_button("Download filtered claims (CSV)", claims.to_csv(index=False).encode(), "claims_filtered.csv")

ui.footer()
