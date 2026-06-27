# Supplementary Table S5 — Secondary LV-hypertrophy analysis (higher grades)

The primary LV-wall-thickness label (max septal/inferolateral ≥1.3 cm) was the weakest component
(AUROC 0.679), consistent with the limited sensitivity of the ECG for *mild* wall thickening. To
test whether this reflects the difficulty of detecting mild hypertrophy rather than failure of the
underlying construct, the model's wall-thickness probability was evaluated against two higher-grade
hypertrophy outcomes on the **full locked one-per-patient cohort (n = 45,878)**.

The analysis is regenerated directly from the locked cohort (`sql/06_lvh_secondary.sql`, each ECG's
own linked echo). A sanity column confirms alignment: the regenerated `max(IVS, inferolateral) ≥ 1.3 cm`
flag reproduces the locked `lvwt_gte_13` label for **45,878 / 45,878 (100.0%)** patients — i.e. 22.4%
prevalence and AUROC 0.679, identical to Table 2 — so the higher-grade variables are on the same cohort.

| Outcome | Definition | Prevalence | AUROC (95% CI) |
|---|---|---|---|
| LV wall thickness ≥1.3 cm (primary; sanity) | max(septal, inferolateral) ≥1.3 cm | 22.4% | 0.679 (0.673–0.684) |
| Septal (IVS) ≥1.5 cm | septal_thickness ≥1.5 cm | 4.0% | **0.746 (0.736–0.756)** |
| Categorical moderate-or-severe LVH | `lv_wall_thickness` graded "mod symmetric (1.5–1.7 cm)" or "severe symmetric (>1.7 cm)" | 3.2% | **0.754 (0.743–0.764)** |

AUROC, area under the receiver operating characteristic curve; CI, confidence interval (2,000-sample
patient-level bootstrap). The improvement from 0.679 at 1.3 cm to ~0.75 at higher grades indicates the
weak primary result is driven by mild wall thickening rather than failure of the broader hypertrophy
construct. Reproduce: `bq query --use_legacy_sql=false < sql/06_lvh_secondary.sql` (save to
`$ECHONEXT_DATA/lvh_secondary.csv`), then `python code/lvh_secondary.py`.
