"""
Stage 5 Track B — MSTL Residual Anomaly Detection

Extracts MSTL residuals from mart.seasonal_components (Stage 3),
computes per-series standardized residuals, and flags anomalies.

Two thresholds applied:
  - |z| > 2.0 (primary, matches Stage 2 z-score baseline for fair comparison)
  - |z| > 3.0 (sensitivity analysis)

Each of the 8 brand x region series is analyzed independently (advisor decision #4).
Results INSERT to mart.anomaly_log with detection_method = 'mstl_residual'.

Usage:
    python analysis/anomaly_mstl_residual.py --inspect     # show seasonal_components schema
    python analysis/anomaly_mstl_residual.py               # run detection + insert
    python analysis/anomaly_mstl_residual.py --dry-run     # run detection, no insert
"""

# stdlib
import argparse
import os
import sys

# third-party
import pandas as pd
import numpy as np
from scipy import stats as sp_stats

# local
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import get_conn

# ================================================================
# CONSTANTS
# ================================================================

THRESHOLDS = [2.0, 3.0]
PRIMARY_THRESHOLD = 2.0
FIG_DIR = "figures/anomaly"
os.makedirs(FIG_DIR, exist_ok=True)


# ================================================================
# PREFLIGHT: Schema inspection
# ================================================================

