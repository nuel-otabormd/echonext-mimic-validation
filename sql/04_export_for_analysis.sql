-- 04_export_for_analysis.sql  (REBUILD v2, Aug 2026)
-- Export the BigQuery analytic_cohort + a race lookup to the local CSVs that the Python
-- analysis/figure scripts read.
-- Run query (A) and query (B) SEPARATELY, saving each to its own CSV, e.g.:
--   bq query --use_legacy_sql=false --format=csv --max_rows=100000 "$(...)" > cohort_oneperpt_full.csv
-- or paste into the BigQuery console and "Save results > CSV (local file)".
-- Both are patient-level - keep local, do NOT commit.
--

-- (A) cohort_oneperpt_full.csv  (one most-recent ECG per patient; ALL columns, one label source)
SELECT
  -- keys
  c.subject_id, c.ecg_path, c.echo_id, c.ecg_time, c.echo_dt, c.ecg_to_echo_days,
  -- model inputs (7 tabular features: sex + 6 numerics)
  c.gender, c.age_at_ecg, c.ventricular_rate, c.pr_interval, c.qrs_duration, c.qt_corrected,
  c.pr_missing,                                    -- released rule fills RAW 0 pre-scaling
  -- acquisition metadata (new sensitivity analysis)
  c.cart_id, c.bandwidth, c.filtering,
  -- care setting
  s.setting, s.setting_detail, s.setting_broad,
  -- the 12 EchoNext labels (PRIMARY definitions)
  c.lvef_lte_45, c.lvwt_gte_13, c.aortic_stenosis_modsev, c.aortic_regurg_modsev,
  c.mitral_regurg_modsev, c.tricuspid_regurg_modsev, c.pulm_regurg_modsev,
  c.rv_dysfunction_modsev, c.pericardial_modlarge, c.pasp_gte_45, c.tr_max_gte_32, c.shd,
  -- graded-field-only comparators, for the label-definition sensitivity analysis
  c.aortic_stenosis_graded_only, c.shd_graded_only,
  -- alternative definitions for sensitivity (Supplementary Table S2)
  c.rv_dysfunction_cat_only, c.rv_dysfunction_tapse, c.tr_max_gte_32_grad,
  c.septal_gte_15, c.lvwt_cat_modsev, c.lvwt_cat_present, c.phtn_modsev, c.phtn_present,
  -- source-present indicators (complete-case sensitivity)
  c.as_source_present, c.as_graded_present, c.ar_present, c.mr_present, c.tr_present,
  c.pr_present, c.rv_present, c.pe_present, c.trvel_present, c.trgrad_present,
  c.lvwt_present, c.lvef_present,
  -- unassessable flags
  c.rv_unassessable, c.ra_unassessable,
  -- raw echo fields retained for sensitivity analyses
  c.lvef_low, c.lvef_high, c.lvef_biplane, c.lvef_3d, c.lvef_best,
  c.ivs_cm, c.inflat_cm, c.tr_grad, c.tr_vel, c.ivc_cm, c.tapse_cm, c.rap_ivc, c.rap_used,
  c.av_pk_vel, c.av_mean_grad, c.av_area
FROM `your-gcp-project.echonext.analytic_cohort` c
LEFT JOIN `your-gcp-project.echonext.care_setting` s
  ON s.subject_id = c.subject_id AND s.ecg_time = c.ecg_time
WHERE c.most_recent_per_patient;

-- (B) subject_race.csv  (subject_id, race) - deterministic assignment from hospital admissions.
--
-- (5) BOTH race sources are used. MIMIC-IV records race in
--     mimiciv_ed.edstays, and 1,424 cohort patients (34% of the published 4,166 'Unknown' group)
--     have an informative race there. Using both sources reduces Unknown from 4,166 to 2,742 and
--     de-contaminates the Unknown group.
WITH coh AS (SELECT DISTINCT subject_id FROM `your-gcp-project.echonext.analytic_cohort` WHERE most_recent_per_patient),
src AS (
  SELECT a.subject_id, a.admittime AS t, a.race FROM `physionet-data.mimiciv_3_1_hosp.admissions` a JOIN coh USING(subject_id)
  UNION ALL
  SELECT e.subject_id, e.intime AS t, e.race FROM `physionet-data.mimiciv_ed.edstays` e JOIN coh USING(subject_id)),
m AS (
  SELECT subject_id, t AS admittime,
    CASE
      WHEN race LIKE 'WHITE%'    THEN 'White'
      WHEN race LIKE 'BLACK%'    THEN 'Black'
      WHEN race LIKE 'HISPANIC%' OR race LIKE 'SOUTH AMERICAN%' THEN 'Hispanic'
      WHEN race LIKE 'ASIAN%'    THEN 'Asian'
      WHEN race IN ('UNKNOWN','UNABLE TO OBTAIN','PATIENT DECLINED TO ANSWER') THEN 'Unknown'
      ELSE 'Other' END AS race
  FROM src
  WHERE race IS NOT NULL AND race != ''),
r AS (SELECT subject_id, race, COUNT(*) AS n, MAX(admittime) AS last_seen FROM m GROUP BY 1,2),
pick AS (
  SELECT subject_id, race,
    ROW_NUMBER() OVER (PARTITION BY subject_id
      ORDER BY (race = 'Unknown') ASC,   -- informative categories first
               n DESC,                    -- then most frequent
               last_seen DESC,            -- then most recent admission
               race ASC) AS rn            -- final deterministic backstop
  FROM r)
SELECT c.subject_id, COALESCE(p.race, 'Unknown') AS race
FROM coh c LEFT JOIN (SELECT * FROM pick WHERE rn = 1) p USING(subject_id);
-- NOTE: race is assigned from hospital ADMISSION records, so the 1,992 cohort patients who were
-- never admitted carry no race at all and fall into 'Unknown'. That is the likely explanation for
-- the Unknown group's distinct performance profile and is directly testable
-- against setting_broad in query (A).
