# How to Publish This Repository (GitHub + Zenodo)

This folder is already a git repo with a clean first commit and a `.gitignore` that **excludes all
patient-level/credentialed data**. Follow these steps to publish it and mint a citable DOI.

> ⚠️ Before pushing: run `git status` and confirm NO `.csv`, `.npy`, `.dat`, `.hea`, or `ecg_needed/`
> files are listed. The `.gitignore` blocks them, but verify — MIMIC-IV is credentialed data and must
> never be public.

## Prerequisites
- A GitHub account.
- Git installed (`git --version`).
- Optional: GitHub CLI (`brew install gh`, then `gh auth login`) — makes step 2 one command.

## Step 1 — (already done locally) verify the commit
```bash
cd ~/Desktop/RESEARCH/echonext-mimic-validation
git log --oneline      # should show the initial commit
git status             # should be clean; confirm no data files tracked
```

## Step 2 — create the GitHub repo and push
**Option A — GitHub CLI (easiest):**
```bash
gh repo create echonext-mimic-validation --public \
  --description "Independent external validation, recalibration & fairness audit of EchoNext-Mini (AI-ECG for structural heart disease) in MIMIC-IV" \
  --source . --remote origin --push
```
**Option B — manual:**
1. On github.com → New repository → name `echonext-mimic-validation`, Public, do NOT add README/license (we have them).
2. Then:
```bash
git remote add origin https://github.com/<YOUR_USERNAME>/echonext-mimic-validation.git
git branch -M main
git push -u origin main
```

## Step 3 — polish the repo page
- Add **topics**: `mimic-iv`, `ecg`, `deep-learning`, `external-validation`, `structural-heart-disease`, `cardiology`, `reproducible-research`.
- Confirm the README renders and the "Cite this repository" button appears (from `CITATION.cff`).

## Step 4 — tag a release (needed for Zenodo)
```bash
git tag -a v1.0.0 -m "Paper 1: external validation of EchoNext-Mini in MIMIC-IV"
git push origin v1.0.0
```

## Step 5 — archive to Zenodo for a DOI (what the original authors did)
1. Go to https://zenodo.org → log in with GitHub.
2. Zenodo → **Settings → GitHub** → flip the toggle **ON** for `echonext-mimic-validation`.
3. Back on GitHub → **Releases → Draft a new release** → choose tag `v1.0.0` → Publish.
4. Zenodo automatically archives the release and mints a **DOI**.
5. Copy the DOI badge from Zenodo into the top of `README.md`, and add the DOI to `CITATION.cff` and the manuscript's Data/Code Availability statement.

## Step 6 — manuscript "Code & Data Availability" wording
> Analysis code, SQL label/cohort definitions, and aggregate results are available at
> https://github.com/<user>/echonext-mimic-validation (archived at Zenodo, DOI: 10.5281/zenodo.XXXXX).
> Patient-level data are available to credentialed users via PhysioNet (MIMIC-IV, MIMIC-IV-ECG) and
> the EchoNext-Mini release; no patient-level data are redistributed here.

## If you ever add data by mistake
```bash
git rm --cached <file>        # untrack it
echo "<file>" >> .gitignore   # ignore it
git commit -m "Remove inadvertently added data file"
```
If it was already pushed, treat the credentials as exposed and rotate/scrub history (`git filter-repo`).
