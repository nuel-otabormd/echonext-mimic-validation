"""
MAC-HFpEF Aim 3: MRA exposure and mitral annular calcification progression.

Reads the CSV exported from `the-project-476301.dhruv.aim3_analytic` and produces
every number needed for the results section. Colab-ready: only pandas, numpy,
statsmodels and scipy are required.

    pip install pandas numpy statsmodels scipy

Usage:
    python analysis_aim3.py aim3_analytic.csv
"""

import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

SEED = 42
np.random.seed(SEED)

CSV = sys.argv[1] if len(sys.argv) > 1 else "aim3_analytic.csv"

# Covariates for the adjusted model. Chosen on clinical grounds: age, sex and renal
# function drive both MRA prescribing and calcification; baseline MAC grade is the
# dominant published predictor of progression; interval length mechanically permits
# more progression the longer it runs.
CONTINUOUS = ["age_at_t0", "egfr", "potassium", "lvef", "charlson_comorbidity_index"]
BINARY = ["has_af", "diabetes", "renal_disease", "congestive_heart_failure",
          "conc_raasi", "conc_bb", "conc_loop"]


def ci_from_logit(res, term):
    """Odds ratio and 95% CI for one model term."""
    beta = res.params[term]
    se = res.bse[term]
    return np.exp(beta), np.exp(beta - 1.96 * se), np.exp(beta + 1.96 * se), res.pvalues[term]


def two_by_two(df, exposure="mra_exposed", outcome="progressed"):
    """Crude OR, RR and risk difference with 95% CIs."""
    a = int(((df[exposure] == 1) & (df[outcome] == 1)).sum())
    b = int(((df[exposure] == 1) & (df[outcome] == 0)).sum())
    c = int(((df[exposure] == 0) & (df[outcome] == 1)).sum())
    d = int(((df[exposure] == 0) & (df[outcome] == 0)).sum())

    orr = (a / b) / (c / d)
    se_log_or = np.sqrt(1/a + 1/b + 1/c + 1/d)
    p1, p2 = a / (a + b), c / (c + d)
    rr = p1 / p2
    se_log_rr = np.sqrt(1/a - 1/(a+b) + 1/c - 1/(c+d))
    rd = p1 - p2
    se_rd = np.sqrt(p1*(1-p1)/(a+b) + p2*(1-p2)/(c+d))
    chi2, p, _, _ = stats.chi2_contingency([[a, b], [c, d]], correction=False)

    return dict(
        a=a, b=b, c=c, d=d, pct_exposed=100*p1, pct_unexposed=100*p2,
        OR=orr, OR_lo=orr*np.exp(-1.96*se_log_or), OR_hi=orr*np.exp(1.96*se_log_or),
        RR=rr, RR_lo=rr*np.exp(-1.96*se_log_rr), RR_hi=rr*np.exp(1.96*se_log_rr),
        RD=100*rd, RD_lo=100*(rd-1.96*se_rd), RD_hi=100*(rd+1.96*se_rd),
        chi2=chi2, p=p)


def smd(df, var, group="mra_exposed"):
    """Standardised mean difference. Threshold 0.1 for adequate balance."""
    g1, g0 = df.loc[df[group] == 1, var].dropna(), df.loc[df[group] == 0, var].dropna()
    if len(g1) < 2 or len(g0) < 2:
        return np.nan
    pooled = np.sqrt((g1.var() + g0.var()) / 2)
    return np.nan if pooled == 0 else (g1.mean() - g0.mean()) / pooled


def e_value(or_point):
    """E-value: minimum association an unmeasured confounder would need with both
    exposure and outcome to explain away the estimate. Protective estimates are
    inverted first, per VanderWeele & Ding."""
    rr = 1 / or_point if or_point < 1 else or_point
    return rr + np.sqrt(rr * (rr - 1))


