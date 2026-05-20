"""
Stage 6 Forecasting — A1: Data Preparation (shared across Track A/B/C)

Extracts NB Korea/Global search_index + CSI exogenous variable,
generates ACF/PACF plots, and saves train/test splits.

Outputs:
    data/forecast/nb_korea_forecast_data.csv
    data/forecast/nb_global_forecast_data.csv
    figures/forecast/nb_korea_search_csi.png
    figures/forecast/nb_global_search_csi.png
    figures/forecast/nb_korea_acf_pacf.png
    figures/forecast/nb_global_acf_pacf.png

Usage:
    python -m analysis.forecast_data_prep
"""

import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

from database.connection import get_conn

warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (14, 5),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

# Constants
DATA_DIR = "data/forecast"
FIG_DIR = "figures/forecast"
TEST_WEEKS = 26
REGIONS = ["korea", "global"]

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


# Data extraction
def fetch_search_index(conn):
    """Fetch NB Korea/Global weekly search_index."""
    query = """
    SELECT region, week_start, search_index
    FROM mart.brand_kpi_weekly
    WHERE brand = 'new_balance'
    ORDER BY region, week_start;
    """
    df = pd.read_sql(query, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def fetch_csi(conn):
    """Fetch CSI monthly data from ECOS."""
    query = """
    SELECT period, value as csi
    FROM raw.ecos_raw
    WHERE stat_code = '511Y002'
    ORDER BY period;
    """
    df = pd.read_sql(query, conn)
    df["month_start"] = pd.to_datetime(df["period"] + "-01")
    return df


def fetch_mstl_components(conn):
    """Fetch MSTL trend + residual for NB (anomaly week tagging reference)."""
    query = """
    SELECT region, week_start, trend, residual
    FROM mart.seasonal_components
    WHERE brand = 'new_balance'
      AND decomposition_method = 'MSTL'
      AND product_line IS NULL
    ORDER BY region, week_start;
    """
    df = pd.read_sql(query, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def fetch_anomaly_weeks(conn):
    """Fetch NB anomaly weeks for forecast error analysis tagging."""
    query = """
    SELECT DISTINCT detected_date as week_start
    FROM mart.anomaly_log
    WHERE brand = 'new_balance'
      AND detection_method IN ('mstl_residual_2.0', 'isolation_forest');
    """
    df = pd.read_sql(query, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


# CSI forward-fill: monthly -> weekly
def forward_fill_csi(csi_df, week_range):
    """Forward-fill monthly CSI to weekly granularity.

    Each week inherits the CSI value of its containing month.
    """
    # Build month_start for each week
    weeks = pd.DataFrame({"week_start": week_range})
    weeks["month_start"] = weeks["week_start"].dt.to_period("M").dt.to_timestamp()

    merged = weeks.merge(
        csi_df[["month_start", "csi"]],
        on="month_start",
        how="left",
    )
    # Forward-fill for any edge cases
    merged["csi"] = merged["csi"].ffill()
    return merged[["week_start", "csi"]]


# Train / Test split
def split_train_test(df, test_weeks=TEST_WEEKS):
    """Split time series into train and test sets."""
    cutoff = df["week_start"].max() - pd.Timedelta(weeks=test_weeks - 1)
    train = df[df["week_start"] < cutoff].copy()
    test = df[df["week_start"] >= cutoff].copy()
    return train, test


# Visualization: search_index + CSI overlay
def plot_search_csi(df, region, train_end):
    """Plot search_index with CSI overlay and train/test split line."""
    fig, ax1 = plt.subplots(figsize=(14, 5))

    ax1.plot(df["week_start"], df["search_index"], color="#E74C3C", linewidth=1.2,
             label="NB Search Index")
    ax1.axvline(train_end, color="gray", linestyle="--", alpha=0.7, label="Train/Test Split")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Search Index", color="#E74C3C")
    ax1.tick_params(axis="y", labelcolor="#E74C3C")

    ax2 = ax1.twinx()
    ax2.plot(df["week_start"], df["csi"], color="#3498DB", linewidth=1.0, alpha=0.7,
             label="CSI")
    ax2.set_ylabel("CSI", color="#3498DB")
    ax2.tick_params(axis="y", labelcolor="#3498DB")

    region_label = "Korea" if region == "korea" else "Global"
    ax1.set_title(f"NB {region_label} Search Index + CSI (Train {174 - TEST_WEEKS}w / Test {TEST_WEEKS}w)")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_search_csi.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ACF / PACF plots
def plot_acf_pacf(series, region):
    """Generate ACF and PACF plots for order identification."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 4))

    plot_acf(series.dropna(), ax=axes[0], lags=52, alpha=0.05)
    axes[0].set_title("ACF")

    plot_pacf(series.dropna(), ax=axes[1], lags=52, alpha=0.05, method="ywm")
    axes[1].set_title("PACF")

    region_label = "Korea" if region == "korea" else "Global"
    fig.suptitle(f"NB {region_label} Search Index — ACF / PACF (Train Set)", fontsize=13)
    fig.tight_layout()

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_acf_pacf.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# Main
if __name__ == "__main__":
    with get_conn() as conn:
        # Extract
        search_df = fetch_search_index(conn)
        csi_df = fetch_csi(conn)
        mstl_df = fetch_mstl_components(conn)
        anomaly_df = fetch_anomaly_weeks(conn)

    anomaly_weeks = set(anomaly_df["week_start"])

    for region in REGIONS:
        # Filter region
        region_search = search_df[search_df["region"] == region].copy()
        region_search = region_search.sort_values("week_start").reset_index(drop=True)

        # CSI forward-fill
        csi_weekly = forward_fill_csi(csi_df, region_search["week_start"])
        region_search = region_search.merge(csi_weekly, on="week_start", how="left")

        # MSTL trend + residual
        region_mstl = mstl_df[mstl_df["region"] == region][["week_start", "trend", "residual"]]
        region_search = region_search.merge(region_mstl, on="week_start", how="left")

        # Anomaly week flag
        region_search["is_anomaly_week"] = region_search["week_start"].isin(anomaly_weeks).astype(int)

        # Train / Test split
        train, test = split_train_test(region_search)
        train_end = train["week_start"].max()

        print(f"\n--- NB {region.upper()} ---")
        print(f"Total: {len(region_search)} weeks")
        print(f"Train: {len(train)} weeks ({train['week_start'].min()} ~ {train_end})")
        print(f"Test:  {len(test)} weeks ({test['week_start'].min()} ~ {test['week_start'].max()})")
        print(f"Anomaly weeks in test: {test['is_anomaly_week'].sum()}")
        print(f"CSI range: {region_search['csi'].min():.1f} ~ {region_search['csi'].max():.1f}")

        # Save full dataset with split indicator
        region_search["split"] = np.where(region_search["week_start"] <= train_end, "train", "test")
        csv_path = os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv")
        region_search.to_csv(csv_path, index=False)
        print(f"Saved: {csv_path}")

        # Plots
        plot_search_csi(region_search, region, train_end)
        plot_acf_pacf(train["search_index"], region)

    print("\nA1 data preparation complete.")
