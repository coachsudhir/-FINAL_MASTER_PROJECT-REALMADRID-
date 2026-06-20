# Real Madrid Tactical & Player Performance Dashboard

**Master's Final Project - Football Data Science & Analytics**

A professional football tactical analytics dashboard built with Python, Dash, and Plotly. This dashboard analyzes Real Madrid's tactical identity, match behavior, player performance, and opponent tendencies using comprehensive football event and statistical data.

## Overview

This dashboard replicates professional football analysis workflows used by elite clubs for:
- Match preparation and tactical planning
- Opposition scouting and vulnerability analysis
- Tactical evaluation and performance metrics
- Player performance analysis and comparisons
- Post-match reporting and trend analysis
- Benchmarking against league standards and rivals
- Recruitment support through comparative analytics

## Features

### 🏠 Home Page
- **Overview KPIs**: Goals, possession, xG, league position, win rate
- **Recent Matches Summary**: Last 5 matches with results and competition
- **Tactical Identity Snapshot**: Current formation, pressing style, possession approach
- **League Standings**: Top 5 teams with points and goal difference
- **Performance Trends**: 5-week rolling trends for goals, xG, and possession
- **Team Radar**: Tactical profile comparison (possession, pressing, transitions, final third, defense, set pieces)

### 📊 Match Analysis
- **Match Selector**: Choose specific matches or date ranges
- **Shot Maps**: Real Madrid vs opponent shot locations and quality
- **Possession Timeline**: Possession % evolution throughout match
- **Passing Networks**: Player connections and pass zones
- **Tactical Phases**: Breakdown of offensive, defensive, and transition moments
- **Player Performance**: Top performers with key statistics

### 👤 Player Analysis
- **Player Selection**: Filter by individual player
- **Statistical Radar**: 6-dimensional tactical profile (passing, shooting, defense, physical, dribbling, positioning)
- **Percentile Rankings**: Position within league distribution
- **Performance Trends**: Goals, xG, and key passes over last 10 matches
- **Heat Maps**: Field positioning and touch density
- **Detailed Statistics**: All-match stats with league comparisons

### ⚔️ Tactical Phases Analysis
Divides football into four distinct tactical moments:

**A. Offensive Moment**
- Build-up structure and rhythm
- Progression style and patterns
- Flank vs central usage
- Chance creation metrics
- xG chain flow
- Zone 14 occupation
- Crossing tendencies

**B. Offensive Transition**
- Fast break efficiency
- Transition xThreat generation
- Time-to-first-shot metrics
- Verticality and directness
- Transition origin/destination maps

**C. Defensive Moment**
- Pressing intensity (PPDA)
- Defensive structure and compactness
- Defensive line height
- Tackle and interception zones
- Aerial duel success rates
- Vulnerable zones analysis

**D. Defensive Transition**
- Counter-pressing behavior
- Recovery times and distances
- Immediate reaction metrics
- Compactness after turnover

### 🎯 Opponent Analysis
- **Opponent Selection**: Compare any team in the league
- **Tactical Profile**: Full radar comparison
- **Key Strengths & Weaknesses**: Automated tactical assessment
- **Top Players**: Most dangerous players with threat levels
- **Head-to-Head History**: Last 5 meetings with xG and possession
- **Set Piece Analysis**: Attacking and defending set piece tendencies

### 📈 Benchmarking
- **League Comparisons**: Real Madrid vs league average, top 4, rivals
- **Standings Table**: Full league table with tactical metrics
- **Possession Dominance**: Bar chart comparison
- **Pressing Intensity (PPDA)**: Lower = more aggressive
- **Goal Scoring Efficiency**: Goals vs xG comparisons
- **Progressive Actions**: Passing and carrying metrics
- **Defensive Solidity**: Goals conceded and defensive actions
- **Tactical Positioning Map**: 2D scatter showing team tactical identity

## Technical Architecture

