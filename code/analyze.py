"""Paper 1 analysis: discrimination (boot CI), calibration + recalibration, decision curve, fairness.
Reads results_full/probs.npy + kept_paths.txt + cohort CSV + subject_race.csv. Writes figs + markdown."""
import os, csv, json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, roc_curve
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

BASE=os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH"))
RES=os.path.join(BASE,"EchoNext-repo/results_full"); FIG=os.path.join(RES,"figs"); os.makedirs(FIG,exist_ok=True)
LABELS=['lvef_lte_45','lvwt_gte_13','aortic_stenosis','aortic_regurg','mitral_regurg','tricuspid_regurg',
        'pulm_regurg','rv_dysfunction','pericardial','pasp_gte_45','tr_max_gte_32','shd']
COLS=['lvef_lte_45','lvwt_gte_13','aortic_stenosis_modsev','aortic_regurg_modsev','mitral_regurg_modsev',
      'tricuspid_regurg_modsev','pulm_regurg_modsev','rv_dysfunction_modsev','pericardial_modlarge',
      'pasp_gte_45','tr_max_gte_32','shd']
ECHONEXT_AUROC={'lvef_lte_45':None,'shd':0.820}  # internal Mini reference (composite)

probs=np.load(os.path.join(RES,"probs.npy"))
paths=open(os.path.join(RES,"kept_paths.txt")).read().split("\n")
coh={r['ecg_path']:r for r in csv.DictReader(open(os.path.join(BASE,"cohort_oneperpt_full.csv")))}
race={r['subject_id']:r['race'] for r in csv.DictReader(open(os.path.join(BASE,"subject_race.csv")))}
def subj(p): return p.split("/")[2][1:]   # files/pXXXX/p<subject>/...
_m=[i for i,p in enumerate(paths) if p in coh]
if len(_m)<len(paths): print(f"NOTE: aligned on intersection, dropped {len(paths)-len(_m)} of {len(paths)} (tie-break drift)")
probs=probs[_m]; paths=[paths[i] for i in _m]
rows=[coh[p] for p in paths]
y=np.array([[int(r[c]) for c in COLS] for r in rows])
sex=np.array([r['gender'].strip().upper() for r in rows])
age=np.array([float(r['age_at_ecg']) for r in rows])
rc=np.array([race.get(subj(p),"Unknown") for p in paths])
n=len(rows); print(f"n={n}")

def logit(p): p=np.clip(p,1e-6,1-1e-6); return np.log(p/(1-p))
def calib(y,p):
    s=LogisticRegression().fit(logit(p).reshape(-1,1),y).coef_[0,0]
    return s, y.mean()-p.mean()    # slope, calibration-in-large (obs-pred)
def boot_auc(y,p,B=2000):
    rng=np.random.default_rng(0); a=[]
    for _ in range(B):
        i=rng.integers(0,len(y),len(y))
        if y[i].sum() in (0,len(y)): continue
        a.append(roc_auc_score(y[i],p[i]))
    return np.percentile(a,[2.5,97.5])

# ---- 1. discrimination + calibration table ----
table=[]
for j,name in enumerate(LABELS):
    yt,pp=y[:,j],probs[:,j]
    if yt.sum()<10: table.append(dict(label=name,prev=float(yt.mean()),auroc=None)); continue
    auc=roc_auc_score(yt,pp); lo,hi=boot_auc(yt,pp)
    sl,cil=calib(yt,pp)
    table.append(dict(label=name,prev=round(100*yt.mean(),1),auroc=round(auc,3),ci=[round(lo,3),round(hi,3)],
                      auprc=round(average_precision_score(yt,pp),3),brier=round(brier_score_loss(yt,pp),3),
                      calib_slope=round(sl,3),calib_in_large=round(cil,3)))

# ---- 2. SHD recalibration (5-fold out-of-fold Platt) ----
js=LABELS.index('shd'); ys,ps=y[:,js],probs[:,js]
oof=np.zeros(n); kf=KFold(5,shuffle=True,random_state=0)
for tr,te in kf.split(ps):
    lr=LogisticRegression().fit(logit(ps[tr]).reshape(-1,1),ys[tr])
    oof[te]=lr.predict_proba(logit(ps[te]).reshape(-1,1))[:,1]
brier_before,brier_after=brier_score_loss(ys,ps),brier_score_loss(ys,oof)
slope_after=calib(ys,oof)[0]
recal={'brier_before':round(brier_before,4),'brier_after':round(brier_after,4),
       'slope_before':round(calib(ys,ps)[0],3),'slope_after':round(slope_after,3)}

def reliability(y,p,bins=10):
    edges=np.linspace(0,1,bins+1); xs=[];ys_=[]
    for k in range(bins):
        m=(p>=edges[k])&(p<edges[k+1])
        if m.sum()>20: xs.append(p[m].mean()); ys_.append(y[m].mean())
    return np.array(xs),np.array(ys_)

# fig: calibration SHD before/after
plt.figure(figsize=(5,5))
for p_,lab in [(ps,f"original (slope {recal['slope_before']})"),(oof,f"recalibrated (slope {recal['slope_after']})")]:
    x,yy=reliability(ys,p_); plt.plot(x,yy,'o-',label=lab)
