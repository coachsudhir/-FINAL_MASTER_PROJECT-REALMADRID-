# Real Madrid Tactical Dashboard — Official Platform Documentation

**Project:** Real Madrid Tactical Dashboard
**Student:** Sudhir Dahiya
**Degree:** Master's in Sports Analytics (2025–2026)
**Club of Study:** Real Madrid CF
**Data Source:** Opta Stats Perform — event-level match data (JSON)
**Technology:** Python · Pandas · NumPy · Plotly · Streamlit (Dash analytics core) · Render (cloud deployment)
**Audience:** Master's thesis examiners · football analysts · professional coaches · technical directors · scouts · future developers · first-time users

---

> **How to read this document.** This is reference documentation, not a tutorial. It is organised so that a coach can jump straight to "Defensive Strategy", an examiner can read the "Executive Summary" and "Methodology", and a developer can read "Dashboard Architecture". Every metric is documented with its **definition, formula (where one exists in the code), interpretation, coaching value, and limitations**. Nothing in this document describes a feature that is not actually implemented; where a capability is partial or planned it is labelled explicitly.

---

## 1. Executive Summary

### 1.1 Purpose of the Dashboard

The Real Madrid Tactical Dashboard is an interactive football analytics platform that converts **raw event-level match data** into **tactical intelligence**. In modern elite football, data providers such as Opta Stats Perform record every on-ball action of a match — every pass, shot, tackle, interception, recovery, foul, corner and substitution — each stamped with a player, a team, a timestamp and an `(x, y)` pitch coordinate. A single match produces between roughly 1,500 and 2,000 such events. This volume is far too large to interpret by eye, and far too granular to communicate to a coaching staff in its raw form.

The dashboard exists to close that gap. It ingests the raw event stream, normalises it into a consistent analytical table, computes a transparent suite of football Key Performance Indicators (KPIs), and renders them as interactive maps, charts, radars and tables. The result is a single environment in which an analyst can answer the question that matters most to a coach: **not "did we win?" but "how did we play, and was the performance sustainable?"**

### 1.2 Main Objectives

The platform pursues four explicit objectives:

1. **Quantify tactical behaviour.** Translate Real Madrid's pressing, possession, transition and attacking behaviour into defensible numbers, each traceable to an explicit formula and to observed events.
2. **Segment the match into tactical phases.** Break every match into the four canonical moments of play — offensive moment, defensive transition, defensive moment, offensive transition — and score Real Madrid's effectiveness in each.
3. **Measure performance against expectation.** Compare actual output (goals, results) against chance quality (Expected Goals), separating sustainable performance from short-term variance and finishing luck.
4. **Deliver an interactive decision-support tool.** Provide a reproducible pipeline and an interactive interface that allows analysts and coaches to explore season, match, player, opponent and benchmark views without writing a line of code.

### 1.3 Intended Users

- **Head coaches and assistant coaches** use the dashboard to confirm whether the team executed the intended game model, to identify which phase of play to address in the next training block, and to prepare specifically against an opponent.
- **Performance analysts** use it as a daily working tool: building pre-match opposition reports, conducting post-match reviews, and tracking season-long trends.
- **Technical directors** use the season and benchmarking views to monitor squad performance across competitions and to support strategic decisions.
- **Scouts** use the Opponent Scout module to profile upcoming opponents and to build reference comparisons.
- **Academics and examiners** use it as a worked, fully documented example of applied phase-based football analysis with a transparent methodology.
- **First-time users** can navigate the dashboard intuitively because it is organised by the same mental model coaches already use: a match has a context, an attacking phase, a defensive phase, transitions, and set pieces.

### 1.4 Tactical Philosophy Encoded in the Tool

The dashboard is opinionated in a deliberate, football-literate way. It is built around the principle that **football is best understood as four repeating moments**, not as a single undifferentiated "performance":

- **Offensive Moment (Phase A)** — the team has the ball in a settled situation and is trying to create and score.
- **Defensive Transition (Phase B)** — the team has just lost the ball and is trying to win it back (counter-pressing).
- **Defensive Moment (Phase C)** — the opponent has settled possession and the team must defend its shape.
- **Offensive Transition (Phase D)** — the team has just won the ball back and is trying to attack quickly before the opponent reorganises (the counter-attack).

This four-phase model — standard in elite coaching methodology and in UEFA Pro Licence curricula — is the spine of the dashboard. It is why the platform can describe Real Madrid not as "a good team" but, precisely, as "a possession-dominant side with a world-class transition engine and a selective, economical press."

### 1.5 Football Problems the Dashboard Solves

- **Outcome bias.** A 2–0 win can hide a poor performance (low chance quality, fortunate finishing) or reflect a dominant one. The dashboard's Expected Goals comparison reveals which.
- **The "feel vs fact" gap.** Coaching staff form strong qualitative impressions of a match. The dashboard provides the quantitative evidence to confirm or challenge those impressions (e.g. "we pressed well today" → PPDA of 6.2 vs a season average of 9.5 confirms it).
- **Opposition preparation.** Instead of watching hours of footage blind, an analyst can profile an opponent's pressing intensity, build-up patterns and set-piece tendencies in minutes, then target the video review.
- **Fragmented tooling.** It replaces a patchwork of spreadsheets, isolated notebooks and static slide decks with one consistent, interactive, reproducible environment.
- **Communication.** It turns 2,000 raw events into a handful of legible visuals a coach can absorb in a pre-match meeting.

---

## 2. Dashboard Architecture

### 2.1 Overall Navigation

The dashboard presents a single, persistent **top navigation bar** rendered in Real Madrid's brand navy (`#0b1730`) with a gold accent line. The navigation contains **seven modules**, each represented by an icon and a short label:

1. **🏠 Overview** — season-level context and trends.
2. **📊 Match Analysis** — deep single-match (or match-range) breakdown.
3. **👤 Player Analysis** — individual player performance.
4. **⚔️ Tactical Phases** — pressing, phases and zonal behaviour.
5. **🔭 Opponent Scout** — opposition profiling and scouting.
6. **📈 Benchmarking** — cross-competition and cross-season comparison.
7. **📋 Report** — automated PDF/DOCX report generation.

The currently active module is highlighted in gold; inactive modules are navy with light text. Selecting a module re-renders the main content area beneath the bar while the navigation remains fixed, so the user never loses orientation.

### 2.2 Dashboard Hierarchy

The information architecture follows a deliberate **zoom hierarchy**, from the widest lens to the narrowest:

- **Season lens** (Overview, Benchmarking) — "How is the team performing across the campaign?"
- **Match lens** (Match Analysis, Tactical Phases) — "How did the team play in this specific game?"
- **Player lens** (Player Analysis) — "Who contributed what, and how?"
- **Opponent lens** (Opponent Scout) — "What does the next opponent do, and how do we exploit it?"
- **Output lens** (Report) — "Package the analysis for distribution to staff."

This mirrors the real workflow of a club analysis department, which moves between season monitoring, match preparation, match review and player development continuously.

### 2.3 Section Relationships and Information Flow

All seven modules are powered by **the same underlying data pipeline and the same KPI definitions**. This is a critical design property: the Expected Goals shown in Overview, in Match Analysis and in Benchmarking are computed by the same model, so the numbers are consistent everywhere. There is no "different xG in different tabs" problem.

The flow of information is:

```
Opta event JSON
   → parse & normalise (one canonical event table per match)
   → compute KPIs (match level)
   → aggregate (season level) / re-slice (player, phase, opponent levels)
   → render (maps, charts, radars, tables)
   → export (Report module)
```

### 2.4 User Workflow

A typical analyst session moves through the dashboard as follows. The user first selects the **competition** and **season** (the global context). They then either review the **Overview** to set season context, or jump directly to **Match Analysis** to select a specific fixture. Within a match, they progress through the natural order of analysis — match information, attacking, defending, transitions, set pieces — using the panels in the order they are presented. They then cross-reference the **Tactical Phases** module for pressing and phase detail, consult **Opponent Scout** for the next fixture, and finally generate a **Report** for distribution.

### 2.5 How Filters Affect Every Visualisation

Filters are not cosmetic; they redefine the **scope of computation**. When a user changes the competition, season, match, venue, or analysis mode (single match vs match range), the dashboard re-loads the relevant event data, re-computes every KPI for the new scope, and re-renders every chart in the active module. A shot map filtered to "away matches only" is not the same shot map with some dots hidden — it is a complete recomputation over the away-match event set. This guarantees that every number on screen is internally consistent with the selected scope. (Filters are documented in full in Section 4.)

### 2.6 Interaction Logic

Each chart is interactive (Plotly-based): users can hover for exact values, and the visual updates instantly when a filter changes. Every panel is wrapped defensively, so that if a single match's data is incomplete, that one panel degrades gracefully (showing an empty-state message) without breaking the rest of the page — an essential property for a tool used live in a match-week environment where data feeds are occasionally imperfect.

---

## 3. Dashboard Landing Page (Overview Module)

The **Overview** module is the landing page and the season-context layer. Its job is to answer, in a single screen, "where does the team stand this season, and is the trend healthy?"

### 3.1 Season KPI Cards

At the top of the Overview, a row of **KPI cards** summarises the season for the selected competition. Each card shows a single headline number with a short descriptor. The cards typically include:

- **Matches Played** — the number of Real Madrid matches in the selected competition-season scope. *Why it exists:* it anchors every other number; a "72 goals" figure is meaningless without knowing it came from 36 matches.
- **Record (W–D–L)** — wins, draws and losses. *Coaching value:* the raw results baseline.
- **Goals Scored / Goals Conceded** — season attacking and defensive output. *Interpretation:* the most fundamental measure of effectiveness, but (crucially) one the dashboard always pairs with xG to test sustainability.
- **Goal Difference** — Goals Scored − Goals Conceded. *Why it matters:* the single best simple predictor of league position over a season.
- **Win %** — wins ÷ matches played × 100.
- **Average Possession %** — the mean of per-match possession share.
- **Average Pass Accuracy %** — the mean of per-match passing accuracy.
- **Expected Goals For / Against (xG / xGA)** — the season's accumulated chance quality, for and against.

Each card is colour-accented in the brand palette. Cards are intentionally large and legible because they are the first thing a coach sees and the numbers most often quoted in a staff meeting.

### 3.2 "Goals Per Match" Chart

