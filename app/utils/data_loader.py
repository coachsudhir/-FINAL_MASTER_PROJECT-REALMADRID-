"""
Data Loading and Preprocessing Pipeline
Handles loading data from various sources and preparing it for analysis
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from functools import lru_cache
import logging

from config import LALIGA_DATA, COPA_DATA, CHAMPIONS_DATA, SEASONS

logger = logging.getLogger(__name__)

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

class DataLoader:
    """Central data loading and caching system"""
    
    def __init__(self, competition="LaLiga", season="2025-2026"):
        self.competition = competition
        self.season = season
        self.data_path = self._get_competition_path(competition, season)
        
    def _get_competition_path(self, competition, season):
        """Get path to competition data"""
        if competition == "LaLiga":
            return LALIGA_DATA / season
        elif competition == "Copa del Rey":
            return COPA_DATA / season
        elif competition == "Champions League":
            return CHAMPIONS_DATA / season
        else:
            raise ValueError(f"Unknown competition: {competition}")
    
    @lru_cache(maxsize=32)
    def load_team_player_stats(self, team_name):
        """
        Load player seasonal statistics for a team
        
        Args:
            team_name: Team name (e.g., 'Real_Madrid_CF')
            
        Returns:
            DataFrame with player statistics
        """
        try:
            team_path = self.data_path / "equipos" / team_name
            csv_files = list(team_path.glob("*_jugadores_seasonstats.csv"))
            
            if not csv_files:
                logger.warning(f"No season stats found for {team_name}")
                return pd.DataFrame()
                
            df = pd.read_csv(csv_files[0], low_memory=False)
            # Clean column names
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            logger.error(f"Error loading team stats for {team_name}: {e}")
            return pd.DataFrame()
    
    def load_team_list(self):
        """Load list of all teams in competition"""
        try:
            csv_files = list(self.data_path.glob("*_equipos.csv"))
            if csv_files:
                df = pd.read_csv(csv_files[0])
                return df.to_dict('records')
            return []
        except Exception as e:
            logger.error(f"Error loading team list: {e}")
            return []
    
    def load_matches_data(self):
        """Load matches metadata"""
        try:
            matches_json = self.data_path / "jsons" / "matches.json"
            if matches_json.exists():
                with open(matches_json, 'r') as f:
                    data = json.load(f)
                    # Convert to DataFrame
                    matches = []
                    for match in data.get('matches', []):
                        matches.append({
                            'match_id': match.get('id'),
                            'date': match.get('date'),
                            'home_team': match.get('home', {}).get('name', ''),
                            'away_team': match.get('away', {}).get('name', ''),
                            'home_score': match.get('result', {}).get('home'),
                            'away_score': match.get('result', {}).get('away'),
                            'status': match.get('status', ''),
                        })
                    return pd.DataFrame(matches)
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading matches: {e}")
            return pd.DataFrame()
    
    def load_standings(self):
        """Load league standings"""
        try:
            standings_json = self.data_path / "jsons" / "standings.json"
            if standings_json.exists():
                with open(standings_json, 'r') as f:
                    data = json.load(f)
                    standings = []
                    for team in data.get('standings', []):
                        standings.append({
                            'position': team.get('position'),
                            'team': team.get('team', {}).get('name', ''),
                            'played': team.get('gamesPlayed'),
                            'wins': team.get('wins'),
                            'draws': team.get('draws'),
                            'losses': team.get('losses'),
                            'goals_for': team.get('goalsFor'),
                            'goals_against': team.get('goalsAgainst'),
                            'goal_difference': team.get('goalsDifference'),
                            'points': team.get('points'),
                        })
                    return pd.DataFrame(standings)
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading standings: {e}")
            return pd.DataFrame()
    
    def load_match_details(self, match_id):
        """
        Load detailed match data (events, etc.)
        
        Args:
            match_id: Match ID
            
        Returns:
            Dictionary with match details
        """
        try:
            partidos_path = self.data_path / "partidos"
            for json_file in partidos_path.glob("*.json"):
                if match_id in json_file.name:
                    with open(json_file, 'r') as f:
                        return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading match details for {match_id}: {e}")
            return {}


# ============================================================================
# DATA AGGREGATION AND CALCULATION FUNCTIONS
# ============================================================================

class TacticalMetricsCalculator:
    """Calculate tactical metrics from player statistics"""
    
    @staticmethod
    def calculate_player_percentiles(df, metrics):
        """
        Calculate percentile rankings for players
        
        Args:
            df: DataFrame with player stats
            metrics: List of metric columns to calculate percentiles for
            
        Returns:
            DataFrame with percentile columns added
        """
        for metric in metrics:
            if metric in df.columns:
                df[f'{metric}_percentile'] = df[metric].rank(pct=True) * 100
        return df
    
    @staticmethod
    def calculate_team_averages(player_stats_df):
        """
        Calculate team-level averages from player statistics
        
        Args:
            player_stats_df: DataFrame with player stats
            
        Returns:
            Dictionary with team averages
        """
        numeric_columns = player_stats_df.select_dtypes(include=[np.number]).columns
        return player_stats_df[numeric_columns].mean().to_dict()
    
    @staticmethod
    def classify_tactical_style(team_stats):
        """
        Classify team tactical style based on key metrics
        
        Args:
            team_stats: Dictionary with team statistics
            
        Returns:
            String describing tactical style
        """
        # This would use actual metrics to classify
        # For now, return placeholder
        return "Positional Attacking"
    
    @staticmethod
    def calculate_pressing_intensity(stats):
        """
        Calculate pressing intensity (PPDA proxy from available stats)
        
        PPDA = Passes Allowed Per Defensive Action
        Lower = more aggressive pressing
        """
        if 'Total Passes' in stats and 'Total Tackles' in stats:
            passes = stats.get('Total Passes', 1)
            tackles = stats.get('Total Tackles', 1)
            if tackles > 0:
                return passes / tackles
        return None
    
    @staticmethod
    def calculate_possession_dominance(team_stats, league_avg_possession=0.50):
        """
        Calculate possession dominance relative to league average
        """
        if 'Possession' in team_stats:
            poss = team_stats['Possession']
            dominance = (poss - league_avg_possession) / league_avg_possession * 100
            return max(-100, min(100, dominance))  # Cap at ±100
        return 0
    
    @staticmethod
    def identify_key_players(player_stats_df, metric='Total Shots', top_n=5):
        """
        Identify key players by a specific metric
        """
        return player_stats_df.nlargest(top_n, metric)[['nombre', 'posicion', metric]]


# ============================================================================
# BENCHMARKING AND COMPARISON
# ============================================================================

class BenchmarkCalculator:
    """Calculate benchmarks against league averages and rivals"""
    
    @staticmethod
    def calculate_league_averages(competition_path):
        """Calculate league-wide average statistics"""
        try:
            equipos_dir = competition_path / "equipos"
            team_stats = []
            
            for team_dir in equipos_dir.iterdir():
                if team_dir.is_dir():
                    stats_files = list(team_dir.glob("*_jugadores_seasonstats.csv"))
                    if stats_files:
                        df = pd.read_csv(stats_files[0], low_memory=False)
                        team_avg = df.select_dtypes(include=[np.number]).mean()
                        team_stats.append(team_avg)
            
            if team_stats:
                league_avg = pd.concat(team_stats, axis=1).mean(axis=1)
                return league_avg.to_dict()
        except Exception as e:
            logger.error(f"Error calculating league averages: {e}")
        return {}
    
    @staticmethod
    def calculate_percentile_rank(value, league_distribution):
        """
        Calculate percentile rank of a value within league
        
        Args:
            value: The value to rank
            league_distribution: List of all league values
            
        Returns:
            Percentile (0-100)
        """
        if not league_distribution:
            return 50
        
        sorted_dist = sorted(league_distribution)
        if value <= sorted_dist[0]:
            return 1
        if value >= sorted_dist[-1]:
            return 99
            
        for i, v in enumerate(sorted_dist):
            if value <= v:
                return int((i / len(sorted_dist)) * 100)
        return 99
    
    @staticmethod
    def compare_with_rivals(team_stats, rivals_stats):
        """
        Compare team statistics with rival teams
        
        Returns:
            DataFrame with comparison
        """
        all_stats = [team_stats] + rivals_stats
        names = ['Real Madrid'] + [f'Rival {i}' for i in range(1, len(rivals_stats)+1)]
        
        comparison_df = pd.DataFrame(all_stats, index=names)
        return comparison_df


# ============================================================================
# DATA PREPROCESSING UTILITIES
# ============================================================================

def clean_player_data(df):
    """Clean and standardize player data"""
    # Fill NaN values
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    
    # Standardize column names
    df.columns = df.columns.str.strip().str.replace(' ', '_').str.lower()
    
    return df


def create_rolling_stats(df, window=5):
    """
    Create rolling statistics for trend analysis
    
    Args:
        df: DataFrame with time-indexed data
        window: Rolling window size
        
    Returns:
        DataFrame with rolling averages
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    rolling_df = df[numeric_cols].rolling(window=window).mean()
    return rolling_df


def normalize_metric(value, min_val, max_val):
    """
    Normalize a metric to 0-1 scale
    
    Args:
        value: Value to normalize
        min_val: Minimum expected value
        max_val: Maximum expected value
        
    Returns:
        Normalized value (0-1)
    """
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def get_position_group(position_code):
    """Map position code to position group"""
    position_map = {
        'GK': 'Goalkeeper',
        'CB': 'Defender',
        'LB': 'Defender',
        'RB': 'Defender',
        'LWB': 'Defender',
        'RWB': 'Defender',
        'DM': 'Midfielder',
        'CM': 'Midfielder',
        'AM': 'Midfielder',
        'LM': 'Midfielder',
        'RM': 'Midfielder',
        'LW': 'Forward',
        'RW': 'Forward',
        'ST': 'Forward',
        'CF': 'Forward',
    }
    return position_map.get(position_code, 'Unknown')
