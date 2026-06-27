-- 02_analytic_cohort.sql
-- ECG-centric analytic cohort (EchoNext labeling rule): each 12-lead ECG paired to its
-- nearest FOLLOWING TTE within 1 year (ECG precedes echo). Deterministic tie-breaking.
-- Derived tabular features from machine_measurements fiducials (ms). EchoNext exclusions.
-- Output: your-gcp-project.echonext.analytic_cohort
-- Primary analysis = WHERE most_recent_per_patient (one ECG per patient).

CREATE OR REPLACE TABLE `your-gcp-project.echonext.analytic_cohort` AS
WITH mm0 AS (
  SELECT subject_id, study_id, ecg_time, rr_interval, p_onset, qrs_onset, qrs_end, t_end,
    LOWER(CONCAT(
      IFNULL(report_0,"")," ",IFNULL(report_1,"")," ",IFNULL(report_2,"")," ",IFNULL(report_3,"")," ",
      IFNULL(report_4,"")," ",IFNULL(report_5,"")," ",IFNULL(report_6,"")," ",IFNULL(report_7,"")," ",
      IFNULL(report_8,"")," ",IFNULL(report_9,"")," ",IFNULL(report_10,"")," ",IFNULL(report_11,"")," ",
      IFNULL(report_12,"")," ",IFNULL(report_13,"")," ",IFNULL(report_14,"")," ",IFNULL(report_15,"")," ",
      IFNULL(report_16,"")," ",IFNULL(report_17,""))) AS rpt
  FROM `physionet-data.mimiciv_ecg.machine_measurements`),
mm AS (
  SELECT subject_id, study_id, ecg_time,
    SAFE_DIVIDE(60000, NULLIF(rr_interval,0)) AS ventricular_rate,           -- bpm (rr in ms)
    IF(p_onset BETWEEN 0 AND 1000 AND qrs_onset BETWEEN 0 AND 1000, qrs_onset - p_onset, NULL) AS pr_interval,   -- ms
    IF(qrs_end<>29999 AND qrs_onset<>29999 AND qrs_end>qrs_onset, qrs_end - qrs_onset, NULL) AS qrs_duration,    -- ms
    IF(t_end<>29999 AND qrs_onset<>29999 AND rr_interval BETWEEN 300 AND 2000,
       (t_end - qrs_onset)/SQRT(rr_interval/1000.0), NULL) AS qt_corrected,  -- Bazett QTc (ms)
    REGEXP_CONTAINS(rpt, r"vent.*pac|paced|pacemaker|v-pac|a-v sequ") AS paced,
    REGEXP_CONTAINS(rpt, r"poor quality|technically limited|uninterpretable|cannot be interpreted|revers|defective|suboptimal|artifact") AS poor_quality,
    (rr_interval BETWEEN 300 AND 2000) AS has_valid_meas   -- 29999 = missing sentinel
  FROM mm0),
ecg AS (
  SELECT r.subject_id, r.study_id, r.ecg_time, r.path AS ecg_path,
         mm.ventricular_rate, mm.pr_interval, mm.qrs_duration, mm.qt_corrected, mm.paced, mm.poor_quality, mm.has_valid_meas
  FROM `physionet-data.mimiciv_ecg.record_list` r JOIN mm USING(subject_id, study_id, ecg_time)),
pat AS (SELECT subject_id, gender, anchor_age, anchor_year FROM `physionet-data.mimiciv_3_1_hosp.patients`),
paired AS (
  SELECT e.*, p.gender, p.anchor_age + (EXTRACT(YEAR FROM e.ecg_time) - p.anchor_year) AS age_at_ecg,
         l.echo_id, l.echo_dt, DATETIME_DIFF(l.echo_dt, e.ecg_time, DAY) AS ecg_to_echo_days,
         l.lvef_lte_45,l.lvwt_gte_13,l.aortic_stenosis_modsev,l.aortic_regurg_modsev,l.mitral_regurg_modsev,
         l.tricuspid_regurg_modsev,l.pulm_regurg_modsev,l.rv_dysfunction_modsev,l.rv_dysfunction_tapse,l.pericardial_modlarge,
         l.pasp_gte_45,l.tr_max_gte_32,l.tr_max_gte_32_grad,l.shd,
         -- DETERMINISTIC nearest-echo tie-break
         ROW_NUMBER() OVER (PARTITION BY e.study_id
                            ORDER BY ABS(DATETIME_DIFF(l.echo_dt, e.ecg_time, MINUTE)), l.echo_id) AS rn
  FROM ecg e JOIN pat p USING(subject_id)
  JOIN `your-gcp-project.echonext.echo_labels` l
    ON e.subject_id=l.subject_id AND l.has_lvef=1 AND l.has_valve=1
   AND l.prosthetic_valve=0                                       -- exclude repaired/replaced-valve echos (EchoNext)
   AND l.echo_dt>=e.ecg_time AND l.echo_dt<=DATETIME_ADD(e.ecg_time, INTERVAL 365 DAY)),
elig AS (
  SELECT * EXCEPT(rn),
         -- DETERMINISTIC most-recent-ECG tie-break
         ROW_NUMBER() OVER (PARTITION BY subject_id ORDER BY ecg_time DESC, study_id DESC) AS recency_rank
  FROM paired
  WHERE rn=1 AND age_at_ecg>=18 AND gender IN ("M","F")
        AND paced=FALSE AND poor_quality=FALSE AND has_valid_meas=TRUE)
SELECT *, (recency_rank=1) AS most_recent_per_patient,
       MOD(ABS(FARM_FINGERPRINT(CAST(subject_id AS STRING))),100) AS subj_hash
FROM elig;
