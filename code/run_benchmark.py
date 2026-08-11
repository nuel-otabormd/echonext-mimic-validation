"""Apply the frozen EchoNext-Mini weights to the RELEASED EchoNext-Mini benchmark test split.

This is: "The released weights should be applied to the released EchoNext-Mini
benchmark dataset, with CIL and calibration slope reported alongside the MIMIC-IV results. If the
same offset is present in the benchmark dataset, it is a property of the released model rather than
a consequence of external dataset shift."

The benchmark ships ALREADY PREPROCESSED by EchoNext's own pipeline:
    EchoNext_test_waveforms.npy         (5442, 1, 2500, 12)  <- exactly the model input shape
    EchoNext_test_tabular_features.npy  (5442, 7)            <- already scaled/imputed
so nothing of ours touches the inputs. Any offset found here therefore cannot be attributed to our
waveform handling, our lead ordering, our baseline filter, or our tabular construction. That makes
nothing in our own preprocessing can contribute to the result.

Reported per label: prevalence, mean predicted probability, AUROC, AUPRC, CIL, calibration slope,
Brier and Brier skill score, plus the same after the closed-form prior-shift correction
    logit(p_corrected) = logit(p) + logit(pi_train)
using ONLY the released training-split prevalences (no local outcome data).

AUROC here is also a self-check: it should reproduce Nature Supplementary Table 15.
"""
import os, sys, csv, json
import numpy as np, torch
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
MDIR = paths.model()
BENCH = paths.benchmark()
OUT = paths.results_dir()
sys.path.insert(0, os.environ.get("ECHONEXT_CRADLENET", os.path.dirname(MDIR.rstrip("/"))))

LABELS = ['lvef_lte_45','lvwt_gte_13','aortic_stenosis','aortic_regurg','mitral_regurg',
          'tricuspid_regurg','pulm_regurg','rv_dysfunction','pericardial','pasp_gte_45',
          'tr_max_gte_32','shd']
FLAGS = ['lvef_lte_45_flag','lvwt_gte_13_flag','aortic_stenosis_moderate_or_greater_flag',
         'aortic_regurgitation_moderate_or_greater_flag','mitral_regurgitation_moderate_or_greater_flag',
         'tricuspid_regurgitation_moderate_or_greater_flag','pulmonary_regurgitation_moderate_or_greater_flag',
         'rv_systolic_dysfunction_moderate_or_greater_flag','pericardial_effusion_moderate_large_flag',
         'pasp_gte_45_flag','tr_max_gte_32_flag','shd_moderate_or_greater_flag']
# Nature Supplementary Table 15 (Columbia Mini-Model on the Columbia ECG test set)
T15 = [85.2, 73.4, 85.9, 73.9, 80.6, 83.3, 82.9, 86.6, 76.6, 77.0, 75.4, 82.0]

lg = lambda p: np.log(np.clip(p, 1e-9, 1 - 1e-9) / (1 - np.clip(p, 1e-9, 1 - 1e-9)))
sig = lambda z: 1.0 / (1.0 + np.exp(-z))


def slope(y, p):
    return LogisticRegression(C=1e6).fit(lg(p).reshape(-1, 1), y).coef_[0, 0]


def bss(y, p):
    pr = y.mean()
    return 1.0 - brier_score_loss(y, p) / (pr * (1 - pr))


# ------------------------------------------------------------------------------ metadata + labels
meta = list(csv.DictReader(open(os.path.join(BENCH, "echonext_metadata_100k.csv"))))
test = [r for r in meta if r['split'] == 'test']
train = [r for r in meta if r['split'] == 'train']
print(f"benchmark test n={len(test):,}   train n={len(train):,}")
y = np.array([[int(float(r[f])) for f in FLAGS] for r in test])
pi_train = np.array([np.mean([float(r[f]) for r in train]) for f in FLAGS])

