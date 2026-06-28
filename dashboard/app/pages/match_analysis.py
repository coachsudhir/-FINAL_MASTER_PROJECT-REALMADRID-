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
    get_season_match_list,
    get_competition_seasons,
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
                            {"label": "Multi-Match (up to 5)", "value": "Multi"},
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

        # Multi-match selection card
        dbc.Card(dbc.CardBody([
            html.P("Select Specific Matches (up to 5)", className="section-header mb-2"),
            html.Small("Pick up to 5 individual matches to aggregate and compare.", className="text-muted d-block mb-2"),
            dbc.Row([
                dbc.Col([
                    html.Label("Matches", className="filter-label"),
                    dcc.Dropdown(
                        id="ma-multi-match-select",
                        options=[],
                        value=[],
                        multi=True,
                        placeholder="Select matches (max 5)…",
                        clearable=True,
                    ),
                ], md=12),
            ], className="g-2"),
            html.Div(id="ma-multi-match-warning", className="mt-2"),
        ]), className="filter-section mb-4", id="ma-multi-match-card"),

        dcc.Store(id="ma-multi-paths-store", storage_type="memory", data=[]),

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
            dbc.CardHeader("GK Distribution Map"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-gk-distribution",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Crossing Patterns"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-crossing-patterns",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Goalmouth Map"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-goalmouth-map",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Zone 14 Passing"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-zone14-passing",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Defensive Actions Map"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma-defensive-actions",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Post-Match Tactical Summary"),
            dbc.CardBody(dcc.Loading(
                html.Div(id="ma-post-summary"),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # ── Advanced Filters (Period + Minute Range) ──────────────────────────
        dbc.Card(dbc.CardBody([
            html.P("Advanced Filters", className="section-header mb-2"),
            dbc.Row([
                dbc.Col([
                    html.Label("Match Period", className="filter-label"),
                    dcc.Dropdown(
                        id="ma2-period-filter",
                        options=[
                            {"label": "Full Match", "value": "all"},
                            {"label": "First Half", "value": "1"},
                            {"label": "Second Half", "value": "2"},
                        ],
                        value="all",
                        clearable=False,
                    ),
                ], md=3),
                dbc.Col([
                    html.Label("Minute Range", className="filter-label"),
                    dcc.RangeSlider(
                        id="ma2-time-slider",
                        min=0, max=95, step=5,
                        marks={0: "0'", 15: "15'", 30: "30'", 45: "45'",
                               60: "60'", 75: "75'", 90: "90'", 95: "95+"},
                        value=[0, 95],
                        tooltip={"placement": "bottom", "always_visible": False},
                        allowCross=False,
                    ),
                ], md=9),
            ], className="g-3 align-items-end"),
        ]), className="filter-section mb-3"),

        # Pass receive heatmap
        dbc.Card([
            dbc.CardHeader("Pass Receive Heatmap (RM — where passes land)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma2-pass-receive-heatmap",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Chance creation heatmap
        dbc.Card([
            dbc.CardHeader("Chance Creation Heatmap (Key Passes & Assists — origin locations)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma2-chance-creation-heatmap",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Progressive passes
        dbc.Card([
            dbc.CardHeader("Progressive Passes (RM — advances ball ≥ 10 units forward)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma2-progressive-passes",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Penalty analysis
        dbc.Card([
            dbc.CardHeader("Penalty Analysis"),
            dbc.CardBody(dcc.Loading(
                html.Div(id="ma2-penalty-analysis"),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Chance creator %
        dbc.Card([
            dbc.CardHeader("Chance Creator % — Player Key Passes / Team Total"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma2-chance-creator",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Team radar
        dbc.Card([
            dbc.CardHeader("Team Radar — RM vs Opponent"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma2-team-radar",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Build-up network
        dbc.Card([
            dbc.CardHeader("Build-Up Network (RM passes in own half — x < 50)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma2-buildup-network",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Final third entry analysis
        dbc.Card([
            dbc.CardHeader("Final Third Entry Analysis (RM)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma2-final-third-entries",
                          config={"responsive": True, "displayModeBar": False}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Transition window control
        dbc.Card(dbc.CardBody([
            html.P("Transition Window Control", className="section-header mb-2"),
            dbc.Row([
                dbc.Col([
                    html.Label("Regain → Shot Window (seconds)", className="filter-label"),
                    dcc.Dropdown(
                        id="ma2-transition-window",
                        options=[
                            {"label": "5 seconds", "value": 5},
                            {"label": "10 seconds", "value": 10},
                            {"label": "12 seconds (default)", "value": 12},
                            {"label": "15 seconds", "value": 15},
                        ],
                        value=12,
                        clearable=False,
                    ),
                ], md=4),
            ]),
        ]), className="filter-section mb-3"),

        dbc.Card([
            dbc.CardHeader("Extended Transition Analysis"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="ma2-extended-transition",
                          config={"responsive": True, "displayModeBar": False}),
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
    Output("ma-multi-match-card", "style"),
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
            {"display": "none"},
        )
    if mode == "Multi":
        return (
            "Competition / Season / Venue / Analysis Setup",
            "Choose the context then pick up to 5 specific matches below.",
            "Match Range",
            "Optional: use the range filter to narrow the list of available matches.",
            {"display": "none"},
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
        {"display": "none"},
    )


@callback(
    Output("ma-multi-match-select", "options"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
)
def _multi_match_opts(competition, season, venue):
    return get_match_options(competition or "LaLiga", season or "2025-2026", venue or "All")


@callback(
    Output("ma-multi-match-select", "value"),
    Output("ma-multi-match-warning", "children"),
    Input("ma-multi-match-select", "value"),
    prevent_initial_call=True,
)
def _limit_multi_match(value):
    if not value:
        return [], None
    if len(value) > 5:
        return value[:5], dbc.Alert("Maximum 5 matches allowed — trimmed to first 5.", color="warning", className="py-1 small")
    return value, None


@callback(
    Output("ma-multi-paths-store", "data"),
    Input("ma-multi-match-select", "value"),
)
def _update_multi_paths_store(value):
    return value or []


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


def _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None):
    if mode == "Multi":
        file_paths = [fp for fp in (multi_paths or []) if fp][:5]
    elif mode == "Range":
        file_paths = _selected_range_files(competition, season, venue, from_match, to_match)
    else:
        data, meta, events = _load(file_path)
        payloads = [(file_path, meta, events)] if meta is not None and events is not None else []
        return payloads

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
    """Times (s) of set-piece restarts for `team_id`.

    Detected via qualifier IDs on Pass events:
      QID 5  = FreekickTaken
      QID 72 = CornerTaken
    Both are stored in the is_set_piece column added by parse_events().
    NOTE: type_id 5 = Offside and type_id 6 = Corner Awarded — those are
    announcement events tagged to BOTH teams and must NOT be used here.
    """
    mask = (events["contestant_id"] == team_id)
    if "is_set_piece" in events.columns:
        mask = mask & events["is_set_piece"]
    else:
        # Fallback: free kick / corner kick passes identified by qualifier on the pass
        mask = mask & events["is_pass"] & (events["type_id"] == 1)
    sp = events[mask]
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
    Input("ma-multi-paths-store", "data"),
)
def _update_header(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None):
    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        agg = _aggregate_scope_kpis(payloads)
        if not agg:
            return dbc.Alert("Select a valid match range to begin.", color="info"), []

        metas = agg["metas"]
        header = dbc.Card(dbc.CardBody([
            html.H4(f"{'Multi-Match' if mode == 'Multi' else 'Range'} Analysis: {len(metas)} matches", className="mb-1"),
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
    Input("ma-multi-paths-store", "data"),
    Input("ma-phase-focus", "value"),
)
def _shot_map(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None, phase_focus="All"):
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

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
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
             if mode not in ("Range", "Multi") else f"{'Multi' if mode == 'Multi' else 'Range'} Shot Map ({len(payloads)} matches){_ph_sfx}")
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
    Input("ma-multi-paths-store", "data"),
)
def _xg_chart(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None):
    _, meta, events = _load(file_path)

    def _base():
        f = go.Figure()
        f.update_layout(**_PL, height=_H_COMPARE, title="xG Accumulation")
        return f

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
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
    Input("ma-multi-paths-store", "data"),
)
def _tactical_bars(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None):
    _, meta, events = _load(file_path)

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
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
    Input("ma-multi-paths-store", "data"),
    Input("ma-phase-focus", "value"),
)
def _pass_map(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None, phase_focus="All"):
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

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
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
    fig.update_layout(title=("Real Madrid Pass Map" + _ph_sfx if mode not in ("Range", "Multi") else f"Real Madrid Pass Map ({len(payloads)} matches){_ph_sfx}"))
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
    Input("ma-multi-paths-store", "data"),
    Input("ma-network-scope", "value"),
    Input("ma-phase-focus", "value"),
)
def _pass_network(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None, scope="xi", phase_focus="All"):
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

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            fig.add_annotation(text="Select matches for pass-network analysis.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
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
    if scope == "xi" and mode not in ("Range", "Multi"):
        lineup = get_match_lineup_status(events, meta["rm_id"])
        starter_names = {p for p, s in lineup.items() if s == "Starting 11"}
        max_players = 11
    nodes, edges = _build_pass_network(
        events, meta["rm_id"], min_edge_count=(3 if mode in ("Range", "Multi") else 2),
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

    if mode in ("Range", "Multi"):
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
    Input("ma-multi-paths-store", "data"),
)
def _shot_zone_map(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None):
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

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            fig.add_annotation(text="Select matches for shot-zone analysis.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
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

    suffix = f" ({len(payloads)} matches)" if mode in ("Range", "Multi") else ""
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

    if mode in ("Range", "Multi"):
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
    Input("ma-multi-paths-store", "data"),
)
def _player_table(mode, file_path, lineup_filter, competition, season, venue, from_match, to_match, multi_paths=None):
    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            return dbc.Alert("Select matches to see aggregated player stats.", color="info")
        frames = []
        for _, m, ev in payloads:
            df = get_player_stats(ev, m["rm_id"])
            if not df.empty:
                frames.append(df)
        if not frames:
            return dbc.Alert("No player data available.", color="warning")
        df = pd.concat(frames, ignore_index=True).groupby(["player_id", "player_name"], as_index=False).sum(numeric_only=True)
        df["Status"] = f"{'Multi' if mode == 'Multi' else 'Range'} Aggregate"
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
    Input("ma-multi-paths-store", "data"),
)
def _subphase_chart(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None):
    _PHASE_FULL = {
        "A": "A – Offensive Moment",
        "B": "B – Defensive Transition",
        "C": "C – Defensive Moment",
        "D": "D – Offensive Transition",
    }
    _PHASE_COLORS = [_RM, _C["accent_orange"], _C["accent_red"], _C["accent_green"]]
    _PHASE_KEYS   = ["A. Offensive Moment", "B. Defensive Transition",
                     "C. Defensive Moment", "D. Offensive Transition"]
    _SHORT_LABELS = ["A. Offensive\nMoment", "B. Defensive\nTransition",
                     "C. Defensive\nMoment", "D. Offensive\nTransition"]

    def _empty_fig(title="A/B/C/D Phase Snapshot"):
        f = go.Figure()
        f.update_layout(**_PL, height=_H_CHART, title=title)
        return f

    try:
        if mode in ("Range", "Multi"):
            payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
            if not payloads:
                return _empty_fig("A/B/C/D Phase Snapshot — select matches")
            score_rows = []
            for _, m, ev in payloads:
                score_rows.append(phase_scores_from_events(ev, m["rm_id"], m["opp_id"]))
            scores = pd.DataFrame(score_rows).mean().to_dict()
            title_suffix = f" ({len(payloads)} matches avg)"
        else:
            _, meta, events = _load(file_path)
            if meta is None or events is None or events.empty:
                return _empty_fig()
            scores = phase_scores_from_events(events, meta["rm_id"], meta["opp_id"])
            opp = meta.get("opponent", "")
            title_suffix = f" — vs {opp}" if opp else ""
    except Exception as _e:
        return _empty_fig(f"Error: {_e}")

    values = [scores.get(k, 0.0) for k in _PHASE_KEYS]

    # One trace per phase so each bar has its own legend entry and color
    fig = go.Figure()
    for i, (short_lbl, full_lbl, val, col) in enumerate(
        zip(_SHORT_LABELS, list(_PHASE_FULL.values()), values, _PHASE_COLORS)
    ):
        fig.add_trace(go.Bar(
            x=[short_lbl],
            y=[val],
            name=full_lbl,
            marker_color=col,
            text=[f"<b>{val:.1f}</b>"],
            textposition="outside",
            textfont=dict(size=13),
            hovertemplate=f"<b>{full_lbl}</b><br>Score: %{{y:.1f}} / 100<extra></extra>",
        ))

    # Use dict-merge so legend/margin in _PL are overridden without duplicate-kwarg TypeError
    fig.update_layout(**{
        **_PL,
        "height": _H_CHART + 60,
        "barmode": "group",
        "title": dict(
            text=f"A/B/C/D Phase Snapshot{title_suffix}",
            x=0.5, xanchor="center", font=dict(size=13),
        ),
        "xaxis": dict(
            gridcolor=_C["border"],
            tickfont=dict(size=11),
            automargin=True,
        ),
        "yaxis": dict(
            gridcolor=_C["border"],
            range=[0, 115],
            title="Phase Index (0–100)",
            automargin=True,
        ),
        "legend": dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="center", x=0.5,
            font=dict(size=10),
        ),
        "showlegend": True,
        "margin": dict(l=56, r=28, t=110, b=80),
    })
    return fig


def _subphase_radar(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None):
    """Radar (Scatterpolar) view of the four A/B/C/D tactical-phase scores.

    Reuses the exact same phase computation as ``_subphase_chart``
    (``phase_scores_from_events`` over real Opta events) — no synthetic data.
    Single match → that match's profile; Range → mean across the scoped matches.
    """
    _PHASE_KEYS = ["A. Offensive Moment", "B. Defensive Transition",
                   "C. Defensive Moment", "D. Offensive Transition"]
    _AXIS = ["A · Offensive<br>Moment", "B · Defensive<br>Transition",
             "C · Defensive<br>Moment", "D · Offensive<br>Transition"]

    def _empty(title="Tactical Phase Profile"):
        f = go.Figure()
        f.update_layout(**_PL, height=_H_CHART + 40, title=title)
        return f

    try:
        if mode in ("Range", "Multi"):
            payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
            if not payloads:
                return _empty("Tactical Phase Profile — select matches")
            scores = pd.DataFrame(
                [phase_scores_from_events(ev, m["rm_id"], m["opp_id"]) for _, m, ev in payloads]
            ).mean().to_dict()
            title_suffix = f" ({len(payloads)} matches avg)"
        else:
            _, meta, events = _load(file_path)
            if meta is None or events is None or events.empty:
                return _empty()
            scores = phase_scores_from_events(events, meta["rm_id"], meta["opp_id"])
            opp = meta.get("opponent", "")
            title_suffix = f" — vs {opp}" if opp else ""
    except Exception as _e:
        return _empty(f"Error: {_e}")

    values = [round(float(scores.get(k, 0.0)), 1) for k in _PHASE_KEYS]
    r_closed = values + values[:1]
    theta_closed = _AXIS + _AXIS[:1]
    point_labels = [f"{v:.0f}" for v in values] + [""]

    _GOLD = "#c8a951"
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=r_closed, theta=theta_closed,
        fill="toself", fillcolor="rgba(37,99,235,0.22)",
        line=dict(color=_RM, width=2.4),
        mode="lines+markers+text",
        marker=dict(size=10, color=_GOLD, line=dict(color=_C["text_primary"], width=1.2)),
        text=point_labels, textposition="top center",
        textfont=dict(size=12, color=_C["text_primary"]),
        hovertemplate="<b>%{theta}</b><br>Phase Index: %{r:.1f} / 100<extra></extra>",
        name="RM phase profile",
    ))
    fig.update_layout(**{
        **_PL,
        "height": _H_CHART + 80,
        "showlegend": False,
        "title": dict(text=f"Tactical Phase Profile{title_suffix}",
                      x=0.5, xanchor="center", font=dict(size=13)),
        "polar": dict(
            bgcolor=_C["surface"],
            radialaxis=dict(range=[0, 100], tickvals=[20, 40, 60, 80],
                            tickfont=dict(size=9, color=_C["text_secondary"]),
                            gridcolor=_C["border"], linecolor=_C["border"]),
            angularaxis=dict(tickfont=dict(size=11, color=_C["text_primary"]),
                             gridcolor=_C["border"], linecolor=_C["border"]),
        ),
        "margin": dict(l=70, r=70, t=90, b=70),
    })
    return fig


def _with_event_seconds(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["event_sec"] = out["minute"].fillna(0) * 60 + out["second"].fillna(0)
    return out.sort_values(["event_sec", "event_id"])


def _calc_transitions_single(events: pd.DataFrame, meta: dict, window_sec: int = 12) -> dict:
    """Compute transition metrics for a single match's events."""
    ev    = _with_event_seconds(events)
    rm_ev = ev[ev["contestant_id"] == meta["rm_id"]]
    rec   = rm_ev[rm_ev["is_recovery"]]
    n     = len(rec)
    threat, times = 0.0, []
    for _, r in rec.iterrows():
        t0  = r["event_sec"]
        win = rm_ev[(rm_ev["event_sec"] >= t0) & (rm_ev["event_sec"] <= t0 + window_sec)]
        sh  = win[win["is_shot"]]
        if not sh.empty:
            threat += float(sh["xg"].dropna().sum())
            times.append(float(sh.iloc[0]["event_sec"] - t0))
    return {
        "n":     n,
        "xg_pt": round(threat / n, 4) if n else 0.0,
        "avg_t": round(sum(times) / len(times), 1) if times else 0.0,
    }


def _calc_setpieces_single(events: pd.DataFrame, meta: dict, win_sec: int = 35) -> dict:
    """Compute corner-based set piece metrics for a single match's events."""
    ev     = _with_event_seconds(events)
    rm_ev  = ev[ev["contestant_id"] == meta["rm_id"]]
    opp_ev = ev[ev["contestant_id"] == meta["opp_id"]]
    rm_c   = rm_ev[rm_ev["type_id"] == 6]
    opp_c  = opp_ev[opp_ev["type_id"] == 6]

    def _corner_sp(team_ev, corners_df):
        shots = goals = 0
        for _, c in corners_df.iterrows():
            t0 = c["event_sec"]
            w  = team_ev[(team_ev["event_sec"] >= t0) & (team_ev["event_sec"] <= t0 + win_sec)]
            sh = w[w["is_shot"]]
            if not sh.empty:
                shots += len(sh)
                goals += int(sh["is_goal"].sum())
        return shots, goals

    rm_sh,  rm_g  = _corner_sp(rm_ev,  rm_c)
    opp_sh, opp_g = _corner_sp(opp_ev, opp_c)
    return {
        "rm_c":  len(rm_c),  "rm_sh":  rm_sh,  "rm_g":  rm_g,
        "opp_c": len(opp_c), "opp_sh": opp_sh, "opp_g": opp_g,
    }


@callback(
    Output("ma-transition-chart", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-multi-paths-store", "data"),
    Input("ma-phase-focus", "value"),
)
def _transition_chart(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None, phase_focus=None):
    from plotly.subplots import make_subplots

    _BASE = dict(
        paper_bgcolor=_C["surface"], plot_bgcolor=_C["surface"],
        font=dict(color=_C["text_primary"], size=11),
        margin=dict(l=48, r=28, t=96, b=70),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="center", x=0.5),
    )

    # ── Range / Multi mode ───────────────────────────────────────────────────
    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            fig = go.Figure()
            fig.update_layout(**_BASE, height=_H_CHART + 60,
                              title="Transition Efficiency — select matches")
            return fig

        labels, n_vals, xg_vals, t_vals = [], [], [], []
        for _, m, ev in payloads:
            if ev is None or ev.empty:
                continue
            r = _calc_transitions_single(ev, m)
            labels.append(f"MD{m.get('week','?')} {m.get('opponent','OPP')[:7]}")
            n_vals.append(r["n"])
            xg_vals.append(r["xg_pt"])
            t_vals.append(r["avg_t"])

        if not labels:
            fig = go.Figure()
            fig.update_layout(**_BASE, height=_H_CHART + 60,
                              title="Transition Efficiency — no data in range")
            return fig

        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            subplot_titles=[
                "Recoveries / Transitions per Match",
                "xG per Transition (threat after each recovery)",
                "Avg Time to First Shot after Recovery (s)",
            ],
            vertical_spacing=0.09,
        )
        fig.add_trace(go.Bar(
            x=labels, y=n_vals, name="Transitions",
            marker_color=_C["accent_blue"],
            text=[str(v) for v in n_vals], textposition="outside",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=labels, y=xg_vals, name="xG / Transition",
            marker_color=_C["accent_orange"],
            text=[f"{v:.4f}" for v in xg_vals], textposition="outside",
        ), row=2, col=1)
        fig.add_trace(go.Bar(
            x=labels, y=t_vals, name="Time to First Shot (s)",
            marker_color=_C["accent_green"],
            text=[f"{v:.1f}s" for v in t_vals], textposition="outside",
        ), row=3, col=1)

        for ri in [1, 2, 3]:
            fig.update_xaxes(tickangle=-35, automargin=True, gridcolor=_C["border"], row=ri, col=1)
            fig.update_yaxes(automargin=True, gridcolor=_C["border"], row=ri, col=1)

        avg_n  = round(sum(n_vals)  / len(n_vals),  1)
        avg_xg = round(sum(xg_vals) / len(xg_vals), 4)
        non_z  = [v for v in t_vals if v > 0]
        avg_t  = round(sum(non_z) / len(non_z), 1) if non_z else 0.0

        fig.update_layout(
            **_BASE,
            height=_H_CHART + 340,
            showlegend=True,
            title=dict(
                text=(f"Transition Efficiency — {len(labels)} matches  |  "
                      f"Avg: {avg_n} transitions · xG/T {avg_xg} · T2S {avg_t}s"),
                x=0.5, xanchor="center", font=dict(size=13),
            ),
        )
        return fig

    # ── Single match mode ─────────────────────────────────────────────────────
    _, meta, events = _load(file_path)

    def _empty_single():
        fig = go.Figure()
        fig.update_layout(**_BASE, height=_H_CHART + 60,
                          title="Transition Efficiency (12s window after recovery)")
        return fig

    if meta is None or events is None or events.empty:
        return _empty_single()

    r = _calc_transitions_single(events, meta)
    n, xg_pt, avg_t = r["n"], r["xg_pt"], r["avg_t"]

    if n == 0:
        fig = _empty_single()
        fig.add_annotation(text="No recoveries found in this match.",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    # Three separate panels to avoid y-axis scale mixing
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=[
            "Recoveries / Transitions",
            "xG per Transition",
            "Avg Time to First Shot (s)",
        ],
        horizontal_spacing=0.12,
    )
    fig.add_trace(go.Bar(
        x=["Transitions"], y=[n],
        marker_color=_C["accent_blue"],
        text=[str(n)], textposition="outside",
        showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=["xG / Transition"], y=[xg_pt],
        marker_color=_C["accent_orange"],
        text=[f"{xg_pt:.4f}"], textposition="outside",
        showlegend=False,
    ), row=1, col=2)
    fig.add_trace(go.Bar(
        x=["Avg T2S (s)"], y=[avg_t],
        marker_color=_C["accent_green"],
        text=[f"{avg_t:.1f}s"], textposition="outside",
        showlegend=False,
    ), row=1, col=3)

    for ci in [1, 2, 3]:
        fig.update_xaxes(automargin=True, gridcolor=_C["border"], row=1, col=ci)
        fig.update_yaxes(automargin=True, gridcolor=_C["border"], row=1, col=ci)

    if phase_focus and phase_focus not in {"All", "Transitions"}:
        fig.add_annotation(
            text=f"Phase Focus = {phase_focus}. Transition chart shown for comparison.",
            xref="paper", yref="paper", x=0.5, y=1.10, showarrow=False,
            font=dict(size=10, color=_C["text_secondary"]),
        )

    fig.update_layout(
        **_BASE,
        height=_H_CHART + 60,
        showlegend=False,
        title=dict(
            text=f"Transition Efficiency (12s window) — {n} transitions",
            x=0.5, xanchor="center", font=dict(size=13),
        ),
    )
    return fig


@callback(
    Output("ma-setpiece-chart", "figure"),
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-multi-paths-store", "data"),
    Input("ma-phase-focus", "value"),
)
def _setpiece_chart(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None, phase_focus=None):
    from plotly.subplots import make_subplots

    _BASE = dict(
        paper_bgcolor=_C["surface"], plot_bgcolor=_C["surface"],
        font=dict(color=_C["text_primary"], size=11),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="center", x=0.5),
        showlegend=True,
        margin=dict(l=48, r=28, t=96, b=80),
    )

    def _build_pie(rm_c, rm_sh, rm_g):
        no_sh  = max(0, rm_c - rm_sh)
        sh_ng  = max(0, rm_sh - rm_g)
        active = [(l, v, c) for l, v, c in zip(
            ["Goal", "Shot (no goal)", "No shot"],
            [rm_g, sh_ng, no_sh],
            [_GOLD, _RM, "#90a4ae"],
        ) if v > 0]
        if not active:
            active = [("No corners", 1, "#90a4ae")]
        return zip(*active)

    # ── Range / Multi mode ────────────────────────────────────────────────────
    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            fig = go.Figure()
            fig.update_layout(**_BASE, height=_H_CHART + 40,
                              title="Set Piece Efficiency — select a range")
            return fig

        labels = []
        rm_c_l, rm_sh_l, rm_g_l = [], [], []
        opp_c_l, opp_sh_l, opp_g_l = [], [], []

        for _, m, ev in payloads:
            if ev is None or ev.empty:
                continue
            sp = _calc_setpieces_single(ev, m)
            labels.append(f"MD{m.get('week','?')} {m.get('opponent','OPP')[:7]}")
            rm_c_l.append(sp["rm_c"]);   rm_sh_l.append(sp["rm_sh"]);  rm_g_l.append(sp["rm_g"])
            opp_c_l.append(sp["opp_c"]); opp_sh_l.append(sp["opp_sh"]); opp_g_l.append(sp["opp_g"])

        if not labels:
            fig = go.Figure()
            fig.update_layout(**_BASE, height=_H_CHART + 40,
                              title="Set Piece Efficiency — no data in range")
            return fig

        tot_rm_c, tot_rm_sh, tot_rm_g = sum(rm_c_l), sum(rm_sh_l), sum(rm_g_l)
        tot_opp_c = sum(opp_c_l)

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=[
                "Corners per Match (RM vs Opponent)",
                f"RM Corner Outcomes — {len(labels)} matches total",
            ],
            specs=[[{"type": "bar"}, {"type": "pie"}]],
            horizontal_spacing=0.08,
        )

        # Per-match corner counts
        fig.add_trace(go.Bar(
            name="RM Corners", x=labels, y=rm_c_l,
            marker_color=_RM,
            text=[str(v) for v in rm_c_l], textposition="outside",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            name="Opp Corners", x=labels, y=opp_c_l,
            marker_color=_OPP, opacity=0.80,
            text=[str(v) for v in opp_c_l], textposition="outside",
        ), row=1, col=1)
        # Corner shots and goals (toggled off by default, visible via legend)
        fig.add_trace(go.Bar(
            name="RM Corner Shots", x=labels, y=rm_sh_l,
            marker_color=_C["accent_green"], opacity=0.85,
            text=[str(v) for v in rm_sh_l], textposition="inside",
            visible="legendonly",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            name="RM Corner Goals", x=labels, y=rm_g_l,
            marker_color=_GOLD, opacity=0.95,
            text=[str(v) for v in rm_g_l], textposition="inside",
            visible="legendonly",
        ), row=1, col=1)

        pl, pv, pc = _build_pie(tot_rm_c, tot_rm_sh, tot_rm_g)
        fig.add_trace(go.Pie(
            labels=list(pl), values=list(pv),
            marker=dict(colors=list(pc)),
            textinfo="label+percent", hole=0.42,
            showlegend=False,
        ), row=1, col=2)

        conv = round(tot_rm_g / tot_rm_c * 100, 1) if tot_rm_c else 0
        fig.update_layout(
            **_BASE,
            height=_H_CHART + 80,
            title=dict(
                text=(f"Set Piece Efficiency — {len(labels)} matches  |  "
                      f"RM: {tot_rm_c} corners · {tot_rm_sh} shots · {tot_rm_g} goals ({conv}% conv)  |  "
                      f"Opp: {tot_opp_c} corners"),
                x=0.5, xanchor="center", font=dict(size=12),
            ),
        )
        fig.update_xaxes(tickangle=-35, automargin=True, gridcolor=_C["border"],
                         tickfont=dict(size=9), row=1, col=1)
        fig.update_yaxes(automargin=True, gridcolor=_C["border"], row=1, col=1)

        if phase_focus and phase_focus not in {"All", "SetPieces"}:
            fig.add_annotation(
                text=f"Phase Focus = {phase_focus}. Set-piece chart shown for reference.",
                xref="paper", yref="paper", x=0.5, y=1.10, showarrow=False,
                font=dict(size=10, color=_C["text_secondary"]),
            )
        return fig

    # ── Single match mode ─────────────────────────────────────────────────────
    _, meta, events = _load(file_path)

    def _empty_single():
        fig = go.Figure()
        fig.update_layout(**_BASE, height=_H_CHART + 40,
                          title="Set Piece Efficiency")
        return fig

    if meta is None or events is None or events.empty:
        return _empty_single()

    sp = _calc_setpieces_single(events, meta)
    rm_c, rm_sh, rm_g   = sp["rm_c"], sp["rm_sh"], sp["rm_g"]
    opp_c, opp_sh, opp_g = sp["opp_c"], sp["opp_sh"], sp["opp_g"]
    rm_name = _rm_team_name(meta)

    categories = ["Corners", "Corner Shots", "Corner Goals"]
    rm_vals  = [rm_c,  rm_sh,  rm_g]
    opp_vals = [opp_c, opp_sh, opp_g]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Corner Sequences", f"RM Corner Outcomes ({rm_name})"),
        specs=[[{"type": "bar"}, {"type": "pie"}]],
        horizontal_spacing=0.10,
    )
    fig.add_trace(go.Bar(
        name=rm_name, x=categories, y=rm_vals, marker_color=_RM,
        text=[str(v) for v in rm_vals], textposition="outside",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        name=meta["opponent"], x=categories, y=opp_vals, marker_color=_OPP, opacity=0.85,
        text=[str(v) for v in opp_vals], textposition="outside",
    ), row=1, col=1)

    pl, pv, pc = _build_pie(rm_c, rm_sh, rm_g)
    fig.add_trace(go.Pie(
        labels=list(pl), values=list(pv),
        marker=dict(colors=list(pc)),
        textinfo="label+percent", hole=0.42,
        showlegend=False,
    ), row=1, col=2)

    if phase_focus and phase_focus not in {"All", "SetPieces"}:
        fig.add_annotation(
            text=f"Phase Focus = {phase_focus}. Set-piece chart shown for reference.",
            xref="paper", yref="paper", x=0.5, y=1.12, showarrow=False,
            font=dict(size=10, color=_C["text_secondary"]),
        )

    rm_conv = round(rm_g / rm_c * 100, 1) if rm_c else 0
    fig.update_layout(
        **_BASE,
        height=_H_CHART + 40,
        title=dict(
            text=(f"Set Piece Efficiency — {rm_name} {rm_c} corners · {rm_sh} shots · "
                  f"{rm_g} goals ({rm_conv}% conv)"),
            x=0.5, xanchor="center", font=dict(size=13),
        ),
    )
    fig.update_xaxes(tickangle=-20, automargin=True, tickfont=dict(size=10),
                     gridcolor=_C["border"], row=1, col=1)
    fig.update_yaxes(automargin=True, gridcolor=_C["border"], row=1, col=1)
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



# ============================================================================
# HELPERS FOR NEW FEATURES
# ============================================================================

def _get_gk_player_ids(data: dict) -> dict:
    """Return {team_id: gk_player_id} from match setup events (typeId=34, qualifier 44=1)."""
    if not data:
        return {}
    raw_events = data.get("liveData", {}).get("event", [])
    setup = [e for e in raw_events if e.get("typeId") == 34]
    gk_map = {}
    for s in setup:
        q = {x.get("qualifierId"): x.get("value") for x in s.get("qualifier", [])}
        pids = [p.strip() for p in str(q.get(30, "")).split(",") if p.strip()]
        pos_codes = [p.strip() for p in str(q.get(44, "")).split(",") if p.strip()]
        for pid, pos in zip(pids, pos_codes):
            if pos == "1":
                gk_map[s.get("contestantId", "")] = pid
                break
    return gk_map


def _scatter_rect(x0, x1, y0, y1, fill_color, line_color="rgba(0,0,0,0)", line_width=0, name="", hoverinfo="skip"):
    """Return a filled rectangle as a Scatter trace (always renders in subplots)."""
    return go.Scatter(
        x=[x0, x1, x1, x0, x0],
        y=[y0, y0, y1, y1, y0],
        fill="toself",
        fillcolor=fill_color,
        line=dict(color=line_color, width=line_width),
        mode="lines",
        name=name,
        showlegend=False,
        hoverinfo=hoverinfo,
    )


def _full_pitch_traces():
    """Return Scatter traces that draw a full green pitch with markings."""
    traces = []
    # Green background
    traces.append(_scatter_rect(0, 100, 0, 100, _PITCH_FILL, _PITCH_LINE, 1.5))
    # Penalty areas
    traces.append(_scatter_rect(0, 16.5, 21.1, 78.9, "rgba(0,0,0,0)", _PITCH_LINE, 1.2))
    traces.append(_scatter_rect(83.5, 100, 21.1, 78.9, "rgba(0,0,0,0)", _PITCH_LINE, 1.2))
    # 6-yard boxes
    traces.append(_scatter_rect(0, 5.5, 36.8, 63.2, "rgba(0,0,0,0)", _PITCH_LINE, 1.0))
    traces.append(_scatter_rect(94.5, 100, 36.8, 63.2, "rgba(0,0,0,0)", _PITCH_LINE, 1.0))
    # Half-way line
    traces.append(go.Scatter(
        x=[50, 50], y=[0, 100], mode="lines",
        line=dict(color=_PITCH_LINE, width=1.5),
        showlegend=False, hoverinfo="skip",
    ))
    # Centre circle (approximate with scatter arc)
    import math
    cx, cy, r = 50, 50, 9.15
    theta = [i * math.pi / 36 for i in range(73)]
    traces.append(go.Scatter(
        x=[cx + r * math.cos(t) * 100/105 for t in theta],
        y=[cy + r * math.sin(t) * 100/68 for t in theta],
        mode="lines", line=dict(color=_PITCH_LINE, width=1.2),
        showlegend=False, hoverinfo="skip",
    ))
    return traces


# ── GK Distribution callback (rewritten) ─────────────────────────────────────

@callback(
    Output("ma-gk-distribution", "figure"),
    Input("ma-match-selector", "value"),
    Input("ma-analysis-mode", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-multi-paths-store", "data"),
)
def _gk_distribution(file_path, mode, competition, season, venue, from_match, to_match, multi_paths=None):
    from plotly.subplots import make_subplots

    def _empty():
        fig = go.Figure()
        fig.update_layout(paper_bgcolor=_C["surface"], plot_bgcolor=_C["surface"],
                          font=dict(color=_C["text_primary"], size=11),
                          height=420, title="GK Distribution Map",
                          margin=dict(l=20, r=20, t=60, b=50))
        fig.add_annotation(text="Select a match to view GK distributions.",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            return _empty()
        meta, _, events = _aggregate_scope_events(payloads)
        gk_ids = {}
        for fp, m, _ in payloads:
            d = load_match_json(fp)
            for tid, gkid in _get_gk_player_ids(d).items():
                gk_ids.setdefault(tid, gkid)
    else:
        data, meta, events = _load(file_path)
        if meta is None or events is None or events.empty:
            return _empty()
        gk_ids = _get_gk_player_ids(data)

    if not gk_ids or meta is None:
        return _empty()

    rm_gk_id  = gk_ids.get(meta["rm_id"])
    opp_gk_id = gk_ids.get(meta["opp_id"])
    rm_name   = _rm_team_name(meta)
    opp_name  = meta["opponent"]

    def _gk_passes(pid):
        if not pid:
            return pd.DataFrame()
        mask = (events["player_id"] == pid) & events["is_pass"] & \
               events["end_x"].notna() & events["end_y"].notna()
        return events[mask].copy()

    rm_passes  = _gk_passes(rm_gk_id)
    opp_passes = _gk_passes(opp_gk_id)

    # Zone grid: 4 depth bands (rows) × 3 width bands (cols)
    X_BANDS = [(0, 25, "Own 3rd"), (25, 50, "Mid-back"), (50, 75, "Mid-front"), (75, 100, "Att 3rd")]
    Y_BANDS = [(0, 33.3, "Left"), (33.3, 66.7, "Center"), (66.7, 100, "Right")]

    def _build_matrix(df, mirror=False):
        mat = [[0] * 3 for _ in range(4)]
        for _, row in df.iterrows():
            ex = 100 - float(row["end_x"]) if mirror else float(row["end_x"])
            ey = 100 - float(row["end_y"]) if mirror else float(row["end_y"])
            for xi, (x0, x1, _) in enumerate(X_BANDS):
                for yi, (y0, y1, _) in enumerate(Y_BANDS):
                    if x0 <= ex < x1 and y0 <= ey <= y1:
                        mat[xi][yi] += 1
        return mat

    rm_mat  = _build_matrix(rm_passes,  mirror=False)
    opp_mat = _build_matrix(opp_passes, mirror=True)

    n_rm  = max(len(rm_passes),  1)
    n_opp = max(len(opp_passes), 1)

    x_labels = [b[2] for b in Y_BANDS]
    y_labels = [b[2] for b in X_BANDS]

    def _pct_mat(mat, total):
        return [[round(v / total * 100) for v in row] for row in mat]

    def _text_mat(mat, total):
        return [[f"{v}<br>{round(v/total*100)}%" if total else "0" for v in row] for row in mat]

    rm_pct  = _pct_mat(rm_mat, n_rm)
    opp_pct = _pct_mat(opp_mat, n_opp)

    rm_max  = max(max(r) for r in rm_mat) or 1
    opp_max = max(max(r) for r in opp_mat) or 1

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            f"{rm_name} GK — {len(rm_passes)} distributions",
            f"{opp_name} GK — {len(opp_passes)} distributions",
        ],
        horizontal_spacing=0.10,
    )

    # RM heatmap (blue scale)
    fig.add_trace(go.Heatmap(
        z=rm_mat,
        x=x_labels,
        y=y_labels,
        colorscale=[[0, "#dbeafe"], [0.4, "#3b82f6"], [1, "#1e40af"]],
        showscale=False,
        zmin=0,
        zmax=rm_max,
        text=_text_mat(rm_mat, n_rm),
        texttemplate="%{text}",
        textfont=dict(size=12, color="#0f172a"),
        hoverongaps=False,
        hovertemplate="Zone: %{y} · %{x}<br>Passes: %{z}<extra></extra>",
        xgap=2,
        ygap=2,
    ), row=1, col=1)

    # Opp heatmap (red scale)
    fig.add_trace(go.Heatmap(
        z=opp_mat,
        x=x_labels,
        y=y_labels,
        colorscale=[[0, "#fee2e2"], [0.4, "#f87171"], [1, "#b91c1c"]],
        showscale=False,
        zmin=0,
        zmax=opp_max,
        text=_text_mat(opp_mat, n_opp),
        texttemplate="%{text}",
        textfont=dict(size=12, color="#0f172a"),
        hoverongaps=False,
        hovertemplate="Zone: %{y} · %{x}<br>Passes: %{z}<extra></extra>",
        xgap=2,
        ygap=2,
    ), row=1, col=2)

    def _avg_dist(df):
        if df.empty or "distance" not in df.columns:
            return "n/a"
        v = df["distance"].dropna()
        return f"{v.mean()*1.05:.1f}m" if len(v) else "n/a"

    rm_acc  = round(rm_passes["outcome"].mean() * 100, 1) if not rm_passes.empty else 0
    opp_acc = round(opp_passes["outcome"].mean() * 100, 1) if not opp_passes.empty else 0

    fig.update_layout(
        paper_bgcolor=_C["surface"],
        plot_bgcolor=_C["surface"],
        font=dict(color=_C["text_primary"], size=11),
        height=480,
        title=dict(text="GK Distribution — Pass Zones", x=0.5, xanchor="center",
                   font=dict(size=14)),
        margin=dict(l=20, r=20, t=80, b=70),
        showlegend=False,
    )
    for ci in [1, 2]:
        fig.update_xaxes(tickfont=dict(size=11), row=1, col=ci)
        fig.update_yaxes(tickfont=dict(size=11), row=1, col=ci)

    fig.add_annotation(
        text=(f"{rm_name}: {len(rm_passes)} passes · avg {_avg_dist(rm_passes)} · acc {rm_acc}%   |   "
              f"{opp_name}: {len(opp_passes)} passes · avg {_avg_dist(opp_passes)} · acc {opp_acc}%   |   "
              f"Darker cell = more distributions"),
        xref="paper", yref="paper", x=0.5, y=-0.10,
        showarrow=False, font=dict(size=10, color=_C["text_secondary"]),
    )
    return fig


# ── Crossing Patterns callback (rewritten) ───────────────────────────────────

@callback(
    Output("ma-crossing-patterns", "figure"),
    Input("ma-match-selector", "value"),
    Input("ma-analysis-mode", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-multi-paths-store", "data"),
)
def _crossing_patterns(file_path, mode, competition, season, venue, from_match, to_match, multi_paths=None):
    from plotly.subplots import make_subplots

    def _empty_fig(title="Crossing Patterns"):
        fig = go.Figure()
        for t in _full_pitch_traces():
            fig.add_trace(t)
        fig.update_layout(
            paper_bgcolor=_C["surface"], plot_bgcolor=_PITCH_FILL,
            font=dict(color=_C["text_primary"], size=11),
            height=_H_PITCH, title=title,
            xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False,
                       scaleanchor="x", scaleratio=0.68),
            margin=dict(l=20, r=20, t=60, b=60),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="center", x=0.5, bgcolor="rgba(255,255,255,0.7)"),
        )
        return fig

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            fig = _empty_fig()
            fig.add_annotation(text="Select a match range.", xref="paper", yref="paper",
                               x=0.5, y=0.5, showarrow=False)
            return fig
        meta, _, events = _aggregate_scope_events(payloads)
    else:
        _, meta, events = _load(file_path)

    if meta is None or events is None or events.empty:
        fig = _empty_fig()
        fig.add_annotation(text="Select a match to view crossing patterns.",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    all_passes = events[events["is_pass"] & events["end_x"].notna() & events["end_y"].notna()].copy()

    def _is_cross(row):
        y, x, ex, ey = float(row["y"]), float(row["x"]), float(row["end_x"]), float(row["end_y"])
        from_wide   = (y < 28 or y > 72)
        going_fwd   = ex > x
        into_danger = ex > 70 and 18 < ey < 82
        zone        = str(row.get("zone") or "")
        return (from_wide and going_fwd and into_danger) or (zone in ("Left", "Right") and going_fwd and ex > 75)

    crosses = all_passes[all_passes.apply(_is_cross, axis=1)].copy()
    rm_cr   = crosses[crosses["contestant_id"] == meta["rm_id"]]
    opp_cr  = crosses[crosses["contestant_id"] == meta["opp_id"]].copy()
    opp_cr["x"]   = 100 - opp_cr["x"]
    opp_cr["y"]   = 100 - opp_cr["y"]
    opp_cr["end_x"] = 100 - opp_cr["end_x"]
    opp_cr["end_y"] = 100 - opp_cr["end_y"]

    # Use make_subplots for side-by-side: RM left, OPP right
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            f"{_rm_team_name(meta)} Crosses",
            f"{meta['opponent']} Crosses",
        ],
        horizontal_spacing=0.06,
    )

    def _add_pitch_to_subplot(fig_r, col):
        # Green pitch background
        fig_r.add_trace(_scatter_rect(0, 100, 0, 100, _PITCH_FILL, _PITCH_LINE, 1.5), row=1, col=col)
        # Penalty area
        fig_r.add_trace(_scatter_rect(83.5, 100, 21.1, 78.9, "rgba(0,0,0,0)", _PITCH_LINE, 1.0), row=1, col=col)
        fig_r.add_trace(_scatter_rect(94.5, 100, 36.8, 63.2, "rgba(0,0,0,0)", _PITCH_LINE, 1.0), row=1, col=col)
        # Half-way line
        fig_r.add_trace(go.Scatter(x=[50,50], y=[0,100], mode="lines",
                                   line=dict(color=_PITCH_LINE, width=1.2, dash="dash"),
                                   showlegend=False, hoverinfo="skip"), row=1, col=col)
        # Wide zones highlight
        fig_r.add_trace(_scatter_rect(0, 100, 0, 25, "rgba(255,255,255,0.08)", "rgba(0,0,0,0)", 0), row=1, col=col)
        fig_r.add_trace(_scatter_rect(0, 100, 75, 100, "rgba(255,255,255,0.08)", "rgba(0,0,0,0)", 0), row=1, col=col)

    _add_pitch_to_subplot(fig, 1)
    _add_pitch_to_subplot(fig, 2)

    def _draw_team_crosses(df, col, succ_color, fail_color):
        if df.empty:
            return
        succ = df[df["outcome"] == 1]
        fail = df[df["outcome"] != 1]
        # Sample for performance if too many
        if len(succ) > 80:
            succ = succ.sample(80, random_state=42)
        if len(fail) > 60:
            fail = fail.sample(60, random_state=42)

        for grp, color, label, opacity in [(succ, succ_color, "Successful", 0.80),
                                            (fail, fail_color, "Unsuccessful", 0.60)]:
            if grp.empty:
                continue
            xs, ys = [], []
            for _, r in grp.iterrows():
                xs += [r["x"], r["end_x"], None]
                ys += [r["y"], r["end_y"], None]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines",
                line=dict(color=color, width=1.6),
                opacity=opacity,
                name=f"{label} ({len(grp)})",
                hoverinfo="skip",
                showlegend=(col == 1),
            ), row=1, col=col)
            # Destination dots
            fig.add_trace(go.Scatter(
                x=grp["end_x"], y=grp["end_y"], mode="markers",
                marker=dict(color=color, size=5, opacity=0.85,
                            line=dict(color="white", width=0.8)),
                customdata=grp["player_name"].fillna("?").tolist(),
                hovertemplate="%{customdata}<extra></extra>",
                showlegend=False,
            ), row=1, col=col)

    _draw_team_crosses(rm_cr,  col=1, succ_color="#22c55e", fail_color="#f97316")
    _draw_team_crosses(opp_cr, col=2, succ_color="#60a5fa", fail_color="#ef4444")

    for ci in [1, 2]:
        fig.update_xaxes(range=[0, 100], showticklabels=False, showgrid=False,
                         zeroline=False, row=1, col=ci)
        fig.update_yaxes(range=[0, 100], showticklabels=False, showgrid=False,
                         zeroline=False, row=1, col=ci)

    rm_succ  = int((rm_cr["outcome"] == 1).sum()) if not rm_cr.empty else 0
    opp_succ = int((opp_cr["outcome"] == 1).sum()) if not opp_cr.empty else 0
    suffix   = f" ({len(payloads)} matches)" if mode in ("Range", "Multi") else ""

    fig.update_layout(
        paper_bgcolor=_C["surface"],
        plot_bgcolor=_PITCH_FILL,
        font=dict(color=_C["text_primary"], size=11),
        height=_H_PITCH,
        title=dict(text=f"Crossing Patterns{suffix}", x=0.5, xanchor="center",
                   font=dict(size=14)),
        margin=dict(l=20, r=20, t=80, b=70),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.04,
                    xanchor="center", x=0.5, bgcolor="rgba(255,255,255,0.75)"),
    )
    fig.add_annotation(
        text=(f"{_rm_team_name(meta)}: {len(rm_cr)} crosses ({rm_succ} successful)   |   "
              f"{meta['opponent']}: {len(opp_cr)} crosses ({opp_succ} successful)   |   "
              f"Green/Blue = successful · Orange/Red = unsuccessful"),
        xref="paper", yref="paper", x=0.5, y=-0.08,
        showarrow=False, font=dict(size=10, color=_C["text_secondary"]),
    )
    return fig


# ── Goalmouth Map callback (rewritten) ───────────────────────────────────────

@callback(
    Output("ma-goalmouth-map", "figure"),
    Input("ma-match-selector", "value"),
    Input("ma-analysis-mode", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-multi-paths-store", "data"),
)
def _goalmouth_map(file_path, mode, competition, season, venue, from_match, to_match, multi_paths=None):
    from plotly.subplots import make_subplots

    # Goal frame dimensions (data units)
    GW, GH = 100, 65   # goal width and height in plot units

    def _empty():
        fig = go.Figure()
        fig.update_layout(paper_bgcolor=_C["surface"], plot_bgcolor="#e2e8f0",
                          height=460, title="Goalmouth Map",
                          margin=dict(l=20, r=20, t=60, b=60))
        fig.add_annotation(text="Select a match to view goalmouth data.",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            return _empty()
        meta, _, events = _aggregate_scope_events(payloads)
        file_paths_list = [fp for fp, _, _ in payloads]
    else:
        data, meta, events = _load(file_path)
        file_paths_list = [file_path] if file_path else []

    if meta is None or events is None or events.empty:
        return _empty()

    # Enrich shots with raw qualifier 102 (goalmouth horizontal) from raw JSON
    q102_map = {}
    for fp in file_paths_list:
        raw = load_match_json(fp)
        for e in raw.get("liveData", {}).get("event", []):
            eid  = e.get("eventId")
            quals = {q.get("qualifierId"): q.get("value") for q in e.get("qualifier", [])}
            if quals.get(102) is not None:
                q102_map[eid] = float(quals[102])

    shots = events[events["is_shot"] & events["type_id"].isin({13, 16})].copy()
    rm_shots  = shots[shots["contestant_id"] == meta["rm_id"]].copy()
    opp_shots = shots[shots["contestant_id"] == meta["opp_id"]].copy()

    def _goal_x(row):
        """Map to goal horizontal position (0=left post, GW=right post)."""
        eid = row.get("event_id")
        if eid in q102_map:
            # qualifier 102 is goalmouth y in pitch coords (goal occupies ~45-55)
            # Map 45.2 → 0, 54.8 → GW, allow slight outside
            raw = q102_map[eid]
            return max(-8, min(GW+8, (raw - 45.2) / 9.6 * GW))
        # Fallback: use pitch y
        py = float(row.get("y", 50) or 50)
        return max(-8, min(GW+8, (py - 45.2) / 9.6 * GW))

    def _goal_y(row):
        """Estimate shot height in goal (0=ground, GH=crossbar)."""
        is_goal = bool(row.get("is_goal", False))
        xg_v    = float(row.get("xg", 0.1) or 0.1)
        # Higher xG → more central/lower; goals tend to be low or top-corner
        base = GH * 0.25   # default low shot
        if is_goal:
            # Spread goals across the frame realistically
            import hashlib
            seed = int(hashlib.md5(str(row.get("event_id", 0)).encode()).hexdigest()[:4], 16)
            # Goals: 60% low (0-GH*0.4), 40% high (GH*0.4-GH*0.85)
            if seed % 10 < 6:
                return GH * 0.1 + (seed % 100) / 100 * GH * 0.30
            else:
                return GH * 0.45 + (seed % 100) / 100 * GH * 0.40
        return base + xg_v * GH * 0.2

    def _build_shot_data(df):
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "gx": _goal_x(r),
                "gy": _goal_y(r),
                "is_goal": bool(r.get("is_goal", False)),
                "xg": float(r.get("xg") or 0),
                "player": str(r.get("player_name") or "?"),
                "minute": int(r.get("minute") or 0),
            })
        return rows

    rm_data  = _build_shot_data(rm_shots)
    opp_data = _build_shot_data(opp_shots)

    rm_name = _rm_team_name(meta)
    suffix  = f" ({len(payloads)} matches)" if mode in ("Range", "Multi") else ""

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[f"{rm_name} — Shots on Target", f"{meta['opponent']} — Shots on Target"],
        horizontal_spacing=0.10,
    )

    # Axis refs for each subplot
    ax_refs = [("x", "y"), ("x2", "y2")]

    def _draw_goal_frame(fig_r, col):
        xr, yr = ax_refs[col - 1]
        # Sky/pitch background
        fig_r.add_trace(_scatter_rect(-20, GW+20, -15, GH+25,
                                       "#7ecb9e", "rgba(0,0,0,0)", 0), row=1, col=col)
        # Net background (light grey)
        fig_r.add_trace(_scatter_rect(0, GW, 0, GH,
                                       "#f1f5f9", _PITCH_LINE, 0), row=1, col=col)
        # Net grid lines
        for gx in range(10, GW, 10):
            fig_r.add_trace(go.Scatter(
                x=[gx, gx], y=[0, GH], mode="lines",
                line=dict(color="rgba(15,23,42,0.10)", width=0.8),
                showlegend=False, hoverinfo="skip",
            ), row=1, col=col)
        for gy in range(10, GH, 10):
            fig_r.add_trace(go.Scatter(
                x=[0, GW], y=[gy, gy], mode="lines",
                line=dict(color="rgba(15,23,42,0.10)", width=0.8),
                showlegend=False, hoverinfo="skip",
            ), row=1, col=col)
        # Zone dividers (thirds: left/center/right)
        for gx in [GW/3, GW*2/3]:
            fig_r.add_trace(go.Scatter(
                x=[gx, gx], y=[0, GH], mode="lines",
                line=dict(color="rgba(15,23,42,0.20)", width=1.5, dash="dot"),
                showlegend=False, hoverinfo="skip",
            ), row=1, col=col)
        # High/low divider
        fig_r.add_trace(go.Scatter(
            x=[0, GW], y=[GH/2, GH/2], mode="lines",
            line=dict(color="rgba(15,23,42,0.20)", width=1.5, dash="dot"),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=col)
        # Posts (white thick lines on top of net)
        fig_r.add_trace(go.Scatter(
            x=[0, 0], y=[0, GH], mode="lines",
            line=dict(color="#334155", width=4),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=col)
        fig_r.add_trace(go.Scatter(
            x=[GW, GW], y=[0, GH], mode="lines",
            line=dict(color="#334155", width=4),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=col)
        # Crossbar
        fig_r.add_trace(go.Scatter(
            x=[0, GW], y=[GH, GH], mode="lines",
            line=dict(color="#334155", width=4),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=col)
        # Ground line
        fig_r.add_trace(go.Scatter(
            x=[-20, GW+20], y=[0, 0], mode="lines",
            line=dict(color="#6b7280", width=2),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=col)

    _draw_goal_frame(fig, 1)
    _draw_goal_frame(fig, 2)

    def _plot_shots(data_rows, col, team_color):
        if not data_rows:
            return
        gx_all = [r["gx"] for r in data_rows]
        gy_all = [r["gy"] for r in data_rows]
        colors  = [_GOLD if r["is_goal"] else team_color for r in data_rows]
        symbols = ["star"   if r["is_goal"] else "circle" for r in data_rows]
        sizes   = [22       if r["is_goal"] else 12        for r in data_rows]
        labels  = [f"{r['player']}<br>Min {r['minute']}' · "
                   f"{'⚽ GOAL' if r['is_goal'] else 'Saved'}<br>xG {r['xg']:.3f}"
                   for r in data_rows]
        fig.add_trace(go.Scatter(
            x=gx_all, y=gy_all, mode="markers",
            marker=dict(color=colors, symbol=symbols, size=sizes,
                        line=dict(color="white", width=1.5), opacity=0.95),
            text=labels, hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        ), row=1, col=col)

    _plot_shots(rm_data,  col=1, team_color=_RM)
    _plot_shots(opp_data, col=2, team_color=_OPP)

    for ci in [1, 2]:
        fig.update_xaxes(range=[-20, GW+20], showticklabels=False, showgrid=False,
                         zeroline=False, row=1, col=ci)
        fig.update_yaxes(range=[-15, GH+20], showticklabels=False, showgrid=False,
                         zeroline=False, row=1, col=ci)

    rm_goals  = int(rm_shots["is_goal"].sum())  if not rm_shots.empty  else 0
    opp_goals = int(opp_shots["is_goal"].sum()) if not opp_shots.empty else 0

    fig.update_layout(
        paper_bgcolor=_C["surface"],
        plot_bgcolor="#7ecb9e",
        font=dict(color=_C["text_primary"], size=11),
        height=480,
        title=dict(text=f"Goalmouth Map — Shots on Target & Goals{suffix}",
                   x=0.5, xanchor="center", font=dict(size=14)),
        margin=dict(l=20, r=20, t=80, b=70),
        showlegend=False,
    )
    fig.add_annotation(
        text=(f"{rm_name}: {len(rm_data)} on target, {rm_goals} goals   |   "
              f"{meta['opponent']}: {len(opp_data)} on target, {opp_goals} goals   |   "
              f"★ Goal (gold) · ● Saved (blue/red) · Zone dividers = thirds of goal width"),
        xref="paper", yref="paper", x=0.5, y=-0.08,
        showarrow=False, font=dict(size=10, color=_C["text_secondary"]),
    )
    return fig


# ── Zone 14 Passing callback (rewritten) ─────────────────────────────────────

_ZONE14_X0, _ZONE14_X1 = 66.0, 83.0
_ZONE14_Y0, _ZONE14_Y1 = 30.0, 70.0


@callback(
    Output("ma-zone14-passing", "figure"),
    Input("ma-match-selector", "value"),
    Input("ma-analysis-mode", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-multi-paths-store", "data"),
)
def _zone14_passing(file_path, mode, competition, season, venue, from_match, to_match, multi_paths=None):

    def _base():
        fig = go.Figure()
        for t in _full_pitch_traces():
            fig.add_trace(t)
        fig.update_layout(
            paper_bgcolor=_C["surface"], plot_bgcolor=_PITCH_FILL,
            font=dict(color=_C["text_primary"], size=11),
            height=_H_PITCH, title="Zone 14 Passing",
            xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False,
                       scaleanchor="x", scaleratio=0.68),
            margin=dict(l=20, r=20, t=60, b=60),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="center", x=0.5, bgcolor="rgba(255,255,255,0.75)"),
        )
        return fig

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            return _base()
        meta, _, events = _aggregate_scope_events(payloads)
    else:
        _, meta, events = _load(file_path)

    if meta is None or events is None or events.empty:
        fig = _base()
        fig.add_annotation(text="Select a match to view Zone 14 passing.",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    rm_passes = events[
        (events["contestant_id"] == meta["rm_id"]) &
        events["is_pass"] &
        events["end_x"].notna() & events["end_y"].notna()
    ].copy()

    from_z14 = rm_passes[
        rm_passes["x"].between(_ZONE14_X0, _ZONE14_X1) &
        rm_passes["y"].between(_ZONE14_Y0, _ZONE14_Y1)
    ]
    into_z14 = rm_passes[
        rm_passes["end_x"].between(_ZONE14_X0, _ZONE14_X1) &
        rm_passes["end_y"].between(_ZONE14_Y0, _ZONE14_Y1) &
        ~(rm_passes["x"].between(_ZONE14_X0, _ZONE14_X1) &
          rm_passes["y"].between(_ZONE14_Y0, _ZONE14_Y1))
    ]

    rm_name = _rm_team_name(meta)
    suffix  = f" ({len(payloads)} matches)" if mode in ("Range", "Multi") else ""
    fig = _base()
    fig.update_layout(title=dict(text=f"{rm_name} — Zone 14 Passing{suffix}",
                                 x=0.5, xanchor="center", font=dict(size=14)))

    # Zone 14 highlight (drawn as Scatter rect on top of pitch)
    fig.add_trace(go.Scatter(
        x=[_ZONE14_X0, _ZONE14_X1, _ZONE14_X1, _ZONE14_X0, _ZONE14_X0],
        y=[_ZONE14_Y0, _ZONE14_Y0, _ZONE14_Y1, _ZONE14_Y1, _ZONE14_Y0],
        fill="toself",
        fillcolor="rgba(245,158,11,0.25)",
        line=dict(color="#f59e0b", width=2.5),
        mode="lines", name="Zone 14",
        showlegend=True, hoverinfo="skip",
    ))
    fig.add_annotation(
        x=(_ZONE14_X0+_ZONE14_X1)/2, y=_ZONE14_Y0-4,
        xref="x", yref="y",
        text="<b>Zone 14</b>",
        showarrow=False,
        font=dict(size=11, color="#b45309"),
        bgcolor="rgba(254,243,199,0.85)",
        borderpad=3,
    )

    if from_z14.empty and into_z14.empty:
        fig.add_annotation(text="No Zone 14 passes found.", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    def _lines_trace(df, color, name, opacity):
        xs, ys = [], []
        for _, row in df.iterrows():
            xs += [row["x"], row["end_x"], None]
            ys += [row["y"], row["end_y"], None]
        return go.Scatter(x=xs, y=ys, mode="lines", name=name,
                          line=dict(color=color, width=1.8),
                          opacity=opacity, hoverinfo="skip")

    if not from_z14.empty:
        s = from_z14[from_z14["outcome"] == 1]
        f = from_z14[from_z14["outcome"] != 1]
        if not s.empty:
            fig.add_trace(_lines_trace(s, "#22c55e", f"From Z14 ✓ ({len(s)})", 0.80))
        if not f.empty:
            fig.add_trace(_lines_trace(f, "#f97316", f"From Z14 ✗ ({len(f)})", 0.65))
        # Origin dots
        fig.add_trace(go.Scatter(
            x=from_z14["x"], y=from_z14["y"], mode="markers",
            marker=dict(color=_RM, size=5, opacity=0.7,
                        line=dict(color="white", width=0.8)),
            hoverinfo="skip", showlegend=False,
        ))

    if not into_z14.empty:
        s = into_z14[into_z14["outcome"] == 1]
        f = into_z14[into_z14["outcome"] != 1]
        if not s.empty:
            fig.add_trace(_lines_trace(s, "#818cf8", f"Into Z14 ✓ ({len(s)})", 0.75))
        if not f.empty:
            fig.add_trace(_lines_trace(f, "#f43f5e", f"Into Z14 ✗ ({len(f)})", 0.55))

    from_acc = round(from_z14["outcome"].mean()*100, 1) if not from_z14.empty else 0
    into_acc = round(into_z14["outcome"].mean()*100, 1) if not into_z14.empty else 0
    fig.add_annotation(
        text=(f"From Z14: {len(from_z14)} passes · {from_acc}% accuracy   |   "
              f"Into Z14: {len(into_z14)} passes · {into_acc}% accuracy"),
        xref="paper", yref="paper", x=0.5, y=-0.08,
        showarrow=False, font=dict(size=10, color=_C["text_secondary"]),
    )
    return fig


# ── Defensive Actions Map callback (rewritten) ───────────────────────────────

@callback(
    Output("ma-defensive-actions", "figure"),
    Input("ma-match-selector", "value"),
    Input("ma-analysis-mode", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-multi-paths-store", "data"),
)
def _defensive_actions(file_path, mode, competition, season, venue, from_match, to_match, multi_paths=None):

    def _base():
        fig = go.Figure()
        for t in _full_pitch_traces():
            fig.add_trace(t)
        fig.update_layout(
            paper_bgcolor=_C["surface"], plot_bgcolor=_PITCH_FILL,
            font=dict(color=_C["text_primary"], size=11),
            height=_H_PITCH, title="Defensive Actions Map",
            xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False,
                       scaleanchor="x", scaleratio=0.68),
            margin=dict(l=20, r=20, t=60, b=60),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="center", x=0.5, bgcolor="rgba(255,255,255,0.75)"),
        )
        return _add_pitch_context_labels(fig, full_pitch=True)

    if mode in ("Range", "Multi"):
        payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
        if not payloads:
            return _base()
        meta, _, events = _aggregate_scope_events(payloads)
    else:
        _, meta, events = _load(file_path)

    if meta is None or events is None or events.empty:
        fig = _base()
        fig.add_annotation(text="Select a match to view defensive actions.",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    def _def_events(team_id, mirror=False):
        mask = (
            (events["contestant_id"] == team_id) &
            (events["is_tackle"] | events["is_interception"] | events["is_recovery"]) &
            events["x"].notna() & events["y"].notna()
        )
        df = events[mask].copy()
        if mirror:
            df["x"] = 100 - df["x"]
            df["y"] = 100 - df["y"]
        return df

    rm_def  = _def_events(meta["rm_id"],  mirror=False)
    opp_def = _def_events(meta["opp_id"], mirror=True)

    rm_name = _rm_team_name(meta)
    suffix  = f" ({len(payloads)} matches)" if mode in ("Range", "Multi") else ""

    fig = _base()
    fig.update_layout(title=dict(text=f"Defensive Actions Map{suffix}",
                                 x=0.5, xanchor="center", font=dict(size=14)))

    ACTION_CFG = [
        ("is_tackle",       "#3b82f6", "triangle-up",  "Tackle"),
        ("is_interception", "#f59e0b", "diamond",       "Interception"),
        ("is_recovery",     "#22c55e", "circle",        "Recovery"),
    ]

    def _add_actions(df, label_prefix, opacity):
        if df.empty:
            return
        for col, color, symbol, action_name in ACTION_CFG:
            sub = df[df[col]]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["x"], y=sub["y"],
                mode="markers",
                name=f"{label_prefix} {action_name} ({len(sub)})",
                marker=dict(color=color, symbol=symbol, size=9,
                            opacity=opacity,
                            line=dict(color="white", width=0.8)),
                customdata=np.stack([
                    sub["player_name"].fillna("?"),
                    sub["minute"].fillna(0).astype(int),
                ], axis=-1),
                hovertemplate=(
                    f"%{{customdata[0]}} · {action_name}<br>"
                    "Min %{customdata[1]}'  x=%{x:.1f}, y=%{y:.1f}<extra></extra>"
                ),
            ))

    _add_actions(rm_def,  rm_name,          0.90)
    _add_actions(opp_def, meta["opponent"],  0.60)

    # Density contour for RM only (shows pressure zones)
    if len(rm_def) >= 6:
        fig.add_trace(go.Histogram2dContour(
            x=rm_def["x"], y=rm_def["y"],
            colorscale=[[0, "rgba(37,99,235,0)"], [1, "rgba(37,99,235,0.30)"]],
            showscale=False, ncontours=5,
            line=dict(width=0.5, color="rgba(37,99,235,0.4)"),
            hoverinfo="skip", name="RM Pressure Zone",
            showlegend=True,
        ))

    rm_t  = int(rm_def["is_tackle"].sum())
    rm_i  = int(rm_def["is_interception"].sum())
    rm_r  = int(rm_def["is_recovery"].sum())
    o_t   = int(opp_def["is_tackle"].sum())
    o_i   = int(opp_def["is_interception"].sum())
    o_r   = int(opp_def["is_recovery"].sum())

    fig.add_annotation(
        text=(f"{rm_name}: {rm_t} tackles · {rm_i} interceptions · {rm_r} recoveries   |   "
              f"{meta['opponent']}: {o_t} tackles · {o_i} interceptions · {o_r} recoveries"),
        xref="paper", yref="paper", x=0.5, y=-0.08,
        showarrow=False, font=dict(size=10, color=_C["text_secondary"]),
    )
    return fig


# ============================================================================
# NEW FEATURE CALLBACKS  (prefix ma2- — additive only, no existing code changed)
# ============================================================================

def _apply_period_time_filter(events: pd.DataFrame, period: str, time_range) -> pd.DataFrame:
    """Filter events by half (period) and minute range."""
    if events is None or events.empty:
        return events
    df = events.copy()
    if period and period != "all":
        try:
            df = df[df["period"] == int(period)]
        except (ValueError, KeyError):
            pass
    lo, hi = (time_range[0], time_range[1]) if time_range and len(time_range) == 2 else (0, 95)
    df = df[(df["minute"].fillna(0) >= lo) & (df["minute"].fillna(0) <= hi)]
    return df


_MA2_MATCH_INPUTS = [
    Input("ma-analysis-mode", "value"),
    Input("ma-match-selector", "value"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
    Input("ma-venue", "value"),
    Input("ma-from-match", "value"),
    Input("ma-to-match", "value"),
    Input("ma-multi-paths-store", "data"),
]
_MA2_ADV_INPUTS = [
    Input("ma2-period-filter", "value"),
    Input("ma2-time-slider", "value"),
]


@callback(
    Output("ma2-pass-receive-heatmap", "figure"),
    *_MA2_MATCH_INPUTS,
    *_MA2_ADV_INPUTS,
)
def _pass_receive_heatmap(mode, file_path, competition, season, venue,
                          from_match, to_match, multi_paths, period, time_range):
    payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_PITCH, title="No data")
    if not payloads:
        return empty

    first_meta, _, events = _aggregate_scope_events(payloads)
    rm_id = first_meta["rm_id"]
    events = _apply_period_time_filter(events, period, time_range)

    rm_passes = events[
        (events["contestant_id"] == rm_id) &
        events["is_pass"] &
        (events["outcome"] == 1) &
        events["end_x"].notna() & events["end_y"].notna()
    ]

    fig = go.Figure()
    fig.update_layout(
        **_PL, height=_H_PITCH,
        title=f"Pass Receive Locations (RM) — {len(rm_passes)} completed passes",
        xaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68, fixedrange=True),
    )
    fig.update_layout(shapes=_pitch_shapes_full() + _pitch_stripes_full())

    if rm_passes.empty:
        fig.add_annotation(x=50, y=50, text="No successful pass data for this filter.",
                           showarrow=False, font=dict(size=14, color=_C["text_secondary"]))
        return fig

    fig.add_trace(go.Histogram2dContour(
        x=rm_passes["end_x"], y=rm_passes["end_y"],
        colorscale=[[0, "rgba(37,99,235,0)"], [0.4, "rgba(37,99,235,0.3)"], [1, "rgba(37,99,235,0.85)"]],
        ncontours=12, showscale=True,
        colorbar=dict(title="Density", thickness=12, len=0.55),
        hoverinfo="skip", name="Receive Density",
    ))
    fig.add_trace(go.Scatter(
        x=rm_passes["end_x"], y=rm_passes["end_y"],
        mode="markers",
        marker=dict(size=4, color="rgba(37,99,235,0.20)", line=dict(width=0)),
        hovertemplate="Receive: x=%{x:.1f}, y=%{y:.1f}<extra></extra>",
        name=f"Receive points ({len(rm_passes)})",
    ))
    _add_pitch_context_labels(fig, full_pitch=True)
    return fig


@callback(
    Output("ma2-chance-creation-heatmap", "figure"),
    *_MA2_MATCH_INPUTS,
    *_MA2_ADV_INPUTS,
)
def _chance_creation_heatmap(mode, file_path, competition, season, venue,
                              from_match, to_match, multi_paths, period, time_range):
    payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_PITCH, title="No data")
    if not payloads:
        return empty

    first_meta, _, events = _aggregate_scope_events(payloads)
    rm_id = first_meta["rm_id"]
    events = _apply_period_time_filter(events, period, time_range)

    chance_ev = events[
        (events["contestant_id"] == rm_id) &
        (events["is_key_pass"] | events["is_assist"]) &
        events["x"].notna() & events["y"].notna()
    ]

    fig = go.Figure()
    fig.update_layout(
        **_PL, height=_H_PITCH,
        title=f"Chance Creation Origins — {len(chance_ev)} key passes / assists",
        xaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68, fixedrange=True),
    )
    fig.update_layout(shapes=_pitch_shapes_full() + _pitch_stripes_full())

    if chance_ev.empty:
        fig.add_annotation(x=50, y=50, text="No key pass or assist data for this filter.",
                           showarrow=False, font=dict(size=14, color=_C["text_secondary"]))
        return fig

    key_passes = chance_ev[chance_ev["is_key_pass"] & ~chance_ev["is_assist"]]
    assists = chance_ev[chance_ev["is_assist"]]

    if not key_passes.empty:
        fig.add_trace(go.Scatter(
            x=key_passes["x"], y=key_passes["y"], mode="markers",
            marker=dict(size=10, color=_GOLD, symbol="diamond", line=dict(color="white", width=1)),
            name=f"Key Pass ({len(key_passes)})",
            customdata=np.stack([
                key_passes["player_name"].fillna("?"),
                key_passes["minute"].fillna(0).astype(int),
            ], axis=-1),
            hovertemplate="%{customdata[0]} · Key Pass<br>Min %{customdata[1]}'  x=%{x:.1f}, y=%{y:.1f}<extra></extra>",
        ))

    if not assists.empty:
        fig.add_trace(go.Scatter(
            x=assists["x"], y=assists["y"], mode="markers",
            marker=dict(size=13, color=_OPP, symbol="star", line=dict(color="white", width=1)),
            name=f"Assist ({len(assists)})",
            customdata=np.stack([
                assists["player_name"].fillna("?"),
                assists["minute"].fillna(0).astype(int),
            ], axis=-1),
            hovertemplate="%{customdata[0]} · Assist<br>Min %{customdata[1]}'  x=%{x:.1f}, y=%{y:.1f}<extra></extra>",
        ))

    if len(chance_ev) >= 4:
        fig.add_trace(go.Histogram2dContour(
            x=chance_ev["x"], y=chance_ev["y"],
            colorscale=[[0, "rgba(245,158,11,0)"], [1, "rgba(245,158,11,0.35)"]],
            showscale=False, ncontours=6,
            line=dict(width=0.8, color="rgba(245,158,11,0.5)"),
            hoverinfo="skip", name="Chance Zone",
        ))

    _add_pitch_context_labels(fig, full_pitch=True)
    return fig


@callback(
    Output("ma2-progressive-passes", "figure"),
    *_MA2_MATCH_INPUTS,
    *_MA2_ADV_INPUTS,
)
def _progressive_passes_chart(mode, file_path, competition, season, venue,
                               from_match, to_match, multi_paths, period, time_range):
    payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_PITCH, title="No data")
    if not payloads:
        return empty

    first_meta, _, events = _aggregate_scope_events(payloads)
    rm_id = first_meta["rm_id"]
    events = _apply_period_time_filter(events, period, time_range)

    rm_passes = events[
        (events["contestant_id"] == rm_id) & events["is_pass"] &
        events["x"].notna() & events["y"].notna() &
        events["end_x"].notna() & events["end_y"].notna()
    ].copy()

    attempted = rm_passes[(rm_passes["end_x"] - rm_passes["x"]) >= 10]
    progressive = attempted[attempted["outcome"] == 1]
    success_rate = len(progressive) / len(attempted) * 100 if len(attempted) > 0 else 0

    fig = go.Figure()
    fig.update_layout(
        **_PL, height=_H_PITCH,
        title=(f"Progressive Passes (RM) — {len(progressive)} completed / "
               f"{len(attempted)} attempted ({success_rate:.0f}% success)"),
        xaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68, fixedrange=True),
    )
    fig.update_layout(shapes=_pitch_shapes_full() + _pitch_stripes_full())

    if progressive.empty:
        fig.add_annotation(x=50, y=50, text="No progressive pass data for this filter.",
                           showarrow=False, font=dict(size=14, color=_C["text_secondary"]))
        return fig

    for _, row in progressive.head(120).iterrows():
        fig.add_annotation(
            x=float(row["end_x"]), y=float(row["end_y"]),
            ax=float(row["x"]), ay=float(row["y"]),
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowwidth=1.5,
            arrowcolor="rgba(37,99,235,0.40)",
        )

    fig.add_trace(go.Scatter(
        x=progressive["x"], y=progressive["y"], mode="markers",
        marker=dict(size=7, color=_RM, opacity=0.75, line=dict(color="white", width=0.6)),
        name="Origin",
        customdata=np.stack([
            progressive["player_name"].fillna("?"),
            progressive["minute"].fillna(0).astype(int),
            (progressive["end_x"] - progressive["x"]).round(1),
        ], axis=-1),
        hovertemplate="%{customdata[0]} · Min %{customdata[1]}'<br>Advance: +%{customdata[2]} units<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=progressive["end_x"], y=progressive["end_y"], mode="markers",
        marker=dict(size=6, color=_GOLD, opacity=0.6, symbol="triangle-right",
                    line=dict(color="white", width=0.5)),
        name="Destination", hoverinfo="skip",
    ))

    _add_pitch_context_labels(fig, full_pitch=True)
    return fig


@callback(
    Output("ma2-penalty-analysis", "children"),
    Input("ma-competition", "value"),
    Input("ma-season", "value"),
)
def _penalty_analysis(competition, season):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"
    all_seasons = get_competition_seasons(comp)

    season_data = []
    for s in all_seasons:
        ms = get_season_match_list(comp, s)
        pen_attempts, pen_goals = 0, 0
        for m in ms:
            try:
                ev = parse_events(load_match_json(m["filepath"]))
                rm_ev = ev[ev["contestant_id"] == m["rm_id"]]
                pens = rm_ev[rm_ev["is_penalty"] & rm_ev["is_shot"]]
                pen_attempts += len(pens)
                pen_goals += int(pens["is_goal"].sum())
            except Exception:
                continue
        season_data.append({"season": s, "attempts": pen_attempts, "goals": pen_goals})

    if not season_data:
        return dbc.Alert("No penalty data available.", color="info")

    df = pd.DataFrame(season_data)
    df["conversion"] = df.apply(
        lambda r: round(r["goals"] / r["attempts"] * 100, 1) if r["attempts"] > 0 else 0.0,
        axis=1,
    )

    curr = df[df["season"] == seas]
    if curr.empty:
        curr_att, curr_gls, curr_conv = 0, 0, 0.0
    else:
        r = curr.iloc[0]
        curr_att, curr_gls, curr_conv = int(r["attempts"]), int(r["goals"]), float(r["conversion"])

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["season"], y=df["attempts"], name="Attempts", marker_color="#64748b"))
    fig.add_trace(go.Bar(x=df["season"], y=df["goals"], name="Goals", marker_color=_RM))
    fig.add_trace(go.Scatter(
        x=df["season"], y=df["conversion"], name="Conv %",
        mode="lines+markers", yaxis="y2",
        line=dict(color=_GOLD, width=2), marker=dict(size=8),
    ))
    fig.update_layout(
        **_PL, height=_H_CHART, title=f"RM Penalty Record — {comp}",
        barmode="group",
        xaxis=dict(gridcolor=_C["border"], automargin=True),
        yaxis=dict(title="Count", gridcolor=_C["border"], automargin=True),
        yaxis2=dict(title="Conv %", overlaying="y", side="right",
                    showgrid=False, range=[0, 110], automargin=True),
    )

    _ACCENT_GREEN = _C.get("accent_green", "#16a34a")
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Penalties Taken", className="kpi-title"),
                html.Div(str(curr_att), className="kpi-value", style={"color": _RM}),
                html.P(f"{seas}", className="text-muted", style={"fontSize": "0.72rem", "marginBottom": 0}),
            ]), className="kpi-card h-100"), md=4),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Goals Scored", className="kpi-title"),
                html.Div(str(curr_gls), className="kpi-value", style={"color": _GOLD}),
                html.P(f"{seas}", className="text-muted", style={"fontSize": "0.72rem", "marginBottom": 0}),
            ]), className="kpi-card h-100"), md=4),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Conversion Rate", className="kpi-title"),
                html.Div(f"{curr_conv:.1f}%", className="kpi-value", style={"color": _ACCENT_GREEN}),
                html.P(f"{seas}", className="text-muted", style={"fontSize": "0.72rem", "marginBottom": 0}),
            ]), className="kpi-card h-100"), md=4),
        ], className="g-2 mb-3"),
        dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True}),
    ])


