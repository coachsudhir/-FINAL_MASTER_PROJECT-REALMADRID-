"""
Tactical Models - Advanced tactical classification and analysis
"""

import numpy as np
import pandas as pd
from enum import Enum

# ============================================================================
# TACTICAL STYLE ENUMS
# ============================================================================

class PossessionStyle(Enum):
    """Possession-based tactical classification"""
    DOMINANT = "Possession Dominant"
    BALANCED = "Balanced Possession"
    LIMITED = "Limited Possession"
    DIRECT = "Direct / Counter"


class PressingStyle(Enum):
    """Pressing intensity classification"""
    HIGH_PRESS = "High Pressing"
    MID_BLOCK = "Mid Block"
    LOW_BLOCK = "Low Block"
    DEFENSIVE = "Defensive Block"


class TransitionStyle(Enum):
    """Transition-based attacking classification"""
    COUNTER_FOCUSED = "Counter-Attack Focused"
    BALANCED_TRANSITION = "Balanced Transitions"
    POSSESSION_TRANSITION = "Possession-Based Transition"


class AttackingStyle(Enum):
    """Attacking approach classification"""
    POSITIONAL = "Positional Attacking"
    DIRECT = "Direct Attacking"
    COMBINATIVE = "Combinative"
    WING_BASED = "Wing-Based"


# ============================================================================
# TACTICAL CLASSIFIER
# ============================================================================

class TacticalStyleClassifier:
    """Classify team tactical style from statistical data"""
    
    @staticmethod
    def classify_possession(possession_pct, pass_success_pct=None):
        """
        Classify possession style
        
        Args:
            possession_pct: Average possession percentage
            pass_success_pct: Average pass success rate
            
        Returns:
            PossessionStyle enum
        """
        if possession_pct >= 55:
            return PossessionStyle.DOMINANT
        elif possession_pct >= 45:
            return PossessionStyle.BALANCED
        elif possession_pct >= 35:
            return PossessionStyle.LIMITED
        else:
            return PossessionStyle.DIRECT
    
    @staticmethod
    def classify_pressing(ppda, tackles_per_90, interceptions_per_90):
        """
        Classify pressing intensity
        
        PPDA = Passes Allowed Per Defensive Action
        Lower PPDA = more aggressive pressing
        
        Args:
            ppda: Passes per defensive action (inverse of pressing)
            tackles_per_90: Tackles per 90 minutes
            interceptions_per_90: Interceptions per 90 minutes
            
        Returns:
            PressingStyle enum
        """
        # PPDA thresholds
        if ppda < 4.5:
            return PressingStyle.HIGH_PRESS
        elif ppda < 6.5:
            return PressingStyle.MID_BLOCK
        elif ppda < 8.5:
            return PressingStyle.LOW_BLOCK
        else:
            return PressingStyle.DEFENSIVE
    
    @staticmethod
    def classify_transitions(
        counter_attack_success,
        transition_xThreat,
        possession_recovery_time
    ):
        """
        Classify transition-based attacking
        
        Args:
            counter_attack_success: Goals from counter-attacks
            transition_xThreat: xThreat from transitions
            possession_recovery_time: Avg time to regain possession
            
        Returns:
            TransitionStyle enum
        """
        counter_score = counter_attack_success * 0.4 + transition_xThreat * 0.6
        
        if counter_score > 1.5:
            return TransitionStyle.COUNTER_FOCUSED
        elif counter_score > 0.8:
            return TransitionStyle.BALANCED_TRANSITION
        else:
            return TransitionStyle.POSSESSION_TRANSITION
    
    @staticmethod
    def classify_attacking(
        crosses_per_90,
        progressive_passes_per_90,
        pass_length_avg,
        possession_pct
    ):
        """
        Classify attacking approach
        
        Args:
            crosses_per_90: Crosses per 90 minutes
            progressive_passes_per_90: Progressive passes per 90
            pass_length_avg: Average pass length
            possession_pct: Possession percentage
            
        Returns:
            AttackingStyle enum
        """
        wing_score = crosses_per_90 / (progressive_passes_per_90 + 0.1)
        
        if wing_score > 0.5:
            return AttackingStyle.WING_BASED
        elif pass_length_avg > 15:
            return AttackingStyle.DIRECT
        elif possession_pct > 55:
            return AttackingStyle.POSITIONAL
        else:
            return AttackingStyle.COMBINATIVE


# ============================================================================
# TEAM TACTICAL PROFILE
# ============================================================================

