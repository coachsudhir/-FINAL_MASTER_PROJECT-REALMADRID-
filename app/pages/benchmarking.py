"""
Benchmarking Page — Real Madrid Tactical Dashboard
Season-by-season and competition comparison from Opta event data.
"""

from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from functools import lru_cache

from config import COLOR_SCHEME
from utils.data_helpers import get_competition_options, get_season_options
from utils.data_loader import (
    calc_season_kpis,
    get_season_match_list,
    get_available_competitions,
    get_competition_seasons,
    iter_match_files,
    load_match_json,
    extract_match_meta,
    parse_events,
    calc_match_kpis,
)

_C  = COLOR_SCHEME
_RM = _C["accent_blue"]
_H_CHART = 400
_H_COMPARE = 460
_PL = dict(
    paper_bgcolor=_C["surface"],
    plot_bgcolor=_C["surface"],
    font=dict(color=_C["text_primary"], size=11),
    margin=dict(l=48, r=32, t=56, b=60),
    hovermode="closest",
    uniformtext_minsize=9,
    uniformtext_mode="hide",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
)


def layout(competition="LaLiga", season="2025-2026"):
    comp_opts = get_competition_options()
    all_comps = [c["value"] for c in comp_opts]

    return html.Div([
        html.Div([
            html.H4("Benchmarking", className="rm-page-title"),
            html.P("Cross-season and cross-competition performance comparison",
                   className="rm-page-subtitle"),
        ], className="rm-page-header"),

        # Competition selector — fully dynamic multi-select (any combination)
        dbc.Card(dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Compare Competitions (select any combination)",
                               className="filter-label"),
                    dcc.Dropdown(
                        id="bm-competitions",
                        options=comp_opts,
                        value=all_comps,          # all selectable; none forced-hidden
                        multi=True,
                        clearable=True,
                        placeholder="Select one or more competitions…",
                    ),
                ], md=12),
            ], className="g-2"),
        ), className="filter-section mb-4"),

        # Summary table
        html.P("Season KPI Summary", className="section-header"),
        dcc.Loading(html.Div(id="bm-summary-table"), type="circle", color=_RM),

        # Comparison charts
        dbc.Card([
            dbc.CardHeader("Goals For vs Against"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="bm-goals-chart", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Win % by Competition / Season"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="bm-win-chart", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("xG For vs xG Against"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="bm-xg-chart", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Pass Accuracy %"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="bm-pass-chart", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card(dbc.CardBody([
            html.P("RM vs League Average vs Rivals", className="section-header mb-2"),
            dbc.Row([
                dbc.Col([
                    html.Label("Competition", className="filter-label"),
                    dcc.Dropdown(id="bm-compare-competition",
                                 options=comp_opts,
                                 value=competition,
                                 clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("Season", className="filter-label"),
                    dcc.Dropdown(id="bm-compare-season",
                                 options=get_season_options(competition),
                                 value=season,
                                 clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("From Match", className="filter-label"),
                    dcc.Dropdown(id="bm-from-match", options=[], clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("To Match", className="filter-label"),
                    dcc.Dropdown(id="bm-to-match", options=[], clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("Rivals", className="filter-label"),
                    dcc.Dropdown(id="bm-rivals",
                                 options=[],  # populated from match data by _rivals_options
                                 value=["Barcelona", "Atlético de Madrid"],
                                 multi=True,
                                 clearable=True),
                ], md=4),
            ], className="g-2"),
        ]), className="filter-section mb-4"),

        dbc.Card([
            dbc.CardHeader("RM vs League Avg vs Rivals"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="bm-rivals-chart", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Tactical Metrics Comparison"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="bm-style-chart", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Core KPI Comparison"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="bm-phase-chart", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

    ], className="page-content")


# ── Helpers ────────────────────────────────────────────────────────────────

def _gather_season_data(competitions: list[str]) -> pd.DataFrame:
    """Collect season KPIs for all (competition, season) combinations."""
    rows = []
    for comp in competitions:
        for seas in get_competition_seasons(comp):
            try:
                kpis = calc_season_kpis(comp, seas)
                if kpis["played"] == 0:
                    continue
                row = {"Competition": comp, "Season": seas}
                row.update(kpis)
                rows.append(row)
            except Exception:
                continue
    return pd.DataFrame(rows)


def _overall_average(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="float64")
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return pd.Series(dtype="float64")
    return numeric.mean(numeric_only=True)


def _norm_team_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return (
        name.lower()
        .replace("cf", "")
        .replace("fc", "")
        .replace("club de futbol", "")
        .replace(" ", "")
        .replace("_", "")
    )


def _match_file_options(competition: str, season: str) -> list[dict]:
    matches = get_season_match_list(competition, season)
    opts = []
    for m in matches:
        venue = "H" if m.get("is_rm_home") else "A"
        week = m.get("week", "?")
        label = f"MD{week} · {venue} vs {m.get('opponent', 'OPP')} ({m.get('score_str', '-')})"
        opts.append({"label": label, "value": m["filepath"]})
    return opts


def _selected_file_set(competition: str, season: str, from_match: str | None, to_match: str | None) -> set[str]:
    opts = _match_file_options(competition, season)
    if not opts:
        return set()
    idx = {o["value"]: i for i, o in enumerate(opts)}
    i0 = idx.get(from_match, 0)
    i1 = idx.get(to_match, len(opts) - 1)
    lo, hi = (i0, i1) if i0 <= i1 else (i1, i0)
    return {o["value"] for o in opts[lo:hi + 1]}


def _league_team_table(competition: str, season: str, selected_files: set[str] | None = None) -> pd.DataFrame:
    rows = []
    for fp in iter_match_files(competition, season) or []:
        if selected_files is not None and str(fp) not in selected_files:
            continue
        data = load_match_json(str(fp))
        if not data:
            continue
        meta = extract_match_meta(data)
        events = parse_events(data)
        if events.empty:
            continue

        # Home perspective
        home_meta = {
            **meta,
            "rm_id": meta["home_id"],
            "opp_id": meta["away_id"],
            "rm_score": int(meta["score_str"].split("-")[0]) if "-" in meta["score_str"] else 0,
            "opp_score": int(meta["score_str"].split("-")[1]) if "-" in meta["score_str"] else 0,
        }
        hk = calc_match_kpis(events, home_meta)
        rows.append({
            "team": meta["home_team"],
            "goals_for": hk["goals_scored"],
            "goals_against": hk["goals_conceded"],
            "xg_for": hk["xg_for"],
            "pass_acc": hk["pass_accuracy"],
            "shots": hk["shots_total"],
            "ppda": hk["ppda"],
            "tackles": hk["tackles"],
            "recoveries": hk["ball_recoveries"],
            "points": 3 if hk["goals_scored"] > hk["goals_conceded"] else 1 if hk["goals_scored"] == hk["goals_conceded"] else 0,
        })

        # Away perspective
        away_meta = {
            **meta,
            "rm_id": meta["away_id"],
            "opp_id": meta["home_id"],
            "rm_score": int(meta["score_str"].split("-")[1]) if "-" in meta["score_str"] else 0,
            "opp_score": int(meta["score_str"].split("-")[0]) if "-" in meta["score_str"] else 0,
        }
        ak = calc_match_kpis(events, away_meta)
        rows.append({
            "team": meta["away_team"],
            "goals_for": ak["goals_scored"],
            "goals_against": ak["goals_conceded"],
            "xg_for": ak["xg_for"],
            "pass_acc": ak["pass_accuracy"],
            "shots": ak["shots_total"],
            "ppda": ak["ppda"],
            "tackles": ak["tackles"],
            "recoveries": ak["ball_recoveries"],
            "points": 3 if ak["goals_scored"] > ak["goals_conceded"] else 1 if ak["goals_scored"] == ak["goals_conceded"] else 0,
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    out = (
        df.groupby("team", as_index=False)
        .agg(
            played=("team", "count"),
            goals_for=("goals_for", "sum"),
            goals_against=("goals_against", "sum"),
            xg_for=("xg_for", "sum"),
            pass_acc=("pass_acc", "mean"),
            shots=("shots", "sum"),
            ppda=("ppda", "mean"),
            tackles=("tackles", "sum"),
            recoveries=("recoveries", "sum"),
            points=("points", "sum"),
        )
    )
    out["points_per_game"] = out["points"] / out["played"].clip(lower=1)
    out["goals_per_game"] = out["goals_for"] / out["played"].clip(lower=1)
    out["conceded_per_game"] = out["goals_against"] / out["played"].clip(lower=1)
    out["xg_per_game"] = out["xg_for"] / out["played"].clip(lower=1)
    out["shots_per_game"] = out["shots"] / out["played"].clip(lower=1)
    out["def_actions_pg"] = (out["tackles"] + out["recoveries"]) / out["played"].clip(lower=1)
    return out


@callback(
    Output("bm-summary-table", "children"),
    Input("bm-competitions", "value"),
)
def _summary_table(competitions):
    comps = competitions or []
    if not comps:
        return dbc.Alert("Select at least one competition above.", color="info")

    df = _gather_season_data(comps)
    if df.empty:
        return dbc.Alert("No data found for the selected competitions.", color="warning")

    cols_map = {
        "Competition": "Competition", "Season": "Season",
        "played": "MP", "wins": "W", "draws": "D", "losses": "L",
        "win_pct": "Win%", "goals_scored": "GF", "goals_conceded": "GA",
        "goal_diff": "GD", "goals_per_game": "G/G",
        "xg_for": "xG For", "xg_against": "xG vs",
        "avg_pass_acc": "Pass Acc%",
    }
    display = df[[c for c in cols_map if c in df.columns]].rename(columns=cols_map)

    avg = _overall_average(df)
    if not avg.empty:
        avg_row = {
            "Competition": "Overall",
            "Season": "Average",
            "MP": round(avg.get("played", 0), 1),
            "W": round(avg.get("wins", 0), 1),
            "D": round(avg.get("draws", 0), 1),
            "L": round(avg.get("losses", 0), 1),
            "Win%": round(avg.get("win_pct", 0), 1),
            "GF": round(avg.get("goals_scored", 0), 1),
            "GA": round(avg.get("goals_conceded", 0), 1),
            "GD": round(avg.get("goal_diff", 0), 1),
            "G/G": round(avg.get("goals_per_game", 0), 2),
            "xG For": round(avg.get("xg_for", 0), 2),
            "xG vs": round(avg.get("xg_against", 0), 2),
            "Pass Acc%": round(avg.get("avg_pass_acc", 0), 1),
        }
        display = pd.concat([display, pd.DataFrame([avg_row])], ignore_index=True)

    return dbc.Card(dbc.CardBody(
        dbc.Table(
            [html.Thead(html.Tr([html.Th(c) for c in display.columns])),
             html.Tbody([
                 html.Tr([html.Td(str(r[c])) for c in display.columns])
                 for _, r in display.iterrows()
             ])],
            striped=True, hover=True, responsive=True, size="sm",
            className="mb-0",
        )
    ))


def _bar_comparison(df, y_col, y_col2, title, y_label, y2_label=None):
    """Generic grouped bar chart for two metrics."""
    if df.empty:
        f = go.Figure()
        f.update_layout(**_PL, height=_H_CHART, title=title)
        return f

    labels = df["Competition"] + " " + df["Season"]
    avg = _overall_average(df)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=df[y_col], name=y_label,
        marker_color=_RM,
        text=df[y_col], textposition="auto",
    ))
    if y_col2 and y_col2 in df.columns:
        fig.add_trace(go.Bar(
            x=labels, y=df[y_col2], name=y2_label or y_col2,
            marker_color=_C["accent_red"], opacity=0.85,
            text=df[y_col2], textposition="auto",
        ))
    if y_col in avg.index:
        fig.add_hline(
            y=float(avg[y_col]),
            line=dict(color="#475569", dash="dot", width=1.5),
            annotation_text=f"Avg {y_label}: {avg[y_col]:.2f}",
            annotation_font_size=10,
        )
    if y_col2 and y_col2 in avg.index:
        fig.add_hline(
            y=float(avg[y_col2]),
            line=dict(color="#94a3b8", dash="dash", width=1.2),
            annotation_text=f"Avg {y2_label or y_col2}: {avg[y_col2]:.2f}",
            annotation_font_size=9,
        )
    fig.update_layout(**{**_PL, "margin": dict(l=60, r=30, t=60, b=110)},
                      height=_H_CHART, title=title, barmode="group",
                      xaxis=dict(tickangle=-35, gridcolor=_C["border"], automargin=True,
                                 tickfont=dict(size=11)),
                      yaxis=dict(gridcolor=_C["border"], automargin=True,
                                 tickfont=dict(size=11)))
    return fig


@callback(
    Output("bm-goals-chart", "figure"),
    Input("bm-competitions", "value"),
)
def _goals_chart(competitions):
    df = _gather_season_data(competitions or [])
    return _bar_comparison(df, "goals_scored", "goals_conceded",
                           "Goals For vs Against",
                           "Goals For", "Goals Against")


@callback(
    Output("bm-win-chart", "figure"),
    Input("bm-competitions", "value"),
)
def _win_chart(competitions):
    df = _gather_season_data(competitions or [])
    if df.empty:
        f = go.Figure()
        f.update_layout(**_PL, height=_H_CHART, title="Win %")
        return f

    labels = df["Competition"] + " " + df["Season"]
    win_pcts = df["win_pct"] if "win_pct" in df.columns else []
    avg = _overall_average(df)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=win_pcts, showlegend=False,
        marker_color=[
            _C["accent_green"] if v >= 60 else
            _C["accent_orange"] if v >= 45 else _C["accent_red"]
            for v in win_pcts
        ],
        text=[f"{v:.0f}%" for v in win_pcts], textposition="auto",
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="High (>=60%)",
        marker=dict(size=9, color=_C["accent_green"]), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Medium (45-59%)",
        marker=dict(size=9, color=_C["accent_orange"]), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Low (<45%)",
        marker=dict(size=9, color=_C["accent_red"]), hoverinfo="skip",
    ))
    fig.add_hline(y=50, line=dict(color="grey", dash="dot"),
                  annotation_text="50%", annotation_font_size=10)
    if "win_pct" in avg.index:
        fig.add_hline(
            y=float(avg["win_pct"]),
            line=dict(color="#475569", dash="dash", width=1.5),
            annotation_text=f"Overall Avg: {avg['win_pct']:.1f}%",
            annotation_font_size=10,
        )
    fig.update_layout(**{**_PL, "margin": dict(l=60, r=30, t=60, b=110)},
                      height=_H_CHART, title="Win Rate %",
                      xaxis=dict(tickangle=-35, gridcolor=_C["border"], automargin=True,
                                 tickfont=dict(size=11)),
                      yaxis=dict(range=[0, 105], gridcolor=_C["border"], automargin=True,
                                 tickfont=dict(size=11)),
                      showlegend=True)
    return fig


@callback(
    Output("bm-xg-chart", "figure"),
    Input("bm-competitions", "value"),
)
def _xg_chart(competitions):
    df = _gather_season_data(competitions or [])
    return _bar_comparison(df, "xg_for", "xg_against",
                           "xG For vs Against",
                           "xG For", "xG Against")


@callback(
    Output("bm-pass-chart", "figure"),
    Input("bm-competitions", "value"),
)
def _pass_chart(competitions):
    df = _gather_season_data(competitions or [])
    if df.empty:
        f = go.Figure()
        f.update_layout(**_PL, height=_H_CHART, title="Pass Accuracy")
        return f

    labels = df["Competition"] + " " + df["Season"]
    vals   = df["avg_pass_acc"] if "avg_pass_acc" in df.columns else []
    avg = _overall_average(df)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=vals, marker_color=_RM,
        text=[f"{v:.1f}%" for v in vals], textposition="auto",
    ))
    if "avg_pass_acc" in avg.index:
        fig.add_hline(
            y=float(avg["avg_pass_acc"]),
            line=dict(color="#475569", dash="dot", width=1.5),
            annotation_text=f"Overall Avg: {avg['avg_pass_acc']:.1f}%",
            annotation_font_size=10,
        )
    fig.update_layout(**_PL, height=_H_CHART, title="Average Pass Accuracy %",
                      xaxis=dict(tickangle=-30, ticklabelstep=2, gridcolor=_C["border"], automargin=True),
                      yaxis=dict(range=[70, 100], gridcolor=_C["border"], automargin=True),
                      showlegend=False)
    return fig


@callback(
    Output("bm-compare-season", "options"),
    Output("bm-compare-season", "value"),
    Input("bm-compare-competition", "value"),
    State("bm-compare-season", "value"),
)
def _compare_season_opts(competition, current):
    comp = competition or "LaLiga"
    opts = get_season_options(comp)
    vals = [o["value"] for o in opts]
    val = current if current in vals else (opts[0]["value"] if opts else "2025-2026")
    return opts, val


@callback(
    Output("bm-from-match", "options"),
    Output("bm-from-match", "value"),
    Output("bm-to-match", "options"),
    Output("bm-to-match", "value"),
    Input("bm-compare-competition", "value"),
    Input("bm-compare-season", "value"),
)
def _range_opts(competition, season):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"
    opts = _match_file_options(comp, seas)
    if not opts:
        return [], None, [], None
    return opts, opts[0]["value"], opts, opts[-1]["value"]


@callback(
    Output("bm-rivals", "options"),
    Input("bm-compare-competition", "value"),
    Input("bm-compare-season", "value"),
)
def _rivals_options(competition, season):
    # Derive rival options from the match data itself (teams RM faced) rather than
    # from equipos/ folders — so it works from the bundled, RM-only data on a fresh
    # clone instead of listing only Real Madrid.
    comp = competition or "LaLiga"
    seas = season or "2025-2026"
    team_df = _league_team_table(comp, seas)
    if team_df.empty:
        return []
    teams = sorted(t for t in team_df["team"].unique()
                   if "realmadrid" not in _norm_team_name(t))
    return [{"label": t, "value": t} for t in teams]


@callback(
    Output("bm-rivals-chart", "figure"),
    Output("bm-style-chart", "figure"),
    Output("bm-phase-chart", "figure"),
    Input("bm-compare-competition", "value"),
    Input("bm-compare-season", "value"),
    Input("bm-rivals", "value"),
    Input("bm-from-match", "value"),
    Input("bm-to-match", "value"),
)
def _rival_comparison(competition, season, rivals, from_match, to_match):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"
    rivals = rivals or []

    selected_files = _selected_file_set(comp, seas, from_match, to_match)
    team_df = _league_team_table(comp, seas, selected_files=selected_files)
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_CHART, title="No data")
    if team_df.empty:
        return empty, empty, empty

    rm_mask = team_df["team"].map(_norm_team_name).str.contains("realmadrid")
    if not rm_mask.any():
        return empty, empty, empty
    rm = team_df[rm_mask].iloc[0]

    league_avg = team_df.select_dtypes(include="number").mean()

    rival_rows = []
    norm_to_row = {_norm_team_name(r["team"]): r for _, r in team_df.iterrows()}
    for rv in rivals:
        n = _norm_team_name(rv)
        match_key = next((k for k in norm_to_row.keys() if n in k or k in n), None)
        if match_key:
            rival_rows.append(norm_to_row[match_key])

    labels = ["Real Madrid", "League Avg"] + [r["team"] for r in rival_rows]
    ppg = [rm["points_per_game"], league_avg.get("points_per_game", 0)] + [r["points_per_game"] for r in rival_rows]
    gpg = [rm["goals_per_game"], league_avg.get("goals_per_game", 0)] + [r["goals_per_game"] for r in rival_rows]
    xgpg = [rm["xg_per_game"], league_avg.get("xg_per_game", 0)] + [r["xg_per_game"] for r in rival_rows]
    pass_acc = [rm["pass_acc"], league_avg.get("pass_acc", 0)] + [r["pass_acc"] for r in rival_rows]

    fig_main = go.Figure()
    fig_main.add_trace(go.Bar(x=labels, y=ppg, name="Points/Game", marker_color=_RM))
    fig_main.add_trace(go.Bar(x=labels, y=gpg, name="Goals/Game", marker_color=_C["accent_green"]))
    fig_main.add_trace(go.Bar(x=labels, y=xgpg, name="xG/Game", marker_color=_C["accent_orange"]))
    fig_main.add_trace(go.Scatter(
        x=labels, y=pass_acc, mode="lines+markers", yaxis="y2",
        name="Pass Acc %", line=dict(color=_C["accent_red"], width=2),
    ))
    fig_main.update_layout(
        **_PL,
        height=_H_COMPARE,
        title=f"{comp} {seas} — RM vs League Avg vs Rivals",
        barmode="group",
        xaxis=dict(gridcolor=_C["border"], automargin=True),
        yaxis=dict(title="Rate", gridcolor=_C["border"], automargin=True),
        yaxis2=dict(title="Pass %", overlaying="y", side="right", showgrid=False, range=[65, 100], automargin=True),
    )

    # Tactical metrics comparison (raw event-derived rates)
    metric_labels = ["Pass Acc %", "PPDA", "Shots/Game", "Def Actions/Game", "xG/Game"]
    rm_metrics = [rm["pass_acc"], rm["ppda"], rm["shots_per_game"], rm["def_actions_pg"], rm["xg_per_game"]]
    lg_metrics = [
        league_avg.get("pass_acc", 0),
        league_avg.get("ppda", 0),
        league_avg.get("shots_per_game", 0),
        league_avg.get("def_actions_pg", 0),
        league_avg.get("xg_per_game", 0),
    ]
    radar = go.Figure()
    radar.add_trace(go.Bar(x=metric_labels, y=rm_metrics, name="Real Madrid", marker_color=_RM))
    radar.add_trace(go.Bar(x=metric_labels, y=lg_metrics, name="League Avg", marker_color="#64748b", opacity=0.8))
    if rival_rows:
        rv = rival_rows[0]
        rv_metrics = [rv["pass_acc"], rv["ppda"], rv["shots_per_game"], rv["def_actions_pg"], rv["xg_per_game"]]
        radar.add_trace(go.Bar(x=metric_labels, y=rv_metrics, name=rv["team"], marker_color=_C["accent_red"], opacity=0.75))
    radar.update_layout(
        **_PL,
        height=_H_COMPARE,
        title="Tactical Metrics Comparison (Raw Event-Derived)",
        barmode="group",
        xaxis=dict(gridcolor=_C["border"], tickangle=-15, automargin=True),
        yaxis=dict(gridcolor=_C["border"], automargin=True),
    )

    # Core KPI comparison chart
    phase_fig = go.Figure()
    phase_labels = ["Points/Game", "Goals/Game", "Conceded/Game", "xG/Game"]
    rm_phase = {
        "Points/Game": rm["points_per_game"],
        "Goals/Game": rm["goals_per_game"],
        "Conceded/Game": rm["conceded_per_game"],
        "xG/Game": rm["xg_per_game"],
    }
    lg_phase = {
        "Points/Game": league_avg.get("points_per_game", 0),
        "Goals/Game": league_avg.get("goals_per_game", 0),
        "Conceded/Game": league_avg.get("conceded_per_game", 0),
        "xG/Game": league_avg.get("xg_per_game", 0),
    }
    phase_fig.add_trace(go.Bar(
        x=phase_labels,
        y=[rm_phase[p] for p in phase_labels],
        name="Real Madrid",
        marker_color=_RM,
    ))
    phase_fig.add_trace(go.Bar(
        x=phase_labels,
        y=[lg_phase[p] for p in phase_labels],
        name="League Avg",
        marker_color="#64748b",
        opacity=0.8,
    ))
    if rival_rows:
        rv = rival_rows[0]
        rv_phase = {
            "Points/Game": rv["points_per_game"],
            "Goals/Game": rv["goals_per_game"],
            "Conceded/Game": rv["conceded_per_game"],
            "xG/Game": rv["xg_per_game"],
        }
        phase_fig.add_trace(go.Bar(
            x=phase_labels,
            y=[rv_phase[p] for p in phase_labels],
            name=rival_rows[0]["team"],
            marker_color=_C["accent_red"],
            opacity=0.75,
        ))
    phase_fig.update_layout(
        **_PL,
        height=_H_CHART,
        title="Core KPI Comparison (Raw Event-Derived)",
        barmode="group",
        xaxis=dict(
            gridcolor=_C["border"],
            categoryorder="array",
            categoryarray=phase_labels,
            tickmode="array",
            tickvals=phase_labels,
            ticktext=phase_labels,
            tickangle=0,
            automargin=True,
            tickfont=dict(size=10),
        ),
        yaxis=dict(title="Value", gridcolor=_C["border"], automargin=True),
    )

    return fig_main, radar, phase_fig
