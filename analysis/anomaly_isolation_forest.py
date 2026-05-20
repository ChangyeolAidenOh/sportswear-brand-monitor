"""
Stage 5 Track C — Isolation Forest Anomaly Detection

Applies sklearn IsolationForest to MSTL residuals from mart.seasonal_components.
Each of the 8 brand x region series is modeled independently (advisor decision #4).
contamination=0.05 to match Stage 2 anomaly rate (advisor decision #2).

Usage:
    python analysis/anomaly_isolation_forest.py               # run detection + insert
    python analysis/anomaly_isolation_forest.py --dry-run     # run detection, no insert
"""

import argparse
import os
import sys

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import get_conn

# CONSTANTS

CONTAMINATION = 0.05
RANDOM_STATE = 42
FIG_DIR = "figures/anomaly"
os.makedirs(FIG_DIR, exist_ok=True)


# DATA EXTRACTION

def fetch_mstl_residuals(conn):
    """Fetch MSTL residuals for brand-level series."""
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
    return df


# ISOLATION FOREST DETECTION

def run_isolation_forest(df):
    """Run Isolation Forest per series. Returns DataFrame of all anomalies."""
    all_anomalies = []

    for (brand, region), grp in df.groupby(["brand", "region"]):
        series = grp.sort_values("week_start").copy()
        residuals = series["residual"].dropna().values.reshape(-1, 1)

        if len(residuals) < 20:
            print(f"  [WARN] {brand}/{region} has {len(residuals)} rows, skipping")
            continue

        model = IsolationForest(
            contamination=CONTAMINATION,
            random_state=RANDOM_STATE,
            n_estimators=100,
        )
        preds = model.fit_predict(residuals)
        scores = model.decision_function(residuals)

        # -1 = anomaly, 1 = normal
        anom_mask = preds == -1
        n_anom = anom_mask.sum()

        valid_idx = series["residual"].dropna().index
        series_valid = series.loc[valid_idx].copy()
        series_valid["if_prediction"] = preds
        series_valid["if_score"] = scores

        anomalies = series_valid.loc[anom_mask].copy()
        anomalies["anomaly_type"] = anomalies["residual"].apply(
            lambda x: "spike" if x > 0 else "dip"
        )

        # Compute a z-score equivalent for severity comparison
        std = series_valid["residual"].std()
        if std > 0:
            anomalies["z_score"] = anomalies["residual"] / std
        else:
            anomalies["z_score"] = 0.0

        print(f"  {brand:15s} {region:8s} anomalies: {n_anom}/{len(residuals)} "
              f"({n_anom/len(residuals)*100:.1f}%)")

        all_anomalies.append(anomalies)

    if all_anomalies:
        result = pd.concat(all_anomalies, ignore_index=True)
    else:
        result = pd.DataFrame()

    return result


# DATABASE INSERT

def clear_existing_if_anomalies(conn):
    """Remove prior Isolation Forest anomaly rows."""
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM mart.anomaly_log
            WHERE detection_method = 'isolation_forest';
        """)
        deleted = cur.rowcount
        conn.commit()
    if deleted > 0:
        print(f"Cleared {deleted} existing isolation_forest anomaly rows")


def insert_anomaly_log(conn, anomalies_df):
    """INSERT IF anomaly rows to mart.anomaly_log."""
    if anomalies_df.empty:
        print("No anomalies to insert")
        return 0

    with conn.cursor() as cur:
        for _, row in anomalies_df.iterrows():
            z = float(row["z_score"])
            cur.execute("""
                INSERT INTO mart.anomaly_log
                    (brand, product_line, metric_name, detected_date,
                     anomaly_type, detection_method, severity_score,
                     z_score, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                row["brand"], None, "search_index",
                row["week_start"], row["anomaly_type"],
                "isolation_forest",
                min(abs(z) / 5.0, 1.0),
                round(z, 4),
                f"IF contamination={CONTAMINATION} ({row['region']}) "
                f"score={row['if_score']:.4f}",
            ))
        conn.commit()
    print(f"Inserted {len(anomalies_df)} anomaly rows")
    return len(anomalies_df)


# VISUALIZATION

def plot_if_anomalies(df, anomalies):
    """Plot 8-panel residual series with IF anomaly markers."""
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
    fig.suptitle(
        f"Isolation Forest Anomalies (contamination={CONTAMINATION})", fontsize=14
    )

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
        ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3, linewidth=0.5)

        anom = anomalies.loc[
            (anomalies["brand"] == brand) & (anomalies["region"] == region)
        ]
        if not anom.empty:
            ax.scatter(anom["week_start"], anom["residual"],
                       color="purple", s=30, zorder=5,
                       marker="D", label=f"IF ({len(anom)})")
            ax.legend(fontsize=8)

        ax.set_title(f"{brand} / {region}")
        ax.set_ylabel("Residual")

    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "isolation_forest_anomalies_8panel.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# SUMMARY

def print_summary(anomalies, df):
    """Print IF detection summary."""
    print("\n" + "=" * 64)
    print("=" * 64)

    total_weeks = len(df.dropna(subset=["residual"]))
    n_anom = len(anomalies)
    rate = n_anom / total_weeks * 100 if total_weeks > 0 else 0

    print(f"Contamination: {CONTAMINATION}")
    print(f"Total anomalies: {n_anom} / {total_weeks} weeks ({rate:.1f}%)")

    if not anomalies.empty:
        by_type = anomalies["anomaly_type"].value_counts()
        print(f"Spikes: {by_type.get('spike', 0)}, Dips: {by_type.get('dip', 0)}")

        top = anomalies.nlargest(5, "z_score", keep="first")
        print("Top 5 spikes:")
        for _, r in top.iterrows():
            print(f"  {r['brand']:15s} {r['region']:8s} "
                  f"{r['week_start'].strftime('%Y-%m-%d')} "
                  f"z={r['z_score']:+.2f} if_score={r['if_score']:.4f}")


def save_anomaly_csv(anomalies):
    """Save IF anomaly list as CSV."""
    out_dir = "data/anomaly"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "isolation_forest_anomalies.csv")
    anomalies.to_csv(path, index=False)
    print(f"Saved: {path}")


# MAIN

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 5 Track C: Isolation Forest anomaly detection"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Run detection without DB insert")
    return parser.parse_args()


def main():
    args = parse_args()

    with get_conn() as conn:
        # Extract MSTL residuals
        df = fetch_mstl_residuals(conn)

        if df.empty:
            print("[ERROR] No MSTL residuals found")
            sys.exit(1)

        # Run Isolation Forest per series
        print(f"\nRunning Isolation Forest (contamination={CONTAMINATION})")
        anomalies = run_isolation_forest(df)

        # Summary
        print_summary(anomalies, df)

        # Save CSV
        if not anomalies.empty:
            save_anomaly_csv(anomalies)

        # Visualization
        plot_if_anomalies(df, anomalies)

        # DB insert
        if not args.dry_run:
            clear_existing_if_anomalies(conn)
            insert_anomaly_log(conn, anomalies)
        else:
            print("\n[DRY RUN] Skipping DB insert")


if __name__ == "__main__":
    main()
