-- ============================================================
-- File: 00_negation_context.sql
-- Study: MAC-HFpEF
-- Database: MIMIC-IV v3.1 via BigQuery + local medication reconciliation pipeline
-- Author: Emmanuel Otabor, MD
-- Description: ConText/NegEx pass over note-derived medication mentions. Assigns
--              negation, temporality and experiencer modifiers so that mentions of a
--              drug the patient is NOT currently taking are not counted as exposure.
-- Dependencies: 2_MIMIC_IV_ADMISSION_MEDS.MIMICIV_ADMISSION_MEDS_FINAL
--               plus the source note text (bind <<TEXT_COL>> / <<NOTE_TABLE>> below)
-- Output: 2_MIMIC_IV_ADMISSION_MEDS.med_mention_context
-- ============================================================
--
-- WHY THIS EXISTS
-- Medication extraction from free text records the drug NAME but not the assertion
-- made about it. A note saying "spironolactone stopped due to hyperkalemia" contains
-- the token "spironolactone" and will be extracted as though the patient were taking
-- it. ConText (the NegEx extension) fixes this by tagging each mention with modifiers:
-- is it negated, is it historical, is it hypothetical, and is it about the patient.
--
-- Clinically the distinctions that matter for a HOME medication list are:
--   DISCONTINUED  - was on it, stopped        -> NOT current exposure
--   HELD          - temporarily interrupted   -> IS chronic exposure, flagged separately
--   NEGATED       - never on it / not taking  -> NOT exposure
--   HISTORICAL    - past use                  -> NOT current exposure
--   PLANNED       - not yet started           -> NOT exposure
--   ALLERGY       - listed as an allergy      -> NOT exposure (and a contraindication)
--   OTHER_PERSON  - family member's drug      -> NOT exposure
--
-- HELD is deliberately separated from DISCONTINUED. A drug held for acute kidney
-- injury during an admission is still the patient's chronic therapy; a drug
-- discontinued is not. For a multi-year exposure window these are different states
-- and collapsing them loses real exposure.

CREATE OR REPLACE TABLE `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.med_mention_context` AS

