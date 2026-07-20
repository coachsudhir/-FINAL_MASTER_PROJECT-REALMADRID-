"""
generate_metrics_report.py
Builds a professional PDF documenting every KPI, metric, formula and key
consideration used by the Real Madrid Tactical Dashboard.

All formulas below are transcribed verbatim from the live dashboard code:
  dashboard/app/utils/data_loader.py   (match + season KPIs, xG, PPDA, field tilt)
  dashboard/app/utils/phase_scoring.py (A/B/C/D tactical phase model)

Output: Dashboard_KPI_Metrics_Report.pdf
"""
from pathlib import Path
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, NextPageTemplate, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Register Unicode-capable fonts ───────────────────────────────────────────
# ReportLab's built-in Helvetica/Courier are Latin-1 only and silently drop
# maths glyphs (√ Σ ≥ ≈ → − ∈). DejaVu (shipped with matplotlib) covers them all
# and renders identically on macOS/Linux, so the report is reproducible anywhere.
from matplotlib.font_manager import FontProperties, findfont

_FONTS = {
    "DejaVu":      ("DejaVu Sans", "normal"),
    "DejaVu-Bold": ("DejaVu Sans", "bold"),
    "DejaVu-Mono": ("DejaVu Sans Mono", "normal"),
}
for name, (family, weight) in _FONTS.items():
    pdfmetrics.registerFont(TTFont(name, findfont(FontProperties(family=family, weight=weight))))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")

FONT, FONT_B, FONT_M = "DejaVu", "DejaVu-Bold", "DejaVu-Mono"

# ── Brand palette ────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0b1730")
NAVY2  = colors.HexColor("#162542")
GOLD   = colors.HexColor("#c8a951")
GOLD_D = colors.HexColor("#a8882e")
CREAM  = colors.HexColor("#f8f7f3")
GREY   = colors.HexColor("#475569")
LGREY  = colors.HexColor("#e2ddd0")
BLUE   = colors.HexColor("#1d4ed8")
GREEN  = colors.HexColor("#059669")
RED    = colors.HexColor("#dc2626")
WHITE  = colors.white

OUT = Path(__file__).parent / "Dashboard_KPI_Metrics_Report.pdf"

# ── Styles ───────────────────────────────────────────────────────────────────
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName=FONT_B,
                    fontSize=15, textColor=NAVY, spaceBefore=14, spaceAfter=4, leading=18)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName=FONT_B,
                    fontSize=11.5, textColor=GOLD_D, spaceBefore=10, spaceAfter=3, leading=14)
BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontName=FONT,
                      fontSize=9.3, textColor=colors.HexColor("#1f2a3d"),
                      leading=13.5, spaceAfter=5, alignment=TA_LEFT)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=12, bulletIndent=2,
                        spaceAfter=3)
MONO = ParagraphStyle("MONO", parent=BODY, fontName=FONT_M, fontSize=8.6,
                      textColor=NAVY, leading=12, backColor=colors.HexColor("#f1efe7"),
                      borderPadding=4, spaceAfter=4, leftIndent=4)
CELL = ParagraphStyle("CELL", parent=BODY, fontSize=8.4, leading=11, spaceAfter=0)
CELLH = ParagraphStyle("CELLH", parent=CELL, fontName=FONT_B,
                       textColor=WHITE, fontSize=8.4)
CAP = ParagraphStyle("CAP", parent=BODY, fontSize=8, textColor=GREY, leading=11)


def section(title):
    return [Spacer(1, 2), Paragraph(title, H1),
            HRFlowable(width="100%", thickness=1.4, color=GOLD,
                       spaceBefore=1, spaceAfter=7)]


def metric_table(rows, col_widths):
    """rows[0] = header list; cells are strings turned into Paragraphs."""
    data = [[Paragraph(c, CELLH) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(str(c), CELL) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("LINEBELOW", (0, 0), (-1, 0), 1.1, GOLD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LGREY),
        ("BOX", (0, 0), (-1, -1), 0.6, LGREY),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), CREAM))
    t.setStyle(TableStyle(style))
    return t


story = []

