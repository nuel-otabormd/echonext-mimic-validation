#!/usr/bin/env python3
"""Export plot-ready calibration data for Figure 2 (rendered by fig2_calibration.R).
Writes reliability.csv (composite reliability curve, original + OOF-Platt) and
cil.csv (per-condition calibration-in-the-large) to results_full/figs/."""
import os, csv, numpy as np
from sklearn.calibration import calibration_curve
from sklearn.model_selection import KFold
from sklearn.linear_model import LogisticRegression
RES=os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "EchoNext-repo/results_full")
OUT=os.path.join(RES,"figs"); os.makedirs(OUT,exist_ok=True)
probs=np.load(f"{RES}/probs.npy"); paths=[p for p in open(f"{RES}/kept_paths.txt").read().split("\n") if p]
coh={r['ecg_path']:r for r in csv.DictReader(open(os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "cohort_oneperpt_full.csv")))}
COLS=['lvef_lte_45','lvwt_gte_13','aortic_stenosis_modsev','aortic_regurg_modsev','mitral_regurg_modsev','tricuspid_regurg_modsev','pulm_regurg_modsev','rv_dysfunction_modsev','pericardial_modlarge','pasp_gte_45','tr_max_gte_32','shd']
NICE=['Reduced LVEF','LV hypertrophy','Aortic stenosis','Aortic regurgitation','Mitral regurgitation','Tricuspid regurgitation','Pulmonic regurgitation','RV dysfunction','Pericardial effusion','Elevated PASP','Elevated TR Vmax','Any SHD (composite)']
rows=[coh[p] for p in paths]; y=np.array([[int(r[c]) for c in COLS] for r in rows]); n=len(rows)
ys,ps=y[:,11],probs[:,11]
oof=np.zeros(n); eps=1e-6; lg=np.log(np.clip(ps,eps,1-eps)/(1-np.clip(ps,eps,1-eps)))
for tr,te in KFold(5,shuffle=True,random_state=0).split(ps):
    lr=LogisticRegression(C=1e6).fit(lg[tr].reshape(-1,1),ys[tr]); oof[te]=lr.predict_proba(lg[te].reshape(-1,1))[:,1]
x0,o0=calibration_curve(ys,ps,n_bins=12,strategy='quantile'); x1,o1=calibration_curve(ys,oof,n_bins=12,strategy='quantile')
with open(f"{OUT}/reliability.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["method","pred","obs"])
    [w.writerow(["Original (slope 0.94)",a,b]) for a,b in zip(x0,o0)]
    [w.writerow(["Recalibrated (out-of-fold Platt)",a,b]) for a,b in zip(x1,o1)]
with open(f"{OUT}/cil.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["label","cil","is_shd"])
    [w.writerow([NICE[j], y[:,j].mean()-probs[:,j].mean(), int(COLS[j]=='shd')]) for j in range(12)]
print("exported reliability.csv + cil.csv ->", OUT)
