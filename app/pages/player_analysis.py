"""
Player Analysis Page — Real Madrid Tactical Dashboard
Per-player event-level metrics from Opta JSON data.
"""

from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

from config import COLOR_SCHEME, DATA_ROOT
from utils.data_helpers import get_competition_options, get_season_options
from utils.data_loader import (
    get_season_match_list,
    load_match_json,
    extract_match_meta,
    parse_events,
    get_player_stats,
    get_match_lineup_status,
)

_C  = COLOR_SCHEME
_RM = _C["accent_blue"]
_H_CHART = 400
_H_RADAR = 420
_PL = dict(
    paper_bgcolor=_C["surface"],
    plot_bgcolor=_C["surface"],
    font=dict(color=_C["text_primary"], size=11),
    margin=dict(l=48, r=28, t=56, b=56),
    uniformtext_minsize=9,
    uniformtext_mode="hide",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
)


def _compact_match_label(week, opponent):
    token = str(opponent or "OPP").replace("_", " ").split()[0]
    short = token[:3].upper() if token else "OPP"
    return f"MD{week if week is not None else '?'} {short}"


_COMP_FOLDER = {
    "LaLiga": "LaLiga",
    "Copa del Rey": "Copa del Rey",
    "Champions League": "UEFA Champions League",
}


def _season_player_csv_path(competition: str, season: str) -> Path:
    folder = _COMP_FOLDER.get(competition, competition)
    return Path(DATA_ROOT) / folder / season / "equipos" / "Real_Madrid_CF" / "Real_Madrid_CF_jugadores_seasonstats.csv"


def _norm_name(name: str) -> str:
    return str(name or "").strip().lower()


def _role_template(player_name: str, position: str) -> str:
    nm = _norm_name(player_name)
    pos = str(position or "")

    if pos == "Goalkeeper":
        return "GK"
    if pos == "Forward":
        return "ST"

    if pos == "Defender":
        fb_tokens = ["carvajal", "alexander-arnold", "fran garc", "mendy", "vazquez", "lucas", "miguel"]
        if any(t in nm for t in fb_tokens):
            return "FB"
        return "CB"

    dm_tokens = ["tchou", "camavinga", "ceballos"]
    amw_tokens = ["bellingham", "guler", "vinicius", "rodrygo", "brahim", "modric", "valverde"]
    if any(t in nm for t in dm_tokens):
        return "DM"
    if any(t in nm for t in amw_tokens):
        return "AMW"
    return "DM"


def _lineup_status(starts: float, sub_on: float, appearances: float) -> str:
    st = float(starts or 0)
    so = float(sub_on or 0)
    ap = float(appearances or 0)
    if st > 0:
        return "Starting 11"
    if so > 0:
        return "Sub On"
    if ap > 0:
        return "On Bench"
    return "Not in Squad"


def _season_player_catalog(competition: str, season: str) -> pd.DataFrame:
    path = _season_player_csv_path(competition, season)
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()

    if "nombre" not in df.columns:
        return pd.DataFrame()

    out = pd.DataFrame({
        "player_name": df["nombre"].astype(str),
        "position": df["posicion"] if "posicion" in df.columns else "",
        "starts": pd.to_numeric(df["Starts"], errors="coerce").fillna(0) if "Starts" in df.columns else 0,
        "sub_on": pd.to_numeric(df["Substitute On"], errors="coerce").fillna(0) if "Substitute On" in df.columns else 0,
        "appearances": pd.to_numeric(df["Appearances"], errors="coerce").fillna(0) if "Appearances" in df.columns else 0,
        "time_played": pd.to_numeric(df["Time Played"], errors="coerce").fillna(0) if "Time Played" in df.columns else 0,
    })
    out["role_template"] = [
        _role_template(n, p) for n, p in zip(out["player_name"], out["position"])
    ]
    out["lineup_status"] = [
        _lineup_status(s, so, a) for s, so, a in zip(out["starts"], out["sub_on"], out["appearances"])
    ]
    return out