# ═══════════════════════════════════════════════════════════════════════════
# COVER
# ═══════════════════════════════════════════════════════════════════════════
story.append(NextPageTemplate("body"))
story.append(Spacer(1, 40 * mm))
story.append(Paragraph("Real Madrid CF", ParagraphStyle(
    "cov", parent=H1, fontSize=30, alignment=TA_CENTER, textColor=NAVY,
    spaceAfter=2)))
story.append(Paragraph("Tactical &amp; Player Performance Dashboard", ParagraphStyle(
    "cov2", parent=BODY, fontSize=14, alignment=TA_CENTER, textColor=GOLD_D,
    spaceAfter=18)))
story.append(HRFlowable(width="55%", thickness=2, color=GOLD, spaceAfter=18))
story.append(Paragraph("KPI, Metrics &amp; Formula Reference", ParagraphStyle(
    "cov3", parent=H1, fontSize=18, alignment=TA_CENTER, textColor=NAVY,
    spaceAfter=6)))
story.append(Paragraph(
    "Definitions, calculation methods and key analytical considerations "
    "for every metric computed by the dashboard — sourced strictly from "
    "Opta Stats Perform event data.",
    ParagraphStyle("cov4", parent=BODY, alignment=TA_CENTER, fontSize=10,
                   textColor=GREY, spaceAfter=40)))
story.append(Paragraph(
    f"Sudhir Dahiya &nbsp;•&nbsp; Master's in Sports Analytics (2025–2026)<br/>"
    f"Escuela Universitaria Real Madrid — Universidad Europea<br/>"
    f"Generated {date.today():%d %B %Y}",
    ParagraphStyle("cov5", parent=BODY, alignment=TA_CENTER, fontSize=9,
                   textColor=GREY)))
story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# 1 · DATA FOUNDATION
# ═══════════════════════════════════════════════════════════════════════════
story += section("1 · Data Foundation &amp; Pipeline")
story.append(Paragraph(
    "Every figure in the dashboard is derived from raw <b>Opta Stats Perform</b> "
    "event-level JSON match files. No synthetic, simulated or manually entered "
    "values are used. The pipeline parses each match's event stream into a "
    "normalised table, then aggregates upward to match-, season- and player-level KPIs.",
    BODY))
story.append(Paragraph(
    "<b>Dataset scope:</b> 108 clean match files · 3 competitions (LaLiga · UEFA "
    "Champions League · Copa del Rey) · 2 seasons (2024-25, 2025-26) · Real Madrid "
    "matches only. Files are cached with an LRU cache for performance.", BODY))

story.append(Paragraph("Opta event type IDs used", H2))
story.append(metric_table([
    ["typeId", "Event", "Used for"],
    ["1, 2", "Pass / Offside Pass", "Possession, pass accuracy, pass networks"],
    ["3", "Take On / Dribble", "Player dribble counts"],
    ["4", "Foul", "Fouls committed"],
    ["6", "Corner Awarded", "Corner counts"],
    ["7", "Tackle", "Defensive actions, PPDA"],
    ["8", "Interception", "Defensive actions, PPDA"],
    ["13", "Shot On Target (saved)", "Shots, shots on target, xG"],
    ["15", "Shot Blocked", "Shots, xG"],
    ["16", "Goal", "Goals, shots on target, xG"],
    ["19", "Player On (sub)", "Lineup status (Starter vs Sub-on)"],
    ["49", "Ball Recovery", "Defensive actions, PPDA"],
    ["65 / 68", "Yellow / Red Card", "Discipline counts"],
], [55, 150, 270]))
story.append(Spacer(1, 4))
story.append(Paragraph(
    "Qualifier IDs: 140/141 = pass end coordinates · 56 = pitch zone · "
    "279 = pass direction · 396 = xGOT proxy (0–100) · 5/72 = set-piece restarts. "
    "Bookkeeping events (27, 28, 30, 32, 34 — period starts, formations) are filtered out.",
    CAP))

# ═══════════════════════════════════════════════════════════════════════════
# 2 · MATCH-LEVEL KPIs
# ═══════════════════════════════════════════════════════════════════════════
story += section("2 · Match-Level KPIs")
story.append(Paragraph(
    "Computed per match by <font face='DejaVu-Mono' size='8'>calc_match_kpis()</font> "
    "over the normalised event table (RM = Real Madrid, OPP = opponent).", BODY))
