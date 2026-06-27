"""Batch external-validation inference: EchoNext-Mini on MIMIC-IV one-per-patient cohort.
Chunked (memory-safe). Archive-first, Desktop-fallback waveform loading.
Usage: python run_inference.py --cohort cohort_oneperpt_full.csv --source archive --out_dir results
"""
import os, sys, json, csv, argparse, time
import numpy as np, torch, joblib, wfdb, scipy.signal

REPO = os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "EchoNext-repo/7-EchoNext Minimodel")
MDIR = os.path.join(REPO, "models/echonext_multilabel_minimodel")
ARCH = os.path.expanduser("~/iCloud Drive (Archive)/Desktop/Claude Cowork/MIMIC-IV ECG/mimic-iv-ecg")
DESK = os.path.expanduser("~/Desktop/Claude Cowork/MIMIC-IV ECG/mimic-iv-ecg")
NEED = os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "ecg_needed")
sys.path.insert(0, REPO)
from cradlenet.models.resnet1d_tabular import ResNet1dWithTabular

MODEL_LEADS = ['I','II','III','aVR','aVL','aVF','V1','V2','V3','V4','V5','V6']
LABELS = ['lvef_lte_45','lvwt_gte_13','aortic_stenosis','aortic_regurg','mitral_regurg',
          'tricuspid_regurg','pulm_regurg','rv_dysfunction','pericardial','pasp_gte_45','tr_max_gte_32','shd']
LABEL_COLS = ['lvef_lte_45','lvwt_gte_13','aortic_stenosis_modsev','aortic_regurg_modsev','mitral_regurg_modsev',
              'tricuspid_regurg_modsev','pulm_regurg_modsev','rv_dysfunction_modsev','pericardial_modlarge',
              'pasp_gte_45','tr_max_gte_32','shd']

def baseline_wander_removal(data, fs=250):
    out=np.zeros(data.shape)
    for L in range(data.shape[0]):
        b=scipy.signal.medfilt(data[L,:], int(np.round(0.2*fs))+1)
        b=scipy.signal.medfilt(b, int(np.round(0.6*fs))+1)
        out[L,:]=data[L,:]-b
    return out

def find_base(path, source):
    bases = {"archive":[ARCH], "desktop":[DESK], "both":[ARCH,DESK], "needed":[NEED,ARCH,DESK]}[source]
    for b in bases:
        if os.path.exists(os.path.join(b,path+".hea")) and os.path.exists(os.path.join(b,path+".dat")):
            return b
    return None

def load_waveform(path, base):
    rec=wfdb.rdrecord(os.path.join(base,path), physical=False)
    sig=rec.d_signal.astype(np.float64)
    idx={n:i for i,n in enumerate(rec.sig_name)}
    sig=sig[:,[idx[l] for l in MODEL_LEADS]][::2,:]
    return baseline_wander_removal(sig.T,250).T          # (2500,12)

