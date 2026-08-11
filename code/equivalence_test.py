"""EchoNext-Mini pipeline equivalence test - STRATIFIED, ALL 12 OUTPUT HEADS.

Replaces the previous smoke_test.py, which the README and TRIPOD checklist described as the
"25-ECG end-to-end pipeline check vs official module" backing the 1.19e-7 equivalence claim but
which, as written, ran standalone inference only, printed the composite probability alone, and
never loaded the official Lightning module at all.

Two independent checks:

  PART A - TABULAR PREPROCESSING
    Our 7-feature construction vs the official preprocess.tabular_transformer().
    Stratified deliberately over the failure modes that matter rather than sampled at random:
    missing PR interval (15.3% of the MIMIC cohort, concentrated in atrial fibrillation and
    rising to 25.1% in ICU), missing atrial rate (100% in MIMIC), missing QRS/QTc, and extreme
    values. A random 25-record sample would very likely contain none of them.

    Hughes et al. (NEJM AI 2026, p5), the released
    preprocess.py:29,35, and the Nature Supplementary Methods all specify that atrial rate and
    PR interval are filled with RAW 0 BEFORE scaling. Letting a missing PR stay NaN through the
    scaler so it reached the median imputer, mapping it to +0.158 instead of -2.474: a 2.63 SD
    error on one of seven inputs. Both fill rules are computed here so the
    magnitude of the defect is measured, not asserted.

  PART B - MODEL
    Official Resnet1dWithTabularModule, instantiated and weight-loaded EXACTLY as
    cradlenet/scripts/inference/ecg_tabular.py does (strict load of weights["model"]), vs our
    standalone ResNet1dWithTabular. Compared across all 12 output heads, not just the composite.

Run:  python code/equivalence_test.py            (needs pytorch_lightning for Part B)
      python code/equivalence_test.py --no-pl    (Part A only)
"""
import os, sys, json, csv, argparse
import numpy as np, joblib
# torch / wfdb / scipy are imported lazily inside PART B so that PART A (tabular equivalence) can be
# run under a bare scikit-learn 1.1.3 environment to confirm the forward-compat shim is faithful.

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
MDIR = paths.model()
WAVE = paths.waveform_dir()
COHORT = paths.cohort_csv()
sys.path.insert(0, os.environ.get("ECHONEXT_CRADLENET", os.path.dirname(MDIR.rstrip("/"))))

MODEL_LEADS = ['I','II','III','aVR','aVL','aVF','V1','V2','V3','V4','V5','V6']  # aVL before aVF (parse_xml)
LABELS = ['lvef_lte_45','lvwt_gte_13','aortic_stenosis','aortic_regurg','mitral_regurg',
          'tricuspid_regurg','pulm_regurg','rv_dysfunction','pericardial','pasp_gte_45',
          'tr_max_gte_32','shd']
# official column order: sex first, then TABULAR_FLOAT
NUMCOLS = ['age_at_ecg','ventricular_rate','atrial_rate','pr_interval','qrs_duration','qt_corrected']

ap = argparse.ArgumentParser()
ap.add_argument("--no-pl", action="store_true", help="skip Part B (no pytorch_lightning)")
ap.add_argument("--n-per-stratum", type=int, default=6)
args = ap.parse_args()


