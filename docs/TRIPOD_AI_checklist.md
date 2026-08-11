# TRIPOD+AI Reporting Checklist (Collins et al., BMJ 2024)

Mapping of TRIPOD+AI items to where each is addressed (M = MANUSCRIPT_DRAFT.md; D = DECISIONS_AND_RATIONALE.md; R = RESULTS_SUMMARY.md). This study is a **model evaluation/external-validation** (no model development).

| # | Item | Addressed | Where |
|---|---|---|---|
| 1 | Title identifies study as AI model evaluation | ✅ | M (Title: "External Validation … EchoNext-Mini …") |
| 2 | Structured abstract | ✅ | M (Abstract) |
| 3 | Background/rationale, intended use, role of AI | ✅ | M (Introduction) |
| 4 | Objectives | ✅ | M (Intro / Objectives) |
| 5 | Data source & study design | ✅ | M (Methods: Data source & cohort) |
| 6 | Eligibility / inclusion–exclusion | ✅ | M (Methods), D, supplement S1 |
| 7 | Outcome (label) definition & assessment | ✅ | M (Methods: Labels), D, supplement S1 |
| 8 | Predictors / model inputs | ✅ | M (Model & preprocessing); 12-lead waveform + 7 tabular |
| 9 | Missing data handling | ✅ | M/D (missing structured field → negative; atrial rate → 0; imputation sensitivity); **per-label missingness in Supplementary Table S2** |
| 10 | Model (released EchoNext-Mini); architecture; version | ✅ | M (Model); frozen released weights; equivalence to official module 1.2e-7 |
| 11 | Model output & post-processing (sigmoid probabilities) | ✅ | M/D |
| 12 | Analysis: discrimination, calibration, recalibration, utility | ✅ | M (Statistics), R |
| 13 | Subgroup/fairness analysis | ✅ | M, R (sex/age/race) |
| 14 | Sample size / events | ✅ | M/R (n=45,878; prevalences) |
| 15 | Participants flow (attrition) | ✅ | **Figure 1** (flow diagram) |
| 16 | Participant characteristics (Table 1) | ✅ | R (Table 1) |
| 17 | Model performance (discrimination + CIs) | ✅ | R (Table 2: AUROC + 95% CI per label) |
| 18 | Calibration + recalibration results | ✅ | M (composite recalibration in main text); **Supplementary Table S4** (per-label recalibration); **Figure 3** (reliability curves before/after correction); **Supplementary Figure S1** (remaining components) |
| 19 | Clinical utility | ✅ | R (Prioritization of echocardiography): decision-curve net benefit in **Figure 4A** and capacity-constrained yield in **Supplementary Table S6**. Utility in an unselected population would still require prospective evaluation. |
| 20 | Fairness results | ✅ | R (Table 5: subgroup AUROC + 95% CI by sex, age, race or ethnicity and care setting; Supplementary Table S5 full) |
| 21 | Sensitivity analyses | ✅ | R (Sensitivity analyses); **Supplementary Table S8** |
| 22 | Interpretation | ✅ | M (Discussion) |
| 23 | Limitations | ✅ | M (Discussion: single site, harmonization, no outcomes) |
| 24 | Fairness/equity implications | ✅ | M (Discussion) |
| 25 | Data availability | ✅ | README (PhysioNet credentialed; no redistribution) |
| 26 | Code availability | ✅ | README + repo (Zenodo DOI on release) |
| 27 | Funding / conflicts / AI use | ✅ | M (Funding; Conflicts of Interest; Declaration of Generative AI) |
| 28 | Reproducibility (env, seeds, deterministic cohort) | ✅ | D, requirements.txt, deterministic SQL, official-module equivalence |

Note: the manuscript uses 4 figures (1 cohort assembly, 2 ROC curves, 3 reliability curves, 4 clinical utility) and 5 tables (1 cohort characteristics, 2 discrimination and calibration by label, 3 the released model in two settings, 4 recalibration, 5 subgroup performance). Supplementary Tables S1-S9 and Supplementary Figures S1-S3 carry the label definitions, field availability, implementation equivalence, benchmark metrics, full subgroups, prioritization, complete-case bounds, sensitivity analyses and the wall-thickness bound. Code and aggregate results are archived at Zenodo under concept DOI 10.5281/zenodo.20962994.