story.append(metric_table([
    ["Metric", "Formula / definition"],
    ["Goals scored / conceded", "Final score from matchInfo (RM goals, opponent goals)."],
    ["Result (W/D/L)", "Sign of (RM score − opponent score)."],
    ["Possession %", "RM passes ÷ (RM passes + OPP passes) × 100. Pass-volume share proxy."],
    ["Pass accuracy %", "mean(outcome) × 100 over RM passes, where outcome = 1 if successful."],
    ["Shots (total)", "Count of RM shot events: typeId ∈ {13,15,16} or shot qualifier present."],
    ["Shots on target", "Count of RM events with typeId ∈ {13,16} (saved attempt + goal)."],
    ["xG for / against", "Σ positional-model xG over RM / OPP shot events (see §4)."],
    ["Tackles / Interceptions / Recoveries", "Count of RM events typeId 7 / 8 / 49."],
    ["Corners / Fouls", "Count of RM events typeId 6 / 4."],
    ["Yellow / Red cards", "Count of RM events typeId 65 / 68."],
    ["PPDA (match KPI)", "OPP passes with x ≥ 40 ÷ RM defensive actions (typeId 7,8,49)."],
], [120, 355]))

# ═══════════════════════════════════════════════════════════════════════════
# 3 · SEASON-LEVEL KPIs
# ═══════════════════════════════════════════════════════════════════════════
story += section("3 · Season-Level Aggregated KPIs")
story.append(Paragraph(
    "Computed by <font face='DejaVu-Mono' size='8'>calc_season_kpis()</font>, which "
    "scans every RM match in a competition-season and aggregates the per-match KPIs above.", BODY))
story.append(metric_table([
    ["Metric", "Formula / definition"],
    ["Played, Wins, Draws, Losses", "Counts of matches by result."],
    ["Win %", "wins ÷ played × 100."],
    ["Goals scored / conceded", "Σ of per-match goals for / against."],
    ["Goal difference", "Goals scored − goals conceded."],
    ["Goals per game", "Goals scored ÷ played."],
    ["Conceded per game", "Goals conceded ÷ played."],
    ["Avg possession %", "Mean of per-match possession% (simple average across matches)."],
    ["Avg pass accuracy %", "Mean of per-match pass accuracy%."],
    ["xG for / against", "Σ of per-match xG for / against."],
    ["xG difference", "Season xG for − season xG against."],
], [120, 355]))

story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# 4 · xG MODEL
# ═══════════════════════════════════════════════════════════════════════════
story += section("4 · Expected Goals (xG) — Positional Model")
story.append(Paragraph(
    "The dashboard uses a transparent, <b>calibrated positional xG model</b> based on "
    "shot location, not the provider's proprietary xG. It is applied to every shot event "
    "so xG is always present (the Opta post-shot qualifier 395 is deliberately excluded — "
    "it appears on only ~11% of shots, goals only, with unreliable bimodal values).", BODY))
story.append(Paragraph("Penalties", H2))
story.append(Paragraph(
    "Detected by Opta's standardised penalty-spot coordinate (x = 88.5, y = 50.0, ±0.2) "
    "and assigned a fixed <b>xG = 0.76</b> (empirical penalty conversion rate).", BODY))
story.append(Paragraph("Open-play logistic model", H2))
story.append(Paragraph(
    "Pitch is Opta 0–100 units (x ≈ 105 m, y ≈ 68 m); attacking goal at x = 100, y = 50; "
    "goal half-width 3.66 m.", BODY))
story.append(Paragraph(
    "dx_m = (100 − x) × 1.05 &nbsp;&nbsp; dy_m = (y − 50) × 0.68<br/>"
    "dist_m = √(dx_m² + dy_m²)<br/>"
    "angle_rad = | atan2(dy_m − 3.66, dx_m) − atan2(dy_m + 3.66, dx_m) |<br/>"
    "logit(xG) = −3.785 − 0.0337 · dist_m + 3.64 · angle_rad<br/>"
    "xG = 1 / (1 + e^−logit), &nbsp; clipped to [0.01, 0.99]", MONO))
