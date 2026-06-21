"""
Real Madrid CF — Tactical & Player Performance Analytics
Streamlit v3.0 — Professional UI matching the Dash dashboard at /benchmarking
"""

import os
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

import streamlit as st

# ── Path & env setup ─────────────────────────────────────────────────────────
_ROOT    = Path(__file__).resolve().parent
_APP_DIR = _ROOT / "dashboard" / "app"
sys.path.insert(0, str(_APP_DIR))
os.environ.setdefault("DATA_ROOT", str(_ROOT / "dashboard" / "data"))

import base64 as _b64
_UE_LOGO_PATH   = _APP_DIR / "assets" / "ue_real_madrid_logo.png"
_RM_CREST_PATH  = _APP_DIR / "assets" / "rm_crest.jpg"
_UE_LOGO_B64    = ""
_RM_CREST_B64   = ""
if _UE_LOGO_PATH.exists():
    _UE_LOGO_B64 = _b64.b64encode(_UE_LOGO_PATH.read_bytes()).decode()
if _RM_CREST_PATH.exists():
    _RM_CREST_B64 = _b64.b64encode(_RM_CREST_PATH.read_bytes()).decode()

# ── Analytics modules (reuse verified Dash backend) ──────────────────────────
from config import COLOR_SCHEME
from utils.data_loader import (
    get_season_match_list, calc_season_kpis, get_season_results_table,
    load_match_json, extract_match_meta, parse_events, calc_match_kpis,
    get_shot_data, get_player_stats, get_match_lineup_status,
    calc_ppda, get_competition_seasons, iter_match_files,
)
from utils.data_helpers import (
    get_match_options, get_competition_options, get_season_options,
    get_available_seasons,
)
import pages.match_analysis    as ma
import pages.tactical_phases   as tp
import pages.player_analysis   as pa
import pages.benchmarking      as bm
import pages.home              as hp
import pages.opponent_analysis as oa

# ── Report generator (new additive module) ────────────────────────────────────
import report_generator as rg

# ── Constants ─────────────────────────────────────────────────────────────────
_C    = COLOR_SCHEME
_RM   = _C["accent_blue"]
_OPP  = _C["accent_red"]
_GOLD = "#d4af37"
_NAVY = "#0b1730"

# ── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Real Madrid CF — Tactical Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS — Real Madrid light theme ─────────────────────────────────────────────
st.markdown("""
<style>
:root {
  --rm-bg:          #f8f7f3;
  --rm-surface:     #ffffff;
  --rm-surface-2:   #f3f1eb;
  --rm-border:      #e2ddd0;
  --rm-border-2:    #d4c898;
  --rm-text:        #0b1730;
  --rm-text-2:      #334155;
  --rm-text-3:      #64748b;
  --rm-blue:        #1d4ed8;
  --rm-blue-light:  rgba(29,78,216,0.10);
  --rm-blue-mid:    #2563eb;
  --rm-navy:        #0b1730;
  --rm-gold:        #c8a951;
  --rm-gold-2:      #a8882e;
  --rm-gold-light:  #f5eed6;
  --rm-silver:      #64748b;
  --rm-silver-2:    #94a3b8;
  --rm-green:       #059669;
  --rm-green-light: rgba(5,150,105,0.10);
  --rm-red:         #dc2626;
  --rm-red-light:   rgba(220,38,38,0.10);
  --rm-amber:       #d97706;
  --rm-amber-light: rgba(217,119,6,0.10);
  --rm-purple:      #7c3aed;
  --rm-purple-light:rgba(124,58,237,0.10);
  --rm-radius:      8px;
  --rm-radius-lg:   12px;
  --rm-shadow:      0 2px 8px rgba(11,23,48,0.08);
  --rm-shadow-md:   0 6px 20px rgba(11,23,48,0.12);
}

/* ── App background — Real Madrid white/cream ── */
.stApp {
  background: linear-gradient(180deg, #f8f7f3 0%, #f5f3ee 60%, #f8f7f3 100%) !important;
  color: #0b1730 !important;
  font-family: 'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
}

/* ── Main container ── */
.main .block-container {
  padding-top: 0 !important;
  max-width: 100% !important;
  padding-left:  1.5rem !important;
  padding-right: 1.5rem !important;
  padding-bottom: 3rem !important;
}

/* ── Hide sidebar completely ── */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarNavItems"] { display: none !important; }
.stMain { margin-left: 0 !important; }

/* ── Top Navigation Bar — kept dark navy (RM brand identity) ── */
.rm-topnav-strip {
  background: linear-gradient(120deg, #060f1e 0%, #0b1730 40%, #0e1f3a 70%, #060f1e 100%);
  border-bottom: 3px solid var(--rm-gold);
  margin: 0 -1.5rem;
  padding: 10px 24px 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.40);
  position: sticky;
  top: 0;
  z-index: 999;
}

/* Nav buttons */
.rm-topnav-strip button,
.rm-topnav-strip [data-testid="stBaseButton-secondary"] {
  background: rgba(255,255,255,0.07) !important;
  color: #c8d8f0 !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  border-radius: 6px !important;
  font-size: 10.5px !important;
  font-weight: 500 !important;
  min-height: 34px !important;
  transition: all .15s ease !important;
  width: 100% !important;
  padding-left: 4px !important;
  padding-right: 4px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
}
/* Prevent button label from wrapping */
.rm-topnav-strip button *,
.rm-topnav-strip button p,
.rm-topnav-strip button span,
.rm-topnav-strip button div,
.rm-topnav-strip [data-testid="stBaseButton-secondary"] *,
.rm-topnav-strip [data-testid="stBaseButton-primary"] *,
[data-testid="stBaseButton-content"],
[data-testid="stBaseButton-content"] * {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  line-height: 1.2 !important;
}
.rm-topnav-strip button:hover,
.rm-topnav-strip [data-testid="stBaseButton-secondary"]:hover {
  background: rgba(255,255,255,0.16) !important;
  color: #ffffff !important;
  border-color: rgba(200,169,81,0.50) !important;
}
/* Active nav button — gold highlight */
.rm-topnav-strip [data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #c8a951 0%, #a8882e 100%) !important;
  color: #ffffff !important;
  border: 1px solid rgba(200,169,81,0.70) !important;
  font-weight: 700 !important;
  box-shadow: 0 2px 10px rgba(200,169,81,0.40) !important;
  width: 100% !important;
  min-height: 34px !important;
  padding-left: 4px !important;
  padding-right: 4px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
}
/* Widget labels inside strip */
.rm-topnav-strip label,
.rm-topnav-strip .stSelectbox label {
  color: #94a3b8 !important;
  font-size: 9px !important;
  text-transform: uppercase !important;
  letter-spacing: 1.2px !important;
  font-weight: 700 !important;
}
/* Selectboxes inside strip */
.rm-topnav-strip [data-baseweb="select"] > div {
  background: rgba(255,255,255,0.10) !important;
  border-color: rgba(255,255,255,0.22) !important;
  color: #e2e8f0 !important;
}
.rm-topnav-strip [data-baseweb="select"] span { color: #e2e8f0 !important; }
.rm-topnav-strip p { color: #e2e8f0 !important; margin: 0 !important; }

/* Brand block */
.rm-nb-brand { display:flex; align-items:center; gap:8px; padding:2px 0; }
.rm-nb-logos { display:flex; align-items:center; gap:4px; flex-shrink:0; }
.rm-nb-crest {
  width:36px; height:36px; border-radius:50%;
  object-fit:cover; border:2px solid rgba(200,169,81,0.7);
  background:#fff;
}
/* High-specificity selectors to beat global span/p colour rules */
.rm-topnav-strip .rm-nb-brand .rm-nb-title,
.rm-topnav-strip [data-testid="stMarkdownContainer"] .rm-nb-title {
  font-weight:700; font-size:13px; color:#ffffff !important;
  letter-spacing:0.3px; line-height:1.2;
}
.rm-topnav-strip .rm-nb-brand .rm-nb-sub,
.rm-topnav-strip [data-testid="stMarkdownContainer"] .rm-nb-sub {
  font-size:10px; color:#e2e8f0 !important;
  text-transform:uppercase; letter-spacing:1px; line-height:1.4;
}
/* Ensure no background bleeds into brand text area */
.rm-topnav-strip [data-testid="stMarkdownContainer"] {
  background: transparent !important;
}
/* Author block */
.rm-nb-author { text-align:right; }
.rm-nb-author-name   { color:#fff; font-weight:700; font-size:12px; line-height:1.4; }
.rm-nb-author-course { color:var(--rm-gold); font-size:10px; line-height:1.4; }

/* ── Global widget colours — light theme ── */
[data-baseweb="select"] > div {
  background: #ffffff !important;
  border-color: #d4c898 !important;
  color: #0b1730 !important;
}
[data-baseweb="select"] span { color: #0b1730 !important; }
/* Prevent selectbox value text from being clipped */
[data-baseweb="select"] [data-testid="stSelectboxValue"],
[data-baseweb="select"] > div > div > div {
  overflow: visible !important;
  white-space: nowrap !important;
  text-overflow: clip !important;
  font-size: 12px !important;
  color: #0b1730 !important;
}
/* Dropdown popup */
[data-baseweb="popover"] [role="listbox"] { background: #ffffff !important; border: 1px solid #d4c898 !important; }
[data-baseweb="menu-item"] { color: #0b1730 !important; }
[data-baseweb="menu-item"]:hover { background: #f5eed6 !important; }
/* Input / text area */
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
  background: #ffffff !important;
  color: #0b1730 !important;
  border-color: #d4c898 !important;
}
/* Multiselect tags — gold tint */
[data-baseweb="tag"] {
  background: rgba(200,169,81,0.15) !important;
  color: #7a5c10 !important;
  border: 1px solid rgba(200,169,81,0.45) !important;
  border-radius: 4px !important;
}
/* All widget labels */
label { color: #334155 !important; font-size:13px; }
/* Streamlit default text — exclude the navbar strip */
p:not(.rm-topnav-strip *), li { color: #1e293b; }
span:not(.rm-topnav-strip *) { color: #334155; }
/* Radio & checkbox labels */
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label { color: #0b1730 !important; }
/* Streamlit info/warning/error boxes */
[data-testid="stAlert"] { border-radius: 8px !important; }

/* ── Plotly chart cards ── */
[data-testid="stPlotlyChart"] {
  background: #ffffff !important;
  border-radius: 0 0 12px 12px !important;
  border: 1px solid #e2ddd0 !important;
  border-top: none !important;
  box-shadow: 0 4px 16px rgba(11,23,48,0.08) !important;
  padding: 4px !important;
  margin-bottom: 16px !important;
  overflow: hidden !important;
  transition: box-shadow .18s ease;
}
[data-testid="stPlotlyChart"]:hover {
  box-shadow: 0 8px 24px rgba(11,23,48,0.14) !important;
}

/* ── DataFrame ── */
[data-testid="stDataFrame"] {
  border-radius: 8px !important;
  border: 1px solid #e2ddd0 !important;
  box-shadow: var(--rm-shadow) !important;
  overflow: hidden !important;
  margin-bottom: 16px !important;
}

/* ── Custom HTML elements ── */

/* Page header */
.rm-page-header {
  position:relative; overflow:hidden;
  margin:16px 0 12px; padding:14px 220px 14px 4px;
  background:linear-gradient(90deg,#f8f7f3 0%,#f5f3ee 100%);
  border-radius:10px;
  border:1px solid #e8e4da;
}
.rm-page-header-logo {
  position:absolute; right:16px; top:50%; transform:translateY(-50%);
  height:46px; max-width:200px; object-fit:contain;
  opacity:0.85; pointer-events:none;
}
.rm-page-title {
  font-size:20px; font-weight:800; color:#0b1730;
  border-left:4px solid var(--rm-gold); padding-left:12px;
  margin:0 0 4px 0; position:relative; z-index:1;
}
.rm-page-subtitle { font-size:13px; color:#64748b; margin:0 0 0 16px; position:relative; z-index:1; }

/* Section header */
.section-header {
  font-size:15px; font-weight:700; color:#0b1730;
  border-bottom:2px solid var(--rm-gold); padding-bottom:6px;
  margin:20px 0 12px 0;
}

/* Breadcrumb sub-bar */
.rm-breadcrumb { color: #64748b !important; }

/* Chart card header */
.chart-card-header {
  background: linear-gradient(180deg, #0b1730 0%, #0e1f3a 100%);
  border: 1px solid #0b1730;
  border-bottom: 2px solid var(--rm-gold);
  border-radius: 12px 12px 0 0;
  padding: 11px 16px;
  font-weight:700; color:#ffffff; font-size:13px; letter-spacing:0.3px;
  margin-top:8px; margin-bottom:0;
}

/* KPI cards */
.kpi-card {
  background: #ffffff;
  border: 1px solid #e2ddd0;
  border-radius: 12px;
  padding: 14px 16px;
  position: relative; overflow: hidden;
  text-align: center;
  box-shadow: 0 2px 10px rgba(11,23,48,0.07);
  transition: transform .18s ease, box-shadow .18s ease;
  min-height: 90px;
}
.kpi-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:3px;
  background: linear-gradient(90deg, #c8a951 0%, #a8882e 50%, #d4c898 100%);
}
.kpi-card:hover { transform:translateY(-2px); box-shadow:0 8px 24px rgba(11,23,48,0.13); border-color:#d4c898; }
.kpi-title { font-size:10px; text-transform:uppercase; letter-spacing:.06em; color:#64748b; font-weight:600; margin:0 0 4px; }
.kpi-value { font-size:26px; font-weight:800; line-height:1; font-variant-numeric:tabular-nums; letter-spacing:-0.5px; margin-bottom:2px; color:#0b1730; }
.kpi-sub   { font-size:11px; color:#94a3b8; margin-top:3px; }

/* Record badge */
.rm-record-card {
  background: #ffffff;
  border: 1px solid #e2ddd0;
  border-left: 4px solid var(--rm-gold);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 16px;
  box-shadow: var(--rm-shadow);
  display: flex; justify-content:space-between; align-items:center;
  flex-wrap: wrap; gap: 8px;
}
.rm-record-title { font-size:15px; font-weight:700; color:#0b1730; margin:0; }
.rm-record-sub   { font-size:12px; color:#64748b; margin:2px 0 0; }
.rm-badge {
  display:inline-flex; align-items:center;
  padding:3px 10px; border-radius:20px;
  font-size:11px; font-weight:700; letter-spacing:0.3px;
}
.rm-badge-blue   { background:rgba(29,78,216,0.10);  color:#1d4ed8; }
.rm-badge-green  { background:rgba(5,150,105,0.10);   color:#059669; }
.rm-badge-red    { background:rgba(220,38,38,0.10);   color:#dc2626; }
.rm-badge-amber  { background:rgba(217,119,6,0.10);   color:#d97706; }
.rm-badge-purple { background:rgba(124,58,237,0.10);  color:#7c3aed; }

/* Match header card */
.rm-match-header {
  background: #ffffff;
  border: 1px solid #e2ddd0;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: var(--rm-shadow);
  text-align: center;
}
.rm-match-score { font-size:40px; font-weight:900; line-height:1; font-variant-numeric:tabular-nums; color:#0b1730; }
.rm-match-team  { font-size:18px; font-weight:700; color:#0b1730; }
.rm-result-win  { color:var(--rm-green); }
.rm-result-draw { color:var(--rm-amber); }
.rm-result-loss { color:var(--rm-red); }

/* Alert info box */
.rm-alert-info {
  background: rgba(29,78,216,0.06);
  border-left: 3px solid var(--rm-blue);
  border-radius: 0 8px 8px 0;
  padding: 10px 14px; font-size:12px; color:#1d4ed8; margin:8px 0 16px;
}

/* Footer */
.rm-footer {
  margin-top: 40px;
  padding: 14px 22px;
  background: linear-gradient(90deg, #060f1e 0%, #0b1730 100%);
  border-top: 3px solid var(--rm-gold);
  color: #94a3b8;
  font-size:.80rem;
  display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:center; text-align:center;
  margin-left: -1.5rem; margin-right: -1.5rem;
}
.rm-footer-title  { color:#fff; font-weight:700; }
.rm-footer-author { color:var(--rm-gold); font-weight:700; }
.rm-footer-course { color:#e2e8f0; }
.rm-footer-meta   { color:#94a3b8; }
.rm-footer-dot    { color:var(--rm-gold); opacity:.7; }

/* Phase alert box */
.rm-phase-alert {
  background: #f5eed6;
  border: 1px solid #d4c898;
  border-left: 4px solid var(--rm-gold);
  border-radius: 8px;
  padding: 12px 16px;
  color: #4a3a10;
  font-size: 12px;
  margin-bottom: 12px;
}
.rm-phase-alert b { color: #7a5c10; }

/* Styled HTML table */
.rm-table-wrap { overflow-x:auto; margin-bottom:16px; }
table.rm-table {
  width:100%; border-collapse:collapse; font-size:13px;
  background:#ffffff; border-radius:8px; overflow:hidden;
  box-shadow: var(--rm-shadow);
  border: 1px solid #e2ddd0;
}
table.rm-table thead tr { background: #0b1730; }
table.rm-table th {
  padding:8px 10px; color:#c8a951; font-size:10px;
  text-transform:uppercase; letter-spacing:0.8px; font-weight:700;
  border-bottom:2px solid #c8a951;
}
table.rm-table td {
  padding:7px 10px; border-bottom:1px solid #e2ddd0; color:#0b1730;
}
table.rm-table tbody tr:nth-child(even) td { background:#f8f7f3; }
table.rm-table tbody tr:hover td { background:#f5eed6; }
table.rm-table tbody tr:last-child td { font-weight:700; background:#f5eed6; }
</style>
""", unsafe_allow_html=True)


