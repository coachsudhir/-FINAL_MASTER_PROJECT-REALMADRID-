"""
Real Madrid CF — Tactical & Player Performance Analytics
Streamlit web front-end.

This app reuses the SAME verified analytics + Plotly figure builders that power
the Dash dashboard (in dashboard/app), so every chart — xG/shot maps, pass
networks, position maps, touch maps, benchmarking — is computed identically from
the bundled real Opta dataset (dashboard/data). No synthetic data is generated
here; this module only wires Streamlit widgets to the existing figure functions.
"""

import os
import sys
from pathlib import Path

import streamlit as st

# --- make the canonical dashboard app importable -----------------------------
_APP_DIR = Path(__file__).resolve().parent / "dashboard" / "app"
sys.path.insert(0, str(_APP_DIR))
# Resolver auto-detects dashboard/data, but set it explicitly for safety.
os.environ.setdefault("DATA_ROOT", str(Path(__file__).resolve().parent / "dashboard" / "data"))

# --- reuse the verified analytics + figure builders --------------------------
from utils.data_loader import (
    get_season_match_list, calc_season_kpis, get_season_results_table,
)
from utils.data_helpers import get_match_options
import pages.match_analysis as ma
import pages.tactical_phases as tp
import pages.player_analysis as pa
import pages.benchmarking as bm

