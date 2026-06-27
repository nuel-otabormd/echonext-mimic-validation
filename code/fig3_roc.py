#!/usr/bin/env python3
"""Export ROC-curve data for Figure 3 (rendered by fig3_roc.R).
Writes roc.csv (interpolated to 500 points/label) to results_full/figs/."""
import os, csv, numpy as np
from sklearn.metrics import roc_curve, roc_auc_score
RES=os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "EchoNext-repo/results_full"); OUT=os.path.join(RES,"figs"); os.makedirs(OUT,exist_ok=True)
probs=np.load(f"{RES}/probs.npy"); paths=[p for p in open(f"{RES}/kept_paths.txt").read().split("\n") if p]
coh={r['ecg_path']:r for r in csv.DictReader(open(os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "cohort_oneperpt_full.csv")))}
COLS=['lvef_lte_45','lvwt_gte_13','aortic_stenosis_modsev','aortic_regurg_modsev','mitral_regurg_modsev','tricuspid_regurg_modsev','pulm_regurg_modsev','rv_dysfunction_modsev','pericardial_modlarge','pasp_gte_45','tr_max_gte_32','shd']
rows=[coh[p] for p in paths]; y=np.array([[int(r[c]) for c in COLS] for r in rows])
grid=np.linspace(0,1,500)
with open(f"{OUT}/roc.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["label","fpr","tpr"])
    for j,name in [(11,'Any SHD'),(0,'Reduced LVEF'),(7,'RV dysfunction')]:
        fpr,tpr,_=roc_curve(y[:,j],probs[:,j]); auc=roc_auc_score(y[:,j],probs[:,j])
        tg=np.interp(grid,fpr,tpr); lab=f"{name} (AUROC {auc:.2f})"
        [w.writerow([lab,a,b]) for a,b in zip(grid,tg)]
print("exported roc.csv ->", OUT)
