"""
Data Preprocessing Example
Demonstrates how to prepare football data for the dashboard

Run this script to:
1. Load raw data from CSV files
2. Clean and normalize metrics
3. Calculate tactical statistics
4. Generate benchmark comparisons
5. Export processed data for dashboard
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from config import LALIGA_DATA, POSITIONS
from utils.data_loader import (
    DataLoader,
    TacticalMetricsCalculator,
    BenchmarkCalculator,
    clean_player_data,
)

# ============================================================================
# EXAMPLE 1: Load Real Madrid Player Data
# ============================================================================

def load_and_clean_real_madrid_data():
    """Load and clean Real Madrid player statistics"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Loading Real Madrid Data")
    print("="*70)
    
    loader = DataLoader("LaLiga", "2025-2026")
    
    # Load Real Madrid stats
    rm_stats = loader.load_team_player_stats("Real_Madrid_CF")
    print(f"\nLoaded {len(rm_stats)} players for Real Madrid")
    print(f"Columns: {rm_stats.shape[1]}")
    
    # Clean data
    rm_stats = clean_player_data(rm_stats)
    
    # Display sample
    print("\nSample players:")
    print(rm_stats[['nombre', 'posicion', 'Goals', 'Assists', 'Total Passes']].head())
    
    return rm_stats


# ============================================================================
# EXAMPLE 2: Calculate Team-Level Metrics
# ============================================================================

def calculate_team_metrics(player_stats):
    """Calculate team-level aggregate metrics"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Team-Level Metrics")
    print("="*70)
    
    # Calculate averages
    team_avg = TacticalMetricsCalculator.calculate_team_averages(player_stats)
    
    # Key metrics
    metrics_to_display = [
        'Goals',
        'Assists',
        'Total Passes',
        'Total Shots',
        'Total Tackles',
        'Interceptions',
        'Recoveries',
        'Successful Dribbles',
    ]
    
    print("\nTeam Averages (per player):")
    for metric in metrics_to_display:
        if metric in team_avg:
            print(f"  {metric}: {team_avg[metric]:.2f}")
    
    return team_avg


# ============================================================================
# EXAMPLE 3: Player Percentile Rankings
# ============================================================================

def calculate_percentiles(player_stats):
    """Calculate percentile rankings for key metrics"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Player Percentile Rankings")
    print("="*70)
    
    metrics = ['Goals', 'Assists', 'Total Passes', 'Total Shots', 'Total Tackles']
    
    player_stats = TacticalMetricsCalculator.calculate_player_percentiles(
        player_stats,
        metrics
    )
    
    # Display top players
    print("\nTop 5 Goal Scorers:")
    top_scorers = player_stats.nlargest(5, 'Goals')[
        ['nombre', 'posicion', 'Goals', 'Goals_percentile']
    ]
    for idx, row in top_scorers.iterrows():
        print(f"  {row['nombre']:20} {row['posicion']:3} - "
              f"Goals: {row['Goals']:5.0f} (Percentile: {row['Goals_percentile']:5.1f}%)")
    
    print("\nTop 5 Playmakers (Assists):")
    top_assists = player_stats.nlargest(5, 'Assists')[
        ['nombre', 'posicion', 'Assists', 'Assists_percentile']
    ]
    for idx, row in top_assists.iterrows():
        print(f"  {row['nombre']:20} {row['posicion']:3} - "
              f"Assists: {row['Assists']:5.0f} (Percentile: {row['Assists_percentile']:5.1f}%)")
    
    return player_stats


# ============================================================================
# EXAMPLE 4: Position-Based Analysis
# ============================================================================

