"""
Tactical Phases Page — Real Madrid Tactical Dashboard
PPDA, pressing intensity, and possession phase analysis from Opta event data.
"""

from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from config import COLOR_SCHEME
from utils.data_helpers import (
    get_competition_options, get_season_options, get_match_options,
)
from utils.data_loader import (
    load_match_json, extract_match_meta, parse_events,
    calc_match_kpis, calc_ppda, calc_field_tilt,
    get_season_match_list,
)

_C  = COLOR_SCHEME
_RM = _C["accent_blue"]
_PL = dict(
    paper_bgcolor=_C["surface"],
    plot_bgcolor=_C["surface"],
    font=dict(color=_C["text_primary"], size=11),
    margin=dict(l=48, r=28, t=56, b=56),
    hovermode="closest",
    uniformtext_minsize=9,
    uniformtext_mode="hide",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
)
_H_CHART = 400
_H_PITCH = 520
_PITCH_LABEL_FONT = dict(size=10, color="rgba(15,23,42,0.62)")
_PITCH_FILL = "#e8f5e9"
_PITCH_LINE = "#388e3c"


def _pitch_shapes_full():
    lw, s = 1.5, []

    def _rect(x0, x1, y0, y1, fc="rgba(0,0,0,0)"):
        s.append(dict(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(color=_PITCH_LINE, width=lw), fillcolor=fc, layer="below"))

    _rect(0, 100, 0, 100, _PITCH_FILL)
    s.append(dict(type="line", x0=50, x1=50, y0=0, y1=100,
                  line=dict(color=_PITCH_LINE, width=lw), layer="below"))
    _rect(0, 16.5, 21.1, 78.9)
    _rect(83.5, 100, 21.1, 78.9)
    _rect(0, 5.5, 36.8, 63.2)
    _rect(94.5, 100, 36.8, 63.2)
    _rect(-2, 0, 45.2, 54.8, "white")
    _rect(100, 102, 45.2, 54.8, "white")
    s.append(dict(type="circle", x0=41.55, x1=58.45, y0=40.65, y1=59.35,
                  line=dict(color=_PITCH_LINE, width=lw), fillcolor="rgba(0,0,0,0)", layer="below"))
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


def _add_pitch_context_labels(fig: go.Figure):
    # Use DATA coordinates (xref/yref = x/y) so the labels sit INSIDE the
    # pitch rectangle even though the axis is letterboxed by scaleratio.
    labels = [
        (16, 5, "Defensive Third"),
        (50, 5, "Middle Third"),
        (84, 5, "Attacking Third"),
    ]
    for x, y, text in labels:
        fig.add_annotation(
            x=x, y=y, xref="x", yref="y", text=text,
            showarrow=False, xanchor="center", yanchor="middle",
            font=_PITCH_LABEL_FONT,
            bgcolor="rgba(255,255,255,0.72)", borderpad=2,
        )
    return fig


def _add_direction_arrows(fig: go.Figure, left_team: str, right_team: str):
    fig.add_annotation(
        x=0.03,
        y=0.99,
        xref="paper",
        yref="paper",
        text=f"{left_team} attacks ←",
        showarrow=False,
        xanchor="left",
        font=dict(size=10, color=_C["accent_red"]),
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


def layout(competition="LaLiga", season="2025-2026"):
    comp_opts   = get_competition_options()
    season_opts = get_season_options(competition)
    match_opts  = get_match_options(competition, season)
    default_val = match_opts[0]["value"] if match_opts else None

    return html.Div([
        html.Div([
            html.H4("Tactical Phases", className="rm-page-title"),
            html.P("Pressing, possession and spatial metrics from Opta event data",
                   className="rm-page-subtitle"),
        ], className="rm-page-header"),

        # Filters
        dbc.Card(dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Competition", className="filter-label"),
                    dcc.Dropdown(id="tp-competition", options=comp_opts,
                                 value=competition, clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("Season", className="filter-label"),
                    dcc.Dropdown(id="tp-season", options=season_opts,
                                 value=season, clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("Match", className="filter-label"),
                    dcc.Dropdown(id="tp-match", options=match_opts,
                                 value=default_val, clearable=False),
                ], md=8),
            ], className="g-2"),
        ), className="filter-section mb-4"),

        # KPI banner
        dcc.Loading(dbc.Row(id="tp-kpi-row", className="g-2 mb-4"),
                    type="circle", color=_RM),

        # Season PPDA trend + single-match pressing map
        dbc.Card([
            dbc.CardHeader("PPDA Trend (Season)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="tp-ppda-trend",
                          config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Pressing Actions Map (this match)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="tp-press-map",
                          config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # Field tilt + recoveries heatmap
        dbc.Card([
            dbc.CardHeader("Field Tilt (Final Third %)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="tp-tilt-chart",
                          config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Ball Recoveries by Zone"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="tp-recovery-map",
                          config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_RM)),
        ], className="mb-3"),

        # ── Position Maps ──────────────────────────────────────────────────────
        dbc.Card([
            dbc.CardHeader([
                html.Span("Position Maps", className="fw-bold me-2"),
                html.Span("Average player locations by game phase · derived from event data",
                          className="text-muted", style={"fontSize": "0.80rem"}),
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Team", className="filter-label d-block"),
                        dbc.RadioItems(
                            id="tp-posmap-team",
                            options=[
                                {"label": "Real Madrid", "value": "rm"},
                                {"label": "Opponent",    "value": "opp"},
                            ],
                            value="rm",
                            inline=True,
                            className="btn-group",
                            inputClassName="btn-check",
                            labelClassName="btn btn-outline-primary btn-sm",
                            labelCheckedClassName="active",
                        ),
                    ], md=4),
                    dbc.Col([
                        html.Label("Game Phase", className="filter-label d-block"),
                        dbc.RadioItems(
                            id="tp-posmap-phase",
                            options=[
                                {"label": "All Phases",        "value": "all"},
                                {"label": "In Possession",     "value": "possession"},
                                {"label": "Out of Possession", "value": "defense"},
                            ],
                            value="all",
                            inline=True,
                            className="btn-group",
                            inputClassName="btn-check",
                            labelClassName="btn btn-outline-secondary btn-sm",
                            labelCheckedClassName="active",
                        ),
                    ], md=8),
                ], className="mb-3 g-3"),
                dcc.Loading(
                    dcc.Graph(id="tp-posmap",
                              config={"displayModeBar": False, "responsive": True}),
                    type="circle", color=_RM,
                ),
                html.Div([
                    html.Div("Position Code Reference",
                             className="text-muted text-center mt-2 mb-1",
                             style={"fontSize": "0.74rem", "fontWeight": 600}),
                    _code_legend_table(),
                    html.Div("Standard pitch zones (forwards top → defenders bottom) for "
                             "reading the zonal activity grid above.",
                             className="text-muted text-center mt-1",
                             style={"fontSize": "0.68rem"}),
                ], className="d-flex flex-column align-items-center mt-2"),
            ]),
        ], className="mb-3"),

        # ── Player Positional Summary table (below the pitch) ──────────────────
        dbc.Card([
            dbc.CardHeader([
                html.Span("Player Positional Summary", className="fw-bold me-2"),
                html.Span("Average pitch position, line & involvement per player · "
                          "updates with the team and phase selected above",
                          className="text-muted", style={"fontSize": "0.80rem"}),
            ]),
            dbc.CardBody(
                dcc.Loading(html.Div(id="tp-posmap-table"), type="circle", color=_RM),
            ),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Tactical Phase Deep-Dive"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Select Phase", className="filter-label"),
                        dcc.Dropdown(
                            id="tp-phase-view",
                            options=[
                                {"label": "A. Offensive Moment", "value": "A"},
                                {"label": "B. Defensive Transition", "value": "B"},
                                {"label": "C. Defensive Moment", "value": "C"},
                                {"label": "D. Offensive Transition", "value": "D"},
                            ],
                            value="A",
                            clearable=False,
                        ),
                    ], md=5),
                ], className="mb-3"),
                dcc.Loading(html.Div(id="tp-phase-panel"), type="circle", color=_RM),
            ]),
        ], className="mb-3"),

    ], className="page-content")


