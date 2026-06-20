"""
Opponent Analysis Page — Real Madrid Tactical Dashboard
Opponent profile and threat analysis from Opta event data.
"""

from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from config import COLOR_SCHEME
from utils.data_helpers import (
    get_competition_options, get_season_options, get_match_options,
)
from utils.data_loader import (
    load_match_json, extract_match_meta, parse_events,
    calc_match_kpis, get_shot_data, get_player_stats, get_match_lineup_status, calc_ppda,
)

_C  = COLOR_SCHEME
_RM = _C["accent_blue"]
_OPP = _C["accent_red"]
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


def _pitch_shapes_half():
    lw, s = 1.5, []

    def _rect(x0, x1, y0, y1, fc="rgba(0,0,0,0)"):
        s.append(dict(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(color=_PITCH_LINE, width=lw), fillcolor=fc, layer="below"))

    _rect(50, 100, 0, 100, _PITCH_FILL)
    s.append(dict(type="line", x0=50, x1=50, y0=0, y1=100,
                  line=dict(color=_PITCH_LINE, width=lw), layer="below"))
    _rect(83.5, 100, 21.1, 78.9)
    _rect(94.5, 100, 36.8, 63.2)
    _rect(100, 102, 45.2, 54.8, "white")
    return s


def _pitch_shapes_full():
    """Full pitch for shot maps showing both ends."""
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


def _pitch_stripes_half():
    stripes = []
    for i in range(10):
        x0 = 50 + (i * 5)
        x1 = x0 + 5
        fc = "rgba(76,175,80,0.08)" if i % 2 == 0 else "rgba(255,255,255,0.00)"
        stripes.append(dict(type="rect", x0=x0, x1=x1, y0=0, y1=100,
                            line=dict(width=0), fillcolor=fc, layer="below"))
    return stripes


def _add_pitch_context_labels(fig: go.Figure):
    # DATA coordinates so labels stay inside the pitch (full-pitch view).
    labels = [(16, 5, "Defensive Third"), (50, 5, "Middle Third"), (84, 5, "Attacking Third")]
    for x, y, text in labels:
        fig.add_annotation(
            x=x, y=y, xref="x", yref="y", text=text,
            showarrow=False, xanchor="center", yanchor="middle",
            font=_PITCH_LABEL_FONT, bgcolor="rgba(255,255,255,0.72)", borderpad=2,
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
        font=dict(size=10, color=_C["accent_blue"]),
    )
    return fig


def _rm_team_name(meta: dict) -> str:
    home = meta.get("home_team", "")
    away = meta.get("away_team", "")
    opp = meta.get("opponent", "")
    if home and away:
        return away if home == opp else home
    return "Real Madrid"


def _match_file_options(competition: str, season: str):
    from utils.data_loader import get_season_match_list
    matches = get_season_match_list(competition, season)
    opts = []
    for m in matches:
        venue = "H" if m.get("is_rm_home") else "A"
        week = m.get("week", "?")
        label = f"MD{week} · {venue} vs {m.get('opponent', 'OPP')} ({m.get('score_str', '-')})"
        opts.append({"label": label, "value": m["filepath"]})
    return opts


