"""
Player Analysis Page - Detailed player statistics and performance metrics
"""

import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from config import COLOR_SCHEME
from utils.data_helpers import (
    get_player_options,
    get_position_options,
    get_player_stats,
    get_competition_options,
    get_season_options,
)

# ============================================================================
# HELPERS
# ============================================================================

STAT_GROUPS = {
    "Attacking": ["Goals", "Assists (Intentional)", "Shots", "Key Passes",
                  "Dribbles", "Chances Created"],
    "Passing":   ["Forward Passes", "Backward Passes", "Successful Final Third Passes",
                  "Progressive Passes"],
    "Defensive": ["Tackles", "Interceptions", "Clearances", "Blocks", "Recoveries"],
    "Physical":  ["Aerial Duels won", "Duels won", "Carries"],
}

RADAR_METRICS = [
    "Goals", "Assists (Intentional)", "Key Passes", "Tackles",
    "Aerial Duels won", "Recoveries",
]


def _to_number(value, default=0.0):
    try:
        if value is None:
            return default
        number = float(value)
        return default if number != number else number
    except (TypeError, ValueError):
        return default


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
    """Player Analysis page layout"""
    default_players = get_player_options("LaLiga", "2025-2026")
    default_player  = default_players[0]["value"] if default_players else None

    return html.Div([
        html.Div([
            html.H4("Player Analysis", className="rm-page-title"),
            html.P("Individual player performance metrics and percentile rankings",
                   className="rm-page-subtitle"),
        ], className="rm-page-header"),

        # ── Filter Row ──────────────────────────────────────────────────────
        dbc.Card(
            dbc.CardBody(
                dbc.Row([
                    dbc.Col([
                        html.Label("Competition", className="filter-label"),
                        dcc.Dropdown(
                            id="pa-competition",
                            options=get_competition_options(),
                            value="LaLiga",
                            clearable=False,
                        ),
                    ], md=2),
                    dbc.Col([
                        html.Label("Season", className="filter-label"),
                        dcc.Dropdown(
                            id="pa-season",
                            options=get_season_options("LaLiga"),
                            value="2025-2026",
                            clearable=False,
                        ),
                    ], md=2),
                    dbc.Col([
                        html.Label("Position", className="filter-label"),
                        dcc.Dropdown(
                            id="pa-position",
                            options=get_position_options(),
                            value="All",
                            clearable=False,
                        ),
                    ], md=2),
                    dbc.Col([
                        html.Label("Select Player", className="filter-label"),
                        dcc.Dropdown(
                            id="pa-player-selector",
                            options=default_players,
                            value=default_player,
                            clearable=False,
                            placeholder="Choose a player…",
                        ),
                    ], md=6),
                ], className="g-2"),
            ),
            className="filter-section mb-4",
        ),

        # ── Player KPI Cards ─────────────────────────────────────────────────
        dbc.Row(id="pa-kpi-row", className="g-2 mb-4"),

        # ── Results sections ───────────────────────────────────────────────
        html.Div([
            html.H6("Radar Profile", className="card-title"),
            dcc.Loading(html.Div(id="pa-radar-tab"), type="circle", color="#1d4ed8"),
        ], className="card mb-3"),

        html.Div([
            html.H6("Statistics Table", className="card-title"),
            dcc.Loading(html.Div(id="pa-stats-tab"), type="circle", color="#1d4ed8"),
        ], className="card mb-3"),

        html.Div([
            html.H6("Position Comparison", className="card-title"),
            dcc.Loading(html.Div(id="pa-compare-tab"), type="circle", color="#1d4ed8"),
        ], className="card mb-3"),

    ], className="page-content")


# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output("pa-season", "options"),
    Output("pa-season", "value"),
    Input("pa-competition", "value"),
)
def update_pa_season(competition):
    opts = get_season_options(competition or "LaLiga")
    return opts, (opts[0]["value"] if opts else "2025-2026")


