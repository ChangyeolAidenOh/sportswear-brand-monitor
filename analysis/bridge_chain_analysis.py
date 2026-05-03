"""
Stage 7 Bridge chain analysis -- Track A1 (VARX) + Track A1' (mediation).

Entry points (selected via --stage CLI arg):
  - a1                     : VARX(2) on (korea_search_d1, global_search_d1) with CSI
                             distributed-lag exogenous; bidirectional Granger + IRF + LR
  - a1_prime               : Mediation Korea_{t-lag} -> Global (original direction).
                             Result preserved for paired comparison after sign correction.
  - a1_prime_sign_corrected: Mediation Global_{t-lag} -> Korea (sign-corrected direction
                             per advisor cascade decision post-Stage-4 sign convention
                             discovery -- see DP24).

Track A1 (Decision 3 + Option 6, advisor approved):
  - Endogenous: (korea_search_d1, global_search_d1)
  - Exogenous: CSI diff1 distributed lag {0, 4, 8, 12}, lag 0 mandatory
  - Lag selection: VAR.select_order(maxlags=13), BIC primary
  - Bidirectional Granger within VARX, joint LR test for CSI exogenous
  - IRF: orthogonalized + cumulative, Cholesky order Korea first

Track A1' (Decision 4 + advisor verdict post Step 0 + A1):
  - Primary    : trend mediation Korea_trend_{t-10w} -> Global_trend_t
  - Robustness : diff1 mediation Korea_d1_{t-10w} -> Global_d1_t
  - Bootstrap  : MovingBlockBootstrap (block=13w) + StationaryBootstrap robustness
  - 5000 iter, BCa 95% CI, joint resampling per Decision 4
  - lag* fixed at +10w (Stage 4 DTW; A3 grid will refine)

Outputs:
  - A1 : data/bridge/varx_results.{json,md}
         figures/bridge/varx_irf_orthogonalized.png
         figures/bridge/varx_irf_cumulative.png
         figures/bridge/varx_lag_selection.png
  - A1': data/bridge/mediation_bootstrap.{json,md}
         figures/bridge/mediation_distribution.png

Usage:
  python -m analysis.bridge_chain_analysis --stage a1
  python -m analysis.bridge_chain_analysis --stage a1_prime
"""

import os
import sys
import json
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from statsmodels.tsa.api import VAR
from scipy import stats as scipy_stats

import argparse
import statsmodels.api as sm
from arch.bootstrap import MovingBlockBootstrap, StationaryBootstrap

# Cosmetic: pandas SQLAlchemy notice on raw psycopg2 conn (TODO: cleanup separately)
warnings.filterwarnings("ignore", category=UserWarning, message=".*SQLAlchemy.*")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.bridge_stationarity_check import extract_data

# Constants
DATA_DIR = "data/bridge"
FIG_DIR = "figures/bridge"
JSON_PATH = os.path.join(DATA_DIR, "varx_results.json")
MD_PATH = os.path.join(DATA_DIR, "varx_results.md")
MAXLAGS = 13
CSI_LAGS = [0, 4, 8, 12]
SIGNIFICANCE = 0.05
IRF_PERIODS = 20
AIC_BIC_ESCALATION_GAP = 4

# A1'-prime (mediation) constants
MEDIATION_JSON_PATH = os.path.join(DATA_DIR, "mediation_bootstrap.json")
MEDIATION_MD_PATH = os.path.join(DATA_DIR, "mediation_bootstrap.md")
MEDIATION_FIG_PATH = os.path.join(FIG_DIR, "mediation_distribution.png")

# A1' sign-corrected (Global -> Korea direction; advisor cascade decision)
MEDIATION_SC_JSON_PATH = os.path.join(DATA_DIR, "mediation_bootstrap_sign_corrected.json")
MEDIATION_SC_MD_PATH = os.path.join(DATA_DIR, "mediation_bootstrap_sign_corrected.md")
MEDIATION_SC_FIG_PATH = os.path.join(FIG_DIR, "mediation_distribution_sign_corrected.png")
LAG_STAR = 10  # Stage 4 DTW +10.4w; A3 grid will refine
N_BOOT = 5000
BLOCK_LEN = 13  # sqrt(n) heuristic, Hall-Horowitz
SEED = 7

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "axes.grid": True,
    "grid.alpha": 0.3,
})

REPORT_LINES = []


def log(msg=""):
    print(msg)
    REPORT_LINES.append(msg)


def section(title):
    log("")
    log(f"## {title}")
    log("")


# =========================================================================
# Data preparation
# =========================================================================

def build_varx_inputs():
    """Construct endogenous (search diff1) and exogenous (CSI diff1 distributed lag)."""
    df = extract_data()

    endog = pd.DataFrame({
        "korea_d1": df["korea_search"].diff(),
        "global_d1": df["global_search"].diff(),
    })

    csi_d1 = df["csi"].diff()
    exog = pd.DataFrame(
        {f"csi_d1_l{lag}": csi_d1.shift(lag) for lag in CSI_LAGS}
    )

    combined = pd.concat([endog, exog], axis=1).dropna()
    log(f"  endog cols: {list(endog.columns)}")
    log(f"  exog cols:  {list(exog.columns)}")
    log(
        f"  effective sample: {combined.index.min().date()} ~ "
        f"{combined.index.max().date()}  ({len(combined)} weeks)"
    )

    return combined[endog.columns], combined[exog.columns]


