# Analysis Plan: Mitral Annular Calcification as a Therapeutic Phenotype in Heart Failure

## Version: 0.1 (DRAFT, pending feasibility confirmation)
## Date: 2026-07-30
## Author: Emmanuel Otabor, MD

---

## 0. Status and open items

This plan is a draft. Three feasibility queries are outstanding and two aims are
conditional on their results:

| Outstanding query | Gates | Status |
|---|---|---|
| MAC grade transition matrix (4x4, first vs last echo) | Aim 3 measurement validity | **RUN 2026-07-30, see 10.1** |
| Recording rate by era (`pct_graded_of_assessed`) | Aim 3 incident analysis | NOT RUN |
| SGLT2i / MRA prescription counts in MIMIC-IV | SGLT2i inclusion throughout | NOT RUN |
| `2_MIMIC_IV_ADMISSION_MEDS` schema | Exposure definition, all aims | NOT RUN |

The transition matrix triggered the pre-specified failure condition in Section 10.1 and
Aim 3 has been restructured accordingly. The incident MAC analysis is **suspended** pending
the era recording-rate diagnostic.

---

## 1. Research Question

Mitral annular calcification (MAC) is an active, osteogenic process rather than passive
degeneration, and mineralocorticoid receptor (MR) signalling is one of its established
drivers in preclinical models. MR activation promotes osteoblastic differentiation of
vascular smooth muscle cells through PIT1 upregulation, and both spironolactone and
eplerenone abolish phosphate induced osteogenic transformation in human aortic smooth
muscle cells. This raises a question that has not been asked in humans at scale: is MAC a
phenotype that mineralocorticoid receptor antagonists (MRAs) act upon, and are the
patients who have it actually receiving them?

**PICO(T)**

- **Population:** Adults with a transthoracic echocardiogram in MIMIC-IV, with a heart
  failure with preserved ejection fraction (HFpEF) subpopulation defined in Section 4.
- **Index/Exposure:** MAC presence and severity (Aims 1, 2, 4); MRA exposure (Aim 3, and
  as the treatment variable in Aim 4).
- **Comparator:** No MAC / lower MAC grade; no MRA exposure.
- **Outcomes:** One year all cause mortality, days alive and out of hospital, incident and
  progressive MAC, guideline directed medical therapy receipt. Full definitions in Section 6.
- **Time:** Index echocardiogram to one year.

---

## 2. Study Design

Retrospective cohort study using routinely collected data, with four pre specified aims.
Aims 1, 2 and 4 are cross sectional or time to event analyses anchored on an index
echocardiogram. Aim 3 is a longitudinal analysis using paired echocardiograms.

This study makes **association and effect modification claims, not efficacy claims.** The
efficacy of MRAs and SGLT2 inhibitors in heart failure is established by randomised trials
(TOPCAT, FINEARTS-HF, EMPEROR-Preserved, DELIVER). Re-estimating efficacy observationally
in a single centre ICU-weighted cohort would be uninformative at best and misleading at
worst. Every aim here is therefore framed around a question trials could not answer:
prescribing behaviour, phenotype characterisation, and a mechanistic endpoint (calcification
progression) that no trial has measured.

---

## 3. Data Sources

- **MIMIC-IV v3.1** (`physionet-data.mimiciv_3_1_hosp`, `_icu`, `_derived`)
- **MIMIC-IV-ECHO** (`physionet-data.mimiciv_echo.structured_measurement`)
- **Medication reconciliation pipeline** (`the-project-476301.2_MIMIC_IV_ADMISSION_MEDS`),
  built previously, providing home medication reconstruction and `gdmt_by_admission`.

Access requires PhysioNet credentialing, CITI training, and a signed data use agreement.

### 3.1 Verified data facts

Established by direct query, 2026-07-30:

- `structured_measurement` restricted to `test_type = 'tte'`: 179,928 echo instances across
  85,292 subjects.
