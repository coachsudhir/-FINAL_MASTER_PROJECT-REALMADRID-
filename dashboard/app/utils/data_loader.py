"""
data_loader.py — Core data pipeline for the Real Madrid Tactical Dashboard.

Parses Opta Stats Perform JSON match files from the raw partidos/ folders.

Confirmed Opta typeId mapping (from data inspection):
    1  = Pass              3  = Take On / Dribble   4  = Foul
    5  = Offside           6  = Corner Awarded       7  = Tackle
    8  = Interception     10  = GK Save             13  = Shot On Target
 15  = Shot Blocked     16  = Goal                17  = Card
 18  = Player Off       19  = Player On           49  = Ball Recovery
 65  = Yellow Card      68  = Red Card

Confirmed Qualifier IDs:
  140 = pass end_x    141 = pass end_y
  395 = post-shot quality (unreliable — only on goals, bimodal values; replaced by positional model)
  396 = xGOT proxy (0-100)   103 = event travel distance (not shot-to-goal)   56 = zone label
"""

import json
import logging
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Opta type-id maps
# ---------------------------------------------------------------------------
GOAL_TYPES       = {16}
SHOT_ON_TARGET   = {13, 16}     # attempt saved + goal
SHOT_BLOCKED     = {15}
ALL_SHOT_TYPES   = {13, 15, 16}
PASS_TYPES       = {1, 2}
TACKLE_TYPES     = {7}
INTERCEPTION_T   = {8}
RECOVERY_TYPES   = {49}
DRIBBLE_TYPES    = {3}
FOUL_TYPES       = {4}
YELLOW_CARD      = {65}
RED_CARD         = {68}

# Competition folder name mapping
COMP_FOLDER = {
    "LaLiga":          "LaLiga",
    "Copa del Rey":    "Copa del Rey",
    "Champions League": "UEFA Champions League",
}


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

# Share one single source of truth with config.py so every dashboard module
# resolves the same clean, verified bundle (dashboard/data). The fallback below
# is only used if config can't be imported; it mirrors config's resolution and
# deliberately avoids the corrupt raw root folders and any machine-specific path.
try:
    from config import DATA_ROOT
except ImportError:
    def _data_root() -> Path:
        import os
        env = os.getenv("DATA_ROOT")
        if env and Path(env).exists():
            return Path(env)
        here = Path(__file__).resolve()
        candidates = [
            here.parent.parent.parent / "data",          # dashboard/data (canonical bundle)
            here.parent.parent.parent.parent / "data",   # <repo-root>/data (deploy fallback)
            Path.cwd() / "data",
        ]
        for p in candidates:
            if (p / "LaLiga").exists() or (p / "Copa del Rey").exists() or (p / "UEFA Champions League").exists():
                return p
        return Path(".")
    DATA_ROOT = _data_root()


def get_competition_seasons(competition: str) -> list[str]:
    """Return available season folders for a competition, newest first."""
    folder = COMP_FOLDER.get(competition, competition)
    base = DATA_ROOT / folder
    if not base.exists():
        return []
    seasons = sorted(
        [d.name for d in base.iterdir() if d.is_dir() and "-" in d.name],
        reverse=True,
    )
    return seasons


def get_available_competitions() -> list[str]:
    """Return competitions that have data on disk."""
    comps = []
    for name, folder in COMP_FOLDER.items():
        if (DATA_ROOT / folder).exists():
            comps.append(name)
    return comps or ["LaLiga"]


def iter_match_files(competition: str, season: str):
    """Yield Path objects for all JSON files in partidos/."""
    folder = COMP_FOLDER.get(competition, competition)
    partidos = DATA_ROOT / folder / season / "partidos"
    if not partidos.exists():
        return
    yield from sorted(partidos.glob("*.json"))


# ---------------------------------------------------------------------------
# Single-match loading
# ---------------------------------------------------------------------------

