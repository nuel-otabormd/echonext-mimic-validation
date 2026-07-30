-- ============================================================
-- File: 02_analytic_hfpef.sql
-- Study: MAC-HFpEF
-- Database: MIMIC-IV v3.1 + MIMIC-IV-ECHO via BigQuery
-- Author: Emmanuel Otabor, MD
-- Description: HFpEF cohort for Aims 1, 2 and 4. One row per patient, anchored on the
--              first hospitalisation containing a transthoracic echocardiogram.
-- Output: the-project-476301.dhruv.hfpef_analytic
-- ============================================================
--
-- WHY THE ANCHOR IS AN ADMISSION, NOT AN ECHO
-- MIMIC-IV records out-of-hospital death only within ~365 days of a patient's LAST
-- discharge (verified: deaths/day fall from 29.0 in the 181-365 window to 1.9 in the
-- 366-400 window). Anchoring on an echo breaks mortality ascertainment, because 31.7% of
-- echoes occur after the last discharge and 21.6% of patients then have no ascertainment
-- window at all.
--
-- Anchoring on an admission makes ascertainment complete by construction:
--   index discharge <= last discharge, therefore
--   index discharge + 365 <= last discharge + 365 = the capture boundary.
-- Every death within one year of index discharge is inside the window. No censoring
-- required and no selection on healthcare contact.
--
-- The cost is that purely outpatient echoes are excluded, so the population is
-- "hospitalised patients with an echocardiogram". This must be stated in the population
-- definition rather than glossed. It also matches the comparator literature, which
-- studied hospitalised patients.