def _match_file_options(competition: str, season: str):
    matches = get_season_match_list(competition, season)
    opts = []
    for m in matches:
        venue = "H" if m.get("is_rm_home") else "A"
        md = m.get("week", "?")
        opp = m.get("opponent", "OPP")
        score = m.get("score_str", "-")
        label = f"MD{md} · {venue} vs {opp} ({score})"
        opts.append({"label": label, "value": m["filepath"]})
    return opts


def _build_season_player_stats(competition: str, season: str, selected_files: set[str] | None = None) -> pd.DataFrame:
    """Aggregate player stats across all RM matches in a season."""
    matches = get_season_match_list(competition, season)
    frames  = []
    for m in matches:
        if selected_files is not None and m["filepath"] not in selected_files:
            continue
        try:
            data   = load_match_json(m["filepath"])
            events = parse_events(data)
            df     = get_player_stats(events, m["rm_id"])
            if not df.empty:
                df["match_label"] = f"MD{m.get('week','?')} {m['opponent'][:10]}"
                df["result"]      = m["result"]
                frames.append(df)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    # Aggregate per player
    agg = combined.groupby(["player_id", "player_name"]).agg(
        matches_played  = ("match_label", "count"),
        passes          = ("passes", "sum"),
        shots           = ("shots", "sum"),
        goals           = ("goals", "sum"),
        key_passes      = ("key_passes", "sum"),
        assists         = ("assists", "sum"),
        tackles         = ("tackles", "sum"),
        interceptions   = ("interceptions", "sum"),
        recoveries      = ("recoveries", "sum"),
        dribbles        = ("dribbles", "sum"),
        xg              = ("xg", "sum"),
    ).reset_index()
    agg["xg"] = agg["xg"].round(2)
    return agg.sort_values("passes", ascending=False)


