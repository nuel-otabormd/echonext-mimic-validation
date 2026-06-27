-- 06_lvh_secondary.sql
-- Secondary LV-hypertrophy analysis: does the model's wall-thickness probability discriminate
-- HIGHER-grade hypertrophy better than the primary 1.3 cm label? Regenerated for the EXACT locked
-- one-per-patient cohort (most_recent_per_patient) so it aligns 1:1 with the Table 2 cohort.
-- Outcomes (per linked echo): septal IVS >=1.5 cm, and categorical moderate-or-severe LVH from the
-- MIMIC-IV-ECHO `lv_wall_thickness` graded field ("mod symmetric ...", "severe symmetric ...").
-- lvh_max13_check is a sanity column: GREATEST(ivs,inflat)>=1.3 must reproduce the locked
-- lvwt_gte_13 label (=> 22.4% prevalence, AUROC 0.679) on all 45,878 rows.
-- Export this result to $ECHONEXT_DATA/lvh_secondary.csv for code/lvh_secondary.py.

WITH cohort AS (
  SELECT subject_id, ecg_path, echo_id, lvwt_gte_13
  FROM `your-gcp-project.echonext.analytic_cohort`
  WHERE most_recent_per_patient
),
lvhcat AS (                                                    -- categorical mod-or-severe LVH per echo
  SELECT measurement_id AS echo_id,
    MAX(CASE WHEN LOWER(TRIM(result)) LIKE "mod symmetric%"
              OR LOWER(TRIM(result)) LIKE "severe symmetric%" THEN 1 ELSE 0 END) AS lvh_modsev_cat
  FROM `physionet-data.mimiciv_echo.structured_measurement`
  WHERE test_type="tte" AND LOWER(TRIM(measurement))="lv_wall_thickness"
  GROUP BY echo_id
)
SELECT c.ecg_path,
       CAST(GREATEST(IFNULL(el.ivs_cm,0),IFNULL(el.inflat_cm,0))>=1.3 AS INT64) AS lvh_max13_check,  -- sanity
       CAST(IFNULL(el.ivs_cm,0)>=1.5 AS INT64)                                  AS ivs_gte_15,
       IFNULL(lc.lvh_modsev_cat,0)                                             AS lvh_modsev_cat,
       c.lvwt_gte_13                                                            -- locked Table-2 label
FROM cohort c
JOIN `your-gcp-project.echonext.echo_labels` el ON c.echo_id=el.echo_id
LEFT JOIN lvhcat lc ON c.echo_id=lc.echo_id;