def layout(competition="LaLiga", season="2025-2026"):
    comp_opts   = get_competition_options()
    season_opts = get_season_options(competition)
    match_opts  = get_match_options(competition, season)
    default_val = match_opts[0]["value"] if match_opts else None

    return html.Div([
        html.Div([
            html.H4("Opponent Analysis", className="rm-page-title"),
            html.P("Opponent threat map and player profile from this match",
                   className="rm-page-subtitle"),
        ], className="rm-page-header"),

        # Primary match selection
        dbc.Card(dbc.CardBody([
            html.P("Competition / Season / Match", className="section-header mb-2"),
            html.Small("Choose the context and exact match to analyse.", className="text-muted d-block mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Label("Competition", className="filter-label"),
                    dcc.Dropdown(id="oa-competition", options=comp_opts,
                                 value=competition, clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("Season", className="filter-label"),
                    dcc.Dropdown(id="oa-season", options=season_opts,
                                 value=season, clearable=False),
                ], md=2),
                dbc.Col([
                    html.Label("Match", className="filter-label"),
                    dcc.Dropdown(id="oa-match", options=match_opts,
                                 value=default_val, clearable=False),
                ], md=8),
            ], className="g-2"),
        ]), className="filter-section mb-3"),

        # Match range filter
        dbc.Card(dbc.CardBody([
            html.P("Match Range", className="section-header mb-2"),
            html.Small("Use this only when you want to limit which matches appear in the Match dropdown.", className="text-muted d-block mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Label("From", className="filter-label"),
                    dcc.Dropdown(id="oa-from-match", options=[], clearable=False),
                ], md=6),
                dbc.Col([
                    html.Label("To", className="filter-label"),
                    dcc.Dropdown(id="oa-to-match", options=[], clearable=False),
                ], md=6),
            ], className="g-2"),
        ]), className="filter-section mb-4"),
        # Opponent KPI banner
        dcc.Loading(html.Div(id="oa-banner"), type="circle", color=_OPP),

        # Opponent shots + player table
        dbc.Card([
            dbc.CardHeader("Opponent Shot Map (attacking direction shown)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="oa-shot-map", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_OPP)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Starting XIs Shape (Selected Match)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="oa-lineup-pitch", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_OPP)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Opponent Player Stats"),
            dbc.CardBody(dcc.Loading(
                html.Div(id="oa-player-table"),
                type="circle", color=_OPP)),
        ], className="mb-3"),

        # Threat zones
        dbc.Card([
            dbc.CardHeader("Opponent Threat Heatmap (action density)"),
            dbc.CardBody(dcc.Loading(
                dcc.Graph(id="oa-threat-chart", config={"displayModeBar": False, "responsive": True}),
                type="circle", color=_OPP)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Style, Strengths, Weaknesses, Tendencies"),
            dbc.CardBody(dcc.Loading(html.Div(id="oa-style-block"), type="circle", color=_OPP)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Tactical Similarities, Reference Matches, Set-Pieces"),
            dbc.CardBody(dcc.Loading(html.Div(id="oa-context-block"), type="circle", color=_OPP)),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Automated Tactical Report"),
            dbc.CardBody(dcc.Loading(html.Div(id="oa-auto-report"), type="circle", color=_OPP)),
        ], className="mb-3"),

    ], className="page-content")


@callback(
    Output("oa-season", "options"), Output("oa-season", "value"),
    Input("oa-competition", "value"),
    State("oa-season", "value"),
)
def _season_opts(comp, current):
    opts = get_season_options(comp or "LaLiga")
    vals = [o["value"] for o in opts]
    return opts, (current if current in vals else (opts[0]["value"] if opts else "2025-2026"))


@callback(
    Output("oa-from-match", "options"), Output("oa-from-match", "value"),
    Output("oa-to-match", "options"), Output("oa-to-match", "value"),
    Input("oa-competition", "value"), Input("oa-season", "value"),
)
def _range_opts(comp, seas):
    opts = _match_file_options(comp or "LaLiga", seas or "2025-2026")
    if not opts:
        return [], None, [], None
    return opts, opts[0]["value"], opts, opts[-1]["value"]


@callback(
    Output("oa-match", "options"), Output("oa-match", "value"),
    Input("oa-competition", "value"), Input("oa-season", "value"),
    Input("oa-from-match", "value"), Input("oa-to-match", "value"),
)
def _match_opts(comp, seas, from_match, to_match):
    full_opts = get_match_options(comp or "LaLiga", seas or "2025-2026")
    if not full_opts:
        return [], None
    idx = {o["value"]: i for i, o in enumerate(full_opts)}
    i0 = idx.get(from_match, 0)
    i1 = idx.get(to_match, len(full_opts) - 1)
    lo, hi = (i0, i1) if i0 <= i1 else (i1, i0)
    opts = full_opts[lo:hi + 1]
    return opts, (opts[0]["value"] if opts else full_opts[0]["value"])