# ── Callbacks ──────────────────────────────────────────────────────────────

@callback(
    Output("tp-season", "options"), Output("tp-season", "value"),
    Input("tp-competition", "value"),
    State("tp-season", "value"),
)
def _season_opts(comp, current):
    opts = get_season_options(comp or "LaLiga")
    vals = [o["value"] for o in opts]
    return opts, (current if current in vals else (opts[0]["value"] if opts else "2025-2026"))


@callback(
    Output("tp-match", "options"), Output("tp-match", "value"),
    Input("tp-competition", "value"), Input("tp-season", "value"),
)
def _match_opts(comp, seas):
    opts = get_match_options(comp or "LaLiga", seas or "2025-2026")
    return opts, (opts[0]["value"] if opts else None)


def _load(fp):
    if not fp:
        return None, None, None
    data   = load_match_json(fp)
    if not data:
        return None, None, None
    meta   = extract_match_meta(data)
    events = parse_events(data)
    return data, meta, events


def _safe_div(a, b):
    return float(a) / float(b) if b else 0.0


def _compact_match_label(week, opponent):
    token = str(opponent or "OPP").replace("_", " ").split()[0]
    short = token[:3].upper() if token else "OPP"
    return f"MD{week if week is not None else '?'} {short}"


def _build_transition_windows(events: pd.DataFrame, team_id: str, opp_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if events.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = events.sort_values(["period", "minute", "second", "event_id"]).copy()
    df["t"] = (df["minute"].fillna(0).astype(int) * 60) + df["second"].fillna(0).astype(int)

    rm_ev = df[df["contestant_id"] == team_id]
    opp_ev = df[df["contestant_id"] == opp_id]

    regains = rm_ev[rm_ev["is_recovery"] | rm_ev["is_interception"] | rm_ev["is_tackle"]]
    losses = rm_ev[(rm_ev["is_pass"] & (rm_ev["outcome"] == 0)) | (rm_ev["is_dribble"] & (rm_ev["outcome"] == 0))]

    trans_rows = []
    for _, r in regains.iterrows():
        t0 = r["t"]
        team_win = rm_ev[(rm_ev["t"] >= t0) & (rm_ev["t"] <= t0 + 15)]
        shots = team_win[team_win["is_shot"]]
        first_shot_t = shots["t"].min() if not shots.empty else np.nan
        shot_delay = (first_shot_t - t0) if pd.notna(first_shot_t) else np.nan
        x_end = team_win["x"].iloc[-1] if not team_win.empty else r.get("x", 0)
        y_end = team_win["y"].iloc[-1] if not team_win.empty else r.get("y", 0)
        if not shots.empty:
            x_end = shots.iloc[0]["x"]
            y_end = shots.iloc[0]["y"]

        trans_rows.append({
            "t0": t0,
            "origin_x": r.get("x", 0.0),
            "origin_y": r.get("y", 0.0),
            "dest_x": x_end,
            "dest_y": y_end,
            "vertical_gain": float((x_end or 0) - (r.get("x", 0) or 0)),
            "shot_in_15s": int(not shots.empty),
            "time_to_first_shot": shot_delay,
            "xg_in_window": float(shots["xg"].dropna().sum()) if not shots.empty else 0.0,
            "xg_obs_count": int(shots["xg"].notna().sum()) if not shots.empty else 0,
        })

    dt_rows = []
    for _, l in losses.iterrows():
        t0 = l["t"]
        rm_after = rm_ev[(rm_ev["t"] >= t0) & (rm_ev["t"] <= t0 + 10)]
        opp_after = opp_ev[(opp_ev["t"] >= t0) & (opp_ev["t"] <= t0 + 10)]
        first_def = rm_after[rm_after["is_tackle"] | rm_after["is_interception"] | rm_after["is_recovery"]]
        def_delay = (first_def["t"].min() - t0) if not first_def.empty else np.nan
        cp_recovery = int(not rm_after[rm_after["is_recovery"]].empty)

        ppda_post = _safe_div(
            len(opp_after[opp_after["is_pass"]]),
            len(first_def),
        )

        dt_rows.append({
            "t0": t0,
            "reaction_time_s": def_delay,
            "counterpress_recovery": cp_recovery,
            "ppda_after_turnover": ppda_post,
        })

    return pd.DataFrame(trans_rows), pd.DataFrame(dt_rows)


def _add_phase_density(fig: go.Figure, x: pd.Series, y: pd.Series, colorscale: str, trace_name: str):
    """Add a pitch-synced density layer using fixed football-pitch bins."""
    if x is None or y is None or len(x) == 0:
        return fig

    fig.add_trace(go.Histogram2d(
        x=x,
        y=y,
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(title="Density", thickness=10),
        opacity=0.82,
        xbins=dict(start=0, end=100, size=5),
        ybins=dict(start=0, end=100, size=5),
        hovertemplate="x %{x:.1f}, y %{y:.1f}<br>Count %{z}<extra></extra>",
        name=trace_name,
    ))
    return fig


def _metric_table(rows: list[tuple[str, str]]) -> dbc.Table:
    return dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Metric"), html.Th("Value")])),
            html.Tbody([html.Tr([html.Td(k), html.Td(v)]) for k, v in rows]),
        ],
        striped=True,
        hover=True,
        responsive=True,
        size="sm",
        className="mb-0",
    )


def _phase_base_pitch(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        **{**_PL, "plot_bgcolor": _PITCH_FILL, "margin": dict(l=24, r=24, t=48, b=24)},
        height=_H_PITCH,
        title=title,
        shapes=_pitch_stripes_full() + _pitch_shapes_full(),
        xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68, fixedrange=True),
    )
    return fig


