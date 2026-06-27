# Supplementary Table S2 — Sensitivity analyses with calibration metrics

Discrimination AND calibration are robust across label definitions and linkage windows. Probabilities are the released EchoNext-Mini outputs (unchanged); only the reference label or cohort window varies. Calibration slope ≈1 and calibration-in-the-large (CIL) near 0 indicate stability.

These analyses use the n=45,035 patients carrying the auxiliary structured fields required for label re-derivation (a subset of the primary 45,878-patient cohort); primary-variant point estimates (e.g., SHD AUROC 0.790) match the main analysis.

| Analysis | Variant | n | Prev % | AUROC | Brier | Calib slope | CIL |
|---|---|---|---|---|---|---|---|
| ECG→TTE window | ≤30 d | 36,214 | 47.5 | 0.789 | 0.187 | 0.94 | +0.016 |
| ECG→TTE window | ≤90 d | 39,901 | 46.3 | 0.791 | 0.186 | 0.94 | +0.014 |
| ECG→TTE window | ≤180 d | 42,198 | 45.9 | 0.792 | 0.185 | 0.94 | +0.015 |
| ECG→TTE window | ≤365 d (primary) | 45,035 | 46.0 | 0.790 | 0.186 | 0.94 | +0.019 |
| Reduced LVEF def | midpoint (primary) | 45,035 | 15.9 | 0.836 | 0.173 | 1.15 | -0.236 |
| Reduced LVEF def | midpoint-only | 45,035 | 15.9 | 0.835 | 0.173 | 1.15 | -0.236 |
| Reduced LVEF def | lower-bound | 45,035 | 17.9 | 0.826 | 0.172 | 1.09 | -0.217 |
| RV dysfunction def | categorical + TAPSE (primary) | 45,035 | 6.0 | 0.830 | 0.162 | 1.11 | -0.288 |
| RV dysfunction def | categorical only | 45,035 | 5.8 | 0.837 | 0.162 | 1.15 | -0.291 |
| TR Vmax def | direct velocity ≥3.2 (primary) | 45,035 | 11.2 | 0.767 | 0.180 | 1.08 | -0.274 |
| TR Vmax def | derived gradient ≥40.96 | 45,035 | 11.2 | 0.767 | 0.180 | 1.08 | -0.274 |
| PASP RAP assumption | ASE IVC-derived (primary) | 45,035 | 10.5 | 0.770 | 0.183 | 1.14 | -0.289 |
| PASP RAP assumption | fixed RAP 3 | 45,035 | 10.2 | 0.769 | 0.183 | 1.14 | -0.292 |
| PASP RAP assumption | fixed RAP 5 | 45,035 | 12.5 | 0.765 | 0.182 | 1.11 | -0.269 |
| PASP RAP assumption | fixed RAP 10 | 45,035 | 19.5 | 0.748 | 0.183 | 1.01 | -0.199 |

*Atrial rate (a model input unavailable in MIMIC, imputed 0) was additionally varied (0 / ventricular-rate proxy / fixed 75 bpm); discrimination was unchanged (AUROC 0.786 in all three), confirming insensitivity to this imputation.*

### Secondary LV wall-thickness analyses
Unlike the robustness rows above (n=45,035 subset), these analyses use the **full** primary cohort (n=45,878), regenerated directly from the locked cohort with each ECG's own linked echo. The primary max(septal, inferolateral) ≥1.3 cm label reproduces the main analysis exactly (sanity check: agrees with the locked `lvwt_gte_13` label for 45,878/45,878 patients), confirming alignment. Discrimination was higher for higher-grade hypertrophy definitions.

| Definition | n | Prev % | AUROC (95% CI) |
|---|---|---|---|
| Primary LV wall thickness: max(septal, inferolateral) ≥1.3 cm | 45,878 | 22.4 | 0.679 (0.673–0.684) |
| Septal thickness ≥1.5 cm | 45,878 | 4.0 | 0.746 (0.736–0.756) |
| Categorical moderate-or-severe LVH | 45,878 | 3.2 | 0.754 (0.743–0.764) |

Categorical LVH = MIMIC-IV-ECHO `lv_wall_thickness` graded "mod symmetric (1.5–1.7 cm)" or "severe symmetric (>1.7 cm)". 2,000-sample patient-level bootstrap CIs. Reproduce: `sql/06_lvh_secondary.sql` → `code/lvh_secondary.py`.
