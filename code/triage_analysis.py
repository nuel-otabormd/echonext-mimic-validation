"""Prioritisation and decision-analytic evaluation of the composite SHD score.

Three analyses, all on the composite label, which is the one that is calibrated and therefore the
one a real triage workflow would rank on:

  A. DECISION CURVE - net benefit vs threshold probability, against treat-all and treat-none.
     Reported for the raw score and after the data-free prior shift, to show that the ranking-based
     use is unaffected by the calibration defect while the threshold-based use is not.

  B. CAPACITY-CONSTRAINED SIMULATION - modelled on Pedroso et al., Am J Prev Cardiol 2026;27:101539
     (PROVAR+, Minas Gerais), who fixed capacity at 200 echoes/month and reported time to diagnose
     25/50/90% of cases under AI-prioritised vs standard referral. We reproduce that design in
     MIMIC-IV. Ranking is invariant to any monotone transform, so this is exactly the use case that
     survives the component miscalibration.

  C. PPV / YIELD AT FIXED SENSITIVITY, and across simulated prevalences - mirrors Poterucha et al.,
     Nature 2025, Table 3, so the two are directly comparable.

Reads results_v2/probs.npy + the cohort CSV. Writes results/triage.json.
"""
import os, sys, csv, json, argparse
import numpy as np
from sklearn.metrics import roc_curve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ap = argparse.ArgumentParser()
ap.add_argument("--probs", default=None)
ap.add_argument("--paths", default=None)
ap.add_argument("--cohort", default=None)
ap.add_argument("--capacity", type=int, default=200, help="echoes per month (AJPC used 200)")
ap.add_argument("--months", type=int, default=6, help="simulation horizon (AJPC used 6)")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", default=None)
args = ap.parse_args()
args.probs  = args.probs  or os.path.join(paths.predictions_dir(), "probs.npy")
args.paths  = args.paths  or os.path.join(paths.predictions_dir(), "kept_paths.txt")
args.cohort = args.cohort or paths.cohort_csv()
args.out    = args.out    or paths.results_dir()
os.makedirs(args.out, exist_ok=True)

PI_TRAIN_SHD = 0.5237
lg = lambda p: np.log(np.clip(p, 1e-9, 1 - 1e-9) / (1 - np.clip(p, 1e-9, 1 - 1e-9)))
sig = lambda z: 1.0 / (1.0 + np.exp(-z))

P = np.load(args.probs).astype(np.float64)
paths = open(args.paths).read().split("\n")
coh = {r["ecg_path"]: r for r in csv.DictReader(open(args.cohort))}
rows = [coh[p] for p in paths]
y = np.array([int(r["shd"]) for r in rows])
p_raw = P[:, 11]
p_shift = sig(lg(p_raw) + lg(PI_TRAIN_SHD))
n = len(y); prev = y.mean()
print(f"n = {n:,}   composite prevalence = {100*prev:.2f}%")
R = {"n": int(n), "prevalence": float(prev), "capacity_per_month": args.capacity, "months": args.months}

# ------------------------------------------------------------------ A. decision curve
def net_benefit(y, p, t):
    pred = p >= t
    tp = np.sum(pred & (y == 1)); fp = np.sum(pred & (y == 0))
    return tp / len(y) - (fp / len(y)) * (t / (1 - t))

ths = np.round(np.arange(0.05, 0.71, 0.01), 2)
R["decision_curve"] = {
    "thresholds": ths.tolist(),
    "raw":       [float(net_benefit(y, p_raw, t))   for t in ths],
    "prior_shift":[float(net_benefit(y, p_shift, t)) for t in ths],
    "treat_all": [float(prev - (1 - prev) * (t / (1 - t))) for t in ths],
}
print("\n[A] decision curve (net benefit; treat-none = 0)")
print(f"  {'thresh':>7}{'raw':>10}{'prior-shift':>13}{'treat-all':>11}")
for t in (0.10, 0.20, 0.30, 0.40, 0.50):
    i = int(np.where(ths == t)[0][0])
    print(f"  {t:7.2f}{R['decision_curve']['raw'][i]:10.4f}"
          f"{R['decision_curve']['prior_shift'][i]:13.4f}{R['decision_curve']['treat_all'][i]:11.4f}")

# ------------------------------------------------ B. capacity-constrained triage simulation
# Rank-based, so invariant to the calibration defect. Compare AI-prioritised ordering against the
# standard (unprioritised) referral order, which we model as random since MIMIC has no referral
# queue. Random ordering is averaged over repeats with a fixed seed.
# NOTE ON DESIGN. Pedroso et al. fixed capacity at 200 echoes/month against a queue of 1,475, which
# clears in ~7 months, so time-to-diagnosis in months is meaningful there. MIMIC-IV's 45,877 patients
# accrued over 2008-2022, i.e. this is NOT a monthly referral queue, and imposing 200/month on it
# yields uninterpretable horizons (>150 months). We therefore report the CAPACITY-INDEPENDENT
# quantity - cumulative gain, i.e. what fraction of all SHD cases are found once a given fraction of
# the queue has been imaged - plus the enrichment over unprioritised referral at each capacity.
# Ranking is invariant to monotone transforms, so this is exactly the use case that survives the
# component-level calibration defect.
order_ai = np.argsort(-p_raw)                       # highest score first
found_ai = np.cumsum(y[order_ai])
total_pos = int(y.sum())
# Unprioritised referral has expectation prevalence*k at every k; use the exact expectation rather
# than simulated permutations (identical in expectation, zero Monte-Carlo noise).
k_grid = np.arange(1, n + 1)
found_rand = prev * k_grid

