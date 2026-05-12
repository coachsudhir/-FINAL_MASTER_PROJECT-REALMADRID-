"""
Quick Start Guide for Real Madrid Tactical Dashboard
"""

# ============================================================================
# STEP 1: INSTALLATION
# ============================================================================

"""
Prerequisites:
- Python 3.8+
- pip or conda
- ~500MB free disk space

Installation Steps:

1. Navigate to project directory:
   cd /Users/sudhirdahiya/Downloads/FINAL_MASTER_PROJECT\(REALMADRID\)/dashboard

2. Create virtual environment (recommended):
   python3 -m venv venv
   source venv/bin/activate

3. Install dependencies:
   pip install -r requirements.txt

4. Verify installation:
   python -c "import dash; import plotly; print('Success!')"
"""

# ============================================================================
# STEP 2: RUN DASHBOARD
# ============================================================================

"""
From dashboard directory:

Development Mode (with hot reload):
   cd app
   python app.py

Then open browser to: http://localhost:8050

To stop: Press Ctrl+C in terminal
"""

# ============================================================================
# STEP 3: NAVIGATION
# ============================================================================

"""
Dashboard Pages (via sidebar):

1. Home - Overview KPIs and team snapshot
   - Last 5 matches
   - League standings
   - Tactical identity
   - Performance trends

2. Match Analysis - Detailed match breakdown
   - Match selector
   - Shot maps and xG
   - Possession timeline
   - Passing networks
   - Player performance

3. Player Analysis - Individual player metrics
   - Player selector
   - Radar chart comparison
   - Percentile rankings
   - Performance trends
   - Heat maps

4. Tactical Phases - Offensive/Defensive breakdown
   - Phase selector (Offensive/Defensive/Transitions)
   - Match filter
   - Specialized KPIs per phase
   - Tactical visualizations

5. Opponent Analysis - Opposition scouting
   - Opponent selector
   - Tactical profile
   - Key players and threat assessment
   - Head-to-head history
   - Set piece analysis

6. Benchmarking - League comparisons
   - Real Madrid vs average
   - League rankings
   - Tactical positioning map
   - Metric comparisons
"""

# ============================================================================
# STEP 4: USING FILTERS
# ============================================================================

"""
Global Filters (Top Left Sidebar):
- Season: 2024-2025 or 2025-2026
- Competition: LaLiga, Copa del Rey, Champions League

Page-Specific Filters:
- Match Analysis: Date range, competition, home/away
- Player Analysis: Player, position, competition, minutes
- Opponent Analysis: Opponent, season, sample size
- Benchmarking: Comparison group, metric category

Filters are interactive - change them to update visualizations
"""

# ============================================================================
# STEP 5: UNDERSTANDING METRICS
# ============================================================================

"""
KEY TACTICAL METRICS:

Possession
- Possession %: Ball control percentage
- Pass Success: % of completed passes
- Progressive Passes: Passes moving ball forward

Attacking
- xG: Expected Goals (shot probability)
- xA: Expected Assists (assist probability)
- Key Passes: Passes directly before shots
- Zone 14: Central area where chances created

Defensive
- PPDA: Passes Per Defensive Action (lower = aggressive pressing)
- Tackles+Int: Defensive actions per 90 minutes
- Shots Conceded: Number of opponent shots
- Goals Conceded: Number of goals against

Transitions
- Counter-Attack Goals: Scoring from transitions
- Recovery Time: Time to regain possession
- Transition Threat: Danger value of counter-attacks
"""

# ============================================================================
# STEP 6: READING VISUALIZATIONS
# ============================================================================

"""
Radar Charts:
- Multiple dimensions of tactical profile
- Real Madrid (blue) vs comparison (grey)
- Larger area = better performance

Bar Charts:
- League comparisons
- Hover for exact values
- Real Madrid highlighted in green

Scatter Plots:
- Tactical positioning (e.g., possession vs pressing)
- Each dot = team
- Real Madrid = white star

Line Charts:
- Performance trends over time
- Blue line = metric value
- Green area = rolling average

Heatmaps:
- Field positioning density
- Red = high frequency
- Blue = low frequency
- Shows where actions concentrate
"""

# ============================================================================
# STEP 7: COMMON TASKS
# ============================================================================

"""
Task: Compare Real Madrid vs Barcelona Tactical Style
Steps:
1. Go to Opponent Analysis
2. Select "Barcelona" from dropdown
3. Review Tactical Profile radar
4. Check Key Strengths & Weaknesses section
5. View head-to-head history

Task: Analyze Vinícius Jr Performance
Steps:
1. Go to Player Analysis
2. Select "Vinícius Jr (LW)"
3. View Radar Chart vs league average
4. Check Percentile Ranking
5. Review Performance Trends (last 10 matches)

Task: Check League Benchmarking
Steps:
1. Go to Benchmarking
2. Select "vs League Average"
3. Choose metric category (Possession, Attacking, etc.)
4. Review league standings
5. Check positioning map for tactical identity

Task: Scout Match Preparation
Steps:
1. Go to Opponent Analysis
2. Select upcoming opponent
3. Identify key players and threat level
4. Check pressing tendencies and defensive vulnerabilities
5. View set piece execution
6. Note formation and tactical approach
"""