# ------------------------------------------------------------------------------ inputs (as shipped)
X = np.load(os.path.join(BENCH, "EchoNext_test_waveforms.npy"), mmap_mode='r')
T = np.load(os.path.join(BENCH, "EchoNext_test_tabular_features.npy"))
assert X.shape[0] == len(test) and T.shape == (len(test), 7), (X.shape, T.shape)
print(f"inputs as shipped: waveforms {X.shape} {X.dtype} | tabular {T.shape}")

# ------------------------------------------------------------------------------ model
from cradlenet.models.resnet1d_tabular import ResNet1dWithTabular
ck = torch.load(os.path.join(MDIR, "weights.pt"), map_location="cpu", weights_only=False)
model = ResNet1dWithTabular(len_tabular_feature_vector=7, filter_size=16, num_classes=12)
model.load_state_dict(ck["model"])          # strict, as upstream
model.eval()
torch.set_num_threads(2)

P = []
B = 128
for s in range(0, X.shape[0], B):
    xb = torch.tensor(np.asarray(X[s:s + B]), dtype=torch.float32)
    tb = torch.tensor(T[s:s + B], dtype=torch.float32)
    with torch.no_grad():
        P.append(torch.sigmoid(model((xb, tb))).numpy())
    if (s // B) % 10 == 0:
        print(f"  {min(s+B, X.shape[0]):,}/{X.shape[0]:,}", flush=True)
P = np.concatenate(P).astype(np.float64)
np.save(os.path.join(paths.predictions_dir(), "probs_benchmark.npy"), P)

# ------------------------------------------------------------------------------ report
print("\n=== BENCHMARK TEST SPLIT (released model on its OWN data, EchoNext's own preprocessing) ===")
print(f"{'label':18s}{'prev%':>7}{'meanPred':>9}{'CIL':>8}{'slope':>7}{'AUROC':>7}{'T15':>7}{'d':>7}{'BSS':>8}")
res = {}
for j, n in enumerate(LABELS):
    yy, pp = y[:, j], P[:, j]
    a = roc_auc_score(yy, pp)
    res[n] = dict(prev=float(yy.mean()), mean_pred=float(pp.mean()), cil=float(yy.mean() - pp.mean()),
                  slope=float(slope(yy, pp)), auroc=float(a), auprc=float(average_precision_score(yy, pp)),
                  brier=float(brier_score_loss(yy, pp)), bss=float(bss(yy, pp)), t15=T15[j] / 100)
    r = res[n]
    print(f"{n:18s}{100*r['prev']:7.2f}{r['mean_pred']:9.3f}{r['cil']:+8.3f}{r['slope']:7.2f}"
          f"{a:7.3f}{T15[j]/100:7.3f}{a-T15[j]/100:+7.3f}{r['bss']:+8.3f}")

print("\n=== AFTER CLOSED-FORM PRIOR SHIFT (uses only released training prevalences) ===")
print(f"{'label':18s}{'pi_train%':>10}{'meanPred':>9}{'CIL':>8}{'slope':>7}{'BSS':>8}")
for j, n in enumerate(LABELS):
    yy = y[:, j]
    pc = sig(lg(P[:, j]) + lg(pi_train[j]))
    res[n].update(cil_corr=float(yy.mean() - pc.mean()), slope_corr=float(slope(yy, pc)),
                  bss_corr=float(bss(yy, pc)), pi_train=float(pi_train[j]))
    print(f"{n:18s}{100*pi_train[j]:10.2f}{pc.mean():9.3f}{yy.mean()-pc.mean():+8.3f}"
          f"{slope(yy, pc):7.2f}{bss(yy, pc):+8.3f}")

mb = np.mean([abs(res[n]['cil']) for n in LABELS])
ma = np.mean([abs(res[n]['cil_corr']) for n in LABELS])
print(f"\nmean |CIL|  before {mb:.3f}  ->  after prior shift {ma:.3f}   ({100*(1-ma/mb):.0f}% reduction)")
json.dump(res, open(os.path.join(OUT, "benchmark_metrics.json"), "w"), indent=2)
print("wrote", OUT)
