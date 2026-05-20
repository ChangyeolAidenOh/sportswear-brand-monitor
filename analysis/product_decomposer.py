"""
Stage 3 Step A2 — NB Product Line Seasonal Decomposition (MSTL)

Decomposes mart.product_portfolio_weekly search_index for all NB product
lines using MSTL(periods=[13, 52]).

Re-verifies Stage 0 H2 weak signal hypothesis (530 SS/FW=1.18,
992 SS/FW=0.93) with proper dual-season decomposition.

Korea products: 530, 574, 992, 2002r, 327
Global products: 9060, 574, 2002r, 1906r, 990

Results are stored in mart.seasonal_components (product_line column)
and visualized in figures/seasonal/products/.

Usage:
    python -m analysis.product_decomposer
    python -m analysis.product_decomposer --dry-run
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
from statsmodels.tsa.seasonal import MSTL

from database.connection import get_conn

# CONSTANTS

FIG_DIR = "figures/seasonal/products"
os.makedirs(FIG_DIR, exist_ok=True)

MSTL_PERIODS = [13, 52]
MIN_OBSERVATIONS = 104  # 2 full annual cycles

METRIC_NAME = "search_index"
DECOMPOSITION_METHOD = "MSTL"

# Season week ranges for SS/FW ratio calculation (ISO weeks approximate)
# SS: ~week 13-38 (Apr-Sep), FW: ~week 39-12 (Oct-Mar)
SS_WEEK_RANGE = range(13, 39)  # April to September
FW_WEEK_RANGE = list(range(39, 53)) + list(range(1, 13))  # October to March

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (14, 10),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

PRODUCT_COLORS = {
    "530": "#E74C3C",
    "574": "#3498DB",
    "992": "#2ECC71",
    "2002r": "#9B59B6",
    "327": "#F39C12",
    "9060": "#E74C3C",
    "1906r": "#F39C12",
    "990": "#1ABC9C",
}


# DATA FETCH

def fetch_product_lines():
    """Fetch distinct product lines per region with observation counts."""
    query = """
        SELECT product_line, region, COUNT(*) AS n_weeks,
               MIN(week_start) AS first_week, MAX(week_start) AS last_week
        FROM mart.product_portfolio_weekly
        WHERE search_index IS NOT NULL
        GROUP BY product_line, region
        ORDER BY region, product_line
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn)
    return df


