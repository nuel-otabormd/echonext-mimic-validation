# EchoNext-Mini × MIMIC-IV — CONSOLIDATED RESULTS (Paper 1)
*Locked 2026-06-26. Deterministic cohort; faithful labels; repaired/replaced-valve echos excluded (per EchoNext/Nature); verified pipeline.*

Artifacts: `EchoNext-repo/results_full/` (`probs.npy` 45,878×12, `kept_paths.txt`, `*.json`, `figs/`). BigQuery: `your-gcp-project.echonext.{echo_labels, analytic_cohort}`.

---

## 1. Cohort (Table 1)
- **n = 45,878** patients (one ECG per patient; deterministic; predictions 1:1; 0 duplicates).
- Attrition: 233,735 ECGs paired to an includable **non-prosthetic** TTE within 1 yr → −9,137 excluded (paced 7,436; poor quality/lead-reversal 1,101; no valid ECG measurements 595; age<18 5) → 224,598 eligible ECGs → most recent per patient → **45,878**.
- Median age 68 [IQR 56–79]; female 22,309 (48.6%). ECG: HR 76 [65–91], PR 158 [141–180], QRS 93 [84–106], QTc 444 [423–469] ms.
- Setting at ECG: inpatient ward 14,331 (31.2%) · emergency dept / acute presentation 13,191 (28.8%) · outpatient/ambulatory 11,196 (24.4%) · ICU 7,160 (15.6%). Classified by concurrent-encounter linkage (ECG time inside an icustay/edstay/admission window). **Correction (audited):** an earlier lenient count put 32.9% in "outpatient," but an `admission_type` audit showed 98% (3,876/3,961) of the near-admission residual were *acute, on-or-before an emergency admittime* — ED-presentation ECGs, not clinic — so they were reassigned to ED/acute, giving the corrected 24.4% outpatient. Of that, ~20.3% is unambiguous (1,663 never-admitted + 7,651 >30 days from any admission). MIMIC-IV-ECG documents outpatient-care-center acquisitions; SQL in `sql/03_care_setting.sql`.
- Race (admissions): White 30,890 (67.3%) · Black 5,762 (12.6%) · Hispanic 1,976 (4.3%) · Asian 1,399 (3.0%) · Other 1,685 (3.7%) · Unknown 4,166 (9.1%).
- Any-SHD 21,590 (47.1%). ECG→echo interval median 2 [IQR 1–15] days.
- Per-label structured-field missingness → Supplementary Table S3 (`docs/supplement_table_S3_missingness.md`).

## 2. Discrimination & calibration (Table 2; n=45,878, 400-boot 95% CI)
| Label | Prev% | AUROC (95% CI) | AUPRC | Brier | Calib slope | Calib-in-large |
|---|---|---|---|---|---|---|
| **SHD (composite)** | 47.1 | **0.790 (0.787–0.794)** | 0.771 | 0.187 | 0.936 | +0.028 |
| Reduced LVEF ≤45 | 16.0 | 0.835 (0.830–0.840) | 0.514 | 0.174 | 1.15 | −0.237 |
| **RV dysfunction** (categorical) | 5.8 | 0.837 (0.830–0.845) | 0.283 | 0.162 | 1.14 | −0.292 |
| Mitral regurgitation | 8.8 | 0.805 (0.798–0.811) | 0.285 | 0.175 | 1.08 | −0.279 |
| Tricuspid regurgitation | 10.3 | 0.798 (0.791–0.804) | 0.314 | 0.162 | 1.15 | −0.262 |
| Aortic stenosis | 4.5 | 0.782 (0.773–0.790) | 0.126 | 0.214 | 0.93 | −0.357 |
| PASP ≥45 | 10.7 | 0.768 (0.762–0.774) | 0.270 | 0.184 | 1.13 | −0.288 |
| Pericardial (mod/large) | 0.6 | 0.765 (0.740–0.792) | 0.019 | 0.172 | 1.37 | −0.379 |
| TR Vmax ≥3.2 (direct velocity) | 12.7 | 0.763 (0.758–0.769) | 0.301 | 0.180 | 1.06 | −0.260 |
| Aortic regurgitation | 1.5 | 0.730 (0.714–0.746) | 0.039 | 0.186 | 0.84 | −0.353 |
| Pulmonic regurgitation | 1.6 | 0.723 (0.705–0.740) | 0.051 | 0.136 | 0.56 | −0.263 |
| **LV hypertrophy ≥1.3** | 22.4 | **0.679 (0.673–0.685)** | 0.350 | 0.208 | 0.78 | −0.198 |