### Project Structure
```
<repo root>
├── wsgi.py                      # Gunicorn entrypoint (loads dashboard/app)
├── render.yaml                  # Render deployment blueprint
├── requirements.txt            # Python dependencies (Render installs this)
├── README.md                   # This file
└── dashboard/
    ├── app/
    │   ├── app.py               # Main Dash application (exposes `server`)
    │   ├── config.py            # Configuration + data-root resolver
    │   ├── pages/               # Multi-page layouts + callbacks
    │   │   ├── home.py
    │   │   ├── match_analysis.py
    │   │   ├── player_analysis.py
    │   │   ├── tactical_phases.py
    │   │   ├── opponent_analysis.py
    │   │   └── benchmarking.py
    │   ├── utils/
    │   │   ├── data_loader.py    # Opta event parsing, xG, KPIs (single source)
    │   │   ├── data_helpers.py   # Match/team/season helpers
    │   │   └── phase_scoring.py  # Tactical phase model
    │   ├── models/              # Tactical classifier
    │   └── assets/              # custom.css, crest, fonts
    └── data/                    # CANONICAL clean dataset (see Data Structure)
```

> **Single source of truth:** the only application code is `dashboard/app/`, and
> the only dataset is `dashboard/data/`. There are no duplicate app/data copies.

### Technology Stack
- **Framework**: Dash + dash-bootstrap-components (reactive web app)
- **Visualizations**: Plotly (interactive charts, pitch maps)
- **Data Processing**: Pandas, NumPy
- **Geometry**: SciPy (`ConvexHull` for team-shape on position maps)
- **Server**: Gunicorn (production WSGI)

## Installation & Setup

### Prerequisites
- Python 3.11 (matches the Render runtime)
- pip

### Run locally

1. **Clone the repository**
```bash
git clone https://github.com/coachsudhir/-FINAL_MASTER_PROJECT-REALMADRID-.git
cd -FINAL_MASTER_PROJECT-REALMADRID-
```

2. **Create a virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the dashboard** (either option works)
```bash
# Option A — run the app module directly (dev server, hot reload)
cd dashboard/app && python app.py

# Option B — run exactly as production does (from the repo root)
gunicorn --bind 0.0.0.0:8050 wsgi:server
```

5. **Access the dashboard**
- Open `http://localhost:8050`
- Navigate via the top menu (Overview, Match Analysis, Player Analysis,
  Tactical Phases, Opponent Scout, Benchmarking)
- Use the global Competition / Season filters in the header

> The data root is auto-detected (it resolves to `dashboard/data`). To point at a
> different dataset, set the `DATA_ROOT` environment variable.

## Configuration