def _get_player_match_series(competition: str, season: str, player_name: str, selected_files: set[str] | None = None) -> pd.DataFrame:
    """Per-match stats for a single player."""
    matches = get_season_match_list(competition, season)
    rows = []
    for m in matches:
        if selected_files is not None and m["filepath"] not in selected_files:
            continue
        try:
            data   = load_match_json(m["filepath"])
            events = parse_events(data)
            df     = get_player_stats(events, m["rm_id"])
            if df.empty:
                continue
            pm = df[df["player_name"] == player_name]
            if pm.empty:
                continue
            r = pm.iloc[0]
            rows.append({
                "match": _compact_match_label(m.get("week", "?"), m.get("opponent", "OPP")),
                "passes": r.get("passes", 0),
                "shots": r.get("shots", 0),
                "goals": r.get("goals", 0),
                "tackles": r.get("tackles", 0),
                "xg": r.get("xg", 0),
                "minutes_played": r.get("minutes_played", 0),
                "result": m["result"],
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


def _collect_player_touches(competition: str, season: str, player_name: str,
                            selected_files: set[str] | None = None):
    """Pool a player's on-ball touch coordinates across the selected match(es).

    Opta coordinates are team-relative (x grows toward the attacking goal), so all
    matches can be pooled directly. Returns (points_df, n_matches).
    For a single match this is that match's touches; for several, the pooled set —
    which is exactly the average spatial distribution the zone percentages describe.
    """
    matches = get_season_match_list(competition, season)
    frames, n_matches = [], 0
    for m in matches:
        if selected_files is not None and m["filepath"] not in selected_files:
            continue
        try:
            events = parse_events(load_match_json(m["filepath"]))
            pe = events[(events["contestant_id"] == m["rm_id"])
                        & (events["player_name"] == player_name)
                        & (events["x"].notna()) & (events["y"].notna())]
            if pe.empty:
                continue
            frames.append(pe[["x", "y"]].copy())
            n_matches += 1
        except Exception:
            continue
    if not frames:
        return pd.DataFrame(columns=["x", "y"]), 0
    return pd.concat(frames, ignore_index=True), n_matches


def _player_touch_heatmap(competition: str, season: str, player_name: str,
                          selected_files: set[str] | None, single_match: bool):
    """Zoned touch heatmap (6×5 grid) with % per zone + touch dots, à la The Athletic."""
    import numpy as np
    from pages.match_analysis import _pitch_shapes_full

    pts, n_matches = _collect_player_touches(competition, season, player_name, selected_files)

    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=_C["surface"], plot_bgcolor="#f3ede9",
        font=dict(color=_C["text_primary"], size=11), height=520,
        margin=dict(l=20, r=20, t=64, b=40),
        xaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(range=[-2, 102], showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=0.68, fixedrange=True),
        showlegend=False,
    )

    # transparent pitch (grey lines, no green fill) so the red zones read clearly
    pitch_lines = _pitch_shapes_full(color="#7c828c", fill="rgba(0,0,0,0)")

    if pts.empty:
        fig.update_layout(shapes=pitch_lines, title=f"{player_name} — Touch Map")
        fig.add_annotation(x=50, y=50, text="No touch data for this selection.",
                           showarrow=False, font=dict(size=14, color=_C["text_secondary"]))
        return fig

    # 6 columns (length) × 5 rows (width) grid
    n_cols, n_rows = 6, 5
    x_edges = np.linspace(0, 100, n_cols + 1)
    y_edges = np.linspace(0, 100, n_rows + 1)
    counts, _, _ = np.histogram2d(pts["x"], pts["y"], bins=[x_edges, y_edges])
    total = counts.sum()
    pct = counts / total * 100.0 if total else counts
    max_pct = float(pct.max()) if total else 1.0

    # zone shading (red, opacity ∝ share, with a visible floor for non-empty zones)
    zone_shapes = []
    for i in range(n_cols):
        for j in range(n_rows):
            share = (pct[i, j] / max_pct) if max_pct else 0.0
            op = (0.07 + 0.80 * share) if counts[i, j] > 0 else 0.0
            zone_shapes.append(dict(
                type="rect", x0=x_edges[i], x1=x_edges[i + 1],
                y0=y_edges[j], y1=y_edges[j + 1], layer="below",
                line=dict(width=0),
                fillcolor=f"rgba(214,40,40,{op:.3f})",
            ))

    # explicit dotted grid lines so every zone partition is clearly visible
    grid_lines = []
    for xe in x_edges[1:-1]:
        grid_lines.append(dict(type="line", x0=xe, x1=xe, y0=0, y1=100, layer="below",
                               line=dict(color="rgba(40,40,40,0.55)", width=1.2, dash="dot")))
    for ye in y_edges[1:-1]:
        grid_lines.append(dict(type="line", x0=0, x1=100, y0=ye, y1=ye, layer="below",
                               line=dict(color="rgba(40,40,40,0.55)", width=1.2, dash="dot")))

    fig.update_layout(shapes=zone_shapes + grid_lines + pitch_lines)

    # touch dots
    fig.add_trace(go.Scatter(
        x=pts["x"], y=pts["y"], mode="markers",
        marker=dict(size=4, color="rgba(40,40,40,0.18)", line=dict(width=0)),
        hoverinfo="skip",
    ))

    # % labels per zone (hide negligible zones)
    for i in range(n_cols):
        for j in range(n_rows):
            v = pct[i, j]
            if v < 0.5:
                continue
            fig.add_annotation(
                x=(x_edges[i] + x_edges[i + 1]) / 2,
                y=(y_edges[j] + y_edges[j + 1]) / 2,
                text=f"<b>{v:.0f}%</b>", showarrow=False,
                font=dict(size=13, color="#1f2937"),
            )

    # "Attack →" direction indicator (bottom-centre)
    fig.add_annotation(x=50, y=-1.5, ax=38, ay=-1.5, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=2, arrowwidth=1.5,
                       arrowcolor=_C["text_secondary"], text="")
    fig.add_annotation(x=50, y=-4.0, text="Attack", showarrow=False,
                       font=dict(size=11, color=_C["text_secondary"]))

    scope = ("this match" if single_match else f"average across {n_matches} matches")
    fig.update_layout(title=dict(
        text=(f"<b>Where {player_name} has had his touches</b>"
              f"<br><sup>{int(total)} on-ball touches · {scope} · {competition} {season}</sup>"),
        x=0.5, xanchor="center", font=dict(size=14),
    ))
    return fig


# ============================================================================
# LAYOUT
# ============================================================================

def layout(competition="LaLiga", season="2025-2026"):
    comp_opts   = get_competition_options()
    season_opts = get_season_options(competition)

    return html.Div([
        html.Div([
            html.H4("Player Analysis", className="rm-page-title"),
            html.P("Individual player metrics computed from Opta event data",
                   className="rm-page-subtitle"),
        ], className="rm-page-header"),

        # Filters
        dbc.Card(dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Competition", className="filter-label"),
                    dcc.Dropdown(id="pa-competition",
                                 options=comp_opts,
                                 value=competition, clearable=False),
                ], md=3, sm=6),
                dbc.Col([
                    html.Label("Season", className="filter-label"),
                    dcc.Dropdown(id="pa-season",
                                 options=season_opts,
                                 value=season, clearable=False),
                ], md=3, sm=6),
                dbc.Col([
                    html.Label("Player", className="filter-label"),
                    dcc.Dropdown(id="pa-player",
                                 options=[],
                                 clearable=False,
                                 placeholder="Select a player…"),
                ], md=6),
            ], className="g-2"),
        ), className="filter-section filter-primary mb-3"),

        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Role Template", className="filter-label"),
                    dcc.Dropdown(
                        id="pa-role-template",
                        options=[
                            {"label": "All", "value": "All"},
                            {"label": "CB", "value": "CB"},
                            {"label": "DM", "value": "DM"},
                            {"label": "FB", "value": "FB"},
                            {"label": "AMW", "value": "AMW"},
                            {"label": "ST", "value": "ST"},
                            {"label": "GK", "value": "GK"},
                        ],
                        value="All",
                        clearable=False,
                    ),
                ], md=3, sm=6),
                dbc.Col([
                    html.Label("Line-up Status", className="filter-label"),
                    dcc.Dropdown(
                        id="pa-lineup-status",
                        options=[
                            {"label": "All", "value": "All"},
                            {"label": "Starting 11", "value": "Starting 11"},
                            {"label": "Sub On", "value": "Sub On"},
                            {"label": "On Bench", "value": "On Bench"},
                            {"label": "Not in Squad", "value": "Not in Squad"},
                        ],
                        value="All",
                        clearable=False,
                    ),
                ], md=3, sm=6),
                dbc.Col([
                    html.Label("Minutes Played % (min)", className="filter-label"),
                    dcc.Slider(
                        id="pa-minutes-pct",
                        min=0,
                        max=100,
                        step=5,
                        value=0,
                        marks={0: "0", 25: "25", 50: "50", 75: "75", 100: "100"},
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                ], md=6),
            ], className="g-2"),
            html.Hr(className="my-3"),
            dbc.Row([
                dbc.Col([
                    html.Label("Match Range: From", className="filter-label"),
                    dcc.Dropdown(id="pa-from-match", options=[], clearable=False),
                ], md=6),
                dbc.Col([
                    html.Label("Match Range: To", className="filter-label"),
                    dcc.Dropdown(id="pa-to-match", options=[], clearable=False),
                ], md=6),
            ], className="g-2"),
        ]), className="filter-section mb-4"),

        # Season squad table
        html.P("Squad Performance Summary", className="section-header"),
        dcc.Loading(html.Div(id="pa-squad-table"), type="circle", color=_RM),

        # Player deep-dive charts
        html.P("Player Deep Dive", className="section-header"),
        dcc.Loading(html.Div(id="pa-player-section"), type="circle", color=_RM),

    ], className="page-content")


# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output("pa-season", "options"),
    Output("pa-season", "value"),
    Input("pa-competition", "value"),
    State("pa-season", "value"),
)
def _season_opts(competition, current):
    comp = competition or "LaLiga"
    opts = get_season_options(comp)
    vals = [o["value"] for o in opts]
    val  = current if current in vals else (opts[0]["value"] if opts else "2025-2026")
    return opts, val


@callback(
    Output("pa-from-match", "options"),
    Output("pa-from-match", "value"),
    Output("pa-to-match", "options"),
    Output("pa-to-match", "value"),
    Input("pa-competition", "value"),
    Input("pa-season", "value"),
)
def _range_opts(competition, season):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"
    opts = _match_file_options(comp, seas)
    if not opts:
        return [], None, [], None
    return opts, opts[0]["value"], opts, opts[-1]["value"]


def _selected_file_set(competition, season, from_match, to_match):
    opts = _match_file_options(competition or "LaLiga", season or "2025-2026")
    if not opts:
        return set()
    idx = {o["value"]: i for i, o in enumerate(opts)}
    i0 = idx.get(from_match, 0)
    i1 = idx.get(to_match, len(opts) - 1)
    lo, hi = (i0, i1) if i0 <= i1 else (i1, i0)
    return {o["value"] for o in opts[lo:hi + 1]}