@callback(
    Output("tp-kpi-row", "children"),
    Input("tp-match", "value"),
)
def _kpi_row(fp):
    _, meta, events = _load(fp)
    if meta is None:
        return []

    ppda   = calc_ppda(events, meta)
    tilt   = calc_field_tilt(events, meta)
    kpis   = calc_match_kpis(events, meta)

    rm_ev  = events[events["contestant_id"] == meta["rm_id"]]
    press_pct = round(
        len(rm_ev[(rm_ev["is_tackle"] | rm_ev["is_interception"] | rm_ev["is_recovery"])]) /
        max(len(rm_ev), 1) * 100, 1
    )

    def _card(title, val, color, sub=None):
        body = [html.P(title, className="kpi-title"),
                html.Div(str(val), className="kpi-value", style={"color": color})]
        if sub:
            body.append(html.P(sub, className="text-muted",
                               style={"fontSize": "0.72rem", "marginBottom": 0}))
        return dbc.Col(dbc.Card(dbc.CardBody(body), className="kpi-card h-100"),
                       lg=3, md=6, xs=12, className="mb-2")

    ppda_color = (_C["accent_green"] if ppda < 4 else
                  _C["accent_yellow"] if ppda < 8 else _C["accent_red"])
    return [
        _card("PPDA", ppda, ppda_color, "< 4 = high press"),
        _card("Field Tilt %", f"{tilt}%",  _RM, "Final-third dominance"),
        _card("Defensive Actions", len(rm_ev[(rm_ev["is_tackle"] | rm_ev["is_interception"] | rm_ev["is_recovery"])]),
              _C["accent_purple"]),
        _card("Press %", f"{press_pct}%", _C["accent_orange"],
              "Defensive actions / total"),
    ]


@callback(
    Output("tp-ppda-trend", "figure"),
    Input("tp-competition", "value"),
    Input("tp-season", "value"),
)
def _ppda_trend(competition, season):
    comp  = competition or "LaLiga"
    seas  = season or "2025-2026"
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_CHART, title="PPDA Trend")

    matches = get_season_match_list(comp, seas)
    if not matches:
        return empty

    labels, ppdas, results = [], [], []
    for m in matches:
        try:
            data   = load_match_json(m["filepath"])
            events = parse_events(data)
            ppda   = calc_ppda(events, m)
            labels.append(_compact_match_label(m.get("week", "?"), m.get("opponent", "OPP")))
            ppdas.append(ppda)
            results.append(m["result"])
        except Exception:
            continue

    if not labels:
        return empty

    colors = [
        _C["accent_green"]  if r == "W" else
        _C["accent_yellow"] if r == "D" else
        _C["accent_red"]
        for r in results
    ]
    avg_ppda = sum(ppdas) / len(ppdas)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=ppdas, marker_color=colors,
        name="PPDA", text=[f"{p:.1f}" for p in ppdas], textposition="auto",
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
    fig.add_hline(y=avg_ppda, line=dict(color=_RM, dash="dot", width=2),
                  annotation_text=f"Avg: {avg_ppda:.1f}",
                  annotation_font_size=10)
    fig.update_layout(**_PL, height=_H_CHART, title="PPDA per Match (lower = more press)",
                      xaxis=dict(tickangle=-45, ticklabelstep=2, gridcolor=_C["border"], automargin=True),
                      yaxis=dict(gridcolor=_C["border"], automargin=True),
                      showlegend=True)
    return fig


@callback(
    Output("tp-press-map", "figure"),
    Input("tp-match", "value"),
)
def _press_map(fp):
    _, meta, events = _load(fp)

    def _base():
        f = go.Figure()
        f.update_layout(**{**_PL, "plot_bgcolor": _PITCH_FILL}, height=_H_PITCH,
                        shapes=_pitch_stripes_full() + _pitch_shapes_full(),
                        xaxis=dict(range=[0, 100], showticklabels=False,
                                   showgrid=False, zeroline=False),
                        yaxis=dict(range=[0, 100], showticklabels=False,
                                   showgrid=False, zeroline=False,
                                   scaleanchor="x", scaleratio=0.68),
                        title="Pressing Actions")
        return _add_pitch_context_labels(f)

    if meta is None:
        return _base()

    rm_ev  = events[events["contestant_id"] == meta["rm_id"]]
    press  = rm_ev[rm_ev["type_id"].isin({7, 8, 49})]   # tackle, interception, recovery

    fig = _base()
    if not press.empty:
        # Pressing-density layer (where RM wins the ball back).
        # Pin the bins to the full pitch (0-100 in both axes) so the density grid
        # aligns exactly with the pitch markings and the scatter points — otherwise
        # Histogram2d auto-bins to the data extent and the layer drifts off-pitch.
        fig.add_trace(go.Histogram2d(
            x=press["x"], y=press["y"],
            xbins=dict(start=0, end=100, size=100 / 14),
            ybins=dict(start=0, end=100, size=100 / 9),
            autobinx=False, autobiny=False,
            colorscale="YlOrRd", opacity=0.45, zsmooth="best", showscale=True,
            colorbar=dict(title=dict(text="Press<br>density", side="right"),
                          len=0.55, thickness=12, x=1.005, tickfont=dict(size=10)),
            hoverinfo="skip",
        ))
        type_colors = {7: _RM, 8: _C["accent_green"], 49: _C["accent_orange"]}
        type_names  = {7: "Tackle", 8: "Interception", 49: "Recovery"}
        for tid, grp in press.groupby("type_id"):
            fig.add_trace(go.Scatter(
                x=grp["x"], y=grp["y"], mode="markers",
                name=f"{type_names.get(tid, tid)} ({len(grp)})",
                marker=dict(color=type_colors.get(tid, "#888"), size=12,
                            opacity=0.9, line=dict(color="white", width=1.4)),
                hovertemplate=f"{type_names.get(tid,'?')}<br>Min %{{customdata}}'<extra></extra>",
                customdata=grp["minute"],
            ))
    rm_name = _rm_team_name(meta)
    fig = _add_direction_arrows(fig, meta["opponent"], rm_name)
    fig.update_layout(
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5,
                    bgcolor="rgba(255,255,255,0.65)", font=dict(size=11)),
        title=f"Pressing Actions — {len(press)} ball-winning events (PPDA {calc_ppda(events, meta):.2f})",
    )
    return fig


@callback(
    Output("tp-tilt-chart", "figure"),
    Input("tp-competition", "value"),
    Input("tp-season", "value"),
)
def _tilt_chart(competition, season):
    comp  = competition or "LaLiga"
    seas  = season or "2025-2026"
    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_CHART, title="Field Tilt %")

    matches = get_season_match_list(comp, seas)
    if not matches:
        return empty

    labels, tilts, results = [], [], []
    for m in matches:
        try:
            data   = load_match_json(m["filepath"])
            events = parse_events(data)
            t      = calc_field_tilt(events, m)
            labels.append(_compact_match_label(m.get("week", "?"), m.get("opponent", "OPP")))
            tilts.append(t)
            results.append(m["result"])
        except Exception:
            continue

    if not labels:
        return empty

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=tilts, mode="lines+markers",
        line=dict(color=_RM, width=2),
        marker=dict(size=6, color=[
            _C["accent_green"] if r == "W" else
            _C["accent_yellow"] if r == "D" else _C["accent_red"]
            for r in results
        ]),
        name="Field Tilt %",
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
    fig.add_hline(y=50, line=dict(color="grey", dash="dot"),
                  annotation_text="50% (equal)", annotation_font_size=10)

    fig.update_layout(**_PL, height=_H_CHART,
                      title="Field Tilt % — Final Third Dominance",
                      xaxis=dict(tickangle=-45, ticklabelstep=2, gridcolor=_C["border"], automargin=True),
                      yaxis=dict(gridcolor=_C["border"], range=[20, 90], automargin=True),
                      showlegend=True)
    return fig


