"""
generate_thesis_pdf.py
Builds the complete, submission-ready Master's project PDF — a combined
presentation + thesis for the Real Madrid Tactical Dashboard — with the live
dashboard figures embedded.

All formulas are transcribed from the live dashboard code; all figures are
rendered from real Opta data by generate_thesis_figures.py.

Output: Real_Madrid_Tactical_Dashboard_Thesis_Presentation.pdf
"""
from pathlib import Path
from datetime import date

from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, NextPageTemplate, PageBreak, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from matplotlib.font_manager import FontProperties, findfont

# ── Unicode-capable fonts (cover maths glyphs √ Σ ≥ ≈ → − ∈) ──────────────────
for name, (fam, wt) in {
    "DejaVu": ("DejaVu Sans", "normal"),
    "DejaVu-Bold": ("DejaVu Sans", "bold"),
    "DejaVu-Mono": ("DejaVu Sans Mono", "normal"),
}.items():
    pdfmetrics.registerFont(TTFont(name, findfont(FontProperties(family=fam, weight=wt))))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")
FONT, FONT_B, FONT_M = "DejaVu", "DejaVu-Bold", "DejaVu-Mono"

# ── Brand palette ────────────────────────────────────────────────────────────
NAVY = colors.HexColor("#0b1730"); NAVY2 = colors.HexColor("#162542")
GOLD = colors.HexColor("#c8a951"); GOLD_D = colors.HexColor("#a8882e")
CREAM = colors.HexColor("#f8f7f3"); GREY = colors.HexColor("#475569")
LGREY = colors.HexColor("#e2ddd0"); BLUE = colors.HexColor("#1d4ed8")
GREEN = colors.HexColor("#059669"); RED = colors.HexColor("#dc2626")
WHITE = colors.white; DARK = colors.HexColor("#1f2a3d")

ROOT = Path(__file__).parent
FIG = ROOT / "thesis_figures"
OUT = ROOT / "Real_Madrid_Tactical_Dashboard_Thesis_Presentation.pdf"
CONTENT_W = A4[0] - 36 * mm  # frame width

# ── Styles ───────────────────────────────────────────────────────────────────
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName=FONT_B, fontSize=15,
                    textColor=NAVY, spaceBefore=14, spaceAfter=4, leading=18)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName=FONT_B, fontSize=11.5,
                    textColor=GOLD_D, spaceBefore=9, spaceAfter=3, leading=14)
BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontName=FONT, fontSize=9.4,
                      textColor=DARK, leading=13.6, spaceAfter=5, alignment=TA_LEFT)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=12, spaceAfter=3)
MONO = ParagraphStyle("MONO", parent=BODY, fontName=FONT_M, fontSize=8.5,
                      textColor=NAVY, leading=12.5, backColor=colors.HexColor("#f1efe7"),
                      borderPadding=5, spaceAfter=5, leftIndent=4)
CELL = ParagraphStyle("CELL", parent=BODY, fontSize=8.4, leading=11, spaceAfter=0)
CELLH = ParagraphStyle("CELLH", parent=CELL, fontName=FONT_B, textColor=WHITE, fontSize=8.4)
CAP = ParagraphStyle("CAP", parent=BODY, fontSize=8, textColor=GREY, leading=11,
                     alignment=TA_CENTER, spaceAfter=8)

S = []
_fig_n = [0]


def section(num_title):
    return [Spacer(1, 2), Paragraph(num_title, H1),
            HRFlowable(width="100%", thickness=1.4, color=GOLD, spaceBefore=1, spaceAfter=6)]


def p(text, style=BODY):
    S.append(Paragraph(text, style))


def h2(t):
    S.append(Paragraph(t, H2))


def bullets(items):
    for it in items:
        S.append(Paragraph("•&nbsp;&nbsp;" + it, BULLET))


def table(rows, widths):
    data = [[Paragraph(c, CELLH) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(str(c), CELL) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), NAVY),
          ("LINEBELOW", (0, 0), (-1, 0), 1.1, GOLD),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
          ("LINEBELOW", (0, 1), (-1, -2), 0.4, LGREY),
          ("BOX", (0, 0), (-1, -1), 0.6, LGREY)]
    for i in range(2, len(data), 2):
        st.append(("BACKGROUND", (0, i), (-1, i), CREAM))
    t.setStyle(TableStyle(st))
    S.append(t); S.append(Spacer(1, 6))


