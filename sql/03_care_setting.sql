-- 03_care_setting.sql
-- Care setting at the ECG for the primary cohort, by linking the ECG timestamp to
-- concurrent MIMIC-IV encounters. ICU/ED/inpatient are positively window-matched;
-- "outpatient/ambulatory" is the residual (no concurrent encounter).
-- NOTE: ECGs in the residual that fall within 1 day on-or-before an EMERGENCY/URGENT/
-- OBSERVATION admission are reassigned to ED/acute — an admission_type audit showed 98%
-- (3,876/3,961) were acute and on-or-before the admit time (ED-presentation ECGs, not clinic).
-- Result (n=45,878): inpatient ward 14,331 (31.2%), ED/acute 13,191 (28.8%),
--                    outpatient/ambulatory 11,196 (24.4%), ICU 7,160 (15.6%).
WITH coh AS (SELECT subject_id, ecg_time FROM `your-gcp-project.echonext.analytic_cohort` WHERE most_recent_per_patient),
icu AS (SELECT DISTINCT c.subject_id,c.ecg_time FROM coh c
        JOIN `physionet-data.mimiciv_3_1_icu.icustays` i ON c.subject_id=i.subject_id AND c.ecg_time BETWEEN i.intime AND i.outtime),
edst AS (SELECT DISTINCT c.subject_id,c.ecg_time FROM coh c
        JOIN `physionet-data.mimiciv_ed.edstays` e ON c.subject_id=e.subject_id AND c.ecg_time BETWEEN e.intime AND e.outtime),
adm AS (SELECT DISTINCT c.subject_id,c.ecg_time FROM coh c
        JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a ON c.subject_id=a.subject_id AND c.ecg_time BETWEEN a.admittime AND a.dischtime),
acute_pre AS (SELECT DISTINCT c.subject_id,c.ecg_time FROM coh c
        JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a ON c.subject_id=a.subject_id
        WHERE REGEXP_CONTAINS(a.admission_type,'EMER|URGENT|OBSERVATION')
          AND DATE_DIFF(DATE(a.admittime), DATE(c.ecg_time), DAY) BETWEEN 0 AND 1)
SELECT
  CASE WHEN icu.subject_id       IS NOT NULL THEN 'ICU'
       WHEN edst.subject_id      IS NOT NULL THEN 'Emergency department'
       WHEN adm.subject_id       IS NOT NULL THEN 'Inpatient ward'
       WHEN acute_pre.subject_id IS NOT NULL THEN 'ED / acute presentation'
       ELSE 'Outpatient/ambulatory' END AS setting,
  COUNT(*) AS n, ROUND(100*COUNT(*)/45878,1) AS pct
FROM coh c
LEFT JOIN icu       USING(subject_id,ecg_time)
LEFT JOIN edst      USING(subject_id,ecg_time)
LEFT JOIN adm       USING(subject_id,ecg_time)
LEFT JOIN acute_pre USING(subject_id,ecg_time)
GROUP BY 1 ORDER BY n DESC;