# =========================================================================
# Lag selection (Decision 3)
# =========================================================================

def select_lag_order(endog, exog):
    """VAR.select_order(maxlags=13) reporting all four ICs. BIC primary."""
    log("")
    log("Lag selection on grid 1..13 with CSI distributed-lag exogenous...")
    model = VAR(endog, exog=exog)
    sel = model.select_order(maxlags=MAXLAGS)

    selected = {
        "aic": int(sel.aic) if sel.aic is not None else None,
        "bic": int(sel.bic) if sel.bic is not None else None,
        "hqic": int(sel.hqic) if sel.hqic is not None else None,
        "fpe": int(sel.fpe) if sel.fpe is not None else None,
    }
    log(
        f"  Selected lags  AIC={selected['aic']}  BIC={selected['bic']}  "
        f"HQIC={selected['hqic']}  FPE={selected['fpe']}"
    )

    p_primary = selected["bic"] if selected["bic"] is not None else selected["aic"]
    aic_bic_gap = abs((selected["aic"] or 0) - (selected["bic"] or 0))
    if aic_bic_gap >= AIC_BIC_ESCALATION_GAP:
        log(
            f"  [ESCALATION CANDIDATE] |AIC - BIC| = {aic_bic_gap} "
            f"(Decision 3: report both; advisor decision needed)"
        )

    return sel, selected, p_primary, aic_bic_gap


def plot_lag_selection(sel, selected, fig_path):
    """Visualize IC values across lag grid. Defensive against API drift."""
    try:
        ics = sel.ics
        fig, ax = plt.subplots(figsize=(10, 5))
        for ic_name, vals in ics.items():
            arr = np.asarray(vals, dtype=float)
            ax.plot(range(len(arr)), arr, marker="o", label=ic_name.upper())
        for ic_name, p_sel in selected.items():
            if p_sel is not None:
                ax.axvline(p_sel, ls="--", alpha=0.25)
        ax.set_xlabel("Endogenous lag")
        ax.set_ylabel("Information criterion")
        ax.set_title("VARX lag selection — IC values across endogenous lag (0..13)")
        ax.legend()
        fig.savefig(fig_path, bbox_inches="tight")
        plt.close(fig)
        log(f"  Lag selection plot saved: {fig_path}")
    except Exception as e:
        log(f"  [WARN] lag selection plot skipped: {e}")


# =========================================================================
# Fit + Granger + joint LR
# =========================================================================

def fit_varx(endog, exog, p):
    model = VAR(endog, exog=exog)
    return model.fit(p, trend="c")


def granger_bidirectional(fit, endog_cols):
    """test_causality F-test in both directions within VARX."""
    k_col, g_col = endog_cols
    gc_k2g = fit.test_causality(caused=g_col, causing=k_col, kind="f")
    gc_g2k = fit.test_causality(caused=k_col, causing=g_col, kind="f")

    def _serialize(gc):
        return {
            "test_statistic": float(gc.test_statistic),
            "pvalue": float(gc.pvalue),
            "df": list(gc.df) if isinstance(gc.df, tuple) else gc.df,
            "conclusion": "reject_null" if gc.pvalue < SIGNIFICANCE else "fail_to_reject",
        }

    return {
        "korea_to_global": _serialize(gc_k2g),
        "global_to_korea": _serialize(gc_g2k),
    }


def csi_joint_lr_test(endog, exog, p):
    """LR test: full (with CSI exog) vs restricted (no exog), same lag order p.

    H0: all CSI distributed-lag coefficients = 0 across both equations.
    LR ~ chi2(df = n_exog_cols * n_endog_eqs).
    """
    fit_full = VAR(endog, exog=exog).fit(p, trend="c")
    fit_restricted = VAR(endog).fit(p, trend="c")

    df_lr = exog.shape[1] * endog.shape[1]
    lr_stat = 2.0 * (fit_full.llf - fit_restricted.llf)
    pvalue = 1.0 - scipy_stats.chi2.cdf(lr_stat, df=df_lr)

    return {
        "ll_full": float(fit_full.llf),
        "ll_restricted": float(fit_restricted.llf),
        "lr_stat": float(lr_stat),
        "df": int(df_lr),
        "pvalue": float(pvalue),
        "conclusion": "reject_null" if pvalue < SIGNIFICANCE else "fail_to_reject",
    }


def csi_per_lag_pvalues(fit, exog_cols, endog_cols):
    """Extract per-(equation, regressor) coefficient + p-value for CSI lags."""
    pvals = fit.pvalues
    coefs = fit.params
    rows = []
    for eq in endog_cols:
        for col in exog_cols:
            try:
                rows.append({
                    "equation": eq,
                    "regressor": col,
                    "coef": float(coefs.loc[col, eq]),
                    "pvalue": float(pvals.loc[col, eq]),
                    "significant": bool(float(pvals.loc[col, eq]) < SIGNIFICANCE),
                })
            except (KeyError, IndexError, ValueError) as e:
                rows.append({
                    "equation": eq,
                    "regressor": col,
                    "coef": None,
                    "pvalue": None,
                    "significant": None,
                    "note": f"lookup failed: {e}",
                })
    return rows