**What it shows.** A per-match view of goals scored (and typically goals conceded) across the season, in match order. **Why it exists.** A season total of "72 goals" tells you the volume but not the rhythm; this chart reveals whether scoring is evenly distributed or concentrated in a few thrashings. **Interpretation.** A flat, high line indicates a reliable scoring side; spikes and troughs indicate a team dependent on big games. **Coaching value.** It flags matches where the team underperformed its norm, prompting a targeted review.

### 3.3 "Shots & Pass Accuracy Trend" Chart

**What it shows.** The evolution across the season of two process metrics — shot volume and passing accuracy — rather than outcomes. **Why it exists.** Process metrics are more stable and more predictive than results; a dip in shot volume is an early warning even if results are still good. **Interpretation.** Rising shots with stable pass accuracy indicates growing attacking control; falling shots with high pass accuracy can indicate sterile, "U-shape" possession without penetration. **Analyst use.** This is the chart an analyst watches to detect a developing problem before it shows up in the league table.

### 3.4 Season Results Table

A **results table** lists every match in the scope with matchday, date, venue (Home/Away), opponent, score and result (W/D/L), with the result colour-coded (green/orange/red). *Use case:* it is the index of the season — an analyst clicks through from here to drill into any individual match. *Why colour-coding matters:* it allows instant pattern recognition (e.g. a cluster of red away from home).

### 3.5 Navigation and Colour Coding

The Overview uses the consistent brand colour system applied throughout the platform: **navy** for structure and headers, **gold** for emphasis and the active state, **green** for positive/Real Madrid, **red** for negative/opponent or losses, and **orange** for neutral/draw. This colour grammar is consistent across all seven modules, so a user learns it once and reads every subsequent chart faster.

---

## 4. Dashboard Filters

Filters define the analytical scope. Each is documented below with its purpose, football meaning, technical logic, and example use.

### 4.1 Competition Filter

- **Purpose.** Selects the competition: **LaLiga**, **UEFA Champions League**, or **Copa del Rey**.
- **Football meaning.** Real Madrid play three very different competitions. Tactical behaviour differs by competition: domestic league matches against deep blocks demand patient build-up; Champions League knockouts demand transition control against elite opponents. Mixing them would average away exactly the differences a coach cares about.
- **Technical logic.** The filter maps to the competition folder in the dataset and restricts every subsequent computation to that competition's matches.
- **Analyst use.** "Is our pressing less intense in Europe than in LaLiga?" is answerable only by toggling this filter and comparing PPDA.
- **Coaching question answered.** "Do we need a different game model for the Champions League?"

### 4.2 Season Filter

