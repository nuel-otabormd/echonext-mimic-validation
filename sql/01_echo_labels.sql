-- 01_echo_labels.sql
-- Build the 12 EchoNext structural-heart-disease (SHD) labels from MIMIC-IV-ECHO
-- structured measurements (TTE only). Harmonized to closest available fields.
-- Output: your-gcp-project.echonext.echo_labels  (one row per echo measurement_id)
-- See docs/DECISIONS_AND_RATIONALE.md for every label-definition choice + rationale.

CREATE OR REPLACE TABLE `your-gcp-project.echonext.echo_labels` AS
WITH base AS (
  SELECT subject_id, measurement_id AS echo_id, measurement_datetime,
         LOWER(TRIM(measurement)) m, LOWER(TRIM(result)) r, SAFE_CAST(result AS FLOAT64) v
  FROM `physionet-data.mimiciv_echo.structured_measurement`
  WHERE test_type = "tte"                                   -- TTE ONLY (exclude stress/TEE)
),
agg AS (
  SELECT subject_id, echo_id, MIN(measurement_datetime) AS echo_dt,
    -- numeric fields
    MAX(IF(m="lvef"             AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_low,
    MAX(IF(m="lvef_upper"       AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_high,
    MAX(IF(m="biplane_lvef"     AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_biplane,
    MAX(IF(m="lvef_3d"          AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_3d,
    MAX(IF(m="septal_thickness" AND v>0 AND v<30, IF(v>3,v/10,v), NULL)) AS ivs_cm,      -- mm->cm clean
    MAX(IF(m="inf_lat_thickness" AND v>0 AND v<30, IF(v>3,v/10,v), NULL)) AS inflat_cm,  -- inferolateral wall (NOT literal posterior wall)
    MAX(IF(m="tr_mmhg"          AND v BETWEEN 0 AND 150, v, NULL)) AS tr_grad,
    MAX(IF(m="tr_velocity"      AND v BETWEEN 0 AND 10,  v, NULL)) AS tr_vel,            -- DIRECT TR Vmax (primary)
    MAX(IF(m="ivc_diam"         AND v BETWEEN 0 AND 5,   v, NULL)) AS ivc_cm,
    MAX(IF(m="tapse"            AND v>0 AND v<60, IF(v>3,v/10,v), NULL)) AS tapse_cm,
    -- RAP from IVC category text (ASE; mmHg stated in the field)
    MAX(IF(m="ivc", CASE WHEN r LIKE "%(0-5mmhg)%" THEN 3 WHEN r LIKE "%(5-10mmhg)%" THEN 8
                         WHEN r LIKE "%(10-15mmhg)%" THEN 13 WHEN r LIKE "%(>15mmhg)%" THEN 20
                         WHEN r LIKE "%dilated%" THEN 20 ELSE NULL END, NULL)) AS rap_ivc,
    -- inclusion helpers
    MAX(IF(m="lvef" AND v BETWEEN 0 AND 100,1,0)) AS has_lvef,
    MAX(IF(m IN ("aortic_stenosis","aortic_regurg","mitral_regurg","tricuspid_regurg","pulm_regurg") AND r!="",1,0)) AS has_valve,
    -- categorical moderate-or-greater positives (mild-moderate excluded; unquantified "present" excluded)
    MAX(IF(m="aortic_stenosis" AND (r LIKE "%sever%" OR REGEXP_CONTAINS(r,r"^mod")),1,0)) AS as_pos,
    MAX(IF(m="aortic_regurg"   AND (r LIKE "%sever%" OR REGEXP_CONTAINS(r,r"^mod")) AND NOT REGEXP_CONTAINS(r,r"^mild"),1,0)) AS ar_pos,
    MAX(IF(m="mitral_regurg"   AND (r LIKE "%sever%" OR REGEXP_CONTAINS(r,r"^mod")) AND NOT REGEXP_CONTAINS(r,r"^mild"),1,0)) AS mr_pos,
    MAX(IF(m="tricuspid_regurg" AND ((r LIKE "%sever%" OR REGEXP_CONTAINS(r,r"^mod") OR r LIKE "%torrential%") AND NOT REGEXP_CONTAINS(r,r"^mild")),1,0)) AS tr_pos,
    MAX(IF(m="pulm_regurg"     AND (r LIKE "%sever%" OR r LIKE "%significant%"),1,0)) AS pr_pos,
    MAX(IF(m="rv_function"     AND (REGEXP_CONTAINS(r,r"(moderate|severe).*hypo") OR r LIKE "%depress%"),1,0)) AS rv_cat_pos,
    MAX(IF(m="pericardial_effusion" AND (REGEXP_CONTAINS(r,r"^moderate") OR r LIKE "%large%") AND NOT REGEXP_CONTAINS(r,r"^small") AND NOT r LIKE "%fat pad%",1,0)) AS pe_pos,
    -- repaired/replaced (prosthetic) valve flag (EchoNext/Nature exclusion)
    MAX(IF(m IN ("avr_structure1","avr_structure2","mvr_structure1","mvr_structure2","mvr_structure3","tvr_structure1","pvr_structure2")
           AND r NOT IN ("","native"),1,0)) AS struct_prosth,
    MAX(IF(m IN ("av_leaflets","mv_leaflets","tv_leaflets","pv_leaflets")
           AND REGEXP_CONTAINS(r, r"prosth|mechanical|bioprosth|annulopl|tavr|tissue valve"),1,0)) AS leaflet_prosth
  FROM base GROUP BY 1,2
)
SELECT subject_id, echo_id, echo_dt, has_lvef, has_valve,
  IFNULL(CAST(COALESCE(lvef_biplane,lvef_3d,(lvef_low+lvef_high)/2,lvef_low,lvef_high) <= 45 AS INT64),0) AS lvef_lte_45,
  IFNULL(CAST(GREATEST(IFNULL(ivs_cm,0),IFNULL(inflat_cm,0)) >= 1.3 AS INT64),0) AS lvwt_gte_13,
  as_pos AS aortic_stenosis_modsev, ar_pos AS aortic_regurg_modsev, mr_pos AS mitral_regurg_modsev,
  tr_pos AS tricuspid_regurg_modsev, pr_pos AS pulm_regurg_modsev,
  rv_cat_pos AS rv_dysfunction_modsev,                                              -- PRIMARY = categorical (faithful to EchoNext)
  rv_cat_pos AS rv_dysfunction_cat_only,
  GREATEST(rv_cat_pos, IFNULL(CAST(tapse_cm<1.7 AS INT64),0)) AS rv_dysfunction_tapse,  -- sensitivity only
  pe_pos AS pericardial_modlarge,
  IFNULL(CAST(tr_vel >= 3.2 AS INT64),0) AS tr_max_gte_32,                          -- PRIMARY = direct velocity (faithful)
  IFNULL(CAST(tr_grad >= 40.96 AS INT64),0) AS tr_max_gte_32_grad,                  -- sensitivity only (derived gradient)
  IFNULL(CAST((tr_grad + COALESCE(rap_ivc, CASE WHEN ivc_cm IS NULL THEN 3 WHEN ivc_cm<=2.1 THEN 3 ELSE 15 END)) >= 45 AS INT64),0) AS pasp_gte_45,
  GREATEST(
    IFNULL(CAST(COALESCE(lvef_biplane,lvef_3d,(lvef_low+lvef_high)/2,lvef_low,lvef_high)<=45 AS INT64),0),
    IFNULL(CAST(GREATEST(IFNULL(ivs_cm,0),IFNULL(inflat_cm,0))>=1.3 AS INT64),0), as_pos,ar_pos,mr_pos,tr_pos,pr_pos,
    rv_cat_pos, pe_pos,
    IFNULL(CAST(tr_vel>=3.2 AS INT64),0),
    IFNULL(CAST((tr_grad + COALESCE(rap_ivc, CASE WHEN ivc_cm IS NULL THEN 3 WHEN ivc_cm<=2.1 THEN 3 ELSE 15 END))>=45 AS INT64),0)
  ) AS shd,
  GREATEST(struct_prosth, leaflet_prosth) AS prosthetic_valve,   -- repaired/replaced valve (EchoNext exclusion)
  -- raw fields retained for sensitivity analyses
  lvef_low,lvef_high,lvef_biplane,lvef_3d,ivs_cm,inflat_cm,tr_grad,tr_vel,ivc_cm,tapse_cm,rap_ivc
FROM agg;