def inspect_schema(conn):
    """Print mart.seasonal_components column names and sample row."""
    query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'mart' AND table_name = 'seasonal_components'
        ORDER BY ordinal_position;
    """
    df = pd.read_sql(query, conn)
    print("mart.seasonal_components columns:")
    for _, row in df.iterrows():
        print(f"  {row['column_name']:30s} {row['data_type']}")

    count = pd.read_sql(
        "SELECT COUNT(*) AS n FROM mart.seasonal_components;", conn
    )
    print(f"\nTotal rows: {count['n'].iloc[0]}")

    sample = pd.read_sql(
        "SELECT * FROM mart.seasonal_components LIMIT 3;", conn
    )
    print(f"\nSample rows:\n{sample.to_string()}")

    # Check decomposition methods present
    methods = pd.read_sql(
        "SELECT DISTINCT decomposition_method FROM mart.seasonal_components;", conn
    )
    print(f"\nDecomposition methods: {methods['decomposition_method'].tolist()}")

    # Check product_line values
    pl = pd.read_sql(
        "SELECT DISTINCT product_line FROM mart.seasonal_components;", conn
    )
    print(f"Product lines: {pl['product_line'].tolist()}")


# ================================================================
# DATA EXTRACTION
# ================================================================

def fetch_mstl_residuals(conn):
    """Fetch MSTL residuals for brand-level (product_line IS NULL) series."""
    query = """
        SELECT brand, region, week_start, residual
        FROM mart.seasonal_components
        WHERE decomposition_method = 'MSTL'
          AND product_line IS NULL
        ORDER BY brand, region, week_start;
    """
    df = pd.read_sql(query, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    df["residual"] = pd.to_numeric(df["residual"], errors="coerce")
    print(f"Fetched {len(df)} MSTL residual rows")
    print(f"  Series: {df.groupby(['brand', 'region']).ngroups} (expected 8)")
    return df


def fetch_stage2_anomalies(conn):
    """Fetch existing Stage 2 z-score anomalies for comparison."""
    query = """
        SELECT brand, detected_date, anomaly_type, z_score, severity_score,
               detection_method, metric_name
        FROM mart.anomaly_log
        WHERE detection_method = 'rolling_zscore_8w'
        ORDER BY brand, detected_date;
    """
    df = pd.read_sql(query, conn)
    df["detected_date"] = pd.to_datetime(df["detected_date"])
    print(f"Fetched {len(df)} Stage 2 z-score anomalies")
    return df


# ================================================================
# ANOMALY DETECTION
# ================================================================

def compute_residual_stats(df):
    """Compute per-series residual statistics for advisor reference."""
    stats_rows = []
    for (brand, region), grp in df.groupby(["brand", "region"]):
        r = grp["residual"].dropna()
        stats_rows.append({
            "brand": brand,
            "region": region,
            "n_weeks": len(r),
            "mean": r.mean(),
            "std": r.std(),
            "skewness": sp_stats.skew(r),
            "kurtosis": sp_stats.kurtosis(r),
            "min": r.min(),
            "max": r.max(),
            "abs_max_z": (r.abs() / r.std()).max() if r.std() > 0 else np.nan,
        })
    stats_df = pd.DataFrame(stats_rows)
    print("\nResidual statistics per series:")
    print(stats_df.to_string(index=False, float_format="{:.4f}".format))
    return stats_df


def detect_anomalies(df, threshold):
    """Flag anomalies where |residual / std| > threshold, per series."""
    results = []
    for (brand, region), grp in df.groupby(["brand", "region"]):
        r = grp["residual"].dropna()
        std = r.std()
        if std == 0 or np.isnan(std):
            print(f"  [WARN] {brand}/{region} std=0, skipping")
            continue

        z_scores = r / std
        mask = z_scores.abs() > threshold
        anomalies = grp.loc[mask].copy()
        anomalies["z_score"] = z_scores.loc[mask]
        anomalies["threshold"] = threshold
        results.append(anomalies)

    if results:
        result_df = pd.concat(results, ignore_index=True)
    else:
        result_df = pd.DataFrame()

    return result_df


def classify_anomaly(z_val):
    """Classify anomaly type based on z-score sign."""
    if z_val > 0:
        return "spike"
    else:
        return "dip"


def build_anomaly_log_rows(anomalies_df, threshold):
    """Build rows for mart.anomaly_log INSERT."""
    rows = []
    for _, row in anomalies_df.iterrows():
        z = float(row["z_score"])
        rows.append({
            "brand": row["brand"],
            "product_line": None,
            "metric_name": "search_index",
            "detected_date": row["week_start"],
            "anomaly_type": classify_anomaly(z),
            "detection_method": f"mstl_residual_{threshold:.1f}",
            "severity_score": min(abs(z) / 5.0, 1.0),  # normalize to 0-1 scale
            "z_score": round(z, 4),
            "description": f"MSTL residual |z|>{threshold:.1f} ({row['region']})",
        })
    return pd.DataFrame(rows)


# ================================================================
# DATABASE INSERT
# ================================================================

def clear_existing_mstl_anomalies(conn):
    """Remove prior MSTL residual anomaly rows (idempotent re-run)."""
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM mart.anomaly_log
            WHERE detection_method LIKE 'mstl_residual_%';
        """)
        deleted = cur.rowcount
        conn.commit()
    if deleted > 0:
        print(f"Cleared {deleted} existing mstl_residual anomaly rows")


