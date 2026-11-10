"""Plotly figures for revenue-cycle analytics."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from . import config
from .ui import AMBER, NAVY, PALETTE, RED, SKY, TEAL

pio.templates["navy"] = go.layout.Template(pio.templates["plotly_white"])
pio.templates["navy"].layout.colorway = PALETTE
pio.templates["navy"].layout.font = dict(family="Inter, Segoe UI, sans-serif", color=NAVY)
TEMPLATE = "navy"


def revenue_trend(t: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=t["month"], y=t["net_revenue"] / 1e6, name="Net revenue (SAR m)", marker_color=SKY)
    fig.add_scatter(x=t["month"], y=t["denial_rate"], name="Denial rate %", yaxis="y2", line=dict(color=RED, width=3))
    fig.add_scatter(x=t["month"], y=t["clean_claim_rate"], name="Clean-claim rate %", yaxis="y2",
                    line=dict(color=TEAL, width=3))
    fig.update_layout(template=TEMPLATE, title="Net revenue, clean-claim and denial rates by service month",
                      yaxis=dict(title="SAR millions"), yaxis2=dict(title="%", overlaying="y", side="right", range=[0, 100], tickmode="linear", dtick=25,
                                                                    showgrid=False),
                      height=400, margin=dict(t=60), legend=dict(orientation="h", y=-0.15))
    return fig


def payer_mix(p: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Pie(labels=p["payer"], values=p["net_revenue"], hole=0.55, marker=dict(colors=PALETTE),
                           textinfo="percent"))
    fig.update_layout(template=TEMPLATE, title="Payer mix (share of net revenue)", height=380, margin=dict(t=60),
                      legend=dict(font=dict(size=11)))
    return fig


def payer_denials(p: pd.DataFrame, target: float) -> go.Figure:
    d = p.sort_values("denial_rate")
    fig = go.Figure(go.Bar(x=d["denial_rate"], y=d["payer"], orientation="h",
                           marker_color=[TEAL if v <= target else (AMBER if v <= target * 2 else RED) for v in d["denial_rate"]],
                           text=d["denial_rate"].round(1).astype(str) + "%", textposition="outside"))
    fig.add_vline(x=target, line_dash="dash", line_color=NAVY, annotation_text=f"Target ≤ {target:.0f}%")
    fig.update_layout(template=TEMPLATE, title="Denial rate by payer", xaxis_title="% of claims denied",
                      height=380, margin=dict(t=60))
    return fig


def denial_pareto(d: pd.DataFrame) -> go.Figure:
    cum = d["count"].cumsum() / d["count"].sum() * 100
    fig = go.Figure()
    fig.add_bar(x=d["denial_reason"], y=d["count"], name="Denied claims",
                marker_color=[NAVY if p else SKY for p in d["preventable"]])
    fig.add_scatter(x=d["denial_reason"], y=cum, yaxis="y2", name="Cumulative %", line=dict(color=AMBER, width=3))
    fig.update_layout(template=TEMPLATE, title="Denial reasons – Pareto (dark = preventable)", height=440,
                      yaxis=dict(title="Claims"), yaxis2=dict(title="Cumulative %", overlaying="y", side="right",
                                                              range=[0, 105], tickmode="linear", dtick=25, showgrid=False),
                      margin=dict(t=60, b=140), legend=dict(orientation="h", y=1.08))
    return fig


def aging_chart(a: pd.DataFrame) -> go.Figure:
    fig = px.bar(a, x="bucket", y=a["balance"] / 1e6, color="payer", color_discrete_sequence=PALETTE)
    fig.update_layout(template=TEMPLATE, title="Accounts receivable aging by payer (days since submission)",
                      yaxis_title="Open A/R (SAR m)", xaxis_title="", height=400, margin=dict(t=60),
                      legend=dict(font=dict(size=10)))
    return fig


def service_line_chart(s: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=s["service_line"], y=s["net_revenue"] / 1e6, name="Net revenue", marker_color=SKY)
    fig.add_bar(x=s["service_line"], y=s["direct_cost"] / 1e6, name="Direct cost", marker_color="#6c757d")
    fig.add_scatter(x=s["service_line"], y=s["margin_pct"], name="Contribution margin %", yaxis="y2", mode="lines+markers",
                    line=dict(color=TEAL, width=3), marker=dict(size=10))
    fig.update_layout(template=TEMPLATE, title="Service-line profitability", barmode="group", height=420,
                      yaxis=dict(title="SAR millions"), yaxis2=dict(title="Margin %", overlaying="y", side="right",
                                                                    showgrid=False),
                      margin=dict(t=60), legend=dict(orientation="h", y=-0.15))
    return fig


def cash_forecast(history: pd.Series, fc: pd.DataFrame, pipeline: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=history.index, y=history.values / 1e6, name="Actual cash collected", mode="lines+markers",
                    line=dict(color=NAVY, width=3))
    fig.add_scatter(x=list(fc["month"]) + list(fc["month"][::-1]),
                    y=list(fc["upper"] / 1e6) + list(fc["lower"][::-1] / 1e6), fill="toself", mode="lines",
                    fillcolor="rgba(42,157,143,0.15)", line=dict(width=0), name="95% band", hoverinfo="skip")
    fig.add_scatter(x=fc["month"], y=fc["forecast"] / 1e6, name="Trend forecast (Holt)", line=dict(color=TEAL, dash="dash", width=3))
    if len(pipeline):
        fig.add_bar(x=pipeline["month"], y=pipeline["pipeline_sar"] / 1e6, name="Expected from open claims",
                    marker_color="rgba(233,196,106,0.7)")
    fig.update_layout(template=TEMPLATE, title="Cash-flow forecast (SAR millions)", height=420, margin=dict(t=60),
                      yaxis_title="SAR millions", legend=dict(orientation="h", y=-0.15))
    return fig


def payer_bubble_animation(pm: pd.DataFrame) -> go.Figure:
    d = pm.dropna(subset=["days_to_pay"]).copy()
    d["month_label"] = d["month"].dt.strftime("%Y-%m")
    d["net_m"] = d["net_revenue"] / 1e6
    fig = px.scatter(d, x="days_to_pay", y="denial_rate", size="net_m", color="payer", animation_frame="month_label",
                     animation_group="payer", size_max=55, color_discrete_sequence=PALETTE,
                     range_x=[0, d["days_to_pay"].max() * 1.15], range_y=[-1, d["denial_rate"].max() * 1.2],
                     labels={"days_to_pay": "Average days to pay", "denial_rate": "Denial rate %", "net_m": "Net SAR m",
                             "month_label": "Service month", "payer": "Payer"})
    fig.add_hline(y=5, line_dash="dot", line_color=RED, annotation_text="Denial target 5%")
    fig.update_layout(template=TEMPLATE, title="Payer performance by service month · press ▶",
                      height=500, margin=dict(t=60), legend=dict(orientation="h", y=-0.2))
    if fig.layout.updatemenus:
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 700
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 400
    return fig


def denial_sunburst(claims: pd.DataFrame) -> go.Figure:
    d = claims[claims["denied"]].assign(type=lambda x: x["denial_reason"].map(
        lambda r: "Preventable" if r in config.PREVENTABLE else "Non-preventable"))
    t = d.groupby(["payer", "type", "denial_reason"])["expected_reimbursement_sar"].sum().reset_index()
    fig = px.sunburst(t, path=["payer", "type", "denial_reason"], values="expected_reimbursement_sar",
                      color="type", color_discrete_map={"Preventable": AMBER, "Non-preventable": SKY, "(?)": "#dfe7f1"})
    fig.update_traces(hovertemplate="%{label}<br>SAR %{value:,.0f}", maxdepth=2, insidetextorientation="horizontal")
    fig.update_layout(template=TEMPLATE, title="Denied value by payer and reason · click to drill down",
                      height=540, margin=dict(t=60, l=5, r=5, b=5))
    return fig


def recovery_waterfall(w: dict) -> go.Figure:
    fig = go.Figure(go.Waterfall(
        x=["Prevented denials", "Extra appeal recoveries", "Total recovered", "One-off cash acceleration"],
        measure=["relative", "relative", "total", "absolute"],
        y=[w["recovered_prevention_sar"] / 1e6, w["recovered_appeals_sar"] / 1e6, 0, w["cash_acceleration_sar"] / 1e6],
        text=[f"{v / 1e6:.2f}" for v in [w["recovered_prevention_sar"], w["recovered_appeals_sar"],
                                          w["total_recovered_sar"], w["cash_acceleration_sar"]]],
        textposition="outside", increasing=dict(marker=dict(color=TEAL)), totals=dict(marker=dict(color=NAVY)),
        connector=dict(line=dict(color=SKY))))
    fig.update_layout(template=TEMPLATE, title="Scenario value over the data period (SAR m)", height=400,
                      margin=dict(t=60), yaxis_title="SAR m")
    return fig