@lru_cache(maxsize=200)
def load_match_json(filepath: str) -> dict:
    """Load and cache a single match JSON file."""
    try:
        return json.loads(Path(filepath).read_bytes())
    except Exception as e:
        logger.warning("Failed to load %s: %s", filepath, e)
        return {}


def _get_qualifier(qualifiers: list, qid: int, default=None):
    """Extract a qualifier value by ID from an event's qualifier list."""
    for q in qualifiers:
        if q.get("qualifierId") == qid:
            return q.get("value", default)
    return default


def _has_qualifier(qualifiers: list, qid: int) -> bool:
    return any(q.get("qualifierId") == qid for q in qualifiers)


def _has_any_qualifier(qualifiers: list, qids: set[int]) -> bool:
    return any(q.get("qualifierId") in qids for q in qualifiers)


def _safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_penalty_spot(x: float, y: float) -> bool:
    """Opta standardises the penalty spot to exactly (88.5, 50.0).
    A tight tolerance of ±0.2 units catches all standardised coordinates
    while excluding open-play shots near the penalty area.
    """
    return abs(x - 88.5) < 0.2 and abs(y - 50.0) < 0.2


def _compute_shot_xg(x: float, y: float) -> float:
    """
    Positional xG model using shot coordinates (Opta 0-100 units).

    Penalty kicks are detected by coordinate (Opta standardises to x=88.5, y=50.0)
    and assigned xG = 0.76 (empirical penalty conversion rate).

    Open-play shots use a calibrated logistic model (distance in metres, angle in radians):
        logit(xG) = -3.785 - 0.0337*dist_m + 3.64*angle_rad
    Anchors (open play, central): 6 m → ~0.50 | 11 m → ~0.14 |
             edge of box 16.5 m → ~0.06 | long shot 25 m → ~0.027.

    Opta pitch: x=0..100 (≈105 m), y=0..100 (≈68 m).
    Attacking goal: x=100, y=50 (goal mouth y=45.2..54.8 → half-width 3.66 m).
    """
    if _is_penalty_spot(x, y):
        return 0.76

    dx_m = (100.0 - x) * 1.05   # metres along pitch
    dy_m = (y - 50.0) * 0.68    # metres lateral offset from goal centre

    if dx_m <= 0:                # shot behind or on the goal line
        return 0.01

    dist_m = math.sqrt(dx_m ** 2 + dy_m ** 2)
    goal_hw = 3.66               # goal half-width in metres

    # Angle (radians) subtended by the goal mouth at the shot position
    angle_rad = abs(
        math.atan2(dy_m - goal_hw, dx_m) - math.atan2(dy_m + goal_hw, dx_m)
    )

    logit = -3.785 - 0.0337 * dist_m + 3.64 * angle_rad
    xg = 1.0 / (1.0 + math.exp(-logit))
    return round(max(0.01, min(0.99, xg)), 3)


# ---------------------------------------------------------------------------
# Match metadata extraction
# ---------------------------------------------------------------------------

