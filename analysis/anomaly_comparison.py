"""
Stage 5 — 3-Way Anomaly Comparison

Compares three anomaly detection methods:
  1. Z-score baseline (Stage 2, re-derived from brand_kpi_weekly for region info)
  2. MSTL residual z-score (Track B)
  3. Isolation Forest on MSTL residuals (Track C)

Core deliverable: Stage 2 vs MSTL confusion matrix (advisor decision #5).
Also produces:
  - 3-way agreement table (8 series x method)
  - Co-occurring anomalies across brands (macro event candidates)
  - NB-only anomalies (brand-specific event candidates)
  - Comparison visualizations

Run AFTER anomaly_mstl_residual.py and anomaly_isolation_forest.py.

Usage:
    python analysis/anomaly_comparison.py
    python analysis/anomaly_comparison.py --inspect   # show Stage 2 anomaly_log contents
"""

# stdlib
import argparse
import os
import sys

# third-party
import pandas as pd
import numpy as np

# local
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import get_conn

# ================================================================
# CONSTANTS
# ================================================================

ZSCORE_THRESHOLD = 2.0
MSTL_CSV = "data/anomaly/mstl_residual_anomalies_2.0.csv"
IF_CSV = "data/anomaly/isolation_forest_anomalies.csv"
FIG_DIR = "figures/anomaly"
OUT_DIR = "data/anomaly"
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


# ================================================================
# PREFLIGHT
# ================================================================

def inspect_stage2(conn):
    """Show Stage 2 anomaly_log contents for region identification."""
    df = pd.read_sql("""
        SELECT brand, metric_name, detected_date, anomaly_type,
               detection_method, z_score, severity_score, description
        FROM mart.anomaly_log
        WHERE detection_method = 'z_score'
        ORDER BY brand, detected_date
        LIMIT 20;
    """, conn)
    print("Stage 2 anomaly_log sample (first 20 rows):")
    print(df.to_string(index=False))

    counts = pd.read_sql("""
        SELECT detection_method, COUNT(*) AS n
        FROM mart.anomaly_log
        GROUP BY detection_method
        ORDER BY detection_method;
    """, conn)
    print(f"\nAnomaly counts by method:\n{counts.to_string(index=False)}")

    # Check if region info is in description or metric_name
    desc_sample = pd.read_sql("""
        SELECT DISTINCT description FROM mart.anomaly_log
        WHERE detection_method = 'z_score' LIMIT 10;
    """, conn)
    print(f"\nDescription samples:\n{desc_sample.to_string(index=False)}")

    metric_sample = pd.read_sql("""
        SELECT DISTINCT metric_name FROM mart.anomaly_log
        WHERE detection_method = 'z_score';
    """, conn)
    print(f"\nMetric names:\n{metric_sample.to_string(index=False)}")


# ================================================================
# DATA LOADING
# ================================================================

def rederive_zscore_anomalies(conn, threshold=ZSCORE_THRESHOLD):
    """
    Re-derive Stage 2 z-score anomalies from brand_kpi_weekly.

    Stage 2 SQL (06_mart_anomaly_residuals.sql) used windowed AVG/STDDEV.
    We replicate the logic here to get (brand, region, week_start) triples.
    Uses 8-week rolling window matching Stage 2 approach.
    """
    df = pd.read_sql("""
        SELECT brand, region, week_start, search_index
        FROM mart.brand_kpi_weekly
        ORDER BY brand, region, week_start;
    """, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])

    anomalies = []
    for (brand, region), grp in df.groupby(["brand", "region"]):
        series = grp.sort_values("week_start").copy()
        series["rolling_mean"] = series["search_index"].rolling(
            window=8, min_periods=8
        ).mean()
        series["rolling_std"] = series["search_index"].rolling(
            window=8, min_periods=8
        ).std()

        series["z_score"] = (
            (series["search_index"] - series["rolling_mean"]) / series["rolling_std"]
        )

        mask = series["z_score"].abs() > threshold
        anom = series.loc[mask].copy()
        anom["anomaly_type"] = anom["z_score"].apply(
            lambda z: "spike" if z > 0 else "dip"
        )
        anomalies.append(anom)

    if anomalies:
        result = pd.concat(anomalies, ignore_index=True)
    else:
        result = pd.DataFrame()

    print(f"Re-derived z-score anomalies: {len(result)} (threshold={threshold})")
    return result


