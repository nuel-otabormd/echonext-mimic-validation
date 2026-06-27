"""Publication-quality figures (vector PDF + PNG) for Paper 1."""
import os, csv, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from sklearn.metrics import roc_auc_score, roc_curve, brier_score_loss
from sklearn.calibration import calibration_curve
from sklearn.model_selection import KFold
from sklearn.linear_model import LogisticRegression

plt.rcParams.update({
 'font.family':'sans-serif','font.sans-serif':['Helvetica','Arial','DejaVu Sans'],
 'font.size':10,'axes.titlesize':11,'axes.labelsize':10,'legend.fontsize':9,
 'xtick.labelsize':9,'ytick.labelsize':9,'axes.spines.top':False,'axes.spines.right':False,
 'axes.linewidth':0.8,'savefig.dpi':300,'savefig.bbox':'tight','pdf.fonttype':42,'figure.dpi':130})
NAVY='#1f3b5c'; TEAL='#2a9d8f'; RUST='#bb4430'; GREY='#6c757d'
OUT=os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "EchoNext-repo/results_full/figs")
REPO=os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "echonext-mimic-validation/results/figures")
os.makedirs(REPO,exist_ok=True)
def save(fig,name):
    for d in (OUT,REPO):
        fig.savefig(f"{d}/{name}.pdf"); fig.savefig(f"{d}/{name}.png")
    plt.close(fig); print("saved",name)

# ---- load predictions + labels ----
RES=os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "EchoNext-repo/results_full")
probs=np.load(f"{RES}/probs.npy"); paths=[p for p in open(f"{RES}/kept_paths.txt").read().split("\n") if p]
coh={r['ecg_path']:r for r in csv.DictReader(open(os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "cohort_oneperpt_full.csv")))}
race={r['subject_id']:r['race'] for r in csv.DictReader(open(os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "subject_race.csv")))}
COLS=['lvef_lte_45','lvwt_gte_13','aortic_stenosis_modsev','aortic_regurg_modsev','mitral_regurg_modsev','tricuspid_regurg_modsev','pulm_regurg_modsev','rv_dysfunction_modsev','pericardial_modlarge','pasp_gte_45','tr_max_gte_32','shd']
NICE=['Reduced LVEF (≤45%)','LV hypertrophy (≥1.3 cm)','Aortic stenosis','Aortic regurgitation','Mitral regurgitation','Tricuspid regurgitation','Pulmonic regurgitation','RV dysfunction','Pericardial effusion','PASP ≥45 mmHg','TR Vmax ≥3.2 m/s','Any SHD (composite)']
rows=[coh[p] for p in paths]; y=np.array([[int(r[c]) for c in COLS] for r in rows])
def subj(p): return p.split("/")[2][1:]
sex=np.array([r['gender'].strip().upper() for r in rows]); age=np.array([float(r['age_at_ecg']) for r in rows])
rc=np.array([race.get(subj(p),"Unknown") for p in paths]); n=len(rows)
ys=y[:,11]; ps=probs[:,11]   # composite SHD outcome/probs (used by the optional fairness panel)
def bootci(yt,pp,B=2000):
    rng=np.random.default_rng(0); a=[]
    for _ in range(B):
        i=rng.integers(0,len(yt),len(yt))
        if 0<yt[i].sum()<len(yt): a.append(roc_auc_score(yt[i],pp[i]))
    return np.percentile(a,[2.5,97.5])

# ===== FIGURE 1: Cohort flow diagram =====
# Generated separately by code/fig1_cohort.R (Graphviz/DiagrammeR, CONSORT-style).
# Do NOT regenerate it here — that would overwrite the cleaner R version.

# ===== FIGURE 2: Forest plot of component AUROCs =====
order=list(np.argsort([roc_auc_score(y[:,j],probs[:,j]) for j in range(12)]))
fig,ax=plt.subplots(figsize=(7,5.4))
yt_pos=np.arange(12)
for k,j in enumerate(order):
    auc=roc_auc_score(y[:,j],probs[:,j]); lo,hi=bootci(y[:,j],probs[:,j])
    col=NAVY if COLS[j]=='shd' else TEAL
    ax.plot([lo,hi],[k,k],color=col,lw=2); ax.plot(auc,k,'o',color=col,ms=6 if COLS[j]=='shd' else 5)
    ax.text(hi+0.004,k,f"{auc:.2f} ({lo:.2f}–{hi:.2f})",va='center',fontsize=8,color='#333')
ax.axvline(0.820,color=RUST,ls='--',lw=1.2,label='EchoNext internal composite (0.82)')
ax.axvline(0.5,color=GREY,ls=':',lw=1)
ax.set_yticks(yt_pos); ax.set_yticklabels([NICE[j] for j in order]); ax.set_xlim(0.5,0.92)
ax.set_xlabel("AUROC (95% CI) in MIMIC-IV external validation"); ax.legend(loc='upper left',frameon=False)
ax.margins(x=0.16)
save(fig,"fig2_forest_auroc")

# ===== FIGURE 2 (manuscript) — Calibration (panels A/B) =====
# Generated separately by code/fig2_calibration.py (data export) + code/fig2_calibration.R (ggplot2).
# Do NOT regenerate it here — that would overwrite the cleaner R version.

# ===== FIGURE 3 (manuscript): ROC curves =====
# Generated separately by code/fig3_roc.py (data export) + code/fig3_roc.R (ggplot2).
# Decision-curve analysis was removed (clinically selected cohort; utility addressed narratively).
# Do NOT regenerate it here — that would overwrite the cleaner R version.

# ===== FIGURE 4: Subgroup discrimination (fairness) =====
groups=[('Male',sex=='M'),('Female',sex=='F'),('Age <65',age<65),('Age 65–79',(age>=65)&(age<80)),('Age ≥80',age>=80),
        ('White',rc=='White'),('Black',rc=='Black'),('Hispanic',rc=='Hispanic'),('Asian',rc=='Asian'),('Other',rc=='Other'),('Unknown',rc=='Unknown')]
fig,ax=plt.subplots(figsize=(6.8,5.2))
for k,(g,m) in enumerate(groups[::-1]):
    yy,pp=ys[m],ps[m]; auc=roc_auc_score(yy,pp); lo,hi=bootci(yy,pp)
    ax.plot([lo,hi],[k,k],color=NAVY,lw=2); ax.plot(auc,k,'o',color=NAVY,ms=5)
    ax.text(hi+0.004,k,f"{auc:.2f}",va='center',fontsize=8)
ax.axvline(roc_auc_score(ys,ps),color=RUST,ls='--',lw=1.2,label='Overall (0.79)')
ax.set_yticks(range(11)); ax.set_yticklabels([g for g,_ in groups[::-1]]); ax.set_xlim(0.66,0.92)
ax.set_xlabel('Any-SHD AUROC (95% CI) by subgroup'); ax.legend(loc='upper left',frameon=False)
save(fig,"fig4_fairness")
print("ALL FIGURES DONE")
