# Methods

The pipeline in order, with the reasoning behind each choice. Aggregate results are in `results/`.

## 1. Data sources

- **MIMIC-IV v3.1** (`mimiciv_3_1_hosp`, `mimiciv_3_1_icu`), **MIMIC-IV-ED**, **MIMIC-IV-ECG v1.0**
  and **MIMIC-IV-ECHO v1.0**, all read from the `physionet-data` BigQuery datasets.
- MIMIC-IV-ECHO v1.0 has two components: structured echocardiographic measurements from 206,488
  studies in 91,372 patients imaged between 2008 and 2022, and a smaller imaging subset of 7,243
  studies in 4,579 patients. Labels here derive from the structured measurements. Earlier work
  referring to roughly 4,579 patients is describing the imaging component, which is a different
  resource.
- The **released EchoNext-Mini benchmark**: 100,000 electrocardiograms from 36,286 patients with a
  published train, validation and test split. The held-out test set of 5,442 records is used as
  distributed, without further preprocessing.

## 2. Echocardiographic labels (`sql/01_echo_labels.sql`)

Twelve labels are derived from `structured_measurement`, restricted to transthoracic studies. Of the
186 distinct transthoracic measurement fields, the mapping uses those listed in `docs/DECISIONS.md`.

**Continuous fields.** Left ventricular ejection fraction takes the best available quantitative
value: biplane, else three-dimensional, else the midpoint of the reported range. In practice the
range midpoint supplies the great majority of studies. Wall thickness, tricuspid regurgitation
velocity and gradient, inferior vena cava diameter and tricuspid annular plane systolic excursion
are bounded by explicit plausibility limits.

**Categorical fields.** Aortic, mitral, tricuspid and pulmonic regurgitation, right ventricular
function and pericardial effusion are graded moderate-or-greater from the free-text severity fields.
Every regular expression was checked against the complete set of values each field takes.

**Aortic stenosis** is derived differently from the severity field alone. That field is populated in
only a minority of studies, whereas peak aortic velocity is available in the large majority. Studies
without a graded severity are therefore classified using guideline quantitative thresholds (peak
velocity ≥3.0 m/s, mean gradient ≥20 mmHg, or valve area ≤1.5 cm²), except where the graded field
explicitly attributes an increased velocity or gradient to high flow rather than to stenosis. This
follows the original EchoNext rule, which also used peak aortic velocity.

**Pulmonary artery systolic pressure** is reconstructed from the tricuspid regurgitation gradient
plus right atrial pressure estimated from the inferior vena cava, using American Society of
Echocardiography categories.

**Missing structured fields are treated as negative**, following the EchoNext labelling convention.
Field availability varies substantially by label and is carried through the pipeline as a per-label
indicator, so that a complete-case sensitivity analysis can be run for every label without a second
export.

## 3. Cohort (`sql/02_analytic_cohort.sql`)

Each electrocardiogram is paired with its nearest following transthoracic echocardiogram within 365
days, the electrocardiogram preceding the echocardiogram, with deterministic tie-breaking. The
echocardiogram must report ejection fraction and at least one valve finding. Exclusions follow the
original EchoNext methods: prosthetic or repaired valves, age under 18, missing age or sex,
ventricular pacing, poor quality or lead reversal, and invalid measurements. One electrocardiogram
per patient is retained, the most recent eligible.

Recording bandwidth, filtering and cart identifier are carried through, as is an indicator for an
unmeasurable PR interval, so that performance can be examined by acquisition setting and the effect
of the PR convention can be quantified.

## 4. Care setting (`sql/03_care_setting.sql`)

Assigned at the time of the electrocardiogram by matching its timestamp against concurrent encounter
windows, with precedence intensive care, then emergency department, then inpatient, then
acute presentation, then outpatient. Records in the residual that fall within one day on or before
an emergency, urgent or observation admission are reassigned to acute presentation. The broad
three-level grouping derives from the same precedence chain rather than being computed independently,
so the two cannot disagree.

## 5. Race and ethnicity (`sql/04_export_for_analysis.sql`)

Assigned from hospital admission **and emergency department** records. Raw values are grouped into
reporting categories before counting; the most frequent informative category is taken; any
informative category is preferred over Unknown; ties resolve by the most recent encounter, then by
category name. Patients with no informative category anywhere are classified Unknown.

Each element matters. Grouping before counting prevents a patient with two differently coded records
of the same ethnicity from being assigned a third category that happens to appear twice. Preferring
informative categories prevents a recorded ethnicity being overridden by a non-answer. Using both
sources materially reduces the Unknown group. Explicit tie-breaking makes the assignment
reproducible.

## 6. Model implementation (`code/run_inference.py`)

