"""
Stage 7 Track A3 follow-up -- MSTL trend forward-looking leakage diagnostic.

Track A3 produced suspicious results:
  - Korea trend at lag 6w yields best CV RMSE; RMSE monotonically increases with lag
  - Adding Korea trend to Prophet/SARIMAX worsens hold-out RMSE by 41-59%
  - Pattern inconsistent with Stage 4 DTW +10.4w finding

Hypothesis: MSTL is a centered smoother. Trend at week T is estimated using
data from both before and after T. When that trend value is then used as a
"lagged" forecasting feature, it carries information from the future,
inflating short-lag CV scores and degrading honest hold-out forecasts.

Diagnostic: compare bulk-fit MSTL trend (computed on the full series) against
real-time MSTL trend (computed on expanding window, taking only the last
fitted value at each t). Significant divergence => forward-looking leakage.

Outputs:
  - data/bridge/mstl_leakage_check.json
  - data/bridge/mstl_leakage_check.md
  - figures/bridge/mstl_leakage_diagnostic.png
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
from statsmodels.tsa.seasonal import MSTL

warnings.filterwarnings("ignore", category=UserWarning, message=".*SQLAlchemy.*")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.bridge_chain_analysis import extract_data

DATA_DIR = "data/bridge"
FIG_DIR = "figures/bridge"
JSON_PATH = os.path.join(DATA_DIR, "mstl_leakage_check.json")
MD_PATH = os.path.join(DATA_DIR, "mstl_leakage_check.md")
FIG_PATH = os.path.join(FIG_DIR, "mstl_leakage_diagnostic.png")
MIN_HISTORY_WEEKS = 60  # MSTL needs at least 2 full annual cycles for stable fit

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


def real_time_mstl_trend(series_values, periods, min_history):
    """Expanding-window MSTL: at each t, fit on data[:t+1], take last trend value.

    This simulates what a real-time forecaster would observe at week t,
    using only past data, no future contamination.
    """
    rt_trend = np.full(len(series_values), np.nan)
    for t in range(min_history, len(series_values)):
        try:
            res = MSTL(series_values[: t + 1], periods=periods).fit()
            rt_trend[t] = float(res.trend[-1])
        except Exception as e:
            rt_trend[t] = np.nan
    return rt_trend


def diagnose(label, series, bulk_trend_from_db, periods):
    """Compare bulk-fit MSTL trend (production, in DB) against real-time MSTL trend."""
    bulk_recomputed = MSTL(series.values, periods=periods).fit().trend
    rt_trend = real_time_mstl_trend(series.values, periods, MIN_HISTORY_WEEKS)

    valid = ~np.isnan(rt_trend)
    diff_db_vs_rt = bulk_trend_from_db.values[valid] - rt_trend[valid]
    diff_recomputed_vs_rt = bulk_recomputed[valid] - rt_trend[valid]
    diff_db_vs_recomputed = bulk_trend_from_db.values[valid] - bulk_recomputed[valid]

    series_std = float(series.std())

    return {
        "label": label,
        "n_total": int(len(series)),
        "n_valid_for_diagnosis": int(valid.sum()),
        "series_std": series_std,
        "db_vs_rt_mean_abs_diff": float(np.mean(np.abs(diff_db_vs_rt))),
        "db_vs_rt_max_abs_diff": float(np.max(np.abs(diff_db_vs_rt))),
        "db_vs_rt_diff_to_std_ratio": float(np.mean(np.abs(diff_db_vs_rt)) / series_std),
        "recomputed_vs_rt_mean_abs_diff": float(np.mean(np.abs(diff_recomputed_vs_rt))),
        "recomputed_vs_rt_diff_to_std_ratio": float(
            np.mean(np.abs(diff_recomputed_vs_rt)) / series_std
        ),
        "db_vs_recomputed_mean_abs_diff": float(np.mean(np.abs(diff_db_vs_recomputed))),
        "valid_mask": valid,
        "bulk_db": bulk_trend_from_db.values,
        "bulk_recomputed": bulk_recomputed,
        "real_time": rt_trend,
    }


def classify_leakage(result):
    """Classify based on diff-to-std ratio. Conservative threshold."""
    ratio = result["recomputed_vs_rt_diff_to_std_ratio"]
    if ratio < 0.05:
        verdict = "no_leakage"
    elif ratio < 0.15:
        verdict = "mild_leakage"
    else:
        verdict = "significant_leakage"
    return verdict, ratio


def plot_diagnostic(results, fig_path):
    fig, axes = plt.subplots(len(results), 1, figsize=(12, 4 * len(results)),
                             sharex=True)
    if len(results) == 1:
        axes = [axes]

    for ax, r in zip(axes, results):
        weeks = np.arange(r["n_total"])
        ax.plot(weeks, r["bulk_db"], lw=1.2, alpha=0.7,
                label="Bulk-fit MSTL trend (current DB value)")
        ax.plot(weeks, r["bulk_recomputed"], lw=1.2, alpha=0.5, ls="--",
                label="Bulk-fit MSTL trend (recomputed)")
        valid = r["valid_mask"]
        ax.plot(weeks[valid], r["real_time"][valid], lw=1.2, alpha=0.8,
                label="Real-time MSTL trend (expanding window)")
        ax.set_title(
            f"{r['label']}  "
            f"diff-to-std ratio = {r['recomputed_vs_rt_diff_to_std_ratio']:.4f}"
        )
        ax.set_ylabel("Trend value")
        ax.legend(fontsize=8)
    axes[-1].set_xlabel("Week index")
    fig.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)


def main():
    print(f"# Stage 7 Track A3 follow-up -- MSTL leakage diagnostic")
    print(f"# Date: {datetime.now():%Y-%m-%d %H:%M}")
    print(f"# Min history for real-time MSTL: {MIN_HISTORY_WEEKS} weeks")

    print("\n## 1. Loading data")
    df = extract_data()
    print(f"  series length: {len(df)} weeks")
    print(f"  korea_trend std: {df['korea_trend'].std():.4f}")
    print(f"  global_trend std: {df['global_trend'].std():.4f}")

    print("\n## 2. Real-time MSTL diagnostic (this is the slow step ~3-5 min)")
    print("  Computing expanding-window MSTL for korea_search...")
    r_korea = diagnose("korea_trend", df["korea_search"], df["korea_trend"],
                       periods=[13, 52])
    print(f"  ...done. n_valid={r_korea['n_valid_for_diagnosis']}")

    print("  Computing expanding-window MSTL for global_search...")
    r_global = diagnose("global_trend", df["global_search"], df["global_trend"],
                        periods=[13, 52])
    print(f"  ...done. n_valid={r_global['n_valid_for_diagnosis']}")

    print("\n## 3. Diagnostic results")
    results_summary = []
    for r in [r_korea, r_global]:
        verdict, ratio = classify_leakage(r)
        print(f"\n  {r['label']}:")
        print(f"    series std:                       {r['series_std']:.4f}")
        print(f"    DB bulk vs real-time mean |diff|: {r['db_vs_rt_mean_abs_diff']:.4f}")
        print(f"    DB bulk vs real-time max |diff|:  {r['db_vs_rt_max_abs_diff']:.4f}")
        print(f"    DB bulk vs real-time ratio:       {r['db_vs_rt_diff_to_std_ratio']:.4f}")
        print(f"    Recomputed bulk vs real-time:     {r['recomputed_vs_rt_mean_abs_diff']:.4f}")
        print(f"    Recomputed ratio (key metric):    {ratio:.4f}")
        print(f"    DB vs recomputed (sanity, should be ~0): {r['db_vs_recomputed_mean_abs_diff']:.4f}")
        print(f"    Verdict: {verdict.upper()}")
        results_summary.append({
            "variable": r["label"],
            "series_std": r["series_std"],
            "db_vs_rt_mean_abs_diff": r["db_vs_rt_mean_abs_diff"],
            "recomputed_vs_rt_mean_abs_diff": r["recomputed_vs_rt_mean_abs_diff"],
            "recomputed_vs_rt_diff_to_std_ratio": ratio,
            "db_vs_recomputed_mean_abs_diff": r["db_vs_recomputed_mean_abs_diff"],
            "verdict": verdict,
        })

    print("\n## 4. Track A3 implication")
    any_leakage = any(s["verdict"] in ("mild_leakage", "significant_leakage")
                      for s in results_summary)
    if any_leakage:
        a3_implication = (
            "Track A3 results invalidated by MSTL forward-looking leakage. "
            "Lag grid CV's monotonic RMSE-vs-lag pattern (lag 6w best, lag 14w worst) "
            "and the +41-59% triple-comparison RMSE degradation are consistent with "
            "shorter lags carrying more future information through the centered "
            "MSTL smoother. Re-design needed: replace MSTL trend exogenous with "
            "either (a) raw korea_search lagged, (b) one-sided rolling mean, or "
            "(c) expanding-window MSTL trend."
        )
    else:
        a3_implication = (
            "MSTL trend has no significant forward-looking leakage. Track A3 "
            "results are valid and represent an honest finding: Korea trend as "
            "exogenous degrades Global forecast in both Prophet and SARIMAX. "
            "Sentinel framing requires reconciliation -- Korea trend has "
            "differential-reactivity signal but no forecast-grade predictive value. "
            "KPI 7 narrative must be further qualified."
        )
    print(f"  {a3_implication}")

    print("\n## 5. Saving diagnostic outputs")
    output = {
        "date": datetime.now().isoformat(),
        "stage": "7_track_a3_followup_mstl_leakage",
        "min_history_weeks": MIN_HISTORY_WEEKS,
        "leakage_threshold_ratio_no_leakage": 0.05,
        "leakage_threshold_ratio_significant": 0.15,
        "results": results_summary,
        "any_leakage_detected": any_leakage,
        "track_a3_implication": a3_implication,
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved: {JSON_PATH}")

    plot_diagnostic([r_korea, r_global], FIG_PATH)
    print(f"  Saved: {FIG_PATH}")


if __name__ == "__main__":
    main()