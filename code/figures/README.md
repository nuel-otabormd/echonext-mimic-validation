# Figures

Drawn in R from the CSVs in `results/figure_data/`, which are written by
`code/export_figure_data.py`. Computing the plotted quantities in Python and drawing them in R means
a figure and a table cannot disagree: both derive from the same predictions and the same label
source, and figures can be redrawn without repeating inference.

Run from anywhere:

```bash
python code/export_figure_data.py          # writes results/figure_data/
for f in code/figures/fig*.R; do Rscript "$f"; done
```

Requires `ggplot2`, `patchwork`, `dplyr`, `readr`, `scales` and `ggrepel`.

| Script | Output | Size |
|---|---|---|
| `fig2_roc.R` | Figure 2, receiver operating characteristic curves | 9.0 x 9.6 cm |
| `fig3_reliability.R` | Figure 3, reliability curves, four labels, before and after correction | 17.0 x 13.0 cm |
| `fig4_utility.R` | Figure 4, decision curve and cumulative diagnostic yield | 12.0 x 17.0 cm |
| `figS1_reliability_all.R` | Supplementary Figure S1, remaining component labels | 18.0 x 11.0 cm |
| `figS2_acquisition.R` | Supplementary Figure S2, performance by acquisition setting | 13.0 x 9.0 cm |
| `figS3_output_bias.R` | Supplementary Figure S3, final-layer bias against training prevalence | 13.0 x 13.0 cm |

Figure 1, the cohort flow diagram, is drawn separately from the counts in
`results/figure_data/cohort_flow.csv` together with the exclusion counts reported by the cohort SQL.

Each script writes a vector PDF and a 600 dpi PNG. **The PDF is the file to submit**: it is
resolution independent, and vector formats are preferred for charts. The PNG is for previewing.

Two implementation notes, both of which fail silently rather than loudly and so are worth knowing.
The base PDF device is used rather than `cairo_pdf`, because cairo reports as available on some
builds but fails to load and then writes no file at all. And R encodes spaces in the `--file=`
argument as `~+~`, so the scripts decode that before resolving their own directory; without it they
cannot find `theme.R` when the repository sits under a path containing a space.
