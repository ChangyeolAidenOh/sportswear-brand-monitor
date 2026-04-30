"""
Stage 3 Step B4+B5 — Brand Sentiment Aggregation & Mart Update

B4: Compute brand-level sentiment distribution from staging.blog_sentiment.
    Broadcast organic-only product sentiment average into
    mart.brand_kpi_weekly.social_sentiment_static.

B5: Cost + accuracy verification.
    - Keyword-only vs API routing ratio
    - Total API cost vs estimate
    - Sample (1K) vs full corpus (10K) representativeness check

Usage:
    python -m analysis.sentiment_aggregator
    python -m analysis.sentiment_aggregator --dry-run
"""

# stdlib
import argparse
import os
import warnings
from datetime import datetime

# third-party
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# local
from database.connection import get_conn

# ================================================================
# CONSTANTS
# ================================================================

FIG_DIR = "figures/sentiment"
os.makedirs(FIG_DIR, exist_ok=True)

BRANDS = ["new_balance", "nike", "adidas", "puma"]
REGIONS = ["korea", "global"]

# B1 sample averages (1,000 samples, organic only, product-only scoring)
B1_SAMPLE_AVG = {
    "new_balance": 0.2971,
    "nike": 0.5088,
    "adidas": 0.4291,
    "puma": 0.3568,
}

BRAND_COLORS = {
    "new_balance": "#E74C3C",
    "nike": "#FF6B00",
    "adidas": "#3498DB",
    "puma": "#2ECC71",
}

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (12, 6),
    "axes.grid": True,
    "grid.alpha": 0.3,
})


# ================================================================
# DATA FETCH
# ================================================================

def fetch_sentiment_summary():
    """Fetch brand-level sentiment summary from staging.blog_sentiment."""
    query = """
        SELECT brand, is_sponsored, final_label, final_source,
               keyword_score, COUNT(*) AS n
        FROM staging.blog_sentiment
        GROUP BY brand, is_sponsored, final_label, final_source, keyword_score
        ORDER BY brand, is_sponsored, final_label
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn)
    return df


def fetch_organic_scores():
    """Fetch individual organic scores for brand averages."""
    query = """
        SELECT brand, keyword_score, final_label
        FROM staging.blog_sentiment
        WHERE is_sponsored = FALSE
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn)
    return df


# ================================================================
# B4: BRAND SENTIMENT DISTRIBUTION
# ================================================================

def compute_brand_sentiment(organic_df):
    """Compute brand-level sentiment metrics."""
    print("\n  === B4: Brand Sentiment Distribution (organic only) ===\n")

    brand_stats = {}

    print(f"  {'Brand':<15} {'n':>5} {'pos':>5} {'neg':>5} {'neu':>5} {'unc':>5} "
          f"{'pos%':>6} {'neg%':>6} {'avg_score':>10}")
    print("  " + "-" * 80)

    for brand in BRANDS:
        bdf = organic_df[organic_df["brand"] == brand]
        n = len(bdf)
        if n == 0:
            continue

        pos = (bdf["final_label"] == "positive").sum()
        neg = (bdf["final_label"] == "negative").sum()
        neu = (bdf["final_label"] == "neutral").sum()
        unc = (bdf["final_label"] == "uncertain").sum()
        avg_score = bdf["keyword_score"].mean()
        pos_pct = pos / n * 100
        neg_pct = neg / n * 100

        brand_stats[brand] = {
            "n": n, "pos": pos, "neg": neg, "neu": neu, "unc": unc,
            "pos_pct": pos_pct, "neg_pct": neg_pct,
            "avg_score": avg_score,
        }

        print(f"  {brand:<15} {n:>5} {pos:>5} {neg:>5} {neu:>5} {unc:>5} "
              f"{pos_pct:>5.1f}% {neg_pct:>5.1f}% {avg_score:>+10.4f}")

    # Sentiment ratio: positive / (positive + negative)
    print(f"\n  --- Positive / (Pos+Neg) Ratio ---")
    for brand in BRANDS:
        s = brand_stats.get(brand)
        if s and (s["pos"] + s["neg"]) > 0:
            ratio = s["pos"] / (s["pos"] + s["neg"])
            print(f"  {brand:<15} {ratio:.4f}")

    return brand_stats


# ================================================================
# B5: SAMPLE VS FULL COMPARISON
# ================================================================

def compare_sample_vs_full(brand_stats):
    """Compare B1 1K sample averages with B2 10K full corpus."""
    print(f"\n  === B5: Sample (1K) vs Full Corpus (10K) Representativeness ===\n")
    print(f"  {'Brand':<15} {'B1_1K':>8} {'B2_10K':>8} {'Delta':>8} {'Status':>15}")
    print("  " + "-" * 55)

    for brand in BRANDS:
        b1 = B1_SAMPLE_AVG.get(brand, 0)
        b2 = brand_stats.get(brand, {}).get("avg_score", 0)
        delta = b2 - b1

        if abs(delta) < 0.03:
            status = "Representative"
        elif abs(delta) < 0.05:
            status = "Minor deviation"
        else:
            status = "Investigate"

        print(f"  {brand:<15} {b1:>+8.4f} {b2:>+8.4f} {delta:>+8.4f} {status:>15}")

    print()


# ================================================================
# B5: COST VERIFICATION
# ================================================================