def figure(filename, caption, max_w=CONTENT_W, max_h=150 * mm):
    fp = FIG / filename if not Path(filename).is_absolute() else Path(filename)
    if not fp.exists():
        return
    iw, ih = PILImage.open(fp).size
    w = max_w; h = w * ih / iw
    if h > max_h:
        h = max_h; w = h * iw / ih
    _fig_n[0] += 1
    img = Image(str(fp), width=w, height=h)
    img.hAlign = "CENTER"
    S.append(KeepTogether([Spacer(1, 4), img,
                           Paragraph(f"Figure {_fig_n[0]}. {caption}", CAP)]))


# ═══════════════════════════════════════════════════════════════════════════
# COVER (presentation-style)
# ═══════════════════════════════════════════════════════════════════════════
S.append(NextPageTemplate("body"))
S.append(Spacer(1, 30 * mm))
S.append(Paragraph("REAL MADRID CF", ParagraphStyle("c0", parent=H1, fontSize=30,
         alignment=TA_CENTER, textColor=NAVY, spaceAfter=2)))
S.append(Paragraph("Tactical &amp; Player Performance Dashboard", ParagraphStyle("c1",
         parent=BODY, fontSize=15, alignment=TA_CENTER, textColor=GOLD_D, spaceAfter=14)))
S.append(HRFlowable(width="60%", thickness=2, color=GOLD, spaceAfter=14))
S.append(Paragraph("Master's Final Project — Presentation &amp; Thesis", ParagraphStyle("c2",
         parent=H1, fontSize=17, alignment=TA_CENTER, textColor=NAVY, spaceAfter=6)))
S.append(Paragraph("Transforming Event-Level Football Data into Interactive Tactical Intelligence",
         ParagraphStyle("c3", parent=BODY, fontSize=11, alignment=TA_CENTER,
                        textColor=GREY, spaceAfter=26)))
cover = Table([
    ["Student", "Sudhir Dahiya"],
    ["Degree", "Master's in Sports Analytics (2025–2026)"],
    ["Institution", "Escuela Universitaria Real Madrid — Universidad Europea"],
    ["Case Club", "Real Madrid CF"],
    ["Data Provider", "Opta Stats Perform (event-level)"],
    ["Technology", "Python · Pandas · NumPy · Plotly · Streamlit (Dash core)"],
], colWidths=[40 * mm, 110 * mm])
cover.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (0, -1), FONT_B), ("FONTNAME", (1, 0), (1, -1), FONT),
    ("FONTSIZE", (0, 0), (-1, -1), 10.5), ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
    ("TEXTCOLOR", (1, 0), (1, -1), DARK), ("ALIGN", (0, 0), (0, -1), "RIGHT"),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LINEBELOW", (0, 0), (-1, -2), 0.4, LGREY)]))
cover.hAlign = "CENTER"
S.append(cover)
S.append(Spacer(1, 26 * mm))
S.append(Paragraph(f"Generated {date.today():%d %B %Y}", ParagraphStyle("c4", parent=BODY,
         fontSize=9, alignment=TA_CENTER, textColor=GREY)))
S.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY / ABSTRACT
# ═══════════════════════════════════════════════════════════════════════════
S += section("Executive Summary &amp; Abstract")
p("Elite football decision-making increasingly depends on converting vast, granular event data into "
  "tactical understanding faster than an opponent can. This project addresses a persistent gap: while "
  "event data is abundant, integrated tools that translate it into phase-specific tactical insight for "
  "coaching staff remain scarce. The <b>Real Madrid Tactical Dashboard</b> ingests Opta Stats Perform "
  "event-level JSON for 108 Real Madrid CF matches across three competitions (LaLiga, UEFA Champions "
  "League, Copa del Rey) and two seasons (2024–25, 2025–26), transforming them into match-, season-, "
  "and player-level tactical intelligence.")
p("The methodology is a reproducible Python pipeline that normalises raw event streams and computes a "
  "transparent KPI suite — a calibrated positional Expected Goals (xG) model, PPDA (pressing "
  "intensity), field tilt, and a four-phase tactical model (offensive moment, defensive transition, "
  "defensive moment, offensive transition) — rendered through an interactive Streamlit interface backed "
  "by Plotly. All metrics derive strictly from observed event data, with no synthetic values.")