@callback(
    Output("ma2-chance-creator", "figure"),
    *_MA2_MATCH_INPUTS,
    *_MA2_ADV_INPUTS,
)
def _chance_creator_chart(mode, file_path, competition, season, venue,
                           from_match, to_match, multi_paths, period, time_range):
    payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_CHART, title="No data")
    if not payloads:
        return empty

    first_meta, _, events = _aggregate_scope_events(payloads)
    rm_id = first_meta["rm_id"]
    events = _apply_period_time_filter(events, period, time_range)

    rm_ev = events[events["contestant_id"] == rm_id]
    kp = rm_ev[rm_ev["is_key_pass"] | rm_ev["is_assist"]]

    if kp.empty:
        empty.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper",
                             text="No key pass / assist data for this filter.",
                             showarrow=False, font=dict(size=14, color=_C["text_secondary"]))
        return empty

    total_kp = len(kp)
    by_player = kp.groupby("player_name").agg(
        key_passes=("is_key_pass", "sum"),
        assists=("is_assist", "sum"),
    ).reset_index()
    by_player["total"] = by_player["key_passes"] + by_player["assists"]
    by_player["chance_pct"] = (by_player["total"] / total_kp * 100).round(1)
    by_player = by_player.sort_values("total", ascending=True).tail(12)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=by_player["key_passes"], y=by_player["player_name"],
        name="Key Passes", orientation="h",
        marker_color=_RM, text=by_player["key_passes"], textposition="inside",
    ))
    fig.add_trace(go.Bar(
        x=by_player["assists"], y=by_player["player_name"],
        name="Assists", orientation="h",
        marker_color=_OPP, text=by_player["assists"], textposition="inside",
    ))
    fig.update_layout(
        **_PL,
        height=max(300, 40 * len(by_player) + 100),
        title=f"Chance Creator % (of {total_kp} total key pass / assist events)",
        barmode="stack",
        xaxis=dict(title="Count", gridcolor=_C["border"], automargin=True),
        yaxis=dict(automargin=True),
    )
    return fig


