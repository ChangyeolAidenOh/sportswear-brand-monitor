"""
Stage 6 Forecasting — Track D (Updated): 4-Way Model Comparison

Extends original 3-way (SARIMAX/LSTM/Chronos) to include Prophet.
Generates SEPARATE 4-way outputs — does NOT overwrite 3-way files.

Inputs:
    data/forecast/sarimax_forecast_korea.csv
    data/forecast/sarimax_forecast_global.csv
    data/forecast/lstm_forecast_korea.csv
    data/forecast/lstm_forecast_global.csv
    data/forecast/chronos_forecast_korea.csv
    data/forecast/chronos_forecast_global.csv
    data/forecast/prophet_forecast_korea.csv
    data/forecast/prophet_forecast_global.csv
    data/forecast/nb_korea_forecast_data.csv
    data/forecast/nb_global_forecast_data.csv

Outputs:
    data/forecast/forecast_comparison_4way.csv
    figures/forecast/nb_korea_forecast_4way.png
    figures/forecast/nb_global_forecast_4way.png
    figures/forecast/forecast_error_distribution_4way.png

Usage:
    python -m analysis.forecast_comparison_4way
"""

# stdlib
import os
import warnings

# third-party
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (14, 5),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

# ================================================================
# Constants
# ================================================================
DATA_DIR = "data/forecast"
FIG_DIR = "figures/forecast"
REGIONS = ["korea", "global"]

MODEL_COLORS = {
    "SARIMAX": "#3498DB",
    "Prophet": "#F39C12",
    "LSTM": "#2ECC71",
    "Chronos-small": "#9B59B6",
}

# Ordered for display
MODEL_ORDER = ["SARIMAX", "Prophet", "LSTM", "Chronos-small"]


# ================================================================
# Evaluation metrics
# ================================================================
def compute_metrics(actual, predicted, model, region, subset="all"):
    """Compute RMSE, MAE, MAPE."""
    residuals = actual - predicted
    rmse = np.sqrt(np.mean(residuals ** 2))
    mae = np.mean(np.abs(residuals))

    nonzero_mask = actual != 0
    if nonzero_mask.sum() > 0:
        mape = np.mean(np.abs(residuals[nonzero_mask] / actual[nonzero_mask])) * 100
    else:
        mape = np.nan

    return {
        "model": model, "region": region, "subset": subset,
        "rmse": round(rmse, 2), "mae": round(mae, 2), "mape_pct": round(mape, 1),
        "n_weeks": len(actual),
    }


# ================================================================
# Load and merge all forecasts
# ================================================================
def load_forecasts(region):
    """Load all 4 model forecasts for a region."""
    base = pd.read_csv(
        os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv"),
        parse_dates=["week_start"],
    )
    train = base[base["split"] == "train"].copy().reset_index(drop=True)
    test = base[base["split"] == "test"].copy().reset_index(drop=True)

    sarimax = pd.read_csv(os.path.join(DATA_DIR, f"sarimax_forecast_{region}.csv"), parse_dates=["week_start"])
    prophet = pd.read_csv(os.path.join(DATA_DIR, f"prophet_forecast_{region}.csv"), parse_dates=["week_start"])
    lstm = pd.read_csv(os.path.join(DATA_DIR, f"lstm_forecast_{region}.csv"), parse_dates=["week_start"])
    chronos = pd.read_csv(os.path.join(DATA_DIR, f"chronos_forecast_{region}.csv"), parse_dates=["week_start"])

    merged = test[["week_start", "search_index", "is_anomaly_week"]].copy()
    merged = merged.merge(sarimax[["week_start", "sarimax_forecast"]], on="week_start", how="left")
    merged = merged.merge(prophet[["week_start", "prophet_forecast"]], on="week_start", how="left")
    merged = merged.merge(lstm[["week_start", "lstm_forecast"]], on="week_start", how="left")
    merged = merged.merge(chronos[["week_start", "chronos_small_median"]], on="week_start", how="left")

    return train, merged


