"""House plotting style, mirrored from theme.R so the two engines cannot drift apart.

Most figures are drawn in R. Two supplementary figures are drawn here in matplotlib instead, for
two reasons that are properties of R's base PDF device rather than preferences:

  1. It cannot represent the >= and <= glyphs. It substitutes three ASCII periods and issues no
     warning, so a panel titled "Elevated PASP >=45 mmHg" is written into the submitted vector file
     as "Elevated PASP ...45 mmHg". The PNG is drawn by a different device and looks correct, so the
     corruption is invisible unless the PDF itself is opened.
  2. It references the base-14 Helvetica rather than embedding a subset. cairo_pdf would embed, but
     cairo fails to load on this build (no X11), and ghostscript, which embedFonts() shells out to,
     is not installed. matplotlib embeds a subset directly.

Every constant below is derived from theme.R. Where theme_minimal applies a relative size the
arithmetic is shown, so a reader can check the two files agree without running either.
"""
import matplotlib as mpl
from matplotlib import font_manager

CM = 1 / 2.54

# ---- typography -------------------------------------------------------------------------------
# theme.R sets BASE_PT <- 9 and builds on theme_minimal(base_size = 9).
BASE_PT = 9
TICK = BASE_PT * 0.8   # 7.2 pt. theme_minimal sizes axis.text at rel(0.8) of base.
TITLE = BASE_PT        # 9 pt.   axis.title inherits base.
STRIP = BASE_PT        # 9 pt bold. strip.text is set explicitly to base_size, face = "bold".
ANNOT = BASE_PT - 1    # 8 pt.   theme.R defines ANNOT as 8 pt for in-panel geom_text.
LEG = BASE_PT - 1      # 8 pt.   legend.text = base_size - 1.
SUBT_PT = BASE_PT - 1  # 8 pt.   plot.subtitle = base_size - 1.
PLETTER = BASE_PT + 1  # 10 pt bold. plot.title = base_size + 1, face = "bold".

# ---- colour -----------------------------------------------------------------------------------
# PAL[1] and PAL[2] verbatim from theme.R. The greys are R's greyNN, which is round(NN/100 * 255).
PRIMARY = "#1b4965"   # PAL[1], the corrected variant
SECOND = "#c1666b"    # PAL[2], the released variant
REF = "#8C8C8C"       # grey55, reserved in theme.R for reference lines
GRID = "#EBEBEB"      # grey92, panel.grid.major
BORDER = "#4D4D4D"    # grey30, panel.border
AXTITLE = "#333333"   # grey20, axis.title
AXTEXT = "#4D4D4D"    # grey30, axis.text
SUBT = "#595959"      # grey35, plot.subtitle
SEG = "#CCCCCC"       # grey80, the connector segments used in figS3

# ---- line weights -----------------------------------------------------------------------------
# ggplot linewidth is in millimetres; points = mm * 2.845.
LW_GRID = 0.3 * 2.13    # 0.64 pt, panel.grid.major linewidth 0.3
LW_BORDER = 0.4 * 2.13  # 0.85 pt, panel.border linewidth 0.4
LW_REF = 0.35 * 2.13    # 0.75 pt, the dashed identity line
LW_LINE = 0.45 * 2.13   # 0.96 pt, geom_line in the supplementary reliability figure
LW_SEG = 0.3 * 2.13     # 0.64 pt, connector segments

DASH_REF = (0, (4, 3))   # ggplot linetype = "dashed"
DOT_REF = (0, (1, 2))    # ggplot linetype = "dotted"


# Arial leads rather than Helvetica, and the reason is specific. macOS ships Helvetica as a .ttc
# whose bold face matplotlib does not index, so a request for bold silently returns the regular
# face: panel titles that theme.R makes bold would render at normal weight and nothing would warn.
# Arial carries a true 700 face, is metrically compatible with Helvetica, and is available off the
# Mac, where Helvetica is not. Liberation Sans is the metric clone used on Linux.
FAMILIES = ["Arial", "Liberation Sans", "Helvetica Neue", "Helvetica", "DejaVu Sans"]


def use_house_style():
    """Apply the shared rcParams, then confirm the resolved family really has a bold face.

    matplotlib falls back silently in two ways: to DejaVu Sans when no requested family exists, and
    to the regular face when the resolved family has no bold. Both would break the match with the
    R-drawn figures without raising anything, so both are checked here rather than assumed.
    """
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": FAMILIES,
        "pdf.fonttype": 42,     # embed a TrueType subset rather than reference a base-14 name
        "svg.fonttype": "none",
        "axes.unicode_minus": False,  # ASCII hyphen on negative ticks, as R's device writes
    })
    # The family is passed as the explicit list: FontProperties reads a bare "sans-serif" as a
    # fontconfig pattern and fails on the hyphen.
    faces = {w: font_manager.findfont(font_manager.FontProperties(family=FAMILIES, weight=w))
             for w in ("normal", "bold")}
    name = font_manager.get_font(faces["normal"]).family_name
    if name == "DejaVu Sans":
        raise RuntimeError(
            f"resolved the DejaVu fallback, so none of {FAMILIES[:-1]} is installed. The figure "
            "would not match the R-drawn set."
        )
    if faces["bold"] == faces["normal"]:
        raise RuntimeError(
            f"{name!r} resolves bold to the same file as regular ({faces['normal']}), so bold "
            "panel titles would render at normal weight. Install a family with a true bold face."
        )
    return name


def style_axes(ax):
    """Grid, ticks and border, matching theme_ehj()."""
    ax.grid(True, which="major", color=GRID, linewidth=LW_GRID, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=TICK, colors=AXTEXT, length=2.2, width=0.6, pad=2)
    for sp in ax.spines.values():
        sp.set_color(BORDER)
        sp.set_linewidth(LW_BORDER)


def save_fig(fig, out_dir, name, w_cm, h_cm):
    """Write the vector PDF and a 600 dpi PNG, as save_fig() in theme.R does."""
    import os
    pdf = os.path.join(out_dir, f"{name}.pdf")
    fig.savefig(pdf, facecolor="white")
    fig.savefig(os.path.join(out_dir, f"{name}.png"), dpi=600, facecolor="white")
    print(f"  {name + '.pdf':<28} {w_cm:.1f} x {h_cm:.1f} cm")