plt.plot([0,1],[0,1],'k--',lw=1); plt.xlabel("Predicted prob"); plt.ylabel("Observed freq")
plt.title(f"SHD calibration (n={n})"); plt.legend(); plt.tight_layout(); plt.savefig(f"{FIG}/calibration_shd.png",dpi=130); plt.close()

# fig: ROC SHD
plt.figure(figsize=(5,5)); fpr,tpr,_=roc_curve(ys,ps)
plt.plot(fpr,tpr,label=f"SHD AUROC {roc_auc_score(ys,ps):.3f}"); plt.plot([0,1],[0,1],'k--',lw=1)
plt.xlabel("1-Specificity"); plt.ylabel("Sensitivity"); plt.title("SHD ROC (MIMIC external)"); plt.legend()
plt.tight_layout(); plt.savefig(f"{FIG}/roc_shd.png",dpi=130); plt.close()

# ---- 3. decision curve (net benefit), SHD ----
ths=np.linspace(0.01,0.6,60); nb_model=[]; nb_all=[]
prev=ys.mean()
for t in ths:
    pred=ps>=t; tp=np.sum(pred&(ys==1)); fp=np.sum(pred&(ys==0))
    nb_model.append(tp/n - fp/n*(t/(1-t)))
    nb_all.append(prev - (1-prev)*(t/(1-t)))
plt.figure(figsize=(5.5,4.5))
plt.plot(ths,nb_model,label="EchoNext-Mini"); plt.plot(ths,nb_all,'--',label="Echo all"); plt.axhline(0,color='k',lw=1,label="Echo none")
plt.ylim(-0.05,prev+0.02); plt.xlabel("Threshold prob"); plt.ylabel("Net benefit"); plt.title("Decision curve — SHD")
plt.legend(); plt.tight_layout(); plt.savefig(f"{FIG}/dca_shd.png",dpi=130); plt.close()

# ---- 4. fairness: SHD AUROC + calib slope by subgroup ----
def grp_metrics(mask):
    yy,pp=ys[mask],ps[mask]
    if yy.sum()<20 or len(yy)<100: return None
    return dict(n=int(mask.sum()),prev=round(100*yy.mean(),1),auroc=round(roc_auc_score(yy,pp),3),slope=round(calib(yy,pp)[0],3))
ageg=np.where(age<65,"<65",np.where(age<80,"65-79","80+"))
fair={'sex':{g:grp_metrics(sex==g) for g in ['M','F']},
      'age':{g:grp_metrics(ageg==g) for g in ['<65','65-79','80+']},
      'race':{g:grp_metrics(rc==g) for g in ['White','Black','Hispanic','Asian','Other','Unknown']}}
# fig: subgroup AUROC
plt.figure(figsize=(7,4)); items=[]
for dim in ['sex','age','race']:
    for g,m in fair[dim].items():
        if m: items.append((f"{dim}:{g}",m['auroc'],m['n']))
items.sort(key=lambda x:x[1])
plt.barh([i[0] for i in items],[i[1] for i in items])
plt.axvline(roc_auc_score(ys,ps),color='r',ls='--',label='overall'); plt.xlim(0.6,0.9)
plt.xlabel("SHD AUROC"); plt.title("Fairness: SHD AUROC by subgroup"); plt.legend(); plt.tight_layout()
plt.savefig(f"{FIG}/subgroup_auroc.png",dpi=130); plt.close()

# ---- write results ----
json.dump({'table':table,'recal':recal,'fairness':fair},open(f"{RES}/paper1_metrics.json","w"),indent=2)
with open(f"{RES}/PAPER1_RESULTS.md","w") as f:
    f.write(f"# Paper 1 — EchoNext-Mini external validation in MIMIC-IV (n={n}, one-per-patient, full cohort)\n\n")
    f.write("## Discrimination & calibration\n\n| Label | Prev% | AUROC (95% CI) | AUPRC | Brier | Calib slope | Calib-in-large |\n|---|---|---|---|---|---|---|\n")
    for t in table:
        if t.get('auroc') is None: f.write(f"| {t['label']} | {round(100*t['prev'],1) if t['prev']<1 else t['prev']} | - | | | | |\n"); continue
        f.write(f"| {t['label']} | {t['prev']} | {t['auroc']} ({t['ci'][0]}-{t['ci'][1]}) | {t['auprc']} | {t['brier']} | {t['calib_slope']} | {t['calib_in_large']} |\n")
    f.write(f"\n## SHD recalibration (5-fold OOF Platt)\nBrier {recal['brier_before']} -> {recal['brier_after']}; slope {recal['slope_before']} -> {recal['slope_after']}\n")
    f.write("\n## Fairness (SHD)\n\n| Subgroup | n | Prev% | AUROC | Calib slope |\n|---|---|---|---|---|\n")
    for dim in ['sex','age','race']:
        for g,m in fair[dim].items():
            if m: f.write(f"| {dim}:{g} | {m['n']} | {m['prev']} | {m['auroc']} | {m['slope']} |\n")
    f.write(f"\nFigures in `figs/`: calibration_shd.png, roc_shd.png, dca_shd.png, subgroup_auroc.png\n")
print("DONE. SHD recal:",recal)
print("results ->",RES)