def insert_anomaly_log(conn, log_df):
    """INSERT anomaly rows to mart.anomaly_log."""
    if log_df.empty:
        print("No anomalies to insert")
        return 0

    with conn.cursor() as cur:
        for _, row in log_df.iterrows():
            cur.execute("""
                INSERT INTO mart.anomaly_log
                    (brand, product_line, metric_name, detected_date,
                     anomaly_type, detection_method, severity_score,
                     z_score, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                row["brand"], row["product_line"], row["metric_name"],
                row["detected_date"], row["anomaly_type"],
                row["detection_method"], row["severity_score"],
                row["z_score"], row["description"],
            ))
        conn.commit()
    print(f"Inserted {len(log_df)} anomaly rows")
    return len(log_df)


# ================================================================
# SUMMARY & COMPARISON PREP
# ================================================================

def print_summary(anomalies_2, anomalies_3, stats_df):
    """Print detection summary for both thresholds."""
    print("\n" + "=" * 64)
    print("MSTL RESIDUAL ANOMALY DETECTION SUMMARY")
    print("=" * 64)

    for threshold, anom_df in [(2.0, anomalies_2), (3.0, anomalies_3)]:
        n_anom = len(anom_df)
        total_weeks = int(stats_df["n_weeks"].sum()) if not stats_df.empty else 0
        rate = n_anom / total_weeks * 100 if total_weeks > 0 else 0

        print(f"\nThreshold |z| > {threshold:.1f}:")
        print(f"  Total anomalies: {n_anom} / {total_weeks} weeks ({rate:.1f}%)")

        if not anom_df.empty:
            by_series = (
                anom_df.groupby(["brand", "region"])
                .size()
                .reset_index(name="count")
            )
            print("  Per series:")
            for _, r in by_series.iterrows():
                print(f"    {r['brand']:15s} {r['region']:8s} {r['count']:3d}")

            by_type = anom_df.groupby("anomaly_type").size()
            print(f"  Spikes: {by_type.get('spike', 0)}, Dips: {by_type.get('dip', 0)}")

            # Top 5 by severity
            top = anom_df.nlargest(5, "z_score", keep="first")
            print("  Top 5 spikes:")
            for _, r in top.iterrows():
                print(f"    {r['brand']:15s} {r['region']:8s} "
                      f"{r['week_start'].strftime('%Y-%m-%d')} z={r['z_score']:+.2f}")

            bottom = anom_df.nsmallest(5, "z_score", keep="first")
            print("  Top 5 dips:")
            for _, r in bottom.iterrows():
                print(f"    {r['brand']:15s} {r['region']:8s} "
                      f"{r['week_start'].strftime('%Y-%m-%d')} z={r['z_score']:+.2f}")


def save_anomaly_csv(anomalies_2, anomalies_3):
    """Save anomaly lists as CSV for downstream comparison scripts."""
    out_dir = "data/anomaly"
    os.makedirs(out_dir, exist_ok=True)

    if not anomalies_2.empty:
        path_2 = os.path.join(out_dir, "mstl_residual_anomalies_2.0.csv")
        anomalies_2.to_csv(path_2, index=False)
        print(f"Saved: {path_2}")

    if not anomalies_3.empty:
        path_3 = os.path.join(out_dir, "mstl_residual_anomalies_3.0.csv")
        anomalies_3.to_csv(path_3, index=False)
        print(f"Saved: {path_3}")


# ================================================================
# VISUALIZATION
# ================================================================

def plot_residual_anomalies(df, anomalies_2, anomalies_3):
    """Plot 8 residual time series with anomaly points marked."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "AppleGothic",
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "axes.grid": True,
        "grid.alpha": 0.3,
    })

    brand_colors = {
        "new_balance": "#E74C3C",
        "nike": "#FF6B00",
        "adidas": "#3498DB",
        "puma": "#2ECC71",
    }

    fig, axes = plt.subplots(4, 2, figsize=(16, 20), sharex=True)
    fig.suptitle("MSTL Residual Anomalies (|z|>2.0 red, |z|>3.0 black)", fontsize=14)

    series_list = sorted(df.groupby(["brand", "region"]).groups.keys())

    for idx, (brand, region) in enumerate(series_list):
        row_idx = idx // 2
        col_idx = idx % 2
        ax = axes[row_idx, col_idx]

        mask = (df["brand"] == brand) & (df["region"] == region)
        series = df.loc[mask].sort_values("week_start")

        color = brand_colors.get(brand, "#888888")
        ax.plot(series["week_start"], series["residual"],
                color=color, alpha=0.6, linewidth=0.8)

        std = series["residual"].std()
        ax.axhline(y=2.0 * std, color="red", linestyle="--", alpha=0.4, linewidth=0.7)
        ax.axhline(y=-2.0 * std, color="red", linestyle="--", alpha=0.4, linewidth=0.7)
        ax.axhline(y=3.0 * std, color="black", linestyle="--", alpha=0.3, linewidth=0.7)
        ax.axhline(y=-3.0 * std, color="black", linestyle="--", alpha=0.3, linewidth=0.7)
        ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3, linewidth=0.5)

        # Mark anomalies (threshold 2.0)
        anom2 = anomalies_2.loc[
            (anomalies_2["brand"] == brand) & (anomalies_2["region"] == region)
        ]
        if not anom2.empty:
            ax.scatter(anom2["week_start"], anom2["residual"],
                       color="red", s=25, zorder=5, label="|z|>2.0")

        # Mark anomalies (threshold 3.0)
        anom3 = anomalies_3.loc[
            (anomalies_3["brand"] == brand) & (anomalies_3["region"] == region)
        ]
        if not anom3.empty:
            ax.scatter(anom3["week_start"], anom3["residual"],
                       color="black", s=40, zorder=6, marker="x", label="|z|>3.0")

        ax.set_title(f"{brand} / {region}")
        ax.set_ylabel("Residual")
        if not anom2.empty or not anom3.empty:
            ax.legend(fontsize=8)

    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "mstl_residual_anomalies_8panel.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ================================================================
