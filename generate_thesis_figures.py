"""
generate_thesis_figures.py
Renders three dashboard figures for the thesis, computed live from the real
Opta dataset via the dashboard's own data pipeline:
  fig_shot_map.png   — Real Madrid shot map (xG-weighted) for a showcase match
  fig_ppda_trend.png — PPDA pressing-intensity trend across the LaLiga season
  fig_phase_radar.png— Four-phase tactical radar for the showcase match

Output: thesis_figures/*.png
"""
import os
import sys
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc, Ellipse
import numpy as np

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("DATA_ROOT", str(ROOT / "dashboard" / "data"))
sys.path.insert(0, str(ROOT / "dashboard" / "app"))

from utils.data_loader import (  # noqa: E402
    get_season_match_list, load_match_json, parse_events, get_shot_data, calc_ppda,
)
from utils.phase_scoring import phase_scores_from_events  # noqa: E402

# ── Brand palette ────────────────────────────────────────────────────────────
NAVY = "#0b1730"; GOLD = "#c8a951"; GOLD_D = "#a8882e"; CREAM = "#f8f7f3"
BLUE = "#1d4ed8"; RED = "#dc2626"; GREEN = "#059669"; GREY = "#475569"; LGREY = "#cbd5e1"

FIG_DIR = ROOT / "thesis_figures"
FIG_DIR.mkdir(exist_ok=True)

COMP, SEASON = "LaLiga", "2025-2026"
matches = get_season_match_list(COMP, SEASON)
SHOWCASE = next((m for m in matches if "Barcelona" in m["opponent"] and m["is_rm_home"]), matches[0])
_data = load_match_json(SHOWCASE["filepath"])
_events = parse_events(_data)


