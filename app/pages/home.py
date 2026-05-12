"""
Home Page — Dashboard Overview
Professional football analytics layout v2.0
"""

from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime

from config import COLOR_SCHEME
from utils.data_helpers import (
    get_competition_options,
    get_season_options,
    get_match_options,
    get_match_summary,
)

# ── PLOT DEFAULTS ──────────────────────────────────────────────────────────

_PL = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8fafc",
    font=dict(color="#0f172a", size=12),
    margin=dict(l=36, r=16, t=16, b=40),
    height=220,
    xaxis=dict(gridcolor="#e2e8f0", showline=False, zeroline=False),
    yaxis=dict(gridcolor="#e2e8f0", showline=False, zeroline=False),
    hovermode="x unified",
)

# ── LAYOUT ─────────────────────────────────────────────────────────────────

def layout():
    comp_opts     = get_competition_options()
    season_opts   = get_season_options("LaLiga")
    match_opts    = get_match_options("LaLiga", "2025-2026")
    default_match = match_opts[0]["value"] if match_opts else None

    return html.Div([

        # ── Page header ────────────────────────────────────────────────
        html.Div([
            html.H4("Season Overview", className="rm-page-title"),
            html.P("Select a competition and match to load full tactical analysis",
                   className="rm-page-subtitle"),
        ], className="rm-page-header"),

        # ── Match Selector (prominent) ─────────────────────────────────
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Competition", className="filter-label"),
                    dcc.Dropdown(
                        id="home-competition",
                        options=comp_opts,
                        value="LaLiga",
                        clearable=False,
                    ),
                ], md=2, sm=6),
                dbc.Col([
                    html.Label("Season", className="filter-label"),
                    dcc.Dropdown(
                        id="home-season",
                        options=season_opts,
                        value="2025-2026",
                        clearable=False,
                    ),
                ], md=2, sm=6),
                dbc.Col([
                    html.Label("Match", className="filter-label"),
                    dcc.Dropdown(
                        id="home-match",
                        options=match_opts,
                        value=default_match,
                        clearable=False,
                        placeholder="Choose a match…",
                    ),
                ], md=8),
            ], className="g-2"),
        ], className="filter-section"),

        # ── Filter context / summary ───────────────────────────────────
        dcc.Loading(html.Div(id="home-context-summary"), type="circle", color="#1d4ed8"),

        # ── Match summary (dynamic) ────────────────────────────────────
        dcc.Loading(html.Div(id="home-match-summary", className="mb-3"), type="circle", color="#1d4ed8"),

        # ── Season KPI cards ───────────────────────────────────────────
        html.P("Season at a Glance", className="section-header"),
        dcc.Loading(html.Div(id="home-kpi-row"), type="circle", color="#1d4ed8"),

        # ── Trend charts ───────────────────────────────────────────────
        html.P("Performance Trends", className="section-header"),
        dcc.Loading(html.Div(id="home-trend-row"), type="circle", color="#1d4ed8"),

        # ── Bottom row ─────────────────────────────────────────────────
        dbc.Row([
            dbc.Col(_recent_matches(), md=4),
            dbc.Col(_standings(),      md=4),
            dbc.Col(_tactical_id(),    md=4),
        ], className="g-3 mb-4"),

    ])


# ── KPI CARD ───────────────────────────────────────────────────────────────

def _kpi(title, value, color, sub=""):
    return dbc.Col(
        html.Div([
            html.P(title, className="kpi-label"),
            html.Div(value, className="kpi-val", style={"color": color}),
            html.P(sub, className="kpi-sub") if sub else None,
        ], className="rm-kpi-card", style={"--kpi-accent": color}),
        lg=2, md=4, sm=6,
    )


def _load_season_summaries(competition, season):
    match_opts = get_match_options(competition or "LaLiga", season or "2025-2026")
    summaries = []
    for opt in match_opts:
        summary = get_match_summary(opt["value"])
        if summary:
            summaries.append(summary)
    summaries.sort(key=lambda item: item.get("week") or 0)
    return summaries


