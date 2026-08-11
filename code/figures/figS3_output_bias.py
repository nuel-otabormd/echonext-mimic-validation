"""Supplementary Figure S3. Final-layer bias of the released model against training prevalence.

A model whose outputs lie on the natural prevalence scale carries a final-layer bias approximating
the log-odds of the label's prevalence, and would fall on the identity line. Panel A shows the
biases do not: they sit at zero across training prevalences spanning 0.8% to 52%.

That argument needs both panels. Panel A must give the two axes the same range for the identity
line to be a true diagonal, which leaves the biases indistinguishable from each other and from
zero. Panel B shows the same twelve values at a scale where they can be read.

Two layout constraints drove the geometry, and neither is solved by reducing the type size.

Panel A is mostly empty below the identity line, and that is the only region with room for the
explanatory note: the grey connectors rise from the diagonal to zero, so any text placed in the
upper left crosses them. The note therefore sits in the lower right, where the connectors, which
all originate left of it, cannot reach.

Panel B carries a label and a prevalence for each of twelve rows. Setting them beside their points,
on the far side of zero, needs more width than a symmetric axis can give: the longest label is
wider than the distance from the panel edge to the zero line at any legible size. The labels are
therefore in a dedicated column, right aligned in two aligned fields, and the plotting area holds
only the points. The axes are positioned explicitly rather than through a grid, because the width
of that column is what has to be controlled.

Reads results/figure_data/output_biases.csv only, so the figure rebuilds from a clean clone.
Output: results/figures/figureS3_output_bias.{pdf,png} at 17.0 x 8.3 cm.
"""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.transforms import blended_transform_factory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mpl_house import (ANNOT, AXTEXT, AXTITLE, CM, DASH_REF, GRID, LW_GRID, LW_REF, LW_SEG, PLETTER,
                       PRIMARY, REF, SECOND, SEG, SUBT, TITLE, save_fig, style_axes,
                       use_house_style)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "results", "figure_data")
OUT = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT, exist_ok=True)

use_house_style()

d = pd.read_csv(os.path.join(DATA, "output_biases.csv")).sort_values("logit_train_prevalence")
d["short"] = d.label.str.replace(r" \(.*\)$", "", regex=True)
d["is_composite"] = d.label == "Structural heart disease"

# Panel B's heading states a bound; derive it rather than typing a number that could go stale.
BOUND = 0.05
if d.output_bias.abs().max() >= BOUND:
    raise RuntimeError(f"a bias of {d.output_bias.abs().max():.4f} exceeds the stated bound {BOUND}")

# ---- geometry, in centimetres on a 17.0 x 8.3 cm canvas ----------------------------------------
FIG_W, FIG_H = 17.0, 8.3
PLOT_B, PLOT_T = 1.45, 7.45          # shared vertical extent of both plotting boxes
A_L, A_W = 1.25, 6.00                # panel A is square, so its width equals its height
NAME_R = 11.60                       # right edge of the label column
PCT_R = 12.55                        # right edge of the prevalence column
B_L, B_W = 12.70, 3.90               # panel B holds only the points
HEAD_Y = 7.72                        # baseline of both panel headings


def fx(cm):
    return cm / FIG_W


def fy(cm):
    return cm / FIG_H


fig = plt.figure(figsize=(FIG_W * CM, FIG_H * CM))
axA = fig.add_axes([fx(A_L), fy(PLOT_B), fx(A_W), fy(PLOT_T - PLOT_B)])
axB = fig.add_axes([fx(B_L), fy(PLOT_B), fx(B_W), fy(PLOT_T - PLOT_B)])


def panel_heading(letter, text, letter_cm, text_cm):
    """Bold panel letter and a grey descriptive line, matching plot.title and plot.subtitle."""
    fig.text(fx(letter_cm), fy(HEAD_Y), letter, fontsize=PLETTER, fontweight="bold", color="black",
             va="baseline")
    fig.text(fx(text_cm), fy(HEAD_Y), text, fontsize=ANNOT, color=SUBT, va="baseline")


