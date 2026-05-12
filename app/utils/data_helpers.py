"""
Data Helpers - Scan actual data files and build dropdown options
"""

import os
import json
import pandas as pd
from pathlib import Path
from functools import lru_cache
from config import DATA_ROOT

COMPETITION_PATHS = {
    "LaLiga": DATA_ROOT / "LaLiga",
    "Copa del Rey": DATA_ROOT / "Copa del Rey",
    "Champions League": DATA_ROOT / "UEFA Champions League",
}

# ============================================================================
# SEASONS
# ============================================================================

def get_available_seasons(competition="LaLiga"):
    """Return list of seasons that have data for this competition"""
    base = COMPETITION_PATHS.get(competition)
    if not base or not base.exists():
        return ["2025-2026"]
    seasons = sorted(
        [d.name for d in base.iterdir() if d.is_dir() and "-" in d.name],
        reverse=True,
    )
    return seasons if seasons else ["2025-2026"]


def get_season_options(competition="LaLiga"):
    """Return dcc.Dropdown options for available seasons"""
    return [{"label": s, "value": s} for s in get_available_seasons(competition)]


# ============================================================================
# COMPETITIONS
# ============================================================================

def get_competition_options():
    """Return dcc.Dropdown options for competitions that have data"""
    comps = []
    for name, path in COMPETITION_PATHS.items():
        if path.exists():
            comps.append({"label": name, "value": name})
    return comps if comps else [{"label": "LaLiga", "value": "LaLiga"}]


# ============================================================================
# MATCHES
# ============================================================================

@lru_cache(maxsize=10)
def _load_match_index(competition, season):
    """Scan partidos/ directory and parse every match JSON - cached per comp+season"""
    base = COMPETITION_PATHS.get(competition)
    if not base:
        return []

    partidos_path = base / season / "partidos"
    if not partidos_path.exists():
        return []

    matches = []
    for f in sorted(partidos_path.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            mi = data.get("matchInfo", {})
            contestants = mi.get("contestant", [])
            home = next((c["name"] for c in contestants if c.get("position") == "home"), "?")
            away = next((c["name"] for c in contestants if c.get("position") == "away"), "?")
            raw_date = mi.get("date", "")
            date_str = raw_date[:10] if raw_date else ""
            week = mi.get("week", "?")
            desc = mi.get("description", f"{home} vs {away}")

            ld = data.get("liveData", {})
            details = ld.get("matchDetails", {})
            scores = details.get("scores", {}).get("total", {})
            h_score = scores.get("home", "-")
            a_score = scores.get("away", "-")
            status = details.get("matchStatus", "Unknown")

            # only include Real Madrid matches
            if "Real Madrid" not in home and "Real Madrid" not in away:
                continue

            venue = "Home" if "Real Madrid" in home else "Away"
            opponent = away if venue == "Home" else home
            result_str = f"{h_score}-{a_score}"

            label = f"MD{week} · {'🏠' if venue=='Home' else '✈️'} vs {opponent} ({result_str}) · {date_str}"

            matches.append({
                "label": label,
                "value": str(f),
                "week": int(week) if str(week).isdigit() else 0,
                "date": date_str,
                "home": home,
                "away": away,
                "opponent": opponent,
                "venue": venue,
                "score": result_str,
                "status": status,
                "file_path": str(f),
            })
        except Exception:
            continue

    matches.sort(key=lambda x: x["week"])
    return matches


def get_match_options(competition="LaLiga", season="2025-2026", venue="All"):
    """Return dcc.Dropdown options for matches involving Real Madrid"""
    all_matches = _load_match_index(competition, season)
    if venue != "All":
        all_matches = [m for m in all_matches if m["venue"] == venue]
    return [{"label": m["label"], "value": m["value"]} for m in all_matches]


def get_match_data(file_path):
    """Load full match JSON for a given file path"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_match_summary(file_path):
    """Return a dict with high-level match info from a file path"""
    data = get_match_data(file_path)
    if not data:
        return {}
    mi = data.get("matchInfo", {})
    ld = data.get("liveData", {})
    details = ld.get("matchDetails", {})
    scores = details.get("scores", {}).get("total", {})
    contestants = mi.get("contestant", [])
    home = next((c["name"] for c in contestants if c.get("position") == "home"), "?")
    away = next((c["name"] for c in contestants if c.get("position") == "away"), "?")
    return {
        "home": home,
        "away": away,
        "date": mi.get("date", "")[:10],
        "week": mi.get("week"),
        "home_score": scores.get("home", 0),
        "away_score": scores.get("away", 0),
        "status": details.get("matchStatus", ""),
        "winner": details.get("winner", ""),
        "ht_home": details.get("scores", {}).get("ht", {}).get("home", 0),
        "ht_away": details.get("scores", {}).get("ht", {}).get("away", 0),
        "venue_name": mi.get("venue", {}).get("shortName", ""),
    }


# ============================================================================
# PLAYERS
# ============================================================================

@lru_cache(maxsize=10)
def _load_player_stats(competition, season):
    """Load Real Madrid player season stats - cached"""
    base = COMPETITION_PATHS.get(competition)
    if not base:
        return pd.DataFrame()
    csv_path = base / season / "equipos" / "Real_Madrid_CF" / "Real_Madrid_CF_jugadores_seasonstats.csv"
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path, low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return pd.DataFrame()


def get_player_options(competition="LaLiga", season="2025-2026", position="All"):
    """Return dcc.Dropdown options for Real Madrid players"""
    df = _load_player_stats(competition, season)
    if df.empty or "nombre" not in df.columns:
        return []
    if position != "All" and "posicion" in df.columns:
        df = df[df["posicion"] == position]
    options = []
    for _, row in df.iterrows():
        pos = row.get("posicion", "") if "posicion" in df.columns else ""
        options.append({
            "label": f"{row['nombre']} ({pos})" if pos else row["nombre"],
            "value": row["nombre"],
        })
    return options


def get_position_options():
    """Return position filter options"""
    return [
        {"label": "All Positions", "value": "All"},
        {"label": "Forwards", "value": "Forward"},
        {"label": "Midfielders", "value": "Midfielder"},
        {"label": "Defenders", "value": "Defender"},
        {"label": "Goalkeepers", "value": "Goalkeeper"},
    ]


def get_player_stats(player_name, competition="LaLiga", season="2025-2026"):
    """Return stats dict for a specific player"""
    df = _load_player_stats(competition, season)
    if df.empty or "nombre" not in df.columns:
        return {}
    row = df[df["nombre"] == player_name]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


# ============================================================================
# OPPONENTS / TEAMS
# ============================================================================

def get_opponent_options(competition="LaLiga", season="2025-2026"):
    """Return opponents Real Madrid has faced"""
    matches = _load_match_index(competition, season)
    seen = set()
    options = []
    for m in matches:
        opp = m["opponent"]
        if opp not in seen:
            seen.add(opp)
            options.append({"label": opp, "value": opp})
    return sorted(options, key=lambda x: x["label"])


def get_all_teams(competition="LaLiga", season="2025-2026"):
    """Return all teams in the competition from the equipos directory"""
    base = COMPETITION_PATHS.get(competition)
    if not base:
        return []
    equipos_path = base / season / "equipos"
    if not equipos_path.exists():
        return []
    return sorted(
        [d.name.replace("_", " ").replace("  ", " ") for d in equipos_path.iterdir()
         if d.is_dir()],
    )


def get_team_options(competition="LaLiga", season="2025-2026"):
    """Return dcc.Dropdown options for all teams"""
    return [{"label": t, "value": t} for t in get_all_teams(competition, season)]
