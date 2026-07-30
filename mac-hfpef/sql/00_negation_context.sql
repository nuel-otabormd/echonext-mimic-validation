-- ============================================================
-- File: 00_negation_context.sql
-- Study: MAC-HFpEF
-- Database: BigQuery, the-project-476301.2_MIMIC_IV_ADMISSION_MEDS
-- Author: Emmanuel Otabor, MD
-- Description: Resolves assertion status for note-derived medication mentions, so a
--              drug the patient is NOT currently taking is not counted as exposure.
-- Dependencies: home_note_reparsed (source text + existing assertion flags)
-- Output: med_mention_context
-- ============================================================
--
-- THE ACTUAL DEFECT
-- The reconciliation pipeline ALREADY detects held and stopped medications:
-- home_note_reparsed carries is_held_or_stopped, is_held, drug_in_lexicon, section
-- and is_prn. None of these survive into MIMICIV_ADMISSION_MEDS_FINAL or
-- gdmt_by_admission, so every downstream analysis treats a discontinued drug as
-- current therapy. The fix is to propagate what already exists, then add a residual
-- pass for the assertion classes the existing flag does not cover.
--
-- ASSERTION CLASSES AND THEIR TREATMENT
--   HELD           temporarily interrupted    -> IS chronic exposure (see note below)
--   STOPPED        formally discontinued      -> NOT exposure
--   ALLERGY        listed as an allergy       -> NOT exposure, and a contraindication
--   OTHER_PERSON   family member's drug       -> NOT exposure
--   HISTORICAL     past use                   -> NOT exposure
--   PLANNED        not yet started            -> NOT exposure
--   NOT_A_DRUG     parse artefact             -> NOT exposure
--
-- HELD is deliberately separated from STOPPED. A drug held for acute kidney injury
-- during an admission remains the patient's chronic therapy; a drug discontinued does
-- not. Over a multi-year exposure window these are different states, and collapsing
-- them discards real exposure. The pipeline already distinguishes them: is_held marks
-- the temporary case, so STOPPED is recoverable as is_held_or_stopped AND NOT is_held.


-- ============================================================
-- STEP 1. DIAGNOSTICS. Run these first; they determine Step 2.
-- ============================================================

-- 1a. Section vocabulary. Establishes which sections exist, whether discharge
--     medications are captured separately from admission medications, and where
--     allergy lists live. If a discharge-medication section is populated, the
--     initiation/discontinuation analysis discussed for Aim 3 becomes available
--     without any new extraction work.
/*
SELECT section,
       COUNT(*)                                   AS n_rows,
       COUNT(DISTINCT hadm_id)                    AS n_admissions,
       COUNTIF(is_mra)                            AS n_mra,
       COUNTIF(is_mra AND is_held_or_stopped)     AS n_mra_held_or_stopped,
       COUNTIF(is_mra AND is_held)                AS n_mra_held,
       COUNTIF(NOT drug_in_lexicon)               AS n_not_in_lexicon
FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.home_note_reparsed`
GROUP BY 1 ORDER BY n_rows DESC;
*/

-- 1b. How much MRA exposure the discarded flags would remove, and how the existing
--     held/stopped detection interacts with lexicon failures and PRN status.
/*
SELECT is_held_or_stopped, is_held, drug_in_lexicon, is_prn,
       COUNT(*)                AS n_rows,
       COUNT(DISTINCT hadm_id) AS n_admissions
FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.home_note_reparsed`
WHERE is_mra
GROUP BY 1, 2, 3, 4 ORDER BY n_rows DESC;
*/


-- ============================================================
-- STEP 2. Assertion resolution.
-- ============================================================

CREATE OR REPLACE TABLE `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.med_mention_context` AS

