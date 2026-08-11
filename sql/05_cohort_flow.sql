-- 05_cohort_flow.sql
-- Every count that appears in Figure 1, emitted as a tidy stage/n table.
--
-- Emitting the flow from SQL keeps the diagram tied to the data: the figure script reads this
-- output directly and no count in Figure 1 is transcribed by hand.
--
-- Every filter below is written to match 01_echo_labels.sql and 02_analytic_cohort.sql exactly. If
-- either of those changes, this must change with it, and the reconciliation rows at the end will
-- fail loudly if it does not.
--
-- Usage:
--   bq query --use_legacy_sql=false --format=csv < sql/05_cohort_flow.sql \
--     > results/figure_data/cohort_flow.csv

WITH mm0 AS (
  SELECT subject_id, study_id, ecg_time, rr_interval,
    LOWER(CONCAT(IFNULL(report_0,"")," ",IFNULL(report_1,"")," ",IFNULL(report_2,"")," ",
      IFNULL(report_3,"")," ",IFNULL(report_4,"")," ",IFNULL(report_5,"")," ",IFNULL(report_6,"")," ",
      IFNULL(report_7,"")," ",IFNULL(report_8,"")," ",IFNULL(report_9,"")," ",IFNULL(report_10,"")," ",
      IFNULL(report_11,"")," ",IFNULL(report_12,"")," ",IFNULL(report_13,"")," ",IFNULL(report_14,"")," ",
      IFNULL(report_15,"")," ",IFNULL(report_16,"")," ",IFNULL(report_17,""))) AS rpt
  FROM `physionet-data.mimiciv_ecg.machine_measurements`),
mm AS (
  SELECT subject_id, study_id, ecg_time,
    REGEXP_CONTAINS(rpt, r"vent.*pac|paced|pacemaker|v-pac|a-v sequ") AS paced,
    REGEXP_CONTAINS(rpt, r"poor quality|technically limited|uninterpretable|cannot be interpreted|revers|defective|suboptimal|artifact") AS poor_quality,
    (rr_interval BETWEEN 300 AND 2000) AS has_valid_meas
  FROM mm0),
ecg AS (
  SELECT r.subject_id, r.study_id, r.ecg_time, mm.paced, mm.poor_quality, mm.has_valid_meas
  FROM `physionet-data.mimiciv_ecg.record_list` r JOIN mm USING(subject_id, study_id, ecg_time)),
pat AS (SELECT subject_id, gender, anchor_age, anchor_year FROM `physionet-data.mimiciv_3_1_hosp.patients`),

-- Each ECG is matched to its nearest FOLLOWING eligible echocardiogram within 365 days. rn=1 keeps
-- that nearest study; an ECG with no eligible echo in the window does not appear at all.
paired AS (
  SELECT e.*, p.gender,
         p.anchor_age + (EXTRACT(YEAR FROM e.ecg_time) - p.anchor_year) AS age_at_ecg,
         ROW_NUMBER() OVER (PARTITION BY e.study_id
           ORDER BY ABS(DATETIME_DIFF(l.echo_dt, e.ecg_time, MINUTE)), l.echo_id) AS rn
  FROM ecg e
  JOIN pat p USING(subject_id)
  JOIN `your-gcp-project.echonext.echo_labels_v2` l
    ON e.subject_id = l.subject_id
   AND l.has_lvef = 1 AND l.has_valve = 1 AND l.prosthetic_valve = 0
   AND l.echo_dt >= e.ecg_time
   AND l.echo_dt <= DATETIME_ADD(e.ecg_time, INTERVAL 365 DAY)),
f AS (SELECT * FROM paired WHERE rn = 1),

-- Exclusions are assigned hierarchically in the order shown, so that they sum to the total excluded
-- and a reader can add the figure up. An ECG that is both paced and poor quality counts once, under
-- pacing. Reporting them as overlapping sets instead would not reconcile.
tag AS (
  SELECT *,
    CASE WHEN paced THEN "paced"
         WHEN poor_quality THEN "poorqual"
         WHEN NOT has_valid_meas THEN "nomeas"
         WHEN age_at_ecg < 18 THEN "age"
         WHEN gender NOT IN ("M","F") THEN "sex"
         ELSE "eligible" END AS disposition
  FROM f),
coh AS (SELECT * FROM `your-gcp-project.echonext.analytic_cohort_v2` WHERE most_recent_per_patient)