print(f"\n[B] capacity-constrained triage - cumulative gain "
      f"({total_pos:,} SHD cases in a queue of {n:,})")
R["triage"] = {"total_positives": total_pos, "by_capacity": {}}
print(f"  {'capacity':>10}{'echoes':>9}{'AI yield':>10}{'standard':>10}{'enrichment':>12}{'PPV of the':>12}")
print(f"  {'(% queue)':>10}{'':>9}{'(% cases)':>10}{'(% cases)':>10}{'':>12}{'slots used':>12}")
for frac in (0.01, 0.025, 0.05, 0.10, 0.20, 0.30, 0.50):
    k = max(1, int(round(frac * n)))
    ya = found_ai[k - 1] / total_pos
    yr = found_rand[k - 1] / total_pos
    R["triage"]["by_capacity"][f"{frac}"] = dict(
        n_echoes=int(k), yield_ai=float(ya), yield_standard=float(yr),
        enrichment=float(ya / yr), ppv=float(found_ai[k - 1] / k))
    print(f"  {100*frac:9.1f}%{k:9,}{100*ya:9.1f}%{100*yr:9.1f}%{ya/yr:11.2f}x{100*found_ai[k-1]/k:11.1f}%")

# how much of the queue must be imaged to reach a given share of cases
print(f"\n  queue fraction needed to capture a given share of all SHD cases:")
print(f"  {'target':>8}{'AI-ranked':>12}{'standard':>11}{'echoes saved':>14}")
R["triage"]["to_capture"] = {}
for frac in (0.25, 0.50, 0.90):
    need = frac * total_pos
    ka = int(np.searchsorted(found_ai, need)) + 1
    kr = int(np.ceil(need / prev))
    R["triage"]["to_capture"][f"{int(frac*100)}%"] = dict(
        echoes_ai=ka, echoes_standard=min(kr, n), frac_ai=float(ka / n), frac_standard=float(min(kr, n) / n))
    print(f"  {int(frac*100):7d}%{100*ka/n:11.1f}%{100*min(kr,n)/n:10.1f}%{max(0,min(kr,n)-ka):13,}")
R["triage"]["curve_ai"] = found_ai[::100].tolist()

# ------------------------------------------------------- C. PPV / yield at fixed sensitivity
print("\n[C] operating points on the composite (MIMIC prevalence "
      f"{100*prev:.1f}%)")
fpr, tpr, thr = roc_curve(y, p_raw)
R["operating_points"] = {}
print(f"  {'sens':>6}{'thresh':>9}{'spec':>8}{'PPV':>8}{'NPV':>8}{'% referred':>12}")
for target in (0.90, 0.80, 0.70, 0.60, 0.50):
    i = int(np.argmin(np.abs(tpr - target)))
    t = thr[i]; pred = p_raw >= t
    tp = np.sum(pred & (y == 1)); fp = np.sum(pred & (y == 0))
    fn = np.sum(~pred & (y == 1)); tn = np.sum(~pred & (y == 0))
    ppv = tp / max(tp + fp, 1); npv = tn / max(tn + fn, 1); spec = tn / max(tn + fp, 1)
    R["operating_points"][f"sens_{int(target*100)}"] = dict(threshold=float(t), sens=float(tpr[i]),
        spec=float(spec), ppv=float(ppv), npv=float(npv), frac_referred=float(pred.mean()))
    print(f"  {100*tpr[i]:5.1f}%{t:9.3f}{100*spec:7.1f}%{100*ppv:7.1f}%{100*npv:7.1f}%{100*pred.mean():11.1f}%")

# projected PPV across prevalences, comparable to Poterucha Nature Table 3
print("\n  projected PPV if applied where prevalence differs (fixed sens/spec):")
print(f"  {'prev':>6}" + "".join(f"{f'sens {s}%':>11}" for s in (90, 70, 50)))
R["ppv_by_prevalence"] = {}
for pv in (0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.30):
    line, d = f"  {100*pv:5.1f}%", {}
    for s in (90, 70, 50):
        op = R["operating_points"][f"sens_{s}"]
        se, sp = op["sens"], op["spec"]
        ppv = se * pv / (se * pv + (1 - sp) * (1 - pv))
        d[f"sens_{s}"] = float(ppv); line += f"{100*ppv:10.1f}%"
    R["ppv_by_prevalence"][f"{pv}"] = d
    print(line)

json.dump(R, open(os.path.join(args.out, "triage.json"), "w"), indent=2)
print("\nwrote", os.path.join(args.out, "triage.json"))