p("The system lets analysts interrogate <i>how</i> Real Madrid plays rather than merely the scoreline: "
  "quantifying transition threat, pressing structure, attacking organisation, and performance against "
  "expectation. It demonstrates measurable value for pre-match preparation, post-match review, and "
  "opposition scouting, and establishes an extensible foundation for predictive and player-level "
  "analytics. The contribution is both practical — a club-grade tactical tool — and academic: a "
  "documented, formula-transparent framework for phase-based football analysis.")

h2("Key facts at a glance")
table([["Dimension", "Value"],
       ["Dataset", "108 clean Opta event files (0 corrupt)"],
       ["Competitions × seasons", "3 × 2 (LaLiga · UCL · Copa del Rey, 2024-25 & 2025-26)"],
       ["2025–26 matches", "50 (LaLiga 36 · UCL 12 · Copa 2)"],
       ["Core KPIs", "xG (positional), PPDA, field tilt, possession, pass accuracy"],
       ["Tactical model", "Four-phase A/B/C/D scoring (0–100)"],
       ["Stack", "Python · Pandas/NumPy · Plotly · Streamlit · Render CI/CD"]],
      [55 * mm, 99 * mm])
S.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# 1 · INTRODUCTION
# ═══════════════════════════════════════════════════════════════════════════
S += section("1 · Introduction")
h2("1.1 Football Analytics Background")
p("Football has transitioned from a results-recording discipline to a data-rich performance science. "
  "Providers such as Opta Stats Perform capture every on-ball event — passes, shots, duels, recoveries, "
  "set-piece restarts — with spatial coordinates and qualifier metadata, producing thousands of "
  "structured events per match. This density enables questions previously reserved for subjective "
  "observation: where a team regains the ball, how quickly it converts regains into shots, and whether "
  "its shot volume is sustainable relative to chance quality.")
h2("1.2 The Importance of Tactical Analysis")
p("Results are noisy; tactics are signal. A deflected goal can decide a match, but the underlying "
  "behaviours — pressing triggers, build-up structure, transition speed, territorial dominance — are "
  "stable, repeatable, and coachable. Quantifying them lets staff validate the intended game model, "
  "diagnose deviations, and prepare against an opponent's structural tendencies. xG and PPDA have "
  "become industry standards precisely because they track sustained performance better than raw "
  "outcomes.")
h2("1.3 Why Real Madrid CF as a Case Study")
p("Real Madrid competes simultaneously across LaLiga, the Champions League, and the Copa del Rey, "
  "generating a multi-competition dataset that exposes tactical adaptation across opponent quality "
  "tiers. Its identity blends possession dominance with devastating transition play, making it an ideal "
  "vehicle to demonstrate phase-based analysis, where the same team must be characterised differently "
  "in settled possession versus moments of transition.")

# ═══════════════════════════════════════════════════════════════════════════
# 2 · PROBLEM & OBJECTIVES
# ═══════════════════════════════════════════════════════════════════════════
S += section("2 · Problem Statement &amp; Objectives")
h2("2.1 Problem Statement")
p("Traditional football analysis suffers from three structural limitations this project targets:")
bullets([
    "<b>Outcome bias over behaviour.</b> Conventional reporting emphasises goals, possession %, and "
    "results — describing what happened, not how or why.",
    "<b>Fragmentation of tooling.</b> Analysts stitch together spreadsheets, notebooks, and slide decks; "
    "rarely is there one interactive environment linking season context, match detail, tactical phases, "
    "and player contribution in a consistent data model.",
    "<b>The data-to-decision gap.</b> Raw event feeds are inaccessible to most staff; translating a JSON "
    "stream into an actionable tactical statement needs an engineering and modelling layer most clubs "
    "lack in transparent form.",
])
p("<b>The problem addressed:</b> the absence of an integrated, transparent, event-driven tactical "
  "dashboard that quantifies Real Madrid's playing identity in phase-specific terms and presents it in "
  "a form usable by analysts and coaches.", BODY)
h2("2.2 Objectives")
bullets([
    "<b>Quantify tactical behaviour</b> with formula-transparent KPIs.",
    "<b>Implement phase-based match analysis</b> across the four canonical tactical phases.",
    "<b>Model performance versus expectation</b> via a calibrated positional xG model.",
    "<b>Deliver an interactive dashboard</b> over a reproducible Python pipeline.",
])