# ── Session state for navigation ──────────────────────────────────────────────
if "section" not in st.session_state:
    st.session_state["section"] = "Overview"

# ── Competition / Season options ───────────────────────────────────────────────
_comp_opts = get_competition_options()
_all_comps  = [o["value"] for o in _comp_opts]

# ── Top Navigation Bar ─────────────────────────────────────────────────────────
_NAV_ITEMS = [
    ("🏠", "Overview"),
    ("📊", "Match Analysis"),
    ("👤", "Player Analysis"),
    ("⚔️", "Tactical Phases"),
    ("🔭", "Opponent Scout"),
    ("📈", "Benchmarking"),
    ("📋", "Report"),
]
# Display labels (shorter) mapped to section keys
_NAV_DISPLAY = {
    "Overview":       "🏠 Overview",
    "Match Analysis": "📊 Match",
    "Player Analysis":"👤 Players",
    "Tactical Phases":"⚔️ Tactical",
    "Opponent Scout": "🔭 Opp Scout",
    "Benchmarking":   "📈 Benchmark",
    "Report":         "📋 Report",
}
_cur = st.session_state.get("section", "Overview")

# Open the dark strip wrapper — all columns sit inside it
st.markdown('<div class="rm-topnav-strip">', unsafe_allow_html=True)

(nc_brand, nc_ov, nc_ma, nc_pa, nc_tp, nc_os, nc_bm, nc_rep,
 nc_comp, nc_seas, nc_auth) = st.columns(
    [1.6, 1.05, 1.05, 1.0, 1.1, 1.05, 1.1, 0.85, 1.35, 1.5, 1.6]
)

with nc_brand:
    _crest_img = (
        f'<img src="data:image/jpeg;base64,{_RM_CREST_B64}" alt="RM" '
        f'style="width:36px;height:36px;border-radius:50%;object-fit:cover;'
        f'border:2px solid rgba(200,169,81,0.8);background:#fff;flex-shrink:0" />'
        if _RM_CREST_B64 else
        '<span style="font-size:22px">⚽</span>'
    )
    st.html(
        f'<div style="display:flex;align-items:center;gap:8px;padding:2px 0">'
        f'  {_crest_img}'
        f'  <div style="line-height:1">'
        f'    <div style="font-weight:700;font-size:13px;color:#60a5fa !important;'
        f'         letter-spacing:0.3px;line-height:1.25;'
        f'         font-family:Arial,sans-serif">Real Madrid CF</div>'
        f'    <div style="font-size:9.5px;color:#c8a951 !important;'
        f'         text-transform:uppercase;letter-spacing:1px;line-height:1.4;'
        f'         font-family:Arial,sans-serif">Tactical &amp; Player Analytics</div>'
        f'  </div>'
        f'</div>'
    )

for _nc, (_icon, _sec) in zip(
    [nc_ov, nc_ma, nc_pa, nc_tp, nc_os, nc_bm, nc_rep], _NAV_ITEMS
):
    with _nc:
        if st.button(
            _NAV_DISPLAY[_sec],
            key=f"nav_{_sec.replace(' ', '_')}",
            type="primary" if _cur == _sec else "secondary",
            use_container_width=True,
        ):
            st.session_state["section"] = _sec
            st.rerun()

with nc_comp:
    competition = st.selectbox("Competition", _all_comps, key="nav_comp")

with nc_seas:
    _avail_seasons = get_available_seasons(competition)
    season = st.selectbox("Season", _avail_seasons, key="nav_seas")

with nc_auth:
    st.html(
        '<div style="text-align:right;padding:2px 0">'
        '  <div style="font-weight:700;font-size:12px;color:#60a5fa !important;'
        '       line-height:1.4;font-family:Arial,sans-serif">Sudhir Dahiya</div>'
        '  <div style="font-size:9.5px;color:#c8a951 !important;'
        '       line-height:1.4;font-family:Arial,sans-serif">'
        '    Master&#39;s in Sports Analytics (2025&#8211;2026)</div>'
        '</div>'
    )

# Close the dark strip wrapper
st.markdown('</div>', unsafe_allow_html=True)

section = st.session_state.get("section", "Overview")

# ── Breadcrumb sub-bar ────────────────────────────────────────────────────────
st.markdown(
    f'<div style="display:flex;justify-content:space-between;align-items:center;'
    f'padding:6px 4px 10px;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:6px">'
    f'<span style="font-size:11px;color:#64748b;font-weight:600;letter-spacing:.6px">'
    f'🏡 {section}</span>'
    f'<span style="font-size:11px;color:#64748b">'
    f'<span style="color:#60a5fa;font-weight:700">{season}</span>'
    f' &nbsp;·&nbsp; '
    f'<span style="color:#34d399;font-weight:700">{competition}</span>'
    f'</span></div>',
    unsafe_allow_html=True,
)


# ── Cached wrappers ───────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _match_opts(comp, seas):
    return get_match_options(comp, seas, "All")

@st.cache_data(show_spinner=False)
def _season_kpis(comp, seas):
    return calc_season_kpis(comp, seas)

@st.cache_data(show_spinner=False)
def _results_df(comp, seas):
    return get_season_results_table(comp, seas)

@st.cache_data(show_spinner=False)
def _matches_list(comp, seas):
    return get_season_match_list(comp, seas)

@st.cache_data(show_spinner=False)
def _squad_df(comp, seas):
    return pa._build_season_player_stats(comp, seas)

@st.cache_data(show_spinner=False)
def _squad_full_df(comp, seas):
    """Squad stats enriched with role_template + lineup_status from the season catalog."""
    squad = pa._build_season_player_stats(comp, seas)
    if squad.empty:
        return squad
    catalog = pa._season_player_catalog(comp, seas)
    if not catalog.empty:
        squad = squad.merge(
            catalog[["player_name", "role_template", "lineup_status"]],
            on="player_name", how="left"
        )
        squad["role_template"] = squad["role_template"].fillna("DM")
        squad["lineup_status"] = squad["lineup_status"].fillna("Starting 11")
    else:
        squad["role_template"] = "DM"
        squad["lineup_status"] = "Starting 11"
    return squad

@st.cache_data(show_spinner=False)
def _player_match_series(comp, seas, player_name, file_tuple):
    return pa._get_player_match_series(
        comp, seas, player_name,
        selected_files=set(file_tuple) if file_tuple else None
    )

@st.cache_data(show_spinner=False)
def _league_df(comp, seas):
    return bm._league_team_table(comp, seas)

@st.cache_data(show_spinner=False)
def _rival_opts(comp, seas):
    return bm._rivals_options(comp, seas)

@st.cache_data(show_spinner=False)
def _match_file_opts(comp, seas):
    return bm._match_file_options(comp, seas)

@st.cache_data(show_spinner=False)
def _bm_gather(comp_tuple):
    return bm._gather_season_data(list(comp_tuple))

@st.cache_data(show_spinner=False)
def _goals_trend_fig(comp, seas):
    return hp._goals_trend(comp, seas)

@st.cache_data(show_spinner=False)
def _shots_trend_fig(comp, seas):
    return hp._shots_trend(comp, seas)

@st.cache_data(show_spinner=False)
def _goals_chart_fig(comp_tuple):
    return bm._goals_chart(list(comp_tuple))

@st.cache_data(show_spinner=False)
def _win_chart_fig(comp_tuple):
    return bm._win_chart(list(comp_tuple))

@st.cache_data(show_spinner=False)
def _xg_chart_fig(comp_tuple):
    return bm._xg_chart(list(comp_tuple))

@st.cache_data(show_spinner=False)
def _pass_chart_fig(comp_tuple):
    return bm._pass_chart(list(comp_tuple))


# ── UI helpers ────────────────────────────────────────────────────────────────
def _chart(fig, key=None):
    st.plotly_chart(fig, width="stretch",
                    config={"displayModeBar": False}, key=key)


def _chart_card(title, fig, key=None):
    st.markdown(f'<div class="chart-card-header">{title}</div>', unsafe_allow_html=True)
    _chart(fig, key=key)


def _page_header(title, subtitle):
    _logo_tag = (
        f'<img class="rm-page-header-logo" '
        f'src="data:image/png;base64,{_UE_LOGO_B64}" alt="UE Real Madrid" />'
        if _UE_LOGO_B64 else ""
    )
    st.markdown(f"""
    <div class="rm-page-header">
      {_logo_tag}
      <h4 class="rm-page-title">{title}</h4>
      <p class="rm-page-subtitle">{subtitle}</p>
    </div>""", unsafe_allow_html=True)


def _section_hdr(title):
    st.markdown(f'<p class="section-header">{title}</p>', unsafe_allow_html=True)


