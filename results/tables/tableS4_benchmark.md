**Supplementary Table S4. Performance of the released model on its own benchmark test set (n = 5,442), before and after the prior-shift correction.**

| Label | Prevalence, % | Mean predicted probability | AUROC | AUPRC | Calibration-in-the-large | Calibration slope | Brier | Brier skill | Calibration-in-the-large after prior shift | Brier skill after prior shift |
|---|---|---|---|---|---|---|---|---|---|---|
| Reduced LVEF (<=45%) | 17.68 | 0.354 | 0.852 | 0.599 | -0.177 | 1.12 | 0.145 | +0.003 | -0.014 | +0.290 |
| LV wall thickness (>=1.3 cm) | 19.50 | 0.401 | 0.734 | 0.372 | -0.206 | 0.99 | 0.188 | -0.198 | -0.008 | +0.106 |
| Aortic stenosis | 5.26 | 0.343 | 0.859 | 0.248 | -0.291 | 1.34 | 0.161 | -2.225 | +0.018 | +0.092 |
| Aortic regurgitation | 1.21 | 0.340 | 0.740 | 0.032 | -0.328 | 0.77 | 0.171 | -13.256 | +0.002 | +0.009 |
| Mitral regurgitation | 6.19 | 0.341 | 0.806 | 0.222 | -0.279 | 0.94 | 0.166 | -1.849 | -0.011 | +0.091 |
| Tricuspid regurgitation | 6.49 | 0.349 | 0.833 | 0.292 | -0.284 | 1.12 | 0.157 | -1.587 | -0.023 | +0.122 |
| Pulmonic regurgitation | 0.37 | 0.258 | 0.832 | 0.116 | -0.254 | 1.00 | 0.128 | -34.086 | -0.002 | +0.035 |
| RV dysfunction | 7.70 | 0.329 | 0.866 | 0.428 | -0.252 | 1.15 | 0.145 | -1.034 | -0.031 | +0.203 |
| Pericardial effusion | 1.27 | 0.400 | 0.766 | 0.072 | -0.387 | 1.25 | 0.190 | -14.186 | -0.013 | +0.006 |
| Elevated PASP (>=45 mmHg) | 12.84 | 0.379 | 0.770 | 0.357 | -0.251 | 1.00 | 0.174 | -0.553 | -0.027 | +0.120 |
| Elevated TR Vmax (>=3.2 m/s) | 6.89 | 0.363 | 0.754 | 0.211 | -0.295 | 0.89 | 0.174 | -1.718 | -0.016 | +0.057 |
| Structural heart disease | 42.59 | 0.412 | 0.820 | 0.789 | +0.014 | 1.03 | 0.169 | +0.309 | -0.002 | +0.309 |

Inputs were the distributed arrays, used without modification, so no preprocessing performed for this study contributed to these values. Areas under the receiver operating characteristic curve reproduce the published values to three decimal places for 10 of 12 labels; the exceptions are aortic regurgitation (0.740 against 0.739) and pulmonic regurgitation (0.832 against 0.829), the two labels with fewest events in this test set. Mean predicted probability lies between 0.26 and 0.40 for all component labels despite prevalence of 0.4%–19.5%, and Brier skill is negative for 10 of 11 components and positive for the composite. The prior shift uses only the released training-split prevalences and no outcome data from this dataset.