WITH src AS (
  SELECT
    note_id, subject_id, hadm_id, section,
    drug, ingredient_base, drug_in_lexicon,
    is_prn, is_taper, is_bridge,
    is_held, is_held_or_stopped,
    total_daily_dose_mg_clean,
    is_mra, is_sglt2i, is_acei, is_arb, is_arni, is_bb_gdmt, is_loop_diuretic,
    raw,
    LOWER(IFNULL(raw, ''))     AS raw_l,
    LOWER(IFNULL(section, '')) AS section_l
  FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.home_note_reparsed`
),

resolved AS (
  SELECT
    *,

    -- Derived from the pipeline's own flags. is_held_or_stopped is the union; is_held
    -- is the temporary subset; the difference is a genuine discontinuation.
    (is_held_or_stopped AND NOT IFNULL(is_held, FALSE)) AS flag_stopped,

    -- Residual pass over the source line, for assertion classes the pipeline does not
    -- currently model. Scoped to the parsed line rather than the whole note, so a
    -- modifier several medications away cannot fire.
    REGEXP_CONTAINS(LOWER(IFNULL(section, '')), r'allerg|adverse|intoleran')
      OR REGEXP_CONTAINS(raw_l, r'\b(allerg\w*|adverse reaction|intoleran\w*)\b')
                                                        AS ctx_allergy,

    REGEXP_CONTAINS(raw_l, r'\b(family history|fhx|mother|father|sister|brother|'
                        || r'son|daughter|spouse|husband|wife)\b')
                                                        AS ctx_other_person,

    REGEXP_CONTAINS(raw_l, r'\b(previously|in the past|formerly|used to|was on|'
                        || r'were on|has been on|had been on|history of|h/o|per omr)\b')
                                                        AS ctx_historical,

    REGEXP_CONTAINS(raw_l, r'\b(will start|to start|plan(ned)? to|planning|'
                        || r'newly started|patient started on|recommend\w*)\b')
                                                        AS ctx_planned,

    REGEXP_CONTAINS(raw_l, r"\b(not taking|not on|denies|denied|declin\w*|refus\w*|"
                        || r"never (took|taken|on|started)|not started|had not started)\b")
                                                        AS ctx_negated,

    -- Residual discontinuation wording, used ONLY to measure what the pipeline's own
    -- flag missed. Reported in Step 3, not used to override it.
    REGEXP_CONTAINS(raw_l, r"\b(d/?c'?d|dc'?d|discontinu\w*|stopped|no longer (taking|on)|"
                        || r"came off|taken off|ceased)\b")
                                                        AS ctx_discontinued
  FROM src
)

SELECT
  note_id, subject_id, hadm_id, section, drug, ingredient_base, raw,
  drug_in_lexicon, is_prn, is_taper, is_bridge,
  is_held, is_held_or_stopped, flag_stopped,
  ctx_allergy, ctx_other_person, ctx_historical, ctx_planned, ctx_negated,
  ctx_discontinued,
  total_daily_dose_mg_clean,
  is_mra, is_sglt2i, is_acei, is_arb, is_arni, is_bb_gdmt, is_loop_diuretic,

  -- Single assertion label. Order matters: the most decisive exclusions are tested
  -- first, and HELD is tested last so that a mention both held and later stopped
  -- resolves to stopped.
  CASE
    WHEN NOT IFNULL(drug_in_lexicon, TRUE)  THEN 'not_a_drug'
    WHEN ctx_other_person                   THEN 'other_experiencer'
    WHEN ctx_allergy                        THEN 'allergy'
    WHEN ctx_negated                        THEN 'negated'
    WHEN flag_stopped OR ctx_discontinued   THEN 'stopped'
    WHEN ctx_historical                     THEN 'historical'
    WHEN ctx_planned                        THEN 'planned'
    WHEN IFNULL(is_held, FALSE)             THEN 'held'
    ELSE 'affirmed'
  END AS assertion,

  -- The flag downstream analyses use. 'held' counts as chronic exposure; every other
  -- non-affirmed state does not. PRN is excluded because intermittent as-needed use is
  -- not chronic daily therapy, which is the exposure the calcification hypothesis
  -- concerns.
  CASE
    WHEN NOT IFNULL(drug_in_lexicon, TRUE)  THEN FALSE
    WHEN ctx_other_person OR ctx_allergy OR ctx_negated
      OR flag_stopped OR ctx_discontinued
      OR ctx_historical OR ctx_planned      THEN FALSE
    WHEN IFNULL(is_prn, FALSE)              THEN FALSE
    ELSE TRUE
  END AS is_current_home_med

FROM resolved;


-- ============================================================
-- STEP 3. Did the pipeline's own flag already catch this?
-- ------------------------------------------------------------
-- Cross-tabulates the existing is_held_or_stopped against the residual regex pass.
-- Cell (FALSE, TRUE) is what the pipeline missed and is the only justification for
-- keeping the regex layer. If that cell is small, delete the regex and simply
-- propagate the existing flags.
-- ============================================================
/*
SELECT is_held_or_stopped, ctx_discontinued,
       COUNT(*)                AS n_rows,
       COUNT(DISTINCT hadm_id) AS n_admissions
FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.med_mention_context`
WHERE is_mra
GROUP BY 1, 2 ORDER BY 1, 2;
*/


-- ============================================================
-- STEP 4. VALIDATION. Required before the flag enters any analysis.
-- ------------------------------------------------------------
-- An NLP-derived phenotype is not usable until measured against manual review. Draw a
-- stratified sample, adjudicate `raw` by hand, and report sensitivity, specificity,
-- PPV and NPV for is_current_home_med. Stratification matters: a simple random sample
-- of 200 would contain almost no allergy or other_experiencer cases, which are exactly
-- the classes whose error rate is unknown.
-- ============================================================
/*
SELECT assertion, hadm_id, drug, ingredient_base, is_current_home_med, raw
FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.med_mention_context`
WHERE is_mra
QUALIFY ROW_NUMBER() OVER (PARTITION BY assertion
        ORDER BY FARM_FINGERPRINT(CONCAT(note_id, IFNULL(drug, '')))) <= 30
ORDER BY assertion;
*/


-- ============================================================
-- STEP 5. PROPAGATION (the change that actually fixes the pipeline)
-- ------------------------------------------------------------
-- MIMICIV_ADMISSION_MEDS_FINAL and gdmt_by_admission must carry an assertion-aware
-- flag, otherwise every downstream study repeats this error. Rebuild the class
-- booleans in those tables as, for example:
--
--   LOGICAL_OR(is_mra AND is_current_home_med) AS mra
--
-- rather than LOGICAL_OR(is_mra). This is a change to the shared pipeline and benefits
-- every study built on it, not only this one.
-- ============================================================
