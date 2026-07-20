"""
generate_fmp_final_pdf.py
Final updated Master's Final Project (FMP) PDF for the Real Madrid Tactical
Dashboard. Follows the six-phase FMP structure, with all content reconciled to
the EXISTING dashboard implementation and the live data figures embedded.

Output: Real_Madrid_Tactical_Dashboard_FMP_Final.pdf
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

for name, (fam, wt) in {
    "DejaVu": ("DejaVu Sans", "normal"),
    "DejaVu-Bold": ("DejaVu Sans", "bold"),
    "DejaVu-Mono": ("DejaVu Sans Mono", "normal"),
}.items():
    pdfmetrics.registerFont(TTFont(name, findfont(FontProperties(family=fam, weight=wt))))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")
FONT, FONT_B, FONT_M = "DejaVu", "DejaVu-Bold", "DejaVu-Mono"

NAVY = colors.HexColor("#0b1730"); GOLD = colors.HexColor("#c8a951")
GOLD_D = colors.HexColor("#a8882e"); CREAM = colors.HexColor("#f8f7f3")
GREY = colors.HexColor("#475569"); LGREY = colors.HexColor("#e2ddd0")
BLUE = colors.HexColor("#1d4ed8"); GREEN = colors.HexColor("#059669")
AMBER = colors.HexColor("#b45309"); RED = colors.HexColor("#dc2626")
WHITE = colors.white; DARK = colors.HexColor("#1f2a3d")

ROOT = Path(__file__).parent
FIG = ROOT / "thesis_figures"
OUT = ROOT / "Real_Madrid_Tactical_Dashboard_FMP_Final.pdf"
CW = A4[0] - 36 * mm

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName=FONT_B, fontSize=14.5,
                    textColor=NAVY, spaceBefore=13, spaceAfter=4, leading=17)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName=FONT_B, fontSize=11,
                    textColor=GOLD_D, spaceBefore=8, spaceAfter=3, leading=13)
BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontName=FONT, fontSize=9.3,
                      textColor=DARK, leading=13.4, spaceAfter=5, alignment=TA_LEFT)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=12, spaceAfter=2.5)
MONO = ParagraphStyle("MONO", parent=BODY, fontName=FONT_M, fontSize=8.4,
                      textColor=NAVY, leading=12.3, backColor=colors.HexColor("#f1efe7"),
                      borderPadding=5, spaceAfter=5, leftIndent=4)
CELL = ParagraphStyle("CELL", parent=BODY, fontSize=7.9, leading=10.4, spaceAfter=0)
CELLH = ParagraphStyle("CELLH", parent=CELL, fontName=FONT_B, textColor=WHITE, fontSize=8.1)
CAP = ParagraphStyle("CAP", parent=BODY, fontSize=8, textColor=GREY, leading=11,
                     alignment=TA_CENTER, spaceAfter=8)

S = []
_fig = [0]


def section(t):
    return [Spacer(1, 2), Paragraph(t, H1),
            HRFlowable(width="100%", thickness=1.4, color=GOLD, spaceBefore=1, spaceAfter=6)]


def p(t, st=BODY): S.append(Paragraph(t, st))
def h2(t): S.append(Paragraph(t, H2))
def bullets(items):
    for it in items: S.append(Paragraph("•&nbsp;&nbsp;" + it, BULLET))


def status_chip(label):
    c = {"Implemented": GREEN, "Partial": AMBER, "Planned": RED}.get(label, GREY)
    return f'<font color="#{c.hexval()[2:]}"><b>{label}</b></font>'


def table(rows, widths, header_bg=NAVY):
    data = [[Paragraph(c, CELLH) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(str(c), CELL) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), header_bg),
          ("LINEBELOW", (0, 0), (-1, 0), 1.1, GOLD),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          ("LINEBELOW", (0, 1), (-1, -2), 0.4, LGREY),
          ("BOX", (0, 0), (-1, -1), 0.6, LGREY)]
    for i in range(2, len(data), 2):
        st.append(("BACKGROUND", (0, i), (-1, i), CREAM))
    t.setStyle(TableStyle(st)); S.append(t); S.append(Spacer(1, 6))


def figure(filename, caption, max_h=130 * mm):
    fp = FIG / filename if not Path(filename).is_absolute() else Path(filename)
    if not fp.exists(): return
    iw, ih = PILImage.open(fp).size
    w = CW; h = w * ih / iw
    if h > max_h: h = max_h; w = h * iw / ih
    _fig[0] += 1
    img = Image(str(fp), width=w, height=h); img.hAlign = "CENTER"
    S.append(KeepTogether([Spacer(1, 3), img,
             Paragraph(f"Figure {_fig[0]}. {caption}", CAP)]))


# ═══════════════════════════════ COVER ═════════════════════════════════════
S.append(NextPageTemplate("body"))
S.append(Spacer(1, 28 * mm))
S.append(Paragraph("REAL MADRID CF", ParagraphStyle("c0", parent=H1, fontSize=29,
         alignment=TA_CENTER, textColor=NAVY, spaceAfter=2)))
S.append(Paragraph("Tactical Dashboard", ParagraphStyle("c1", parent=H1, fontSize=22,
         alignment=TA_CENTER, textColor=GOLD_D, spaceAfter=12)))
S.append(HRFlowable(width="60%", thickness=2, color=GOLD, spaceAfter=12))
S.append(Paragraph("Final Master Project (FMP)", ParagraphStyle("c2", parent=H1, fontSize=16,
         alignment=TA_CENTER, textColor=NAVY, spaceAfter=4)))
S.append(Paragraph("Quantifying Real Madrid's Game Model from Event-Level Football Data",
         ParagraphStyle("c3", parent=BODY, fontSize=11, alignment=TA_CENTER, textColor=GREY,
                        spaceAfter=24)))
cov = Table([
    ["Student", "Sudhir Dahiya"],
    ["Degree", "Master's in Sports Analytics (2025–2026)"],
    ["Institution", "Escuela Universitaria Real Madrid — Universidad Europea"],
    ["Case Club", "Real Madrid CF"],
    ["Data Source", "Opta Stats Perform — event-level match data (JSON)"],
    ["Stack", "Python · Pandas · NumPy · Plotly · Streamlit (Dash core)"],
], colWidths=[38 * mm, 112 * mm])
cov.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (0, -1), FONT_B), ("FONTNAME", (1, 0), (1, -1), FONT),
    ("FONTSIZE", (0, 0), (-1, -1), 10.3), ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
    ("TEXTCOLOR", (1, 0), (1, -1), DARK), ("ALIGN", (0, 0), (0, -1), "RIGHT"),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LINEBELOW", (0, 0), (-1, -2), 0.4, LGREY)]))
cov.hAlign = "CENTER"; S.append(cov)
S.append(Spacer(1, 24 * mm))
S.append(Paragraph(f"Final updated version · {date.today():%d %B %Y}", ParagraphStyle("c4",
         parent=BODY, fontSize=9, alignment=TA_CENTER, textColor=GREY)))
S.append(PageBreak())

# ═══════════════════ 1 · PROJECT, OBJECTIVE & VALUE ════════════════════════
S += section("1 · General Project, Objective &amp; Value")
h2("1.1 General Project")
p("This project analyses Real Madrid CF's tactical behaviour across competitive matches using "
  "event-level football data, providing actionable insights for match preparation, opposition "
  "analysis, and performance evaluation.")
h2("1.2 Objective")
p("The project quantifies Real Madrid's game model and tactical behaviour from event-level data, "
  "seeking to understand <i>how</i> Real Madrid play — not just whether they win. By breaking matches "
  "into distinct tactical phases (attacking, defending, transitions, set pieces, and possession "
  "recovery), the analysis identifies:")
bullets(["Tactical strengths and weaknesses",
         "Spatial and temporal patterns of play",
         "Differences between expected and actual performance (e.g. goals vs xG)",
         "Comparisons between Real Madrid and opponents, and trends across matches"])
h2("1.3 Value")
p("The dashboard gives coaching staff actionable insights for match preparation, opponent scouting, "
  "and tactical optimisation through interactive visualisations showing where Real Madrid attacks and "
  "defends most effectively. It bridges data analytics and tactical football understanding:")
bullets(["Supports tactical preparation and opposition scouting",
         "Offers evidence-based insights into attacking/defensive efficiency",
         "Provides a foundation for professional football analytics"])

# ═══════════════════ 2 · DATASET & SCOPE ══════════════════════════════════
S += section("2 · Dataset &amp; Scope")
p("<b>Update vs proposal:</b> the existing dashboard is built on <b>Opta Stats Perform event-level "
  "JSON</b> (not CSV), and already covers a far larger corpus than five matches. The case-study lens "
  "foregrounds recent LaLiga fixtures, while the platform indexes the full multi-competition dataset.",
  ParagraphStyle("upd", parent=BODY, fontSize=8.7, textColor=GREY))
table([["Dimension", "Coverage in the existing dashboard"],
       ["Competitions", "LaLiga · UEFA Champions League · Copa del Rey"],
       ["Seasons", "2024–25 and 2025–26"],
       ["Total clean match files", "108 (verified, 0 corrupt)"],
       ["2025–26 matches", "50 (LaLiga 36 · UCL 12 · Copa 2)"],
       ["Case-study lens", "Recent LaLiga 2025–26 fixtures, home and away"],
       ["Data type", "Passes, shots, duels, interceptions, recoveries, set-piece restarts, transitions"],
       ["Granularity", "Single-event (on-ball), Opta 0–100 pitch coordinates"]],
      [42 * mm, 112 * mm])
p("The data is event (on-ball) only — there is no optical/GPS tracking — so possession is represented "
  "as a pass-share proxy rather than a stopwatch duration.")

# ═══════════════════ 3 · SIX-PHASE APPROACH ═══════════════════════════════
S += section("3 · Dashboard Architecture &amp; Analytical Approach")
h2("3.1 The Dashboard — Seven Application Modules")
p("The deployed dashboard is organised as a seven-module interface (the top-navigation of the live app). "
  "The six analytical tactical phases described below are not separate screens — they are the analytical "
  "framework realised <i>inside</i> these modules, principally within Tactical Phases and Match Analysis.")
table([["#", "Module (app navigation)", "Key metrics &amp; visualisations", "Status"],
       ["1", "🏠 Overview", "Season KPIs, W/D/L &amp; results table, xG vs xGA, possession trends",
        status_chip("Implemented")],
       ["2", "📊 Match Analysis", "Shot/zone maps, xG curve, pass &amp; build-up networks, transitions, "
        "set-piece efficiency, final-third entries, defensive-actions map, sub-phases",
        status_chip("Implemented")],
       ["3", "👤 Player Analysis", "Squad table, per-player stats, multi-radar, touch heatmap, "
        "lineup status, chance-creator %", status_chip("Implemented")],
       ["4", "⚔️ Tactical Phases", "PPDA season trend, pressing &amp; recoveries-by-zone maps, "
        "four-phase A/B/C/D deep-dive, field tilt", status_chip("Implemented")],
       ["5", "🔭 Opponent Scout", "Opponent context &amp; profiling for pre-match preparation",
        status_chip("Implemented")],
       ["6", "📈 Benchmarking", "Cross-competition KPI comparison and trends",
        status_chip("Implemented")],
       ["7", "📋 Report", "Automated PDF / DOCX match &amp; season reports",
        status_chip("Implemented")]],
      [8 * mm, 40 * mm, 78 * mm, 28 * mm])
p("<b>Mapping the analytical phases to modules:</b> Pre-Match → Overview + Opponent Scout + Benchmarking; "
  "Attacking Transition, Defensive Strategy &amp; Possession Recovery → Tactical Phases; Organized Attack "
  "&amp; Final-Third Entries → Match Analysis (+ field tilt in Tactical Phases); Post-Match → Match "
  "Analysis; reporting → Report.", ParagraphStyle("map", parent=BODY, fontSize=8.7, textColor=GREY))

h2("3.2 Pre-Match Analysis (Expectation Setting)")
p("<b>Includes:</b> goals for/against, xG vs xGA, possession trends; opponent context (league position, "
  "defensive style); expected match difficulty. <b>Outcome:</b> tactical context before kickoff. "
  "<b>Status:</b> " + status_chip("Implemented") + " via the Overview, Opponent Scout and Benchmarking "
  "modules.")

h2("3.3 In-Match Tactical-Phase Analysis (within Tactical Phases &amp; Match Analysis)")
p("Every phase below is <b>implemented</b> in the live dashboard, each with one or more dedicated "
  "panels (named in the table). The right column lists genuine future enhancements only.",
  ParagraphStyle("impl", parent=BODY, fontSize=8.7, textColor=GREY))
table([["Phase", "Metrics", "Implemented panels (live app)", "Future enhancement"],
       ["Attacking Transition",
        "Transitions/match, shots/goals from transitions, configurable regain→shot window "
        "(5/10/12/15 s), fast-break efficiency %, transition xG",
        "“Transition Metrics”, “Extended Transition Analysis”, “Match Tactical Sub-Phases (A/B/C/D)”",
        "Explicit time-to-first-shot distribution"],
       ["Organized Attack",
        "Possession %, pass sequences, final-third entries, shot-creation zones, progressive passes",
        "“Shot Map”, “Shot Zone Map”, “Pass Map”, “Build-Up Network”, “Zone 14 Passing”, "
        "“Crossing Patterns”, “Progressive Passes”, “Chance Creation Heatmap”",
        "Edge-weighted passing-lane networks"],
       ["Defensive Strategy",
        "PPDA, defensive actions per zone, shots conceded",
        "“PPDA Trend (Season)”, “Pressing Actions Map”, “Defensive Actions Map”",
        "Block-height viz; shots-conceded heatmap"],
       ["Set Pieces",
        "Corners, shots, goals from set pieces, shots within 20 s of a corner",
        "“Set Piece Efficiency” (Match); set-piece tendencies (Opponent Scout)",
        "Dedicated set-piece shot maps"],
       ["Possession Recovery",
        "Interceptions, ball recoveries, recovery counts per pitch zone",
        "“Ball Recoveries by Zone” (zonal heatmap)",
        "High/mid/low recovery-zone comparison"],
       ["Final-Third Entries",
        "Entry locations, final-third dominance (field tilt, x ≥ 67)",
        "“Final Third Entry Analysis (RM)”, “Field Tilt (Final Third %)” card &amp; season trend",
        "xG-from-entries; shot-probability maps"]],
      [25 * mm, 40 * mm, 45 * mm, 44 * mm])

h2("3.4 Post-Match Analysis (Result vs Performance)")
p("<b>Comparison:</b> goals vs xG, expected vs actual results, match vs average performance. "
  "<b>Metrics:</b> goals vs xG, recoveries, defensive actions. <b>Outcome:</b> evaluates whether "
  "results reflect tactical dominance or efficiency. <b>Status:</b> " + status_chip("Implemented") +
  " via the post-match KPI panel and xG-accumulation curve.")
S.append(PageBreak())

# ═══════════════════ 4 · CASE STUDY WITH FIGURES ══════════════════════════
S += section("4 · Tactical Insights — Live Dashboard Evidence")
p("All figures below are produced live from real Opta event data by the dashboard's own pipeline. "
  "Showcase fixture: Real Madrid 2–1 Barcelona (LaLiga 2025–26, Matchday 10). xG is from the project's "
  "positional model.", ParagraphStyle("n", parent=BODY, fontSize=8.6, textColor=GREY))

h2("4.1 Phase Profile — Transition-Heavy Identity")
figure("fig_phase_radar.png",
       "Four-phase tactical profile (A/B/C/D, normalised 0–100) for the showcase fixture, from the "
       "dashboard's phase-scoring model — a quantified view of attacking, defending and transition moments.",
       max_h=115 * mm)
h2("4.2 Organized Attack &amp; Efficiency vs Expectation")
figure("fig_shot_map.png",
       "Real Madrid shot map (marker size ∝ positional xG; goals highlighted): 24 shots, 2 goals, "
       "3.34 xG. High-xG attempts cluster centrally inside the box.",
       max_h=115 * mm)
h2("4.3 Defensive Strategy &amp; Pressing Trend")
figure("fig_ppda_trend.png",
       "PPDA across all 36 LaLiga 2025–26 matchdays (lower = more intense press); dashed line = season "
       "average (9.48). Variance reveals selective, game-state-dependent pressing.",
       max_h=92 * mm)

# ═══════════════════ 5 · STRENGTHS / WEAKNESSES / IDENTITY ═════════════════
S += section("5 · Strengths, Weaknesses &amp; Tactical Identity")
h2("Strengths")
bullets(["Efficient attacking transitions — quantified by a high offensive-transition phase score and "
         "rapid regain→shot conversion",
         "Strong set-piece execution (dead-ball threat tagged from restart events)",
         "High ball-recovery zones feeding immediate attacking threat"])
h2("Weaknesses / Watch-Points")
bullets(["Vulnerability immediately after possession loss (defensive-transition exposure)",
         "Reduced creativity against deep, compact defensive blocks",
         "Mild over-performance vs xG-for — a finishing-variance regression risk"])
h2("Tactical Identity")
p("Real Madrid operate as a <b>controlled attacking team with high transition efficiency and "
  "disciplined chance suppression</b>, rather than relying solely on possession dominance — winning "
  "through ruthless conversion of regains and a low expected-goals-against, more than through pressing "
  "volume.")

# ═══════════════════ 6 · TOOLS & SOFTWARE ═════════════════════════════════
S += section("6 · Tools &amp; Software")
table([["Category", "Technology", "Role"],
       ["Language", "Python 3.11", "Data processing &amp; analysis"],
       ["Data handling", "Pandas, NumPy", "Event-level data manipulation"],
       ["Visualisation", "Matplotlib, Plotly", "Static &amp; interactive visualisations"],
       ["Dashboard", "Streamlit (Dash/Plotly analytics core)", "Interactive multi-page dashboard"],
       ["Reporting", "ReportLab, python-docx", "Automated PDF/DOCX export"],
       ["Data source", "Opta Stats Perform event JSON", "Match-level event data"],
       ["Deployment", "Git · GitHub · Render (CI/CD)", "Reproducible, auto-deployed web app"]],
      [30 * mm, 56 * mm, 68 * mm])
p("<b>Update vs proposal:</b> the live interface is Streamlit (not Dash alone), and the source is Opta "
  "JSON rather than CSV — both stronger and already in production.",
  ParagraphStyle("u2", parent=BODY, fontSize=8.6, textColor=GREY))
S.append(PageBreak())

# ═══════════════════ 7 · IMPLEMENTATION STATUS ════════════════════════════
S += section("7 · Implementation Status of Dashboard Features")
p("Reconciled strictly to the existing codebase: <b>all nine proposal features are " +
  status_chip("Implemented") + " in the live dashboard</b>, each with one or more dedicated panels "
  "(named below). The final column lists genuine future enhancements only.")
table([["Feature / Analysis", "Status", "Delivered now — actual dashboard panels", "Future enhancement"],
       ["Pre-Match: goals, xG, possession", status_chip("Implemented"),
        "“Goals Per Match”, “Shots &amp; Pass Accuracy Trend”, season KPIs, xG vs xGA",
        "Rolling form, opponent-adjusted baselines"],
       ["Attacking Transition (fast breaks)", status_chip("Implemented"),
        "“Transition Metrics”, “Extended Transition Analysis”, A/B/C/D sub-phases, 5–15 s window",
        "Time-to-first-shot distribution"],
       ["Organized Attack", status_chip("Implemented"),
        "“Shot Map”, “Shot Zone Map”, “Pass Map”, “Build-Up Network”, “Zone 14”, “Progressive Passes”",
        "Edge-weighted passing networks"],
       ["Defensive Strategy", status_chip("Implemented"),
        "“PPDA Trend (Season)”, “Pressing Actions Map”, “Defensive Actions Map”",
        "Block-height viz, shots-conceded heatmap"],
       ["Set Pieces", status_chip("Implemented"),
        "“Set Piece Efficiency”; set-piece tendencies (corners, shots ≤20 s) in Opp Scout",
        "Dedicated set-piece shot maps"],
       ["Possession Recovery", status_chip("Implemented"),
        "“Ball Recoveries by Zone” (zonal heatmap)", "High/mid/low zonal comparison"],
       ["Post-Match Analysis", status_chip("Implemented"),
        "“Post-Match Tactical Summary”, goals vs xG, recoveries, defensive actions",
        "Auto expected-vs-actual narrative"],
       ["Final-Third Entries", status_chip("Implemented"),
        "“Final Third Entry Analysis (RM)”, “Field Tilt (Final Third %)” card &amp; trend",
        "xG-from-entries, shot-probability maps"],
       ["Match Info Summary", status_chip("Implemented"),
        "Date, score, opponent, result, venue", "Historical scores, contextual info"]],
      [34 * mm, 20 * mm, 56 * mm, 38 * mm])
p("<b>Beyond the proposal, the live dashboard also ships:</b> GK Distribution Map · Goalmouth Map · "
  "Penalty Analysis · Crossing Patterns · Chance Creation Heatmap · Team &amp; Player Radars · Player "
  "touch heatmaps · Opponent Threat Heatmap &amp; auto-scout report · a full Benchmarking suite "
  "(Goals F/A, Win %, xG F/A, pass accuracy, KPI comparison) · and one-click PDF/DOCX Report export.",
  ParagraphStyle("extra", parent=BODY, fontSize=8.7, textColor=GREY))

# ═══════════════════ 8 · FEASIBILITY & FUTURE SCOPE ═══════════════════════
S += section("8 · Feasibility, Academic Value &amp; Future Scope")
h2("8.1 Feasibility & Academic Value")
bullets(["<b>Feasible:</b> uses accessible event-level data; computationally light with Python, Pandas "
         "and Streamlit — already deployed publicly via Render.",
         "<b>Academic value:</b> bridges football-analytics theory and practice; every metric is "
         "formula-transparent and traceable to observed data, with no synthetic values."])
h2("8.2 Future Scope")
bullets(["<b>Expanded dataset:</b> more matches, seasons and competitions for robustness.",
         "<b>Player-level analysis:</b> individual tendencies and contribution to team tactics.",
         "<b>Opponent analysis:</b> automated multi-opponent comparison.",
         "<b>Predictive modelling:</b> forecast xG, transition success, or match outcomes.",
         "<b>Interactive expansion:</b> real-time filtering by player, phase and event type.",
         "<b>AI / ML tactical insights:</b> cluster attack/defence strategies, optimise training.",
         "<b>Video integration:</b> sync event data with footage to validate tactical observations.",
         "<b>Multi-competition analysis:</b> LaLiga, UCL and Copa del Rey in one platform."])
p("<b>Expected impact:</b> a professional-grade analytics platform supporting coaching decisions, "
  "player development, and opponent scouting across Real Madrid's competitive calendar.")
S.append(Spacer(1, 8))
S.append(HRFlowable(width="100%", thickness=1, color=GOLD))
S.append(Paragraph("Real Madrid CF Tactical &amp; Player Performance Analytics · Data: Opta Stats "
                   "Perform · Python · Pandas · NumPy · Plotly · Streamlit", CAP))

# ═══════════════════ APPENDIX · POSTER ════════════════════════════════════
if (ROOT / "poster.png").exists():
    S.append(PageBreak())
    S += section("Appendix · Project Summary Poster")
    figure(str(ROOT / "poster.png"),
           "Real Madrid CF Tactical &amp; Player Performance Analytics — one-page project summary.",
           max_h=215 * mm)


def header_footer(canvas, doc):
    canvas.saveState(); w, h = A4
    canvas.setFillColor(NAVY); canvas.rect(0, h - 16 * mm, w, 16 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD); canvas.rect(0, h - 16 * mm, w, 1.2 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE); canvas.setFont(FONT_B, 10)
    canvas.drawString(18 * mm, h - 10.5 * mm, "Real Madrid Tactical Dashboard — Final Master Project")
    canvas.setFillColor(GOLD); canvas.setFont(FONT, 7.5)
    canvas.drawRightString(w - 18 * mm, h - 10.5 * mm, "Opta Stats Perform")
    canvas.setFillColor(GREY); canvas.setFont(FONT, 7.5)
    canvas.drawString(18 * mm, 10 * mm, "Sudhir Dahiya · Master's in Sports Analytics 2025–2026")
    canvas.drawRightString(w - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(LGREY); canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 13 * mm, w - 18 * mm, 13 * mm); canvas.restoreState()


doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=22 * mm, bottomMargin=16 * mm,
                      title="Real Madrid Tactical Dashboard — Final Master Project",
                      author="Sudhir Dahiya")
doc.addPageTemplates([PageTemplate(id="body",
                      frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="m")],
                      onPage=header_footer)])
doc.build(S)
print(f"Saved → {OUT}  ({OUT.stat().st_size // 1024} KB, figures: {_fig[0]})")