def _load(fp):
    if not fp:
        return None, None, None
    data   = load_match_json(fp)
    if not data:
        return None, None, None
    meta   = extract_match_meta(data)
    events = parse_events(data)
    return data, meta, events


@callback(
    Output("oa-banner", "children"),
    Input("oa-match", "value"),
)
def _banner(fp):
    _, meta, events = _load(fp)
    if meta is None:
        return dbc.Alert("Select a match to analyse the opponent.", color="info")

    opp_meta = {**meta, "rm_id": meta["opp_id"], "opp_id": meta["rm_id"],
                "rm_score": meta["opp_score"], "opp_score": meta["rm_score"]}
    kpis = calc_match_kpis(events, opp_meta)

    rm_score  = meta["rm_score"]
    opp_score = meta["opp_score"]
    result_vs = ("Won" if rm_score > opp_score else
                 "Drew" if rm_score == opp_score else "Lost")

    cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Opponent", className="kpi-title"),
            html.Div(meta["opponent"], className="kpi-value",
                     style={"color": _OPP, "fontSize": "1.2rem"}),
            html.Small(f"RM {result_vs} {rm_score}-{opp_score}",
                       className="text-muted"),
        ]), className="kpi-card"), lg=2, md=4, xs=6, className="mb-2"),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Opp Shots", className="kpi-title"),
            html.Div(str(kpis["shots_total"]), className="kpi-value",
                     style={"color": _OPP}),
            html.Small(f"On target: {kpis['shots_on_target']}", className="text-muted"),
        ]), className="kpi-card"), lg=2, md=4, xs=6, className="mb-2"),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Opp Passes", className="kpi-title"),
            html.Div(str(kpis["passes_total"]), className="kpi-value",
                     style={"color": _OPP}),
            html.Small(f"Acc: {kpis['pass_accuracy']}%", className="text-muted"),
        ]), className="kpi-card"), lg=2, md=4, xs=6, className="mb-2"),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Opp Possession %", className="kpi-title"),
            html.Div(f"{kpis['possession']}%", className="kpi-value",
                     style={"color": _OPP}),
        ]), className="kpi-card"), lg=2, md=4, xs=6, className="mb-2"),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Opp Tackles", className="kpi-title"),
            html.Div(str(kpis["tackles"]), className="kpi-value",
                     style={"color": _OPP}),
            html.Small(f"Inter: {kpis['interceptions']}", className="text-muted"),
        ]), className="kpi-card"), lg=2, md=4, xs=6, className="mb-2"),
    ], className="g-2 mb-3")
    return cards