def load_mstl_anomalies():
    """Load MSTL residual anomalies from CSV (output of anomaly_mstl_residual.py)."""
    if not os.path.exists(MSTL_CSV):
        print(f"[ERROR] {MSTL_CSV} not found. Run anomaly_mstl_residual.py first.")
        return pd.DataFrame()
    df = pd.read_csv(MSTL_CSV)
    df["week_start"] = pd.to_datetime(df["week_start"])
    print(f"Loaded MSTL anomalies: {len(df)}")
    return df


def load_if_anomalies():
    """Load Isolation Forest anomalies from CSV (output of anomaly_isolation_forest.py)."""
    if not os.path.exists(IF_CSV):
        print(f"[ERROR] {IF_CSV} not found. Run anomaly_isolation_forest.py first.")
        return pd.DataFrame()
    df = pd.read_csv(IF_CSV)
    df["week_start"] = pd.to_datetime(df["week_start"])
    print(f"Loaded IF anomalies: {len(df)}")
    return df


# ================================================================
# CONFUSION MATRIX: Z-score vs MSTL
# ================================================================

def build_universe(conn):
    """Build full universe of (brand, region, week_start) from brand_kpi_weekly."""
    df = pd.read_sql("""
        SELECT DISTINCT brand, region, week_start
        FROM mart.brand_kpi_weekly
        ORDER BY brand, region, week_start;
    """, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def build_confusion_matrix(universe, zscore_anom, mstl_anom):
    """
    Build Stage 2 vs MSTL confusion matrix.

    Categories:
      - Both anomaly: true positive (both methods agree)
      - Z-score only: false positive (seasonal pattern caused z-score flag)
      - MSTL only: new discovery (deseasonalized signal reveals anomaly)
      - Neither: true negative (both agree normal)
    """
    # Create keys for set operations
    zscore_keys = set(
        zscore_anom[["brand", "region", "week_start"]].apply(tuple, axis=1)
    )
    mstl_keys = set(
        mstl_anom[["brand", "region", "week_start"]].apply(tuple, axis=1)
    )
    all_keys = set(
        universe[["brand", "region", "week_start"]].apply(tuple, axis=1)
    )

    both = zscore_keys & mstl_keys
    zscore_only = zscore_keys - mstl_keys
    mstl_only = mstl_keys - zscore_keys
    neither = all_keys - zscore_keys - mstl_keys

    print("\n" + "=" * 64)
    print("CONFUSION MATRIX: Z-score (Stage 2) vs MSTL Residual")
    print("=" * 64)
    print(f"  Both anomaly (agreement):     {len(both):5d}")
    print(f"  Z-score only (false positive): {len(zscore_only):5d}")
    print(f"  MSTL only (new discovery):     {len(mstl_only):5d}")
    print(f"  Neither (true negative):       {len(neither):5d}")
    print(f"  Total:                         {len(all_keys):5d}")
    print()
    print(f"  Z-score false positive rate: "
          f"{len(zscore_only)}/{len(zscore_keys)} = "
          f"{len(zscore_only)/max(len(zscore_keys),1)*100:.1f}% of Stage 2 anomalies "
          f"were seasonal artifacts")
    print(f"  MSTL new discovery rate: "
          f"{len(mstl_only)} anomalies not caught by Stage 2 z-score")

    # Per-brand breakdown
    print("\nPer-brand breakdown:")
    brands = sorted(set(k[0] for k in all_keys))
    regions = sorted(set(k[1] for k in all_keys))

    rows = []
    for brand in brands:
        for region in regions:
            b = sum(1 for k in both if k[0] == brand and k[1] == region)
            zo = sum(1 for k in zscore_only if k[0] == brand and k[1] == region)
            mo = sum(1 for k in mstl_only if k[0] == brand and k[1] == region)
            zk = sum(1 for k in zscore_keys if k[0] == brand and k[1] == region)
            mk = sum(1 for k in mstl_keys if k[0] == brand and k[1] == region)
            rows.append({
                "brand": brand,
                "region": region,
                "zscore_total": zk,
                "mstl_total": mk,
                "both": b,
                "zscore_only": zo,
                "mstl_only": mo,
            })
            print(f"  {brand:15s} {region:8s}  "
                  f"z={zk:2d}  mstl={mk:2d}  "
                  f"both={b:2d}  z_only={zo:2d}  mstl_only={mo:2d}")

    cm_df = pd.DataFrame(rows)

    # Detailed list of z-score only (false positives) for narrative
    if zscore_only:
        print("\nZ-score only (seasonal false positives) — top candidates:")
        fp_list = []
        for key in sorted(zscore_only, key=lambda k: (k[0], k[1], k[2])):
            brand, region, ws = key
            z_row = zscore_anom.loc[
                (zscore_anom["brand"] == brand) &
                (zscore_anom["region"] == region) &
                (zscore_anom["week_start"] == ws)
            ]
            z_val = z_row["z_score"].iloc[0] if not z_row.empty else np.nan
            fp_list.append({
                "brand": brand, "region": region,
                "week_start": ws, "z_score": z_val,
            })
        fp_df = pd.DataFrame(fp_list).sort_values("z_score", key=abs, ascending=False)
        print(fp_df.head(15).to_string(index=False))

    return cm_df, both, zscore_only, mstl_only


# ================================================================
# 3-WAY COMPARISON
# ================================================================

def three_way_comparison(universe, zscore_anom, mstl_anom, if_anom):
    """Build 3-way agreement table across methods."""
    zscore_keys = set(
        zscore_anom[["brand", "region", "week_start"]].apply(tuple, axis=1)
    )
    mstl_keys = set(
        mstl_anom[["brand", "region", "week_start"]].apply(tuple, axis=1)
    )
    if_keys = set(
        if_anom[["brand", "region", "week_start"]].apply(tuple, axis=1)
    ) if not if_anom.empty else set()

    all_anomaly_keys = zscore_keys | mstl_keys | if_keys

    rows = []
    for key in sorted(all_anomaly_keys, key=lambda k: (k[0], k[1], k[2])):
        brand, region, ws = key
        rows.append({
            "brand": brand,
            "region": region,
            "week_start": ws,
            "zscore": key in zscore_keys,
            "mstl": key in mstl_keys,
            "isolation_forest": key in if_keys,
            "n_methods": sum([
                key in zscore_keys,
                key in mstl_keys,
                key in if_keys,
            ]),
        })

    comp_df = pd.DataFrame(rows)

    print("\n" + "=" * 64)
    print("3-WAY COMPARISON SUMMARY")
    print("=" * 64)

    if not comp_df.empty:
        by_agreement = comp_df["n_methods"].value_counts().sort_index()
        for n, cnt in by_agreement.items():
            print(f"  Flagged by {n} method(s): {cnt}")

        # All 3 agree
        all_three = comp_df.loc[comp_df["n_methods"] == 3]
        print(f"\nAll 3 methods agree ({len(all_three)} anomalies):")
        if not all_three.empty:
            print(all_three[["brand", "region", "week_start"]].to_string(index=False))

        # Per series summary
        print("\nPer-series anomaly count by method:")
        series_summary = []
        for (brand, region), grp in comp_df.groupby(["brand", "region"]):
            series_summary.append({
                "brand": brand,
                "region": region,
                "zscore": grp["zscore"].sum(),
                "mstl": grp["mstl"].sum(),
                "isolation_forest": grp["isolation_forest"].sum(),
                "all_3": (grp["n_methods"] == 3).sum(),
            })
        summary_df = pd.DataFrame(series_summary)
        print(summary_df.to_string(index=False))

    return comp_df


# ================================================================
# CO-OCCURRING & BRAND-SPECIFIC ANOMALIES
# ================================================================

def find_co_occurring(comp_df):
    """Find weeks where multiple brands have anomalies (macro event candidates)."""
    if comp_df.empty:
        return pd.DataFrame()

    # Use MSTL anomalies as primary
    mstl_weeks = comp_df.loc[comp_df["mstl"]].copy()
    by_week = mstl_weeks.groupby("week_start")["brand"].agg(
        brands=lambda x: sorted(set(x)), n_brands=lambda x: x.nunique()
    ).reset_index()

    multi = by_week.loc[by_week["n_brands"] >= 2].sort_values(
        "n_brands", ascending=False
    )

    print("\n" + "=" * 64)
    print("CO-OCCURRING ANOMALIES (macro event candidates)")
    print("=" * 64)

    if multi.empty:
        print("  No weeks with multi-brand anomalies found")
    else:
        for _, row in multi.iterrows():
            print(f"  {row['week_start'].strftime('%Y-%m-%d')} "
                  f"({row['n_brands']} brands): {row['brands']}")

    return multi


def find_nb_only(comp_df):
    """Find anomalies that are NB-specific (brand event candidates)."""
    if comp_df.empty:
        return pd.DataFrame()

    # Weeks where NB is anomaly but no other brand is
    mstl_weeks = comp_df.loc[comp_df["mstl"]].copy()
    nb_weeks = set(
        mstl_weeks.loc[
            mstl_weeks["brand"] == "new_balance", "week_start"
        ]
    )
    other_weeks = set(
        mstl_weeks.loc[
            mstl_weeks["brand"] != "new_balance", "week_start"
        ]
    )
    nb_only_weeks = nb_weeks - other_weeks

    nb_only = mstl_weeks.loc[
        (mstl_weeks["brand"] == "new_balance") &
        (mstl_weeks["week_start"].isin(nb_only_weeks))
    ].sort_values("week_start")

    print("\n" + "=" * 64)
    print("NB-ONLY ANOMALIES (brand-specific event candidates)")
    print("=" * 64)

    if nb_only.empty:
        print("  No NB-only anomalies found")
    else:
        for _, row in nb_only.iterrows():
            print(f"  {row['week_start'].strftime('%Y-%m-%d')} "
                  f"{row['region']:8s}")

    return nb_only


# ================================================================
# VISUALIZATION
# ================================================================

def plot_comparison_heatmap(comp_df):
    """Plot method agreement heatmap per series."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if comp_df.empty:
        print("[WARN] No comparison data for heatmap")
        return

    plt.rcParams.update({
        "font.family": "AppleGothic",
        "axes.unicode_minus": False,
        "figure.dpi": 150,
    })

    # Pivot: rows = (brand, region), columns = method, values = count
    summary = []
    for (brand, region), grp in comp_df.groupby(["brand", "region"]):
        summary.append({
            "series": f"{brand}/{region}",
            "Z-score": grp["zscore"].sum(),
            "MSTL": grp["mstl"].sum(),
            "IF": grp["isolation_forest"].sum(),
        })
    summary_df = pd.DataFrame(summary).set_index("series")

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(summary_df.values, cmap="YlOrRd", aspect="auto")

    ax.set_xticks(range(len(summary_df.columns)))
    ax.set_xticklabels(summary_df.columns, fontsize=11)
    ax.set_yticks(range(len(summary_df.index)))
    ax.set_yticklabels(summary_df.index, fontsize=10)

    for i in range(len(summary_df.index)):
        for j in range(len(summary_df.columns)):
            val = int(summary_df.values[i, j])
            ax.text(j, i, str(val), ha="center", va="center",
                    fontsize=12, fontweight="bold",
                    color="white" if val > summary_df.values.max() * 0.6 else "black")

    plt.colorbar(im, ax=ax, label="Anomaly count")
    ax.set_title("Anomaly Count by Method and Series")

    fig_path = os.path.join(FIG_DIR, "anomaly_comparison_heatmap.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


def plot_confusion_venn(cm_df, both, zscore_only, mstl_only):
    """Plot confusion matrix as summary bar chart."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "AppleGothic",
        "axes.unicode_minus": False,
        "figure.dpi": 150,
    })

    categories = ["Both\n(agreement)", "Z-score only\n(false positive)",
                   "MSTL only\n(new discovery)"]
    counts = [len(both), len(zscore_only), len(mstl_only)]
    colors = ["#2ECC71", "#E74C3C", "#3498DB"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(categories, counts, color=colors, edgecolor="white", linewidth=1.5)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(count), ha="center", va="bottom", fontsize=14, fontweight="bold")

    ax.set_ylabel("Number of anomalies")
    ax.set_title("Stage 2 Z-score vs MSTL Residual: Reclassification")
    ax.set_ylim(0, max(counts) * 1.2)

    fig_path = os.path.join(FIG_DIR, "zscore_vs_mstl_confusion.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ================================================================
# SAVE OUTPUTS
# ================================================================

def save_outputs(cm_df, comp_df, co_occurring, nb_only):
    """Save comparison tables as CSV."""
    cm_df.to_csv(os.path.join(OUT_DIR, "confusion_matrix_by_series.csv"), index=False)
    comp_df.to_csv(os.path.join(OUT_DIR, "three_way_comparison.csv"), index=False)
    if not co_occurring.empty:
        co_occurring.to_csv(
            os.path.join(OUT_DIR, "co_occurring_anomalies.csv"), index=False
        )
    if not nb_only.empty:
        nb_only.to_csv(
            os.path.join(OUT_DIR, "nb_only_anomalies.csv"), index=False
        )
    print(f"\nComparison outputs saved to {OUT_DIR}/")


# ================================================================
# MAIN
# ================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 5: 3-way anomaly comparison"
    )
    parser.add_argument("--inspect", action="store_true",
                        help="Inspect Stage 2 anomaly_log contents")
    return parser.parse_args()


