#!/usr/bin/env python3
"""Secondary LV-hypertrophy analysis (reported in Results / Discussion).

Does the model's wall-thickness probability discriminate higher-grade hypertrophy better than the
primary 1.3 cm label? Computes AUROC (2,000-sample patient-level bootstrap 95% CI) of the LVWT
probability against: (a) septal IVS >=1.5 cm and (b) categorical moderate-or-severe LVH, on the
FULL locked one-per-patient cohort. Prints a sanity check that must reproduce Table 2 exactly:
the locked lvwt_gte_13 label -> 22.4% prevalence, AUROC 0.679.

Inputs (all under $ECHONEXT_DATA, default ~/Desktop/RESEARCH):
  EchoNext-repo/results_full/{probs.npy, kept_paths.txt}   model outputs
  lvh_secondary.csv                                        export of sql/06_lvh_secondary.sql
Run:  bq query --use_legacy_sql=false < sql/06_lvh_secondary.sql  (save -> lvh_secondary.csv)
      python code/lvh_secondary.py
"""
import os, csv, numpy as np
from sklearn.metrics import roc_auc_score

BASE = os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH"))
RES  = os.path.join(BASE, "EchoNext-repo/results_full")
LVWT_IDX = 1   # COLS index of 'lvwt_gte_13' -> model wall-thickness probability

probs = np.load(os.path.join(RES, "probs.npy"))
paths = [p for p in open(os.path.join(RES, "kept_paths.txt")).read().split("\n") if p]
lvh   = {r["ecg_path"]: r for r in csv.DictReader(open(os.path.join(BASE, "lvh_secondary.csv")))}

p, y_lock, y_max13, y_ivs15, y_cat = [], [], [], [], []
for i, pth in enumerate(paths):
    d = lvh.get(pth)
    if d is None:
        continue
    p.append(probs[i, LVWT_IDX]); y_lock.append(int(d["lvwt_gte_13"]))
    y_max13.append(int(d["lvh_max13_check"])); y_ivs15.append(int(d["ivs_gte_15"])); y_cat.append(int(d["lvh_modsev_cat"]))
p = np.array(p); y_lock = np.array(y_lock); y_max13 = np.array(y_max13); y_ivs15 = np.array(y_ivs15); y_cat = np.array(y_cat)

agree = 100 * (y_max13 == y_lock).mean()
print(f"matched {len(p)}/{len(paths)} cohort ECGs; regenerated max(IVS,inflat)>=1.3 vs locked "
      f"lvwt_gte_13: {agree:.3f}% agree (expect 100.000% on the locked cohort)\n")

def boot_ci(y, pp, B=2000):
    rng = np.random.default_rng(0); a = []
    for _ in range(B):
        idx = rng.integers(0, len(y), len(y))
        if 0 < y[idx].sum() < len(y):
            a.append(roc_auc_score(y[idx], pp[idx]))
    return np.percentile(a, [2.5, 97.5])

for name, y in [("LVWT >=1.3 cm  (locked Table-2 label; SANITY -> 0.679 / 22.4%)", y_lock),
                ("Septal (IVS) >=1.5 cm", y_ivs15),
                ("Categorical moderate-or-severe LVH", y_cat)]:
    auc = roc_auc_score(y, p); lo, hi = boot_ci(y, p)
    print(f"{name}\n    n={len(y)}  prev={100*y.mean():.1f}%  n_pos={int(y.sum())}  "
          f"AUROC={auc:.3f} (95% CI {lo:.3f}-{hi:.3f})")