# ═══════════════════════════════════════════════════════════════════════════
# 3 · DATASET & METHODOLOGY
# ═══════════════════════════════════════════════════════════════════════════
S += section("3 · Dataset, Methodology &amp; KPI Formulas")
h2("3.1 Dataset & Scope")
p("The dataset comprises Opta Stats Perform event-level JSON for every Real Madrid CF fixture across the "
  "covered competitions and seasons. Each file holds a complete typed event stream (x/y coordinates, "
  "outcomes, player/team IDs, qualifiers) plus match metadata. The data is event (on-ball) only — there "
  "is no optical/GPS tracking — so possession is represented as a pass-share proxy, not a stopwatch "
  "duration.")
h2("3.2 KPI Computation")
table([["KPI", "Formula / definition"],
       ["Possession %", "RM passes ÷ (RM + opponent passes) × 100"],
       ["Pass accuracy %", "mean(outcome) × 100 over RM passes"],
       ["xG (positional)", "logistic of shot distance &amp; angle; penalties fixed at 0.76"],
       ["PPDA", "opponent passes (x ≥ 40) ÷ RM defensive actions (tackle/intercept/recovery, x ≥ 40)"],
       ["Field tilt", "RM final-third touches (x ≥ 67) ÷ all final-third touches × 100"]],
      [34 * mm, 120 * mm])
p("<b>Positional xG model:</b>")
S.append(Paragraph(
    "dx = (100 − x)·1.05 ;&nbsp; dy = (y − 50)·0.68<br/>"
    "dist = √(dx² + dy²)<br/>"
    "angle = | atan2(dy − 3.66, dx) − atan2(dy + 3.66, dx) |<br/>"
    "logit(xG) = −3.785 − 0.0337·dist + 3.64·angle<br/>"
    "xG = 1 / (1 + e^−logit), &nbsp;clipped to [0.01, 0.99]", MONO))
h2("3.3 Tactical Phase Segmentation")
p("Four phases are scored on a normalised 0–100 scale by blending weighted components:")
S.append(Paragraph(
    "A · Offensive Moment&nbsp;&nbsp;&nbsp;= pass_acc·0.45 + (Σxg·10)·0.35 + (shots·2.5)·0.20<br/>"
    "B · Defensive Transition = (100/(1+PPDA))·0.55 + ((recov+inter)·1.8)·0.45<br/>"
    "C · Defensive Moment&nbsp;&nbsp;&nbsp;&nbsp;= (100/(1+PPDA))·0.40 + max(0, 40 − opp_shots·2)·0.60<br/>"
    "D · Offensive Transition = trans_rate·0.65 + (Σxg·7)·0.35", MONO))
p("where <b>trans_rate</b> = the percentage of ball regains (recovery/interception/tackle) that produce "
  "a Real Madrid shot within 15 seconds — a direct, event-timed measure of transition threat.")

# ═══════════════════════════════════════════════════════════════════════════
# 4 · SYSTEM ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════
S += section("4 · System Architecture")
S.append(Paragraph(
    "OPTA STATS PERFORM (event JSON)<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;↓&nbsp; data_loader.py — parse &amp; normalise (Pandas / NumPy)<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;↓&nbsp; KPI &amp; MODEL LAYER — xG · PPDA · field tilt · phase scoring · player stats<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;↓&nbsp; VISUALISATION LAYER — Plotly (shot maps, heatmaps, radars, trends)<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;↓&nbsp; PRESENTATION LAYER — Streamlit UI + Dash analytics core<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;↓&nbsp; EXPORT LAYER — automated PDF / DOCX reporting", MONO))
table([["Layer", "Technology", "Role"],
       ["Data processing", "Python, Pandas, NumPy", "Parsing, normalisation, aggregation"],
       ["Modelling", "Python (math/SciPy)", "xG, PPDA, phase scoring"],
       ["Visualisation", "Plotly", "Interactive pitch maps, charts, radars"],
       ["Interface", "Streamlit (Dash heritage)", "Interactive multi-page exploration"],
       ["Reporting", "ReportLab, python-docx", "Automated report export"],
       ["Deployment", "Render (CI/CD from GitHub)", "Public, auto-deployed web service"]],
      [32 * mm, 52 * mm, 70 * mm])