def analyze_by_position(player_stats):
    """Analyze metrics by player position"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Position-Based Analysis")
    print("="*70)
    
    positions_to_analyze = ['Goals', 'Total Passes', 'Total Tackles', 'Assists']
    
    print("\nMetrics by Position:")
    for position in player_stats['posicion'].unique():
        if pd.isna(position):
            continue
        
        pos_players = player_stats[player_stats['posicion'] == position]
        
        print(f"\n{position} (n={len(pos_players)}):")
        for metric in positions_to_analyze:
            if metric in pos_players.columns:
                avg = pos_players[metric].mean()
                max_val = pos_players[metric].max()
                print(f"  {metric:20} - Avg: {avg:6.2f}, Max: {max_val:6.2f}")


# ============================================================================
# EXAMPLE 5: League Benchmarking
# ============================================================================

def benchmark_against_league(season="2025-2026"):
    """Calculate and display league benchmarks"""
    print("\n" + "="*70)
    print("EXAMPLE 5: League Benchmarking")
    print("="*70)
    
    # Load standings
    loader = DataLoader("LaLiga", season)
    standings = loader.load_standings()
    
    if standings.empty:
        print("\nNote: Standings data not available in this format")
        return
    
    print("\nLaLiga Top 5 Teams:")
    top_5 = standings.head(5)[['position', 'team', 'wins', 'draws', 'losses', 'points']]
    for idx, row in top_5.iterrows():
        print(f"  {row['position']:2}. {row['team']:25} - "
              f"W:{row['wins']:2} D:{row['draws']:2} L:{row['losses']:2} Pts:{row['points']:3}")
    
    # Calculate league averages
    if 'goals_for' in standings.columns:
        avg_goals = standings['goals_for'].mean()
        avg_goals_against = standings['goals_against'].mean()
        print(f"\nLeague Averages:")
        print(f"  Goals For: {avg_goals:.2f}")
        print(f"  Goals Against: {avg_goals_against:.2f}")


# ============================================================================
# EXAMPLE 6: Tactical Metric Calculations
# ============================================================================

def calculate_tactical_metrics(player_stats):
    """Calculate advanced tactical metrics"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Tactical Metrics")
    print("="*70)
    
    # Get team average
    team_stats = TacticalMetricsCalculator.calculate_team_averages(player_stats)
    
    # Calculate pressing intensity (PPDA proxy)
    if 'Total Passes' in team_stats and 'Total Tackles' in team_stats:
        ppda = TacticalMetricsCalculator.calculate_pressing_intensity(team_stats)
        if ppda:
            print(f"\nPressing Intensity (PPDA): {ppda:.2f}")
            if ppda < 4.0:
                print("  → High aggressive pressing")
            elif ppda < 6.0:
                print("  → Moderate pressing")
            else:
                print("  → Passive defensive block")
    
    # Tactical style classification
    style = TacticalMetricsCalculator.classify_tactical_style(team_stats)
    print(f"\nTactical Style: {style}")
    
    # Key players
    print("\nKey Players (by Total Shots):")
    key_players = TacticalMetricsCalculator.identify_key_players(
        player_stats,
        'Total Shots',
        top_n=5
    )
    for idx, row in key_players.iterrows():
        print(f"  {row['nombre']:20} ({row['posicion']:3}) - {row['Total Shots']:.0f} shots")


# ============================================================================
# EXAMPLE 7: Export Processed Data
# ============================================================================

def export_processed_data(player_stats, output_dir="./processed_data"):
    """Export processed data to CSV for dashboard"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Exporting Processed Data")
    print("="*70)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Export full stats
    rm_export = player_stats[[
        'nombre', 'posicion', 'dorsal', 'Goals', 'Assists', 'Total Passes',
        'Total Shots', 'Total Tackles', 'Interceptions', 'Recoveries',
        'Goals_percentile', 'Assists_percentile', 'Total Passes_percentile'
    ]].copy()
    
    export_file = output_path / "real_madrid_stats.csv"
    rm_export.to_csv(export_file, index=False)
    print(f"\n✓ Exported to: {export_file}")
    
    # Export position summary
    position_summary = player_stats.groupby('posicion').agg({
        'Goals': ['mean', 'max', 'sum'],
        'Assists': ['mean', 'max', 'sum'],
        'Total Passes': 'mean',
        'Total Tackles': 'mean',
    }).round(2)
    
    position_file = output_path / "position_summary.csv"
    position_summary.to_csv(position_file)
    print(f"✓ Exported to: {position_file}")
    
    return output_path


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("FOOTBALL DATA PREPROCESSING EXAMPLES")
    print("Real Madrid Tactical Dashboard Data Preparation")
    print("="*70)
    
    try:
        # Example 1: Load data
        rm_stats = load_and_clean_real_madrid_data()
        
        # Example 2: Team metrics
        team_avg = calculate_team_metrics(rm_stats)
        
        # Example 3: Percentiles
        rm_stats = calculate_percentiles(rm_stats)
        
        # Example 4: Position analysis
        analyze_by_position(rm_stats)
        
        # Example 5: League benchmarking
        benchmark_against_league()
        
        # Example 6: Tactical metrics
        calculate_tactical_metrics(rm_stats)
        
        # Example 7: Export
        output_path = export_processed_data(rm_stats)
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"\n✓ Successfully processed Real Madrid player data")
        print(f"✓ Calculated {rm_stats.shape[0]} player records")
        print(f"✓ Generated {rm_stats.shape[1]} metrics per player")
        print(f"✓ Exported processed files to: {output_path}")
        print(f"\nNext steps:")
        print(f"  1. Run dashboard: python app/app.py")
        print(f"  2. Navigate to http://localhost:8050")
        print(f"  3. Explore Real Madrid analytics")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