@callback(
    Output("tp-recovery-map", "figure"),
    Input("tp-match", "value"),
)
def _recovery_map(fp):
    _, meta, events = _load(fp)

    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_CHART, title="Ball Recoveries by Zone")

    if meta is None:
        return empty

    rm_ev = events[events["contestant_id"] == meta["rm_id"]]
    recoveries = rm_ev[rm_ev["is_recovery"]]

    if recoveries.empty:
        empty.add_annotation(text="No ball recoveries in this match", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False)
        return empty

    def _zone(x):
        if x < 33:
            return "Defensive Third"
        elif x < 67:
            return "Middle Third"
        else:
            return "Attacking Third"

    zone_counts = recoveries["x"].map(_zone).value_counts()
    zone_order  = ["Defensive Third", "Middle Third", "Attacking Third"]
    zone_colors = [_C["accent_red"], _C["accent_orange"], _C["accent_green"]]

    labels = [z for z in zone_order if int(zone_counts.get(z, 0)) > 0]
    values = [int(zone_counts.get(z, 0)) for z in labels]
    colors = [zone_colors[zone_order.index(z)] for z in labels]

    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Recoveries by Zone", "Zone Distribution"),
        specs=[[{"type": "bar"}, {"type": "pie"}]],
    )

    fig.add_trace(go.Bar(
        x=labels, y=values, marker_color=colors,
        text=values, textposition="auto", showlegend=False,
    ), row=1, col=1)

    fig.add_trace(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors),
        textinfo="label+percent", hole=0.4,
        showlegend=True,
        name="Recovery Zones",
    ), row=1, col=2)

    total = sum(values)
    fig.update_layout(
        paper_bgcolor=_C["surface"],
        plot_bgcolor=_C["surface"],
        font=dict(color=_C["text_primary"], size=11),
        height=_H_CHART,
        title=f"Ball Recoveries by Pitch Zone — {total} total",
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
        margin=dict(l=48, r=48, t=80, b=48),
    )
    return fig