CREATE OR REPLACE TABLE `the-project-476301.dhruv.hfpef_analytic` AS (

WITH
-- ---------- 1. Echo-level measurements ----------
echo AS (
  SELECT
    subject_id,
    measurement_id AS echo_id,
    MIN(measurement_datetime) AS echo_dt,
    MAX(CASE WHEN m = 'mac_severity' THEN
          CASE WHEN r = 'severe' THEN 3 WHEN r = 'mod mac' THEN 2
               WHEN r = 'mild' THEN 1 END END)                     AS mac_grade_raw,
    MAX(IF(m = 'lvef'         AND v BETWEEN 0 AND 100, v, NULL))   AS lvef_low,
    MAX(IF(m = 'lvef_upper'   AND v BETWEEN 0 AND 100, v, NULL))   AS lvef_high,
    MAX(IF(m = 'biplane_lvef' AND v BETWEEN 0 AND 100, v, NULL))   AS lvef_biplane,
    MAX(IF(m = 'lvef_3d'      AND v BETWEEN 0 AND 100, v, NULL))   AS lvef_3d,
    MAX(IF(m = 'septal_thickness'  AND v > 0 AND v < 30, IF(v > 3, v/10, v), NULL)) AS ivs_cm,
    MAX(IF(m = 'inf_lat_thickness' AND v > 0 AND v < 30, IF(v > 3, v/10, v), NULL)) AS inflat_cm,
    MAX(IF(m = 'mv_peak_e_a'  AND v BETWEEN 0 AND 10,  v, NULL))   AS e_a_ratio,
    MAX(IF(m = 'sept_e_prime' AND v BETWEEN 0 AND 0.5, v, NULL))   AS sept_e_prime,
    MAX(IF(m = 'lat_e_prime'  AND v BETWEEN 0 AND 0.5, v, NULL))   AS lat_e_prime,
    MAX(IF(m = 'mv_peak_e'    AND v BETWEEN 0 AND 5,   v, NULL))   AS mv_peak_e,
    MAX(IF(m = 'mv_e_decel'   AND v BETWEEN 0 AND 1000, v, NULL))  AS decel_time_ms,
    MAX(IF(m = 'tapse'        AND v > 0 AND v < 60, IF(v > 3, v/10, v), NULL)) AS tapse_cm,
    MAX(IF(m = 'tr_mmhg'      AND v BETWEEN 0 AND 150, v, NULL))   AS tr_grad,
    MAX(IF(m = 'mitral_regurg' AND (REGEXP_CONTAINS(r, r'^mod') OR r LIKE '%sever%')
           AND NOT REGEXP_CONTAINS(r, r'^mild'), 1, 0))            AS mr_modsev,
    MAX(IF(m IN ('mvr_structure1','mvr_structure2','mvr_structure3')
           AND r NOT IN ('', 'native'), 1, 0))                     AS mv_prosth_struct,
    MAX(IF(m = 'mv_leaflets'
           AND REGEXP_CONTAINS(r, r'prosth|mechanical|bioprosth|annulopl|tissue valve'),
           1, 0))                                                  AS mv_prosth_leaflet
  FROM (
    SELECT subject_id, measurement_id, measurement_datetime,
           LOWER(TRIM(measurement)) AS m,
           LOWER(TRIM(result))      AS r,
           SAFE_CAST(result AS FLOAT64) AS v
    FROM `physionet-data.mimiciv_echo.structured_measurement`
    WHERE LOWER(TRIM(test_type)) = 'tte'
  )
  GROUP BY 1, 2
),

-- ---------- 2. Link each echo to the admission containing it ----------
echo_adm AS (
  SELECT e.*, a.hadm_id, a.admittime, a.dischtime,
         a.admission_type, a.discharge_location, a.insurance, a.race,
         a.hospital_expire_flag
  FROM echo e
  JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a
    ON a.subject_id = e.subject_id
   AND e.echo_dt BETWEEN a.admittime AND a.dischtime
),

-- ---------- 3. Heart failure by ICD, both coding eras ----------
hf AS (
  SELECT DISTINCT subject_id, hadm_id
  FROM `physionet-data.mimiciv_3_1_hosp.diagnoses_icd`
  WHERE (icd_version = 10 AND STARTS_WITH(icd_code, 'I50'))
     OR (icd_version = 9  AND STARTS_WITH(icd_code, '428'))
),
hf_ever AS (SELECT DISTINCT subject_id FROM hf),

-- ---------- 4. Index = FIRST qualifying admission per patient ----------
qualifying AS (
  SELECT ea.*,
         COALESCE(ea.lvef_biplane, ea.lvef_3d,
                  (ea.lvef_low + ea.lvef_high)/2, ea.lvef_low, ea.lvef_high) AS lvef
  FROM echo_adm ea
  WHERE GREATEST(ea.mv_prosth_struct, ea.mv_prosth_leaflet) = 0
),
indexed AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT q.*, ROW_NUMBER() OVER (PARTITION BY q.subject_id
                                   ORDER BY q.admittime, q.echo_dt, q.echo_id) AS rn
    FROM qualifying q
    JOIN hf_ever h ON h.subject_id = q.subject_id
    WHERE q.lvef >= 50                       -- HFpEF
  ) WHERE rn = 1
),

-- ---------- 5. Demographics ----------
demog AS (
  SELECT subject_id, gender, anchor_age, anchor_year, dod
  FROM `physionet-data.mimiciv_3_1_hosp.patients`
),

-- ---------- 6. Outcomes ----------
-- Days alive and out of hospital in the 365 days after index discharge. Days after death
-- contribute nothing; hospital days are subtracted from the days actually survived.
readmits AS (
  SELECT i.subject_id,
         COUNT(DISTINCT a.hadm_id)                                    AS n_readmit_1yr,
         COUNTIF(DATE_DIFF(DATE(a.admittime), DATE(i.dischtime), DAY) <= 30) AS n_readmit_30d,
         SUM(GREATEST(DATE_DIFF(
               DATE(LEAST(a.dischtime, TIMESTAMP_ADD(i.dischtime, INTERVAL 365 DAY))),
               DATE(a.admittime), DAY), 0))                           AS hosp_days_1yr
  FROM indexed i
  JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a
    ON a.subject_id = i.subject_id
   AND a.admittime > i.dischtime
   AND a.admittime <= TIMESTAMP_ADD(i.dischtime, INTERVAL 365 DAY)
  GROUP BY 1
),

