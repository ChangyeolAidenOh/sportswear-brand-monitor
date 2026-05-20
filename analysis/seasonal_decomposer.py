"""
Stage 3 Step A1 — Seasonal Decomposition (STL + MSTL comparison)

Decomposes mart.brand_kpi_weekly search_index into trend, seasonal,
and residual components for 4 brands x 2 regions = 8 time series.

STL (period=52) is the primary method. MSTL (periods=[13, 52]) is
run as a comparison to verify whether sub-annual seasonality exists.

Results are stored in mart.seasonal_components and visualized
in figures/seasonal/.

Usage:
    python -m analysis.seasonal_decomposer
    python -m analysis.seasonal_decomposer --compare-mstl
    python -m analysis.seasonal_decomposer --plot-only
    python -m analysis.seasonal_decomposer --dry-run
"""

import argparse
import os
import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL, MSTL

from database.connection import get_conn

# CONSTANTS

FIG_DIR = "figures/seasonal"
os.makedirs(FIG_DIR, exist_ok=True)

BRANDS = ["nike", "adidas", "puma", "new_balance"]
REGIONS = ["korea", "global"]

# STL parameters
STL_PERIOD = 52          # weekly data, annual seasonality
STL_SEASONAL = 53        # must be odd, >= period + 1
STL_ROBUST = True        # robust to outliers

# MSTL parameters
MSTL_PERIODS = [13, 52]  # quarterly + annual

METRIC_NAME = "search_index"

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (14, 8),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

BRAND_COLORS = {
    "new_balance": "#E74C3C",
    "nike": "#FF6B00",
    "adidas": "#3498DB",
    "puma": "#2ECC71",
}


# DATA FETCH