def extract_match_meta(data: dict) -> dict:
    """Extract flat metadata dict from raw match JSON."""
    mi = data.get("matchInfo", {})
    ld = data.get("liveData", {})
    details = ld.get("matchDetails", {})
    contestants = mi.get("contestant", [])

    home_obj = next((c for c in contestants if c.get("position") == "home"), {})
    away_obj = next((c for c in contestants if c.get("position") == "away"), {})
    home = home_obj.get("name", "?")
    away = away_obj.get("name", "?")
    home_id = home_obj.get("id", "")
    away_id = away_obj.get("id", "")

    scores = details.get("scores", {})
    ft = scores.get("ft", scores.get("total", {}))
    ht = scores.get("ht", {})

    venue_obj = mi.get("venue", {})
    competition_obj = mi.get("competition", {})
    stage_obj = mi.get("stage", {})

    is_rm_home = "Real Madrid" in home
    rm_id = home_id if is_rm_home else away_id
    opp_id = away_id if is_rm_home else home_id
    opponent = away if is_rm_home else home

    rm_score  = ft.get("home", 0) if is_rm_home else ft.get("away", 0)
    opp_score = ft.get("away", 0) if is_rm_home else ft.get("home", 0)

    if rm_score > opp_score:
        result = "W"
    elif rm_score == opp_score:
        result = "D"
    else:
        result = "L"

    return {
        "match_id":    mi.get("id", ""),
        "date":        mi.get("date", "")[:10],
        "time":        mi.get("time", ""),
        "week":        mi.get("week", ""),
        "description": mi.get("description", f"{home} vs {away}"),
        "competition": competition_obj.get("name", ""),
        "stage":       stage_obj.get("name", ""),
        "venue_name":  venue_obj.get("name", ""),
        "home_team":   home,
        "away_team":   away,
        "home_id":     home_id,
        "away_id":     away_id,
        "rm_id":       rm_id,
        "opp_id":      opp_id,
        "opponent":    opponent,
        "is_rm_home":  is_rm_home,
        "rm_score":    rm_score,
        "opp_score":   opp_score,
        "result":      result,
        "score_str":   f"{ft.get('home',0)}-{ft.get('away',0)}",
        "ht_score":    f"{ht.get('home','-')}-{ht.get('away','-')}",
        "match_status": details.get("matchStatus", ""),
    }


# ---------------------------------------------------------------------------
# Event normalisation
# ---------------------------------------------------------------------------

