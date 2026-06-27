import os
"""Paper 1 sensitivity analyses + spline calibration (on existing full-cohort probs)."""
import numpy as np, csv, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
BASE=os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")); RES=BASE+"/EchoNext-repo/results_full"
probs=np.load(RES+"/probs.npy"); paths=open(RES+"/kept_paths.txt").read().split("\n")
idx={p:i for i,p in enumerate(paths)}
S=[r for r in csv.DictReader(open(BASE+"/sensitivity.csv")) if r['ecg_path'] in idx]
def col(j,key=None): return np.array([probs[idx[r['ecg_path']],j] for r in S])
def fv(r,k):
    try: return float(r[k])
    except: return np.nan
def auc(y,p):
    y=np.asarray(y);
    return roc_auc_score(y,p) if 5<y.sum()<len(y)-5 else float('nan')
print(f"n={len(S)}\n")

# ---------- 1. ECG-echo window sensitivity (SHD) ----------
print("== 1. SHD AUROC by ECG->TTE interval ==")
gap=np.array([fv(r,'ecg_to_echo_days') for r in S]); pshd=col(11); yshd=np.array([int(r['shd']) for r in S])
for w in [30,90,180,365]:
    m=gap<=w
    print(f"   <= {w:3d}d : n={m.sum():6d}  prev {100*yshd[m].mean():4.1f}%  AUROC {auc(yshd[m],pshd[m]):.3f}")

# ---------- 2. LVEF definition sensitivity ----------
print("\n== 2. LVEF<=45 label/AUROC under definitions (model out[0]) ==")
p0=col(0)
def lvef_mid(r):
    lo,hi=fv(r,'lvef_low'),fv(r,'lvef_high'); b,t=fv(r,'lvef_biplane'),fv(r,'lvef_3d')
    for v in (b,t):
        if not np.isnan(v): return v
    if not np.isnan(lo) and not np.isnan(hi): return (lo+hi)/2
    return lo if not np.isnan(lo) else hi
defs={
 'quant>then>midpoint(primary)':[int((lvef_mid(r)<=45)) if not np.isnan(lvef_mid(r)) else 0 for r in S],
 'midpoint_only':[int(((fv(r,'lvef_low')+fv(r,'lvef_high'))/2)<=45) if not np.isnan(fv(r,'lvef_low')) and not np.isnan(fv(r,'lvef_high')) else 0 for r in S],
 'lower_bound':[int(fv(r,'lvef_low')<=45) if not np.isnan(fv(r,'lvef_low')) else 0 for r in S],
}
for k,y in defs.items(): print(f"   {k:30s} prev {100*np.mean(y):4.1f}%  AUROC {auc(y,p0):.3f}")

# ---------- 3. RV dysfunction: categorical-only vs +TAPSE ----------
print("\n== 3. RV dysfunction definition (model out[7]) ==")
p7=col(7)
for k,key in [('categorical only','rv_dysfunction_cat_only'),('categorical OR TAPSE<1.7 (primary)','rv_dysfunction_modsev')]:
    y=[int(r[key]) for r in S]; print(f"   {k:34s} prev {100*np.mean(y):4.1f}%  AUROC {auc(y,p7):.3f}")

# ---------- 4. PASP>=45 RAP assumption sensitivity ----------
print("\n== 4. PASP>=45 under RAP assumptions (model out[9]) ==")
p9=col(9)
for k,rapf in [('ASE IVC-derived (primary)','ase'),('fixed RAP=3','3'),('fixed RAP=5','5'),('fixed RAP=10','10')]:
    y=[]
    for r in S:
        tg=fv(r,'tr_grad')
        if np.isnan(tg): y.append(0); continue
        rap = (fv(r,'rap_ivc') if not np.isnan(fv(r,'rap_ivc')) else 3) if rapf=='ase' else float(rapf)
        y.append(int((tg+rap)>=45))
    print(f"   {k:26s} prev {100*np.mean(y):4.1f}%  AUROC {auc(y,p9):.3f}")

# ---------- 5. SPLINE/binned calibration for SHD (clean, no logit-LR) ----------
print("\n== 5. spline calibration SHD ==")
def logit(p): p=np.clip(p,1e-6,1-1e-6); return np.log(p/(1-p))
iso=IsotonicRegression(out_of_bounds='clip').fit(pshd,yshd); preg=iso.predict(pshd)  # nonparametric recalibration
xb,yb=calibration_curve(yshd,pshd,n_bins=15,strategy='quantile')
xr,yr=calibration_curve(yshd,preg,n_bins=15,strategy='quantile')
plt.figure(figsize=(5,5))
plt.plot(xb,yb,'o-',label='original'); plt.plot(xr,yr,'s-',label='isotonic-recalibrated')
plt.plot([0,1],[0,1],'k--',lw=1); plt.xlabel('Predicted probability'); plt.ylabel('Observed frequency')
plt.title(f'SHD calibration (quantile bins, n={len(S)})'); plt.legend(); plt.tight_layout()
plt.savefig(RES+"/figs/calibration_shd_spline.png",dpi=130); plt.close()
print(f"   Brier original {brier_score_loss(yshd,pshd):.4f} -> isotonic {brier_score_loss(yshd,preg):.4f}")
print("   saved figs/calibration_shd_spline.png")
print("\nDONE sensitivity analyses.")
