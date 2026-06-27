#!/usr/bin/env python3
"""Table 1 EchoNext-Mini comparison column — patient-level (most-recent ECG) cohort
characteristics of the released EchoNext-Mini benchmark, for side-by-side comparison with
the MIMIC-IV validation cohort.

Input: echonext_metadata_100k.csv from the credentialed EchoNext-Mini release
       (PhysioNet echonext/1.1.1; not redistributed here). Pass its path as argv[1].
Output: prints the EchoNext-Mini column (n=36,286 patients, one most-recent ECG each).

NOTE on units: values are per-patient (most_recent_ecg==1). The per-ECG prevalences in
Hughes et al. (all 100,000 ECGs; e.g., 52.2% any SHD) are higher because patients with
repeat ECGs carry more disease — report per-patient for a like-for-like cohort comparison.
"""
import sys, csv, collections, numpy as np
path = sys.argv[1] if len(sys.argv) > 1 else "echonext_metadata_100k.csv"
rows = [r for r in csv.DictReader(open(path)) if r["most_recent_ecg"] == "1"]
n = len(rows)
def miqr(col):
    a = np.array([float(r[col]) for r in rows if r[col] not in ("", "NA", "nan") and 0 < float(r[col]) < 9000])
    return f"{np.median(a):.0f} [{np.percentile(a,25):.0f}-{np.percentile(a,75):.0f}]"
print(f"EchoNext-Mini, most-recent ECG per patient: n={n:,}")
print(f"Age, years: {miqr('age_at_ecg')}")
print(f"Female, %: {100*sum(r['sex']=='female' for r in rows)/n:.1f}")
rc = collections.Counter(r["race_ethnicity"] for r in rows)
print(f"Race (White/Black/Hispanic/Asian/Other-unk), %: "
      f"{100*rc['white']/n:.1f} / {100*rc['black']/n:.1f} / {100*rc['hispanic']/n:.1f} / "
      f"{100*rc['asian']/n:.1f} / {100*(rc['other']+rc['unknown'])/n:.1f}")
for c, lab, u in [("ventricular_rate","Ventricular rate","bpm"),("pr_interval","PR interval","ms"),
                  ("qrs_duration","QRS duration","ms"),("qt_corrected","QTc","ms")]:
    print(f"{lab}, {u}: {miqr(c)}")
for col, lab in [("shd_moderate_or_greater_flag","Any SHD"),("lvef_lte_45_flag","Reduced LVEF"),
    ("lvwt_gte_13_flag","LV hypertrophy"),("rv_systolic_dysfunction_moderate_or_greater_flag","RV dysfunction"),
    ("pericardial_effusion_moderate_large_flag","Pericardial effusion"),("pasp_gte_45_flag","Elevated PASP"),
    ("tr_max_gte_32_flag","Elevated TR Vmax"),("aortic_stenosis_moderate_or_greater_flag","Aortic stenosis"),
    ("aortic_regurgitation_moderate_or_greater_flag","Aortic regurgitation"),
    ("mitral_regurgitation_moderate_or_greater_flag","Mitral regurgitation"),
    ("tricuspid_regurgitation_moderate_or_greater_flag","Tricuspid regurgitation"),
    ("pulmonary_regurgitation_moderate_or_greater_flag","Pulmonic regurgitation")]:
    print(f"{lab}, %: {100*sum(int(r[col]) for r in rows)/n:.1f}")
