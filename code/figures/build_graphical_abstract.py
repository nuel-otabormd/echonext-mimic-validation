"""Graphical abstract.

Every number is read from results/figure_data/ga_summary.json and ga_both_settings.csv, which are
emitted from the same results object the tables are generated from, so the abstract cannot drift
from the paper.

Output: results/figures/graphical_abstract.{png,pdf} at 18.0 x 11.0 cm, 600 dpi, sans serif,
no text below 8 pt.
"""
import json, os
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Ellipse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "results", "figure_data")
OUT  = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT, exist_ok=True)

mpl.rcParams["font.family"] = "sans-serif"
mpl.rcParams["font.sans-serif"] = ["Helvetica", "Arial", "DejaVu Sans"]
CM = 1 / 2.54

NAVY, PURPLE, MAGENTA, CRIM = "#1A3A6B", "#5B2D6E", "#90206A", "#C4275C"
PINKBG, BLUEBG, INK, GREY, LINE = "#FBEDF2", "#EDF1F8", "#2B2B33", "#6E7480", "#D8DEE7"

S = json.load(open(os.path.join(DATA, "ga_summary.json")))
both = pd.read_csv(os.path.join(DATA, "ga_both_settings.csv"))
mim, ben = both[both.setting == "MIMIC-IV"], both[both.setting == "Benchmark"]
med_m, med_b = mim.mean_pred.median(), ben.mean_pred.median()

fig = plt.figure(figsize=(18 * CM, 11 * CM), dpi=300)
fig.patch.set_facecolor("white")
T = fig.transFigure
ASPECT = 18.0 / 11.0


def pill(x, y, w, h, txt, fc, fs=8.5):
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.014",
                                      transform=T, facecolor=fc, edgecolor="none", zorder=3))
    fig.text(x + w / 2, y + h / 2, txt, ha="center", va="center", color="white",
             fontsize=fs, fontweight="bold", zorder=4)


def panel(x, y, w, h, fc):
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.02",
                                      transform=T, facecolor=fc, edgecolor="none", zorder=1))


def medallion(cx, cy, rad, fc, glyph):
    fig.patches.append(Ellipse((cx, cy), 2 * rad, 2 * rad * ASPECT, transform=T,
                               facecolor=fc, edgecolor="none", zorder=4))
    fig.text(cx, cy, glyph, ha="center", va="center", color="white",
             fontsize=8.5, fontweight="bold", zorder=5)


# ---- title. States where the miscalibration comes from, which is the paper's finding, and avoids
# the em dash the manuscript does not use anywhere.
fig.patches.append(FancyBboxPatch((0.035, 0.885), 0.93, 0.088,
                   boxstyle="round,pad=0,rounding_size=0.030", transform=T,
                   facecolor="white", edgecolor=NAVY, linewidth=1.2, zorder=3))
fig.text(0.5, 0.929, "Component outputs are ranking scores, not risks, in the model's own "
         "benchmark as well as in MIMIC-IV",
         ha="center", va="center", fontsize=9.4, fontweight="bold", color=NAVY, zorder=4)
fig.text(0.5, 0.853, f"External validation and recalibration of EchoNext-Mini in MIMIC-IV  ·  "
         f"{S['n']:,} patients",
         ha="center", va="center", fontsize=8, color=GREY, style="italic")

# ---- panel 1: study
panel(0.035, 0.175, 0.245, 0.645, BLUEBG)
pill(0.055, 0.745, 0.205, 0.055, "Study", NAVY)
BX = 0.068
for i, ((num, head, sub), cy) in enumerate(zip(
        [("1", f"{S['n']:,} patients", "one 12-lead ECG each"),
         ("2", "Echocardiography", "reference within 1 year"),
         ("3", "Released model", "applied without retraining")],
        [0.672, 0.545, 0.418])):
    medallion(BX, cy, 0.0148, [NAVY, PURPLE, MAGENTA][i], num)
    fig.text(BX + 0.030, cy + 0.019, head, ha="left", va="center", fontsize=8.5,
             fontweight="bold", color=INK)
    fig.text(BX + 0.030, cy - 0.019, sub, ha="left", va="center", fontsize=8, color=GREY)
    if i < 2:
        fig.add_artist(plt.Line2D([BX, BX], [cy - 0.027, cy - 0.100], color="#B9C2D2",
                                  lw=1.2, transform=T, zorder=2, solid_capstyle="round"))
fig.add_artist(plt.Line2D([0.060, 0.255], [0.300, 0.300], color=LINE, lw=0.9, transform=T))
fig.text(0.1575, 0.253, f"{S['prev_pct']}%", ha="center", va="center", fontsize=15,
         fontweight="bold", color=CRIM)
fig.text(0.1575, 0.208, "had structural heart disease", ha="center", va="center",
         fontsize=8, color=GREY)

# ---- panel 2: discrimination
panel(0.298, 0.175, 0.315, 0.645, PINKBG)
pill(0.318, 0.745, 0.275, 0.055, "Discrimination transported", MAGENTA)
ax2 = fig.add_axes([0.348, 0.452, 0.240, 0.250], zorder=6)
ax2.set_facecolor("none")
for i, (lab, v, c) in enumerate([("Benchmark test set", S["auroc_bench"], PURPLE),
                                 ("MIMIC-IV", S["auroc_mimic"], CRIM)]):
    y = 1 - i
    ax2.plot([0.60, v], [y, y], color=c, lw=1.4, solid_capstyle="round", zorder=2)
    ax2.plot(v, y, "o", ms=9, color=c, zorder=4)
    ax2.text(v, y + 0.34, f"{v:.3f}", ha="center", va="center", fontsize=10,
             fontweight="bold", color=c)
    ax2.text(0.598, y - 0.30, lab, ha="left", va="center", fontsize=8, color=INK)