def _season_kpis(competition, season):
    matches = _load_season_summaries(competition, season)
    if not matches:
        return [
            _kpi("Matches", "0", "#1d4ed8", "No match data"),
            _kpi("Goals Scored", "—", "#059669"),
            _kpi("Goals Conceded", "—", "#dc2626"),
            _kpi("Goal Diff", "—", "#1d4ed8"),
            _kpi("Points", "—", "#d97706"),
            _kpi("Win Rate", "—", "#7c3aed"),
        ]

    goals_for = 0
    goals_against = 0
    wins = draws = losses = 0
    points = 0
    for match in matches:
        home = match.get("home", "")
        away = match.get("away", "")
        hs = int(match.get("home_score") or 0)
        as_ = int(match.get("away_score") or 0)
        rm_home = "Real Madrid" in home
        rm_score = hs if rm_home else as_
        opp_score = as_ if rm_home else hs
        goals_for += rm_score
        goals_against += opp_score
        if rm_score > opp_score:
            wins += 1
            points += 3
        elif rm_score == opp_score:
            draws += 1
            points += 1
        else:
            losses += 1

    total = len(matches)
    win_rate = round((wins / total) * 100, 1) if total else 0
    goal_diff = goals_for - goals_against
    date_start = matches[0].get("date", "")
    date_end = matches[-1].get("date", "")
    context = f"{competition or 'LaLiga'} {season or '2025-2026'} | {total} matches"
    if date_start and date_end:
        context += f" | {date_start} to {date_end}"

    return [
        _kpi("Matches", total, "#1d4ed8", context),
        _kpi("Goals Scored", goals_for, "#059669", f"{wins}W {draws}D {losses}L"),
        _kpi("Goals Conceded", goals_against, "#dc2626", f"Average {round(goals_against / total, 2)} per match" if total else ""),
        _kpi("Goal Diff", f"+{goal_diff}" if goal_diff >= 0 else str(goal_diff), "#1d4ed8", "Season aggregate"),
        _kpi("Points", points, "#d97706", f"{points / total:.2f} per match" if total else ""),
        _kpi("Win Rate", f"{win_rate}%", "#7c3aed", "Season win percentage"),
    ]


def _trend_cards(competition, season):
    matches = _load_season_summaries(competition, season)
    if not matches:
        empty = dbc.Alert("No season data found for the selected competition and season.", color="warning")
        return [dbc.Col(dbc.Card(dbc.CardBody([empty])), md=12)]

    weeks = []
    goals_for = []
    goal_diff = []
    points = []
    cumulative_points = []
    running_points = 0
    for match in matches:
        week = f"MD{match.get('week')}"
        home = match.get("home", "")
        hs = int(match.get("home_score") or 0)
        as_ = int(match.get("away_score") or 0)
        rm_home = "Real Madrid" in home
        rm_score = hs if rm_home else as_
        opp_score = as_ if rm_home else hs
        if rm_score > opp_score:
            match_points = 3
        elif rm_score == opp_score:
            match_points = 1
        else:
            match_points = 0
        running_points += match_points
        weeks.append(week)
        goals_for.append(rm_score)
        goal_diff.append(rm_score - opp_score)
        points.append(match_points)
        cumulative_points.append(running_points)

    goals_fig = go.Figure(
        go.Bar(x=weeks, y=goals_for, marker_color="#059669",
               hovertemplate="%{x}: %{y} goals<extra></extra>")
    )
    goals_fig.update_layout(**_PL, title=dict(text="Goals Scored by Matchday", font=dict(size=12, color="#475569")))

    diff_fig = go.Figure(
        go.Scatter(x=weeks, y=goal_diff, mode="lines+markers",
                   line=dict(color="#1d4ed8", width=2.5),
                   marker=dict(size=7, color="#1d4ed8"),
                   fill="tozeroy", fillcolor="rgba(29,78,216,0.08)",
                   hovertemplate="%{x}: goal diff %{y}<extra></extra>")
    )
    diff_fig.update_layout(**_PL, title=dict(text="Goal Difference Trend", font=dict(size=12, color="#475569")))

    points_fig = go.Figure(
        go.Scatter(x=weeks, y=cumulative_points, mode="lines+markers",
                   line=dict(color="#7c3aed", width=2.5),
                   marker=dict(size=7, color="#7c3aed"),
                   hovertemplate="%{x}: cumulative points %{y}<extra></extra>")
    )
    points_fig.update_layout(**_PL, title=dict(text="Cumulative Points", font=dict(size=12, color="#475569")))

    return [
        dbc.Col(_card("Goals per Matchday", dcc.Graph(figure=goals_fig, config={"displayModeBar": False, "responsive": True})), md=4),
        dbc.Col(_card("Goal Difference", dcc.Graph(figure=diff_fig, config={"displayModeBar": False, "responsive": True})), md=4),
        dbc.Col(_card("Cumulative Points", dcc.Graph(figure=points_fig, config={"displayModeBar": False, "responsive": True})), md=4),
    ]


# ── CHART HELPERS ──────────────────────────────────────────────────────────

