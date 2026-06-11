"""
Match Analysis Page — Real Madrid Tactical Dashboard
Event-level tactical breakdown using Opta JSON data.
"""

import numpy as np
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from config import COLOR_SCHEME
from utils.data_helpers import (
    get_competition_options,
    get_season_options,
    get_match_options,
)
from utils.data_loader import (
    load_match_json,
    extract_match_meta,
    parse_events,
    calc_match_kpis,
    get_shot_data,
    get_player_stats,
    get_match_lineup_status,
    calc_ppda,
    calc_field_tilt,
)
from utils.phase_scoring import phase_scores_from_events

_C = COLOR_SCHEME
_RM   = _C["accent_blue"]
_OPP  = _C["accent_red"]
_GOLD = "#f59e0b"
_PITCH_FILL = "#d9f0dc"
_PITCH_LINE = "#2e7d32"

_PL = dict(
    paper_bgcolor=_C["surface"],
    plot_bgcolor=_C["surface"],
    font=dict(color=_C["text_primary"], size=11),
    hovermode="closest",
    margin=dict(l=52, r=30, t=84, b=60),
    uniformtext_minsize=9,
    uniformtext_mode="hide",
    legend=dict(orientation="h", yanchor="bottom", y=1.005, xanchor="right", x=1,
                bgcolor="rgba(255,255,255,0.6)"),
)
_H_CHART = 400
_H_COMPARE = 480
_H_PITCH = 520
_PITCH_LABEL_FONT = dict(size=10, color="rgba(15,23,42,0.62)")


# ── Pitch drawing helpers ──────────────────────────────────────────────────

def _pitch_shapes(color=_PITCH_LINE, fill=_PITCH_FILL):
    """Half-pitch shapes (attacking end x=50..100)."""
    lw, s = 1.5, []

    def _rect(x0, x1, y0, y1, fc="rgba(0,0,0,0)"):
        s.append(dict(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(color=color, width=lw), fillcolor=fc, layer="below"))

    _rect(50, 100, 0, 100, fill)
    s.append(dict(type="line", x0=50, x1=50, y0=0, y1=100,
                  line=dict(color=color, width=lw), layer="below"))
    _rect(83.5, 100, 21.1, 78.9)
    _rect(94.5, 100, 36.8, 63.2)
    _rect(100, 102, 45.2, 54.8, "white")
    s.append(dict(type="circle", x0=88, x1=88.8, y0=49.6, y1=50.4,
                  fillcolor=color, line=dict(color=color, width=1), layer="below"))
    return s


def _pitch_stripes_half():
    stripes = []
    for i in range(10):
        x0 = 50 + (i * 5)
        x1 = x0 + 5
        fc = "rgba(76,175,80,0.08)" if i % 2 == 0 else "rgba(255,255,255,0.00)"
        stripes.append(dict(type="rect", x0=x0, x1=x1, y0=0, y1=100,
                            line=dict(width=0), fillcolor=fc, layer="below"))
    return stripes


def _pitch_shapes_full(color=_PITCH_LINE, fill=_PITCH_FILL):
    """Full pitch shapes."""
    lw, s = 1.5, []

    def _rect(x0, x1, y0, y1, fc="rgba(0,0,0,0)"):
        s.append(dict(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(color=color, width=lw), fillcolor=fc, layer="below"))

    _rect(0, 100, 0, 100, fill)
    s.append(dict(type="line", x0=50, x1=50, y0=0, y1=100,
                  line=dict(color=color, width=lw), layer="below"))
    _rect(0, 16.5, 21.1, 78.9)
    _rect(83.5, 100, 21.1, 78.9)
    _rect(0, 5.5, 36.8, 63.2)
    _rect(94.5, 100, 36.8, 63.2)
    _rect(-2, 0, 45.2, 54.8, "white")
    _rect(100, 102, 45.2, 54.8, "white")
    s.append(dict(type="circle", x0=41.55, x1=58.45, y0=40.65, y1=59.35,
                  line=dict(color=color, width=lw), fillcolor="rgba(0,0,0,0)", layer="below"))
    return s


def _pitch_stripes_full():
    stripes = []
    for i in range(20):
        x0 = i * 5
        x1 = x0 + 5
        fc = "rgba(76,175,80,0.08)" if i % 2 == 0 else "rgba(255,255,255,0.00)"
        stripes.append(dict(type="rect", x0=x0, x1=x1, y0=0, y1=100,
                            line=dict(width=0), fillcolor=fc, layer="below"))
    return stripes


def _add_pitch_context_labels(fig: go.Figure, full_pitch: bool):
    # DATA coordinates (xref/yref=x/y) so labels sit INSIDE the pitch even
    # though the y-axis is letterboxed by scaleratio.  RM attacks → right.
    if full_pitch:
        labels = [(16, 5, "Defensive Third"), (50, 5, "Middle Third"), (84, 5, "Attacking Third")]
    else:
        labels = [(62, 5, "Middle Third"), (84, 5, "Final Third")]
    for x, y, text in labels:
        fig.add_annotation(
            x=x, y=y, xref="x", yref="y", text=text,
            showarrow=False, xanchor="center", yanchor="middle",
            font=_PITCH_LABEL_FONT, bgcolor="rgba(255,255,255,0.72)", borderpad=2,
        )
    return fig


def _kpi_card(title, value, color=None, sub=None):
    color = color or _RM
    body = [
        html.P(title, className="kpi-title"),
        html.Div(str(value), className="kpi-value", style={"color": color}),
    ]
    if sub:
        body.append(html.P(sub, className="text-muted",
                           style={"fontSize": "0.72rem", "marginBottom": 0}))
    return dbc.Col(
        dbc.Card(dbc.CardBody(body), className="kpi-card h-100"),
        lg=2, md=4, sm=6, xs=12, className="mb-2",
    )


def _add_direction_arrows(fig: go.Figure, left_team: str, right_team: str):
    fig.add_annotation(
        x=0.03,
        y=0.99,
        xref="paper",
        yref="paper",
        text=f"{left_team} attacks ←",
        showarrow=False,
        xanchor="left",
        font=dict(size=10, color=_OPP),
    )
    fig.add_annotation(
        x=0.97,
        y=0.99,
        xref="paper",
        yref="paper",
        text=f"{right_team} attacks →",
        showarrow=False,
        xanchor="right",
        font=dict(size=10, color=_RM),
    )
    return fig


def _rm_team_name(meta: dict) -> str:
    home = meta.get("home_team", "")
    away = meta.get("away_team", "")
    opp = meta.get("opponent", "")
    if home and away:
        return away if home == opp else home
    return "Real Madrid"


def _short_name(name: str) -> str:
    parts = [p for p in str(name or "").split() if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][:10]
    return f"{parts[0][0]}. {' '.join(parts[1:])[:12]}"


def _team_starting_positions(events: pd.DataFrame, team_id: str, mirror: bool = False) -> pd.DataFrame:
    """Estimate starting XI positions using early-phase open-play events."""
    if events is None or events.empty:
        return pd.DataFrame()

    tm = events[(events["contestant_id"] == team_id) & events["player_name"].notna()].copy()
    tm = tm[tm["player_name"].astype(str).str.strip() != ""]
    if tm.empty:
        return pd.DataFrame()

    # Keep only action-like events to avoid noise from restarts/bookkeeping.
    action_mask = (
        tm["is_pass"] | tm["is_shot"] | tm["is_tackle"] |
        tm["is_interception"] | tm["is_recovery"] | tm["is_dribble"]
    )
    tm = tm[action_mask & tm["x"].notna() & tm["y"].notna()]
    if tm.empty:
        return pd.DataFrame()

    lineup_map = get_match_lineup_status(events, team_id)
    starter_names = {p for p, status in lineup_map.items() if status == "Starting 11"}
    if not starter_names:
        return pd.DataFrame()

    grouped = tm.groupby("player_name", as_index=False).agg(
        first_min=("minute", "min"),
        touches=("event_id", "count"),
    )
    starters = grouped[grouped["player_name"].isin(starter_names)].copy()

    # Enforce exactly 11 players when event noise creates ambiguities.
    starters = starters.sort_values(["first_min", "touches"], ascending=[True, False])
    if len(starters) > 11:
        starters = starters.head(11)
    elif len(starters) < 11:
        missing = 11 - len(starters)
        fallback = grouped[~grouped["player_name"].isin(starters["player_name"])]\
            .sort_values(["first_min", "touches"], ascending=[True, False])\
            .head(missing)
        starters = pd.concat([starters, fallback], ignore_index=True)

    rows = []
    for player in starters["player_name"].tolist():
        p_ev = tm[tm["player_name"] == player]
        early = p_ev[p_ev["minute"].fillna(0) <= 35]
        use = early if not early.empty else p_ev
        x = float(use["x"].median())
        y = float(use["y"].median())
        if mirror:
            x, y = 100.0 - x, 100.0 - y
        rows.append({
            "player_name": player,
            "x": x,
            "y": y,
            "touches": int(len(p_ev)),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["x", "y"], ascending=[True, True]).head(11)


def _team_events_sorted(events: pd.DataFrame, team_id: str) -> pd.DataFrame:
    if events is None or events.empty:
        return pd.DataFrame()
    tm = events[events["contestant_id"] == team_id].copy()
    if tm.empty:
        return tm
    for c in ["period", "minute", "second", "event_id"]:
        if c not in tm.columns:
            tm[c] = 0
    # Include __match_index as primary sort key when available (Range mode)
    # so events from different matches stay ordered within their own match.
    sort_keys = ["period", "minute", "second", "event_id"]
    if "__match_index" in tm.columns:
        sort_keys = ["__match_index"] + sort_keys
    return tm.sort_values(sort_keys)


def _build_pass_network(events: pd.DataFrame, team_id: str, min_edge_count: int = 2,
                        starter_names: set | None = None, max_players: int = 11):
    """Build pass-network nodes/edges from ordered team events only.

    starter_names: if provided, restrict the network to those players (Starting XI
                   view).  max_players caps node count (11 for the XI, larger for the
                   full-match view).  Edges are built only from successful passes.
    """
    tm = _team_events_sorted(events, team_id)
    if tm.empty:
        return pd.DataFrame(), pd.DataFrame()

    tm = tm[tm["player_name"].notna()].copy()
    tm = tm[tm["player_name"].astype(str).str.strip() != ""]
    if starter_names:
        tm = tm[tm["player_name"].isin(starter_names)]
    if tm.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Assign a unique integer row key so event_id collisions across matches
    # (each file starts event_id from 1) never corrupt the receiver merge.
    tm = tm.reset_index(drop=True)
    tm["__row_key"] = tm.index

    passes = tm[(tm["is_pass"]) & (tm["outcome"] == 1)].copy()
    if passes.empty:
        return pd.DataFrame(), pd.DataFrame()

    tm_names = tm[["__row_key", "player_name"]].copy()
    tm_names = tm_names.reset_index(drop=True)
    tm_names["receiver_name"] = tm_names["player_name"].shift(-1)

    # Null out receiver assignments that cross match boundaries (Range mode).
    if "__match_index" in tm.columns:
        boundary = tm["__match_index"].values
        cross = boundary != np.roll(boundary, -1)
        cross[-1] = True  # last event has no valid receiver
        tm_names.loc[cross, "receiver_name"] = None

    pass_seq = passes.merge(tm_names[["__row_key", "receiver_name"]], on="__row_key", how="left")
    pass_seq = pass_seq[pass_seq["receiver_name"].notna()]
    pass_seq = pass_seq[pass_seq["receiver_name"].astype(str).str.strip() != ""]
    pass_seq = pass_seq[pass_seq["player_name"] != pass_seq["receiver_name"]]
    if pass_seq.empty:
        return pd.DataFrame(), pd.DataFrame()

    edges = pass_seq.groupby(["player_name", "receiver_name"], as_index=False).agg(
        pass_count=("event_id", "count")
    )
    edges = edges[edges["pass_count"] >= min_edge_count]
    if edges.empty:
        return pd.DataFrame(), pd.DataFrame()

    involvement = pd.concat([
        edges[["player_name", "pass_count"]].rename(columns={"player_name": "player"}),
        edges[["receiver_name", "pass_count"]].rename(columns={"receiver_name": "player"}),
    ], ignore_index=True).groupby("player", as_index=False).sum()
    involvement = involvement.sort_values("pass_count", ascending=False)
    keep_players = set(involvement.head(max_players)["player"].tolist())

    edges = edges[
        edges["player_name"].isin(keep_players) & edges["receiver_name"].isin(keep_players)
    ].copy()
    if edges.empty:
        return pd.DataFrame(), pd.DataFrame()

    player_pos = tm[tm["player_name"].isin(keep_players)].groupby("player_name", as_index=False).agg(
        x=("x", "median"),
        y=("y", "median"),
        touches=("event_id", "count"),
    )
    player_pos = player_pos.rename(columns={"player_name": "player"})

    player_passes = involvement.rename(columns={"pass_count": "involvement"})
    nodes = player_pos.merge(player_passes, on="player", how="left")
    nodes["involvement"] = nodes["involvement"].fillna(0)

    return nodes, edges.sort_values("pass_count", ascending=False).head(36)


def _build_shot_zone_grid(shots: pd.DataFrame, bins_x: int = 12, bins_y: int = 12):
    if shots is None or shots.empty:
        return None, None, None, None

    x = shots["x"].astype(float).clip(0, 100)
    y = shots["y"].astype(float).clip(0, 100)
    x_edges = np.linspace(0, 100, bins_x + 1)
    y_edges = np.linspace(0, 100, bins_y + 1)
    hist, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges])

    total = float(hist.sum())
    pct = (hist / total * 100.0) if total > 0 else hist
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2.0
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2.0

    return pct.T, x_centers, y_centers, total, x_edges, y_edges