def norm(wf, p):                                          # (n,2500,12)->(n,1,2500,12)
    d=np.transpose(wf,(0,2,1)).copy()
    for L in range(12):
        d[:,L,:]=np.clip(d[:,L,:],p['lowerbound'][L],p['upperbound'][L])
        d[:,L,:]=(d[:,L,:]-p['mean'][L])/p['std'][L]
    return np.transpose(d,(0,2,1))[:,None,:,:]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cohort",required=True); ap.add_argument("--source",default="archive")
    ap.add_argument("--out_dir",default="results"); ap.add_argument("--chunk",type=int,default=512)
    ap.add_argument("--limit",type=int,default=0)
    a=ap.parse_args(); os.makedirs(a.out_dir,exist_ok=True)

    rows=list(csv.DictReader(open(a.cohort)))
    if a.limit: rows=rows[:a.limit]
    # resolve which rows are loadable
    for r in rows: r["_base"]=find_base(r["ecg_path"], a.source)
    use=[r for r in rows if r["_base"]]
    print(f"cohort={len(rows)} loadable({a.source})={len(use)} skipped={len(rows)-len(use)}",flush=True)

    params=json.load(open(os.path.join(MDIR,"waveform_normalization_params.json")))
    pipe=joblib.load(os.path.join(MDIR,"tabular_transformer.joblib"))
    sc,im=pipe.named_steps['scale'],pipe.named_steps['impute']
    model=ResNet1dWithTabular(len_tabular_feature_vector=7,filter_size=16,num_classes=12)
    ck=torch.load(os.path.join(MDIR,"weights.pt"),map_location='cpu')
    sd=ck['model'] if 'model' in ck else ck.get('state_dict',ck)
    sd={(k[6:] if k.startswith('model.') else k):v for k,v in sd.items()}
    model.load_state_dict(sd,strict=False); model.eval()
    def ff(x):
        try:return float(x)
        except:return np.nan

    all_probs=[]; kept=[]; t0=time.time()
    for s in range(0,len(use),a.chunk):
        ch=use[s:s+a.chunk]; wf=[]; ok=[]
        for r in ch:
            try: wf.append(load_waveform(r["ecg_path"],r["_base"])); ok.append(r)
            except Exception as e:
                pass
        if not wf: continue
        X=torch.tensor(norm(np.stack(wf),params),dtype=torch.float32)
        Xn=np.array([[ff(r['age_at_ecg']),ff(r['ventricular_rate']),0.0,ff(r['pr_interval']),ff(r['qrs_duration']),ff(r['qt_corrected'])] for r in ok])
        Xs=(Xn-sc.mean_)/sc.scale_; nan=np.isnan(Xs); Xs[nan]=np.take(im.statistics_,np.where(nan)[1])
        sex=np.array([[1.0 if r['gender'].strip().upper()=='M' else 0.0] for r in ok])
        T=torch.tensor(np.concatenate([sex,Xs],1),dtype=torch.float32)
        with torch.no_grad(): p=torch.sigmoid(model((X,T))).numpy()
        all_probs.append(p); kept+=ok
        print(f"  {len(kept)}/{len(use)} done ({time.time()-t0:.0f}s)",flush=True)

    probs=np.concatenate(all_probs); y=np.array([[int(r[c]) for c in LABEL_COLS] for r in kept])
    np.save(os.path.join(a.out_dir,"probs.npy"),probs)
    with open(os.path.join(a.out_dir,"kept_paths.txt"),"w") as f: f.write("\n".join(r["ecg_path"] for r in kept))

    # metrics
    from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
    print(f"\n== EXTERNAL VALIDATION (n={len(kept)}) ==")
    print(f"{'label':<22}{'prev%':>7}{'AUROC':>8}{'AUPRC':>8}{'Brier':>8}{'calib_slope':>12}")
    res={}
    for j,name in enumerate(LABELS):
        yt,pp=y[:,j],probs[:,j]
        if yt.sum()<5 or yt.sum()>len(yt)-5:
            print(f"{name:<22}{100*yt.mean():>7.1f}{'n/a':>8}");continue
        auc=roc_auc_score(yt,pp); ap_=average_precision_score(yt,pp); br=brier_score_loss(yt,pp)
        lg=np.log(np.clip(pp,1e-6,1-1e-6)/(1-np.clip(pp,1e-6,1-1e-6)))
        from sklearn.linear_model import LogisticRegression
        slope=LogisticRegression().fit(lg.reshape(-1,1),yt).coef_[0,0]
        res[name]=dict(prev=float(yt.mean()),auroc=auc,auprc=ap_,brier=br,calib_slope=slope)
        print(f"{name:<22}{100*yt.mean():>7.1f}{auc:>8.3f}{ap_:>8.3f}{br:>8.3f}{slope:>12.3f}")
    json.dump(res,open(os.path.join(a.out_dir,"metrics.json"),"w"),indent=2)
    print("saved ->",a.out_dir)

if __name__=="__main__": main()