S.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# 5 · DASHBOARD MODULES
# ═══════════════════════════════════════════════════════════════════════════
S += section("5 · Dashboard Modules")
p("Each module is summarised by its metrics, visualisation, and implementation status. The requested "
  "module taxonomy is mapped onto the implemented multi-page architecture.")
table([["Module", "Implemented dashboard panels", "Status"],
       ["Pre-Match Analysis", "Goals Per Match, Shots &amp; Pass Accuracy Trend, season KPIs, xG vs xGA", "Implemented"],
       ["Attacking Transitions", "Transition Metrics, Extended Transition Analysis, A/B/C/D sub-phases, 5–15 s window", "Implemented"],
       ["Organized Attack", "Shot Map, Shot Zone Map, Pass Map, Build-Up Network, Zone 14, Progressive Passes", "Implemented"],
       ["Defensive Strategy", "PPDA Trend, Pressing Actions Map, Defensive Actions Map", "Implemented"],
       ["Set Piece Analysis", "Set Piece Efficiency; set-piece tendencies (corners, shots ≤20 s)", "Implemented"],
       ["Possession Recovery", "Ball Recoveries by Zone (zonal heatmap)", "Implemented"],
       ["Final-Third Entries", "Final Third Entry Analysis, Field Tilt card &amp; trend (x ≥ 67)", "Implemented"],
       ["Post-Match Analysis", "Post-Match Tactical Summary, goals vs xG, defensive actions", "Implemented"],
       ["Match Information", "Score, opponent, venue, competition, result", "Implemented"]],
      [38 * mm, 88 * mm, 28 * mm])

# ═══════════════════════════════════════════════════════════════════════════
# 6 · TACTICAL CASE STUDY (with figures)
# ═══════════════════════════════════════════════════════════════════════════
S += section("6 · Tactical Insights — Real Madrid Case Study")
p("Figures below are the dashboard's computed outputs, generated live from real Opta event data via the "
  "dashboard's own pipeline. The showcase fixture is Real Madrid 2–1 Barcelona (LaLiga 2025–26, "
  "Matchday 10). xG derives from the project's positional model, not the provider's proprietary xG.",
  ParagraphStyle("note", parent=BODY, fontSize=8.6, textColor=GREY))

h2("6.1 Transition-Heavy Attacking Identity")
p("Real Madrid's offensive signature is the speed of conversion from regain to shot. The four-phase "
  "profile below quantifies a single match across the offensive moment, defensive transition, defensive "
  "moment, and offensive transition phases on a normalised 0–100 scale.")
figure("fig_phase_radar.png",
       "Four-phase tactical profile (A/B/C/D) for Real Madrid vs Barcelona, computed by the dashboard's "
       "phase-scoring model. The pronounced offensive-moment axis reflects settled-attack productivity.",
       max_h=120 * mm)

h2("6.2 Organised Attack &amp; Efficiency vs Expectation")
p("Across LaLiga 2025–26 the dashboard reports ~58.8% possession and ~87.7% pass accuracy; with a "
  "season xG-for of ≈66.0 against 72 goals scored, the side marginally outperforms chance quality "
  "(goals/xG just above 1.0) — flagged as a regression watch-point. The shot map localises chance "
  "creation: marker size is proportional to positional xG, and goals are highlighted.")
figure("fig_shot_map.png",
       "Real Madrid shot map for the showcase fixture (get_shot_data pipeline). The concentration of "
       "high-xG attempts inside the box illustrates central penetration; 24 shots, 2 goals, 3.34 xG.",
       max_h=120 * mm)

h2("6.3 Defensive Structure &amp; Pressing")
p("PPDA values (season average ≈9.5, with elite single-match presses near 3.3) describe a side that "
  "presses with controlled, selective intensity, then defends in a compact mid-block. The season trend "
  "below makes the variance — and its game-state dependence — explicit.")
figure("fig_ppda_trend.png",
       "Pressing intensity (PPDA) across all 36 LaLiga 2025–26 matchdays via calc_ppda (lower = more "
       "intense press). The dashed line marks the season average; variance shows selective pressing.",
       max_h=95 * mm)

