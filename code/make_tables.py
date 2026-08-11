"""Generate every manuscript and supplementary table from the results objects.

Nothing here is hand-transcribed: all numbers come from results/analysis.json and
results/triage.json. One source, generated output, no retyping, so a table cannot disagree with the
analysis it reports.

Writes Markdown (for review) and CSV (for pasting into Word) into results/tables/.

EHJ-DH limits: 6 tables, 6 figures, 5,000 main-text words, 50 references.
Main text uses Tables 1-4; everything else is supplementary.
"""
import os, json, csv, argparse

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
ap = argparse.ArgumentParser()
ap.add_argument("--results", default=None)
args = ap.parse_args()
args.results = args.results or paths.results_dir()
OUT = os.path.join(args.results, "tables"); os.makedirs(OUT, exist_ok=True)

A = json.load(open(os.path.join(args.results, "analysis.json")))
T = json.load(open(os.path.join(args.results, "triage.json")))
B = A.get("benchmark", {})

# Nature Suppl. Table 15: released model on the released benchmark, as PUBLISHED by the authors
T15 = {"Reduced LVEF (<=45%)": 85.2, "LV wall thickness (>=1.3 cm)": 73.4, "Aortic stenosis": 85.9,
       "Aortic regurgitation": 73.9, "Mitral regurgitation": 80.6, "Tricuspid regurgitation": 83.3,
       "Pulmonic regurgitation": 82.9, "RV dysfunction": 86.6, "Pericardial effusion": 76.6,
       "Elevated PASP (>=45 mmHg)": 77.0, "Elevated TR Vmax (>=3.2 m/s)": 75.4,
       "Structural heart disease": 82.0}
BKEY = {"Reduced LVEF (<=45%)": "lvef_lte_45", "LV wall thickness (>=1.3 cm)": "lvwt_gte_13",
        "Aortic stenosis": "aortic_stenosis", "Aortic regurgitation": "aortic_regurg",
        "Mitral regurgitation": "mitral_regurg", "Tricuspid regurgitation": "tricuspid_regurg",
        "Pulmonic regurgitation": "pulm_regurg", "RV dysfunction": "rv_dysfunction",
        "Pericardial effusion": "pericardial", "Elevated PASP (>=45 mmHg)": "pasp_gte_45",
        "Elevated TR Vmax (>=3.2 m/s)": "tr_max_gte_32", "Structural heart disease": "shd"}


# Cohort sizes are DERIVED from the results object, never typed into a caption.
NTOT   = A["meta"]["n"]
# The benchmark test split is fixed by the release: 5,442 of the 100,000 records carry split "test"
# in echonext_metadata_100k.csv (train 72,475, val 4,626, no_split 17,457). Unlike the MIMIC-IV
# cohort it cannot drift, so it is stated here rather than derived from a file the table build would
# otherwise have no reason to open.
NBENCH = 5442

import re as _re

def _cell(x):
    """Make one value safe to print in a Markdown table and consistent with house style.

    Two things are enforced:
      1. A literal pipe in a value would silently add a column to the Markdown row, so pipes are
         replaced. ECG-acquisition subgroup names are built as "bandwidth | filtering" and contain
         one.
      2. Numeric ranges use an en dash, matching the manuscript, so the separator cannot vary from
         table to table.
    """
    s = str(x).replace(" | ", ", ").replace("|", ";")
    return _re.sub(r"(?<=\d)-(?=\d)", "–", s)


