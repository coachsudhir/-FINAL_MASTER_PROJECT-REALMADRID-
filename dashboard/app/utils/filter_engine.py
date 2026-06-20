"""
FilterEngine - Centralized filtering architecture for football analytics dashboard

This module provides reusable filtering logic for all pages.
All pages should import and use these functions to ensure:
- consistent filtering behavior
- proper dataframe validation
- empty state handling
- filter context tracking
"""

import pandas as pd
from typing import Optional, Dict, Any, List
from utils.data_helpers import (
    get_match_options,
    get_match_summary,
    get_available_seasons,
)


class FilterEngine:
    """
    Centralized filtering engine for Real Madrid analytics.
    
    Provides:
    - Dynamic option generation for cascading dropdowns
    - Data filtering with validation
    - Empty state detection
    - Filter context tracking
    - Error handling
    """

    # ────────────────────────────────────────────────────────────────────────
    # DROPDOWN OPTIONS GENERATION
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_season_options(competition: str) -> List[Dict[str, str]]:
        """
        Get available seasons for a competition.
        
        Args:
            competition: Competition name (LaLiga, Copa del Rey, Champions League)
            
        Returns:
            List of dropdown options
        """
        try:
            seasons = get_available_seasons(competition or "LaLiga")
            return [{"label": s, "value": s} for s in seasons] if seasons else []
        except Exception as e:
            print(f"Error loading seasons for {competition}: {e}")
            return []

    @staticmethod
    def get_match_options(
        competition: str,
        season: str
    ) -> List[Dict[str, str]]:
        """
        Get available matches for competition/season.
        
        Args:
            competition: Competition name
            season: Season (e.g., "2025-2026")
            
        Returns:
            List of dropdown options for matches
        """
        try:
            return get_match_options(
                competition or "LaLiga",
                season or "2025-2026"
            )
        except Exception as e:
            print(f"Error loading matches for {competition}/{season}: {e}")
            return []

    # ────────────────────────────────────────────────────────────────────────
    # DATA FILTERING & AGGREGATION
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def load_matches_data(
        competition: str,
        season: str
    ) -> List[Dict[str, Any]]:
        """
        Load all match summaries for a competition/season.
        
        Used for:
        - KPI calculations
        - Standings
        - Trend analysis
        
        Args:
            competition: Competition name
            season: Season string
            
        Returns:
            List of match summary dicts, sorted by week
        """
        try:
            match_opts = get_match_options(
                competition or "LaLiga",
                season or "2025-2026"
            )
            
            matches = []
            for opt in match_opts:
                try:
                    summary = get_match_summary(opt["value"])
                    if summary:
                        matches.append(summary)
                except Exception as e:
                    print(f"Warning: Could not load match {opt.get('label')}: {e}")
                    continue
            
            # Sort by week
            matches.sort(key=lambda x: int(x.get("week") or 0))
            return matches
            
        except Exception as e:
            print(f"Error loading matches for {competition}/{season}: {e}")
            return []

    @staticmethod
    def filter_matches(
        matches: List[Dict],
        opponent: Optional[str] = None,
        venue: Optional[str] = None
    ) -> List[Dict]:
        """
        Filter matches by opponent and/or venue.
        
        Args:
            matches: List of match summaries
            opponent: Opponent name (optional filter)
            venue: "Home" or "Away" (optional filter)
            
        Returns:
            Filtered list of matches
        """
        filtered = matches.copy()
        
        if opponent:
            filtered = [
                m for m in filtered
                if opponent.lower() in m.get("away", "").lower() 
                or opponent.lower() in m.get("home", "").lower()
            ]
        
        if venue == "Home":
            filtered = [m for m in filtered if m.get("home") == "Real Madrid"]
        elif venue == "Away":
            filtered = [m for m in filtered if m.get("away") == "Real Madrid"]
        
        return filtered

    # ────────────────────────────────────────────────────────────────────────
    # FILTER CONTEXT (for display)
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_filter_context(
        competition: str,
        season: str,
        matches: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate filter context metadata for display.
        
        Shows user what data they're viewing.
        
        Args:
            competition: Selected competition
            season: Selected season
            matches: Loaded matches (for sample size)
            
        Returns:
            Dict with context information
        """
        if matches is None:
            matches = []
        
        # Calculate date range
        dates = [m.get("date") for m in matches if m.get("date")]
        date_range = ""
        if dates:
            date_range = f"{min(dates)} to {max(dates)}"
        
        return {
            "competition": competition or "LaLiga",
            "season": season or "2025-2026",
            "sample_size": len(matches),
            "date_range": date_range,
            "has_data": len(matches) > 0,
        }

    @staticmethod
    def format_filter_context(context: Dict[str, Any]) -> str:
        """
        Format filter context as readable string.
        
        Example output:
        "LaLiga 2025-2026 · 30 matches · 2025-08-19 to 2025-10-19"
        """
        parts = [
            f"{context.get('competition')} {context.get('season')}"
        ]
        
        if context.get("sample_size"):
            parts.append(f"{context['sample_size']} matches")
        
        if context.get("date_range"):
            parts.append(context["date_range"])
        
        return " · ".join(parts)

    # ────────────────────────────────────────────────────────────────────────
    # VALIDATION & ERROR HANDLING
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def validate_filter_state(
        competition: Optional[str],
        season: Optional[str],
        matches: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Validate filter state and return status.
        
        Returns:
            {
                "is_valid": bool,
                "has_data": bool,
                "error_message": str (if invalid),
                "sample_size": int
            }
        """
        if not competition or not season:
            return {
                "is_valid": False,
                "has_data": False,
                "error_message": "Competition and season required",
                "sample_size": 0,
            }
        
        if matches is None:
            matches = []
        
        if len(matches) == 0:
            return {
                "is_valid": True,
                "has_data": False,
                "error_message": f"No data available for {competition} {season}",
                "sample_size": 0,
            }
        
        return {
            "is_valid": True,
            "has_data": True,
            "error_message": None,
            "sample_size": len(matches),
        }

    @staticmethod
    def empty_state_message(context: Dict[str, Any]) -> str:
        """Generate user-friendly empty state message."""
        return (
            f"No data available for {context.get('competition')} {context.get('season')}. "
            f"Please select a different competition or season."
        )


# Convenience function for common filter pattern
def apply_filters(
    competition: str,
    season: str,
    opponent: Optional[str] = None,
    venue: Optional[str] = None
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function: Load and filter matches in one call.
    
    Returns:
        (filtered_matches, filter_context)
    """
    engine = FilterEngine()
    
    # Load all matches
    matches = engine.load_matches_data(competition, season)
    
    # Filter
    filtered = engine.filter_matches(matches, opponent, venue)
    
    # Get context
    context = engine.get_filter_context(competition, season, filtered)
    
    return filtered, context