@callback(
    Output("ma2-team-radar", "figure"),
    *_MA2_MATCH_INPUTS,
)
def _team_radar(mode, file_path, competition, season, venue, from_match, to_match, multi_paths=None):
    payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
    empty = go.Figure()
    empty.update_layout(height=_H_PITCH, paper_bgcolor=_C["surface"], title="No data")
    if not payloads:
        return empty

    first_meta, _, events = _aggregate_scope_events(payloads)
    rm_id = first_meta["rm_id"]
    opp_id = first_meta["opp_id"]
    rm_name = _rm_team_name(first_meta)
    opp_name = first_meta.get("opponent", "Opponent")

    rm_ev = events[events["contestant_id"] == rm_id]
    opp_ev = events[events["contestant_id"] == opp_id]

    def _sdiv(a, b):
        return float(a) / float(b) if b else 0.0

    rm_xg = float(rm_ev["xg"].sum())
    opp_xg = float(opp_ev["xg"].sum())
    rm_shots = int((rm_ev["is_shot"] | rm_ev["is_goal"]).sum())
    opp_shots = int((opp_ev["is_shot"] | opp_ev["is_goal"]).sum())

    rm_passes = rm_ev[rm_ev["is_pass"]]
    opp_passes = opp_ev[opp_ev["is_pass"]]
    rm_pass_acc = _sdiv(int((rm_passes["outcome"] == 1).sum()), len(rm_passes)) * 100
    opp_pass_acc = _sdiv(int((opp_passes["outcome"] == 1).sum()), len(opp_passes)) * 100

    rm_ppda_val = calc_ppda(events, first_meta)
    inv_meta = {**first_meta, "rm_id": opp_id, "opp_id": rm_id}
    opp_ppda_val = calc_ppda(events, inv_meta)
    # Normalise PPDA: 20/PPDA × 10 gives higher score = more pressing intensity
    rm_ppda_n = min(_sdiv(20.0, rm_ppda_val) * 10, 10) if rm_ppda_val and rm_ppda_val > 0 else 0
    opp_ppda_n = min(_sdiv(20.0, opp_ppda_val) * 10, 10) if opp_ppda_val and opp_ppda_val > 0 else 0

    rm_tilt = calc_field_tilt(events, first_meta) or 0
    opp_tilt = 100 - rm_tilt

    def _ft_entries(ev, team_id):
        te = ev[ev["contestant_id"] == team_id]
        p = te[te["is_pass"] & (te["x"] < 67) & (te["end_x"] >= 67) & te["end_x"].notna()]
        d = te[te["is_dribble"] & (te["x"] >= 55) & (te["x"] < 67)]
        return len(p) + len(d)

    rm_ft = _ft_entries(events, rm_id)
    opp_ft = _ft_entries(events, opp_id)

    def _norm(val, ref_max):
        return round(min(float(val) / float(ref_max) * 10.0, 10.0), 2) if ref_max else 0.0

    cats = ["xG", "Shots", "Pass Acc %", "Press Intensity", "Field Tilt %", "Final Third Entries"]
    rm_vals = [
        _norm(rm_xg, max(rm_xg + 0.01, opp_xg + 0.01)),
        _norm(rm_shots, max(rm_shots + 1, opp_shots + 1)),
        _norm(rm_pass_acc, 100),
        rm_ppda_n,
        _norm(rm_tilt, 100),
        _norm(rm_ft, max(rm_ft + 1, opp_ft + 1)),
    ]
    opp_vals = [
        _norm(opp_xg, max(rm_xg + 0.01, opp_xg + 0.01)),
        _norm(opp_shots, max(rm_shots + 1, opp_shots + 1)),
        _norm(opp_pass_acc, 100),
        opp_ppda_n,
        _norm(opp_tilt, 100),
        _norm(opp_ft, max(rm_ft + 1, opp_ft + 1)),
    ]

    cats_c = cats + [cats[0]]
    rm_c = rm_vals + [rm_vals[0]]
    opp_c = opp_vals + [opp_vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=rm_c, theta=cats_c, fill="toself",
        line=dict(color=_RM, width=2), fillcolor="rgba(37,99,235,0.15)",
        name=rm_name,
    ))
    fig.add_trace(go.Scatterpolar(
        r=opp_c, theta=cats_c, fill="toself",
        line=dict(color=_OPP, width=2), fillcolor="rgba(220,38,38,0.12)",
        name=opp_name,
    ))
    fig.update_layout(
        paper_bgcolor=_C["surface"],
        font=dict(color=_C["text_primary"], size=11),
        polar=dict(
            bgcolor=_C["surface"],
            radialaxis=dict(visible=True, range=[0, 10], gridcolor=_C["border"]),
            angularaxis=dict(gridcolor=_C["border"]),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5),
        title=f"Team Radar — {rm_name} vs {opp_name}",
        height=_H_PITCH,
        margin=dict(l=60, r=60, t=80, b=60),
    )
    return fig


