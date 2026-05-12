"""
Dashboard Configuration and Constants
Real Madrid Tactical Analytics Dashboard
"""

import os
from pathlib import Path

# ============================================================================
# PATHS
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent


def _resolve_data_root() -> Path:
    """Resolve data root across local/dev/deploy environments."""
    env_root = os.getenv("DATA_ROOT")
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if p.exists():
            return p

    candidates = [
        # Workspace root when running from dashboard/app
        PROJECT_ROOT.parent,
        # Dashboard root (if data copied inside repo)
        PROJECT_ROOT,
        # Legacy absolute location on this machine
        Path("/Users/sudhirdahiya/Downloads/FINAL_MASTER_PROJECT(REALMADRID)"),
    ]

    for p in candidates:
        if (p / "LaLiga").exists() or (p / "Copa del Rey").exists() or (p / "UEFA Champions League").exists():
            return p

    # Safe fallback to avoid crashing; app will show empty states.
    return PROJECT_ROOT


DATA_ROOT = _resolve_data_root()
LALIGA_DATA = DATA_ROOT / "LaLiga"
COPA_DATA = DATA_ROOT / "Copa del Rey"
CHAMPIONS_DATA = DATA_ROOT / "UEFA Champions League"

# ============================================================================
# COLORS - LIGHT PROFESSIONAL ANALYTICS THEME
# ============================================================================
COLOR_SCHEME = {
    "background": "#f8fafc",           # Light grey background
    "surface": "#ffffff",              # White surface
    "border": "#e2e8f0",               # Light border
    "text_primary": "#1e293b",         # Dark slate text
    "text_secondary": "#64748b",       # Medium grey text
    "accent_blue": "#2563eb",          # Royal blue accent
    "accent_green": "#059669",         # Emerald green
    "accent_red": "#dc2626",           # Red
    "accent_yellow": "#d97706",        # Amber
    "accent_orange": "#ea580c",        # Orange
    "accent_purple": "#7c3aed",        # Violet

    # Tactical heatmap colors
    "heatmap_cold": "#bfdbfe",         # Light blue
    "heatmap_warm": "#fca5a5",         # Light red
    "heatmap_neutral": "#e2e8f0",      # Neutral grey

    # Team colors
    "real_madrid": "#1e293b",          # Dark text on white
    "real_madrid_bg": "#ffffff",       # White background
}

DARK_TEMPLATE = {
    "layout": {
        "paper_bgcolor": COLOR_SCHEME["background"],
        "plot_bgcolor": COLOR_SCHEME["surface"],
        "font": {"color": COLOR_SCHEME["text_primary"], "family": "Arial, sans-serif"},
        "margin": {"l": 40, "r": 40, "t": 40, "b": 40},
        "hovermode": "closest",
    }
}

# ============================================================================
# LEAGUES AND COMPETITIONS
# ============================================================================
COMPETITIONS = {
    "LaLiga": {
        "name": "LaLiga EA SPORTS",
        "country": "Spain",
        "level": "Domestic",
        "path": LALIGA_DATA,
    },
    "Copa del Rey": {
        "name": "Copa del Rey",
        "country": "Spain",
        "level": "Domestic Cup",
        "path": COPA_DATA,
    },
    "Champions League": {
        "name": "UEFA Champions League",
        "country": "Europe",
        "level": "International",
        "path": CHAMPIONS_DATA,
    },
}

SEASONS = ["2024-2025", "2025-2026"]

# ============================================================================
# TACTICAL METRICS THRESHOLDS
# ============================================================================
TACTICAL_THRESHOLDS = {
    "PPDA": {
        "aggressive": 4.0,     # Below 4.0 = aggressive pressing
        "moderate": 6.0,       # 4.0-6.0 = moderate pressing
        "defensive": 10.0,     # 6.0-10.0 = passive pressing
        "very_defensive": 10.0,  # Above 10.0 = very passive
    },
    "possession": {
        "dominant": 0.60,      # > 60% = possession dominant
        "balanced": 0.40,      # 40-60% = balanced
        "limited": 0.40,       # < 40% = limited possession
    },
    "xThreat": {
        "high": 0.15,          # > 0.15 = high transition threat
        "moderate": 0.08,      # 0.08-0.15 = moderate
        "low": 0.08,           # < 0.08 = low
    },
    "pressing_success": {
        "excellent": 0.40,     # > 40% = excellent
        "good": 0.25,          # 25-40% = good
        "average": 0.15,       # < 25% = below average
    },
}

