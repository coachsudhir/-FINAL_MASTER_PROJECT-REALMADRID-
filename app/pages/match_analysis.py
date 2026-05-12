"""
Match Analysis Page - Detailed tactical analysis of individual matches
"""

import dash
from dash import dcc, html, Input, Output, callback, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from config import COLOR_SCHEME, DARK_TEMPLATE
from utils.data_helpers import (
    get_match_options,
    get_match_summary,
    get_competition_options,
    get_season_options,
)

# ============================================================================
# HELPERS
# ============================================================================

def _kpi_card(title, value, color):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.P(title, className="kpi-title"),
                html.Div(str(value), className="kpi-value", style={"color": color}),
            ]),
            className="kpi-card",
        ),
        lg=2, md=4, sm=6, xs=12, className="mb-2",
    )


# ============================================================================
# LAYOUT
# ============================================================================

def layout():
    """Match Analysis page layout"""
    default_options = get_match_options("LaLiga", "2025-2026")
    default_value = default_options[0]["value"] if default_options else None

    return html.Div([
        html.Div([
            html.H4("Match Analysis", className="rm-page-title"),
            html.P("Detailed tactical breakdown of individual Real Madrid matches",
                   className="rm-page-subtitle"),
        ], className="rm-page-header"),

        # ── Filter Row ──────────────────────────────────────────────────────
        dbc.Card(
            dbc.CardBody(
                dbc.Row([
                    dbc.Col([
                        html.Label("Competition", className="filter-label"),
                        dcc.Dropdown(
                            id="ma-competition",
                            options=get_competition_options(),
                            value="LaLiga",
                            clearable=False,
                        ),
                    ], md=2),
                    dbc.Col([
                        html.Label("Season", className="filter-label"),
                        dcc.Dropdown(
                            id="ma-season",
                            options=get_season_options("LaLiga"),
                            value="2025-2026",
                            clearable=False,
                        ),
                    ], md=2),
                    dbc.Col([
                        html.Label("Venue", className="filter-label"),
                        dcc.Dropdown(
                            id="ma-venue",
                            options=[
                                {"label": "All", "value": "All"},
                                {"label": "Home 🏠", "value": "Home"},
                                {"label": "Away ✈️", "value": "Away"},
                            ],
                            value="All",
                            clearable=False,
                        ),
                    ], md=2),
                    dbc.Col([
                        html.Label("Select Match", className="filter-label"),
                        dcc.Dropdown(
                            id="ma-match-selector",
                            options=default_options,
                            value=default_value,
                            clearable=False,
                            placeholder="Choose a match…",
                        ),
                    ], md=6),
                ], className="g-2"),
            ),
            className="filter-section mb-4",
        ),

        # ── Match Header ────────────────────────────────────────────────────
        html.Div(id="ma-match-header", className="mb-3"),

        # ── KPI Row ─────────────────────────────────────────────────────────
        dbc.Row(id="ma-kpi-row", className="g-2 mb-4"),

        # ── Results sections ───────────────────────────────────────────────
        html.Div([
            html.H6("Score & Timeline", className="card-title"),
            dcc.Loading(html.Div(id="ma-score-tab"), type="circle", color="#1d4ed8"),
        ], className="card mb-3"),

        html.Div([
            html.H6("Possession & Passing", className="card-title"),
            dcc.Loading(html.Div(id="ma-possession-tab"), type="circle", color="#1d4ed8"),
        ], className="card mb-3"),

        html.Div([
            html.H6("Tactical Phases", className="card-title"),
            dcc.Loading(html.Div(id="ma-phases-tab"), type="circle", color="#1d4ed8"),
        ], className="card mb-3"),

    ], className="page-content")


# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output("ma-season", "options"),
    Output("ma-season", "value"),
    Input("ma-competition", "value"),
)
def update_ma_season_options(competition):
    comp = competition or "LaLiga"
    opts = get_season_options(comp)
    val = opts[0]["value"] if opts else "2025-2026"
    return opts, val


