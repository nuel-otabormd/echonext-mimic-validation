# Supplementary Table S1 — Label Definitions (EchoNext → MIMIC-IV harmonization)

All labels derived from MIMIC-IV-ECHO **structured** fields (`structured_measurement`, TTE only), not free text. Threshold = EchoNext. Missing structured field → negative.

| # | Condition | EchoNext definition | MIMIC primary definition | Sensitivity analyses | Prevalence % (MIMIC / EchoNext-Mini)³ |
|---|---|---|---|---|---|
| 1 | Reduced LVEF | numeric LVEF ≤45% | best-available quantitative LVEF (biplane→3D→visual-range midpoint) ≤45% | midpoint-only; lower-bound | 16.0% / 18.0% |
| 2 | LV hypertrophy | max(IVS, posterior wall) ≥1.3 cm | max(`septal_thickness`, **inferolateral** wall) ≥1.3 cm¹ | septal ≥1.5 cm; categorical moderate-or-severe LVH⁴ | 22.4% / 18.8% |
| 3 | Aortic stenosis | moderate-or-greater | `aortic_stenosis` ∈ {mod, mod-severe, severe, very severe} | — | 4.5% / 5.4% |
| 4 | Aortic regurgitation | moderate-or-greater | `aortic_regurg` ≥ moderate (mild-mod = negative) | — | 1.5% / 1.2% |
| 5 | Mitral regurgitation | moderate-or-greater | `mitral_regurg` ≥ moderate (mild-mod = negative) | — | 8.8% / 6.5% |
| 6 | Tricuspid regurgitation | moderate-or-greater | `tricuspid_regurg` ≥ moderate (incl. torrential) | — | 10.3% / 7.0% |
| 7 | Pulmonic regurgitation | moderate-or-greater | `pulm_regurg` ∈ {mod/severe, severe, significant} | — | 1.6% / 0.4% |
| 8 | RV systolic dysfunction | categorical moderate/severe | **categorical `rv_function`** moderate/severe (incl. "depressed") | + TAPSE <1.7 cm | 5.8% / 8.0% |
| 9 | Pericardial effusion | moderate or large | moderate / moderate-large / large (small & below = negative) | tamponade descriptors | 0.6% / 1.3% |
| 10 | Elevated PASP | numeric PASP ≥45 mmHg | TR gradient + IVC-derived RAP ≥45² | fixed RAP 3/5/10 mmHg | 10.7% / 12.9% |
| 11 | Elevated TR Vmax | direct TR Vmax ≥3.2 m/s | **direct `tr_velocity` ≥3.2 m/s** | derived gradient `tr_mmhg`≥40.96 | 12.7% / 6.5% |
| 12 | Any SHD (composite) | any of 1–11 | GREATEST(1–11); model output index 11 | — | 47.1% / 43.3% |

¹ MIMIC-IV-ECHO provides septal and inferolateral LV wall thickness but **no distinct numeric posterior-wall/LVPW field**; inferolateral is anatomically adjacent but not identical to the posterior wall.
² MIMIC-IV-ECHO exposes **no single numeric PASP field**; RAP estimated from the structured IVC field per American Society of Echocardiography categories (0–5→3, 5–10→8, 10–15→13, >15/dilated→20 mmHg; Rudski et al., J Am Soc Echocardiogr 2010;23:685–713); missing/non-visualized IVC → RAP = 3 mmHg.
³ Both columns are computed on the **most-recent ECG per patient** (MIMIC n=45,878; EchoNext-Mini n=36,286), so the two cohorts are compared on the same analytic unit. The per-ECG prevalences reported by Hughes et al. over all 100,000 EchoNext-Mini ECGs are higher (e.g., any SHD 52.2%, reduced LVEF 24.0%) because patients with repeat ECGs carry more disease.
⁴ Secondary higher-grade hypertrophy outcomes (septal ≥1.5 cm; categorical moderate-or-severe LVH) reported in Supplementary Table S2 ("Secondary LV wall-thickness analyses").

**Inclusion (EchoNext):** echo must report LVEF AND ≥1 valve finding. **Valve severity logic:** moderate / mod-severe / severe = positive; trace / mild / physiologic = negative; mild-moderate (1–2+) = negative; unquantified "present / can't qualify" = negative. **Exclusions:** age <18; missing age/sex; ventricular-paced; poor-quality/lead-reversal/artifact; all ECG measurements missing; **echocardiograms with repaired or replaced (prosthetic) heart valves** — matching EchoNext/Nature, which excluded these (identified via valve-replacement-structure and leaflet fields).
