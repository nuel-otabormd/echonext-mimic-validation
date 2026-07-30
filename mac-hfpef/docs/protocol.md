# Study Protocol

## Mitral Annular Calcification as a Therapeutic Phenotype in Heart Failure with Preserved Ejection Fraction: Severity-Graded Characterisation, Outcomes, and Mineralocorticoid Receptor Antagonist Exposure

**Running title:** MAC as a therapeutic phenotype in HFpEF
**Version:** 1.0
**Date:** 2026-07-30
**Author:** Emmanuel Otabor, MD
**Reporting guideline:** STROBE, with the RECORD extension for routinely collected health data

---

## Structured Abstract

**Background.** Mitral annular calcification (MAC) is an active osteogenic process rather
than passive degeneration. Mineralocorticoid receptor (MR) activation promotes osteoblastic
differentiation of vascular smooth muscle cells, and MR antagonism attenuates
phosphate-induced osteogenic transformation in preclinical models. MAC is independently
associated with incident heart failure with preserved ejection fraction (HFpEF) and with
worse outcomes once HFpEF is established. Whether the phenotype defined by calcification
receives, or responds to, the therapy mechanistically directed at it has not been examined in
humans.

**Objectives.** To characterise severity-graded MAC as a diastolic phenotype in HFpEF and
quantify its association with one-year outcomes; to determine whether MAC is associated with
lower receipt of guideline-directed medical therapy; to estimate the association between
mineralocorticoid receptor antagonist (MRA) exposure and echocardiographic MAC progression;
and to test whether MAC modifies the association between MRA exposure and mortality.

**Methods.** Retrospective cohort study in MIMIC-IV v3.1 linked to MIMIC-IV-ECHO structured
echocardiographic measurements. MAC severity is taken from a structured field graded mild,
moderate or severe, available on 52,809 of 179,928 transthoracic echocardiograms across
85,292 patients. The longitudinal cohort comprises 6,654 patients with MAC explicitly graded
on two studies at least 365 days apart. MRA exposure is derived from reconciled home
medication across the inter-echocardiogram interval, with assertion status resolved by a
ConText negation pass. The primary progression analysis uses logistic regression with inverse
probability of treatment weighting and doubly robust estimation, adjusted for baseline MAC
grade and interval length. Survival analyses use Cox proportional hazards; therapy receipt
uses modified Poisson regression with robust variance.

**Results.** To be completed.

**Conclusions.** To be completed.

---

## 1. Background and Rationale

Mitral annular calcification affects a substantial minority of patients undergoing
echocardiography and rises steeply with age, chronic kidney disease and diabetes. It was long
regarded as an incidental degenerative finding. That view has been displaced by evidence that
MAC reflects an active, regulated osteogenic process sharing biology with vascular and
calcific aortic valve disease, and by epidemiological work establishing MAC as an independent
predictor of cardiovascular morbidity and mortality.

Recent evidence links MAC specifically to HFpEF. In a large multicentre analysis of
hospitalised patients without prior heart failure, MAC predicted incident HFpEF at one year,
and among patients with established HFpEF, MAC was associated with excess heart failure
hospitalisation and all-cause hospitalisation. That work defined MAC from diagnosis codes and
therefore could not characterise severity, diastolic physiology, or the relationship between
calcific burden and therapy.

A mechanistic rationale connects MAC to mineralocorticoid receptor blockade. Aldosterone
acting through the MR promotes osteoblastic differentiation of vascular smooth muscle cells
via PIT1 upregulation, and both spironolactone and eplerenone abolish phosphate-induced
osteogenic transformation in human aortic smooth muscle cells. Spironolactone reduces arterial
medial calcification in uremic animal models, and MR pathway signalling has been implicated in
calcific aortic stenosis. Clinical translation is limited to a small pilot in dialysis
patients examining coronary calcification. No human study has examined MRA exposure in
relation to mitral annular calcification.

