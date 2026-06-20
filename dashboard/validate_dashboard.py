"""
End-to-end dashboard visual validator — runs every figure/table callback against
REAL data across many matches/seasons and reports blank/empty/error visuals.
"""
import sys, os, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "app"))
os.chdir(str(Path(__file__).parent / "app"))

import plotly.graph_objects as go

from utils.data_helpers import get_match_options
from utils.data_loader import get_season_match_list, get_available_competitions, get_competition_seasons

import pages.home as home
import pages.match_analysis as ma
import pages.player_analysis as pa
import pages.tactical_phases as tp
import pages.opponent_analysis as oa
import pages.benchmarking as bm

results = []   # (name, status, ntraces, npoints, note)

def fig_points(fig):
    if not isinstance(fig, go.Figure):
        try: fig = go.Figure(fig)
        except Exception: return -1, -1
    n_tr = len(fig.data); pts = 0
    for tr in fig.data:
        for attr in ("x", "y", "z", "values", "labels", "lat", "lon"):
            v = getattr(tr, attr, None)
            if v is not None:
                try: pts += len(v)
                except TypeError: pts += 1
                break
    return n_tr, pts

def no_data_anno(fig):
    if not isinstance(fig, go.Figure):
        try: fig = go.Figure(fig)
        except Exception: return False
    for a in fig.layout.annotations or []:
        t = (a.text or "").lower()
        if any(k in t for k in ["no ", "select", "insufficient", "not available", "unavailable", "no shot", "no data"]):
            return True
    return False

def check_fig(name, fn, *args):
    try:
        fig = fn(*args)
    except Exception as e:
        results.append((name, "ERROR", 0, 0, f"{type(e).__name__}: {e}"))
        traceback.print_exc(); return
    figs = fig if isinstance(fig, tuple) else (fig,)
    for i, f in enumerate(figs):
        nm = name if len(figs) == 1 else f"{name}[{i}]"
        n_tr, pts = fig_points(f)
        blank = (pts <= 0)
        note = "shows 'no data' annotation" if (blank and no_data_anno(f)) else ""
        results.append((nm, "BLANK" if blank else "PASS", n_tr, pts, note))

def check_children(name, fn, *args):
    try:
        out = fn(*args)
    except Exception as e:
        results.append((name, "ERROR", 0, 0, f"{type(e).__name__}: {e}"))
        traceback.print_exc(); return
    outs = out if isinstance(out, tuple) else (out,)
    for i, o in enumerate(outs):
        nm = name if len(outs) == 1 else f"{name}[{i}]"
        empty = o is None or (isinstance(o, (list, str)) and len(o) == 0)
        results.append((nm, "BLANK" if empty else "PASS", 0, 0, ""))

# Iterate over a representative set: each competition's largest season + a small comp
SCOPES = [("LaLiga","2024-2025"), ("LaLiga","2025-2026"),
          ("Champions League","2024-2025"), ("Copa del Rey","2024-2025")]

