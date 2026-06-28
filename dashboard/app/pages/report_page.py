"""
Report Generator Page — Real Madrid Tactical Dashboard
Generates PDF/DOCX reports from live dashboard data.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc

# Add project root to sys.path so report_generator.py can be imported
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

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
    get_player_stats,
)

_C = COLOR_SCHEME


# ── Helpers ─────────────────────────────────────────────────────────────────

def _load_match(fp):
    data = load_match_json(fp)
    if not data:
        return None, None, None
    return data, extract_match_meta(data), parse_events(data)


def _scope_fps(mode, single_fp, competition, season, venue, from_fp, to_fp, multi_paths):
    comp   = competition or "LaLiga"
    seas   = season or "2025-2026"
    venue_ = venue or "All"
    if mode == "Multi":
        return [fp for fp in (multi_paths or []) if fp][:5]
    if mode == "Range":
        opts = get_match_options(comp, seas, venue_)
        if not opts:
            return []
        v2i = {o["value"]: i for i, o in enumerate(opts)}
        i0  = v2i.get(from_fp, 0)
        i1  = v2i.get(to_fp, len(opts) - 1)
        lo, hi = (i0, i1) if i0 <= i1 else (i1, i0)
        return [o["value"] for o in opts[lo:hi + 1]]
    return [single_fp] if single_fp else []


def _build_squad_df(all_ps: list[pd.DataFrame]) -> pd.DataFrame:
    if not all_ps:
        return pd.DataFrame()
    combined = pd.concat(all_ps, ignore_index=True)
    num_cols = [c for c in ["passes", "shots", "goals", "assists", "key_passes",
                             "tackles", "interceptions", "recoveries", "xg"]
                if c in combined.columns]
    agg = combined.groupby("player_name")[num_cols].sum().reset_index()
    agg["matches_played"] = combined.groupby("player_name").size().values
    return agg.sort_values("goals", ascending=False)


# ── Layout ──────────────────────────────────────────────────────────────────

def layout(competition="LaLiga", season="2025-2026"):
    comp_opts   = get_competition_options()
    season_opts = get_season_options(competition)
    match_opts  = get_match_options(competition, season, "All")

    first_fp = match_opts[0]["value"] if match_opts else None
    last_fp  = match_opts[-1]["value"] if match_opts else None

    return dbc.Container([
        dcc.Download(id="rg-download"),

        # Page header
        html.Div([
            html.H3("Report Generator", className="page-title mb-1"),
            html.P(
                "Build a branded PDF or DOCX report directly from match event data.",
                className="text-muted small mb-0",
            ),
        ], className="mb-4"),

        dbc.Row([
            # ── Left column: filters ─────────────────────────────────────────
            dbc.Col([
                # Data selection card
                dbc.Card(dbc.CardBody([
                    html.P("Data Selection", className="section-header mb-3"),

                    dbc.Row([
                        dbc.Col([
                            html.Label("Competition", className="filter-label"),
                            dcc.Dropdown(
                                id="rg-competition", options=comp_opts,
                                value=competition, clearable=False,
                            ),
                        ], md=4),
                        dbc.Col([
                            html.Label("Season", className="filter-label"),
                            dcc.Dropdown(
                                id="rg-season", options=season_opts,
                                value=season, clearable=False,
                            ),
                        ], md=4),
                        dbc.Col([
                            html.Label("Venue", className="filter-label"),
                            dcc.Dropdown(
                                id="rg-venue",
                                options=[
                                    {"label": "All Venues", "value": "All"},
                                    {"label": "Home Only",  "value": "Home"},
                                    {"label": "Away Only",  "value": "Away"},
                                ],
                                value="All", clearable=False,
                            ),
                        ], md=4),
                    ], className="g-2 mb-3"),

                    html.Label("Analysis Mode", className="filter-label mb-1"),
                    dcc.RadioItems(
                        id="rg-mode",
                        options=[
                            {"label": " Single Match",      "value": "Single"},
                            {"label": " Match Range",       "value": "Range"},
                            {"label": " Multi-Match (≤5)",  "value": "Multi"},
                        ],
                        value="Single",
                        inline=True,
                        className="mb-3",
                        inputClassName="me-1",
                        labelClassName="me-4 small",
                    ),

                    # Single match
                    html.Div([
                        html.Label("Match", className="filter-label"),
                        dcc.Dropdown(
                            id="rg-match-single", options=match_opts,
                            value=first_fp, clearable=False,
                        ),
                    ], id="rg-single-card", className="mb-2"),

                    # Range
                    html.Div([
                        dbc.Row([
                            dbc.Col([
                                html.Label("From", className="filter-label"),
                                dcc.Dropdown(
                                    id="rg-from-match", options=match_opts, value=first_fp,
                                ),
                            ], md=6),
                            dbc.Col([
                                html.Label("To", className="filter-label"),
                                dcc.Dropdown(
                                    id="rg-to-match", options=match_opts, value=last_fp,
                                ),
                            ], md=6),
                        ], className="g-2"),
                    ], id="rg-range-card", style={"display": "none"}, className="mb-2"),

                    # Multi
                    html.Div([
                        html.Label("Matches (up to 5)", className="filter-label"),
                        dcc.Dropdown(
                            id="rg-multi-select", options=match_opts,
                            value=[], multi=True,
                            placeholder="Pick up to 5 matches…",
                        ),
                        html.Div(id="rg-multi-warning", className="mt-1"),
                    ], id="rg-multi-card", style={"display": "none"}, className="mb-2"),

                    dcc.Store(id="rg-multi-paths-store", storage_type="memory", data=[]),
                ]), className="filter-section mb-3"),

                # Report options card
                dbc.Card(dbc.CardBody([
                    html.P("Report Options", className="section-header mb-3"),

                    html.Label(
                        "Players (optional — leave blank for squad summary)",
                        className="filter-label",
                    ),
                    dcc.Dropdown(
                        id="rg-players", options=[], value=[], multi=True,
                        placeholder="Select players to include…",
                        clearable=True, className="mb-3",
                    ),

                    html.Label("Output Format", className="filter-label mb-1"),
                    dcc.RadioItems(
                        id="rg-format",
                        options=[
                            {"label": " PDF  (recommended)", "value": "pdf"},
                            {"label": " DOCX",               "value": "docx"},
                        ],
                        value="pdf",
                        inline=True,
                        inputClassName="me-1",
                        labelClassName="me-4 small",
                        className="mb-3",
                    ),

                    dbc.Button(
                        "Generate & Download Report",
                        id="rg-generate-btn",
                        color="primary",
                        className="w-100",
                        n_clicks=0,
                    ),

                    html.Div(id="rg-status", className="mt-3"),
                ]), className="filter-section"),
            ], md=4),

            # ── Right column: contents preview ───────────────────────────────
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.P("Report Contents", className="section-header mb-3"),
                    dbc.ListGroup([
                        dbc.ListGroupItem([
                            html.Span("01", className="badge bg-primary me-2"),
                            html.Strong("Filter Summary"),
                            " — Competition, season, match selection",
                        ]),
                        dbc.ListGroupItem([
                            html.Span("02", className="badge bg-primary me-2"),
                            html.Strong("Executive Summary"),
                            " — W/D/L record, xG, possession, PPDA",
                        ]),
                        dbc.ListGroupItem([
                            html.Span("03", className="badge bg-primary me-2"),
                            html.Strong("Team Performance"),
                            " — Aggregate table + match-by-match breakdown",
                        ]),
                        dbc.ListGroupItem([
                            html.Span("04", className="badge bg-primary me-2"),
                            html.Strong("Player Performance"),
                            " — Goals, shots, passes, xG per selected player",
                        ]),
                        dbc.ListGroupItem([
                            html.Span("05", className="badge bg-primary me-2"),
                            html.Strong("Tactical Analysis"),
                            " — Pressing, position maps",
                        ]),
                        dbc.ListGroupItem([
                            html.Span("06", className="badge bg-primary me-2"),
                            html.Strong("Match Analysis"),
                            " — Shot maps, xG chart, pass network",
                        ]),
                        dbc.ListGroupItem([
                            html.Span("07", className="badge bg-primary me-2"),
                            html.Strong("Benchmarking"),
                            " — League comparisons",
                        ]),
                        dbc.ListGroupItem([
                            html.Span("08", className="badge bg-primary me-2"),
                            html.Strong("Visualisation Appendix"),
                            " — All captured charts",
                        ]),
                        dbc.ListGroupItem([
                            html.Span("✓", className="badge bg-success me-2"),
                            html.Strong("Conclusion"),
                            " — Pre / Match / Post-match evaluation",
                        ]),
                    ], flush=True, className="small"),
                ]), className="filter-section mb-3"),

                dbc.Card(dbc.CardBody([
                    html.P("How to Use", className="section-header mb-2"),
                    html.Ol([
                        html.Li("Choose Competition, Season and Venue."),
                        html.Li("Pick your Analysis Mode: Single, Range, or Multi-Match."),
                        html.Li("Select the match(es) you want in the report."),
                        html.Li("Optionally pick specific players for a player breakdown."),
                        html.Li("Choose PDF or DOCX, then click Generate."),
                        html.Li("The file downloads automatically when ready."),
                    ], className="small text-muted ps-3 mb-0"),
                ]), className="filter-section"),
            ], md=8),
        ]),
    ], fluid=True, className="py-3")


# ── Callbacks ───────────────────────────────────────────────────────────────

@callback(
    Output("rg-season", "options"),
    Output("rg-season", "value"),
    Input("rg-competition", "value"),
)
def _rg_season_opts(competition):
    from utils.data_helpers import get_available_seasons
    comp    = competition or "LaLiga"
    seasons = get_available_seasons(comp)
    options = [{"label": s, "value": s} for s in seasons]
    default = seasons[0] if seasons else "2025-2026"
    return options, default


@callback(
    Output("rg-match-single", "options"),
    Output("rg-match-single", "value"),
    Output("rg-from-match", "options"),
    Output("rg-from-match", "value"),
    Output("rg-to-match", "options"),
    Output("rg-to-match", "value"),
    Output("rg-multi-select", "options"),
    Input("rg-competition", "value"),
    Input("rg-season", "value"),
    Input("rg-venue", "value"),
)
def _rg_match_opts(competition, season, venue):
    opts  = get_match_options(
        competition or "LaLiga", season or "2025-2026", venue or "All"
    )
    first = opts[0]["value"] if opts else None
    last  = opts[-1]["value"] if opts else None
    return opts, first, opts, first, opts, last, opts


@callback(
    Output("rg-single-card", "style"),
    Output("rg-range-card",  "style"),
    Output("rg-multi-card",  "style"),
    Input("rg-mode", "value"),
)
def _rg_mode_visibility(mode):
    show = {"display": "block"}
    hide = {"display": "none"}
    if mode == "Range":
        return hide, show, hide
    if mode == "Multi":
        return hide, hide, show
    return show, hide, hide


@callback(
    Output("rg-multi-select", "value"),
    Output("rg-multi-warning", "children"),
    Input("rg-multi-select", "value"),
    prevent_initial_call=True,
)
def _rg_limit_multi(value):
    if not value:
        return [], None
    if len(value) > 5:
        return value[:5], dbc.Alert(
            "Maximum 5 matches allowed — trimmed to first 5.",
            color="warning", className="py-1 small",
        )
    return value, None


@callback(
    Output("rg-multi-paths-store", "data"),
    Input("rg-multi-select", "value"),
)
def _rg_update_multi_store(value):
    return value or []


@callback(
    Output("rg-players", "options"),
    Input("rg-mode", "value"),
    Input("rg-match-single", "value"),
    Input("rg-from-match", "value"),
    Input("rg-to-match", "value"),
    Input("rg-multi-paths-store", "data"),
    Input("rg-competition", "value"),
    Input("rg-season", "value"),
    Input("rg-venue", "value"),
)
def _rg_player_opts(mode, single_fp, from_fp, to_fp, multi_paths,
                    competition, season, venue):
    fps = _scope_fps(mode, single_fp, competition, season, venue,
                     from_fp, to_fp, multi_paths)
    names: set[str] = set()
    for fp in fps[:5]:
        _, meta, events = _load_match(fp)
        if meta is None or events is None or events.empty:
            continue
        ps = get_player_stats(events, meta["rm_id"])
        if not ps.empty and "player_name" in ps.columns:
            names.update(ps["player_name"].dropna().tolist())
    return [{"label": n, "value": n} for n in sorted(names)]


@callback(
    Output("rg-download", "data"),
    Output("rg-status", "children"),
    Input("rg-generate-btn", "n_clicks"),
    State("rg-mode", "value"),
    State("rg-match-single", "value"),
    State("rg-competition", "value"),
    State("rg-season", "value"),
    State("rg-venue", "value"),
    State("rg-from-match", "value"),
    State("rg-to-match", "value"),
    State("rg-multi-paths-store", "data"),
    State("rg-players", "value"),
    State("rg-format", "value"),
    prevent_initial_call=True,
)
def _rg_generate(n_clicks, mode, single_fp, competition, season, venue,
                 from_fp, to_fp, multi_paths, players, fmt):
    if not n_clicks:
        return dash.no_update, dash.no_update

    try:
        from report_generator import build_report_config, generate_pdf, generate_docx

        fps = _scope_fps(mode, single_fp, competition, season, venue,
                         from_fp, to_fp, multi_paths)
        if not fps:
            return dash.no_update, dbc.Alert(
                "No matches selected.", color="warning", dismissable=True,
            )

        match_records: list[dict]     = []
        all_ps:        list[pd.DataFrame] = []
        player_rows:   dict[str, list] = {p: [] for p in (players or [])}
        match_labels:  list[str]       = []

        for fp in fps:
            _, meta, events = _load_match(fp)
            if meta is None or events is None or events.empty:
                continue

            kpis = calc_match_kpis(events, meta)
            ps   = get_player_stats(events, meta["rm_id"])

            label = (
                f"MD{meta.get('week','?')} "
                f"{meta.get('home_team','?')} vs {meta.get('away_team','?')}"
            )
            match_labels.append(label)

            match_records.append({
                "meta": meta,
                "kpis": {
                    "xg_for":        kpis.get("xg_for", 0),
                    "xg_against":    kpis.get("xg_against", 0),
                    "possession":    kpis.get("possession", 0),
                    "pass_accuracy": kpis.get("pass_accuracy", 0),
                    "shots_total":   kpis.get("shots_total", 0),
                },
                "ppda":         kpis.get("ppda", 0),
                "player_stats": ps,
            })

            if not ps.empty:
                all_ps.append(ps)

            for pname in (players or []):
                row = ps[ps["player_name"] == pname]
                if row.empty:
                    continue
                d = row.iloc[0].to_dict()
                d["match"]  = label
                d["result"] = meta.get("result", "-")
                player_rows[pname].append(d)

        if not match_records:
            return dash.no_update, dbc.Alert(
                "No match data could be loaded for the selected filters.",
                color="danger", dismissable=True,
            )

        squad_df = _build_squad_df(all_ps)

        player_dfs = {
            pname: pd.DataFrame(rows)
            for pname, rows in player_rows.items()
            if rows
        }

        cfg = build_report_config(
            competition=competition or "LaLiga",
            season=season or "2025-2026",
            match_mode=mode,
            fps=fps,
            match_labels=match_labels,
            players=players or [],
            match_records=match_records,
            squad_df=squad_df,
            player_dfs=player_dfs,
            figures={},
        )

        ts = datetime.now().strftime("%Y%m%d_%H%M")
        if fmt == "docx":
            data_bytes = generate_docx(cfg)
            filename   = f"RealMadrid_Report_{ts}.docx"
        else:
            data_bytes = generate_pdf(cfg)
            filename   = f"RealMadrid_Report_{ts}.pdf"

        n = len(match_records)
        status = dbc.Alert(
            [html.Strong("Report ready! "),
             f"{n} match{'es' if n > 1 else ''} included. "
             f"Download: {filename}"],
            color="success", dismissable=True,
        )
        return dcc.send_bytes(data_bytes, filename), status

    except Exception as exc:
        import traceback
        return dash.no_update, dbc.Alert(
            [html.Strong("Error generating report: "), str(exc)],
            color="danger", dismissable=True,
        )
