"""
Tactical Phases Analysis Page - Analysis of offensive, defensive, and transition phases
"""

import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from config import COLOR_SCHEME
from utils.data_helpers import (
    get_match_options,
    get_match_summary,
    get_competition_options,
    get_season_options,
)

PHASES = [
    {"label": "Offensive Moment",       "value": "offensive"},
    {"label": "Defensive Moment",       "value": "defensive"},
    {"label": "Offensive Transition",   "value": "off_transition"},
    {"label": "Defensive Transition",   "value": "def_transition"},
]

def layout():
    """Tactical Phases Analysis page layout"""
    default_matches = get_match_options("LaLiga", "2025-2026")
    default_match   = default_matches[0]["value"] if default_matches else None
    return html.Div(
        [
            html.H4("Tactical Phases Analysis", className="rm-page-title"),
            html.P("Offensive, defensive and transition phase breakdown per match",
                   className="text-muted mb-4"),
            dbc.Card(
                dbc.CardBody(
                    dbc.Row([
                        dbc.Col([
                            html.Label("Competition", className="filter-label"),
                            dcc.Dropdown(id="tp-competition",
                                         options=get_competition_options(),
                                         value="LaLiga", clearable=False),
                        ], md=2),
                        dbc.Col([
                            html.Label("Season", className="filter-label"),
                            dcc.Dropdown(id="tp-season",
                                         options=get_season_options("LaLiga"),
                                         value="2025-2026", clearable=False),
                        ], md=2),
                        dbc.Col([
                            html.Label("Phase", className="filter-label"),
                            dcc.Dropdown(id="tp-phase",
                                         options=PHASES,
                                         value="offensive", clearable=False),
                        ], md=2),
                        dbc.Col([
                            html.Label("Match", className="filter-label"),
                            dcc.Dropdown(id="tp-match-selector",
                                         options=default_matches,
                                         value=default_match, clearable=False,
                                         placeholder="Choose a match…"),
                        ], md=6),
                    ], className="g-2"),
                ),
                className="filter-section mb-4",
            ),
            dcc.Loading(html.Div(id="tp-phase-content"), type="circle", color="#1d4ed8"),
        ],
        className="page-content",
    )


# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output("tp-season", "options"),
    Output("tp-season", "value"),
    Input("tp-competition", "value"),
)
def update_tp_season(competition):
    opts = get_season_options(competition or "LaLiga")
    return opts, (opts[0]["value"] if opts else "2025-2026")


@callback(
    Output("tp-match-selector", "options"),
    Output("tp-match-selector", "value"),
    Input("tp-competition", "value"),
    Input("tp-season", "value"),
)
def update_tp_matches(competition, season):
    opts = get_match_options(competition or "LaLiga", season or "2025-2026")
    return opts, (opts[0]["value"] if opts else None)


@callback(
    Output("tp-phase-content", "children"),
    Input("tp-match-selector", "value"),
    Input("tp-phase", "value"),
)
def update_tp_content(file_path, phase):
    if not file_path:
        return dbc.Alert("Select a match to view tactical phases.", color="info")

    s = get_match_summary(file_path)
    if not s:
        return dbc.Alert("Could not load match data.", color="warning")

    phase_data = {
        "offensive": {
            "title": "Offensive Moment",
            "metrics": ["Build-Up Sequences", "Progressive Passes", "Chances Created", "xG", "Zone 14 Touches", "Crosses"],
            "rm":  [45, 142, 12, 2.8, 28, 34],
            "opp": [28,  98,  6, 1.2, 14, 18],
            "color": COLOR_SCHEME['accent_green'],
        },
        "defensive": {
            "title": "Defensive Moment",
            "metrics": ["PPDA", "Tackles", "Interceptions", "Clearances", "Blocks", "Recoveries"],
            "rm":  [4.2, 18, 10, 12, 5, 45],
            "opp": [7.1, 12,  7,  8, 3, 30],
            "color": COLOR_SCHEME['accent_red'],
        },
        "off_transition": {
            "title": "Offensive Transition",
            "metrics": ["Counter-Attacks", "Passes in Transition", "Shots from Counter", "xG Counter", "Speed (m/s)", "Success %"],
            "rm":  [8, 24, 6, 1.4, 8.2, 75],
            "opp": [5, 16, 3, 0.8, 7.5, 60],
            "color": COLOR_SCHEME['accent_orange'],
        },
        "def_transition": {
            "title": "Defensive Transition",
            "metrics": ["Counter-Press Success", "Recovery Time (s)", "Duels Won %", "Ball Wins", "Compactness", "Line Height"],
            "rm":  [68, 3.2, 72, 18, 8.4, 42],
            "opp": [54, 4.8, 61, 12, 7.1, 38],
            "color": COLOR_SCHEME['accent_purple'],
        },
    }

    pd_ = phase_data.get(phase, phase_data["offensive"])
    rm_label  = s["home"] if "Real Madrid" in s["home"] else s["away"]
    opp_label = s["away"] if rm_label == s["home"] else s["home"]

    fig = go.Figure()
    fig.add_trace(go.Bar(name=rm_label, x=pd_["metrics"], y=pd_["rm"],
                         marker_color=pd_["color"],
                         text=pd_["rm"], textposition="outside"))
    fig.add_trace(go.Bar(name=opp_label, x=pd_["metrics"], y=pd_["opp"],
                         marker_color=COLOR_SCHEME['accent_blue'], opacity=0.7,
                         text=pd_["opp"], textposition="outside"))
    fig.update_layout(
        barmode="group",
        paper_bgcolor=COLOR_SCHEME['background'],
        plot_bgcolor=COLOR_SCHEME['background'],
        font=dict(color=COLOR_SCHEME['text_primary']),
        margin=dict(l=40, r=40, t=50, b=60),
        height=380,
        title=f"{pd_['title']} — {rm_label} vs {opp_label}",
        legend=dict(bgcolor=COLOR_SCHEME['surface']),
        xaxis=dict(gridcolor=COLOR_SCHEME['border']),
        yaxis=dict(gridcolor=COLOR_SCHEME['border']),
    )

    return dbc.Card(dbc.CardBody([
        html.H5(pd_["title"], className="card-title"),
        dcc.Graph(figure=fig, config={"responsive": True, "displayModeBar": False}),
    ]))

