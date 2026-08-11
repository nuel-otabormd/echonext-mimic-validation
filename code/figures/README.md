# Figures

Drawn from the CSVs in `results/figure_data/`, which are written by `code/export_figure_data.py`.
Computing the plotted quantities in Python and drawing them separately means a figure and a table
cannot disagree: both derive from the same predictions and the same label source, and figures can be
redrawn without repeating inference.

Run from anywhere:

```bash
python code/export_figure_data.py
for f in code/figures/fig*.R; do Rscript "$f"; done
for f in code/figures/fig*.py code/figures/build_graphical_abstract.py; do python "$f"; done
```

R needs `ggplot2`, `patchwork`, `dplyr`, `readr`, `scales` and `ggrepel`. Python needs `matplotlib`
and `pandas`.

| Script | Output | Size |
|---|---|---|
| `fig2_roc.R` | Figure 2, receiver operating characteristic curves | 9.0 x 9.6 cm |
| `fig3_reliability.py` | Figure 3, reliability curves, four labels, before and after correction | 17.0 x 13.0 cm |
| `fig4_utility.R` | Figure 4, decision curve and cumulative diagnostic yield | 12.0 x 17.0 cm |
| `figS1_reliability_all.py` | Supplementary Figure S1, remaining component labels | 18.0 x 11.2 cm |
| `figS2_acquisition.R` | Supplementary Figure S2, performance by acquisition setting | 16.0 x 10.0 cm |
| `figS3_output_bias.py` | Supplementary Figure S3, final-layer bias against training prevalence | 17.0 x 8.3 cm |
| `build_graphical_abstract.py` | Graphical abstract | 18.0 x 11.0 cm |

Figure 1, the cohort flow diagram, is drawn separately from the counts in
`results/figure_data/cohort_flow.csv` together with the exclusion counts reported by the cohort SQL.

Each script writes a vector PDF and a 600 dpi PNG. **The PDF is the file to submit**: it is
resolution independent, and vector formats are preferred for charts. The PNG is for previewing and
for embedding in the manuscript and supplement.

## Why two drawing engines

`theme.R` holds the style for the R figures and `mpl_house.py` mirrors it for the Python ones, so
the two agree on every colour, type size and line weight. Figure 3, two supplementary figures and
the graphical abstract are drawn in matplotlib because of two limitations of R's base PDF device,
both of which fail silently.

It cannot represent the `>=` and `<=` glyphs. It substitutes three ASCII periods without warning, so
a panel titled `Elevated PASP >=45 mmHg` is written into the vector file as `Elevated PASP ...45
mmHg`. The PNG is drawn by a different device and looks correct, so the corruption is invisible
unless the PDF itself is opened. Figure 3 was ported for this reason alone: its `Reduced LVEF
(<=45%)` panel sat beside the three thresholds in Supplementary Figure S1 and read as a
typographic error. Its construction is otherwise unchanged.

It also names the base-14 Helvetica rather than embedding a subset, which journal production systems
flag. `cairo_pdf` would embed but fails to load on this build for want of X11, so `save_fig()` in
`theme.R` passes each PDF through `embedFonts()` instead. That needs **ghostscript** on the path
(`brew install ghostscript`); without it the figure is still written and the script says so rather
than passing silently. Note that `embedFonts()` does not pass `-dEmbedAllFonts` on its own and
ghostscript's `pdfwrite` leaves the base-14 fonts as references by default, so `save_fig()` supplies
that option explicitly. Omitting it produces a call that succeeds, rewrites the file and embeds
nothing. The matplotlib figures embed an Arial subset directly and need no post-processing.

All eight figures embed their fonts. To check after any change:

```bash
python - <<'EOF'
from pypdf import PdfReader; import glob
for f in sorted(glob.glob('results/figures/*.pdf')):
    r=PdfReader(f); ok=[]
    for p in r.pages:
        for v in (p.get('/Resources',{}).get_object().get('/Font',{}) or {}).values():
            d=v.get_object(); ds=[d.get('/FontDescriptor')]+[x.get_object().get('/FontDescriptor')
                                                             for x in (d.get('/DescendantFonts') or [])]
            ok.append(any(k in y.get_object() for y in ds if y is not None
                          for k in ('/FontFile','/FontFile2','/FontFile3')))
    print(f, 'EMBEDDED' if ok and all(ok) else 'NOT EMBEDDED')
EOF
```

Arial, not Helvetica: macOS ships Helvetica as a `.ttc` whose bold face matplotlib does not index,
so a request for bold silently returns the regular face and bold panel titles come out at normal
weight. Arial carries a true bold, is metrically compatible, and exists off the Mac.
`mpl_house.use_house_style()` raises rather than continuing if the resolved family has no true bold.

## Two R implementation notes

Both fail silently rather than loudly and so are worth knowing. The base PDF device is used rather
than `cairo_pdf`, for the reason above: cairo reports as available on some builds but fails to load
and then writes no file at all. And R encodes spaces in the `--file=` argument as `~+~`, so the
scripts decode that before resolving their own directory; without it they cannot find `theme.R` when
the repository sits under a path containing a space.