@callback(
    Output("pa-player-selector", "options"),
    Output("pa-player-selector", "value"),
    Input("pa-competition", "value"),
    Input("pa-season", "value"),
    Input("pa-position", "value"),
)
def update_player_options(competition, season, position):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"
    pos  = position or "All"
    opts = get_player_options(comp, seas, pos)
    return opts, (opts[0]["value"] if opts else None)


@callback(
    Output("pa-kpi-row", "children"),
    Input("pa-player-selector", "value"),
    Input("pa-competition", "value"),
    Input("pa-season", "value"),
)
def update_player_kpis(player, competition, season):
    if not player:
        return []
    stats = get_player_stats(player, competition or "LaLiga", season or "2025-2026")
    if not stats:
        return []

    def safe(key):
        val = stats.get(key, 0)
        try:
            v = _to_number(val, 0.0)
            if v == 0.0 and str(val) in {"nan", "NaN"}:
                return 0
            return int(v) if v == int(v) else round(v, 2)
        except (TypeError, ValueError):
            return val or "—"

    pos  = stats.get("posicion", "")
    apps = safe("Appearances")

    kpis = [
        _kpi_card("Appearances", apps, COLOR_SCHEME['accent_blue']),
        _kpi_card("Goals", safe("Goals"), COLOR_SCHEME['accent_green']),
        _kpi_card("Assists", safe("Assists (Intentional)"), COLOR_SCHEME['accent_orange']),
        _kpi_card("Tackles", safe("Tackles"), COLOR_SCHEME['accent_red']),
        _kpi_card("Recoveries", safe("Recoveries"), COLOR_SCHEME['accent_purple']),
        _kpi_card("Position", pos, COLOR_SCHEME['accent_yellow']),
    ]
    return kpis


@callback(
    Output("pa-radar-tab", "children"),
    Input("pa-player-selector", "value"),
    Input("pa-competition", "value"),
    Input("pa-season", "value"),
)
def update_player_radar(player, competition, season):
    if not player:
        return dbc.Alert("Select a player to see their radar profile.", color="info")
    stats = get_player_stats(player, competition or "LaLiga", season or "2025-2026")
    if not stats:
        return dbc.Alert("No statistics found for this player.", color="warning")

    metrics = RADAR_METRICS
    values  = []
    for m in metrics:
        values.append(_to_number(stats.get(m, 0), 0.0))

    # Normalise to 0-100 for radar display
    max_vals = [10, 10, 10, 50, 20, 50]
    norm = [min(100, round((v / mx) * 100)) if mx else 0 for v, mx in zip(values, max_vals)]

    labels = ["Goals", "Assists", "Key Passes", "Tackles", "Aerial\nDuels", "Recoveries"]
    fig = go.Figure(go.Scatterpolar(
        r=norm + [norm[0]],
        theta=labels + [labels[0]],
        fill="toself",
        fillcolor=f"rgba(59, 130, 246, 0.3)",
        line=dict(color=COLOR_SCHEME['accent_blue'], width=2),
        name=player,
    ))
    fig.update_layout(
        polar=dict(
            bgcolor=COLOR_SCHEME['surface'],
            radialaxis=dict(visible=True, range=[0, 100],
                            gridcolor=COLOR_SCHEME['border'],
                            color=COLOR_SCHEME['text_secondary']),
            angularaxis=dict(gridcolor=COLOR_SCHEME['border'],
                             color=COLOR_SCHEME['text_primary']),
        ),
        paper_bgcolor=COLOR_SCHEME['background'],
        font=dict(color=COLOR_SCHEME['text_primary']),
        margin=dict(l=50, r=50, t=60, b=50),
        height=420,
        title=dict(text=f"{player} — Tactical Radar",
                   font=dict(size=15, color=COLOR_SCHEME['text_primary'])),
    )

    # Raw values table below radar
    rows = [
        html.Tr([html.Td(m), html.Td(str(int(v)) if v == int(v) else str(round(v, 2)))])
        for m, v in zip(labels, values)
    ]
    table = html.Table([
        html.Thead(html.Tr([html.Th("Metric"), html.Th("Value")])),
        html.Tbody(rows),
    ], className="w-100 table table-sm mt-3",
       style={"color": COLOR_SCHEME['text_primary']})

    return dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            dcc.Graph(figure=fig, config={"responsive": True, "displayModeBar": False}),
        ])), md=8),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Raw Values", className="filter-label"),
            table,
        ])), md=4),
    ], className="g-3")


