"""
Stage 4 Track B: Korea-Global Lead-Lag Analysis (DTW)
Re-examines Stage 0 H1 cross-correlation -167w anomaly using Dynamic Time Warping.

Steps:
  B1: Time series extraction (4 brands x 2 regions from brand_kpi_weekly)
  B2: DTW distance + warping path computation
  B3: Visualization (alignment plots, cross-correlation comparison)
  B4: Quantified metrics for Stage 7 Korea-Global Bridge

Usage:
  python analysis/dtw_korea_global.py
  python analysis/dtw_korea_global.py --step b1     # extraction only
  python analysis/dtw_korea_global.py --step b2     # DTW computation
  python analysis/dtw_korea_global.py --deseason trend   # use MSTL trend
  python analysis/dtw_korea_global.py --deseason detrended  # use detrended
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import argparse
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from database.connection import get_conn

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "axes.grid": True,
    "grid.alpha": 0.3,
})

# CONSTANTS

BRANDS = ["nike", "adidas", "puma", "new_balance"]
BRAND_COLORS = {
    "nike": "#FF6B00",
    "adidas": "#3498DB",
    "puma": "#2ECC71",
    "new_balance": "#E74C3C",
}

FIG_DIR = "figures/dtw"
DOCS_DIR = "docs"

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

REPORT_LINES = []


def log(msg=""):
    print(msg)
    REPORT_LINES.append(msg)


def section(title):
    log("")
    log(f"## {title}")
    log("")


# STEP B1: Time Series Extraction

def extract_brand_search():
    """Extract search_index from mart.brand_kpi_weekly (4 brands x 2 regions)."""
    query = """
        SELECT brand, region, week_start, search_index
        FROM mart.brand_kpi_weekly
        WHERE search_index IS NOT NULL
        ORDER BY brand, region, week_start
    """
    with get_conn() as conn:
        df = pd.read_sql(query, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def extract_seasonal_trend():
    """Extract MSTL trend and compute detrended from mart.seasonal_components."""
    query = """
        SELECT brand, region, week_start, observed, trend, residual
        FROM mart.seasonal_components
        WHERE product_line IS NULL
        ORDER BY brand, region, week_start
    """
    with get_conn() as conn:
        df = pd.read_sql(query, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    df["detrended"] = df["observed"] - df["trend"]
    return df


def step_b1():
    """Execute Step B1: extract and prepare Korea vs Global pairs."""
    section("Step B1: Time Series Extraction")

    search_df = extract_brand_search()
    seasonal_df = extract_seasonal_trend()

    # Merge
    merged = pd.merge(
        search_df, seasonal_df[["brand", "region", "week_start", "trend", "detrended", "residual"]],
        on=["brand", "region", "week_start"],
        how="inner",
    )

    log(f"  rows: {len(merged)}")
    log(f"  period: {merged['week_start'].min()} ~ {merged['week_start'].max()}")
    log(f"  brands: {sorted(merged['brand'].unique())}")

    # Summary per brand x region
    log("")
    log("| Brand | Region | N_weeks | Search Mean | Search Std |")
    log("|---|---|---|---|---|")
    for (brand, region), grp in merged.groupby(["brand", "region"]):
        log(
            f"| {brand} | {region} | {len(grp)} "
            f"| {grp['search_index'].mean():.2f} "
            f"| {grp['search_index'].std():.2f} |"
        )

    return {"merged": merged}


# STEP B2: DTW Distance + Warping Path

def compute_dtw_pair(korea_series, global_series):
    """Compute DTW distance and warping path between Korea and Global series."""
    try:
        from tslearn.metrics import dtw_path
        path, distance = dtw_path(
            korea_series.reshape(-1, 1),
            global_series.reshape(-1, 1),
        )
        return path, distance
    except ImportError:
        # Fallback to fastdtw
        from fastdtw import fastdtw
        from scipy.spatial.distance import euclidean
        distance, path = fastdtw(
            korea_series.reshape(-1, 1),
            global_series.reshape(-1, 1),
            dist=euclidean,
        )
        return path, distance


def compute_lag_from_path(path):
    """Extract lead-lag statistics from DTW warping path."""
    path = np.array(path)
    lags = path[:, 0] - path[:, 1]  # positive = Korea leads

    return {
        "mean_lag": round(np.mean(lags), 2),
        "median_lag": round(np.median(lags), 2),
        "std_lag": round(np.std(lags), 2),
        "min_lag": int(np.min(lags)),
        "max_lag": int(np.max(lags)),
        "direction": "Korea leads" if np.mean(lags) > 0.5 else
                     "Global leads" if np.mean(lags) < -0.5 else
                     "Synchronous",
    }


def z_normalize(series):
    """Z-normalize a time series for scale-invariant DTW."""
    std = series.std()
    if std == 0:
        return series - series.mean()
    return (series - series.mean()) / std


def step_b2(data, deseason="search_index"):
    """Execute Step B2: DTW computation for all 4 brands."""
    section("Step B2: DTW Distance Computation")

    merged = data["merged"]
    log(f"  input series: {deseason}")

    dtw_results = []

    for brand in BRANDS:
        korea = merged[(merged["brand"] == brand) & (merged["region"] == "korea")].copy()
        glob = merged[(merged["brand"] == brand) & (merged["region"] == "global")].copy()

        korea = korea.sort_values("week_start").reset_index(drop=True)
        glob = glob.sort_values("week_start").reset_index(drop=True)

        # Align to common weeks
        common_weeks = set(korea["week_start"]) & set(glob["week_start"])
        korea = korea[korea["week_start"].isin(common_weeks)].reset_index(drop=True)
        glob = glob[glob["week_start"].isin(common_weeks)].reset_index(drop=True)

        if len(korea) < 30:
            log(f"  [WARN] {brand}: insufficient common weeks ({len(korea)})")
            continue

        kr_series = z_normalize(korea[deseason].values.astype(float))
        gl_series = z_normalize(glob[deseason].values.astype(float))

        path, distance = compute_dtw_pair(kr_series, gl_series)
        lag_stats = compute_lag_from_path(path)

        # Cross-correlation for comparison
        from scipy.signal import correlate
        corr = correlate(kr_series, gl_series, mode="full")
        corr = corr / (len(kr_series) * kr_series.std() * gl_series.std())
        lags_cc = np.arange(-(len(kr_series) - 1), len(kr_series))
        best_lag_cc = lags_cc[np.argmax(corr)]

        result = {
            "brand": brand,
            "n_weeks": len(korea),
            "dtw_distance": round(distance, 4),
            "dtw_normalized": round(distance / len(korea), 4),
            **lag_stats,
            "cc_best_lag": int(best_lag_cc),
            "cc_max_corr": round(np.max(corr), 4),
            "deseason_method": deseason,
        }
        dtw_results.append(result)

        log(f"  {brand}: DTW={distance:.2f}, norm={distance/len(korea):.4f}, "
            f"lag={lag_stats['mean_lag']:.1f}w ({lag_stats['direction']}), "
            f"CC best lag={best_lag_cc}")

    dtw_df = pd.DataFrame(dtw_results)
    data["dtw"] = dtw_df
    data["deseason"] = deseason

    # Summary table
    log("")
    log("| Brand | DTW dist | Norm DTW | Mean Lag | Direction | CC Lag | Stage 0 Ref |")
    log("|---|---|---|---|---|---|---|")
    for _, row in dtw_df.iterrows():
        s0_ref = "-167w" if row["brand"] == "new_balance" else ""
        log(
            f"| {row['brand']} | {row['dtw_distance']:.2f} "
            f"| {row['dtw_normalized']:.4f} | {row['mean_lag']:.1f}w "
            f"| {row['direction']} | {row['cc_best_lag']}w | {s0_ref} |"
        )

    return data


# STEP B3: Visualization

def plot_dtw_alignment(korea_vals, global_vals, path, brand, weeks, deseason, fig_dir):
    """Plot DTW alignment between Korea and Global series."""
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [3, 3, 2]})
    path = np.array(path)

    # Panel 1: Korea series
    axes[0].plot(range(len(korea_vals)), korea_vals, color=BRAND_COLORS.get(brand, "#333"), linewidth=1.2)
    axes[0].set_ylabel("Korea (z-norm)")
    axes[0].set_title(f"DTW Alignment: {brand} — Korea vs Global ({deseason})")

    # Panel 2: Global series
    axes[1].plot(range(len(global_vals)), global_vals, color=BRAND_COLORS.get(brand, "#333"),
                 linewidth=1.2, linestyle="--")
    axes[1].set_ylabel("Global (z-norm)")

    # Panel 3: Lag profile over time
    lags = path[:, 0] - path[:, 1]
    axes[2].plot(range(len(lags)), lags, color=BRAND_COLORS.get(brand, "#333"), linewidth=0.8)
    axes[2].axhline(0, color="gray", linestyle=":", linewidth=0.5)
    axes[2].fill_between(range(len(lags)), lags, 0, alpha=0.15,
                         color=BRAND_COLORS.get(brand, "#333"))
    axes[2].set_ylabel("Lag (Korea - Global)")
    axes[2].set_xlabel("Warping path index")

    plt.tight_layout()
    fig_path = os.path.join(fig_dir, f"dtw_alignment_{brand}.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    return fig_path


def plot_dtw_summary(dtw_df, fig_dir):
    """Plot DTW distance comparison across brands."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    brands = dtw_df["brand"].values
    colors = [BRAND_COLORS.get(b, "#333") for b in brands]

    # DTW normalized distance
    axes[0].barh(brands, dtw_df["dtw_normalized"], color=colors, alpha=0.8)
    axes[0].set_xlabel("Normalized DTW Distance")
    axes[0].set_title("Korea-Global DTW Distance")

    # Mean lag
    axes[1].barh(brands, dtw_df["mean_lag"], color=colors, alpha=0.8)
    axes[1].axvline(0, color="gray", linestyle=":", linewidth=0.5)
    axes[1].set_xlabel("Mean Lag (weeks, + = Korea leads)")
    axes[1].set_title("Korea-Global Lead-Lag")

    plt.tight_layout()
    fig_path = os.path.join(fig_dir, "dtw_summary.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    return fig_path


def step_b3(data):
    """Execute Step B3: visualization of DTW results."""
    section("Step B3: Visualization")

    merged = data["merged"]
    dtw_df = data["dtw"]
    deseason = data["deseason"]

    for _, row in dtw_df.iterrows():
        brand = row["brand"]
        korea = merged[(merged["brand"] == brand) & (merged["region"] == "korea")].copy()
        glob = merged[(merged["brand"] == brand) & (merged["region"] == "global")].copy()

        korea = korea.sort_values("week_start").reset_index(drop=True)
        glob = glob.sort_values("week_start").reset_index(drop=True)

        common_weeks = sorted(set(korea["week_start"]) & set(glob["week_start"]))
        korea = korea[korea["week_start"].isin(common_weeks)].reset_index(drop=True)
        glob = glob[glob["week_start"].isin(common_weeks)].reset_index(drop=True)

        kr_vals = z_normalize(korea[deseason].values.astype(float))
        gl_vals = z_normalize(glob[deseason].values.astype(float))

        path, _ = compute_dtw_pair(kr_vals, gl_vals)
        fig_path = plot_dtw_alignment(kr_vals, gl_vals, path, brand, common_weeks, deseason, FIG_DIR)
        log(f"  saved: {fig_path}")

    # Summary chart
    summary_path = plot_dtw_summary(dtw_df, FIG_DIR)
    log(f"  saved: {summary_path}")

    return data


# STEP B4: Mart Table Output for Stage 7

def step_b4(data):
    """Execute Step B4: write DTW metrics to mart.korea_global_lag."""
    section("Step B4: Mart Table Output")

    dtw_df = data["dtw"]

    # Prepare records for DB insert
    records = []
    for _, row in dtw_df.iterrows():
        records.append({
            "brand": row["brand"],
            "dtw_distance": row["dtw_distance"],
            "dtw_normalized": row["dtw_normalized"],
            "mean_lag_weeks": row["mean_lag"],
            "median_lag_weeks": row["median_lag"],
            "lag_direction": row["direction"],
            "cc_best_lag_weeks": row["cc_best_lag"],
            "cc_max_corr": row["cc_max_corr"],
            "deseason_method": row["deseason_method"],
            "n_weeks": row["n_weeks"],
        })

    # Migration SQL for the new table
    migration_sql = """
-- Stage 4 Migration: Korea-Global DTW lag metrics
CREATE TABLE IF NOT EXISTS mart.korea_global_lag (
    id                  BIGSERIAL PRIMARY KEY,
    brand               brand_enum    NOT NULL,
    dtw_distance        NUMERIC(10,4),
    dtw_normalized      NUMERIC(10,6),
    mean_lag_weeks      NUMERIC(6,2),
    median_lag_weeks    NUMERIC(6,2),
    lag_direction       VARCHAR(20),          -- 'Korea leads','Global leads','Synchronous'
    cc_best_lag_weeks   SMALLINT,
    cc_max_corr         NUMERIC(6,4),
    deseason_method     VARCHAR(30),
    n_weeks             SMALLINT,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, deseason_method)
);
"""

    migration_path = "database/migrations/008_korea_global_lag.sql"
    os.makedirs(os.path.dirname(migration_path), exist_ok=True)

    with open(migration_path, "w", encoding="utf-8") as f:
        f.write(migration_sql)
    log(f"  migration written: {migration_path}")

    # Insert records
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Create table if not exists
                cur.execute(migration_sql)
                # Upsert records
                for rec in records:
                    cur.execute("""
                        INSERT INTO mart.korea_global_lag
                            (brand, dtw_distance, dtw_normalized, mean_lag_weeks,
                             median_lag_weeks, lag_direction, cc_best_lag_weeks,
                             cc_max_corr, deseason_method, n_weeks)
                        VALUES (%(brand)s, %(dtw_distance)s, %(dtw_normalized)s,
                                %(mean_lag_weeks)s, %(median_lag_weeks)s,
                                %(lag_direction)s, %(cc_best_lag_weeks)s,
                                %(cc_max_corr)s, %(deseason_method)s, %(n_weeks)s)
                        ON CONFLICT (brand, deseason_method) DO UPDATE SET
                            dtw_distance = EXCLUDED.dtw_distance,
                            dtw_normalized = EXCLUDED.dtw_normalized,
                            mean_lag_weeks = EXCLUDED.mean_lag_weeks,
                            median_lag_weeks = EXCLUDED.median_lag_weeks,
                            lag_direction = EXCLUDED.lag_direction,
                            cc_best_lag_weeks = EXCLUDED.cc_best_lag_weeks,
                            cc_max_corr = EXCLUDED.cc_max_corr,
                            n_weeks = EXCLUDED.n_weeks,
                            created_at = NOW()
                    """, rec)
            conn.commit()
        log(f"  inserted {len(records)} rows into mart.korea_global_lag")
    except Exception as e:
        log(f"  [WARN] DB insert failed: {e}")
        log("  records available in data['dtw'] DataFrame")

    return data


# REPORT GENERATION

def generate_report():
    """Write DTW results to markdown."""
    report_path = os.path.join(DOCS_DIR, "stage4_dtw_report.md")
    header = [
        "# Stage 4 Track B: Korea-Global Lead-Lag (DTW) Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Method:** Dynamic Time Warping (tslearn/fastdtw)",
        f"**Context:** Re-examination of Stage 0 H1 cross-correlation -167w anomaly",
        "",
        "---",
    ]
    with open(report_path, "w", encoding="utf-8") as f:
        for line in header + REPORT_LINES:
            f.write(line + "\n")
    print(f"\nReport saved: {report_path}")


# MAIN

def parse_args():
    parser = argparse.ArgumentParser(description="Stage 4 Track B: DTW Korea-Global")
    parser.add_argument(
        "--step", type=str, default="all",
        choices=["b1", "b2", "b3", "b4", "all"],
        help="Run a specific step or all",
    )
    parser.add_argument(
        "--deseason", type=str, default="search_index",
        choices=["search_index", "trend", "detrended", "residual"],
        help="Which series to use for DTW (awaiting advisor decision)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    log(f"Stage 4 Track B: DTW Korea-Global Lead-Lag")
    log(f"Started: {datetime.now()}")

    data = step_b1()

    if args.step in ("b2", "b3", "b4", "all"):
        data = step_b2(data, deseason=args.deseason)

    if args.step in ("b3", "all"):
        data = step_b3(data)

    if args.step in ("b4", "all"):
        data = step_b4(data)

    generate_report()


if __name__ == "__main__":
    main()
