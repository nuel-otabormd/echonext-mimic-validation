#!/usr/bin/env python3
"""Per-label recalibration table (Supplementary Table S4): Brier and calibration slope
before vs after five-fold out-of-fold Platt scaling, for all 12 labels. Writes
results_full/recal_per_label.json. Reads probs.npy + kept_paths.txt + cohort CSV."""
import os, csv, json, numpy as np
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import KFold
from sklearn.linear_model import LogisticRegression
RES = os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "EchoNext-repo/results_full")
probs = np.load(f"{RES}/probs.npy"); paths = [p for p in open(f"{RES}/kept_paths.txt").read().split("\n") if p]
coh = {r['ecg_path']: r for r in csv.DictReader(open(os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "cohort_oneperpt_full.csv")))}
COLS = ['lvef_lte_45','lvwt_gte_13','aortic_stenosis_modsev','aortic_regurg_modsev','mitral_regurg_modsev',
        'tricuspid_regurg_modsev','pulm_regurg_modsev','rv_dysfunction_modsev','pericardial_modlarge',
        'pasp_gte_45','tr_max_gte_32','shd']
NICE = ['LVEF<=45','LVWT>=1.3','AS','AR','MR','TR','PR','RV dysf','Pericardial','PASP>=45','TRVmax>=3.2','SHD']
rows = [coh[p] for p in paths]; y = np.array([[int(r[c]) for c in COLS] for r in rows]); n = len(rows)
def slope(ys, p):
    lg = np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6)))
    return float(LogisticRegression(C=1e6).fit(lg.reshape(-1,1), ys).coef_[0,0])
out = {}
for j, name in enumerate(NICE):
    ys, ps = y[:,j], probs[:,j]
    oof = np.zeros(n); lg = np.log(np.clip(ps,1e-6,1-1e-6)/(1-np.clip(ps,1e-6,1-1e-6)))
    for tr, te in KFold(5, shuffle=True, random_state=0).split(ps):
        lr = LogisticRegression(C=1e6).fit(lg[tr].reshape(-1,1), ys[tr]); oof[te] = lr.predict_proba(lg[te].reshape(-1,1))[:,1]
    out[name] = {"brier_before": round(brier_score_loss(ys,ps),3), "brier_after": round(brier_score_loss(ys,oof),3),
                 "slope_before": round(slope(ys,ps),3), "slope_after": round(slope(ys,oof),3)}
json.dump(out, open(f"{RES}/recal_per_label.json","w"), indent=2)
print("wrote recal_per_label.json"); [print(f"  {k}: {v}") for k,v in out.items()]
