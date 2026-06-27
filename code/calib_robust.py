import os
"""Cross-validated (OOF) recalibration + calibration robustness across label-definition variants."""
import numpy as np, csv, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
BASE=os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")); RES=BASE+"/EchoNext-repo/results_full"
probs=np.load(RES+"/probs.npy"); paths=open(RES+"/kept_paths.txt").read().split("\n")
idx={p:i for i,p in enumerate(paths)}
S=[r for r in csv.DictReader(open(BASE+"/sensitivity.csv")) if r['ecg_path'] in idx]
def colj(j): return np.array([probs[idx[r['ecg_path']],j] for r in S])
def fv(r,k):
    try: return float(r[k])
    except: return np.nan
def logit(p): p=np.clip(p,1e-4,1-1e-4); return np.log(p/(1-p))
def cal_metrics(y,p):
    y=np.asarray(y,float)
    try: sl=LogisticRegression(C=1e6).fit(logit(p).reshape(-1,1),y).coef_[0,0]
    except Exception: sl=np.nan
    return dict(prev=round(100*y.mean(),1),auroc=round(roc_auc_score(y,p),3),
                brier=round(brier_score_loss(y,p),4),slope=round(sl,3),cil=round(y.mean()-p.mean(),3))
def oof(y,p,kind):
    y=np.asarray(y,float); o=np.zeros(len(y))
    for tr,te in KFold(5,shuffle=True,random_state=0).split(p):
        if kind=='platt': o[te]=LogisticRegression(C=1e6).fit(logit(p[tr]).reshape(-1,1),y[tr]).predict_proba(logit(p[te]).reshape(-1,1))[:,1]
        else: o[te]=IsotonicRegression(out_of_bounds='clip').fit(p[tr],y[tr]).predict(p[te])
    return o
print(f"n={len(S)}")

# ---- SHD cross-validated recalibration (Platt + isotonic), OOF ----
pshd=colj(11); yshd=np.array([int(r['shd']) for r in S])
o_platt=oof(yshd,pshd,'platt'); o_iso=oof(yshd,pshd,'iso')
print("\n== SHD recalibration (5-fold OUT-OF-FOLD, not apparent) ==")
for nm,p in [('original',pshd),('OOF Platt',o_platt),('OOF isotonic',o_iso)]:
    m=cal_metrics(yshd,p); print(f"   {nm:14s} Brier {m['brier']}  slope {m['slope']}  calib-in-large {m['cil']}")
# figure: OOF reliability
plt.figure(figsize=(5,5))
for nm,p,mk in [('original',pshd,'o-'),('recalibrated (OOF isotonic)',o_iso,'s-')]:
    x,yv=calibration_curve(yshd,p,n_bins=15,strategy='quantile'); plt.plot(x,yv,mk,label=nm)
plt.plot([0,1],[0,1],'k--',lw=1); plt.xlabel('Predicted probability'); plt.ylabel('Observed frequency')
plt.title(f'SHD calibration — out-of-fold isotonic (n={len(S)})'); plt.legend(); plt.tight_layout()
plt.savefig(RES+"/figs/calibration_shd_oof.png",dpi=130); plt.close()
print("   saved figs/calibration_shd_oof.png")

# ---- calibration ROBUSTNESS across label-definition variants (AUROC + Brier + slope + CIL) ----
print("\n== Calibration & discrimination across label-definition variants ==")
def lvef_mid(r):
    b,t=fv(r,'lvef_biplane'),fv(r,'lvef_3d')
    for v in (b,t):
        if not np.isnan(v): return v
    lo,hi=fv(r,'lvef_low'),fv(r,'lvef_high')
    return (lo+hi)/2 if not (np.isnan(lo) or np.isnan(hi)) else (lo if not np.isnan(lo) else hi)
variants={
 ('LVEF',0):{'primary(quant/mid)':[int(lvef_mid(r)<=45) if not np.isnan(lvef_mid(r)) else 0 for r in S],
             'lower_bound':[int(fv(r,'lvef_low')<=45) if not np.isnan(fv(r,'lvef_low')) else 0 for r in S]},
 ('RV',7):{'cat_only':[int(r['rv_dysfunction_cat_only']) for r in S],
           '+TAPSE(primary)':[int(r['rv_dysfunction_modsev']) for r in S]},
 ('PASP',9):{'ASE_IVC(primary)':[int((fv(r,'tr_grad')+(fv(r,'rap_ivc') if not np.isnan(fv(r,'rap_ivc')) else 3))>=45) if not np.isnan(fv(r,'tr_grad')) else 0 for r in S],
             'fixed_RAP5':[int((fv(r,'tr_grad')+5)>=45) if not np.isnan(fv(r,'tr_grad')) else 0 for r in S]},
}
print(f"{'label/variant':28s}{'prev%':>7}{'AUROC':>7}{'Brier':>8}{'slope':>7}{'CIL':>7}")
for (lab,j),vs in variants.items():
    p=colj(j)
    for vn,y in vs.items():
        m=cal_metrics(y,p); print(f"{lab+': '+vn:28s}{m['prev']:>7}{m['auroc']:>7}{m['brier']:>8}{m['slope']:>7}{m['cil']:>7}")
print("\nDONE.")
