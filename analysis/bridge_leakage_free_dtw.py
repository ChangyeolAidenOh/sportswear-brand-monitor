"""
Stage 7 Track A3 follow-up -- Leakage-free DTW + CC re-calculation

Stage 4 trend DTW (+10.4w) and CC (+9w) used MSTL trend as input. MSTL
forward-looking leakage (DP23, korea_trend ratio 0.27) means both methods
share the leakage. Dual-method confirmation strength is reduced -- two
methods using the same leaky input is not independent verification.

This script re-computes Korea-Global lead-lag using leakage-free trend
extraction:

  Method A: Expanding-window MSTL trend (real-time MSTL)
            At each t, fit MSTL on data[:t+1], take last fitted trend value.
            Theoretically principled but early values (~52w) unstable.

  Method B: 13-week trailing rolling mean
            One-sided smoother with leakage=0 by construction. Smooths some
            seasonality but not all (does not remove sub-annual cycles).
            Faster and more stable than Method A.

For each method, recompute:
  - DTW lag (Stage 4 protocol: z-normalize, dtw-python sakoe-chiba)
  - Cross-correlation lag (Stage 4 protocol: numpy.correlate, demean)

Compare against Stage 4 originals (DTW +10.4w, CC +9w on bulk MSTL trend).

Outputs:
  - data/bridge/leakage_free_dtw.json
  - data/bridge/leakage_free_dtw.md
  - figures/bridge/leakage_free_dtw_comparison.png
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

# DTW backend detection -- prefer tslearn (Stage 4 primary), fallback to fastdtw
DTW_BACKEND = None
try:
    from tslearn.metrics import dtw_path
    DTW_BACKEND = "tslearn"
except ImportError:
    try:
        from fastdtw import fastdtw
        from scipy.spatial.distance import euclidean
        DTW_BACKEND = "fastdtw"
    except ImportError:
        pass

DTW_AVAILABLE = DTW_BACKEND is not None

warnings.filterwarnings("ignore", category=UserWarning, message=".*SQLAlchemy.*")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.bridge_chain_analysis import extract_data

DATA_DIR = "data/bridge"
FIG_DIR = "figures/bridge"
JSON_PATH = os.path.join(DATA_DIR, "leakage_free_dtw.json")
MD_PATH = os.path.join(DATA_DIR, "leakage_free_dtw.md")
FIG_PATH = os.path.join(FIG_DIR, "leakage_free_dtw_comparison.png")
MIN_HISTORY_WEEKS = 60
ROLLING_WINDOW = 13  # one-sided trailing mean window
CC_MAX_LAG = 26  # Stage 4 used full window; bound for clarity

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


# =========================================================================
# Trend extraction methods
# =========================================================================

def expanding_window_mstl_trend(series, periods=(13, 52), min_history=MIN_HISTORY_WEEKS):
    """At each t, fit MSTL on data[:t+1], record last trend value.

    Reused from bridge_mstl_leakage_check.py logic. Returns array same length
    as series with NaN for t < min_history.
    """
    s = np.asarray(series.values, dtype=float)
    rt = np.full(len(s), np.nan)
    for t in range(min_history, len(s)):
        try:
            res = MSTL(s[: t + 1], periods=list(periods)).fit()
            rt[t] = float(res.trend[-1])
        except Exception:
            rt[t] = np.nan
    return rt


def trailing_rolling_mean(series, window=ROLLING_WINDOW):
    """One-sided trailing rolling mean. NaN for first (window-1) points."""
    return series.rolling(window=window, min_periods=window).mean().values


# =========================================================================
# Lead-lag estimators (Stage 4 protocol)
# =========================================================================

def z_normalize(x):
    x = np.asarray(x, dtype=float)
    return (x - np.nanmean(x)) / np.nanstd(x)


def dtw_lag(korea_arr, global_arr):
    """DTW alignment lag: positive = Korea leads Global.

    EXACTLY MATCHES Stage 4 protocol from analysis/dtw_korea_global.py:
      lags = path[:, 0] - path[:, 1]  # positive = Korea leads
      mean_lag = round(np.mean(lags), 2)

    Returns full set of Stage 4 statistics for direct comparability.
    """
    if not DTW_AVAILABLE:
        return None, "no_dtw_backend_installed"

    valid = (~np.isnan(korea_arr)) & (~np.isnan(global_arr))
    k_z = z_normalize(korea_arr[valid])
    g_z = z_normalize(global_arr[valid])

    try:
        if DTW_BACKEND == "tslearn":
            # Stage 4 calls with .reshape(-1, 1) for univariate
            path, distance = dtw_path(k_z.reshape(-1, 1), g_z.reshape(-1, 1))
            path_arr = np.array(path)
        elif DTW_BACKEND == "fastdtw":
            distance, path = fastdtw(
                k_z.reshape(-1, 1), g_z.reshape(-1, 1), dist=euclidean
            )
            path_arr = np.array(path)
        else:
            return None, f"unknown_backend_{DTW_BACKEND}"

        # Stage 4 sign convention: idx_korea - idx_global, positive = Korea leads
        lags = path_arr[:, 0] - path_arr[:, 1]

        stats = {
            "mean_lag": round(float(np.mean(lags)), 2),
            "median_lag": round(float(np.median(lags)), 2),
            "std_lag": round(float(np.std(lags)), 2),
            "min_lag": int(np.min(lags)),
            "max_lag": int(np.max(lags)),
            "distance": float(distance),
            "n_path_points": int(len(path_arr)),
        }
        return stats, f"ok_{DTW_BACKEND}"
    except Exception as e:
        return None, f"backend_error: {type(e).__name__}: {e}"


def cross_correlation_lag(korea_arr, global_arr, max_lag=CC_MAX_LAG):
    """Find lag in [-max_lag, max_lag] that maximizes correlation.

    Stage 4 protocol: demean, scan lags, positive lag means Korea leads.
    Specifically: corr(Korea_{t-lag}, Global_t) maximum.
    """
    valid = (~np.isnan(korea_arr)) & (~np.isnan(global_arr))
    k = np.asarray(korea_arr[valid], dtype=float)
    g = np.asarray(global_arr[valid], dtype=float)
    k = k - k.mean()
    g = g - g.mean()
    n = len(k)

    lags = range(-max_lag, max_lag + 1)
    corrs = []
    for lag in lags:
        if lag >= 0:
            # Korea leads by lag: align Korea[0:n-lag] with Global[lag:n]
            num = np.sum(k[: n - lag] * g[lag:])
            den = np.sqrt(np.sum(k[: n - lag] ** 2) * np.sum(g[lag:] ** 2))
        else:
            l = -lag
            num = np.sum(k[l:] * g[: n - l])
            den = np.sqrt(np.sum(k[l:] ** 2) * np.sum(g[: n - l] ** 2))
        corrs.append(num / den if den > 0 else 0.0)

    corrs = np.array(corrs)
    best_idx = int(np.argmax(corrs))
    best_lag = list(lags)[best_idx]
    best_corr = float(corrs[best_idx])
    return {
        "best_lag": int(best_lag),
        "best_corr": best_corr,
        "lags": list(lags),
        "corrs": corrs.tolist(),
    }


# =========================================================================
# Comparison + classification
# =========================================================================

def classify_replication(method_results, stage4_dtw=10.4, stage4_cc=9.0,
                         tolerance=2.0):
    """Decide Scenario X (replication consistent) vs Scenario Y (revised).

        Inputs `method_results` is the per-method dict from main():
          method_results["dtw_stats"]["mean_lag"] (or None if dtw unavailable)
          method_results["cc"]["best_lag"]

        Replication consistent (Scenario X): both DTW mean_lag and CC lag within
        +/- tolerance of Stage 4 originals AND same direction (positive).

        Revised (Scenario Y): direction preserved (both positive) but magnitude
        materially different.

        Direction-flip: any negative lag -> advisor escalation (large decision).
        """
    dtw_stats = method_results.get("dtw_stats")
    dtw_lag = dtw_stats["mean_lag"] if dtw_stats is not None else None
    cc_lag = method_results["cc"]["best_lag"]

    flags = []
    if dtw_lag is None:
        flags.append("dtw_unavailable")
        direction_preserved = cc_lag > 0
    else:
        direction_preserved = (dtw_lag > 0) and (cc_lag > 0)

    if not direction_preserved:
        return "direction_flipped", flags + ["direction_flip_advisor_escalation"]

    if dtw_lag is None:
        if abs(cc_lag - stage4_cc) <= tolerance:
            return "scenario_x_consistent", flags + ["cc_within_tolerance"]
        else:
            return "scenario_y_revised", flags + ["cc_outside_tolerance"]

    dtw_close = abs(dtw_lag - stage4_dtw) <= tolerance
    cc_close = abs(cc_lag - stage4_cc) <= tolerance
    if dtw_close and cc_close:
        return "scenario_x_consistent", flags
    return "scenario_y_revised", flags


# =========================================================================
# Visualization
# =========================================================================

def plot_methods(df_global, trend_dict, fig_path):
    fig, axes = plt.subplots(len(trend_dict), 1, figsize=(13, 4 * len(trend_dict)),
                             sharex=True)
    if len(trend_dict) == 1:
        axes = [axes]
    for ax, (method_name, trends) in zip(axes, trend_dict.items()):
        weeks = np.arange(len(df_global))
        ax.plot(weeks, df_global["korea_search"], color="black", alpha=0.25,
                lw=0.6, label="Korea raw search")
        ax.plot(weeks, df_global["global_search"], color="gray", alpha=0.25,
                lw=0.6, label="Global raw search")
        ax.plot(weeks, trends["korea"], color="#E74C3C", lw=1.2, alpha=0.85,
                label=f"Korea trend ({method_name})")
        ax.plot(weeks, trends["global"], color="#3498DB", lw=1.2, alpha=0.85,
                label=f"Global trend ({method_name})")
        ax.set_title(f"Leakage-free trend extraction -- {method_name}")
        ax.set_ylabel("Value")
        ax.legend(fontsize=8, loc="upper left")
    axes[-1].set_xlabel("Week index")
    fig.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)


# =========================================================================
# Main
# =========================================================================

def main():
    print(f"# Stage 7 Track A3 follow-up -- Leakage-free DTW + CC")
    print(f"# Date: {datetime.now():%Y-%m-%d %H:%M}")
    print(f"# Stage 4 originals (bulk MSTL): DTW +10.4w, CC +9w")
    print(f"# Tolerance for Scenario X classification: ±2w")
    if not DTW_AVAILABLE:
        print(f"# WARNING: dtw-python not installed -- DTW skipped, CC only")

    print("\n## 1. Loading data")
    df_full = extract_data()
    df_global = pd.DataFrame({
        "korea_search": df_full["korea_search"].values,
        "global_search": df_full["global_search"].values,
    }, index=df_full.index)
    print(f"  series length: {len(df_global)} weeks")

    print("\n## 2. Method A — Expanding-window MSTL trend (~3-5 min)")
    print("  Computing real-time MSTL for korea_search...")
    korea_rt = expanding_window_mstl_trend(df_global["korea_search"])
    print(f"  ...done. n_valid={int((~np.isnan(korea_rt)).sum())}")
    print("  Computing real-time MSTL for global_search...")
    global_rt = expanding_window_mstl_trend(df_global["global_search"])
    print(f"  ...done. n_valid={int((~np.isnan(global_rt)).sum())}")

    print("\n## 3. Method B — 13w trailing rolling mean")
    korea_roll = trailing_rolling_mean(df_global["korea_search"])
    global_roll = trailing_rolling_mean(df_global["global_search"])
    print(f"  korea trailing mean n_valid: {int((~np.isnan(korea_roll)).sum())}")
    print(f"  global trailing mean n_valid: {int((~np.isnan(global_roll)).sum())}")

    print("\n## 4. Lead-lag estimation (DTW + CC) per method")
    methods = {
        "expanding_mstl": {"korea": korea_rt, "global": global_rt},
        "trailing_mean_13w": {"korea": korea_roll, "global": global_roll},
    }

    results = {}
    for method_name, trends in methods.items():
        print(f"\n  Method: {method_name}")
        dtw_stats, dtw_status = dtw_lag(trends["korea"], trends["global"])
        cc_result = cross_correlation_lag(
            trends["korea"], trends["global"], max_lag=CC_MAX_LAG
        )
        results[method_name] = {
            "dtw_stats": dtw_stats,
            "dtw_status": dtw_status,
            "cc": {
                "best_lag": cc_result["best_lag"],
                "best_corr": cc_result["best_corr"],
            },
            "cc_full": cc_result,
        }
        if dtw_stats is None:
            print(f"    DTW: unavailable ({dtw_status})")
        else:
            print(
                f"    DTW mean_lag:  {dtw_stats['mean_lag']:+.2f}w  "
                f"median={dtw_stats['median_lag']:+.2f}w  "
                f"std={dtw_stats['std_lag']:.2f}  (Stage 4 mean: +10.4w)"
            )
        print(f"    CC lag:   {cc_result['best_lag']:+d}w  "
              f"corr={cc_result['best_corr']:.4f}  (Stage 4: +9w)")

        scenario, flags = classify_replication(results[method_name])
        results[method_name]["scenario"] = scenario
        results[method_name]["flags"] = flags
        print(f"    Scenario: {scenario}  flags={flags}")

    print("\n## 5. Cross-method consistency")
    method_a_dtw_stats = results["expanding_mstl"].get("dtw_stats")
    method_a_dtw = method_a_dtw_stats["mean_lag"] if method_a_dtw_stats is not None else None
    method_b_dtw_stats = results["trailing_mean_13w"].get("dtw_stats")
    method_b_dtw = method_b_dtw_stats["mean_lag"] if method_b_dtw_stats is not None else None
    method_a_cc = results["expanding_mstl"]["cc"]["best_lag"]
    method_b_cc = results["trailing_mean_13w"]["cc"]["best_lag"]

    if method_a_dtw is not None and method_b_dtw is not None:
        cross_dtw = abs(method_a_dtw - method_b_dtw)
        print(f"  DTW cross-method diff: {cross_dtw:.2f}w  "
              f"(Method A {method_a_dtw:+.2f}w vs Method B {method_b_dtw:+.2f}w)")
    cross_cc = abs(method_a_cc - method_b_cc)
    print(f"  CC cross-method diff:  {cross_cc}w  "
          f"(Method A {method_a_cc:+d}w vs Method B {method_b_cc:+d}w)")

    print("\n## 6. Section 12.6 narrative slot draft")
    method_a_scenario = results["expanding_mstl"]["scenario"]
    if method_a_scenario == "scenario_x_consistent":
        slot = (
            "DTW + CC dual confirmation, both methods sharing MSTL trend smoothing leakage. "
            "Leakage-free replication via expanding-window MSTL yielded "
            f"DTW {method_a_dtw if method_a_dtw is not None else 'NA'}w / CC {method_a_cc:+d}w, "
            "confirming the shape similarity finding survives the leakage correction. "
            "The lead estimate's precision is reduced but the structural finding is robust."
        )
    elif method_a_scenario == "scenario_y_revised":
        slot = (
            "DTW + CC convergence at +10.4w/+9w partly attributable to MSTL forward-looking "
            "smoothing. Leakage-free replication via expanding-window MSTL yielded "
            f"DTW {method_a_dtw if method_a_dtw is not None else 'NA'}w / CC {method_a_cc:+d}w, "
            "refining the original Stage 4 finding. Direction (Korea leading Global) is "
            "preserved but magnitude estimate is materially revised."
        )
    else:  # direction_flipped
        slot = (
            "Leakage-free replication produced direction-flipped result -- advisor "
            "escalation. Stage 4 +10.4w lead is not robust to leakage correction; "
            "original DTW finding may be artifact of MSTL forward-looking smoothing."
        )
    print(f"  {slot}")

    print("\n## 7. Save outputs")
    output = {
        "date": datetime.now().isoformat(),
        "stage": "7_track_a3_followup_leakage_free_dtw",
        "stage_4_originals": {"dtw_lag": 10.4, "cc_lag": 9.0},
        "tolerance_weeks": 2.0,
        "min_history_weeks": MIN_HISTORY_WEEKS,
        "rolling_window_weeks": ROLLING_WINDOW,
        "dtw_backend": DTW_BACKEND,
        "dtw_available": DTW_AVAILABLE,
        "cc_max_lag_searched": CC_MAX_LAG,
        "results": {
            method_name: {
                "dtw_stats": r["dtw_stats"],
                "dtw_status": r["dtw_status"],
                "cc_best_lag": r["cc"]["best_lag"],
                "cc_best_corr": r["cc"]["best_corr"],
                "scenario": r["scenario"],
                "flags": r["flags"],
            }
            for method_name, r in results.items()
        },
        "section_12_6_narrative_slot": slot,
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved: {JSON_PATH}")

    # Save trends for Track B1 reuse (advisor decision)
    np.savez(
        os.path.join(DATA_DIR, "leakage_free_trends.npz"),
        korea_expanding_mstl=korea_rt,
        global_expanding_mstl=global_rt,
        korea_trailing_mean=korea_roll,
        global_trailing_mean=global_roll,
        week_start=df_full.index.values.astype("datetime64[D]"),
    )
    print(f"  Saved: data/bridge/leakage_free_trends.npz  (Track B1 reuse)")

    plot_methods(df_global, methods, FIG_PATH)
    print(f"  Saved: {FIG_PATH}")


if __name__ == "__main__":
    main()