@callback(
    Output("tp-phase-panel", "children"),
    Input("tp-match", "value"),
    Input("tp-phase-view", "value"),
)
def _phase_panel(fp, selected_phase):
    _, meta, events = _load(fp)
    if meta is None or events is None or events.empty:
        return dbc.Alert("Select a match to view phase details.", color="info")

    rm_id = meta["rm_id"]
    opp_id = meta["opp_id"]
    rm = events[events["contestant_id"] == rm_id].copy()
    opp = events[events["contestant_id"] == opp_id].copy()

    rm_pass = rm[rm["is_pass"] & rm["end_x"].notna()]
    opp_shots = opp[opp["is_shot"]]

    trans_df, dt_df = _build_transition_windows(events, rm_id, opp_id)

    # A. Offensive Moment
    build_up = _safe_div(len(rm_pass[(rm_pass["x"] < 40) & (rm_pass["outcome"] == 1)]), max(len(rm_pass), 1))
    progressive = _safe_div(len(rm_pass[(rm_pass["end_x"] - rm_pass["x"]) >= 15]), max(len(rm_pass), 1))
    flank_use = _safe_div(len(rm[(rm["y"] <= 20) | (rm["y"] >= 80)]), max(len(rm), 1))
    direct = _safe_div(len(rm_pass[(rm_pass["end_x"] - rm_pass["x"]) >= 25]), max(len(rm_pass), 1))
    combinative = 1.0 - direct
    chance_creation = int(rm["is_key_pass"].sum())
    xg_chain = float(rm["xg"].dropna().sum())
    xg_chain_obs = int(rm["xg"].notna().sum())
    zone14 = int(len(rm[(rm["x"] >= 75) & (rm["x"] <= 88) & (rm["y"] >= 35) & (rm["y"] <= 65)]))
    crosses = int(len(rm_pass[(rm_pass["x"] >= 75) & ((rm_pass["y"] <= 20) | (rm_pass["y"] >= 80))]))

    a_table = _metric_table([
        ("build-up structure", f"{build_up * 100:.1f}% controlled build-up passes"),
        ("progression style", f"{progressive * 100:.1f}% progressive passes"),
        ("flank usage", f"{flank_use * 100:.1f}% wide-lane actions"),
        ("direct vs combinative play", f"Direct {direct * 100:.1f}% / Combinative {combinative * 100:.1f}%"),
        ("chance creation", str(chance_creation)),
        ("xG chain", f"{xg_chain:.2f} (from {xg_chain_obs} shots with xG qualifier)"),
        ("zone 14 occupation", str(zone14)),
        ("crossing tendencies", str(crosses)),
    ])

    # B. Defensive Transition
    reaction = float(dt_df["reaction_time_s"].dropna().median()) if not dt_df.empty else 0.0
    cp_rec = float(dt_df["counterpress_recovery"].mean() * 100) if not dt_df.empty else 0.0
    compact = float(rm[rm["is_tackle"] | rm["is_interception"] | rm["is_recovery"]]["y"].std()) if not rm.empty else 0.0
    ppda_turn = float(dt_df["ppda_after_turnover"].replace([np.inf, -np.inf], np.nan).dropna().mean()) if not dt_df.empty else 0.0

    b_table = _metric_table([
        ("reaction after losing possession", f"{reaction:.2f}s median defensive reaction"),
        ("counterpressing recoveries", f"{cp_rec:.1f}% of loss windows"),
        ("defensive compactness", f"{compact:.2f} y-std (lower is tighter)"),
        ("recovery times", f"{reaction:.2f}s"),
        ("PPDA after turnover", f"{ppda_turn:.2f}"),
    ])

    # C. Defensive Moment
    ppda_val = calc_ppda(events, meta)
    def_actions = rm[rm["is_tackle"] | rm["is_interception"] | rm["is_recovery"]]
    high = int(len(def_actions[def_actions["x"] >= 67]))
    mid = int(len(def_actions[(def_actions["x"] >= 33) & (def_actions["x"] < 67)]))
    low = int(len(def_actions[def_actions["x"] < 33]))
    def_line = float(def_actions["x"].mean()) if not def_actions.empty else 0.0
    recovs = int(rm["is_recovery"].sum())
    aerial = int((rm["type_id"] == 37).sum())
    conceded = int(len(opp_shots))
    if opp_shots.empty:
        vuln = "No shot concessions"
    else:
        opp_zone = pd.cut(opp_shots["x"], bins=[-1, 33, 67, 101], labels=["Defensive", "Middle", "Attacking"])
        vuln = str(opp_zone.value_counts().idxmax()) + " zone"

    c_table = _metric_table([
        ("pressing intensity", f"PPDA {ppda_val:.2f}"),
        ("defensive structure", f"High/Mid/Low actions: {high}/{mid}/{low}"),
        ("compactness", f"{compact:.2f} y-std"),
        ("defensive line", f"avg line at x={def_line:.1f}"),
        ("recoveries", str(recovs)),
        ("aerial duels", str(aerial)),
        ("shots conceded", str(conceded)),
        ("vulnerable zones", vuln),
    ])

    # D. Offensive Transition
    fb_eff = float(trans_df["shot_in_15s"].mean() * 100) if not trans_df.empty else 0.0
    txth = float(trans_df["xg_in_window"].sum()) if not trans_df.empty else 0.0
    txth_obs = int(trans_df["xg_obs_count"].sum()) if not trans_df.empty else 0
    t2s = float(trans_df["time_to_first_shot"].dropna().median()) if not trans_df.empty else 0.0
    vert = float(trans_df["vertical_gain"].mean()) if not trans_df.empty else 0.0

    d_table = _metric_table([
        ("fast break efficiency", f"{fb_eff:.1f}% transitions with shot <=15s"),
        ("transition xG", f"{txth:.2f} (from {txth_obs} shots with xG qualifier)"),
        ("time-to-first-shot", f"{t2s:.2f}s median"),
        ("verticality", f"{vert:.2f} average x-gain"),
    ])

    trans_map = _phase_base_pitch("Transition origin/destination map")
    if not trans_df.empty:
        xs, ys = [], []
        for _, r in trans_df.iterrows():
            xs += [r["origin_x"], r["dest_x"], None]
            ys += [r["origin_y"], r["dest_y"], None]
        trans_map.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name="Transition path",
            line=dict(color=_RM, width=1.2), opacity=0.45, hoverinfo="skip",
        ))
        trans_map.add_trace(go.Scatter(
            x=trans_df["origin_x"], y=trans_df["origin_y"], mode="markers",
            name="Origin", marker=dict(color=_C["accent_orange"], size=6,
                                         line=dict(color="white", width=1)),
        ))
        trans_map.add_trace(go.Scatter(
            x=trans_df["dest_x"], y=trans_df["dest_y"], mode="markers",
            name="Destination", marker=dict(color=_C["accent_green"], size=6,
                                              line=dict(color="white", width=1)),
        ))
        trans_map.update_layout(legend=dict(bgcolor="rgba(0,0,0,0)"))

    # Phase A visuals
    a_heat = _phase_base_pitch("A Heatmap — RM progressive pass destinations")
    a_prog = rm_pass[(rm_pass["outcome"] == 1) & ((rm_pass["end_x"] - rm_pass["x"]) >= 10)]
    if not a_prog.empty:
        a_heat = _add_phase_density(a_heat, a_prog["end_x"], a_prog["end_y"], "YlGnBu", "Progressive destinations")
        a_heat.add_trace(go.Scatter(
            x=a_prog["end_x"], y=a_prog["end_y"], mode="markers",
            marker=dict(size=4, color="rgba(255,255,255,0.45)", line=dict(color="rgba(0,0,0,0.18)", width=0.5)),
            name="Pass end", hoverinfo="skip",
        ))
    rm_name = _rm_team_name(meta)
    a_heat = _add_direction_arrows(a_heat, meta["opponent"], rm_name)

    a_zone = go.Figure()
    a_zone_counts = {
        "Left Lane": int(len(rm[(rm["y"] >= 67)])),
        "Half-space/Central": int(len(rm[(rm["y"] >= 33) & (rm["y"] < 67)])),
        "Right Lane": int(len(rm[(rm["y"] < 33)])),
    }
    a_zone.add_trace(go.Bar(
        x=["Left Lane"], y=[a_zone_counts["Left Lane"]],
        name="Left Lane", marker_color=_C["accent_blue"],
        text=[a_zone_counts["Left Lane"]], textposition="auto",
    ))
    a_zone.add_trace(go.Bar(
        x=["Half-space/Central"], y=[a_zone_counts["Half-space/Central"]],
        name="Half-space/Central", marker_color=_C["accent_green"],
        text=[a_zone_counts["Half-space/Central"]], textposition="auto",
    ))
    a_zone.add_trace(go.Bar(
        x=["Right Lane"], y=[a_zone_counts["Right Lane"]],
        name="Right Lane", marker_color=_C["accent_orange"],
        text=[a_zone_counts["Right Lane"]], textposition="auto",
    ))
    a_zone.update_layout(**_PL, height=_H_CHART, title="A Visualization — RM lane usage", xaxis=dict(gridcolor=_C["border"], automargin=True), yaxis=dict(gridcolor=_C["border"], automargin=True))

    # Phase B visuals
    b_heat = _phase_base_pitch("B Heatmap — RM turnovers (loss points)")
    loss_pts = rm[(rm["is_pass"] & (rm["outcome"] == 0)) | (rm["is_dribble"] & (rm["outcome"] == 0))]
    if not loss_pts.empty:
        b_heat = _add_phase_density(b_heat, loss_pts["x"], loss_pts["y"], "Reds", "Turnover density")
        b_heat.add_trace(go.Scatter(
            x=loss_pts["x"], y=loss_pts["y"], mode="markers",
            marker=dict(size=4, color="rgba(255,255,255,0.45)", line=dict(color="rgba(0,0,0,0.18)", width=0.5)),
            name="Loss", hoverinfo="skip",
        ))
    b_heat = _add_direction_arrows(b_heat, meta["opponent"], rm_name)

    b_reaction = go.Figure()
    rt = dt_df["reaction_time_s"].dropna() if "reaction_time_s" in dt_df else pd.Series(dtype=float)
    if not rt.empty:
        b_reaction.add_trace(go.Histogram(
            x=rt,
            nbinsx=12,
            marker=dict(color=_C["accent_red"], line=dict(color="white", width=1)),
            name="Reaction time (s)",
        ))
        b_reaction.add_vline(x=float(rt.median()), line=dict(color=_RM, dash="dot"), annotation_text=f"Median {rt.median():.2f}s")
    b_reaction.update_layout(**_PL, height=_H_CHART, title="B Visualization — defensive reaction time", xaxis=dict(title="Seconds", gridcolor=_C["border"], automargin=True), yaxis=dict(title="Count", gridcolor=_C["border"], automargin=True), showlegend=False)

    # Phase C visuals
    c_heat = _phase_base_pitch("C Heatmap — RM defensive action density")
    if not def_actions.empty:
        c_heat = _add_phase_density(c_heat, def_actions["x"], def_actions["y"], "Blues", "Defensive density")
        c_heat.add_trace(go.Scatter(
            x=def_actions["x"], y=def_actions["y"], mode="markers",
            marker=dict(size=4, color="rgba(255,255,255,0.45)", line=dict(color="rgba(0,0,0,0.18)", width=0.5)),
            name="Action", hoverinfo="skip",
        ))
    c_heat = _add_direction_arrows(c_heat, meta["opponent"], rm_name)

    c_struct = go.Figure()
    c_struct.add_trace(go.Bar(
        x=["High"], y=[high],
        name="High Block", marker_color=_C["accent_green"],
        text=[high], textposition="auto",
    ))
    c_struct.add_trace(go.Bar(
        x=["Middle"], y=[mid],
        name="Middle Block", marker_color=_C["accent_blue"],
        text=[mid], textposition="auto",
    ))
    c_struct.add_trace(go.Bar(
        x=["Low"], y=[low],
        name="Low Block", marker_color=_C["accent_red"],
        text=[low], textposition="auto",
    ))
    c_struct.update_layout(**_PL, height=_H_CHART, title="C Visualization — defensive structure by block", xaxis=dict(gridcolor=_C["border"], automargin=True), yaxis=dict(gridcolor=_C["border"], automargin=True))

    # Phase D visuals
    d_heat = _phase_base_pitch("D Heatmap — transition origins")
    if not trans_df.empty:
        d_heat = _add_phase_density(d_heat, trans_df["origin_x"], trans_df["origin_y"], "Viridis", "Origin density")
        d_heat.add_trace(go.Scatter(
            x=trans_df["origin_x"], y=trans_df["origin_y"], mode="markers",
            marker=dict(size=4, color="rgba(255,255,255,0.45)", line=dict(color="rgba(0,0,0,0.18)", width=0.5)),
            name="Origin", hoverinfo="skip",
        ))
    d_heat = _add_direction_arrows(d_heat, meta["opponent"], rm_name)

    trans_map = _add_direction_arrows(trans_map, meta["opponent"], rm_name)

    phase_map = {
        "A": ("A. Offensive Moment", a_table, a_heat, a_zone),
        "B": ("B. Defensive Transition", b_table, b_heat, b_reaction),
        "C": ("C. Defensive Moment", c_table, c_heat, c_struct),
        "D": ("D. Offensive Transition", d_table, d_heat, trans_map),
    }
    key = selected_phase if selected_phase in phase_map else "A"
    title, table, heat_fig, viz_fig = phase_map[key]

    return html.Div([
        html.P(title, className="section-header"),
        dbc.Card(dbc.CardBody(table), className="mb-3"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=heat_fig, config={"displayModeBar": False, "responsive": True})), className="mb-3"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=viz_fig, config={"displayModeBar": False, "responsive": True})), className="mb-3"),
    ])


