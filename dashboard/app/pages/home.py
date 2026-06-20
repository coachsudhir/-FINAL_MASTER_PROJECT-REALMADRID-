"""
Home Page — Season Overview
Real Madrid Tactical Dashboard — dynamic KPIs from Opta event data.
"""

from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from config import COLOR_SCHEME
from utils.data_helpers import get_competition_options, get_season_options
from utils.data_loader import (
    calc_season_kpis,
    get_season_results_table,
    get_season_match_list,
    load_match_json,
    extract_match_meta,
    parse_events,
    calc_match_kpis,
)

_C   = COLOR_SCHEME
_RM  = _C["accent_blue"]
_H_CHART = 400
_PL  = dict(
    paper_bgcolor=_C["surface"],
    plot_bgcolor=_C["surface"],
    font=dict(color=_C["text_primary"], size=11),
    margin=dict(l=48, r=28, t=56, b=56),
    hovermode="x unified",
    uniformtext_minsize=9,
    uniformtext_mode="hide",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
)


def _stat_card(title, value, color=None, sub=None, icon=""):
    color = color or _RM
    body  = [
        html.P(f"{icon} {title}".strip(), className="kpi-title"),
        html.Div(str(value), className="kpi-value", style={"color": color}),
    ]
    if sub:
        body.append(html.P(sub, className="text-muted",
                           style={"fontSize": "0.72rem", "marginBottom": 0}))
    return dbc.Col(
        dbc.Card(dbc.CardBody(body), className="kpi-card h-100"),
        lg=2, md=4, sm=6, xs=12, className="mb-2",
    )


def _compact_match_label(week, opponent):
    token = str(opponent or "OPP").replace("_", " ").split()[0]
    short = token[:3].upper() if token else "OPP"
    return f"MD{week if week is not None else '?'} {short}"


# ============================================================================
# LAYOUT
# ============================================================================

def layout(competition="LaLiga", season="2025-2026"):
    comp_opts   = get_competition_options()
    season_opts = get_season_options(competition)

    return html.Div([
        html.Div([
            html.H4("Season Overview", className="rm-page-title"),
            html.P("Aggregated season KPIs and results — powered by real Opta match data",
                   className="rm-page-subtitle"),
        ], className="rm-page-header"),

        # Filters
        dbc.Card(dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Competition", className="filter-label"),
                    dcc.Dropdown(id="home-competition",
                                 options=comp_opts,
                                 value=competition, clearable=False),
                ], md=3, sm=6),
                dbc.Col([
                    html.Label("Season", className="filter-label"),
                    dcc.Dropdown(id="home-season",
                                 options=season_opts,
                                 value=season, clearable=False),
                ], md=3, sm=6),
            ], className="g-2"),
        ), className="filter-section mb-4"),

        # Season record badge
        dcc.Loading(html.Div(id="home-record-badge", className="mb-3"),
                    type="circle", color=_RM),

        # KPI cards — goals / xG / possession
        html.P("Season Statistics", className="section-header"),
        dcc.Loading(dbc.Row(id="home-kpi-row", className="g-2 mb-4"),
                    type="circle", color=_RM),

        # Results trend charts
        html.P("Performance Trends", className="section-header"),
        dbc.Card([
            dbc.CardHeader("Goals Per Match"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="home-goals-trend",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),
        dbc.Card([
            dbc.CardHeader("Shots & Pass Accuracy Trend"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="home-shots-trend",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Match results table
        html.P("All Matches", className="section-header"),
        dcc.Loading(html.Div(id="home-results-table"), type="circle", color=_RM),

    ], className="page-content")


# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output("home-season", "options"),
    Output("home-season", "value"),
    Input("home-competition", "value"),
    State("home-season", "value"),
)
def _update_season_opts(competition, current):
    comp = competition or "LaLiga"
    opts = get_season_options(comp)
    vals = [o["value"] for o in opts]
    # Preserve the current (e.g. globally-seeded) season if still valid,
    # so changing season actually reflects instead of snapping to newest.
    val  = current if current in vals else (opts[0]["value"] if opts else "2025-2026")
    return opts, val


@callback(
    Output("home-record-badge", "children"),
    Output("home-kpi-row", "children"),
    Input("home-competition", "value"),
    Input("home-season", "value"),
)
def _update_kpis(competition, season):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"

    kpis = calc_season_kpis(comp, seas)

    # Record badge
    w, d, l = kpis["wins"], kpis["draws"], kpis["losses"]
    badge = dbc.Card(dbc.CardBody(dbc.Row([
        dbc.Col([
            html.H5(f"Real Madrid — {comp} {seas}", className="mb-0"),
            html.Small(f"Matchday record: {w}W {d}D {l}L", className="text-muted"),
        ], xs=8),
        dbc.Col([
            dbc.Badge(f"{kpis['win_pct']}% Win Rate", color="primary",
                      className="me-2"),
            dbc.Badge(f"+{kpis['goal_diff']} GD",
                      color="success" if kpis["goal_diff"] >= 0 else "danger"),
        ], xs=4, className="d-flex align-items-center justify-content-end"),
    ], align="center")), className="mb-1")

    # KPI grid
    kpi_cards = [
        _stat_card("Matches Played",  kpis["played"],             _C["text_secondary"]),
        _stat_card("Goals Scored",    kpis["goals_scored"],       _C["accent_green"],
                   sub=f"{kpis['goals_per_game']} per game"),
        _stat_card("Goals Conceded",  kpis["goals_conceded"],     _C["accent_red"],
                   sub=f"{kpis['conceded_per_game']} per game"),
        _stat_card("xG For",          kpis["xg_for"],             _C["accent_blue"],
                   sub=f"xG diff: {kpis['xg_diff']:+.2f}"),
        _stat_card("xG Against",      kpis["xg_against"],         _C["accent_orange"]),
        _stat_card("Avg Pass Acc.",   f"{kpis['avg_pass_acc']}%", _C["accent_purple"],
                   sub=f"{kpis['shots_total']} shots total"),
    ]
    return badge, kpi_cards


@callback(
    Output("home-goals-trend", "figure"),
    Input("home-competition", "value"),
    Input("home-season", "value"),
)
def _goals_trend(competition, season):
    comp  = competition or "LaLiga"
    seas  = season or "2025-2026"
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_CHART, title="Goals per Match")

    matches = get_season_match_list(comp, seas)
    if not matches:
        return empty

    scored    = [m["rm_score"]  for m in matches]
    conceded  = [m["opp_score"] for m in matches]
    labels    = [_compact_match_label(m.get("week", "?"), m.get("opponent", "OPP")) for m in matches]
    result_colors = [
        _C["accent_green"]  if m["result"] == "W" else
        _C["accent_yellow"] if m["result"] == "D" else
        _C["accent_red"]
        for m in matches
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=scored, name="Goals Scored",
        marker_color=result_colors,
        text=scored, textposition="auto",
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=conceded, name="Goals Conceded",
        line=dict(color=_C["accent_red"], width=2, dash="dot"),
        mode="lines+markers",
        marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Win (W)",
        marker=dict(size=9, color=_C["accent_green"]), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Draw (D)",
        marker=dict(size=9, color=_C["accent_yellow"]), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Loss (L)",
        marker=dict(size=9, color=_C["accent_red"]), hoverinfo="skip",
    ))
    fig.update_layout(**_PL, height=_H_CHART,
                      title="Goals Scored (bar) vs Conceded (line)",
                      xaxis=dict(tickangle=-45, ticklabelstep=2, gridcolor=_C["border"], automargin=True),
                      yaxis=dict(gridcolor=_C["border"], automargin=True),
                      showlegend=True)
    return fig


