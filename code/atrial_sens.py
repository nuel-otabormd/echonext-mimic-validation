"""Sensitivity: atrial_rate imputed 0 (primary) vs ventricular_rate proxy. Subset re-inference."""
import os,sys,json,numpy as np,torch,joblib,wfdb,scipy.signal,csv
from sklearn.metrics import roc_auc_score
sys.path.insert(0,"7-EchoNext Minimodel")
from cradlenet.models.resnet1d_tabular import ResNet1dWithTabular
MDIR="7-EchoNext Minimodel/models/echonext_multilabel_minimodel"; NEED=os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "ecg_needed")
LEADS=['I','II','III','aVR','aVL','aVF','V1','V2','V3','V4','V5','V6']
def bwr(d,fs=250):
    o=np.zeros(d.shape)
    for L in range(d.shape[0]):
        b=scipy.signal.medfilt(d[L],int(round(0.2*fs))+1); b=scipy.signal.medfilt(b,int(round(0.6*fs))+1); o[L]=d[L]-b
    return o
def load(p):
    r=wfdb.rdrecord(os.path.join(NEED,p),physical=False); s=r.d_signal.astype(np.float64)
    i={n:k for k,n in enumerate(r.sig_name)}; return bwr(s[:,[i[l] for l in LEADS]][::2,:].T,250).T
coh={r['ecg_path']:r for r in csv.DictReader(open(os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "cohort_oneperpt_full.csv")))}
paths=[p for p in open("results_full/kept_paths.txt").read().split("\n") if p in coh][:8000]
print(f"subset n={len(paths)}",flush=True)
prm=json.load(open(MDIR+"/waveform_normalization_params.json"))
wf=[]
for k,p in enumerate(paths):
    wf.append(load(p))
    if (k+1)%2000==0: print(f"  loaded {k+1}",flush=True)
wf=np.stack(wf); d=np.transpose(wf,(0,2,1)).copy()
for L in range(12): d[:,L,:]=(np.clip(d[:,L,:],prm['lowerbound'][L],prm['upperbound'][L])-prm['mean'][L])/prm['std'][L]
X=torch.tensor(np.transpose(d,(0,2,1))[:,None,:,:],dtype=torch.float32)
pipe=joblib.load(MDIR+"/tabular_transformer.joblib"); sc,im=pipe.named_steps['scale'],pipe.named_steps['impute']
def f(x):
    try:return float(x)
    except:return np.nan
mdl=ResNet1dWithTabular(len_tabular_feature_vector=7,filter_size=16,num_classes=12)
mdl.load_state_dict(torch.load(MDIR+"/weights.pt",map_location="cpu")["model"]); mdl.eval()
y=np.array([int(coh[p]['shd']) for p in paths])
def run(mode):
    Xn=[]
    for p in paths:
        r=coh[p]; vr=f(r['ventricular_rate'])
        atr = 0.0 if mode=='zero' else (vr if mode=='proxy' else 75.0)  # 0 (primary) / ventricular proxy / normal 75 bpm
        Xn.append([f(r['age_at_ecg']),vr,atr,f(r['pr_interval']),f(r['qrs_duration']),f(r['qt_corrected'])])
    Xn=np.array(Xn); Xs=(Xn-sc.mean_)/sc.scale_; nan=np.isnan(Xs); Xs[nan]=np.take(im.statistics_,np.where(nan)[1])
    sex=np.array([[1.0 if coh[p]['gender'].strip().upper()=='M' else 0.0] for p in paths])
    T=torch.tensor(np.concatenate([sex,Xs],1),dtype=torch.float32)
    with torch.no_grad(): return torch.sigmoid(mdl((X,T))).numpy()[:,11]
p0=run('zero'); p1=run('proxy'); p2=run('normal')
print(f"\nSHD AUROC  atrial_rate=0 (primary)     : {roc_auc_score(y,p0):.4f}")
print(f"SHD AUROC  atrial_rate=ventricular proxy: {roc_auc_score(y,p1):.4f}")
print(f"SHD AUROC  atrial_rate=normal(75 bpm)   : {roc_auc_score(y,p2):.4f}")
print(f"max|p0-p1| {np.abs(p0-p1).max():.4f}  max|p0-p2| {np.abs(p0-p2).max():.4f}")