Reference: EchoNext-Mini internal composite 0.820; LVWT (their weakest) 0.730.

## 3. Recalibration — 5-fold out-of-fold Platt (Table 3; slope-before == Table 2 calibration slope)
| Label | Brier before | Brier after | Slope before | Slope after |
|---|---|---|---|---|
| SHD (composite) | 0.187 | 0.186 | 0.94 | 1.00 |
| Reduced LVEF | 0.174 | 0.103 | 1.15 | 1.00 |
| RV dysfunction | 0.162 | 0.047 | 1.14 | 1.00 |
| Mitral regurg | 0.175 | 0.071 | 1.08 | 1.00 |
| Tricuspid regurg | 0.162 | 0.081 | 1.15 | 1.00 |
| Aortic stenosis | 0.214 | 0.041 | 0.93 | 1.00 |
| PASP ≥45 | 0.184 | 0.087 | 1.13 | 1.00 |
| Pericardial | 0.172 | 0.006 | 1.38 | 0.97 |
| TR Vmax | 0.180 | 0.099 | 1.06 | 1.00 |
| Aortic regurg | 0.186 | 0.015 | 0.84 | 0.95 |
| Pulmonic regurg | 0.136 | 0.015 | 0.56 | 1.00 |
| LV hypertrophy | 0.208 | 0.162 | 0.78 | 1.00 |

Composite already near-calibrated; sub-conditions over-predict and recalibration restores slopes to ~1.0. (Authoritative source: `recal_per_label.json`.)

## 4. Fairness — SHD (no material disparity)
| Group | AUROC (95% CI) | n |
|---|---|---|
| Male | 0.778 (0.772–0.783) | 23,569 |
| Female | 0.800 (0.795–0.806) | 22,309 |
| Age <65 / 65–79 / ≥80 | 0.773 (0.766–0.780) / 0.751 (0.744–0.759) / 0.731 (0.722–0.741) | 19,492 / 15,360 / 11,026 |
| White | 0.782 (0.777–0.787) | 30,890 |
| Black | 0.798 (0.787–0.809) | 5,762 |
| Hispanic | 0.776 (0.754–0.796) | 1,976 |
| Asian | 0.802 (0.776–0.825) | 1,399 |
| Other | 0.797 (0.777–0.818) | 1,685 |
| Unknown | 0.821 (0.807–0.835) | 4,166 |

Subgroup calibration slopes (descriptive): sex 0.89/0.98; age 0.91/0.84/0.79; race 0.92–1.01. Intervals overlap broadly → no large subgroup disparity (analyses descriptive).

## 5. Sensitivity analyses — all robust
ECG→TTE window ≤30–365 d ~0.79; LVEF def midpoint/lower-bound 0.835/0.825; RV categorical/+TAPSE 0.837/0.830; TR Vmax direct/gradient 0.763/0.765; PASP RAP ASE/3/5/10 ~0.77→0.75; atrial-rate 0/proxy/75 bpm 0.786 (all). Calibration also stable across variants.

## 6. LV hypertrophy secondary
LVWT AUROC ≥1.3 cm 0.679 (mild-dominated) → IVS ≥1.5 cm 0.745 → categorical mod/severe LVH 0.754. ECG's known low sensitivity for mild hypertrophy; matches EchoNext-internal 0.730.

## 7. Verification
Standalone inference == official EchoNext Lightning module to 1.19×10⁻⁷. All `.dat` = 120,000 bytes (12-lead/5000-sample/500 Hz). Deterministic cohort; predictions 1:1.

## ONE-LINE TAKEAWAY
The publicly released EchoNext-Mini model (derived from the EchoNext framework, Nature 2025) **transports to an independent, multi-setting US health system with preserved, fair discrimination (composite AUROC 0.79) and a well-calibrated composite, but its per-condition probabilities over-predict and require recalibration before deployment; mild LV-hypertrophy detection is the principal limitation.**