SELECT * FROM UNNEST([
  STRUCT(1  AS seq, "ecg_source"          AS stage, (SELECT COUNT(*) FROM `physionet-data.mimiciv_ecg.record_list`) AS n,
                                                   (SELECT COUNT(DISTINCT subject_id) FROM `physionet-data.mimiciv_ecg.record_list`) AS n_patients),
  -- The echocardiographic source is the WHOLE structured-measurement component, not the
  -- transthoracic subset. echo_labels_v2 is already filtered to test_type = "tte", so counting it
  -- as the source would silently absorb the 26,560 transoesophageal and stress studies into no
  -- stated exclusion and misdescribe the resource.
  STRUCT(2, "echo_source",       (SELECT COUNT(DISTINCT measurement_id) FROM `physionet-data.mimiciv_echo.structured_measurement`),
                                 (SELECT COUNT(DISTINCT subject_id)     FROM `physionet-data.mimiciv_echo.structured_measurement`)),
  STRUCT(3, "echo_excl_nontte",  (SELECT COUNT(DISTINCT IF(test_type != "tte", measurement_id, NULL)) FROM `physionet-data.mimiciv_echo.structured_measurement`), 0),
  STRUCT(4, "echo_excl_prosthetic", (SELECT COUNTIF(prosthetic_valve=1) FROM `your-gcp-project.echonext.echo_labels_v2`), 0),
  STRUCT(5, "echo_excl_incomplete", (SELECT COUNTIF(prosthetic_valve=0 AND (has_lvef=0 OR has_valve=0)) FROM `your-gcp-project.echonext.echo_labels_v2`), 0),
  STRUCT(6, "echo_eligible",     (SELECT COUNTIF(has_lvef=1 AND has_valve=1 AND prosthetic_valve=0) FROM `your-gcp-project.echonext.echo_labels_v2`),
                                 (SELECT COUNT(DISTINCT IF(has_lvef=1 AND has_valve=1 AND prosthetic_valve=0, subject_id, NULL)) FROM `your-gcp-project.echonext.echo_labels_v2`)),
  STRUCT(7,  "paired",        (SELECT COUNT(*) FROM f), (SELECT COUNT(DISTINCT subject_id) FROM f)),
  STRUCT(8,  "excl_paced",    (SELECT COUNTIF(disposition="paced")    FROM tag), 0),
  STRUCT(9,  "excl_poorqual", (SELECT COUNTIF(disposition="poorqual") FROM tag), 0),
  STRUCT(10, "excl_nomeas",   (SELECT COUNTIF(disposition="nomeas")   FROM tag), 0),
  STRUCT(11, "excl_age",      (SELECT COUNTIF(disposition="age")      FROM tag), 0),
  STRUCT(12, "excl_sex",      (SELECT COUNTIF(disposition="sex")      FROM tag), 0),
  STRUCT(13, "eligible_ecgs", (SELECT COUNTIF(disposition="eligible") FROM tag),
                              (SELECT COUNT(DISTINCT IF(disposition="eligible", subject_id, NULL)) FROM tag)),
  STRUCT(14, "cohort",           (SELECT COUNT(*) FROM coh), (SELECT COUNT(DISTINCT subject_id) FROM coh)),
  STRUCT(15, "cohort_shd",       (SELECT COUNTIF(shd=1) FROM coh), 0),
  STRUCT(16, "cohort_pr_missing",(SELECT COUNTIF(pr_missing) FROM coh), 0),
  -- Reconciliation. All three must be zero. They are carried in the output rather than checked in a
  -- comment so that a broken flow is visible in the figure's own input file, and the figure script
  -- refuses to draw unless they are zero.
  STRUCT(90, "check_echo_excl_sums",
         (SELECT COUNT(DISTINCT measurement_id) FROM `physionet-data.mimiciv_echo.structured_measurement`)
         - (SELECT COUNT(DISTINCT IF(test_type != "tte", measurement_id, NULL)) FROM `physionet-data.mimiciv_echo.structured_measurement`)
         - (SELECT COUNTIF(prosthetic_valve=1) + COUNTIF(prosthetic_valve=0 AND (has_lvef=0 OR has_valve=0))
                 + COUNTIF(has_lvef=1 AND has_valve=1 AND prosthetic_valve=0)
            FROM `your-gcp-project.echonext.echo_labels_v2`), 0),
  STRUCT(91, "check_excl_sums_to_paired",
         (SELECT COUNT(*) FROM f) - (SELECT COUNTIF(disposition!="eligible") + COUNTIF(disposition="eligible") FROM tag), 0),
  STRUCT(92, "check_eligible_patients_equals_cohort",
         (SELECT COUNT(DISTINCT IF(disposition="eligible", subject_id, NULL)) FROM tag) - (SELECT COUNT(*) FROM coh), 0)
])
ORDER BY seq;