- MAC is a dedicated structured field, `mac_severity` ("Mitral Valve - Mitral Annular
  Calcification"), populated on 52,809 of 179,928 TTEs (29.4%).
- The field vocabulary is closed and contains exactly three values: `mild` (37,052),
  `mod mac` (13,134), `severe` (2,623). These sum exactly to the non-blank count.
- **There is no negative token.** The field is only populated when MAC is observed, which
  is the basis for the missing-as-negative convention in Section 5.1.
- Ejection fraction is available on 98.0 to 99.0% of MAC positive echoes.
- 23,100 subjects have two or more TTEs at least 365 days apart.

---

## 4. Study Population

Populations differ by aim. This is deliberate: the MR-calcification biology is not specific
to HFpEF, and restricting Aim 3 to HFpEF would discard roughly three quarters of the at-risk
sample for no scientific gain.

### 4.1 Aim 3 population (broad echo cohort)

**Inclusion**
1. Age 18 or over at index echocardiogram. Paediatric physiology and calcification biology differ.
2. Two or more transthoracic echocardiograms at least 365 days apart. A shorter interval
   cannot distinguish true progression from reader variability.
3. **`mac_severity` explicitly non-blank at BOTH index and follow-up.** This is not a
   refinement, it is the condition on which the aim's validity rests. Admitting blank
   follow-up studies produces a 41.9% apparent regression rate in a condition that does not
   regress. See Section 10.1.

**Exclusion**
1. Mitral valve replacement or repair at **any point up to and including the follow-up
   study**, not merely at baseline. An annuloplasty ring or prosthesis placed between the two
   echoes genuinely removes the gradable native annulus and manufactures apparent regression.
   Identified using the `mvr_structure*` and `mv_leaflets` fields already validated in
   `sql/01_echo_labels.sql`.
2. Baseline severe MAC **for the progression analysis only** (ceiling effect: 0 of 170
   progressed because there is no higher grade). These patients are retained for Aims 1, 2 and 4.

### 4.2 Aims 1, 2 and 4 population (HFpEF cohort)

**Inclusion**
1. Age 18 or over.
2. Heart failure by ICD-9 (428%) or ICD-10 (I50%) at or before the index admission.
   Both coding eras are required; MIMIC-IV spans 2008 to 2022.
3. LVEF 50% or greater on the index echocardiogram, using the coalescing order established
   in `sql/01_echo_labels.sql`: biplane, then 3D, then the midpoint of the reported
   `lvef`/`lvef_upper` range, then either bound alone.

**Exclusion**
1. Prior mitral valve replacement or repair (as above).
2. Missing EF on the index study (1.0 to 2.0% of MAC positive echoes).

### 4.3 Anticipated sample sizes

| Aim | At risk | Events |
|---|---|---|
| 3 PRIMARY, progression, graded at both timepoints, baseline mild or moderate | 4,025 | 1,172 (29.1%) |
| 3 SUSPENDED, incident MAC (baseline grade 0) | 16,480 | 3,893 (23.6%) |
| 1, 2, 4 (HFpEF with MAC) | TBC, approx. 41,800 echoes have MAC with EF above 45 | TBC |

**Progression among patients graded at both timepoints is the primary Aim 3 analysis.**
It is smaller than the incident cohort but is the only one of the two with a defensible
denominator.

The incident MAC analysis is suspended. Baseline grade 0 conflates "no MAC" with "not
assessed," so the 16,480 at-risk cohort contains an unknown number of patients with
unrecorded prevalent MAC. The diagnostic evidence is in the transition matrix: 575 patients
moved from grade 0 to moderate and 53 from grade 0 to severe within a year or more. Moderate
and severe annular calcification do not arise de novo on that timescale, so those 628 cases,
16% of apparent incident MAC, indicate baseline under-recording. If echocardiographic
thoroughness correlates with MRA exposure, the resulting misclassification is differential.
Reinstatement requires the era recording-rate diagnostic in Section 0 to show stable
ascertainment.

---

## 5. Exposure Definitions

### 5.1 MAC (Aims 1, 2, 4)

Graded ordinally from `mac_severity`: 0 = none or not recorded, 1 = mild, 2 = moderate,
3 = severe. Analysed as an ordinal trend and as categorical indicators.

**Missing as negative, for cross-sectional aims only.** Blank `mac_severity` is treated as no
MAC in Aims 1, 2 and 4. Justification: the field vocabulary contains no negative token, so it
is populated only when MAC is seen. The convention also matches the missing-as-negative
approach used in the EchoNext validation work. **Sensitivity analysis:** restrict to echoes
with a non-blank field.

**This convention is invalid for Aim 3 and must not be carried over.** The transition matrix
(Section 10.1) shows that 88% of apparent MAC regression is movement to a blank field rather
than to a lower grade, meaning blank at follow-up reflects non-recording rather than absence.
For all longitudinal analyses, blank is treated as **missing**, and MAC must be explicitly
graded at both timepoints.

**Known imperfection:** 55 echoes record mitral stenosis attributed to MAC while leaving
`mac_severity` blank. These are flagged as `mac_present_ungraded` and handled in sensitivity
analysis rather than silently coded negative.

### 5.2 MRA and SGLT2 inhibitor exposure

Primary source: `gdmt_by_admission` from the existing reconciliation pipeline, pending schema
review. Fallback: `physionet-data.mimiciv_3_1_hosp.prescriptions`, matching spironolactone,
eplerenone and finerenone (MRA) and empagliflozin, dapagliflozin, canagliflozin,
ertugliflozin and sotagliflozin (SGLT2i).

**Finerenone will be absent** from MIMIC-IV's era. SGLT2i entered practice around 2014 and
received its HFpEF indication in 2022, so counts may be too low to support any SGLT2i
analysis. If so, this becomes an MRA study and says so explicitly rather than reporting an
underpowered SGLT2i arm.

### 5.3 The Aim 3 exposure problem

MIMIC observes medications only at admissions, so exposure across a two year inter-echo
interval is sampled intermittently. Patients with more admissions have more opportunities to
be classified as exposed, and admission frequency correlates with severity. This is
surveillance bias built into the exposure variable.

**Mitigation:** define exposure as the proportion of interval admissions with MRA on the
reconciled list, restrict the analysis to patients with a minimum number of admissions
during the interval, and include admission count as a covariate. Sensitivity analyses will
vary that minimum.

---

## 6. Outcome Definitions

### 6.1 Primary outcomes by aim

| Aim | Primary outcome |
|---|---|
| 1 | One year all cause mortality from the index echocardiogram |
| 2 | Receipt of an MRA at the index admission |
| 3 | MAC progression (grade increase between paired echoes, both explicitly graded) |
| 4 | One year all cause mortality, tested for MRA by MAC interaction |

### 6.2 Definitions

**One year all cause mortality.** From `patients.dod`, analysed as time to event with
administrative censoring. MIMIC-IV captures out of hospital death within approximately one
year of discharge through state registry linkage; beyond that the record degrades.
**Required verification before use:** confirm the truncation empirically by examining the
distribution of days from last discharge to `dod`.

**Days alive and out of hospital (DAOH) at one year.** 365 minus inpatient days, set to zero
on death. Captures mortality and hospitalisation burden in a single measure. Limited to
BIDMC encounters, which is a stated limitation.

**MAC progression.** An increase in grade between index and follow-up echocardiogram.
**Incident MAC** is progression from grade 0.

**Secondary outcomes:** all cause and heart failure readmission at 30 days and one year;
recurrent admission count (negative binomial or Andersen-Gill); ICU admission and length of
stay; KDIGO stage 2 or higher acute kidney injury; hyperkalemia (potassium 5.5 mmol/L or
above, and 6.0 or above); discharge disposition including hospice.

---

## 7. Covariates

Age, sex, race (as a social construct, from `admissions.race`, most frequent non-missing
category per patient), insurance, admission type and care setting at index. Comorbidity via
the `charlson` derived table with its component conditions retained individually. Renal
function via baseline creatinine and estimated GFR from `creatinine_baseline`, plus baseline
potassium. Echocardiographic covariates: LVEF, LV wall thickness, left atrial size where
available, E/A, septal and lateral E prime, deceleration time, PASP, TAPSE. Concomitant
RAASi and diuretic exposure. Atrial fibrillation by ICD code, which is both a MAC correlate
and an outcome determinant.

For Aim 3, **baseline MAC grade is the single most important covariate**, since published
work identifies baseline calcium burden as the dominant predictor of progression. Failing to
adjust for it would confound the entire aim.

---

## 8. Statistical Analysis

**Aim 1.** Cox proportional hazards for one year mortality with MAC grade as an ordinal
trend term and as categorical indicators. Proportional hazards assessed by Schoenfeld
residuals. DAOH by quantile regression given expected skew and a point mass at zero. Echo
phenotype compared across grades with standardised mean differences and multivariable
adjusted mean differences.

**Aim 2.** Modified Poisson regression with robust variance for MRA receipt, giving risk
ratios rather than odds ratios given a common outcome. Adjusted for eGFR, potassium, age,
sex and comorbidity. The question is whether any under-treatment persists beyond what renal
function justifies, so eGFR adjustment is central rather than incidental. Trend tested across
MAC grades.

**Aim 3.** Primary: MAC progression among patients with baseline mild or moderate MAC graded
at both timepoints, by ordinal logistic regression adjusted for baseline grade, with
inter-echo interval as an offset or covariate. Baseline severe excluded for the ceiling
reason in Section 4.1. The observed 7.8% regression rate among patients graded at both
timepoints provides an empirical estimate of grading misclassification and will be used to
bound the primary estimate in a quantitative bias analysis rather than merely acknowledged.
Secondary, conditional on the era diagnostic: incident MAC among baseline grade 0 by pooled
logistic regression with time varying MRA exposure.

**Aim 4.** MRA by MAC interaction term in the Aim 1 Cox model. Reported on **both**
multiplicative and additive scales, the latter via the relative excess risk due to
interaction, because additive interaction is what carries clinical meaning for treatment
decisions. Stratum specific hazard ratios reported alongside the interaction p value. This
aim is explicitly **hypothesis generating** and will be labelled as such in any manuscript.

**Missing data.** Multiple imputation by chained equations for covariates missing at random,
with the number of imputations set to the percentage of incomplete cases. MAC blank is
handled by convention, not imputation (Section 5.1). Missingness patterns reported per
variable before modelling.

**Controls for residual confounding.**
- *Positive control:* the MRA to hyperkalemia association is established. Recovering it
  validates that exposure ascertainment works. Failure to recover it invalidates the
  exposure definition and must halt Aim 3.
- *Negative control outcome:* an outcome with no plausible MR pathway, to be specified before
  analysis. Candidates for discussion: incident cataract, benign prostatic hyperplasia
  admission. A non-null association there indicates residual confounding.
- *E-value* for the primary Aim 3 and Aim 4 estimates.

---

## 9. Sample Size Considerations

No formal power calculation for Aims 1, 2 and 4 until exposure counts return. For Aim 3,
16,480 at risk with 3,893 incident events supports detection of modest associations, but the
binding constraint is the proportion MRA exposed, which is unknown until the prescription
query runs. Formal calculation deferred to version 1.0.

---

## 10. Sensitivity Analyses (pre-specified)

1. **Measurement noise in MAC grading.** See 10.1.
2. Require a two grade change to define progression.
3. Vary the minimum inter-echo interval (365, 545, 730 days).
4. Vary the minimum interval admission count for exposure ascertainment.
5. Restrict to echoes with non-blank `mac_severity` (tests the missing-as-negative convention).
6. Exclude the 55 `mac_present_ungraded` echoes, then include them as MAC positive.
7. E-value for unmeasured confounding on primary estimates.

### 10.1 The pre-specified failure condition, and its resolution

**Condition as pre-specified:** MAC grading is a qualitative reader judgement and MAC does
not biologically regress, so apparent regression estimates measurement noise directly. If
regression approached the observed progression rate, Aim 3 could not proceed as designed.

**Result, 2026-07-30.** The 4x4 transition matrix over 23,100 patients with paired echoes at
least 365 days apart:

| baseline \ follow-up | 0 | 1 mild | 2 mod | 3 severe |
|---|---|---|---|---|
| **0 none** | 12,587 | 3,265 | 575 | 53 |
| **1 mild** | 2,263 | 1,944 | 834 | 116 |
| **2 moderate** | 162 | 267 | 642 | 222 |
| **3 severe** | 23 | 8 | 51 | 88 |

Naive regression rate was 2,774 of 6,620 (**41.9%**), which exceeds progression (18.2%) by
more than two-fold. **The failure condition was met.**

**Diagnosis.** The failure is not what the condition assumed. Of 2,774 apparent regressions,
2,448 (88.2%) are movement to a blank field rather than to a lower grade; only 326 (11.8%)
are genuine grade disagreements. This is non-recording at follow-up, not reader disagreement
about severity.

**Resolution.** Restricting to patients explicitly graded at both timepoints:

| | n | rate |
|---|---|---|
| Progression (baseline mild or moderate) | 1,172 / 4,025 | 29.1% |
| Regression (genuine grade disagreement) | 326 / 4,172 | 7.8% |

Progression exceeds regression 3.7-fold, and 7.8% is a plausible inter-reader disagreement
rate for a qualitative three-level scale. Aim 3 proceeds on the restricted cohort, with the
7.8% carried forward as a quantified misclassification bound (Section 8).

The incident MAC analysis does not survive this restriction and is suspended (Section 4.3).

---

## 11. Reporting Guideline

STROBE for observational cohort reporting, with the RECORD extension for routinely collected
health data. Aim 4 additionally follows subgroup analysis reporting conventions: pre
specification stated, interaction test reported, and no claim made from stratum specific
estimates alone.

---

## 12. Ethics

This study uses MIMIC-IV v3.1, approved by the institutional review boards of Beth Israel
Deaconess Medical Center and MIT. Individual patient consent was waived because all data are
de-identified.

---

## 13. Decision Log

| Date | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 2026-07-30 | MAC from structured `mac_severity`, not note text | Dedicated structured field exists, populated on 29.4% of TTEs; avoids NLP and negation handling entirely | Regex over radiology reports with ConText negation |
| 2026-07-30 | Blank `mac_severity` treated as no MAC | Field vocabulary contains no negative token, so it is populated only when MAC is observed | Treat blank as missing and impute; restrict to non-blank (retained as sensitivity 5) |
| 2026-07-30 | Rejected "does MAC predict MRA associated hyperkalemia" | MAC is not on the causal path to potassium handling; eGFR and baseline K are upstream, directly measured, and already drive the clinical decision. A positive result would not change practice | Retained only as the positive control in Section 8 |
| 2026-07-30 | Reversed the mechanistic direction to MR drives calcification | Preclinical evidence supports MR activation promoting osteogenic transformation, with spironolactone and eplerenone attenuating it | Original framing of MAC as a contraindication marker |
| 2026-07-30 | Aim 3 primary is incident MAC, not progression | 16,480 at risk with 3,893 events versus 6,450 with 1,172; better powered and a cleaner statement of the biology | Progression as primary |
| 2026-07-30 | **REVERSED.** Aim 3 primary is progression among patients graded at both timepoints; incident MAC suspended | Transition matrix showed 41.9% apparent regression, 88% of it to a blank field. Baseline grade 0 conflates no MAC with not assessed, and 628 patients apparently developing moderate or severe MAC within a year is not biologically credible | Retain incident MAC with imputation of baseline status; abandon Aim 3 entirely |
| 2026-07-30 | Blank treated as missing for longitudinal aims, negative for cross-sectional aims | Same field, different failure modes. Blank is uninformative for prevalence (no negative token exists) but actively misleading for transitions | Single convention across all aims |
| 2026-07-30 | Mitral valve intervention excluded through follow-up, not only at baseline | An annuloplasty ring or prosthesis placed between echoes removes the gradable native annulus and manufactures apparent regression | Baseline-only exclusion |
| 2026-07-30 | 7.8% regression rate retained as a quantitative bias parameter | An empirical misclassification estimate is more useful bounding the primary estimate than as a limitations-section sentence | Report as a limitation only |
| 2026-07-30 | Baseline severe MAC excluded from progression analysis only | Ceiling effect, 0 of 170 progressed because no higher grade exists | Collapse moderate and severe; treat severe as its own outcome state |
| 2026-07-30 | Aim 3 population not restricted to HFpEF | MR-calcification biology is not HFpEF specific; restriction would discard most of the at-risk sample for no gain | Restrict all aims to HFpEF for consistency |
| 2026-07-30 | Efficacy framing rejected across all aims | Settled by randomised trials; observational re-estimation adds nothing and invites confounding-by-indication criticism | Direct comparative effectiveness analysis |

---

## 14. Prior Literature Positioning

Verified via web search on 2026-07-30. **PMIDs require confirmation against PubMed before
citation.**

- A 2025 *American Journal of Cardiology* TriNetX analysis (PMID 41138985) established that
  MAC predicts incident HFpEF (HR 3.80) and that MAC within HFpEF predicts heart failure
  hospitalisation (HR 1.24). **This study does not duplicate that finding.** It asks the
  question that follows from it: given that MAC marks a high risk phenotype, is that
  phenotype being treated, and does the mechanistically indicated drug act on it.
- The TriNetX work defined MAC from diagnosis codes. This study uses graded structured echo
  measurements with paired diastolic parameters, which claims based data cannot provide.
  That is the methodological differentiator.
- MAC and heart failure rehospitalisation subtypes: PMID 34240401 (n = 353).
- Finerenone versus spironolactone in HFpEF: PMID 41313540.
- No study was identified linking MAC to MRA or SGLT2i treatment response, or testing
  whether MRA exposure associates with MAC incidence or progression.