WITH mention AS (
  -- One row per extracted medication mention, with the surrounding source text.
  -- BIND THESE TWO PLACEHOLDERS to whatever the note pipeline retains:
  --   <<NOTE_TABLE>> : the table holding the parsed note lines
  --   <<TEXT_COL>>   : the column holding the source sentence / line / window
  SELECT
    f.hadm_id,
    f.subject_id,
    f.norm_ingredient,
    f.drug_display,
    f.in_note, f.in_medrecon, f.in_rx,
    f.home_med_confidence,
    f.is_mra,
    LOWER(COALESCE(n.<<TEXT_COL>>, f.norm_ingredient)) AS src_text
  FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.MIMICIV_ADMISSION_MEDS_FINAL` f
  LEFT JOIN `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.<<NOTE_TABLE>>` n
         ON n.hadm_id = f.hadm_id
        AND REGEXP_CONTAINS(LOWER(n.<<TEXT_COL>>), CONCAT(r'\b', REGEXP_REPLACE(
              REGEXP_EXTRACT(LOWER(f.norm_ingredient), r'[a-z]{4,}'), r'([.\\+*?()\[\]{}|^$])', r'\\\1'), r''))
),

windowed AS (
  -- Restrict modifier matching to a scope window around the drug term rather than the
  -- whole note. ConText uses a token window; a character window is a defensible
  -- approximation and avoids a modifier three sentences away firing spuriously.
  SELECT
    m.*,
    REGEXP_EXTRACT(LOWER(norm_ingredient), r'[a-z]{4,}') AS ing_token,
    SUBSTR(
      src_text,
      GREATEST(1, STRPOS(src_text, IFNULL(REGEXP_EXTRACT(LOWER(norm_ingredient), r'[a-z]{4,}'), '~')) - 70),
      150
    ) AS win
  FROM mention m
),

flagged AS (
  SELECT
    *,
    -- DISCONTINUED: the drug was being taken and has been formally stopped.
    REGEXP_CONTAINS(win, r"\b(d/?c'?d|dc'?d|d/c|discontinu\w*|stopped|stop taking|"
                       || r"no longer (taking|on)|came off|taken off|ceased|"
                       || r"recently stopped|was stopped|were stopped)\b") AS mod_discontinued,

    -- HELD: temporary interruption. Still chronic therapy.
    REGEXP_CONTAINS(win, r"\b(held|on hold|holding|hold\b|being held|were held|was held)\b")
                                                                            AS mod_held,

    -- NEGATED: explicitly not taking, never taken, declined.
    REGEXP_CONTAINS(win, r"\b(not taking|not on|denies|denied|never (took|taken|on|started)|"
                       || r"not started|had not started|declin\w*|refus\w*|without)\b")
                                                                            AS mod_negated,

    -- HISTORICAL: past exposure, not current.
    REGEXP_CONTAINS(win, r"\b(previously|in the past|formerly|used to|was on|were on|"
                       || r"has been on|had been on|history of|h/o|prior to|"
                       || r"per omr|previously on)\b")                      AS mod_historical,

    -- PLANNED: prescribed going forward, not a home medication at this admission.
    REGEXP_CONTAINS(win, r"\b(will start|to start|plan(ned)? to|planning|consider\w*|"
                       || r"recommend\w*|start(ed|ing)? on|newly started|"
                       || r"patient started on)\b")                         AS mod_planned,

    -- ALLERGY: appears in an allergy or intolerance list.
    REGEXP_CONTAINS(win, r"\b(allerg\w*|adverse reaction|intoleran\w*|reaction to)\b")
                                                                            AS mod_allergy,

    -- OTHER EXPERIENCER: the drug belongs to somebody else.
    REGEXP_CONTAINS(win, r"\b(family history|fhx|mother|father|sister|brother|"
                       || r"son|daughter|spouse|husband|wife)\b")           AS mod_other_person,

    -- UNCERTAIN: dosing or status not established.
    REGEXP_CONTAINS(win, r"\b(unclear|uncertain|\?|unknown|unable to confirm|"
                       || r"not clear|possibly|may be)\b")                  AS mod_uncertain
  FROM windowed
)

SELECT
  hadm_id, subject_id, norm_ingredient, drug_display, ing_token,
  in_note, in_medrecon, in_rx, home_med_confidence, is_mra,
  mod_discontinued, mod_held, mod_negated, mod_historical,
  mod_planned, mod_allergy, mod_other_person, mod_uncertain,
  -- Retained so the validation sampler below can show a reviewer the text the
  -- classifier actually saw. Without it manual review is impossible.
  win AS context_window,

  -- Assertion status. Order matters: the most decisive exclusions are tested first,
  -- and HELD is tested AFTER discontinued so that "held then discontinued" resolves
  -- to discontinued rather than to held.
  CASE
    WHEN mod_other_person                      THEN 'other_experiencer'
    WHEN mod_allergy                           THEN 'allergy'
    WHEN mod_negated                           THEN 'negated'
    WHEN mod_discontinued                      THEN 'discontinued'
    WHEN mod_historical                        THEN 'historical'
    WHEN mod_planned                           THEN 'planned'
    WHEN mod_held                              THEN 'held'
    ELSE 'affirmed'
  END AS assertion,

  -- The exposure flag downstream analyses should use.
  -- 'held' counts as chronic exposure; every other non-affirmed state does not.
  CASE
    WHEN mod_other_person OR mod_allergy OR mod_negated
      OR mod_discontinued OR mod_historical OR mod_planned THEN FALSE
    ELSE TRUE
  END AS is_current_home_med

FROM flagged;


-- ============================================================
-- IMMEDIATE PARTIAL FIX (runnable now, no note text required)
-- ------------------------------------------------------------
-- Where normalisation failed, the assertion is already visible inside
-- norm_ingredient itself ("spironolactone dc'd", "aldactone stopped"). These can be
-- excluded without any note linkage. This catches only mentions whose normalisation
-- also failed, so it is a floor on the problem, not a solution to it.
-- ============================================================

-- SELECT
--   COUNT(*)                                                    AS n_mra_rows,
--   COUNTIF(REGEXP_CONTAINS(LOWER(norm_ingredient),
--     r"\b(d/?c'?d|dc'?d|stopped|held|hold|not taking|previously|discontinu\w*|"
--     || r"unclear|had not started|no longer|on hold|were held)\b"))  AS n_assertion_negative,
--   COUNTIF(NOT REGEXP_CONTAINS(LOWER(norm_ingredient), r'^[a-z/\- ]+$')) AS n_normalisation_failed
-- FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.MIMICIV_ADMISSION_MEDS_FINAL`
-- WHERE is_mra;


-- ============================================================
-- VALIDATION (REQUIRED before the cleaned flag is used in analysis)
-- ------------------------------------------------------------
-- An NLP phenotype is not usable until its performance is measured against manual
-- review. Draw a stratified random sample, review the source text by hand, and report
-- sensitivity, specificity, PPV and NPV for is_current_home_med. Stratify so that the
-- rare classes are actually represented; a simple random sample of 200 would contain
-- almost no allergy or other_experiencer cases.
-- ============================================================

-- SELECT assertion, hadm_id, norm_ingredient, is_current_home_med, context_window
-- FROM `the-project-476301.2_MIMIC_IV_ADMISSION_MEDS.med_mention_context`
-- WHERE is_mra
-- QUALIFY ROW_NUMBER() OVER (PARTITION BY assertion ORDER BY FARM_FINGERPRINT(
--          CONCAT(CAST(hadm_id AS STRING), norm_ingredient))) <= 30
-- ORDER BY assertion;