# ============================================================================
# LAYOUT
# ============================================================================

def layout(competition="LaLiga", season="2025-2026"):
    default_opts = get_match_options(competition, season)
    default_val  = default_opts[0]["value"] if default_opts else None

    return html.Div([
        html.Div([
            html.H4("Match Analysis", className="rm-page-title"),
            html.P("Event-level tactical breakdown — real Opta data",
                   className="rm-page-subtitle"),
        ], className="rm-page-header"),

        # Primary selection
        dbc.Card(dbc.CardBody([
            html.P("Competition / Season / Venue / Match", className="section-header mb-2", id="ma-primary-title"),
            html.Small("Choose the context and exact match for analysis.", className="text-muted d-block mb-3", id="ma-primary-help"),
            dbc.Row([
                dbc.Col([
                    html.Label("Analysis Mode", className="filter-label"),
                    dcc.Dropdown(
                        id="ma-analysis-mode",
                        options=[
                            {"label": "Single Match", "value": "Single"},
                            {"label": "Match Range", "value": "Range"},
                        ],
                        value="Single",
                        clearable=False,
                    ),
                ], md=2),
                dbc.Col([
                    html.Label("Competition", className="filter-label"),
                    dcc.Dropdown(id="ma-competition",
                                 options=get_competition_options(),
                                 value=competition, clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("Season", className="filter-label"),
                    dcc.Dropdown(id="ma-season",
                                 options=get_season_options(competition),
                                 value=season, clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("Venue", className="filter-label"),
                    dcc.Dropdown(id="ma-venue",
                                 options=[{"label": "All", "value": "All"},
                                          {"label": "Home 🏠", "value": "Home"},
                                          {"label": "Away ✈️", "value": "Away"}],
                                 value="All", clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("Phase Focus", className="filter-label"),
                    dcc.Dropdown(
                        id="ma-phase-focus",
                        options=[
                            {"label": "All Phases", "value": "All"},
                            {"label": "Offensive", "value": "Offensive"},
                            {"label": "Defensive", "value": "Defensive"},
                            {"label": "Transitions", "value": "Transitions"},
                            {"label": "Set Pieces", "value": "SetPieces"},
                        ],
                        value="All",
                        clearable=False,
                    ),
                ], md=4),
            ], className="g-2"),
            dbc.Row([
                dbc.Col([
                    html.Label("Select Match", className="filter-label"),
                    dcc.Dropdown(id="ma-match-selector",
                                 options=default_opts,
                                 value=default_val, clearable=False,
                                 placeholder="Choose a match…"),
                ], md=12, id="ma-single-match-col"),
            ], className="g-2"),
        ]), className="filter-section mb-3"),

        # Match range filter
        dbc.Card(dbc.CardBody([
            html.P("Match Range", className="section-header mb-2", id="ma-range-title"),
            html.Small("Use this only to narrow which matches are available in Select Match.", className="text-muted d-block mb-3", id="ma-range-help"),
            dbc.Row([
                dbc.Col([
                    html.Label("Match Range: From", className="filter-label"),
                    dcc.Dropdown(id="ma-from-match", options=default_opts,
                                 value=default_val, clearable=False),
                ], md=4),
                dbc.Col([
                    html.Label("Match Range: To", className="filter-label"),
                    dcc.Dropdown(id="ma-to-match", options=default_opts,
                                 value=(default_opts[-1]["value"] if default_opts else default_val),
                                 clearable=False),
                ], md=4),
            ], className="g-2"),
        ]), className="filter-section mb-4", id="ma-range-card"),

        # Match header
        dcc.Loading(html.Div(id="ma-match-header", className="mb-3"),
                    type="circle", color=_RM),

        # KPI row
        dcc.Loading(dbc.Row(id="ma-kpi-row", className="g-2 mb-4"),
                    type="circle", color=_RM),

        # Shot map + xG chart
        dbc.Card([
            dbc.CardHeader("Shot Map"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-shot-map",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("xG Accumulation by Minute"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-xg-chart",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Tactical bars + pass map
        dbc.Card([
            dbc.CardHeader("Tactical Comparison"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-tactical-bars",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Pass Map (RM successful passes)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-pass-map",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader(dbc.Row([
                dbc.Col("Pass Network (RM)", className="d-flex align-items-center"),
                dbc.Col(dbc.RadioItems(
                    id="ma-network-scope",
                    options=[
                        {"label": " Starting XI", "value": "xi"},
                        {"label": " Full Match", "value": "full"},
                    ],
                    value="xi",
                    inline=True,
                    inputClassName="me-1",
                    labelClassName="me-3 small",
                ), width="auto", className="d-flex align-items-center"),
            ], className="g-0 justify-content-between align-items-center")),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-pass-network",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Shot Zone Map (RM)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-shot-zone-map",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Starting XIs Shape (Selected Match)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-lineup-pitch",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Player table
        dbc.Card([
            dbc.CardHeader("Real Madrid Player Performance"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(
                        dcc.RadioItems(
                            id="ma-lineup-filter",
                            options=[
                                {"label": " All Players", "value": "All"},
                                {"label": " Starting 11", "value": "Starting 11"},
                                {"label": " Sub On", "value": "Sub On"},
                            ],
                            value="Starting 11",
                            inline=True,
                            inputStyle={"marginRight": "4px"},
                            labelStyle={"marginRight": "16px", "fontSize": "0.85rem"},
                        ), md=12
                    ),
                ], className="mb-2"),
                dcc.Loading(
                    html.Div(id="ma-player-table"),
                    type="circle", color=_RM),
            ]),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Match Tactical Sub-Phases (A/B/C/D)"),
            dbc.CardBody([
                dbc.Alert([
                    html.B("Phase Index (0–100): "),
                    "A composite score measuring Real Madrid's effectiveness in each of the 4 tactical moments. ",
                    html.Br(),
                    html.Span([
                        html.B("A – Offensive Moment: "), "Quality of possession & attacking output (pass accuracy 45% + xG 35% + shots 20%). "
                    ]),
                    html.Br(),
                    html.Span([
                        html.B("B – Defensive Transition: "), "Press intensity & ball regains after losing possession (PPDA 55% + recoveries/interceptions 45%). "
                    ]),
                    html.Br(),
                    html.Span([
                        html.B("C – Defensive Moment: "), "Defensive solidity when opponent has the ball (PPDA 40% + opponent shots suppressed 60%). "
                    ]),
                    html.Br(),
                    html.Span([
                        html.B("D – Offensive Transition: "), "Danger created immediately after winning the ball (regain-to-shot rate within 15s = 65% + xG 35%). "
                    ]),
                    html.Br(),
                    html.Small("Scores are within-match relative — compare phases against each other, not as an absolute benchmark.", className="text-muted"),
                ], color="dark", className="py-2 px-3 mb-2", style={"fontSize": "0.78rem", "borderLeft": f"4px solid {_RM}"}),
                dcc.Loading(
                    dcc.Graph(id="ma-subphase-chart", config={"responsive": True, "displayModeBar": False}),
                    type="circle", color=_RM),
            ]),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Transition Metrics"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-transition-chart", config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Set Piece Efficiency"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-setpiece-chart", config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Post-Match Tactical Summary"),
            dbc.CardBody(dcc.Loading(
                html.Div(id="ma-post-summary"),
                type="circle", color=_RM)),
        ], className="mb-3"),

    ], className="page-content")


# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output("ma-season", "options"),
    Output("ma-season", "value"),
    Input("ma-competition", "value"),
    State("ma-season", "value"),
)
def _season_opts(competition, current):
    comp = competition or "LaLiga"
    opts = get_season_options(comp)
    vals = [o["value"] for o in opts]
    val  = current if current in vals else (opts[0]["value"] if opts else "2025-2026")
    return opts, val

@callback(
    Output("ma-primary-title", "children"),
    Output("ma-primary-help", "children"),
    Output("ma-range-title", "children"),
    Output("ma-range-help", "children"),
    Output("ma-single-match-col", "style"),
    Output("ma-range-card", "style"),
    Input("ma-analysis-mode", "value"),
)
def _analysis_mode_visibility(mode):
    if mode == "Range":
        return (
            "Competition / Season / Venue / Analysis Setup",
            "Choose the context for aggregate analysis across multiple matches.",
            "Match Range",
            "Select the start and end match for the range analysis below.",
            {"display": "none"},
            {"display": "block"},
        )
    return (
        "Competition / Season / Venue / Match",
        "Choose the context and exact match for analysis.",
        "Match Range",
        "Optional: narrow which matches are available in Select Match.",
        {"display": "block"},
        {"display": "none"},
    )


@callback(
    Output("ma-from-match", "options"),
    Output("ma-from-match", "value"),
    Output("ma-to-match", "options"),
    Output("ma-to-match", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
)
def _match_range_opts(competition, season, venue):
    opts = get_match_options(competition or "LaLiga", season or "2025-2026", venue or "All")
    if not opts:
        return [], None, [], None
    return opts, opts[0]["value"], opts, opts[-1]["value"]


@callback(
    Output("ma-match-selector", "options"),
    Output("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
)
def _match_opts(competition, season, venue, from_match, to_match):
    full_opts = get_match_options(competition or "LaLiga", season or "2025-2026", venue or "All")
    if not full_opts:
        return [], None

    value_to_idx = {o["value"]: i for i, o in enumerate(full_opts)}
    i0 = value_to_idx.get(from_match, 0)
    i1 = value_to_idx.get(to_match, len(full_opts) - 1)
    lo, hi = (i0, i1) if i0 <= i1 else (i1, i0)

    opts = full_opts[lo:hi + 1] if full_opts else []
    val = opts[0]["value"] if opts else (full_opts[0]["value"] if full_opts else None)
    return opts, val


def _load(file_path):
    if not file_path:
        return None, None, None
    data   = load_match_json(file_path)
    if not data:
        return None, None, None
    meta   = extract_match_meta(data)
    events = parse_events(data)
    return data, meta, events


def _selected_range_files(competition, season, venue, from_match, to_match) -> list[str]:
    full_opts = get_match_options(competition or "LaLiga", season or "2025-2026", venue or "All")
    if not full_opts:
        return []
    value_to_idx = {o["value"]: i for i, o in enumerate(full_opts)}
    i0 = value_to_idx.get(from_match, 0)
    i1 = value_to_idx.get(to_match, len(full_opts) - 1)
    lo, hi = (i0, i1) if i0 <= i1 else (i1, i0)
    return [o["value"] for o in full_opts[lo:hi + 1]]


def _load_scope(mode, file_path, competition, season, venue, from_match, to_match):
    if mode != "Range":
        data, meta, events = _load(file_path)
        payloads = [(file_path, meta, events)] if meta is not None and events is not None else []
        return payloads

    file_paths = _selected_range_files(competition, season, venue, from_match, to_match)
    payloads = []
    for fp in file_paths:
        data, meta, events = _load(fp)
        if meta is None or events is None or events.empty:
            continue
        payloads.append((fp, meta, events))
    return payloads


def _aggregate_scope_events(payloads):
    if not payloads:
        return None, None, pd.DataFrame()

    metas = [meta for _, meta, _ in payloads]
    frames = []
    for idx, (_, meta, events) in enumerate(payloads):
        frame = events.copy()
        frame["__match_index"] = idx
        frame["__match_label"] = f"MD{meta.get('week', '?')} {meta.get('opponent', 'OPP')}"
        frames.append(frame)
    return metas[0], metas, pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _aggregate_scope_kpis(payloads) -> dict:
    if not payloads:
        return {}

    first_meta, metas, events = _aggregate_scope_events(payloads)
    rm_id = first_meta["rm_id"]
    rm_ev = events[events["contestant_id"] == rm_id]
    opp_ev = events[events["contestant_id"] != rm_id]
    rm_passes = rm_ev[rm_ev["is_pass"]]
    opp_passes = opp_ev[opp_ev["is_pass"]]
    total_passes = len(rm_passes) + len(opp_passes)
    rm_def = rm_ev[(rm_ev["type_id"].isin({7, 8, 49})) & (rm_ev["x"] >= 40)]
    opp_passes_att = opp_ev[(opp_ev["is_pass"]) & (opp_ev["x"] >= 40)]

    wins = sum(1 for m in metas if m["rm_score"] > m["opp_score"])
    draws = sum(1 for m in metas if m["rm_score"] == m["opp_score"])
    losses = len(metas) - wins - draws

    return {
        "match_count": len(metas),
        "goals_for": int(sum(m["rm_score"] for m in metas)),
        "goals_against": int(sum(m["opp_score"] for m in metas)),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "possession": round(len(rm_passes) / total_passes * 100, 1) if total_passes else 0,
        "pass_accuracy": round(rm_passes["outcome"].mean() * 100, 1) if len(rm_passes) else 0,
        "shots_total": int(rm_ev["is_shot"].sum()),
        "xg_for": round(float(rm_ev["xg"].dropna().sum()), 2),
        "xg_against": round(float(opp_ev["xg"].dropna().sum()), 2),
        "ppda": round(len(opp_passes_att) / (len(rm_def) or 1), 2),
        "first_meta": first_meta,
        "metas": metas,
        "events": events,
    }


# ---------------------------------------------------------------------------
# Phase Focus — filter event-driven visuals by phase of play
# ---------------------------------------------------------------------------
_PHASE_LABELS = {
    "All": "All Phases", "Offensive": "Offensive", "Defensive": "Defensive",
    "Transitions": "Transitions", "SetPieces": "Set Pieces",
}


def _phase_label(phase) -> str:
    return _PHASE_LABELS.get(phase or "All", "All Phases")


def _event_seconds(df: pd.DataFrame) -> pd.Series:
    """Absolute time of each event in seconds (period-aware)."""
    if df.empty:
        return pd.Series([], dtype=float, index=df.index)
    period = df["period"].fillna(1).astype(int) if "period" in df.columns else 1
    return (period * 100000
            + df["minute"].fillna(0).astype(int) * 60
            + df["second"].fillna(0).astype(int))


def _regain_seconds(events: pd.DataFrame, team_id: str) -> np.ndarray:
    """Times (s) at which `team_id` regains the ball (tackle / interception / recovery)."""
    reg = events[(events["contestant_id"] == team_id)
                 & (events["is_tackle"] | events["is_interception"] | events["is_recovery"])]
    return np.sort(_event_seconds(reg).to_numpy()) if not reg.empty else np.array([])


def _restart_seconds(events: pd.DataFrame, team_id: str) -> np.ndarray:
    """Times (s) of set-piece restarts for `team_id` (corners=6, free kicks=5)."""
    sp = events[(events["contestant_id"] == team_id) & (events["type_id"].isin({5, 6}))]
    return np.sort(_event_seconds(sp).to_numpy()) if not sp.empty else np.array([])


def _within_window_mask(df: pd.DataFrame, anchor_secs: np.ndarray, window: int = 15) -> pd.Series:
    """True for rows whose time falls within `window` seconds AFTER any anchor time."""
    if df.empty or anchor_secs.size == 0:
        return pd.Series(False, index=df.index)
    t = _event_seconds(df).to_numpy()
    # for each event time, is there an anchor a with a <= t <= a+window ?
    keep = np.zeros(len(t), dtype=bool)
    for i, v in enumerate(t):
        keep[i] = bool(((anchor_secs <= v) & (v <= anchor_secs + window)).any())
    return pd.Series(keep, index=df.index)


def _phase_filter_shots(rm_shots, opp_shots, events, meta, phase):
    """Return (rm_shots, opp_shots) reduced to the selected phase of play."""
    phase = phase or "All"
    if phase == "Offensive":          # RM with the ball → RM shots only
        return rm_shots, opp_shots.iloc[0:0]
    if phase == "Defensive":          # RM defending → shots faced only
        return rm_shots.iloc[0:0], opp_shots
    if phase == "Transitions":        # shots soon after a regain
        rm = rm_shots[_within_window_mask(rm_shots, _regain_seconds(events, meta["rm_id"]), 15)]
        opp = opp_shots[_within_window_mask(opp_shots, _regain_seconds(events, meta["opp_id"]), 15)]
        return rm, opp
    if phase == "SetPieces":          # shots soon after a set-piece restart
        rm = rm_shots[_within_window_mask(rm_shots, _restart_seconds(events, meta["rm_id"]), 12)]
        opp = opp_shots[_within_window_mask(opp_shots, _restart_seconds(events, meta["opp_id"]), 12)]
        return rm, opp
    return rm_shots, opp_shots


def _phase_filter_passes(passes, events, team_id, phase):
    """Reduce a team's passes to the selected phase of play."""
    phase = phase or "All"
    if passes.empty or phase == "All":
        return passes
    if phase == "Offensive":          # progression into / within attacking half
        end_x = passes["end_x"].fillna(passes["x"])
        return passes[(passes["x"] >= 50) | (end_x >= 50)]
    if phase == "Defensive":          # build-up / circulation in own half
        return passes[passes["x"] < 50]
    if phase == "Transitions":        # passes shortly after a regain
        return passes[_within_window_mask(passes, _regain_seconds(events, team_id), 15)]
    if phase == "SetPieces":          # passes shortly after a set-piece restart
        return passes[_within_window_mask(passes, _restart_seconds(events, team_id), 12)]
    return passes


@callback(
    Output("ma-match-header", "children"),
    Output("ma-kpi-row", "children"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
)
def _update_header(mode, file_path, competition, season, venue, from_match, to_match):
    if mode == "Range":
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match)
        agg = _aggregate_scope_kpis(payloads)
        if not agg:
            return dbc.Alert("Select a valid match range to begin.", color="info"), []

        metas = agg["metas"]
        header = dbc.Card(dbc.CardBody([
            html.H4(f"Range Analysis: {len(metas)} matches", className="mb-1"),
            html.P(
                f"From MD {metas[0].get('week', '?')} to MD {metas[-1].get('week', '?')} · "
                f"Record {agg['wins']}-{agg['draws']}-{agg['losses']}",
                className="text-muted mb-0",
            ),
        ]), style={"borderLeft": f"4px solid {_RM}"})

        kpi_cards = [
            _kpi_card("Goals For", agg["goals_for"], _C["accent_green"], sub=f"{agg['match_count']} matches"),
            _kpi_card("Goals Against", agg["goals_against"], _C["accent_red"], sub=f"W-D-L {agg['wins']}-{agg['draws']}-{agg['losses']}"),
            _kpi_card("Possession %", f"{agg['possession']}%", _C["accent_blue"], sub="Range aggregate"),
            _kpi_card("Pass Accuracy", f"{agg['pass_accuracy']}%", _C["accent_blue"], sub=f"{agg['shots_total']} shots total"),
            _kpi_card("PPDA", agg["ppda"], _C["accent_purple"], sub="Range aggregate"),
            _kpi_card("xG For / Against", f"{agg['xg_for']} / {agg['xg_against']}", _C["accent_orange"]),
        ]
        return header, kpi_cards

    _, meta, events = _load(file_path)
    if meta is None:
        return dbc.Alert("Select a match to begin.", color="info"), []

    kpis = calc_match_kpis(events, meta)
    ppda = calc_ppda(events, meta)

    rc, rt = (
        (_C["accent_green"], "WIN")  if meta["rm_score"] > meta["opp_score"] else
        (_C["accent_yellow"], "DRAW") if meta["rm_score"] == meta["opp_score"] else
        (_C["accent_red"],   "LOSS")
    )

    header = dbc.Card(dbc.CardBody(dbc.Row([
        dbc.Col([
            html.H3(meta["home_team"], className="mb-0 text-end"),
            html.Small(meta["competition"], className="text-muted"),
        ], md=4, className="d-flex flex-column align-items-end justify-content-center"),
        dbc.Col([
            html.H2(meta["score_str"], className="mb-1 text-center",
                    style={"color": rc, "fontWeight": 700, "fontSize": "2.5rem"}),
            dbc.Badge(rt,
                      color=("success" if rt == "WIN" else
                             "warning" if rt == "DRAW" else "danger"),
                      className="d-block mx-auto text-center mb-1",
                      style={"width": "70px"}),
            html.P(f"MD {meta.get('week', '')}  ·  {meta['date']}",
                   className="text-muted text-center small mb-0"),
            html.Small(meta.get("venue_name", ""),
                       className="text-muted text-center d-block"),
        ], md=4, className="text-center"),
        dbc.Col([
            html.H3(meta["away_team"], className="mb-0"),
        ], md=4, className="d-flex align-items-center"),
    ], align="center")), style={"borderLeft": f"4px solid {rc}"}),

    kpi_cards = [
        _kpi_card("Goals For",         meta["rm_score"],             _C["accent_green"]),
        _kpi_card("Goals Against",     meta["opp_score"],            _C["accent_red"]),
        _kpi_card("Possession %",      f"{kpis['possession']}%",     _C["accent_blue"],
                  sub=f"{kpis['passes_total']} passes"),
        _kpi_card("Pass Accuracy",     f"{kpis['pass_accuracy']}%",  _C["accent_blue"],
                  sub=f"{kpis['shots_total']} shots total"),
        _kpi_card("PPDA",              ppda,                         _C["accent_purple"],
                  sub="Lower = more press"),
        _kpi_card("xG For / Against",
                  f"{kpis['xg_for']} / {kpis['xg_against']}",       _C["accent_orange"]),
    ]
    return header, kpi_cards

@callback(
    Output("ma-shot-map", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-phase-focus", "value"),
)
def _shot_map(mode, file_path, competition, season, venue, from_match, to_match, phase_focus="All"):
    _, meta, events = _load(file_path)

    def _base():
        f = go.Figure()
        f.update_layout(**{**_PL, "plot_bgcolor": _PITCH_FILL}, height=_H_PITCH,
                        shapes=_pitch_stripes_full() + _pitch_shapes_full(),
                        xaxis=dict(range=[0, 102], showticklabels=False,
                                   showgrid=False, zeroline=False),
                        yaxis=dict(range=[0, 100], showticklabels=False,
                                   showgrid=False, zeroline=False,
                                   scaleanchor="x", scaleratio=0.68),
                        title="Shot Map")
        return _add_pitch_context_labels(f, full_pitch=True)

    if mode == "Range":
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match)
        if not payloads:
            return _base()
        first_meta, metas, events = _aggregate_scope_events(payloads)
        meta = first_meta

    if meta is None:
        return _base()

    shots = get_shot_data(events, meta)
    if shots.empty:
        fig = _base()
        fig.add_annotation(text="No shots recorded", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    rm_shots  = shots[shots["contestant_id"] == meta["rm_id"]]
    opp_shots = shots[shots["contestant_id"] == meta["opp_id"]]
    rm_shots, opp_shots = _phase_filter_shots(rm_shots, opp_shots, events, meta, phase_focus)

    def _colors(df, team_color):
        # Colour by TEAM (so RM vs opponent are distinguishable); goals = gold.
        return [_GOLD if r["is_goal"] else team_color for _, r in df.iterrows()]

    def _sizes(df):
        # Marker size scales gently with xG (chance quality); goals slightly larger.
        sizes = []
        for _, r in df.iterrows():
            raw = r.get("xg_display", r.get("xg", 0))
            xg_val = 0.0 if pd.isna(raw) else float(raw)
            s = 9.0 + xg_val * 22.0
            sizes.append(s + 5.0 if r["is_goal"] else s)
        return sizes

    def _syms(df):
        return ["star" if r["is_goal"] else
                "diamond-open" if r["is_shot_on_target"] else "x"
                for _, r in df.iterrows()]

    def _xg_text(v):
        if pd.isna(v):
            return "N/A"
        return f"{float(v):.3f}"

    fig = _base()
    _ph = _phase_label(phase_focus)
    _ph_sfx = "" if (phase_focus or "All") == "All" else f" · {_ph}"
    title = (f"{meta['home_team']} vs {meta['away_team']} — Shot Map{_ph_sfx}"
             if mode != "Range" else f"Match Range Shot Map ({len(payloads)} matches){_ph_sfx}")
    fig.update_layout(title=title)

    if rm_shots.empty and opp_shots.empty:
        fig.add_annotation(text=f"No shots in the selected phase ({_ph})",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                           font=dict(size=13, color=_C["text_secondary"]))
        return fig

    if not rm_shots.empty:
        fig.add_trace(go.Scatter(
            x=rm_shots["x"], y=rm_shots["y"],
            mode="markers", name="Real Madrid",
            marker=dict(color=_colors(rm_shots, _RM), size=_sizes(rm_shots),
                        symbol=_syms(rm_shots),
                        line=dict(color="white", width=1.5)),
            text=[f"{r['player_name']}<br>{r['event_type']}<br>Min {r['minute']}'<br>"
                f"xG {_xg_text(r.get('xg_display'))}"
                  for _, r in rm_shots.iterrows()],
            hovertemplate="%{text}<extra></extra>",
        ))

    if not opp_shots.empty:
        # Opta coords are team-relative (each team's x=100 is their attacking goal).
        # Mirror opp shots so they appear at RM's defensive end (x near 0).
        opp_x = 100 - opp_shots["x"]
        opp_y = 100 - opp_shots["y"]
        fig.add_trace(go.Scatter(
            x=opp_x, y=opp_y,
            mode="markers", name=meta["opponent"],
            marker=dict(color=_colors(opp_shots, _OPP), size=_sizes(opp_shots),
                        symbol=_syms(opp_shots), opacity=0.85,
                        line=dict(color="white", width=1)),
            text=[f"{r['player_name']}<br>{r['event_type']}<br>Min {r['minute']}'<br>"
                f"xG {_xg_text(r.get('xg_display'))}"
                  for _, r in opp_shots.iterrows()],
            hovertemplate="%{text}<extra></extra>",
        ))

    rm_name = _rm_team_name(meta)
    fig = _add_direction_arrows(fig, meta["opponent"], rm_name)
    fig.add_annotation(
        text="Colour = team · size = shot quality (xG) · ★ Goal  ◆ On Target  ✕ Off/Blocked  ·  RM attacks → right",
        xref="paper", yref="paper", x=0.5, y=-0.06,
        showarrow=False, font=dict(size=10, color=_C["text_secondary"]),
    )
    return fig

@callback(
    Output("ma-xg-chart", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
)
def _xg_chart(mode, file_path, competition, season, venue, from_match, to_match):
    _, meta, events = _load(file_path)

    def _base():
        f = go.Figure()
        f.update_layout(**_PL, height=_H_COMPARE, title="xG Accumulation")
        return f

    if mode == "Range":
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match)
        if not payloads:
            return _base()
        fig = go.Figure()
        labels, rm_vals, opp_vals = [], [], []
        for _, m, ev in payloads:
            labels.append(f"MD{m.get('week', '?')} {m.get('opponent', 'OPP')}")
            rm_vals.append(round(float(ev[(ev['contestant_id'] == m['rm_id']) & (ev['is_shot'])]['xg'].dropna().sum()), 2))
            opp_vals.append(round(float(ev[(ev['contestant_id'] != m['rm_id']) & (ev['is_shot'])]['xg'].dropna().sum()), 2))
        fig.add_trace(go.Bar(x=labels, y=rm_vals, name="Real Madrid", marker_color=_RM))
        fig.add_trace(go.Bar(x=labels, y=opp_vals, name="Opponents", marker_color=_OPP, opacity=0.85))
        fig.update_layout(**_PL, height=_H_COMPARE, title="xG By Match (Selected Range)", barmode="group",
                          xaxis=dict(tickangle=-45, gridcolor=_C["border"], automargin=True),
                          yaxis=dict(title="xG", gridcolor=_C["border"], automargin=True))
        return fig

    if meta is None:
        return _base()

    shots = events[events["is_shot"]].copy() if not events.empty else pd.DataFrame()
    if shots.empty:
        f = _base()
        f.add_annotation(text="No shot data available", xref="paper", yref="paper",
                         x=0.5, y=0.5, showarrow=False)
        return f

    shots = shots.sort_values("minute")
    minutes = list(range(0, 97))

    def _cum_xg(team_id):
        t = shots[shots["contestant_id"] == team_id].copy()
        cum, vals = 0.0, [0.0]
        for m in minutes:
            cum += t[t["minute"] == m]["xg"].dropna().sum()
            vals.append(cum)
        return vals

    rm_xg  = _cum_xg(meta["rm_id"])
    opp_xg = _cum_xg(meta["opp_id"])
    mins   = [0] + minutes

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=mins, y=rm_xg, name="Real Madrid",
        line=dict(color=_RM, width=2.5), fill="tozeroy",
        fillcolor="rgba(37,99,235,0.12)",
        hovertemplate="Min %{x}<br>RM xG: %{y:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=mins, y=opp_xg, name=meta["opponent"],
        line=dict(color=_OPP, width=2.5), fill="tozeroy",
        fillcolor="rgba(220,38,38,0.10)",
        hovertemplate="Min %{x}<br>Opp xG: %{y:.3f}<extra></extra>",
    ))

    goals = events[events["is_goal"]] if not events.empty else pd.DataFrame()
    for _, g in goals.iterrows():
        clr  = _RM if g["contestant_id"] == meta["rm_id"] else _OPP
        name = g["player_name"].split()[-1] if g["player_name"] else "?"
        fig.add_vline(x=g["minute"], line=dict(color=clr, dash="dot", width=1.5),
                      annotation_text=f"⚽ {name} {g['minute']}'",
                      annotation_font_size=9)

    fig.update_layout(**_PL, height=_H_COMPARE,
                      title="xG Accumulation Over Time",
                      xaxis=dict(title="Minute", range=[0, 96],
                                 gridcolor=_C["border"], automargin=True),
                      yaxis=dict(title="Cumulative xG",
                                 gridcolor=_C["border"], automargin=True))
    return fig

@callback(
    Output("ma-tactical-bars", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
)
def _tactical_bars(mode, file_path, competition, season, venue, from_match, to_match):
    _, meta, events = _load(file_path)

    if mode == "Range":
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match)
        if not payloads:
            return go.Figure().update_layout(**_PL, height=_H_COMPARE, title="Tactical Stats Comparison")
        rm_avgs = np.zeros(6)
        opp_avgs = np.zeros(6)
        for _, m, ev in payloads:
            kpis = calc_match_kpis(ev, m)
            opp_meta = {**m, "rm_id": m["opp_id"], "opp_id": m["rm_id"], "rm_score": m["opp_score"], "opp_score": m["rm_score"]}
            opp_kpis = calc_match_kpis(ev, opp_meta)
            rm_avgs += np.array([kpis["shots_total"], kpis["shots_on_target"], kpis["tackles"], kpis["interceptions"], kpis["ball_recoveries"], kpis["corners"]])
            opp_avgs += np.array([opp_kpis["shots_total"], opp_kpis["shots_on_target"], opp_kpis["tackles"], opp_kpis["interceptions"], opp_kpis["ball_recoveries"], opp_kpis["corners"]])
        rm_vals = (rm_avgs / len(payloads)).round(1).tolist()
        opp_vals = (opp_avgs / len(payloads)).round(1).tolist()
        categories = ["Shots", "On Target", "Tackles", "Interceptions", "Ball Recoveries", "Corners"]
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Real Madrid", y=categories, x=rm_vals, orientation="h", marker_color=_RM, text=[str(v) for v in rm_vals], textposition="auto"))
        fig.add_trace(go.Bar(name="Opponents Avg", y=categories, x=opp_vals, orientation="h", marker_color=_OPP, opacity=0.85, text=[str(v) for v in opp_vals], textposition="auto"))
        fig.update_layout(**_PL, height=_H_COMPARE, barmode="group", title="Tactical Stats Comparison (Per Match Average)",
                          xaxis=dict(gridcolor=_C["border"], automargin=True), yaxis=dict(gridcolor=_C["border"], automargin=True))
        return fig

    def _base():
        f = go.Figure()
        f.update_layout(**_PL, height=_H_COMPARE, title="Tactical Comparison")
        return f

    if meta is None:
        return _base()

    kpis = calc_match_kpis(events, meta)
    opp_meta = {**meta, "rm_id": meta["opp_id"], "opp_id": meta["rm_id"],
                "rm_score": meta["opp_score"], "opp_score": meta["rm_score"]}
    opp_kpis = calc_match_kpis(events, opp_meta)

    categories = [
        "Shots", "Shots On Target",
        "Tackles", "Interceptions",
        "Ball Recoveries", "Corners",
    ]
    rm_vals  = [kpis["shots_total"], kpis["shots_on_target"],
                kpis["tackles"], kpis["interceptions"],
                kpis["ball_recoveries"], kpis["corners"]]
    opp_vals = [opp_kpis["shots_total"], opp_kpis["shots_on_target"],
                opp_kpis["tackles"], opp_kpis["interceptions"],
                opp_kpis["ball_recoveries"], opp_kpis["corners"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Real Madrid", y=categories, x=rm_vals,
                         orientation="h", marker_color=_RM,
                         text=[str(v) for v in rm_vals], textposition="auto"))
    fig.add_trace(go.Bar(name=meta["opponent"], y=categories, x=opp_vals,
                         orientation="h", marker_color=_OPP, opacity=0.85,
                         text=[str(v) for v in opp_vals], textposition="auto"))
    fig.update_layout(**_PL, height=_H_COMPARE, barmode="group",
                      title="Tactical Stats Comparison",
                      xaxis=dict(gridcolor=_C["border"], automargin=True),
                      yaxis=dict(gridcolor=_C["border"], automargin=True))
    return fig

@callback(
    Output("ma-pass-map", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-phase-focus", "value"),
)
def _pass_map(mode, file_path, competition, season, venue, from_match, to_match, phase_focus="All"):
    _, meta, events = _load(file_path)

    def _base():
        f = go.Figure()
        f.update_layout(**{**_PL, "plot_bgcolor": _PITCH_FILL}, height=_H_PITCH,
                        shapes=_pitch_stripes_full() + _pitch_shapes_full(),
                        xaxis=dict(range=[0, 100], showticklabels=False,
                                   showgrid=False, zeroline=False),
                        yaxis=dict(range=[0, 100], showticklabels=False,
                                   showgrid=False, zeroline=False,
                                   scaleanchor="x", scaleratio=0.68),
                        title="Pass Map")
        return _add_pitch_context_labels(f, full_pitch=True)

    if mode == "Range":
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match)
        if not payloads:
            return _base()
        meta, metas, events = _aggregate_scope_events(payloads)

    if meta is None:
        return _base()

    rm_passes = events[
        (events["contestant_id"] == meta["rm_id"]) &
        (events["is_pass"]) &
        (events["end_x"].notna())
    ].copy()

    rm_passes = _phase_filter_passes(rm_passes, events, meta["rm_id"], phase_focus)

    _ph = _phase_label(phase_focus)
    _ph_sfx = "" if (phase_focus or "All") == "All" else f" · {_ph}"
    if rm_passes.empty:
        fig = _base()
        fig.update_layout(title=f"Real Madrid Pass Map{_ph_sfx}")
        fig.add_annotation(text=f"No passes in the selected phase ({_ph})",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                           font=dict(size=13, color=_C["text_secondary"]))
        return fig

    # Sample for performance (max 400 passes)
    if len(rm_passes) > 400:
        rm_passes = rm_passes.sample(400, random_state=42)

    success = rm_passes[rm_passes["outcome"] == 1]
    fail    = rm_passes[rm_passes["outcome"] == 0]

    # Build pass lines as a single scatter with None separators (much faster)
    def _lines_trace(df, color, name, opacity):
        xs, ys = [], []
        for _, row in df.iterrows():
            xs += [row["x"], row["end_x"], None]
            ys += [row["y"], row["end_y"], None]
        return go.Scatter(
            x=xs, y=ys, mode="lines", name=name,
            line=dict(color=color, width=1.5),
            opacity=opacity, hoverinfo="skip",
        )

    fig = _base()
    fig.update_layout(title=("Real Madrid Pass Map" + _ph_sfx if mode != "Range" else f"Real Madrid Pass Map ({len(payloads)} matches){_ph_sfx}"))
    if not success.empty:
        fig.add_trace(_lines_trace(success, _RM,  "Completed",  0.65))
    if not fail.empty:
        fig.add_trace(_lines_trace(fail,    _OPP, "Incomplete", 0.55))

    # Dots at pass origins
    fig.add_trace(go.Scatter(
        x=rm_passes["x"], y=rm_passes["y"], mode="markers",
        marker=dict(color=_RM, size=3, opacity=0.5),
        hoverinfo="skip", showlegend=False,
    ))
    rm_name = _rm_team_name(meta)
    fig = _add_direction_arrows(fig, meta["opponent"], rm_name)
    fig.update_layout(legend=dict(bgcolor="rgba(0,0,0,0)"))
    return fig


@callback(
    Output("ma-pass-network", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-network-scope", "value"),
    Input("ma-phase-focus", "value"),
)
def _pass_network(mode, file_path, competition, season, venue, from_match, to_match, scope="xi", phase_focus="All"):
    _, meta, events = _load(file_path)
    scope = scope or "xi"

    fig = go.Figure()
    fig.update_layout(
        **{**_PL, "plot_bgcolor": _PITCH_FILL},
        height=_H_PITCH,
        shapes=_pitch_stripes_full() + _pitch_shapes_full(),
        xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68),
        title="Pass Network (Real Madrid)",
        showlegend=False,
    )

    if mode == "Range":
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match)
        if not payloads:
            fig.add_annotation(text="Select a valid range for pass-network analysis.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        meta, _, events = _aggregate_scope_events(payloads)

    if meta is None or events is None or events.empty:
        fig.add_annotation(text="Select a match to see pass network.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    # Phase focus: chain only the RM passes belonging to the selected phase so the
    # network reflects that phase of play. Opponent events are unused by the builder.
    _ph = _phase_label(phase_focus)
    if (phase_focus or "All") != "All":
        rm_all = events[events["contestant_id"] == meta["rm_id"]]
        rm_pass = rm_all[rm_all["is_pass"]]
        rm_pass_phase = _phase_filter_passes(rm_pass, events, meta["rm_id"], phase_focus)
        other = events[events["contestant_id"] != meta["rm_id"]]
        events = pd.concat([rm_pass_phase, other])

    # Starting-XI view restricts to the 11 starters; Full Match shows up to 14.
    starter_names = None
    max_players = 14
    if scope == "xi" and mode != "Range":
        lineup = get_match_lineup_status(events, meta["rm_id"])
        starter_names = {p for p, s in lineup.items() if s == "Starting 11"}
        max_players = 11
    nodes, edges = _build_pass_network(
        events, meta["rm_id"], min_edge_count=(3 if mode == "Range" else 2),
        starter_names=starter_names, max_players=max_players,
    )
    if nodes.empty or edges.empty:
        _msg = ("Insufficient connected pass data for this scope."
                if (phase_focus or "All") == "All"
                else f"Insufficient connected passes in the selected phase ({_ph}).")
        fig.add_annotation(text=_msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    node_map = {r["player"]: (r["x"], r["y"]) for _, r in nodes.iterrows()}
    max_edge = max(float(edges["pass_count"].max()), 1.0)

    for _, e in edges.iterrows():
        p1 = e["player_name"]
        p2 = e["receiver_name"]
        if p1 not in node_map or p2 not in node_map:
            continue
        x0, y0 = node_map[p1]
        x1, y1 = node_map[p2]
        w = 0.6 + (float(e["pass_count"]) / max_edge) * 4.0
        fig.add_trace(go.Scatter(
            x=[x0, x1],
            y=[y0, y1],
            mode="lines",
            line=dict(color="rgba(15,23,42,0.38)", width=w),
            hovertemplate=f"{p1} -> {p2}<br>Passes: {int(e['pass_count'])}<extra></extra>",
        ))

    max_inv = max(float(nodes["involvement"].max()), 1.0)
    fig.add_trace(go.Scatter(
        x=nodes["x"],
        y=nodes["y"],
        mode="markers+text",
        text=[_short_name(n) for n in nodes["player"]],
        textposition="bottom center",
        textfont=dict(size=9, color="#0f172a"),
        marker=dict(
            size=[10 + (float(v) / max_inv) * 18 for v in nodes["involvement"]],
            color=nodes["involvement"],
            colorscale="Blues",
            cmin=0,
            cmax=max_inv,
            opacity=0.95,
            line=dict(color="#0f172a", width=0.9),
        ),
        customdata=np.stack([nodes["player"], nodes["involvement"], nodes["touches"]], axis=-1),
        hovertemplate="%{customdata[0]}<br>Network involvement: %{customdata[1]:.0f}<br>Touches: %{customdata[2]:.0f}<extra></extra>",
    ))

    if mode == "Range":
        suffix = f" · {len(payloads)} matches (full squad)"
    else:
        suffix = " · Starting XI" if scope == "xi" else " · Full match squad"
    if (phase_focus or "All") != "All":
        suffix += f" · {_ph}"
    fig.update_layout(title=f"Real Madrid Pass Network — {len(nodes)} players{suffix}")
    fig.add_annotation(
        text="Edge width = completed pass volume · Node size/color = involvement",
        xref="paper", yref="paper", x=0.5, y=-0.06, showarrow=False,
        font=dict(size=10, color=_C["text_secondary"]),
    )
    return fig


@callback(
    Output("ma-shot-zone-map", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
)
def _shot_zone_map(mode, file_path, competition, season, venue, from_match, to_match):
    _, meta, events = _load(file_path)

    fig = go.Figure()
    fig.update_layout(
        **{**_PL, "plot_bgcolor": _PITCH_FILL},
        height=_H_PITCH,
        shapes=_pitch_stripes_full() + _pitch_shapes_full(),
        xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68),
        title="Shot Zone Map (Real Madrid)",
    )

    if mode == "Range":
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match)
        if not payloads:
            fig.add_annotation(text="Select a valid range for shot-zone analysis.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        meta, _, events = _aggregate_scope_events(payloads)

    if meta is None or events is None or events.empty:
        fig.add_annotation(text="Select a match to view shot zones.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    rm_shots = events[(events["contestant_id"] == meta["rm_id"]) & (events["is_shot"]) & events["x"].notna() & events["y"].notna()].copy()
    if rm_shots.empty:
        fig.add_annotation(text="No Real Madrid shots found for selected scope.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    z, x_centers, y_centers, total, x_edges, y_edges = _build_shot_zone_grid(rm_shots, bins_x=12, bins_y=12)
    max_pct = max(float(np.nanmax(z)), 1.0)

    # Build discrete zone boxes (reference style) instead of a smooth heatmap.
    for yi in range(len(y_centers)):
        for xi in range(len(x_centers)):
            val = float(z[yi, xi])
            x0 = float(x_edges[xi])
            x1 = float(x_edges[xi + 1])
            y0 = float(y_edges[yi])
            y1 = float(y_edges[yi + 1])

            if val > 0:
                alpha = 0.24 + 0.70 * (val / max_pct)
                fig.add_shape(
                    type="rect",
                    x0=x0,
                    x1=x1,
                    y0=y0,
                    y1=y1,
                    line=dict(width=0),
                    fillcolor=f"rgba(22,163,74,{alpha:.3f})",
                    layer="below",
                )

    # Subtle grid guides to improve readability of zone percentages.
    for x in x_edges:
        fig.add_shape(
            type="line",
            x0=float(x), x1=float(x), y0=0, y1=100,
            line=dict(color="rgba(15,23,42,0.08)", width=0.8),
            layer="below",
        )
    for y in y_edges:
        fig.add_shape(
            type="line",
            x0=0, x1=100, y0=float(y), y1=float(y),
            line=dict(color="rgba(15,23,42,0.08)", width=0.8),
            layer="below",
        )

    for yi, y in enumerate(y_centers):
        for xi, x in enumerate(x_centers):
            val = float(z[yi, xi])
            fig.add_annotation(
                x=float(x),
                y=float(y),
                text=(
                    "0%" if val == 0 else
                    "<1%" if val < 1 else
                    f"{val:.1f}%" if val < 10 else
                    f"{val:.0f}%"
                ),
                showarrow=False,
                font=dict(size=9, color=("#0f172a" if val < 9 else "#ffffff")),
                opacity=0.95,
            )

    fig.add_trace(go.Scatter(
        x=rm_shots["x"],
        y=rm_shots["y"],
        mode="markers",
        marker=dict(size=5, color="red", opacity=0.9, line=dict(color="white", width=0.7)),
        name="Shot events",
        hovertemplate="x=%{x:.1f}, y=%{y:.1f}<extra></extra>",
    ))

    suffix = f" ({len(payloads)} matches)" if mode == "Range" else ""
    fig.update_layout(title=f"Real Madrid Shot Zone Map{suffix}")
    fig.add_annotation(
        text=f"Zone value = % of RM shots in zone (rounded) · Total shots: {int(total)}",
        xref="paper", yref="paper", x=0.5, y=-0.06, showarrow=False,
        font=dict(size=10, color=_C["text_secondary"]),
    )
    fig.update_layout(showlegend=False)
    return fig

_ROLE_NAME = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


def _extract_formation_lineup(data: dict, team_id: str, mirror: bool = False):
    """Build the real Starting XI + formation from the Opta team set-up event
    (typeId 34): qualifier 30 = player ids, 44 = position code (1 GK/2 DEF/3 MID/
    4 FWD), 59 = shirt numbers, 131 = formation place (1-11 = starters), 130 =
    Opta formation id.  Returns (DataFrame[player_name,shirt,role,x,y], formation_str).
    Coordinates are role-row based (attacking → x=100); mirror flips for the away XI.
    """
    evs = data.get("liveData", {}).get("event", [])
    id2name = {}
    for e in evs:
        pid, nm = e.get("playerId"), e.get("playerName")
        if pid and nm:
            id2name.setdefault(pid, nm)
    setup = [e for e in evs if e.get("typeId") == 34 and e.get("contestantId") == team_id]
    if not setup:
        return pd.DataFrame(), ""
    q = {x.get("qualifierId"): x.get("value") for x in setup[0].get("qualifier", [])}

    def lst(v):
        return [s.strip() for s in str(v).split(",")] if v is not None else []

    pids, poss, shirts, places = lst(q.get(30)), lst(q.get(44)), lst(q.get(59)), lst(q.get(131))
    rows = []
    for i, pid in enumerate(pids):
        try:
            code = int(poss[i]) if i < len(poss) else 0
            place = int(places[i]) if i < len(places) else 0
        except ValueError:
            continue
        if code not in (1, 2, 3, 4) or not (1 <= place <= 11):
            continue  # skip substitutes (code 5) / non-starters (place 0)
        rows.append({"player_name": id2name.get(pid, "?"),
                     "shirt": shirts[i] if i < len(shirts) else "",
                     "code": code, "place": place, "role": _ROLE_NAME[code]})
    if not rows:
        return pd.DataFrame(), ""
    df = pd.DataFrame(rows).drop_duplicates("player_name").head(11)

    n_def = int((df["code"] == 2).sum())
    n_mid = int((df["code"] == 3).sum())
    n_fwd = int((df["code"] == 4).sum())
    # Derive formation from the authoritative Opta position codes (q44), NOT the
    # formation-id dictionary (which proved unreliable). This feed classifies
    # GK/DEF/MID/FWD only, so e.g. 4-2-3-1 and 4-1-4-1 both read as 4-5-1.
    fstr = f"{n_def}-{n_mid}-{n_fwd}"

    out = []

    def place_row(sub, xc):
        k = len(sub)
        ys = np.linspace(82, 18, k) if k > 1 else [50.0]
        for (_, r), y in zip(sub.iterrows(), ys):
            out.append({**r.to_dict(),
                        "x": (100.0 - xc) if mirror else xc,
                        "y": (100.0 - y) if mirror else y})

    # Goalkeeper.
    place_row(df[df["code"] == 1], 5.0)

    # Distinct formation depth: split the formation string into lines.
    #   first line = defenders, last line = forwards, middle lines = midfield
    #   sub-rows (DM → CM → AM).  This makes 4-2-3-1 ≠ 4-3-3 ≠ 4-1-4-1 etc.
    lines = [int(t) for t in fstr.split("-") if t.isdigit()]
    use_depth = (len(lines) >= 2 and sum(lines) == 10 and
                 lines[0] == n_def and lines[-1] == n_fwd and
                 sum(lines[1:-1]) == n_mid)

    if use_depth:
        # Keep each XI inside its own half with a clear central gap (forwards
        # stop at x≈40) so the two teams never crowd / overlap at the half-way line.
        xs = np.linspace(15.0, 40.0, len(lines))
        place_row(df[df["code"] == 2].sort_values("place"), xs[0])
        mids = df[df["code"] == 3].sort_values("place")
        idx = 0
        for li, cnt in enumerate(lines[1:-1]):
            place_row(mids.iloc[idx:idx + cnt], xs[1 + li])
            idx += cnt
        place_row(df[df["code"] == 4].sort_values("place"), xs[-1])
    else:
        # Fallback to simple role rows if the string can't be reconciled.
        for code, xc in {2: 15.0, 3: 28.0, 4: 40.0}.items():
            place_row(df[df["code"] == code].sort_values("place"), xc)

    return pd.DataFrame(out), fstr


def _add_lineup_team(fig, df, color, name_pos, team_color_label):
    """Plot one XI: numbered jersey markers + readable name labels."""
    if df.empty:
        return
    fig.add_trace(go.Scatter(
        x=df["x"], y=df["y"], mode="markers+text",
        text=[str(s) for s in df["shirt"]],
        textposition="middle center",
        textfont=dict(size=10, color="white", family="Arial Black"),
        marker=dict(size=25, color=color, line=dict(color="white", width=2)),
        hovertemplate="%{customdata[0]} (#%{text}) · %{customdata[1]}<extra></extra>",
        customdata=np.stack([df["player_name"], df["role"]], axis=-1),
        name=team_color_label, showlegend=True,
    ))
    fig.add_trace(go.Scatter(
        x=df["x"], y=df["y"] + (5.0 if name_pos == "top" else -5.0),
        mode="text",
        text=[_short_name(n) for n in df["player_name"]],
        textposition="middle center",
        textfont=dict(size=9, color="#0f172a", family="Arial"),
        hoverinfo="skip", showlegend=False,
    ))


@callback(
    Output("ma-lineup-pitch", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
)
def _lineup_pitch(mode, file_path):
    data, meta, events = _load(file_path)

    fig = go.Figure()
    fig.update_layout(
        **{**_PL, "plot_bgcolor": _PITCH_FILL,
           "legend": dict(orientation="h", yanchor="bottom", y=1.01, xanchor="center", x=0.5,
                          bgcolor="rgba(255,255,255,0.6)")},
        height=_H_PITCH,
        shapes=_pitch_stripes_full() + _pitch_shapes_full(),
        xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68),
        title="Starting XIs",
    )

    if mode == "Range":
        fig.add_annotation(text="Starting XI positions are available only in Single Match mode.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    if meta is None or events is None or events.empty:
        fig.add_annotation(text="Select a match to view starting 11.", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    rm_name = _rm_team_name(meta)
    # Real Madrid attacks right; opponent mirrored attacking left.
    rm_df, rm_form = _extract_formation_lineup(data, meta["rm_id"], mirror=False)
    opp_df, opp_form = _extract_formation_lineup(data, meta["opp_id"], mirror=True)

    if rm_df.empty and opp_df.empty:
        # Fallback to data-driven average positions if no set-up event present.
        rm_df = _team_starting_positions(events, meta["rm_id"], mirror=False)
        opp_df = _team_starting_positions(events, meta["opp_id"], mirror=True)
        if not rm_df.empty:
            rm_df["shirt"] = ""; rm_df["role"] = ""
        if not opp_df.empty:
            opp_df["shirt"] = ""; opp_df["role"] = ""
        if rm_df.empty and opp_df.empty:
            fig.add_annotation(text="Could not detect starting XIs for this match.", xref="paper", yref="paper",
                               x=0.5, y=0.5, showarrow=False)
            return fig

    _add_lineup_team(fig, opp_df, _OPP, "bottom", f"{meta['opponent']}" + (f"  ({opp_form})" if opp_form else ""))
    _add_lineup_team(fig, rm_df, _RM, "top", f"{rm_name}" + (f"  ({rm_form})" if rm_form else ""))

    fig = _add_direction_arrows(fig, meta["opponent"], rm_name)
    title = f"{rm_name} ({rm_form}) vs {meta['opponent']} ({opp_form}) — Starting XIs" if rm_form else \
            f"{rm_name} vs {meta['opponent']} — Starting XIs"
    fig.update_layout(title=title)
    fig.add_annotation(text="Numbers = shirt · positions from Opta team set-up", xref="paper", yref="paper",
                       x=0.5, y=-0.06, showarrow=False,
                       font=dict(size=10, color=_C["text_secondary"]))
    return fig


@callback(
    Output("ma-player-table", "children"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-lineup-filter", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
)
def _player_table(mode, file_path, lineup_filter, competition, season, venue, from_match, to_match):
    if mode == "Range":
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match)
        if not payloads:
            return dbc.Alert("Select a match range to see aggregated player stats.", color="info")
        frames = []
        for _, m, ev in payloads:
            df = get_player_stats(ev, m["rm_id"])
            if not df.empty:
                frames.append(df)
        if not frames:
            return dbc.Alert("No player data available.", color="warning")
        df = pd.concat(frames, ignore_index=True).groupby(["player_id", "player_name"], as_index=False).sum(numeric_only=True)
        df["Status"] = "Range Aggregate"
    else:
        _, meta, events = _load(file_path)
        if meta is None:
            return dbc.Alert("Select a match to see player stats.", color="info")

        df = get_player_stats(events, meta["rm_id"])
        if df.empty:
            return dbc.Alert("No player data available.", color="warning")

        lineup = get_match_lineup_status(events, meta["rm_id"])
        df["Status"] = df["player_name"].map(lambda n: lineup.get(n, "Starting 11"))

        if lineup_filter and lineup_filter != "All":
            df = df[df["Status"] == lineup_filter]
    _, meta, events = _load(file_path)
    if meta is None:
        return dbc.Alert("Select a match to see player stats.", color="info")

    df = get_player_stats(events, meta["rm_id"])
    if df.empty:
        return dbc.Alert("No player data available.", color="warning")

    lineup = get_match_lineup_status(events, meta["rm_id"])
    df["Status"] = df["player_name"].map(lambda n: lineup.get(n, "Starting 11"))

    if lineup_filter and lineup_filter != "All":
        df = df[df["Status"] == lineup_filter]

    cols_map = {
        "player_name": "Player", "Status": "Status", "passes": "Passes",
        "shots": "Shots", "goals": "Goals",
        "tackles": "Tackles", "interceptions": "Inter.",
        "recoveries": "Recov.", "dribbles": "Dribbles", "xg": "xG",
    }
    display = df[[c for c in cols_map if c in df.columns]].rename(columns=cols_map)
    display = display[display["Passes"] > 0].sort_values("Passes", ascending=False)

    _STATUS_BADGE = {
        "Starting 11": "primary",
        "Sub On": "warning",
    }

    def _row(r):
        cells = []
        for c in display.columns:
            val = r[c]
            if c == "Status":
                cells.append(html.Td(dbc.Badge(str(val), color=_STATUS_BADGE.get(str(val), "secondary"), className="me-1")))
            else:
                cells.append(html.Td(str(val)))
        return html.Tr(cells)

    return dbc.Table(
        [html.Thead(html.Tr([html.Th(c) for c in display.columns])),
         html.Tbody([_row(r) for _, r in display.iterrows()])],
        striped=True, hover=True, responsive=True, className="small",
    )

@callback(
    Output("ma-subphase-chart", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
)
def _subphase_chart(mode, file_path, competition, season, venue, from_match, to_match):
    _, meta, events = _load(file_path)
    fig = go.Figure()
    fig.update_layout(**_PL, height=_H_CHART, title="A/B/C/D Phase Snapshot")
    if mode == "Range":
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match)
        if not payloads:
            return fig
        score_rows = []
        for _, m, ev in payloads:
            score_rows.append(phase_scores_from_events(ev, m["rm_id"], m["opp_id"]))
        scores = pd.DataFrame(score_rows).mean().to_dict()
    elif meta is None or events is None or events.empty:
        return fig
    else:
        scores = phase_scores_from_events(events, meta["rm_id"], meta["opp_id"])
    labels = list(scores.keys())
    values = [scores[k] for k in labels]
    phase_colors = {
        "A": _RM,
        "B": _C["accent_orange"],
        "C": _C["accent_red"],
        "D": _C["accent_green"],
    }
    for label, value in zip(labels, values):
        fig.add_trace(go.Bar(
            x=[label],
            y=[value],
            name=f"Phase {label}",
            marker_color=phase_colors.get(label, _RM),
            text=[f"{value:.1f}"],
            textposition="auto",
        ))
    fig.update_layout(
        **_PL,
        height=_H_CHART,
        xaxis=dict(gridcolor=_C["border"], tickangle=-15, ticklabelstep=2, automargin=True),
        yaxis=dict(gridcolor=_C["border"], range=[0, 100], title="Phase Index", automargin=True),
        showlegend=True,
    )
    return fig


def _with_event_seconds(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["event_sec"] = out["minute"].fillna(0) * 60 + out["second"].fillna(0)
    return out.sort_values(["event_sec", "event_id"])


@callback(
    Output("ma-transition-chart", "figure"),
    Input("ma-match-selector", "value"),
    Input("ma-phase-focus", "value"),
)
def _transition_chart(file_path, phase_focus):
    fig = go.Figure()
    fig.update_layout(**_PL, height=_H_CHART, title="Transition Efficiency (after recoveries)")

    _, meta, events = _load(file_path)
    if meta is None or events is None or events.empty:
        return fig

    ev = _with_event_seconds(events)
    rm_ev = ev[ev["contestant_id"] == meta["rm_id"]]
    rec = rm_ev[rm_ev["is_recovery"]]
    if rec.empty:
        fig.add_annotation(text="No recoveries found in this match", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    window_sec = 12
    n_transitions = int(len(rec))
    threat_sum = 0.0
    time_to_shot = []

    for _, r in rec.iterrows():
        t0 = r["event_sec"]
        win = rm_ev[(rm_ev["event_sec"] >= t0) & (rm_ev["event_sec"] <= t0 + window_sec)]
        shots = win[win["is_shot"]]
        if not shots.empty:
            threat_sum += float(shots["xg"].dropna().sum())
            time_to_shot.append(float(shots.iloc[0]["event_sec"] - t0))

    xth_per_transition = (threat_sum / n_transitions) if n_transitions else 0.0
    avg_tfs = (sum(time_to_shot) / len(time_to_shot)) if time_to_shot else 0.0

    fig.add_trace(go.Bar(
        x=["Transitions", "xG / Transition", "Time-to-First-Shot (s)"],
        y=[n_transitions, xth_per_transition, avg_tfs],
        marker_color=[_C["accent_blue"], _C["accent_orange"], _C["accent_green"]],
        text=[f"{n_transitions}", f"{xth_per_transition:.3f}", f"{avg_tfs:.1f}"],
        textposition="auto",
    ))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Transition Count", marker=dict(size=9, color=_C["accent_blue"]), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Threat Efficiency", marker=dict(size=9, color=_C["accent_orange"]), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Speed To Shot", marker=dict(size=9, color=_C["accent_green"]), hoverinfo="skip"))

    if phase_focus and phase_focus not in {"All", "Transitions"}:
        fig.add_annotation(
            text=f"Phase Focus = {phase_focus}. Transition chart shown for comparison.",
            xref="paper", yref="paper", x=0.5, y=1.08, showarrow=False,
            font=dict(size=10, color=_C["text_secondary"]),
        )

    fig.update_layout(
        **_PL,
        height=_H_CHART,
        title="Transition Efficiency (12s window after recovery)",
        xaxis=dict(gridcolor=_C["border"], automargin=True),
        yaxis=dict(gridcolor=_C["border"], automargin=True),
        showlegend=True,
    )
    return fig


@callback(
    Output("ma-setpiece-chart", "figure"),
    Input("ma-match-selector", "value"),
    Input("ma-phase-focus", "value"),
)
def _setpiece_chart(file_path, phase_focus):
    fig = go.Figure()
    fig.update_layout(**_PL, height=_H_CHART, title="Set Piece Efficiency")

    _, meta, events = _load(file_path)
    if meta is None or events is None or events.empty:
        return fig

    ev = _with_event_seconds(events)
    rm_ev = ev[ev["contestant_id"] == meta["rm_id"]]
    opp_ev = ev[ev["contestant_id"] == meta["opp_id"]]

    rm_corners = rm_ev[rm_ev["type_id"] == 6]
    opp_corners = opp_ev[opp_ev["type_id"] == 6]

    def _shots_from_corners(team_events, corners_df, sec_window=20):
        n_shots = 0
        n_goals = 0
        for _, c in corners_df.iterrows():
            t0 = c["event_sec"]
            win = team_events[(team_events["event_sec"] >= t0) & (team_events["event_sec"] <= t0 + sec_window)]
            shots = win[win["is_shot"]]
            if not shots.empty:
                n_shots += int(len(shots))
                n_goals += int(shots["is_goal"].sum())
        return n_shots, n_goals

    rm_sp_shots, rm_sp_goals = _shots_from_corners(rm_ev, rm_corners)
    opp_sp_shots, opp_sp_goals = _shots_from_corners(opp_ev, opp_corners)

    rm_conv = (rm_sp_goals / rm_corners.shape[0] * 100.0) if rm_corners.shape[0] else 0.0
    opp_conv = (opp_sp_goals / opp_corners.shape[0] * 100.0) if opp_corners.shape[0] else 0.0

    # Build subplot: bar chart left, pie chart right
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Corner Sequences", "RM Shot Outcomes (Corners)"),
        specs=[[{"type": "bar"}, {"type": "pie"}]],
    )

    categories = ["Corners", "Corner<br>Shots", "Corner<br>Goals"]
    rm_vals  = [int(rm_corners.shape[0]),  int(rm_sp_shots),  int(rm_sp_goals)]
    opp_vals = [int(opp_corners.shape[0]), int(opp_sp_shots), int(opp_sp_goals)]

    fig.add_trace(go.Bar(
        name="Real Madrid", x=categories, y=rm_vals, marker_color=_RM,
        text=[str(v) for v in rm_vals], textposition="outside",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        name=meta["opponent"], x=categories, y=opp_vals, marker_color=_OPP,
        text=[str(v) for v in opp_vals], textposition="outside", opacity=0.85,
    ), row=1, col=1)

    # Pie: RM corner shot outcomes
    rm_no_shot = max(0, int(rm_corners.shape[0]) - int(rm_sp_shots))
    rm_shot_no_goal = max(0, int(rm_sp_shots) - int(rm_sp_goals))
    pie_labels = ["Goal", "Shot (no goal)", "No shot"]
    pie_values = [int(rm_sp_goals), rm_shot_no_goal, rm_no_shot]
    pie_colors = [_GOLD, _RM, "#90a4ae"]
    # Only include slices with non-zero values
    active = [(l, v, c) for l, v, c in zip(pie_labels, pie_values, pie_colors) if v > 0]
    if active:
        pie_labels, pie_values, pie_colors = zip(*active)
    else:
        pie_labels, pie_values, pie_colors = ["No corners"], [1], ["#90a4ae"]

    fig.add_trace(go.Pie(
        labels=list(pie_labels), values=list(pie_values),
        marker=dict(colors=list(pie_colors)),
        textinfo="label+percent", hole=0.4,
        showlegend=False,
        name="RM Corner Outcomes",
    ), row=1, col=2)

    if phase_focus and phase_focus not in {"All", "SetPieces"}:
        fig.add_annotation(
            text=f"Phase Focus = {phase_focus}. Set-piece chart shown for reference.",
            xref="paper", yref="paper", x=0.5, y=1.12, showarrow=False,
            font=dict(size=10, color=_C["text_secondary"]),
        )

    fig.update_layout(
        paper_bgcolor=_C["surface"],
        plot_bgcolor=_C["surface"],
        font=dict(color=_C["text_primary"], size=11),
        height=_H_CHART + 40,
        barmode="group",
        title="Set Piece Efficiency — Corner Sequences",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=0.5),
        showlegend=True,
        margin=dict(l=48, r=28, t=96, b=70),
    )

    fig.update_xaxes(
        categoryorder="array",
        categoryarray=categories,
        tickmode="array",
        tickvals=categories,
        ticktext=categories,
        tickangle=-20,
        automargin=True,
        tickfont=dict(size=10),
        row=1,
        col=1,
    )
    fig.update_yaxes(automargin=True, row=1, col=1)
    return fig


@callback(
    Output("ma-post-summary", "children"),
    Input("ma-match-selector", "value"),
    Input("ma-phase-focus", "value"),
)
def _post_match_summary(file_path, phase_focus):
    _, meta, events = _load(file_path)
    if meta is None or events is None or events.empty:
        return dbc.Alert("Select a match to generate the tactical summary.", color="info")

    kpis = calc_match_kpis(events, meta)
    ppda = calc_ppda(events, meta)
    tilt = calc_field_tilt(events, meta)

    goals = float(kpis["goals_scored"])
    xg = float(kpis["xg_for"])
    xg_diff = goals - xg
    finish_tag = "Clinical finishing" if xg_diff >= 0.4 else ("Under-finishing" if xg_diff <= -0.4 else "Finishing near expectation")

    strengths = []
    weaknesses = []

    if ppda <= 8:
        strengths.append("High defensive pressure intensity")
    else:
        weaknesses.append("Pressing intensity below target")

    if tilt >= 55:
        strengths.append("Final-third territorial control")
    else:
        weaknesses.append("Limited final-third control")

    if kpis["pass_accuracy"] >= 86:
        strengths.append("Stable possession circulation")
    else:
        weaknesses.append("Possession quality can improve")

    if kpis["xg_against"] <= 1.0:
        strengths.append("Defensive shot quality suppression")
    else:
        weaknesses.append("Allowed high-quality chances")

    if not strengths:
        strengths = ["Competitive phases in open play"]
    if not weaknesses:
        weaknesses = ["No major tactical weaknesses flagged in this match"]

    if kpis["pass_accuracy"] >= 86 and tilt >= 55 and ppda <= 8:
        identity = "Controlled attacking + proactive press"
    elif ppda <= 8:
        identity = "High-pressure, transition-oriented"
    elif kpis["pass_accuracy"] >= 86:
        identity = "Positional possession-led"
    else:
        identity = "Mixed tactical profile"

    focus_note = html.Small(f"Phase Focus: {phase_focus or 'All'}", className="text-muted")

    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Goals vs xG", className="kpi-title"),
                html.H5(f"{goals:.0f} vs {xg:.2f}", style={"color": _RM}),
                html.P(f"Delta: {xg_diff:+.2f} ({finish_tag})", className="text-muted small mb-0"),
            ]), className="kpi-card h-100"), md=4, className="mb-2"),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Expected vs Actual", className="kpi-title"),
                html.H5(meta["score_str"], style={"color": _C["accent_green"] if meta["result"] == "W" else _C["accent_red"] if meta["result"] == "L" else _C["accent_yellow"]}),
                html.P(f"xG For/Against: {kpis['xg_for']} / {kpis['xg_against']}", className="text-muted small mb-0"),
            ]), className="kpi-card h-100"), md=4, className="mb-2"),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Tactical Identity", className="kpi-title"),
                html.H5(identity, style={"color": _C["accent_purple"]}),
                html.P(f"PPDA: {ppda} · Field Tilt: {tilt}%", className="text-muted small mb-0"),
            ]), className="kpi-card h-100"), md=4, className="mb-2"),
        ]),
        html.Hr(className="my-2"),
        html.Div([
            html.H6("Strengths"),
            html.Ul([html.Li(s) for s in strengths], className="mb-2"),
            html.H6("Weaknesses"),
            html.Ul([html.Li(w) for w in weaknesses], className="mb-2"),
            focus_note,
        ]),
    ])
