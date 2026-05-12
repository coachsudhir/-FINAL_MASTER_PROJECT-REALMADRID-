"""
Visualization Utilities and Components
Football-specific visualizations using Plotly and mplsoccer
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from config import COLOR_SCHEME, DARK_TEMPLATE, PITCH

# ============================================================================
# FOOTBALL PITCH VISUALIZATION
# ============================================================================

class FootballPitch:
    """Create football pitch templates for visualizations"""
    
    @staticmethod
    def create_pitch_background(fig, pitch_type='full'):
        """
        Add pitch markings to figure
        
        Args:
            fig: Plotly figure
            pitch_type: 'full', 'half', or 'box'
        """
        if pitch_type == 'full':
            x_range = [0, PITCH['length']]
            y_range = [0, PITCH['width']]
            center_x = PITCH['center_line']
            
            # Center circle
            circle = go.Scatter(
                x=[center_x + 9.15*np.cos(t) for t in np.linspace(0, 2*np.pi, 100)],
                y=[PITCH['width']/2 + 9.15*np.sin(t) for t in np.linspace(0, 2*np.pi, 100)],
                fill='toself',
                fillcolor='rgba(0,0,0,0)',
                line=dict(color=COLOR_SCHEME['text_secondary'], width=1),
                hoverinfo='skip',
                showlegend=False,
            )
            
            # Penalty boxes and goal lines
            shapes = [
                # Left box
                dict(type='rect', x0=0, y0=18, x1=16.5, y1=61.5, 
                     line=dict(color=COLOR_SCHEME['text_secondary'], width=1),
                     fillcolor='rgba(0,0,0,0)'),
                # Right box
                dict(type='rect', x0=PITCH['length']-16.5, y0=18, x1=PITCH['length'], y1=61.5,
                     line=dict(color=COLOR_SCHEME['text_secondary'], width=1),
                     fillcolor='rgba(0,0,0,0)'),
                # Left goal area
                dict(type='rect', x0=0, y0=27.3, x1=5.5, y1=52.7,
                     line=dict(color=COLOR_SCHEME['text_secondary'], width=1),
                     fillcolor='rgba(0,0,0,0)'),
                # Right goal area
                dict(type='rect', x0=PITCH['length']-5.5, y0=27.3, x1=PITCH['length'], y1=52.7,
                     line=dict(color=COLOR_SCHEME['text_secondary'], width=1),
                     fillcolor='rgba(0,0,0,0)'),
                # Center line
                dict(type='line', x0=center_x, y0=0, x1=center_x, y1=PITCH['width'],
                     line=dict(color=COLOR_SCHEME['text_secondary'], width=1)),
                # Halfway circle
                dict(type='circle', x0=center_x-9.15, y0=PITCH['width']/2-9.15,
                     x1=center_x+9.15, y1=PITCH['width']/2+9.15,
                     line=dict(color=COLOR_SCHEME['text_secondary'], width=1),
                     fillcolor='rgba(0,0,0,0)'),
            ]
            
            fig.add_trace(circle)
            for shape in shapes:
                fig.add_shape(shape, layer='below')
            
            fig.update_xaxes(range=x_range, showgrid=False, zeroline=False)
            fig.update_yaxes(range=y_range, showgrid=False, zeroline=False)
        
        fig.update_layout(**DARK_TEMPLATE['layout'])
        return fig
    
    @staticmethod
    def plot_heatmap(df_positions, title="Heatmap", colorscale='Hot'):
        """
        Create a heatmap on football pitch
        
        Args:
            df_positions: DataFrame with x, y coordinates
            title: Heatmap title
            colorscale: Plotly colorscale name
        """
        # Create 2D histogram
        fig = go.Figure()
        
        fig.add_trace(go.Histogram2d(
            x=df_positions.get('x', []),
            y=df_positions.get('y', []),
            nbinsx=12,
            nbinsy=8,
            colorscale=colorscale,
            hovertemplate='<b>Position</b><br>X: %{x:.1f}<br>Y: %{y:.1f}<br>Count: %{z}',
        ))
        
        fig.update_layout(
            title=f"{title}",
            xaxis_title="",
            yaxis_title="",
            **DARK_TEMPLATE['layout']
        )
        
        FootballPitch.create_pitch_background(fig, 'full')
        return fig


# ============================================================================
# RADAR CHARTS
# ============================================================================

class RadarChart:
    """Create radar charts for tactical comparisons"""
    
    @staticmethod
    def create_player_radar(player_stats, position, league_percentiles):
        """
        Create player radar chart
        
        Args:
            player_stats: Player statistics dictionary
            position: Player position
            league_percentiles: League percentile benchmarks
        """
        categories = ['Passing', 'Shooting', 'Defense', 'Physical', 'Dribbling']
        
        values = [
            player_stats.get('passing_score', 50),
            player_stats.get('shooting_score', 50),
            player_stats.get('defense_score', 50),
            player_stats.get('physical_score', 50),
            player_stats.get('dribbling_score', 50),
        ]
        
        fig = go.Figure()
        
        # Player stats
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=f'{player_stats.get("nombre", "Player")} ({position})',
            line_color=COLOR_SCHEME['accent_blue'],
            fillcolor='rgba(59, 130, 246, 0.3)',
        ))
        
        # League average (if provided)
        if league_percentiles:
            league_values = [
                league_percentiles.get('passing', 50),
                league_percentiles.get('shooting', 50),
                league_percentiles.get('defense', 50),
                league_percentiles.get('physical', 50),
                league_percentiles.get('dribbling', 50),
            ]
            fig.add_trace(go.Scatterpolar(
                r=league_values,
                theta=categories,
                fill='toself',
                name='League Average',
                line_color=COLOR_SCHEME['text_secondary'],
                fillcolor='rgba(160, 174, 192, 0.1)',
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    gridcolor=COLOR_SCHEME['border'],
                    gridwidth=1,
                ),
                angularaxis=dict(
                    gridcolor=COLOR_SCHEME['border'],
                ),
                bgcolor=COLOR_SCHEME['background'],
            ),
            **DARK_TEMPLATE['layout']
        )
        
        return fig
    
    @staticmethod
    def create_team_radar(team_stats, rivals_stats=None):
        """Create team tactical radar chart"""
        categories = [
            'Possession',
            'Pressing',
            'Transitions',
            'Final Third',
            'Defensive Recovery',
            'Set Pieces',
        ]
        
        team_values = [
            team_stats.get('possession_score', 50),
            team_stats.get('pressing_score', 50),
            team_stats.get('transition_score', 50),
            team_stats.get('final_third_score', 50),
            team_stats.get('defense_score', 50),
            team_stats.get('set_piece_score', 50),
        ]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=team_values,
            theta=categories,
            fill='toself',
            name='Real Madrid',
            line_color=COLOR_SCHEME['real_madrid'],
            fillcolor='rgba(255, 255, 255, 0.2)',
        ))
        
        if rivals_stats:
            for i, rival_stats in enumerate(rivals_stats):
                rival_values = [
                    rival_stats.get('possession_score', 50),
                    rival_stats.get('pressing_score', 50),
                    rival_stats.get('transition_score', 50),
                    rival_stats.get('final_third_score', 50),
                    rival_stats.get('defense_score', 50),
                    rival_stats.get('set_piece_score', 50),
                ]
                fig.add_trace(go.Scatterpolar(
                    r=rival_values,
                    theta=categories,
                    fill='toself',
                    name=f'Rival {i+1}',
                    line_color=COLOR_SCHEME['accent_red'],
                    fillcolor='rgba(239, 68, 68, 0.1)',
                ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    gridcolor=COLOR_SCHEME['border'],
                ),
                angularaxis=dict(
                    gridcolor=COLOR_SCHEME['border'],
                ),
                bgcolor=COLOR_SCHEME['background'],
            ),
            **DARK_TEMPLATE['layout']
        )
        
        return fig


# ============================================================================
# TREND AND TIME SERIES CHARTS
# ============================================================================

def create_performance_trend(df, metric, player_name, window=5):
    """
    Create rolling performance trend chart
    
    Args:
        df: DataFrame with time-indexed data
        metric: Metric column to plot
        player_name: Player name for title
        window: Rolling window size
    """
    fig = go.Figure()
    
    # Raw values
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df[metric],
        mode='markers',
        name=f'{metric} (Actual)',
        marker=dict(color=COLOR_SCHEME['accent_blue'], size=6, opacity=0.6),
    ))
    
    # Rolling average
    rolling_avg = df[metric].rolling(window=window).mean()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=rolling_avg,
        mode='lines',
        name=f'{metric} ({window}-match avg)',
        line=dict(color=COLOR_SCHEME['accent_green'], width=2),
    ))
    
    fig.update_layout(
        title=f"{player_name} - {metric} Trend",
        xaxis_title="Match",
        yaxis_title=metric,
        hovermode='x unified',
        **DARK_TEMPLATE['layout']
    )
    
    return fig


def create_percentile_chart(player_value, league_percentiles, metric_name):
    """
    Create percentile comparison bar chart
    
    Args:
        player_value: Player's value
        league_percentiles: Dictionary of percentile values
        metric_name: Name of metric
    """
    fig = go.Figure()
    
    percentiles = list(league_percentiles.values())
    labels = list(league_percentiles.keys())
    
    colors = [COLOR_SCHEME['accent_blue'] if label == 'Player' 
              else COLOR_SCHEME['accent_green'] for label in labels]
    
    fig.add_trace(go.Bar(
        x=labels,
        y=percentiles,
        marker=dict(color=colors),
        text=[f'{p:.0f}%' for p in percentiles],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Percentile: %{y:.1f}%<extra></extra>',
    ))
    
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color=COLOR_SCHEME['text_secondary'],
        annotation_text="League Median",
    )
    
    fig.update_layout(
        title=f"{metric_name} Percentile Comparison",
        yaxis_title="Percentile (%)",
        yaxis=dict(range=[0, 100]),
        showlegend=False,
        **DARK_TEMPLATE['layout']
    )
    
    return fig


# ============================================================================
# PASS MAPS AND NETWORK VISUALIZATIONS
# ============================================================================

def create_pass_map(passes_df, player_name):
    """
    Create pass map showing completed passes
    
    Args:
        passes_df: DataFrame with pass locations
        player_name: Player name
    """
    fig = go.Figure()
    
    # Completed passes
    fig.add_trace(go.Scatter(
        x=passes_df[passes_df['outcome'] == 'Successful']['x'],
        y=passes_df[passes_df['outcome'] == 'Successful']['y'],
        mode='markers',
        marker=dict(
            size=6,
            color=COLOR_SCHEME['accent_green'],
            opacity=0.7,
        ),
        name='Completed Pass',
        hovertemplate='<b>Pass Start</b><br>X: %{x:.1f}<br>Y: %{y:.1f}',
    ))
    
    # Incomplete passes
    fig.add_trace(go.Scatter(
        x=passes_df[passes_df['outcome'] != 'Successful']['x'],
        y=passes_df[passes_df['outcome'] != 'Successful']['y'],
        mode='markers',
        marker=dict(
            size=5,
            color=COLOR_SCHEME['accent_red'],
            opacity=0.4,
        ),
        name='Incomplete Pass',
        hovertemplate='<b>Pass Start</b><br>X: %{x:.1f}<br>Y: %{y:.1f}',
    ))
    
    fig.update_layout(
        title=f"{player_name} - Pass Map",
        **DARK_TEMPLATE['layout']
    )
    
    FootballPitch.create_pitch_background(fig, 'full')
    return fig


# ============================================================================
# TACTICAL HEATMAPS
# ============================================================================

def create_defensive_heatmap(defense_actions_df):
    """Create heatmap of defensive actions"""
    fig = go.Figure()
    
    fig.add_trace(go.Histogram2d(
        x=defense_actions_df.get('x', []),
        y=defense_actions_df.get('y', []),
        nbinsx=12,
        nbinsy=8,
        colorscale='Reds',
        hovertemplate='<b>Defensive Action</b><br>X: %{x:.1f}<br>Y: %{y:.1f}<br>Count: %{z}',
    ))
    
    fig.update_layout(
        title="Defensive Action Heatmap",
        **DARK_TEMPLATE['layout']
    )
    
    FootballPitch.create_pitch_background(fig, 'full')
    return fig


# ============================================================================
# LEAGUE COMPARISON VISUALIZATIONS
# ============================================================================

def create_league_comparison_scatter(teams_data, metric_x, metric_y):
    """
    Create scatter plot comparing teams
    
    Args:
        teams_data: List of dicts with team data
        metric_x: X-axis metric
        metric_y: Y-axis metric
    """
    df = pd.DataFrame(teams_data)
    
    fig = px.scatter(
        df,
        x=metric_x,
        y=metric_y,
        hover_name='team',
        color='team',
        title=f"{metric_x} vs {metric_y}",
        template="plotly_dark",
    )
    
    # Highlight Real Madrid
    if any(df['team'].str.contains('Real Madrid', case=False, na=False)):
        fig.add_scatter(
            x=[df[df['team'].str.contains('Real Madrid', case=False)][metric_x].values[0]],
            y=[df[df['team'].str.contains('Real Madrid', case=False)][metric_y].values[0]],
            mode='markers',
            marker=dict(size=15, color='white', symbol='star'),
            name='Real Madrid',
            hoverinfo='skip',
        )
    
    fig.update_layout(**DARK_TEMPLATE['layout'])
    return fig


# ============================================================================
# KPI INDICATORS
# ============================================================================

def create_kpi_card(title, value, unit="", comparison=None, color=COLOR_SCHEME['accent_blue']):
    """
    Create KPI indicator card
    
    Args:
        title: KPI title
        value: KPI value
        unit: Unit of measurement
        comparison: Previous value for comparison
        color: Color of indicator
    """
    change_text = ""
    if comparison is not None:
        change = value - comparison
        change_pct = (change / abs(comparison)) * 100 if comparison != 0 else 0
        direction = "↑" if change > 0 else "↓" if change < 0 else "="
        change_text = f"<br><span style='font-size:0.8em; color:{color}'>{direction} {change_pct:+.1f}%</span>"
    
    return {
        "title": title,
        "value": f"{value:.2f}{unit}",
        "change": change_text,
        "color": color,
    }


def create_gauge_chart(value, min_val=0, max_val=100, title="Metric", color=COLOR_SCHEME['accent_blue']):
    """Create gauge chart for metric visualization"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': color},
            'steps': [
                {'range': [min_val, max_val * 0.33], 'color': "rgba(239, 68, 68, 0.3)"},
                {'range': [max_val * 0.33, max_val * 0.66], 'color': "rgba(251, 191, 36, 0.3)"},
                {'range': [max_val * 0.66, max_val], 'color': "rgba(16, 185, 129, 0.3)"},
            ],
        }
    ))
    
    fig.update_layout(**DARK_TEMPLATE['layout'])
    return fig