def verify_cost():
    """Print routing and cost summary."""
    query = """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE final_source = 'keyword') AS keyword_count,
            COUNT(*) FILTER (WHERE final_source = 'api') AS api_count,
            COUNT(*) FILTER (WHERE final_source = 'pending') AS pending_count,
            COUNT(*) FILTER (WHERE is_sponsored) AS sponsored_count
        FROM staging.blog_sentiment
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            row = pd.read_sql(query, conn).iloc[0]

    total = int(row["total"])
    keyword = int(row["keyword_count"])
    api = int(row["api_count"])
    pending = int(row["pending_count"])
    sponsored = int(row["sponsored_count"])

    print(f"\n  === B5: Cost & Routing Verification ===\n")
    print(f"  Total texts:     {total}")
    print(f"  Sponsored:       {sponsored} ({sponsored/total*100:.1f}%)")
    print(f"  Keyword resolved: {keyword} ({keyword/total*100:.1f}%)")
    print(f"  API resolved:    {api} ({api/total*100:.1f}%)")
    print(f"  Pending:         {pending}")
    print(f"  Keyword coverage: {(keyword+api)/total*100:.1f}% complete")

    # Cost: check cost_log.csv
    cost_log_path = "data/batch/cost_log.csv"
    if os.path.exists(cost_log_path):
        cost_df = pd.read_csv(cost_log_path)
        total_est = cost_df["est_cost_krw"].sum()
        print(f"\n  Estimated total cost: ~{total_est:.1f} KRW")
        print(f"  Cost per text: ~{total_est/total:.4f} KRW")
    print()


# ================================================================
# MART UPDATE
# ================================================================

def update_mart(brand_stats):
    """Broadcast organic sentiment average into mart.brand_kpi_weekly."""
    print(f"  === Updating mart.brand_kpi_weekly.social_sentiment_static ===\n")

    with get_conn() as conn:
        with conn.cursor() as cur:
            for brand in BRANDS:
                avg_score = brand_stats.get(brand, {}).get("avg_score")
                if avg_score is None:
                    continue

                # Broadcast: same value for all rows of this brand (both regions)
                cur.execute("""
                    UPDATE mart.brand_kpi_weekly
                    SET social_sentiment_static = %s
                    WHERE brand = %s
                """, (float(round(avg_score, 4)), brand))
                updated = cur.rowcount
                print(f"  {brand}: {avg_score:+.4f} → {updated} rows updated")

            conn.commit()

    print()


# ================================================================
# VISUALIZATION
# ================================================================

def plot_sentiment_distribution(brand_stats):
    """Bar chart of sentiment distribution by brand."""
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(BRANDS))
    width = 0.2

    pos_vals = [brand_stats.get(b, {}).get("pos_pct", 0) for b in BRANDS]
    neg_vals = [brand_stats.get(b, {}).get("neg_pct", 0) for b in BRANDS]
    neu_vals = [100 - p - n for p, n in zip(pos_vals, neg_vals)]

    ax.bar(x - width, pos_vals, width, label="Positive", color="#2ECC71", alpha=0.8)
    ax.bar(x, neu_vals, width, label="Neutral/Uncertain", color="#95A5A6", alpha=0.8)
    ax.bar(x + width, neg_vals, width, label="Negative", color="#E74C3C", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(BRANDS)
    ax.set_ylabel("Percentage (%)")
    ax.set_title("Brand Sentiment Distribution (organic, product-only)",
                 fontsize=12, fontweight="bold")
    ax.legend()

    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, "brand_sentiment_distribution.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


def plot_sample_vs_full(brand_stats):
    """Side-by-side comparison of B1 sample vs B2 full."""
    fig, ax = plt.subplots(figsize=(10, 5))

    x = np.arange(len(BRANDS))
    width = 0.3

    b1_vals = [B1_SAMPLE_AVG.get(b, 0) for b in BRANDS]
    b2_vals = [brand_stats.get(b, {}).get("avg_score", 0) for b in BRANDS]

    bars1 = ax.bar(x - width/2, b1_vals, width, label="B1 Sample (1K)",
                   color="#3498DB", alpha=0.7)
    bars2 = ax.bar(x + width/2, b2_vals, width, label="B2 Full (10K)",
                   color="#E74C3C", alpha=0.7)

    ax.set_xticks(x)
    ax.set_xticklabels(BRANDS)
    ax.set_ylabel("Average Product Score")
    ax.set_title("Sample vs Full Corpus — Sentiment Average Comparison",
                 fontsize=12, fontweight="bold")
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax.legend()

    # Add value labels
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{bar.get_height():.3f}", ha="center", fontsize=8)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{bar.get_height():.3f}", ha="center", fontsize=8)

    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, "sample_vs_full_comparison.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ================================================================
# CLI / MAIN
# ================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 3 B4+B5: Brand sentiment aggregation + mart update"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute and print without mart update")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Stage 3 B4+B5: Brand Sentiment Aggregation")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Fetch organic scores
    organic_df = fetch_organic_scores()
    print(f"  Fetched {len(organic_df)} organic scores")

    # B4: Brand distribution
    brand_stats = compute_brand_sentiment(organic_df)

    # B5: Comparisons
    compare_sample_vs_full(brand_stats)
    verify_cost()

    # Visualization
    plot_sentiment_distribution(brand_stats)
    plot_sample_vs_full(brand_stats)

    # Mart update
    if not args.dry_run:
        update_mart(brand_stats)

    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