def fetch_product_series(product_line, region):
    """Fetch weekly search_index for a single product-region pair."""
    query = """
        SELECT week_start, search_index
        FROM mart.product_portfolio_weekly
        WHERE product_line = %s
          AND region = %s
          AND search_index IS NOT NULL
        ORDER BY week_start
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn, params=(product_line, region))

    df["week_start"] = pd.to_datetime(df["week_start"])
    df = df.set_index("week_start")
    df = df.asfreq("W-SUN")
    return df


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

    mstl = MSTL(series, periods=periods)
    result = mstl.fit()
    return result


# SS/FW RATIO CALCULATION

def compute_ss_fw_ratio(seasonal_annual):
    """Compute SS/FW seasonal amplitude ratio from annual component."""
    idx = seasonal_annual.index
    iso_weeks = idx.isocalendar().week.values

    ss_vals = seasonal_annual.values[np.isin(iso_weeks, list(SS_WEEK_RANGE))]
    fw_vals = seasonal_annual.values[np.isin(iso_weeks, FW_WEEK_RANGE)]

    ss_amp = np.abs(ss_vals).mean() if len(ss_vals) > 0 else 0
    fw_amp = np.abs(fw_vals).mean() if len(fw_vals) > 0 else 0

    ratio = ss_amp / fw_amp if fw_amp > 0 else np.nan
    return ratio, ss_amp, fw_amp


# DECOMPOSE ALL PRODUCTS

def decompose_all():
    """Decompose all product lines across both regions."""
    # Check observation counts first
    inventory = fetch_product_lines()
    print("\n  === Product Line Observation Inventory ===\n")
    print(f"  {'Product':<12} {'Region':<8} {'Weeks':>5} {'First':>12} {'Last':>12} {'Status':>20}")
    print("  " + "-" * 70)

    eligible = []
    for _, row in inventory.iterrows():
        status = "OK" if row["n_weeks"] >= MIN_OBSERVATIONS else "INSUFFICIENT"
        print(f"  {row['product_line']:<12} {row['region']:<8} {row['n_weeks']:>5} "
              f"{str(row['first_week'])[:10]:>12} {str(row['last_week'])[:10]:>12} {status:>20}")
        if row["n_weeks"] >= MIN_OBSERVATIONS:
            eligible.append((row["product_line"], row["region"]))

    print(f"\n  Eligible: {len(eligible)} / {len(inventory)} product-region pairs")

    # Run MSTL decomposition
    results = {}
    for product_line, region in eligible:
        label = f"{product_line}_{region}"
        print(f"  Decomposing: {label}")

        df = fetch_product_series(product_line, region)
        if df.empty:
            print(f"  [WARN] No data for {label}")
            continue

        series = df["search_index"]
        result = run_mstl(series)
        if result is None:
            continue

        resid_var = result.resid.var()
        resid_std = result.resid.std()
        seasonal_total = result.seasonal.sum(axis=1)
        seasonal_amp = seasonal_total.max() - seasonal_total.min()

        # Extract individual seasonal components
        seasonal_cols = result.seasonal.columns.tolist()
        # MSTL names columns as 'seasonal_13', 'seasonal_52'
        seasonal_annual = result.seasonal.iloc[:, -1]  # period=52 (last)
        seasonal_quarterly = result.seasonal.iloc[:, 0]  # period=13 (first)

        annual_amp = seasonal_annual.max() - seasonal_annual.min()
        quarterly_amp = seasonal_quarterly.max() - seasonal_quarterly.min()

        # SS/FW ratio from annual component
        ss_fw_ratio, ss_amp, fw_amp = compute_ss_fw_ratio(seasonal_annual)

        print(f"    Resid std: {resid_std:.4f}, variance: {resid_var:.4f}")
        print(f"    Annual amp: {annual_amp:.4f}, Quarterly amp: {quarterly_amp:.4f}")
        print(f"    SS/FW ratio: {ss_fw_ratio:.4f} (SS={ss_amp:.4f}, FW={fw_amp:.4f})")

        # Build output DataFrame
        out = pd.DataFrame({
            "brand": "new_balance",
            "region": region,
            "product_line": product_line,
            "week_start": series.index,
            "metric_name": METRIC_NAME,
            "observed": result.observed,
            "trend": result.trend,
            "seasonal": seasonal_total,
            "residual": result.resid,
            "decomposition_method": DECOMPOSITION_METHOD,
        })

        results[label] = {
            "result": result,
            "dataframe": out,
            "series": series,
            "product_line": product_line,
            "region": region,
            "resid_var": resid_var,
            "resid_std": resid_std,
            "seasonal_amp": seasonal_amp,
            "annual_amp": annual_amp,
            "quarterly_amp": quarterly_amp,
            "ss_fw_ratio": ss_fw_ratio,
            "ss_amp": ss_amp,
            "fw_amp": fw_amp,
        }

    return results


# DATABASE WRITE

def save_to_db(results):
    """Insert product decomposition results into mart.seasonal_components."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clear previous product-level MSTL results
            cur.execute("""
                DELETE FROM mart.seasonal_components
                WHERE product_line IS NOT NULL
                  AND decomposition_method = %s
            """, (DECOMPOSITION_METHOD,))
            deleted = cur.rowcount
            if deleted > 0:
                print(f"  Deleted {deleted} existing product MSTL rows")

            total = 0
            for label, data in results.items():
                df = data["dataframe"]
                for _, row in df.iterrows():
                    cur.execute("""
                        INSERT INTO mart.seasonal_components
                            (brand, region, product_line, week_start,
                             metric_name, observed, trend, seasonal,
                             residual, decomposition_method)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        row["brand"], row["region"], row["product_line"],
                        row["week_start"], row["metric_name"],
                        row["observed"], row["trend"], row["seasonal"],
                        row["residual"], row["decomposition_method"],
                    ))
                total += len(df)

            conn.commit()
            print(f"  Inserted {total} rows into mart.seasonal_components (products)")


# VISUALIZATION

def plot_product_decomposition(product_line, region, result, series):
    """5-panel MSTL decomposition: observed, trend, annual, quarterly, residual."""
    fig, axes = plt.subplots(5, 1, figsize=(14, 12), sharex=True)
    color = PRODUCT_COLORS.get(product_line, "#333333")

    seasonal_annual = result.seasonal.iloc[:, -1]
    seasonal_quarterly = result.seasonal.iloc[:, 0]

    components = [
        ("Observed", result.observed),
        ("Trend", result.trend),
        ("Seasonal (52w)", seasonal_annual),
        ("Seasonal (13w)", seasonal_quarterly),
        ("Residual", result.resid),
    ]

    for ax, (title, comp) in zip(axes, components):
        ax.plot(comp.index, comp.values, color=color, linewidth=1.2)
        ax.set_ylabel(title, fontsize=9)
        if title == "Residual":
            ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")

    axes[0].set_title(
        f"MSTL Decomposition: NB {product_line} ({region}) — periods=[13, 52]",
        fontsize=12, fontweight="bold"
    )
    axes[-1].set_xlabel("Week")

    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, f"mstl_{product_line}_{region}.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"    Saved: {fig_path}")


def plot_product_overlay(results):
    """Overlay seasonal components of all products per region."""
    for region in ["korea", "global"]:
        region_results = {k: v for k, v in results.items() if v["region"] == region}
        if not region_results:
            continue

        fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

        for label, data in sorted(region_results.items()):
            product = data["product_line"]
            result = data["result"]
            color = PRODUCT_COLORS.get(product, "#333333")

            seasonal_annual = result.seasonal.iloc[:, -1]
            seasonal_quarterly = result.seasonal.iloc[:, 0]

            axes[0].plot(seasonal_annual.index, seasonal_annual.values,
                         label=product, color=color, linewidth=1.2)
            axes[1].plot(seasonal_quarterly.index, seasonal_quarterly.values,
                         label=product, color=color, linewidth=1.2)

        axes[0].set_title(f"NB Product — Annual Seasonal (52w) Overlay — {region}",
                          fontsize=12, fontweight="bold")
        axes[0].set_ylabel("Seasonal (52w)")
        axes[0].axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
        axes[0].legend(loc="upper right", fontsize=9)

        axes[1].set_title(f"NB Product — Quarterly Seasonal (13w) Overlay — {region}",
                          fontsize=12, fontweight="bold")
        axes[1].set_ylabel("Seasonal (13w)")
        axes[1].set_xlabel("Week")
        axes[1].axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
        axes[1].legend(loc="upper right", fontsize=9)

        fig.tight_layout()
        fig_path = os.path.join(FIG_DIR, f"mstl_product_overlay_{region}.png")
        plt.savefig(fig_path, bbox_inches="tight")
        plt.close()
        print(f"  Saved: {fig_path}")


def plot_all(results):
    """Generate all product decomposition plots."""
    print("  Generating product decomposition plots...")
    for label, data in results.items():
        plot_product_decomposition(
            data["product_line"], data["region"],
            data["result"], data["series"]
        )

    print("  Generating product overlay plots...")
    plot_product_overlay(results)


# SUMMARY

def print_summary(results):
    """Print summary with season strength and SS/FW ratio re-verification."""
    print("\n  === NB Product Line — MSTL Decomposition Summary ===\n")
    header = (f"  {'Product':<10} {'Region':<8} {'Weeks':>5} "
              f"{'Ann_Amp':>9} {'Qtr_Amp':>9} {'Resid_Std':>10} "
              f"{'SS/FW':>7} {'S0_H2_Ref':>10}")
    print(header)
    print("  " + "-" * len(header.strip()))

    # Stage 0 H2 reference values
    s0_ref = {"530_korea": 1.18, "992_korea": 0.93}

    for label, data in sorted(results.items()):
        ref = s0_ref.get(label, "")
        ref_str = f"{ref:.2f}" if ref else "-"

        print(f"  {data['product_line']:<10} {data['region']:<8} "
              f"{len(data['series']):>5} "
              f"{data['annual_amp']:>9.4f} {data['quarterly_amp']:>9.4f} "
              f"{data['resid_std']:>10.4f} "
              f"{data['ss_fw_ratio']:>7.4f} {ref_str:>10}")

    print("  SS/FW ratio: > 1.0 = SS-dominant, < 1.0 = FW-dominant")
    print("  S0_H2_Ref: Stage 0 Hypothesis 2 reference value (single-season STL)")


# CLI / MAIN

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 3 Step A2: NB product line MSTL decomposition"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Decompose and print summary without DB write or plot")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Stage 3 Step A2: NB Product Line Decomposition (MSTL)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = decompose_all()

    if not results:
        print("  [ERROR] No decomposition results produced")
        return

    print_summary(results)

    if not args.dry_run:
        save_to_db(results)
        plot_all(results)

    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