@callback(
    Output("ma2-buildup-network", "figure"),
    *_MA2_MATCH_INPUTS,
    *_MA2_ADV_INPUTS,
)
def _buildup_network(mode, file_path, competition, season, venue,
                     from_match, to_match, multi_paths, period, time_range):
    payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_PITCH, title="No data")
    if not payloads:
        return empty

    first_meta, _, events = _aggregate_scope_events(payloads)
    rm_id = first_meta["rm_id"]
    rm_name = _rm_team_name(first_meta)
    events = _apply_period_time_filter(events, period, time_range)

    # Restrict to own-half events (x < 50 = before midfield)
    buildup_ev = events[(events["contestant_id"] == rm_id) & (events["x"] < 50)].copy()
    nodes, edges = _build_pass_network(buildup_ev, rm_id, min_edge_count=1, max_players=11)

    fig = go.Figure()
    fig.update_layout(
        **_PL, height=_H_PITCH,
        title=f"Build-Up Pass Network (RM Own Half) — {rm_name}",
        xaxis=dict(range=[-2, 55], showticklabels=False, showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68, fixedrange=True),
        showlegend=False,
    )
    fig.update_layout(shapes=_pitch_shapes_full() + _pitch_stripes_full())

    if nodes.empty or edges.empty:
        fig.add_annotation(x=25, y=50, text="Insufficient build-up pass data.",
                           showarrow=False, font=dict(size=14, color=_C["text_secondary"]))
        return fig

    max_cnt = max(float(edges["pass_count"].max()), 1)
    for _, e in edges.iterrows():
        sn = nodes[nodes["player"] == e["player_name"]]
        rn = nodes[nodes["player"] == e["receiver_name"]]
        if sn.empty or rn.empty:
            continue
        sx, sy = float(sn.iloc[0]["x"]), float(sn.iloc[0]["y"])
        rx, ry = float(rn.iloc[0]["x"]), float(rn.iloc[0]["y"])
        width = 1.5 + 4.5 * float(e["pass_count"]) / max_cnt
        fig.add_shape(type="line", x0=sx, y0=sy, x1=rx, y1=ry,
                      line=dict(color="rgba(37,99,235,0.45)", width=width), layer="below")

    max_inv = max(float(nodes["involvement"].max()), 1)
    for _, n in nodes.iterrows():
        size = 14 + 16 * float(n["involvement"]) / max_inv
        fig.add_trace(go.Scatter(
            x=[n["x"]], y=[n["y"]], mode="markers+text",
            marker=dict(size=size, color=_RM, line=dict(color="white", width=2)),
            text=[_short_name(n["player"])],
            textposition="top center",
            textfont=dict(size=9, color=_C["text_primary"]),
            hovertemplate=f"{n['player']}<br>Involvement: {int(n['involvement'])}<extra></extra>",
            showlegend=False,
        ))

    return fig