- **Purpose.** Selects the campaign — **2024–25** or **2025–26**.
- **Football meaning.** Allows year-on-year comparison and tactical-evolution tracking (e.g. the effect of a managerial change or a new signing's integration).
- **Use.** Combined with the competition filter, it scopes the entire dashboard to, say, "LaLiga 2025–26."

### 4.3 Match Selector

- **Purpose.** Selects a single fixture for deep analysis.
- **Football meaning.** The atomic unit of match preparation and review is one game. The selector lists every Real Madrid match in the scope, labelled with matchday, venue (home/away), opponent and score.
- **Technical logic.** Selecting a match loads that match's event JSON and triggers recomputation of every match-level panel.

### 4.4 Analysis Mode (Single Match vs Match Range)

- **Purpose.** Switches between analysing **one match** and analysing an **aggregated range** of matches.
- **Football meaning.** Single-match mode answers "how did we play in *this* game?"; range mode answers "what is our pattern over the last *N* games?" Range mode averages out the noise of any single match to reveal stable tendencies — exactly what you want when defining a game model, and exactly what you do *not* want when reviewing a specific performance.
- **Example.** A coach reviewing a specific defeat uses single mode; a coach defining the team's transition identity uses range mode across ten matches.

### 4.5 Venue Filter (Home / Away / All)

- **Purpose.** Restricts analysis by venue.
- **Football meaning.** Home and away performances differ systematically — home sides typically have more possession, press higher and create more. Separating them prevents misleading averages.
- **Coaching question answered.** "Do we sit deeper away from home, and is that costing us control?"

### 4.6 Game-Phase / Possession Filter (Tactical Phases module)

- **Purpose.** In the Tactical Phases position maps, the user can filter to **All Phases**, **In Possession**, or **Out of Possession**.
- **Football meaning.** A player's or team's average position differs hugely depending on whether they have the ball. Filtering isolates the team's attacking shape from its defensive shape.
- **Use.** This is how an analyst extracts "our defensive block sits at x≈35" from the same data that also yields "our attacking line sits at x≈70."

### 4.7 Team Selector (Real Madrid / Opponent)

- **Purpose.** In position and zonal maps, toggles between Real Madrid and the opponent.
- **Use.** Enables direct shape comparison — e.g. overlaying where Real Madrid attacked against where the opponent defended.

### 4.8 Transition Window Control

- **Purpose.** In Match Analysis, sets the time window (5, 10, 12 or 15 seconds) that defines a "transition" — i.e. how many seconds after winning the ball a shot must occur to count as a transition outcome.
- **Football meaning.** There is no universal definition of a counter-attack; analysts debate whether the window is 5, 10 or 15 seconds. Exposing it as a control lets the analyst test the sensitivity of the conclusion and align it with the club's own definition.
- **Why this is sophisticated.** Most tools hard-code this; surfacing it as a control is a mark of analytical maturity.

### 4.9 Pass Network Scope (Starting XI / Full Match)

- **Purpose.** Restricts the pass network to the starting eleven or includes substitutes.
- **Football meaning.** The starting XI network shows the intended structure; the full-match network shows what actually happened including in-game changes.

### 4.10 Example Filter Combinations

- *"LaLiga 2025–26 · Away · Range mode"* → "What is our settled away-game identity in the league this season?"
- *"Champions League 2025–26 · single knockout match · transition window 10s"* → "How dangerous were our counter-attacks in this specific European tie?"
- *"Tactical Phases · Out of Possession · Opponent"* → "Where did the opponent's attacking players occupy space against our block?"

---

## 5. Match Information Section

Every single-match analysis is anchored by a **Match Information** header, derived directly from the match metadata (`extract_match_meta`). It displays:

- **Opponent** — the team Real Madrid faced.
- **Competition** — LaLiga, Champions League or Copa del Rey.
- **Stage** — matchday number or knockout round.
- **Venue** — stadium name and home/away indicator.
- **Date** — calendar date of the fixture.
- **Score** — full-time score, with the half-time score available.
- **Result** — Win, Draw or Loss, derived from the sign of (RM goals − opponent goals).

### 5.1 Why Contextual Information Is Indispensable

Context changes interpretation more than any single metric. The same statistical performance means completely different things depending on context:

- **Possession of 65%** is unremarkable at home against a relegation side and exceptional away at a top rival.
- **A PPDA of 12** (relatively passive press) is a concern in a home league game the team should dominate, but entirely rational away in a Champions League knockout where conceding the counter would be fatal.
- **Conceding 1.4 xGA** against Barcelona is a strong defensive performance; against a bottom-half side it is a warning.

This is why the Match Information section is not decorative. It is the lens through which every subsequent number must be read. A professional analyst never quotes a metric without its context — "we had 1.9 xG" is incomplete; "we created 1.9 xG away at a side defending a low block, having taken the lead on 20 minutes" is analysis.

---

## 6. Pre-Match Analysis

Pre-match analysis lives primarily in the **Overview**, **Benchmarking** and **Opponent Scout** modules. Its purpose is **expectation setting**: establishing what a "normal" performance looks like for Real Madrid and what to expect from the opponent, before a ball is kicked.

### 6.1 Goals and Goals Against

- **Definition.** Goals scored and conceded over the scope.
- **Calculation.** Direct count from the match scores.
- **Interpretation.** The baseline outcomes. Always read alongside xG/xGA to test whether they are sustainable.
- **Coaching value.** Sets the attacking and defensive expectation level.
- **Limitation.** Outcome metrics are noisy over small samples; a single deflected goal distorts them.

### 6.2 Expected Goals (xG) and Expected Goals Against (xGA)

- **Definition.** xG is the probability that a given shot results in a goal, based on the shot's location and angle; summed across all shots it gives the total chance quality created (xG) or conceded (xGA).
- **Calculation (this platform's positional model).** Penalties are detected by their standardised coordinate and assigned a fixed value of **0.76**. For open-play shots, the model computes the distance and the angle of the goal mouth from the shot location and applies a calibrated logistic function:

  ```
  dx = (100 − x)·1.05 ;  dy = (y − 50)·0.68
  dist = √(dx² + dy²)
  angle = | atan2(dy − 3.66, dx) − atan2(dy + 3.66, dx) |
  logit(xG) = −3.785 − 0.0337·dist + 3.64·angle
  xG = 1 / (1 + e^−logit), clipped to [0.01, 0.99]
  ```

  Calibration anchors: a central chance at 6 m ≈ 0.50; at 11 m (penalty-spot distance, open play) ≈ 0.14; at the edge of the box (16.5 m) ≈ 0.06; a 25 m shot ≈ 0.027.
- **Interpretation.** If goals exceed xG, the team is finishing above expectation (clinical, but liable to regress); if goals trail xG, the team is creating well but finishing poorly (likely to improve). xGA works identically for the defence.
- **Coaching value.** The single most important sustainability check in modern analysis. It distinguishes a "lucky" win from a "deserved" one.
- **Limitation.** This is a transparent, location-only model. It does not (by design) account for defender positioning, goalkeeper position, the body part used, or assist type. It is therefore best read as a directional, auditable indicator rather than a provider-grade post-shot model.

### 6.3 Possession

- **Definition.** The share of play Real Madrid controlled.
- **Calculation.** `RM passes ÷ (RM passes + opponent passes) × 100`. Because the event feed contains no ball-possession *duration*, possession is expressed as a **pass-volume share** — a robust and standard proxy.
- **Interpretation.** High possession is a means, not an end; it must be paired with field tilt and final-third entries to confirm it is productive rather than sterile.
- **Limitation.** It is a proxy, not a stopwatch figure.

### 6.4 Opponent Context: League Position, Defensive Style, Difficulty, Form

These are surfaced principally in the **Opponent Scout** module. The dashboard profiles the opponent's style, strengths, weaknesses and tendencies (Section 7.5), allowing the analyst to set an **expected match scenario**: e.g. "a deep, compact block that concedes possession but defends the box well, with a set-piece threat" — which dictates that Real Madrid should expect to dominate the ball, attack the half-spaces, and be disciplined in defensive transition against the opponent's counters.

### 6.5 Expected Match Scenario

By combining Real Madrid's season identity (from Overview/Benchmarking) with the opponent profile (from Opponent Scout), the analyst forms a pre-match hypothesis. The dashboard's value is that this hypothesis is **evidence-based** rather than impressionistic, and that after the match the same tool can confirm or refute it.

---

## 7. Tactical Phase Analysis

This is the analytical core of the platform, distributed across the **Match Analysis** and **Tactical Phases** modules. It is organised around the four moments of play plus set pieces and the spatial sub-analyses (recoveries, final-third entries).

### 7.1 Attacking Transition (Offensive Transition — Phase D)

**Transition definition.** An offensive transition is the moment immediately after Real Madrid win the ball, when the opponent is briefly disorganised and most vulnerable to a fast, direct attack (the counter-attack / fast break).

**How transitions are identified.** The platform locates every Real Madrid **ball regain** (a recovery, interception or tackle) and then checks whether a Real Madrid **shot** occurred within the configurable window (default 12–15 seconds). The proportion of regains that produce a shot within the window is the **transition rate** (`trans_rate`) — a direct, event-timed measure of counter-attacking threat.

**Panels.**
- **Transition Metrics** — summarises the number of transitions, shots and goals generated from transitions, and the fast-break efficiency (the % of regains producing a shot within the window) and transition xG.
- **Extended Transition Analysis** — a deeper view controlled by the Transition Window Control, allowing the analyst to vary the time threshold and observe how transition output changes.
- **Tactical Phase Profile (Radar)** and **Match Tactical Sub-Phases** — show the Phase D score in the context of the other three phases (Section 7.7).

**Recovery-to-shot time.** This is the heart of transition analysis: a team that converts regains into shots in under 10 seconds is a genuine counter-attacking threat; a team that takes 20+ seconds is recycling possession, not transitioning.

**Coaching applications.** If transition output is high, the coach reinforces it in training (rest-defence positioning to enable counters, runners beyond the ball). If it is low against a high-pressing opponent, the coach may instruct the team to exploit the space behind the press more directly.

### 7.2 Organized Attack (Offensive Moment — Phase A)

**Definition.** The settled phase in which Real Madrid have established possession against an organised opponent and must create through structure, not transition.

**Panels and what they reveal.**
- **Shot Map** — the location of every Real Madrid shot, with marker size proportional to xG and goals highlighted. *Reveals* where and how good the chances were.
- **Shot Zone Map** — shots aggregated into pitch zones, showing the dominant areas of chance creation.
- **xG Accumulation by Minute** — the running total of xG through the match, for and against, as a step curve. *Reveals* when in the match the team created — early control, second-half surge, late desperation, etc.
- **Pass Map (RM successful passes)** — the network and direction of completed passes. *Reveals* circulation patterns and whether the ball progresses or merely circulates.
- **Build-Up Network (RM passes in own half, x < 50)** — the structure of the first phase of build-up. *Reveals* how the team plays out from the back and which players are the build-up hubs.
- **Progressive Passes (advances ball ≥ 10 units forward)** — passes that meaningfully move the ball upfield. *Reveals* who progresses the ball and through which channels.
- **Zone 14 Passing** — activity in the central zone just outside the penalty area (the single most dangerous creative zone in football). *Reveals* whether the team accesses the key creative space.
- **Crossing Patterns** — the volume, origin and target of crosses. *Reveals* wide attacking tendencies.
- **Chance Creation Heatmap (Key Passes & Assists — origin locations)** — where the chances are created from.
- **Pass Receive Heatmap** — where Real Madrid passes are received (where the team wants the ball to land).
- **Final Third Entry Analysis** and **Field Tilt** — territorial penetration (Section 7.6).
- **Team Radar — RM vs Opponent** — a multi-metric comparison of the two teams in the match.

**Metrics emphasised.** Possession %, pass accuracy, progressive passes, final-third entries, shot-creation zones, field tilt.

**Coaching value.** This is where a coach evaluates whether the build-up is functioning, whether the team accesses dangerous zones (Zone 14, half-spaces), and whether possession is translating into penetration rather than sterile circulation.

### 7.3 Defensive Strategy (Defensive Moment — Phase C — and the Press)

**Definition.** How Real Madrid behave without the ball: the intensity and height of the press, the compactness of the defensive block, and the chances conceded.

**PPDA (Passes Allowed Per Defensive Action).**
- **Definition.** The number of passes the opponent is allowed to make per Real Madrid defensive action in the pressing zone. It is the standard measure of pressing intensity.
- **Formula.** `opponent passes (x ≥ 40) ÷ Real Madrid defensive actions (tackles + interceptions + recoveries) in the same zone (x ≥ 40)`.
- **Interpretation.** **Lower PPDA = more intense press** (the opponent is allowed fewer passes before being challenged). A PPDA around 8–10 indicates a controlled press; a PPDA of 4–6 indicates an aggressive, high press; a PPDA above 14 indicates a passive, deep-block approach.
- **Coaching value.** It quantifies the team's pressing identity and lets the coach see, match by match, whether the team pressed as instructed.

**Panels.**
- **PPDA Trend (Season)** — PPDA per matchday across the season, with the season average marked. *Reveals* the consistency and game-state dependence of the press.
- **Pressing Actions Map** — the pitch locations of the team's pressing/defensive actions in the match. *Reveals* where on the pitch the team engages — high press vs mid-block.
- **Press Classification — Spatial Distribution** — categorises pressing actions by zone/height. *Reveals* the structure of the press.
- **Defensive Actions Map** — the locations of tackles, interceptions and recoveries.
- **Shots conceded** — surfaced as a count (and, in Opponent Scout, the opponent's shot map). *Note:* a dedicated shots-conceded heatmap is a planned enhancement.

**What coaches learn.** Whether the block is compact, where it is breached, how high the team presses, and whether pressing intensity matches the game plan. A coach seeing a high PPDA (passive press) in a game the team intended to dominate knows immediately that the pressing instruction was not executed.

### 7.4 Set Pieces

**Definition.** Dead-ball situations — corners and free kicks — both attacking and defending.

**How they are identified.** Set-piece restarts are tagged from the event qualifiers (free-kick taken, corner taken), and corner-derived chances are identified by locating shots occurring within ~20 seconds of a corner.

**Panels.**
- **Set Piece Efficiency** (Match Analysis) — Real Madrid's output from set pieces.
- **Goalmouth Map** — where shots/efforts arrive relative to the goal, relevant to both set-piece delivery and finishing.
- **Set-piece tendencies** (Opponent Scout) — the opponent's corner count and shots generated from corners.

**Why set pieces matter.** Roughly a quarter to a third of goals in elite football come from set pieces. They are also the most coachable, most rehearsable phase of the game. A coach uses this analysis to (a) exploit an opponent's defensive set-piece weakness and (b) shore up the team's own.

*Status note.* Set-piece analysis is implemented at the efficiency/tendency level; dedicated set-piece shot maps and delivery-zone maps are a planned enhancement.

### 7.5 Possession Recovery

**Definition.** How and, above all, **where** Real Madrid win the ball back.

**Metrics.** Ball recoveries (Opta type 49), interceptions (type 8), tackles (type 7), and recovery counts per pitch zone.

**Panel.** **Ball Recoveries by Zone** — a zonal heatmap of where on the pitch the team regains possession.

**Tactical implications of recovery height.**
- **High recoveries** (in the attacking third) indicate an effective high press and create the most dangerous transition opportunities (winning the ball close to the opponent's goal).
- **Middle-third recoveries** indicate a mid-block strategy.
- **Deep recoveries** (in the team's own third) indicate the team is defending deep and absorbing pressure.

A coach reads the recovery map to confirm the pressing strategy is working: a team instructed to press high but recovering the ball mostly in its own third is being played through.

### 7.6 Final Third Entries

**Definition.** The moments Real Madrid move the ball into the opponent's final third — the entry point of meaningful attacking threat.

**Panels.**
- **Final Third Entry Analysis (RM)** — the locations and pattern of entries.
- **Field Tilt (Final Third %)** — the share of all final-third touches that belong to Real Madrid. **Formula:** `RM final-third touches (x ≥ 67) ÷ all final-third touches (x ≥ 67) × 100`. *Interpretation:* a territorial-dominance measure; a field tilt of 75% means three-quarters of all final-third activity was Real Madrid's.
- **Territorial Tilt by Phase** — how field tilt varies across phases.

**Wide, central and half-space entries.** The pattern of entries reveals attacking identity: a team entering mainly through wide areas relies on crossing; a team entering through the half-spaces (the channels between full-back and centre-back) is more incisive and harder to defend. *Status note:* explicit half-space classification and xG-from-entries are planned enhancements; the current implementation establishes entry locations and territorial dominance.

**Coaching value.** Entries are a leading indicator of attacking threat — a team that enters the final third frequently but creates few shots has a problem in the final action, not in progression.

### 7.7 The Tactical Phase Profile (A/B/C/D Radar) and Sub-Phase Snapshot

The platform synthesises all four phases into two complementary panels:

- **Match Tactical Sub-Phases (A/B/C/D)** — a bar chart of the four phase scores.
- **Tactical Phase Profile (Radar)** — the same four scores on a polar radar, producing an instantly readable "shape" of the team's match.

**The four phase scores, with exact formulas (each normalised and clipped to 0–100):**

```
A · Offensive Moment      = pass_acc·0.45 + (Σxg·10)·0.35 + (shots·2.5)·0.20
B · Defensive Transition  = (100/(1+PPDA))·0.55 + ((recoveries+interceptions)·1.8)·0.45
C · Defensive Moment      = (100/(1+PPDA))·0.40 + max(0, 40 − opp_shots·2)·0.60
D · Offensive Transition  = trans_rate·0.65 + (Σxg·7)·0.35
```

- **A (Offensive Moment)** rewards keeping the ball (pass accuracy), creating quality chances (xG) and shot volume.
- **B (Defensive Transition)** rewards an intense press (the `100/(1+PPDA)` term rises as PPDA falls) and a high count of ball-winning actions.
- **C (Defensive Moment)** rewards pressing intensity *and* keeping the opponent's shot count low.
- **D (Offensive Transition)** rewards converting regains into quick shots (transition rate) and the xG generated.

**How a coach reads the shape.** A radar stretched toward A and B with low C and D (a "possession-and-counter-press" shape) describes a game in which Real Madrid dominated the ball and won it back aggressively, but defended their settled block less and rarely countered — the typical pattern against a deep block. A radar stretched toward C and D describes a reactive, transition-based game against a stronger, possession-dominant opponent.

**Important caveat (for examiners).** These four numbers are **weighted composite indices**, deliberately normalised to 0–100 so they can be compared on one picture. They are interpretive rankings of relative phase strength, **not physical units** — a "60" is not 60 of anything. The *inputs* (PPDA, xG, recoveries, transition rate) are all real, measured event metrics; the *weights* are a modelling choice. This is precisely why the dashboard always presents the radar alongside the raw underlying panels (PPDA trend, shot maps, recovery map): the radar is the executive summary, the other panels are the evidence.

---

## 8. Post-Match Analysis

Post-match analysis (principally the **Post-Match Tactical Summary** in Match Analysis, plus the xG comparison) answers the question that decides whether a coach should be satisfied: **did the result reflect the performance?**

### 8.1 Goals vs xG

- **What it compares.** Actual goals scored against the xG created.
- **Interpretation.** Goals > xG = clinical finishing (enjoy it, but expect regression); Goals < xG = wasteful finishing (the process is good, results should improve); the same logic applies to xGA vs goals conceded for the defence.
- **Example.** Winning 1–0 with 2.3 xG and 0.4 xGA is a *dominant* performance that flattered the opponent in the scoreline; winning 1–0 with 0.5 xG and 1.8 xGA is a *fortunate* result that should worry the coach despite the three points.

### 8.2 Performance vs Expectation and Match Dominance

By combining xG difference (xG − xGA), field tilt, possession and PPDA, the post-match view characterises **match dominance** independently of the scoreline. This is the antidote to outcome bias: it tells the coaching staff whether to trust the result or to treat it as variance.

### 8.3 Defensive and Attacking Efficiency

- **Attacking efficiency** = goals per xG (or goals per shot): how clinically chances were converted.
- **Defensive efficiency** = goals conceded per xGA: how well the goalkeeper and last-ditch defending suppressed conceded chances.
- These efficiency ratios separate *creation/suppression* (repeatable, coachable) from *finishing/saving* (more variable).

---

## 9. Every Graph (Chart-by-Chart Reference)

This section documents the chart types used across the platform. For each: graph type, axes, colours, data source, meaning, interpretation, football application and limitations.

### 9.1 Shot Map
- **Type.** Scatter plot on a pitch. **Axes.** Pitch coordinates (x = length, y = width). **Colours/markers.** Marker size ∝ xG; goals highlighted (gold/star), on-target vs off-target distinguished. **Data source.** Shot events (`get_shot_data`). **Meaning.** Where and how good each chance was. **Application.** Identifies whether the team creates high-value central chances or low-value shots from distance. **Limitation.** Does not show defensive pressure on the shot.

### 9.2 xG Accumulation by Minute
- **Type.** Step/line chart. **Axes.** x = match minute, y = cumulative xG. **Colours.** RM vs opponent in contrasting colours. **Meaning.** The temporal story of chance creation. **Application.** Reveals momentum shifts — who controlled which phase of the match. **Limitation.** A single big chance (e.g. a penalty) creates a large step that can dominate the curve.

### 9.3 Tactical Comparison
- **Type.** Grouped bar chart. **Axes.** Metric categories vs values, RM vs opponent. **Meaning.** Side-by-side comparison of key match KPIs. **Application.** A one-glance "who won which battle" summary. **Limitation.** Bars compare levels, not context.

### 9.4 Pass Map / Build-Up Network / Pass Network
- **Type.** Node-and-position network on a pitch. **Nodes.** Players at their average pass position; node size ∝ involvement. **Meaning.** Team structure and circulation. **Application.** Reveals build-up hubs, isolated players, and structural balance. **Limitation (current).** Edges (player-to-player connections) are a planned enhancement; the current network emphasises average positions and volumes.

### 9.5 Progressive Passes / Crossing Patterns / Zone 14 Passing
- **Type.** Directional/positional pass plots on a pitch. **Meaning.** Ball progression, wide delivery and central penetration respectively. **Application.** Identify the channels and players through which the team advances and creates.

### 9.6 xG / Pass-Accuracy / Goals-per-Match Trend Charts
- **Type.** Line/bar time series. **Axes.** x = matchday, y = metric. **Meaning.** Season trajectory of a process or outcome. **Application.** Early-warning detection of form changes. **Limitation.** Trend charts need a reasonable sample to be meaningful.

### 9.7 Team Radar / Tactical Phase Profile Radar
- **Type.** Polar (radar) chart. **Axes.** Each spoke is a metric/phase, scaled 0–100. **Meaning.** A multidimensional "shape" of performance. **Application.** Instant pattern recognition and team-vs-team or match-vs-match comparison. **Limitation.** Radar areas are visually seductive but the enclosed area has no literal meaning; read the spokes, not the area.

### 9.8 Penalty Analysis, Goalmouth Map, GK Distribution Map
- **Type.** Specialised pitch/goal plots. **Meaning.** Penalty outcomes, where efforts arrive at goal, and goalkeeper distribution patterns respectively. **Application.** Niche but high-value: GK distribution reveals whether the team builds short or goes long; the goalmouth map informs finishing and goalkeeping coaching.

---

## 10. Every Heatmap (Spatial-Analysis Reference)

Heatmaps encode **where** something happens by colour intensity over pitch zones. Hot (intense) zones indicate high activity; cold zones indicate low activity. The platform's heatmaps include:

### 10.1 Ball Recoveries by Zone
- **Pitch zones.** The pitch divided into zones; colour intensity = recovery frequency. **Hot zones.** Where the team most often wins the ball. **Interpretation.** High/attacking-third hot zones = effective high press; own-third hot zones = deep defending. **Decision-making.** Confirms or refutes the pressing plan and identifies the launch points of transitions.

### 10.2 Chance Creation Heatmap (Key Passes & Assists origins)
- **Hot zones.** Where the team's chances originate. **Interpretation.** Half-space and Zone 14 hot zones indicate incisive central creation; wide hot zones indicate a cross-based attack. **Application.** Directs both training (rehearse the productive patterns) and opposition planning (defend the productive zones).

### 10.3 Pass Receive Heatmap
- **Hot zones.** Where passes are received. **Interpretation.** Reveals where the team wants the ball to arrive — the target areas of its passing game.

### 10.4 Opponent Threat Heatmap (Opponent Scout)
- **Hot zones.** Where the opponent generates action density/threat. **Application.** Tells the analyst where the opponent is dangerous, so the defensive plan can prioritise those zones.

### 10.5 Player Touch Heatmap (Player Analysis)
- **Hot zones.** An individual player's touch concentration. **Application.** Confirms a player's functional role (e.g. a "winger" whose heatmap is heavily inside the half-space is really an inside-forward).

### 10.6 Pressing Actions Map / Defensive Actions Map
- **Interpretation.** Defensive engagement locations. High, advanced hot zones = aggressive high press; hot zones around the halfway line = mid-block; deep hot zones = low block. **Pressing implication.** Directly visualises the team's defensive height and triggers.

**General heatmap reading guidance.** Always compare the heatmap to the team's intention. A heatmap is not "good" or "bad" in isolation — a deep recovery map is excellent for a counter-attacking game plan and alarming for a high-pressing one. Context (Section 5) governs interpretation.

---

## 11. Every Table (Tabular-Data Reference)

### 11.1 Season Results Table (Overview)
- **Columns.** Matchday, Date, Venue (H/A), Opponent, Score, Result. **Sorting.** Chronological by matchday. **Colour.** Result colour-coded (green/orange/red). **Use case.** The navigable index of the season; the entry point to any single-match drill-down. **Interpretation.** Pattern recognition across the campaign (home/away splits, runs of form).

### 11.2 Real Madrid Player Performance Table (Match Analysis) / Squad Table (Player Analysis)
- **Columns.** Player, minutes, passes, pass accuracy, shots, shots on target, goals, key passes, assists, tackles, interceptions, recoveries, dribbles, xG, fouls. **Rows.** One per player. **Sorting/Ranking.** Sortable by any metric to rank contributors. **Use case.** Identify the match's most influential players, spot under-involved players, and feed selection/rotation decisions. **Interpretation.** Always normalise mentally by minutes — a substitute's raw totals are not comparable to a starter's (per-90 normalisation is a planned enhancement).

### 11.3 Opponent Player Stats Table (Opponent Scout)
- **Use case.** Identifies the opponent's key individuals — their creators, their pressers, their goal threat — so the game plan can account for them (e.g. assign a specific player to screen the opponent's primary creator).

### 11.4 Lineup / Starting XIs Shape
- **Use case.** Shows the starting formation and average shape of both teams, the structural starting point of all tactical analysis. **Interpretation.** Reveals the formation matchup (e.g. a back three vs a front two) that frames every other pattern.

---

## 12. Every KPI Card (Card-by-Card Reference)

Each KPI card presents one headline number. For each: definition, calculation, why it is monitored, and high/low interpretation.

- **Matches Played** — count of matches in scope. *High/low:* a sample-size anchor, not a performance metric.
- **Record (W–D–L)** — wins/draws/losses. *High wins:* effective; *high draws/losses:* investigate via xG whether it is performance or variance.
- **Win %** — wins ÷ played × 100. *High:* dominant; *low:* underperforming relative to a club of Real Madrid's level.
- **Goals Scored** — attacking output. *High:* potent attack; *low:* finishing or creation problem (check xG to tell which).
- **Goals Conceded** — defensive output. *Low:* solid defence; *high:* structural or goalkeeping issue (check xGA).
- **Goal Difference** — GF − GA. *The headline efficiency number;* strongly correlated with final standing.
- **xG / xGA** — chance quality created/conceded. *High xG, low xGA:* dominant underlying performance regardless of results.
- **xG Difference (xG − xGA)** — net underlying dominance. *Positive and large:* the team is the better side on chances; *negative:* results may be flattering the team.
- **Average Possession %** — pass-share control. *High:* controls games; *interpret with field tilt.*
- **Average Pass Accuracy %** — passing reliability. *High:* secure in possession; *very high with low penetration:* possibly sterile.
- **PPDA** (Tactical Phases) — pressing intensity. *Low:* aggressive press; *high:* passive/deep.
- **Field Tilt %** — territorial dominance. *High:* the team plays in the opponent's half.

Coaches monitor these because together they form a balanced scorecard: outcome (goals, results), process (xG, possession, PPDA), and territory (field tilt) — preventing any single number from telling a misleading story.

---

## 13. Every Metric (Metric-by-Metric Reference)

For each: definition, formula where applicable, interpretation, coaching value, limitation.

- **Goals Scored / Conceded.** Count of goals for/against. *Outcome metric; pair with xG.*
- **Expected Goals (xG).** Probability-weighted chance quality (see §6.2 for the full formula). *The key sustainability metric.*
- **Expected Goals Against (xGA).** The same model applied to the opponent's shots. *Measures chances conceded.*
- **xG Difference.** xG − xGA. *Net underlying superiority.*
- **Possession %.** `RM passes ÷ total passes × 100`. *Pass-share proxy for control.* Limitation: not a duration.
- **Pass Accuracy %.** `mean(pass outcome) × 100` over the team's passes (outcome = 1 if successful). *Security in possession.*
- **Passes (total).** Count of pass events. *Volume of circulation.*
- **Progressive Passes.** Passes advancing the ball ≥ ~10–15 units toward goal. *Ball progression; identifies the team's advancers.*
- **Final Third Entries.** Ball entries into the attacking third (x ≥ 67). *Leading indicator of attacking threat.*
- **Field Tilt %.** `RM final-third touches ÷ all final-third touches × 100`. *Territorial dominance.*
- **Shots (total).** Count of shot events (Opta types 13/15/16, plus shot qualifiers). *Attacking volume; pair with xG for quality.*
- **Shots on Target.** Shots of type 13 (saved) + 16 (goal). *Threat on goal.*
- **Shot Accuracy.** Shots on target ÷ total shots. *Shot selection/quality.*
- **Goals per Shot / Goals per xG.** Finishing efficiency. *Separates conversion from creation.*
- **PPDA.** `opp passes (x≥40) ÷ RM defensive actions (tackle+interception+recovery, x≥40)`. *Pressing intensity; lower = more intense.*
- **Tackles (Opta 7), Interceptions (8), Ball Recoveries (49).** Defensive ball-winning actions. *Volume and location of defensive engagement.*
- **Defensive Actions.** The union of tackles, interceptions and recoveries. *Total defensive workload; feeds PPDA and the phase model.*
- **Dribbles / Take-ons (Opta 3).** Attempts to beat an opponent. *Individual carrying threat.*
- **Key Passes.** Passes leading directly to a shot. *Chance creation.*
- **Assists.** Passes leading directly to a goal. *End-product creation.*
- **Corners (Opta 6), Fouls (4), Cards (65/68).** Set-piece and discipline counts.
- **Transition Rate (trans_rate).** % of regains producing a shot within the window. *Counter-attacking threat — the engine of Phase D.*
- **Transition xG.** xG generated from transitions. *Quality of counter-attacking chances.*
- **Phase Scores A/B/C/D.** Weighted composite indices, 0–100 (see §7.7 for formulas). *Phase-by-phase effectiveness; interpretive, not unit-based.*
- **Minutes Played (player).** The player's maximum event minute. *Time-on-pitch proxy for normalisation.*

*A note on Expected Threat (xT).* xT — a metric valuing each possession action by how much it raises the probability of scoring — is referenced as a future capability. It is **not currently computed** as a standalone metric; the platform uses xG, transition rate and field tilt to capture related concepts. Documenting this honestly matters for an examiner.

---

## 14. Tactical Insights Generated

The dashboard is built to support specific tactical conclusions. The kinds of insight a coach can legitimately draw, each tied to the panels that evidence it:

- **Transition strength.** High Phase-D score + high transition rate + high transition xG (Transition Metrics, radar) → "we are a genuine counter-attacking threat."
- **Pressing effectiveness.** Low PPDA + high/attacking-third recovery hot zones (PPDA Trend, Recoveries by Zone) → "our high press is functioning."
- **A passive or beaten press.** High PPDA + deep recovery hot zones → "we are not winning the ball where we intend to."
- **Build-up efficiency.** A balanced build-up network + high progressive-pass volume → "we play out from the back effectively."
- **Central vs wide attacking identity.** Zone 14 / chance-creation heatmaps vs crossing patterns → "we create centrally" or "we are cross-dependent."
- **Defensive vulnerability.** Low Phase-C score + opponent threat hot zones in dangerous areas + xGA → "our settled defending concedes quality chances here."
- **Set-piece strength/weakness.** Set Piece Efficiency + opponent set-piece tendencies → "we should target their corners / protect against theirs."
- **Match control / dominance.** Positive xG difference + high field tilt + low PPDA → "we dominated independent of the scoreline."
- **Attacking and defensive identity, and the overall game model.** The four-phase radar shape, read across many matches, *is* the team's tactical identity in a single picture.

---

## 15. User Journey (End-to-End Workflow)

A complete match-week workflow, as a club analyst would actually run it:

1. **Open the dashboard** and select the **competition and season** (e.g. LaLiga 2025–26).
2. **Review the Overview** to refresh season context — record, goal difference, xG/xGA trend, recent form from the results table.
3. **Open Opponent Scout** for the upcoming opponent: read the style/strengths/weaknesses profile, the opponent shot map and threat heatmap, the opponent player stats, and the set-piece tendencies. Form the **expected match scenario**.
4. **Open Benchmarking** to compare Real Madrid's metrics against the opponents faced and rivals, calibrating expectations.
5. **Build the pre-match plan:** decide pressing height (informed by the opponent's build-up vulnerability), attacking emphasis (central vs wide, informed by the opponent's defensive weak zones), and transition discipline.
6. **Generate a Report** (PDF/DOCX) to distribute the plan to the coaching staff.
7. **After the match,** switch to **Match Analysis**, select the fixture, and work through the panels in order: Match Information → Shot Map and xG Accumulation (attacking) → Pass/Build-up networks → Defensive Actions and PPDA → Transitions → Set Pieces → the **Tactical Phase Profile radar** for the executive summary → the Post-Match Tactical Summary.
8. **Compare the radar shape and xG to the pre-match plan:** did the team execute the intended game model? Did the result reflect the performance (Goals vs xG)?
9. **Use Player Analysis** to attribute the performance to individuals and inform rotation/training.
10. **Translate findings into training:** the weakest phase (e.g. a low Phase-C against quality opponents) becomes the next training block's focus; the strongest (e.g. transition) is reinforced.
11. **Make match decisions:** selection, formation and in-game plans for the next fixture, now evidence-based.

---

## 16. Dashboard Strengths

- **End-to-end and integrated.** Season, match, player, opponent, benchmark and reporting in one consistent environment with one shared data model — the same xG everywhere.
- **Phase-based by design.** It speaks the coach's language (the four moments), not just a list of disconnected stats.
- **Transparent and auditable.** Every metric maps to an explicit formula over observed events; there are no black boxes and no synthetic values. This is rare and is a major academic and professional strength.
- **Genuinely interactive.** Filters recompute rather than merely hide, so every view is internally consistent for its scope.
- **Rich panel coverage.** Beyond the headline phases it includes specialist views (Zone 14, half-space creation, GK distribution, goalmouth, penalty analysis, build-up networks) that elevate it above a generic stats page.
- **Robust in operation.** Defensive error-handling means an imperfect single feed degrades one panel, not the whole tool — important for live match-week use.
- **Reproducible and deployed.** It runs as a public, auto-deployed web application, and the analysis can be regenerated deterministically.
- **Multi-competition.** It captures how Real Madrid adapt across LaLiga, the Champions League and the Copa del Rey.

---

## 17. Current Limitations

Stated honestly, as a professional document must.

- **Event data only — no tracking.** The platform sees on-ball events but not continuous off-ball positioning. It therefore *approximates* rather than *measures* defensive shape, pressing distances, off-ball runs and compactness. Concepts like true team compactness or pitch control require optical/GPS tracking data the platform does not have.
- **Possession is a proxy.** Computed from pass share, not ball-possession duration. Directionally correct, but not a stopwatch figure.
- **xG is a transparent positional model, not a provider model.** It uses shot location and angle only, omitting defender pressure, goalkeeper position, body part and assist type. It is auditable but simplified, and should be read as directional.
- **Phase scores are weighted composites.** They rank relative phase strength on a 0–100 scale and are sensitive to their weighting choices; they are interpretive indices, not physical units.
- **No expected threat (xT) or full possession-chain valuation yet.** Sequence-level value metrics are referenced as future work, not current capability.
- **Player metrics are not yet per-90 normalised**, so raw totals must be read with minutes in mind.
- **Some spatial panels are at the metric/aggregate level** (e.g. shots-conceded as a count rather than a heatmap; half-space entry classification; dedicated set-piece shot maps) — implemented in part, with specific visual enhancements planned.
- **Not predictive and not real-time.** The platform is descriptive and diagnostic; it analyses completed matches from stored files. It does not forecast outcomes or ingest a live in-match feed.

---

## 18. Future Improvements (Professional Roadmap)

Recommended enhancements, prioritised as a club analytics department would:

1. **Tracking-data integration.** Fuse optical/GPS tracking to add off-ball positioning, true compactness, pressing distances, defensive line height and pitch control — the single biggest analytical upgrade available.
2. **Player-level dashboards.** Deepen Player Analysis with per-90 normalisation, role-specific radars, on/off-ball impact and individual phase contribution.
3. **Expected Threat (xT) and possession-chain valuation.** Value every action by how much it increases scoring probability, enabling sequence analysis and possession-chain breakdowns.
4. **Passing networks with weighted edges** and press-resistance metrics, to quantify build-up under pressure.
5. **Defensive-shape analytics** — block height, width and compactness over time — once tracking data is available.
6. **Machine learning and AI tactical recommendations.** Unsupervised clustering of phases and possession sequences to discover recurring patterns automatically, and a recommendation layer that suggests tactical adjustments.
7. **Predictive analytics.** Forecasting models for xG, transition success and match outcomes, conditioned on game state.
8. **Video integration.** Synchronise each event/metric with clip timestamps so a tactical statement is one click from its footage — the feature coaches value most.
9. **Automatic event tagging** to reduce dependence on the provider feed and enable faster turnaround.
10. **A dedicated opponent-scouting module** with automated, templated opposition reports and multi-opponent comparison.
11. **Training-session recommendations** that translate the weakest diagnosed phase into concrete drills.
12. **Live, real-time dashboards** for in-match decision support.
13. **Recruitment analytics** extending the same framework to player identification and squad planning.

---

## Part II — Annotated Visual Walkthrough (Real Match: Real Madrid 2–1 Barcelona, LaLiga 2025–26, Matchday 10)

The remainder of this document is a **screen-by-screen, panel-by-panel walkthrough of the live dashboard**, illustrated with the dashboard's own rendered charts. Every figure below is produced by the live application's own functions, driven exclusively by the **real Opta event feed** for the fixture — there is no synthetic, simulated or illustrative data anywhere in this section. The chosen fixture, *El Clásico* (Real Madrid 2–1 Barcelona), is used as a single, coherent case study so that a reader can see how the panels interlock to tell one complete tactical story. The same panels behave identically for any other match in the dataset.

The walkthrough follows the exact order in which an analyst meets the panels when working through the **Match Analysis** and **Tactical Phases** modules, and is the practical counterpart to the conceptual reference in Parts 1–18 above. Read this part as if you were sitting beside the analyst as they review the match.

### II.1 Overview — "Goals Per Match" (Season Context)

[[FIG:ov_goals_trend|Overview module — the "Goals Per Match" panel rendered live from the real LaLiga 2025–26 feed. Each point is one match in chronological order.]]

Before any single match is opened, the analyst orients themselves with the season context panels. The **Goals Per Match** chart is the first. It plots Real Madrid's goals in each league fixture in chronological order, so the eye can immediately distinguish a steady, reliable scoring rhythm from a "feast-or-famine" pattern in which a handful of heavy wins inflate the season total. This distinction matters enormously to a coach: two teams can score the same number of league goals, but the team that scores in a narrow, consistent band is the more dependable and the more tactically mature, because it is creating and converting in a repeatable way rather than relying on the occasional avalanche. When the analyst later studies an individual match, this chart is the baseline against which that match's output is judged — a two-goal game is "normal" if the team's per-match band sits around two, and a noteworthy under-performance if the band sits higher. The panel exists, in short, to convert a single season-total number into a *distribution*, and distributions are where the tactical truth lives.

### II.2 Overview — "Shots & Pass Accuracy Trend" (Process vs Outcome)

[[FIG:ov_shots_trend|Overview module — the "Shots & Pass Accuracy Trend" panel, tracking two stable process metrics across the real season rather than results.]]

The second context panel deliberately ignores results and tracks two **process metrics**: shot volume and passing accuracy. The reasoning is one of the most important principles in performance analysis — *process metrics are more stable and more predictive than outcomes*. A team's results in any short window are heavily contaminated by finishing variance and refereeing decisions; its shot volume and its passing reliability are far more repeatable from week to week, and a change in them is therefore an early signal. A coach who sees shot volume declining over four matches has a developing problem to address *before* it shows up as dropped points. Conversely, a very high passing accuracy combined with a *falling* shot count is the classic statistical fingerprint of sterile possession — the team is keeping the ball comfortably but no longer hurting anyone with it, the so-called "U-shape" passing in front of a deep block. This panel is the dashboard's early-warning system, and an analyst checks it weekly precisely because it speaks before the league table does.

### II.3 Match Analysis — Shot Map

[[FIG:shot_map|Match Analysis module — the live Shot Map for Real Madrid 2–1 Barcelona. Marker colour = team (blue Real Madrid attacking right, red Barcelona attacking left); marker size ∝ shot quality (xG); ★ = goal, ◆ = on target, ✗ = off target/blocked. The pitch is divided into defensive, middle and attacking thirds.]]

The Shot Map is the single most important attacking panel and usually the first an analyst opens after the Match Information header. It plots every shot in the match at its true pitch location, encoding three dimensions of information simultaneously: **team** (by colour — Real Madrid in blue attacking toward the right goal, Barcelona in red attacking toward the left), **shot quality** (by marker size, scaled to the Expected Goals value of each shot), and **outcome** (by marker shape — a star for a goal, a diamond for an on-target effort, a cross for an off-target or blocked attempt). The legend and the attacking-direction arrows make the orientation unambiguous, and the third-lines provide instant spatial reference.

Reading this specific map, the analyst sees Real Madrid's blue markers heavily concentrated in and around the Barcelona penalty area on the right, with two gold stars marking the two goals and several large blue markers indicating high-quality central chances — the visual signature of a team that did not merely shoot often but shot from *good positions*. Barcelona's red markers, by contrast, are more scattered and include efforts from wider and more distant positions on the left, the signature of a team reduced to lower-probability attempts. The tactical conclusion is immediate and defensible: Real Madrid's attacking output in this match was both high-volume and high-quality, and concentrated in the central "golden zone" directly in front of goal.

For a coach, the Shot Map answers "where and how good were our chances?" — and, just as importantly, "where and how good were *theirs*?" A cluster of opponent shots from one specific zone is an actionable defensive finding. For a scout profiling Barcelona, the same map, read across several of their matches, reveals their preferred shooting zones and shot-selection discipline. The panel's one honest limitation is that it shows the *location* of a shot but not the *pressure* on it; a wide-open six-yard chance and a heavily-blocked one of identical coordinates would look similar, which is why the Shot Map is always read in conjunction with the xG figure (which weights for distance and angle) and the match footage.

### II.4 Match Analysis — xG Accumulation by Minute

[[FIG:xg_accumulation|Match Analysis module — Expected Goals accumulating minute-by-minute for both teams, from the real event feed. The slope of each line is the rate of chance creation; steps mark individual chances.]]

Where the Shot Map shows *where*, the xG Accumulation chart shows *when*. It plots the running total of Expected Goals for both teams as a step function across the ninety minutes, so the analyst can read the *narrative* of chance creation rather than just its sum. A steep section of a team's line is a period of sustained threat; a flat section is a period of control or sterility; a sudden tall step is a single high-value chance such as a penalty or a clear one-on-one. The gap between the two lines at full time is the match's **xG difference**, the cleanest single measure of which team deserved to win on the balance of chances.

In the Clásico, the chart lets the analyst answer questions a scoreline cannot: did Real Madrid's two goals come from a period of genuine dominance, or from two isolated moments in an otherwise even game? Did Barcelona's threat come early (suggesting Real Madrid grew into the game) or late (suggesting a nervy finish protecting a lead)? These temporal questions drive concrete coaching responses — a team that consistently concedes a flurry of late xG is a team with a game-management or fitness problem, regardless of whether those late chances were converted. The panel's limitation is that a single large step (a penalty) can visually dominate the curve and exaggerate one team's "deserved" advantage; the analyst reads it alongside the Shot Map to keep that in perspective.

### II.5 Match Analysis — Tactical Comparison

[[FIG:tactical_comparison|Match Analysis module — the Tactical Comparison panel, a head-to-head bar chart of the key match KPIs (possession, shots, passing, defensive actions) for Real Madrid versus Barcelona, computed from the real feed.]]

The Tactical Comparison panel distils the match into a head-to-head bar chart of the headline KPIs — possession, shots, shots on target, passing accuracy, defensive actions and so on — for the two teams side by side. Its purpose is communication speed: in a pre-match or post-match meeting a coach has seconds, not minutes, to absorb "who won which battle," and a paired bar chart is the fastest possible read. Each metric is a small tactical story — a possession bar heavily in Real Madrid's favour combined with a shots bar also in their favour confirms productive control; possession in their favour but shots *level* would instead flag sterile dominance. The panel exists because the human eye compares bar lengths far faster than it compares numbers in a table, and because side-by-side framing forces every metric into its proper *relative* context (a team's own number means little; the gap to the opponent means everything). Its limitation is the limitation of all such summaries: bars compare levels, not context, so a "lower" defensive-actions bar is not automatically worse — a team with the ball for 65% of the match *should* have fewer defensive actions.

### II.6 Match Analysis — Pass Map

[[FIG:pass_map|Match Analysis module — the Pass Map of Real Madrid's successful passes from the real feed, showing circulation structure, direction and the areas of densest passing.]]

The Pass Map renders Real Madrid's successful passes, revealing the *structure* of the team's possession — where the ball was circulated, in which directions it travelled, and which areas of the pitch the team occupied with the ball. The analyst reads it for two things above all: **progression** (does the ball move forward into dangerous areas, or does it circulate sideways and backwards in front of the opponent's block?) and **balance** (is the team's possession lop-sided to one flank, or does it switch play and stretch the opponent?). Against a deep, compact block of the kind Barcelona deployed at moments in this match, the Pass Map typically shows dense circulation in the middle third and a concentration of forward passes funnelled into the half-spaces and wide areas where the block can be unlocked. For a coach, an honest Pass Map is the difference between "we kept the ball well" and "we kept the ball but only in safe areas" — a distinction that determines whether the next training session works on patience or on penetration. The panel pairs naturally with Field Tilt and Final-Third Entries, which quantify the territorial outcome of the circulation the Pass Map describes.

### II.7 Match Analysis — Tactical Sub-Phases (A/B/C/D Bars) and the Phase Profile Radar

[[FIG:subphase_bars|Match Analysis module — the "Match Tactical Sub-Phases (A/B/C/D)" bar chart: the four phase indices (Offensive Moment, Defensive Transition, Defensive Moment, Offensive Transition) for the real match, each scored 0–100.]]

[[FIG:phase_radar|Match Analysis / Tactical Phases — the Tactical Phase Profile radar for the same real match. The four spokes are the A/B/C/D phase indices; the enclosed shape is the match's tactical "fingerprint." Values shown are computed live from the match's events.]]

These two panels present the same four numbers in two complementary ways, and together they are the dashboard's executive summary of *how the team played*. The four phase indices — **A · Offensive Moment**, **B · Defensive Transition**, **C · Defensive Moment**, **D · Offensive Transition** — are each a weighted composite of real event metrics, normalised to a 0–100 scale so that the four moments of the game can be compared on one picture (the exact formulas are given in §7.7). The **bar chart** is the precise, value-first view: a coach who wants the number reads the bars. The **radar** is the pattern-first view: a coach who wants the *shape* reads the polar plot, where the team's match collapses into a single, instantly recognisable silhouette.

For this fixture the profile is characteristically *possession-and-counter-press* in shape — strong in the Offensive Moment (the team created and controlled in settled possession) and strong in the Defensive Transition (the team counter-pressed aggressively to win the ball back), with lower scores in the Defensive Moment and the Offensive Transition. Read tactically, that silhouette says: *Real Madrid dominated the ball, hunted it back immediately when they lost it, but rarely had to defend a settled Barcelona attack and rarely needed to break at speed because they so seldom surrendered possession in the first place.* This is exactly the profile one expects of the superior side controlling a match — and the radar lets a coach confirm in one glance that the intended game model was executed. The essential caveat, repeated here because it matters for examiners, is that these indices are interpretive *rankings* on a 0–100 scale, not physical units; a "60" is not sixty of anything. The dashboard therefore always presents them beside the raw evidence panels — the Shot Map, the PPDA Trend, the Recovery Map — so that the summary is never read in isolation from the data that produced it.

### II.8 Match Analysis — Transition Metrics

[[FIG:transition|Match Analysis module — the Transition Metrics panel, quantifying Real Madrid's offensive transitions from the real feed: regains, the proportion producing a shot within the time window, and the xG generated.]]

The Transition Metrics panel isolates the offensive-transition phase — the counter-attack — and quantifies it directly from the event timeline. The dashboard locates every Real Madrid ball regain and tests whether a shot followed within the analyst-configurable window (the Transition Window Control, defaulting to twelve seconds), reporting the count of transitions, the fast-break efficiency (the share of regains converted into a shot inside the window) and the Expected Goals those transitions generated. This is the panel that turns the vague compliment "they're dangerous on the break" into a measured fact. Against a possession-minded opponent like Barcelona, transitions are doubly important because the opponent commits players forward and is therefore exposed to a quick counter when dispossessed; a high transition efficiency in this match would confirm that Real Madrid punished Barcelona's commitment, while a low one would suggest the team chose (or was forced) to slow the game and build rather than break. For a coach, the panel directly informs training: if transition output is a strength it is reinforced with rest-defence and counter-attack patterns; if it is underused it becomes a deliberate tactical instruction for the next fixture. Its honest limitation is definitional — "a transition" depends on the time window chosen, which is exactly why the dashboard exposes that window as a control rather than hiding it.

### II.9 Tactical Phases — Pressing Actions Map

[[FIG:press_map|Tactical Phases module — the Pressing Actions Map, showing the pitch locations of Real Madrid's pressing and defensive actions in the real match. The height of the actions reveals the team's pressing line.]]

Moving into the Tactical Phases module, the Pressing Actions Map plots *where on the pitch* Real Madrid engaged defensively — every tackle, interception and pressing action at its true location. The single most important thing this panel reveals is **pressing height**: a cloud of actions concentrated high up the pitch, near the opponent's penalty area, is the fingerprint of an aggressive high press that tries to win the ball close to the opponent's goal; a cloud concentrated around the halfway line is a mid-block; a cloud deep in the team's own half is a low block that absorbs pressure and defends the box. The map also reveals *asymmetry* — if a team presses more intensely down one flank, the opponent will exploit the other, and the map exposes that tendency before the opponent does. For a coach, this panel is the direct visual evidence of whether the pressing instruction was carried out: a team told to press high but whose action-cloud sits deep was pressed *through*, and the training response (compactness, pressing triggers, the timing of the first presser) follows immediately. For a scout, the same panel applied to an upcoming opponent reveals exactly where that opponent will try to win the ball, and therefore where the space to play through them will appear.

### II.10 Tactical Phases — Press Classification

[[FIG:press_class|Tactical Phases module — the Press Classification panel, categorising the team's defensive engagements by zone and intensity for the real match.]]

The Press Classification panel takes the same defensive-action data and organises it by category — by pitch zone and by the nature of the engagement — to turn the spatial picture of the Pressing Map into a structured breakdown. Where the map answers "where did we press?", this panel answers "what *kind* of press was it, and in what proportions?" — how much of the defensive work was high pressing versus mid-block containment versus deep defending. This matters because two teams with similar overall pressing-action counts can have completely different defensive identities: one front-loaded and aggressive, the other patient and contain-first. For a coach refining the team's out-of-possession identity, the classification is the quantitative check on whether the balance of pressing behaviours matches the intended model, and a shift in that balance from match to match (for example, pressing higher at home than away) is itself a finding worth surfacing in a staff review.

### II.11 Tactical Phases — PPDA Trend (Season)

[[FIG:ppda_trend|Tactical Phases module — the season-long PPDA trend (Passes Allowed Per Defensive Action) across the real LaLiga campaign, with the season average marked. Lower PPDA = more intense pressing.]]

The PPDA Trend panel is the dashboard's definitive measure of pressing *intensity* across the whole season, and one of the most important panels in the entire platform for a coach defining a pressing identity. PPDA — Passes Allowed Per Defensive Action — counts how many passes the opponent is permitted to complete for each defensive action Real Madrid make in the pressing zone; a **lower** value means a **more intense** press, because the opponent is challenged sooner and allowed fewer passes. The trend plots this match by match across the season with the season average marked as a reference line, so the analyst can see at once whether the press is consistent or wildly variable, and whether it adapts to context (a team will rationally press less intensely away at an elite opponent than at home against a weaker one). The dispersion of points around the average line is itself the message: a tight band signals a stable, drilled pressing identity; a wide scatter signals a press that is heavily game-state dependent. For a coach, a single match's PPDA — read against this season baseline — is the instant verdict on whether "we pressed well today" is true: a value well below the average confirms an aggressive press was executed, a value well above it confirms a passive one, whatever the post-match impression. This panel is the quantitative backbone of the Defensive Transition (Phase B) and Defensive Moment (Phase C) indices, both of which reward a lower PPDA.

### II.12 Tactical Phases — Ball Recoveries by Zone

[[FIG:recovery_map|Tactical Phases module — "Ball Recoveries by Pitch Zone" for the real match: a zonal bar chart and distribution donut showing where Real Madrid regained possession (Defensive / Middle / Attacking third).]]

The Ball Recoveries by Zone panel answers the question that pressing intensity alone cannot: not *how hard* the team pressed, but *where it actually won the ball back*. It divides the pitch into thirds and counts Real Madrid's recoveries in each, presenting both a bar chart and a distribution donut. In this real match the panel reports thirty-seven total recoveries, distributed as fourteen in the defensive third, eighteen in the middle third and five in the attacking third — a middle-third-dominant profile (48.6%) with a meaningful defensive-third share (37.8%) and a smaller attacking-third share (13.5%). This distribution is the tactical truth of the team's defensive work: a middle-third-dominant recovery profile describes a team that defends primarily through a compact mid-block, winning the ball in the centre of the pitch rather than either hunting it in the opponent's box or camping deep in its own. Read against the team's *intention*, this is the panel's power — the same distribution is excellent evidence of a working mid-block but disappointing evidence for a team that intended to press high and win the ball in the attacking third. The location of recoveries also feeds directly into transition danger: an attacking-third recovery is the most dangerous regain in football because the ball is won close to the opponent's goal with their defence disorganised, so a coach who wants more transition threat will look here first and ask why the attacking-third share is low. For a scout, an opponent's recovery map reveals exactly the height at which they defend, and therefore the most profitable way to play through or around them.

### II.13 Tactical Phases — Field Tilt

[[FIG:field_tilt|Tactical Phases module — the Field Tilt panel: the share of final-third activity belonging to Real Madrid across the real season, a measure of territorial dominance.]]

The Field Tilt panel measures **territorial dominance** — the share of all final-third activity that belongs to Real Madrid rather than the opponent. It is the antidote to the most common misreading of possession statistics. Possession tells you who held the ball; Field Tilt tells you who held it *in the area that matters*. A team can have 60% possession that is entirely sterile (circulating in its own half) and a Field Tilt barely above 50%; another can have 55% possession but a Field Tilt of 75%, meaning three-quarters of all the action in the final third was theirs. The second team is dominating territory; the first is merely holding the ball. For a coach, Field Tilt is the metric that validates the *purpose* of possession — it confirms whether the team's control of the ball is translating into sustained pressure in the opponent's third, exactly the question the Pass Map raises but cannot fully answer. Tracked across the season, as in this panel, it reveals whether the team's territorial dominance is a stable identity or a function of the opponent, and a drop in Field Tilt against a particular *type* of opponent (say, well-organised mid-table sides) is a precise, actionable tactical finding.

### II.14 How the Panels Interlock — One Coherent Match Story

The power of the dashboard is not in any single panel but in the way the panels *triangulate* a single conclusion from independent angles. For this Clásico the story assembles itself: the **Shot Map** shows high-volume, high-quality central chances and two goals; the **xG Accumulation** confirms the chances came from genuine periods of control rather than two flukes; the **Tactical Comparison** shows the headline KPIs tilted toward Real Madrid; the **Pass Map** and **Field Tilt** show the possession was territorial rather than sterile; the **Recovery Map** and **Pressing Map** show the ball was won back in a compact mid-block; the **PPDA Trend** locates that pressing intensity against the season norm; the **Transition Metrics** quantify the threat generated from those regains; and the **Phase Radar** collapses the whole performance into a single possession-and-counter-press silhouette. No single panel proves the conclusion; together they make it unarguable. This is precisely what a professional analytics platform is *for* — not to produce one clever number, but to let an analyst build a conclusion that survives challenge from every direction, and to let a coach act on it with confidence. A first-time user who works through these fourteen panels in order, for any match in the dataset, will arrive at a defensible tactical read of that match without needing any external explanation — which is the standard this documentation, and the dashboard it describes, are built to meet.

---

## Part III — Worked Coaching Scenarios

To demonstrate how the dashboard is used in practice rather than in theory, this part walks through four realistic scenarios a Real Madrid analyst and coaching staff would encounter across a season. Each scenario names the specific panels consulted, the metric thresholds that trigger a decision, and the tactical action that results. All metric behaviour described is exactly as the live dashboard computes it on the real dataset; the scenarios are illustrative *applications* of real panels, not invented data.

### III.1 Scenario — Preparing to Break Down a Deep, Compact Block

The most frequent tactical problem Real Madrid face domestically is the deep, compact low block: a mid-table or relegation-threatened side that concedes possession deliberately, defends with two banks of four close to its own goal, and waits to counter or to earn a point. The analyst's preparation begins in **Opponent Scout**, reading the opponent's style profile and their **Recovery Map** and **Pressing Actions Map** — if the opponent's recoveries and defensive actions cluster deep in their own third, the low-block intention is confirmed quantitatively, not just assumed. The analyst then consults the opponent's **Opponent Threat Heatmap** to locate the few zones from which they generate their counter-attacking danger, because the whole game plan must be built around dominating territory *without* exposing those specific transition lanes.

The in-match expectation is then framed using Real Madrid's own season panels. Against such a block the analyst expects very high possession but warns the coach that possession alone is the trap; the metrics that will actually matter are **Field Tilt** (which must climb above its season norm to confirm territorial dominance) and **Final-Third Entries**, especially through the **half-spaces** and **Zone 14**, since a packed central block is most reliably unlocked through those channels rather than through hopeful crosses. The coaching action that follows is concrete: rehearse third-man combinations and half-space rotations in training, instruct the full-backs to provide width so the block must stretch, and — critically — drill the rest-defence so that when a move breaks down the team is immediately compact enough to kill the opponent's only weapon, the counter. After the match, the same **Field Tilt**, **Pass Map** and **Transition** panels confirm whether the plan worked: high Field Tilt with central entries and few opponent transitions is success; high possession with a flat Field Tilt is the sterile-dominance failure the team set out to avoid.

### III.2 Scenario — Facing a High-Pressing Opponent in Europe

The opposite problem arrives in the Champions League against an elite, aggressive high press. Here the analyst's preparation centres on the opponent's **Pressing Actions Map** and **PPDA** profile: if those reveal a very low PPDA and a high, advanced action-cloud, the opponent intends to suffocate Real Madrid's build-up high up the pitch. The danger metric to respect is the opponent's **attacking-third recovery share** in their Recovery Map — a high value means they win the ball close to Real Madrid's goal, the most dangerous regain in football. The game plan therefore inverts the low-block approach: instead of seeking maximum possession, the team plans to *use the press against itself*. Because a high-pressing opponent commits numbers forward, the space behind their press is large, and Real Madrid's **Transition Metrics** become the primary attacking weapon rather than patient build-up. The coaching action is to drill quick, vertical playing-out patterns that bait the press and release a runner behind it, to accept a lower possession share as a deliberate choice, and to set the Transition Window Control to a short value when reviewing, because against this opponent the chances will come fast or not at all. Post-match, a strong Phase-D (Offensive Transition) score on the radar and a healthy transition xG confirm the plan was executed; a low Phase-D with a high count of deep, hurried clearances confirms the press won the battle and the next session must address press-resistance in the first build-up line.

### III.3 Scenario — Diagnosing a Defeat That "Felt Unlucky"

Every season produces a defeat the coaching staff feel they did not deserve, and the dashboard exists precisely to adjudicate that feeling with evidence rather than emotion. The analyst opens the match in **Match Analysis** and goes straight to the **xG Accumulation** chart and the **Goals vs xG** comparison in the Post-Match summary. There are three possible verdicts, each with a different consequence. If Real Madrid out-created the opponent heavily on xG but lost — a large positive xG difference with a negative scoreline — the defeat was genuine variance: the performance was good, the process sound, and the correct response is to change nothing and trust regression. If the xG was roughly level despite Real Madrid's strong subjective impression, the "we dominated" feeling was an illusion produced by sterile possession, and the **Field Tilt** and **Final-Third Entries** panels will confirm that the control never became territorial threat — the response is to work on penetration. If Real Madrid were actually out-created — a negative xG difference — then the defeat was deserved regardless of how the staff felt, and the **Recovery Map**, **PPDA Trend** and **Shot Map** (opponent shots) will localise exactly which phase failed. This scenario is the single clearest demonstration of why the dashboard exists: it replaces the most expensive thing in football, a wrong conclusion drawn from a misleading scoreline, with a defensible reading of the underlying performance.

### III.4 Scenario — Building and Monitoring the Team's Pressing Identity

Some uses of the dashboard are not about a single match but about shaping the team's identity over a block of matches. Suppose the coaching staff decide the team must press more aggressively. The dashboard makes this a measurable project. The baseline is the **PPDA Trend** in Tactical Phases, read in **Range mode** across the preceding ten matches to establish the current average and its variability. The target is a specific reduction in average PPDA, and the supporting metric is the **attacking-third recovery share** in the Recovery Map, which should rise as the press climbs. Each subsequent match is then a data point: the analyst checks the new PPDA against the trend line and the recovery distribution against the previous block, and reports to the coach whether the identity is shifting as intended or whether the team is reverting under pressure. Crucially, the dashboard also surfaces the *cost* of the change — a more aggressive press concedes more space behind it, so the staff watch the opponent's **Transition** threat and the team's **Defensive Moment (Phase C)** score for signs that the new aggression is being punished. This closed loop — set a target on a metric, act in training, measure the change match by match, and watch the trade-off metric — is the essence of evidence-led coaching, and it is exactly the workflow the platform is built to support.

---

## Part IV — Interpreting the Dashboard Responsibly (Common Pitfalls)

A professional analytics platform is only as good as the discipline with which it is read. This part documents the most common misreadings, so that a first-time user — examiner, coach or scout — avoids drawing the wrong conclusion from the right data.

**Never read a metric without its context.** This is the cardinal rule, repeated from Section 5 because it is violated most often. A PPDA of 12 is passive at home against a weak side and entirely correct away in a knockout. Possession of 65% is dominant against a peer and unremarkable against a side that has deliberately ceded the ball. Every number on the dashboard must pass through the lens of the Match Information header before it means anything. The dashboard deliberately places that header first for exactly this reason.

**Never confuse the phase indices with physical units.** The A/B/C/D scores are weighted composites normalised to 0–100. They are designed for *comparison* — match against match, phase against phase — not for literal interpretation. A Defensive Moment score of 16 does not mean "16 of something"; it means "low relative to the scale and to the team's other phases." The correct response to a striking phase score is always to drop down to the raw panel that produced it — the PPDA Trend, the Recovery Map, the opponent Shot Map — and read the evidence directly. The radar is a signpost, not a destination.

**Never treat xG as truth, only as a better question.** The platform's xG is a transparent, location-only model. It is a far better guide than raw shot counts, but it does not know whether a defender was blocking the shooting lane or whether the goalkeeper was out of position. A 0.6 xG chance that was actually struck under heavy pressure was worth less than the model says; an open one was worth more. xG is the start of the conversation about chance quality, not the end of it, and the dashboard pairs it with the Shot Map precisely so the analyst can see the locations the model is summarising.

**Never compare players by raw totals.** Until per-90 normalisation is added, a starter's 80 passes and a substitute's 20 passes are not comparable, because they reflect vastly different minutes on the pitch. When ranking players in the squad table, the analyst must mentally normalise by minutes, or restrict the comparison to players with similar playing time. This is a current limitation (Section 17), and a responsible reader keeps it in mind.

**Never mistake a proxy for the thing itself.** Possession on this platform is a pass-share proxy, not a stopwatch figure; field tilt is a touch-share proxy for territorial dominance; the pass network shows average positions, not literal passing lanes. These proxies are robust and standard, but they are proxies, and an honest analyst reports them as such. The platform's commitment to transparency means every proxy is documented; the reader's responsibility is to respect the documentation.

**Never read one match as a trend, or one trend as destiny.** A single match is a small, noisy sample; a striking single-match number is a hypothesis, not a conclusion. The dashboard's Range mode and its season-long trend panels exist to separate signal from noise, and the disciplined analyst uses them — confirming a single-match observation against the season pattern before reporting it to the coach. Equally, a season trend describes the past, not the guaranteed future; it informs expectation without dictating it.

**Always let the panels triangulate.** The single most important interpretive habit, demonstrated throughout Part II, is to never rest a conclusion on one panel. A tactical claim that is true will leave its fingerprint on several independent panels at once — the Shot Map, the xG curve, the Field Tilt, the Recovery Map. A claim visible in only one panel and contradicted or unsupported by the others is a candidate for being an artefact of that one view. The dashboard is built as a set of mutually-reinforcing windows onto the same match precisely so that the analyst can demand this kind of agreement before acting. Used this way — with context respected, proxies acknowledged, composites grounded in their raw evidence, and conclusions triangulated across panels — the platform delivers exactly what an elite club requires of its analysis department: not clever numbers, but reliable, defensible, actionable football truth.

---

## Appendix A — Data, Methodology and Reproducibility

- **Data source.** Opta Stats Perform event-level JSON, one file per match. The platform covers Real Madrid's matches across LaLiga, the UEFA Champions League and the Copa del Rey for 2024–25 and 2025–26 — 108 verified, clean match files (0 corrupt), of which 50 are 2025–26 fixtures (LaLiga 36, Champions League 12, Copa del Rey 2).
- **Pipeline.** `Opta JSON → parse & normalise events → compute match KPIs → aggregate to season / re-slice to player, phase, opponent → render → export`. Match files are cached for responsiveness, and bookkeeping events (period starts, formation markers) are filtered out.
- **No synthetic data.** Every figure on the dashboard is derived from observed events. Where a value cannot be computed from the event feed (e.g. true possession duration), the platform uses an explicit, documented proxy rather than inventing a number.
- **Consistency.** All seven modules share the same KPI definitions, so the same metric reads identically wherever it appears.

## Appendix B — Colour and Iconography Legend

- **Navy (`#0b1730`).** Structure, headers, navigation — Real Madrid brand identity.
- **Gold (`#c8a951`).** Emphasis, the active navigation state, highlighted markers (e.g. goals, radar vertices).
- **Royal blue.** Real Madrid in comparison contexts; primary chart series.
- **Green.** Positive outcomes / wins / Real Madrid in some comparisons.
- **Red.** Negative outcomes / losses / opponent / xG (against).
- **Orange.** Neutral / draws.
- **Icons.** 🏠 Overview · 📊 Match Analysis · 👤 Player Analysis · ⚔️ Tactical Phases · 🔭 Opponent Scout · 📈 Benchmarking · 📋 Report.

## Appendix C — Glossary

- **Phase A/B/C/D** — the four moments of play (offensive moment, defensive transition, defensive moment, offensive transition).
- **PPDA** — Passes Allowed Per Defensive Action; pressing-intensity metric (lower = more intense).
- **xG / xGA** — Expected Goals for / against; chance quality.
- **Field tilt** — share of final-third activity belonging to the team; territorial dominance.
- **Transition rate** — % of ball regains producing a shot within the chosen time window.
- **Zone 14** — the central zone just outside the penalty area, the most dangerous creative space.
- **Half-space** — the channel between the central zone and the wing, prized for incisive attacking.
- **High/mid/low block** — the height at which a team defends.
- **Counter-press** — winning the ball back immediately after losing it (the heart of Phase B).

---

*Real Madrid CF Tactical & Player Performance Analytics · Data: Opta Stats Perform · Built with Python, Pandas, NumPy, Plotly and Streamlit. Prepared by Sudhir Dahiya, Master's in Sports Analytics 2025–2026. This document describes the dashboard as implemented; features labelled "planned" or "future" are explicitly distinguished from current capability.*