# ================================================================
# Plot: 4-way forecast overlay
# ================================================================
def plot_4way(train, test_merged, region):
    """Overlay actual vs all 4 model forecasts."""
    fig, ax = plt.subplots(figsize=(14, 5))

    train_tail = train.tail(26)
    ax.plot(train_tail["week_start"], train_tail["search_index"],
            color="#888888", linewidth=0.8, label="Train (last 26w)")
    ax.plot(test_merged["week_start"], test_merged["search_index"],
            color="#E74C3C", linewidth=2.0, label="Actual")

    forecast_cols = {
        "SARIMAX": "sarimax_forecast",
        "Prophet": "prophet_forecast",
        "LSTM": "lstm_forecast",
        "Chronos-small": "chronos_small_median",
    }
    for model_name in MODEL_ORDER:
        col = forecast_cols[model_name]
        ax.plot(test_merged["week_start"], test_merged[col],
                color=MODEL_COLORS[model_name], linewidth=1.3, linestyle="--",
                label=model_name)

    ax.axvline(train["week_start"].iloc[-1], color="gray", linestyle="--", alpha=0.5)

    anomaly = test_merged[test_merged["is_anomaly_week"] == 1]
    if len(anomaly) > 0:
        ax.scatter(anomaly["week_start"], anomaly["search_index"],
                   color="red", marker="x", s=100, zorder=5, label="Anomaly")

    region_label = "Korea" if region == "korea" else "Global"
    ax.set_title(f"NB {region_label} — 4-Way Forecast Comparison (26-Week Test)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Search Index")
    ax.legend(loc="upper left", fontsize=9)

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_forecast_4way.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ================================================================
# Plot: 4-way error distribution
# ================================================================
def plot_error_distribution(all_errors):
    """Box plot of forecast errors — 4 models."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for idx, region in enumerate(REGIONS):
        labels = []
        data = []
        for model in MODEL_ORDER:
            if (model, region) in all_errors:
                labels.append(model)
                data.append(all_errors[(model, region)])

        bp = axes[idx].boxplot(data, tick_labels=labels, patch_artist=True)
        for patch, model in zip(bp["boxes"], labels):
            patch.set_facecolor(MODEL_COLORS.get(model, "#888888"))
            patch.set_alpha(0.6)

        axes[idx].axhline(0, color="black", linewidth=0.5, alpha=0.5)
        region_label = "Korea" if region == "korea" else "Global"
        axes[idx].set_title(f"NB {region_label}")
        axes[idx].set_ylabel("Forecast Error (Actual - Predicted)")
        axes[idx].tick_params(axis="x", rotation=15)

    fig.suptitle("Forecast Error Distribution — 4-Way Comparison", fontsize=13)
    fig.tight_layout()

    fig_path = os.path.join(FIG_DIR, "forecast_error_distribution_4way.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ================================================================
# Main
# ================================================================
if __name__ == "__main__":
    all_metrics = []
    all_errors = {}

    forecast_cols = {
        "SARIMAX": "sarimax_forecast",
        "Prophet": "prophet_forecast",
        "LSTM": "lstm_forecast",
        "Chronos-small": "chronos_small_median",
    }

    for region in REGIONS:
        print(f"\n{'='*60}")
        print(f"NB {region.upper()} — 4-Way Comparison")
        print(f"{'='*60}")

        train, test_merged = load_forecasts(region)
        actual = test_merged["search_index"].values
        anomaly_mask = test_merged["is_anomaly_week"].values == 1

        for model_name in MODEL_ORDER:
            col = forecast_cols[model_name]
            predicted = test_merged[col].values
            errors = actual - predicted

            m_all = compute_metrics(actual, predicted, model_name, region, "all")
            all_metrics.append(m_all)

            if (~anomaly_mask).sum() > 0:
                m_norm = compute_metrics(actual[~anomaly_mask], predicted[~anomaly_mask],
                                         model_name, region, "normal")
                all_metrics.append(m_norm)

            if anomaly_mask.sum() > 0:
                m_anom = compute_metrics(actual[anomaly_mask], predicted[anomaly_mask],
                                         model_name, region, "anomaly")
                all_metrics.append(m_anom)

            all_errors[(model_name, region)] = errors

        plot_4way(train, test_merged, region)

    metrics_df = pd.DataFrame(all_metrics)

    # ---- Summary ----
    print(f"\n{'='*60}")
    print("4-WAY COMPARISON TABLE")
    print(f"{'='*60}")

    overall = metrics_df[metrics_df["subset"] == "all"].copy()
    pivot = overall.pivot(index="model", columns="region", values=["rmse", "mape_pct"])
    # Reorder rows
    model_idx = pd.CategoricalIndex(pivot.index, categories=MODEL_ORDER, ordered=True)
    pivot = pivot.reindex(model_idx)
    print(pivot.to_string())

    # Prophet vs SARIMAX delta
    print(f"\n{'='*60}")
    print("PROPHET vs SARIMAX DELTA")
    print(f"{'='*60}")
    for region in REGIONS:
        region_label = "Korea" if region == "korea" else "Global"
        s_rmse = overall[(overall["model"] == "SARIMAX") & (overall["region"] == region)]["rmse"].values[0]
        p_rmse = overall[(overall["model"] == "Prophet") & (overall["region"] == region)]["rmse"].values[0]
        delta = p_rmse - s_rmse
        pct = (delta / s_rmse) * 100
        winner = "SARIMAX" if delta > 0 else "Prophet"
        print(f"  {region_label}: SARIMAX={s_rmse:.2f}, Prophet={p_rmse:.2f}, delta={delta:+.2f} ({pct:+.1f}%) -> {winner}")

    # Save
    metrics_path = os.path.join(DATA_DIR, "forecast_comparison_4way.csv")
    metrics_df.to_csv(metrics_path, index=False)
    print(f"\nSaved: {metrics_path}")

    plot_error_distribution(all_errors)

    # Ranking
    print(f"\n{'='*60}")
    print("RANKING BY RMSE (4-WAY)")
    print(f"{'='*60}")
    for region in REGIONS:
        region_overall = overall[overall["region"] == region].sort_values("rmse")
        region_label = "Korea" if region == "korea" else "Global"
        print(f"\n{region_label}:")
        for rank, (_, row) in enumerate(region_overall.iterrows(), 1):
            print(f"  {rank}. {row['model']:15s} RMSE={row['rmse']:.2f}  MAPE={row['mape_pct']:.1f}%")

    print("\n4-Way comparison complete.")
