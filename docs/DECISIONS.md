# Label and method choices

Each choice, the alternative considered, and the reason. Where a choice could have gone either way,
the alternative is evaluated as a sensitivity analysis and reported in `results/tables/`.

## Labels

**Transthoracic studies only.** Stress and transoesophageal studies are excluded. EchoNext labels
derive from transthoracic echocardiography, and severity grading is not interchangeable across
modalities.

**Ejection fraction: best available quantitative value.** Biplane, else three-dimensional, else the
midpoint of the reported range. MIMIC-IV-ECHO reports ejection fraction as a range far more often
than as a single biplane or three-dimensional value, so the midpoint carries most of the cohort.
Alternatives evaluated: midpoint only, and the lower bound of the range.

**Wall thickness: maximum of septal and inferolateral.** EchoNext uses the maximum of septum and
posterior wall. MIMIC-IV-ECHO records septal and inferolateral thickness but has no posterior-wall
field anywhere among its transthoracic measurements, so the inferolateral wall, which is
anatomically adjacent, is substituted. The cost of this substitution cannot be measured in MIMIC-IV
because the posterior wall is absent; it is bounded instead on the EchoNext benchmark, which
reports both walls, by comparing the true definition against single-wall definitions.

**Aortic stenosis: graded severity, with quantitative fallback.** The graded severity field is
populated in a minority of studies, whereas peak aortic velocity is available in most. Using the
graded field alone would leave the large majority of studies classified negative by default.
Studies without a graded severity are therefore classified by guideline thresholds on peak velocity,
mean gradient or valve area. The graded field takes precedence where present, because it already
accounts for flow state: MIMIC-IV-ECHO explicitly records categories attributing an increased
velocity or gradient to high output or to regurgitation rather than to stenosis, and those are held
negative. The severity-field-only definition is retained as a sensitivity analysis.

**Pulmonary artery systolic pressure: reconstructed.** From the tricuspid regurgitation gradient
plus right atrial pressure estimated from the inferior vena cava, using American Society of
Echocardiography categories. MIMIC-IV-ECHO also carries a pulmonary hypertension severity field with
higher availability, but that field is keyed to the tricuspid gradient rather than to systolic
pressure, so it maps less faithfully to the EchoNext threshold. It is reported as a
coverage sensitivity analysis rather than as the primary definition.

**Right ventricular dysfunction: categorical descriptors.** Tricuspid annular plane systolic
excursion is evaluated as an alternative. Studies in which right ventricular function is explicitly
recorded as unassessable are treated as negative in the primary analysis, consistent with the
missing-as-negative convention, and excluded in a sensitivity analysis.

**Regurgitation lesions: moderate or greater.** Mild-to-moderate grades are held negative, as are
unquantified "present" descriptors. Pulmonic regurgitation has no explicit moderate tier in
MIMIC-IV-ECHO; the "significant" grade is the closest analogue and is treated as positive.

**Missing structured fields are negative.** This follows the EchoNext labelling convention, and
preserving it keeps the estimand comparable with the model's development. It is not assumed to be
harmless: field availability is carried through per label, and a complete-case restriction is
reported for every label with incomplete availability. The two estimates bound the truth in opposite
directions and neither is unbiased.

## Preprocessing

**Atrial rate and PR interval are set to zero when unavailable, not imputed.** This is the released
preprocessing specification, which treats an absent value as informative rather than missing, on the
basis that it usually reflects atrial arrhythmia. Imputing the median instead assigns these records
a value near the population centre, which is a substantial error in the opposite direction.

**Intervals are computed from fiducial points.** MIMIC-IV-ECG distributes fiducial markers rather
than derived intervals, so PR interval, QRS duration and QT are obtained by subtraction. This is
arithmetic on machine-produced values, not a re-derivation from the waveform. QT is corrected by
Bazett's formula, the default of the platform on which the model was developed.

**Scaler constants are read from JSON, not from the released joblib.** The joblib was created with
scikit-learn 1.1.3 and cannot be applied on 1.2 or later. Its stored arrays unpickle correctly on
any version, so they are extracted once and the arithmetic performed directly. This removes a
version dependency from the inference path.

## Analysis

**Calibration slopes use unpenalised logistic regression.** The default regularisation in common
implementations shrinks the slope toward zero, which biases the very quantity being reported.

**Mean predicted probability is reported alongside calibration-in-the-large.** The two together make
the scale of the predictions unambiguous.

**Brier skill score rather than raw Brier.** The raw Brier score is dominated by prevalence and is
not comparable across labels of differing frequency. The skill score is referenced to a predictor
assigning the observed prevalence to everyone, which is the relevant null.

**Prevalence-normalised area under the precision-recall curve.** A no-skill classifier achieves an
area equal to prevalence, so the raw value overstates performance for common outcomes.

**Bootstrap resamples are shared across labels and subgroups.** Identical resample indices are reused
so that intervals are comparable rather than independently noisy. Resamples containing no events are
discarded, which slightly reduces the effective count for the rarest labels.

**Prioritisation is reported capacity-independently.** Published designs fix a monthly imaging
capacity against a queue that clears within the study horizon. This cohort accrued over fourteen
years and is not a referral queue, so cumulative yield as a function of the proportion imaged is
reported instead. The comparator is a random ordering, because no referral sequence exists in the
data; real referral is already clinically prioritised, so the increment over usual care is smaller
than the comparison implies.
