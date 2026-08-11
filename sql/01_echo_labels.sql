-- 01_echo_labels.sql  (REBUILD v2, Aug 2026)
-- Build the 12 EchoNext structural-heart-disease (SHD) labels from MIMIC-IV-ECHO v1.0
-- structured measurements (TTE only). Harmonized to closest available fields.
-- Output: your-gcp-project.echonext.echo_labels  (one row per echo measurement_id)
-- See docs/DECISIONS_AND_RATIONALE.md for every label-definition choice + rationale.
--
-- SOURCE: physionet-data.mimiciv_echo.structured_measurement
--   MIMIC-IV-ECHO: Echocardiogram Matched Subset v1.0, released 10 Mar 2026,
--   doi 10.13026/nrjh-5r77. Structured measurements: 206,488 studies / 91,372 patients
--   (179,928 TTE / 16,389 stress / 10,171 TEE), 186 distinct TTE measurement fields.
--

CREATE OR REPLACE TABLE `your-gcp-project.echonext.echo_labels` AS
WITH base AS (
  SELECT subject_id, measurement_id AS echo_id, measurement_datetime,
         LOWER(TRIM(measurement)) m, LOWER(TRIM(result)) r, SAFE_CAST(result AS FLOAT64) v
  FROM `physionet-data.mimiciv_echo.structured_measurement`
  WHERE test_type = "tte"                                   -- TTE ONLY (exclude stress/TEE)
),
agg AS (
  SELECT subject_id, echo_id, MIN(measurement_datetime) AS echo_dt,

    ---------- numeric fields (explicit plausibility bounds; units verified from `unit` column) ----------
    MAX(IF(m="lvef"              AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_low,      -- %, range lower bound
    MAX(IF(m="lvef_upper"        AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_high,     -- %, range upper bound
    MAX(IF(m="biplane_lvef"      AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_biplane,  -- %, used in only ~101 cohort studies
    MAX(IF(m="lvef_3d"           AND v BETWEEN 0 AND 100, v, NULL)) AS lvef_3d,       -- %
    MAX(IF(m="septal_thickness"  AND v BETWEEN 0.3 AND 3.0, v, NULL)) AS ivs_cm,      -- cm (native), plausibility-bounded
    MAX(IF(m="inf_lat_thickness" AND v BETWEEN 0.3 AND 3.0, v, NULL)) AS inflat_cm,   -- cm, inferolateral wall
                                                                                      -- NOTE: MIMIC has NO posterior-wall
                                                                                      -- field (verified across all 186 TTE
                                                                                      -- measurements). Substitution is
                                                                                      -- necessary, not optional.
    MAX(IF(m="tr_mmhg"           AND v BETWEEN 0 AND 150, v, NULL)) AS tr_grad,       -- mm Hg
    MAX(IF(m="tr_velocity"       AND v BETWEEN 0 AND 10,  v, NULL)) AS tr_vel,        -- m/s, DIRECT TR Vmax (primary)
                                                                                      -- internally consistent with tr_mmhg:
                                                                                      -- only 30/34,515 violate grad=4v^2 by >5
    MAX(IF(m="ivc_diam"          AND v BETWEEN 0 AND 5,   v, NULL)) AS ivc_cm,        -- cm
    -- TAPSE entries ARE mixed cm/mm; bounded explicit conversion rather than a bare >3 heuristic
    MAX(IF(m="tapse", CASE WHEN v BETWEEN 0.5 AND 4.0 THEN v
                           WHEN v BETWEEN 5   AND 40  THEN v/10
                           ELSE NULL END, NULL)) AS tapse_cm,                          -- cm

    ---------- aortic-valve quantitative fields (NEW in v2) ----------
    MAX(IF(m="av_pk_vel"          AND v BETWEEN 0 AND 8,   v, NULL)) AS av_pk_vel,     -- m/s
    MAX(IF(m="av_mean_grad"       AND v BETWEEN 0 AND 150, v, NULL)) AS av_mean_grad,  -- mm Hg
    MAX(IF(m="av_area_continuity" AND v BETWEEN 0.1 AND 8, v, NULL)) AS av_area,       -- cm2

    ---------- right atrial pressure from IVC category text (ASE; mmHg stated in the field) ----------
    -- Verified against the MIMIC vocabulary: no "(0-5mmHg)" string occurs in this field.
    MAX(IF(m="ivc", CASE
        WHEN r LIKE "%(5-10mmhg)%"  THEN 8       -- "IVC<=2.1cm, <50% collapse (5-10mmHg)"   n=2,444
        WHEN r LIKE "%(10-15mmhg)%" THEN 13      -- ">2.1cm, >50% (10-15mmHg)"               n=3,253
        WHEN r LIKE "%(>15mmhg)%"   THEN 20
        WHEN r LIKE "%dilated%"     THEN 20      -- "IVC dilated (>2.5cm)"                   n=672
        WHEN r LIKE "nl ivc%"       THEN 3       -- "NL IVC <2.2 cm" -> ASE normal RAP 3     n=3,022  [NEW]
        WHEN r LIKE "%ra <10mmhg%"  THEN 5       -- "Intubated, IVC<1.5cm, RA <10mmHg"       n=90     [NEW]
        ELSE NULL END, NULL)) AS rap_ivc,
    MAX(IF(m="ivc" AND r LIKE "%cannot assess%",1,0)) AS ra_unassessable,  -- "Intubated - cannot assess RA pressure" n=1,170

    ---------- inclusion helpers ----------
    MAX(IF(m="lvef" AND v BETWEEN 0 AND 100,1,0)) AS has_lvef,
    MAX(IF(m IN ("aortic_stenosis","aortic_regurg","mitral_regurg","tricuspid_regurg","pulm_regurg")
           AND r!="",1,0)) AS has_valve,

    ---------- categorical moderate-or-greater positives ----------
    -- (mild-moderate excluded; unquantified "present" excluded; verified against full value lists)
    MAX(IF(m="aortic_stenosis" AND (r LIKE "%sever%" OR REGEXP_CONTAINS(r,r"^mod")),1,0)) AS as_graded_pos,
    MAX(IF(m="aortic_stenosis" AND REGEXP_CONTAINS(r,r"^none, incr"),1,0)) AS as_highflow_neg,
           -- MIMIC explicitly flags high-flow states that mimic stenosis:
           -- "None, incr vel high output" n=906; "None, incr grad from AR/stroke vol" n=493.
           -- These MUST stay negative even when peak velocity is high.
    MAX(IF(m="aortic_regurg"   AND (r LIKE "%sever%" OR REGEXP_CONTAINS(r,r"^mod")) AND NOT REGEXP_CONTAINS(r,r"^mild"),1,0)) AS ar_pos,
    MAX(IF(m="mitral_regurg"   AND (r LIKE "%sever%" OR REGEXP_CONTAINS(r,r"^mod")) AND NOT REGEXP_CONTAINS(r,r"^mild"),1,0)) AS mr_pos,
    MAX(IF(m="tricuspid_regurg" AND ((r LIKE "%sever%" OR REGEXP_CONTAINS(r,r"^mod") OR r LIKE "%torrential%") AND NOT REGEXP_CONTAINS(r,r"^mild")),1,0)) AS tr_pos,
    MAX(IF(m="pulm_regurg"     AND (r LIKE "%sever%" OR r LIKE "%significant%"),1,0)) AS pr_pos,
           -- MIMIC has no explicit "moderate" tier for PR:
           -- Physiologic -> Mild -> Significant -> Mod/severe -> Severe. "Significant" is the closest analogue.
    MAX(IF(m="rv_function"     AND (REGEXP_CONTAINS(r,r"(moderate|severe).*hypo") OR r LIKE "%depress%"),1,0)) AS rv_cat_pos,
    MAX(IF(m="rv_function"     AND r IN ("rv not well seen","cannot assess rv function"),1,0)) AS rv_unassessable,  -- n=3,850 (2.14%)
    MAX(IF(m="pericardial_effusion" AND (REGEXP_CONTAINS(r,r"^moderate") OR r LIKE "%large%") AND NOT REGEXP_CONTAINS(r,r"^small") AND NOT r LIKE "%fat pad%",1,0)) AS pe_pos,

    ---------- per-label source-present indicators (NEW in v2; for complete-case sensitivity) ----------
    MAX(IF(m="aortic_stenosis"       AND r!="",1,0)) AS as_graded_present,
    MAX(IF(m="aortic_regurg"         AND r!="",1,0)) AS ar_present,
    MAX(IF(m="mitral_regurg"         AND r!="",1,0)) AS mr_present,
    MAX(IF(m="tricuspid_regurg"      AND r!="",1,0)) AS tr_present,
    MAX(IF(m="pulm_regurg"           AND r!="",1,0)) AS pr_present,
    MAX(IF(m="rv_function"           AND r!="",1,0)) AS rv_present,
    MAX(IF(m="pericardial_effusion"  AND r!="",1,0)) AS pe_present,

    ---------- sensitivity-only fields (NEW in v2) ----------
    -- phtn_severity: 90.0% populated but keyed to TR GRADIENT ("Mod (TR 37-60mmHg)"), NOT to PASP.
    -- EchoNext defines elevated PASP as >=45 mmHg, so the TR-gradient + RAP reconstruction below
    -- remains PRIMARY. This field is a COVERAGE sensitivity analysis only.
    MAX(IF(m="phtn_severity" AND r!="",1,0)) AS phtn_present,
    MAX(IF(m="phtn_severity" AND (REGEXP_CONTAINS(r,r"^mod") OR r LIKE "%severe%"),1,0)) AS phtn_modsev,
    -- categorical LV wall thickness (92.2% populated) for the secondary higher-grade LVH analysis
    MAX(IF(m="lv_wall_thickness" AND r!="",1,0)) AS lvwt_cat_present,
    MAX(IF(m="lv_wall_thickness" AND (REGEXP_CONTAINS(r,r"^mod") OR REGEXP_CONTAINS(r,r"^severe")),1,0)) AS lvwt_cat_modsev,
           -- "Mod symmetric LVH (1.5-1.7cm)" n=6,061; "Severe symmetric (>1.7cm)" n=855

    ---------- repaired/replaced (prosthetic) valve flag (EchoNext/Nature exclusion) ----------
    MAX(IF(m IN ("avr_structure1","avr_structure2",
                 "mvr_structure1","mvr_structure2","mvr_structure3",
                 "tvr_structure1","tvr_structure2","tvr_structure3",   -- tvr_structure2/3 NEW in v2
                 "pvr_structure1","pvr_structure2")                     -- pvr_structure1  NEW in v2
           AND r NOT IN ("","native"),1,0)) AS struct_prosth,
    MAX(IF(m IN ("av_leaflets","mv_leaflets","tv_leaflets","pv_leaflets")
           AND REGEXP_CONTAINS(r, r"prosth|mechanical|bioprosth|annulopl|tavr|tissue valve"),1,0)) AS leaflet_prosth
  FROM base GROUP BY 1,2
),
lab AS (
  SELECT *,
    -- best-available quantitative LVEF. In practice the reported-range midpoint carries 93.1% of
    -- cohort studies; biplane 101 and 3D 8. Order kept for correctness, description softened.
    COALESCE(lvef_biplane, lvef_3d, (lvef_low+lvef_high)/2, lvef_low, lvef_high) AS lvef_best,
    -- REBUILT aortic stenosis: graded text authoritative where present (it already accounts for
    -- high-flow states); quantitative fallback only where the graded field is empty.
    CASE
      WHEN as_graded_present = 1 THEN as_graded_pos
      WHEN av_pk_vel >= 3.0 OR av_mean_grad >= 20 OR av_area <= 1.5 THEN 1   -- ASE/ACC mod-or-greater
      ELSE 0
    END AS as_pos_v2,
    -- right atrial pressure actually used: explicit IVC category, else diameter-based fallback
    COALESCE(rap_ivc, CASE WHEN ivc_cm IS NULL THEN 3 WHEN ivc_cm <= 2.1 THEN 3 ELSE 15 END) AS rap_used
  FROM agg
)
SELECT subject_id, echo_id, echo_dt, has_lvef, has_valve,

  ---------- the 12 EchoNext labels ----------
  IFNULL(CAST(lvef_best <= 45 AS INT64),0) AS lvef_lte_45,
  IFNULL(CAST(GREATEST(IFNULL(ivs_cm,0),IFNULL(inflat_cm,0)) >= 1.3 AS INT64),0) AS lvwt_gte_13,
  as_pos_v2 AS aortic_stenosis_modsev,                                              -- REBUILT (v2)
  ar_pos AS aortic_regurg_modsev, mr_pos AS mitral_regurg_modsev,
  tr_pos AS tricuspid_regurg_modsev, pr_pos AS pulm_regurg_modsev,
  rv_cat_pos AS rv_dysfunction_modsev,                                              -- PRIMARY = categorical (faithful to EchoNext)
  rv_cat_pos AS rv_dysfunction_cat_only,
  GREATEST(rv_cat_pos, IFNULL(CAST(tapse_cm < 1.7 AS INT64),0)) AS rv_dysfunction_tapse,  -- sensitivity only
  pe_pos AS pericardial_modlarge,
  IFNULL(CAST(tr_vel >= 3.2 AS INT64),0) AS tr_max_gte_32,                          -- PRIMARY = direct velocity (faithful)
  IFNULL(CAST(tr_grad >= 40.96 AS INT64),0) AS tr_max_gte_32_grad,                  -- sensitivity only (derived gradient)
  IFNULL(CAST((tr_grad + rap_used) >= 45 AS INT64),0) AS pasp_gte_45,
  GREATEST(
    IFNULL(CAST(lvef_best <= 45 AS INT64),0),
    IFNULL(CAST(GREATEST(IFNULL(ivs_cm,0),IFNULL(inflat_cm,0)) >= 1.3 AS INT64),0),
    as_pos_v2, ar_pos, mr_pos, tr_pos, pr_pos, rv_cat_pos, pe_pos,
    IFNULL(CAST(tr_vel >= 3.2 AS INT64),0),
    IFNULL(CAST((tr_grad + rap_used) >= 45 AS INT64),0)
  ) AS shd,

  ---------- graded-field-only comparators, for the label-definition sensitivity analysis ----------
  as_graded_pos AS aortic_stenosis_graded_only,
  GREATEST(
    IFNULL(CAST(lvef_best <= 45 AS INT64),0),
    IFNULL(CAST(GREATEST(IFNULL(ivs_cm,0),IFNULL(inflat_cm,0)) >= 1.3 AS INT64),0),
    as_graded_pos, ar_pos, mr_pos, tr_pos, pr_pos, rv_cat_pos, pe_pos,
    IFNULL(CAST(tr_vel >= 3.2 AS INT64),0),
    IFNULL(CAST((tr_grad + rap_used) >= 45 AS INT64),0)
  ) AS shd_graded_only,

  ---------- source-present indicators (complete-case sensitivity) ----------
  GREATEST(as_graded_present,
           IF(av_pk_vel IS NOT NULL OR av_mean_grad IS NOT NULL OR av_area IS NOT NULL,1,0)) AS as_source_present,
  as_graded_present, ar_present, mr_present, tr_present, pr_present, rv_present, pe_present,
  IF(tr_vel  IS NOT NULL,1,0) AS trvel_present,
  IF(tr_grad IS NOT NULL,1,0) AS trgrad_present,
  IF(ivs_cm IS NOT NULL OR inflat_cm IS NOT NULL,1,0) AS lvwt_present,
  IF(lvef_best IS NOT NULL,1,0) AS lvef_present,

  ---------- unassessable flags (sensitivity) ----------
  rv_unassessable, ra_unassessable,

  ---------- sensitivity-only alternative definitions ----------
  phtn_present, phtn_modsev, lvwt_cat_present, lvwt_cat_modsev,
  IFNULL(CAST(ivs_cm >= 1.5 AS INT64),0) AS septal_gte_15,   -- secondary higher-grade LVH analysis

  GREATEST(struct_prosth, leaflet_prosth) AS prosthetic_valve,  -- repaired/replaced valve (EchoNext exclusion)

  ---------- raw fields retained for sensitivity analyses ----------
  lvef_low, lvef_high, lvef_biplane, lvef_3d, lvef_best,
  ivs_cm, inflat_cm, tr_grad, tr_vel, ivc_cm, tapse_cm, rap_ivc, rap_used,
  av_pk_vel, av_mean_grad, av_area
FROM lab;