This creates a clinically consequential gap. If MAC marks a phenotype in which MR-driven
calcification is active, then MAC is a candidate marker of therapeutic relevance rather than
an incidental finding. If patients with MAC are additionally less likely to receive MRA
therapy, as their coexisting renal impairment would predict, then a therapeutic mismatch
exists between the phenotype and its mechanistically indicated treatment.

## 2. Objectives

**Aim 1.** Characterise severity-graded MAC as a diastolic phenotype in HFpEF, and estimate
its association with one-year all-cause mortality and days alive and out of hospital.

**Aim 2.** Determine whether MAC severity is associated with lower receipt of
guideline-directed medical therapy, specifically MRAs, after accounting for renal function.

**Aim 3.** Estimate the association between MRA exposure and echocardiographic MAC
progression across paired studies. *(Primary novel objective.)*

**Aim 4.** Test whether MAC status modifies the association between MRA exposure and one-year
mortality. *(Hypothesis-generating.)*

## 3. Design

Retrospective cohort study using routinely collected clinical data. Aims 1, 2 and 4 are
anchored on an index echocardiogram. Aim 3 is a longitudinal analysis of paired
echocardiograms.

This study estimates associations and effect modification. It does not estimate treatment
efficacy. The efficacy of MRAs in heart failure is established by randomised evidence, and
observational re-estimation in a single-centre cohort would be uninformative. Every objective
is framed around a question randomised trials could not address: phenotype characterisation,
prescribing behaviour, and a calcification endpoint no trial has measured.

## 4. Setting and Data Sources

MIMIC-IV v3.1, a single-centre database from a tertiary academic medical centre covering 2008
to 2022, linked by `subject_id` to MIMIC-IV-ECHO structured echocardiographic measurements.
Home medication exposure is derived from a medication reconciliation pipeline integrating
admission medication reconciliation, discharge and admission notes, and inpatient prescribing
records, with a per-record confidence grade.

Access requires PhysioNet credentialing, CITI training, and a signed data use agreement.

## 5. Participants

### 5.1 Longitudinal cohort (Aim 3)

Adults aged 18 years or over with two or more transthoracic echocardiograms separated by at
least 365 days, with MAC explicitly graded on both the index and follow-up study. A minimum
interval of one year is required because MAC progression over shorter periods cannot be
distinguished from inter-reader variability.

Patients with mitral valve replacement, repair or annuloplasty at any point up to and
including the follow-up study are excluded, since a prosthesis or annuloplasty ring removes
the gradable native annulus. Patients with severe MAC at baseline are excluded from the
progression analysis because the grading scale has no higher category, and are retained for
all other objectives.

The resulting cohort comprises 6,654 patients with baseline mild or moderate MAC.

### 5.2 HFpEF cohort (Aims 1, 2 and 4)

Adults aged 18 years or over with heart failure recorded by ICD-9 code 428.x or ICD-10 code
I50.x at or before the index admission, and left ventricular ejection fraction of 50% or
greater on the index echocardiogram. Both coding systems are required because the database
spans the ICD transition.

Patients with prior mitral valve replacement or repair, or with missing ejection fraction on
the index study, are excluded.

The populations differ deliberately between objectives. The MR-calcification mechanism is not
specific to HFpEF, and restricting Aim 3 to HFpEF would discard the majority of the at-risk
sample without scientific justification.

## 6. Variables

### 6.1 Mitral annular calcification

MAC is taken from a structured echocardiographic field graded mild, moderate or severe, and
modelled as an ordinal variable (0 none, 1 mild, 2 moderate, 3 severe). The field is populated
only when calcification is observed and contains no negative token, so an unpopulated field is
treated as absence of MAC for cross-sectional objectives.

For the longitudinal objective this convention is not applied. MAC must be explicitly graded
at both timepoints, because an unpopulated follow-up field indicates non-recording rather than
resolution, and MAC does not regress.

### 6.2 Mineralocorticoid receptor antagonist exposure

Exposure is defined from reconciled home medication across the interval between paired
echocardiograms, restricted to records of high or medium ascertainment confidence. Records
sourced solely from inpatient prescribing without corroborating home-medication evidence are
excluded, as these reflect medication ordered during an admission rather than chronic therapy.

