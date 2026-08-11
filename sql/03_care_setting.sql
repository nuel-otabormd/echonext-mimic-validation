-- 03_care_setting.sql  (REBUILD v2, Aug 2026)
-- Care setting at the ECG for the primary cohort, by linking the ECG timestamp to
-- concurrent MIMIC-IV encounters. ICU/ED/inpatient are positively window-matched;
-- "outpatient/ambulatory" is the residual (no concurrent encounter).
-- NOTE: ECGs in the residual that fall within 1 day on-or-before an EMERGENCY/URGENT/
-- OBSERVATION admission are reassigned to ED/acute - an admission_type audit showed 98%
-- (3,876/3,961) were acute and on-or-before the admit time (ED-presentation ECGs, not clinic).
--

CREATE OR REPLACE TABLE `your-gcp-project.echonext.care_setting` AS
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
SELECT c.subject_id, c.ecg_time,
  -- five-level detail
  CASE WHEN icu.subject_id       IS NOT NULL THEN 'ICU'
       WHEN edst.subject_id      IS NOT NULL THEN 'Emergency department'
       WHEN adm.subject_id       IS NOT NULL THEN 'Inpatient ward'
       WHEN acute_pre.subject_id IS NOT NULL THEN 'ED / acute presentation'
       ELSE 'Outpatient/ambulatory' END AS setting_detail,
  -- four-level, as reported in the manuscript (ED and ED/acute merged)
  CASE WHEN icu.subject_id       IS NOT NULL THEN 'ICU'
       WHEN edst.subject_id      IS NOT NULL THEN 'Emergency / acute'
       WHEN adm.subject_id       IS NOT NULL THEN 'Inpatient ward'
       WHEN acute_pre.subject_id IS NOT NULL THEN 'Emergency / acute'
       ELSE 'Outpatient/ambulatory' END AS setting,
  -- three-level contrast: emergency or acute, inpatient or intensive care, and outpatient.
  -- MUST be derived from the same precedence as `setting` above. An earlier version re-derived it
  -- independently with admission checked BEFORE ED, which put 888 ECGs taken in the ED (of patients
  -- who were also admitted) into 'Inpatient/ICU', contradicting their own setting_detail.
  -- The setting at the time of the ECG is the ED, so ED precedence governs.
  CASE WHEN icu.subject_id  IS NOT NULL THEN 'Inpatient/ICU'
       WHEN edst.subject_id IS NOT NULL THEN 'Emergency / acute'
       WHEN adm.subject_id  IS NOT NULL THEN 'Inpatient/ICU'
       WHEN acute_pre.subject_id IS NOT NULL THEN 'Emergency / acute'
       ELSE 'Outpatient/ambulatory' END AS setting_broad
FROM coh c
LEFT JOIN icu       USING(subject_id,ecg_time)
LEFT JOIN edst      USING(subject_id,ecg_time)
LEFT JOIN adm       USING(subject_id,ecg_time)
LEFT JOIN acute_pre USING(subject_id,ecg_time);