@callback(
    Output("pa-stats-tab", "children"),
    Input("pa-player-selector", "value"),
    Input("pa-competition", "value"),
    Input("pa-season", "value"),
)
def update_stats_table(player, competition, season):
    if not player:
        return dbc.Alert("Select a player to view statistics.", color="info")
    stats = get_player_stats(player, competition or "LaLiga", season or "2025-2026")
    if not stats:
        return dbc.Alert("No statistics found.", color="warning")

    rows = []
    for group_name, metrics in STAT_GROUPS.items():
        rows.append(html.Tr([
            html.Td(html.Strong(group_name), colSpan=2,
                    style={"backgroundColor": COLOR_SCHEME['border'],
                           "color": COLOR_SCHEME['accent_blue'],
                           "paddingLeft": "8px"}),
        ]))
        for m in metrics:
            val = stats.get(m, "—")
            try:
                v = float(val)
                val = int(v) if v == int(v) else round(v, 2)
            except (TypeError, ValueError):
                pass
            rows.append(html.Tr([html.Td(m), html.Td(str(val))]))

    return dbc.Card(dbc.CardBody([
        html.H5(f"{player} — Season Statistics", className="card-title"),
        html.Table(
            [html.Tbody(rows)],
            className="w-100 table table-sm",
            style={"color": COLOR_SCHEME['text_primary']},
        ),
    ]))


@callback(
    Output("pa-compare-tab", "children"),
    Input("pa-player-selector", "value"),
    Input("pa-competition", "value"),
    Input("pa-season", "value"),
    Input("pa-position", "value"),
)
def update_compare_tab(player, competition, season, position):
    if not player:
        return dbc.Alert("Select a player to compare.", color="info")
    stats = get_player_stats(player, competition or "LaLiga", season or "2025-2026")
    if not stats:
        return dbc.Alert("No statistics found.", color="warning")

    metrics = ["Goals", "Assists (Intentional)", "Tackles", "Recoveries",
               "Aerial Duels won", "Key Passes"]
    labels  = ["Goals", "Assists", "Tackles", "Recoveries", "Aerial Duels", "Key Passes"]

    player_vals = []
    for m in metrics:
        player_vals.append(_to_number(stats.get(m, 0), 0.0))

    # Squad average (all RM players)
    from utils.data_helpers import _load_player_stats
    df = _load_player_stats(competition or "LaLiga", season or "2025-2026")
    avg_vals = []
    for m in metrics:
        if not df.empty and m in df.columns:
            avg_vals.append(round(df[m].mean(), 1))
        else:
            avg_vals.append(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(name=player, x=labels, y=player_vals,
                         marker_color=COLOR_SCHEME['accent_blue'],
                         text=player_vals, textposition="outside"))
    fig.add_trace(go.Bar(name="Squad Average", x=labels, y=avg_vals,
                         marker_color=COLOR_SCHEME['accent_orange'], opacity=0.7,
                         text=avg_vals, textposition="outside"))
    fig.update_layout(
        barmode="group",
        paper_bgcolor=COLOR_SCHEME['background'],
        plot_bgcolor=COLOR_SCHEME['background'],
        font=dict(color=COLOR_SCHEME['text_primary']),
        margin=dict(l=40, r=40, t=50, b=60),
        height=400,
        title=f"{player} vs Squad Average",
        legend=dict(bgcolor=COLOR_SCHEME['surface']),
        xaxis=dict(gridcolor=COLOR_SCHEME['border']),
        yaxis=dict(gridcolor=COLOR_SCHEME['border']),
    )
    return dbc.Card(dbc.CardBody([
        html.H5("Player vs Squad Average", className="card-title"),
        dcc.Graph(figure=fig, config={"responsive": True, "displayModeBar": False}),
    ]))