@callback(
    Output("pa-player", "options"),
    Output("pa-player", "value"),
    Input("pa-competition", "value"),
    Input("pa-season", "value"),
    Input("pa-role-template", "value"),
    Input("pa-lineup-status", "value"),
    Input("pa-minutes-pct", "value"),
    Input("pa-from-match", "value"),
    Input("pa-to-match", "value"),
)
def _player_opts(competition, season, role_template, lineup_status, min_minutes_pct, from_match, to_match):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"
    selected_files = _selected_file_set(comp, seas, from_match, to_match)
    df   = _build_season_player_stats(comp, seas, selected_files=selected_files)
    if df.empty:
        return [], None

    catalog = _season_player_catalog(comp, seas)
    if not catalog.empty:
        merged = df.merge(catalog[["player_name", "role_template", "lineup_status"]], on="player_name", how="left")
    else:
        merged = df.copy()
        merged["role_template"] = ""
        merged["lineup_status"] = ""

    matches_in_range = max(len(selected_files), 1)
    merged["minutes_pct"] = (pd.to_numeric(merged.get("matches_played", 0), errors="coerce").fillna(0) * 90.0 / (matches_in_range * 90.0) * 100.0)

    if role_template and role_template != "All":
        merged = merged[merged["role_template"] == role_template]
    if lineup_status and lineup_status != "All":
        merged = merged[merged["lineup_status"] == lineup_status]

    min_pct = float(min_minutes_pct or 0)
    merged = merged[merged["minutes_pct"] >= min_pct]

    opts = [{"label": row["player_name"], "value": row["player_name"]}
            for _, row in merged.head(60).iterrows()
            if row["passes"] > 0]
    val  = opts[0]["value"] if opts else None
    return opts, val


