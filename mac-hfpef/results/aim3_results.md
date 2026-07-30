# Aim 3 Results: MRA exposure and mitral annular calcification progression

**Status:** complete. **Conclusion: null.**
**Date:** 2026-07-30
**Analysis:** logistic regression, `statsmodels` (Newton-Raphson), complete case.

---

## Cohort

Patients with mitral annular calcification (MAC) explicitly graded on two transthoracic
echocardiograms at least 365 days apart, baseline grade mild or moderate, no mitral valve
prosthesis through follow-up, aged 18 or over.

| Step | n |
|---|---|
| Paired graded echoes, baseline mild or moderate | 6,570 |
| Excluded: no admission during interval (no exposure information) | −930 |
| Analytic set with exposure ascertainable | 5,640 |
| Complete case for adjustment (creatinine, LVEF, Charlson) | 4,329 |

Mean age 73.4 years, 51.7% female, mean LVEF 62.0%, mean eGFR 61.9, mean inter-echo
interval 1,758 days (4.8 years). Progression occurred in 1,043 of 4,329 (24.1%).

**Exclusion of the 930 patients with no interval admission was pre-specified** before these
results were seen. They are unclassifiable rather than unexposed, and progressed at 17.7%,
materially below either observed group.

---

## Primary result

**Adjusted OR 0.94 (95% CI 0.77 to 1.15), p = 0.53.**

Adjusted for baseline MAC grade, log interval length, age, sex, creatinine, LVEF, Charlson
comorbidity index and atrial fibrillation.

| Estimate | OR | 95% CI | p |
|---|---|---|---|
| Crude, full analytic set | 0.84 | 0.71 – 1.00 | 0.051 |
| Crude, complete case | 0.86 | 0.71 – 1.04 | — |
| **Adjusted** | **0.94** | **0.77 – 1.15** | **0.53** |

### Why the crude signal disappeared

Follow-up interval. `log(interval_days)` is the strongest predictor in the model
(coefficient +0.380, z = 6.76, p < 0.001). Unexposed patients had longer gaps between
echocardiograms and therefore more time to progress, which manufactured an apparently
protective association for MRA. Adjustment removes it.

The prior expectation recorded in the analysis plan, that confounding by indication would
bias toward the null and adjustment might strengthen the estimate, was wrong. The dominant
confounder was differential follow-up time and it operated in the opposite direction.

---

## Sensitivity analyses

| Analysis | n | events | OR (95% CI) | p |
|---|---|---|---|---|
| Primary, any MRA | 4,329 | 1,043 | 0.94 (0.77–1.15) | 0.53 |
| Exposure: high/medium ascertainment confidence | 4,329 | 1,043 | 0.89 (0.71–1.12) | 0.32 |
| Exposure: admission reconciliation required | 4,329 | 1,043 | 0.88 (0.67–1.15) | 0.34 |
| Interval 545 days or more | 3,761 | 932 | 0.97 (0.79–1.20) | 0.80 |
| Interval 730 days or more | 3,315 | 848 | 0.95 (0.76–1.18) | 0.63 |
| Baseline mild | 3,341 | 875 | 0.88 (0.71–1.11) | 0.28 |
| Baseline moderate | 988 | 168 | 1.20 (0.76–1.90) | 0.43 |
| Two-grade progression | 4,329 | 85 | **not estimable** | — |

Seven specifications, all intervals crossing unity, point estimates between 0.88 and 1.20.
The null is stable rather than fragile.

The two-grade progression model failed to converge (85 events; only baseline-mild patients
can advance two grades). Reported as not estimable rather than quoting an unstable estimate.

**E-value** for the primary estimate is 1.33. Because the confidence interval already
includes the null, no unmeasured confounding is required to explain the result.

---

## Dose-response (pre-specified secondary)

| Group | n | events | % | OR (95% CI) | p |
|---|---|---|---|---|---|
| No MRA | 3,604 | 885 | 24.6 | reference | — |
| Below target dose | 355 | 81 | 22.8 | 0.99 (0.76–1.30) | 0.94 |
| Target dose, 50 mg or above | 138 | 23 | 16.7 | 0.65 (0.41–1.04) | 0.070 |
| Linear trend across levels | 4,097 | 989 | — | 0.88 per level (0.73–1.05) | 0.15 |

A threshold pattern rather than a gradient: no association below target dose, a 35% lower
odds at target dose. Pharmacologically this is the shape a real effect would take, and the
comparison was pre-specified rather than identified post hoc.

**It rests on 138 patients and 23 events, and the linear trend is not significant.** This is
hypothesis-generating. The event count must appear alongside any statement of the estimate.

---

## Interpretation

MRA exposure was not associated with progression of mitral annular calcification. The
confidence interval excludes relative reductions greater than approximately 23%, so this is
an informative null rather than an uninformative one.

This is the first evaluation in humans of a hypothesis that previously rested on cell
culture and uremic animal models. The result constrains that hypothesis at the doses and
exposure durations observable here; it does not exclude an effect at consistently
maintained target dosing, which the dose-stratified estimate identifies as the question for
a study with better dose ascertainment.

---

## Methodological notes for the manuscript

**BigQuery ML was not used for inference.** Fitted through `ML.ADVANCED_WEIGHTS` it returned
standard errors inflated by a factor of 1/SD for numeric predictors (exposure SE 0.274
against the correct 0.103) and, more seriously, coefficients of the wrong sign for
interval length and age even after apparent convergence. All inference here is from
`statsmodels`, which converged in six Newton-Raphson iterations.

**Collinearity was checked and corrected before the final model.** CKD-EPI eGFR is computed
from age and sex, so eGFR was replaced by creatinine; the Charlson index contains renal
disease, heart failure and diabetes as components, so those were not entered alongside it.

**Limitations specific to this aim.** Exposure is prevalent rather than incident: only the
admission medication list is machine-readable, so no initiator design with a defined time
zero was achievable. Medication exposure is observed at admissions rather than continuously
and reflects prescription rather than adherence. Requiring a graded follow-up study
conditions on the outcome being ascertainable. MAC grading is a qualitative reader
judgement with an empirically estimated disagreement rate of 7.8%.