# ── Position Maps ──────────────────────────────────────────────────────────────

# Events used per phase
_POSMAP_PHASES = {
    "all":        None,                              # all events with valid x,y
    "possession": {"is_pass", "is_shot", "is_dribble", "touch"},   # attacking/possession
    "defense":    {"is_tackle", "is_interception", "is_recovery", "aerial"},  # defensive
}


def _get_shirt_numbers(data: dict, team_id: str) -> dict:
    """Return {player_id: shirt_number_str} from the typeId=34 formation event.

    Opta encodes the Starting XI in a single typeId=34 (team set-up) event per team.
    Qualifier 30 = comma-separated player_ids  (same IDs as event.playerId).
    Qualifier 59 = comma-separated shirt numbers in the same order.
    """
    evs = data.get("liveData", {}).get("event", [])
    for ev in evs:
        if ev.get("typeId") != 34 or ev.get("contestantId") != team_id:
            continue
        quals = {q.get("qualifierId"): q.get("value", "") for q in ev.get("qualifier", [])}
        pids   = [s.strip() for s in str(quals.get(30, "")).split(",") if s.strip()]
        shirts = [s.strip() for s in str(quals.get(59, "")).split(",") if s.strip()]
        return {pid: shirts[i] for i, pid in enumerate(pids) if i < len(shirts) and shirts[i]}
    return {}


def _shorten_name(full_name: str, max_len: int = 11) -> str:
    """Return a display-ready short name (last name or abbreviated first)."""
    parts = str(full_name).strip().split()
    if not parts:
        return full_name[:max_len]
    if len(parts) == 1:
        return parts[0][:max_len]
    last = parts[-1]
    if len(last) <= max_len:
        return last
    return last[:max_len]


def _filter_phase_events(ev: pd.DataFrame, phase: str) -> pd.DataFrame:
    """Filter events DataFrame to the events relevant for a given phase."""
    if phase == "possession":
        mask = (
            ev["is_pass"] | ev["is_shot"] | ev["is_dribble"] |
            (ev["type_id"] == 44)   # touch
        )
        return ev[mask]
    if phase == "defense":
        mask = (
            ev["is_tackle"] | ev["is_interception"] | ev["is_recovery"] |
            (ev["type_id"] == 37)   # aerial duel
        )
        return ev[mask]
    return ev   # "all"


def _convex_hull_trace(xs: np.ndarray, ys: np.ndarray, fill_rgba: str, line_color: str) -> go.Scatter | None:
    """Return a filled convex-hull Scatter trace, or None if < 3 points."""
    if len(xs) < 3:
        return None
    try:
        from scipy.spatial import ConvexHull
        pts = np.column_stack([xs, ys])
        hull = ConvexHull(pts)
        hx = list(pts[hull.vertices, 0]) + [pts[hull.vertices[0], 0]]
        hy = list(pts[hull.vertices, 1]) + [pts[hull.vertices[0], 1]]
        return go.Scatter(
            x=hx, y=hy, mode="lines",
            fill="toself", fillcolor=fill_rgba,
            line=dict(color=line_color, width=1.5, dash="dot"),
            hoverinfo="skip", showlegend=False,
        )
    except Exception:
        return None


def _team_line_shapes(avg_x_values: np.ndarray) -> list[dict]:
    """
    Vertical lines marking the FIXED pitch thirds (defensive | middle | attacking).

    Boundaries are absolute (x = 33.3 and 66.7), so the DEF/MID/FWD divisions never
    drift between phases / teams / matches. (Previously they were placed at the mean
    of a relative equal-thirds split of the players' average x, which moved every
    time the average positions changed.)
    """
    if len(avg_x_values) < 4:
        return []
    shapes = []
    for bx in (100.0 / 3.0, 200.0 / 3.0):
        shapes.append(dict(
            type="line",
            x0=bx, x1=bx, y0=0, y1=100,
            line=dict(color="rgba(80,80,80,0.40)", width=1.0, dash="dot"),
            layer="above",
        ))
    return shapes


