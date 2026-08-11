"""UNIFIED analysis for the EchoNext-Mini / MIMIC-IV external validation.

Every quantity reported in the manuscript is computed here, from ONE label source, ONE metrics
function, ONE estimator and ONE seed, and emitted into ONE results object that the tables are
generated from. No number in the manuscript is hand-transcribed.

What is computed:
  * Discrimination (AUROC, AUPRC, and AUPRC normalised to prevalence) per label.
  * Calibration: mean predicted probability, calibration-in-the-large on the probability scale,
    calibration slope, Brier score and Brier skill score relative to a prevalence-only predictor.
    Mean predicted probability is a column of its own beside prevalence and CIL so the two cannot
    be confused.
  * Calibration slopes use C=1e6, i.e. effectively unpenalised. A default LogisticRegression() is
    L2-penalised at C=1.0, which shrinks the slope toward zero and is not what is wanted here.
  * Percentile bootstrap intervals, 2,000 resamples, seed 0, with identical resample indices reused
    across labels and subgroups so comparisons between them are paired.
  * Complete-case sensitivity from the *_source_present indicators.
  * Subgroups by sex, age, race, care setting and ECG acquisition setting.
  * A closed-form prior shift compared head to head against local out-of-fold Platt scaling.

Usage:  python code/analyze.py            (writes results/analysis.json + a readable summary)
"""
import os, sys, csv, json, argparse
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ap = argparse.ArgumentParser()
ap.add_argument("--probs", default=None, help="default: $ECHONEXT_WORK/predictions/probs.npy")
ap.add_argument("--paths", default=None)
ap.add_argument("--cohort", default=None)
ap.add_argument("--race", default=None)
ap.add_argument("--bench", default=None)
ap.add_argument("--boot", type=int, default=2000)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", default=None)
args = ap.parse_args()
args.probs  = args.probs  or os.path.join(paths.predictions_dir(), "probs.npy")
args.paths  = args.paths  or os.path.join(paths.predictions_dir(), "kept_paths.txt")
args.cohort = args.cohort or paths.cohort_csv()
args.race   = args.race   or paths.race_csv()
args.bench  = args.bench  or os.path.join(paths.results_dir(), "benchmark_metrics.json")
args.out    = args.out    or paths.results_dir()
os.makedirs(args.out, exist_ok=True)

# label name -> (probability column index, cohort CSV column, source-present column or None)
LABELS = [
    ("Reduced LVEF (<=45%)",            0,  "lvef_lte_45",              "lvef_present"),
    ("LV wall thickness (>=1.3 cm)",    1,  "lvwt_gte_13",              "lvwt_present"),
    ("Aortic stenosis",                 2,  "aortic_stenosis_modsev",   "as_source_present"),
    ("Aortic regurgitation",            3,  "aortic_regurg_modsev",     "ar_present"),
    ("Mitral regurgitation",            4,  "mitral_regurg_modsev",     "mr_present"),
    ("Tricuspid regurgitation",         5,  "tricuspid_regurg_modsev",  "tr_present"),
    ("Pulmonic regurgitation",          6,  "pulm_regurg_modsev",       "pr_present"),
    ("RV dysfunction",                  7,  "rv_dysfunction_modsev",    "rv_present"),
    ("Pericardial effusion",            8,  "pericardial_modlarge",     "pe_present"),
    ("Elevated PASP (>=45 mmHg)",       9,  "pasp_gte_45",              "trgrad_present"),
    ("Elevated TR Vmax (>=3.2 m/s)",   10,  "tr_max_gte_32",            "trvel_present"),
    ("Structural heart disease",        11, "shd",                      None),
]
# released training-split prevalences, for the data-free prior shift
PI_TRAIN = [0.2340, 0.2438, 0.0403, 0.0121, 0.0847, 0.1063, 0.0083, 0.1324, 0.0287, 0.1894, 0.1034, 0.5237]

lg = lambda p: np.log(np.clip(p, 1e-9, 1 - 1e-9) / (1 - np.clip(p, 1e-9, 1 - 1e-9)))
sig = lambda z: 1.0 / (1.0 + np.exp(-z))