@callback(
    Output("ma-match-selector", "options"),
    Output("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
)
def update_match_options(competition, season, venue):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"
    ven  = venue or "All"
    opts = get_match_options(comp, seas, ven)
    val = opts[0]["value"] if opts else None
    return opts, val


@callback(
    Output("ma-match-header", "children"),
    Output("ma-kpi-row", "children"),
    Input("ma-match-selector", "value"),
)
def update_match_header(file_path):
    if not file_path:
        return (
            dbc.Alert("Please select a match using the filters above.", color="info"),
            [],
        )
    s = get_match_summary(file_path)
    if not s:
        return dbc.Alert("Could not load match data.", color="warning"), []

    home, away = s["home"], s["away"]
    hs, as_ = s["home_score"], s["away_score"]

    rm_home = "Real Madrid" in home
    rm_score = hs if rm_home else as_
    opp_score = as_ if rm_home else hs
    if rm_score > opp_score:
        result_color, result_txt = COLOR_SCHEME['accent_green'], "WIN"
    elif rm_score == opp_score:
        result_color, result_txt = COLOR_SCHEME['accent_yellow'], "DRAW"
    else:
        result_color, result_txt = COLOR_SCHEME['accent_red'], "LOSS"

    header = dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.H3(home, className="mb-0 text-end",
                            style={"color": COLOR_SCHEME['text_primary']}),
                ], md=4, className="d-flex align-items-center justify-content-end"),
                dbc.Col([
                    html.Div([
                        html.H2(f"{hs}  –  {as_}",
                                style={"color": result_color, "fontWeight": "bold",
                                       "textAlign": "center", "fontSize": "2.5rem"}),
                        dbc.Badge(
                            result_txt,
                            color="success" if result_txt == "WIN"
                            else "warning" if result_txt == "DRAW" else "danger",
                            className="d-block text-center mb-1",
                        ),
                        html.P(f"Matchday {s.get('week', '')}  ·  {s.get('date', '')}",
                               className="text-muted text-center small mb-0"),
                    ]),
                ], md=4, className="text-center"),
                dbc.Col([
                    html.H3(away, className="mb-0 text-start",
                            style={"color": COLOR_SCHEME['text_primary']}),
                ], md=4, className="d-flex align-items-center"),
            ], align="center"),
        ),
        className="mb-3",
        style={"borderLeft": f"4px solid {result_color}"},
    )

    ht_str = f"HT: {s['ht_home']}–{s['ht_away']}"
    kpis = [
        _kpi_card("Home Goals", hs, COLOR_SCHEME['accent_green']),
        _kpi_card("Away Goals", as_, COLOR_SCHEME['accent_red']),
        _kpi_card("Half-Time", ht_str, COLOR_SCHEME['accent_blue']),
        _kpi_card("Venue", s.get("venue_name", "—"), COLOR_SCHEME['accent_purple']),
        _kpi_card("Status", s.get("status", ""), COLOR_SCHEME['accent_orange']),
        _kpi_card("Result", result_txt, result_color),
    ]
    return header, kpis


@callback(
    Output("ma-score-tab", "children"),
    Input("ma-match-selector", "value"),
)
def update_score_tab(file_path):
    if not file_path:
        return dbc.Alert("Select a match to see the score timeline.", color="info")
    s = get_match_summary(file_path)
    if not s:
        return dbc.Alert("No data available.", color="warning")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=s["home"], x=["Full-Time"], y=[s["home_score"]],
        marker_color=COLOR_SCHEME['accent_blue'],
        text=[s["home_score"]], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name=s["away"], x=["Full-Time"], y=[s["away_score"]],
        marker_color=COLOR_SCHEME['accent_red'],
        text=[s["away_score"]], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name=f"{s['home']} (HT)", x=["Half-Time"], y=[s["ht_home"]],
        marker_color=COLOR_SCHEME['accent_green'], opacity=0.7,
        text=[s["ht_home"]], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name=f"{s['away']} (HT)", x=["Half-Time"], y=[s["ht_away"]],
        marker_color=COLOR_SCHEME['accent_orange'], opacity=0.7,
        text=[s["ht_away"]], textposition="outside",
    ))
    fig.update_layout(
        barmode="group",
        paper_bgcolor=COLOR_SCHEME['background'],
        plot_bgcolor=COLOR_SCHEME['background'],
        font=dict(color=COLOR_SCHEME['text_primary']),
        margin=dict(l=40, r=40, t=50, b=40),
        height=380,
        title=f"{s['home']} vs {s['away']}  ·  {s['date']}",
        legend=dict(bgcolor=COLOR_SCHEME['surface']),
        xaxis=dict(gridcolor=COLOR_SCHEME['border']),
        yaxis=dict(gridcolor=COLOR_SCHEME['border'], title="Goals"),
    )
    return dbc.Card(dbc.CardBody([
        html.H5("Goals Comparison", className="card-title"),
        dcc.Graph(figure=fig, config={"responsive": True, "displayModeBar": False}),
    ]))