# ---- panel A: equal axis ranges, so the identity line is a true diagonal ------------------------
style_axes(axA)
LIM = (-5.4, 0.9)
axA.plot(LIM, LIM, ls=DASH_REF, lw=LW_REF, color=REF, zorder=2)
axA.vlines(d.logit_train_prevalence, d.logit_train_prevalence, d.output_bias,
           color=SEG, lw=LW_SEG, zorder=2)
for mask, colour in [(~d.is_composite, PRIMARY), (d.is_composite, SECOND)]:
    axA.scatter(d.logit_train_prevalence[mask], d.output_bias[mask], s=13, color=colour,
                zorder=4, linewidths=0)
axA.set_xlim(LIM)
axA.set_ylim(LIM)
axA.set_xlabel("Log-odds of label prevalence in the training split", fontsize=TITLE,
               color=AXTITLE, labelpad=3)
axA.set_ylabel("Final-layer bias of the released model", fontsize=TITLE, color=AXTITLE, labelpad=3)

# Every connector runs from the diagonal up to zero, so each one lies to the left of, and above,
# the diagonal point it starts from. Text placed below the diagonal and to the right of x = -3
# cannot be crossed by any of them.
axA.annotate("Outputs on the natural\nprevalence scale would\nlie on this line",
             xy=(-4.10, -4.10), xytext=(-3.00, -4.55), fontsize=ANNOT, color=SUBT,
             linespacing=1.30, ha="left", va="center",
             arrowprops=dict(arrowstyle="-", color=SEG, lw=LW_SEG,
                             connectionstyle="arc3,rad=-0.18", shrinkA=3, shrinkB=3))
# The leader lands on the mitral regurgitation marker rather than on bare axis between two points.
axA.annotate("Observed biases", xy=(-2.38, 0.026), xytext=(-3.70, 0.62), fontsize=ANNOT,
             color=SUBT, ha="center", va="bottom",
             arrowprops=dict(arrowstyle="-", color=SEG, lw=LW_SEG, shrinkA=2, shrinkB=3))
panel_heading("A", "Biases sit at zero, not on the prevalence line", 0.55, A_L)

# ---- panel B: the same twelve values at a readable scale ----------------------------------------
style_axes(axB)
axB.grid(False)
axB.grid(True, axis="x", which="major", color=GRID, linewidth=LW_GRID, zorder=0)
y = np.arange(len(d))[::-1]
axB.axvline(0, color=REF, lw=LW_REF, zorder=2)
axB.hlines(y, 0, d.output_bias, color=SEG, lw=LW_SEG, zorder=2)
axB.scatter(d.output_bias, y, s=13, zorder=4, linewidths=0,
            color=[SECOND if c else PRIMARY for c in d.is_composite])
axB.set_yticks(y)
axB.set_yticklabels([])
axB.tick_params(axis="y", length=0)
axB.set_xlim(-0.065, 0.065)
axB.set_ylim(-0.8, len(d) - 0.2)
axB.set_xticks([-BOUND, 0, BOUND])
axB.set_xticklabels([f"-{BOUND:g}", "0", f"{BOUND:g}"])
axB.set_xlabel("Final-layer bias", fontsize=TITLE, color=AXTITLE, labelpad=3)

# Two right-aligned fields: the name, then the prevalence. x is in figure coordinates so the column
# keeps a fixed width, y in data coordinates so each row tracks its own point.
col = blended_transform_factory(fig.transFigure, axB.transData)
for yy, name, pct in zip(y, d.short, 100 * d.train_prevalence):
    axB.text(fx(NAME_R), yy, name, transform=col, ha="right", va="center", fontsize=ANNOT,
             color=AXTEXT)
    axB.text(fx(PCT_R), yy, f"{pct:.1f}%", transform=col, ha="right", va="center", fontsize=ANNOT,
             color=AXTEXT)

panel_heading("B", f"Every bias lies within {BOUND:g} of zero", 7.30, 7.90)
# Right aligned to panel B rather than to the label column: panel A's axis title is wide enough to
# reach x = 8.6 cm, and a note ending at the column edge would run into it.
fig.text(fx(B_L + B_W), fy(0.32), "each label with its training-split prevalence",
         ha="right", fontsize=ANNOT, color=SUBT)

save_fig(fig, OUT, "figureS3_output_bias", FIG_W, FIG_H)
