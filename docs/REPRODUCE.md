# Reproducing the analysis

Approximate runtimes are for a ten-core laptop. All commands assume the environment variables in
the Setup section of `README.md` are set.

## Step 0 — Environment

```bash
pip install -r requirements.txt
export ECHONEXT_WORK=/path/to/working/directory
export ECHONEXT_MODEL=/path/to/echonext_multilabel_minimodel
export ECHONEXT_BENCHMARK=/path/to/echonext/1.1.1
mkdir -p "$ECHONEXT_WORK"/{waveforms,predictions}
```

`pytorch_lightning` is required only by `equivalence_test.py`, which compares against the official
Lightning module. Every other script runs without it.

## Step 1 — Labels, cohort, care setting  (BigQuery, ~2 min)

Replace the placeholder project, then run in order. Each script depends on the previous one.

```bash
sed -i '' 's/your-gcp-project/YOUR_PROJECT/g' sql/*.sql    # GNU sed: sed -i 's/.../.../g'
bq query --use_legacy_sql=false < sql/01_echo_labels.sql
bq query --use_legacy_sql=false < sql/02_analytic_cohort.sql
bq query --use_legacy_sql=false < sql/03_care_setting.sql
```

## Step 2 — Export the two CSVs  (~1 min)

`sql/04_export_for_analysis.sql` contains two queries. Run them separately and save each:

- query (A) → `$ECHONEXT_WORK/cohort_oneperpt_full.csv`
- query (B) → `$ECHONEXT_WORK/subject_race.csv`

Query (A) returns one row per patient with the model inputs, all twelve labels, the alternative
label definitions, the per-label field-availability indicators, care setting and acquisition
metadata. It replaces the two separate exports used in earlier versions, so that every analysis
reads one label source.

## Step 3 — Waveforms  (~13 GB, time depends on bandwidth)

```bash
python code/s3_download.py
```

Every `.dat` file must be exactly 120,000 bytes. The script verifies this.

## Step 4 — Verify the implementation  (~1 min)

```bash
python code/equivalence_test.py            # requires pytorch_lightning
python code/equivalence_test.py --no-pl    # tabular check only, no Lightning needed
```

Both parts must report exact agreement before proceeding. If the tabular check fails, inference will
be wrong in a way the model outputs will not reveal.

## Step 5 — Inference  (MIMIC ~70 min, benchmark ~3 min)

```bash
python code/run_inference.py --threads 2
python code/run_benchmark.py
```

`run_inference.py` writes two prediction matrices from a single pass over the waveforms: the
analysis file, and a second file reproducing an earlier PR-interval convention so that its effect can
be measured rather than asserted. Records with a measurable PR interval are identical between the
two, which the script checks and reports.

Keep `--threads` low. See the note in `README.md`.

## Step 6 — Analysis and tables  (~10 min)

```bash
python code/analyze.py            # writes results/analysis.json
python code/triage_analysis.py    # writes results/triage.json
python code/make_tables.py        # writes results/tables/
```

`analyze.py` accepts `--boot` to change the number of bootstrap resamples; the published analysis
uses the default of 2,000. Reduce it for a fast check.

## Step 7 — Figures  (R)

See `code/figures/` for the plotting scripts. Figures are produced as vector PDF, which is
resolution-independent and is the preferred format for charts.

## Verifying a reproduction

`results/` in this repository contains the outputs from the published run. After completing Step 6,
compare your `results/analysis.json` against the committed copy. The pipeline is deterministic, so
values should agree exactly. Any difference indicates a divergence in the inputs, most likely an
incomplete waveform download or a different MIMIC-IV version.
