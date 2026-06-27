# Decisions & Rationale — EchoNext-Mini × MIMIC-IV External Validation

Every non-obvious methodological choice, why we made it, and the alternative we tested. Read with `sql/01_echo_labels.sql`, `sql/02_analytic_cohort.sql`, and `code/`.

## Study design
- **Genre:** independent external validation + recalibration + fairness audit of the *publicly released* EchoNext-Mini model. Not a new model/outcome/trial.
- **Model artifact:** EchoNext-Mini (Hughes et al., NEJM AI 2026, DOI 10.1056/AIdbp2500516; weights/code at github.com/PierreElias/IntroECG → `7-EchoNext Minimodel`). Applied frozen, no retraining.
- **Population framing:** clinically selected — patients with clinically obtained ECGs linked to a subsequent clinically obtained TTE; NOT general-population screening. **Multi-setting** (inpatient ward 31.2% / ED-acute 28.8% / outpatient 24.4% / ICU 15.6%; see `sql/03_care_setting.sql` — outpatient corrected from an earlier 32.9% overcount after an admission_type audit) — NOT ICU-only.
- **Primary analytic unit:** one ECG per patient (most recent eligible) → bootstrap/CV folds are patient-level (no repeated-ECG leakage). All-ECG = optional secondary.

## Cohort construction (`02_analytic_cohort.sql`)
- **Pairing:** each ECG → nearest FOLLOWING TTE within 365 days (ECG precedes echo), matching EchoNext's "ECG up to 1 yr before TTE." Verified: differs from "any-TTE-within-1yr" label for only 0.4% → equivalent.
- **Deterministic tie-breaking:** most-recent ECG `ORDER BY ecg_time DESC, study_id DESC`; nearest echo `ORDER BY |minutes|, echo_id`. Makes rebuilds bit-reproducible (earlier non-determinism caused 0.15% drift).
- **Exclusions (EchoNext-faithful):** age<18; missing age/sex; ventricular-paced (report-text regex); poor-quality / lead-reversal / artifact (report-text); all-ECG-measurements missing (rr 29999 sentinel); **repaired/replaced (prosthetic)-valve echocardiograms EXCLUDED** — the Nature EchoNext paper explicitly excluded these (85,491 echos / ~11%), and the Mini inherits it as a subset. Identified in MIMIC via valve-replacement-structure fields (avr/mvr/tvr/pvr_structure non-null) + leaflet values (prosthesis/mechanical/bioprosthetic/annuloplasty/TAVR). Removes ~1,191 cohort patients (4.2%); SHD AUROC 0.792→0.790 (negligible).
- **Tabular features** derived from `machine_measurements` fiducials (units = ms; 29999 = missing): ventricular_rate=60000/rr; pr=qrs_onset−p_onset; qrs=qrs_end−qrs_onset; QTc=Bazett. Validated vs EchoNext Table 1 (vent 74/78, PR 160/154, QRS 93/88, QTc 440/444). **atrial_rate unavailable in MIMIC → imputed 0** (EchoNext pipeline convention); sensitivity (0 / ventricular proxy / 75 bpm) → AUROC 0.786 all (harmless).
- **Demographics:** age/sex from `patients` (100% complete). Race from `admissions.race`, most-frequent non-missing category per patient, bucketed (White/Black/Hispanic/Asian/Other/Unknown); 9% Unknown.

## Label harmonization (`01_echo_labels.sql`) — "mapped to closest available structured fields, not exact replication"
All from MIMIC structured echo (`structured_measurement`, **TTE only**), not free text. Thresholds = EchoNext. **Missing structured field → negative** (EchoNext convention). Decisions per label:

