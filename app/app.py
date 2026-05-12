"""
Real Madrid Tactical & Player Performance Dashboard
Main Application Entry Point — v2.0 Professional UI
"""

import sys
import logging
import logging.config
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

from config import (
    COLOR_SCHEME,
    DARK_TEMPLATE,
    DASHBOARD_CONFIG,
    LOG_CONFIG,
)
from utils.data_helpers import (
    get_competition_options,
    get_season_options,
    get_available_seasons,
)

# Configure logging
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

# Import all pages to register their callbacks
# This MUST be done before app.layout is defined
import pages.home
import pages.match_analysis
import pages.player_analysis
import pages.tactical_phases
import pages.opponent_analysis
import pages.benchmarking

# ============================================================================
# APP INIT
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)
app.title = DASHBOARD_CONFIG["title"]
server = app.server

# ============================================================================
# NAV ITEMS
# ============================================================================

NAV_ITEMS = [
    {"icon": "🏠", "label": "Overview",        "href": "/"},
    {"icon": "📊", "label": "Match Analysis",  "href": "/match-analysis"},
    {"icon": "👤", "label": "Player Analysis", "href": "/player-analysis"},
    {"icon": "⚔️", "label": "Tactical Phases", "href": "/tactical-phases"},
    {"icon": "🔭", "label": "Opponent Scout",  "href": "/opponent-analysis"},
    {"icon": "📈", "label": "Benchmarking",    "href": "/benchmarking"},
]


# ============================================================================
# SIDEBAR
# ============================================================================

def create_sidebar_full():
    comp_opts   = get_competition_options()
    season_opts = get_season_options("LaLiga")

    nav_links = [
        dbc.NavLink(
            [html.Span(i["icon"], className="rm-nav-icon"), html.Span(i["label"])],
            href=i["href"],
            active="exact",
            className="rm-nav-link",
        )
        for i in NAV_ITEMS
    ]

    return dbc.Col(
        html.Div(
            [
                html.Div(
                    html.Div(
                        [
                            html.Div(
                                html.Span("⚽", style={"fontSize": "20px"}),
                                className="rm-sidebar-brand-icon",
                            ),
                            html.Div(
                                [
                                    html.Div("Real Madrid CF", className="rm-sidebar-brand-text"),
                                    html.Div("Tactical Analytics", className="rm-sidebar-brand-sub"),
                                ]
                            ),
                        ],
                        className="d-flex align-items-center gap-2",
                    ),
                    className="rm-sidebar-header",
                ),
                html.Div(
                    [
                        html.Div("Navigation", className="rm-sidebar-section-label"),
                        dbc.Nav(nav_links, vertical=True),
                    ],
                    className="rm-sidebar-section",
                ),
                html.Div(
                    [
                        html.Span("Quick Filters", className="rm-sidebar-filter-label"),
                        html.Label("Competition", className="rm-sidebar-filter-label"),
                        dcc.Dropdown(
                            id="global-competition-dropdown",
                            options=comp_opts,
                            value="LaLiga",
                            clearable=False,
                            className="mb-2",
                        ),
                        html.Label("Season", className="rm-sidebar-filter-label"),
                        dcc.Dropdown(
                            id="global-season-dropdown",
                            options=season_opts,
                            value="2025-2026",
                            clearable=False,
                        ),
                    ],
                    className="rm-sidebar-filters",
                ),
                html.Div(
                    [
                        html.P("Master's Final Project", className="text-xs mb-0",
                               style={"color": "#94a3b8"}),
                        html.P(f"Updated {datetime.now().strftime('%d %b %Y')}",
                               className="text-xs mb-0", style={"color": "#94a3b8"}),
                    ],
                    style={"padding": "12px 16px",
                           "borderTop": "1px solid rgba(255,255,255,0.08)"},
                ),
            ],
            className="rm-sidebar",
            style={"height": "100vh", "overflowY": "auto"},
        ),
        width=2,
        className="p-0",
    )