@callback(
    Output("oa-shot-map", "figure"),
    Input("oa-match", "value"),
)
def _shot_map(fp):
    _, meta, events = _load(fp)

    def _base():
        f = go.Figure()
        f.update_layout(**{**_PL, "plot_bgcolor": _PITCH_FILL}, height=_H_PITCH,
                        shapes=_pitch_stripes_full() + _pitch_shapes_full(),
                        xaxis=dict(range=[0, 102], showticklabels=False,
                                   showgrid=False, zeroline=False),
                        yaxis=dict(range=[0, 100], showticklabels=False,
                                   showgrid=False, zeroline=False,
                                   scaleanchor="x", scaleratio=0.68),
                        title="Opponent Shot Map")
        f.add_annotation(x=0.25, y=0.97, xref="paper", yref="paper",
                         text="← Opponent attacks here", showarrow=False,
                         font=dict(size=10, color=_OPP))
        f.add_annotation(x=0.75, y=0.97, xref="paper", yref="paper",
                         text="Real Madrid attacks →", showarrow=False,
                         font=dict(size=10, color=_RM))
        return f

    if meta is None:
        return _base()

    shots = get_shot_data(events, meta)
    opp_id = str(meta["opp_id"])
    opp_shots = pd.DataFrame()
    if not shots.empty:
        opp_shots = shots[shots["contestant_id"].astype(str) == opp_id].copy()
        if opp_shots.empty and "team_label" in shots.columns:
            opp_shots = shots[shots["team_label"] == meta["opponent"]].copy()
    fig = _base()

    if opp_shots.empty:
        fig.add_annotation(text="No opponent shots", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    def _sizes(df):
        sizes = []
        for _, r in df.iterrows():
            raw = r.get("xg_display", r.get("xg", 0))
            xg_val = 0.0 if pd.isna(raw) else float(raw)
            sizes.append(9 + xg_val * 22)
        return sizes

    def _xg_text(v):
        if pd.isna(v):
            return "N/A"
        return f"{float(v):.3f}"

    # Opta coords are team-relative. Opp shots at x=84-96 mean near RM's goal.
    # Mirror (100-x, 100-y) to place them on the LEFT side of the full-pitch view.
    ox = 100 - opp_shots["x"]
    oy = 100 - opp_shots["y"]

    fig.update_layout(title=f"{meta['opponent']} Shots vs RM — Full Pitch View")
    fig.add_trace(go.Scatter(
        x=ox, y=oy, mode="markers",
        name="Opp shot",
        marker=dict(
            color=[_C["accent_yellow"] if r["is_goal"] else
                   _OPP if r["is_shot_on_target"] else "#90a4ae"
                   for _, r in opp_shots.iterrows()],
            size=_sizes(opp_shots),
            symbol=["star" if r["is_goal"] else
                    "diamond-open" if r["is_shot_on_target"] else "x"
                    for _, r in opp_shots.iterrows()],
            line=dict(color="white", width=1),
        ),
        text=[f"{r['player_name']}<br>{r['event_type']}<br>Min {r['minute']}'<br>xG {_xg_text(r.get('xg_display'))}"
              for _, r in opp_shots.iterrows()],
        hovertemplate="%{text}<extra></extra>",
    ))
    fig.add_annotation(
        text="⭐ = Goal  ◆ = On Target  ✕ = Off/Blocked",
        xref="paper", yref="paper", x=0.5, y=-0.06,
        showarrow=False, font=dict(size=10, color=_C["text_secondary"]),
    )
    return fig


@callback(
    Output("oa-player-table", "children"),
    Input("oa-match", "value"),
)
def _player_table(fp):
    _, meta, events = _load(fp)
    if meta is None:
        return dbc.Alert("Select a match first.", color="info")

    df = get_player_stats(events, meta["opp_id"])
    if df.empty:
        return dbc.Alert("No opponent player data.", color="warning")

    cols = {
        "player_name": "Player", "passes": "Passes",
        "shots": "Shots", "goals": "Goals",
        "tackles": "Tackles", "interceptions": "Inter.",
    }
    display = df[[c for c in cols if c in df.columns]].rename(columns=cols)
    display = display[display["Passes"] > 0].sort_values("Passes", ascending=False).head(15)

    return dbc.Table(
        [html.Thead(html.Tr([html.Th(c) for c in display.columns])),
         html.Tbody([
             html.Tr([html.Td(str(r[c])) for c in display.columns])
             for _, r in display.iterrows()
         ])],
        striped=True, hover=True, responsive=True, size="sm",
    )


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


@callback(
    Output("oa-lineup-pitch", "figure"),
    Input("oa-match", "value"),
)
def _lineup_pitch(fp):
    from pages.match_analysis import _extract_formation_lineup, _add_lineup_team
    data, meta, events = _load(fp)

    fig = go.Figure()
    fig.update_layout(
        **{**_PL, "plot_bgcolor": _PITCH_FILL,
           "legend": dict(orientation="h", yanchor="bottom", y=1.01, xanchor="center", x=0.5,
                          bgcolor="rgba(255,255,255,0.6)")},
        height=_H_PITCH,
        shapes=_pitch_stripes_full() + _pitch_shapes_full(),
        xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False, scaleanchor="x", scaleratio=0.68),
        title="Starting XIs",
    )

    if meta is None or events is None or events.empty:
        fig.add_annotation(text="Select a match to view starting 11.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    rm_name = _rm_team_name(meta)
    # Real formation from the Opta team set-up event (opponent attacks left = mirrored).
    rm_df, rm_form = _extract_formation_lineup(data, meta["rm_id"], mirror=False)
    opp_df, opp_form = _extract_formation_lineup(data, meta["opp_id"], mirror=True)

    if rm_df.empty and opp_df.empty:
        rm_df = _team_starting_positions(events, meta["rm_id"], mirror=False)
        opp_df = _team_starting_positions(events, meta["opp_id"], mirror=True)
        for d in (rm_df, opp_df):
            if not d.empty:
                d["shirt"] = ""; d["role"] = ""
        if rm_df.empty and opp_df.empty:
            fig.add_annotation(text="Could not detect starting XIs for this match.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig

    _add_lineup_team(fig, opp_df, _OPP, "bottom", f"{meta['opponent']}" + (f"  ({opp_form})" if opp_form else ""))
    _add_lineup_team(fig, rm_df, _RM, "top", f"{rm_name}" + (f"  ({rm_form})" if rm_form else ""))

    fig = _add_direction_arrows(fig, meta["opponent"], rm_name)
    title = f"{rm_name} ({rm_form}) vs {meta['opponent']} ({opp_form}) — Starting XIs" if rm_form else \
            f"{rm_name} vs {meta['opponent']} — Starting XIs"
    fig.update_layout(title=title)
    fig.add_annotation(text="Numbers = shirt · positions from Opta team set-up", xref="paper", yref="paper",
                       x=0.5, y=-0.06, showarrow=False, font=dict(size=10, color=_C["text_secondary"]))
    return fig


@callback(
    Output("oa-threat-chart", "figure"),
    Input("oa-match", "value"),
)
def _threat_chart(fp):
    _, meta, events = _load(fp)

    empty = go.Figure()
    empty.update_layout(**_PL, height=_H_PITCH, title="Opponent Threat Heatmap")

    if meta is None:
        return empty

    opp_ev = events[events["contestant_id"] == meta["opp_id"]]
    opp_ev = opp_ev[opp_ev["x"].notna() & opp_ev["y"].notna()].copy()
    if opp_ev.empty:
        return empty

    opp_name = meta.get("opponent", "Opponent")

    # Mirror coordinates: opponent attacks toward x=0 in RM's data frame, so
    # flip to show their attacking events on the right side of the display pitch.
    opp_ev["px"] = 100.0 - opp_ev["x"].astype(float)
    opp_ev["py"] = 100.0 - opp_ev["y"].astype(float)

    # Zone counts for annotation (from their perspective, high x = their attacking third)
    n_high = int((opp_ev["px"] >= 67).sum())   # opponent attacking third
    n_mid  = int(((opp_ev["px"] >= 33) & (opp_ev["px"] < 67)).sum())
    n_low  = int((opp_ev["px"] < 33).sum())    # opponent defensive third
    total  = len(opp_ev)

    fig = go.Figure()
    fig.update_layout(
        **_PL,
        height=_H_PITCH,
        title=(f"{opp_name} Action Density Heatmap  |  "
               f"Def Third {n_low} ({n_low/max(total,1)*100:.0f}%)  "
               f"Mid {n_mid} ({n_mid/max(total,1)*100:.0f}%)  "
               f"Att Third {n_high} ({n_high/max(total,1)*100:.0f}%)"),
        xaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False,
                   zeroline=False, fixedrange=True),
        yaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False,
                   zeroline=False, scaleanchor="x", scaleratio=0.68, fixedrange=True),
    )
    fig.update_layout(shapes=_pitch_stripes_full() + _pitch_shapes_full())

    # 2-D density heatmap on the pitch
    fig.add_trace(go.Histogram2d(
        x=opp_ev["px"], y=opp_ev["py"],
        xbins=dict(start=0, end=100, size=5),
        ybins=dict(start=0, end=100, size=5),
        colorscale=[
            [0.0,  "rgba(220,38,38,0.0)"],
            [0.25, "rgba(220,38,38,0.25)"],
            [0.6,  "rgba(220,38,38,0.55)"],
            [1.0,  "rgba(220,38,38,0.85)"],
        ],
        showscale=True,
        colorbar=dict(title="Actions", thickness=12, len=0.55),
        hovertemplate="x=%{x}, y=%{y}<br>Events: %{z}<extra></extra>",
        name="Action Density",
        zsmooth="best",
    ))

    # Individual high-danger events (shots + key passes) as markers
    danger = opp_ev[opp_ev["is_shot"] | opp_ev["is_goal"] | opp_ev["is_key_pass"]]
    if not danger.empty:
        fig.add_trace(go.Scatter(
            x=danger["px"], y=danger["py"],
            mode="markers",
            marker=dict(
                size=[12 if r["is_goal"] else 9 for _, r in danger.iterrows()],
                color=[_C.get("accent_yellow", "#f59e0b") if r["is_goal"] else
                       _OPP if r["is_shot"] else "#94a3b8"
                       for _, r in danger.iterrows()],
                symbol=["star" if r["is_goal"] else
                        "diamond-open" if r["is_shot"] else "circle-open"
                        for _, r in danger.iterrows()],
                line=dict(width=1, color="white"),
                opacity=0.85,
            ),
            name="Shots & Key Passes",
            customdata=[
                [r.get("player_name", "?"), int(r.get("minute", 0)),
                 "Goal" if r["is_goal"] else "Shot" if r["is_shot"] else "Key Pass"]
                for _, r in danger.iterrows()
            ],
            hovertemplate="%{customdata[0]} · %{customdata[2]} Min %{customdata[1]}'<extra></extra>",
        ))

    # Direction arrows
    fig.add_annotation(x=0.03, y=0.99, xref="paper", yref="paper",
                       text=f"{opp_name} attacks →", showarrow=False,
                       xanchor="left", font=dict(size=10, color=_OPP))
    fig.add_annotation(x=0.97, y=0.99, xref="paper", yref="paper",
                       text="← Real Madrid attacks", showarrow=False,
                       xanchor="right", font=dict(size=10, color=_RM))

    # Pitch third labels
    for cx, label in [(16, "Def Third"), (50, "Mid Third"), (84, "Att Third")]:
        fig.add_annotation(x=cx, y=4, xref="x", yref="y", text=label,
                           showarrow=False, font=dict(size=9, color="rgba(15,23,42,0.55)"),
                           bgcolor="rgba(255,255,255,0.70)", borderpad=2)

    return fig


