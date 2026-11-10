"""Shared UI helpers: navy healthcare theme, hero banner, KPI cards with deltas and callouts for Streamlit."""
from __future__ import annotations

import math

import streamlit as st

NAVY = "#0b2545"
NAVY_2 = "#13315c"
BLUE = "#1d4e89"
TEAL = "#2a9d8f"
SKY = "#8da9c4"
AMBER = "#e9c46a"
RED = "#d1495b"
LIGHT = "#eef4ed"
PALETTE = [NAVY_2, TEAL, "#5fa8d3", AMBER, RED, SKY, "#6c757d", "#264653"]

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {{ --navy:{NAVY}; --teal:{TEAL}; }}
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
.block-container {{ padding-top: 3.0rem; padding-bottom: 2rem; max-width: 1520px; }}
@keyframes fadeUp {{ from {{ opacity:0; transform: translateY(10px); }} to {{ opacity:1; transform:none; }} }}
@keyframes shimmer {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
@keyframes pulse {{ 0%,100% {{ box-shadow: 0 0 0 0 rgba(42,157,143,.55); }} 50% {{ box-shadow: 0 0 0 6px rgba(42,157,143,0); }} }}

/* ---------- Sidebar (dark navy, high-contrast controls) ---------- */
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {NAVY} 0%, {NAVY_2} 100%); }}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] li, [data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {{ color: #f1f5f9 !important; }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {{ color: #c9d6e3 !important; }}
/* every input surface in the sidebar: white field, navy text */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"],
[data-testid="stSidebar"] [data-baseweb="base-input"],
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] [data-testid="stDateInput"] > div > div,
[data-testid="stSidebar"] [data-testid="stNumberInput"] > div > div {{ background-color: #ffffff !important; border-radius: 8px; }}
[data-testid="stSidebar"] [data-baseweb="select"] *, [data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea, [data-testid="stSidebar"] [data-baseweb="input"] *,
[data-testid="stSidebar"] [data-testid="stDateInput"] *, [data-testid="stSidebar"] [data-testid="stNumberInput"] input {{
    color: {NAVY} !important; -webkit-text-fill-color: {NAVY} !important; }}
[data-testid="stSidebar"] [data-baseweb="tag"] {{ background-color: {TEAL} !important; }}
[data-testid="stSidebar"] [data-baseweb="tag"] * {{ color: #fff !important; -webkit-text-fill-color: #fff !important; }}
[data-testid="stSidebar"] [data-testid="stSliderTickBarMin"], [data-testid="stSidebar"] [data-testid="stSliderTickBarMax"],
[data-testid="stSidebar"] [data-testid="stThumbValue"] {{ color: #f1f5f9 !important; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.18); }}
.side-brand {{ padding: 4px 0 6px 0; }}
.side-brand .t {{ font-size: 1.25rem; font-weight: 800; color: #fff; letter-spacing: .01em; }}
.side-brand .s {{ font-size: .8rem; color: #c9d6e3; }}
.side-chip {{ display:inline-block; margin-top:8px; padding:3px 10px; border-radius:999px; font-size:.72rem;
        background: rgba(233,196,106,.18); border:1px solid rgba(233,196,106,.6); color:#fbe7b0 !important; }}

/* ---------- Hero ---------- */
.hero {{ background: linear-gradient(120deg, {NAVY} 0%, {BLUE} 55%, {TEAL} 120%); background-size: 200% 200%;
        animation: shimmer 14s ease infinite, fadeUp .6s ease both; color: #fff;
        padding: 26px 32px; border-radius: 18px; margin-bottom: 18px; box-shadow: 0 10px 28px rgba(11,37,69,.22);
        position: relative; overflow: hidden; }}
.hero:after {{ content:""; position:absolute; right:-80px; top:-80px; width:260px; height:260px; border-radius:50%;
        background: radial-gradient(circle, rgba(255,255,255,.16) 0%, rgba(255,255,255,0) 70%); }}
.hero h1 {{ color: #fff; font-size: 2.05rem; font-weight: 800; margin: 0 0 4px 0; padding: 0; }}
.hero p {{ color: #dbe7f3; margin: 0; font-size: 1.02rem; max-width: 1050px; }}
.hero .badges span {{ display:inline-block; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28);
        padding: 3px 11px; border-radius: 999px; font-size: .78rem; margin: 10px 6px 0 0; color:#fff; }}
.hero .live {{ display:inline-block; width:9px; height:9px; border-radius:50%; background:{TEAL}; margin-right:7px;
        animation: pulse 2s infinite; vertical-align: middle; }}

/* ---------- KPI cards ---------- */
.kpi {{ background: #fff; border: 1px solid #e3e9f1; border-left: 5px solid {TEAL}; border-radius: 14px;
        padding: 14px 16px; box-shadow: 0 2px 10px rgba(11,37,69,.06); height: 100%;
        animation: fadeUp .55s ease both; transition: transform .18s ease, box-shadow .18s ease; }}
.kpi:hover {{ transform: translateY(-3px); box-shadow: 0 10px 22px rgba(11,37,69,.12); }}
.kpi .label {{ color: #4a5a6e; font-size: .76rem; text-transform: uppercase; letter-spacing: .05em; font-weight:600; }}
.kpi .value {{ color: {NAVY}; font-size: 1.65rem; font-weight: 800; line-height: 1.25; }}
.kpi .sub {{ font-size: .80rem; color: #4a5a6e; }}
.kpi .delta {{ display:inline-block; font-size:.74rem; font-weight:700; padding:1px 8px; border-radius:999px; margin-left:4px;
        vertical-align: middle; }}
.kpi .delta.up {{ background:#d8f0ec; color:#1d6f65; }} .kpi .delta.down {{ background:#f7d6da; color:#9b2226; }}
.kpi .delta.flat {{ background:#eef2f7; color:#4a5a6e; }}
.kpi.good {{ border-left-color: {TEAL}; }} .kpi.warn {{ border-left-color: {AMBER}; }} .kpi.bad {{ border-left-color: {RED}; }}
.kpi.info {{ border-left-color: {BLUE}; }}

/* ---------- Cards, callouts, section headers ---------- */
.card {{ background:#f7f9fc; border:1px solid #e3e9f1; border-radius:14px; padding:16px 18px; height:100%;
        animation: fadeUp .6s ease both; transition: border-color .2s; }}
.card:hover {{ border-color: {SKY}; }}
.card h4 {{ color:{NAVY}; margin-top:0; }}
.insight {{ background: linear-gradient(90deg, #eaf4f3 0%, #f4f8fc 100%); border:1px solid #cfe5e2; border-left:5px solid {TEAL};
        border-radius:12px; padding:12px 16px; color:{NAVY}; font-size:.93rem; margin: 6px 0 12px 0; animation: fadeUp .5s ease both; }}
.insight b {{ color:{NAVY}; }}
.section {{ margin: 8px 0 6px 0; }}
.section .t {{ font-size:1.15rem; font-weight:800; color:{NAVY}; }}
.section .s {{ font-size:.86rem; color:#4a5a6e; }}
.synthetic {{ background:#fff8e6; border:1px solid {AMBER}; color:#6b4e00; padding:8px 14px; border-radius:10px; font-size:.86rem; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; flex-wrap: wrap; }}
.stTabs [data-baseweb="tab"] {{ background:#f2f5f9; border-radius:10px 10px 0 0; padding:8px 16px; transition: background .2s; }}
.stTabs [data-baseweb="tab"]:hover {{ background:#e3ebf5; }}
.stTabs [aria-selected="true"] {{ background:{NAVY} !important; }}
.stTabs [aria-selected="true"] * {{ color:#fff !important; }}
[data-testid="stMetric"] {{ background:#fff; border:1px solid #e3e9f1; border-radius:12px; padding:10px 14px; }}
.stDownloadButton button, .stButton button {{ border-radius:10px; border:1px solid {BLUE}; color:{BLUE}; font-weight:600; }}
.stDownloadButton button:hover, .stButton button:hover {{ background:{BLUE}; color:#fff; }}
h2, h3, h4 {{ color: {NAVY}; }}
footer {{ visibility: hidden; }}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def sidebar_brand(title: str, subtitle: str = "", chip: str = "Synthetic data") -> None:
    st.sidebar.markdown(f'<div class="side-brand"><div class="t">{title}</div><div class="s">{subtitle}</div>'
                        f'<span class="side-chip">{chip}</span></div>', unsafe_allow_html=True)


def hero(title: str, subtitle: str, badges: list[str] | None = None) -> None:
    b = "".join(f"<span>{x}</span>" for x in (badges or []))
    st.markdown(f'<div class="hero"><h1>{title}</h1><p><span class="live"></span>{subtitle}</p>'
                f'<div class="badges">{b}</div></div>', unsafe_allow_html=True)


def fmt_delta(delta: float | None, unit: str = "", digits: int = 1, higher_is_better: bool = True) -> str:
    """HTML pill for a change vs the comparison period (green when the change is an improvement)."""
    if delta is None or (isinstance(delta, float) and math.isnan(delta)):
        return ""
    if abs(delta) < 10 ** (-digits) / 2:
        return f'<span class="delta flat">● 0{unit}</span>'
    arrow = "▲" if delta > 0 else "▼"
    good = (delta > 0) == higher_is_better
    return f'<span class="delta {"up" if good else "down"}">{arrow} {abs(delta):.{digits}f}{unit}</span>'


def kpi(col, label: str, value: str, sub: str = "", status: str = "good", delta: str = "") -> None:
    col.markdown(f'<div class="kpi {status}"><div class="label">{label}</div>'
                 f'<div class="value">{value}{delta}</div><div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def card(col, title: str, body_md: str) -> None:
    col.markdown(f'<div class="card"><h4>{title}</h4>{body_md}</div>', unsafe_allow_html=True)


def insight(text: str, target=None) -> None:
    (target or st).markdown(f'<div class="insight">{text}</div>', unsafe_allow_html=True)


def section(title: str, subtitle: str = "", target=None) -> None:
    (target or st).markdown(f'<div class="section"><div class="t">{title}</div><div class="s">{subtitle}</div></div>',
                            unsafe_allow_html=True)


def synthetic_banner() -> None:
    st.markdown('<div class="synthetic"><b>Synthetic data.</b> All records are randomly generated for '
                'demonstration. No real patients, organisations or results are represented.</div>',
                unsafe_allow_html=True)


def footer(author: str = "Mohammed Alahmadi") -> None:
    st.divider()
    st.caption(f"Built by {author} · [LinkedIn](https://www.linkedin.com/in/mohyou) · "
               "[GitHub](https://github.com/MOHAMMEDYOUSEFALAHMADI) · Open-source portfolio project · All data is synthetic.")


def status_for(value: float, good: float, warn: float, higher_is_better: bool = True) -> str:
    if higher_is_better:
        return "good" if value >= good else ("warn" if value >= warn else "bad")
    return "good" if value <= good else ("warn" if value <= warn else "bad")
