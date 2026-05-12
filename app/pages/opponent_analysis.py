"""
Opponent Analysis Page - Opposition scouting and tactical analysis
"""

import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from config import COLOR_SCHEME
from utils.data_helpers import (
    get_opponent_options,
    get_competition_options,
    get_season_options,
)

def layout():
    """Opponent Analysis page layout"""
    default_opponents = get_opponent_options("LaLiga", "2025-2026")
    default_opponent  = default_opponents[0]["value"] if default_opponents else None
    return html.Div(
        [
            html.H4("Opponent Scouting", className="rm-page-title"),
            html.P("Opposition scouting and head-to-head tactical breakdown",
                   className="text-muted mb-4"),
            dbc.Card(
                dbc.CardBody(
                    dbc.Row([
                        dbc.Col([
                            html.Label("Competition", className="filter-label"),
                            dcc.Dropdown(id="oa-competition",
                                         options=get_competition_options(),
                                         value="LaLiga", clearable=False),
                        ], md=2),
                        dbc.Col([
                            html.Label("Season", className="filter-label"),
                            dcc.Dropdown(id="oa-season",
                                         options=get_season_options("LaLiga"),
                                         value="2025-2026", clearable=False),
                        ], md=2),
                        dbc.Col([
                            html.Label("Opponent", className="filter-label"),
                            dcc.Dropdown(id="oa-opponent",
                                         options=default_opponents,
                                         value=default_opponent, clearable=False,
                                         placeholder="Choose an opponent…"),
                        ], md=8),
                    ], className="g-2"),
                ),
                className="filter-section mb-4",
            ),
            dcc.Loading(html.Div(id="oa-opponent-content"), type="circle", color="#1d4ed8"),
        ],
        className="page-content",
    )


# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output("oa-season", "options"),
    Output("oa-season", "value"),
    Input("oa-competition", "value"),
)
def update_oa_season(competition):
    opts = get_season_options(competition or "LaLiga")
    return opts, (opts[0]["value"] if opts else "2025-2026")


@callback(
    Output("oa-opponent", "options"),
    Output("oa-opponent", "value"),
    Input("oa-competition", "value"),
    Input("oa-season", "value"),
)
def update_oa_opponents(competition, season):
    opts = get_opponent_options(competition or "LaLiga", season or "2025-2026")
    return opts, (opts[0]["value"] if opts else None)


@callback(
    Output("oa-opponent-content", "children"),
    Input("oa-opponent", "value"),
    Input("oa-competition", "value"),
    Input("oa-season", "value"),
)
def update_oa_content(opponent, competition, season):
    if not opponent:
        return dbc.Alert("Select an opponent to view scouting analysis.", color="info")

    import plotly.graph_objects as go
    metrics = ["Goals Scored", "Goals Conceded", "Shots pg", "Possession %",
               "Pass Acc %", "Tackles pg"]
    values  = [1.8, 1.1, 12.4, 52, 81, 18]

    fig = go.Figure(go.Bar(
        x=metrics, y=values,
        marker_color=COLOR_SCHEME['accent_red'],
        text=values, textposition="outside",
    ))
    fig.update_layout(
        paper_bgcolor=COLOR_SCHEME['background'],
        plot_bgcolor=COLOR_SCHEME['background'],
        font=dict(color=COLOR_SCHEME['text_primary']),
        margin=dict(l=40, r=40, t=50, b=60),
        height=360,
        title=f"{opponent} — Season Profile",
        xaxis=dict(gridcolor=COLOR_SCHEME['border']),
        yaxis=dict(gridcolor=COLOR_SCHEME['border']),
    )

    return dbc.Card(dbc.CardBody([
        html.H5(f"Scouting: {opponent}", className="card-title"),
        dcc.Graph(figure=fig, config={"responsive": True, "displayModeBar": False}),
    ]))