def slope(y, p):
    """Calibration slope. C=1e6 => effectively unpenalised. See module docstring."""
    return float(LogisticRegression(C=1e6).fit(lg(p).reshape(-1, 1), y).coef_[0, 0])


def metrics(y, p):
    y = np.asarray(y, float); p = np.asarray(p, float)
    pr = y.mean()
    if not (0 < pr < 1):
        return None
    noskill = pr * (1 - pr)
    auprc = average_precision_score(y, p)
    br = brier_score_loss(y, p)
    return dict(n=int(len(y)), n_pos=int(y.sum()), prev=float(pr),
                mean_pred=float(p.mean()), cil=float(pr - p.mean()), slope=slope(y, p),
                auroc=float(roc_auc_score(y, p)), auprc=float(auprc),
                auprc_norm=float((auprc - pr) / (1 - pr)),
                brier=float(br), bss=float(1 - br / noskill))


def boot_ci(y, p, fn, B, rng):
    """Percentile bootstrap. rng is re-seeded by the caller so the SAME resample indices are reused
    across every label and subgroup, making comparisons between them paired."""
    y = np.asarray(y); p = np.asarray(p); n = len(y); out = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        if y[i].sum() in (0, n):
            continue                      # degenerate resample; disclosed in Methods
        try:
            out.append(fn(y[i], p[i]))
        except Exception:
            pass
    if not out:
        return None, None, 0
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(out)


def oof_platt(y, p, seed=0):
    """Local recalibration: 5-fold out-of-fold Platt scaling. Needs local outcome labels."""
    y = np.asarray(y, float); oof = np.zeros(len(y))
    for tr, te in KFold(5, shuffle=True, random_state=seed).split(p):
        lr = LogisticRegression(C=1e6).fit(lg(p[tr]).reshape(-1, 1), y[tr])
        oof[te] = lr.predict_proba(lg(p[te]).reshape(-1, 1))[:, 1]
    return oof


# ----------------------------------------------------------------------------------- load
P = np.load(args.probs).astype(np.float64)
paths = open(args.paths).read().split("\n")
coh = {r["ecg_path"]: r for r in csv.DictReader(open(args.cohort))}
race = {r["subject_id"]: r["race"] for r in csv.DictReader(open(args.race))}
rows = [coh[p] for p in paths]
n = len(rows)
assert P.shape[0] == n, (P.shape, n)
print(f"n = {n:,}   labels = {len(LABELS)}   bootstrap B = {args.boot}, seed {args.seed}")

age = np.array([float(r["age_at_ecg"]) for r in rows])
sex = np.array([r["gender"].strip().upper() for r in rows])
rc = np.array([race.get(r["subject_id"], "Unknown") for r in rows])
setting = np.array([r["setting"] for r in rows])
setting_broad = np.array([r["setting_broad"] for r in rows])
acq = np.array([f"{r['bandwidth']} | {r['filtering']}" for r in rows])
prmiss = np.array([r["pr_missing"].lower() == "true" for r in rows])

# Only the BASENAME of the predictions file is recorded: analysis.json is committed to the public
# repository and an absolute path would be specific to whoever ran it.
R = {"meta": dict(n=n, bootstrap=args.boot, seed=args.seed, interval="percentile",
                  estimator="LogisticRegression(C=1e6)",
                  probs=os.path.basename(args.probs))}

