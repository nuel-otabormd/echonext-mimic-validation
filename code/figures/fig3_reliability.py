"""Figure 3. Reliability curves for the composite and three representative components.

Ported from R for one reason: R's base PDF device cannot represent the <= glyph and substitutes
three ASCII periods without warning, so this panel could only be titled "Reduced LVEF (<=45%)". Set
beside Supplementary Figure S1, which carries three thresholds and is drawn here, that reads as a
typographic error rather than a deliberate choice. The construction is otherwise unchanged from the
R version: linear axes, free per-panel scaling, same colours, weights and type sizes.

The axes stay linear where Supplementary Figure S1 is logarithmic, and the difference is not
arbitrary. These four labels have observed prevalences of 5.1% to 47.2%, all legible against a
linear axis. The eight in S1 span 0.6% to 22.4%, and below about 2% a linear axis cannot resolve the
curve from the horizontal at all.

Reads results/figure_data/reliability.csv only, so the figure rebuilds from a clean clone.
Output: results/figures/figure3_reliability.{pdf,png} at 17.0 x 13.0 cm.
"""
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, PercentFormatter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mpl_house import (AXTITLE, CM, DASH_REF, LEG, LW_REF, PRIMARY, REF, SECOND, STRIP, TITLE,
                       save_fig, style_axes, use_house_style)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "results", "figure_data")
OUT = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT, exist_ok=True)

use_house_style()

KEEP = ["Structural heart disease", "Reduced LVEF (<=45%)", "RV dysfunction", "Aortic stenosis"]
SHORT = {"Reduced LVEF (<=45%)": "Reduced LVEF ≤45%"}

# geom_line(linewidth = 0.5) and geom_point(size = 1.1) in the R original; ggplot linewidth is in
# millimetres, so 0.5 mm is 1.07 pt. Point size is an area in ggplot and in matplotlib alike.
LW_LINE = 0.5 * 2.13
MS = 9.0

rel = pd.read_csv(os.path.join(DATA, "reliability.csv"))
d = rel[rel.label.isin(KEEP)]

FIG_W, FIG_H = 17.0, 13.0
fig, axes = plt.subplots(2, 2, figsize=(FIG_W * CM, FIG_H * CM))
fig.subplots_adjust(left=0.070, right=0.988, top=0.960, bottom=0.135, wspace=0.16, hspace=0.26)

for ax, lab in zip(axes.ravel(), KEEP):
    sub = d[d.label == lab]
    style_axes(ax)
    for variant, colour in [("As released", SECOND), ("After prior shift", PRIMARY)]:
        s = sub[sub.variant == variant].sort_values("predicted")
        ax.plot(s.predicted, s.observed, color=colour, lw=LW_LINE, solid_capstyle="round", zorder=3)
        ax.scatter(s.predicted, s.observed, s=MS, color=colour, zorder=4, linewidths=0)

    # Matplotlib's default 5% margin matches ggplot's default continuous expansion, so the panels
    # frame the data exactly as the R version did. The reference line is drawn across whichever
    # range is wider and clipped to the panel.
    ax.autoscale_view()
    lo = min(ax.get_xlim()[0], ax.get_ylim()[0])
    hi = max(ax.get_xlim()[1], ax.get_ylim()[1])
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    ax.plot([lo, hi], [lo, hi], ls=DASH_REF, lw=LW_REF, color=REF, zorder=2)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(MaxNLocator(nbins=5, steps=[1, 2, 2.5, 5, 10]))
        axis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax.set_title(SHORT.get(lab, lab), fontsize=STRIP, fontweight="bold", color=AXTITLE, pad=4)

fig.text(0.529, 0.062, "Predicted probability", ha="center", fontsize=TITLE, color=AXTITLE)
fig.text(0.006, 0.548, "Observed frequency", va="center", rotation=90, fontsize=TITLE,
         color=AXTITLE)

handles = [
    Line2D([], [], color=SECOND, lw=LW_LINE, marker="o", ms=3.0, label="As released"),
    Line2D([], [], color=PRIMARY, lw=LW_LINE, marker="o", ms=3.0, label="After prior shift"),
]
fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.529, 0.004), ncol=2,
           frameon=False, fontsize=LEG, handlelength=2.0, columnspacing=2.4, handletextpad=0.6)

save_fig(fig, OUT, "figure3_reliability", FIG_W, FIG_H)