st.set_page_config(
    page_title="Real Madrid CF — Tactical Analytics",
    page_icon="⚪",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY, GOLD = "#0b1f4d", "#c9a227"
COMPETITIONS = ["LaLiga", "Copa del Rey", "Champions League"]
SEASONS = ["2025-2026", "2024-2025"]


# ---------------------------------------------------------------------------
# Cached data accessors (figures themselves are cheap thanks to lru_cache in
# the loader; we cache the heavier season-level aggregations).
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _matches(comp, season):
    return get_match_options(comp, season, "All")

@st.cache_data(show_spinner=False)
def _season_kpis(comp, season):
    return calc_season_kpis(comp, season)

@st.cache_data(show_spinner=False)
def _results(comp, season):
    return get_season_results_table(comp, season)

@st.cache_data(show_spinner=False)
def _squad(comp, season):
    return pa._build_season_player_stats(comp, season)

@st.cache_data(show_spinner=False)
def _league(comp, season):
    return bm._league_team_table(comp, season)

@st.cache_data(show_spinner=False)
def _rivals(comp, season):
    return bm._rivals_options(comp, season)


def _chart(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Sidebar — global filters + navigation
# ---------------------------------------------------------------------------
st.sidebar.title("⚪ Real Madrid CF")
st.sidebar.caption("Tactical & Player Performance Analytics")
competition = st.sidebar.selectbox("Competition", COMPETITIONS, index=0)
season = st.sidebar.selectbox("Season", SEASONS, index=0)
section = st.sidebar.radio(
    "Section",
    ["Overview", "Match Analysis", "Tactical Phases", "Player Analysis", "Benchmarking"],
)
st.sidebar.markdown("---")
st.sidebar.caption("Data: Opta Stats Perform · all metrics computed from the "
                   "bundled real dataset (no synthetic values).")

match_opts = _matches(competition, season)
match_labels = [m["label"] for m in match_opts]
match_by_label = {m["label"]: m["value"] for m in match_opts}


# ===========================================================================
# OVERVIEW
# ===========================================================================
if section == "Overview":
    st.title("Season Overview")
    st.caption(f"{competition} · {season}")
    k = _season_kpis(competition, season)
    if not k or k.get("played", 0) == 0:
        st.warning("No matches found for this competition/season.")
    else:
        c = st.columns(6)
        c[0].metric("Played", k["played"])
        c[1].metric("Record", f"{k['wins']}-{k['draws']}-{k['losses']}")
        c[2].metric("Goals (F–A)", f"{k['goals_scored']}–{k['goals_conceded']}")
        c[3].metric("xG For", k["xg_for"])
        c[4].metric("xG Against", k["xg_against"])
        c[5].metric("Win %", f"{k['win_pct']}%")
        st.markdown("#### Results")
        st.dataframe(_results(competition, season), use_container_width=True, hide_index=True)


# ===========================================================================
# MATCH ANALYSIS
# ===========================================================================
elif section == "Match Analysis":
    st.title("Match Analysis")
    st.caption("Event-level tactical breakdown — real Opta data")
    if not match_labels:
        st.warning("No matches available.")
    else:
        col1, col2 = st.columns([3, 1])
        label = col1.selectbox("Match", match_labels)
        phase = col2.selectbox("Phase Focus",
                               ["All", "Offensive", "Defensive", "Transitions", "SetPieces"])
        fp = match_by_label[label]
        args = ("Single", fp, competition, season, "All", None, None)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Shot Map (xG)")
            _chart(ma._shot_map(*args, phase))
        with c2:
            st.subheader("Pass Network")
            _chart(ma._pass_network(*args, "xi", phase))
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Pass Map")
            _chart(ma._pass_map(*args, phase))
        with c4:
            st.subheader("Cumulative xG")
            _chart(ma._xg_chart(*args))
        st.subheader("Tactical Comparison")
        _chart(ma._tactical_bars(*args))


# ===========================================================================
# TACTICAL PHASES
# ===========================================================================
elif section == "Tactical Phases":
    st.title("Tactical Phases")
    st.caption("Pressing, position maps & zonal activity — derived from event data")
    if not match_labels:
        st.warning("No matches available.")
    else:
        label = st.selectbox("Match", match_labels)
        fp = match_by_label[label]
        st.subheader("Pressing Actions Map (PPDA)")
        _chart(tp._press_map(fp))
        st.subheader("Position Map + Zonal Activity")
        col1, col2 = st.columns(2)
        team = col1.radio("Team", ["Real Madrid", "Opponent"], horizontal=True)
        phase = col2.radio("Game Phase", ["All Phases", "In Possession", "Out of Possession"],
                           horizontal=True)
        team_side = "rm" if team == "Real Madrid" else "opp"
        phase_key = {"All Phases": "all", "In Possession": "possession",
                     "Out of Possession": "defense"}[phase]
        fig, table = tp._position_map(fp, phase_key, team_side)
        _chart(fig)


# ===========================================================================
# PLAYER ANALYSIS
# ===========================================================================
elif section == "Player Analysis":
    st.title("Player Analysis")
    st.caption("Individual player metrics computed from Opta event data")
    squad = _squad(competition, season)
    if squad.empty:
        st.warning("No player data for this competition/season.")
    else:
        players = squad["player_name"].tolist() if "player_name" in squad.columns else []
        player = st.selectbox("Player", players)
        st.subheader(f"Where {player} has had his touches")
        _chart(pa._player_touch_heatmap(competition, season, player, None, False))
        st.subheader("Squad Performance Summary")
        st.dataframe(squad, use_container_width=True, hide_index=True)


# ===========================================================================
# BENCHMARKING
# ===========================================================================
elif section == "Benchmarking":
    st.title("Benchmarking")
    st.caption("Real Madrid vs league average vs rivals")
    rival_opts = [o["label"] for o in _rivals(competition, season)]
    default = [r for r in ["Barcelona", "Atlético de Madrid"] if r in rival_opts]
    rivals = st.multiselect("Rivals", rival_opts, default=default)
    figs = bm._rival_comparison(competition, season, rivals, None, None)
    titles = ["RM vs League vs Rivals", "Tactical Style", "Phase Comparison"]
    for title, fig in zip(titles, figs):
        st.subheader(title)
        _chart(fig)
    st.subheader("Cross-Competition")
    c1, c2 = st.columns(2)
    with c1:
        _chart(bm._goals_chart(COMPETITIONS))
    with c2:
        _chart(bm._win_chart(COMPETITIONS))
    st.subheader("League Table (from match data)")
    st.dataframe(_league(competition, season), use_container_width=True, hide_index=True)
