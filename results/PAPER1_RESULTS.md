# Paper 1 — EchoNext-Mini external validation in MIMIC-IV (n=45878, one-per-patient, full cohort)

## Discrimination & calibration

| Label | Prev% | AUROC (95% CI) | AUPRC | Brier | Calib slope | Calib-in-large |
|---|---|---|---|---|---|---|
| lvef_lte_45 | 16.0 | 0.835 (0.83-0.84) | 0.514 | 0.174 | 1.153 | -0.237 |
| lvwt_gte_13 | 22.4 | 0.679 (0.673-0.685) | 0.35 | 0.208 | 0.78 | -0.198 |
| aortic_stenosis | 4.5 | 0.782 (0.773-0.79) | 0.126 | 0.214 | 0.934 | -0.357 |
| aortic_regurg | 1.5 | 0.73 (0.714-0.746) | 0.039 | 0.186 | 0.839 | -0.353 |
| mitral_regurg | 8.8 | 0.805 (0.798-0.811) | 0.285 | 0.175 | 1.079 | -0.279 |
| tricuspid_regurg | 10.3 | 0.798 (0.791-0.804) | 0.314 | 0.162 | 1.146 | -0.262 |
| pulm_regurg | 1.6 | 0.723 (0.705-0.74) | 0.051 | 0.136 | 0.562 | -0.263 |
| rv_dysfunction | 5.8 | 0.837 (0.83-0.845) | 0.283 | 0.162 | 1.143 | -0.292 |
| pericardial | 0.6 | 0.765 (0.74-0.792) | 0.019 | 0.172 | 1.369 | -0.379 |
| pasp_gte_45 | 10.7 | 0.768 (0.762-0.774) | 0.27 | 0.184 | 1.13 | -0.288 |
| tr_max_gte_32 | 12.7 | 0.763 (0.758-0.769) | 0.301 | 0.18 | 1.056 | -0.26 |
| shd | 47.1 | 0.79 (0.787-0.794) | 0.771 | 0.187 | 0.936 | 0.028 |

## SHD recalibration (5-fold OOF Platt)
Brier 0.1871 -> 0.1862; slope 0.936 -> 1.0

## Fairness (SHD)

| Subgroup | n | Prev% | AUROC | Calib slope |
|---|---|---|---|---|
| sex:M | 23569 | 51.3 | 0.778 | 0.891 |
| sex:F | 22309 | 42.5 | 0.8 | 0.975 |
| age:<65 | 19492 | 31.6 | 0.773 | 0.914 |
| age:65-79 | 15360 | 50.7 | 0.751 | 0.844 |
| age:80+ | 11026 | 69.3 | 0.731 | 0.791 |
| race:White | 30890 | 49.1 | 0.782 | 0.92 |
| race:Black | 5762 | 49.3 | 0.798 | 0.964 |
| race:Hispanic | 1976 | 38.7 | 0.776 | 0.881 |
| race:Asian | 1399 | 39.4 | 0.802 | 0.97 |
| race:Other | 1685 | 41.7 | 0.797 | 0.964 |
| race:Unknown | 4166 | 37.6 | 0.821 | 1.005 |

Figures in `figs/`: calibration_shd.png, roc_shd.png, dca_shd.png, subgroup_auroc.png