Note-derived mentions are resolved for assertion status before contributing to exposure.
Mentions recorded as discontinued, as parse artefacts failing lexicon matching, or as
as-needed rather than scheduled therapy are not counted. Mentions recorded as temporarily
held are retained, since interruption during an acute admission does not end chronic therapy.
These exclusions affect 0.75% of mineralocorticoid receptor antagonist mentions and are
applied for correctness rather than because they materially alter exposure classification.
The medication parser reads the structured admission medication list, which contains little
narrative, so assertion ambiguity is uncommon by construction.

Exposure is modelled as the proportion of interval admissions with an MRA recorded, and
dichotomised at any exposure for the primary analysis. Dose intensity is derived from absolute
daily milligrams referenced to heart-failure target dosing.

SGLT2 inhibitors were evaluated and are not analysed. Only 54 patients in the longitudinal
cohort had any exposure, reflecting the agents' market entry relative to the study period.
This count is reported once in the cohort description.

### 6.3 Outcomes

**MAC progression** (Aim 3, primary): an increase in MAC grade between paired
echocardiograms.

**One-year all-cause mortality** (Aims 1 and 4): from recorded date of death, analysed as time
to event with administrative censoring.

**Days alive and out of hospital at one year** (Aim 1): 365 minus inpatient days, set to zero
on death.

**MRA receipt** (Aim 2): an MRA recorded on the reconciled home medication list at the index
admission.

**Secondary outcomes:** all-cause and heart failure readmission at 30 days and one year;
recurrent admission count; intensive care admission and length of stay; acute kidney injury by
KDIGO stage 2 or above; hyperkalemia at thresholds of 5.5 and 6.0 mmol/L; discharge
disposition including hospice.

### 6.4 Covariates

Age, sex, race, insurance status, admission type and care setting at the index study.
Comorbidity by Charlson index with component conditions retained individually. Renal function
by baseline creatinine and estimated glomerular filtration rate, and baseline serum potassium.
Echocardiographic covariates comprising ejection fraction, left ventricular wall thickness,
mitral E/A ratio, septal and lateral E prime, deceleration time, pulmonary artery systolic
pressure and tricuspid annular plane systolic excursion. Concomitant renin-angiotensin system
inhibitor, beta blocker and diuretic exposure. Atrial fibrillation by diagnosis code.

For Aim 3, baseline MAC grade is a required covariate, as baseline calcific burden is the
dominant published predictor of progression. Interval length is included because a longer
interval mechanically permits greater progression.

## 7. Bias

Confounding by indication is the principal threat to Aim 3. Patients receiving MRAs have more
severe heart failure, worse renal function and greater calcific burden, each independently
predicting progression, so unadjusted estimates are biased toward the null or beyond it.

Exposure ascertainment is intermittent, as medications are observed at admissions rather than
continuously. Patients with more admissions have more opportunities to be classified as
exposed, and admission frequency correlates with severity.

Selection into having a repeat echocardiogram is not random, and requiring a graded follow-up
study conditions on the outcome being ascertainable.

Each is addressed in Sections 8 and 10.

## 8. Statistical Methods

**Aim 1.** Cox proportional hazards regression for one-year mortality, with MAC entered as an
ordinal trend term and, separately, as categorical indicators. The proportional hazards
assumption is assessed by scaled Schoenfeld residuals; if violated, a time-varying coefficient
or restricted follow-up is used. Days alive and out of hospital is analysed by quantile
regression, given right skew and a point mass at zero. Diastolic parameters are compared
across MAC grades by standardised mean differences and by multivariable-adjusted mean
differences.

**Aim 2.** Modified Poisson regression with robust variance, yielding risk ratios. Odds ratios
are avoided because MRA receipt is common and would be overstated. Estimates are adjusted for
estimated glomerular filtration rate, potassium, age, sex and comorbidity, since the question
is whether any deficit persists beyond what renal function justifies. Trend across MAC grades
is tested.

