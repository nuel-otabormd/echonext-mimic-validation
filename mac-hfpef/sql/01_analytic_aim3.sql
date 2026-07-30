-- ============================================================
-- File: 01_analytic_aim3.sql
-- Study: MAC-HFpEF
-- Database: MIMIC-IV v3.1 + MIMIC-IV-ECHO via BigQuery; medication pipeline in
--           the-project-476301.2_MIMIC_IV_ADMISSION_MEDS
-- Author: Emmanuel Otabor, MD
-- Description: Builds the Aim 3 analytic table, one row per patient: paired-echo MAC
--              progression cohort with MRA exposure, covariates and CONSORT counts.
-- Dependencies: mimiciv_echo.structured_measurement, mimiciv_3_1_hosp.{patients,
--               admissions,diagnoses_icd,labevents}, mimiciv_3_1_derived.charlson,
--               2_MIMIC_IV_ADMISSION_MEDS.MIMICIV_ADMISSION_MEDS_FINAL
-- Output: the-project-476301.dhruv.aim3_analytic   (expect 6,654 rows)
-- ============================================================
--
-- Export this table to CSV for the Python analysis. It is ~6,654 rows, well below any
-- console export limit, but VERIFY THE ROW COUNT AFTER EXPORT against the CONSORT
-- query at the foot of this file before analysing it.

CREATE OR REPLACE TABLE `the-project-476301.dhruv.aim3_analytic` AS

WITH
-- ---------- 1. MAC grade per echo, graded studies only ----------
echo_all AS (
  SELECT
    subject_id,
    measurement_id AS echo_id,
    MIN(measurement_datetime) AS echo_dt,
    MAX(CASE WHEN LOWER(TRIM(measurement)) = 'mac_severity' THEN
          CASE WHEN LOWER(TRIM(result)) = 'severe'  THEN 3
               WHEN LOWER(TRIM(result)) = 'mod mac' THEN 2
               WHEN LOWER(TRIM(result)) = 'mild'    THEN 1 END END) AS mac_grade,
    -- Mitral prosthesis / annuloplasty. Removes the gradable native annulus, so a
    -- patient receiving one between studies would show spurious regression.
    MAX(IF(LOWER(TRIM(measurement)) IN ('mvr_structure1','mvr_structure2','mvr_structure3')
           AND LOWER(TRIM(result)) NOT IN ('', 'native'), 1, 0)) AS mv_prosth_struct,
    MAX(IF(LOWER(TRIM(measurement)) = 'mv_leaflets'
           AND REGEXP_CONTAINS(LOWER(TRIM(result)),
               r'prosth|mechanical|bioprosth|annulopl|tissue valve'), 1, 0)) AS mv_prosth_leaflet
  FROM `physionet-data.mimiciv_echo.structured_measurement`
  WHERE LOWER(TRIM(test_type)) = 'tte'
  GROUP BY 1, 2
),
graded AS (SELECT * FROM echo_all WHERE mac_grade IS NOT NULL),

-- ---------- 2. Pair first and last GRADED study, >= 365 days apart ----------
pairs AS (
  SELECT subject_id, MIN(echo_dt) AS t0, MAX(echo_dt) AS t1,
         COUNT(*) AS n_graded_echos,
         DATE_DIFF(DATE(MAX(echo_dt)), DATE(MIN(echo_dt)), DAY) AS interval_days
  FROM graded GROUP BY 1
  HAVING COUNT(*) >= 2
     AND DATE_DIFF(DATE(MAX(echo_dt)), DATE(MIN(echo_dt)), DAY) >= 365
),
paired AS (
  SELECT p.subject_id, p.t0, p.t1, p.n_graded_echos, p.interval_days,
         MAX(IF(g.echo_dt = p.t0, g.echo_id,   NULL)) AS echo_id_t0,
         MAX(IF(g.echo_dt = p.t0, g.mac_grade, NULL)) AS mac_baseline,
         MAX(IF(g.echo_dt = p.t1, g.mac_grade, NULL)) AS mac_followup
  FROM pairs p JOIN graded g USING (subject_id)
  GROUP BY 1, 2, 3, 4, 5
),

