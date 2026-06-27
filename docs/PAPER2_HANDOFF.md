# Paper 2 Handoff — Prognostic Value of the AI-ECG SHD Score

Start here for Paper 2. Paper 1 (external validation) is DONE and locked; its cohort + model scores feed Paper 2 directly.

## Paper 2 concept
**Does the continuous EchoNext-Mini SHD score predict downstream outcomes (mortality, HF hospitalization), incremental to the echo result and clinical variables — including in "echo-negative" patients (ECG-SHD+ / echo−)?** The discordant-positive phenotype is the novel narrative ("apparent false positives may be early/occult disease").

## What already exists (reuse — do NOT rebuild)
- **Scored cohort:** `your-gcp-project.echonext.analytic_cohort` (45,878 one-per-patient; ECG features, 12 echo labels, echo_id, ecg_time, demographics).
- **Model predictions:** `~/Desktop/RESEARCH/EchoNext-repo/results_full/{probs.npy (45,878×12), kept_paths.txt}` — 1:1 aligned, deterministic. Column order: lvef_lte_45, lvwt_gte_13, aortic_stenosis, aortic_regurg, mitral_regurg, tricuspid_regurg, pulm_regurg, rv_dysfunction, pericardial, pasp_gte_45, tr_max_gte_32, **shd (index 11)**.
- **Pipeline/inference** all in `code/` (can score additional ECGs if needed, e.g., all-ECG or a pre-echo-only design).

## What Paper 2 needs to add
- **Outcomes (BigQuery `mimiciv_3_1_hosp`):** `patients.dod` (date of death), `admissions` (admittime/dischtime/deathtime, hospital_expire_flag), HF readmissions (ICD `diagnoses_icd` I50*, dischtime intervals). Consider competing-risk (death vs HF) + landmark from ECG date.
- **Design:** ECG date = index/landmark; follow-up to death/readmission. Cox / Fine-Gray; primary = all-cause mortality, secondary = HF hospitalization. Test SHD-score association adjusted for the echo SHD label + age/sex/comorbidities → "incremental to echo."
- **Discordance:** stratify ECG-SHD+ (high score) × echo-SHD− vs concordant groups; outcomes + (if serial echos) incident SHD on follow-up TTE.

## Framing / novelty guardrails (verified in Paper 1 lit review)
- "False-positive = future disease" is ESTABLISHED for LOW-EF only (Attia HR ~4; normal-EF-worse-outcomes PMC11450892). rECHOmmend (Circulation 2022, DOI 10.1161/CIRCULATIONAHA.121.057869) predicts incident SHD within 1 yr. → Paper 2's OPEN lane = full multi-condition SHD composite + HARD outcomes (mortality/HF) + this cohort + the released model. Frame accordingly; do not overclaim novelty on incident-SHD detection.
- Caveat: MIMIC post-discharge follow-up is limited (single-center); state it.

## Where everything lives
- Repo: `~/Desktop/RESEARCH/echonext-mimic-validation/` (this folder, shareable).
- Working scripts + probs + cohort CSVs: `~/Desktop/RESEARCH/EchoNext-repo/` and `~/Desktop/RESEARCH/*.csv`.
- BigQuery dataset: `echonext` (set your own billing project).
- Full method/decision detail: `docs/DECISIONS_AND_RATIONALE.md`; all Paper 1 numbers: `results/RESULTS_SUMMARY.md`.