# ============================================================================
# STEP 8: TROUBLESHOOTING
# ============================================================================

"""
Problem: Dashboard won't start
Solution: 
  - Check Python version: python --version (must be 3.8+)
  - Verify pip: pip --version
  - Reinstall requirements: pip install -r requirements.txt

Problem: "Port 8050 already in use"
Solution:
  - Find process: lsof -i :8050
  - Kill process: kill -9 <PID>
  - Or change port in app.py (bottom of file)

Problem: Data not loading
Solution:
  - Check data path in config.py
  - Verify files exist in correct directories
  - Check file permissions

Problem: Slow performance
Solution:
  - Close other browser tabs
  - Use "Last 5" sample size instead of "Season"
  - Reduce browser extensions
  - Clear browser cache

Problem: Charts not displaying
Solution:
  - Refresh browser (Ctrl+R or Cmd+R)
  - Clear browser cache
  - Check JavaScript console for errors (F12)
  - Try different browser
"""

# ============================================================================
# STEP 9: CUSTOMIZATION
# ============================================================================

"""
Change Theme Colors:
- Edit app/config.py
- Look for COLOR_SCHEME dictionary
- Update hex values for colors
- Example: '#3b82f6' = blue, '#10b981' = green

Add New Metric:
- Update data_loader.py with calculation
- Add to visualization.py for plotting
- Include in relevant page

Change Filter Options:
- Edit page layout (e.g., pages/home.py)
- Modify dcc.Dropdown options
- Update callback logic

Add New Page:
1. Create file in pages/ directory
2. Define layout() function
3. Add route in app.py
4. Add navigation link in sidebar
"""

# ============================================================================
# STEP 10: ADVANCED USAGE
# ============================================================================

"""
Accessing Data Programmatically:

from app.utils import DataLoader

loader = DataLoader("LaLiga", "2025-2026")

# Load team data
team_stats = loader.load_team_player_stats("Real_Madrid_CF")

# Load standings
standings = loader.load_standings()

# Load matches
matches = loader.load_matches_data()

# Calculate metrics
from app.utils import TacticalMetricsCalculator

percentiles = TacticalMetricsCalculator.calculate_player_percentiles(
    team_stats, 
    ['Goals', 'Assists', 'Passes']
)

# Benchmarking
from app.utils import BenchmarkCalculator

percentile = BenchmarkCalculator.calculate_percentile_rank(
    value=61.5,  # possession
    league_distribution=[55, 52, 48, ...]
)
"""

# ============================================================================
# KEYBOARD SHORTCUTS
# ============================================================================

"""
Browser:
- F12: Developer Tools
- Ctrl+F: Find on page
- Ctrl+R: Refresh page
- Ctrl+Shift+R: Hard refresh (clear cache)

Dashboard:
- Click filter dropdown: Change selection
- Hover chart: See detailed tooltip
- Click chart legend: Toggle data series
- Drag on axis: Zoom in
- Double-click: Reset zoom
"""

# ============================================================================
# HELP RESOURCES
# ============================================================================

"""
Documentation Files:
- README.md: Full project documentation
- config.py: Configuration and constants
- data_loader.py: Data loading functions
- visualization.py: Chart creation functions
- tactical_classifier.py: Tactical modeling

Key Functions:
- DataLoader: Load data from CSV/JSON
- TacticalMetricsCalculator: Calculate metrics
- BenchmarkCalculator: League comparisons
- RadarChart: Multi-dimensional profiles
- FootballPitch: Pitch visualizations

External Resources:
- Dash Documentation: https://dash.plotly.com
- Plotly Documentation: https://plotly.com/python/
- Pandas Documentation: https://pandas.pydata.org/docs/
- Football Analytics Concepts: Search StatsBomb or Opta Sports
"""

# ============================================================================
# BEST PRACTICES
# ============================================================================

"""
1. Data Management
   - Keep raw data in original directories
   - Don't modify source CSV files
   - Use cache for frequently accessed data

2. Dashboard Usage
   - Start with Home page for overview
   - Use filters to narrow analysis
   - Cross-reference between pages
   - Use benchmarking for context

3. Tactical Analysis
   - Compare metrics to league averages
   - Look for patterns across multiple matches
   - Consider context (opponent quality, injuries)
   - Validate observations with visualizations

4. Performance
   - Use appropriate time samples
   - Avoid analyzing single matches in isolation
   - Consider rolling averages for trends
   - Account for sample size in comparisons

5. Interpretation
   - Always check percentile rankings
   - Use contextual descriptions
   - Compare to historical performance
   - Consider external factors (injuries, tactics changes)
"""

print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║         REAL MADRID TACTICAL & PERFORMANCE DASHBOARD                      ║
║                      Quick Start Complete!                                ║
║                                                                           ║
║  To start dashboard:                                                      ║
║  1. cd dashboard/app                                                      ║
║  2. python app.py                                                         ║
║  3. Open http://localhost:8050                                            ║
║                                                                           ║
║  For full documentation, see README.md                                   ║
╚═══════════════════════════════════════════════════════════════════════════╝
""")