class TacticalProfile:
    """Complete tactical profile of a team"""
    
    def __init__(self, team_name, season):
        self.team_name = team_name
        self.season = season
        self.possession_style = None
        self.pressing_style = None
        self.transition_style = None
        self.attacking_style = None
        self.formation = None
        self.key_metrics = {}
        self.tactical_description = ""
    
    def generate_description(self):
        """
        Generate natural language description of tactical profile
        
        Returns:
            String description of team's tactical identity
        """
        description_parts = []
        
        # Possession approach
        if self.possession_style == PossessionStyle.DOMINANT:
            description_parts.append(
                f"{self.team_name} is possession-dominant, controlling play through ball retention."
            )
        elif self.possession_style == PossessionStyle.BALANCED:
            description_parts.append(
                f"{self.team_name} employs balanced possession, mixing control with efficiency."
            )
        elif self.possession_style == PossessionStyle.LIMITED:
            description_parts.append(
                f"{self.team_name} limits possession, focusing on efficiency over control."
            )
        else:
            description_parts.append(
                f"{self.team_name} plays direct football with emphasis on quick transitions."
            )
        
        # Pressing style
        if self.pressing_style == PressingStyle.HIGH_PRESS:
            description_parts.append(
                "Aggressive high pressing forces turnovers in opponent's half."
            )
        elif self.pressing_style == PressingStyle.MID_BLOCK:
            description_parts.append(
                "Moderate pressing from mid-field allows space but disrupts play."
            )
        else:
            description_parts.append(
                "Deep defensive positioning minimizes pressing and focuses on shape."
            )
        
        # Attacking approach
        if self.attacking_style == AttackingStyle.POSITIONAL:
            description_parts.append(
                "Positional attacking through methodical build-up and combination play."
            )
        elif self.attacking_style == AttackingStyle.WING_BASED:
            description_parts.append(
                "Wing-based attacking utilizing width and crossing opportunities."
            )
        elif self.attacking_style == AttackingStyle.DIRECT:
            description_parts.append(
                "Direct attacking with emphasis on quick vertical progression."
            )
        else:
            description_parts.append(
                "Combinative attacking through short passes and movement."
            )
        
        self.tactical_description = " ".join(description_parts)
        return self.tactical_description
    
    def to_dict(self):
        """Convert profile to dictionary"""
        return {
            'team': self.team_name,
            'season': self.season,
            'possession_style': self.possession_style.value if self.possession_style else None,
            'pressing_style': self.pressing_style.value if self.pressing_style else None,
            'transition_style': self.transition_style.value if self.transition_style else None,
            'attacking_style': self.attacking_style.value if self.attacking_style else None,
            'formation': self.formation,
            'description': self.tactical_description,
            'metrics': self.key_metrics,
        }


# ============================================================================
# DEFENSIVE ANALYSIS
# ============================================================================

class DefensiveAnalyzer:
    """Analyze defensive patterns and vulnerabilities"""
    
    @staticmethod
    def identify_vulnerable_zones(shots_conceded_df):
        """
        Identify areas where team concedes most shots
        
        Args:
            shots_conceded_df: DataFrame with opponent shots (x, y coordinates)
            
        Returns:
            List of vulnerable zones with frequency
        """
        if shots_conceded_df.empty:
            return []
        
        # Divide pitch into zones
        zones = {
            'left_box': {"x": (0, 18), "y": (18, 62)},
            'center_box': {"x": (18, 102), "y": (18, 62)},
            'right_box': {"x": (102, 120), "y": (18, 62)},
            'left_outside': {"x": (0, 40), "y": (0, 18)},
            'center_outside': {"x": (40, 80), "y": (0, 18)},
            'right_outside': {"x": (80, 120), "y": (0, 18)},
        }
        
        vulnerabilities = []
        for zone_name, zone_coords in zones.items():
            shots_in_zone = shots_conceded_df[
                (shots_conceded_df['x'] >= zone_coords['x'][0]) &
                (shots_conceded_df['x'] <= zone_coords['x'][1]) &
                (shots_conceded_df['y'] >= zone_coords['y'][0]) &
                (shots_conceded_df['y'] <= zone_coords['y'][1])
            ]
            
            if len(shots_in_zone) > 0:
                vulnerabilities.append({
                    'zone': zone_name,
                    'shots_conceded': len(shots_in_zone),
                    'frequency': len(shots_in_zone) / len(shots_conceded_df),
                })
        
        # Sort by frequency
        vulnerabilities.sort(key=lambda x: x['frequency'], reverse=True)
        return vulnerabilities
    
    @staticmethod
    def analyze_defensive_line_height(player_positions_df):
        """
        Calculate average defensive line height
        
        Args:
            player_positions_df: DataFrame with player x-coordinates during defense
            
        Returns:
            Dictionary with line height metrics
        """
        if player_positions_df.empty:
            return {}
        
        # Get defender positions (typically CB, LB, RB)
        defenders = player_positions_df[
            player_positions_df['position'].isin(['CB', 'LB', 'RB'])
        ]
        
        if defenders.empty:
            return {}
        
        return {
            'average_height': defenders['x'].mean(),
            'max_height': defenders['x'].max(),
            'min_height': defenders['x'].min(),
            'std_deviation': defenders['x'].std(),
            'compactness': 120 - defenders['x'].std(),  # Lower = more compact
        }