# ------------------------------------------------------- 1. per-label primary + recalibration
print("\n[1] per-label primary analysis + recalibration")
R["labels"] = {}
for name, j, col, present in LABELS:
    y = np.array([int(r[col]) for r in rows]); p = P[:, j]
    m = metrics(y, p)
    rng = np.random.default_rng(args.seed)
    m["auroc_ci"] = boot_ci(y, p, lambda a, b: roc_auc_score(a, b), args.boot, rng)[:2]
    rng = np.random.default_rng(args.seed)
    m["cil_ci"] = boot_ci(y, p, lambda a, b: a.mean() - b.mean(), args.boot, rng)[:2]

    # data-free prior shift (no local labels used)
    pc = sig(lg(p) + lg(PI_TRAIN[j]))
    m["prior_shift"] = metrics(y, pc)
    # local out-of-fold Platt (needs local labels) - head-to-head comparison
    po = oof_platt(y, p, args.seed)
    m["platt_oof"] = metrics(y, po)

    # complete-case sensitivity
    if present:
        k = np.array([int(r[present]) for r in rows]).astype(bool)
        m["complete_case"] = metrics(y[k], p[k]) if k.sum() > 50 else None
        m["source_present_frac"] = float(k.mean())
    R["labels"][name] = m
    cc = m.get("complete_case")
    print(f"  {name:32s} prev {100*m['prev']:5.2f}%  meanPred {m['mean_pred']:.3f}  "
          f"CIL {m['cil']:+.3f}  slope {m['slope']:.2f}  AUROC {m['auroc']:.3f}  "
          f"BSS {m['bss']:+.3f} -> shift {m['prior_shift']['bss']:+.3f} / platt {m['platt_oof']['bss']:+.3f}"
          + (f"  | complete-case AUROC {cc['auroc']:.3f} (n={cc['n']:,})" if cc else ""))

# ------------------------------------------------------------------- 2. subgroups (composite)
print("\n[2] subgroups, composite label")
yc = np.array([int(r["shd"]) for r in rows]); pc_ = P[:, 11]
R["subgroups"] = {}
groups = {
    "Sex": {"Male": sex == "M", "Female": sex == "F"},
    "Age": {"<65": age < 65, "65-79": (age >= 65) & (age < 80), ">=80": age >= 80},
    "Race/ethnicity": {g: rc == g for g in ["White", "Black", "Hispanic", "Asian", "Other", "Unknown"]},
    "Care setting": {g: setting == g for g in np.unique(setting)},
    "Care setting (broad)": {g: setting_broad == g for g in np.unique(setting_broad)},
    "ECG acquisition": {g: acq == g for g in np.unique(acq)},
    "PR interval": {"present": ~prmiss, "missing": prmiss},
}
for dim, gs in groups.items():
    R["subgroups"][dim] = {}
    print(f"  {dim}")
    for g, mask in gs.items():
        if mask.sum() < 100 or yc[mask].sum() < 20:
            print(f"    {g:38s} n={int(mask.sum()):,} (too small, skipped)"); continue
        m = metrics(yc[mask], pc_[mask])
        rng = np.random.default_rng(args.seed)
        m["auroc_ci"] = boot_ci(yc[mask], pc_[mask], lambda a, b: roc_auc_score(a, b), args.boot, rng)[:2]
        R["subgroups"][dim][g] = m
        lo, hi = m["auroc_ci"]
        print(f"    {g:38s} n={m['n']:6,}  prev {100*m['prev']:5.1f}%  "
              f"AUROC {m['auroc']:.3f} [{lo:.3f}-{hi:.3f}]  slope {m['slope']:.2f}")

# --------------------------------------------------------- 3. linkage-window sensitivity
print("\n[3] ECG-to-echo linkage window (composite)")
gap = np.array([float(r["ecg_to_echo_days"]) for r in rows])
R["linkage_window"] = {}
for w in (30, 90, 180, 365):
    k = gap <= w
    m = metrics(yc[k], pc_[k]); R["linkage_window"][f"<={w}d"] = m
    print(f"  <={w:3d} d  n={m['n']:6,}  prev {100*m['prev']:5.1f}%  AUROC {m['auroc']:.3f}  "
          f"CIL {m['cil']:+.3f}  slope {m['slope']:.2f}")