# =========================================================================
# IRF (Cholesky: Korea ordered first per Stage 4 lead hypothesis)
# =========================================================================

def plot_and_extract_irf(fit, periods, out_dir):
    """Orthogonalized IRF + cumulative effects. Returns cumulative array."""
    irf = fit.irf(periods=periods)

    fig_orth = irf.plot(orth=True)
    fig_orth.suptitle(
        "VARX orthogonalized IRF -- search diff1 shocks (Cholesky: Korea first)",
        y=1.02,
    )
    fig_orth.savefig(os.path.join(out_dir, "varx_irf_orthogonalized.png"),
                     bbox_inches="tight")
    plt.close(fig_orth)

    fig_cum = irf.plot_cum_effects(orth=True)
    fig_cum.suptitle(
        "VARX cumulative orthogonalized IRF (Korea <-> Global)",
        y=1.02,
    )
    fig_cum.savefig(os.path.join(out_dir, "varx_irf_cumulative.png"),
                    bbox_inches="tight")
    plt.close(fig_cum)

    # cum_effects shape: (periods+1, n_eq_response, n_eq_shock)
    return irf.cum_effects


# =========================================================================
# Main
# =========================================================================

# =========================================================================
# A1' Mediation -- helpers (point estimate)
# =========================================================================

def mediation_point_estimate(df, mediator_col, outcome_col, treatment_cols):
    """Run 3-regression Baron-Kenny mediation, return a, b, c, c', a*b.

    Primary treatment is the first element of treatment_cols (csi_*_l0 by
    construction below; matches A1 finding global_d1 ~ csi_d1_l0 sole
    significant per-lag).
    """
    df = df.dropna().copy()
    primary_treatment = treatment_cols[0]

    X_a = sm.add_constant(df[treatment_cols])
    res_a = sm.OLS(df[mediator_col], X_a).fit()
    a_coef = float(res_a.params[primary_treatment])

    X_b = sm.add_constant(df[treatment_cols + [mediator_col]])
    res_b = sm.OLS(df[outcome_col], X_b).fit()
    b_coef = float(res_b.params[mediator_col])
    c_prime = float(res_b.params[primary_treatment])

    X_c = sm.add_constant(df[treatment_cols])
    res_c = sm.OLS(df[outcome_col], X_c).fit()
    c_coef = float(res_c.params[primary_treatment])

    indirect = a_coef * b_coef
    total = c_coef
    pct_indirect = float(indirect / total * 100.0) if abs(total) > 1e-12 else None

    return {
        "a_coef": a_coef,
        "b_coef": b_coef,
        "c_coef": c_coef,
        "c_prime_coef": c_prime,
        "indirect_a_times_b": float(indirect),
        "total_effect_c": float(total),
        "pct_indirect": pct_indirect,
        "primary_treatment": primary_treatment,
    }


def _indirect_only(df, mediator_col, outcome_col, treatment_cols):
    """Minimal callable returning only indirect a*b for bootstrap iteration."""
    primary = treatment_cols[0]
    primary_idx_in_X = 1 + treatment_cols.index(primary)
    X_a = sm.add_constant(df[treatment_cols].values)
    res_a = sm.OLS(df[mediator_col].values, X_a).fit()
    a = res_a.params[primary_idx_in_X]
    X_b = sm.add_constant(df[treatment_cols + [mediator_col]].values)
    res_b = sm.OLS(df[outcome_col].values, X_b).fit()
    b = res_b.params[-1]
    return a * b


# =========================================================================
# A1' Mediation -- block bootstrap + BCa
# =========================================================================

def joint_block_bootstrap(df, mediator_col, outcome_col, treatment_cols,
                          bootstrap_cls, bootstrap_kwargs, n_iter, seed, label):
    """Run block bootstrap on full DataFrame (joint resampling).

    arch.bootstrap classes accept positional DataFrame and resample by row,
    preserving column synchronization across mediator / outcome / treatments
    -- this satisfies Decision 4's joint time-aligned resampling requirement.
    """
    rng = np.random.default_rng(seed)
    bs = bootstrap_cls(*bootstrap_kwargs, df, seed=int(rng.integers(1, 2**31 - 1)))

    log(f"  Running {label}: n_iter={n_iter}, blocks={bootstrap_kwargs}, n_obs={len(df)}")

    indirect_samples = np.empty(n_iter, dtype=float)
    skipped = 0
    for i, (data, _) in enumerate(bs.bootstrap(n_iter)):
        if i >= n_iter:
            break
        df_b = data[0]
        try:
            indirect_samples[i] = _indirect_only(df_b, mediator_col, outcome_col, treatment_cols)
        except Exception:
            indirect_samples[i] = np.nan
            skipped += 1

    indirect_samples = indirect_samples[~np.isnan(indirect_samples)]
    point = _indirect_only(df, mediator_col, outcome_col, treatment_cols)
    bca = bca_ci(indirect_samples, point, df, mediator_col, outcome_col, treatment_cols)

    log(
        f"  {label}: point={point:+.4f}  BCa 95% CI=[{bca['lo']:+.4f}, {bca['hi']:+.4f}]  "
        f"(skipped {skipped}/{n_iter})"
    )
    return {
        "label": label,
        "point": float(point),
        "bca_lo": float(bca["lo"]),
        "bca_hi": float(bca["hi"]),
        "ci_excludes_zero": bool(bca["lo"] * bca["hi"] > 0),
        "n_valid": int(len(indirect_samples)),
        "n_skipped": int(skipped),
        "samples": indirect_samples,
    }


