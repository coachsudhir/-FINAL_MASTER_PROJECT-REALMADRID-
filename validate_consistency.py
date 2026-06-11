"""
Phase 4 — Data consistency: confirm dashboard aggregates trace back to raw events.
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "app"))
os.chdir(str(Path(__file__).parent / "app"))

import json
import pandas as pd
from utils.data_loader import (get_season_match_list, load_match_json, parse_events,
                               extract_match_meta, calc_match_kpis, calc_season_kpis)

COMP, SEASON = "LaLiga", "2024-2025"
matches = get_season_match_list(COMP, SEASON)
out = []

# 1) Match count consistency: season list vs raw RM files on disk
raw_rm = 0
from utils.data_loader import iter_match_files
for fp in iter_match_files(COMP, SEASON):
    d = load_match_json(str(fp))
    m = extract_match_meta(d)
    if "Real Madrid" in (m["home_team"] + m["away_team"]):
        raw_rm += 1
out.append(("Match count: season_list == raw RM files on disk",
            len(matches) == raw_rm, f"{len(matches)} vs {raw_rm}"))

# 2) Per-match: KPI shots == raw shot-type events; KPI passes == raw pass events;
#    KPI xG_for == sum of positional xg on RM shots; goals == raw goal events
shot_ok = pass_ok = xg_ok = goal_ok = poss_ok = 0
season_goals_for = 0
for m in matches:
    ev = parse_events(load_match_json(m["filepath"]))
    k = calc_match_kpis(ev, m)
    rm = ev[ev["contestant_id"] == m["rm_id"]]
    opp = ev[ev["contestant_id"] == m["opp_id"]]
    # raw counts
    raw_shots = int(rm["is_shot"].sum())
    raw_passes = int(rm["is_pass"].sum())
    raw_xg = round(float(rm[rm["is_shot"]]["xg"].dropna().sum()), 2)
    raw_goals = int(rm["is_goal"].sum())
    tot_pass = int(rm["is_pass"].sum()) + int(opp["is_pass"].sum())
    raw_poss = round(int(rm["is_pass"].sum()) / tot_pass * 100, 1) if tot_pass else 0
    shot_ok += (k["shots_total"] == raw_shots)
    pass_ok += (k["passes_total"] == raw_passes)
    xg_ok   += (abs(k["xg_for"] - raw_xg) < 0.01)
    goal_ok += (k["goals_scored"] == m["rm_score"])      # KPI uses meta score
    poss_ok += (abs(k["possession"] - raw_poss) < 0.01)
    season_goals_for += m["rm_score"]

N = len(matches)
out.append((f"Shots KPI == raw shot events ({N} matches)", shot_ok == N, f"{shot_ok}/{N}"))
out.append((f"Passes KPI == raw pass events ({N} matches)", pass_ok == N, f"{pass_ok}/{N}"))
out.append((f"xG_for KPI == sum positional xG ({N} matches)", xg_ok == N, f"{xg_ok}/{N}"))
out.append((f"Possession KPI == raw pass share ({N} matches)", poss_ok == N, f"{poss_ok}/{N}"))
out.append((f"Goals KPI == final score ({N} matches)", goal_ok == N, f"{goal_ok}/{N}"))

# 3) Season aggregation: calc_season_kpis goals == sum of per-match goals
sk = calc_season_kpis(COMP, SEASON)
out.append(("Season goals_scored == sum match scores",
            sk["goals_scored"] == season_goals_for, f"{sk['goals_scored']} vs {season_goals_for}"))
out.append(("Season played == match count",
            sk["played"] == N, f"{sk['played']} vs {N}"))
wdl = sk["wins"] + sk["draws"] + sk["losses"]
out.append(("Season W+D+L == played", wdl == sk["played"], f"{wdl} vs {sk['played']}"))

# 4) xG never null for shots, never present for non-shots
bad_xg = 0
for m in matches[:10]:
    ev = parse_events(load_match_json(m["filepath"]))
    shots = ev[ev["is_shot"]]
    nonshots = ev[~ev["is_shot"]]
    if shots["xg"].isna().any(): bad_xg += 1
    if nonshots["xg"].notna().any(): bad_xg += 1
out.append(("xG present iff shot (first 10 matches)", bad_xg == 0, f"violations={bad_xg}"))

lines = ["============ DATA CONSISTENCY ============"]
allpass = True
for desc, ok, detail in out:
    lines.append(f"{'PASS' if ok else 'FAIL'}  {desc:48s} [{detail}]")
    allpass = allpass and ok
lines.append(f"\n{'ALL CONSISTENT' if allpass else 'INCONSISTENCIES FOUND'}")
res = "\n".join(lines)
print(res)
Path("/tmp/consistency.txt").write_text(res)