-- ---------- 7. Guideline-directed therapy at the index admission (Aim 2) ----------
gdmt AS (
  SELECT hadm_id,
         LOGICAL_OR(is_mra)                       AS mra,
         LOGICAL_OR(is_sglt2i)                    AS sglt2i,
         LOGICAL_OR(is_acei OR is_arb OR is_arni) AS raasi,
         LOGICAL_OR(is_bb_gdmt)                   AS bb,
         LOGICAL_OR(is_loop_diuretic)             AS loop_diuretic,
         LOGICAL_OR(is_statin)                    AS statin,
         MAX(IF(is_mra, dose_mg_imputed, NULL))   AS mra_dose_mg
  FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.MIMICIV_ADMISSION_MEDS_FINAL`
  GROUP BY hadm_id
),

-- ---------- 8. Labs and comorbidity at the index admission ----------
labs AS (
  SELECT i.subject_id,
         ARRAY_AGG(IF(l.itemid = 50912, l.valuenum, NULL) IGNORE NULLS
                   ORDER BY ABS(TIMESTAMP_DIFF(l.charttime, i.admittime, HOUR)) LIMIT 1)[SAFE_OFFSET(0)] AS creatinine,
         ARRAY_AGG(IF(l.itemid = 50971, l.valuenum, NULL) IGNORE NULLS
                   ORDER BY ABS(TIMESTAMP_DIFF(l.charttime, i.admittime, HOUR)) LIMIT 1)[SAFE_OFFSET(0)] AS potassium,
         ARRAY_AGG(IF(l.itemid = 50963, l.valuenum, NULL) IGNORE NULLS
                   ORDER BY ABS(TIMESTAMP_DIFF(l.charttime, i.admittime, HOUR)) LIMIT 1)[SAFE_OFFSET(0)] AS ntprobnp
  FROM indexed i
  JOIN `physionet-data.mimiciv_3_1_hosp.labevents` l
    ON l.subject_id = i.subject_id
   AND l.itemid IN (50912, 50971, 50963)
   AND l.valuenum IS NOT NULL
   AND l.charttime BETWEEN TIMESTAMP_SUB(i.admittime, INTERVAL 7 DAY) AND i.dischtime
  GROUP BY i.subject_id, i.admittime
),
charl AS (
  SELECT hadm_id, charlson_comorbidity_index,
         congestive_heart_failure, diabetes_without_cc, diabetes_with_cc,
         renal_disease, myocardial_infarct, cerebrovascular_disease,
         peripheral_vascular_disease, chronic_pulmonary_disease
  FROM `physionet-data.mimiciv_3_1_derived.charlson`
),
afib AS (
  SELECT DISTINCT subject_id, 1 AS has_af
  FROM `physionet-data.mimiciv_3_1_hosp.diagnoses_icd`
  WHERE (icd_version = 10 AND STARTS_WITH(icd_code, 'I48'))
     OR (icd_version = 9  AND icd_code IN ('42731','42732'))
),
icu AS (
  SELECT i.subject_id, MAX(1) AS icu_stay,
         SUM(s.los) AS icu_los_days
  FROM indexed i
  JOIN `physionet-data.mimiciv_3_1_icu.icustays` s
    ON s.hadm_id = i.hadm_id
  GROUP BY 1
)

-- ---------- 9. Assembly ----------
SELECT
  i.subject_id, i.hadm_id, i.echo_id, i.echo_dt, i.admittime, i.dischtime,

  -- EXPOSURE for Aims 1 and 4: MAC grade. Blank means not observed; for cross-sectional
  -- aims this is treated as absence, per the protocol (the field has no negative token).
  IFNULL(i.mac_grade_raw, 0)                            AS mac_grade,
  CAST(IFNULL(i.mac_grade_raw, 0) >= 1 AS INT64)        AS mac_any,
  CAST(IFNULL(i.mac_grade_raw, 0) >= 2 AS INT64)        AS mac_modsev,
  CAST(i.mac_grade_raw IS NOT NULL AS INT64)            AS mac_recorded,

  -- demographics
  d.gender,
  d.anchor_age + (EXTRACT(YEAR FROM i.admittime) - d.anchor_year) AS age,
  CASE WHEN i.race LIKE 'WHITE%'    THEN 'White'
       WHEN i.race LIKE 'BLACK%'    THEN 'Black'
       WHEN i.race LIKE 'HISPANIC%' THEN 'Hispanic'
       WHEN i.race LIKE 'ASIAN%'    THEN 'Asian'
       WHEN i.race IS NULL OR i.race IN ('UNKNOWN','UNABLE TO OBTAIN',
            'PATIENT DECLINED TO ANSWER') THEN 'Unknown'
       ELSE 'Other' END                                 AS race_group,
  i.insurance, i.admission_type,

  -- echocardiographic phenotype (Aim 1)
  i.lvef,
  GREATEST(IFNULL(i.ivs_cm, 0), IFNULL(i.inflat_cm, 0))  AS max_wall_cm,
  i.e_a_ratio, i.sept_e_prime, i.lat_e_prime, i.mv_peak_e, i.decel_time_ms,
  i.tapse_cm, i.tr_grad, i.mr_modsev,
  SAFE_DIVIDE(i.mv_peak_e,
    (IFNULL(i.sept_e_prime, i.lat_e_prime)
   + IFNULL(i.lat_e_prime,  i.sept_e_prime)) / 2)        AS e_over_e_prime,

  -- therapy at index (Aim 2 outcome)
  CAST(IFNULL(g.mra, FALSE) AS INT64)            AS mra,
  CAST(IFNULL(g.sglt2i, FALSE) AS INT64)         AS sglt2i,
  CAST(IFNULL(g.raasi, FALSE) AS INT64)          AS raasi,
  CAST(IFNULL(g.bb, FALSE) AS INT64)             AS bb,
  CAST(IFNULL(g.loop_diuretic, FALSE) AS INT64)  AS loop_diuretic,
  CAST(IFNULL(g.statin, FALSE) AS INT64)         AS statin,
  g.mra_dose_mg,

  -- renal, comorbidity
  l.creatinine, l.potassium, l.ntprobnp,
  CASE WHEN l.creatinine IS NULL THEN NULL ELSE
    142
    * POW(LEAST(l.creatinine / IF(d.gender = 'F', 0.7, 0.9), 1.0),
          IF(d.gender = 'F', -0.241, -0.302))
    * POW(GREATEST(l.creatinine / IF(d.gender = 'F', 0.7, 0.9), 1.0), -1.200)
    * POW(0.9938, d.anchor_age + (EXTRACT(YEAR FROM i.admittime) - d.anchor_year))
    * IF(d.gender = 'F', 1.012, 1.0)
  END AS egfr,
  c.charlson_comorbidity_index, c.congestive_heart_failure, c.renal_disease,
  GREATEST(IFNULL(c.diabetes_without_cc,0), IFNULL(c.diabetes_with_cc,0)) AS diabetes,
  c.myocardial_infarct, c.cerebrovascular_disease, c.peripheral_vascular_disease,
  c.chronic_pulmonary_disease,
  IFNULL(af.has_af, 0)      AS has_af,
  IFNULL(ic.icu_stay, 0)    AS icu_stay,
  ic.icu_los_days,
  DATE_DIFF(DATE(i.dischtime), DATE(i.admittime), DAY) AS index_los_days,
  i.hospital_expire_flag,
  i.discharge_location,

  -- OUTCOMES (Aim 1). Ascertainment is complete: index discharge <= last discharge, so
  -- one year from index discharge lies inside the death-capture window.
  d.dod,
  CAST(d.dod IS NOT NULL
       AND DATE_DIFF(DATE(d.dod), DATE(i.dischtime), DAY) BETWEEN 0 AND 365
       AS INT64)                                        AS died_1yr,
  CAST(d.dod IS NOT NULL
       AND DATE_DIFF(DATE(d.dod), DATE(i.dischtime), DAY) BETWEEN 0 AND 30
       AS INT64)                                        AS died_30d,
  DATE_DIFF(DATE(d.dod), DATE(i.dischtime), DAY)        AS days_to_death,
  -- Time to event for Cox: death day, else 365.
  LEAST(IFNULL(DATE_DIFF(DATE(d.dod), DATE(i.dischtime), DAY), 365), 365) AS fu_days,

  IFNULL(r.n_readmit_1yr, 0) AS n_readmit_1yr,
  IFNULL(r.n_readmit_30d, 0) AS n_readmit_30d,
  -- Days alive and out of hospital: days survived in the year, minus hospital days.
  GREATEST(
    LEAST(IFNULL(DATE_DIFF(DATE(d.dod), DATE(i.dischtime), DAY), 365), 365)
      - IFNULL(r.hosp_days_1yr, 0), 0)                  AS daoh_1yr

FROM indexed i
JOIN demog d  ON d.subject_id = i.subject_id
LEFT JOIN gdmt g    ON g.hadm_id    = i.hadm_id
LEFT JOIN charl c   ON c.hadm_id    = i.hadm_id
LEFT JOIN labs l    ON l.subject_id = i.subject_id
LEFT JOIN afib af   ON af.subject_id = i.subject_id
LEFT JOIN icu ic    ON ic.subject_id = i.subject_id
LEFT JOIN readmits r ON r.subject_id = i.subject_id
WHERE d.anchor_age + (EXTRACT(YEAR FROM i.admittime) - d.anchor_year) >= 18
  AND i.hospital_expire_flag = 0        -- must survive to discharge to have follow-up
);


-- ============================================================
-- CONSORT + description. Run after building.
-- ============================================================
/*
SELECT
  COUNT(*)                                          AS n_cohort,
  COUNTIF(mac_grade = 0)                            AS mac_none,
  COUNTIF(mac_grade = 1)                            AS mac_mild,
  COUNTIF(mac_grade = 2)                            AS mac_moderate,
  COUNTIF(mac_grade = 3)                            AS mac_severe,
  COUNTIF(died_1yr = 1)                             AS deaths_1yr,
  ROUND(100*COUNTIF(died_1yr = 1)/COUNT(*), 1)      AS pct_died_1yr,
  COUNTIF(mra = 1)                                  AS n_on_mra,
  ROUND(100*COUNTIF(mra = 1)/COUNT(*), 1)           AS pct_on_mra,
  ROUND(AVG(age), 1)                                AS mean_age,
  ROUND(100*COUNTIF(gender = 'F')/COUNT(*), 1)      AS pct_female,
  ROUND(AVG(lvef), 1)                               AS mean_lvef,
  ROUND(AVG(egfr), 1)                               AS mean_egfr,
  ROUND(AVG(daoh_1yr), 1)                           AS mean_daoh,
  COUNTIF(egfr IS NULL)                             AS miss_egfr,
  COUNTIF(charlson_comorbidity_index IS NULL)       AS miss_charlson,
  COUNTIF(e_a_ratio IS NULL)                        AS miss_ea
FROM `the-project-476301.dhruv.hfpef_analytic`;
*/

-- Aim 1 and Aim 2 headline numbers by MAC grade
/*
SELECT mac_grade,
       COUNT(*)                                     AS n,
       COUNTIF(died_1yr = 1)                        AS deaths,
       ROUND(100*COUNTIF(died_1yr = 1)/COUNT(*), 1) AS pct_died,
       ROUND(AVG(daoh_1yr), 1)                      AS mean_daoh,
       COUNTIF(mra = 1)                             AS n_mra,
       ROUND(100*COUNTIF(mra = 1)/COUNT(*), 1)      AS pct_mra,
       ROUND(AVG(egfr), 1)                          AS mean_egfr,
       ROUND(AVG(age), 1)                           AS mean_age,
       ROUND(AVG(e_a_ratio), 2)                     AS mean_ea,
       ROUND(AVG(e_over_e_prime), 1)                AS mean_e_eprime,
       ROUND(AVG(tr_grad), 1)                       AS mean_tr_grad
FROM `the-project-476301.dhruv.hfpef_analytic`
GROUP BY 1 ORDER BY 1;
*/