def bca_ci(samples, point, df, mediator_col, outcome_col, treatment_cols, alpha=0.05):
    """BCa: bias-corrected and accelerated CI. Jackknife for acceleration."""
    samples = np.asarray(samples)
    n = len(samples)

    prop_below = float(np.mean(samples < point))
    prop_below = min(max(prop_below, 1.0 / n), 1.0 - 1.0 / n)
    z0 = scipy_stats.norm.ppf(prop_below)

    jack = np.empty(len(df), dtype=float)
    for i in range(len(df)):
        df_jack = df.drop(df.index[i])
        try:
            jack[i] = _indirect_only(df_jack, mediator_col, outcome_col, treatment_cols)
        except Exception:
            jack[i] = np.nan
    jack = jack[~np.isnan(jack)]
    jack_mean = jack.mean()
    num = np.sum((jack_mean - jack) ** 3)
    den = 6.0 * (np.sum((jack_mean - jack) ** 2) ** 1.5)
    a_hat = float(num / den) if den > 1e-12 else 0.0

    z_alpha_lo = scipy_stats.norm.ppf(alpha / 2.0)
    z_alpha_hi = scipy_stats.norm.ppf(1.0 - alpha / 2.0)
    alpha_lo = scipy_stats.norm.cdf(
        z0 + (z0 + z_alpha_lo) / (1.0 - a_hat * (z0 + z_alpha_lo))
    )
    alpha_hi = scipy_stats.norm.cdf(
        z0 + (z0 + z_alpha_hi) / (1.0 - a_hat * (z0 + z_alpha_hi))
    )
    lo = float(np.quantile(samples, alpha_lo))
    hi = float(np.quantile(samples, alpha_hi))
    return {
        "lo": lo, "hi": hi,
        "z0": float(z0), "a_hat": a_hat,
        "alpha_lo": float(alpha_lo), "alpha_hi": float(alpha_hi),
    }


# =========================================================================
# A1' Mediation -- DataFrame builders
# =========================================================================

def build_trend_df(weekly_df, lag):
    """Mediator = Korea trend lagged. Outcome = Global trend.
    Treatment = CSI level distributed lags.

    NOTE: trend regression carries spurious risk (advisor verdict);
    diff1 robustness is the safety net.
    """
    csi_lags = pd.DataFrame(
        {f"csi_l{lag_}": weekly_df["csi"].shift(lag_) for lag_ in CSI_LAGS}
    )
    df = pd.DataFrame({
        "outcome_global_trend": weekly_df["global_trend"],
        "mediator_korea_trend_lag": weekly_df["korea_trend"].shift(lag),
    })
    df = pd.concat([df, csi_lags], axis=1).dropna()
    spec = (
        "mediator_korea_trend_lag",
        "outcome_global_trend",
        [f"csi_l{lag_}" for lag_ in CSI_LAGS],
    )
    return df, spec


def build_diff1_df(weekly_df, lag):
    """Mediator = Korea search diff1 lagged. Outcome = Global search diff1.
    Treatment = CSI diff1 distributed lags. Spurious risk = 0 (Step 0 stationary).
    """
    csi_d1 = weekly_df["csi"].diff()
    csi_lags = pd.DataFrame(
        {f"csi_d1_l{lag_}": csi_d1.shift(lag_) for lag_ in CSI_LAGS}
    )
    df = pd.DataFrame({
        "outcome_global_d1": weekly_df["global_search"].diff(),
        "mediator_korea_d1_lag": weekly_df["korea_search"].diff().shift(lag),
    })
    df = pd.concat([df, csi_lags], axis=1).dropna()
    spec = (
        "mediator_korea_d1_lag",
        "outcome_global_d1",
        [f"csi_d1_l{lag_}" for lag_ in CSI_LAGS],
    )
    return df, spec


def build_trend_df_sign_corrected(weekly_df, lag):
    """Mediator = Global trend lagged. Outcome = Korea trend.
    Treatment = CSI level distributed lags.

    Sign-corrected per Stage 4 sign convention discovery (DP24).
    Stage 4 DTW +10.4w in original labeling actually means Global leads Korea by ~10w.
    """
    csi_lags = pd.DataFrame(
        {f"csi_l{lag_}": weekly_df["csi"].shift(lag_) for lag_ in CSI_LAGS}
    )
    df = pd.DataFrame({
        "outcome_korea_trend": weekly_df["korea_trend"],
        "mediator_global_trend_lag": weekly_df["global_trend"].shift(lag),
    })
    df = pd.concat([df, csi_lags], axis=1).dropna()
    spec = (
        "mediator_global_trend_lag",
        "outcome_korea_trend",
        [f"csi_l{lag_}" for lag_ in CSI_LAGS],
    )
    return df, spec


