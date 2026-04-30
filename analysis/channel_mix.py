"""
Stage 3 Step A3 — Channel Mix Analysis

Two analyses:
  1. Search type mix (web/youtube/shopping) share from staging.search_weekly
     - NB Korea: how search demand distributes across channels
     - 4-brand comparison
  2. D2C trend re-verification from raw.naver_datalab_raw
     - Stage 0 H5: D2C slope = -0.179/week (p=0.0001)
     - Re-verify with mart-era data + linear regression

Usage:
    python -m analysis.channel_mix
    python -m analysis.channel_mix --dry-run
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
from scipy import stats

# local
from database.connection import get_conn

# ================================================================
# CONSTANTS
# ================================================================

FIG_DIR = "figures/channel_mix"
os.makedirs(FIG_DIR, exist_ok=True)

BRANDS = ["nike", "adidas", "puma", "new_balance"]

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (14, 6),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

BRAND_COLORS = {
    "new_balance": "#E74C3C",
    "nike": "#FF6B00",
    "adidas": "#3498DB",
    "puma": "#2ECC71",
}

SEARCH_TYPE_COLORS = {
    "web": "#3498DB",
    "youtube": "#E74C3C",
    "shopping": "#2ECC71",
    "naver_search": "#9B59B6",
}


# ================================================================
# PART 1: SEARCH TYPE MIX
# ================================================================

def fetch_search_type_mix():
    """Fetch weekly search interest by brand, search_type from staging."""
    query = """
        SELECT brand, search_type, week_start,
               SUM(interest) AS interest
        FROM staging.search_weekly
        WHERE source = 'google_trends'
          AND keyword_group = 'brand'
          AND region = 'korea'
          AND product_line IS NULL
        GROUP BY brand, search_type, week_start
        ORDER BY brand, week_start, search_type
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn)

    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def analyze_search_type_mix(df):
    """Compute search type share per brand."""
    print("\n  === Search Type Mix — Korea GT Brand ===\n")

    results = {}

    for brand in BRANDS:
        bdf = df[df["brand"] == brand]
        if bdf.empty:
            continue

        # Pivot: week_start × search_type
        pivot = bdf.pivot_table(
            index="week_start", columns="search_type",
            values="interest", aggfunc="sum", fill_value=0,
        )

        # Compute shares
        row_total = pivot.sum(axis=1)
        shares = pivot.div(row_total, axis=0) * 100

        # Average shares
        avg_shares = shares.mean()
        print(f"  {brand}:")
        for st in sorted(avg_shares.index):
            print(f"    {st:<15} {avg_shares[st]:>6.2f}%")
        print()

        results[brand] = {
            "pivot": pivot,
            "shares": shares,
            "avg_shares": avg_shares,
        }

    return results


def plot_search_type_stacked(results):
    """Stacked area chart of search type shares per brand."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex=True)
    axes = axes.flatten()

    for ax, brand in zip(axes, BRANDS):
        if brand not in results:
            continue

        shares = results[brand]["shares"]

        # Sort search types for consistent stacking
        search_types = sorted(shares.columns)
        colors = [SEARCH_TYPE_COLORS.get(st, "#999") for st in search_types]

        ax.stackplot(shares.index, [shares[st].values for st in search_types],
                     labels=search_types, colors=colors, alpha=0.7)
        ax.set_title(brand, fontsize=11, fontweight="bold")
        ax.set_ylabel("Share (%)")
        ax.set_ylim(0, 100)
        ax.legend(loc="upper right", fontsize=8)

    fig.suptitle("Search Type Mix — Korea GT Brand", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, "search_type_mix_stacked.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


def plot_search_type_trend(results):
    """Line chart of shopping share trend (D2C proxy)."""
    fig, ax = plt.subplots(figsize=(14, 5))

    for brand in BRANDS:
        if brand not in results:
            continue

        shares = results[brand]["shares"]
        if "shopping" in shares.columns:
            # 4-week rolling average for smoothing
            shopping_ma = shares["shopping"].rolling(4, min_periods=1).mean()
            color = BRAND_COLORS.get(brand, "#333")
            ax.plot(shopping_ma.index, shopping_ma.values,
                    label=brand, color=color, linewidth=1.2)

    ax.set_title("Shopping Search Share Trend — Korea (4-week MA)",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("Week")
    ax.set_ylabel("Shopping Share (%)")
    ax.legend(loc="upper right")

    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, "shopping_share_trend.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ================================================================
# PART 2: D2C TREND RE-VERIFICATION
# ================================================================

def fetch_d2c_raw():
    """Fetch NB D2C (공식몰) search data from raw.naver_datalab_raw."""
    query = """
        SELECT keyword, period_start, ratio
        FROM raw.naver_datalab_raw
        WHERE keyword_group = 'nb_channel'
        ORDER BY keyword, period_start
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn)

    df["period_start"] = pd.to_datetime(df["period_start"])
    return df