# ------------------------------------------------- 4. label-definition sensitivity analyses
print("\n[4] alternative label definitions")
ALT = [
    ("RV dysfunction: categorical only (PRIMARY)", 7, "rv_dysfunction_cat_only"),
    ("RV dysfunction: categorical + TAPSE",        7, "rv_dysfunction_tapse"),
    ("TR Vmax: direct velocity (PRIMARY)",        10, "tr_max_gte_32"),
    ("TR Vmax: derived gradient",                 10, "tr_max_gte_32_grad"),
    ("Aortic stenosis: rebuilt (PRIMARY)",         2, "aortic_stenosis_modsev"),
    ("Aortic stenosis: graded severity field only", 2, "aortic_stenosis_graded_only"),
    ("LVWT: max(septal, inferolateral) (PRIMARY)", 1, "lvwt_gte_13"),
    ("LVWT: septal >=1.5 cm",                      1, "septal_gte_15"),
    ("LVWT: categorical moderate-or-severe",       1, "lvwt_cat_modsev"),
    ("PASP: TR gradient + IVC RAP (PRIMARY)",      9, "pasp_gte_45"),
    ("PASP: phtn_severity moderate-or-severe",     9, "phtn_modsev"),
    ("Composite: rebuilt AS (PRIMARY)",           11, "shd"),
    ("Composite: graded severity field only",     11, "shd_graded_only"),
]
R["alt_definitions"] = {}
for name, j, col in ALT:
    if col not in rows[0]:
        print(f"  {name:44s} [column {col} absent]"); continue
    y = np.array([int(r[col]) for r in rows])
    m = metrics(y, P[:, j])
    if m is None:
        continue
    R["alt_definitions"][name] = m
    print(f"  {name:44s} prev {100*m['prev']:5.2f}%  AUROC {m['auroc']:.3f}  "
          f"CIL {m['cil']:+.3f}  slope {m['slope']:.2f}")

# ------------------------------------------------------------- 5. RV unassessable sensitivity
k = np.array([int(r["rv_unassessable"]) for r in rows]) == 0
y = np.array([int(r["rv_dysfunction_modsev"]) for r in rows])
R["rv_excl_unassessable"] = metrics(y[k], P[k, 7])
print(f"\n[5] RV dysfunction excluding 'not well seen'/'cannot assess': n={int(k.sum()):,} "
      f"AUROC {R['rv_excl_unassessable']['auroc']:.3f} (vs {R['labels']['RV dysfunction']['auroc']:.3f} all)")

# ------------------------------------------- 5b. tabular fill sensitivity: the atrial-rate rule
# MIMIC-IV-ECG has no atrial-rate field, so that predictor is 100% absent for every patient and its
# value is decided entirely by the fill rule rather than by any measurement. The released rule
# writes RAW 0 before scaling; the alternative routes it to the median imputer like any other
# missing continuous feature. run_inference.py produces both from the SAME waveform tensor, so any
# difference here is attributable to that one choice.
alt_probs = os.path.join(os.path.dirname(args.probs), "probs_atrial_median.npy")
if os.path.exists(alt_probs):
    PA = np.load(alt_probs).astype(np.float64)
    if PA.shape != P.shape:
        print(f"\n[5b] atrial-rate variant shape {PA.shape} != {P.shape}; SKIPPED")
    else:
        print("\n[5b] atrial-rate fill sensitivity (released raw 0 vs median imputation)")
        R["atrial_fill"] = {}
        for name, j, col, _present in LABELS:
            y = np.array([int(r[col]) for r in rows])
            a, b = metrics(y, P[:, j]), metrics(y, PA[:, j])
            if a is None or b is None:
                continue
            R["atrial_fill"][name] = {"released_zero": a, "median_imputed": b}
            print(f"  {name:32s} AUROC {a['auroc']:.3f} -> {b['auroc']:.3f} "
                  f"({b['auroc']-a['auroc']:+.3f})   CIL {a['cil']:+.3f} -> {b['cil']:+.3f}")
        d = np.abs(PA - P)
        R["atrial_fill_delta"] = {"max_abs": float(d.max()), "mean_abs": float(d.mean())}
        print(f"  predicted probability shift: max {d.max():.4f}, mean {d.mean():.4f}")
else:
    print(f"\n[5b] atrial-rate variant not found at {alt_probs}; SKIPPED")

# ------------------------------------------------------------------------ 6. benchmark side
if os.path.exists(args.bench):
    R["benchmark"] = json.load(open(args.bench))
    print("\n[6] benchmark metrics attached from", args.bench)

json.dump(R, open(os.path.join(args.out, "analysis.json"), "w"), indent=2)
print("\nwrote", os.path.join(args.out, "analysis.json"))