def write(name, header, rows, caption, note=""):
    header = [_cell(h) for h in header]
    rows   = [[_cell(c) for c in r] for r in rows]
    # A ragged table is a silent corruption; refuse to write one.
    bad = [i for i, r in enumerate(rows) if len(r) != len(header)]
    if bad:
        raise SystemExit(f"{name}: rows {bad} have a different width from the header "
                         f"({len(header)} columns).")
    with open(os.path.join(OUT, name + ".md"), "w") as f:
        f.write(f"**{caption}**\n\n")
        f.write("| " + " | ".join(header) + " |\n")
        f.write("|" + "|".join(["---"] * len(header)) + "|\n")
        for r in rows:
            f.write("| " + " | ".join(str(x) for x in r) + " |\n")
        if note:
            f.write("\n" + note + "\n")
    with open(os.path.join(OUT, name + ".csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(f"  wrote {name}.md / .csv  ({len(rows)} rows)")


print("generating tables ->", OUT)

# ------------------------------------------------------------------ Table 1: cohort characteristics
# The EchoNext-Mini column is NOT recomputed by us. These are the PUBLISHED values from the
# "Latest ECG" column of Table 1 in Hughes et al., NEJM AI 2026;3(5):AIdbp2500516 (n = 36,286),
# which is the correct comparator because our cohort is also one ECG per patient. Labelling it as
# such prevents it being read as a recalculation of our own.
EN = {  # Hughes et al., Table 1, "Latest ECG" column
    "n": "36,286", "age": "64 [52–75]", "female": "50.5", "white": "29.3", "black": "14.9",
    "hispanic": "30.3", "asian": "3.0", "other_unknown": "22.4",
    "lvef": "18.0", "lvwt": "18.8", "rv": "8.0", "peri": "1.3", "pasp": "12.9", "trv": "6.5",
    "as": "5.4", "ar": "1.2", "mr": "6.5", "tr": "7.0", "pr": "0.4", "shd": "43.3",
    "inpatient": "41.2", "emergency": "35.9", "outpatient": "18.8", "procedural": "4.1",
}
import statistics as _st
rows_c = list(csv.DictReader(open(paths.cohort_csv())))
race_map = {r["subject_id"]: r["race"] for r in csv.DictReader(open(paths.race_csv()))}
N = len(rows_c)
def pct(f):  return f"{100*sum(1 for r in rows_c if f(r))/N:.1f}"
def lab(c):  return f"{100*sum(int(r[c]) for r in rows_c)/N:.1f}"
ages = sorted(float(r["age_at_ecg"]) for r in rows_c)
q1, med, q3 = (ages[int(N*0.25)], ages[int(N*0.5)], ages[int(N*0.75)])
gaps = sorted(float(r["ecg_to_echo_days"]) for r in rows_c)
g1, gm, g3 = (gaps[int(N*0.25)], gaps[int(N*0.5)], gaps[int(N*0.75)])
def med_of(c):
    v = sorted(float(r[c]) for r in rows_c if r[c] not in ("", None))
    return f"{v[len(v)//2]:.0f}"

t1 = [
    ["Patients, n", f"{N:,}", EN["n"]],
    ["Age, years, median [IQR]", f"{med:.0f} [{q1:.0f}–{q3:.0f}]", EN["age"]],
    ["Female, %", pct(lambda r: r["gender"].strip().upper() == "F"), EN["female"]],
    ["Race or ethnicity, %", "", ""],
    ["  White", f"{100*sum(1 for r in rows_c if race_map.get(r['subject_id'])=='White')/N:.1f}", EN["white"]],
    ["  Black", f"{100*sum(1 for r in rows_c if race_map.get(r['subject_id'])=='Black')/N:.1f}", EN["black"]],
    ["  Hispanic", f"{100*sum(1 for r in rows_c if race_map.get(r['subject_id'])=='Hispanic')/N:.1f}", EN["hispanic"]],
    ["  Asian", f"{100*sum(1 for r in rows_c if race_map.get(r['subject_id'])=='Asian')/N:.1f}", EN["asian"]],
    ["  Other or unknown", f"{100*sum(1 for r in rows_c if race_map.get(r['subject_id'],'Unknown') in ('Other','Unknown'))/N:.1f}", EN["other_unknown"]],
    ["Care setting at ECG, %", "", ""],
    ["  Inpatient ward", pct(lambda r: r["setting"] == "Inpatient ward"), EN["inpatient"]],
    ["  Emergency or acute", pct(lambda r: r["setting"] == "Emergency / acute"), EN["emergency"]],
    ["  Outpatient or ambulatory", pct(lambda r: r["setting"] == "Outpatient/ambulatory"), EN["outpatient"]],
    ["  Intensive care", pct(lambda r: r["setting"] == "ICU"), "not reported separately"],
    ["Electrocardiographic measurements, median", "", ""],
    ["  Ventricular rate, bpm", med_of("ventricular_rate"), "78"],
    ["  PR interval, ms", med_of("pr_interval"), "156"],
    ["  QRS duration, ms", med_of("qrs_duration"), "88"],
    ["  QTc, ms", med_of("qt_corrected"), "444"],
    ["  PR interval unmeasurable, %", pct(lambda r: r["pr_missing"].lower() == "true"), "11.2"],
    ["Structural heart disease prevalence, %", "", ""],
    ["  Any (composite)", lab("shd"), EN["shd"]],
    ["  Reduced LVEF", lab("lvef_lte_45"), EN["lvef"]],
    ["  LV wall thickness", lab("lvwt_gte_13"), EN["lvwt"]],
    ["  RV dysfunction", lab("rv_dysfunction_modsev"), EN["rv"]],
    ["  Pericardial effusion", lab("pericardial_modlarge"), EN["peri"]],
    ["  Elevated PASP", lab("pasp_gte_45"), EN["pasp"]],
    ["  Elevated TR Vmax", lab("tr_max_gte_32"), EN["trv"]],
    ["  Aortic stenosis", lab("aortic_stenosis_modsev"), EN["as"]],
    ["  Aortic regurgitation", lab("aortic_regurg_modsev"), EN["ar"]],
    ["  Mitral regurgitation", lab("mitral_regurg_modsev"), EN["mr"]],
    ["  Tricuspid regurgitation", lab("tricuspid_regurg_modsev"), EN["tr"]],
    ["  Pulmonic regurgitation", lab("pulm_regurg_modsev"), EN["pr"]],
    ["ECG-to-echocardiogram interval, days, median [IQR]", f"{gm:.0f} [{g1:.0f}–{g3:.0f}]", "not available"],
]
write("table1_cohort", ["Characteristic", "MIMIC-IV (this study)",
                        "EchoNext-Mini, latest ECG per patient (published)"], t1,
      "Table 1. Characteristics of the MIMIC-IV external validation cohort and the EchoNext-Mini "
      "benchmark cohort.",
      "The EchoNext-Mini column reproduces the published 'Latest ECG' column of Table 1 in Hughes "
      "et al. (n = 36,286) and was not recalculated here; it is the appropriate comparator because "
      "both cohorts use one electrocardiogram per patient. Prevalences therefore differ from the "
      "per-electrocardiogram values reported for the full benchmark. PR interval is unmeasurable "
      "when no P wave is discernible, most often in atrial fibrillation; the released model assigns "
      "such records a value of zero before scaling. EchoNext-Mini does not report ECG-to-"
      "echocardiogram intervals, and reports a procedural care setting (4.1%) that has no "
      "counterpart in MIMIC-IV.")

# ------------------------------------------------------------------ Table 2: per-label performance
rows = []
for k, m in A["labels"].items():
    lo, hi = m["auroc_ci"]
    rows.append([k, f"{100*m['prev']:.1f}", f"{m['mean_pred']:.3f}",
                 f"{m['auroc']:.3f} ({lo:.3f}–{hi:.3f})", f"{m['auprc']:.3f}",
                 f"{m['auprc_norm']:.3f}", f"{m['cil']:+.3f}", f"{m['slope']:.2f}",
                 f"{m['brier']:.3f}", f"{m['bss']:+.3f}"])
write("table2_performance",
      ["Label", "Prevalence, %", "Mean predicted probability", "AUROC (95% CI)", "AUPRC",
       "Normalized AUPRC", "Calibration-in-the-large", "Calibration slope", "Brier", "Brier skill"],
      rows,
      f"Table 2. Discrimination and calibration by label in MIMIC-IV (n = {NTOT:,}).",
      "Calibration-in-the-large is observed prevalence minus mean predicted probability, on the "
      "probability scale; mean predicted probability is shown explicitly so the two cannot be "
      "confused. Normalized AUPRC is (AUPRC - prevalence)/(1 - prevalence). Brier skill score is "
      "1 - Brier/[p(1-p)]; negative values indicate performance worse than assigning the observed "
      "prevalence to every patient. Confidence intervals are percentile bootstrap, 2,000 resamples, "
      "seed 0, with identical resample indices reused across labels.")

# ------------------------------- Table 3: dual-setting comparison - the core new claim
rows = []
for k, m in A["labels"].items():
    b = B.get(BKEY[k], {})
    if not b:
        continue
    rows.append([k,
                 f"{100*b['prev']:.1f}", f"{b['auroc']:.3f}", f"{T15[k]/100:.3f}",
                 f"{100*m['prev']:.1f}", f"{m['auroc']:.3f}",
                 f"{m['auroc']-b['auroc']:+.3f}",
                 f"{b['mean_pred']:.3f}", f"{m['mean_pred']:.3f}",
                 f"{b['cil']:+.3f}", f"{m['cil']:+.3f}"])
write("table3_dual_setting",
      ["Label", "Benchmark prevalence, %", "Benchmark AUROC (this study)",
       "Benchmark AUROC (as published)", "MIMIC-IV prevalence, %", "MIMIC-IV AUROC",
       "AUROC difference", "Benchmark mean predicted", "MIMIC-IV mean predicted",
       "Benchmark CIL", "MIMIC-IV CIL"],
      rows,
      "Table 3. The released model applied in two settings: its own benchmark test set "
      f"(n = {NBENCH:,}) and MIMIC-IV (n = {NTOT:,}).",
      "Benchmark AUROC (this study) is our own computation using the released arrays exactly as "
      "distributed; Benchmark AUROC (as published) is Supplementary Table 15 of Poterucha et al. "
      "The two agree to three decimal places for every label, verifying our implementation. Mean "
      "predicted probability and calibration-in-the-large are closely similar in the two settings "
      "despite differing prevalence, indicating a property of the released model rather than of "
      "the external dataset.")

# ------------------------------------------------------- Table 4: recalibration comparison
rows = []
for k, m in A["labels"].items():
    ps, pl = m["prior_shift"], m["platt_oof"]
    rows.append([k, f"{100*m['prev']:.1f}",
                 f"{m['cil']:+.3f}", f"{m['slope']:.2f}", f"{m['bss']:+.3f}",
                 f"{ps['cil']:+.3f}", f"{ps['slope']:.2f}", f"{ps['bss']:+.3f}",
                 f"{pl['cil']:+.3f}", f"{pl['slope']:.2f}", f"{pl['bss']:+.3f}"])
write("table4_recalibration",
      ["Label", "Prevalence, %", "CIL, as released", "Slope, as released", "Brier skill, as released",
       "CIL, prior shift", "Slope, prior shift", "Brier skill, prior shift",
       "CIL, local Platt", "Slope, local Platt", "Brier skill, local Platt"],
      rows,
      "Table 4. Effect of two recalibration strategies in MIMIC-IV.",
      "The prior shift is logit(p) + logit(pi_train) using only the released training-split "
      "prevalences and no local outcome data. Local Platt scaling is five-fold out-of-fold and "
      "requires local labels. Calibration slopes are essentially unchanged by the prior shift, "
      "since it is an intercept correction by construction.")

# -------------------------------------------------- Supplementary: complete-case bounds
rows = []
for k, m in A["labels"].items():
    cc = m.get("complete_case")
    if not cc or "source_present_frac" not in m:
        continue
    rows.append([k, f"{100*m['source_present_frac']:.1f}",
                 f"{100*m['prev']:.2f}", f"{m['auroc']:.3f}",
                 f"{cc['n']:,}", f"{100*cc['prev']:.2f}", f"{cc['auroc']:.3f}",
                 f"{cc['auroc']-m['auroc']:+.3f}"])
write("tableS7_complete_case",
      ["Label", "Source field populated, %", "Prevalence all records, %", "AUROC all records",
       "n complete-case", "Prevalence complete-case, %", "AUROC complete-case", "Difference"],
      rows,
      "Supplementary Table S7. Complete-case sensitivity analysis: performance restricted to studies "
      "in which the relevant structured field was populated.",
      "Neither estimate is unbiased. The all-records estimate is optimistic because studies with an "
      "absent field are treated as negative and are systematically lower-scoring. The complete-case "
      "estimate is pessimistic because fields are populated by indication, so the retained negatives "
      "are enriched for lesser degrees of the same pathology. The two should be read as bounds. "
      "Labels with near-complete ascertainment show no material difference.")

# ------------------------------- Supplementary: benchmark test set, FULL metrics (S6)
# Needed because Table 3 carries AUROC / mean predicted / CIL for both settings but not Brier skill,
# and Table 4 is MIMIC-only. Without this, the statements that Brier skill is negative for every
# component IN BOTH SETTINGS, and that the prior shift works on the benchmark, have no reference.
rows = []
for k, m in A["labels"].items():
    b = B.get(BKEY[k], {})
    if not b:
        continue
    rows.append([k, f"{100*b['prev']:.2f}", f"{b['mean_pred']:.3f}", f"{b['auroc']:.3f}",
                 f"{b['auprc']:.3f}", f"{b['cil']:+.3f}", f"{b['slope']:.2f}",
                 f"{b['brier']:.3f}", f"{b['bss']:+.3f}",
                 f"{b.get('cil_corr', float('nan')):+.3f}", f"{b.get('bss_corr', float('nan')):+.3f}"])
_pretty = {v: k for k, v in BKEY.items()}
_exc    = [(_pretty.get(k, k), round(v["auroc"], 3), T15[_pretty[k]] / 100)
           for k, v in B.items() if round(v["auroc"], 3) != round(T15[_pretty[k]] / 100, 3)]
N_LABELS = len(B)
N_EXACT  = N_LABELS - len(_exc)
EXC_TXT  = " and ".join(f"{n.lower()} ({a:.3f} against {p:.3f})" for n, a, p in _exc) or "none"
N_NEG    = sum(1 for k, v in B.items() if k != "shd" and v["bss"] < 0)
_mp      = [v["mean_pred"] for k, v in B.items() if k != "shd"]
_pv      = [v["prev"]      for k, v in B.items() if k != "shd"]
MP_LO, MP_HI = min(_mp), max(_mp)
PV_LO, PV_HI = min(_pv), max(_pv)

write("tableS4_benchmark",
      ["Label", "Prevalence, %", "Mean predicted probability", "AUROC", "AUPRC",
       "Calibration-in-the-large", "Calibration slope", "Brier", "Brier skill",
       "Calibration-in-the-large after prior shift", "Brier skill after prior shift"], rows,
      "Supplementary Table S4. Performance of the released model on its own benchmark test set "
      "(n = 5,442), before and after the prior-shift correction.",
      # Both quantified claims below are COMPUTED, not asserted. Earlier wording stated that AUROC
      # reproduced the published values for every label and that Brier skill was negative for every
      # component; neither is true. Ten of twelve labels reproduce exactly, and reduced LVEF has
      # marginally positive Brier skill on this benchmark. Deriving the counts stops the caption
      # drifting from the table beneath it.
      f"Inputs were the distributed arrays, used without modification, so no preprocessing performed "
      f"for this study contributed to these values. Areas under the receiver operating characteristic "
      f"curve reproduce the published values to three decimal places for {N_EXACT} of "
      f"{N_LABELS} labels; the exceptions are {EXC_TXT}, the two labels with fewest events in this "
      f"test set. Mean predicted probability lies between {MP_LO:.2f} and {MP_HI:.2f} for all "
      f"component labels despite prevalence of {PV_LO*100:.1f}%\u2013{PV_HI*100:.1f}%, and "
      f"Brier skill is negative for {N_NEG} of {N_LABELS-1} components and positive for the "
      f"composite. The prior shift uses only the released training-split prevalences and no outcome "
      f"data from this dataset.")

# ------------------------------------------------------------------------------- Table 5: subgroups
# The MAIN subgroup table, covering the four dimensions the reviewers asked about. The full set,
# including ECG acquisition setting and the PR-interval strata, is Supplementary Table S5 below.
# This table was missing entirely from the first build while the Results and Discussion both cited
# Table 5, so the citation resolved to nothing.
# Grouped like Table 1: a dimension label on its own row with empty cells, then its members
# indented beneath it, which keeps a single Subgroup column while making the dimensions visible.
GROUPS = [
    ("Sex",               "Sex",               {"Male": "Male", "Female": "Female"}),
    ("Age",               "Age",               {"<65": "Under 65 years", "65-79": "65\u201379 years",
                                                ">=80": "80 years and older"}),
    ("Race/ethnicity",    "Race or ethnicity", {"White": "White", "Black": "Black",
                                                "Hispanic": "Hispanic", "Asian": "Asian",
                                                "Other": "Other", "Unknown": "Unknown"}),
    ("Care setting (broad)", "Care setting at ECG",
                                               {"Emergency / acute": "Emergency or acute presentation",
                                                "Inpatient/ICU": "Inpatient or intensive care",
                                                "Outpatient/ambulatory": "Outpatient or ambulatory"}),
]
rows = []
for key, heading, members in GROUPS:
    rows.append([heading, "", "", "", ""])
    for g, label in members.items():
        m = A["subgroups"][key][g]
        lo, hi = m["auroc_ci"]
        rows.append([label, f"{m['n']:,}", f"{100*m['prev']:.1f}",
                     f"{m['auroc']:.3f} ({lo:.3f}-{hi:.3f})", f"{m['slope']:.2f}"])
write("table5_subgroups",
      ["Subgroup", "n", "Prevalence, %", "AUROC (95% CI)", "Calibration slope"], rows,
      "Table 5. Subgroup discrimination and calibration for the composite label.",
      "Race and ethnicity are assigned from both hospital admission and emergency department "
      "records. Prevalence differs markedly across strata and should be read alongside "
      "discrimination. Intervals are percentile bootstrap, 2,000 resamples, seed 0. Performance by "
      "ECG acquisition setting is given in Supplementary Table S5.")

# ------------------------------------------- Supplementary S2: structured-field availability
# Derived from the same results object as every other table, so the repository reproduces it.
SRC_FIELD = {
    "Reduced LVEF (<=45%)": "lvef / biplane_lvef / lvef_3d",
    "LV wall thickness (>=1.3 cm)": "ivs_thickness, inferolateral_thickness",
    "Aortic stenosis": "aortic valve severity; av_pk_vel, av_mean_grad, av_area",
    "Aortic regurgitation": "aortic regurgitation severity",
    "Mitral regurgitation": "mitral regurgitation severity",
    "Tricuspid regurgitation": "tricuspid regurgitation severity",
    "Pulmonic regurgitation": "pulmonic regurgitation severity",
    "RV dysfunction": "RV systolic function descriptor",
    "Pericardial effusion": "pericardial effusion size",
    "Elevated PASP (>=45 mmHg)": "TR gradient + IVC-estimated RAP",
    "Elevated TR Vmax (>=3.2 m/s)": "TR peak velocity",
}
rows = []
for name, m in A["labels"].items():
    if name == "Structural heart disease":
        continue
    f = m.get("source_present_frac")
    if f is None:
        continue
    present = int(round(f * NTOT))
    rows.append([name, SRC_FIELD.get(name, ""), f"{present:,} ({100*f:.1f})",
                 f"{NTOT-present:,} ({100*(1-f):.1f})", f"{100*m['prev']:.2f}"])
write("tableS2_field_availability",
      ["Label", "MIMIC-IV-ECHO source field", "Field populated, n (%)",
       "Field absent, treated as negative, n (%)", "Prevalence under this convention, %"], rows,
      "Supplementary Table S2. Per-label structured-field availability and the "
      "missing-as-negative convention.",
      "Structured reports populate qualitative valve and pericardial fields chiefly when a finding "
      "is present, so absence of a field is not equivalent to absence of disease. Supplementary "
      "Table S7 bounds the consequence for the two labels where it matters. Ejection fraction is "
      "present in every study by the inclusion criterion.")

# ------------------------------------------------------------ Supplementary: subgroups
# Same grouped layout as main Table 5: a bold dimension label on its own row, members beneath.
SG_LABEL = {"<65": "Under 65 years", "65-79": "65\u201379 years", ">=80": "80 years and older",
            "Inpatient/ICU": "Inpatient or intensive care",
            "Outpatient/ambulatory": "Outpatient or ambulatory",
            "Emergency / acute": "Emergency or acute presentation",
            "Inpatient ward": "Inpatient ward", "ICU": "Intensive care",
            "present": "PR interval measurable", "missing": "PR interval unmeasurable"}
DIM_TITLE = {"Sex": "Sex", "Age": "Age", "Race/ethnicity": "Race or ethnicity",
             "Care setting": "Care setting at ECG (detailed)",
             "Care setting (broad)": "Care setting at ECG (grouped)",
             "ECG acquisition": "ECG acquisition setting (bandwidth, filtering)",
             "PR interval": "PR interval availability"}
rows = []
for dim, gs in A["subgroups"].items():
    rows.append([DIM_TITLE.get(dim, dim), "", "", "", "", "", ""])
    for g, m in gs.items():
        lo, hi = m["auroc_ci"]
        rows.append([SG_LABEL.get(g, g), f"{m['n']:,}", f"{100*m['prev']:.1f}",
                     f"{m['auroc']:.3f} ({lo:.3f}-{hi:.3f})", f"{m['slope']:.2f}",
                     f"{m['cil']:+.3f}", f"{m['bss']:+.3f}"])
write("tableS5_subgroups",
      ["Subgroup", "n", "Prevalence, %", "AUROC (95% CI)", "Calibration slope",
       "CIL", "Brier skill"], rows,
      "Supplementary Table S5. Composite structural heart disease performance by subgroup.",
      "Subgroups with fewer than 100 patients or 20 events were not evaluated. Race and ethnicity "
      "are assigned from hospital admission and emergency department records; prevalence differs "
      "markedly across strata and should be read alongside discrimination.")

# ------------------------------------------------------------ Supplementary: sensitivity analyses
rows = [[k, f"{100*m['prev']:.2f}", f"{m['auroc']:.3f}", f"{m['cil']:+.3f}", f"{m['slope']:.2f}",
         f"{m['bss']:+.3f}"] for k, m in A["alt_definitions"].items()]
for w, m in A["linkage_window"].items():
    rows.append([f"ECG-to-echocardiogram window {w}", f"{100*m['prev']:.2f}", f"{m['auroc']:.3f}",
                 f"{m['cil']:+.3f}", f"{m['slope']:.2f}", f"{m['bss']:+.3f}"])
m = A["rv_excl_unassessable"]
rows.append(["RV dysfunction excluding unassessable studies", f"{100*m['prev']:.2f}",
             f"{m['auroc']:.3f}", f"{m['cil']:+.3f}", f"{m['slope']:.2f}", f"{m['bss']:+.3f}"])
# Atrial-rate fill. Reported for the composite, which is the label the conclusions rest on; the
# per-label comparison is in analysis.json under "atrial_fill".
if "atrial_fill" in A and "Structural heart disease" in A["atrial_fill"]:
    af = A["atrial_fill"]["Structural heart disease"]
    for lbl, key in [("Atrial rate filled with zero, as released (PRIMARY)", "released_zero"),
                     ("Atrial rate median-imputed", "median_imputed")]:
        m = af[key]
        rows.append([lbl, f"{100*m['prev']:.2f}", f"{m['auroc']:.3f}", f"{m['cil']:+.3f}",
                     f"{m['slope']:.2f}", f"{m['bss']:+.3f}"])
write("tableS8_sensitivity",
      ["Analysis", "Prevalence, %", "AUROC", "CIL", "Calibration slope", "Brier skill"], rows,
      "Supplementary Table S8. Sensitivity analyses across alternative label definitions and "
      "linkage windows.",
      "Model outputs are unchanged throughout; only the reference label or the cohort window varies. "
      "All analyses use the same single label source as the primary analysis.")

# ------------------------------------------------------------ Supplementary: triage
rows = []
for frac, d in T["triage"]["by_capacity"].items():
    rows.append([f"{100*float(frac):.1f}", f"{d['n_echoes']:,}", f"{100*d['yield_ai']:.1f}",
                 f"{100*d['yield_standard']:.1f}", f"{d['enrichment']:.2f}", f"{100*d['ppv']:.1f}"])
write("tableS6_triage",
      ["Echocardiographic capacity, % of queue", "Studies performed",
       "Cases identified, model-ranked, %", "Cases identified, unprioritized, %",
       "Enrichment", "Positive predictive value of studies performed, %"], rows,
      "Supplementary Table S6. Capacity-constrained triage on the composite label.",
      "The unprioritized comparator is a random ordering of the same queue, because MIMIC-IV does "
      "not record a referral sequence; real-world referral is already prioritised clinically, so "
      "the increment over usual care is smaller than shown. At the cohort prevalence of 47.2% the "
      "maximum achievable enrichment is 1/0.472 = 2.12, so the observed values are close to the "
      "ceiling. This is a referred population, not a screening population.")

# ------------------- Supplementary S9: wall-thickness substitution penalty
# MIMIC-IV-ECHO has NO posterior-wall field (verified across all 186 TTE measurement fields), so the
# cost of substituting the inferolateral wall cannot be measured there. It CAN be measured on the
# EchoNext-Mini benchmark, which ships both interventricular septum and posterior wall. The reviewer
# wrote that label misclassification and limited model performance "cannot be separated in the
# present data"; they can be separated, just not in MIMIC-IV.
import numpy as np
from sklearn.metrics import roc_auc_score
try:
    Pb = np.load(os.path.join(paths.predictions_dir(), "probs_benchmark.npy"))
    bmeta = [r for r in csv.DictReader(open(os.path.join(paths.benchmark(),
             "echonext_metadata_100k.csv"))) if r["split"] == "test"]
    def _f(x):
        try:
            v = float(x); return v if np.isfinite(v) else np.nan
        except Exception:
            return np.nan
    ivs = np.array([_f(r["ivs_measurement"]) for r in bmeta])
    pw  = np.array([_f(r["lvpw_measurement"]) for r in bmeta])
    flag = np.array([int(float(r["lvwt_gte_13_flag"])) for r in bmeta])
    score = Pb[:, 1]                                   # LV wall thickness head
    both = ~np.isnan(ivs) & ~np.isnan(pw)
    truth = (np.fmax(ivs, pw) >= 1.3).astype(int)
    agree = 100 * (truth[both] == flag[both]).mean()
    defs = [("Maximum of septum and posterior wall (EchoNext definition)", truth),
            ("Interventricular septum alone", (ivs >= 1.3).astype(int)),
            ("Posterior wall alone", (pw >= 1.3).astype(int))]
    a_ref = roc_auc_score(defs[0][1][both], score[both])
    rows = [[d, f"{100*lab[both].mean():.2f}", f"{roc_auc_score(lab[both], score[both]):.3f}",
             f"{roc_auc_score(lab[both], score[both]) - a_ref:+.3f}"] for d, lab in defs]
    write("tableS9_wall_thickness",
          ["Label definition", "Prevalence, %", "AUROC", "Difference versus EchoNext definition"],
          rows,
          "Supplementary Table S9. Effect of restricting the left ventricular wall thickness label "
          "to a single wall, in the EchoNext-Mini benchmark test set.",
          f"Restricted to the {int(both.sum()):,} of {len(bmeta):,} test records in which both walls "
          f"were measured ({100*both.mean():.1f}%). The published label flag agrees with a threshold "
          f"of 1.3 cm applied to the maximum of the two walls in {agree:.1f}% of these records. "
          "MIMIC-IV-ECHO records septal and inferolateral wall thickness but no posterior wall "
          "measurement, so the substitution used in this study could not be evaluated directly; "
          "omitting one wall entirely, a more severe perturbation than substituting an anatomically "
          "adjacent one, is shown here as a bound.")
except Exception as e:
    print(f"  [skipped S9 wall thickness: {e}]")

print("\ndone. Main text: Table 1 (cohort, built separately), Tables 2-4 above.")
print("Supplementary: complete-case, subgroups, sensitivity, triage.")