# ── Pitch helper (Opta 0–100 coordinates) ────────────────────────────────────
def draw_pitch(ax):
    ax.set_facecolor(CREAM)
    lc = NAVY
    ax.add_patch(Rectangle((0, 0), 100, 100, fill=False, ec=lc, lw=1.6))
    ax.plot([50, 50], [0, 100], color=lc, lw=1.2)
    ax.add_patch(Ellipse((50, 50), 17.4, 26, fill=False, ec=lc, lw=1.2))
    ax.scatter([50], [50], s=8, color=lc)
    # right penalty + goal area (RM attacks right)
    ax.add_patch(Rectangle((84.3, 21.1), 15.7, 57.8, fill=False, ec=lc, lw=1.2))
    ax.add_patch(Rectangle((94.2, 36.8), 5.8, 26.4, fill=False, ec=lc, lw=1.2))
    ax.scatter([88.5], [50], s=8, color=lc)
    ax.add_patch(Arc((88.5, 50), 17.4, 26, angle=0, theta1=128, theta2=232, ec=lc, lw=1.2))
    # left penalty + goal area
    ax.add_patch(Rectangle((0, 21.1), 15.7, 57.8, fill=False, ec=lc, lw=1.2))
    ax.add_patch(Rectangle((0, 36.8), 5.8, 26.4, fill=False, ec=lc, lw=1.2))
    ax.scatter([11.5], [50], s=8, color=lc)
    ax.add_patch(Arc((11.5, 50), 17.4, 26, angle=0, theta1=-52, theta2=52, ec=lc, lw=1.2))
    ax.set_xlim(-2, 102); ax.set_ylim(-2, 102)
    ax.set_aspect(68 / 105 * (104 / 104))  # near-real aspect for Opta units
    ax.axis("off")


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 1 — Shot map
# ═══════════════════════════════════════════════════════════════════════════
def fig_shot_map():
    shots = get_shot_data(_events, SHOWCASE)
    rm = shots[shots["team_label"] == "Real Madrid"].copy()
    fig, ax = plt.subplots(figsize=(9.2, 6.0), dpi=150)
    fig.patch.set_facecolor("white")
    draw_pitch(ax)

    goals = rm[rm["is_goal"]]
    ontgt = rm[(~rm["is_goal"]) & (rm["is_shot_on_target"])]
    offtg = rm[(~rm["is_goal"]) & (~rm["is_shot_on_target"])]

    def sz(d):
        return 80 + d["xg"].astype(float) * 1400

    ax.scatter(offtg["x"], offtg["y"], s=sz(offtg), facecolor="white", edgecolor=GREY,
               lw=1.3, alpha=.85, zorder=3, label="Off target")
    ax.scatter(ontgt["x"], ontgt["y"], s=sz(ontgt), facecolor=BLUE, edgecolor=NAVY,
               lw=1.0, alpha=.75, zorder=4, label="On target")
    ax.scatter(goals["x"], goals["y"], s=sz(goals) + 60, marker="*",
               facecolor=GOLD, edgecolor=RED, lw=1.4, zorder=5, label="Goal")

    total_xg = float(rm["xg"].sum())
    ax.set_title(
        f"Real Madrid Shot Map — {SHOWCASE['description']}  ({SHOWCASE['score_str']})\n"
        f"{len(rm)} shots · {int(rm['is_goal'].sum())} goals · {total_xg:.2f} xG (positional model)",
        fontsize=11.5, fontweight="bold", color=NAVY, pad=10)
    leg = ax.legend(loc="lower left", fontsize=8.5, framealpha=.95, title="Marker size ∝ xG")
    leg.get_title().set_fontsize(8)
    ax.annotate("Attacking direction →", xy=(72, -1.5), fontsize=8.5, color=GOLD_D,
                fontstyle="italic", ha="center")
    out = FIG_DIR / "fig_shot_map.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("saved", out.name)


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 2 — PPDA trend across the season
# ═══════════════════════════════════════════════════════════════════════════
def fig_ppda_trend():
    xs, ys, labels = [], [], []
    for i, m in enumerate(matches, 1):
        ev = parse_events(load_match_json(m["filepath"]))
        ys.append(calc_ppda(ev, m)); xs.append(i); labels.append(m["opponent"][:3].upper())
    avg = float(np.mean(ys))
    fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.plot(xs, ys, "-", color=BLUE, lw=1.8, zorder=2)
    ax.scatter(xs, ys, s=34, color=NAVY, zorder=3)
    ax.axhline(avg, color=GOLD_D, lw=1.5, ls="--", zorder=1,
               label=f"Season average PPDA = {avg:.2f}")
    # highlight best (lowest) press
    bi = int(np.argmin(ys))
    ax.scatter([xs[bi]], [ys[bi]], s=120, facecolor=GREEN, edgecolor="white", lw=1.5, zorder=4)
    ax.annotate(f"Most intense press\nvs {matches[bi]['opponent']} ({ys[bi]:.1f})",
                xy=(xs[bi], ys[bi]), xytext=(xs[bi] + 1.5, ys[bi] + 4),
                fontsize=8, color=GREEN, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1))
    ax.set_title("Pressing Intensity (PPDA) — LaLiga 2025–26, by Matchday",
                 fontsize=12, fontweight="bold", color=NAVY, pad=8)
    ax.set_xlabel("Matchday", fontsize=9.5, color=NAVY)
    ax.set_ylabel("PPDA  (lower = more intense press)", fontsize=9.5, color=NAVY)
    ax.set_xticks(xs[::2]); ax.tick_params(labelsize=8, colors=NAVY)
    for s in ax.spines.values(): s.set_color(LGREY)
    ax.grid(axis="y", color=LGREY, lw=.5, alpha=.7)
    ax.legend(fontsize=8.5, loc="upper right", framealpha=.95)
    out = FIG_DIR / "fig_ppda_trend.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("saved", out.name)


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 3 — Four-phase tactical radar
# ═══════════════════════════════════════════════════════════════════════════
def fig_phase_radar():
    scores = phase_scores_from_events(_events, SHOWCASE["rm_id"], SHOWCASE["opp_id"])
    labels = ["A · Offensive\nMoment", "B · Defensive\nTransition",
              "C · Defensive\nMoment", "D · Offensive\nTransition"]
    vals = [scores["A. Offensive Moment"], scores["B. Defensive Transition"],
            scores["C. Defensive Moment"], scores["D. Offensive Transition"]]
    ang = np.linspace(0, 2 * np.pi, len(vals), endpoint=False).tolist()
    vals_c = vals + vals[:1]; ang_c = ang + ang[:1]

    fig, ax = plt.subplots(figsize=(6.6, 6.2), dpi=150, subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")
    ax.set_facecolor(CREAM)
    ax.plot(ang_c, vals_c, color=BLUE, lw=2.2, zorder=3)
    ax.fill(ang_c, vals_c, color=BLUE, alpha=.22, zorder=2)
    ax.scatter(ang, vals, s=55, color=GOLD, edgecolor=NAVY, lw=1.2, zorder=4)
    for a, v in zip(ang, vals):
        ax.annotate(f"{v:.0f}", xy=(a, v), xytext=(a, v + 7), ha="center",
                    fontsize=9.5, fontweight="bold", color=NAVY)
    ax.set_xticks(ang); ax.set_xticklabels(labels, fontsize=9, color=NAVY, fontweight="bold")
    ax.set_ylim(0, 100); ax.set_yticks([20, 40, 60, 80])
    ax.set_yticklabels(["20", "40", "60", "80"], fontsize=7.5, color=GREY)
    ax.grid(color=LGREY, lw=.6)
    ax.set_title(f"Tactical Phase Profile — {SHOWCASE['description']} ({SHOWCASE['score_str']})\n"
                 "Phase scores normalised 0–100",
                 fontsize=11.5, fontweight="bold", color=NAVY, pad=22)
    out = FIG_DIR / "fig_phase_radar.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("saved", out.name)


if __name__ == "__main__":
    fig_shot_map()
    fig_ppda_trend()
    fig_phase_radar()
    print("Showcase match:", SHOWCASE["description"], SHOWCASE["score_str"])
