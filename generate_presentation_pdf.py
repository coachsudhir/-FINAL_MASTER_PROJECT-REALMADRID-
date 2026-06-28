"""
generate_presentation_pdf.py — updated 28 Jun 2026
Builds the slide-deck: FMP_Real Madrid Tactical Dashboard — Presentation(28 Jun).pdf

Changes in this version
────────────────────────
• UE Real Madrid / Universidad Europea branding on cover + every page header
• RM crest image (not emoji) on cover slide
• Stack corrected: Python · Plotly/Dash · Gunicorn · Render
• New figures generated on the fly from live Opta data:
    pass_network, shot_zone, zone14, set_pieces
• New slides: Multi-Match Mode · Pass Network · Shot Zone Map ·
              Zone 14 Passing · Set Piece Efficiency · Report Generator
• Updated: Architecture · Implementation Status
"""

from __future__ import annotations
from pathlib import Path
from datetime import date
from collections import defaultdict
import os, sys, math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Arc, Ellipse
import numpy as np

from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from matplotlib.font_manager import FontProperties, findfont

# ── Fonts ─────────────────────────────────────────────────────────────────────
for _nm, (_fam, _wt) in {
    "DejaVu":      ("DejaVu Sans",      "normal"),
    "DejaVu-Bold": ("DejaVu Sans",      "bold"),
    "DejaVu-Mono": ("DejaVu Sans Mono", "normal"),
}.items():
    pdfmetrics.registerFont(
        TTFont(_nm, findfont(FontProperties(family=_fam, weight=_wt)))
    )
FONT, FONT_B, FONT_M = "DejaVu", "DejaVu-Bold", "DejaVu-Mono"

# ── Brand palette ──────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0b1730")
NAVY2  = colors.HexColor("#13213f")
GOLD   = colors.HexColor("#c8a951")
GOLD_D = colors.HexColor("#a8882e")
CREAM  = colors.HexColor("#f8f7f3")
GREY   = colors.HexColor("#475569")
LGREY  = colors.HexColor("#cbd5e1")
DARK   = colors.HexColor("#1f2a3d")
WHITE  = colors.white
# Hex strings for matplotlib
_NAVY  = "#0b1730"; _GOLD  = "#c8a951"; _GOLD_D = "#a8882e"
_BLUE  = "#1d4ed8"; _RED   = "#dc2626"; _GREEN  = "#059669"
_GREY  = "#475569"; _LGREY = "#cbd5e1"; _CREAM  = "#f8f7f3"

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).parent
FIG    = ROOT / "dashboard_figures"
ASSETS = ROOT / "dashboard" / "app" / "assets"
CREST  = ASSETS / "rm_crest.jpg"
UE_LOGO = ASSETS / "ue_real_madrid_logo.png"
OUT    = ROOT / "FMP_Real Madrid Tactical Dashboard — Presentation(28 Jun).pdf"
FIG.mkdir(exist_ok=True)

# ── Dashboard data pipeline ───────────────────────────────────────────────────
os.environ.setdefault("DATA_ROOT", str(ROOT / "dashboard" / "data"))
sys.path.insert(0, str(ROOT / "dashboard" / "app"))

from utils.data_loader import (          # noqa: E402
    get_season_match_list, load_match_json, extract_match_meta,
    parse_events, get_shot_data, calc_ppda,
)
from utils.phase_scoring import phase_scores_from_events  # noqa: E402

