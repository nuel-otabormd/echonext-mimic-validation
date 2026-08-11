# Figure build specification

Everything needed to draw the figures, independent of the R scripts in `code/figures/`. All data are
in this folder. All values here have been verified against `results/analysis.json`,
`results/triage.json` and the released model weights (188 values checked, no discrepancies).

---

## Global specification

**Output.** Vector PDF is the deliverable; the journal prefers vector for charts. A 600 dpi PNG may
accompany it for preview. Page dimensions below are in centimetres and are final print size, so do
not scale afterwards.

**Typography.** One size scheme across every figure, so the set reads as one piece of work.

| Element | Size |
|---|---|
| Axis text, axis titles, legend text, facet strip labels | 9 pt |
| Panel subtitles | 8 pt |
| Panel letters (A, B) | 10 pt bold |
| In-panel annotation text | 8 pt |

Sans serif throughout. Text must never fall below 8 pt at final size.

**Palette.** Colour-blind safe. Grey is reserved for reference lines and null strategies, and must
never encode a data series.

| Role | Hex |
|---|---|
| Primary (model, corrected) | `#1b4965` |
| Secondary (as released, composite highlight) | `#c1666b` |
| Tertiary (prior-shift variant in Figure 4A) | `#4c956c` |
| Reference lines, null strategies | `grey55` (`#8C8C8C`) |
| Panel border | `grey30`, 0.4 pt |
| Major gridlines | `grey92`, 0.3 pt; no minor gridlines |

**Common elements.** Diagonal and null reference lines are dashed, `grey55`, 0.35 pt. Proportions
are shown as percentages with no decimal place. Legends sit below the panel unless stated.

---

## Figure 2 — Receiver operating characteristic curves

**Data** `roc_curves.csv` — columns `label`, `auroc`, `fpr`, `tpr`.
**Size** 9.0 × 9.6 cm. **Aspect** equal (a square plotting region).

Three curves, one per `label`, plotted `tpr` against `fpr`, line width 0.6 pt. Dashed diagonal from
(0,0) to (1,1). Axes 0 to 1, labelled as percentages. Legend inside the panel, bottom right, on a
semi-transparent white background, ordered by descending AUROC, each entry reading
`label (AUROC 0.xxx)`.

| Curve | AUROC | Colour |
|---|---|---|
| Structural heart disease | 0.790 | `#1b4965` |
| RV dysfunction | 0.837 | `#c1666b` |
| Reduced LVEF (≤45%) | 0.835 | `#4c956c` |

Axis titles: "1 − specificity" and "Sensitivity".

---

## Figure 3 — Reliability curves, four labels

**Data** `reliability.csv` — columns `label`, `variant`, `n`, `predicted`, `observed`.
**Size** 17.0 × 13.0 cm. **Layout** 2 × 2 facets, **independent axis scales per panel**.

Filter to these four labels, in this order: `Structural heart disease`, `Reduced LVEF (<=45%)`,
`RV dysfunction`, `Aortic stenosis`.

Each panel plots `observed` against `predicted` for two series, line 0.5 pt with points at 1.1 pt,
plus a dashed diagonal. Axes as percentages.

| Series (`variant`) | Colour |
|---|---|
| As released | `#c1666b` |
| After prior shift | `#1b4965` |

Independent scales are necessary because prevalence ranges from 0.6% to 47%; a shared scale renders
the rare labels invisible. **The caption must state that panel scales differ.**

Axis titles: "Predicted probability" and "Observed frequency".

---

## Figure 4 — Clinical utility (two stacked panels)

**Size** 12.0 × 17.0 cm total, panel A above panel B, each labelled with a bold letter.

### Panel A — Decision curve
**Data** `decision_curve.csv` — columns `threshold`, `strategy`, `net_benefit`.

Three series plotted against `threshold`, y limited to −0.05 to 0.50, horizontal line at zero in
`grey55`. X axis as percentages.

| Strategy | Colour | Line | Width |
|---|---|---|---|
| Model | `#1b4965` | solid | 1.1 pt |
| Model, prior shift | `#4c956c` | solid | 0.45 pt |
| Image all | `grey55` | dashed | 0.55 pt |

**The two model curves overlap almost exactly.** That is the finding: the composite is already
calibrated, so the correction has nothing to change. The first must therefore be drawn thick and the
second thin and on top, so both remain visible. Subtitle: "The two model curves overlap; imaging no
patient corresponds to zero".

Axis titles: "Threshold probability" and "Net benefit".

### Panel B — Cumulative diagnostic yield
**Data** `cumulative_gain.csv` — columns `proportion_imaged`, `n_studies`, `yield_model`,
`yield_unprioritised`, `ppv`.

Two curves against `proportion_imaged`: `yield_model` in `#1b4965` at 0.7 pt, and
`yield_unprioritised` in `grey55` dashed at 0.5 pt. Both axes 0 to 1 as percentages.

Annotate the point at 10% capacity: a marker at 1.4 pt on the model curve, a thin vertical connector
down to the unprioritised curve, and the label **"19% of cases at 10% capacity"** placed to the
right.

Subtitle: "Unprioritised referral is a random ordering of the same cohort".
Axis titles: "Proportion of cohort imaged" and "Structural heart disease identified".

Key values: at 10% capacity the model identifies **19.1%** of all cases against **10.0%**
unprioritised, and **90.1%** of studies performed are positive. Half of all cases require imaging
**30.0%** of the cohort rather than **50.0%**.

---

## Supplementary Figure S1 — Reliability curves, remaining labels

**Data** `reliability.csv`, excluding the four labels shown in Figure 3 (eight remain).
**Size** 18.0 × 13.0 cm. **Layout** 4 columns of facets, independent scales.