story.append(Paragraph(
    "<b>Calibration anchors</b> (central, open play): 6 m → ≈0.50 · 11 m → ≈0.14 · "
    "edge of box 16.5 m → ≈0.06 · long shot 25 m → ≈0.027.", CAP))

# ═══════════════════════════════════════════════════════════════════════════
# 5 · TACTICAL METRICS
# ═══════════════════════════════════════════════════════════════════════════
story += section("5 · Tactical Metrics")
story.append(Paragraph("PPDA — Passes Allowed Per Defensive Action", H2))
story.append(Paragraph(
    "Pressing-intensity metric (lower = more intense press). The tactical page uses "
    "<font face='DejaVu-Mono' size='8'>calc_ppda()</font>, restricting <i>both</i> terms to "
    "the pressing zone (x ≥ 40):", BODY))
story.append(Paragraph(
    "PPDA = ( OPP passes with x ≥ 40 ) ÷ ( RM defensive actions [tackle, interception, "
    "recovery] with x ≥ 40 )", MONO))
story.append(Paragraph("Field Tilt", H2))
story.append(Paragraph(
    "Share of final-third activity belonging to Real Madrid — a territorial dominance proxy.", BODY))
story.append(Paragraph(
    "Field tilt % = RM touches with x ≥ 67 ÷ all touches with x ≥ 67 × 100", MONO))

# ═══════════════════════════════════════════════════════════════════════════
# 6 · PHASE MODEL
# ═══════════════════════════════════════════════════════════════════════════
story += section("6 · Tactical Phase Model (A / B / C / D)")
story.append(Paragraph(
    "Four play-phase scores, each normalised to 0–100, computed by "
    "<font face='DejaVu-Mono' size='8'>phase_scores_from_events()</font>. They blend "
    "weighted components so the radar/benchmark views compare phases on one scale.", BODY))
story.append(metric_table([
    ["Phase", "Weighted formula (clipped 0–100)"],
    ["A · Offensive Moment",
     "pass_acc × 0.45 + (Σxg × 10) × 0.35 + (shots × 2.5) × 0.20"],
    ["B · Defensive Transition",
     "(100 / (1 + PPDA)) × 0.55 + ((recoveries + interceptions) × 1.8) × 0.45"],
    ["C · Defensive Moment",
     "(100 / (1 + PPDA)) × 0.40 + max(0, 40 − opp_shots × 2) × 0.60"],
    ["D · Offensive Transition",
     "trans_rate × 0.65 + (Σxg × 7) × 0.35"],
], [120, 355]))
story.append(Spacer(1, 3))
story.append(Paragraph(
    "<b>trans_rate</b> = % of ball regains (recovery / interception / tackle) that lead to "
    "a Real Madrid shot within 15 seconds. A parallel "
    "<font face='DejaVu-Mono' size='8'>phase_scores_from_team_row()</font> variant recomputes the "
    "same four phases from per-game season aggregates (goals_pg, xg_pg, shots_pg, def_actions_pg) "
    "for cross-competition benchmarking.", CAP))

# ═══════════════════════════════════════════════════════════════════════════
# 7 · PLAYER METRICS
# ═══════════════════════════════════════════════════════════════════════════
story += section("7 · Player-Level Metrics")
story.append(Paragraph(
    "Per-player aggregates from <font face='DejaVu-Mono' size='8'>get_player_stats()</font>, "
    "grouped by player across the selected scope; feed the squad table and multi-radar.", BODY))
story.append(metric_table([
    ["Metric", "Definition"],
    ["Minutes played", "Max event minute for the player (proxy for time on pitch)."],
    ["Passes / Pass accuracy", "Pass count; mean(outcome) × 100 over the player's passes."],
    ["Shots / Shots on target / Goals", "Counts of the player's shot, SoT and goal events."],
    ["Key passes / Assists", "Opta keyPass flag count; assist flag count."],
    ["Tackles / Interceptions / Recoveries / Dribbles", "Counts of typeId 7 / 8 / 49 / 3."],
    ["xG", "Σ positional-model xG over the player's shots."],
    ["Fouls", "Count of the player's foul events (typeId 4)."],
    ["Lineup status", "typeId 19 ⇒ 'Sub On'; otherwise 'Starting 11'."],
], [165, 310]))