**Aim 3.** The primary analysis is logistic regression for any grade increase, with inverse
probability of treatment weighting and doubly robust estimation combining the weighted design
with an outcome model. Covariate balance is assessed by standardised mean differences with a
threshold of 0.1, and positivity by inspection of the propensity score distribution.
Adjustment includes baseline MAC grade and log interval length. Baseline severe MAC is
excluded. A secondary ordinal model examines magnitude of grade change. A pre-specified
dose-response analysis compares no exposure, exposure below target dose, and exposure at
target dose or above, tested for trend.

**Aim 4.** A multiplicative interaction term between MRA exposure and MAC status is fitted in
the Aim 1 model. Additive interaction is reported as the relative excess risk due to
interaction, since additive scale interaction carries the clinical meaning for treatment
decisions. Stratum-specific estimates are reported alongside the interaction test and are not
interpreted independently of it.

**Missing data.** Multiple imputation by chained equations for covariates missing at random,
with the number of imputations set to the percentage of incomplete cases and estimates
combined by Rubin's rules. Missingness is tabulated per variable before modelling. MAC
assertion is handled by the conventions in Section 6.1 rather than by imputation.

**Residual confounding.** Three controls are pre-specified. A positive control tests the
established association between MRA exposure and hyperkalemia; failure to recover it
invalidates exposure ascertainment and halts Aim 3. A negative control outcome with no
plausible mineralocorticoid pathway is specified before analysis, where a non-null association
indicates residual confounding. E-values are computed for the primary Aim 3 and Aim 4
estimates.

All tests are two-sided at the 5% level. No adjustment for multiplicity is applied across the
four objectives, which are treated as separate pre-specified questions rather than as a family;
this is stated explicitly and secondary outcomes are reported as exploratory.

## 9. Sample Size

No formal power calculation is performed, as the cohort is fixed by data availability. The
longitudinal cohort comprises 6,654 patients with 1,607 progression events, of whom 644 are
MRA-exposed under the primary definition contributing 146 events. This supports estimation of
moderate associations with confidence intervals excluding large effects, and is stated as a
precision constraint rather than presented as adequate power for small effects. The events per
variable ratio permits generous covariate adjustment.

## 10. Sensitivity Analyses

1. Exposure defined by pooled ascertainment across all sources, and separately by requiring
   admission medication reconciliation.
2. Progression defined by a two-grade change.
3. Minimum inter-echocardiogram interval varied at 365, 545 and 730 days.
4. Minimum number of interval admissions varied for exposure ascertainment.
5. Restriction to records where home medication was fully ascertainable.
6. Cross-sectional analyses restricted to echocardiograms with an explicitly graded MAC field.
7. Quantitative bias analysis using the empirically observed grading disagreement rate.
8. E-value for unmeasured confounding on primary estimates.

## 11. Ethics

This study uses MIMIC-IV v3.1, approved by the institutional review boards of Beth Israel
Deaconess Medical Center and the Massachusetts Institute of Technology. Individual patient
consent was waived because all data are deidentified.

## 12. Limitations

Single-centre data limit generalisability, and the population is weighted toward acute and
critical care. Medication exposure is observed at admissions rather than continuously and
reflects prescription rather than adherence, as outpatient dispensing is unavailable. Only
the admission medication list is machine-readable in this dataset, so medication changes
occurring during an admission are not observed; exposure is therefore prevalent rather than
incident, and an initiator design with a defined time zero was not achievable. This is the
principal design limitation of the progression analysis and the clearest target for future
work.
Readmission capture is limited to the contributing institution. MAC grading is a qualitative
reader judgement, with an empirically estimated disagreement rate carried into sensitivity
analysis. Mortality ascertainment is reliable within approximately one year of discharge.
Residual confounding by indication cannot be excluded and is quantified rather than claimed to
be absent.

## 13. Data and Code Availability

All analytic code, SQL, and the full decision record are deposited publicly. Patient-level
data are not redistributable and require independent PhysioNet credentialing.
