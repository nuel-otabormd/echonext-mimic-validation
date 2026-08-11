"""EchoNext-Mini inference on the MIMIC-IV cohort - THREE VARIANTS.

Runs the frozen released model over the analytic cohort and writes THREE prediction matrices from a
single pass over the waveforms:

  probs.npy     CORRECTED tabular features. Missing PR interval is filled with RAW 0 before scaling,
                matching the released rule (Hughes et al., NEJM AI 2026, p5; preprocess.py:29,35;
                Nature Supplementary Methods, Model Design). This is the analysis file.

  probs_pr_imputed.npy   A missing PR interval routed to the median imputer instead, becoming
                +0.158 rather than -2.474 on the scaled input. This quantifies what the fill rule is
                worth per label and per subgroup. PR interval is unmeasurable in 15.3% of the
                cohort, rising to 25.1% in intensive care.

  probs_atrial_median.npy   Atrial rate routed to the median imputer rather than filled with raw 0.
                MIMIC-IV-ECG has no atrial-rate field, so this predictor is 100% absent and its
                value is set entirely by the fill rule. This variant bounds how much that choice
                can matter; it is the atrial-rate sensitivity analysis.

All three variants share the identical waveform tensor, so any difference between them is attributable
solely to the tabular input. Verified bit-exact against the official Lightning module and the
official preprocess.tabular_transformer() by code/equivalence_test.py.

Scaler and imputer constants are read from code/tabular_transform_params.json, not from the released
joblib, so inference carries no scikit-learn version dependency.
"""
import os, sys, json, csv, time, argparse
import numpy as np, torch, wfdb, scipy.signal
# (multiprocessing removed - see note in main())

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths
MDIR = paths.model()
WAVE = paths.waveform_dir()
sys.path.insert(0, os.environ.get("ECHONEXT_CRADLENET", os.path.dirname(MDIR.rstrip("/"))))

MODEL_LEADS = ['I','II','III','aVR','aVL','aVF','V1','V2','V3','V4','V5','V6']
LABELS = ['lvef_lte_45','lvwt_gte_13','aortic_stenosis','aortic_regurg','mitral_regurg',
          'tricuspid_regurg','pulm_regurg','rv_dysfunction','pericardial','pasp_gte_45',
          'tr_max_gte_32','shd']

PRM = json.load(open(os.path.join(MDIR, "waveform_normalization_params.json")))
TP = json.load(open(os.path.join(HERE, "tabular_transform_params.json")))
MEAN = np.asarray(TP['scaler_mean']); SCALE = np.asarray(TP['scaler_scale'])
MEDIAN = np.asarray(TP['imputer_median_scaled'])