def build_diff1_df_sign_corrected(weekly_df, lag):
    """Mediator = Global search diff1 lagged. Outcome = Korea search diff1.
    Spurious risk = 0 (Step 0 stationary). Sign-corrected.
    """
    csi_d1 = weekly_df["csi"].diff()
    csi_lags = pd.DataFrame(
        {f"csi_d1_l{lag_}": csi_d1.shift(lag_) for lag_ in CSI_LAGS}
    )
    df = pd.DataFrame({
        "outcome_korea_d1": weekly_df["korea_search"].diff(),
        "mediator_global_d1_lag": weekly_df["global_search"].diff().shift(lag),
    })
    df = pd.concat([df, csi_lags], axis=1).dropna()
    spec = (
        "mediator_global_d1_lag",
        "outcome_korea_d1",
        [f"csi_d1_l{lag_}" for lag_ in CSI_LAGS],
    )
    return df, spec


def plot_mediation_distributions(results, fig_path):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    panels = [
        ("trend_mbb", axes[0, 0], "Trend mediation -- Moving Block Bootstrap"),
        ("trend_sb", axes[0, 1], "Trend mediation -- Stationary Bootstrap"),
        ("diff1_mbb", axes[1, 0], "Diff1 mediation (robustness) -- MBB"),
        ("diff1_sb", axes[1, 1], "Diff1 mediation (robustness) -- SB"),
    ]
    for key, ax, title in panels:
        r = results.get(key)
        if r is None or "samples" not in r:
            ax.set_visible(False)
            continue
        samples = r["samples"]
        ax.hist(samples, bins=60, alpha=0.7)
        ax.axvline(0, color="red", ls="--", lw=1, label="zero")
        ax.axvline(r["point"], color="black", lw=1.5, label=f"point={r['point']:+.3f}")
        ax.axvspan(r["bca_lo"], r["bca_hi"], alpha=0.15, color="green",
                   label=f"BCa 95% CI [{r['bca_lo']:+.3f}, {r['bca_hi']:+.3f}]")
        ax.set_title(title)
        ax.set_xlabel("indirect effect a*b")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)
    log(f"  Distribution figure saved: {fig_path}")


# =========================================================================
# A1' Entry point
# =========================================================================

