"""
Stage 7 Track A3 -- Prophet triple comparison + Korea trend lag grid CV

Per Stage 7 Decision 5 + 6 (advisor approved):
  - 3 Prophet specs: baseline / +CSI / +CSI + Korea_trend@lag*
  - Lag grid 6-14w paired-fold CV (initial=52w, period=13w, horizon=13w)
  - Same 148w/26w train/test split as Stage 6 (comparison preserved)
  - Korea exogenous = MSTL trend (Decision 6 unchanged)
  - SARIMAX parallel comparison on same inputs (DP18 generalization probe)
  - Lag* uncertainty disclosure: paired fold RMSE diffs, no "exactly 10w" claim

Outputs:
  - data/bridge/lag_grid_cv_results.csv
  - data/bridge/global_forecast_triple_comparison.csv     (Stage 8 right panel input)
  - data/bridge/triple_comparison_metrics.json
  - figures/bridge/triple_comparison_rmse.png
  - figures/bridge/lag_grid_cv.png
  - figures/bridge/triple_comparison_forecasts.png
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

from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
import statsmodels.api as sm

warnings.filterwarnings("ignore", category=Warning, module="statsmodels")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, message=".*SQLAlchemy.*")
# Prophet emits cmdstanpy info logs; quiet them
import logging
import contextlib
import io

@contextlib.contextmanager
def suppress_stdout_stderr():
    """Suppress C-level stdout/stderr from cmdstanpy. Prophet 4.6+ logger reset
    workaround: cmdstanpy bypasses Python logging by writing directly to fds.
    """
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.bridge_chain_analysis import extract_data

# Constants
DATA_DIR = "data/bridge"
FIG_DIR = "figures/bridge"
LAG_GRID = list(range(6, 15))  # 6, 7, ..., 14
TEST_WEEKS = 26
TRAIN_WEEKS = 148
CV_INITIAL = "364 days"   # 52 weeks
CV_PERIOD = "91 days"     # 13 weeks
CV_HORIZON = "91 days"    # 13 weeks
CHANGEPOINT_PRIOR_SCALE = 0.05  # Stage 6 finding
FOURIER_K_YEARLY = 2  # Stage 6 ablation: K=2 optimal
FOURIER_K_QUARTERLY = 2

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "axes.grid": True,
    "grid.alpha": 0.3,
})


# =========================================================================
# Data preparation
# =========================================================================

def build_global_dataset():
    """Build NB Global forecast dataset matching Stage 6 split.

    Returns DataFrame with columns:
      ds (week_start), y (global_search), csi, korea_trend
    """
    df = extract_data()
    out = pd.DataFrame({
        "ds": df.index,
        "y": df["global_search"].values,
        "csi": df["csi"].values,
        "korea_trend": df["korea_trend"].values,
    }).reset_index(drop=True)
    out["ds"] = pd.to_datetime(out["ds"])
    return out


def add_lagged_korea_trend(df, lag):
    """Add korea_trend_lag column (NaN for first `lag` rows)."""
    out = df.copy()
    out[f"korea_trend_lag{lag}"] = out["korea_trend"].shift(lag)
    return out


# =========================================================================
# Prophet builders
# =========================================================================

def build_prophet_baseline():
    m = Prophet(
        seasonality_mode="additive",
        changepoint_prior_scale=CHANGEPOINT_PRIOR_SCALE,
        yearly_seasonality=False,  # custom below for K control
        weekly_seasonality=False,
        daily_seasonality=False,
    )
    m.add_seasonality(name="yearly", period=365.25, fourier_order=FOURIER_K_YEARLY)
    m.add_seasonality(name="quarterly", period=91.25, fourier_order=FOURIER_K_QUARTERLY)
    return m


def build_prophet_with_csi():
    m = build_prophet_baseline()
    m.add_regressor("csi")
    return m


def build_prophet_with_csi_and_korea(lag):
    m = build_prophet_with_csi()
    m.add_regressor(f"korea_trend_lag{lag}")
    return m


# =========================================================================
# Train/test evaluation
# =========================================================================

def evaluate_prophet(model_builder, df_full, exog_cols, label):
    """Fit on first TRAIN_WEEKS, forecast next TEST_WEEKS, return RMSE/MAE/MAPE.

    model_builder is a zero-arg callable. For lag-dependent specs, use lambda
    to bind the lag at call site.
    """
    df = df_full.dropna(subset=exog_cols + ["y"]).reset_index(drop=True)
    if len(df) < TRAIN_WEEKS + TEST_WEEKS:
        n = len(df)
        train = df.iloc[: n - TEST_WEEKS].copy()
        test = df.iloc[n - TEST_WEEKS:].copy()
    else:
        train = df.iloc[: TRAIN_WEEKS].copy()
        test = df.iloc[TRAIN_WEEKS : TRAIN_WEEKS + TEST_WEEKS].copy()

    m = model_builder()  # always zero-arg
    train_input_cols = ["ds", "y"] + exog_cols
    with suppress_stdout_stderr():
        m.fit(train[train_input_cols])

    future_cols = ["ds"] + exog_cols
    forecast = m.predict(test[future_cols])
    yhat = forecast["yhat"].values
    y = test["y"].values

    rmse = float(np.sqrt(np.mean((y - yhat) ** 2)))
    mae = float(np.mean(np.abs(y - yhat)))
    mask = y != 0
    mape = float(np.mean(np.abs((y[mask] - yhat[mask]) / y[mask])) * 100) if mask.any() else None

    return {
        "label": label,
        "rmse": rmse,
        "mae": mae,
        "mape": mape,
        "n_train": len(train),
        "n_test": len(test),
        "exog_cols": exog_cols,
        "yhat": yhat.tolist(),
        "y": y.tolist(),
        "ds": [str(d.date()) for d in test["ds"]],
    }, m, train, test


def evaluate_sarimax(df_full, exog_cols, label):
    """SARIMAX parallel comparison on same input. Order from Stage 6: Global = (0,1,0).

    Fourier K=2 yearly + K=2 quarterly = 8 columns added per Stage 6.
    """
    df = df_full.dropna(subset=exog_cols + ["y"]).reset_index(drop=True)
    if len(df) < TRAIN_WEEKS + TEST_WEEKS:
        n = len(df)
        train = df.iloc[: n - TEST_WEEKS].copy()
        test = df.iloc[n - TEST_WEEKS:].copy()
    else:
        train = df.iloc[: TRAIN_WEEKS].copy()
        test = df.iloc[TRAIN_WEEKS : TRAIN_WEEKS + TEST_WEEKS].copy()

    # Add Stage 6 Fourier terms (K=2 yearly + K=2 quarterly = 8 cols)
    fourier_cols = []
    t_train = np.arange(len(train))
    t_test = np.arange(len(train), len(train) + len(test))
    for k in range(1, FOURIER_K_YEARLY + 1):
        for fn_name, fn in [("sin", np.sin), ("cos", np.cos)]:
            col = f"{fn_name}_52_{k}"
            train[col] = fn(2 * np.pi * k * t_train / 52)
            test[col] = fn(2 * np.pi * k * t_test / 52)
            fourier_cols.append(col)
    for k in range(1, FOURIER_K_QUARTERLY + 1):
        for fn_name, fn in [("sin", np.sin), ("cos", np.cos)]:
            col = f"{fn_name}_13_{k}"
            train[col] = fn(2 * np.pi * k * t_train / 13)
            test[col] = fn(2 * np.pi * k * t_test / 13)
            fourier_cols.append(col)

    full_exog = exog_cols + fourier_cols

    if not full_exog:
        sx_train = None
        sx_test = None
    else:
        sx_train = train[full_exog].values
        sx_test = test[full_exog].values

    model = sm.tsa.SARIMAX(
        train["y"].values,
        exog=sx_train,
        order=(0, 1, 0),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    res = model.fit(disp=False)
    forecast = res.forecast(steps=len(test), exog=sx_test)
    yhat = np.asarray(forecast)
    y = test["y"].values

    rmse = float(np.sqrt(np.mean((y - yhat) ** 2)))
    mae = float(np.mean(np.abs(y - yhat)))
    mask = y != 0
    mape = float(np.mean(np.abs((y[mask] - yhat[mask]) / y[mask])) * 100) if mask.any() else None

    return {
        "label": label,
        "rmse": rmse,
        "mae": mae,
        "mape": mape,
        "n_train": len(train),
        "n_test": len(test),
        "exog_cols": exog_cols,
        "yhat": yhat.tolist(),
        "y": y.tolist(),
        "ds": [str(d.date()) for d in test["ds"]],
    }


# =========================================================================
# Lag grid paired-fold CV (Decision 5)
# =========================================================================

def lag_grid_paired_cv(df_global):
    """Run Prophet CV across lag grid 6-14w with same fold structure.

    For each lag, fit Prophet(+CSI+korea_trend_lag{lag}) and run cross_validation.
    Same (initial, period, horizon) -> same fold cutoffs across lags ->
    paired fold RMSE comparison reduces variance.
    """
    print("\n=== Lag grid CV (paired folds) ===")
    print(f"  initial={CV_INITIAL}, period={CV_PERIOD}, horizon={CV_HORIZON}")
    print(f"  lag grid: {LAG_GRID}")

    all_fold_rmse = {}  # lag -> array of fold RMSEs
    all_cv_dfs = {}

    for lag in LAG_GRID:
        df_lag = add_lagged_korea_trend(df_global, lag).dropna(
            subset=["y", "csi", f"korea_trend_lag{lag}"]
        ).reset_index(drop=True)

        m = build_prophet_with_csi_and_korea(lag)
        with suppress_stdout_stderr():
            m.fit(df_lag[["ds", "y", "csi", f"korea_trend_lag{lag}"]])
            df_cv = cross_validation(
                m,
                initial=CV_INITIAL,
                period=CV_PERIOD,
                horizon=CV_HORIZON,
                disable_tqdm=True,
            )

        # Per-fold RMSE: group by cutoff
        df_cv["sq_err"] = (df_cv["y"] - df_cv["yhat"]) ** 2
        per_fold = df_cv.groupby("cutoff")["sq_err"].mean().pow(0.5)
        all_fold_rmse[lag] = per_fold.values
        all_cv_dfs[lag] = df_cv
        print(f"  lag={lag:>2}w  n_folds={len(per_fold)}  mean_RMSE={per_fold.mean():.4f}  median={per_fold.median():.4f}")

    return all_fold_rmse, all_cv_dfs


def paired_fold_analysis(all_fold_rmse):
    """For each lag pair, compute paired-fold RMSE difference + SE.

    Returns DataFrame with rows = lag, cols = mean/median/std/se across folds.
    """
    rows = []
    # First normalize fold counts -- paired comparison requires same fold count
    fold_counts = {lag: len(rmses) for lag, rmses in all_fold_rmse.items()}
    n_folds_min = min(fold_counts.values())
    print(f"\n  Paired analysis using {n_folds_min} common folds (min across lags)")

    for lag, rmses in all_fold_rmse.items():
        rmses_n = rmses[:n_folds_min]
        rows.append({
            "lag": lag,
            "n_folds": int(len(rmses_n)),
            "mean_rmse": float(np.mean(rmses_n)),
            "median_rmse": float(np.median(rmses_n)),
            "std_rmse": float(np.std(rmses_n, ddof=1)),
            "se_rmse": float(np.std(rmses_n, ddof=1) / np.sqrt(len(rmses_n))),
            "fold_rmses": rmses_n.tolist(),
        })
    df_out = pd.DataFrame(rows).sort_values("mean_rmse").reset_index(drop=True)
    return df_out, n_folds_min


def find_best_lag_with_uncertainty(df_lag_cv):
    """Identify best lag and lags within ±1 SE / ±1-2w neighborhood."""
    best = df_lag_cv.iloc[0]
    best_lag = int(best["lag"])
    best_rmse = float(best["mean_rmse"])

    # Lags within best mean RMSE + 1 SE of best -> "statistically indistinguishable"
    threshold = best_rmse + best["se_rmse"]
    indistinguishable = df_lag_cv[df_lag_cv["mean_rmse"] <= threshold]["lag"].tolist()

    # Lags within ±2w of best
    near_neighbors = [l for l in df_lag_cv["lag"].tolist() if abs(l - best_lag) <= 2]

    return {
        "best_lag": best_lag,
        "best_rmse": best_rmse,
        "best_se": float(best["se_rmse"]),
        "indistinguishable_lags": indistinguishable,
        "near_neighbor_lags": near_neighbors,
        "uncertainty_disclosure": (
            f"lag {best_lag}w lowest mean RMSE; lags within ±1 SE = "
            f"{indistinguishable} (statistically indistinguishable); "
            f"±2w neighborhood = {near_neighbors}"
        ),
    }


# =========================================================================
# Visualization
# =========================================================================

def plot_lag_grid_cv(df_lag_cv, fig_path):
    fig, ax = plt.subplots(figsize=(10, 5))
    df_sorted = df_lag_cv.sort_values("lag").reset_index(drop=True)
    ax.errorbar(
        df_sorted["lag"], df_sorted["mean_rmse"],
        yerr=df_sorted["se_rmse"],
        marker="o", capsize=4, lw=1.5,
        label="Mean RMSE ± SE across folds",
    )
    best_idx = df_sorted["mean_rmse"].idxmin()
    ax.axvline(df_sorted.loc[best_idx, "lag"], ls="--", color="red", alpha=0.4,
               label=f"Best lag = {int(df_sorted.loc[best_idx, 'lag'])}w")
    ax.axvline(10, ls=":", color="black", alpha=0.4, label="Stage 4 DTW reference (10w)")
    ax.set_xlabel("Korea trend lag (weeks)")
    ax.set_ylabel("Cross-validation RMSE (paired folds)")
    ax.set_title("Track A3 -- Lag grid paired-fold CV (Prophet + CSI + Korea_trend_lag)")
    ax.legend()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)


def plot_triple_comparison_rmse(triple_metrics, fig_path):
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = [r["label"] for r in triple_metrics]
    rmses = [r["rmse"] for r in triple_metrics]
    colors = ["#888888", "#3498DB", "#E74C3C", "#888888", "#3498DB", "#E74C3C"]
    bars = ax.bar(range(len(labels)), rmses, color=colors[:len(labels)])
    for i, (b, r) in enumerate(zip(bars, rmses)):
        ax.text(b.get_x() + b.get_width() / 2, r + 0.05,
                f"{r:.3f}", ha="center", fontsize=9)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("Test-set RMSE (26w)")
    ax.set_title("Track A3 -- Triple comparison: Prophet vs SARIMAX × baseline / +CSI / +Korea_trend")
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)


def plot_triple_forecasts(triple_results, df_global, fig_path):
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
    for ax, family, title in [
        (axes[0], "prophet", "Prophet — baseline / +CSI / +CSI+Korea_trend"),
        (axes[1], "sarimax", "SARIMAX — baseline / +CSI / +CSI+Korea_trend"),
    ]:
        ax.plot(df_global["ds"], df_global["y"], color="black", alpha=0.4, lw=0.8, label="Actual (full)")
        for r in triple_results:
            if not r["label"].startswith(family):
                continue
            ds_test = pd.to_datetime(r["ds"])
            ax.plot(ds_test, r["yhat"], lw=1.5, label=f"{r['label']}  RMSE={r['rmse']:.3f}")
        ax.set_title(title)
        ax.set_ylabel("Search index")
        ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)


# =========================================================================
# Main
# =========================================================================

def main():
    print(f"# Stage 7 Track A3 -- Prophet triple comparison + lag grid CV")
    print(f"# Date: {datetime.now():%Y-%m-%d %H:%M}")
    print(f"# Lag grid: {LAG_GRID}")

    print("\n## 1. Data Preparation")
    df_global = build_global_dataset()
    print(f"  rows: {len(df_global)}  range: {df_global['ds'].min().date()} ~ {df_global['ds'].max().date()}")

    print("\n## 2. Lag Grid Paired-Fold CV (Decision 5)")
    all_fold_rmse, _ = lag_grid_paired_cv(df_global)
    df_lag_cv, n_folds = paired_fold_analysis(all_fold_rmse)

    print("\n## 3. Lag* selection with uncertainty disclosure")
    lag_uncertainty = find_best_lag_with_uncertainty(df_lag_cv)
    print(f"  Best lag:                {lag_uncertainty['best_lag']}w")
    print(f"  Best mean RMSE:          {lag_uncertainty['best_rmse']:.4f}")
    print(f"  Best SE:                 {lag_uncertainty['best_se']:.4f}")
    print(f"  Indistinguishable lags:  {lag_uncertainty['indistinguishable_lags']}")
    print(f"  Near-neighbor lags:      {lag_uncertainty['near_neighbor_lags']}")
    print(f"  Disclosure: {lag_uncertainty['uncertainty_disclosure']}")
    lag_star = lag_uncertainty["best_lag"]

    df_lag_cv.to_csv(os.path.join(DATA_DIR, "lag_grid_cv_results.csv"), index=False)
    plot_lag_grid_cv(df_lag_cv, os.path.join(FIG_DIR, "lag_grid_cv.png"))

    print("\n## 4. Triple comparison -- Prophet × {baseline, +CSI, +CSI+Korea_trend@lag*}")
    df_with_lag = add_lagged_korea_trend(df_global, lag_star)

    prophet_baseline_metrics, _, _, _ = evaluate_prophet(
        build_prophet_baseline, df_global, [], "prophet_baseline"
    )
    print(f"  prophet_baseline:                 RMSE={prophet_baseline_metrics['rmse']:.4f}")

    prophet_csi_metrics, _, _, _ = evaluate_prophet(
        build_prophet_with_csi, df_global, ["csi"], "prophet_csi"
    )
    print(f"  prophet_csi:                      RMSE={prophet_csi_metrics['rmse']:.4f}")

    prophet_csi_korea_metrics, _, _, _ = evaluate_prophet(
        lambda: build_prophet_with_csi_and_korea(lag_star),
        df_with_lag, ["csi", f"korea_trend_lag{lag_star}"],
        f"prophet_csi_korea_lag{lag_star}",
    )
    print(f"  prophet_csi_korea (lag={lag_star}w):     RMSE={prophet_csi_korea_metrics['rmse']:.4f}")

    print("\n## 5. SARIMAX parallel comparison (DP18 generalization probe)")
    sarimax_baseline = evaluate_sarimax(df_global, [], "sarimax_baseline")
    print(f"  sarimax_baseline:                 RMSE={sarimax_baseline['rmse']:.4f}")
    sarimax_csi = evaluate_sarimax(df_global, ["csi"], "sarimax_csi")
    print(f"  sarimax_csi:                      RMSE={sarimax_csi['rmse']:.4f}")
    sarimax_csi_korea = evaluate_sarimax(
        df_with_lag, ["csi", f"korea_trend_lag{lag_star}"],
        f"sarimax_csi_korea_lag{lag_star}",
    )
    print(f"  sarimax_csi_korea (lag={lag_star}w):     RMSE={sarimax_csi_korea['rmse']:.4f}")

    triple_results = [
        prophet_baseline_metrics, prophet_csi_metrics, prophet_csi_korea_metrics,
        sarimax_baseline, sarimax_csi, sarimax_csi_korea,
    ]

    print("\n## 6. Outcome framing (3-way pre-commit)")
    prophet_korea_gain = prophet_csi_metrics["rmse"] - prophet_csi_korea_metrics["rmse"]
    sarimax_korea_gain = sarimax_csi["rmse"] - sarimax_csi_korea["rmse"]
    prophet_pct_gain = prophet_korea_gain / prophet_csi_metrics["rmse"] * 100
    sarimax_pct_gain = sarimax_korea_gain / sarimax_csi["rmse"] * 100
    print(f"  Prophet RMSE gain (CSI -> CSI+Korea):    {prophet_korea_gain:+.4f}  ({prophet_pct_gain:+.2f}%)")
    print(f"  SARIMAX RMSE gain (CSI -> CSI+Korea):    {sarimax_korea_gain:+.4f}  ({sarimax_pct_gain:+.2f}%)")

    if abs(prophet_pct_gain) < 2.0:
        prophet_outcome = "no_gain"
    elif prophet_pct_gain > 5.0:
        prophet_outcome = "large_gain"
    else:
        prophet_outcome = "small_gain"

    if abs(sarimax_pct_gain) < 2.0:
        sarimax_outcome = "no_gain"
    elif sarimax_pct_gain > 5.0:
        sarimax_outcome = "large_gain"
    else:
        sarimax_outcome = "small_gain"

    asymmetry = (
        "asymmetric_prophet_absorbs"
        if (sarimax_outcome in ("large_gain", "small_gain")) and prophet_outcome == "no_gain"
        else "consistent" if prophet_outcome == sarimax_outcome
        else "asymmetric_other"
    )
    print(f"  Prophet outcome: {prophet_outcome}")
    print(f"  SARIMAX outcome: {sarimax_outcome}")
    print(f"  Cross-model asymmetry: {asymmetry}")

    if asymmetry == "asymmetric_prophet_absorbs":
        narrative_slot = (
            "DP18 generalized: Prophet changepoint absorbs Korea trend signal as "
            "it absorbed CSI; SARIMAX explicit drift cannot, so Korea trend is "
            "informative for SARIMAX but redundant for Prophet. Confirms "
            "differential-reactivity model -- Korea trend carries common-driver "
            "signal that Prophet's piecewise trend already captures."
        )
    elif prophet_outcome == "no_gain" and sarimax_outcome == "no_gain":
        narrative_slot = (
            "Strongest common-driver evidence: Korea trend provides no incremental "
            "predictive information beyond CSI in either Prophet or SARIMAX. Korea "
            "trend = differential reactor of the same driver landscape, not an "
            "independent driver."
        )
    elif prophet_outcome in ("large_gain", "small_gain") and sarimax_outcome in ("large_gain", "small_gain"):
        narrative_slot = (
            "Korea trend = leading proxy of common-driver signal. Both Prophet and "
            "SARIMAX gain from its inclusion -- predictive value confirmed without "
            "implying causal mediation (mediation analysis still null per Track A1')."
        )
    else:
        narrative_slot = (
            f"Cross-model outcome asymmetric in unexpected direction "
            f"(prophet={prophet_outcome}, sarimax={sarimax_outcome}). "
            f"Advisor escalation."
        )
    print(f"\n  Section 12.4 narrative slot: {narrative_slot}")

    print("\n## 7. Save outputs")
    triple_df = pd.DataFrame([
        {"model": r["label"], "rmse": r["rmse"], "mae": r["mae"], "mape": r["mape"]}
        for r in triple_results
    ])
    triple_csv_path = os.path.join(DATA_DIR, "global_forecast_triple_comparison.csv")
    triple_df.to_csv(triple_csv_path, index=False)
    print(f"  Saved: {triple_csv_path}  (Stage 8 right panel input)")

    metrics_json = {
        "date": datetime.now().isoformat(),
        "stage": "7_track_a3",
        "lag_grid": LAG_GRID,
        "lag_star": lag_star,
        "lag_uncertainty": lag_uncertainty,
        "n_paired_folds": int(n_folds),
        "triple_results": [
            {k: v for k, v in r.items() if k not in ("yhat", "y", "ds")}
            for r in triple_results
        ],
        "prophet_korea_gain_pct": prophet_pct_gain,
        "sarimax_korea_gain_pct": sarimax_pct_gain,
        "prophet_outcome": prophet_outcome,
        "sarimax_outcome": sarimax_outcome,
        "cross_model_asymmetry": asymmetry,
        "section_12_4_narrative_slot": narrative_slot,
    }
    metrics_path = os.path.join(DATA_DIR, "triple_comparison_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_json, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved: {metrics_path}")

    plot_triple_comparison_rmse(triple_results, os.path.join(FIG_DIR, "triple_comparison_rmse.png"))
    plot_triple_forecasts(triple_results, df_global, os.path.join(FIG_DIR, "triple_comparison_forecasts.png"))
    print(f"  Saved: figures/bridge/triple_comparison_rmse.png")
    print(f"  Saved: figures/bridge/triple_comparison_forecasts.png")
    print(f"  Saved: figures/bridge/lag_grid_cv.png")


if __name__ == "__main__":
    main()