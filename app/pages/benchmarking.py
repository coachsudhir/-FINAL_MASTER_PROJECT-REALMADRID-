"""
Benchmarking Page - League comparison and tactical positioning
"""

import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from config import COLOR_SCHEME
from utils.data_helpers import (
    get_team_options,
    get_competition_options,
    get_season_options,
)

METRIC_CATEGORIES = [
    {"label": "Attacking",  "value": "attacking"},
    {"label": "Defensive",  "value": "defensive"},
    {"label": "Possession", "value": "possession"},
    {"label": "Transitions","value": "transitions"},
]

def layout():
    """Benchmarking page layout"""
    default_teams = get_team_options("LaLiga", "2025-2026")
    default_team  = "Real Madrid CF" if any(t["value"] == "Real Madrid CF" for t in default_teams) else (default_teams[0]["value"] if default_teams else None)
    return html.Div(
        [
            html.H4("Benchmarking & League Comparison", className="rm-page-title"),
            html.P("Compare Real Madrid against LaLiga and European competition",
                   className="text-muted mb-4"),
            dbc.Card(
                dbc.CardBody(
                    dbc.Row([
                        dbc.Col([
                            html.Label("Competition", className="filter-label"),
                            dcc.Dropdown(id="bm-competition",
                                         options=get_competition_options(),
                                         value="LaLiga", clearable=False),
                        ], md=2),
                        dbc.Col([
                            html.Label("Season", className="filter-label"),
                            dcc.Dropdown(id="bm-season",
                                         options=get_season_options("LaLiga"),
                                         value="2025-2026", clearable=False),
                        ], md=2),
                        dbc.Col([
                            html.Label("Metric Category", className="filter-label"),
                            dcc.Dropdown(id="bm-metric",
                                         options=METRIC_CATEGORIES,
                                         value="attacking", clearable=False),
                        ], md=2),
                        dbc.Col([
                            html.Label("Compare Team", className="filter-label"),
                            dcc.Dropdown(id="bm-team",
                                         options=default_teams,
                                         value=default_team, clearable=False,
                                         placeholder="Choose a team…"),
                        ], md=6),
                    ], className="g-2"),
                ),
                className="filter-section mb-4",
            ),
            dcc.Loading(html.Div(id="bm-content"), type="circle", color="#1d4ed8"),
        ],
        className="page-content",
    )


# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output("bm-season", "options"),
    Output("bm-season", "value"),
    Input("bm-competition", "value"),
)
def update_bm_season(competition):
    opts = get_season_options(competition or "LaLiga")
    return opts, (opts[0]["value"] if opts else "2025-2026")


@callback(
    Output("bm-team", "options"),
    Output("bm-team", "value"),
    Input("bm-competition", "value"),
    Input("bm-season", "value"),
)
def update_bm_teams(competition, season):
    opts = get_team_options(competition or "LaLiga", season or "2025-2026")
    val = "Real Madrid CF" if any(t["value"] == "Real Madrid CF" for t in opts) else (opts[0]["value"] if opts else None)
    return opts, val


@callback(
    Output("bm-content", "children"),
    Input("bm-team", "value"),
    Input("bm-competition", "value"),
    Input("bm-season", "value"),
    Input("bm-metric", "value"),
)
def update_bm_content(team, competition, season, metric):
    if not team:
        return dbc.Alert("Select a team to compare.", color="info")

    import plotly.graph_objects as go

    metric_data = {
        "attacking":  {"labels": ["Goals pg", "Shots pg", "xG pg", "Key Passes pg", "Chances Created pg"],
                       "rm": [2.4, 14.2, 1.8, 12.3, 3.2], "other": [1.6, 10.8, 1.2, 9.1, 2.4]},
        "defensive":  {"labels": ["Goals Conceded pg", "Shots Conceded pg", "Tackles pg", "Interceptions pg", "Clean Sheets"],
                       "rm": [0.9, 8.1, 18.2, 9.4, 14], "other": [1.4, 10.3, 15.6, 8.1, 9]},
        "possession": {"labels": ["Possession %", "Pass Acc %", "Prog Passes pg", "Dribbles pg", "PPDA"],
                       "rm": [61, 88, 42, 14.2, 4.2], "other": [54, 83, 34, 11.8, 6.1]},
        "transitions":{"labels": ["Counter-attacks pg", "Counter Goals", "Recovery Rate %", "Transitions Won %", "Speed (km/h)"],
                       "rm": [3.2, 0.8, 68, 72, 26.4], "other": [2.1, 0.5, 55, 61, 24.8]},
    }
    md = metric_data.get(metric, metric_data["attacking"])

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Real Madrid", x=md["labels"], y=md["rm"],
                         marker_color=COLOR_SCHEME['accent_blue'],
                         text=md["rm"], textposition="outside"))
    fig.add_trace(go.Bar(name=team, x=md["labels"], y=md["other"],
                         marker_color=COLOR_SCHEME['accent_orange'], opacity=0.75,
                         text=md["other"], textposition="outside"))
    fig.update_layout(
        barmode="group",
        paper_bgcolor=COLOR_SCHEME['background'],
        plot_bgcolor=COLOR_SCHEME['background'],
        font=dict(color=COLOR_SCHEME['text_primary']),
        margin=dict(l=40, r=40, t=60, b=60),
        height=400,
        title=f"Real Madrid vs {team} — {metric.title()} Metrics",
        legend=dict(bgcolor=COLOR_SCHEME['surface']),
        xaxis=dict(gridcolor=COLOR_SCHEME['border']),
        yaxis=dict(gridcolor=COLOR_SCHEME['border']),
    )

    return dbc.Card(dbc.CardBody([
        html.H5(f"Real Madrid vs {team}", className="card-title"),
        dcc.Graph(figure=fig, config={"responsive": True, "displayModeBar": False}),
    ]))
