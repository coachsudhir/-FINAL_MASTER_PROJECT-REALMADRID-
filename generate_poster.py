"""
Real Madrid CF — Defence Poster Generator
All statistics sourced strictly from the Opta dataset (108 match files).
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
from pathlib import Path
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# ── Brand colours ──────────────────────────────────────────────────────────
NAVY  = '#0b1730'; NAVY2 = '#060f1e'; GOLD  = '#c8a951'; GOLD_D = '#a8882e'
GOLD_L = '#f5eed6'; CREAM = '#f8f7f3'; WHITE = '#ffffff'
BLUE  = '#2563eb'; RED   = '#dc2626'; GREEN = '#059669'
AMBER = '#d97706'; GREY  = '#475569'; LGREY = '#e0ddd5'

ASSET_DIR = Path(__file__).parent / 'dashboard' / 'app' / 'assets'

# ── 100 % real data — Opta Stats Perform ───────────────────────────────────
LALIGA = dict(matches=36,wins=25,draws=5,losses=6,win_pct=69.4,
              goals=72,conceded=33,gd=39,goals_pg=2.0,conceded_pg=0.92,
              shots=649,shots_ot=297,possession=58.8,pass_acc=87.7,
              xgf=66.01,xga=38.57,xgd=27.44)
UCL    = dict(matches=12,wins=9,draws=0,losses=3,win_pct=75.0,
              goals=29,conceded=14,gd=15,goals_pg=2.42,conceded_pg=1.17,
              shots=217,shots_ot=92,possession=55.6,pass_acc=87.2,
              xgf=21.28,xga=18.27,xgd=3.01)
COPA   = dict(matches=2,wins=1,draws=0,losses=1,goals=5,conceded=5,
              possession=71.2,pass_acc=88.2)

TOP_PLAYERS = [
    ('K. Mbappé',        'ST',  24,  5, 29, 14.73, 141),
    ('Vinícius Júnior',  'ST',  15,  5, 35, 10.64,  99),
    ('F. Valverde',      'AMW',  5,  8, 32,  1.63,  51),
    ('J. Bellingham',    'AMW',  5,  4, 26,  7.87,  49),
    ('A. Güler',         'DM',   4,  9, 32,  3.36,  50),
]
MODULES = [
    ('Season Overview',  '📊', 'Season KPIs · win/loss record\nAll-Matches table · trends'),
    ('Match Analysis',   '⚽', 'Shot maps · xG accumulation\nPass networks · tactical bars'),
    ('Player Analysis',  '👤', 'Squad table · Min% slider\nMulti-radar · per-match stats'),
    ('Tactical Phases',  '⚔️', 'Pressing maps · PPDA trend\nPhase-by-phase event analysis'),
    ('Opponent Scout',   '🔭', 'Opposition pass maps\nDefensive shape · set pieces'),
    ('Benchmarking',     '📈', 'Cross-competition charts\nGoal & pass accuracy trends'),
    ('Analysis Report',  '📋', 'Auto-generated PDF / DOCX\nfrom real match data only'),
]

# ── Figure ──────────────────────────────────────────────────────────────────
FW, FH, DPI = 22, 31, 130
fig = plt.figure(figsize=(FW, FH), dpi=DPI, facecolor=CREAM)


def make_ax(l, b, w, h, facecolor=CREAM, zorder=2):
    ax = fig.add_axes([l/FW, b/FH, w/FW, h/FH], zorder=zorder)
    ax.set_facecolor(facecolor)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    return ax


def t(ax, x, y, s, **kw):
    kw.setdefault('transform', ax.transAxes)
    kw.setdefault('clip_on', False)
    return ax.text(x, y, s, **kw)


def hd(ax, label, sub=None):
    """Draw a section header bar inside ax."""
    ax.add_patch(FancyBboxPatch((0, .8), 1, .2,
                 boxstyle='square,pad=0', fc=NAVY, ec='none', transform=ax.transAxes))
    ax.axhline(.8, color=GOLD, lw=2, xmin=0, xmax=1)
    t(ax, .5, .9, label, ha='center', va='center',
      fontsize=12, fontweight='bold', color=WHITE)
    if sub:
        t(ax, .5, .72, sub, ha='center', va='center',
          fontsize=8.5, color=GREY, fontstyle='italic')


def stat_row(ax, y, label, val, color=NAVY, lw=True):
    t(ax, .04, y, label, ha='left',  va='center', fontsize=8, color=GREY)
    t(ax, .96, y, val,   ha='right', va='center', fontsize=9, color=color, fontweight='bold')
    if lw:
        ax.axhline(y-.042, color=LGREY, lw=.5, xmin=.02, xmax=.98)


# ═══════════════════════════════════════════════════════════════════════════
# 1 · HEADER
# ═══════════════════════════════════════════════════════════════════════════
hax = make_ax(0, 28.8, FW, 2.2, facecolor=NAVY2, zorder=10)
hax.axhline(0, color=GOLD, lw=4)

# RM crest
cp = ASSET_DIR / 'rm_crest.jpg'
if cp.exists():
    ci = np.array(Image.open(cp).convert('RGB'))
    hax.add_artist(AnnotationBbox(OffsetImage(ci, zoom=.21),
                   (.045, .52), frameon=False, xycoords='axes fraction'))
# UE logo
up = ASSET_DIR / 'ue_real_madrid_logo.png'
if up.exists():
    ui = Image.open(up).convert('RGBA')
    bg = Image.new('RGBA', ui.size, (255,255,255,255))
    bg.paste(ui, mask=ui.split()[3])
    hax.add_artist(AnnotationBbox(OffsetImage(np.array(bg.convert('RGB')), zoom=.13),
                   (.955, .52), frameon=False, xycoords='axes fraction'))

t(hax, .5, .75, 'Real Madrid CF', ha='center', va='center',
  fontsize=30, fontweight='bold', color=WHITE)
t(hax, .5, .43, 'Tactical & Player Performance Analytics', ha='center', va='center',
  fontsize=14, color=GOLD, fontstyle='italic')
t(hax, .5, .12,
  "Sudhir Dahiya  •  Master's in Sports Analytics (2025–2026)  •  Data: Opta Stats Perform",
  ha='center', va='center', fontsize=8.5, color='#94a3b8')

# ═══════════════════════════════════════════════════════════════════════════
# 2 · INTRO BAND
# ═══════════════════════════════════════════════════════════════════════════
iax = make_ax(.3, 27.3, FW-.6, 1.35, facecolor=GOLD_L, zorder=5)
t(iax, .5, .55,
  ('This platform provides in-depth tactical and player performance analysis for Real Madrid CF, '
   'powered exclusively by real Opta Stats Perform event data.\n'
   'Covering 50 matches across 3 competitions (LaLiga · UCL · Copa del Rey) in the 2025–2026 season, '
   'the dashboard delivers 7 analytics modules — from shot maps and xG models\n'
   'to pressing metrics, player radars and auto-generated PDF / DOCX reports. '
   'Built with Python, Streamlit and Plotly.'),
  ha='center', va='center', fontsize=8.8, color=NAVY, multialignment='center', linespacing=1.65)

# ═══════════════════════════════════════════════════════════════════════════
# 3 · SECTION HEADER — Season Performance
# ═══════════════════════════════════════════════════════════════════════════
s1ax = make_ax(.3, 26.5, FW-.6, .65, facecolor=CREAM, zorder=5)
t(s1ax, .5, .72, '2025–2026 Season Performance', ha='center', va='center',
  fontsize=13, fontweight='bold', color=NAVY)
s1ax.axhline(.18, color=GOLD, lw=2.5, xmin=.08, xmax=.92)

# ── LaLiga card ────────────────────────────────────────────────────────────
def comp_card(l, b, w, h, title, accent, rows, badge):
    ax = make_ax(l, b, w, h, facecolor=WHITE, zorder=5)
    ax.add_patch(FancyBboxPatch((0,0), 1, 1, boxstyle='round,pad=0.01',
                                fc='none', ec=LGREY, lw=1.2, transform=ax.transAxes))
    ax.add_patch(FancyBboxPatch((0,.88), 1, .12, boxstyle='square,pad=0',
                                fc=accent, ec='none', transform=ax.transAxes))
    t(ax, .5, .935, title, ha='center', va='center',
      fontsize=9.5, fontweight='bold', color=WHITE)
    t(ax, .5, .83, badge, ha='center', va='center',
      fontsize=9, fontweight='bold', color=accent)
    ax.axhline(.80, color=LGREY, lw=.8, xmin=.03, xmax=.97)
    step = .76 / max(len(rows), 1)
    for i, (lbl, val, col) in enumerate(rows):
        y = .77 - i * step
        stat_row(ax, y, lbl, val, color=col, lw=(i < len(rows)-1))

comp_card(.3, 20.65, 6.9, 5.65,
    'LaLiga 2025–2026', NAVY,
    [('Record (W–D–L)',  '25–5–6',    GREEN),
     ('Win Rate',        '69.4%',     GREEN),
     ('Goals Scored',    '72  (2.0/g)', BLUE),
     ('Goals Conceded',  '33  (0.92/g)', RED),
     ('Goal Diff.',      '+39',        GREEN),
     ('Shots / On Tgt',  '649 / 297',  GREY),
     ('Avg Possession',  '58.8%',      BLUE),
     ('Pass Accuracy',   '87.7%',      BLUE),
     ('xG For',          '66.01',      BLUE),
     ('xG Against',      '38.57',      RED),
     ('xG Diff.',        '+27.44',     GREEN)],
    '🏆  LaLiga Champions 2025–26')

comp_card(7.5, 20.65, 6.9, 5.65,
    'UEFA Champions League 2025–26', '#1a56db',
    [('Record (W–D–L)',  '9–0–3',      GREEN),
     ('Win Rate',        '75.0%',      GREEN),
     ('Goals Scored',    '29  (2.42/g)', BLUE),
     ('Goals Conceded',  '14  (1.17/g)', RED),
     ('Goal Diff.',      '+15',         GREEN),
     ('Shots / On Tgt',  '217 / 92',    GREY),
     ('Avg Possession',  '55.6%',       BLUE),
     ('Pass Accuracy',   '87.2%',       BLUE),
     ('xG For',          '21.28',       BLUE),
     ('xG Against',      '18.27',       RED),
     ('xG Diff.',        '+3.01',       GREEN)],
    '⭐  UCL 2025–26 Campaign')

comp_card(14.7, 20.65, 6.9, 5.65,
    'Copa del Rey 2025–26', AMBER,
    [('Record (W–D–L)',  '1–0–1',     AMBER),
     ('Goals Scored',    '5  (2.5/g)', BLUE),
     ('Goals Conceded',  '5  (2.5/g)', RED),
     ('Avg Possession',  '71.2%',      BLUE),
     ('Pass Accuracy',   '88.2%',      BLUE),
     ('xG For',          '5.08',       BLUE),
     ('xG Against',      '2.38',       RED),
     ('xG Diff.',        '+2.70',      GREEN)],
    'Copa del Rey — 2 matches')

# ── Overall combined badge strip ─────────────────────────────────────────
bax = make_ax(.3, 20.0, FW-.6, .55, facecolor=NAVY, zorder=5)
badges = [('50 Matches Analysed', WHITE), ('36 Goals Scored',     GOLD),
          ('66 xG For (LaLiga)', GOLD),   ('69.4% Win Rate (LL)', GREEN),
          ('87.7% Pass Acc.',     GOLD),  ('108 Opta Files',      '#60a5fa')]
for i,(lbl,col) in enumerate(badges):
    bax.add_patch(FancyBboxPatch((.01+i*.165, .12), .155, .76,
                  boxstyle='round,pad=0.02', fc=WHITE, ec=GOLD,
                  lw=.8, alpha=0.18, transform=bax.transAxes))
    t(bax, .09+i*.165, .5, lbl, ha='center', va='center',
      fontsize=7.8, color=col, fontweight='bold')

# ═══════════════════════════════════════════════════════════════════════════
# 4 · DASHBOARD MODULES
# ═══════════════════════════════════════════════════════════════════════════
s2ax = make_ax(.3, 19.2, FW-.6, .65, facecolor=CREAM, zorder=5)
t(s2ax, .5, .72, 'Dashboard Analytics Modules', ha='center', va='center',
  fontsize=13, fontweight='bold', color=NAVY)
s2ax.axhline(.18, color=GOLD, lw=2.5, xmin=.08, xmax=.92)

ncols, col_w, col_h = 4, (FW-.6)/4, 2.1
for idx, (title, icon, desc) in enumerate(MODULES):
    col = idx % ncols
    row = idx // ncols
    mx = .3 + col * col_w
    my = 19.2 - (row+1)*(col_h+.08)
    max_ = make_ax(mx, my, col_w*.97, col_h, facecolor=WHITE, zorder=5)
    max_.add_patch(FancyBboxPatch((0,0), 1, 1, boxstyle='round,pad=0.01',
                   fc='none', ec=LGREY, lw=1, transform=max_.transAxes))
    max_.add_patch(FancyBboxPatch((0,.82), 1, .18, boxstyle='square,pad=0',
                   fc=NAVY, ec='none', transform=max_.transAxes))
    t(max_, .5, .91, f'{icon}  {title}', ha='center', va='center',
      fontsize=8.5, fontweight='bold', color=WHITE)
    t(max_, .5, .45, desc, ha='center', va='center',
      fontsize=7.8, color=GREY, multialignment='center', linespacing=1.65)

# ═══════════════════════════════════════════════════════════════════════════
# 5 · KEY INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════
base_y = 19.2 - 2*(col_h+.08) - .1
s3ax = make_ax(.3, base_y-.65, FW-.6, .65, facecolor=CREAM, zorder=5)
t(s3ax, .5, .72, 'Key Analytical Findings  (Opta Data — No Synthetic Values)',
  ha='center', va='center', fontsize=13, fontweight='bold', color=NAVY)
s3ax.axhline(.18, color=GOLD, lw=2.5, xmin=.08, xmax=.92)

ins_top = base_y - .65
ins_h   = ins_top - 2.4

# ── LEFT: Top performers table ─────────────────────────────────────────────
tax = make_ax(.3, 2.4, 10.0, ins_h, facecolor=WHITE, zorder=5)
tax.add_patch(FancyBboxPatch((0,0), 1, 1, boxstyle='round,pad=0.01',
              fc='none', ec=LGREY, lw=1.2, transform=tax.transAxes))
tax.add_patch(FancyBboxPatch((0,.94), 1, .06, boxstyle='square,pad=0',
              fc=NAVY, ec='none', transform=tax.transAxes))
t(tax, .5, .97, 'LaLiga 2025–26 — Top Performers', ha='center', va='center',
  fontsize=9.5, fontweight='bold', color=WHITE)

hdrs = ['Player','Pos','G','Ast','MP','xG','Shots']
hxs  = [.03,.31,.43,.52,.61,.73,.85]
for hx_, h in zip(hxs, hdrs):
    t(tax, hx_, .91, h, ha='left', va='center', fontsize=8, fontweight='bold', color=NAVY)
tax.axhline(.895, color=GOLD, lw=1.8, xmin=.01, xmax=.99)

row_h = .145
for i,(nm,pos,g,ast,mp,xg,sh) in enumerate(TOP_PLAYERS):
    y = .84 - i*row_h
    bg_col = GOLD_L if i%2==0 else WHITE
    tax.add_patch(FancyBboxPatch((0.005, y-.09), .99, row_h-.01,
                  boxstyle='square,pad=0', fc=bg_col, ec='none', transform=tax.transAxes))
    vals  = [nm,   pos, str(g),   str(ast), str(mp), f'{xg:.2f}', str(sh)]
    cols_ = [NAVY, GREY, GREEN if g>=10 else BLUE, BLUE, GREY, RED, GREY]
    wts   = ['bold','normal','bold','normal','normal','normal','normal']
    for hx_, v, c, w in zip(hxs, vals, cols_, wts):
        t(tax, hx_, y-.025, v, ha='left', va='center',
          fontsize=8.5, color=c, fontweight=w)

# ── MIDDLE: Goals vs xG bar chart ──────────────────────────────────────────
gax = fig.add_axes([10.55/FW, 2.4/FH, 5.5/FW, ins_h/FH], zorder=5)
gax.set_facecolor(WHITE)
for sp in gax.spines.values(): sp.set_color(LGREY); sp.set_linewidth(.8)
names = [p[0].split()[-1] for p in TOP_PLAYERS]
gy = np.arange(len(names))
gax.barh(gy+.18, [p[2] for p in TOP_PLAYERS], .32, color=GREEN, alpha=.85, label='Goals')
gax.barh(gy-.18, [p[5] for p in TOP_PLAYERS], .32, color=RED,   alpha=.65, label='xG')
gax.set_yticks(gy); gax.set_yticklabels(names, fontsize=8.5, color=NAVY)
gax.tick_params(axis='x', labelsize=8, colors=NAVY)
gax.set_title('Goals vs xG — Top Scorers', fontsize=9.5, fontweight='bold', color=NAVY, pad=6)
gax.legend(fontsize=8, loc='lower right', framealpha=.9)
gax.set_xlim(0, 29); gax.set_xlabel('Value', fontsize=8, color=NAVY)
gax.grid(axis='x', color=LGREY, lw=.5, alpha=.7)
for label in gax.get_xticklabels()+gax.get_yticklabels(): label.set_color(NAVY)

# Add goal numbers
for i,(p_) in enumerate(TOP_PLAYERS):
    gax.text(p_[2]+.3, i+.18, str(p_[2]), va='center', fontsize=7.5, color=GREEN, fontweight='bold')
    gax.text(p_[5]+.3, i-.18, f'{p_[5]:.1f}', va='center', fontsize=7.5, color=RED)

# ── RIGHT: Tactical insights panel ─────────────────────────────────────────
pax = make_ax(16.3, 2.4, 5.4, ins_h, facecolor=WHITE, zorder=5)
pax.add_patch(FancyBboxPatch((0,0), 1, 1, boxstyle='round,pad=0.01',
              fc='none', ec=LGREY, lw=1.2, transform=pax.transAxes))
pax.add_patch(FancyBboxPatch((0,.94), 1, .06, boxstyle='square,pad=0',
              fc=NAVY, ec='none', transform=pax.transAxes))
t(pax, .5, .97, 'Pressing & Tactical Metrics', ha='center', va='center',
  fontsize=9.5, fontweight='bold', color=WHITE)

insights = [
    ('Avg PPDA (LaLiga)',     '9.48',  AMBER,  'Moderate pressing intensity'),
    ('Best PPDA (match)',     '3.32',  GREEN,  'Elite high-press — best match'),
    ('Worst PPDA (match)',   '22.64',  RED,    'Low-block, passive shape'),
    ('xG Diff. (LaLiga)',   '+27.44',  GREEN,  'Clinical attacking efficiency'),
    ('Avg Possession (LL)',  '58.8%',  BLUE,   'Above-average ball control'),
    ('Pass Acc. (LaLiga)',   '87.7%',  BLUE,   'Possession-dominant style'),
    ('Pass Acc. (UCL)',      '87.2%',  BLUE,   'Consistent across comps'),
    ('Shots on Target %',   '45.8%',  BLUE,   '297 of 649 shots on target'),
    ('Goals / xG ratio',     '1.09',  GREEN,  'Slight overperformance vs xG'),
]
pax.axhline(.91, color=GOLD, lw=1.5, xmin=.02, xmax=.98)
step = .86 / len(insights)
for i,(lbl,val,col,note) in enumerate(insights):
    y = .885 - i*step
    t(pax, .03, y, lbl,  ha='left',   va='center', fontsize=7.8, color=GREY)
    t(pax, .52, y, val,  ha='center', va='center', fontsize=9.5, color=col, fontweight='bold')
    t(pax, .97, y, note, ha='right',  va='center', fontsize=7,   color=GREY, fontstyle='italic')
    if i < len(insights)-1:
        pax.axhline(y-step*.35, color=LGREY, lw=.4, xmin=.02, xmax=.98)

# ═══════════════════════════════════════════════════════════════════════════
# 6 · TECH PIPELINE
# ═══════════════════════════════════════════════════════════════════════════
s4ax = make_ax(.3, 1.65, FW-.6, .65, facecolor=CREAM, zorder=5)
t(s4ax, .5, .72, 'Technical Architecture & Data Pipeline',
  ha='center', va='center', fontsize=13, fontweight='bold', color=NAVY)
s4ax.axhline(.18, color=GOLD, lw=2.5, xmin=.08, xmax=.92)

tpax = make_ax(.3, .75, FW-.6, .82, facecolor=NAVY, zorder=5)
pipeline = [
    ('Opta JSON\nMatch Files', '#3b82f6'),
    ('data_loader.py\n(Parse & aggregate)', NAVY),
    ('Analytics Modules\n(match · player · tactical)', NAVY),
    ('Streamlit UI\nstreamlit_app.py', '#2563eb'),
    ('Report Export\nPDF / DOCX', GOLD_D),
]
bw = .16; gap = (1-len(pipeline)*bw)/(len(pipeline)+1)
for i,(lbl,col) in enumerate(pipeline):
    bx = gap+i*(bw+gap)
    tpax.add_patch(FancyBboxPatch((bx,.12), bw, .76,
                   boxstyle='round,pad=0.02', fc=col, ec=GOLD if col==NAVY else 'none',
                   lw=.8, transform=tpax.transAxes, alpha=.92))
    t(tpax, bx+bw/2, .5, lbl, ha='center', va='center',
      fontsize=7.5, color=WHITE, fontweight='bold', multialignment='center')
    if i < len(pipeline)-1:
        t(tpax, bx+bw+gap/2, .5, '→', ha='center', va='center',
          fontsize=14, color=GOLD, fontweight='bold')
t(tpax, .5, .95, '108 clean match files  ·  3 competitions  ·  2025–2026 season  ·  event-level Opta data',
  ha='center', va='center', fontsize=7.5, color='#94a3b8', fontstyle='italic')

# ── Tech badge row ──────────────────────────────────────────────────────────
tbadges = [('Python 3.11', GREEN), ('Streamlit ≥1.31', BLUE), ('Plotly 5.18', '#7c3aed'),
           ('Pandas / NumPy', '#0ea5e9'), ('Opta Stats Perform', GOLD_D), ('ReportLab / docx', RED)]
for i,(bn,bc) in enumerate(tbadges):
    tpax.add_patch(FancyBboxPatch((.005+i/6, .01), 1/6-.01, .1,
                   boxstyle='round,pad=0.01', fc=bc, ec='none', alpha=.85,
                   transform=tpax.transAxes))
    t(tpax, .005+i/6+.08+.005, .06, bn, ha='center', va='center',
      fontsize=7, color=WHITE, fontweight='bold')

# ═══════════════════════════════════════════════════════════════════════════
# 7 · FOOTER
# ═══════════════════════════════════════════════════════════════════════════
fax = make_ax(0, 0, FW, .7, facecolor=NAVY2, zorder=10)
fax.axhline(1, color=GOLD, lw=3)
t(fax, .5, .72, 'Real Madrid CF Tactical & Player Performance Analytics',
  ha='center', va='center', fontsize=10, fontweight='bold', color=WHITE)
t(fax, .5, .38,
  "Sudhir Dahiya  •  Master's in Sports Analytics (2025–2026)  •  "
  "Escuela Universitaria Real Madrid — Universidad Europea",
  ha='center', va='center', fontsize=8, color=GOLD)
t(fax, .5, .08,
  'Data: Opta Stats Perform  •  github.com/coachsudhir/-FINAL_MASTER_PROJECT-REALMADRID-',
  ha='center', va='center', fontsize=7.5, color='#64748b')

# ═══════════════════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════════════════
out = Path(__file__).parent / 'poster.png'
plt.savefig(out, dpi=DPI, bbox_inches='tight', facecolor=CREAM, edgecolor='none')
plt.close()
print(f'Saved → {out}  ({out.stat().st_size//1024} KB)')