-- ---------- 3. Exclusions ----------
-- Prosthesis at ANY study up to and including follow-up, not baseline only.
prosth AS (
  SELECT p.subject_id,
         MAX(GREATEST(e.mv_prosth_struct, e.mv_prosth_leaflet)) AS ever_mv_prosth
  FROM paired p
  JOIN echo_all e ON e.subject_id = p.subject_id AND e.echo_dt <= p.t1
  GROUP BY 1
),
demog AS (
  SELECT subject_id, gender, anchor_age, anchor_year, dod
  FROM `physionet-data.mimiciv_3_1_hosp.patients`
),
cohort AS (
  SELECT p.*,
         d.gender,
         -- Age at baseline echo. anchor_age applies at anchor_year; both are shifted
         -- consistently within a patient, so the difference is valid.
         d.anchor_age + (EXTRACT(YEAR FROM p.t0) - d.anchor_year) AS age_at_t0,
         d.dod,
         IFNULL(x.ever_mv_prosth, 0) AS ever_mv_prosth
  FROM paired p
  JOIN demog d USING (subject_id)
  LEFT JOIN prosth x USING (subject_id)
),
eligible AS (
  SELECT * FROM cohort
  WHERE mac_baseline IN (1, 2)          -- severe excluded: ceiling effect
    AND ever_mv_prosth = 0
    AND age_at_t0 >= 18
),