def _kpi_row(items):
    cols = st.columns(len(items))
    for col, (label, value, color, sub) in zip(cols, items):
        sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
        col.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-title">{label}</div>
          <div class="kpi-value" style="color:{color}">{value}</div>
          {sub_html}
        </div>""", unsafe_allow_html=True)


def _no_data(msg="No data available."):
    st.markdown(f'<div class="rm-alert-info">{msg}</div>', unsafe_allow_html=True)


def _df_html_table(df: pd.DataFrame, max_rows: int = 40) -> str:
    df = df.head(max_rows)
    header = "".join(f"<th>{c}</th>" for c in df.columns)
    rows = ""
    for _, r in df.iterrows():
        rows += "<tr>" + "".join(f"<td>{r[c]}</td>" for c in df.columns) + "</tr>"
    return f'<div class="rm-table-wrap"><table class="rm-table"><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>'


# ═══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
if section == "Overview":
    _page_header("Season Overview",
                 "Aggregated season KPIs and results — powered by real Opta match data")

    k = _season_kpis(competition, season)
    if not k or k.get("played", 0) == 0:
        _no_data(f"No matches found for {competition} {season}.")
    else:
        # Record badge
        w, d, l = k["wins"], k["draws"], k["losses"]
        gd_class = "rm-badge-green" if k["goal_diff"] >= 0 else "rm-badge-red"
        gd_sign  = "+" if k["goal_diff"] >= 0 else ""
        st.markdown(f"""
        <div class="rm-record-card">
          <div>
            <p class="rm-record-title">Real Madrid — {competition} {season}</p>
            <p class="rm-record-sub">Matchday record: {w}W {d}D {l}L</p>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <span class="rm-badge rm-badge-blue">{k['win_pct']}% Win Rate</span>
            <span class="rm-badge {gd_class}">{gd_sign}{k['goal_diff']} GD</span>
          </div>
        </div>""", unsafe_allow_html=True)

        # KPI cards
        _section_hdr("Season Statistics")
        _kpi_row([
            ("Matches Played", k["played"],           _C["text_secondary"], None),
            ("Goals Scored",   k["goals_scored"],     _C["accent_green"],   f"{k['goals_per_game']} per game"),
            ("Goals Conceded", k["goals_conceded"],   _C["accent_red"],     f"{k['conceded_per_game']} per game"),
            ("xG For",         k["xg_for"],           _C["accent_blue"],    f"xG diff: {k['xg_diff']:+.2f}"),
            ("xG Against",     k["xg_against"],       _C["accent_orange"],  None),
            ("Avg Pass Acc.",  f"{k['avg_pass_acc']}%", _C["accent_purple"], f"{k['shots_total']} shots total"),
        ])
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Trend charts
        _section_hdr("Performance Trends")
        try:
            _chart_card("Goals Per Match", _goals_trend_fig(competition, season), key="ov_goals")
            _chart_card("Shots &amp; Pass Accuracy Trend", _shots_trend_fig(competition, season), key="ov_shots")
        except Exception as e:
            st.warning(f"Trend charts unavailable: {e}")

        # Results table
        _section_hdr("All Matches")
        df = _results_df(competition, season)
        if df is not None and not df.empty:
            # Drop internal _color column and render Result as badge pills
            _disp = df.drop(columns=[c for c in ["_color"] if c in df.columns])
            _BADGE = {
                "W": ("background:#059669;color:#fff", "W"),
                "D": ("background:#d97706;color:#fff", "D"),
                "L": ("background:#dc2626;color:#fff", "L"),
            }
            _badge_style = (
                "display:inline-flex;align-items:center;justify-content:center;"
                "width:26px;height:26px;border-radius:50%;"
                "font-size:11px;font-weight:700;letter-spacing:0;"
            )
            # Build HTML table with badge in Result column
            _cols = list(_disp.columns)
            _header = "".join(
                f"<th style='padding:9px 12px;text-align:left;font-size:11px;"
                f"text-transform:uppercase;letter-spacing:.8px;font-weight:700;"
                f"color:#c8a951;border-bottom:2px solid #c8a951;"
                f"background:#0b1730'>{c}</th>"
                for c in _cols
            )
            _rows_html = ""
            for _ri, (_, _row) in enumerate(_disp.iterrows()):
                _bg = "#f8f7f3" if _ri % 2 == 0 else "#ffffff"
                _cells = ""
                for _col in _cols:
                    _val = str(_row[_col])
                    if _col == "Result" and _val in _BADGE:
                        _bst, _btxt = _BADGE[_val]
                        _cell_html = (
                            f"<span style='{_badge_style}{_bst}'>{_btxt}</span>"
                        )
                    else:
                        _cell_html = _val
                    _cells += (
                        f"<td style='padding:8px 12px;border-bottom:1px solid #e2ddd0;"
                        f"font-size:13px;color:#0b1730;background:{_bg}'>"
                        f"{_cell_html}</td>"
                    )
                _rows_html += f"<tr>{_cells}</tr>"
            st.markdown(
                f"<div style='overflow-x:auto;border-radius:10px;"
                f"border:1px solid #e2ddd0;box-shadow:0 2px 8px rgba(11,23,48,0.08);margin-bottom:16px'>"
                f"<table style='width:100%;border-collapse:collapse;font-family:inherit'>"
                f"<thead><tr>{_header}</tr></thead>"
                f"<tbody>{_rows_html}</tbody>"
                f"</table></div>",
                unsafe_allow_html=True,
            )
        else:
            _no_data(f"No match results found for {competition} {season}.")


# ═══════════════════════════════════════════════════════════════════════════════
# MATCH ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "Match Analysis":
    _page_header("Match Analysis",
                 "Event-level tactical breakdown — real Opta data")

    opts = _match_opts(competition, season)
    if not opts:
        _no_data(f"No matches available for {competition} {season}.")
    else:
        # Primary filters
        col_mode, col_comp_lbl = st.columns([2, 6])
        with col_mode:
            mode = st.selectbox("Analysis Mode",
                                ["Single Match", "Match Range", "Specific Matches"],
                                label_visibility="visible")
        mode_key = "Single" if mode == "Single Match" else "Range"

        col_ven, col_phase = st.columns([2, 4])
        with col_ven:
            venue_filter = st.selectbox("Venue", ["All", "Home 🏠", "Away ✈️"],
                                        label_visibility="visible")
            venue_val = venue_filter.split()[0]
        with col_phase:
            phase = st.selectbox("Phase Focus",
                                 ["All", "Offensive", "Defensive", "Transitions", "SetPieces"],
                                 format_func=lambda x: {"All":"All Phases","SetPieces":"Set Pieces"}.get(x,x),
                                 label_visibility="visible")

        venue_opts = get_match_options(competition, season, venue_val)
        if not venue_opts:
            _no_data("No matches for this venue filter.")
        else:
            spec_fps  = []    # populated for Specific Matches mode only
            spec_mode = None

            if mode == "Single Match":
                match_labels = [o["label"] for o in venue_opts]
                sel_label    = st.selectbox("Select Match", match_labels)
                fp = next(o["value"] for o in venue_opts if o["label"] == sel_label)
                from_match = to_match = None
            elif mode == "Match Range":
                c1, c2 = st.columns(2)
                with c1:
                    from_label = st.selectbox("From Match", [o["label"] for o in venue_opts],
                                              index=0, key="ma_from")
                with c2:
                    to_label = st.selectbox("To Match", [o["label"] for o in venue_opts],
                                            index=len(venue_opts)-1, key="ma_to")
                fp         = next(o["value"] for o in venue_opts if o["label"] == from_label)
                from_match = fp
                to_match   = next(o["value"] for o in venue_opts if o["label"] == to_label)
            else:  # Specific Matches
                _c_sm1, _c_sm2 = st.columns([2, 4])
                with _c_sm1:
                    spec_mode = st.radio("View Mode", ["Aggregate", "Compare"],
                                         horizontal=True, key="ma_spec_mode")
                with _c_sm2:
                    _spec_labels = st.multiselect(
                        "Select Matches (max 5)",
                        [o["label"] for o in venue_opts],
                        max_selections=5,
                        key="ma_spec_matches",
                        help="Pick up to 5 specific matches to analyze",
                    )
                if not _spec_labels:
                    st.info("Select one or more matches above to begin analysis.")
                    fp = None
                    from_match = to_match = None
                else:
                    spec_fps   = [next(o["value"] for o in venue_opts if o["label"] == _sl)
                                  for _sl in _spec_labels]
                    fp         = spec_fps[0]
                    from_match = spec_fps[0]
                    to_match   = spec_fps[-1]
                    mode_key   = "Range" if len(spec_fps) > 1 else "Single"

            # ── Specific Matches: Aggregate / Compare table ─────────────────
            if spec_fps:
                _sm_hdr = (
                    f"Aggregate Summary — {len(spec_fps)} Selected Matches"
                    if spec_mode == "Aggregate" else
                    f"Match-by-Match Comparison — {len(spec_fps)} Matches"
                )
                _section_hdr(_sm_hdr)
                _sm_rows = []
                for _sfp in spec_fps:
                    try:
                        _, _sm, _se = ma._load(_sfp)
                        if _sm and _se is not None and not _se.empty:
                            _sk = calc_match_kpis(_se, _sm)
                            _sp = calc_ppda(_se, _sm)
                            _sm_rows.append({
                                "Match":      (f"{_sm.get('home_team','')} vs "
                                               f"{_sm.get('away_team','')}"),
                                "Score":      _sm.get("score_str", ""),
                                "Result":     ("W" if _sm["rm_score"] > _sm["opp_score"] else
                                               "D" if _sm["rm_score"] == _sm["opp_score"]
                                               else "L"),
                                "Goals":      int(_sm["rm_score"]),
                                "GA":         int(_sm["opp_score"]),
                                "Poss %":     _sk.get("possession", 0),
                                "Pass Acc %": _sk.get("pass_accuracy", 0),
                                "Shots":      int(_sk.get("shots_total", 0)),
                                "xG For":     round(float(_sk.get("xg_for", 0)), 2),
                                "xG Ag":      round(float(_sk.get("xg_against", 0)), 2),
                                "PPDA":       _sp,
                            })
                    except Exception:
                        pass

                if _sm_rows:
                    _smdf = pd.DataFrame(_sm_rows)
                    if spec_mode == "Aggregate":
                        _sum_cols  = ["Goals", "GA", "Shots"]
                        _mean_cols = ["Poss %", "Pass Acc %", "xG For", "xG Ag", "PPDA"]
                        _agg_r = {"Match": f"AGGREGATE ({len(_sm_rows)} matches)",
                                  "Score": "", "Result": ""}
                        for _sc in _sum_cols:
                            _agg_r[_sc] = int(_smdf[_sc].sum())
                        for _mc in _mean_cols:
                            _agg_r[_mc] = round(float(_smdf[_mc].mean()), 2)
                        _smdf = pd.concat([_smdf, pd.DataFrame([_agg_r])], ignore_index=True)

                    def _result_style(v):
                        if v == "W": return "color: #22c55e; font-weight: bold"
                        if v == "D": return "color: #f59e0b; font-weight: bold"
                        if v == "L": return "color: #ef4444; font-weight: bold"
                        return ""

                    _sm_styled = _smdf.style.map(_result_style, subset=["Result"])
                    st.dataframe(_sm_styled, width="stretch", hide_index=True)
                    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # Match header & KPI
            try:
                header_children, kpi_children = ma._update_header(
                    mode_key, fp, competition, season, venue_val, from_match, to_match)
                # Extract KPI values for display
                if mode_key == "Single":
                    _, meta, events = ma._load(fp)
                    if meta:
                        kpis = calc_match_kpis(events, meta)
                        ppda = calc_ppda(events, meta)
                        rc = (_C["accent_green"] if meta["rm_score"] > meta["opp_score"] else
                              _C["accent_yellow"] if meta["rm_score"] == meta["opp_score"] else
                              _C["accent_red"])
                        rt = ("WIN" if meta["rm_score"] > meta["opp_score"] else
                              "DRAW" if meta["rm_score"] == meta["opp_score"] else "LOSS")
                        st.markdown(f"""
                        <div class="rm-match-header">
                          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px">
                            <div style="text-align:right;flex:1"><div class="rm-match-team">{meta['home_team']}</div><small style="color:#64748b">{meta['competition']}</small></div>
                            <div style="text-align:center;flex:0 0 auto">
                              <div class="rm-match-score" style="color:{rc}">{meta['score_str']}</div>
                              <span class="rm-badge {'rm-badge-green' if rt=='WIN' else 'rm-badge-amber' if rt=='DRAW' else 'rm-badge-red'}">{rt}</span>
                              <div style="color:#64748b;font-size:12px;margin-top:4px">MD {meta.get('week','')} · {meta['date']}</div>
                            </div>
                            <div style="text-align:left;flex:1"><div class="rm-match-team">{meta['away_team']}</div></div>
                          </div>
                        </div>""", unsafe_allow_html=True)
                        _kpi_row([
                            ("Goals For",       meta["rm_score"],              _C["accent_green"],  None),
                            ("Goals Against",   meta["opp_score"],             _C["accent_red"],    None),
                            ("Possession %",    f"{kpis['possession']}%",      _C["accent_blue"],   f"{kpis['passes_total']} passes"),
                            ("Pass Accuracy",   f"{kpis['pass_accuracy']}%",   _C["accent_blue"],   f"{kpis['shots_total']} shots"),
                            ("PPDA",            ppda,                          _C["accent_purple"], "Lower = more press"),
                            ("xG For / vs",     f"{kpis['xg_for']} / {kpis['xg_against']}", _C["accent_orange"], None),
                        ])
                        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            except Exception:
                pass

            # Shot map
            try:
                _chart_card("Shot Map",
                    ma._shot_map(mode_key, fp, competition, season, venue_val,
                                 from_match, to_match, phase), key="ma_shot")
            except Exception as e:
                st.warning(f"Shot map unavailable: {e}")

            # xG chart
            try:
                _chart_card("xG Accumulation by Minute",
                    ma._xg_chart(mode_key, fp, competition, season, venue_val,
                                 from_match, to_match), key="ma_xg")
            except Exception as e:
                st.warning(f"xG chart unavailable: {e}")

            # Tactical bars
            try:
                _chart_card("Tactical Comparison",
                    ma._tactical_bars(mode_key, fp, competition, season, venue_val,
                                      from_match, to_match), key="ma_tac")
            except Exception as e:
                st.warning(f"Tactical bars unavailable: {e}")

            # Pass map
            try:
                _chart_card("Pass Map (RM successful passes)",
                    ma._pass_map(mode_key, fp, competition, season, venue_val,
                                 from_match, to_match, phase), key="ma_pass")
            except Exception as e:
                st.warning(f"Pass map unavailable: {e}")

            # Pass network
            net_scope = st.radio("Pass Network Scope", ["Starting XI", "Full Match"],
                                 horizontal=True, key="ma_net_scope")
            net_key = "xi" if net_scope == "Starting XI" else "full"
            try:
                _chart_card(f"Pass Network (RM) — {net_scope}",
                    ma._pass_network(mode_key, fp, competition, season, venue_val,
                                     from_match, to_match, net_key, phase), key="ma_pnet")
            except Exception as e:
                st.warning(f"Pass network unavailable: {e}")

            # Phase sub-scores
            _section_hdr("Match Tactical Sub-Phases (A/B/C/D)")
            st.markdown("""
            <div class="rm-phase-alert">
              <b>Phase Index (0–100):</b> A composite score measuring RM's effectiveness in each of the 4 tactical moments.<br>
              <b>A – Offensive Moment:</b> Quality of possession &amp; attacking output.<br>
              <b>B – Defensive Transition:</b> Press intensity &amp; ball regains after losing possession.<br>
              <b>C – Defensive Moment:</b> Defensive solidity when opponent has the ball.<br>
              <b>D – Offensive Transition:</b> Danger created immediately after winning the ball.
            </div>""", unsafe_allow_html=True)
            try:
                _chart_card("Match Tactical Sub-Phases",
                    ma._subphase_chart(mode_key, fp, competition, season, venue_val,
                                       from_match, to_match), key="ma_sub")
            except Exception:
                pass

            # Transition metrics
            try:
                _chart_card("Transition Metrics",
                    ma._transition_chart(mode_key, fp, competition, season, venue_val,
                                         from_match, to_match), key="ma_trans")
            except Exception:
                pass

            # Player table
            _section_hdr("Real Madrid Player Performance")
            lineup_filter = st.radio("Lineup Filter",
                                     ["Starting 11", "Sub On", "All Players"],
                                     horizontal=True, key="ma_lup")
            if mode_key == "Single":
                try:
                    _, meta, events = ma._load(fp)
                    if meta and events is not None and not events.empty:
                        pstats = get_player_stats(events, meta["rm_id"])
                        if not pstats.empty:
                            lineup_map = get_match_lineup_status(events, meta["rm_id"])
                            pstats["lineup"] = pstats["player_name"].map(
                                lambda n: lineup_map.get(n, "Starting 11"))
                            if lineup_filter != "All Players":
                                pstats = pstats[pstats["lineup"] == lineup_filter]
                            show_cols = [c for c in
                                         ["player_name","lineup","passes","shots","goals",
                                          "key_passes","assists","tackles","interceptions",
                                          "recoveries","xg"]
                                         if c in pstats.columns]
                            st.dataframe(pstats[show_cols].head(25),
                                         width="stretch", hide_index=True)
                        else:
                            _no_data("No player stats for this match.")
                except Exception as e:
                    st.warning(f"Player table unavailable: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "Player Analysis":
    _page_header("Player Analysis",
                 "Individual player metrics computed from Opta event data")

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2 = st.columns([3, 3])
    with col1:
        role_template = st.selectbox("Role Template",
                                     ["All", "CB", "DM", "FB", "AMW", "ST", "GK"])
    with col2:
        lineup_status = st.selectbox("Line-up Status",
                                     ["All", "Starting 11", "Sub On", "On Bench", "Not in Squad"])
    min_minutes_pct = st.slider(
        "Minutes Played % (min)", min_value=0, max_value=100, value=0, step=5,
        key="pa_min_pct",
        help="Only show players who appeared in at least this % of matches",
    )

    match_file_ops = _match_file_opts(competition, season)
    _pa_mode = st.selectbox("Match Selection Mode",
                             ["Match Range", "Specific Matches"],
                             key="pa_match_mode")
    if match_file_ops:
        if _pa_mode == "Match Range":
            c3, c4 = st.columns(2)
            with c3:
                from_label_pa = st.selectbox("From Match",
                                             [o["label"] for o in match_file_ops],
                                             index=0, key="pa_from")
            with c4:
                to_label_pa = st.selectbox("To Match",
                                           [o["label"] for o in match_file_ops],
                                           index=len(match_file_ops) - 1, key="pa_to")
            from_match_pa     = next(o["value"] for o in match_file_ops
                                     if o["label"] == from_label_pa)
            to_match_pa       = next(o["value"] for o in match_file_ops
                                     if o["label"] == to_label_pa)
            selected_files_pa = pa._selected_file_set(competition, season,
                                                       from_match_pa, to_match_pa)
        else:  # Specific Matches
            _pa_spec_labels = st.multiselect(
                "Select Matches (max 5)",
                [o["label"] for o in match_file_ops],
                max_selections=5,
                key="pa_spec_matches",
                help="Pick up to 5 specific matches to filter player stats",
            )
            if _pa_spec_labels:
                selected_files_pa = {
                    next(o["value"] for o in match_file_ops if o["label"] == _l)
                    for _l in _pa_spec_labels
                }
            else:
                st.info("Select one or more matches to filter player stats by specific games.")
                selected_files_pa = set()
            from_match_pa = to_match_pa = None
    else:
        from_match_pa = to_match_pa = None
        selected_files_pa = set()

    # ── Squad table — uses catalog merge so role/lineup filters actually work ─
    _section_hdr("Squad Performance Summary")
    with st.spinner("Loading squad data…"):
        squad_full = _squad_full_df(competition, season)

    if squad_full.empty:
        _no_data(f"No player data for {competition} {season}.")
    else:
        # Compute Min % = matches_played / total season matches * 100
        # Use len(match_file_ops) so denominator = actual season match count (e.g. 36),
        # NOT the best player's appearance count — keeps values consistent with Dash dashboard.
        _tot_m = max(len(match_file_ops) if match_file_ops else 1,
                     int(squad_full["matches_played"].max()) if "matches_played" in squad_full.columns else 1,
                     1)
        squad_full = squad_full.copy()
        squad_full["min_pct"] = (
            pd.to_numeric(squad_full["matches_played"], errors="coerce")
            .fillna(0) / _tot_m * 100
        ).round(1)

        filtered = squad_full.copy()
        if role_template != "All" and "role_template" in filtered.columns:
            filtered = filtered[filtered["role_template"] == role_template]
        if lineup_status != "All" and "lineup_status" in filtered.columns:
            filtered = filtered[filtered["lineup_status"] == lineup_status]
        if min_minutes_pct > 0 and "min_pct" in filtered.columns:
            filtered = filtered[filtered["min_pct"] >= min_minutes_pct]

        _want_cols = ["player_name", "role_template", "lineup_status", "min_pct",
                      "matches_played", "passes", "shots", "goals", "key_passes",
                      "assists", "tackles", "interceptions", "recoveries", "xg"]
        show_cols = [c for c in _want_cols if c in filtered.columns]
        _hdr_labels = {
            "player_name": "PLAYER", "role_template": "ROLE",
            "lineup_status": "LINE-UP", "min_pct": "MIN %",
            "matches_played": "MP", "passes": "PASSES", "shots": "SHOTS",
            "goals": "GOALS", "key_passes": "KEY PASSES", "assists": "ASSISTS",
            "tackles": "TACKLES", "interceptions": "INTER.", "recoveries": "RECOV.",
            "xg": "XG",
        }
        _LBADGE = {
            "Starting 11": ("#2563eb", "#fff"),
            "Sub On":       ("#059669", "#fff"),
            "On Bench":     ("#d97706", "#fff"),
            "Not in Squad": ("#dc2626", "#fff"),
        }
        _lbadge_s = (
            "display:inline-block;padding:2px 10px;border-radius:12px;"
            "font-size:11px;font-weight:600;"
        )
        display_sq = filtered[show_cols].copy()
        if "passes" in display_sq.columns:
            display_sq = display_sq[
                pd.to_numeric(display_sq["passes"], errors="coerce").fillna(0) > 0
            ]
        display_sq = display_sq.head(30)

        _sq_hdr = "".join(
            f'<th style="padding:8px 12px;text-align:left;white-space:nowrap;'
            f'color:#c8a951;font-size:11px;font-weight:700;letter-spacing:.06em;'
            f'border-bottom:1px solid #1e3a5f">{_hdr_labels.get(c, c)}</th>'
            for c in show_cols
        )
        _sq_rows = ""
        for _ri, (_, _rw) in enumerate(display_sq.iterrows()):
            _rbg = "#f8f7f3" if _ri % 2 == 0 else "#ffffff"
            _cells = ""
            for _c in show_cols:
                _v = _rw[_c]
                if _c == "lineup_status":
                    _lv = str(_v) if pd.notna(_v) else ""
                    _bb, _bf = _LBADGE.get(_lv, ("#64748b", "#fff"))
                    _cv = (f'<span style="{_lbadge_s}background:{_bb};color:{_bf}">'
                           f'{_lv}</span>')
                elif _c == "min_pct":
                    _cv = f"{float(_v):.1f}%" if pd.notna(_v) else "—"
                elif _c == "xg":
                    _cv = f"{float(_v):.2f}" if pd.notna(_v) else "—"
                elif isinstance(_v, float) and pd.notna(_v):
                    _cv = str(int(_v))
                else:
                    _cv = str(_v) if pd.notna(_v) else "—"
                _cells += (
                    f'<td style="padding:7px 12px;white-space:nowrap;'
                    f'font-size:13px;color:#0b1730;border-bottom:1px solid #e8e4da">'
                    f'{_cv}</td>'
                )
            _sq_rows += f'<tr style="background:{_rbg}">{_cells}</tr>'

        st.markdown(
            f'<div style="overflow-x:auto;border-radius:10px;'
            f'border:1px solid #e0d9cc;margin-bottom:16px">'
            f'<table style="width:100%;border-collapse:collapse;background:#fff">'
            f'<thead><tr style="background:#0b1730">{_sq_hdr}</tr></thead>'
            f'<tbody>{_sq_rows}</tbody>'
            f'</table></div>',
            unsafe_allow_html=True,
        )

    # ── Chance Creator % ──────────────────────────────────────────────────────
    _section_hdr("Chance Creator % — Key Passes / Team Total")
    try:
        _chart_card("Chance Creator %",
                    pa._chance_creator_pa(competition, season, from_match_pa, to_match_pa),
                    key="pa_cc")
    except Exception:
        pass

    # ── Player Deep Dive ──────────────────────────────────────────────────────
    _section_hdr("Player Deep Dive")
    all_players = squad_full["player_name"].dropna().tolist() if not squad_full.empty else []
    if not all_players:
        _no_data("No players available.")
    else:
        players = st.multiselect(
            "Select Players (max 5)",
            all_players,
            max_selections=5,
            key="pa_players",
            help="Select 1–5 players to compare on the radar chart",
        )

        if not players:
            st.info("Select one or more players above to view their profile.")
        else:
            # ── Squad-max normalization denominators (shared across all players) ─
            sq_pg_max = {}
            for _col in ["passes", "shots", "goals", "tackles", "xg"]:
                if _col in squad_full.columns and "matches_played" in squad_full.columns:
                    _sq_pg = squad_full[_col] / squad_full["matches_played"].clip(lower=1)
                    sq_pg_max[_col] = float(_sq_pg.max()) or 1.0
                else:
                    sq_pg_max[_col] = 1.0

            radar_cats = ["Passes/G", "Shots/G", "Goals/G", "Tackles/G", "xG/G"]
            col_keys   = ["passes",   "shots",   "goals",   "tackles",   "xg"]
            _PALETTE = [
                "#d4af37", "#3b82f6", "#22c55e", "#f97316", "#ec4899",
            ]
            _PALETTE_FILL = [
                "rgba(212,175,55,0.14)", "rgba(59,130,246,0.14)",
                "rgba(34,197,94,0.14)",  "rgba(249,115,22,0.14)",
                "rgba(236,72,153,0.14)",
            ]

            fig_radar       = go.Figure()
            comparison_rows = []
            player_match_dfs = {}

            for _i, _pname in enumerate(players):
                with st.spinner(f"Loading {_pname}…"):
                    _p_df = _player_match_series(
                        competition, season, _pname,
                        tuple(sorted(selected_files_pa)) if selected_files_pa else ()
                    )
                player_match_dfs[_pname] = _p_df
                if _p_df.empty:
                    continue
                _n_m  = len(_p_df)
                _agg  = _p_df[col_keys].sum()
                _pg   = (_agg / max(_n_m, 1)).round(3)
                _vals = [
                    min(float(_pg.get(_c, 0)) / sq_pg_max[_c] * 100, 100)
                    for _c in col_keys
                ]
                fig_radar.add_trace(go.Scatterpolar(
                    r=_vals + [_vals[0]],
                    theta=radar_cats + [radar_cats[0]],
                    fill="toself",
                    line=dict(color=_PALETTE[_i], width=2),
                    fillcolor=_PALETTE_FILL[_i],
                    name=_pname,
                    hovertemplate=f"<b>{_pname}</b><br>%{{theta}}: %{{r:.1f}}% of squad max<extra></extra>",
                ))
                comparison_rows.append({
                    "Player":    _pname,
                    "Passes/G":  round(float(_pg.get("passes",  0)), 2),
                    "Shots/G":   round(float(_pg.get("shots",   0)), 2),
                    "Goals/G":   round(float(_pg.get("goals",   0)), 2),
                    "Tackles/G": round(float(_pg.get("tackles", 0)), 2),
                    "xG/G":      round(float(_pg.get("xg",      0)), 3),
                    "Matches":   _n_m,
                })

            # ── Radar chart ───────────────────────────────────────────────────
            _section_hdr("Player Radar Comparison")
            if fig_radar.data:
                _radar_title = (
                    " vs ".join(players) + " — Per-Game Profile (% of squad max)"
                    if len(players) > 1 else
                    f"{players[0]} — Per-Game Profile (% of squad max)"
                )
                fig_radar.update_layout(
                    paper_bgcolor=_C["surface"],
                    font=dict(color=_C["text_primary"], size=11),
                    polar=dict(
                        bgcolor=_C["surface"],
                        radialaxis=dict(
                            visible=True, range=[0, 100],
                            ticksuffix="%", gridcolor=_C["border"],
                            tickfont=dict(size=9),
                        ),
                        angularaxis=dict(gridcolor=_C["border"]),
                    ),
                    title=dict(text=_radar_title, font=dict(size=12)),
                    height=420,
                    margin=dict(l=60, r=60, t=70, b=50),
                    showlegend=len(players) > 1,
                    legend=dict(
                        orientation="h", yanchor="top", y=-0.05,
                        xanchor="center", x=0.5,
                        bgcolor="rgba(0,0,0,0)", font=dict(size=11),
                    ),
                )
                _chart_card("Radar Comparison", fig_radar, key="pa_radar")
            else:
                _no_data("No match data found for selected player(s).")

            # ── Comparison summary table ──────────────────────────────────────
            if len(players) > 1 and comparison_rows:
                _section_hdr("Comparison Summary Table")
                _cmp_df      = pd.DataFrame(comparison_rows)
                _metric_cols = ["Passes/G", "Shots/G", "Goals/G", "Tackles/G", "xG/G"]

                def _highlight_best(s):
                    _mx = s.max()
                    return [
                        "background-color: rgba(212,175,55,0.30); font-weight: bold"
                        if v == _mx else ""
                        for v in s
                    ]

                _styled = _cmp_df.style.apply(_highlight_best, subset=_metric_cols)
                st.dataframe(_styled, width="stretch", hide_index=True)
                st.caption("Gold highlight = best value in that category")

            # ── Single-player detail (touch heatmap + per-match trend charts) ─
            if len(players) == 1:
                _primary  = players[0]
                _match_df = player_match_dfs.get(_primary, pd.DataFrame())

                try:
                    _chart_card(f"Touch Map — {_primary}",
                                pa._player_touch_heatmap(competition, season, _primary,
                                                         selected_files_pa or None,
                                                         len(selected_files_pa) == 1),
                                key="pa_touch")
                except Exception as _e:
                    st.warning(f"Touch heatmap unavailable: {_e}")

                if _match_df.empty:
                    _no_data(f"No per-match data found for {_primary}.")
                else:
                    _n_matches = len(_match_df)
                    _result_colors = [
                        _C["accent_green"]  if r == "W" else
                        _C["accent_yellow"] if r == "D" else _C["accent_red"]
                        for r in _match_df["result"]
                    ]

                    # Passes per match
                    fig_passes = go.Figure()
                    fig_passes.add_trace(go.Bar(
                        x=_match_df["match"], y=_match_df["passes"],
                        marker_color=_result_colors, name="Passes",
                        text=_match_df["passes"], textposition="auto",
                    ))
                    for _lbl, _clr in [("Win (W)", _C["accent_green"]),
                                       ("Draw (D)", _C["accent_yellow"]),
                                       ("Loss (L)", _C["accent_red"])]:
                        fig_passes.add_trace(go.Scatter(
                            x=[None], y=[None], mode="markers", name=_lbl,
                            marker=dict(size=9, color=_clr), hoverinfo="skip",
                        ))
                    fig_passes.update_layout(
                        paper_bgcolor=_C["surface"], plot_bgcolor=_C["surface"],
                        font=dict(color=_C["text_primary"], size=11),
                        height=380, title=f"{_primary} — Passes Per Match",
                        xaxis=dict(tickangle=-45, ticklabelstep=2,
                                   gridcolor=_C["border"], automargin=True),
                        yaxis=dict(gridcolor=_C["border"], automargin=True),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                    xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
                        margin=dict(l=48, r=28, t=56, b=80),
                    )
                    _chart_card(f"{_primary} — Passes Per Match", fig_passes, key="pa_passes")

                    # Goals & xG per match
                    fig_goals = go.Figure()
                    fig_goals.add_trace(go.Bar(
                        x=_match_df["match"], y=_match_df["goals"],
                        name="Goals", marker_color=_C["accent_green"],
                        text=_match_df["goals"], textposition="auto",
                    ))
                    fig_goals.add_trace(go.Scatter(
                        x=_match_df["match"], y=_match_df["xg"],
                        name="xG", yaxis="y2",
                        line=dict(color=_C["accent_orange"], width=2),
                        mode="lines+markers", marker=dict(size=6),
                    ))
                    fig_goals.update_layout(
                        paper_bgcolor=_C["surface"], plot_bgcolor=_C["surface"],
                        font=dict(color=_C["text_primary"], size=11),
                        height=380, title=f"{_primary} — Goals & xG Per Match",
                        xaxis=dict(tickangle=-45, ticklabelstep=2,
                                   gridcolor=_C["border"], automargin=True),
                        yaxis=dict(title="Goals", gridcolor=_C["border"], automargin=True),
                        yaxis2=dict(title="xG", overlaying="y", side="right",
                                    showgrid=False, automargin=True),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                    xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
                        margin=dict(l=48, r=60, t=56, b=80),
                    )
                    _chart_card(f"{_primary} — Goals & xG Per Match", fig_goals, key="pa_goals")


# ═══════════════════════════════════════════════════════════════════════════════
# TACTICAL PHASES
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "Tactical Phases":
    _page_header("Tactical Phases",
                 "Pressing, position maps &amp; zonal activity — derived from event data")

    opts = _match_opts(competition, season)
    if not opts:
        _no_data(f"No matches available for {competition} {season}.")
    else:
        match_labels = [o["label"] for o in opts]
        sel = st.selectbox("Select Match", match_labels, key="tp_match")
        fp  = next(o["value"] for o in opts if o["label"] == sel)

        # ── Press map ─────────────────────────────────────────────────────────
        _section_hdr("Pressing Actions Map (PPDA)")
        try:
            _chart_card("Pressing Map", tp._press_map(fp), key="tp_press")
        except Exception as e:
            st.warning(f"Press map unavailable: {e}")

        # ── Press Classification (spatial distribution) ────────────────────
        _section_hdr("Press Classification — Spatial Distribution")
        try:
            _chart_card("Press Classification", tp._press_classification(fp), key="tp_pressclass")
        except Exception as e:
            st.warning(f"Press classification unavailable: {e}")

        # ── Position Map + Zonal Activity ─────────────────────────────────
        _section_hdr("Position Map + Zonal Activity")
        c1, c2 = st.columns(2)
        with c1:
            team_sel  = st.radio("Team", ["Real Madrid", "Opponent"],
                                  horizontal=True, key="tp_team")
        with c2:
            phase_sel = st.radio("Game Phase",
                                  ["All Phases", "In Possession", "Out of Possession"],
                                  horizontal=True, key="tp_phase")

        team_side = "rm" if team_sel == "Real Madrid" else "opp"
        phase_key = {"All Phases": "all", "In Possession": "possession",
                     "Out of Possession": "defense"}[phase_sel]

        try:
            pos_result = tp._position_map(fp, phase_key, team_side)
            pos_fig    = pos_result[0] if isinstance(pos_result, tuple) else pos_result
            _chart_card(f"Position Map — {team_sel} ({phase_sel})", pos_fig, key="tp_pos")
        except Exception as e:
            st.warning(f"Position map unavailable: {e}")

        # ── Position Code Reference (static grid) ─────────────────────────
        _section_hdr("Position Code Reference")
        _pos_codes = getattr(tp, "_POSITION_CODES", [
            ["LF",  "LCF", "CF",  "RCF", "RF"],
            ["LWF", "LAM", "CAM", "RAM", "RWF"],
            ["LM",  "LCM", "CM",  "RCM", "RM"],
            ["LWB", "LDM", "CDM", "RDM", "RWB"],
            ["LB",  "LCB", "CB",  "RCB", "RB"],
        ])
        _code_header = "".join(
            f"<th style='text-align:center;padding:5px 12px;font-size:11px;color:#475569;"
            f"border:1px solid #cbd5e1;background:#f8fafc'>{c}</th>"
            for c in _pos_codes[0]
        )
        _code_rows = "".join(
            "<tr>" + "".join(
                f"<td style='text-align:center;padding:5px 12px;font-size:11px;"
                f"color:#475569;border:1px solid #cbd5e1'>{c}</td>"
                for c in row
            ) + "</tr>"
            for row in _pos_codes
        )
        st.markdown(
            f'<div style="overflow-x:auto;margin-bottom:8px">'
            f'<table style="border-collapse:collapse;margin:0 auto">'
            f'<tbody>{_code_rows}</tbody></table>'
            f'<p style="text-align:center;font-size:11px;color:#94a3b8;margin-top:6px">'
            f'Standard pitch zones (forwards top → defenders bottom) for reading the zonal activity grid above.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Player Positional Summary ─────────────────────────────────────
        _section_hdr("Player Positional Summary")
        st.markdown(
            '<p style="font-size:12px;color:#64748b;margin:-8px 0 8px">'
            'Average pitch position, line &amp; involvement per player · updates with the team and phase selected above</p>',
            unsafe_allow_html=True,
        )
        try:
            pos_df = tp._position_data(fp, phase_key, team_side)
            if pos_df.empty:
                _no_data("No positional data for this phase / team selection.")
            else:
                # Line colour badges
                _LINE_COLORS = {"FWD": "#059669", "MID": "#d97706", "DEF": "#dc2626"}
                pos_display = pos_df.rename(columns={
                    "shirt":       "#",
                    "player_name": "Player",
                    "line":        "Line",
                    "avg_x":       "Avg X",
                    "avg_y":       "Avg Y",
                    "n_ev":        "Events",
                    "passes":      "Passes",
                })
                pos_display["Avg X"] = pos_display["Avg X"].round(1)
                pos_display["Avg Y"] = pos_display["Avg Y"].round(1)
                # Build styled HTML table
                hdr = "".join(
                    f"<th style='padding:8px 10px;color:#64748b;font-size:10px;"
                    f"text-transform:uppercase;letter-spacing:.8px;font-weight:700;"
                    f"border-bottom:2px solid #e2e8f0'>{c}</th>"
                    for c in pos_display.columns
                )
                rows_html = ""
                for i, (_, r) in enumerate(pos_display.iterrows()):
                    bg = "background:#f8fbff;" if i % 2 == 0 else ""
                    cells = ""
                    for c in pos_display.columns:
                        val = r[c]
                        if c == "Line":
                            col = _LINE_COLORS.get(str(val), "#374151")
                            cells += (f"<td style='padding:7px 10px;font-size:13px;"
                                      f"font-weight:600;color:{col}'>{val}</td>")
                        elif c == "#":
                            cells += (f"<td style='padding:7px 10px;font-size:13px;"
                                      f"font-weight:700;color:{_RM}'>{val}</td>")
                        else:
                            cells += f"<td style='padding:7px 10px;font-size:13px'>{val}</td>"
                    rows_html += f"<tr style='{bg}'>{cells}</tr>"
                st.markdown(
                    f'<div class="rm-table-wrap"><table class="rm-table">'
                    f'<thead><tr>{hdr}</tr></thead><tbody>{rows_html}</tbody>'
                    f'</table></div>',
                    unsafe_allow_html=True,
                )
        except Exception as e:
            st.warning(f"Player positional summary unavailable: {e}")

        # ── PPDA Trend ────────────────────────────────────────────────────
        _section_hdr("PPDA Trend (Season)")
        try:
            _chart_card("PPDA Trend", tp._ppda_trend(competition, season), key="tp_ppda")
        except Exception:
            pass

        # ── Ball Recovery Map ─────────────────────────────────────────────
        try:
            _chart_card("Ball Recovery Map", tp._recovery_map(fp), key="tp_recovery")
        except Exception:
            pass

        # ── Territorial Tilt ──────────────────────────────────────────────
        try:
            _chart_card("Territorial Tilt by Phase", tp._tilt_chart(competition, season), key="tp_tilt")
        except Exception:
            pass

        # ── Tactical Phase Deep-Dive ──────────────────────────────────────
        _section_hdr("Tactical Phase Deep-Dive")
        deep_phase = st.selectbox(
            "Select Phase",
            ["A. Offensive Moment", "B. Defensive Transition",
             "C. Defensive Moment", "D. Offensive Transition"],
            key="tp_deepphase",
        )
        phase_key_dd = deep_phase[0]  # "A", "B", "C", "D"

        try:
            _, meta_dd, events_dd = tp._load(fp)
            if meta_dd is not None and events_dd is not None and not events_dd.empty:
                rm_id_dd   = meta_dd["rm_id"]
                opp_id_dd  = meta_dd["opp_id"]
                rm_dd      = events_dd[events_dd["contestant_id"] == rm_id_dd].copy()
                opp_dd     = events_dd[events_dd["contestant_id"] == opp_id_dd].copy()
                rm_pass_dd = rm_dd[rm_dd["is_pass"] & rm_dd["end_x"].notna()]
                opp_shots_dd = opp_dd[opp_dd["is_shot"]]
                trans_df_dd, dt_df_dd = tp._build_transition_windows(events_dd, rm_id_dd, opp_id_dd)
                rm_name_dd = tp._rm_team_name(meta_dd)
                def_act_dd = rm_dd[rm_dd["is_tackle"] | rm_dd["is_interception"] | rm_dd["is_recovery"]]
                compact_dd = float(def_act_dd["y"].std()) if not def_act_dd.empty else 0.0

                # ── A. Offensive Moment ──────────────────────────────────────
                if phase_key_dd == "A":
                    build_up    = tp._safe_div(len(rm_pass_dd[(rm_pass_dd["x"] < 40) & (rm_pass_dd["outcome"] == 1)]), max(len(rm_pass_dd), 1))
                    progressive = tp._safe_div(len(rm_pass_dd[(rm_pass_dd["end_x"] - rm_pass_dd["x"]) >= 15]), max(len(rm_pass_dd), 1))
                    flank_use   = tp._safe_div(len(rm_dd[(rm_dd["y"] <= 20) | (rm_dd["y"] >= 80)]), max(len(rm_dd), 1))
                    direct      = tp._safe_div(len(rm_pass_dd[(rm_pass_dd["end_x"] - rm_pass_dd["x"]) >= 25]), max(len(rm_pass_dd), 1))
                    combinative = 1.0 - direct
                    chance_cr   = int(rm_dd["is_key_pass"].sum())
                    xg_chain    = float(rm_dd["xg"].dropna().sum())
                    xg_obs      = int(rm_dd["xg"].notna().sum())
                    zone14      = int(len(rm_dd[(rm_dd["x"] >= 75) & (rm_dd["x"] <= 88) & (rm_dd["y"] >= 35) & (rm_dd["y"] <= 65)]))
                    crosses     = int(len(rm_pass_dd[(rm_pass_dd["x"] >= 75) & ((rm_pass_dd["y"] <= 20) | (rm_pass_dd["y"] >= 80))]))
                    metrics_dd  = [
                        ("build-up structure",    f"{build_up * 100:.1f}% controlled build-up passes"),
                        ("progression style",     f"{progressive * 100:.1f}% progressive passes"),
                        ("flank usage",           f"{flank_use * 100:.1f}% wide-lane actions"),
                        ("direct vs combinative", f"Direct {direct * 100:.1f}% / Combinative {combinative * 100:.1f}%"),
                        ("chance creation",       str(chance_cr)),
                        ("xG chain",              f"{xg_chain:.2f} (from {xg_obs} shots with xG qualifier)"),
                        ("zone 14 occupation",    str(zone14)),
                        ("crossing tendencies",   str(crosses)),
                    ]
                    heat_fig_dd = tp._phase_base_pitch("A Heatmap — RM progressive pass destinations")
                    a_prog = rm_pass_dd[(rm_pass_dd["outcome"] == 1) & ((rm_pass_dd["end_x"] - rm_pass_dd["x"]) >= 10)]
                    if not a_prog.empty:
                        heat_fig_dd = tp._add_phase_density(heat_fig_dd, a_prog["end_x"], a_prog["end_y"], "YlGnBu", "Progressive destinations")
                        heat_fig_dd.add_trace(go.Scatter(
                            x=a_prog["end_x"], y=a_prog["end_y"], mode="markers",
                            marker=dict(size=4, color="rgba(255,255,255,0.45)", line=dict(color="rgba(0,0,0,0.18)", width=0.5)),
                            name="Pass end", hoverinfo="skip",
                        ))
                    heat_fig_dd = tp._add_direction_arrows(heat_fig_dd, meta_dd["opponent"], rm_name_dd)
                    a_zone = {
                        "Left Lane":          int(len(rm_dd[rm_dd["y"] >= 67])),
                        "Half-space/Central": int(len(rm_dd[(rm_dd["y"] >= 33) & (rm_dd["y"] < 67)])),
                        "Right Lane":         int(len(rm_dd[rm_dd["y"] < 33])),
                    }
                    viz_fig_dd = go.Figure()
                    for zn, col in [("Left Lane", "#2563eb"), ("Half-space/Central", "#059669"), ("Right Lane", "#d97706")]:
                        viz_fig_dd.add_trace(go.Bar(
                            x=[zn], y=[a_zone[zn]], name=zn, marker_color=col,
                            text=[a_zone[zn]], textposition="outside",
                            textfont=dict(color="#0b1730", size=13, family="Arial Black"),
                        ))
                    viz_fig_dd.update_layout(height=360, title="A Visualization — RM lane usage",
                                             plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                             font=dict(color="#0b1730", size=12),
                                             xaxis=dict(gridcolor="#e0d9cc", color="#0b1730"),
                                             yaxis=dict(gridcolor="#e0d9cc", color="#0b1730"))

                # ── B. Defensive Transition ──────────────────────────────────
                elif phase_key_dd == "B":
                    reaction  = float(dt_df_dd["reaction_time_s"].dropna().median()) if not dt_df_dd.empty else 0.0
                    cp_rec    = float(dt_df_dd["counterpress_recovery"].mean() * 100) if not dt_df_dd.empty else 0.0
                    ppda_turn = float(dt_df_dd["ppda_after_turnover"].replace([float("inf"), float("-inf")], float("nan")).dropna().mean()) if not dt_df_dd.empty else 0.0
                    metrics_dd = [
                        ("reaction after losing possession", f"{reaction:.2f}s median defensive reaction"),
                        ("counterpressing recoveries",       f"{cp_rec:.1f}% of loss windows"),
                        ("defensive compactness",            f"{compact_dd:.2f} y-std (lower is tighter)"),
                        ("recovery times",                   f"{reaction:.2f}s"),
                        ("PPDA after turnover",              f"{ppda_turn:.2f}"),
                    ]
                    heat_fig_dd = tp._phase_base_pitch("B Heatmap — RM turnovers (loss points)")
                    loss_pts = rm_dd[(rm_dd["is_pass"] & (rm_dd["outcome"] == 0)) | (rm_dd["is_dribble"] & (rm_dd["outcome"] == 0))]
                    if not loss_pts.empty:
                        heat_fig_dd = tp._add_phase_density(heat_fig_dd, loss_pts["x"], loss_pts["y"], "Reds", "Turnover density")
                        heat_fig_dd.add_trace(go.Scatter(
                            x=loss_pts["x"], y=loss_pts["y"], mode="markers",
                            marker=dict(size=4, color="rgba(255,255,255,0.45)", line=dict(color="rgba(0,0,0,0.18)", width=0.5)),
                            name="Loss", hoverinfo="skip",
                        ))
                    heat_fig_dd = tp._add_direction_arrows(heat_fig_dd, meta_dd["opponent"], rm_name_dd)
                    viz_fig_dd = go.Figure()
                    rt = dt_df_dd["reaction_time_s"].dropna() if (not dt_df_dd.empty and "reaction_time_s" in dt_df_dd.columns) else pd.Series(dtype=float)
                    if not rt.empty:
                        viz_fig_dd.add_trace(go.Histogram(x=rt, nbinsx=12,
                                                           marker=dict(color="#dc2626", line=dict(color="white", width=1)),
                                                           name="Reaction time (s)"))
                        viz_fig_dd.add_vline(x=float(rt.median()), line=dict(color="#e11d48", dash="dot"),
                                             annotation_text=f"Median {rt.median():.2f}s")
                    viz_fig_dd.update_layout(height=360, title="B Visualization — defensive reaction time",
                                             plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                             font=dict(color="#0b1730", size=12),
                                             xaxis=dict(title="Seconds", gridcolor="#e0d9cc", color="#0b1730"),
                                             yaxis=dict(title="Count", gridcolor="#e0d9cc", color="#0b1730"),
                                             showlegend=False)

                # ── C. Defensive Moment ──────────────────────────────────────
                elif phase_key_dd == "C":
                    ppda_val_dd = tp.calc_ppda(events_dd, meta_dd)
                    high  = int(len(def_act_dd[def_act_dd["x"] >= 67]))
                    mid   = int(len(def_act_dd[(def_act_dd["x"] >= 33) & (def_act_dd["x"] < 67)]))
                    low   = int(len(def_act_dd[def_act_dd["x"] < 33]))
                    def_line = float(def_act_dd["x"].mean()) if not def_act_dd.empty else 0.0
                    recovs   = int(rm_dd["is_recovery"].sum())
                    aerial   = int((rm_dd["type_id"] == 37).sum())
                    conceded = int(len(opp_shots_dd))
                    if opp_shots_dd.empty:
                        vuln = "No shot concessions"
                    else:
                        opp_zone_s = pd.cut(opp_shots_dd["x"], bins=[-1, 33, 67, 101], labels=["Defensive", "Middle", "Attacking"])
                        vuln = str(opp_zone_s.value_counts().idxmax()) + " zone"
                    metrics_dd = [
                        ("pressing intensity",  f"PPDA {ppda_val_dd:.2f}"),
                        ("defensive structure", f"High/Mid/Low actions: {high}/{mid}/{low}"),
                        ("compactness",         f"{compact_dd:.2f} y-std"),
                        ("defensive line",      f"avg line at x={def_line:.1f}"),
                        ("recoveries",          str(recovs)),
                        ("aerial duels",        str(aerial)),
                        ("shots conceded",      str(conceded)),
                        ("vulnerable zones",    vuln),
                    ]
                    heat_fig_dd = tp._phase_base_pitch("C Heatmap — RM defensive action density")
                    if not def_act_dd.empty:
                        heat_fig_dd = tp._add_phase_density(heat_fig_dd, def_act_dd["x"], def_act_dd["y"], "Blues", "Defensive density")
                        heat_fig_dd.add_trace(go.Scatter(
                            x=def_act_dd["x"], y=def_act_dd["y"], mode="markers",
                            marker=dict(size=4, color="rgba(255,255,255,0.45)", line=dict(color="rgba(0,0,0,0.18)", width=0.5)),
                            name="Action", hoverinfo="skip",
                        ))
                    heat_fig_dd = tp._add_direction_arrows(heat_fig_dd, meta_dd["opponent"], rm_name_dd)
                    viz_fig_dd = go.Figure()
                    for blk, cnt, col in [("High", high, "#059669"), ("Middle", mid, "#2563eb"), ("Low", low, "#dc2626")]:
                        viz_fig_dd.add_trace(go.Bar(x=[blk], y=[cnt], name=f"{blk} Block", marker_color=col, text=[cnt], textposition="auto"))
                    viz_fig_dd.update_layout(height=360, title="C Visualization — defensive structure by block",
                                             plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                             font=dict(color="#0b1730", size=12),
                                             xaxis=dict(gridcolor="#e0d9cc", color="#0b1730"),
                                             yaxis=dict(gridcolor="#e0d9cc", color="#0b1730"))

                # ── D. Offensive Transition ──────────────────────────────────
                else:
                    fb_eff   = float(trans_df_dd["shot_in_15s"].mean() * 100) if not trans_df_dd.empty else 0.0
                    txth     = float(trans_df_dd["xg_in_window"].sum()) if not trans_df_dd.empty else 0.0
                    txth_obs = int(trans_df_dd["xg_obs_count"].sum()) if not trans_df_dd.empty else 0
                    t2s      = float(trans_df_dd["time_to_first_shot"].dropna().median()) if not trans_df_dd.empty else 0.0
                    vert     = float(trans_df_dd["vertical_gain"].mean()) if not trans_df_dd.empty else 0.0
                    metrics_dd = [
                        ("fast break efficiency", f"{fb_eff:.1f}% transitions with shot <=15s"),
                        ("transition xG",         f"{txth:.2f} (from {txth_obs} shots with xG qualifier)"),
                        ("time-to-first-shot",    f"{t2s:.2f}s median"),
                        ("verticality",           f"{vert:.2f} average x-gain"),
                    ]
                    heat_fig_dd = tp._phase_base_pitch("D Heatmap — transition origins")
                    if not trans_df_dd.empty:
                        heat_fig_dd = tp._add_phase_density(heat_fig_dd, trans_df_dd["origin_x"], trans_df_dd["origin_y"], "Viridis", "Origin density")
                        heat_fig_dd.add_trace(go.Scatter(
                            x=trans_df_dd["origin_x"], y=trans_df_dd["origin_y"], mode="markers",
                            marker=dict(size=4, color="rgba(255,255,255,0.45)", line=dict(color="rgba(0,0,0,0.18)", width=0.5)),
                            name="Origin", hoverinfo="skip",
                        ))
                    heat_fig_dd = tp._add_direction_arrows(heat_fig_dd, meta_dd["opponent"], rm_name_dd)
                    viz_fig_dd = tp._phase_base_pitch("Transition origin/destination map")
                    if not trans_df_dd.empty:
                        xs_td, ys_td = [], []
                        for _, row_td in trans_df_dd.iterrows():
                            xs_td += [row_td["origin_x"], row_td["dest_x"], None]
                            ys_td += [row_td["origin_y"], row_td["dest_y"], None]
                        viz_fig_dd.add_trace(go.Scatter(x=xs_td, y=ys_td, mode="lines", name="Transition path",
                                                         line=dict(color="#e11d48", width=1.2), opacity=0.45, hoverinfo="skip"))
                        viz_fig_dd.add_trace(go.Scatter(x=trans_df_dd["origin_x"], y=trans_df_dd["origin_y"], mode="markers",
                                                         name="Origin", marker=dict(color="#f97316", size=6, line=dict(color="white", width=1))))
                        viz_fig_dd.add_trace(go.Scatter(x=trans_df_dd["dest_x"], y=trans_df_dd["dest_y"], mode="markers",
                                                         name="Destination", marker=dict(color="#22c55e", size=6, line=dict(color="white", width=1))))
                    viz_fig_dd = tp._add_direction_arrows(viz_fig_dd, meta_dd["opponent"], rm_name_dd)

                # Render metric table
                metrics_df_dd = pd.DataFrame(metrics_dd, columns=["Metric", "Value"])
                st.dataframe(metrics_df_dd, width="stretch", hide_index=True)

                # Render heatmap + visualization side-by-side
                col_h, col_v = st.columns(2)
                with col_h:
                    _chart_card(f"{deep_phase} — Heatmap", heat_fig_dd, key="tp_dd_heat")
                with col_v:
                    _chart_card(f"{deep_phase} — Visualization", viz_fig_dd, key="tp_dd_viz")
            else:
                _no_data("Select a match to view phase deep-dive details.")
        except Exception as e:
            st.warning(f"Phase deep-dive unavailable: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# OPPONENT SCOUT
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "Opponent Scout":
    _page_header("Opponent Scout",
                 "Opponent profile and threat analysis from Opta event data")

    opts = _match_opts(competition, season)
    if not opts:
        _no_data(f"No matches available for {competition} {season}.")
    else:
        match_labels = [o["label"] for o in opts]
        sel = st.selectbox("Select Match", match_labels, key="oa_match")
        fp  = next(o["value"] for o in opts if o["label"] == sel)

        # Load once, reuse throughout
        try:
            _oa_data   = load_match_json(fp)
            _oa_meta   = extract_match_meta(_oa_data)
            _oa_events = parse_events(_oa_data)
            _oa_opp_meta = {**_oa_meta, "rm_id": _oa_meta["opp_id"], "opp_id": _oa_meta["rm_id"],
                            "rm_score": _oa_meta["opp_score"], "opp_score": _oa_meta["rm_score"]}
            _oa_rm_meta  = {**_oa_meta}
            _oa_ok   = calc_match_kpis(_oa_events, _oa_opp_meta)
            _oa_rk   = calc_match_kpis(_oa_events, _oa_rm_meta)
            _oa_name = _oa_meta["opponent"]
            _oa_loaded = True
        except Exception:
            _oa_loaded = False

        # ── Opponent KPIs ─────────────────────────────────────────────────────
        if _oa_loaded:
            _section_hdr(f"Opponent: {_oa_name}")
            _kpi_row([
                ("Shots",       _oa_ok["shots_total"],               _OPP,                 None),
                ("On Target",   _oa_ok.get("shots_on_target", "—"),  _OPP,                 None),
                ("xG",          _oa_ok["xg_for"],                    _C["accent_orange"],   None),
                ("Pass Acc.",   f"{_oa_ok['pass_accuracy']}%",       _C["accent_blue"],     None),
                ("Tackles",     _oa_ok["tackles"],                   _C["accent_purple"],   None),
                ("PPDA (opp)",  calc_ppda(_oa_events, _oa_opp_meta), _C["text_secondary"],  "vs RM"),
            ])
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # ── Starting XIs Shape ────────────────────────────────────────────────
        _section_hdr("Starting XIs Shape (Selected Match)")
        try:
            _chart_card("Starting XIs", oa._lineup_pitch(fp), key="oa_lineup")
        except Exception as e:
            st.warning(f"Starting XIs unavailable: {e}")

        # ── Opponent Threat Heatmap ───────────────────────────────────────────
        _section_hdr("Opponent Threat Heatmap (action density)")
        try:
            _chart_card("Threat Heatmap", oa._threat_chart(fp), key="oa_threat")
        except Exception as e:
            st.warning(f"Threat heatmap unavailable: {e}")

        # ── Opponent shot map ─────────────────────────────────────────────────
        try:
            _chart_card("Opponent Shot Map", oa._shot_map(fp), key="oa_shot")
        except Exception:
            try:
                _chart_card("Shot Map (Both Teams)",
                    ma._shot_map("Single", fp, competition, season, "All", None, None, "All"),
                    key="oa_shot_fb")
            except Exception as e:
                st.warning(f"Shot map unavailable: {e}")

        # ── Opponent player table ─────────────────────────────────────────────
        _section_hdr("Opponent Player Stats")
        if _oa_loaded:
            try:
                opp_stats = get_player_stats(_oa_events, _oa_meta["opp_id"])
                if not opp_stats.empty:
                    show_cols = [c for c in ["player_name","passes","shots","goals",
                                              "key_passes","tackles","interceptions","xg"]
                                 if c in opp_stats.columns]
                    st.dataframe(opp_stats[show_cols].head(20),
                                 width="stretch", hide_index=True)
            except Exception as e:
                st.warning(f"Opponent player table unavailable: {e}")

        # ── Style, Strengths, Weaknesses & Tendencies ─────────────────────────
        _section_hdr("Style, Strengths, Weaknesses, Tendencies")
        if _oa_loaded:
            try:
                ok = _oa_ok
                _style = oa._style_classification(ok)
                _strengths, _weaknesses = [], []
                if ok["pass_accuracy"] >= 84:
                    _strengths.append("Reliable circulation under pressure")
                else:
                    _weaknesses.append("Pass completion unstable under pressure")
                if ok["shots_total"] >= 10:
                    _strengths.append("Creates frequent shot volume")
                else:
                    _weaknesses.append("Limited shot generation")
                if ok["ppda"] <= 7:
                    _strengths.append("Can sustain active pressing phases")
                else:
                    _weaknesses.append("Pressing intensity drops in settled phases")
                if ok.get("goals_conceded", 0) >= 2:
                    _weaknesses.append("Concedes high-quality moments")

                _press_tend = f"PPDA {ok['ppda']:.2f}; defensive actions {ok['tackles'] + ok['interceptions'] + ok['ball_recoveries']}"
                _poss_style = f"{ok['possession']}% possession, {ok['pass_accuracy']}% pass accuracy"

                # Transition danger
                _opp_ev = _oa_events[_oa_events["contestant_id"] == _oa_meta["opp_id"]]
                _regains = _opp_ev[_opp_ev["is_recovery"] | _opp_ev["is_interception"] | _opp_ev["is_tackle"]].copy()
                if not _regains.empty:
                    _tdf = _oa_events.sort_values(["period","minute","second","event_id"]).copy()
                    _tdf["_t"] = (_tdf["minute"].fillna(0).astype(int) * 60) + _tdf["second"].fillna(0).astype(int)
                    _regains["_t"] = (_regains["minute"].fillna(0).astype(int) * 60) + _regains["second"].fillna(0).astype(int)
                    _ts = 0
                    for _, _r in _regains.iterrows():
                        _win = _tdf[(_tdf["contestant_id"] == _oa_meta["opp_id"]) & (_tdf["_t"] >= _r["_t"]) & (_tdf["_t"] <= _r["_t"] + 15)]
                        if not _win[_win["is_shot"]].empty:
                            _ts += 1
                    _trans_danger = f"{oa._safe_div(_ts, len(_regains)) * 100:.1f}% regains lead to shot <=15s"
                else:
                    _trans_danger = "No clear transition windows"

                # Vulnerable zones (where RM won duels)
                _rm_ev = _oa_events[_oa_events["contestant_id"] == _oa_meta["rm_id"]]
                _forced = _rm_ev[_rm_ev["is_recovery"] | _rm_ev["is_interception"] | _rm_ev["is_tackle"]]
                if _forced.empty:
                    _vuln_zone = "Not enough forced turnovers"
                else:
                    _thirds = pd.cut(_forced["x"], bins=[-1, 33, 67, 101], labels=["RM defensive", "middle", "RM attacking"])
                    _vuln_zone = str(_thirds.value_counts().idxmax())

                _style_rows = [
                    ("opponent style classification", _style),
                    ("strengths and weaknesses",
                     "Strengths: " + "; ".join(_strengths[:3]) + " | Weaknesses: " + "; ".join(_weaknesses[:3])),
                    ("pressing tendencies",  _press_tend),
                    ("possession style",     _poss_style),
                    ("transition danger",    _trans_danger),
                    ("vulnerable zones",     _vuln_zone),
                ]
                st.dataframe(
                    pd.DataFrame(_style_rows, columns=["Category", "Assessment"]),
                    width="stretch", hide_index=True,
                )
            except Exception as e:
                st.warning(f"Style analysis unavailable: {e}")

        # ── Tactical Similarities, Reference Matches, Set-Pieces ──────────────
        _section_hdr("Tactical Similarities, Reference Matches, Set-Pieces")
        if _oa_loaded:
            try:
                ok = _oa_ok
                rk = _oa_rk
                # Key players
                _pstats = get_player_stats(_oa_events, _oa_meta["opp_id"])
                if _pstats.empty:
                    _key_players = []
                else:
                    _key_players = _pstats.sort_values(
                        ["shots", "xg", "passes", "tackles", "interceptions"],
                        ascending=[False, False, False, False, False],
                    ).head(3)["player_name"].tolist()

                # Tactical comparison vs RM
                _pass_d  = ok["pass_accuracy"] - rk["pass_accuracy"]
                _ppda_d  = ok["ppda"] - rk["ppda"]
                _shot_d  = ok["shots_total"] - rk["shots_total"]
                _xg_d    = ok["xg_for"] - rk["xg_for"]
                _tac_cmp = (f"Pass acc delta {_pass_d:+.1f} pp | PPDA delta {_ppda_d:+.2f} | "
                            f"Shot volume delta {_shot_d:+d} | xG delta {_xg_d:+.2f}")

                # Tactical similarity score
                _norm_v = [
                    min(abs(_pass_d) / 25.0, 1.0),
                    min(abs(_ppda_d) / 12.0, 1.0),
                    min(abs(_shot_d) / 15.0, 1.0),
                    min(abs(_xg_d)   / 2.5,  1.0),
                    min(abs(ok["possession"] - rk["possession"]) / 40.0, 1.0),
                ]
                _sim = round(100.0 * (1.0 - sum(_norm_v) / len(_norm_v)), 1)

                # Reference matches
                from utils.data_helpers import get_match_options as _gmo
                _refs = [m.get("label", "") for m in _gmo(competition, season)
                         if _oa_meta["opponent"] in m.get("label", "")][:5]
                _refs_display = (f"{len(_refs)} fixture(s) vs {_oa_meta['opponent']}: " + ", ".join(_refs)
                                 if _refs else "No additional indexed matches")

                # Set-piece tendencies
                _opp_ev2 = _oa_events[_oa_events["contestant_id"] == _oa_meta["opp_id"]]
                _corners = int((_opp_ev2["type_id"] == 6).sum())
                _ev_s = _oa_events.sort_values(["period","minute","second","event_id"]).copy()
                _ev_s["_es"] = (_ev_s["minute"].fillna(0).astype(int) * 60) + _ev_s["second"].fillna(0).astype(int)
                _opp_s = _ev_s[_ev_s["contestant_id"] == _oa_meta["opp_id"]].copy()
                _cs_count = 0
                for _, _c in _opp_s[_opp_s["type_id"] == 6].iterrows():
                    _t0 = _c["_es"]
                    _w  = _opp_s[(_opp_s["_es"] >= _t0) & (_opp_s["_es"] <= _t0 + 20)]
                    _cs_count += int(len(_w[_w["is_shot"]]))
                _sp_line = f"Corners: {_corners}, shots within 20s of corner: {_cs_count}"

                _ctx_rows = [
                    ("key players",              ", ".join(_key_players) if _key_players else "Not enough player-level events"),
                    ("tactical comparison vs RM", _tac_cmp),
                    ("reference matches",         _refs_display),
                    ("set-piece tendencies",      _sp_line),
                ]
                st.dataframe(
                    pd.DataFrame(_ctx_rows, columns=["Category", "Assessment"]),
                    width="stretch", hide_index=True,
                )
            except Exception as e:
                st.warning(f"Tactical context unavailable: {e}")

        # ── Automated Tactical Report ─────────────────────────────────────────
        _section_hdr("Automated Tactical Report")
        if _oa_loaded:
            try:
                _report_lines = [
                    f"Automated Tactical Report — {_oa_name} vs Real Madrid",
                    f"Style: {_style}.",
                    f"Pressing profile: {_press_tend}.",
                    f"Possession profile: {_poss_style}.",
                    f"Transition danger: {_trans_danger}.",
                    f"Key players: {', '.join(_key_players) if _key_players else 'No clear high-impact players extracted'}.",
                    f"Vulnerable zone against RM pressure: {_vuln_zone}.",
                    f"Set-piece tendencies: {_sp_line}.",
                    f"Tactical similarity to RM: {_sim:.1f}/100.",
                    "Actionable recommendation: press their first pass after regain and force play into the identified vulnerable zone.",
                ]
                st.code("\n".join(_report_lines), language=None)
            except Exception:
                _no_data("Tactical report unavailable.")


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARKING  ← reference page (must match /benchmarking exactly)
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "Benchmarking":
    _page_header("Benchmarking",
                 "Cross-season and cross-competition performance comparison")

    # ── Filter: competitions multi-select ─────────────────────────────────────
    _section_hdr("Compare Competitions (select any combination)")
    bm_comps = st.multiselect(
        "Competitions",
        options=_all_comps,
        default=_all_comps,
        label_visibility="collapsed",
        key="bm_comps",
    )

    # ── Season KPI Summary table ──────────────────────────────────────────────
    _section_hdr("Season KPI Summary")
    if not bm_comps:
        _no_data("Select at least one competition above.")
    else:
        with st.spinner("Loading season data…"):
            summary_df = _bm_gather(tuple(bm_comps))

        if summary_df.empty:
            _no_data("No data found for the selected competitions.")
        else:
            _COLS = {
                "Competition": "Competition", "Season": "Season",
                "played": "MP", "wins": "W", "draws": "D", "losses": "L",
                "win_pct": "Win%", "goals_scored": "GF", "goals_conceded": "GA",
                "goal_diff": "GD", "goals_per_game": "G/G",
                "xg_for": "xG For", "xg_against": "xG vs",
                "avg_pass_acc": "Pass Acc%",
            }
            display = summary_df[[c for c in _COLS if c in summary_df.columns]].rename(columns=_COLS)
            avg = bm._overall_average(summary_df)
            if not avg.empty:
                avg_row = {
                    "Competition": "Overall", "Season": "Average",
                    "MP": round(avg.get("played", 0), 1),
                    "W":  round(avg.get("wins", 0), 1),
                    "D":  round(avg.get("draws", 0), 1),
                    "L":  round(avg.get("losses", 0), 1),
                    "Win%": round(avg.get("win_pct", 0), 1),
                    "GF": round(avg.get("goals_scored", 0), 1),
                    "GA": round(avg.get("goals_conceded", 0), 1),
                    "GD": round(avg.get("goal_diff", 0), 1),
                    "G/G": round(avg.get("goals_per_game", 0), 2),
                    "xG For": round(avg.get("xg_for", 0), 2),
                    "xG vs":  round(avg.get("xg_against", 0), 2),
                    "Pass Acc%": round(avg.get("avg_pass_acc", 0), 1),
                }
                display = pd.concat([display, pd.DataFrame([avg_row])], ignore_index=True)
            st.markdown(_df_html_table(display), unsafe_allow_html=True)

        # ── Goals For vs Against ──────────────────────────────────────────────
        _chart_card("Goals For vs Against",
                    _goals_chart_fig(tuple(bm_comps)), key="bm_goals")

        # ── Win % ─────────────────────────────────────────────────────────────
        _chart_card("Win % by Competition / Season",
                    _win_chart_fig(tuple(bm_comps)), key="bm_win")

        # ── xG For vs Against ─────────────────────────────────────────────────
        _chart_card("xG For vs xG Against",
                    _xg_chart_fig(tuple(bm_comps)), key="bm_xg")

        # ── Pass Accuracy ─────────────────────────────────────────────────────
        _chart_card("Pass Accuracy %",
                    _pass_chart_fig(tuple(bm_comps)), key="bm_pass")

    # ── RM vs Avg vs Rivals section ───────────────────────────────────────────
    _section_hdr("RM vs Avg of Opponents Faced vs Rivals")

    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 4])
    with c1:
        bm_comp = st.selectbox("Competition ", _all_comps, index=0,
                               label_visibility="visible", key="bm_c")
    with c2:
        bm_seasons = get_available_seasons(bm_comp)
        bm_season  = st.selectbox("Season ", bm_seasons, index=0,
                                  label_visibility="visible", key="bm_s")

    mf_opts = _match_file_opts(bm_comp, bm_season)

    with c3:
        if mf_opts:
            from_idx   = st.selectbox("From Match", range(len(mf_opts)),
                                      format_func=lambda i: mf_opts[i]["label"],
                                      index=0, label_visibility="visible", key="bm_from")
            from_match = mf_opts[from_idx]["value"]
        else:
            st.write("No matches"); from_match = None
    with c4:
        if mf_opts:
            to_idx   = st.selectbox("To Match", range(len(mf_opts)),
                                    format_func=lambda i: mf_opts[i]["label"],
                                    index=len(mf_opts)-1,
                                    label_visibility="visible", key="bm_to")
            to_match = mf_opts[to_idx]["value"]
        else:
            st.write(""); to_match = None

    with c5:
        rv_opts = _rival_opts(bm_comp, bm_season)
        rv_vals = [o["value"] for o in rv_opts]
        defaults = [r for r in ["Barcelona", "Atlético de Madrid"] if r in rv_vals]
        rivals = st.multiselect("Rivals", rv_vals, default=defaults,
                                label_visibility="visible", key="bm_rivals")

    # ── Rival comparison charts ───────────────────────────────────────────────
    with st.spinner("Computing rival comparison…"):
        try:
            fig_main, fig_radar, fig_phase = bm._rival_comparison(
                bm_comp, bm_season, rivals, from_match, to_match)

            _chart_card("RM vs Avg of Opponents Faced vs Rivals", fig_main, key="bm_rv_main")
            _chart_card("Tactical Metrics Comparison (Raw Event-Derived)", fig_radar, key="bm_rv_tac")
            _chart_card("Core KPI Comparison (Raw Event-Derived)", fig_phase, key="bm_rv_kpi")

        except Exception as e:
            st.warning(f"Rival comparison unavailable: {e}")

    # ── League Table ──────────────────────────────────────────────────────────
    _section_hdr(f"League Table — {bm_comp} {bm_season} (from match data)")
    with st.spinner("Building league table…"):
        ltdf = _league_df(bm_comp, bm_season)
    if ltdf is not None and not ltdf.empty:
        lt_show = ["team","played","goals_for","goals_against","points",
                   "points_per_game","goals_per_game","xg_per_game",
                   "pass_acc","shots_per_game","def_actions_pg"]
        lt_show = [c for c in lt_show if c in ltdf.columns]
        lt_sorted = ltdf[lt_show].sort_values("points", ascending=False).reset_index(drop=True)
        lt_sorted.index += 1
        st.dataframe(lt_sorted, width="stretch")
    else:
        _no_data("League table data not available.")


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "Report":
    _page_header("Analysis Report Generator",
                 "Build a professional PDF or DOCX report from your current dashboard selections")

    st.markdown("""
    <div class="rm-phase-alert">
      <b>Data integrity:</b> every number in the report is derived directly from the
      underlying Opta dataset and existing dashboard calculations.
      No synthetic data, no placeholder values.
    </div>""", unsafe_allow_html=True)

    # ── Report filters ─────────────────────────────────────────────────────
    _section_hdr("1 — Select Match Scope")
    rpt_opts = _match_opts(competition, season)
    rpt_labels = [o["label"] for o in rpt_opts] if rpt_opts else []

    rc1, rc2 = st.columns([2, 4])
    with rc1:
        rpt_mode = st.selectbox("Match Mode",
                                ["Single Match", "Match Range", "Specific Matches"],
                                key="rpt_mode")
    rpt_fps: list[str] = []
    rpt_match_labels: list[str] = []

    if not rpt_opts:
        _no_data(f"No matches found for {competition} {season}.")
    else:
        if rpt_mode == "Single Match":
            with rc2:
                rpt_sel = st.selectbox("Select Match", rpt_labels, key="rpt_single")
            rpt_fps         = [next(o["value"] for o in rpt_opts if o["label"] == rpt_sel)]
            rpt_match_labels = [rpt_sel]
        elif rpt_mode == "Match Range":
            rr1, rr2 = st.columns(2)
            with rr1:
                rpt_from = st.selectbox("From Match", rpt_labels, index=0, key="rpt_from")
            with rr2:
                rpt_to   = st.selectbox("To Match", rpt_labels,
                                         index=len(rpt_labels)-1, key="rpt_to")
            _from_fp = next(o["value"] for o in rpt_opts if o["label"] == rpt_from)
            _to_fp   = next(o["value"] for o in rpt_opts if o["label"] == rpt_to)
            _range_set = pa._selected_file_set(competition, season, _from_fp, _to_fp)
            rpt_fps = [o["value"] for o in rpt_opts if o["value"] in _range_set]
            rpt_match_labels = [o["label"] for o in rpt_opts if o["value"] in _range_set]
        else:  # Specific Matches
            with rc2:
                _rpt_spec = st.multiselect("Select Matches (max 5)", rpt_labels,
                                           max_selections=5, key="rpt_spec")
            rpt_fps         = [next(o["value"] for o in rpt_opts if o["label"] == l)
                               for l in _rpt_spec]
            rpt_match_labels = list(_rpt_spec)

    # ── Player selection ───────────────────────────────────────────────────
    _section_hdr("2 — Select Athletes")
    with st.spinner("Loading squad…"):
        rpt_squad = _squad_full_df(competition, season)

    rpt_all_players = rpt_squad["player_name"].dropna().tolist() if not rpt_squad.empty else []
    rpt_players = st.multiselect(
        "Select Players for Detailed Analysis (max 5, optional)",
        rpt_all_players,
        max_selections=5,
        key="rpt_players",
        help="Leave blank to include squad-level data only",
    )

    # ── Content toggles ────────────────────────────────────────────────────
    _section_hdr("3 — Report Content")
    rt1, rt2, rt3, rt4 = st.columns(4)
    with rt1:
        inc_tactical = st.checkbox("Tactical Charts", value=True, key="rpt_inc_tac")
    with rt2:
        inc_match    = st.checkbox("Match Charts",    value=True, key="rpt_inc_match")
    with rt3:
        inc_bm       = st.checkbox("Benchmarking",   value=True, key="rpt_inc_bm")
    with rt4:
        inc_radar    = st.checkbox("Radar / Comparison", value=True, key="rpt_inc_radar")

    # ── Generate button ────────────────────────────────────────────────────
    _section_hdr("4 — Generate")
    if not rpt_fps:
        _no_data("Select at least one match above to generate a report.")
    else:
        gen_col1, gen_col2, gen_col3 = st.columns([2, 2, 4])
        gen_pdf  = gen_col1.button("⬇ Generate PDF",  key="rpt_gen_pdf",
                                    type="primary", use_container_width=True)
        gen_docx = gen_col2.button("⬇ Generate DOCX", key="rpt_gen_docx",
                                    type="secondary", use_container_width=True)

        if gen_pdf or gen_docx:
            with st.spinner("Collecting data and generating report…"):
                # ── Load match records ────────────────────────────────────
                _rpt_records: list[dict] = []
                for _fp in rpt_fps:
                    try:
                        _, _meta, _events = ma._load(_fp)
                        if _meta and _events is not None and not _events.empty:
                            _rpt_records.append({
                                "meta":         _meta,
                                "kpis":         calc_match_kpis(_events, _meta),
                                "ppda":         calc_ppda(_events, _meta),
                                "player_stats": get_player_stats(_events, _meta["rm_id"]),
                            })
                    except Exception:
                        pass

                # ── Load per-player match series ──────────────────────────
                _rpt_player_dfs: dict[str, pd.DataFrame] = {}
                _files_tuple = tuple(sorted(rpt_fps))
                for _pname in rpt_players:
                    try:
                        _rpt_player_dfs[_pname] = _player_match_series(
                            competition, season, _pname, _files_tuple
                        )
                    except Exception:
                        _rpt_player_dfs[_pname] = pd.DataFrame()

                # ── Collect figures ───────────────────────────────────────
                _figs: dict = {}
                _fp0 = rpt_fps[0]
                _mk  = "Range" if len(rpt_fps) > 1 else "Single"
                _fm  = rpt_fps[0]  if len(rpt_fps) > 1 else None
                _tm  = rpt_fps[-1] if len(rpt_fps) > 1 else None

                if inc_match:
                    try:
                        _figs["shot_map"] = ma._shot_map(_mk, _fp0, competition, season,
                                                          "All", _fm, _tm, "All")
                    except Exception:
                        pass
                    try:
                        _figs["xg_chart"] = ma._xg_chart(_mk, _fp0, competition, season,
                                                          "All", _fm, _tm)
                    except Exception:
                        pass
                    try:
                        _figs["pass_map"] = ma._pass_map(_mk, _fp0, competition, season,
                                                          "All", _fm, _tm, "All")
                    except Exception:
                        pass
                    try:
                        _figs["pass_network"] = ma._pass_network(_mk, _fp0, competition, season,
                                                                   "All", _fm, _tm, "xi", "All")
                    except Exception:
                        pass

                if inc_tactical:
                    try:
                        _figs["press_map"] = tp._press_map(_fp0)
                    except Exception:
                        pass
                    try:
                        _figs["press_class"] = tp._press_classification(_fp0)
                    except Exception:
                        pass
                    try:
                        _figs["tactical_bars"] = ma._tactical_bars(_mk, _fp0, competition,
                                                                    season, "All", _fm, _tm)
                    except Exception:
                        pass

                if inc_bm:
                    try:
                        _figs["benchmarking_goals"] = bm._goals_chart([competition])
                    except Exception:
                        pass
                    try:
                        _figs["benchmarking_xg"] = bm._xg_chart([competition])
                    except Exception:
                        pass

                if inc_radar and rpt_players:
                    # Build combined radar (reuse PA logic)
                    _sq_pg_max = {}
                    for _col in ["passes", "shots", "goals", "tackles", "xg"]:
                        if _col in rpt_squad.columns and "matches_played" in rpt_squad.columns:
                            _sq_col = rpt_squad[_col] / rpt_squad["matches_played"].clip(lower=1)
                            _sq_pg_max[_col] = float(_sq_col.max()) or 1.0
                        else:
                            _sq_pg_max[_col] = 1.0

                    _radar_cats = ["Passes/G","Shots/G","Goals/G","Tackles/G","xG/G"]
                    _col_keys   = ["passes","shots","goals","tackles","xg"]
                    _PAL = ["#d4af37","#3b82f6","#22c55e","#f97316","#ec4899"]
                    _PAL_F = ["rgba(212,175,55,0.14)","rgba(59,130,246,0.14)",
                              "rgba(34,197,94,0.14)","rgba(249,115,22,0.14)",
                              "rgba(236,72,153,0.14)"]
                    _rfig = go.Figure()
                    for _ri, _rp in enumerate(rpt_players):
                        _rpdf = _rpt_player_dfs.get(_rp, pd.DataFrame())
                        if _rpdf.empty:
                            continue
                        _nm   = len(_rpdf)
                        _agg  = _rpdf[_col_keys].sum()
                        _pg   = (_agg / max(_nm, 1)).round(3)
                        _vals = [min(float(_pg.get(_c,0))/_sq_pg_max[_c]*100,100) for _c in _col_keys]
                        _rfig.add_trace(go.Scatterpolar(
                            r=_vals+[_vals[0]], theta=_radar_cats+[_radar_cats[0]],
                            fill="toself", name=_rp,
                            line=dict(color=_PAL[_ri % 5], width=2),
                            fillcolor=_PAL_F[_ri % 5],
                        ))
                    _rfig.update_layout(
                        paper_bgcolor="white", height=400,
                        polar=dict(
                            bgcolor="white",
                            radialaxis=dict(visible=True, range=[0,100], ticksuffix="%"),
                        ),
                        title="Player Radar — % of Squad Max",
                        showlegend=len(rpt_players) > 1,
                        margin=dict(l=60,r=60,t=60,b=50),
                    )
                    _figs["radar_comparison"] = _rfig

                # ── Build config dict ─────────────────────────────────────
                _cfg = rg.build_report_config(
                    competition    = competition,
                    season         = season,
                    match_mode     = rpt_mode,
                    fps            = rpt_fps,
                    match_labels   = rpt_match_labels,
                    players        = rpt_players,
                    match_records  = _rpt_records,
                    squad_df       = rpt_squad,
                    player_dfs     = _rpt_player_dfs,
                    figures        = _figs,
                )

                # ── Generate & serve ──────────────────────────────────────
                _ts  = _cfg["generated_at"].strftime("%Y%m%d_%H%M")
                _rid = _cfg["report_id"]

                if gen_pdf:
                    try:
                        _pdf_bytes = rg.generate_pdf(_cfg)
                        st.download_button(
                            label="⬇ Download PDF Report",
                            data=_pdf_bytes,
                            file_name=f"RM_Report_{_ts}_{_rid}.pdf",
                            mime="application/pdf",
                            key="rpt_dl_pdf",
                        )
                        st.success(f"PDF ready — Report ID: {_rid}")
                    except Exception as _e:
                        st.error(f"PDF generation failed: {_e}")

                if gen_docx:
                    try:
                        _docx_bytes = rg.generate_docx(_cfg)
                        st.download_button(
                            label="⬇ Download DOCX Report",
                            data=_docx_bytes,
                            file_name=f"RM_Report_{_ts}_{_rid}.docx",
                            mime="application/vnd.openxmlformats-officedocument"
                                 ".wordprocessingml.document",
                            key="rpt_dl_docx",
                        )
                        st.success(f"DOCX ready — Report ID: {_rid}")
                    except Exception as _e:
                        st.error(f"DOCX generation failed: {_e}")

        # ── Preview: report summary card ──────────────────────────────────
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        _section_hdr("Report Preview")
        prev_recs: list[dict] = []
        for _fp in rpt_fps[:3]:
            try:
                _, _m, _e = ma._load(_fp)
                if _m and _e is not None and not _e.empty:
                    prev_recs.append({
                        "meta": _m,
                        "kpis": calc_match_kpis(_e, _m),
                        "ppda": calc_ppda(_e, _m),
                    })
            except Exception:
                pass

        if prev_recs:
            pv_n  = len(prev_recs)
            pv_gf = sum(r["meta"].get("rm_score",  0) for r in prev_recs)
            pv_ga = sum(r["meta"].get("opp_score", 0) for r in prev_recs)
            pv_xf = sum(r["kpis"].get("xg_for",    0) for r in prev_recs)
            pv_xa = sum(r["kpis"].get("xg_against",0) for r in prev_recs)
            pv_w  = sum(1 for r in prev_recs if r["meta"].get("rm_score",0) > r["meta"].get("opp_score",0))
            _kpi_row([
                ("Matches",    pv_n,                     _C["accent_blue"],   rpt_mode),
                ("Record",     f"{pv_w}W/{pv_n-pv_w}L", _C["accent_green"],  "Selected period"),
                ("Goals / GA", f"{pv_gf} / {pv_ga}",    _C["accent_orange"], None),
                ("xG / xGA",   f"{pv_xf:.2f} / {pv_xa:.2f}", _C["accent_purple"], "Total"),
            ])

        # ── Per-match preview table ───────────────────────────────────────
        if prev_recs:
            _prev_rows = []
            for _r in prev_recs:
                _pm, _pk = _r["meta"], _r["kpis"]
                _res = ("W" if _pm.get("rm_score",0) > _pm.get("opp_score",0) else
                        "D" if _pm.get("rm_score",0) == _pm.get("opp_score",0) else "L")
                _prev_rows.append({
                    "Match":  f"{_pm.get('home_team','?')} vs {_pm.get('away_team','?')}",
                    "Score":  _pm.get("score_str","?"),
                    "Result": _res,
                    "Poss%":  f"{_pk.get('possession',0):.0f}%",
                    "PA%":    f"{_pk.get('pass_accuracy',0):.0f}%",
                    "xGF":    f"{_pk.get('xg_for',0):.2f}",
                    "xGA":    f"{_pk.get('xg_against',0):.2f}",
                    "PPDA":   str(_r.get("ppda","?")),
                })
            if len(rpt_fps) > 3:
                _prev_rows.append({"Match": f"… +{len(rpt_fps)-3} more matches",
                                   "Score":"","Result":"","Poss%":"","PA%":"","xGF":"","xGA":"","PPDA":""})
            _prev_df = pd.DataFrame(_prev_rows)

            def _pv_style(v):
                if v == "W": return "color: #22c55e; font-weight: bold"
                if v == "D": return "color: #f59e0b; font-weight: bold"
                if v == "L": return "color: #ef4444; font-weight: bold"
                return ""

            st.dataframe(_prev_df.style.map(_pv_style, subset=["Result"]),
                         width="stretch", hide_index=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.html(
    '<div style="margin-top:40px;padding:14px 22px;'
    'background:linear-gradient(90deg,#060f1e 0%,#0b1730 100%);'
    'border-top:3px solid #c8a951;font-size:0.80rem;'
    'display:flex;flex-wrap:wrap;gap:8px;align-items:center;'
    'justify-content:center;text-align:center;'
    'margin-left:-1.5rem;margin-right:-1.5rem">'
    '<span style="color:#ffffff !important;font-weight:700;font-family:Arial,sans-serif">'
    'Real Madrid CF Tactical &amp; Player Performance Analytics</span>'
    '<span style="color:#c8a951 !important;opacity:.8;font-family:Arial,sans-serif">•</span>'
    '<span style="color:#ffffff !important;font-weight:700;font-family:Arial,sans-serif">'
    'Sudhir Dahiya</span>'
    '<span style="color:#c8a951 !important;opacity:.8;font-family:Arial,sans-serif">•</span>'
    '<span style="color:#ffffff !important;font-family:Arial,sans-serif">'
    "Master&#39;s in Sports Analytics (2025&#8211;2026)</span>"
    '<span style="color:#c8a951 !important;opacity:.8;font-family:Arial,sans-serif">•</span>'
    '<span style="color:#ffffff !important;font-family:Arial,sans-serif">'
    'Data: Opta Stats Perform</span>'
    '</div>'
)
