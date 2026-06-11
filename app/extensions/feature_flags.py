"""Feature flags for the non-destructive tactical intelligence overlay.

All flags default to OFF to guarantee backward compatibility.
"""

from __future__ import annotations

import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_feature_flag_map() -> dict[str, bool]:
    flags = {
        "ENABLE_SUB_PHASE_TAGGING": _env_bool("ENABLE_SUB_PHASE_TAGGING", False),
        "ENABLE_ADVANCED_KPI_LAYER": _env_bool("ENABLE_ADVANCED_KPI_LAYER", False),
        "ENABLE_CROSS_PHASE_METRICS": _env_bool("ENABLE_CROSS_PHASE_METRICS", False),
        "ENABLE_SEQUENCE_ENRICHMENT": _env_bool("ENABLE_SEQUENCE_ENRICHMENT", False),
        "ENABLE_OPPONENT_ADJUSTMENTS": _env_bool("ENABLE_OPPONENT_ADJUSTMENTS", False),
        "ENABLE_GAMESTATE_ADJUSTMENTS": _env_bool("ENABLE_GAMESTATE_ADJUSTMENTS", False),
    }

    # Backward-compatible aliases for older env var spellings.
    flags["ENABLE_CROSS_PHASE_LAYER"] = flags["ENABLE_CROSS_PHASE_METRICS"]
    flags["ENABLE_GAME_STATE_ADJUSTMENTS"] = flags["ENABLE_GAMESTATE_ADJUSTMENTS"]
    return flags
