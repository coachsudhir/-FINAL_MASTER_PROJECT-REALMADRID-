"""
generate_dashboard_doc_pdf.py
Renders DASHBOARD_DOCUMENTATION.md into a branded, submission-ready PDF with the
real dashboard figures embedded at their [[FIG:name|caption]] markers.

Figures are the live dashboard's own Plotly charts, exported from real Opta data
by the capture step (dashboard_figures/*.png). No synthetic data is used.

Output: FMP_RM_Dashboard.pdf
"""
import re
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
    "DejaVu-Oblique": ("DejaVu Sans", "normal"),
    "DejaVu-Mono": ("DejaVu Sans Mono", "normal"),
}.items():
    pdfmetrics.registerFont(TTFont(name, findfont(FontProperties(family=fam, weight=wt))))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                              italic="DejaVu", boldItalic="DejaVu-Bold")
FONT, FONT_B, FONT_M = "DejaVu", "DejaVu-Bold", "DejaVu-Mono"

NAVY = colors.HexColor("#0b1730"); GOLD = colors.HexColor("#c8a951")
GOLD_D = colors.HexColor("#a8882e"); CREAM = colors.HexColor("#f8f7f3")
GREY = colors.HexColor("#475569"); LGREY = colors.HexColor("#e2ddd0")
WHITE = colors.white; DARK = colors.HexColor("#1f2a3d")

ROOT = Path(__file__).parent
MD = ROOT / "DASHBOARD_DOCUMENTATION.md"
FIGDIR = ROOT / "dashboard_figures"
OUT = ROOT / "FMP_RM_Dashboard.pdf"
CW = A4[0] - 36 * mm

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", fontName=FONT_B, fontSize=15, textColor=NAVY,
                    spaceBefore=14, spaceAfter=4, leading=18)
H2 = ParagraphStyle("H2", fontName=FONT_B, fontSize=11.5, textColor=GOLD_D,
                    spaceBefore=9, spaceAfter=3, leading=14)
H3 = ParagraphStyle("H3", fontName=FONT_B, fontSize=10, textColor=NAVY,
                    spaceBefore=7, spaceAfter=2, leading=13)
BODY = ParagraphStyle("BODY", fontName=FONT, fontSize=9.4, textColor=DARK,
                      leading=14, spaceAfter=6, alignment=TA_LEFT)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=12, spaceAfter=3)
MONO = ParagraphStyle("MONO", fontName=FONT_M, fontSize=8.3, textColor=NAVY,
                      leading=12, backColor=colors.HexColor("#f1efe7"),
                      borderPadding=5, spaceAfter=6, leftIndent=4)
NOTE = ParagraphStyle("NOTE", parent=BODY, fontSize=9, textColor=GREY,
                      leftIndent=10, borderColor=GOLD, borderWidth=0,
                      backColor=colors.HexColor("#faf8f1"), borderPadding=6, spaceAfter=8)
CELL = ParagraphStyle("CELL", parent=BODY, fontSize=8.2, leading=11, spaceAfter=0)
CELLH = ParagraphStyle("CELLH", parent=CELL, fontName=FONT_B, textColor=WHITE, fontSize=8.4)
CAP = ParagraphStyle("CAP", parent=BODY, fontSize=8, textColor=GREY, leading=11,
                     alignment=TA_CENTER, spaceAfter=10)

FIG_FILES = {p.stem: p for p in FIGDIR.glob("*.png")} if FIGDIR.exists() else {}


def esc(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    t = t.replace("`", "")
    return t


def figure(name, caption, story):
    fp = FIG_FILES.get(name)
    if fp is None or not fp.exists():
        return
    iw, ih = PILImage.open(fp).size
    w = CW; h = w * ih / iw
    maxh = 110 * mm
    if h > maxh:
        h = maxh; w = h * iw / ih
    img = Image(str(fp), width=w, height=h); img.hAlign = "CENTER"
    story.append(KeepTogether([
        Spacer(1, 3),
        HRFlowable(width="40%", thickness=0.6, color=GOLD),
        Spacer(1, 3), img,
        Paragraph(caption, CAP),
        HRFlowable(width="40%", thickness=0.6, color=GOLD), Spacer(1, 4),
    ]))


def flush_table(rows, story):
    if not rows:
        return
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [c for c in cells if not all(re.fullmatch(r"-{2,}\s*", x or "-") for x in c)]
    if not cells:
        return
    ncol = max(len(c) for c in cells)
    cells = [c + [""] * (ncol - len(c)) for c in cells]
    data = [[Paragraph(esc(c), CELLH if i == 0 else CELL) for c in row]
            for i, row in enumerate(cells)]
    colw = [CW / ncol] * ncol
    t = Table(data, colWidths=colw, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), NAVY),
          ("LINEBELOW", (0, 0), (-1, 0), 1.0, GOLD),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          ("LINEBELOW", (0, 1), (-1, -2), 0.4, LGREY),
          ("BOX", (0, 0), (-1, -1), 0.6, LGREY)]
    for i in range(2, len(data), 2):
        st.append(("BACKGROUND", (0, i), (-1, i), CREAM))
    t.setStyle(TableStyle(st))
    story.append(t); story.append(Spacer(1, 6))