def fnum(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else np.nan
    except Exception:
        return np.nan


def load_waveform(path):
    """WFDB -> (2500,12) model lead order, raw ADC, 500->250 Hz, per-lead baseline removed."""
    rec = wfdb.rdrecord(os.path.join(WAVE, path), physical=False)
    sig = rec.d_signal.astype(np.float64)
    idx = {n: i for i, n in enumerate(rec.sig_name)}
    sig = sig[:, [idx[l] for l in MODEL_LEADS]][::2, :]        # reorder + decimate
    out = np.zeros((12, sig.shape[0]))
    d = sig.T
    for lead in range(12):
        b = scipy.signal.medfilt(d[lead], int(round(0.2 * 250)) + 1)
        b = scipy.signal.medfilt(b,       int(round(0.6 * 250)) + 1)
        out[lead] = d[lead] - b
    return out.T                                               # (2500,12)


def _safe_load(path):
    try:
        return path, load_waveform(path)
    except Exception as e:
        return path, None


def norm_batch(wf):
    d = np.transpose(wf, (0, 2, 1)).copy()                     # (N,12,2500)
    for L in range(12):
        d[:, L, :] = (np.clip(d[:, L, :], PRM['lowerbound'][L], PRM['upperbound'][L])
                      - PRM['mean'][L]) / PRM['std'][L]
    return np.transpose(d, (0, 2, 1))[:, None, :, :]           # (N,1,2500,12)


def tabular(rows, fix_pr, fill_atrial=True):
    """7 features: [sex] + scaled [age, vent, atrial, pr, qrs, qtc].
    Released rule: atrial_rate and pr_interval -> RAW 0 before scaling; others -> median after.
    fix_pr=False routes a missing PR interval to the median imputer instead, which quantifies
    what the fill rule is worth on this cohort.

    fill_atrial=False routes atrial rate to the median imputer instead. MIMIC-IV-ECG carries no
    atrial-rate field at all, so this predictor is 100% absent and its value is decided entirely by
    the fill rule; the two settings bound how much that choice can matter.
    """
    x = np.array([[fnum(r['age_at_ecg']), fnum(r['ventricular_rate']), np.nan,
                   fnum(r['pr_interval']), fnum(r['qrs_duration']), fnum(r['qt_corrected'])]
                  for r in rows])
    if fill_atrial:
        x[:, 2] = np.nan_to_num(x[:, 2], nan=0.0)              # atrial rate absent in MIMIC -> 0
    if fix_pr:
        x[:, 3] = np.nan_to_num(x[:, 3], nan=0.0)              # released rule
    xs = (x - MEAN) / SCALE
    nan = np.isnan(xs)
    xs[nan] = np.take(MEDIAN, np.where(nan)[1])
    sex = np.array([[1.0 if r['gender'].strip().upper() == 'M' else 0.0] for r in rows])
    return np.concatenate([sex, xs], axis=1)


def main():
  # NOTE: this guard is load-bearing on macOS. multiprocessing defaults to the "spawn" start
  # method, which re-imports the main module inside every worker. Without it each worker re-ran the
  # cohort scan, the model load, and then tried to create its own Pool.
  ap = argparse.ArgumentParser()
  ap.add_argument("--cohort", default=None)
  ap.add_argument("--out_dir", default=None)
  ap.add_argument("--batch", type=int, default=256)
  ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2))
  ap.add_argument("--threads", type=int, default=2, help="torch CPU threads; keep LOW on a busy machine")
  ap.add_argument("--limit", type=int, default=0, help="debug: only first N records")
  args = ap.parse_args()
  args.cohort = args.cohort or paths.cohort_csv()
  args.out_dir = args.out_dir or paths.predictions_dir()
  os.makedirs(args.out_dir, exist_ok=True)

  # ---------------------------------------------------------------------------------- cohort
  rows = list(csv.DictReader(open(args.cohort)))
  rows = [r for r in rows
          if os.path.exists(os.path.join(WAVE, r['ecg_path'] + '.dat'))
          and os.path.exists(os.path.join(WAVE, r['ecg_path'] + '.hea'))]
  if args.limit:
      rows = rows[:args.limit]
  n_pr = sum(1 for r in rows if r['pr_missing'].lower() == 'true')
  print(f"records: {len(rows):,}   PR missing: {n_pr:,} ({100*n_pr/len(rows):.1f}%)", flush=True)

  # ------------------------------------------------------------------------------------ model
  from cradlenet.models.resnet1d_tabular import ResNet1dWithTabular
  ck = torch.load(os.path.join(MDIR, "weights.pt"), map_location="cpu", weights_only=False)
  model = ResNet1dWithTabular(len_tabular_feature_vector=7, filter_size=16, num_classes=12)
  model.load_state_dict(ck["model"])          # strict, as upstream ecg_tabular.py
  model.eval()
  # Deliberately modest. Setting this to cpu_count-1 over-subscribes an already-busy machine and
  # causes context-switch thrashing: on a 10-core box under load ~11, a 9-thread setting ran at
  # ~2.9 s/record with the process showing 0% CPU (constantly descheduled), versus ~40 ms/record
  # for the same primitives measured in isolation. Fewer threads is dramatically faster here.
  torch.set_num_threads(args.threads)

  # Sequential by design. Waveform loading is ~41 ms/record (wfdb 3.8, medfilt 37.4), so the full
  # cohort takes ~30-40 min, matching the original run. An earlier version used multiprocessing.Pool,
  # which DEADLOCKS on macOS: the default start method is "spawn", workers re-import the module, and
  # that interacts badly with an already-initialised torch. Not worth the fragility for a 2x gain in
  # a script other people are meant to reproduce.
  # Three tabular variants share ONE waveform pass. Waveform loading dominates runtime, so the
  # extra forward passes are nearly free compared with running the script three times.
  P_fix, P_v1, P_atr, kept, failed = [], [], [], [], []
  t0 = time.time()
  for s in range(0, len(rows), args.batch):
      chunk = rows[s:s + args.batch]
      wf, good = [], []
      for r in chunk:
          try:
              wf.append(load_waveform(r['ecg_path'])); good.append(r)
          except Exception:
              failed.append(r['ecg_path'])
      if not good:
          continue
      X = torch.tensor(norm_batch(np.stack(wf)), dtype=torch.float32)
      with torch.no_grad():
          P_fix.append(torch.sigmoid(model((X, torch.tensor(tabular(good, True),  dtype=torch.float32)))).numpy())
          P_v1.append( torch.sigmoid(model((X, torch.tensor(tabular(good, False), dtype=torch.float32)))).numpy())
          P_atr.append(torch.sigmoid(model((X, torch.tensor(tabular(good, True, fill_atrial=False),
                                                            dtype=torch.float32)))).numpy())
      kept += [r['ecg_path'] for r in good]
      done = len(kept)
      el = time.time() - t0
      print(f"  {done:,}/{len(rows):,}  {el/60:.1f} min elapsed, "
            f"~{el/done*(len(rows)-done)/60:.1f} min left", flush=True)

  probs = np.concatenate(P_fix); probs_pr_imputed = np.concatenate(P_v1)
  probs_atr = np.concatenate(P_atr)
  np.save(os.path.join(args.out_dir, "probs.npy"), probs)
  np.save(os.path.join(args.out_dir, "probs_pr_imputed.npy"), probs_pr_imputed)
  np.save(os.path.join(args.out_dir, "probs_atrial_median.npy"), probs_atr)
  open(os.path.join(args.out_dir, "kept_paths.txt"), "w").write("\n".join(kept))
  if failed:
      open(os.path.join(args.out_dir, "failed_paths.txt"), "w").write("\n".join(failed))

  # ------------------------------------------------------------------ what the PR defect cost
  prmiss = np.array([r['pr_missing'].lower() == 'true'
                     for r in rows if r['ecg_path'] in set(kept)])
  d = np.abs(probs - probs_pr_imputed)
  print(f"\ndone in {(time.time()-t0)/60:.1f} min | kept {len(kept):,} | failed {len(failed)}")
  print(f"\nPR-interval defect, effect on predicted probability (n affected = {int(prmiss.sum()):,})")
  print(f"  {'label':18s}{'mean|delta| affected':>22}{'max|delta|':>12}{'mean prob (fixed)':>19}")
  for j, nm in enumerate(LABELS):
      print(f"  {nm:18s}{d[prmiss, j].mean():22.4f}{d[:, j].max():12.4f}{probs[:, j].mean():19.4f}")
  print(f"\nunaffected records max|delta| (sanity, should be 0): {d[~prmiss].max():.2e}")
  print("wrote", args.out_dir)


if __name__ == "__main__":
    main()
