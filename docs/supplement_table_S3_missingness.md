# Supplementary Table S3 — Per-label structured-field availability and missing-as-negative impact

For each EchoNext label, the MIMIC-IV-ECHO source field, the number of the 45,878 primary-cohort echocardiograms in which that field was populated with an interpretable value ('present'), the number treated as negative because the field was absent ('missing → negative', per the EchoNext convention), the label prevalence among echocardiograms with the field present, and the prevalence over the full cohort after the missing-as-negative rule.

Structured echocardiographic reports populate qualitative valve and pericardial fields chiefly when a finding is present or graded. Absence of a structured field may therefore reflect a normal or absent finding, selective structured reporting, or an unavailable measurement, depending on the label; EchoNext made the same missing-as-negative assumption. Quantitative fields (LVEF, wall thickness) are near-universally reported; TR velocity and derived PASP are missing in about 25% of studies because a measurable tricuspid regurgitant jet is required. The two prevalence columns let readers gauge sensitivity to the missing-as-negative rule.

| Label | MIMIC source field | Present, n (%) | Missing → negative, n (%) | Prevalence if present | Prevalence overall |
|---|---|---|---|---|---|
| Reduced LVEF | numeric LVEF (biplane/3D/range) | 45,878 (100.0%) | 0 (0.0%) | 16.0% | 16.0% |
| LV hypertrophy | septal / inferolateral wall thickness | 43,528 (94.9%) | 2,350 (5.1%) | 23.6% | 22.4% |
| Aortic stenosis | aortic_stenosis (graded text) | 5,272 (11.5%) | 40,606 (88.5%) | 38.8% | 4.5% |
| Aortic regurgitation | aortic_regurg (graded text) | 15,009 (32.7%) | 30,869 (67.3%) | 4.7% | 1.5% |
| Mitral regurgitation | mitral_regurg (graded text) | 42,455 (92.5%) | 3,423 (7.5%) | 9.5% | 8.8% |
| Tricuspid regurgitation | tricuspid_regurg (graded text) | 42,754 (93.2%) | 3,124 (6.8%) | 11.1% | 10.3% |
| Pulmonic regurgitation | pulm_regurg (graded text) | 30,490 (66.5%) | 15,388 (33.5%) | 2.4% | 1.6% |
| RV dysfunction | rv_function (graded text) | 44,665 (97.4%) | 1,213 (2.6%) | 5.9% | 5.8% |
| Pericardial effusion | pericardial_effusion (graded text) | 8,246 (18.0%) | 37,632 (82.0%) | 3.3% | 0.6% |
| Elevated TR Vmax | tr_velocity (direct, m/s) | 34,542 (75.3%) | 11,336 (24.7%) | 16.9% | 12.7% |
| Elevated PASP | tr_mmhg gradient + IVC-derived RAP | 34,541 (75.3%) | 11,337 (24.7%) | 14.3% | 10.7% |

LVEF present in 100% by the inclusion criterion (echocardiogram must report ejection fraction). The composite SHD label is positive if any component is positive and is therefore not subject to a single missingness rule.