@callback(
    Output("home-shots-trend", "figure"),
    Input("home-competition", "value"),
    Input("home-season", "value"),
)
def _shots_trend(competition, season):
    comp  = competition or "LaLiga"
    seas  = season or "2025-2026"
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_CHART, title="Shots & Pass Accuracy")

    matches = get_season_match_list(comp, seas)
    if not matches:
        return empty

    shots_list    = []
    pass_acc_list = []
    labels        = []

    for m in matches:
        try:
            data   = load_match_json(m["filepath"])
            events = parse_events(data)
            kpis   = calc_match_kpis(events, m)
            shots_list.append(kpis["shots_total"])
            pass_acc_list.append(kpis["pass_accuracy"])
            labels.append(_compact_match_label(m.get("week", "?"), m.get("opponent", "OPP")))
        except Exception:
            shots_list.append(0)
            pass_acc_list.append(0)
            labels.append(f"MD?")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=shots_list, name="Total Shots",
        marker_color=_RM, opacity=0.75,
        text=shots_list, textposition="auto",
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=pass_acc_list, name="Pass Accuracy %",
        yaxis="y2", line=dict(color=_C["accent_green"], width=2),
        mode="lines+markers", marker=dict(size=5),
    ))
    fig.update_layout(
        **_PL, height=_H_CHART,
        title="Shots (bar) & Pass Accuracy % (line)",
        xaxis=dict(tickangle=-45, ticklabelstep=2, gridcolor=_C["border"], automargin=True),
        yaxis=dict(title="Shots", gridcolor=_C["border"], automargin=True),
        yaxis2=dict(title="Pass Acc %", overlaying="y", side="right",
                    range=[70, 100], showgrid=False, automargin=True),
    )
    return fig


@callback(
    Output("home-results-table", "children"),
    Input("home-competition", "value"),
    Input("home-season", "value"),
)
def _results_table(competition, season):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"

    df = get_season_results_table(comp, seas)
    if df.empty:
        return dbc.Alert(f"No matches found for {comp} {seas}.", color="info")

    result_badge = {
        "W": dbc.Badge("W", color="success"),
        "D": dbc.Badge("D", color="warning"),
        "L": dbc.Badge("L", color="danger"),
    }

    rows = []
    for _, r in df.iterrows():
        rows.append(html.Tr([
            html.Td(str(r["MD"])),
            html.Td(r["Date"]),
            html.Td(r["Venue"]),
            html.Td(r["Opponent"]),
            html.Td(r["Score"], style={"fontWeight": "bold"}),
            html.Td(result_badge.get(r["Result"], r["Result"])),
        ]))

    return dbc.Card(dbc.CardBody(
        dbc.Table(
            [html.Thead(html.Tr([
                html.Th("MD"), html.Th("Date"), html.Th("Venue"),
                html.Th("Opponent"), html.Th("Score"), html.Th("Result"),
            ])),
             html.Tbody(rows)],
            striped=True, hover=True, responsive=True, size="sm",
            className="mb-0",
        )
    ))