### config.py
Main configuration file with:
- **Color Scheme**: Dark elite analytics theme
  - Background: Deep navy (#0a0e27)
  - Accent: Blue (#3b82f6), Green (#10b981), Red (#ef4444)
- **Data Paths**: Pointers to data directories
- **Competitions**: LaLiga, Copa del Rey, Champions League
- **Tactical Thresholds**: PPDA, possession, xThreat ranges
- **Pitch Dimensions**: Standard 120x80 football pitch
- **Position Groups**: Goalkeeper, Defender, Midfielder, Forward

## Data Structure

### Expected Data Format
The dashboard expects:
- **CSV Files**: Player statistics with columns like Goals, Assists, Passes, xG, xA, Tackles, etc.
- **JSON Files**: Match metadata, standings, squad lists
- **Directory Structure**: `/Competition/Season/equipos/Team/` for team data

### Key Datasets
```
LaLiga/
├── 2024-2025/
│   ├── equipos/
│   │   ├── Real_Madrid_CF/
│   │   │   ├── *_jugadores.csv
│   │   │   └── *_jugadores_seasonstats.csv
│   │   └── [Other teams...]
│   ├── jsons/
│   │   ├── matches.json
│   │   ├── standings.json
│   │   └── squads.json
│   └── partidos/
│       └── [Match detail JSON files]
└── 2025-2026/
    └── [Same structure]
```

## Tactical Metrics & Definitions

### Key Performance Indicators

**Possession & Control**
- **Possession %**: Percentage of ball possession
- **Pass Success %**: Percentage of completed passes
- **Progressive Passes**: Passes that move ball 10+ yards toward opponent goal

**Attacking**
- **xG (Expected Goals)**: Sum of shot probabilities
- **xA (Expected Assists)**: Sum of assist probabilities
- **xThreat**: Threat value of actions
- **Key Passes**: Passes directly preceding a shot
- **Final Third Entries**: Actions entering opponent's final third

**Defensive**
- **PPDA**: Passes Allowed Per Defensive Action (lower = more aggressive)
- **Tackles Won**: Successful defensive tackles
- **Interceptions**: Recovered loose balls
- **Defensive Line Height**: Average depth of defensive line
- **Shots Conceded**: Total opponent shots

**Transitions**
- **Transition xThreat**: Threat generated from transitions
- **Recovery Time**: Time to regain possession after losing it
- **Counter-Attack Success**: Goals/shots from counter-attacks

### Tactical Classifications

Teams classified by style profile:
- **Possession Dominant**: >55% possession, controlled play
- **Direct**: <45% possession, long ball strategy
- **High Pressing**: PPDA <4.0, aggressive ball recovery
- **Mid Block**: PPDA 5-7, moderate pressing distance
- **Low Block**: PPDA >8.0, deep defensive line
- **Transition-Focused**: High counter-attack threat
- **Combinative**: Short-passing, intricate movement

## Benchmarking & Contextual Analysis

All metrics include contextual interpretation:

### League Context
- Real Madrid vs LaLiga average
- Real Madrid vs Top 4 average
- Real Madrid vs Bottom 5 average
- Percentile ranking (0-100, 100=best)

### Example Outputs
```
"Real Madrid presses more aggressively than 91% of LaLiga teams (PPDA: 4.2 vs 5.8 avg)"
"Goal-scoring efficiency is 8% above expected (42 goals vs 37.8 xG)"
"Defensive compactness ranks 5th in league (8.2m line height)"
"Possession dominance enables control of game tempo"
```

## Advanced Analytics Features

### Implemented
- Percentile normalization and ranking
- Rolling statistics for trend analysis
- PPDA calculation (proxy pressing metric)
- Position-specific player comparisons
- Goal difference analysis
- xG chain modeling
- Tactical phase detection

### Future Enhancements
- Machine learning clustering of tactical patterns
- Automated formation detection from positional data
- Player recommendation engine using similarity clustering
- Injury impact analysis on team metrics
- Real-time event tracking integration
- Predictive match outcome models
- Player market value estimation

## Visualization Components

### Chart Types
- **Bar Charts**: League comparisons, seasonal trends
- **Scatter Plots**: Tactical positioning, correlation analysis
- **Radar Charts**: Multi-dimensional tactical profiles
- **Heatmaps**: Positional density and action zones
- **Line Charts**: Performance trends over time
- **Sankey Diagrams**: xG chain flow and attacking sequences
- **Pitch Visualizations**: Shot maps, pass zones, defensive action density

### Interactive Features
- Hover tooltips with detailed statistics
- Clickable filters for dynamic updates
- Tab navigation for drill-down analysis
- Date range selectors for temporal analysis
- Dropdown selections for teams and players
- Animated transitions on metric changes

## Color Theme

**Dark Elite Analytics**
```
Background: #0a0e27 (Deep Navy)
Surface: #1a1f3a
Border: #2d3561
Text Primary: #ffffff (White)
Text Secondary: #a0aec0 (Light Grey)

Accent Colors:
- Blue: #3b82f6 (Tactical)
- Green: #10b981 (Positive/Possession)
- Red: #ef4444 (Danger/Defensive)
- Yellow: #fbbf24 (Warning)
- Orange: #f97316 (Emphasis)
- Purple: #a855f7 (Analysis)
```

## Performance Optimization

### Data Caching
- `@lru_cache` on frequently accessed data
- Session storage for global selections
- Lazy loading of heavy datasets

### Dashboard Efficiency
- Responsive design for mobile/tablet
- Minimal callback triggers
- Efficient Plotly rendering
- CSS optimization for dark theme

## Deployment

### Development
```bash
cd dashboard/app && python app.py     # localhost:8050, hot reload
```

### Production (Gunicorn)
```bash
gunicorn --workers 2 --timeout 120 --bind 0.0.0.0:$PORT wsgi:server
```

### Deploy on Render (Community / Free tier)

The repo ships a `render.yaml` blueprint, so deployment is one click:

1. Push to GitHub (already configured: `origin/main`).
2. In the [Render dashboard](https://dashboard.render.com) → **New → Blueprint**,
   connect this repository. Render reads `render.yaml` automatically.
3. Render provisions a Python web service with:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --workers 2 --timeout 120 --bind 0.0.0.0:$PORT wsgi:server`
   - **Env:** `PYTHON_VERSION=3.11.9`, `DATA_ROOT=/opt/render/project/src/dashboard/data`
4. `autoDeploy: true` — every push to `main` redeploys automatically.
5. The live URL appears as `https://real-madrid-tactical-dashboard.onrender.com`
   (name from `render.yaml`; the exact subdomain is shown in Render).

No manual settings are required — everything is declared in `render.yaml`.
The bundled `dashboard/data` (Real Madrid matches, all competitions/seasons,
verified 0 corrupt) is committed, so no external data source is needed.

### Environment Variables
- `DATA_ROOT` *(optional)* — absolute path to a folder containing
  `LaLiga/`, `Copa del Rey/`, `UEFA Champions League/`. Defaults to the bundled
  `dashboard/data`. Set automatically on Render.

## Troubleshooting

### Common Issues

**Port Already in Use**
```bash
lsof -i :8050  # Find process
kill -9 <PID>  # Kill process
```

**Data Not Loading**
- Check data path in `config.py`
- Verify CSV/JSON file structure
- Check file permissions

**Slow Dashboard**
- Reduce data sample size (use "Last 5/10" instead of "Season")
- Check system resources
- Optimize callback logic

**Missing Metrics**
- Verify all required columns in CSV files
- Check data type conversions (numeric vs string)
- Ensure no NaN values in critical columns

## Future Roadmap

### Phase 2
- [ ] Real-time event data integration
- [ ] Player clustering and similarity analysis
- [ ] Formation detection and tracking
- [ ] Injury impact modeling
- [ ] Recruitment player pool analysis

### Phase 3
- [ ] Machine learning prediction models
- [ ] Natural language match summaries
- [ ] Video highlight integration
- [ ] 3D pitch visualizations
- [ ] Network analysis of passing patterns

### Phase 4
- [ ] Multi-team dashboard comparison
- [ ] Historical trend analysis (3+ seasons)
- [ ] API integration with external data providers
- [ ] Mobile app for remote access
- [ ] Report generation (PDF/PPT exports)

## Contributing

To extend the dashboard:

1. **Add new metric**: Update `TacticalMetricsCalculator` in `utils/data_loader.py`
2. **Create new page**: Add file to `pages/` directory following existing structure
3. **Add visualization**: Add function to `utils/visualization.py`
4. **Update config**: Add constants to `config.py`

## Documentation

### Key Functions

**DataLoader.load_team_player_stats(team_name)**
```python
# Load all season statistics for a team
stats = loader.load_team_player_stats("Real_Madrid_CF")
# Returns: DataFrame with all player statistics
```

**TacticalMetricsCalculator.classify_tactical_style(stats)**
```python
# Classify team tactical approach
style = TacticalMetricsCalculator.classify_tactical_style(team_stats)
# Returns: "Possession Dominant", "High Pressing", etc.
```

**BenchmarkCalculator.calculate_percentile_rank(value, distribution)**
```python
# Get percentile rank within league
percentile = BenchmarkCalculator.calculate_percentile_rank(
    value=61.5,  # Real Madrid possession
    league_distribution=[55, 52, 48, ...]
)
# Returns: 87 (87th percentile)
```

## References

### Football Analytics Concepts
- **PPDA (Passes Per Defensive Action)**: Pressing intensity metric
- **xG (Expected Goals)**: Quality-weighted shot metric
- **xThreat**: Threat value of any action
- **OBV (On-Ball Value)**: Player contribution to team objectives
- **VAEP (Valuing Actions by Estimating Probabilities)**: Action value framework
- **xA (Expected Assists)**: Quality-weighted assist metric

### Data Sources
- Aggregated from football statistics databases
- Player match performances
- Competition standings
- Squad information

## License

**Master's Final Project**
Real Madrid Tactical & Player Performance Dashboard
© 2026 - For Academic Purposes

## Contact & Support

For issues, questions, or suggestions:
- Review documentation first
- Check troubleshooting section
- Consult config.py for customization
- Extend utils modules for new features

---

**Dashboard Version**: 1.0  
**Last Updated**: May 12, 2026  
**Python Version**: 3.8+  
**Dash Version**: 2.14.1  
**Plotly Version**: 5.18.0  

---

### Quick Start Checklist
- [ ] Python 3.8+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Bundled dataset present at `dashboard/data/`
- [ ] Dashboard running (`cd dashboard/app && python app.py`)
- [ ] Accessed at `http://localhost:8050`
- [ ] All pages loading correctly
- [ ] Filters responding to changes

### Performance Targets
- Dashboard load time: <2 seconds
- Page transition: <1 second
- Filter response: <500ms
- Data query: <1 second
- Visualization render: <2 seconds

### Browser Compatibility
- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge
- Mobile browsers (responsive design)

---

**For professional use in elite football clubs, integrate with live data providers (Opta, StatsBomb, Wyscout) for real-time metrics.**
