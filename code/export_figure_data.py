"""Export the tidy CSVs the figure scripts consume.

Figures are drawn in R, but the underlying quantities are computed here so that a figure can never
disagree with a table: both derive from the same predictions and the same label source. Writing the
plotting inputs to disk also means the figures can be redrawn without repeating inference.

Outputs, all in results/figure_data/:
    roc_curves.csv          Figure 2  - ROC for the composite and strongest components
    reliability.csv         Figures 3 and S1 - reliability curves, before and after prior shift
    decision_curve.csv      Figure 4a - net benefit against threshold probability
    cumulative_gain.csv     Figure 4b - diagnostic yield against proportion imaged
    output_biases.csv       Supp Fig  - final-layer bias against logit training prevalence
    acquisition.csv         Supp Fig  - composite performance by ECG acquisition setting
    cohort_flow.csv         Figure 1  - counts for the flow diagram
"""
import os, sys, csv, json
import numpy as np
from sklearn.metrics import roc_curve, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

OUT = os.path.join(paths.results_dir(), "figure_data")
os.makedirs(OUT, exist_ok=True)

LABELS = [("Reduced LVEF (<=45%)", 0, "lvef_lte_45"),
          ("LV wall thickness (>=1.3 cm)", 1, "lvwt_gte_13"),
          ("Aortic stenosis", 2, "aortic_stenosis_modsev"),
          ("Aortic regurgitation", 3, "aortic_regurg_modsev"),
          ("Mitral regurgitation", 4, "mitral_regurg_modsev"),
          ("Tricuspid regurgitation", 5, "tricuspid_regurg_modsev"),
          ("Pulmonic regurgitation", 6, "pulm_regurg_modsev"),
          ("RV dysfunction", 7, "rv_dysfunction_modsev"),
          ("Pericardial effusion", 8, "pericardial_modlarge"),
          ("Elevated PASP (>=45 mmHg)", 9, "pasp_gte_45"),
          ("Elevated TR Vmax (>=3.2 m/s)", 10, "tr_max_gte_32"),
          ("Structural heart disease", 11, "shd")]
PI_TRAIN = [0.2340, 0.2438, 0.0403, 0.0121, 0.0847, 0.1063,
            0.0083, 0.1324, 0.0287, 0.1894, 0.1034, 0.5237]

lg = lambda p: np.log(np.clip(p, 1e-9, 1 - 1e-9) / (1 - np.clip(p, 1e-9, 1 - 1e-9)))
sig = lambda z: 1.0 / (1.0 + np.exp(-z))