def fetch_nb_total():
    """Fetch NB total search from staging for comparison."""
    query = """
        SELECT week_start, SUM(interest) AS nb_total
        FROM staging.search_weekly
        WHERE brand = 'new_balance'
          AND source = 'naver_datalab'
          AND keyword_group = 'brand'
          AND region = 'korea'
        GROUP BY week_start
        ORDER BY week_start
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn)

    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def analyze_d2c_trend(d2c_df, nb_total_df):
    """Re-verify D2C trend with linear regression."""
    print("\n  === D2C Trend Re-verification ===\n")

    # Summarize available keywords
    keywords = d2c_df["keyword"].unique()
    print(f"  Available nb_channel keywords: {list(keywords)}")

    for kw in keywords:
        kdf = d2c_df[d2c_df["keyword"] == kw].copy()
        kdf = kdf.sort_values("period_start").reset_index(drop=True)
        n = len(kdf)

        if n < 10:
            print(f"  {kw}: only {n} points, skipping regression")
            continue

        # Linear regression
        x = np.arange(n)
        y = kdf["ratio"].values
        slope, intercept, r_val, p_val, std_err = stats.linregress(x, y)

        print(f"  {kw}:")
        print(f"    N={n}, range: {kdf['period_start'].min().date()} ~ {kdf['period_start'].max().date()}")
        print(f"    Mean ratio: {y.mean():.2f}")
        print(f"    Slope: {slope:.4f}/week, p={p_val:.6f}")
        print(f"    R-squared: {r_val**2:.4f}")
        if p_val < 0.05:
            direction = "DECLINING" if slope < 0 else "INCREASING"
            print(f"    Verdict: {direction} (significant)")
        else:
            print(f"    Verdict: No significant trend")
        print()

    return d2c_df


def plot_d2c_trend(d2c_df, nb_total_df):
    """Plot D2C keywords + NB total for comparison."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # Panel 1: NB total search (from staging)
    ax1 = axes[0]
    if not nb_total_df.empty:
        ax1.plot(nb_total_df["week_start"], nb_total_df["nb_total"],
                 color=BRAND_COLORS["new_balance"], linewidth=1.2)
    ax1.set_title("NB Total Search — Naver DataLab (brand group)",
                  fontsize=11, fontweight="bold")
    ax1.set_ylabel("Ratio")

    # Panel 2: D2C keywords (from raw)
    ax2 = axes[1]
    kw_colors = {"뉴발란스 공식몰": "#E74C3C", "뉴발란스 공홈": "#FF6B00",
                 "뉴발란스 자사몰": "#3498DB", "뉴발란스 무신사": "#2ECC71",
                 "뉴발란스 쿠팡": "#9B59B6"}

    for kw in d2c_df["keyword"].unique():
        kdf = d2c_df[d2c_df["keyword"] == kw].sort_values("period_start")
        color = kw_colors.get(kw, "#999")
        ax2.plot(kdf["period_start"], kdf["ratio"],
                 label=kw, color=color, linewidth=1.2, alpha=0.8)

        # Add trend line for D2C keywords with enough data
        if len(kdf) >= 10:
            x = np.arange(len(kdf))
            slope, intercept, _, p_val, _ = stats.linregress(x, kdf["ratio"].values)
            if p_val < 0.05:
                trend_y = intercept + slope * x
                ax2.plot(kdf["period_start"], trend_y,
                         color=color, linewidth=1.5, linestyle="--", alpha=0.6)

    ax2.set_title("NB Channel Keywords — raw.naver_datalab_raw (nb_channel group)",
                  fontsize=11, fontweight="bold")
    ax2.set_ylabel("Ratio")
    ax2.set_xlabel("Week")
    ax2.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, "d2c_trend_reverification.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ================================================================
# CLI / MAIN
# ================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 3 Step A3: Channel mix analysis"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze and print without saving plots")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Stage 3 Step A3: Channel Mix Analysis")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Part 1: Search type mix
    print("\n  --- Part 1: Search Type Mix ---")
    st_df = fetch_search_type_mix()
    print(f"  Fetched {len(st_df)} rows from staging.search_weekly")
    st_results = analyze_search_type_mix(st_df)

    if not args.dry_run:
        plot_search_type_stacked(st_results)
        plot_search_type_trend(st_results)

    # Part 2: D2C trend
    print("\n  --- Part 2: D2C Trend Re-verification ---")
    d2c_df = fetch_d2c_raw()
    nb_total_df = fetch_nb_total()
    print(f"  Fetched {len(d2c_df)} nb_channel rows from raw")
    print(f"  Fetched {len(nb_total_df)} NB total rows from staging")

    analyze_d2c_trend(d2c_df, nb_total_df)

    if not args.dry_run:
        plot_d2c_trend(d2c_df, nb_total_df)

    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