def _pass_edge_traces(ev: pd.DataFrame) -> list[go.BaseTraceType]:
    """
    Build lightweight pass-connection traces between players.
    Uses ordered successful passes to infer passer→receiver pairs.
    Returns one transparent line trace per edge with opacity scaled to pass count.
    """
    traces = []
    succ = ev[ev["is_pass"] & (ev["outcome"] == 1)].copy().reset_index(drop=True)
    if succ.empty:
        return traces

    succ["__recv"] = succ["player_name"].shift(-1)
    succ = succ[succ["__recv"].notna() & (succ["__recv"] != succ["player_name"])]
    if succ.empty:
        return traces

    edges = (
        succ.groupby(["player_name", "__recv"])
        .size()
        .reset_index(name="cnt")
        .query("cnt >= 4")
    )
    if edges.empty:
        return traces

    # avg positions for edge endpoints
    pos_map = ev.groupby("player_name")[["x", "y"]].mean().to_dict("index")
    max_cnt = int(edges["cnt"].max()) or 1

    for _, row in edges.iterrows():
        p1, p2 = row["player_name"], row["__recv"]
        if p1 not in pos_map or p2 not in pos_map:
            continue
        alpha = 0.12 + 0.45 * (row["cnt"] / max_cnt)
        lw    = 0.8  + 3.2  * (row["cnt"] / max_cnt)
        traces.append(go.Scatter(
            x=[pos_map[p1]["x"], pos_map[p2]["x"]],
            y=[pos_map[p1]["y"], pos_map[p2]["y"]],
            mode="lines",
            line=dict(color=f"rgba(99,155,255,{alpha:.2f})", width=lw),
            hoverinfo="skip", showlegend=False,
        ))
    return traces


def _pitch_zone_overlay(ev: pd.DataFrame, n_x: int = 6, n_y: int = 5):
    """Zonal-activity overlay merged onto the position-map pitch.

    Returns (shapes, annotations): a grid of red-shaded rectangles (opacity ∝ the
    % of the team's events in that pitch zone) plus a small % label in each zone's
    corner. Coordinates match the pitch (x = length, attack → right; y = width),
    so it overlays directly under the player nodes. Reflects the phase already
    applied to `ev`.
    """
    shapes, annos = [], []
    if ev.empty:
        return shapes, annos
    x = ev["x"].clip(0, 100).to_numpy()
    y = ev["y"].clip(0, 100).to_numpy()
    xe = np.linspace(0, 100, n_x + 1)
    ye = np.linspace(0, 100, n_y + 1)
    counts, _, _ = np.histogram2d(x, y, bins=[xe, ye])
    total = counts.sum() or 1.0
    pct = counts / total * 100.0
    mx = float(pct.max()) or 1.0
    for i in range(n_x):
        for j in range(n_y):
            if counts[i, j] <= 0:
                op = 0.0
            else:
                op = 0.06 + 0.52 * (pct[i, j] / mx)
            shapes.append(dict(
                type="rect", x0=xe[i], x1=xe[i + 1], y0=ye[j], y1=ye[j + 1],
                layer="below", line=dict(color="rgba(20,20,20,0.18)", width=0.6),
                fillcolor=f"rgba(214,40,40,{op:.3f})",
            ))
            if pct[i, j] >= 1.0:
                # label in the zone's top-left corner to avoid colliding with nodes
                annos.append(dict(
                    x=xe[i] + (xe[i + 1] - xe[i]) * 0.18,
                    y=ye[j + 1] - (ye[j + 1] - ye[j]) * 0.20,
                    text=f"{pct[i, j]:.0f}%", showarrow=False,
                    font=dict(size=8.5, color="rgba(31,41,55,0.62)"),
                ))
    return shapes, annos


# Standard 5×5 position-code reference key (forward line at top → back line).
_POSITION_CODES = [
    ["LF",  "LCF", "CF",  "RCF", "RF"],
    ["LWF", "LAM", "CAM", "RAM", "RWF"],
    ["LM",  "LCM", "CM",  "RCM", "RM"],
    ["LWB", "LDM", "CDM", "RDM", "RWB"],
    ["LB",  "LCB", "CB",  "RCB", "RB"],
]


def _code_legend_table():
    """Small static position-code reference grid (for reading the zonal map)."""
    body = [
        html.Tr([
            html.Td(c, style={"textAlign": "center", "padding": "5px 9px",
                              "border": "1px solid #cbd5e1", "fontSize": "0.7rem",
                              "color": "#475569", "minWidth": "38px"})
            for c in row
        ])
        for row in _POSITION_CODES
    ]
    return html.Table(html.Tbody(body),
                      style={"borderCollapse": "collapse", "margin": "0 auto"})