def _chart_goals():
    mds  = [f"MD{i}" for i in range(20, 26)]
    vals = [1, 2, 3, 1, 2, 2]
    fig  = go.Figure(
        go.Bar(x=mds, y=vals,
               marker_color="#059669",
               hovertemplate="%{x}: %{y} goals<extra></extra>"),
        layout=go.Layout(**_PL, title=dict(text="Goals per Matchday", font=dict(size=12, color="#475569"))),
    )
    return _card("Goals per Matchday", dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True}))


def _chart_xg():
    mds  = [f"MD{i}" for i in range(20, 26)]
    vals = [2.1, 2.8, 1.5, 2.3, 3.2, 2.6]
    fig  = go.Figure(
        go.Scatter(x=mds, y=vals, mode="lines+markers",
                   line=dict(color="#1d4ed8", width=2.5),
                   marker=dict(size=7, color="#1d4ed8"),
                   fill="tozeroy", fillcolor="rgba(29,78,216,0.08)",
                   hovertemplate="%{x}: xG %{y:.2f}<extra></extra>"),
        layout=go.Layout(**_PL),
    )
    return _card("xG per Matchday", dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True}))


def _chart_poss():
    mds  = [f"MD{i}" for i in range(20, 26)]
    vals = [58, 62, 61, 59, 64, 61]
    fig  = go.Figure(
        go.Scatter(x=mds, y=vals, mode="lines+markers",
                   line=dict(color="#7c3aed", width=2.5),
                   marker=dict(size=7, color="#7c3aed"),
                   fill="tozeroy", fillcolor="rgba(124,58,237,0.08)",
                   hovertemplate="%{x}: %{y}% possession<extra></extra>"),
        layout=go.Layout(**{**_PL, "yaxis": dict(gridcolor="#e2e8f0", range=[40, 80])}),
    )
    return _card("Possession % Trend", dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True}))


def _card(title, content):
    return dbc.Card(dbc.CardBody([
        html.H6(title, className="card-title"),
        content,
    ]))


# ── TABLE CARDS ────────────────────────────────────────────────────────────

def _recent_matches():
    rows = [
        ("26", "2026-03-01", "Betis",          "3-0", "W"),
        ("25", "2026-02-22", "Girona",          "2-1", "W"),
        ("24", "2026-02-15", "Barcelona",       "2-0", "W"),
        ("23", "2026-02-08", "Valencia",        "1-1", "D"),
        ("22", "2026-02-01", "Real Sociedad",   "3-1", "W"),
    ]
    def badge(r):
        color = "success" if r == "W" else "warning" if r == "D" else "danger"
        return dbc.Badge(r, color=color, style={"minWidth": "26px", "textAlign": "center"})

    return dbc.Card(dbc.CardBody([
        html.H6("Recent Matches", className="card-title"),
        html.Table([
            html.Thead(html.Tr([
                html.Th("MD", style={"width": "36px"}),
                html.Th("Opponent"),
                html.Th("Score"),
                html.Th(""),
            ])),
            html.Tbody([html.Tr([
                html.Td(md, className="text-xs text-muted"),
                html.Td(opp, style={"fontWeight": 500}),
                html.Td(html.Strong(sc)),
                html.Td(badge(r)),
            ]) for md, _, opp, sc, r in rows]),
        ], className="table table-sm w-100 mb-0"),
    ]))


def _standings():
    data = [
        ("1", "Real Madrid",     "62", True),
        ("2", "Barcelona",       "54", False),
        ("3", "Atlético Madrid", "52", False),
        ("4", "Real Sociedad",   "47", False),
        ("5", "Athletic Club",   "44", False),
    ]
    return dbc.Card(dbc.CardBody([
        html.H6("LaLiga Standings", className="card-title"),
        html.Table([
            html.Thead(html.Tr([html.Th("#"), html.Th("Team"), html.Th("Pts")])),
            html.Tbody([html.Tr([
                html.Td(html.Strong(pos)),
                html.Td(html.Strong(team, style={"color": "#1d4ed8"}) if hi else team),
                html.Td(html.Strong(pts, style={"color": "#1d4ed8"}) if hi else pts),
            ], style={"backgroundColor": "#eff6ff" if hi else "transparent"})
            for pos, team, pts, hi in data]),
        ], className="table table-sm w-100 mb-0"),
    ]))