def fetch_brand_kpi(brand, region):
    """Fetch weekly search_index for a single brand-region pair."""
    query = """
        SELECT week_start, search_index
        FROM mart.brand_kpi_weekly
        WHERE brand = %s
          AND region = %s
          AND search_index IS NOT NULL
        ORDER BY week_start
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn, params=(brand, region))

    df["week_start"] = pd.to_datetime(df["week_start"])
    df = df.set_index("week_start")
    df = df.asfreq("W-SUN")  # GT Sunday-start convention
    return df


# STL DECOMPOSITION

def run_stl(series, period=STL_PERIOD, seasonal=STL_SEASONAL, robust=STL_ROBUST):
    """Run STL decomposition on a pandas Series, handling missing values."""
    if series.isna().sum() > 0:
        series = series.interpolate(method="linear")

    n = len(series)
    if n < 2 * period:
        print(f"  [WARN] Series length {n} < {2 * period}, skipping STL")
        return None

    stl = STL(
        series,
        period=period,
        seasonal=seasonal,
        robust=robust,
    )
    result = stl.fit()
    return result


# MSTL DECOMPOSITION

def run_mstl(series, periods=None):
    """Run MSTL decomposition with multiple seasonal periods."""
    if periods is None:
        periods = MSTL_PERIODS

    if series.isna().sum() > 0:
        series = series.interpolate(method="linear")

    n = len(series)
    max_period = max(periods)
    if n < 2 * max_period:
        print(f"  [WARN] Series length {n} < {2 * max_period}, skipping MSTL")
        return None

    mstl = MSTL(
        series,
        periods=periods,
    )
    result = mstl.fit()
    return result


# DECOMPOSE ALL

def decompose_all(method="STL"):
    """Decompose all 8 brand-region time series with specified method."""
    results = {}

    for brand in BRANDS:
        for region in REGIONS:
            label = f"{brand}_{region}"
            print(f"  Decomposing ({method}): {label}")

            df = fetch_brand_kpi(brand, region)
            if df.empty:
                print(f"  [WARN] No data for {label}")
                continue

            series = df["search_index"]
            print(f"    Rows: {len(series)}, range: {series.index.min()} ~ {series.index.max()}")

            if method == "STL":
                result = run_stl(series)
            else:
                result = run_mstl(series)

            if result is None:
                continue

            resid = result.resid
            resid_var = resid.var()
            resid_std = resid.std()

            if method == "STL":
                seasonal_amp = result.seasonal.max() - result.seasonal.min()
            else:
                # MSTL stores seasonal components in .seasonal DataFrame
                seasonal_amp = result.seasonal.sum(axis=1).max() - result.seasonal.sum(axis=1).min()

            print(f"    Residual std: {resid_std:.4f}, variance: {resid_var:.4f}")
            print(f"    Seasonal amplitude: {seasonal_amp:.4f}")

            # Build output DataFrame
            if method == "STL":
                out = pd.DataFrame({
                    "brand": brand,
                    "region": region,
                    "week_start": series.index,
                    "metric_name": METRIC_NAME,
                    "observed": result.observed,
                    "trend": result.trend,
                    "seasonal": result.seasonal,
                    "residual": result.resid,
                    "decomposition_method": method,
                })
            else:
                # MSTL: sum all seasonal components into one column for DB storage
                out = pd.DataFrame({
                    "brand": brand,
                    "region": region,
                    "week_start": series.index,
                    "metric_name": METRIC_NAME,
                    "observed": result.observed,
                    "trend": result.trend,
                    "seasonal": result.seasonal.sum(axis=1),
                    "residual": result.resid,
                    "decomposition_method": method,
                })

            results[label] = {
                "result": result,
                "dataframe": out,
                "series": series,
                "resid_var": resid_var,
                "resid_std": resid_std,
                "seasonal_amp": seasonal_amp,
            }

    return results


# DATABASE WRITE

def save_to_db(results, method="STL"):
    """Insert decomposition results into mart.seasonal_components."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clear previous results for this method + metric
            cur.execute("""
                DELETE FROM mart.seasonal_components
                WHERE metric_name = %s
                  AND decomposition_method = %s
            """, (METRIC_NAME, method))
            deleted = cur.rowcount
            if deleted > 0:
                print(f"  Deleted {deleted} existing {method} rows")

            total = 0
            for label, data in results.items():
                df = data["dataframe"]
                for _, row in df.iterrows():
                    cur.execute("""
                        INSERT INTO mart.seasonal_components
                            (brand, region, week_start, metric_name,
                             observed, trend, seasonal, residual,
                             decomposition_method)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        row["brand"], row["region"], row["week_start"],
                        row["metric_name"], row["observed"], row["trend"],
                        row["seasonal"], row["residual"],
                        row["decomposition_method"],
                    ))
                total += len(df)

            conn.commit()
            print(f"  Inserted {total} rows into mart.seasonal_components ({method})")


# VISUALIZATION

def plot_decomposition(brand, region, result, series, method="STL"):
    """4-panel decomposition plot for a single brand-region pair."""
    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
    color = BRAND_COLORS.get(brand, "#333333")
    label = f"{brand} ({region})"

    if method == "STL":
        seasonal_vals = result.seasonal
    else:
        seasonal_vals = result.seasonal.sum(axis=1)

    components = [
        ("Observed", result.observed),
        ("Trend", result.trend),
        ("Seasonal", seasonal_vals),
        ("Residual", result.resid),
    ]

    for ax, (title, comp) in zip(axes, components):
        ax.plot(comp.index, comp.values, color=color, linewidth=1.2)
        ax.set_ylabel(title, fontsize=10)
        if title == "Residual":
            ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")

    period_label = f"period={STL_PERIOD}" if method == "STL" else f"periods={MSTL_PERIODS}"
    axes[0].set_title(f"{method} Decomposition: {label} — search_index ({period_label})",
                       fontsize=12, fontweight="bold")
    axes[-1].set_xlabel("Week")

    fig.tight_layout()
    prefix = method.lower()
    fig_path = os.path.join(FIG_DIR, f"{prefix}_{brand}_{region}.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"    Saved: {fig_path}")


def plot_seasonal_overlay(method="STL"):
    """Overlay seasonal components of all brands for each region."""
    for region in REGIONS:
        fig, ax = plt.subplots(figsize=(14, 5))

        for brand in BRANDS:
            df = fetch_brand_kpi(brand, region)
            if df.empty:
                continue

            series = df["search_index"]

            if method == "STL":
                result = run_stl(series)
                if result is None:
                    continue
                seasonal_vals = result.seasonal
            else:
                result = run_mstl(series)
                if result is None:
                    continue
                seasonal_vals = result.seasonal.sum(axis=1)

            color = BRAND_COLORS.get(brand, "#333333")
            ax.plot(seasonal_vals.index, seasonal_vals.values,
                    label=brand, color=color, linewidth=1.2)

        ax.set_title(f"Seasonal Component Overlay — {region} ({method})",
                     fontsize=12, fontweight="bold")
        ax.set_xlabel("Week")
        ax.set_ylabel("Seasonal")
        ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
        ax.legend(loc="upper right")

        fig.tight_layout()
        prefix = method.lower()
        fig_path = os.path.join(FIG_DIR, f"{prefix}_seasonal_overlay_{region}.png")
        plt.savefig(fig_path, bbox_inches="tight")
        plt.close()
        print(f"  Saved: {fig_path}")


def plot_all(results, method="STL"):
    """Generate all decomposition plots."""
    print(f"  Generating {method} decomposition plots...")
    for label, data in results.items():
        brand, region = label.rsplit("_", 1)
        plot_decomposition(brand, region, data["result"], data["series"], method)

    print(f"  Generating {method} seasonal overlay plots...")
    plot_seasonal_overlay(method)


# SUMMARY / COMPARISON

def print_summary(results, method="STL"):
    """Print summary table of decomposition metrics."""
    print(f"\n  === {method} Decomposition Summary ===\n")
    header = f"  {'Brand':<15} {'Region':<8} {'Weeks':>5} {'Trend_Std':>10} {'Seas_Amp':>10} {'Resid_Std':>10} {'S/N Ratio':>10}"
    print(header)
    print("  " + "-" * len(header.strip()))

    for label, data in sorted(results.items()):
        brand, region = label.rsplit("_", 1)

        n = len(data["result"].observed)
        trend_std = data["result"].trend.std()
        seas_amp = data["seasonal_amp"]
        resid_std = data["resid_std"]
        sn_ratio = seas_amp / resid_std if resid_std > 0 else np.nan

        print(f"  {brand:<15} {region:<8} {n:>5} {trend_std:>10.4f} {seas_amp:>10.4f} {resid_std:>10.4f} {sn_ratio:>10.4f}")



def print_comparison(stl_results, mstl_results):
    """Print STL vs MSTL residual variance comparison table."""
    print("\n  === STL vs MSTL — Residual Variance Comparison ===\n")
    header = f"  {'Brand':<15} {'Region':<8} {'STL_Var':>10} {'MSTL_Var':>10} {'Reduction%':>11} {'Verdict':>22}"
    print(header)
    print("  " + "-" * len(header.strip()))

    for label in sorted(stl_results.keys()):
        brand, region = label.rsplit("_", 1)

        stl_var = stl_results[label]["resid_var"]

        if label in mstl_results:
            mstl_var = mstl_results[label]["resid_var"]
            reduction = (1 - mstl_var / stl_var) * 100 if stl_var > 0 else 0.0
            # Threshold: < 5% reduction = not meaningful
            if reduction > 5.0:
                verdict = "MSTL improves"
            else:
                verdict = "Single season confirmed"
        else:
            mstl_var = np.nan
            reduction = np.nan
            verdict = "MSTL failed"

        print(f"  {brand:<15} {region:<8} {stl_var:>10.4f} {mstl_var:>10.4f} {reduction:>10.2f}% {verdict:>22}")

    print("  Threshold: reduction > 5% = sub-annual seasonality detected")
    print("  Conclusion: if all reductions < 5%, single annual season structure confirmed.")


# CLI / MAIN

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 3 Step A1: STL seasonal decomposition (+ MSTL comparison)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Decompose and print summary without DB write or plot")
    parser.add_argument("--plot-only", action="store_true",
                        help="Regenerate plots without recomputing")
    parser.add_argument("--compare-mstl", action="store_true",
                        help="Run MSTL comparison and print variance reduction table")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Stage 3 Step A1: Seasonal Decomposition")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- STL (primary) ---
    if args.plot_only:
        stl_results = decompose_all(method="STL")
        if stl_results:
            plot_all(stl_results, method="STL")
            print_summary(stl_results, method="STL")
        print("  Done (plot-only mode)")
        return

    stl_results = decompose_all(method="STL")

    if not stl_results:
        print("  [ERROR] No STL decomposition results produced")
        return

    print_summary(stl_results, method="STL")

    if not args.dry_run:
        save_to_db(stl_results, method="STL")
        plot_all(stl_results, method="STL")

    # --- MSTL (comparison, if requested) ---
    if args.compare_mstl:
        print("\n  --- MSTL Comparison (periods=[13, 52]) ---")
        mstl_results = decompose_all(method="MSTL")

        if mstl_results:
            print_summary(mstl_results, method="MSTL")
            print_comparison(stl_results, mstl_results)

            if not args.dry_run:
                save_to_db(mstl_results, method="MSTL")

    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