def run_a1_prime():
    # Reset report buffer so this entry point has its own markdown output.
    REPORT_LINES.clear()

    log("# Stage 7 Track A1' -- Mediation with Joint Block Bootstrap")
    log("")
    log(f"**Date:** {datetime.now():%Y-%m-%d %H:%M}")
    log(f"**lag* fixed at:** +{LAG_STAR}w (Stage 4 DTW finding; A3 will refine)")
    log(f"**CSI distributed lags:** {CSI_LAGS}")
    log(f"**Block length:** {BLOCK_LEN}w (sqrt(n) heuristic)")
    log(f"**Bootstrap iterations:** {N_BOOT}")

    section("1. Data Preparation")
    weekly_df = extract_data()
    df_trend, trend_spec = build_trend_df(weekly_df, LAG_STAR)
    df_diff1, diff1_spec = build_diff1_df(weekly_df, LAG_STAR)
    log(f"  trend mediation rows: {len(df_trend)}")
    log(f"    cols: {list(df_trend.columns)}")
    log(f"  diff1 mediation rows: {len(df_diff1)}")
    log(f"    cols: {list(df_diff1.columns)}")

    section("2. Trend Mediation -- Point Estimate (Primary)")
    pt_trend = mediation_point_estimate(df_trend, *trend_spec)
    for k, v in pt_trend.items():
        log(f"  {k:<22} = {v:+.4f}" if isinstance(v, float) else f"  {k:<22} = {v}")

    section("3. Diff1 Mediation -- Point Estimate (Robustness)")
    pt_diff1 = mediation_point_estimate(df_diff1, *diff1_spec)
    for k, v in pt_diff1.items():
        log(f"  {k:<22} = {v:+.4f}" if isinstance(v, float) else f"  {k:<22} = {v}")

    section("4. Bootstrap Inference -- 4 cells (trend/diff1 x MBB/SB)")
    results = {}
    for label, df_b, spec, boot_cls, boot_kwargs in [
        ("trend_mbb", df_trend, trend_spec, MovingBlockBootstrap, (BLOCK_LEN,)),
        ("trend_sb", df_trend, trend_spec, StationaryBootstrap, (BLOCK_LEN,)),
        ("diff1_mbb", df_diff1, diff1_spec, MovingBlockBootstrap, (BLOCK_LEN,)),
        ("diff1_sb", df_diff1, diff1_spec, StationaryBootstrap, (BLOCK_LEN,)),
    ]:
        results[label] = joint_block_bootstrap(
            df_b, spec[0], spec[1], spec[2],
            boot_cls, boot_kwargs, N_BOOT,
            SEED + abs(hash(label)) % 10000, label,
        )

    section("5. Scenario Classification (Decision 7 + advisor matrix)")
    trend_sig = results["trend_mbb"]["ci_excludes_zero"]
    diff1_sig = results["diff1_mbb"]["ci_excludes_zero"]

    if trend_sig and diff1_sig:
        matrix_row = "row_1_both_significant"
        narrative = "Both dimensions chain (rare; trend + diff1 both indirect)"
    elif trend_sig and not diff1_sig:
        matrix_row = "row_2_trend_only"
        narrative = ("Trend channel only -- VARX null + diff1 null confirms "
                     "short-run absence; trend channel is the chain pathway")
    elif (not trend_sig) and (not diff1_sig):
        matrix_row = "row_3_full_parallel"
        narrative = "Full parallel structure -- Scenario B confirmed, 'early reactor' pivot"
    else:
        matrix_row = "row_4_diff1_only_contradiction"
        narrative = ("Contradiction: VARX null + diff1 mediation significant "
                     "but trend null -- advisor escalation required")

    log(f"  Matrix row: {matrix_row}")
    log(f"  Narrative:  {narrative}")

    if trend_sig and pt_trend["pct_indirect"] is not None:
        pct = pt_trend["pct_indirect"]
        if pct > 50:
            decision_7 = "A_full_chain"
        elif pct >= 20:
            decision_7 = "C_strong_partial_mediation"
        else:
            decision_7 = "C_weak_marginal"
        log(f"  Decision 7 scenario: {decision_7} (% indirect = {pct:.1f}%)")
    elif not trend_sig:
        decision_7 = "B_parallel"
        log(f"  Decision 7 scenario: {decision_7}")
    else:
        decision_7 = "undefined_total_zero"
        log(f"  Decision 7 scenario: {decision_7}")

    section("6. Distribution Plot")
    plot_mediation_distributions(results, MEDIATION_FIG_PATH)

    output = {
        "date": datetime.now().isoformat(),
        "stage": "7_track_a1_prime_mediation",
        "lag_star_weeks": LAG_STAR,
        "csi_lags": CSI_LAGS,
        "block_len_weeks": BLOCK_LEN,
        "n_bootstrap": N_BOOT,
        "trend_point_estimate": pt_trend,
        "diff1_point_estimate": pt_diff1,
        "bootstrap_results": {
            k: {kk: vv for kk, vv in v.items() if kk != "samples"}
            for k, v in results.items()
        },
        "matrix_row": matrix_row,
        "matrix_row_narrative": narrative,
        "decision_7_scenario": decision_7,
    }

    with open(MEDIATION_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    log("")
    log(f"JSON saved:     {MEDIATION_JSON_PATH}")

    with open(MEDIATION_MD_PATH, "w", encoding="utf-8") as f:
        for line in REPORT_LINES:
            f.write(line + "\n")
    log(f"Markdown saved: {MEDIATION_MD_PATH}")


def run_a1_prime_sign_corrected():
    """Mediation re-run with sign-corrected direction (Global -> Korea).

    Per advisor cascade decision following Stage 4 sign convention discovery
    (DP24). Stage 4 +10.4w DTW lag in original labeling actually means Global
    leads Korea by ~10w. Mediation re-run with mediator/outcome swapped to
    test whether common-driver chain operates in the sign-corrected direction.

    Spec preserved from a1_prime: lag*=10w, joint MBB block=13w, Stationary
    Bootstrap robustness, 5000 iter, BCa CI. Variable swap only.
    """
    REPORT_LINES.clear()

    log("# Stage 7 Track A1' SIGN-CORRECTED -- Global_{t-lag} -> Korea Mediation")
    log("")
    log(f"**Date:** {datetime.now():%Y-%m-%d %H:%M}")
    log(f"**Direction:** Global trend lagged -> Korea trend (sign-corrected per DP24)")
    log(f"**lag*:** +{LAG_STAR}w (Stage 4 magnitude preserved)")
    log(f"**CSI distributed lags:** {CSI_LAGS}")
    log(f"**Block length:** {BLOCK_LEN}w")
    log(f"**Bootstrap iterations:** {N_BOOT}")

    section("1. Data Preparation")
    weekly_df = extract_data()
    df_trend, trend_spec = build_trend_df_sign_corrected(weekly_df, LAG_STAR)
    df_diff1, diff1_spec = build_diff1_df_sign_corrected(weekly_df, LAG_STAR)
    log(f"  trend mediation rows: {len(df_trend)}")
    log(f"    cols: {list(df_trend.columns)}")
    log(f"  diff1 mediation rows: {len(df_diff1)}")
    log(f"    cols: {list(df_diff1.columns)}")

    section("2. Trend Mediation -- Point Estimate (Sign-Corrected)")
    pt_trend = mediation_point_estimate(df_trend, *trend_spec)
    for k, v in pt_trend.items():
        log(f"  {k:<22} = {v:+.4f}" if isinstance(v, float) else f"  {k:<22} = {v}")

    section("3. Diff1 Mediation -- Point Estimate (Sign-Corrected Robustness)")
    pt_diff1 = mediation_point_estimate(df_diff1, *diff1_spec)
    for k, v in pt_diff1.items():
        log(f"  {k:<22} = {v:+.4f}" if isinstance(v, float) else f"  {k:<22} = {v}")

    section("4. Bootstrap Inference -- 4 cells")
    results = {}
    for label, df_b, spec, boot_cls, boot_kwargs in [
        ("trend_mbb", df_trend, trend_spec, MovingBlockBootstrap, (BLOCK_LEN,)),
        ("trend_sb", df_trend, trend_spec, StationaryBootstrap, (BLOCK_LEN,)),
        ("diff1_mbb", df_diff1, diff1_spec, MovingBlockBootstrap, (BLOCK_LEN,)),
        ("diff1_sb", df_diff1, diff1_spec, StationaryBootstrap, (BLOCK_LEN,)),
    ]:
        results[label] = joint_block_bootstrap(
            df_b, spec[0], spec[1], spec[2],
            boot_cls, boot_kwargs, N_BOOT,
            SEED + abs(hash(label)) % 10000, label,
        )

    section("5. Scenario Classification + Paired Comparison vs Original")
    trend_sig = results["trend_mbb"]["ci_excludes_zero"]
    diff1_sig = results["diff1_mbb"]["ci_excludes_zero"]

    if trend_sig and diff1_sig:
        matrix_row = "row_1_both_significant"
        narrative = ("Sign-corrected: both trend and diff1 channels significant. "
                     "Indirect channel detected in Global->Korea direction. "
                     "Sentinel framing primary preserved; mechanism augmented "
                     "with partial mediation channel.")
    elif trend_sig and not diff1_sig:
        matrix_row = "row_2_trend_only"
        narrative = ("Sign-corrected: trend channel significant but diff1 null. "
                     "Spurious regression / driver-confounded co-movement still "
                     "active even in corrected direction. diff1 = conservative anchor.")
    elif (not trend_sig) and (not diff1_sig):
        matrix_row = "row_3_full_parallel"
        narrative = ("Sign-corrected: both null. Combined with original-direction "
                     "null, channel absence is bidirectionally confirmed. CSI is "
                     "common direct driver of both Korea and Global; no intermediary. "
                     "5-dimension orthogonal null (mediation x 2 directions + VARX + "
                     "monthly Granger + lagged cointegration).")
    else:
        matrix_row = "row_4_diff1_only_contradiction"
        narrative = ("Sign-corrected: diff1 significant + trend null - advisor "
                     "escalation (contradicts spurious regression diagnostic).")

    log(f"  Matrix row: {matrix_row}")
    log(f"  Narrative:  {narrative}")

    if trend_sig and pt_trend["pct_indirect"] is not None:
        pct = pt_trend["pct_indirect"]
        if pct > 50:
            decision_7 = "A_full_chain"
        elif pct >= 20:
            decision_7 = "C_strong_partial_mediation"
        else:
            decision_7 = "C_weak_marginal"
    elif not trend_sig:
        decision_7 = "B_parallel"
    else:
        decision_7 = "undefined_total_zero"
    log(f"  Decision 7 scenario: {decision_7}")

    log("")
    log("  Paired comparison vs original (Korea -> Global):")
    log("  | Component         | Original (K->G) | Sign-corrected (G->K) |")
    log("  |---|---|---|")
    log(f"  | Trend a path      | +0.0928         | {pt_trend['a_coef']:+.4f}              |")
    log(f"  | Trend b path      | +0.5272         | {pt_trend['b_coef']:+.4f}              |")
    log(f"  | Trend indirect    | +0.0489         | {pt_trend['indirect_a_times_b']:+.4f}              |")
    log(f"  | Trend MBB BCa CI  | [-0.39, +0.18]  | "
        f"[{results['trend_mbb']['bca_lo']:+.4f}, {results['trend_mbb']['bca_hi']:+.4f}] |")
    log(f"  | Diff1 a path      | +0.1216         | {pt_diff1['a_coef']:+.4f}              |")
    log(f"  | Diff1 b path      | -0.0390         | {pt_diff1['b_coef']:+.4f}              |")
    log(f"  | Diff1 indirect    | -0.0047         | {pt_diff1['indirect_a_times_b']:+.4f}              |")
    log(f"  | Diff1 MBB BCa CI  | [-0.04, +0.003] | "
        f"[{results['diff1_mbb']['bca_lo']:+.4f}, {results['diff1_mbb']['bca_hi']:+.4f}] |")

    section("6. Distribution Plot")
    plot_mediation_distributions(results, MEDIATION_SC_FIG_PATH)

    output = {
        "date": datetime.now().isoformat(),
        "stage": "7_track_a1_prime_sign_corrected",
        "direction": "global_to_korea",
        "lag_star_weeks": LAG_STAR,
        "csi_lags": CSI_LAGS,
        "block_len_weeks": BLOCK_LEN,
        "n_bootstrap": N_BOOT,
        "trend_point_estimate": pt_trend,
        "diff1_point_estimate": pt_diff1,
        "bootstrap_results": {
            k: {kk: vv for kk, vv in v.items() if kk != "samples"}
            for k, v in results.items()
        },
        "matrix_row": matrix_row,
        "matrix_row_narrative": narrative,
        "decision_7_scenario": decision_7,
        "paired_comparison_with_original": {
            "trend_indirect_original": 0.0489,
            "trend_indirect_sign_corrected": pt_trend["indirect_a_times_b"],
            "diff1_indirect_original": -0.0047,
            "diff1_indirect_sign_corrected": pt_diff1["indirect_a_times_b"],
        },
    }

    with open(MEDIATION_SC_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    log("")
    log(f"JSON saved:     {MEDIATION_SC_JSON_PATH}")

    with open(MEDIATION_SC_MD_PATH, "w", encoding="utf-8") as f:
        for line in REPORT_LINES:
            f.write(line + "\n")
    log(f"Markdown saved: {MEDIATION_SC_MD_PATH}")


def run_a1():
    log("# Stage 7 Track A1 -- VARX on Search diff1 with CSI Distributed-Lag Exogenous")
    log("")
    log(f"**Date:** {datetime.now():%Y-%m-%d %H:%M}")
    log(f"**Endogenous:** (korea_d1, global_d1)  -- Step 0 + Option 6 advisor decision")
    log(f"**Exogenous CSI lags:** {CSI_LAGS}")
    log(f"**Cholesky ordering:** Korea first (Stage 4 +10.4w lead hypothesis)")
    log(f"**Significance:** alpha = {SIGNIFICANCE}")

    section("1. Data Preparation")
    endog, exog = build_varx_inputs()

    section("2. Lag Selection (Decision 3 -- BIC primary)")
    sel, selected, p_bic, aic_bic_gap = select_lag_order(endog, exog)
    plot_lag_selection(sel, selected,
                       os.path.join(FIG_DIR, "varx_lag_selection.png"))
    log(f"  Selected p = {p_bic} (BIC)")

    section("3. VAR(p) Fit with CSI Exogenous")
    fit = fit_varx(endog, exog, p_bic)
    log(f"  Effective observations: {fit.nobs}")
    log(f"  Number of equations:    {fit.neqs}")
    log(
        f"  AIC={fit.aic:.4f}  BIC={fit.bic:.4f}  "
        f"HQIC={fit.hqic:.4f}  Log-Lik={fit.llf:.4f}"
    )

    section("4. Bidirectional Granger Causality (within VARX)")
    granger_results = granger_bidirectional(fit, list(endog.columns))
    for direction, r in granger_results.items():
        log(
            f"  {direction:<22}  F={r['test_statistic']:7.4f}  "
            f"p={r['pvalue']:.4f}  -> {r['conclusion']}"
        )

    section("5. Joint Significance of CSI Distributed Lags (LR test)")
    lr = csi_joint_lr_test(endog, exog, p_bic)
    log(f"  LL_full       = {lr['ll_full']:.4f}")
    log(f"  LL_restricted = {lr['ll_restricted']:.4f}")
    log(
        f"  LR statistic  = {lr['lr_stat']:.4f}  df={lr['df']}  "
        f"p={lr['pvalue']:.4f}  -> {lr['conclusion']}"
    )

    section("6. CSI Per-Lag Coefficients")
    per_lag = csi_per_lag_pvalues(fit, list(exog.columns), list(endog.columns))
    log(f"  {'Equation':<14} {'Regressor':<14} {'Coef':>10} {'p':>10}")
    for r in per_lag:
        c_str = f"{r['coef']:>10.4f}" if r['coef'] is not None else f"{'NA':>10}"
        p_str = f"{r['pvalue']:>10.4f}" if r['pvalue'] is not None else f"{'NA':>10}"
        flag = " *" if r.get("significant") else ""
        log(f"  {r['equation']:<14} {r['regressor']:<14} {c_str} {p_str}{flag}")

    section("7. IRF (Cumulative Orthogonalized)")
    cum_arr = plot_and_extract_irf(fit, IRF_PERIODS, FIG_DIR)
    eq_idx = {col: i for i, col in enumerate(endog.columns)}
    k_idx = eq_idx[endog.columns[0]]
    g_idx = eq_idx[endog.columns[1]]
    cum_g_to_k_shock = cum_arr[:, g_idx, k_idx]
    cum_k_to_g_shock = cum_arr[:, k_idx, g_idx]
    log(
        f"  Cumulative response of Global to Korea shock @ h=20: "
        f"{cum_g_to_k_shock[-1]:+.4f}"
    )
    log(
        f"  Cumulative response of Korea to Global shock @ h=20: "
        f"{cum_k_to_g_shock[-1]:+.4f}"
    )
    log(f"  IRF figures saved: {FIG_DIR}/varx_irf_*.png")

    output = {
        "date": datetime.now().isoformat(),
        "stage": "7_track_a1_varx",
        "endog_cols": list(endog.columns),
        "exog_cols": list(exog.columns),
        "csi_lags": CSI_LAGS,
        "n_obs_effective": int(fit.nobs),
        "lag_selection": {
            "ic_selected": selected,
            "primary_p_bic": int(p_bic),
            "aic_bic_gap": int(aic_bic_gap),
            "escalation_candidate": bool(aic_bic_gap >= AIC_BIC_ESCALATION_GAP),
        },
        "fit_metrics": {
            "aic": float(fit.aic),
            "bic": float(fit.bic),
            "hqic": float(fit.hqic),
            "llf": float(fit.llf),
        },
        "granger_within_varx": granger_results,
        "csi_joint_lr": lr,
        "csi_per_lag": per_lag,
        "irf_cumulative_h20": {
            "global_response_to_korea_shock": float(cum_g_to_k_shock[-1]),
            "korea_response_to_global_shock": float(cum_k_to_g_shock[-1]),
        },
    }

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    log("")
    log(f"JSON saved:     {JSON_PATH}")

    with open(MD_PATH, "w", encoding="utf-8") as f:
        for line in REPORT_LINES:
            f.write(line + "\n")
    log(f"Markdown saved: {MD_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stage 7 Bridge chain analysis (A1: VARX, A1': mediation)"
    )
    parser.add_argument(
        "--stage",
        choices=["a1", "a1_prime", "a1_prime_sign_corrected"],
        required=True,
        help="a1 = VARX(2) on search diff1; a1_prime = mediation analysis",
    )
    args = parser.parse_args()
    if args.stage == "a1":
        run_a1()
    elif args.stage == "a1_prime":
        run_a1_prime()
    else:
        run_a1_prime_sign_corrected()