def fnum(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else np.nan
    except Exception:
        return np.nan


# ----------------------------------------------------------------------------- stratified sample
rows = list(csv.DictReader(open(COHORT)))
present = {r['ecg_path'] for r in rows
           if os.path.exists(os.path.join(WAVE, r['ecg_path'] + '.dat'))
           and os.path.exists(os.path.join(WAVE, r['ecg_path'] + '.hea'))}
rows = [r for r in rows if r['ecg_path'] in present]
print(f"cohort rows with waveform on disk: {len(rows):,}")

k = args.n_per_stratum
def take(pred, n=k):
    return [r for r in rows if pred(r)][:n]

strata = {
    "PR missing":        take(lambda r: r['pr_missing'].lower() == 'true'),
    "PR present":        take(lambda r: r['pr_missing'].lower() != 'true'),
    "QRS or QTc missing":take(lambda r: np.isnan(fnum(r['qrs_duration'])) or np.isnan(fnum(r['qt_corrected']))),
    "ICU (PR miss 25%)": take(lambda r: r.get('setting') == 'ICU'),
    "Outpatient":        take(lambda r: r.get('setting') == 'Outpatient/ambulatory'),
}
# extremes on each numeric input
for col in ['age_at_ecg','ventricular_rate','qt_corrected','qrs_duration']:
    ok = [r for r in rows if not np.isnan(fnum(r[col]))]
    ok.sort(key=lambda r: fnum(r[col]))
    strata[f"extreme {col}"] = ok[:2] + ok[-2:]

sel, seen = [], set()
for name, rs in strata.items():
    got = 0
    for r in rs:
        if r['ecg_path'] not in seen:
            seen.add(r['ecg_path']); sel.append(r); got += 1
    print(f"  {name:22s} +{got}")
print(f"stratified test set: n={len(sel)}\n")
if not sel:
    sys.exit("No records selected - check ECHONEXT_DATA and that waveforms are present.")


# ------------------------------------------------------------------- PART A: tabular equivalence
pipe = joblib.load(os.path.join(MDIR, "tabular_transformer.joblib"))
sc, im = pipe.named_steps['scale'], pipe.named_steps['impute']

# --- scikit-learn forward-compat shim -----------------------------------------------------------
# The released joblib was pickled with scikit-learn 1.1.3. Its stored ARRAYS unpickle correctly on
# any modern version (mean_, scale_, statistics_ verified byte-identical under 1.1.3 and 1.6.1), but
# calling .transform() on it fails on >=1.2 because SimpleImputer gained attributes that the 1.1.3
# pickle does not carry. We restore them at their 1.1.3-equivalent defaults so the OFFICIAL function
# can be executed for comparison. This shim affects only the reference path in this test; the
# production pipeline reads mean_/scale_/statistics_ directly and never calls .transform(), which is
# why it is version-independent by construction.
_DEFAULTS = {"keep_empty_features": False, "add_indicator": False, "fill_value": None}
for _a, _v in _DEFAULTS.items():
    if not hasattr(im, _a):
        setattr(im, _a, _v)
        print(f"  [shim] SimpleImputer.{_a} = {_v!r} (absent in the 1.1.3 pickle)")
if not hasattr(sc, "feature_names_in_"):
    pass  # optional attribute, not used by transform

raw = np.array([[fnum(r['age_at_ecg']), fnum(r['ventricular_rate']), np.nan,   # atrial rate absent in MIMIC
                 fnum(r['pr_interval']), fnum(r['qrs_duration']), fnum(r['qt_corrected'])]
                for r in sel])
sex = np.array([[1.0 if r['gender'].strip().upper() == 'M' else 0.0] for r in sel])


def ours_fixed(raw):
    """Released rule: atrial_rate and pr_interval -> RAW 0 before scaling; others -> median after."""
    x = raw.copy()
    x[:, 2] = np.nan_to_num(x[:, 2], nan=0.0)   # atrial rate  fillna(0)
    x[:, 3] = np.nan_to_num(x[:, 3], nan=0.0)   # PR interval  fillna(0)   <-- the fix
    xs = (x - sc.mean_) / sc.scale_
    nan = np.isnan(xs)
    xs[nan] = np.take(im.statistics_, np.where(nan)[1])
    return xs


def ours_alt(raw):
    """Alternative fill: atrial rate 0, but a missing PR routed to the median imputer."""
    x = raw.copy()
    x[:, 2] = np.nan_to_num(x[:, 2], nan=0.0)
    xs = (x - sc.mean_) / sc.scale_
    nan = np.isnan(xs)
    xs[nan] = np.take(im.statistics_, np.where(nan)[1])
    return xs


import pandas as pd
from preprocess import tabular_transformer, TABULAR_COLS
df = pd.DataFrame({
    'sex': ['male' if s[0] == 1.0 else 'female' for s in sex],
    **{c: raw[:, i] for i, c in enumerate(NUMCOLS)},
})
official, _ = tabular_transformer(df[TABULAR_COLS], fit_yn=False, pipe=pipe)
off = official.to_numpy(dtype=np.float64)          # [sex_clean, age, vent, atrial, pr, qrs, qtc]

ours = np.concatenate([sex, ours_fixed(raw)], axis=1)
alt  = np.concatenate([sex, ours_alt(raw)],   axis=1)

d_fix = np.abs(off - ours).max(axis=0)
d_alt = np.abs(off - alt).max(axis=0)
names = ['sex'] + NUMCOLS
print("PART A - tabular features vs official preprocess.tabular_transformer()")
print(f"  {'feature':18s}{'max|fixed-official|':>22}{'max|imputed-official|':>24}")
for i, nm in enumerate(names):
    flag = "   <-- imputed fill DIVERGES" if d_alt[i] > 1e-9 else ""
    print(f"  {nm:18s}{d_fix[i]:22.3e}{d_alt[i]:20.3e}{flag}")
A_OK = d_fix.max() < 1e-9
n_prmiss = int(np.isnan(raw[:, 3]).sum())
print(f"\n  records with missing PR in this test set: {n_prmiss}/{len(sel)}")
print(f"  PART A: {'PASS' if A_OK else 'FAIL'}  (max abs diff {d_fix.max():.3e})\n")


# ------------------------------------------------------------------- PART B: model equivalence
if args.no_pl:
    print("PART B skipped (--no-pl)."); sys.exit(0 if A_OK else 1)

import torch, wfdb, scipy.signal


def baseline_wander_removal(data, fs=250):          # data: (12, 2500)
    out = np.zeros(data.shape)
    for lead in range(data.shape[0]):
        base = scipy.signal.medfilt(data[lead, :], int(np.round(0.2 * fs)) + 1)
        base = scipy.signal.medfilt(base,          int(np.round(0.6 * fs)) + 1)
        out[lead, :] = data[lead, :] - base
    return out


def load_waveform(path):
    rec = wfdb.rdrecord(os.path.join(WAVE, path), physical=False)
    sig = rec.d_signal.astype(np.float64)
    idx = {n: i for i, n in enumerate(rec.sig_name)}
    sig = sig[:, [idx[l] for l in MODEL_LEADS]][::2, :]     # reorder + 500->250 Hz
    return baseline_wander_removal(sig.T, 250).T            # (2500, 12)


prm = json.load(open(os.path.join(MDIR, "waveform_normalization_params.json")))
wf = np.stack([load_waveform(r['ecg_path']) for r in sel])          # (N,2500,12)
d = np.transpose(wf, (0, 2, 1)).copy()
for L in range(12):
    d[:, L, :] = (np.clip(d[:, L, :], prm['lowerbound'][L], prm['upperbound'][L]) - prm['mean'][L]) / prm['std'][L]
X = torch.tensor(np.transpose(d, (0, 2, 1))[:, None, :, :], dtype=torch.float32)
T = torch.tensor(ours, dtype=torch.float32)

from cradlenet.models.resnet1d_tabular import ResNet1dWithTabular
from cradlenet.lightning.modules.resnet1d_with_tabular import Resnet1dWithTabularModule

ck = torch.load(os.path.join(MDIR, "weights.pt"), map_location="cpu", weights_only=False)

# official: exactly as cradlenet/scripts/inference/ecg_tabular.py --legacy echonext
module = Resnet1dWithTabularModule(
    model_kwargs={"len_tabular_feature_vector": 7, "filter_size": 16, "num_classes": 12},
    lr=0, binary=True)
module.model.load_state_dict(ck["model"])          # strict=True, as upstream
module.eval()

# ours: standalone, ALSO strict - strict=False would mask a key mismatch
mine = ResNet1dWithTabular(len_tabular_feature_vector=7, filter_size=16, num_classes=12)
missing, unexpected = mine.load_state_dict(ck["model"], strict=True), None
mine.eval()

with torch.no_grad():
    p_off = module((X, T)).numpy()                 # module.forward applies sigmoid when binary
    p_our = torch.sigmoid(mine((X, T))).numpy()

diff = np.abs(p_off - p_our)
print("PART B - all 12 output heads, official Lightning module vs standalone")
print(f"  {'#':>2}  {'head':18s}{'max|diff|':>13}{'mean prob':>12}")
for j, nm in enumerate(LABELS):
    print(f"  {j:2d}  {nm:18s}{diff[:, j].max():13.3e}{p_off[:, j].mean():12.4f}")
B_OK = diff.max() < 1e-6
print(f"\n  overall max abs diff across all heads and records: {diff.max():.3e}")
print(f"  PART B: {'PASS' if B_OK else 'FAIL'}")
print(f"\nEQUIVALENCE TEST: {'PASS' if (A_OK and B_OK) else 'FAIL'}")
# ---------------------------------------------------------------------------- persist the result
# The outcome is written to disk, not only printed, so the verification leaves an artefact that can
# be checked without re-running the test.
RESULTS_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "results", "equivalence.json")
os.makedirs(os.path.dirname(RESULTS_OUT), exist_ok=True)
json.dump({"part_a": "PASS" if A_OK else "FAIL",
           "part_b": "PASS" if B_OK else "FAIL",
           "overall": "PASS" if (A_OK and B_OK) else "FAIL",
           "max_abs_diff_tabular": float(d_fix.max()),
           "max_abs_diff_outputs": float(diff.max())},
          open(RESULTS_OUT, "w"), indent=1)
print(f"\nwrote {RESULTS_OUT}")

sys.exit(0 if (A_OK and B_OK) else 1)