def _tactical_id():
    items = [
        ("Formation",       "4-3-3",       "#1d4ed8"),
        ("Press Style",     "High Press",  "#059669"),
        ("Build-Up",        "Short Pass",  "#1d4ed8"),
        ("Attack Style",    "Positional",  "#ea580c"),
        ("PPDA",            "3.8",         "#dc2626"),
        ("Avg Possession",  "61.5%",       "#7c3aed"),
    ]
    rows = []
    for label, value, color in items:
        rows.append(
            dbc.Row([
                dbc.Col(html.Span(label, className="text-xs text-muted"), width=7),
                dbc.Col(html.Span(value, className="fw-700 text-xs",
                                  style={"color": color}), width=5, className="text-end"),
            ], className="mb-1 align-items-center")
        )
    return dbc.Card(dbc.CardBody([
        html.H6("Tactical Identity", className="card-title"),
        *rows,
    ]))


# ── CALLBACKS ──────────────────────────────────────────────────────────────

@callback(
    Output("home-context-summary", "children"),
    Output("home-kpi-row", "children"),
    Output("home-trend-row", "children"),
    Input("home-competition", "value"),
    Input("home-season", "value"),
)
def update_home_overview(competition, season):
    try:
        competition = competition or "LaLiga"
        season = season or "2025-2026"
        
        context = dbc.Card(dbc.CardBody([
            html.Div([
                html.Span("Currently Viewing", className="rm-badge rm-badge-blue me-2"),
                html.Span(f"{competition} {season}", className="rm-badge rm-badge-green me-2"),
                html.Span("Season-level view", className="text-xs text-muted"),
            ], className="d-flex flex-wrap align-items-center gap-2"),
        ]), className="mb-3")
        
        kpi_cards = html.Div(_season_kpis(competition, season), className="row g-2")
        trend_charts = html.Div(_trend_cards(competition, season), className="row g-2")
        
        return context, kpi_cards, trend_charts
    except Exception as e:
        return html.Div(f"ERROR: {str(e)}"), html.Div("ERROR"), html.Div("ERROR")


@callback(
    Output("home-season", "options"),
    Output("home-season", "value"),
    Input("home-competition", "value"),
)
def update_home_season(competition):
    opts = get_season_options(competition or "LaLiga")
    return opts, (opts[0]["value"] if opts else "2025-2026")


@callback(
    Output("home-match", "options"),
    Output("home-match", "value"),
    Input("home-competition", "value"),
    Input("home-season",      "value"),
)
def update_home_matches(competition, season):
    opts = get_match_options(competition or "LaLiga", season or "2025-2026")
    return opts, (opts[0]["value"] if opts else None)


@callback(
    Output("home-match-summary", "children"),
    Input("home-match", "value"),
)
def update_home_summary(file_path):
    if not file_path:
        return dbc.Alert(
            [html.Strong("Select a match"), " above to view match details and score."],
            color="info", className="mb-0",
        )
    s = get_match_summary(file_path)
    if not s:
        return dbc.Alert("Could not load match data.", color="warning", className="mb-0")

    home, away = s["home"], s["away"]
    hs, as_    = s["home_score"], s["away_score"]
    rm_home    = "Real Madrid" in home
    rm_score   = hs if rm_home else as_
    opp_score  = as_ if rm_home else hs

    if rm_score > opp_score:
        accent, badge_cls, result = "#059669", "rm-result-win",  "WIN"
    elif rm_score == opp_score:
        accent, badge_cls, result = "#d97706", "rm-result-draw", "DRAW"
    else:
        accent, badge_cls, result = "#dc2626", "rm-result-loss", "LOSS"

    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div(home, className="rm-match-team text-end"),
                html.Div("Home", className="text-xs text-muted text-end mt-1"),
            ], md=4, className="d-flex flex-column justify-content-center align-items-end"),

            dbc.Col([
                html.Div(f"{hs} – {as_}",
                         className="rm-match-score text-center",
                         style={"color": accent}),
                html.Div([
                    html.Span(result, className=f"rm-result-badge {badge_cls}"),
                ], className="text-center my-1"),
                html.P(
                    f"Matchday {s.get('week','')}  ·  {s.get('date','')}  ·  "
                    f"HT: {s['ht_home']}–{s['ht_away']}  ·  {s.get('venue_name','')}",
                    className="text-xs text-muted text-center mb-0",
                ),
            ], md=4, className="d-flex flex-column justify-content-center"),

            dbc.Col([
                html.Div(away, className="rm-match-team"),
                html.Div("Away", className="text-xs text-muted mt-1"),
            ], md=4, className="d-flex flex-column justify-content-center"),
        ], align="center"),
    ], className="rm-match-card mb-3", style={"borderLeft": f"5px solid {accent}"})
