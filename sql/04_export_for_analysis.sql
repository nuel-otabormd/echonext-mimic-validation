-- 04_export_for_analysis.sql
-- Export the BigQuery analytic_cohort + a race lookup to the two local CSVs that the Python
-- analysis/figure scripts read (cohort_oneperpt_full.csv, subject_race.csv).
-- Run query (A) and query (B) SEPARATELY, saving each to its own CSV, e.g.:
--   bq query --use_legacy_sql=false --format=csv --max_rows=100000 "$(sed -n '/^-- (A)/,/;/p' sql/04_export_for_analysis.sql | grep -v '^--')" > cohort_oneperpt_full.csv
-- or just paste the query into the BigQuery console and "Save results > CSV (local file)".
-- Both are patient-level — keep local, do NOT commit.

-- (A) cohort_oneperpt_full.csv  (one most-recent ECG per patient; columns the scripts expect)
SELECT
  ecg_path, gender, age_at_ecg,
  ventricular_rate, pr_interval, qrs_duration, qt_corrected,
  lvef_lte_45, lvwt_gte_13,
  aortic_stenosis_modsev, aortic_regurg_modsev, mitral_regurg_modsev,
  tricuspid_regurg_modsev, pulm_regurg_modsev, rv_dysfunction_modsev,
  pericardial_modlarge, pasp_gte_45, tr_max_gte_32, shd
FROM `your-gcp-project.echonext.analytic_cohort`
WHERE most_recent_per_patient;

-- (B) subject_race.csv  (subject_id, race) — most-frequent non-missing race per patient, bucketed.
SELECT subject_id,
  CASE
    WHEN race LIKE 'WHITE%'    THEN 'White'
    WHEN race LIKE 'BLACK%'    THEN 'Black'
    WHEN race LIKE 'HISPANIC%' OR race LIKE 'SOUTH AMERICAN%' THEN 'Hispanic'
    WHEN race LIKE 'ASIAN%'    THEN 'Asian'
    WHEN race IN ('UNKNOWN','UNABLE TO OBTAIN','PATIENT DECLINED TO ANSWER') THEN 'Unknown'
    ELSE 'Other' END AS race
FROM (
  SELECT subject_id, race, ROW_NUMBER() OVER (PARTITION BY subject_id ORDER BY COUNT(*) DESC) AS rn
  FROM `physionet-data.mimiciv_3_1_hosp.admissions`
  WHERE race IS NOT NULL AND race != ''
  GROUP BY subject_id, race)
WHERE rn = 1;
