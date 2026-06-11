"""Additive tactical intelligence overlay package.

This package is intentionally isolated from the baseline pipeline.
Importing it does not alter existing app behavior.
"""

from .pipeline import OverlayOutput, build_tactical_intelligence_overlay
from .feature_flags import get_feature_flag_map

__all__ = [
    "OverlayOutput",
    "build_tactical_intelligence_overlay",
    "get_feature_flag_map",
]