The released weights are applied frozen. Waveforms are read from Waveform Database records,
reordered to the model lead order, decimated from 500 Hz to 250 Hz, baseline-wander corrected,
clipped and normalised with the released per-lead parameters.

Seven tabular features are supplied: sex, age, ventricular rate, atrial rate, PR interval, QRS
duration and corrected QT interval. MIMIC-IV-ECG distributes fiducial points rather than derived
intervals, so PR interval, QRS duration and QT are computed from those points, with QT corrected by
Bazett's formula. **Atrial rate and PR interval are set to zero before scaling when unavailable,
rather than imputed to the median**, following the released preprocessing specification. Atrial rate
is not reported in MIMIC-IV-ECG and is therefore zero throughout; the PR interval is unmeasurable in
a substantial minority of records, most often in atrial fibrillation.

Scaler and imputer constants are read from `code/tabular_transform_params.json`. The released joblib
cannot be applied on scikit-learn 1.2 or later, so reading the constants directly and performing the
arithmetic in NumPy removes any dependence on the installed version.

## 7. Verifying the implementation (`code/equivalence_test.py`)

Two independent checks.

**Component level.** Constructed tabular features are compared against the official
`tabular_transformer`, and model outputs against the official Lightning module, on a test set
stratified to include records with an unmeasurable PR interval, unmeasurable atrial rate, missing
QRS duration or QT, and extreme measurement values. A random sample would very likely contain none
of these. Agreement is exact.

**End to end.** The same frozen weights are applied to the released benchmark test set, using the
distributed arrays without modification, and per-label discrimination is compared against the values
published for that model.

## 8. Statistical analysis (`code/analyze.py`)

One module, one label source, one estimator, one seed. Every reported quantity comes from a single
results object, and the tables are generated from it rather than transcribed.

Per label: prevalence, **mean predicted probability**, calibration-in-the-large (observed prevalence
minus mean predicted probability, on the probability scale), calibration slope from **unpenalised**
logistic recalibration on the predicted logit, area under the receiver operating characteristic
curve, area under the precision-recall curve and its prevalence-normalised form, Brier score, and
Brier skill score relative to a predictor assigning the observed prevalence to everyone.

Confidence intervals are patient-level percentile bootstrap, 2,000 resamples, fixed seed, with
identical resample indices reused across labels and subgroups; resamples containing no events are
discarded.

Reporting mean predicted probability alongside calibration-in-the-large is deliberate: the two
together make the scale of the predictions unambiguous, which a single summary does not.

## 9. Recalibration

Two strategies, reported side by side.

**Prior shift**, adding the logit of the label's prevalence in the released training split to the
predicted logit. This requires no outcome data from the target setting and is therefore applicable
where local echocardiography is unavailable. It is a standard prior-probability-shift correction.

**Local Platt scaling**, five-fold out of fold, fitted separately for each label. This requires local
labels.

The prior shift corrects to the training prevalence, not the local one, so it under-corrects where
local prevalence diverges far from training prevalence. Both are reported so the trade-off is
visible.

## 10. Subgroups and sensitivity analyses

Subgroups: sex, age group, race and ethnicity, care setting, ECG acquisition setting, and records
with an unmeasurable PR interval.

Sensitivity analyses: electrocardiogram-to-echocardiogram linkage window; alternative definitions for
right ventricular dysfunction, tricuspid regurgitation velocity, aortic stenosis, wall thickness and
pulmonary artery systolic pressure; exclusion of studies in which right ventricular function was
recorded as unassessable; and, for every label with incomplete field availability, restriction to
studies in which the field was populated.

The complete-case restriction is reported as a bound rather than as a corrected estimate. Records
with an absent field are treated as negative and score systematically lower, which inflates the
all-records estimate; fields are populated by clinical indication, so retained negatives carry lesser
degrees of the same pathology, which deflates the complete-case estimate. Neither is unbiased.

## 11. Prioritisation (`code/triage_analysis.py`)

The composite score is evaluated as a prioritisation tool under constrained echocardiographic
capacity, and by decision-curve analysis of net benefit.

Published capacity-constrained designs fix a monthly imaging capacity against a queue that clears
within the study horizon. That does not transfer here: this cohort accrued over fourteen years and
is not a referral queue, so imposing a monthly capacity produces uninterpretable horizons. Cumulative
diagnostic yield as a function of the proportion of the cohort imaged is reported instead, which is
capacity-independent.

The unprioritised comparator is a random ordering of the same cohort, because MIMIC-IV does not
record a referral sequence. Real referral is already clinically prioritised, so the increment over
usual care is smaller than the comparison implies. At the observed composite prevalence the maximum
achievable enrichment is bounded by the reciprocal of prevalence, and the observed values sit close
to that ceiling. This is a referred population, not a screening population.