def _position_map(fp: str, phase: str, team_side: str) -> go.Figure:
    """
    Build average-position map for Real Madrid or the opponent.

    Position calculation methodology
    ---------------------------------
    1. Load match events via parse_events().
    2. Filter to team and phase:
       • All Phases   — every event with valid x, y.
       • In Possession — passes (type 1/2), shots (13/15/16), dribbles (3), touches (44).
       • Out of Possession — tackles (7), interceptions (8), recoveries (49), aerials (37).
    3. Group by player_name → mean(x), mean(y), count(events).
    4. For opponents, mirror coordinates (100−x, 100−y) so they also read left→right.
    5. Node radius ∝ log1p(event_count); shirt number shown inside node.
    6. Convex hull drawn over player positions (scipy ConvexHull).
    7. Vertical lines mark defensive / midfield / forward line centres (equal-thirds split).
    8. Pass connection edges drawn for All/Possession phases (≥4 passes, opacity ∝ count).
    """
    data, meta, events = _load(fp)

    # ── empty figure factory ───────────────────────────────────────────────────
    def _empty(msg: str):
        fig = _phase_base_pitch("Position Map")
        fig.add_annotation(x=50, y=50, text=msg, showarrow=False,
                           font=dict(size=14, color=_C["text_secondary"]))
        return fig, html.Small(msg, className="text-muted")

    if meta is None or events is None or events.empty:
        return _empty("Select a match to view position map.")

    # ── team setup ─────────────────────────────────────────────────────────────
    team_id   = meta["rm_id"]   if team_side == "rm"  else meta["opp_id"]
    team_name = _rm_team_name(meta) if team_side == "rm" else meta.get("opponent", "Opponent")
    node_col  = _RM             if team_side == "rm"  else _C["accent_red"]
    hull_rgba = "rgba(37,99,235,0.09)"  if team_side == "rm" else "rgba(220,38,38,0.09)"

    shirt_nums = _get_shirt_numbers(data, team_id)

    # ── filter events ──────────────────────────────────────────────────────────
    ev = events[events["contestant_id"] == team_id].copy()
    ev = ev[ev["player_name"].notna() & (ev["player_name"].str.strip() != "")]
    ev = ev[ev["x"].notna() & ev["y"].notna()]
    ev = _filter_phase_events(ev, phase)

    if ev.empty:
        phase_labels = {"all": "All Phases", "possession": "In Possession", "defense": "Out of Possession"}
        return _empty(f"No {phase_labels.get(phase, phase)} events found.")

    # ── mirror opponent so both read left → right ──────────────────────────────
    if team_side == "opp":
        ev = ev.copy()
        ev["x"] = 100.0 - ev["x"]
        ev["y"] = 100.0 - ev["y"]

    # ── average positions ──────────────────────────────────────────────────────
    pid_first = ev.groupby("player_name")["player_id"].first()
    pos = (
        ev.groupby("player_name")
        .agg(avg_x=("x", "mean"), avg_y=("y", "mean"), n_ev=("event_id", "count"))
        .reset_index()
    )
    pos["player_id"] = pos["player_name"].map(pid_first).astype(str)
    pos["shirt"]     = pos["player_id"].map(shirt_nums).fillna("")
    pos["short"]     = pos["player_name"].apply(_shorten_name)
    # per-player pass volume (for the summary table)
    pass_ct = ev[ev["is_pass"]].groupby("player_name").size()
    pos["passes"] = pos["player_name"].map(pass_ct).fillna(0).astype(int)
    # role line (DEF / MID / FWD) by FIXED pitch thirds of average x — stable across
    # phases (team attacks → right, so the attacking third is high x).
    pos["line"] = np.where(pos["avg_x"] < 100.0 / 3.0, "DEF",
                  np.where(pos["avg_x"] < 200.0 / 3.0, "MID", "FWD"))
    # node size: logarithmic scaling → range [14, 44]
    log_ev  = np.log1p(pos["n_ev"].values)
    lo, hi  = log_ev.min(), log_ev.max()
    denom   = (hi - lo) if hi > lo else 1.0
    pos["sz"] = 14 + 30 * (log_ev - lo) / denom

    # ── zonal activity overlay (merged onto the pitch) ─────────────────────────
    zone_shapes, zone_annos = _pitch_zone_overlay(ev)

    # ── build figure ───────────────────────────────────────────────────────────
    fig = go.Figure()
    fig.update_layout(
        **{**_PL, "plot_bgcolor": _PITCH_FILL, "margin": dict(l=24, r=24, t=62, b=24)},
        height=_H_PITCH + 60,
        shapes=_pitch_stripes_full() + _pitch_shapes_full() + zone_shapes +
               _team_line_shapes(pos["avg_x"].values),
        xaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False,
                   zeroline=False, fixedrange=True),
        yaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False,
                   zeroline=False, scaleanchor="x", scaleratio=0.68, fixedrange=True),
    )
    for _a in zone_annos:
        fig.add_annotation(**_a)

    # pass connection edges (all / possession only)
    if phase in ("all", "possession"):
        for tr in _pass_edge_traces(ev):
            fig.add_trace(tr)

    # convex hull
    hull_tr = _convex_hull_trace(pos["avg_x"].values, pos["avg_y"].values, hull_rgba, node_col)
    if hull_tr is not None:
        fig.add_trace(hull_tr)

    # player nodes (circles sized by involvement)
    fig.add_trace(go.Scatter(
        x=pos["avg_x"], y=pos["avg_y"],
        mode="markers",
        marker=dict(
            size=pos["sz"], color=node_col, opacity=0.88,
            line=dict(color="white", width=2.2),
        ),
        customdata=np.stack([pos["player_name"], pos["n_ev"].astype(str),
                             pos["shirt"]], axis=1),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Events: %{customdata[1]}<br>"
            "Avg position: (%{x:.1f}, %{y:.1f})"
            "<extra></extra>"
        ),
        showlegend=False,
        name="Players",
    ))

    # shirt numbers inside nodes
    shirt_mask = pos["shirt"] != ""
    if shirt_mask.any():
        fig.add_trace(go.Scatter(
            x=pos.loc[shirt_mask, "avg_x"],
            y=pos.loc[shirt_mask, "avg_y"],
            mode="text",
            text=pos.loc[shirt_mask, "shirt"],
            textfont=dict(size=8, color="white", family="Arial Black"),
            textposition="middle center",
            hoverinfo="skip", showlegend=False,
        ))

    # player name labels — alternating above/below to reduce overlap
    for i, row in pos.reset_index(drop=True).iterrows():
        yshift = 22 if (i % 2 == 0) else -22
        fig.add_annotation(
            x=row["avg_x"], y=row["avg_y"],
            text=row["short"],
            showarrow=False,
            yshift=yshift,
            font=dict(size=8.5, color=_C["text_primary"], family="Arial"),
            bgcolor="rgba(255,255,255,0.78)",
            borderpad=2,
            bordercolor="rgba(0,0,0,0.08)",
            borderwidth=0.5,
            xanchor="center",
        )

    # line labels — fixed pitch thirds, centred in each third (team attacks → right)
    for cx, color, lbl in [
        (100.0 / 6.0, "#dc2626", "DEF"),   # defensive third  (≈16.7)
        (50.0,        "#d97706", "MID"),   # middle third
        (500.0 / 6.0, "#059669", "FWD"),   # attacking third  (≈83.3)
    ]:
        fig.add_annotation(
            x=cx, y=97, text=f"<b>{lbl}</b>", showarrow=False,
            font=dict(size=9, color=color),
            bgcolor="rgba(255,255,255,0.65)", borderpad=2,
        )

    # direction arrows + title
    opp_name = meta.get("opponent", "Opponent")
    rm_name  = _rm_team_name(meta)
    _add_direction_arrows(fig, opp_name, rm_name)

    phase_labels = {
        "all":        "All Phases",
        "possession": "In Possession",
        "defense":    "Out of Possession",
    }
    n_total = int(pos["n_ev"].sum())
    fig.update_layout(
        title=dict(
            text=(f"<b>{team_name} — {phase_labels.get(phase, phase)} Position Map</b>"
                  f"<br><sup>{len(pos)} players · {n_total} events · "
                  f"node size = event involvement</sup>"),
            x=0.5, xanchor="center",
            font=dict(size=13),
        ),
    )

    table = _position_table(pos, node_col)
    return fig, table


def _position_table(pos: pd.DataFrame, accent: str):
    """Player positional-summary table (shirt, name, line, avg position, events, passes)."""
    line_color = {"DEF": "#dc2626", "MID": "#d97706", "FWD": "#059669"}
    df = pos.sort_values(["avg_x"], ascending=False).reset_index(drop=True)

    header = html.Thead(html.Tr([
        html.Th("#"), html.Th("Player"), html.Th("Line"),
        html.Th("Avg X", className="text-end"), html.Th("Avg Y", className="text-end"),
        html.Th("Events", className="text-end"), html.Th("Passes", className="text-end"),
    ]))
    rows = []
    for _, r in df.iterrows():
        rows.append(html.Tr([
            html.Td(html.Span(r["shirt"] or "–",
                              style={"fontWeight": 700, "color": accent})),
            html.Td(r["player_name"]),
            html.Td(html.Span(r["line"], style={
                "color": line_color.get(r["line"], "#374151"), "fontWeight": 600,
                "fontSize": "0.78rem"})),
            html.Td(f"{r['avg_x']:.1f}", className="text-end"),
            html.Td(f"{r['avg_y']:.1f}", className="text-end"),
            html.Td(f"{int(r['n_ev'])}", className="text-end"),
            html.Td(f"{int(r['passes'])}", className="text-end"),
        ]))
    return dbc.Table([header, html.Tbody(rows)],
                     bordered=False, hover=True, striped=True, size="sm",
                     className="align-middle mb-0", style={"fontSize": "0.82rem"})


@callback(
    Output("tp-posmap",       "figure"),
    Output("tp-posmap-table", "children"),
    Input("tp-match",        "value"),
    Input("tp-posmap-phase", "value"),
    Input("tp-posmap-team",  "value"),
)
def _posmap_cb(fp, phase, team_side):
    phase = phase or "all"
    side  = team_side or "rm"
    return _position_map(fp, phase, side)