@callback(
    Output("pa-squad-table", "children"),
    Input("pa-competition", "value"),
    Input("pa-season", "value"),
    Input("pa-role-template", "value"),
    Input("pa-lineup-status", "value"),
    Input("pa-minutes-pct", "value"),
    Input("pa-from-match", "value"),
    Input("pa-to-match", "value"),
)
def _squad_table(competition, season, role_template, lineup_status, min_minutes_pct, from_match, to_match):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"
    selected_files = _selected_file_set(comp, seas, from_match, to_match)
    df   = _build_season_player_stats(comp, seas, selected_files=selected_files)

    if df.empty:
        return dbc.Alert(f"No player data found for {comp} {seas}.", color="info")

    # --- Lineup status: use per-match detection when single match selected ---
    single_match = (from_match == to_match and from_match is not None)
    if single_match:
        try:
            data   = load_match_json(from_match)
            meta   = extract_match_meta(data)
            events = parse_events(data)
            per_match_lineup = get_match_lineup_status(events, meta["rm_id"])
        except Exception:
            per_match_lineup = {}
        df["lineup_status"] = df["player_name"].map(lambda n: per_match_lineup.get(n, "Starting 11"))
        df["role_template"] = ""
    else:
        catalog = _season_player_catalog(comp, seas)
        if not catalog.empty:
            df = df.merge(catalog[["player_name", "role_template", "lineup_status"]], on="player_name", how="left")
        else:
            df["role_template"] = ""
            df["lineup_status"] = ""

    matches_in_range = max(len(selected_files), 1)
    df["minutes_pct"] = (pd.to_numeric(df.get("matches_played", 0), errors="coerce").fillna(0) / matches_in_range * 100.0).round(1)

    if role_template and role_template != "All" and not single_match:
        df = df[df["role_template"] == role_template]
    if lineup_status and lineup_status != "All":
        df = df[df["lineup_status"] == lineup_status]
    if not single_match:
        df = df[df["minutes_pct"] >= float(min_minutes_pct or 0)]

    cols_map = {
        "player_name":    "Player",
        "role_template":  "Role",
        "lineup_status":  "Line-up",
        "minutes_pct":    "Min %",
        "matches_played": "MP",
        "passes":         "Passes",
        "shots":          "Shots",
        "goals":          "Goals",
        "key_passes":     "Key Passes",
        "assists":        "Assists",
        "tackles":        "Tackles",
        "interceptions":  "Inter.",
        "recoveries":     "Recov.",
        "xg":             "xG",
    }
    # Hide Role/Min% columns in single-match view since they're meaningless
    if single_match:
        cols_map.pop("role_template", None)
        cols_map.pop("minutes_pct", None)

    display = df[[c for c in cols_map if c in df.columns]].rename(columns=cols_map)
    display = display[display["Passes"] > 0].head(30)

    _STATUS_BADGE = {"Starting 11": "primary", "Sub On": "warning"}

    rows = []
    for i, (_, r) in enumerate(display.iterrows()):
        style = {"backgroundColor": "rgba(37,99,235,0.05)"} if i % 2 == 0 else {}
        cells = []
        for c in display.columns:
            val = r[c]
            if c == "Line-up":
                cells.append(html.Td(dbc.Badge(str(val), color=_STATUS_BADGE.get(str(val), "secondary"))))
            else:
                cells.append(html.Td(str(val)))
        rows.append(html.Tr(cells, style=style))

    title = "Single Match Lineup" if single_match else f"Season Summary ({len(selected_files)} matches)"
    return dbc.Card(dbc.CardBody([
        html.Small(title, className="text-muted d-block mb-2"),
        dbc.Table(
            [html.Thead(html.Tr([html.Th(c) for c in display.columns])),
             html.Tbody(rows)],
            striped=True, hover=True, responsive=True, size="sm",
            className="mb-0",
        ),
    ]))