_matches    = get_season_match_list("LaLiga", "2025-2026")
_SHOWCASE   = next(
    (m for m in _matches if "Barcelona" in m["opponent"] and m["is_rm_home"]),
    _matches[0]
)
_raw_data   = load_match_json(_SHOWCASE["filepath"])
_meta       = extract_match_meta(_raw_data)
_events     = parse_events(_raw_data)
_RM_ID      = _meta["rm_id"]
_OPP_ID     = _meta["opp_id"]
_RM_NAME    = _meta["home_team"] if _meta["is_rm_home"] else _meta["away_team"]
_OPP_NAME   = _meta["opponent"]
_SCORE      = _meta["score_str"]


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE GENERATORS  (matplotlib → dashboard_figures/*.png)
# ═══════════════════════════════════════════════════════════════════════════════

def _pitch(ax, half=False):
    ax.set_facecolor("#d9f0dc")
    lc, lw = "#2e7d32", 1.4
    if half:
        ax.add_patch(Rectangle((50, 0), 50, 100, fill=False, ec=lc, lw=lw))
        ax.add_patch(Rectangle((84.3, 21.1), 15.7, 57.8, fill=False, ec=lc, lw=lw))
        ax.add_patch(Rectangle((94.2, 36.8), 5.8, 26.4, fill=False, ec=lc, lw=lw))
        ax.scatter([88.5], [50], s=10, color=lc)
        ax.add_patch(Arc((88.5, 50), 17.4, 26, angle=0, theta1=128, theta2=232, ec=lc, lw=lw))
        ax.add_patch(Arc((50, 50), 17.4, 26, angle=0, theta1=-90, theta2=90, ec=lc, lw=lw))
        ax.set_xlim(48, 103); ax.set_ylim(-2, 102)
    else:
        ax.add_patch(Rectangle((0, 0), 100, 100, fill=False, ec=lc, lw=lw))
        ax.plot([50, 50], [0, 100], color=lc, lw=1.1)
        ax.add_patch(Ellipse((50, 50), 17.4, 26, fill=False, ec=lc, lw=1.1))
        ax.scatter([50], [50], s=8, color=lc)
        for side in [(84.3, 21.1, 15.7, 57.8), (0, 21.1, 15.7, 57.8)]:
            ax.add_patch(Rectangle(side[:2], side[2], side[3], fill=False, ec=lc, lw=lw))
        for side in [(94.2, 36.8, 5.8, 26.4), (0, 36.8, 5.8, 26.4)]:
            ax.add_patch(Rectangle(side[:2], side[2], side[3], fill=False, ec=lc, lw=lw))
        ax.scatter([88.5, 11.5], [50, 50], s=8, color=lc)
        ax.add_patch(Arc((88.5, 50), 17.4, 26, angle=0, theta1=128, theta2=232, ec=lc, lw=1.1))
        ax.add_patch(Arc((11.5, 50), 17.4, 26, angle=0, theta1=-52, theta2=52, ec=lc, lw=1.1))
        ax.set_xlim(-2, 102); ax.set_ylim(-2, 102)
    ax.set_aspect("equal"); ax.axis("off")


def _gen_pass_network():
    rm_ev = _events[_events["contestant_id"] == _RM_ID].sort_values(
        ["period", "minute", "second"]
    ).reset_index(drop=True)
    h1    = rm_ev[rm_ev["period"] == 1]
    top_p = h1["player_name"].value_counts().head(11).index.tolist()
    pos   = rm_ev.groupby("player_name")[["x", "y"]].mean()
    pos   = pos.loc[pos.index.isin(top_p)]
    touch = h1.groupby("player_name").size()

    edges = defaultdict(int)
    for i in range(len(rm_ev) - 1):
        r, n = rm_ev.iloc[i], rm_ev.iloc[i + 1]
        if (r["is_pass"] and r.get("outcome", 0) == 1
                and r["player_name"] in pos.index
                and n["player_name"] in pos.index
                and r["player_name"] != n["player_name"]):
            edges[(r["player_name"], n["player_name"])] += 1

    fig, ax = plt.subplots(figsize=(9.2, 6.0), dpi=150)
    fig.patch.set_facecolor("white")
    _pitch(ax, half=False)
    max_e = max(edges.values(), default=1)
    max_t = touch.max() if not touch.empty else 1

    for (p1, p2), cnt in sorted(edges.items(), key=lambda x: x[1]):
        if cnt < 2 or p1 not in pos.index or p2 not in pos.index:
            continue
        x1, y1 = pos.loc[p1, "x"], pos.loc[p1, "y"]
        x2, y2 = pos.loc[p2, "x"], pos.loc[p2, "y"]
        ax.plot([x1, x2], [y1, y2], color=_BLUE,
                alpha=0.15 + 0.65 * cnt / max_e,
                lw=1.0 + 4.0 * cnt / max_e, zorder=2, solid_capstyle="round")

    for p in pos.index:
        px, py = pos.loc[p, "x"], pos.loc[p, "y"]
        sz = 120 + 280 * (touch.get(p, 1) / max_t)
        ax.scatter(px, py, s=sz, color=_NAVY, zorder=5, edgecolors=_GOLD, lw=1.5)
        ax.text(px, py - 5.5, p.split()[-1][:11], ha="center", va="top",
                fontsize=6.5, color=_NAVY, fontweight="bold", zorder=6)

    ax.set_title(f"Pass Network — {_RM_NAME} Starting XI\n"
                 f"Node size = touches  ·  line width & opacity = pass frequency",
                 fontsize=11, color=_NAVY, fontweight="bold", pad=8)
    plt.tight_layout(pad=0.5)
    plt.savefig(str(FIG / "pass_network.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


def _gen_shot_zone():
    rm_sh  = _events[(_events["contestant_id"] == _RM_ID)  & _events["is_shot"]].copy()
    opp_sh = _events[(_events["contestant_id"] == _OPP_ID) & _events["is_shot"]].copy()
    opp_sh["x"] = 100 - opp_sh["x"]; opp_sh["y"] = 100 - opp_sh["y"]

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.2), dpi=150)
    fig.patch.set_facecolor("white")

    for ax, shots, col, title in [
        (axes[0], rm_sh,  _BLUE, f"{_RM_NAME}"),
        (axes[1], opp_sh, _RED,  f"{_OPP_NAME} (mirrored)"),
    ]:
        _pitch(ax, half=True)
        v = shots.dropna(subset=["x", "y"])
        goals = v[v["is_goal"]]
        on_t  = v[~v["is_goal"] & v["is_shot_on_target"]]
        other = v[~v.index.isin(goals.index) & ~v.index.isin(on_t.index)]
        if len(other) > 0:
            ax.scatter(other["x"], other["y"], s=55, color=col, alpha=0.35,
                       marker="o", edgecolors="white", lw=0.5, zorder=3, label="Off Target")
        if len(on_t) > 0:
            ax.scatter(on_t["x"], on_t["y"], s=80, color=col, alpha=0.70,
                       marker="s", edgecolors="white", lw=0.5, zorder=4, label="On Target")
        if len(goals) > 0:
            ax.scatter(goals["x"], goals["y"], s=160, color=_GOLD, alpha=1.0,
                       marker="*", edgecolors=_NAVY, lw=0.8, zorder=5, label="Goal")
        xg = v["xg"].sum() if "xg" in v else 0
        ax.set_title(f"{title}\n{len(v)} shots · {len(goals)} goals · {xg:.2f} xG",
                     fontsize=10, color=_NAVY, fontweight="bold", pad=6)
        ax.legend(fontsize=7.5, loc="lower left", framealpha=0.7)

    plt.suptitle(f"Shot Zone Map — {_RM_NAME} vs {_OPP_NAME}  ({_SCORE})",
                 fontsize=13, color=_NAVY, fontweight="bold", y=1.01)
    plt.tight_layout(pad=0.8)
    plt.savefig(str(FIG / "shot_zone.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


def _gen_zone14():
    rm_p = _events[
        (_events["contestant_id"] == _RM_ID) & _events["is_pass"] &
        _events["end_x"].notna() & _events["end_y"].notna()
    ].copy()
    X0, X1, Y0, Y1 = 66, 83, 21, 79
    from_z = rm_p[rm_p["x"].between(X0, X1) & rm_p["y"].between(Y0, Y1)]
    into_z = rm_p[rm_p["end_x"].between(X0, X1) & rm_p["end_y"].between(Y0, Y1)]

    fig, ax = plt.subplots(figsize=(8.0, 6.2), dpi=150)
    fig.patch.set_facecolor("white")
    _pitch(ax, half=True)
    ax.add_patch(Rectangle((X0, Y0), X1 - X0, Y1 - Y0, fill=True,
                            facecolor=_GOLD, alpha=0.18, edgecolor=_GOLD, lw=2.5,
                            linestyle="--", zorder=3))
    ax.text((X0 + X1) / 2, (Y0 + Y1) / 2, "ZONE 14",
            ha="center", va="center", fontsize=11, fontweight="bold",
            color=_GOLD, alpha=0.9, zorder=4)

    for _, r in from_z.iterrows():
        col = _GREEN if r.get("outcome", 0) == 1 else _RED
        ax.annotate("", xy=(r["end_x"], r["end_y"]), xytext=(r["x"], r["y"]),
                    arrowprops=dict(arrowstyle="->", color=col, lw=0.9, alpha=0.55))
    for _, r in into_z.head(28).iterrows():
        ax.plot([r["x"], r["end_x"]], [r["y"], r["end_y"]],
                color=_BLUE, lw=0.7, alpha=0.35, zorder=2)

    n_from  = len(from_z)
    n_succ  = int((from_z["outcome"] == 1).sum()) if not from_z.empty else 0
    n_into  = len(into_z)
    ax.set_title(
        f"Zone 14 Passing — {_RM_NAME}\n"
        f"{n_from} passes from Zone 14 ({n_succ} completed)  ·  {n_into} passes into Zone 14",
        fontsize=10.5, color=_NAVY, fontweight="bold", pad=8
    )
    ax.text(0.01, 0.01,
            "Green/Red arrows = from Zone 14  ·  Blue lines = passes into Zone 14",
            transform=ax.transAxes, fontsize=7.5, color=_GREY)
    plt.tight_layout(pad=0.5)
    plt.savefig(str(FIG / "zone14.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


def _gen_set_pieces():
    def _window_shots(corner_ev, shot_ev, win=35):
        sh = g = 0
        for _, ck in corner_ev.iterrows():
            t0 = ck["minute"] * 60 + int(ck.get("second", 0) or 0)
            mask = ((shot_ev["minute"] * 60 + shot_ev["second"].fillna(0).astype(int))
                    .between(t0, t0 + win))
            sl = shot_ev[mask]
            sh += len(sl)
            g  += int(sl["is_goal"].sum())
        return sh, g

    rm_ev  = _events[_events["contestant_id"] == _RM_ID]
    opp_ev = _events[_events["contestant_id"] == _OPP_ID]
    rm_ck  = rm_ev[rm_ev["type_id"] == 6]
    opp_ck = opp_ev[opp_ev["type_id"] == 6]
    rm_sh_ev  = rm_ev[rm_ev["is_shot"]]
    opp_sh_ev = opp_ev[opp_ev["is_shot"]]

    rm_c,  opp_c  = len(rm_ck),  len(opp_ck)
    rm_sh, rm_g   = _window_shots(rm_ck,  rm_sh_ev)
    opp_sh, opp_g = _window_shots(opp_ck, opp_sh_ev)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 5.0), dpi=150)
    fig.patch.set_facecolor("white")

    cats = ["Corners", "Corner\nShots", "Corner\nGoals"]
    x = np.arange(len(cats)); w = 0.35
    ax1.set_facecolor(_CREAM)
    for bars, vals, col, label in [
        (ax1.bar(x - w/2, [rm_c, rm_sh, rm_g],   w, color=_BLUE, label=_RM_NAME,   alpha=0.85), [rm_c, rm_sh, rm_g],   _BLUE, _RM_NAME),
        (ax1.bar(x + w/2, [opp_c, opp_sh, opp_g], w, color=_RED,  label=_OPP_NAME, alpha=0.75), [opp_c, opp_sh, opp_g], _RED,  _OPP_NAME),
    ]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, h + 0.05,
                         str(int(h)), ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax1.set_xticks(x); ax1.set_xticklabels(cats, fontsize=10)
    ax1.set_title("Corner Count & Derived Shots / Goals", fontsize=11, color=_NAVY, fontweight="bold")
    ax1.legend(fontsize=9); ax1.set_ylim(0, max(rm_c, opp_c, 1) * 1.4 + 1)
    ax1.spines[["top", "right"]].set_visible(False); ax1.grid(axis="y", alpha=0.3)

    ax2.set_facecolor(_CREAM)
    pieces = [(v, l, c) for v, l, c in [
        (rm_g,              "Goal",          _GOLD),
        (max(0, rm_sh - rm_g), "Shot (no goal)", _BLUE),
        (max(0, rm_c - rm_sh), "No shot",       "#90a4ae"),
    ] if v > 0]
    if pieces:
        vals, lbls, cols = zip(*pieces)
        ax2.pie(vals, labels=lbls, colors=cols, autopct="%1.0f%%", startangle=90,
                textprops={"fontsize": 9})
    else:
        ax2.text(0.5, 0.5, "No corners", ha="center", va="center", transform=ax2.transAxes)
    conv = round(rm_g / rm_c * 100, 1) if rm_c else 0
    ax2.set_title(f"{_RM_NAME} Corner Outcomes\n{rm_c} corners · {conv:.0f}% conversion",
                  fontsize=11, color=_NAVY, fontweight="bold")

    plt.suptitle(f"Set Piece Efficiency — {_RM_NAME} vs {_OPP_NAME}  ({_SCORE})",
                 fontsize=13, color=_NAVY, fontweight="bold", y=1.02)
    plt.tight_layout(pad=1.0)
    plt.savefig(str(FIG / "set_pieces.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


# Generate all figures (overwrite to keep fresh)
print("Generating dashboard figures…")
for fn, gen in [
    ("pass_network.png", _gen_pass_network),
    ("shot_zone.png",    _gen_shot_zone),
    ("zone14.png",       _gen_zone14),
    ("set_pieces.png",   _gen_set_pieces),
]:
    gen()
    print(f"  ✓ {fn}")
print("Done.\n")


# ═══════════════════════════════════════════════════════════════════════════════
# PDF SLIDE DECK
# ═══════════════════════════════════════════════════════════════════════════════

W, H = landscape(A4)   # 841.9 × 595.3 pt
c = rl_canvas.Canvas(str(OUT), pagesize=(W, H))
c.setTitle("Real Madrid Tactical Dashboard — FMP Presentation")
c.setAuthor("Sudhir Dahiya")

PAGE  = [0]
TOTAL = [0]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wrap(text, font, size, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        c.setFont(font, size)
        if c.stringWidth(t, font, size) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _img_fit(path, bx, by, bw, bh):
    if not Path(path).exists():
        return bx, by, bw, bh
    iw, ih = PILImage.open(path).size
    s = min(bw / iw, bh / ih)
    w, h = iw * s, ih * s
    x, y = bx + (bw - w) / 2, by + (bh - h) / 2
    c.setFillColor(WHITE); c.setStrokeColor(LGREY); c.setLineWidth(0.7)
    c.roundRect(x - 6, y - 6, w + 12, h + 12, 6, fill=1, stroke=1)
    c.drawImage(str(path), x, y, w, h, preserveAspectRatio=True, mask="auto")
    return x, y, w, h


def _header(title, kicker=None):
    c.setFillColor(NAVY); c.rect(0, H - 64, W, 64, fill=1, stroke=0)
    c.setFillColor(GOLD); c.rect(0, H - 67, W, 3, fill=1, stroke=0)
    # UE logo in header (top-right)
    if UE_LOGO.exists():
        try:
            _ue_h = 44; _ue_w = int(_ue_h * 4.2)
            c.drawImage(str(UE_LOGO), W - _ue_w - 30, H - 64 + (64 - _ue_h) / 2,
                        width=_ue_w, height=_ue_h,
                        preserveAspectRatio=True, anchor="sw", mask="auto")
        except Exception:
            pass
    if kicker:
        c.setFillColor(GOLD); c.setFont(FONT_B, 9)
        c.drawString(40, H - 26, kicker.upper())
        c.setFillColor(WHITE); c.setFont(FONT_B, 19)
        c.drawString(40, H - 50, title)
    else:
        c.setFillColor(WHITE); c.setFont(FONT_B, 21)
        c.drawString(40, H - 42, title)


def _footer():
    PAGE[0] += 1
    c.setStrokeColor(LGREY); c.setLineWidth(0.5); c.line(40, 30, W - 40, 30)
    c.setFillColor(GREY); c.setFont(FONT, 7.5)
    c.drawString(40, 20, ("Real Madrid Tactical Dashboard  ·  Sudhir Dahiya  ·  "
                           "Master's in Sports Analytics 2025–2026  ·  Data: Opta Stats Perform"))
    c.setFillColor(GOLD_D); c.setFont(FONT_B, 8)
    c.drawRightString(W - 40, 20, f"{PAGE[0]} / {TOTAL[0]}")


def _bullets(items, x, y, w, size=11.5, lead=15.5, gap=9, color=DARK):
    cy = y
    for it in items:
        sub  = it.startswith("  ")
        txt  = it.strip()
        bx   = x + (16 if sub else 0)
        avail = w - 14 - (16 if sub else 0)
        c.setFillColor(GOLD if not sub else GOLD_D)
        c.rect(bx, cy - 8.5, 5, 5, fill=1, stroke=0)
        c.setFillColor(color); c.setFont(FONT, size)
        lines = _wrap(txt, FONT, size, avail)
        for j, ln in enumerate(lines):
            c.drawString(bx + 12, cy - j * lead - 9, ln)
        cy -= lead * len(lines) + gap
    return cy


def _caption(text, x, y, w):
    c.setFillColor(GREY); c.setFont(FONT, 8)
    for j, ln in enumerate(_wrap(text, FONT, 8, w)):
        c.drawCentredString(x + w / 2, y - j * 11, ln)


# ── Slide builders ────────────────────────────────────────────────────────────

def slide_title():
    c.setFillColor(NAVY); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(GOLD); c.rect(0, H * 0.60, W, 3, fill=1, stroke=0)

    # UE logo top-left
    if UE_LOGO.exists():
        try:
            _ue_h = 52; _ue_w = int(_ue_h * 4.2)
            c.drawImage(str(UE_LOGO), 36, H - _ue_h - 24,
                        width=_ue_w, height=_ue_h,
                        preserveAspectRatio=True, anchor="sw", mask="auto")
        except Exception:
            pass

    # RM Crest top-right
    if CREST.exists():
        try:
            _cr = 68
            c.drawImage(str(CREST), W - _cr - 36, H - _cr - 18,
                        width=_cr, height=_cr,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    # Main title
    c.setFillColor(WHITE); c.setFont(FONT_B, 40)
    c.drawCentredString(W / 2, H * 0.66, "Real Madrid CF")
    c.setFillColor(GOLD); c.setFont(FONT_B, 24)
    c.drawCentredString(W / 2, H * 0.66 - 36, "Tactical & Player Analytics Dashboard")

    c.setFillColor(colors.HexColor("#cbd5e1")); c.setFont(FONT, 13)
    c.drawCentredString(W / 2, H * 0.44,
                        "Transforming event-level football data into actionable tactical intelligence")

    c.setFont(FONT, 11)
    for i, ln in enumerate([
        "Sudhir Dahiya  ·  Master's in Sports Analytics (2025–2026)",
        "Escuela Universitaria Real Madrid — Universidad Europea",
        "Python · Plotly/Dash · Gunicorn · Render  ·  Data: Opta Stats Perform (event-level)",
    ]):
        c.drawCentredString(W / 2, H * 0.30 - i * 18, ln)

    c.setFillColor(GOLD_D); c.setFont(FONT, 9)
    c.drawCentredString(W / 2, 38,
                        f"Live charts rendered from real match data  ·  {date.today():%d %B %Y}")
    c.showPage()


def slide_text(title, kicker, items, note=None):
    c.setFillColor(CREAM); c.rect(0, 0, W, H, fill=1, stroke=0)
    _header(title, kicker)
    end = _bullets(items, 50, H - 100, W - 100, size=13, lead=18, gap=12)
    if note:
        c.setFillColor(colors.HexColor("#faf6ea"))
        c.setStrokeColor(GOLD); c.setLineWidth(0.8)
        c.roundRect(50, end - 54, W - 100, 50, 5, fill=1, stroke=1)
        c.setFillColor(GOLD_D); c.setFont(FONT_B, 9)
        c.drawString(62, end - 20, "KEY POINT")
        c.setFillColor(DARK); c.setFont(FONT, 10)
        for j, ln in enumerate(_wrap(note, FONT, 10, W - 130)):
            c.drawString(62, end - 34 - j * 12, ln)
    _footer(); c.showPage()


def slide_visual(title, kicker, fig_name, items, cap):
    c.setFillColor(CREAM); c.rect(0, 0, W, H, fill=1, stroke=0)
    _header(title, kicker)
    _bullets(items, 44, H - 100, 295, size=11, lead=15, gap=9)
    fp = FIG / f"{fig_name}.png"
    if fp.exists():
        x, y, w, h = _img_fit(fp, 356, 68, W - 356 - 34, H - 64 - 68 - 18)
        _caption(cap, 356, y - 12, W - 356 - 34)
    _footer(); c.showPage()


def slide_two_visual(title, kicker, fa, fb, items, cap):
    c.setFillColor(CREAM); c.rect(0, 0, W, H, fill=1, stroke=0)
    _header(title, kicker)
    end  = _bullets(items, 50, H - 94, W - 100, size=11, lead=15, gap=8)
    top  = end - 8; bot = 58; half = (W - 80) / 2
    if (FIG / f"{fa}.png").exists():
        _img_fit(FIG / f"{fa}.png", 40, bot, half - 10, top - bot)
    if (FIG / f"{fb}.png").exists():
        _img_fit(FIG / f"{fb}.png", 40 + half + 10, bot, half - 10, top - bot)
    _caption(cap, 40, 46, W - 80)
    _footer(); c.showPage()


def slide_feature(title, kicker, features, highlight):
    """Two-column slide: left = feature cards, right = highlight block."""
    c.setFillColor(CREAM); c.rect(0, 0, W, H, fill=1, stroke=0)
    _header(title, kicker)

    # Left column: feature cards
    left_w = (W - 80) * 0.54
    cy = H - 98
    for feat in features:
        bx, by, bw, bh = 44, cy - 44, left_w, 42
        c.setFillColor(colors.HexColor("#eef2ff"))
        c.setStrokeColor(colors.HexColor("#c7d2fe")); c.setLineWidth(0.7)
        c.roundRect(bx, by, bw, bh, 5, fill=1, stroke=1)
        c.setFillColor(GOLD_D); c.setFont(FONT_B, 9)
        c.drawString(bx + 10, cy - 14, feat["tag"].upper())
        c.setFillColor(DARK); c.setFont(FONT_B, 11)
        c.drawString(bx + 10, cy - 27, feat["title"])
        c.setFont(FONT, 9)
        for j, ln in enumerate(_wrap(feat["desc"], FONT, 9, bw - 20)):
            c.drawString(bx + 10, cy - 39 - j * 11, ln)
        cy -= 52

    # Right column: highlight (gold-bordered box with bullet points)
    rx  = 44 + left_w + 22
    rw  = W - rx - 36
    c.setFillColor(colors.HexColor("#faf6ea"))
    c.setStrokeColor(GOLD); c.setLineWidth(1.5)
    c.roundRect(rx, 55, rw, H - 64 - 55 - 30, 8, fill=1, stroke=1)
    c.setFillColor(GOLD_D); c.setFont(FONT_B, 10)
    c.drawString(rx + 14, H - 98, highlight["title"].upper())
    c.setFillColor(DARK)
    _bullets(highlight["items"], rx + 14, H - 118, rw - 28, size=10.5, lead=16, gap=8)

    _footer(); c.showPage()


def slide_close():
    c.setFillColor(NAVY); c.rect(0, 0, W, H, fill=1, stroke=0)

    # UE logo and RM crest side by side at top
    if UE_LOGO.exists():
        try:
            _ue_h = 52; _ue_w = int(_ue_h * 4.2)
            c.drawImage(str(UE_LOGO), W / 2 - _ue_w - 20, H - _ue_h - 28,
                        width=_ue_w, height=_ue_h,
                        preserveAspectRatio=True, anchor="sw", mask="auto")
        except Exception:
            pass
    if CREST.exists():
        try:
            _cr = 52
            c.drawImage(str(CREST), W / 2 + 20, H - _cr - 28,
                        width=_cr, height=_cr,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    c.setFillColor(GOLD); c.rect(0, H * 0.56, W, 3, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont(FONT_B, 30)
    c.drawCentredString(W / 2, H * 0.585, "From Data to Tactical Decision")
    c.setFillColor(colors.HexColor("#cbd5e1")); c.setFont(FONT, 13)
    c.drawCentredString(W / 2, H * 0.455,
                        "One transparent, interactive platform — "
                        "match prep, scouting, review and player development.")
    c.setFillColor(GOLD); c.setFont(FONT_B, 14)
    c.drawCentredString(W / 2, H * 0.34, "Real Madrid CF Tactical Dashboard")
    c.setFillColor(colors.HexColor("#cbd5e1")); c.setFont(FONT, 11)
    c.drawCentredString(W / 2, H * 0.34 - 22,
                        "Sudhir Dahiya  ·  Master's in Sports Analytics 2025–2026  ·  Data: Opta Stats Perform")
    PAGE[0] += 1
    c.showPage()


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE DECK
# ═══════════════════════════════════════════════════════════════════════════════

slides = [

    ("title",),

    ("text", "The Problem & The Objective", "Why this dashboard exists", [
        "Elite football generates ~1,500–2,000 on-ball events per match — far too granular to read by eye.",
        "Traditional analysis suffers from outcome bias: a scoreline hides whether a performance was earned.",
        "Coaching staff need the data-to-decision layer that turns a raw Opta feed into tactical answers.",
        "Objective: quantify HOW Real Madrid play — not just whether they win — across attacking, defending,"
        " transitions and set pieces.",
        "Deliver an interactive, transparent, reproducible tool for match prep, opposition scouting and review.",
    ], "Every metric is traceable to an explicit formula over observed events — no synthetic data anywhere."),

    ("text", "Dashboard Architecture — Seven Modules", "How the platform is organised", [
        "Overview — season KPIs, results table, xG / xGA trends, goals trend, form tracker.",
        "Match Analysis — shot maps, xG chart, pass map, pass network, shot zones, Zone 14,"
        " GK distribution, crossing patterns, goalmouth, defensive actions, transitions, set pieces.",
        "Player Analysis — squad table, per-player stats, multi-radar, touch heatmaps.",
        "Tactical Phases — PPDA, pressing maps, four-phase A/B/C/D scoring, recoveries, field tilt.",
        "Opponent Scout — opposition profiling, threat heatmap, set-piece tendencies, auto report.",
        "Benchmarking — cross-competition and cross-season comparisons.",
        "Report — one-click PDF / DOCX export from any selection.",
    ], "All seven modules share one data pipeline and one set of KPI definitions."),

    ("text", "Data Foundation & Methodology", "What powers every number", [
        "Source: Opta Stats Perform event-level JSON — one file per match.",
        "Scope: 108 clean match files · 3 competitions (LaLiga · UCL · Copa del Rey) · 2 seasons.",
        "Pipeline: parse & normalise events → compute match KPIs → re-slice to player, phase, opponent.",
        "Transparent models: positional xG (location), PPDA (pressing), field tilt, four-phase A/B/C/D.",
        "Showcase fixture for the visuals that follow: Real Madrid 2–1 Barcelona, LaLiga 2025–26 MD10.",
    ], "Possession is a documented pass-share proxy; no tracking data — limitations stated openly."),

    ("feature", "Multi-Match Analysis Mode", "New feature — Match Analysis",
     [
         {"tag": "new", "title": "Multi-Match (up to 5)",
          "desc": "Select any 5 specific matches for aggregated cross-match analysis."},
         {"tag": "how", "title": "Mode Selector",
          "desc": "Dropdown now has 3 options: Single Match · Match Range · Multi-Match (≤5)."},
         {"tag": "data", "title": "Shared Store Relay",
          "desc": "dcc.Store propagates selected paths to all 25+ callbacks without performance cost."},
         {"tag": "scope", "title": "All Sections Covered",
          "desc": "Shot map, xG, pass network, Zone 14, transitions, set pieces — all multi-match aware."},
     ],
     {"title": "Why it matters",
      "items": [
          "Range mode aggregates a continuous window of matches.",
          "Multi-Match lets an analyst cherry-pick: home legs, rivals, or run of form.",
          "Same visualisations, aggregated data — no new learning curve.",
          "Enables direct pattern comparison across non-consecutive fixtures.",
          "Implemented without breaking Single or Range modes.",
      ]}),

    ("visual", "Overview — Season Context", "Module 1 · Overview", "ov_shots_trend", [
        "Tracks process metrics across the season, not just results.",
        "Process metrics are more stable and more predictive than outcomes.",
        "Falling shots with high pass accuracy = early warning of sterile possession.",
        "The panel a coach watches weekly to spot a problem before the table shows it.",
    ], "Overview module — Shots & Pass-Accuracy Trend, live from the real LaLiga 2025–26 feed."),

    ("visual", "Match Analysis — Shot Map", "Module 2 · Match Analysis", "shot_map", [
        "Every shot at its true location; marker size ∝ xG; ★ = goal.",
        "Real Madrid (blue) attack right; Barcelona (red) attack left.",
        "RM's chances cluster centrally inside the box — high volume AND high quality.",
        "Answers: where, and how good, were the chances — for both teams.",
    ], "Match Analysis — Shot Map · Real Madrid 2–1 Barcelona (24 shots · 2 goals · 3.34 xG)."),

    ("visual", "Match Analysis — xG Accumulation", "Module 2 · Match Analysis", "xg_accumulation", [
        "Running total of Expected Goals, minute by minute, for both teams.",
        "Slope = rate of chance creation; a tall step = a single large chance.",
        "Reveals WHEN control happened — early dominance vs a nervy finish.",
        "Full-time gap between the lines = the match's xG difference.",
    ], "Match Analysis — Expected Goals accumulating through the match from the real event feed."),

    ("visual", "Match Analysis — Tactical Comparison", "Module 2 · Match Analysis", "tactical_comparison", [
        "Head-to-head bars of headline KPIs: possession, shots, passing, defensive actions.",
        "Built for communication speed — 'who won which battle' in one glance.",
        "Each metric read in relative context — the gap to the opponent, not just the raw value.",
    ], "Match Analysis — Tactical Comparison, Real Madrid vs Barcelona, from the real feed."),

    ("visual", "Match Analysis — Pass Network", "Module 2 · Match Analysis", "pass_network", [
        "Directed graph of the starting XI's passing connections.",
        "Node position = player's average event location on the pitch.",
        "Node size = total touches; line width & opacity = pass frequency.",
        "Exposes the dominant playmaking triangle and width of ball circulation.",
        "High centrality in Zone 14 = chance-creating hub detected automatically.",
    ], "Pass Network — inferred from Opta event sequences for the Real Madrid starting XI."),

    ("visual", "Match Analysis — Shot Zone Map", "Module 2 · Match Analysis", "shot_zone", [
        "Every shot plotted at its true Opta coordinate on a half-pitch view.",
        "Outcome coded by shape: ★ = goal · ■ = on target · ● = off target / blocked.",
        "Side-by-side: Real Madrid (left) and opponent (right, mirrored to same direction).",
        "Reveals WHERE both teams created chances — box dominance vs long-range reliance.",
    ], "Shot Zone Map — spatial shot quality comparison for both teams, from the real event feed."),

    ("visual", "Match Analysis — Zone 14 Passing", "Module 2 · Match Analysis", "zone14", [
        "Zone 14 (the half-space between penalty area top and wide channels) is where chances originate.",
        "Green arrows = completed passes from Zone 14; red = unsuccessful.",
        "Blue lines = passes played INTO Zone 14 (feeding the danger zone).",
        "High volume into Zone 14 + high completion from it = dangerous central build-up.",
    ], "Zone 14 Passing — Opta passes filtered to the central attacking half-space."),

    ("visual", "Tactical Phase Profile (A/B/C/D)", "Module 4 · Tactical Phases", "phase_radar", [
        "Four moments of play scored 0–100: Offensive Moment (A), Defensive Transition (B),"
        " Defensive Moment (C), Offensive Transition (D).",
        "The radar 'shape' is the match's tactical fingerprint.",
        "This fixture: strong A + B, lower C + D = possession-and-counter-press.",
        "Composite indices grounded in PPDA, xG, recoveries & transition rate.",
    ], "Tactical Phase Profile — the dashboard's executive summary of how the team played."),

    ("visual", "Attacking Transitions", "Module 2 · Match Analysis", "transition", [
        "Locates every ball regain, then tests for a shot within the time window (5–15 s).",
        "Quantifies fast-break efficiency and transition xG — the counter-attack as a number.",
        "Against possession sides, transitions punish their committed players.",
        "Window is an analyst control, not a hidden assumption.",
    ], "Match Analysis — Transition Metrics, quantifying Real Madrid's counter-attacking threat."),

    ("visual", "Pressing Intensity — PPDA Trend", "Module 4 · Tactical Phases", "ppda_trend", [
        "PPDA = passes the opponent completes per RM defensive action (lower = more intense).",
        "Plotted every matchday with the season average marked.",
        "Tight band = a drilled pressing identity; wide scatter = game-state dependent.",
        "The instant verdict on whether 'we pressed well today' is actually true.",
    ], "Tactical Phases — season-long PPDA trend across the real LaLiga campaign."),

    ("visual", "Pressing Actions Map", "Module 4 · Tactical Phases", "press_map", [
        "Where on the pitch Real Madrid engaged defensively — every press, tackle, interception.",
        "Reveals pressing HEIGHT: high press vs mid-block vs low block.",
        "Exposes asymmetry — a flank pressed harder is a flank the opponent will exploit.",
        "Direct evidence of whether the pressing instruction was executed.",
    ], "Tactical Phases — Pressing Actions Map for the real match."),

    ("visual", "Ball Recoveries by Zone", "Module 4 · Tactical Phases", "recovery_map", [
        "WHERE the team wins the ball back — defensive / middle / attacking third.",
        "This match: 37 recoveries — Mid 48.6% · Def 37.8% · Att 13.5% (mid-block profile).",
        "Attacking-third recoveries are the most dangerous regains in football.",
        "Read against intention: great for a mid-block, disappointing for a high press.",
    ], "Tactical Phases — Ball Recoveries by Pitch Zone from the real feed."),

    ("visual", "Territorial Dominance — Field Tilt", "Module 4 · Tactical Phases", "field_tilt", [
        "Share of all final-third activity belonging to Real Madrid.",
        "Antidote to misreading possession — control that becomes territory.",
        "55% possession with 75% field tilt beats 60% possession with 51% tilt.",
        "Validates the PURPOSE of keeping the ball.",
    ], "Tactical Phases — Field Tilt across the real season."),

    ("visual", "Set Piece Efficiency", "Module 2 · Match Analysis", "set_pieces", [
        "Counts corners awarded, shots derived from corners and goals from corners.",
        "Pie chart shows RM's corner conversion funnel: corners → shots → goals.",
        "Side-by-side bars compare RM and opponent set-piece output.",
        "Also covers free kicks and penalty areas in the full dashboard.",
        "Set pieces account for ~30% of goals at elite level — this panel quantifies them.",
    ], "Set Piece Efficiency — derived from Opta event sequences for the real match."),

    ("two", "How the Panels Triangulate", "Case study · Real Madrid 2–1 Barcelona",
     "shot_map", "phase_radar", [
         "No single panel proves a conclusion — together they make it unarguable: the Shot Map shows"
         " high-quality central chances; the radar collapses the match into one possession-and-counter"
         "-press shape.",
         "Triangulation runs across xG, field tilt, recoveries and PPDA — a tactical claim that is"
         " true leaves its fingerprint on several independent panels at once.",
     ], "Two independent views of the same real match converging on one tactical read."),

    ("feature", "Report Generator", "Module 7 · Report",
     [
         {"tag": "output", "title": "PDF & DOCX Export",
          "desc": "One-click branded report in PDF or DOCX — downloads directly from the browser."},
         {"tag": "scope", "title": "Match Scope",
          "desc": "Mirrors Match Analysis: Single, Range or Multi-Match (up to 5)."},
         {"tag": "player", "title": "Player Breakdown",
          "desc": "Per-player stats table auto-populates from squad in selected matches."},
         {"tag": "content", "title": "9 Sections",
          "desc": "Filter Summary · Executive Summary · Team · Player · Tactical · Match · "
                  "Benchmarking · Appendix · Conclusion."},
     ],
     {"title": "Report sections",
      "items": [
          "01 — Filter Summary (competition, season, matches).",
          "02 — Executive Summary (W/D/L, xG, PPDA, possession).",
          "03 — Team Performance (aggregate + match-by-match table).",
          "04 — Player Performance (goals, shots, passes, xG per player).",
          "05 — Tactical Analysis (pressing maps, position maps).",
          "06 — Match Analysis (shot maps, xG chart, pass network).",
          "07 — Benchmarking (league comparisons).",
          "08 — Visualisation Appendix (all captured charts).",
          "09 — Conclusion: Pre / Match / Post-match evaluation.",
      ]}),

    ("text", "Implementation Status", "Strictly reconciled to the live codebase", [
        "All nine core analysis features IMPLEMENTED with dedicated panels:",
        "  Pre-Match · Attacking Transitions · Organised Attack · Defensive Strategy · Set Pieces.",
        "  Possession Recovery · Post-Match · Final-Third Entries · Match Info.",
        "New in June 2026: Multi-Match mode · Pass Network · Shot Zone Map · Zone 14 ·"
        " Set Piece Efficiency · GK Distribution · Crossing Patterns · Goalmouth Map ·"
        " Defensive Actions Map · Report Generator.",
        "Deployed publicly via GitHub → Render CI/CD (Plotly/Dash + Gunicorn).",
        "Report export: PDF and DOCX with UE / Real Madrid branding.",
    ], "108 clean match files across 3 competitions and 2 seasons; no synthetic data anywhere."),

    ("text", "Limitations & Future Scope", "Honest boundaries and the roadmap", [
        "Event data only — no tracking: off-ball shape & pressing distances are approximated.",
        "xG is a transparent positional model (location only), not a provider post-shot model.",
        "Phase scores are interpretive 0–100 composites, not physical units.",
        "Descriptive & diagnostic — not predictive, not real-time.",
        "Roadmap: tracking-data integration · player per-90 depth · Expected Threat (xT) ·"
        " ML pattern clustering · predictive analytics · video integration · live dashboards.",
    ], "The platform is a foundation for continued research and professional deployment."),

    ("close",),
]

TOTAL[0] = len(slides)

for s in slides:
    if   s[0] == "title":   slide_title()
    elif s[0] == "text":    slide_text(s[1], s[2], s[3], s[4] if len(s) > 4 else None)
    elif s[0] == "visual":  slide_visual(s[1], s[2], s[3], s[4], s[5])
    elif s[0] == "two":     slide_two_visual(s[1], s[2], s[3], s[4], s[5], s[6])
    elif s[0] == "feature": slide_feature(s[1], s[2], s[3], s[4])
    elif s[0] == "close":   slide_close()

c.save()
print(f"Saved → {OUT}")
print(f"        {OUT.stat().st_size // 1024} KB  ·  {TOTAL[0]} slides")