# ═══════════════════════════════════════════════════════════════════════════
# 8 · KEY CONSIDERATIONS
# ═══════════════════════════════════════════════════════════════════════════
story += section("8 · Key Points &amp; Considerations")
points = [
    "<b>100% real data.</b> Every metric is derived from Opta event files; no synthetic or "
    "estimated values are introduced anywhere in the pipeline.",
    "<b>Possession is a pass-share proxy.</b> The event feed has no ball-possession duration, "
    "so possession% uses each side's share of total passes — directionally accurate, not a stopwatch figure.",
    "<b>xG is a transparent positional model</b> (distance + shot angle logistic), not the "
    "provider's proprietary xG. Penalties are flagged by standardised coordinate and fixed at 0.76. "
    "Opta qualifier 395 is excluded because it only covers goals (~11% of shots) with bimodal values.",
    "<b>PPDA pressing zone = x ≥ 40.</b> Lower PPDA means a more aggressive press; the tactical "
    "page restricts both passes and defensive actions to this zone for consistency.",
    "<b>Phase scores are weighted composites</b> normalised to 0–100 for comparability — they rank "
    "relative phase strength, they are not physical units.",
    "<b>Lineup status is inferred</b> from substitution-on events (typeId 19); all other players "
    "with events are treated as starters.",
    "<b>Season averages are match-simple means</b> (e.g. avg possession), not minutes- or "
    "events-weighted, keeping each match an equal observation.",
    "<b>Data hygiene.</b> Only Real-Madrid matches are loaded, bookkeeping events are stripped, "
    "files are LRU-cached, and the canonical clean bundle (dashboard/data, 0 corrupt files) is the single source of truth.",
    "<b>Optional advanced layer.</b> An experimental tactical-intelligence overlay (sub-phase tagging, "
    "advanced/cross-phase KPIs, sequence enrichment) exists behind feature flags that default to OFF, "
    "so it never affects the standard metrics above unless explicitly enabled via environment variables.",
]
for p in points:
    story.append(Paragraph("•&nbsp;&nbsp;" + p, BULLET))

story.append(Spacer(1, 10))
story.append(HRFlowable(width="100%", thickness=1, color=GOLD))
story.append(Paragraph(
    "Real Madrid CF Tactical &amp; Player Performance Analytics · "
    "Data: Opta Stats Perform · Built with Python, Streamlit &amp; Plotly",
    ParagraphStyle("end", parent=CAP, alignment=TA_CENTER, spaceBefore=4)))


# ═══════════════════════════════════════════════════════════════════════════
# PAGE FRAME (header band + footer with page numbers)
# ═══════════════════════════════════════════════════════════════════════════
def header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    # top band
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 16 * mm, w, 16 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, h - 16 * mm, w, 1.2 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont(FONT_B, 10)
    canvas.drawString(18 * mm, h - 10.5 * mm, "Real Madrid CF — Dashboard KPI & Metrics Reference")
    canvas.setFillColor(GOLD)
    canvas.setFont(FONT, 7.5)
    canvas.drawRightString(w - 18 * mm, h - 10.5 * mm, "Opta Stats Perform")
    # footer
    canvas.setFillColor(GREY)
    canvas.setFont(FONT, 7.5)
    canvas.drawString(18 * mm, 10 * mm, "Sudhir Dahiya · Master's in Sports Analytics 2025–2026")
    canvas.drawRightString(w - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(LGREY)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 13 * mm, w - 18 * mm, 13 * mm)
    canvas.restoreState()


doc = BaseDocTemplate(
    str(OUT), pagesize=A4,
    leftMargin=18 * mm, rightMargin=18 * mm,
    topMargin=22 * mm, bottomMargin=16 * mm,
    title="Real Madrid Dashboard — KPI & Metrics Reference",
    author="Sudhir Dahiya",
)
frame = Frame(doc.leftMargin, doc.bottomMargin,
              doc.width, doc.height, id="main")
doc.addPageTemplates([
    PageTemplate(id="body", frames=[frame], onPage=header_footer),
])
doc.build(story)
print(f"Saved → {OUT}  ({OUT.stat().st_size // 1024} KB)")