@callback(
    Output("pa-player-section", "children"),
    Input("pa-competition", "value"),
    Input("pa-season", "value"),
    Input("pa-player", "value"),
    Input("pa-from-match", "value"),
    Input("pa-to-match", "value"),
)
def _player_deep_dive(competition, season, player_name, from_match, to_match):
    comp = competition or "LaLiga"
    seas = season or "2025-2026"

    if not player_name:
        return dbc.Alert("Select a player above to see their detailed stats.", color="info")

    selected_files = _selected_file_set(comp, seas, from_match, to_match)
    match_df = _get_player_match_series(comp, seas, player_name, selected_files=selected_files)
    if match_df.empty:
        return dbc.Alert(f"No data found for {player_name}.", color="warning")

    single_match = bool(selected_files) and len(selected_files) == 1
    fig_touch = _player_touch_heatmap(comp, seas, player_name, selected_files, single_match)

    result_colors = [
        _C["accent_green"]  if r == "W" else
        _C["accent_yellow"] if r == "D" else
        _C["accent_red"]
        for r in match_df["result"]
    ]

    # Passes per match bar
    fig_passes = go.Figure()
    fig_passes.add_trace(go.Bar(
        x=match_df["match"], y=match_df["passes"],
        marker_color=result_colors,
        name="Passes",
        text=match_df["passes"], textposition="auto",
    ))
    fig_passes.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Win (W)",
        marker=dict(size=9, color=_C["accent_green"]), hoverinfo="skip",
    ))
    fig_passes.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Draw (D)",
        marker=dict(size=9, color=_C["accent_yellow"]), hoverinfo="skip",
    ))
    fig_passes.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Loss (L)",
        marker=dict(size=9, color=_C["accent_red"]), hoverinfo="skip",
    ))
    fig_passes.update_layout(
        **_PL, height=_H_CHART,
        title=f"{player_name} — Passes Per Match",
        xaxis=dict(tickangle=-45, ticklabelstep=2, gridcolor=_C["border"], automargin=True),
        yaxis=dict(gridcolor=_C["border"], automargin=True),
        showlegend=True,
    )

    # Goals + xG per match scatter
    fig_goals = go.Figure()
    fig_goals.add_trace(go.Bar(
        x=match_df["match"], y=match_df["goals"],
        name="Goals", marker_color=_C["accent_green"],
    ))
    fig_goals.add_trace(go.Scatter(
        x=match_df["match"], y=match_df["xg"],
        name="xG", yaxis="y2",
        line=dict(color=_C["accent_orange"], width=2),
        mode="lines+markers", marker=dict(size=6),
    ))
    fig_goals.update_layout(
        **_PL, height=_H_CHART,
        title=f"{player_name} — Goals & xG Per Match",
        xaxis=dict(tickangle=-45, ticklabelstep=2, gridcolor=_C["border"], automargin=True),
        yaxis=dict(title="Goals", gridcolor=_C["border"], automargin=True),
        yaxis2=dict(title="xG", overlaying="y", side="right", showgrid=False, automargin=True),
    )

    # Radar chart — aggregate season totals
    agg = match_df[["passes", "shots", "goals", "tackles", "xg"]].sum()
    n_matches = len(match_df)
    per_game  = (agg / n_matches).round(2) if n_matches > 0 else agg

    categories  = ["Passes/G", "Shots/G", "Goals/G", "Tackles/G", "xG/G"]
    vals        = [
        per_game.get("passes", 0),
        per_game.get("shots",  0) * 10,   # scaled for radar
        per_game.get("goals",  0) * 50,
        per_game.get("tackles", 0) * 5,
        per_game.get("xg",     0) * 100,
    ]
    cats_closed = categories + [categories[0]]
    vals_closed = list(vals)  + [vals[0]]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=vals_closed, theta=cats_closed, fill="toself",
        line=dict(color=_RM), fillcolor="rgba(37,99,235,0.15)",
        name=player_name,
    ))
    fig_radar.update_layout(
        paper_bgcolor=_C["surface"],
        font=dict(color=_C["text_primary"], size=11),
        polar=dict(
            bgcolor=_C["surface"],
            radialaxis=dict(visible=True, gridcolor=_C["border"]),
            angularaxis=dict(gridcolor=_C["border"]),
        ),
        title=f"{player_name} — Per-Game Profile",
        height=_H_RADAR,
        margin=dict(l=40, r=40, t=50, b=40),
        showlegend=False,
    )

    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.Span("Touch Map", className="fw-bold me-2"),
                html.Span("Zoned touch distribution on the pitch (% of on-ball touches per zone)",
                          className="text-muted", style={"fontSize": "0.80rem"}),
            ]),
            dbc.CardBody(dcc.Graph(figure=fig_touch,
                                   config={"displayModeBar": False, "responsive": True}))
        ], className="mb-3"),
        dbc.Card([
            dbc.CardBody(dcc.Graph(figure=fig_radar,
                                   config={"displayModeBar": False, "responsive": True}))
        ], className="mb-3"),
        dbc.Card([
            dbc.CardBody(dcc.Graph(figure=fig_passes,
                                   config={"displayModeBar": False, "responsive": True}))
        ], className="mb-3"),
        dbc.Card([
            dbc.CardBody(dcc.Graph(figure=fig_goals,
                                   config={"displayModeBar": False, "responsive": True}))
        ], className="mb-3"),
    ])