h2("6.4 Strengths, Weaknesses &amp; Tactical Identity")
p("<b>Strengths:</b> elite, time-bounded transition threat; possession dominance converted into "
  "territory; strong chance suppression (low xGA). <b>Watch-points:</b> mild over-performance versus "
  "xG-for (variance risk); selective pressing leaves occasional mid-block gaps against deep blocks.")
p("<b>Tactical identity:</b> in data, Real Madrid is a proactive possession side with a world-class "
  "transition engine and disciplined defensive economy — winning through chance suppression and "
  "ruthless conversion of regains, rather than through pressing volume alone.")

# ═══════════════════════════════════════════════════════════════════════════
# 7 · IMPLEMENTATION STATUS
# ═══════════════════════════════════════════════════════════════════════════
S += section("7 · Implementation Status — Current vs Future")
table([["Feature / Module", "Status", "Improvements Needed"],
       ["Match information &amp; metadata", "Implemented", "Referee, weather, formation parsing"],
       ["Season KPIs &amp; trends (pre-match)", "Implemented", "Rolling-form, opponent-adjusted baselines"],
       ["xG vs xGA / performance vs expectation", "Implemented", "Validate model vs provider xG"],
       ["Shot maps (organised attack)", "Implemented", "xG-weighted markers, body-part split"],
       ["Pass networks", "Implemented", "Edge-weighted lanes, phase filtering"],
       ["PPDA &amp; pressing", "Implemented", "Pressing-trigger detection, by-zone PPDA"],
       ["Tactical phase scoring (A/B/C/D)", "Implemented", "Model validation; weighting sensitivity"],
       ["Post-match review (xG curve)", "Implemented", "Automated narrative summary"],
       ["Player analysis (table, radars)", "Implemented", "Per-90 normalisation, role radars"],
       ["Benchmarking (cross-competition)", "Implemented", "League-percentile context"],
       ["Opponent analysis / scouting", "Implemented", "Opponent tendency modelling"],
       ["Attacking transitions (Transition Metrics)", "Implemented", "Time-to-first-shot distribution"],
       ["Possession recovery (Recoveries by Zone)", "Implemented", "High/mid/low zonal comparison"],
       ["Final-third entries (+ Field Tilt)", "Implemented", "xG-from-entries, shot-probability maps"],
       ["Set-piece analysis (Set Piece Efficiency)", "Implemented", "Dedicated set-piece shot maps"],
       ["Automated PDF/DOCX reporting", "Implemented", "Templated per-opponent export"],
       ["Cloud deployment (Render CI/CD)", "Implemented", "Caching/CDN for large dataset"],
       ["Shots-conceded heatmap", "Planned", "Defensive shot-concession map (count shown today)"],
       ["Block-height visualisation", "Planned", "Defensive line-height metric &amp; viz"]],
      [56 * mm, 24 * mm, 74 * mm])
S.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# 8 · LIMITATIONS & FUTURE SCOPE
# ═══════════════════════════════════════════════════════════════════════════
S += section("8 · Limitations &amp; Future Scope")
h2("8.1 Limitations")
bullets([
    "<b>Event data only — no tracking.</b> Off-ball positioning, pressing distances and defensive shape "
    "are approximated, not measured.",
    "<b>Possession is a proxy</b> (pass-volume share), not a stopwatch figure.",
    "<b>xG is a transparent positional model</b> (distance + angle), not a provider model — auditable "
    "but simplified.",
    "<b>Limited predictive modelling</b> — the system is descriptive/diagnostic, not yet forecasting.",
    "<b>No real-time ingestion</b> — analysis is post-hoc on stored files.",
    "<b>Phase scores are weighted composites</b> — interpretive 0–100 indices, not physical units.",
])
h2("8.2 Future Scope")
bullets([
    "<b>Player-level depth:</b> per-90 contributions, role-specific radars, on/off impact.",
    "<b>Multi-season expansion</b> for longitudinal tactical-evolution tracking.",
    "<b>Opponent modelling:</b> automated pressing triggers, build-up and set-piece tendencies.",
    "<b>Predictive analytics:</b> xG/xGA forecasting, expected-points, transition-threat prediction.",
    "<b>AI-driven tactical clustering</b> of phases and possession sequences to surface patterns.",
    "<b>Tracking-data integration</b> for off-ball positioning, compactness, and pitch control.",
    "<b>Video integration</b> linking each metric to synchronised clip timestamps.",
    "<b>Real-time ingestion</b> for in-match decision support.",
])