# MAIN
# ================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 5 Track B: MSTL residual anomaly detection"
    )
    parser.add_argument("--inspect", action="store_true",
                        help="Inspect mart.seasonal_components schema and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run detection without DB insert")
    return parser.parse_args()


def main():
    args = parse_args()

    with get_conn() as conn:

        # Preflight schema inspection
        if args.inspect:
            inspect_schema(conn)
            return

        # Step B1: Extract MSTL residuals
        print("Step B1: Extracting MSTL residuals")
        df = fetch_mstl_residuals(conn)

        if df.empty:
            print("[ERROR] No MSTL residuals found. Check mart.seasonal_components.")
            sys.exit(1)

        # Residual statistics (useful for advisor threshold review)
        stats_df = compute_residual_stats(df)

        # Step B2: Anomaly detection at both thresholds
        print("\nStep B2: Detecting anomalies")
        anomalies_2 = detect_anomalies(df, threshold=2.0)
        anomalies_3 = detect_anomalies(df, threshold=3.0)

        # Add anomaly_type classification
        if not anomalies_2.empty:
            anomalies_2["anomaly_type"] = anomalies_2["z_score"].apply(classify_anomaly)
        if not anomalies_3.empty:
            anomalies_3["anomaly_type"] = anomalies_3["z_score"].apply(classify_anomaly)

        # Summary
        print_summary(anomalies_2, anomalies_3, stats_df)

        # Save CSV for downstream scripts
        save_anomaly_csv(anomalies_2, anomalies_3)

        # Visualization
        print("\nGenerating plots")
        plot_residual_anomalies(df, anomalies_2, anomalies_3)

        # DB insert (primary threshold only)
        if not args.dry_run:
            print("\nInserting to mart.anomaly_log")
            clear_existing_mstl_anomalies(conn)

            # Insert primary threshold (2.0) anomalies
            log_2 = build_anomaly_log_rows(anomalies_2, threshold=2.0)
            n_2 = insert_anomaly_log(conn, log_2)

            # Insert sensitivity threshold (3.0) anomalies
            log_3 = build_anomaly_log_rows(anomalies_3, threshold=3.0)
            n_3 = insert_anomaly_log(conn, log_3)

            print(f"\nTotal inserted: {n_2 + n_3} "
                  f"(2.0: {n_2}, 3.0: {n_3})")
        else:
            print("\n[DRY RUN] Skipping DB insert")

        # Fetch Stage 2 anomalies for quick cross-reference
        print("\nStage 2 z-score baseline reference:")
        stage2 = fetch_stage2_anomalies(conn)
        if not stage2.empty:
            print(f"  Total Stage 2 anomalies: {len(stage2)}")
            by_brand = stage2.groupby("brand").size()
            for brand, cnt in by_brand.items():
                print(f"    {brand:15s} {cnt:3d}")


if __name__ == "__main__":
    main()
