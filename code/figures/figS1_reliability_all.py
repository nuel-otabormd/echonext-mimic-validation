"""Supplementary Figure S1. Reliability curves for the remaining component labels.

Figure 3 carries the composite and three representative components on linear axes, where their
prevalences of 5% to 47% are all legible. The eight labels here span 0.6% to 22.4%, a forty-fold
range, and on a linear axis the rare ones collapse onto the bottom edge: an earlier draft of this
figure gave pericardial effusion a vertical axis reading 0%, 0%, 1%, 2%, 2%, because rounding to
whole percentage points is all a linear axis can offer at a prevalence of 0.6%.

Logarithmic axes shared across all eight panels fix that and buy something else. Over-prediction by
a constant factor is a constant vertical offset on log axes, so the near-parallel displacement of
the released curve from the identity line is the multiplicative over-prediction the paper reports,
read directly off the figure rather than inferred from it.

Nothing is hidden by the log transform: no bin has an observed frequency of zero, so no point is
dropped. The script checks this rather than assuming it.

Reads results/figure_data/reliability.csv only, so the figure rebuilds from a clean clone.
Output: results/figures/figureS1_reliability_all.{pdf,png} at 18.0 x 11.2 cm.
"""
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, NullLocator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mpl_house import (ANNOT, AXTITLE, CM, DASH_REF, DOT_REF, LEG, LW_LINE, LW_REF, PRIMARY, REF,
                       SECOND, STRIP, SUBT, TITLE, save_fig, style_axes, use_house_style)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "results", "figure_data")
OUT = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT, exist_ok=True)

use_house_style()

# The four labels carried in Figure 3; this figure holds the remainder.
IN_FIGURE_3 = ["Structural heart disease", "Reduced LVEF (<=45%)", "RV dysfunction",
               "Aortic stenosis"]

# The stored labels spell the thresholds in ASCII. Typeset them properly here.
SHORT = {
    "LV wall thickness (>=1.3 cm)": "LV wall thickness ≥1.3 cm",
    "Elevated PASP (>=45 mmHg)": "Elevated PASP ≥45 mmHg",
    "Elevated TR Vmax (>=3.2 m/s)": "Elevated TR Vmax ≥3.2 m/s",
}

rel = pd.read_csv(os.path.join(DATA, "reliability.csv"))

if (rel.observed <= 0).any():
    raise RuntimeError("a bin has observed frequency <= 0 and would vanish on a log axis")

# Observed prevalence is recovered from the same file the curves are drawn from, weighting each bin
# by its size, rather than read from a second source that could disagree with it.
prev = (rel[rel.variant == "As released"]
        .groupby("label")
        .apply(lambda d: (d.n * d.observed).sum() / d.n.sum(), include_groups=False))

d = rel[~rel.label.isin(IN_FIGURE_3)]
order = [lab for lab in prev.loc[sorted(d.label.unique())].sort_values().index]

LO, HI = 1e-4, 1.0
TICKS = [1e-3, 1e-2, 1e-1, 1.0]
TICKLAB = ["0.1%", "1%", "10%", "100%"]

# The panels are square, so their height follows from the figure width and cannot be stretched. The
# figure height is set to what those eight squares plus the axis label and legend actually need;
# leaving it taller centres each square in an over-tall cell and opens a band of white between rows.
FIG_W, FIG_H = 18.0, 11.2
fig, axes = plt.subplots(2, 4, figsize=(FIG_W * CM, FIG_H * CM), sharex=True, sharey=True)
fig.subplots_adjust(left=0.076, right=0.982, top=0.950, bottom=0.180, wspace=0.11, hspace=0.30)

for ax, lab in zip(axes.ravel(), order):
    sub = d[d.label == lab]
    style_axes(ax)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(LO, HI)
    ax.set_ylim(LO, HI)
    ax.set_aspect("equal", adjustable="box")

    ax.plot([LO, HI], [LO, HI], ls=DASH_REF, lw=LW_REF, color=REF, zorder=2)
    ax.axhline(prev[lab], color=REF, lw=LW_REF, ls=DOT_REF, zorder=2)

    for variant, colour in [("As released", SECOND), ("After prior shift", PRIMARY)]:
        s = sub[sub.variant == variant].sort_values("predicted")
        ax.plot(s.predicted, s.observed, color=colour, lw=LW_LINE, solid_capstyle="round", zorder=3)
        ax.scatter(s.predicted, s.observed, s=6.6, color=colour, zorder=4, linewidths=0)

    ax.xaxis.set_major_locator(FixedLocator(TICKS))
    ax.yaxis.set_major_locator(FixedLocator(TICKS))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_xticklabels(TICKLAB)
    ax.set_yticklabels(TICKLAB)
    ax.set_title(SHORT.get(lab, lab), fontsize=STRIP, fontweight="bold", color=AXTITLE, pad=4)
    ax.text(0.955, 0.055, f"prevalence {100 * prev[lab]:.1f}%", transform=ax.transAxes,
            fontsize=ANNOT, color=SUBT, ha="right", va="bottom")

fig.text(0.536, 0.072, "Predicted probability", ha="center", fontsize=TITLE, color=AXTITLE)
fig.text(0.006, 0.550, "Observed frequency", va="center", rotation=90, fontsize=TITLE,
         color=AXTITLE)

# theme_ehj() places the legend below the panels; Figure 3 does the same.
handles = [
    Line2D([], [], color=SECOND, lw=LW_LINE, marker="o", ms=2.6, label="As released"),
    Line2D([], [], color=PRIMARY, lw=LW_LINE, marker="o", ms=2.6, label="After prior shift"),
    Line2D([], [], color=REF, lw=LW_REF, ls=DASH_REF, label="Perfect calibration"),
    Line2D([], [], color=REF, lw=LW_REF, ls=DOT_REF, label="Observed prevalence"),
]
fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.536, 0.005), ncol=4,
           frameon=False, fontsize=LEG, handlelength=2.0, columnspacing=2.2, handletextpad=0.6)

save_fig(fig, OUT, "figureS1_reliability_all", FIG_W, FIG_H)
