"""Location configuration for the analysis pipeline.

Every path used by this repository is supplied through an environment variable, so that no
machine-specific location appears in the source. Set these once per session:

    export ECHONEXT_WORK=/path/to/working/directory
    export ECHONEXT_MODEL=/path/to/echonext_multilabel_minimodel
    export ECHONEXT_BENCHMARK=/path/to/echonext/1.1.1      # only for run_benchmark.py

ECHONEXT_WORK is a writable directory holding the credentialed inputs and the generated outputs:

    $ECHONEXT_WORK/
        cohort_oneperpt_full.csv     exported by sql/04 query (A)
        subject_race.csv             exported by sql/04 query (B)
        waveforms/                   MIMIC-IV-ECG records, mirroring the PhysioNet layout
        predictions/                 written by run_inference.py and run_benchmark.py

ECHONEXT_MODEL is the released EchoNext-Mini model directory containing weights.pt and
waveform_normalization_params.json.

ECHONEXT_BENCHMARK is the PhysioNet EchoNext release directory containing the benchmark
waveform and tabular arrays and echonext_metadata_100k.csv.

None of these directories may be inside a cloud-synchronised folder: MIMIC-IV and the EchoNext
release are credentialed resources whose data use agreements prohibit redistribution.
"""
import os
import sys


def _require(var, description):
    value = os.environ.get(var)
    if not value:
        sys.exit(f"Environment variable {var} is not set.\n"
                 f"  It must point to {description}.\n"
                 f"  See the Setup section of README.md.")
    path = os.path.abspath(os.path.expanduser(value))
    if not os.path.isdir(path):
        sys.exit(f"{var} is set to {path}, which does not exist.")
    return path


def work():
    return _require("ECHONEXT_WORK", "a writable working directory for inputs and outputs")


def model():
    return _require("ECHONEXT_MODEL", "the released EchoNext-Mini model directory")


def benchmark():
    return _require("ECHONEXT_BENCHMARK", "the PhysioNet EchoNext release directory")


def cohort_csv():
    return os.path.join(work(), "cohort_oneperpt_full.csv")


def race_csv():
    return os.path.join(work(), "subject_race.csv")


def waveform_dir():
    """Directory holding the MIMIC-IV-ECG record tree (files/pXXXX/pXXXXXXXX/sXXXXXXXX/XXXXXXXX).

    Defaults to <ECHONEXT_WORK>/waveforms, but ECHONEXT_WAVEFORMS overrides it. The waveforms are
    bulky and credentialed, so they often live on a different volume from the working directory;
    forcing them under it would mean copying 5-6 GB or symlinking around the problem.
    """
    override = os.environ.get("ECHONEXT_WAVEFORMS")
    if override:
        path = os.path.abspath(os.path.expanduser(override))
        if not os.path.isdir(path):
            sys.exit(f"ECHONEXT_WAVEFORMS is set to {path}, which does not exist.")
        return path
    return os.path.join(work(), "waveforms")


def predictions_dir():
    d = os.path.join(work(), "predictions")
    os.makedirs(d, exist_ok=True)
    return d


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def results_dir():
    d = os.path.join(repo_root(), "results")
    os.makedirs(d, exist_ok=True)
    return d