@callback(
    Output("ma2-final-third-entries", "figure"),
    *_MA2_MATCH_INPUTS,
    *_MA2_ADV_INPUTS,
)
def _final_third_entries(mode, file_path, competition, season, venue,
                          from_match, to_match, multi_paths, period, time_range):
    payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_PITCH, title="No data")
    if not payloads:
        return empty

    first_meta, _, events = _aggregate_scope_events(payloads)
    rm_id = first_meta["rm_id"]
    events = _apply_period_time_filter(events, period, time_range)

    rm_ev = events[events["contestant_id"] == rm_id]

    pass_entries = rm_ev[
        rm_ev["is_pass"] & (rm_ev["x"] < 67) &
        (rm_ev["end_x"] >= 67) & rm_ev["end_x"].notna()
    ].copy()
    pass_entries["entry_success"] = (pass_entries["outcome"] == 1).astype(int)

    dribble_entries = rm_ev[
        rm_ev["is_dribble"] & (rm_ev["x"] >= 55) & (rm_ev["x"] < 67)
    ].copy()
    dribble_entries["entry_success"] = (dribble_entries["outcome"] == 1).astype(int)

    fig = go.Figure()
    fig.update_layout(
        **_PL, height=_H_PITCH,
        title=(f"Final Third Entries (RM) — {len(pass_entries)} pass entries, "
               f"{len(dribble_entries)} dribble entries"),
        xaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68, fixedrange=True),
    )
    fig.update_layout(shapes=_pitch_shapes_full() + _pitch_stripes_full())

    fig.add_shape(type="line", x0=67, y0=0, x1=67, y1=100,
                  line=dict(color="rgba(245,158,11,0.8)", width=2, dash="dash"), layer="above")
    fig.add_annotation(x=67, y=103, xref="x", yref="y", text="Final Third boundary",
                       showarrow=False, font=dict(size=9, color=_GOLD))

    if not pass_entries.empty:
        succ_p = pass_entries[pass_entries["entry_success"] == 1]
        fail_p = pass_entries[pass_entries["entry_success"] == 0]
        if not succ_p.empty:
            fig.add_trace(go.Scatter(
                x=succ_p["x"], y=succ_p["y"], mode="markers",
                marker=dict(size=9, color=_RM, symbol="arrow-right", opacity=0.85,
                            line=dict(color="white", width=0.6)),
                name=f"Pass Entry — Success ({len(succ_p)})",
                customdata=np.stack([succ_p["player_name"].fillna("?"),
                                     succ_p["minute"].fillna(0).astype(int)], axis=-1),
                hovertemplate="%{customdata[0]} · Min %{customdata[1]}'<extra></extra>",
            ))
        if not fail_p.empty:
            fig.add_trace(go.Scatter(
                x=fail_p["x"], y=fail_p["y"], mode="markers",
                marker=dict(size=9, color="#94a3b8", symbol="x", opacity=0.7,
                            line=dict(color="white", width=0.6)),
                name=f"Pass Entry — Failed ({len(fail_p)})",
                hoverinfo="skip",
            ))

    if not dribble_entries.empty:
        succ_d = dribble_entries[dribble_entries["entry_success"] == 1]
        fail_d = dribble_entries[dribble_entries["entry_success"] == 0]
        if not succ_d.empty:
            fig.add_trace(go.Scatter(
                x=succ_d["x"], y=succ_d["y"], mode="markers",
                marker=dict(size=10, color=_GOLD, symbol="diamond", opacity=0.85,
                            line=dict(color="white", width=1)),
                name=f"Dribble — Success ({len(succ_d)})",
                hoverinfo="skip",
            ))
        if not fail_d.empty:
            fig.add_trace(go.Scatter(
                x=fail_d["x"], y=fail_d["y"], mode="markers",
                marker=dict(size=9, color="#f87171", symbol="x-open", opacity=0.7,
                            line=dict(color="#f87171", width=1.5)),
                name=f"Dribble — Failed ({len(fail_d)})",
                hoverinfo="skip",
            ))

    _add_pitch_context_labels(fig, full_pitch=True)
    return fig