def _safe_div(a, b):
    return float(a) / float(b) if b else 0.0


def _style_classification(k: dict) -> str:
    if k["pass_accuracy"] >= 85 and k["possession"] >= 52:
        return "Positional / possession-led"
    if k["ppda"] <= 6 and k["tackles"] + k["interceptions"] >= 18:
        return "Aggressive pressing"
    if k["shots_total"] >= 12 and k["pass_accuracy"] < 83:
        return "Direct transition"
    return "Balanced mixed style"


@callback(
    Output("oa-style-block", "children"),
    Output("oa-context-block", "children"),
    Output("oa-auto-report", "children"),
    Input("oa-match", "value"),
    Input("oa-competition", "value"),
    Input("oa-season", "value"),
)
def _scouting_blocks(fp, competition, season):
    _, meta, events = _load(fp)
    if meta is None or events is None or events.empty:
        empty = dbc.Alert("Select a match to generate opponent scouting report.", color="info")
        return empty, empty, empty

    opp_meta = {**meta, "rm_id": meta["opp_id"], "opp_id": meta["rm_id"],
                "rm_score": meta["opp_score"], "opp_score": meta["rm_score"]}
    rm_meta = {**meta, "rm_id": meta["rm_id"], "opp_id": meta["opp_id"],
               "rm_score": meta["rm_score"], "opp_score": meta["opp_score"]}
    ok = calc_match_kpis(events, opp_meta)
    rk = calc_match_kpis(events, rm_meta)

    opp_ev = events[events["contestant_id"] == meta["opp_id"]]
    rm_ev = events[events["contestant_id"] == meta["rm_id"]]
    opp_pass = opp_ev[opp_ev["is_pass"] & opp_ev["end_x"].notna()]

    style = _style_classification(ok)

    strengths = []
    weaknesses = []
    if ok["pass_accuracy"] >= 84:
        strengths.append("Reliable circulation under pressure")
    else:
        weaknesses.append("Pass completion unstable under pressure")
    if ok["shots_total"] >= 10:
        strengths.append("Creates frequent shot volume")
    else:
        weaknesses.append("Limited shot generation")
    if ok["ppda"] <= 7:
        strengths.append("Can sustain active pressing phases")
    else:
        weaknesses.append("Pressing intensity drops in settled phases")
    if ok["goals_conceded"] >= 2:
        weaknesses.append("Concedes high-quality moments")

    press_tend = f"PPDA {ok['ppda']:.2f}; defensive actions {ok['tackles'] + ok['interceptions'] + ok['ball_recoveries']}"
    poss_style = f"{ok['possession']}% possession, {ok['pass_accuracy']}% pass accuracy"

    # Transition danger from observed regain-to-shot windows
    regains = opp_ev[opp_ev["is_recovery"] | opp_ev["is_interception"] | opp_ev["is_tackle"]].copy()
    if not regains.empty:
        tdf = events.sort_values(["period", "minute", "second", "event_id"]).copy()
        tdf["t"] = (tdf["minute"].fillna(0).astype(int) * 60) + tdf["second"].fillna(0).astype(int)
        regains = regains.assign(t=(regains["minute"].fillna(0).astype(int) * 60) + regains["second"].fillna(0).astype(int))
        trans_shots = 0
        for _, r in regains.iterrows():
            win = tdf[(tdf["contestant_id"] == meta["opp_id"]) & (tdf["t"] >= r["t"]) & (tdf["t"] <= r["t"] + 15)]
            if not win[win["is_shot"]].empty:
                trans_shots += 1
        transition_danger = f"{_safe_div(trans_shots, len(regains)) * 100:.1f}% regains lead to shot <=15s"
    else:
        transition_danger = "No clear transition windows"

    # Key players from raw event outputs (no weighted synthetic score)
    pstats = get_player_stats(events, meta["opp_id"])
    if pstats.empty:
        key_players = []
    else:
        pstats = pstats.copy()
        key_players = pstats.sort_values(
            ["shots", "xg", "passes", "tackles", "interceptions"],
            ascending=[False, False, False, False, False],
        ).head(3)["player_name"].tolist()

    # Tactical comparison vs RM from directly observed metrics
    pass_delta = ok["pass_accuracy"] - rk["pass_accuracy"]
    ppda_delta = ok["ppda"] - rk["ppda"]
    shots_delta = ok["shots_total"] - rk["shots_total"]
    xg_delta = ok["xg_for"] - rk["xg_for"]
    tactical_compare = (
        f"Pass acc delta {pass_delta:+.1f} pp | "
        f"PPDA delta {ppda_delta:+.2f} | "
        f"Shot volume delta {shots_delta:+d} | "
        f"xG delta {xg_delta:+.2f}"
    )

    # Tactical similarity to RM (0-100), derived purely from the observed deltas
    # above. Each metric's absolute delta is normalised by a typical match-level
    # spread, clamped to [0,1]; similarity = 100 * (1 - mean normalised distance).
    _norm = [
        min(abs(pass_delta) / 25.0, 1.0),                       # pass accuracy (pp)
        min(abs(ppda_delta) / 12.0, 1.0),                       # PPDA
        min(abs(shots_delta) / 15.0, 1.0),                      # shot volume
        min(abs(xg_delta) / 2.5, 1.0),                          # xG
        min(abs(ok["possession"] - rk["possession"]) / 40.0, 1.0),  # possession (pp)
    ]
    sim = round(100.0 * (1.0 - sum(_norm) / len(_norm)), 1)

    # Reference matches — all fixtures vs same opponent this season
    from utils.data_helpers import get_match_options
    refs = []
    for m in get_match_options(competition or "LaLiga", season or "2025-2026"):
        label = m.get("label", "")
        if meta["opponent"] in label:
            refs.append(label)
    refs = refs[:5]
    refs_display = (
        f"{len(refs)} fixture(s) vs {meta['opponent']}: " + ", ".join(refs)
        if refs else "No additional indexed matches"
    )

    # Set-piece tendencies from observed corner sequences
    corners = int((opp_ev["type_id"] == 6).sum())
    ev_sorted = events.sort_values(["period", "minute", "second", "event_id"]).copy()
    ev_sorted["event_sec"] = (ev_sorted["minute"].fillna(0).astype(int) * 60) + ev_sorted["second"].fillna(0).astype(int)
    opp_sorted = ev_sorted[ev_sorted["contestant_id"] == meta["opp_id"]].copy()
    opp_corners = opp_sorted[opp_sorted["type_id"] == 6]
    corner_shot_count = 0
    for _, c in opp_corners.iterrows():
        t0 = c["event_sec"]
        win = opp_sorted[(opp_sorted["event_sec"] >= t0) & (opp_sorted["event_sec"] <= t0 + 20)]
        corner_shot_count += int(len(win[win["is_shot"]]))
    set_piece_line = f"Corners: {corners}, shots within 20s of corner: {corner_shot_count}"

    # Vulnerable zones (where RM won duels/recoveries vs opponent)
    forced = rm_ev[rm_ev["is_recovery"] | rm_ev["is_interception"] | rm_ev["is_tackle"]]
    if forced.empty:
        vuln_zone = "Not enough forced turnovers"
    else:
        thirds = pd.cut(forced["x"], bins=[-1, 33, 67, 101], labels=["RM defensive", "middle", "RM attacking"])
        vuln_zone = str(thirds.value_counts().idxmax())

    style_block = dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Category"), html.Th("Assessment")])),
            html.Tbody([
                html.Tr([html.Td("opponent style classification"), html.Td(style)]),
                html.Tr([html.Td("strengths and weaknesses"), html.Td("Strengths: " + "; ".join(strengths[:3]) + " | Weaknesses: " + "; ".join(weaknesses[:3]))]),
                html.Tr([html.Td("pressing tendencies"), html.Td(press_tend)]),
                html.Tr([html.Td("possession style"), html.Td(poss_style)]),
                html.Tr([html.Td("transition danger"), html.Td(transition_danger)]),
                html.Tr([html.Td("vulnerable zones"), html.Td(vuln_zone)]),
            ]),
        ],
        striped=True,
        hover=True,
        responsive=True,
        size="sm",
        className="mb-0",
    )

    context_block = dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Category"), html.Th("Assessment")])),
            html.Tbody([
                html.Tr([html.Td("key players"), html.Td(", ".join(key_players) if key_players else "Not enough player-level events")]),
                html.Tr([html.Td("tactical comparison vs RM"), html.Td(tactical_compare)]),
                html.Tr([html.Td("reference matches"), html.Td(refs_display)]),
                html.Tr([html.Td("set-piece tendencies"), html.Td(set_piece_line)]),
            ]),
        ],
        striped=True,
        hover=True,
        responsive=True,
        size="sm",
        className="mb-0",
    )

    report_lines = [
        f"Automated Tactical Report — {meta['opponent']} vs Real Madrid",
        f"Style: {style}.",
        f"Pressing profile: {press_tend}.",
        f"Possession profile: {poss_style}.",
        f"Transition danger: {transition_danger}.",
        f"Key players: {', '.join(key_players) if key_players else 'No clear high-impact players extracted'}.",
        f"Vulnerable zone against RM pressure: {vuln_zone}.",
        f"Set-piece tendencies: {set_piece_line}.",
        f"Tactical similarity to RM: {sim:.1f}/100.",
        "Actionable recommendation: press their first pass after regain and force play into the identified vulnerable zone.",
    ]
    report = dbc.Alert(html.Pre("\n".join(report_lines), style={"marginBottom": 0, "whiteSpace": "pre-wrap"}), color="light")

    return style_block, context_block, report
