"""EchoNext-Mini smoke test on MIMIC-IV-ECG (25 ECGs).
WFDB -> model input adapter + standalone inference (no Lightning/azureml)."""
import os, sys, json, csv
import numpy as np, torch, joblib, wfdb
import scipy.signal

REPO = os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "EchoNext-repo/7-EchoNext Minimodel")
MDIR = os.path.join(REPO, "models/echonext_multilabel_minimodel")
WAVE_BASE = os.path.expanduser("~/iCloud Drive (Archive)/Desktop/Claude Cowork/MIMIC-IV ECG/mimic-iv-ecg")  # materialized local copy
CSV = os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "EchoNext-repo/smoke25.csv")
sys.path.insert(0, REPO)
from cradlenet.models.resnet1d_tabular import ResNet1dWithTabular

MODEL_LEADS = ['I','II','III','aVR','aVL','aVF','V1','V2','V3','V4','V5','V6']  # aVL before aVF (parse_xml)
LABELS = ['lvef_lte_45','lvwt_gte_13','aortic_stenosis','aortic_regurg','mitral_regurg',
          'tricuspid_regurg','pulm_regurg','rv_dysfunction','pericardial','pasp_gte_45','tr_max_gte_32','shd']

def baseline_wander_removal(data, fs=250):  # data: (12, 2500)
    out = np.zeros(data.shape)
    for lead in range(data.shape[0]):
        w1 = int(np.round(0.2*fs))+1
        base = scipy.signal.medfilt(data[lead,:], w1)
        w2 = int(np.round(0.6*fs))+1
        base = scipy.signal.medfilt(base, w2)
        out[lead,:] = data[lead,:] - base
    return out

def load_waveform(path):
    """Return (2500,12) in MODEL lead order, raw ADC, decimated 500->250, baseline-removed."""
    rec = wfdb.rdrecord(os.path.join(WAVE_BASE, path), physical=False)  # raw digital (~200/mV)
    sig = rec.d_signal.astype(np.float64)           # (5000, 12) MIMIC order
    name2idx = {n: i for i, n in enumerate(rec.sig_name)}
    sig = sig[:, [name2idx[l] for l in MODEL_LEADS]] # reorder to model order
    sig = sig[::2, :]                                # 500 -> 250 Hz (every other) -> (2500,12)
    sig = baseline_wander_removal(sig.T, 250).T      # per-lead baseline removal
    return sig                                       # (2500, 12)

def per_lead_norm(wf, params):  # wf: (N,2500,12) -> (N,1,2500,12)
    d = np.transpose(wf, (0,2,1)).copy()             # (N,12,2500)
    for L in range(12):
        d[:,L,:] = np.clip(d[:,L,:], params['lowerbound'][L], params['upperbound'][L])
        d[:,L,:] = (d[:,L,:] - params['mean'][L]) / params['std'][L]
    print("  post-norm overall mean=%.3f std=%.3f (expect ~0 / ~1)" % (d.mean(), d.std()))
    return np.transpose(d, (0,2,1))[:, None, :, :]    # (N,1,2500,12)

# ---- load data ----
rows = list(csv.DictReader(open(CSV)))
rows = [r for r in rows if os.path.exists(os.path.join(WAVE_BASE, r['ecg_path'] + '.dat'))
                        and os.path.exists(os.path.join(WAVE_BASE, r['ecg_path'] + '.hea'))]  # Archive-materialized (both files)
print(f"using {len(rows)} ECGs present in Archive (SHD+ {sum(int(r['shd']) for r in rows)} / SHD- {sum(1-int(r['shd']) for r in rows)})")
wf = np.stack([load_waveform(r['ecg_path']) for r in rows])           # (N,2500,12)
print("raw waveform amplitude range: [%.0f, %.0f] (ADC units)" % (wf.min(), wf.max()))
params = json.load(open(os.path.join(MDIR, "waveform_normalization_params.json")))
X_wave = torch.tensor(per_lead_norm(wf, params), dtype=torch.float32)

# ---- tabular: sex + [age, vent, atrial(0), pr, qrs, qtc] scaled ----
pipe = joblib.load(os.path.join(MDIR, "tabular_transformer.joblib"))
sc, im = pipe.named_steps['scale'], pipe.named_steps['impute']
def f(x):
    try: return float(x)
    except: return np.nan
Xnum = np.array([[f(r['age_at_ecg']), f(r['ventricular_rate']), 0.0,
                  f(r['pr_interval']), f(r['qrs_duration']), f(r['qt_corrected'])] for r in rows])
Xs = (Xnum - sc.mean_) / sc.scale_
nan = np.isnan(Xs); Xs[nan] = np.take(im.statistics_, np.where(nan)[1])
sex = np.array([[1.0 if r['gender'].strip().upper()=='M' else 0.0] for r in rows])
X_tab = torch.tensor(np.concatenate([sex, Xs], axis=1), dtype=torch.float32)
print("tabular shape:", tuple(X_tab.shape))

# ---- model ----
model = ResNet1dWithTabular(len_tabular_feature_vector=7, filter_size=16, num_classes=12)
ck = torch.load(os.path.join(MDIR, "weights.pt"), map_location='cpu')
sd = ck['model'] if isinstance(ck, dict) and 'model' in ck else ck.get('state_dict', ck)
sd = {(k[6:] if k.startswith('model.') else k): v for k, v in sd.items()}
miss, unexp = model.load_state_dict(sd, strict=False)
print(f"loaded weights | missing={len(miss)} unexpected={len(unexp)}")
model.eval()
with torch.no_grad():
    probs = torch.sigmoid(model((X_wave, X_tab))).numpy()           # (N,12)

# ---- report ----
y = np.array([[int(r[c]) for c in ['lvef_lte_45','lvwt_gte_13','aortic_stenosis_modsev','aortic_regurg_modsev',
     'mitral_regurg_modsev','tricuspid_regurg_modsev','pulm_regurg_modsev','rv_dysfunction_modsev',
     'pericardial_modlarge','pasp_gte_45','tr_max_gte_32','shd']] for r in rows])
shd_p, shd_y = probs[:,11], y[:,11]
print("\nSHD prob by true label:  pos mean=%.3f  neg mean=%.3f" % (shd_p[shd_y==1].mean(), shd_p[shd_y==0].mean()))
# rank-based AUC on the 26
from itertools import product
pairs = list(product(np.where(shd_y==1)[0], np.where(shd_y==0)[0]))
auc = np.mean([shd_p[i] > shd_p[j] for i,j in pairs])
print("SHD AUROC (26-sample, smoke only): %.3f" % auc)
print("\nper-ECG SHD prob vs label:")
for k,r in enumerate(rows):
    print("  %s  p_shd=%.3f  y_shd=%d" % (r['ecg_path'].split('/')[-1], shd_p[k], shd_y[k]))