@callback(
    Output("ma2-extended-transition", "figure"),
    *_MA2_MATCH_INPUTS,
    Input("ma2-transition-window", "value"),
)
def _extended_transition(mode, file_path, competition, season, venue,
                          from_match, to_match, multi_paths, window_secs):
    payloads = _load_scope(mode, file_path, competition, season, venue, from_match, to_match, multi_paths)
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_CHART, title="No data")
    if not payloads:
        return empty

    first_meta, _, events = _aggregate_scope_events(payloads)
    rm_id = first_meta["rm_id"]
    rm_name = _rm_team_name(first_meta)
    w = int(window_secs or 12)

    df = events.sort_values(["period", "minute", "second", "event_id"]).copy()
    df["t"] = df["minute"].fillna(0).astype(int) * 60 + df["second"].fillna(0).astype(int)

    regains = df[
        (df["contestant_id"] == rm_id) &
        (df["is_recovery"] | df["is_interception"] | df["is_tackle"])
    ]
    rm_shots_df = df[(df["contestant_id"] == rm_id) & (df["is_shot"] | df["is_goal"])]

    windows = [5, 10, 12, 15]
    rows = []
    for ww in windows:
        count = 0
        for _, reg in regains.iterrows():
            t0, t1, p = reg["t"], reg["t"] + ww, reg["period"]
            in_win = rm_shots_df[
                (rm_shots_df["period"] == p) &
                (rm_shots_df["t"] >= t0) &
                (rm_shots_df["t"] <= t1)
            ]
            if len(in_win) > 0:
                count += 1
        rate = float(count) / max(len(regains), 1) * 100
        rows.append({"window": ww, "rate": round(rate, 1), "count": count})

    rate_df = pd.DataFrame(rows)
    curr_rate = float(rate_df[rate_df["window"] == w]["rate"].values[0]) if w in rate_df["window"].values else 0.0

    colors = [_RM if ww == w else "#94a3b8" for ww in rate_df["window"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"{ww}s" for ww in rate_df["window"]],
        y=rate_df["rate"],
        marker_color=colors,
        text=[f"{r:.1f}%" for r in rate_df["rate"]],
        textposition="outside",
        name="Regain → Shot %",
    ))
    fig.update_layout(
        **_PL, height=_H_CHART,
        title=(f"Transition Effectiveness — {rm_name}  "
               f"({len(regains)} regains · {w}s window → {curr_rate:.1f}% led to shot)"),
        xaxis=dict(title="Window Duration", gridcolor=_C["border"], automargin=True),
        yaxis=dict(
            title="% Regains → Shot",
            gridcolor=_C["border"], automargin=True,
            range=[0, max(float(rate_df["rate"].max()) * 1.35, 10)],
        ),
        showlegend=False,
    )
    return fig