for COMP, SEASON in SCOPES:
    opts = get_match_options(COMP, SEASON, "All")
    if not opts:
        results.append((f"[{COMP} {SEASON}] match options", "BLANK", 0, 0, "no matches")); continue
    matches = get_season_match_list(COMP, SEASON)
    tag = f"{COMP[:4]}/{SEASON[2:4]}"
    # test up to 3 matches in this scope (first, mid, last)
    idxs = sorted(set([0, len(opts)//2, len(opts)-1]))
    for k in idxs:
        FILE = opts[k]["value"]
        FROM = opts[0]["value"]; TO = opts[min(4,len(opts)-1)]["value"]
        mtag = f"{tag} m{k}"
        S = (FILE, COMP, SEASON, "All", FROM, TO)
        # MATCH ANALYSIS - single
        for nm, idn in [("ma-shot-map","_shot_map"),("ma-xg-chart","_xg_chart"),
                        ("ma-tactical-bars","_tactical_bars"),("ma-pass-map","_pass_map"),
                        ("ma-pass-network","_pass_network"),("ma-shot-zone-map","_shot_zone_map"),
                        ("ma-subphase-chart","_subphase_chart")]:
            check_fig(f"{mtag} {nm}", getattr(ma,idn), "Single", *S)
        check_fig(f"{mtag} ma-lineup-pitch", ma._lineup_pitch, "Single", FILE)
        check_fig(f"{mtag} ma-transition-chart", ma._transition_chart, FILE, "all")
        check_fig(f"{mtag} ma-setpiece-chart", ma._setpiece_chart, FILE, "all")
        check_children(f"{mtag} ma-player-table", ma._player_table, "Single", FILE, "All", COMP, SEASON, "All", FROM, TO)
        check_children(f"{mtag} ma-header/kpi", ma._update_header, "Single", FILE, COMP, SEASON, "All", FROM, TO)
        check_children(f"{mtag} ma-post-summary", ma._post_match_summary, FILE, "all")
        # OPPONENT ANALYSIS
        check_fig(f"{mtag} oa-shot-map", oa._shot_map, FILE)
        check_fig(f"{mtag} oa-lineup-pitch", oa._lineup_pitch, FILE)
        check_fig(f"{mtag} oa-threat-chart", oa._threat_chart, FILE)
        check_children(f"{mtag} oa-player-table", oa._player_table, FILE)
        check_children(f"{mtag} oa-scouting", oa._scouting_blocks, FILE, COMP, SEASON)
        # TACTICAL PHASES (per match)
        check_fig(f"{mtag} tp-press-map", tp._press_map, FILE)
        check_fig(f"{mtag} tp-recovery-map", tp._recovery_map, FILE)
        check_children(f"{mtag} tp-phase-panel", tp._phase_panel, FILE, "A")

    # SEASON-LEVEL visuals (once per scope)
    check_fig(f"{tag} home-goals-trend", home._goals_trend, COMP, SEASON)
    check_fig(f"{tag} home-shots-trend", home._shots_trend, COMP, SEASON)
    check_children(f"{tag} home-results-table", home._results_table, COMP, SEASON)
    check_fig(f"{tag} tp-ppda-trend", tp._ppda_trend, COMP, SEASON)
    check_fig(f"{tag} tp-tilt-chart", tp._tilt_chart, COMP, SEASON)
    check_children(f"{tag} pa-squad-table", pa._squad_table, COMP, SEASON, "All", "All", 0, opts[0]["value"], opts[-1]["value"])
    # player deep dive — pick first player from squad
    df = pa._build_season_player_stats(COMP, SEASON)
    if not df.empty:
        pname = df.iloc[0]["player_name"]
        check_children(f"{tag} pa-player-section", pa._player_deep_dive, COMP, SEASON, pname, opts[0]["value"], opts[-1]["value"])
    # BENCHMARKING
    comps_input = [COMP]
    check_children(f"{tag} bm-summary-table", bm._summary_table, comps_input)
    check_fig(f"{tag} bm-goals-chart", bm._goals_chart, comps_input)
    check_fig(f"{tag} bm-win-chart", bm._win_chart, comps_input)
    check_fig(f"{tag} bm-xg-chart", bm._xg_chart, comps_input)
    check_fig(f"{tag} bm-pass-chart", bm._pass_chart, comps_input)
    # rivals (need rival ids)
    rv = bm._rivals_options(COMP, SEASON)
    rival_vals = [o["value"] for o in (rv or [])[:2]]
    check_fig(f"{tag} bm-rivals/style/phase", bm._rival_comparison, COMP, SEASON, rival_vals, opts[0]["value"], opts[-1]["value"])

lines = ["================ VALIDATION RESULTS ================"]
n_pass = n_blank = n_err = 0
for name, status, ntr, pts, note in results:
    if status == "PASS": n_pass += 1; continue
    mark = "!!" if status == "BLANK" else "XX"
    lines.append(f"{mark} {name:38s} {status:6s} traces={ntr:3d} pts={pts:5d} {note}")
    if status == "BLANK": n_blank += 1
    else: n_err += 1
lines.append(f"\nTOTAL: {len(results)} checks | PASS={n_pass} BLANK={n_blank} ERROR={n_err}")
out = "\n".join(lines)
print(out)
Path("/tmp/valresult.txt").write_text(out)