# ── Parse markdown ───────────────────────────────────────────────────────────
lines = MD.read_text(encoding="utf-8").splitlines()
story = [NextPageTemplate("body")]

# Cover
story += [Spacer(1, 30 * mm),
          Paragraph("Real Madrid CF", ParagraphStyle("cv0", fontName=FONT_B, fontSize=30,
                    leading=36, alignment=TA_CENTER, textColor=NAVY, spaceAfter=6)),
          Paragraph("Tactical Dashboard", ParagraphStyle("cv1", fontName=FONT_B, fontSize=20,
                    leading=26, alignment=TA_CENTER, textColor=GOLD_D, spaceAfter=16)),
          HRFlowable(width="60%", thickness=2, color=GOLD, spaceAfter=16),
          Paragraph("Official Platform Documentation", ParagraphStyle("cv2", fontName=FONT_B,
                    fontSize=16, leading=20, alignment=TA_CENTER, textColor=NAVY, spaceAfter=8)),
          Paragraph("A complete reference to every module, panel, chart, heatmap, table, KPI "
                    "and metric — illustrated with the dashboard's own charts, rendered live "
                    "from real Opta Stats Perform event data.",
                    ParagraphStyle("cv3", parent=BODY, alignment=TA_CENTER, fontSize=10.5,
                                   textColor=GREY, spaceAfter=26)),
          Paragraph("Sudhir Dahiya · Master's in Sports Analytics (2025–2026)<br/>"
                    "Escuela Universitaria Real Madrid — Universidad Europea<br/>"
                    f"Data: Opta Stats Perform · Generated {date.today():%d %B %Y}",
                    ParagraphStyle("cv4", parent=BODY, alignment=TA_CENTER, fontSize=9.5,
                                   textColor=GREY)),
          PageBreak()]

i = 0
tbl_buf = []
code_buf = None
while i < len(lines):
    raw = lines[i]
    line = raw.rstrip()

    # code fences
    if line.strip().startswith("```"):
        if code_buf is None:
            code_buf = []
        else:
            story.append(Paragraph("<br/>".join(esc(x) for x in code_buf), MONO))
            code_buf = None
        i += 1; continue
    if code_buf is not None:
        code_buf.append(raw); i += 1; continue

    # table rows
    if line.strip().startswith("|") and line.strip().endswith("|"):
        tbl_buf.append(line); i += 1; continue
    elif tbl_buf:
        flush_table(tbl_buf, story); tbl_buf = []

    # figure marker
    m = re.match(r"\s*\[\[FIG:([a-z0-9_]+)\|(.+?)\]\]\s*$", line)
    if m:
        figure(m.group(1), "Figure — " + esc(m.group(2)), story); i += 1; continue

    if not line.strip():
        i += 1; continue
    if line.startswith("# "):
        i += 1; continue  # main title handled by cover
    if line.startswith("## "):
        story.append(Paragraph(esc(line[3:]), H1))
        story.append(HRFlowable(width="100%", thickness=1.2, color=GOLD,
                                spaceBefore=1, spaceAfter=6)); i += 1; continue
    if line.startswith("### "):
        story.append(Paragraph(esc(line[4:]), H2)); i += 1; continue
    if line.startswith("> "):
        story.append(Paragraph(esc(line[2:]), NOTE)); i += 1; continue
    if line.strip() in ("---", "***"):
        i += 1; continue
    if re.match(r"\s*[-•]\s+", line):
        story.append(Paragraph("•&nbsp;&nbsp;" + esc(re.sub(r"^\s*[-•]\s+", "", line)), BULLET))
        i += 1; continue
    story.append(Paragraph(esc(line), BODY)); i += 1

if tbl_buf:
    flush_table(tbl_buf, story)


# ── Page frame ───────────────────────────────────────────────────────────────
def header_footer(canvas, doc):
    canvas.saveState(); w, h = A4
    canvas.setFillColor(NAVY); canvas.rect(0, h - 15 * mm, w, 15 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD); canvas.rect(0, h - 15 * mm, w, 1.1 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE); canvas.setFont(FONT_B, 9.5)
    canvas.drawString(18 * mm, h - 10 * mm, "Real Madrid Tactical Dashboard — Official Documentation")
    canvas.setFillColor(GOLD); canvas.setFont(FONT, 7.2)
    canvas.drawRightString(w - 18 * mm, h - 10 * mm, "Opta Stats Perform")
    canvas.setFillColor(GREY); canvas.setFont(FONT, 7.2)
    canvas.drawString(18 * mm, 9 * mm, "Sudhir Dahiya · Master's in Sports Analytics 2025–2026")
    canvas.drawRightString(w - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(LGREY); canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 12 * mm, w - 18 * mm, 12 * mm); canvas.restoreState()


doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=21 * mm, bottomMargin=15 * mm,
                      title="Real Madrid Tactical Dashboard — Official Documentation",
                      author="Sudhir Dahiya")
doc.addPageTemplates([PageTemplate(id="body",
                      frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="m")],
                      onPage=header_footer)])
doc.build(story)
print(f"Saved → {OUT}  ({OUT.stat().st_size // 1024} KB)")