def dump(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(f"  {name:24s} {len(rows):6,} rows")


P = np.load(os.path.join(paths.predictions_dir(), "probs.npy")).astype(np.float64)
kept = open(os.path.join(paths.predictions_dir(), "kept_paths.txt")).read().split("\n")
coh = {r["ecg_path"]: r for r in csv.DictReader(open(paths.cohort_csv()))}
rows = [coh[p] for p in kept]
print(f"n = {len(rows):,}\nwriting to {OUT}")

# ---------------------------------------------------------------- Figure 2: ROC curves
out = []
for name, j, col in [LABELS[11], LABELS[0], LABELS[7]]:      # composite, LVEF, RV dysfunction
    y = np.array([int(r[col]) for r in rows])
    fpr, tpr, _ = roc_curve(y, P[:, j])
    step = max(1, len(fpr) // 2000)                          # thin for plotting; curve unchanged
    a = roc_auc_score(y, P[:, j])
    for f, t in zip(fpr[::step], tpr[::step]):
        out.append([name, f"{a:.3f}", f"{f:.5f}", f"{t:.5f}"])
dump("roc_curves.csv", ["label", "auroc", "fpr", "tpr"], out)

# ------------------------------------------- Figure 3: reliability, before and after prior shift
out = []
for name, j, col in LABELS:            # all twelve; figure scripts subset as needed
    y = np.array([int(r[col]) for r in rows])
    for variant, p in [("As released", P[:, j]),
                       ("After prior shift", sig(lg(P[:, j]) + lg(PI_TRAIN[j])))]:
        edges = np.quantile(p, np.linspace(0, 1, 11))
        edges[0], edges[-1] = -np.inf, np.inf
        for k in range(10):
            m = (p >= edges[k]) & (p < edges[k + 1])
            if m.sum() > 20:
                out.append([name, variant, int(m.sum()),
                            f"{p[m].mean():.5f}", f"{y[m].mean():.5f}"])
dump("reliability.csv", ["label", "variant", "n", "predicted", "observed"], out)

# ------------------------------------------------------ Figure 4: decision curve + cumulative gain
T = json.load(open(os.path.join(paths.results_dir(), "triage.json")))
dc = T["decision_curve"]
dump("decision_curve.csv", ["threshold", "strategy", "net_benefit"],
     [[t, s, f"{v:.6f}"] for s, key in [("Model", "raw"), ("Model, prior shift", "prior_shift"),
                                        ("Image all", "treat_all")]
      for t, v in zip(dc["thresholds"], dc[key])])

y = np.array([int(r["shd"]) for r in rows]); p = P[:, 11]
order = np.argsort(-p); gain = np.cumsum(y[order]); tot = y.sum(); n = len(y)
out = []
for k in range(max(1, n // 500), n + 1, max(1, n // 500)):
    out.append([f"{k/n:.4f}", k, f"{gain[k-1]/tot:.5f}", f"{y.mean()*k/tot:.5f}", f"{gain[k-1]/k:.5f}"])
dump("cumulative_gain.csv",
     ["proportion_imaged", "n_studies", "yield_model", "yield_unprioritised", "ppv"], out)

# --------------------------------------- Supplementary: final-layer biases vs training prevalence
try:
    import torch
    ck = torch.load(os.path.join(paths.model(), "weights.pt"), map_location="cpu", weights_only=False)
    bias = ck["model"]["output.bias"].numpy()
    dump("output_biases.csv", ["label", "train_prevalence", "logit_train_prevalence", "output_bias"],
         [[nm, f"{PI_TRAIN[j]:.4f}", f"{np.log(PI_TRAIN[j]/(1-PI_TRAIN[j])):.4f}", f"{bias[j]:.5f}"]
          for nm, j, _ in LABELS])
except Exception as e:
    print(f"  [skipped output_biases.csv: {e}]")

# ------------------------------------------------- Supplementary: performance by acquisition setting
A = json.load(open(os.path.join(paths.results_dir(), "analysis.json")))
acq = A["subgroups"].get("ECG acquisition", {})
dump("acquisition.csv", ["setting", "n", "prevalence", "auroc", "ci_low", "ci_high", "slope"],
     [[k, m["n"], f"{m['prev']:.4f}", f"{m['auroc']:.4f}",
       f"{m['auroc_ci'][0]:.4f}", f"{m['auroc_ci'][1]:.4f}", f"{m['slope']:.3f}"]
      for k, m in acq.items()])

# ----------------------------------------------------------------- Figure 1: cohort flow counts
# NOT written here. The flow diagram needs counts from stages that exist only upstream of the
# predictions (source dataset totals, echocardiographic exclusions, ECGs excluded before the cohort
# was formed), none of which this script can see. sql/05_cohort_flow.sql emits the whole flow,
# including its own reconciliation rows, straight to results/figure_data/cohort_flow.csv.
#
# What this script CAN see is checked against that file, so the two cannot disagree.
flow_path = os.path.join(OUT, "cohort_flow.csv")
if os.path.exists(flow_path):
    flow = {r["stage"]: int(r["n"]) for r in csv.DictReader(open(flow_path))}
    here_ = {"cohort": len(rows), "cohort_shd": int(y.sum()),
             "cohort_pr_missing": sum(1 for r in rows if r["pr_missing"].lower() == "true")}
    bad = {k: (v, flow[k]) for k, v in here_.items() if k in flow and flow[k] != v}
    if bad:
        raise SystemExit(f"cohort_flow.csv disagrees with the predictions: {bad}\n"
                         f"  Re-run sql/05_cohort_flow.sql.")
    print(f"  cohort_flow.csv         checked, {len(here_)} counts agree")
else:
    print("  [cohort_flow.csv absent: run sql/05_cohort_flow.sql before drawing Figure 1]")
print("done")