# ═══════════════════════════════════════════════════════════════════════════
# 9 · TOOLS & CONCLUSION
# ═══════════════════════════════════════════════════════════════════════════
S += section("9 · Tools, Technologies &amp; Conclusion")
table([["Category", "Technology", "Purpose"],
       ["Language", "Python 3.11", "Core implementation"],
       ["Data", "Pandas, NumPy", "Event parsing, vectorised aggregation"],
       ["Modelling", "Python math / SciPy", "xG, PPDA, phase scoring"],
       ["Visualisation", "Plotly", "Interactive pitch maps, charts, radars"],
       ["Interface", "Streamlit (Dash core)", "Interactive multi-page dashboard"],
       ["Reporting", "ReportLab, python-docx", "Automated PDF/DOCX export"],
       ["Data format", "Opta Stats Perform event JSON", "Source event data"],
       ["VC / CI-CD", "Git, GitHub, Render", "Reproducibility and deployment"]],
      [30 * mm, 52 * mm, 72 * mm])
h2("9.1 Conclusion")
p("This project delivers a working, club-grade Real Madrid Tactical Dashboard that closes the "
  "data-to-decision gap for event-level football analysis. By normalising 108 Opta match files into a "
  "reproducible pipeline and computing a transparent, formula-documented KPI suite — positional xG, "
  "PPDA, field tilt, and a four-phase tactical model — it characterises how Real Madrid plays, not "
  "merely the result.")
p("<b>Tactical relevance:</b> the platform objectively confirms and quantifies Real Madrid's identity — "
  "a possession-dominant side with an elite transition engine and disciplined chance suppression — and "
  "surfaces actionable watch-points. <b>Value for staff:</b> integrated pre-match, post-match, "
  "tactical-phase, and opposition views with automated reporting compress an analyst's preparation into "
  "one interactive environment. <b>Academic contribution:</b> a fully documented, auditable methodology "
  "for phase-based football analysis, traceable to explicit formulas and observed data, with no "
  "synthetic values — reproducible and extensible.")
S.append(Spacer(1, 8))
S.append(HRFlowable(width="100%", thickness=1, color=GOLD))
S.append(Paragraph("Real Madrid CF Tactical &amp; Player Performance Analytics · Data: Opta Stats "
                   "Perform · Built with Python, Pandas, NumPy, Plotly &amp; Streamlit", CAP))

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX — POSTER
# ═══════════════════════════════════════════════════════════════════════════
if (ROOT / "poster.png").exists():
    S.append(PageBreak())
    S += section("Appendix · Project Summary Poster")
    p("The accompanying summary poster condenses the platform's season KPIs, dashboard modules, key "
      "analytical findings, and technical pipeline into a single visual.", BODY)
    figure(str(ROOT / "poster.png"),
           "Real Madrid CF Tactical &amp; Player Performance Analytics — project summary poster.",
           max_h=215 * mm)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE FRAME
# ═══════════════════════════════════════════════════════════════════════════
def header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY); canvas.rect(0, h - 16 * mm, w, 16 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD); canvas.rect(0, h - 16 * mm, w, 1.2 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE); canvas.setFont(FONT_B, 10)
    canvas.drawString(18 * mm, h - 10.5 * mm, "Real Madrid Tactical Dashboard — Master's Project")
    canvas.setFillColor(GOLD); canvas.setFont(FONT, 7.5)
    canvas.drawRightString(w - 18 * mm, h - 10.5 * mm, "Opta Stats Perform")
    canvas.setFillColor(GREY); canvas.setFont(FONT, 7.5)
    canvas.drawString(18 * mm, 10 * mm, "Sudhir Dahiya · Master's in Sports Analytics 2025–2026")
    canvas.drawRightString(w - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(LGREY); canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 13 * mm, w - 18 * mm, 13 * mm)
    canvas.restoreState()


doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=22 * mm, bottomMargin=16 * mm,
                      title="Real Madrid Tactical Dashboard — Master's Project Presentation & Thesis",
                      author="Sudhir Dahiya")
doc.addPageTemplates([PageTemplate(id="body",
                      frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")],
                      onPage=header_footer)])
doc.build(S)
print(f"Saved → {OUT}  ({OUT.stat().st_size // 1024} KB, figures embedded: {_fig_n[0]})")