| Label | EchoNext | MIMIC primary | Rationale / alternative tested |
|---|---|---|---|
| LVEF ≤45% | numeric LVEF | best-available quant (biplane→3D→visual-range midpoint) ≤45 | MIMIC reports EF as a range; sensitivity = midpoint / lower-bound (AUROC 0.834/0.825, stable) |
| LVWT ≥1.3 cm | max(IVS, posterior wall) | max(septal, **inferolateral**) ≥1.3 | MIMIC has NO numeric posterior-wall/LVPW field; inferolateral ≈ but is **not literally** posterior wall. Sensitivity = categorical LVH. Matches prevalence 24.2% exactly. |
| TR Vmax ≥3.2 m/s | direct TR max velocity | **direct `tr_velocity` ≥3.2** | MIMIC HAS direct velocity (what EchoNext used). Derived gradient `tr_mmhg≥40.96` only 68.7% concordant → kept as sensitivity, not primary. |
| PASP ≥45 mmHg | direct numeric PASP | TR gradient + IVC-derived RAP ≥45 | MIMIC has **no single PASP field**. RAP from `ivc` category (ASE mmHg); missing/non-visualized IVC → RAP=3. Sensitivity = fixed RAP 3/5/10 (AUROC 0.769/0.767/0.763/0.746, stable). |
| RV dysfunction | categorical mod/severe | **categorical `rv_function` mod/severe** (incl. "depressed") | PRIMARY = faithful categorical. TAPSE<1.7 cm added only as a sensitivity (AUROC 0.838 cat vs 0.830 +TAPSE). |
| Pericardial effusion | moderate or large | moderate / moderate-large / large | trivial/very-small/small = negative; "fat pad" excluded; tamponade descriptors = optional sensitivity (not primary). |
| AS / AR / MR / TR / PR | moderate-or-greater | regex: (`^mod` OR `sever`) AND NOT `^mild` | mild-moderate (1-2+) = negative; unquantified "present/can't qualify" = negative (verified). |
| SHD composite | any of the above | GREATEST(all 11) | model's own composite head (output index 11). |

## Inference pipeline (`code/run_inference.py`, `smoke_test.py`)
- WFDB → model adapter: `wfdb.rdrecord(physical=False).d_signal` (raw int16 ADC ≈200/mV = MIMIC native, **no mV conversion**) → reorder by `sig_name` to model order **[I,II,III,aVR,aVL,aVF,V1–V6]** (note aVL before aVF; MIMIC native has aVF before aVL → must reorder) → downsample 500→250 Hz by `[::2]` → baseline-wander removal (median filter 0.2s+0.6s) → per-lead clip+z-score from `waveform_normalization_params.json` → tensor (N,1,2500,12). Tabular: scaler params from `tabular_transformer.joblib`; order [sex, age, vent_rate, atrial=0, pr, qrs, qtc]. Model: `ResNet1dWithTabular(7,16,12)`, load `weights.pt["model"]`, `sigmoid(model((wave,tab)))`.
- **Verification:** standalone inference == official EchoNext Lightning module to **1.19×10⁻⁷** on real records → pipeline correct; over-prediction is genuine model behavior.
- **Waveform integrity:** all `.dat` must be exactly 120,000 bytes (12 leads × 5000 samples × 2). Truncated downloads fail wfdb validation and are skipped (no silent corruption). Re-download check: `find ecg_needed -name '*.dat' ! -size 120000c`.

## Analysis (`code/analyze.py`, `sensitivity.py`, `calib_robust.py`)
- Discrimination: AUROC/AUPRC + 2,000-bootstrap 95% CI (patient-level).
- Calibration: slope (logistic of outcome on predicted logit), calibration-in-the-large, quantile-binned reliability.
- Recalibration: **5-fold out-of-fold** Platt + isotonic (NOT spline; not apparent/in-sample).
- Clinical utility: **decision-curve analysis excluded from the manuscript** — the cohort is clinically selected (all patients already echocardiographed), so net benefit for echo referral is not interpretable; utility is addressed narratively (a prospective unselected cohort would be required). `analyze.py` can still compute it, but it is not reported (Figure 3 = ROC only).
- Fairness: subgroup AUROC + 95% CI + calibration slope by sex/age/race.
- Sensitivities report **both** discrimination AND calibration (not AUROC alone).

## Key data facts (verified live)
- `mimiciv_echo.structured_measurement`: 91,372 subjects, 206,488 echo instances (measurement_id = one full echo, 114+ fields). Pair to ECG by subject_id + measurement_datetime (echo_study_list is a small 4,579-subj DICOM subset — DO NOT use for pairing).
- `mimiciv_ecg`: 800,036 ECGs; raw waveforms via S3 (NOT in BigQuery). ECG↔echo subject overlap 67,664.
- Date shifts consistent across modules (37,132 same-day ECG-echo pairs prove it).