def parse_events(data: dict) -> pd.DataFrame:
    """
    Convert raw event list to a clean DataFrame.

    Columns:
      event_id, type_id, event_type, period, minute, second,
      contestant_id, player_id, player_name,
      x, y, end_x, end_y,
      outcome, is_goal, is_shot, is_pass, is_tackle, is_recovery,
      xg, xgot, distance, zone, pass_direction,
      is_key_pass, is_assist, timestamp
    """
    mi = data.get("matchInfo", {})
    contestants = mi.get("contestant", [])
    raw_events = data.get("liveData", {}).get("event", [])

    # Build team name lookup
    id_to_name = {c["id"]: c.get("name", "") for c in contestants if "id" in c}

    rows = []
    for ev in raw_events:
        tid = ev.get("typeId", 0)
        quals = ev.get("qualifier", [])

        xgot_raw = _get_qualifier(quals, 396)
        xgot = (_safe_float(xgot_raw) / 100.0) if xgot_raw is not None else None

        distance_raw = _get_qualifier(quals, 103)
        distance = _safe_float(distance_raw)

        end_x_raw = _get_qualifier(quals, 140)
        end_y_raw = _get_qualifier(quals, 141)
        end_x = _safe_float(end_x_raw)
        end_y = _safe_float(end_y_raw)

        x_pos = _safe_float(ev.get("x"), 0.0)
        y_pos = _safe_float(ev.get("y"), 0.0)

        is_shot_event = tid in ALL_SHOT_TYPES or _has_any_qualifier(quals, {102, 103})
        is_pen = is_shot_event and _is_penalty_spot(x_pos, y_pos)
        # Use calibrated positional xG model for all shot events.
        # Penalty kicks detected by coordinate (Opta: 88.5, 50.0) → xG = 0.76.
        # Qualifier 395 excluded: only covers ~11% of shots (goals only).
        xg_value = _compute_shot_xg(x_pos, y_pos) if is_shot_event else None

        cid = ev.get("contestantId", "")
        rows.append({
            "event_id":     ev.get("eventId", 0),
            "type_id":      tid,
            "event_type":   _type_label(tid),
            "period":       ev.get("periodId", 0),
            "minute":       ev.get("timeMin", 0),
            "second":       ev.get("timeSec", 0),
            "contestant_id": cid,
            "team_name":    id_to_name.get(cid, ""),
            "player_id":    ev.get("playerId", ""),
            "player_name":  ev.get("playerName", ""),
            "x":            x_pos,
            "y":            y_pos,
            "end_x":        end_x,
            "end_y":        end_y,
            "outcome":      ev.get("outcome", 0),
            "is_goal":      tid in GOAL_TYPES,
            "is_shot":      is_shot_event,
            "is_penalty":   is_pen,
            "is_shot_on_target": tid in SHOT_ON_TARGET,
            "is_pass":      tid in PASS_TYPES,
            "is_tackle":    tid in TACKLE_TYPES,
            "is_interception": tid in INTERCEPTION_T,
            "is_recovery":  tid in RECOVERY_TYPES,
            "is_dribble":   tid in DRIBBLE_TYPES,
            "is_foul":      tid in FOUL_TYPES,
            "is_key_pass":  ev.get("keyPass", False),
            "is_assist":    bool(ev.get("assist")),
            "xg":           xg_value,
            "xgot":         xgot,
            "distance":     distance,
            "zone":         _get_qualifier(quals, 56),
            "pass_direction": _get_qualifier(quals, 279),
            "timestamp":    ev.get("timeStamp", ""),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Filter out setup / bookkeeping events (period starts, formations)
    setup_types = {27, 28, 30, 32, 34}
    df = df[~df["type_id"].isin(setup_types)].copy()

    return df


def _type_label(tid: int) -> str:
    LABELS = {
        1: "Pass", 2: "Offside Pass", 3: "Take On", 4: "Foul",
        5: "Offside", 6: "Corner Awarded", 7: "Tackle", 8: "Interception",
        10: "GK Save", 13: "Shot On Target",
        15: "Shot Blocked", 16: "Goal", 17: "Card", 18: "Player Off",
        19: "Player On", 37: "Aerial", 44: "Touch", 49: "Ball Recovery",
        65: "Yellow Card", 68: "Red Card",
    }
    return LABELS.get(tid, f"Event {tid}")


# ---------------------------------------------------------------------------
# KPI calculation from events
# ---------------------------------------------------------------------------

def calc_match_kpis(events: pd.DataFrame, meta: dict) -> dict:
    """Compute standard match KPIs from normalised events."""
    if events.empty:
        return _empty_kpis()

    rm_id  = meta["rm_id"]
    opp_id = meta["opp_id"]

    rm_ev  = events[events["contestant_id"] == rm_id]
    opp_ev = events[events["contestant_id"] == opp_id]

    rm_shots   = rm_ev[rm_ev["is_shot"]]
    opp_shots  = opp_ev[opp_ev["is_shot"]]
    rm_passes  = rm_ev[rm_ev["is_pass"]]
    opp_passes = opp_ev[opp_ev["is_pass"]]

    total_passes = len(rm_passes) + len(opp_passes)
    possession   = round(len(rm_passes) / total_passes * 100, 1) if total_passes else 0

    pass_acc = 0.0
    if len(rm_passes) > 0:
        pass_acc = round(rm_passes["outcome"].mean() * 100, 1)

    rm_xg  = rm_ev["xg"].dropna().sum()
    opp_xg = opp_ev["xg"].dropna().sum()

    # PPDA = opponent passes allowed in defensive third / RM pressures
    # Simplified: opponent passes in RM's defensive half / RM defensive actions
    rm_def_actions = len(rm_ev[rm_ev["type_id"].isin({7, 8, 49})]) or 1
    opp_passes_att_third = len(opp_ev[(opp_ev["is_pass"]) & (opp_ev["x"] >= 40)])
    ppda = round(opp_passes_att_third / rm_def_actions, 2)

    return {
        "goals_scored":       meta["rm_score"],
        "goals_conceded":     meta["opp_score"],
        "result":             meta["result"],
        "score":              meta["score_str"],
        "possession":         possession,
        "shots_total":        len(rm_shots),
        "shots_on_target":    len(rm_ev[rm_ev["is_shot_on_target"]]),
        "xg_for":             round(rm_xg, 2),
        "xg_against":         round(opp_xg, 2),
        "passes_total":       len(rm_passes),
        "pass_accuracy":      pass_acc,
        "tackles":            len(rm_ev[rm_ev["is_tackle"]]),
        "interceptions":      len(rm_ev[rm_ev["is_interception"]]),
        "ball_recoveries":    len(rm_ev[rm_ev["is_recovery"]]),
        "corners":            len(rm_ev[rm_ev["type_id"] == 6]),
        "fouls_committed":    len(rm_ev[rm_ev["is_foul"]]),
        "yellow_cards":       len(rm_ev[rm_ev["type_id"] == 65]),
        "red_cards":          len(rm_ev[rm_ev["type_id"] == 68]),
        "ppda":               ppda,
        "opponent":           meta["opponent"],
        "opponent_shots":     len(opp_shots),
        "opp_shots_on_target": len(opp_ev[opp_ev["is_shot_on_target"]]),
    }


def _empty_kpis() -> dict:
    return {k: 0 for k in [
        "goals_scored", "goals_conceded", "possession", "shots_total",
        "shots_on_target", "xg_for", "xg_against", "passes_total",
        "pass_accuracy", "tackles", "interceptions", "ball_recoveries",
        "corners", "fouls_committed", "yellow_cards", "red_cards", "ppda",
        "opponent_shots", "opp_shots_on_target",
    ]} | {"result": "-", "score": "0-0", "opponent": ""}


# ---------------------------------------------------------------------------
# Player-level stats
# ---------------------------------------------------------------------------

def get_player_stats(events: pd.DataFrame, team_id: str) -> pd.DataFrame:
    """Per-player summary for a given team."""
    if events.empty:
        return pd.DataFrame()

    tm = events[events["contestant_id"] == team_id]
    if tm.empty:
        return pd.DataFrame()

    grp = tm.groupby(["player_id", "player_name"])

    stats = grp.agg(
        minutes_played  = ("minute", "max"),
        passes          = ("is_pass", "sum"),
        pass_acc        = ("outcome", lambda s: round(s[tm.loc[s.index, "is_pass"]].mean() * 100, 1) if s[tm.loc[s.index, "is_pass"]].any() else 0),
        shots           = ("is_shot", "sum"),
        shots_on_target = ("is_shot_on_target", "sum"),
        goals           = ("is_goal", "sum"),
        key_passes      = ("is_key_pass", "sum"),
        assists         = ("is_assist", "sum"),
        tackles         = ("is_tackle", "sum"),
        interceptions   = ("is_interception", "sum"),
        recoveries      = ("is_recovery", "sum"),
        dribbles        = ("is_dribble", "sum"),
        xg              = ("xg", "sum"),
        fouls           = ("is_foul", "sum"),
    ).reset_index()

    stats["xg"] = stats["xg"].round(2)
    return stats.sort_values("passes", ascending=False)


def get_match_lineup_status(events: pd.DataFrame, team_id: str) -> dict[str, str]:
    """
    Returns {player_name: "Starting 11" | "Sub On"} for a single match.
    typeId=19 in Opta = Substitution On (player coming on).
    All other RM players with events are considered starters.
    """
    if events.empty:
        return {}
    tm = events[events["contestant_id"] == team_id]
    sub_on = set(tm[tm["type_id"] == 19]["player_name"].dropna().tolist()) - {""}
    all_players = set(tm["player_name"].dropna().tolist()) - {""}
    return {p: ("Sub On" if p in sub_on else "Starting 11") for p in all_players}


# ---------------------------------------------------------------------------
# Season aggregation — scans all RM matches in a season
# ---------------------------------------------------------------------------

@lru_cache(maxsize=20)
def get_season_match_list(competition: str, season: str) -> list[dict]:
    """
    Return list of match meta dicts for all RM matches in a season.
    Cached per competition+season.
    """
    results = []
    for fp in iter_match_files(competition, season):
        data = load_match_json(str(fp))
        if not data:
            continue
        meta = extract_match_meta(data)
        if "Real Madrid" not in (meta["home_team"] + meta["away_team"]):
            continue
        meta["filepath"] = str(fp)
        results.append(meta)

    # Sort by matchday / date
    results.sort(key=lambda m: (str(m.get("week", "0")).zfill(3), m.get("date", "")))
    return results


def calc_season_kpis(competition: str, season: str) -> dict:
    """Aggregate KPIs across all RM matches in a season."""
    matches = get_season_match_list(competition, season)
    if not matches:
        return _empty_season_kpis()

    totals = dict(
        played=0, wins=0, draws=0, losses=0,
        goals_scored=0, goals_conceded=0,
        shots=0, shots_on_target=0,
        passes=0, pass_acc_sum=0, possession_sum=0,
        tackles=0, recoveries=0,
        xg_for=0.0, xg_against=0.0,
    )

    for m in matches:
        try:
            data   = load_match_json(m["filepath"])
            events = parse_events(data)
            kpis   = calc_match_kpis(events, m)
        except Exception as e:
            logger.warning("KPI error %s: %s", m.get("filepath"), e)
            continue

        totals["played"]         += 1
        totals["wins"]           += 1 if m["result"] == "W" else 0
        totals["draws"]          += 1 if m["result"] == "D" else 0
        totals["losses"]         += 1 if m["result"] == "L" else 0
        totals["goals_scored"]   += kpis["goals_scored"]
        totals["goals_conceded"] += kpis["goals_conceded"]
        totals["shots"]          += kpis["shots_total"]
        totals["shots_on_target"]+= kpis["shots_on_target"]
        totals["passes"]         += kpis["passes_total"]
        totals["pass_acc_sum"]   += kpis["pass_accuracy"]
        totals["possession_sum"] += kpis["possession"]
        totals["tackles"]        += kpis["tackles"]
        totals["recoveries"]     += kpis["ball_recoveries"]
        totals["xg_for"]         += kpis["xg_for"]
        totals["xg_against"]     += kpis["xg_against"]

    n = totals["played"] or 1
    return {
        "played":           totals["played"],
        "wins":             totals["wins"],
        "draws":            totals["draws"],
        "losses":           totals["losses"],
        "win_pct":          round(totals["wins"] / n * 100, 1),
        "goals_scored":     totals["goals_scored"],
        "goals_conceded":   totals["goals_conceded"],
        "goal_diff":        totals["goals_scored"] - totals["goals_conceded"],
        "goals_per_game":   round(totals["goals_scored"] / n, 2),
        "conceded_per_game": round(totals["goals_conceded"] / n, 2),
        "shots_total":      totals["shots"],
        "shots_on_target":  totals["shots_on_target"],
        "avg_possession":   round(totals["possession_sum"] / n, 1),
        "avg_pass_acc":     round(totals["pass_acc_sum"] / n, 1),
        "xg_for":           round(totals["xg_for"], 2),
        "xg_against":       round(totals["xg_against"], 2),
        "xg_diff":          round(totals["xg_for"] - totals["xg_against"], 2),
    }


def _empty_season_kpis() -> dict:
    return {k: 0 for k in [
        "played", "wins", "draws", "losses", "win_pct",
        "goals_scored", "goals_conceded", "goal_diff",
        "goals_per_game", "conceded_per_game",
        "shots_total", "shots_on_target",
        "avg_possession", "avg_pass_acc",
        "xg_for", "xg_against", "xg_diff",
    ]}


def get_season_results_table(competition: str, season: str) -> pd.DataFrame:
    """Return a DataFrame of match results for display."""
    matches = get_season_match_list(competition, season)
    rows = []
    for m in matches:
        venue = "H" if m["is_rm_home"] else "A"
        result_color = {"W": "green", "D": "orange", "L": "red"}.get(m["result"], "grey")
        rows.append({
            "MD":       m.get("week", ""),
            "Date":     m.get("date", ""),
            "Venue":    venue,
            "Opponent": m["opponent"],
            "Score":    m["score_str"],
            "Result":   m["result"],
            "_color":   result_color,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Shot-map data (for pitch visualisation)
# ---------------------------------------------------------------------------

def get_shot_data(events: pd.DataFrame, meta: dict) -> pd.DataFrame:
    """Return shot events enriched with team context."""
    if events.empty:
        return pd.DataFrame()

    shots = events[events["is_shot"]].copy()
    if shots.empty:
        return shots

    shots["team_label"] = shots["contestant_id"].map({
        meta["rm_id"]:  "Real Madrid",
        meta["opp_id"]: meta["opponent"],
    }).fillna("Other")
    shots["xg_display"] = shots["xg"].round(3)  # positional xG, always present for shots
    return shots


# ---------------------------------------------------------------------------
# Pass-network data
# ---------------------------------------------------------------------------

def get_pass_network(events: pd.DataFrame, team_id: str, min_passes: int = 3) -> dict:
    """
    Return nodes (players) and edges (passes between players) for a pass network.
    Only includes passes with end coordinates.
    """
    if events.empty:
        return {"nodes": pd.DataFrame(), "edges": pd.DataFrame()}

    passes = events[
        (events["contestant_id"] == team_id) &
        (events["is_pass"]) &
        (events["end_x"].notna()) &
        (events["outcome"] == 1)   # successful passes only
    ].copy()

    if passes.empty:
        return {"nodes": pd.DataFrame(), "edges": pd.DataFrame()}

    # Average position per player
    nodes = passes.groupby(["player_id", "player_name"]).agg(
        x=("x", "mean"), y=("y", "mean"), n_passes=("is_pass", "count")
    ).reset_index()

    return {"nodes": nodes, "edges": pd.DataFrame()}


# ---------------------------------------------------------------------------
# Tactical metrics
# ---------------------------------------------------------------------------

def calc_ppda(events: pd.DataFrame, meta: dict) -> float:
    """
    PPDA = Passes Allowed Per Defensive Action.
    Opponent passes in attacking half / RM defensive actions in attacking half.
    Lower = more intense press.
    """
    if events.empty:
        return 0.0

    opp_id = meta["opp_id"]
    rm_id  = meta["rm_id"]

    opp_passes_att = events[
        (events["contestant_id"] == opp_id) &
        (events["is_pass"]) &
        (events["x"] >= 40)
    ]
    rm_def = events[
        (events["contestant_id"] == rm_id) &
        (events["type_id"].isin({7, 8, 49})) &
        (events["x"] >= 40)
    ]
    denom = len(rm_def) or 1
    return round(len(opp_passes_att) / denom, 2)


def calc_field_tilt(events: pd.DataFrame, meta: dict) -> float:
    """
    Field tilt = % of final-third touches that belong to RM.
    """
    if events.empty:
        return 0.0

    final_third = events[events["x"] >= 67]
    if final_third.empty:
        return 0.0

    rm_touches  = len(final_third[final_third["contestant_id"] == meta["rm_id"]])
    total_touches = len(final_third)
    return round(rm_touches / total_touches * 100, 1) if total_touches else 0.0


# ---------------------------------------------------------------------------
# Dropdown helpers (used by pages)
# ---------------------------------------------------------------------------

def build_match_options(competition: str, season: str) -> list[dict]:
    """Return sorted dcc.Dropdown options for all RM matches in a season."""
    matches = get_season_match_list(competition, season)
    options = []
    for m in matches:
        venue  = "🏠" if m["is_rm_home"] else "✈️"
        week   = m.get("week", "?")
        prefix = f"MD{week} " if str(week).isdigit() else f"{week} "
        label  = f"{prefix}{venue} vs {m['opponent']}  {m['score_str']}  ({m['date']})"
        options.append({"label": label, "value": m["filepath"]})
    return options