def main():
    args = parse_args()

    with get_conn() as conn:

        if args.inspect:
            inspect_stage2(conn)
            return

        # Build universe
        universe = build_universe(conn)
        print(f"Universe: {len(universe)} (brand, region, week_start) triples")

        # Load all three methods
        print("\nLoading anomaly sets:")
        zscore_anom = rederive_zscore_anomalies(conn)
        mstl_anom = load_mstl_anomalies()
        if_anom = load_if_anomalies()

        if mstl_anom.empty:
            print("[ERROR] MSTL anomalies required. Run anomaly_mstl_residual.py first.")
            sys.exit(1)

        # Confusion matrix: z-score vs MSTL
        cm_df, both, zscore_only, mstl_only = build_confusion_matrix(
            universe, zscore_anom, mstl_anom
        )

        # 3-way comparison
        comp_df = three_way_comparison(universe, zscore_anom, mstl_anom, if_anom)

        # Co-occurring anomalies (macro event candidates)
        co_occurring = find_co_occurring(comp_df)

        # NB-only anomalies (brand event candidates)
        nb_only = find_nb_only(comp_df)

        # Visualizations
        print("\nGenerating comparison plots")
        plot_confusion_venn(cm_df, both, zscore_only, mstl_only)
        plot_comparison_heatmap(comp_df)

        # Save outputs
        save_outputs(cm_df, comp_df, co_occurring, nb_only)


if __name__ == "__main__":
    main()