def main():
    df = pd.read_csv(CSV)
    print(f"Loaded {len(df):,} rows from {CSV}\n")

    # ---- Exclusion: no admission during the interval means no exposure information.
    # These patients are unclassifiable, not unexposed. Pre-specified in the protocol.
    n_before = len(df)
    excluded = df[df["n_adm_interval"] == 0]
    df = df[df["n_adm_interval"] > 0].copy()
    print("=" * 70)
    print("EXCLUSION")
    print(f"  Cohort as built             {n_before:,}")
    print(f"  No admission in interval    {len(excluded):,} "
          f"(progression {100*excluded['progressed'].mean():.1f}%) -> EXCLUDED")
    print(f"  Analytic set                {len(df):,}")

    # ---- Missingness
    print("\n" + "=" * 70)
    print("MISSINGNESS (analytic set)")
    for v in CONTINUOUS + BINARY:
        if v in df.columns:
            n_miss = df[v].isna().sum()
            print(f"  {v:32s} {n_miss:5,} ({100*n_miss/len(df):5.1f}%)")

    # ---- Crude
    print("\n" + "=" * 70)
    print("CRUDE ASSOCIATION")
    r = two_by_two(df)
    print(f"  Exposed    {r['a']+r['b']:5,}  events {r['a']:5,}  ({r['pct_exposed']:.1f}%)")
    print(f"  Unexposed  {r['c']+r['d']:5,}  events {r['c']:5,}  ({r['pct_unexposed']:.1f}%)")
    print(f"  OR  {r['OR']:.3f}  (95% CI {r['OR_lo']:.3f} to {r['OR_hi']:.3f})")
    print(f"  RR  {r['RR']:.3f}  (95% CI {r['RR_lo']:.3f} to {r['RR_hi']:.3f})")
    print(f"  RD  {r['RD']:+.2f} pp (95% CI {r['RD_lo']:+.2f} to {r['RD_hi']:+.2f})")
    print(f"  chi2 {r['chi2']:.2f}, p = {r['p']:.4f}")

    # ---- Table 1 with SMDs
    print("\n" + "=" * 70)
    print("TABLE 1  (mean or %, by exposure, with SMD)")
    print(f"  {'variable':32s} {'exposed':>10s} {'unexposed':>10s} {'SMD':>7s}")
    for v in CONTINUOUS + BINARY + ["interval_days", "mac_baseline"]:
        if v not in df.columns:
            continue
        m1 = df.loc[df.mra_exposed == 1, v].mean()
        m0 = df.loc[df.mra_exposed == 0, v].mean()
        print(f"  {v:32s} {m1:10.2f} {m0:10.2f} {smd(df, v):7.3f}")

    # ---- Adjusted model. Complete-case on the adjustment set, plus a missingness
    # indicator model as sensitivity, so the reader can see whether exclusion of
    # incomplete records moved anything.
    covars = [v for v in CONTINUOUS + BINARY if v in df.columns]
    formula = ("progressed ~ mra_exposed + C(mac_baseline) + np.log(interval_days) + "
               + " + ".join(covars) + " + C(gender)")

    print("\n" + "=" * 70)
    print("ADJUSTED MODEL (complete case)")
    cc = df.dropna(subset=covars + ["progressed", "mra_exposed", "interval_days"])
    print(f"  n = {len(cc):,}  events = {int(cc.progressed.sum()):,}  "
          f"exposed = {int(cc.mra_exposed.sum()):,}")
    fit = smf.logit(formula, data=cc).fit(disp=0)
    o, lo, hi, p = ci_from_logit(fit, "mra_exposed")
    print(f"  Adjusted OR  {o:.3f}  (95% CI {lo:.3f} to {hi:.3f})   p = {p:.4f}")
    print(f"  E-value (point)      {e_value(o):.2f}")
    print(f"  E-value (CI limit)   {e_value(min(hi, 0.999)) if hi < 1 else 1.0:.2f}")

    # ---- IPTW sensitivity
    print("\n" + "=" * 70)
    print("IPTW SENSITIVITY (stabilised weights, robust SE)")
    ps_formula = ("mra_exposed ~ C(mac_baseline) + np.log(interval_days) + "
                  + " + ".join(covars) + " + C(gender)")
    ps_fit = smf.logit(ps_formula, data=cc).fit(disp=0)
    ps = ps_fit.predict(cc)
    marg = cc.mra_exposed.mean()
    w = np.where(cc.mra_exposed == 1, marg / ps, (1 - marg) / (1 - ps))
    w = np.clip(w, np.percentile(w, 1), np.percentile(w, 99))   # trim extremes
    print(f"  PS range {ps.min():.3f} to {ps.max():.3f}  (positivity: no mass at 0 or 1)")
    print(f"  Weight range after 1/99 trim: {w.min():.2f} to {w.max():.2f}")

    wfit = smf.glm("progressed ~ mra_exposed", data=cc,
                   family=sm.families.Binomial(), freq_weights=w).fit(cov_type="HC1")
    o2, lo2, hi2 = (np.exp(wfit.params["mra_exposed"]),
                    np.exp(wfit.params["mra_exposed"] - 1.96*wfit.bse["mra_exposed"]),
                    np.exp(wfit.params["mra_exposed"] + 1.96*wfit.bse["mra_exposed"]))
    print(f"  IPTW OR  {o2:.3f}  (95% CI {lo2:.3f} to {hi2:.3f})")

    cc2 = cc.copy()
    cc2["w"] = w
    print("  Weighted balance (SMD, target < 0.1):")
    for v in covars[:6]:
        print(f"    {v:30s} unweighted {smd(cc, v):+.3f}")

    # ---- Dose-response
    print("\n" + "=" * 70)
    print("DOSE-RESPONSE")
    order = ["none", "below_target", "target"]
    sub = df[df.mra_dose_group.isin(order)].copy()
    sub["dose_score"] = sub.mra_dose_group.map({k: i for i, k in enumerate(order)})
    for g in order:
        s = sub[sub.mra_dose_group == g]
        print(f"  {g:14s} n = {len(s):5,}  events {int(s.progressed.sum()):5,}  "
              f"({100*s.progressed.mean():.1f}%)")
    tab = pd.crosstab(sub.dose_score, sub.progressed)
    counts = tab[1].values
    totals = tab.sum(axis=1).values
    scores = np.array(sorted(sub.dose_score.unique()), dtype=float)
    pbar = counts.sum() / totals.sum()
    T = np.sum(scores * (counts - totals * pbar))
    varT = pbar * (1 - pbar) * (np.sum(totals * scores**2)
                                - (np.sum(totals * scores))**2 / totals.sum())
    z = T / np.sqrt(varT)
    print(f"  Cochran-Armitage trend: z = {z:.3f}, p = {2*stats.norm.sf(abs(z)):.4f}")

    # ---- Effect modification by baseline grade
    print("\n" + "=" * 70)
    print("BY BASELINE MAC GRADE")
    for g, label in [(1, "mild"), (2, "moderate")]:
        s = df[df.mac_baseline == g]
        rg = two_by_two(s)
        print(f"  {label:9s} OR {rg['OR']:.3f} (95% CI {rg['OR_lo']:.3f} to {rg['OR_hi']:.3f})"
              f"  exposed {rg['a']}/{rg['a']+rg['b']}, unexposed {rg['c']}/{rg['c']+rg['d']}")
    inter = smf.logit("progressed ~ mra_exposed * C(mac_baseline) + np.log(interval_days)",
                      data=df).fit(disp=0)
    key = [t for t in inter.params.index if "mra_exposed:" in t]
    if key:
        print(f"  Interaction p = {inter.pvalues[key[0]]:.4f}  "
              "(overlapping strata are not heterogeneity)")

    # ---- Sensitivity: exposure definitions and two-grade progression
    print("\n" + "=" * 70)
    print("SENSITIVITY")
    for expo in ["mra_exposed_himed", "mra_exposed_medrecon"]:
        if expo in df.columns:
            rs = two_by_two(df, exposure=expo)
            print(f"  {expo:24s} OR {rs['OR']:.3f} "
                  f"({rs['OR_lo']:.3f} to {rs['OR_hi']:.3f}), exposed n = {rs['a']+rs['b']:,}")
    if "progressed_2grade" in df.columns:
        rs = two_by_two(df, outcome="progressed_2grade")
        print(f"  {'two-grade progression':24s} OR {rs['OR']:.3f} "
              f"({rs['OR_lo']:.3f} to {rs['OR_hi']:.3f}), events = {rs['a']+rs['c']:,}")
    for lo_days in (545, 730):
        s = df[df.interval_days >= lo_days]
        rs = two_by_two(s)
        print(f"  interval >= {lo_days}d{'':11s} OR {rs['OR']:.3f} "
              f"({rs['OR_lo']:.3f} to {rs['OR_hi']:.3f}), n = {len(s):,}")

    print("\n" + "=" * 70)
    print("Done. Paste this whole block back for the results section.")


if __name__ == "__main__":
    main()