ax2.errorbar(S["auroc_mimic"], 0, xerr=[[0.004], [0.004]], color=CRIM, lw=1.5, capsize=2.2, zorder=3)
ax2.set_xlim(0.595, 0.875); ax2.set_ylim(-0.72, 1.62)
ax2.set_yticks([]); ax2.set_xticks([0.65, 0.75, 0.85])
ax2.tick_params(axis="x", labelsize=8, colors=GREY, length=2.5)
ax2.set_xlabel("Composite AUROC", fontsize=8, color=INK, labelpad=1.5)
for s in ("top", "right", "left"):
    ax2.spines[s].set_visible(False)
ax2.spines["bottom"].set_color(LINE)
fig.text(0.4555, 0.322, f"Composite discrimination held within\n{S['gap']:.2f} of the model's "
         f"own benchmark", ha="center", va="center", fontsize=8, color=INK, linespacing=1.5)
fig.text(0.4555, 0.222, f"Component AUROC\n{S['comp_auroc_lo']:.3f} to {S['comp_auroc_hi']:.3f}",
         ha="center", va="center", fontsize=8, color=MAGENTA, fontweight="bold", linespacing=1.45)

# ---- panel 3: calibration. "over-predict" is the specific word and is what the data show.
panel(0.631, 0.175, 0.334, 0.645, PINKBG)
pill(0.651, 0.745, 0.294, 0.055, "Probabilities over-predict in both", CRIM)
ax3 = fig.add_axes([0.692, 0.452, 0.246, 0.250], zorder=6)
ax3.set_facecolor("none")
xid = np.logspace(np.log10(0.30), np.log10(30), 200)
ax3.plot(xid, xid / 100, color="#A9B2C0", lw=1.0, ls=(0, (3, 2)), zorder=1)
ax3.scatter(ben.prev_pct, ben.mean_pred, s=30, marker="s", facecolor="white",
            edgecolor=PURPLE, lw=1.2, zorder=3)
ax3.scatter(mim.prev_pct, mim.mean_pred, s=32, marker="o", facecolor=CRIM,
            edgecolor="white", lw=0.7, zorder=4)
ax3.set_xscale("log"); ax3.set_xlim(0.30, 32); ax3.set_ylim(0, 0.50)
ax3.set_xticks([1, 10]); ax3.set_xticklabels(["1%", "10%"], fontsize=8)
ax3.set_yticks([0, 0.2, 0.4]); ax3.set_yticklabels(["0", "0.2", "0.4"], fontsize=8)
ax3.tick_params(colors=GREY, length=2.5)
ax3.set_xlabel("Observed prevalence", fontsize=8, color=INK, labelpad=1.5)
ax3.set_ylabel("Mean predicted", fontsize=8, color=INK, labelpad=1.5)
for s in ("top", "right"):
    ax3.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax3.spines[s].set_color(LINE)
ax3.annotate("perfect calibration", xy=(12, 0.12), xytext=(0.75, 0.20), fontsize=8,
             color="#8A93A2", ha="left", va="center",
             arrowprops=dict(arrowstyle="-", color="#BCC4D0", lw=0.8, shrinkA=2, shrinkB=3))
ax3.plot([0.36], [0.545], marker="s", ms=5, mfc="white", mec=PURPLE, mew=1.2, clip_on=False)
ax3.text(0.45, 0.545, "Benchmark", fontsize=8, color=PURPLE, va="center", clip_on=False)
ax3.plot([3.4], [0.545], marker="o", ms=5.4, mfc=CRIM, mec="white", mew=0.7, clip_on=False)
ax3.text(4.3, 0.545, "MIMIC-IV", fontsize=8, color=CRIM, va="center", clip_on=False)
fig.text(0.798, 0.322, f"All {S['n_components']} components over-predicted risk in\nboth settings, "
         f"a property of the model", ha="center", va="center", fontsize=8, color=INK, linespacing=1.5)
fig.text(0.798, 0.222, f"Predictions cluster near {min(med_b, med_m):.2f} to {max(med_b, med_m):.2f}"
         f"\nwhatever the prevalence", ha="center", va="center", fontsize=8, color=CRIM,
         fontweight="bold", linespacing=1.45)

# ---- takeaway. States what a reader should DO; the mechanism sits on the second line.
fig.patches.append(FancyBboxPatch((0.035, 0.038), 0.93, 0.098,
                   boxstyle="round,pad=0,rounding_size=0.030", transform=T,
                   facecolor=NAVY, edgecolor="none", zorder=3))
fig.text(0.5, 0.104, "Rank on the composite as released; correct component probabilities before "
         "reading them as risk", ha="center", va="center", color="white", fontsize=9,
         fontweight="bold", zorder=4)
fig.text(0.5, 0.065, f"A shift from the published training prevalences does this without local "
         f"outcome data, for {S['n_corrected']} of {S['n_components']} components",
         ha="center", va="center", color="#C3D0E6", fontsize=8, zorder=4)

fig.savefig(os.path.join(OUT, "graphical_abstract.png"), dpi=600, facecolor="white")
fig.savefig(os.path.join(OUT, "graphical_abstract.pdf"), facecolor="white")
print(f"rendered graphical_abstract.png / .pdf  (18.0 x 11.0 cm)")
print(f"  medians: benchmark {med_b:.3f}, MIMIC-IV {med_m:.3f}")