-- ---------- 4. Baseline echocardiographic phenotype (index study) ----------
echo_params AS (
  SELECT
    e.subject_id, e.measurement_id AS echo_id,
    MAX(IF(m = 'lvef'          AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_low,
    MAX(IF(m = 'lvef_upper'    AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_high,
    MAX(IF(m = 'biplane_lvef'  AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_biplane,
    MAX(IF(m = 'lvef_3d'       AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_3d,
    -- Wall thickness recorded in mm or cm depending on era; normalise to cm.
    MAX(IF(m = 'septal_thickness'  AND v > 0 AND v < 30, IF(v > 3, v/10, v), NULL)) AS ivs_cm,
    MAX(IF(m = 'inf_lat_thickness' AND v > 0 AND v < 30, IF(v > 3, v/10, v), NULL)) AS inflat_cm,
    MAX(IF(m = 'mv_peak_e_a'   AND v BETWEEN 0 AND 10,   v, NULL)) AS e_a_ratio,
    MAX(IF(m = 'sept_e_prime'  AND v BETWEEN 0 AND 0.5,  v, NULL)) AS sept_e_prime,
    MAX(IF(m = 'lat_e_prime'   AND v BETWEEN 0 AND 0.5,  v, NULL)) AS lat_e_prime,
    MAX(IF(m = 'mv_peak_e'     AND v BETWEEN 0 AND 5,    v, NULL)) AS mv_peak_e,
    MAX(IF(m = 'mv_e_decel'    AND v BETWEEN 0 AND 1000, v, NULL)) AS decel_time_ms,
    MAX(IF(m = 'tapse'         AND v > 0 AND v < 60, IF(v > 3, v/10, v), NULL)) AS tapse_cm,
    MAX(IF(m = 'tr_mmhg'       AND v BETWEEN 0 AND 150,  v, NULL)) AS tr_grad,
    MAX(IF(m = 'ivc_diam'      AND v BETWEEN 0 AND 5,    v, NULL)) AS ivc_cm,
    MAX(IF(m = 'mitral_regurg' AND (REGEXP_CONTAINS(r, r'^mod') OR r LIKE '%sever%')
           AND NOT REGEXP_CONTAINS(r, r'^mild'), 1, 0))            AS mr_modsev,
    MAX(IF(m = 'mitral_stenosis' AND REGEXP_CONTAINS(r, r'from mac'), 1, 0)) AS ms_from_mac
  FROM (
    SELECT subject_id, measurement_id,
           LOWER(TRIM(measurement)) AS m,
           LOWER(TRIM(result))      AS r,
           SAFE_CAST(result AS FLOAT64) AS v
    FROM `physionet-data.mimiciv_echo.structured_measurement`
    WHERE LOWER(TRIM(test_type)) = 'tte'
  ) e
  GROUP BY 1, 2
),

-- ---------- 5. Comorbidity and renal function nearest the index study ----------
-- Admission closest to t0 within one year, used to attach Charlson and labs.
adm_near AS (
  SELECT e.subject_id, e.t0,
         ARRAY_AGG(a.hadm_id ORDER BY ABS(TIMESTAMP_DIFF(a.admittime, e.t0, DAY)) LIMIT 1)[OFFSET(0)] AS hadm_near
  FROM eligible e
  JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a
    ON a.subject_id = e.subject_id
   AND ABS(TIMESTAMP_DIFF(a.admittime, e.t0, DAY)) <= 365
  GROUP BY 1, 2
),
charl AS (
  SELECT hadm_id, charlson_comorbidity_index,
         congestive_heart_failure, diabetes_without_cc, diabetes_with_cc,
         renal_disease, myocardial_infarct, cerebrovascular_disease,
         peripheral_vascular_disease, chronic_pulmonary_disease, malignant_cancer
  FROM `physionet-data.mimiciv_3_1_derived.charlson`
),
labs AS (
  -- Creatinine (50912) and potassium (50971) nearest the index study, within 365 days.
  SELECT e.subject_id,
         ARRAY_AGG(IF(l.itemid = 50912, l.valuenum, NULL) IGNORE NULLS
                   ORDER BY ABS(TIMESTAMP_DIFF(l.charttime, e.t0, DAY)) LIMIT 1)[SAFE_OFFSET(0)] AS creatinine,
         ARRAY_AGG(IF(l.itemid = 50971, l.valuenum, NULL) IGNORE NULLS
                   ORDER BY ABS(TIMESTAMP_DIFF(l.charttime, e.t0, DAY)) LIMIT 1)[SAFE_OFFSET(0)] AS potassium
  FROM eligible e
  JOIN `physionet-data.mimiciv_3_1_hosp.labevents` l
    ON l.subject_id = e.subject_id
   AND l.itemid IN (50912, 50971)
   AND l.valuenum IS NOT NULL
   AND ABS(TIMESTAMP_DIFF(l.charttime, e.t0, DAY)) <= 365
  GROUP BY 1
),
afib AS (
  SELECT e.subject_id, MAX(1) AS has_af
  FROM eligible e
  JOIN `physionet-data.mimiciv_3_1_hosp.diagnoses_icd` d ON d.subject_id = e.subject_id
  WHERE (d.icd_version = 10 AND STARTS_WITH(d.icd_code, 'I48'))
     OR (d.icd_version = 9  AND d.icd_code IN ('42731','42732'))
  GROUP BY 1
),
race AS (
  SELECT subject_id,
         ARRAY_AGG(race ORDER BY n DESC LIMIT 1)[OFFSET(0)] AS race_raw
  FROM (
    SELECT subject_id, race, COUNT(*) AS n
    FROM `physionet-data.mimiciv_3_1_hosp.admissions`
    WHERE race IS NOT NULL AND race NOT IN ('UNKNOWN','UNABLE TO OBTAIN','PATIENT DECLINED TO ANSWER')
    GROUP BY 1, 2
  ) GROUP BY 1
),

-- ---------- 6. MRA exposure across the interval ----------
-- Primary definition: any MRA recorded at any admission during the interval. The three
-- ascertainment definitions were compared and gave 0.91, 0.91 and 0.95, so restricting by
-- source buys no separation and costs sample size. The narrower definitions are retained
-- as columns for sensitivity analysis only.
mra_adm AS (
  SELECT hadm_id,
         ANY_VALUE(subject_id) AS subject_id,
         ANY_VALUE(admittime)  AS admittime,
         LOGICAL_OR(home_med_confidence IN ('high','medium')) AS mra_himed,
         LOGICAL_OR(in_medrecon)                              AS mra_medrecon,
         MAX(dose_mg_imputed)                                 AS mra_dose_mg
  FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.MIMICIV_ADMISSION_MEDS_FINAL`
  WHERE is_mra
  GROUP BY hadm_id
),
raasi_adm AS (
  SELECT hadm_id,
         LOGICAL_OR(is_acei OR is_arb OR is_arni) AS any_raasi,
         LOGICAL_OR(is_bb_gdmt)                   AS any_bb,
         LOGICAL_OR(is_loop_diuretic)             AS any_loop
  FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.MIMICIV_ADMISSION_MEDS_FINAL`
  GROUP BY hadm_id
),
exposure AS (
  SELECT e.subject_id,
         COUNT(DISTINCT a.hadm_id)                                  AS n_adm_interval,
         COUNTIF(m.mra_himed)                                       AS n_adm_mra_himed,
         COUNTIF(m.mra_medrecon)                                    AS n_adm_mra_medrecon,
         COUNTIF(m.hadm_id IS NOT NULL)                             AS n_adm_mra_any,
         MAX(m.mra_dose_mg)                                         AS mra_max_dose_mg,
         LOGICAL_OR(IFNULL(r.any_raasi, FALSE))                     AS conc_raasi,
         LOGICAL_OR(IFNULL(r.any_bb, FALSE))                        AS conc_bb,
         LOGICAL_OR(IFNULL(r.any_loop, FALSE))                      AS conc_loop
  FROM eligible e
  LEFT JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a
         ON a.subject_id = e.subject_id AND a.admittime BETWEEN e.t0 AND e.t1
  LEFT JOIN mra_adm   m ON m.hadm_id = a.hadm_id
  LEFT JOIN raasi_adm r ON r.hadm_id = a.hadm_id
  GROUP BY 1
)

-- ---------- 7. Assembly ----------
SELECT
  e.subject_id,
  e.t0, e.t1, e.interval_days, e.n_graded_echos,
  e.mac_baseline, e.mac_followup,
  CAST(e.mac_followup > e.mac_baseline AS INT64)      AS progressed,
  CAST(e.mac_followup >= e.mac_baseline + 2 AS INT64) AS progressed_2grade,

  -- demographics
  e.age_at_t0, e.gender,
  CASE
    WHEN rc.race_raw LIKE 'WHITE%'                        THEN 'White'
    WHEN rc.race_raw LIKE 'BLACK%'                        THEN 'Black'
    WHEN rc.race_raw LIKE 'HISPANIC%'                     THEN 'Hispanic'
    WHEN rc.race_raw LIKE 'ASIAN%'                        THEN 'Asian'
    WHEN rc.race_raw IS NULL                              THEN 'Unknown'
    ELSE 'Other' END                                      AS race_group,

  -- exposure
  x.n_adm_interval,
  CAST(x.n_adm_mra_any      >= 1 AS INT64)  AS mra_exposed,            -- PRIMARY: on it or not
  CAST(x.n_adm_mra_himed    >= 1 AS INT64)  AS mra_exposed_himed,      -- sensitivity
  CAST(x.n_adm_mra_medrecon >= 1 AS INT64)  AS mra_exposed_medrecon,   -- sensitivity
  SAFE_DIVIDE(x.n_adm_mra_any, x.n_adm_interval) AS mra_coverage,
  x.mra_max_dose_mg,
  CASE WHEN x.n_adm_mra_any = 0              THEN 'none'
       WHEN x.mra_max_dose_mg >= 50          THEN 'target'
       WHEN x.mra_max_dose_mg IS NOT NULL    THEN 'below_target'
       ELSE 'dose_unknown' END               AS mra_dose_group,
  CAST(x.conc_raasi AS INT64) AS conc_raasi,
  CAST(x.conc_bb    AS INT64) AS conc_bb,
  CAST(x.conc_loop  AS INT64) AS conc_loop,

  -- echocardiographic covariates at the index study
  COALESCE(ep.lvef_biplane, ep.lvef_3d,
           (ep.lvef_low + ep.lvef_high)/2, ep.lvef_low, ep.lvef_high) AS lvef,
  GREATEST(IFNULL(ep.ivs_cm, 0), IFNULL(ep.inflat_cm, 0))             AS max_wall_cm,
  ep.e_a_ratio, ep.sept_e_prime, ep.lat_e_prime, ep.mv_peak_e,
  ep.decel_time_ms, ep.tapse_cm, ep.tr_grad,
  -- Average e' when both walls measured, otherwise whichever is available.
  SAFE_DIVIDE(ep.mv_peak_e,
    (IFNULL(ep.sept_e_prime, ep.lat_e_prime)
   + IFNULL(ep.lat_e_prime,  ep.sept_e_prime)) / 2)                   AS e_over_e_prime,
  ep.mr_modsev, ep.ms_from_mac,

  -- renal, comorbidity
  l.creatinine, l.potassium,
  -- CKD-EPI 2021, race-free
  CASE WHEN l.creatinine IS NULL THEN NULL ELSE
    142
    * POW(LEAST(l.creatinine / IF(e.gender = 'F', 0.7, 0.9), 1.0),
          IF(e.gender = 'F', -0.241, -0.302))
    * POW(GREATEST(l.creatinine / IF(e.gender = 'F', 0.7, 0.9), 1.0), -1.200)
    * POW(0.9938, e.age_at_t0)
    * IF(e.gender = 'F', 1.012, 1.0)
  END AS egfr,
  c.charlson_comorbidity_index, c.congestive_heart_failure, c.renal_disease,
  GREATEST(IFNULL(c.diabetes_without_cc,0), IFNULL(c.diabetes_with_cc,0)) AS diabetes,
  c.myocardial_infarct, c.cerebrovascular_disease, c.peripheral_vascular_disease,
  IFNULL(af.has_af, 0) AS has_af,

  -- mortality (for Aim 4 linkage)
  e.dod,
  CAST(e.dod IS NOT NULL AND DATE_DIFF(DATE(e.dod), DATE(e.t1), DAY) BETWEEN 0 AND 365
       AS INT64) AS died_1yr_after_t1

FROM eligible e
LEFT JOIN exposure    x  USING (subject_id)
LEFT JOIN echo_params ep ON ep.subject_id = e.subject_id AND ep.echo_id = e.echo_id_t0
LEFT JOIN adm_near    an USING (subject_id)
LEFT JOIN charl       c  ON c.hadm_id = an.hadm_near
LEFT JOIN labs        l  USING (subject_id)
LEFT JOIN afib        af USING (subject_id)
LEFT JOIN race        rc USING (subject_id);


-- ============================================================
-- CONSORT FLOW. Run and record before analysing.
-- ============================================================
/*
WITH echo_all AS (
  SELECT subject_id, measurement_id AS echo_id, MIN(measurement_datetime) AS echo_dt,
         MAX(CASE WHEN LOWER(TRIM(measurement)) = 'mac_severity' THEN
               CASE WHEN LOWER(TRIM(result))='severe' THEN 3
                    WHEN LOWER(TRIM(result))='mod mac' THEN 2
                    WHEN LOWER(TRIM(result))='mild' THEN 1 END END) AS mac_grade
  FROM `physionet-data.mimiciv_echo.structured_measurement`
  WHERE LOWER(TRIM(test_type)) = 'tte' GROUP BY 1,2
)
SELECT
  (SELECT COUNT(DISTINCT subject_id) FROM echo_all)                           AS s1_any_tte,
  (SELECT COUNT(DISTINCT subject_id) FROM echo_all WHERE mac_grade IS NOT NULL) AS s2_mac_graded_ever,
  (SELECT COUNT(*) FROM `the-project-476301.dhruv.aim3_analytic`)      AS s6_analytic,
  (SELECT COUNTIF(progressed = 1) FROM `the-project-476301.dhruv.aim3_analytic`) AS s7_events,
  (SELECT COUNTIF(mra_exposed = 1) FROM `the-project-476301.dhruv.aim3_analytic`) AS s8_exposed,
  (SELECT COUNTIF(mra_exposed = 1 AND progressed = 1)
     FROM `the-project-476301.dhruv.aim3_analytic`)                    AS s9_events_exposed;
*/
