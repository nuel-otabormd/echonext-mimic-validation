# Supplementary Table S4 — Recalibration by label (five-fold out-of-fold)

Per-label probability recalibration using five-fold out-of-fold Platt scaling. Brier score and calibration slope are shown before and after recalibration. Recalibration improves calibration (slope toward 1.0, lower Brier); discrimination (AUROC, Table 2) is unchanged. The composite was already near-calibrated and is retained in the main text.

| Label | Brier before | Brier after | Calibration slope before | Calibration slope after |
|---|---|---|---|---|
| Structural heart disease (composite) | 0.187 | 0.186 | 0.94 | 1.00 |
| Reduced ejection fraction | 0.174 | 0.103 | 1.15 | 1.00 |
| Right ventricular dysfunction | 0.162 | 0.047 | 1.14 | 1.00 |
| Mitral regurgitation | 0.175 | 0.071 | 1.08 | 1.00 |
| Tricuspid regurgitation | 0.162 | 0.081 | 1.15 | 1.00 |
| Aortic stenosis | 0.214 | 0.041 | 0.93 | 1.00 |
| Pulmonary artery systolic pressure | 0.184 | 0.087 | 1.13 | 1.00 |
| Pericardial effusion | 0.172 | 0.006 | 1.37 | 0.97 |
| Tricuspid regurgitation velocity | 0.180 | 0.100 | 1.06 | 1.00 |
| Aortic regurgitation | 0.186 | 0.015 | 0.84 | 0.95 |
| Pulmonary regurgitation | 0.136 | 0.015 | 0.56 | 1.00 |
| Left ventricular wall thickness | 0.208 | 0.162 | 0.78 | 1.00 |

Out-of-fold isotonic recalibration gave equivalent composite calibration.