Same colours and structure as Figure 3, with line 0.45 pt and points 0.9 pt.

---

## Supplementary Figure S2 — Performance by acquisition setting

**Data** `acquisition.csv` — columns `setting`, `n`, `prevalence`, `auroc`, `ci_low`, `ci_high`,
`slope`. **Size** 16.0 × 10.0 cm.

Horizontal forest plot. One row per `setting`, sorted by ascending `auroc`. Point at `auroc` sized by
`n`, horizontal interval from `ci_low` to `ci_high`, both in `#1b4965`, interval height 0.18, line
0.45 pt. Vertical dashed reference at the overall cohort estimate of **0.790** in `grey55`.

Row labels give the setting with its bandwidth and filtering on separate lines, followed by
`(n = ...)`. Subtitle: "Dashed line is the overall cohort estimate". X axis: "Composite AUROC
(95% CI)"; no y-axis title.

---

## Supplementary Figure S3 — Final-layer bias against training prevalence

**Data** `output_biases.csv` — columns `label`, `train_prevalence`, `logit_train_prevalence`,
`output_bias`. **Size** 13.0 × 13.0 cm. **Aspect equal, with identical x and y ranges** (−5 to +1).

Plot `output_bias` against `logit_train_prevalence`. Dashed identity line. A thin `grey80` vertical
segment from each point down to the identity line, showing the gap. Points at 2 pt: `#c1666b` for
Structural heart disease, `#1b4965` for the eleven components. Labels repelled, 8 pt, `grey25`, with
thin leader lines.

Annotation at the lower left: "Outputs on the natural prevalence scale would lie on this line".

**The equal range is essential.** Scaling the vertical axis to the biases alone (which span only
−0.03 to +0.05) collapses the identity line into what appears to be a vertical line at zero, and the
figure then fails to make its point. The point is that all twelve biases sit near zero while training
prevalence spans 0.8% to 52%.

| Label | logit(prevalence) | Bias |
|---|---|---|
| Pulmonic regurgitation | −4.78 | −0.042 |
| Aortic regurgitation | −4.40 | +0.035 |
| Pericardial effusion | −3.52 | +0.048 |
| Aortic stenosis | −3.17 | −0.030 |
| Mitral regurgitation | −2.38 | +0.026 |
| Elevated TR Vmax | −2.16 | +0.025 |
| Tricuspid regurgitation | −2.13 | +0.027 |
| RV dysfunction | −1.88 | +0.026 |
| Elevated PASP | −1.45 | +0.032 |
| Reduced LVEF | −1.19 | −0.000 |
| LV wall thickness | −1.13 | −0.006 |
| **Structural heart disease** | **+0.095** | **+0.023** |

Axis titles: "Log-odds of label prevalence in the training split" and "Final-layer bias of the
released model".

---

## Figure 1 — Cohort assembly

**Data** `cohort_flow.csv` — columns `seq`, `stage`, `n`, `n_patients`, written by
`sql/05_cohort_flow.sql`. **Size** 18.0 × 14.7 cm. Drawn as a flow diagram, not a plot.

Two streams converge. ECGs run down the left at x-centre 30, echocardiographic labels down the
right at x-centre 81, on an arbitrary 0–100 grid. Exclusions hang to the right of the stem they
leave, each entered by a horizontal arrow at the exclusion box's vertical centre.

| Box | Column | Heading | Body |
|---|---|---|---|
| A | left | MIMIC-IV-ECG v1.0 | 800,035 ECGs from 161,352 patients |
| B | right | MIMIC-IV-ECHO v1.0 | 206,488 studies from 91,372 patients |
| B2 | right | Excluded 84,741 studies | Transoesophageal or stress 26,560 · Prosthetic valve 11,774 · LVEF or valve not fully assessed 46,407 |
| B3 | right | 121,747 label-eligible studies | in 67,703 patients |
| C | left | ECGs paired with a label-eligible echocardiogram | recorded within the following 365 days · 233,729 ECGs from 46,349 patients |
| D | right | Excluded 9,137 ECGs | Ventricular pacing 7,436 · Poor quality or lead reversal 1,101 · No valid ECG measurements 595 · Age under 18 years 5 · *(blank line)* · 471 patients thereby retained no ECG |
| E | left | Eligible ECGs | 224,592 ECGs from 45,878 patients |
| F | left | Analytic cohort | 45,878 patients, the most recent eligible ECG of each · 21,659 (47.2%) with structural heart disease |

Box B3 feeds box C by a horizontal arrow, because the echocardiogram supplies the label rather than
the cohort. Source and stage boxes are white with a `grey30` border; exclusion boxes are `grey97`
with a `grey65` border; the final box is `#eaf0f4` with a `#1b4965` border. Headings bold 8 pt in
`grey15`, body 8 pt in `grey30`, arrows `grey45` (`grey65` for exclusion branches) with closed 4 pt
heads.

**Two things the diagram must get right.** The echocardiographic source is the whole structured
measurement component, 206,488 studies, not the 179,928 transthoracic subset; stating the subset as
the source would silently absorb 26,560 transoesophageal and stress studies into no declared
exclusion. And the blank line before "471 patients" is deliberate: that is a patient count, and
without the separation it reads as a fifth addend of the 9,137 ECGs, which would not sum.

Every count reconciles, and `05_cohort_flow.sql` emits three check rows that must all be zero
(`check_echo_excl_sums`, `check_excl_sums_to_paired`, `check_eligible_patients_equals_cohort`). The
figure script refuses to draw if any is non-zero. 206,488 − 26,560 − 11,774 − 46,407 = 121,747, and
233,729 − 7,436 − 1,101 − 595 − 5 = 224,592.