# ============================================================================
# APP LAYOUT
# ============================================================================

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="session-store", storage_type="session"),

        dbc.Row(
            [
                create_sidebar_full(),

                dbc.Col(
                    [
                        # Topbar
                        html.Div(
                            dbc.Row(
                                [
                                    dbc.Col(
                                        html.Div(id="page-breadcrumb",
                                                 className="text-sm text-muted"),
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        html.Div(
                                            id="topbar-badges",
                                            className="d-flex align-items-center justify-content-end",
                                            children=[
                                                html.Span("2025-2026",
                                                          className="rm-badge rm-badge-blue me-2"),
                                                html.Span("LaLiga",
                                                          className="rm-badge rm-badge-green"),
                                            ],
                                        ),
                                    ),
                                ],
                                className="align-items-center",
                            ),
                            className="rm-filter-bar",
                        ),

                        # Page content with loading
                        dcc.Loading(
                            html.Div(id="page-content", className="page-content"),
                            type="circle",
                            color="#1d4ed8",
                            delay_show=200,
                        ),
                    ],
                    width=10,
                    className="p-0",
                ),
            ],
            className="g-0",
            style={"minHeight": "100vh"},
        ),
    ],
)

# ============================================================================
# ROUTING
# ============================================================================

CRUMB_MAP = {
    "/":                  "🏠  Overview",
    "/match-analysis":    "📊  Match Analysis",
    "/player-analysis":   "👤  Player Analysis",
    "/tactical-phases":   "⚔️  Tactical Phases",
    "/opponent-analysis": "🔭  Opponent Scout",
    "/benchmarking":      "📈  Benchmarking",
}


@app.callback(
    Output("page-content",    "children"),
    Output("page-breadcrumb", "children"),
    Input("url", "pathname"),
)
def display_page(pathname):
    breadcrumb = html.Span(CRUMB_MAP.get(pathname, "Dashboard"), className="fw-700")

    if pathname in ("/", "/home", None):
        from pages.home import layout
        return layout(), breadcrumb
    elif pathname == "/match-analysis":
        from pages.match_analysis import layout
        return layout(), breadcrumb
    elif pathname == "/player-analysis":
        from pages.player_analysis import layout
        return layout(), breadcrumb
    elif pathname == "/tactical-phases":
        from pages.tactical_phases import layout
        return layout(), breadcrumb
    elif pathname == "/opponent-analysis":
        from pages.opponent_analysis import layout
        return layout(), breadcrumb
    elif pathname == "/benchmarking":
        from pages.benchmarking import layout
        return layout(), breadcrumb
    else:
        return (
            dbc.Alert("404 – Page not found.", color="danger", className="m-4"),
            html.Span("Not found"),
        )


# ============================================================================
# GLOBAL CALLBACKS
# ============================================================================

@app.callback(
    Output("session-store", "data"),
    Input("global-season-dropdown",      "value"),
    Input("global-competition-dropdown", "value"),
)
def store_global_selections(season, competition):
    return {
        "season":      season      or "2025-2026",
        "competition": competition or "LaLiga",
    }


@app.callback(
    Output("global-season-dropdown", "options"),
    Output("global-season-dropdown", "value"),
    Input("global-competition-dropdown", "value"),
)
def update_season_options(competition):
    comp    = competition or "LaLiga"
    seasons = get_available_seasons(comp)
    options = [{"label": s, "value": s} for s in seasons]
    default = seasons[0] if seasons else "2025-2026"
    return options, default


@app.callback(
    Output("topbar-badges", "children"),
    Input("global-competition-dropdown", "value"),
    Input("global-season-dropdown",      "value"),
)
def update_topbar_badges(competition, season):
    return [
        html.Span(season or "2025-2026", className="rm-badge rm-badge-blue me-2"),
        html.Span(competition or "LaLiga", className="rm-badge rm-badge-green"),
    ]


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    logger.info(f"Starting {DASHBOARD_CONFIG['title']}")
    app.run(debug=False, host="127.0.0.1", port=8051)
