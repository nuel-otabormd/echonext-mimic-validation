-- 05_missingness.sql
-- Supplementary Table S3: per-label structured-field availability and missing-as-negative impact.
-- For each EchoNext label, counts cohort echocardiograms in which the source field is present
-- (categorical = non-empty result; numeric = valid in-range value) vs treated-as-negative-because-missing.
-- Combine the presence counts below with the per-label positive counts (sum of the label columns in
-- analytic_cohort WHERE most_recent_per_patient) to build the S3 table.
WITH coh AS (
  SELECT echo_id FROM `your-gcp-project.echonext.analytic_cohort` WHERE most_recent_per_patient),
b AS (
  SELECT measurement_id AS echo_id, LOWER(TRIM(measurement)) AS m, TRIM(result) AS r, SAFE_CAST(result AS FLOAT64) AS v
  FROM `physionet-data.mimiciv_echo.structured_measurement`
  WHERE test_type='tte' AND measurement_id IN (SELECT echo_id FROM coh)),
pres AS (
  SELECT echo_id,
    MAX(IF(m IN ('lvef','lvef_upper','biplane_lvef','lvef_3d') AND v BETWEEN 0 AND 100,1,0)) AS lvef,
    MAX(IF(m IN ('septal_thickness','inf_lat_thickness') AND v>0 AND v<30,1,0))             AS lvwt,
    MAX(IF(m='aortic_stenosis'      AND r!='',1,0)) AS as_,
    MAX(IF(m='aortic_regurg'        AND r!='',1,0)) AS ar,
    MAX(IF(m='mitral_regurg'        AND r!='',1,0)) AS mr,
    MAX(IF(m='tricuspid_regurg'     AND r!='',1,0)) AS tr,
    MAX(IF(m='pulm_regurg'          AND r!='',1,0)) AS pr,
    MAX(IF(m='rv_function'          AND r!='',1,0)) AS rv,
    MAX(IF(m='pericardial_effusion' AND r!='',1,0)) AS pe,
    MAX(IF(m='tr_velocity' AND v BETWEEN 0 AND 10,1,0))  AS trvel,
    MAX(IF(m='tr_mmhg'     AND v BETWEEN 0 AND 150,1,0)) AS trgrad
  FROM b GROUP BY 1)
SELECT COUNT(*) AS N,
  SUM(lvef) AS lvef_present, SUM(lvwt) AS lvwt_present, SUM(as_) AS as_present, SUM(ar) AS ar_present,
  SUM(mr) AS mr_present, SUM(tr) AS tr_present, SUM(pr) AS pr_present, SUM(rv) AS rv_present,
  SUM(pe) AS pe_present, SUM(trvel) AS trvel_present, SUM(trgrad) AS trgrad_present
FROM pres;