# ============================================================================
# TRANSITIONAL ANALYSIS
# ============================================================================

class TransitionAnalyzer:
    """Analyze offensive and defensive transitions"""
    
    @staticmethod
    def calculate_counter_attack_efficiency(
        counter_attacks_df,
        shots_df,
        goals_df
    ):
        """
        Calculate efficiency of counter-attack sequences
        
        Args:
            counter_attacks_df: Counter-attack sequences
            shots_df: Shots from counter-attacks
            goals_df: Goals from counter-attacks
            
        Returns:
            Dictionary with efficiency metrics
        """
        if counter_attacks_df.empty:
            return {}
        
        return {
            'counter_attacks': len(counter_attacks_df),
            'shots': len(shots_df),
            'goals': len(goals_df),
            'shot_efficiency': len(shots_df) / len(counter_attacks_df) if len(counter_attacks_df) > 0 else 0,
            'goal_efficiency': len(goals_df) / len(counter_attacks_df) if len(counter_attacks_df) > 0 else 0,
            'conversion_rate': len(goals_df) / max(len(shots_df), 1),
        }
    
    @staticmethod
    def calculate_recovery_metrics(possession_changes_df):
        """
        Calculate defensive recovery time and distance
        
        Args:
            possession_changes_df: DataFrame with possession change events
            
        Returns:
            Dictionary with recovery metrics
        """
        if possession_changes_df.empty:
            return {}
        
        return {
            'average_recovery_time': possession_changes_df['recovery_time'].mean(),
            'min_recovery_time': possession_changes_df['recovery_time'].min(),
            'max_recovery_time': possession_changes_df['recovery_time'].max(),
            'average_recovery_distance': possession_changes_df['recovery_distance'].mean(),
            'quick_recoveries': len(possession_changes_df[possession_changes_df['recovery_time'] < 5]),
        }


# ============================================================================
# COMPARISON AND CLUSTERING
# ============================================================================

class TacticalComparator:
    """Compare tactical profiles between teams"""
    
    @staticmethod
    def similarity_score(profile1, profile2):
        """
        Calculate similarity between two tactical profiles
        
        Args:
            profile1: TacticalProfile object
            profile2: TacticalProfile object
            
        Returns:
            Similarity score (0-1, 1 = identical)
        """
        score = 0
        components = 0
        
        # Compare styles
        if profile1.possession_style and profile2.possession_style:
            if profile1.possession_style == profile2.possession_style:
                score += 1
            components += 1
        
        if profile1.pressing_style and profile2.pressing_style:
            if profile1.pressing_style == profile2.pressing_style:
                score += 1
            components += 1
        
        if profile1.attacking_style and profile2.attacking_style:
            if profile1.attacking_style == profile2.attacking_style:
                score += 1
            components += 1
        
        if components == 0:
            return 0.5
        
        return score / components
    
    @staticmethod
    def find_tactical_peers(
        team_profile,
        all_profiles,
        n_closest=5
    ):
        """
        Find teams with similar tactical profiles
        
        Args:
            team_profile: Reference team profile
            all_profiles: List of all team profiles
            n_closest: Number of similar teams to return
            
        Returns:
            List of (team, similarity_score) tuples
        """
        similarities = []
        
        for profile in all_profiles:
            if profile.team_name == team_profile.team_name:
                continue
            
            score = TacticalComparator.similarity_score(team_profile, profile)
            similarities.append((profile, score))
        
        # Sort by similarity score
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:n_closest]


if __name__ == "__main__":
    # Example usage
    classifier = TacticalStyleClassifier()
    
    # Classify Real Madrid (example metrics)
    possession = classifier.classify_possession(61.5)
    pressing = classifier.classify_pressing(4.2, 22.3, 8.2)
    
    print(f"Possession Style: {possession.value}")
    print(f"Pressing Style: {pressing.value}")
    
    # Create tactical profile
    rm_profile = TacticalProfile("Real Madrid", "2025-2026")
    rm_profile.possession_style = possession
    rm_profile.pressing_style = pressing
    rm_profile.formation = "4-3-3"
    rm_profile.key_metrics = {
        'possession': 61.5,
        'ppda': 4.2,
        'goals': 42,
        'xg': 37.8,
    }
    rm_profile.generate_description()
    
    print(f"\nTactical Description:\n{rm_profile.tactical_description}")
    print(f"\nProfile:\n{rm_profile.to_dict()}")