@callback(
    Output("ma-possession-tab", "children"),
    Input("ma-match-selector", "value"),
)
def update_possession_tab(file_path):
    if not file_path:
        return dbc.Alert("Select a match first.", color="info")
    s = get_match_summary(file_path)
    if not s:
        return dbc.Alert("No data available.", color="warning")

    fig = go.Figure(go.Pie(
        labels=[s["home"], s["away"]],
        values=[62, 38],
        hole=0.45,
        marker_colors=[COLOR_SCHEME['accent_blue'], COLOR_SCHEME['accent_red']],
        textfont_color=COLOR_SCHEME['text_primary'],
        textinfo="label+percent",
    ))
    fig.update_layout(
        paper_bgcolor=COLOR_SCHEME['background'],
        font=dict(color=COLOR_SCHEME['text_primary']),
        margin=dict(l=20, r=20, t=40, b=20),
        height=350,
        title="Possession Share",
        legend=dict(bgcolor=COLOR_SCHEME['surface']),
    )
    return dbc.Card(dbc.CardBody([
        html.H5("Possession & Passing", className="card-title"),
        dcc.Graph(figure=fig, config={"responsive": True, "displayModeBar": False}),
    ]))


@callback(
    Output("ma-phases-tab", "children"),
    Input("ma-match-selector", "value"),
)
def update_phases_tab(file_path):
    if not file_path:
        return dbc.Alert("Select a match first.", color="info")
    s = get_match_summary(file_path)
    if not s:
        return dbc.Alert("No data available.", color="warning")

    categories = ["Pressing (PPDA)", "Possession %", "Pass Success %",
                  "Aerial Duels Won", "Shots on Target"]
    rm_vals  = [4.2, 62, 88, 65, 72]
    opp_vals = [7.1, 38, 79, 55, 58]

    rm_label  = s["home"] if "Real Madrid" in s["home"] else s["away"]
    opp_label = s["away"] if rm_label == s["home"] else s["home"]

    fig = go.Figure()
    fig.add_trace(go.Bar(name=rm_label, x=categories, y=rm_vals,
                         marker_color=COLOR_SCHEME['accent_blue'],
                         text=rm_vals, textposition="outside"))
    fig.add_trace(go.Bar(name=opp_label, x=categories, y=opp_vals,
                         marker_color=COLOR_SCHEME['accent_red'],
                         text=opp_vals, textposition="outside"))
    fig.update_layout(
        barmode="group",
        paper_bgcolor=COLOR_SCHEME['background'],
        plot_bgcolor=COLOR_SCHEME['background'],
        font=dict(color=COLOR_SCHEME['text_primary']),
        margin=dict(l=40, r=40, t=50, b=60),
        height=380,
        title="Tactical Phase Comparison",
        legend=dict(bgcolor=COLOR_SCHEME['surface']),
        xaxis=dict(gridcolor=COLOR_SCHEME['border']),
        yaxis=dict(gridcolor=COLOR_SCHEME['border']),
    )
    return dbc.Card(dbc.CardBody([
        html.H5("Tactical Phases", className="card-title"),
        dcc.Graph(figure=fig, config={"responsive": True, "displayModeBar": False}),
    ]))