# ============================================================================
# PLAYER POSITIONS
# ============================================================================
POSITIONS = {
    "GK": "Goalkeeper",
    "CB": "Centre Back",
    "LB": "Left Back",
    "RB": "Right Back",
    "LWB": "Left Wing Back",
    "RWB": "Right Wing Back",
    "DM": "Defensive Midfielder",
    "CM": "Central Midfielder",
    "AM": "Attacking Midfielder",
    "LM": "Left Midfielder",
    "RM": "Right Midfielder",
    "LW": "Left Winger",
    "RW": "Right Winger",
    "ST": "Striker",
    "CF": "Centre Forward",
}

POSITION_GROUPS = {
    "Goalkeeper": ["GK"],
    "Defender": ["CB", "LB", "RB", "LWB", "RWB"],
    "Midfielder": ["DM", "CM", "AM", "LM", "RM"],
    "Forward": ["LW", "RW", "ST", "CF"],
}

# ============================================================================
# TACTICAL CLASSIFICATIONS
# ============================================================================
TACTICAL_STYLES = {
    "possession_dominant": "Possession Dominant",
    "direct": "Direct / Counter",
    "high_pressing": "High Pressing",
    "mid_block": "Mid Block",
    "low_block": "Low Block",
    "combinative": "Combinative Attacking",
    "positional": "Positional Attacking",
    "transition_focused": "Transition Focused",
    "balanced": "Balanced",
}

# ============================================================================
# PITCH DIMENSIONS
# ============================================================================
PITCH = {
    "length": 120,
    "width": 80,
    "half_pitch_length": 60,
    "half_pitch_width": 40,
    "box_length": 18,
    "box_width": 44,
    "penalty_spot": 12,
    "goal_line": 0,
    "center_line": 60,
}

# ============================================================================
# ZONE DEFINITIONS (for pitch analysis)
# ============================================================================
ZONES = {
    "defensive_third": {"x_range": (0, 40), "label": "Defensive Third"},
    "middle_third": {"x_range": (40, 80), "label": "Middle Third"},
    "attacking_third": {"x_range": (80, 120), "label": "Attacking Third"},
    "final_third": {"x_range": (80, 120), "label": "Final Third"},
    "zone_14": {"x_range": (85, 120), "y_range": (18, 62), "label": "Zone 14"},
    "box": {"x_range": (102, 120), "y_range": (18, 62), "label": "Penalty Box"},
}

# ============================================================================
# DASHBOARD LAYOUT SETTINGS
# ============================================================================
DASHBOARD_CONFIG = {
    "title": "Real Madrid Tactical & Player Performance Dashboard",
    "subtitle": "Master's Final Project - Football Data Analytics",
    "refresh_interval": 3600000,  # 1 hour in milliseconds
    "rows_per_page": 10,
    "default_season": "2025-2026",
    "default_competition": "LaLiga",
}

# ============================================================================
# PERCENTILE BINS FOR RANKING
# ============================================================================
PERCENTILE_BINS = {
    "xG": [0, 0.5, 1.0, 1.5, 2.0, 3.0],
    "xA": [0, 0.2, 0.4, 0.6, 0.8, 1.0],
    "passes_completed": [0, 30, 60, 100, 150, 200],
    "tackles": [0, 2, 4, 6, 8, 10],
    "progressive_passes": [0, 2, 4, 6, 8, 10],
    "duels_won_percent": [30, 45, 55, 65, 75, 100],
}

# ============================================================================
# CACHE SETTINGS
# ============================================================================
CACHE_CONFIG = {
    "cache_type": "simple",
    "cache_default_timeout": 300,
}

# ============================================================================
# LOGGING
# ============================================================================
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": True,
        }
    },
}
