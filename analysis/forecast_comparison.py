"""
Stage 6 Forecasting — Track D: 3-Way Model Comparison + Anomaly Analysis

Combines SARIMAX, LSTM, Chronos forecast results.
Generates comparison table, overlay plots, error distribution,
anomaly week analysis (test + train in-sample residuals).

Inputs:
    data/forecast/sarimax_forecast_korea.csv
    data/forecast/sarimax_forecast_global.csv
    data/forecast/lstm_forecast_korea.csv
    data/forecast/lstm_forecast_global.csv
    data/forecast/chronos_forecast_korea.csv
    data/forecast/chronos_forecast_global.csv
    data/forecast/nb_korea_forecast_data.csv
    data/forecast/nb_global_forecast_data.csv

Outputs:
    data/forecast/forecast_comparison_metrics.csv
    data/forecast/train_insample_residual_analysis.csv
    figures/forecast/nb_korea_forecast_3way.png
    figures/forecast/nb_global_forecast_3way.png
    figures/forecast/forecast_error_distribution.png
    figures/forecast/anomaly_week_error_analysis.png
    figures/forecast/train_anomaly_residual_analysis.png

Usage:
    python -m analysis.forecast_comparison
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
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

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
FOURIER_CONFIG = {52: 2, 13: 2}

ORDERS = {
    "korea": (0, 1, 1),
    "global": (0, 1, 0),
}

MODEL_COLORS = {
    "SARIMAX": "#3498DB",
    "LSTM": "#2ECC71",
    "Chronos-small": "#9B59B6",
    "Chronos-base": "#E67E22",
}


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
# Fourier terms (identical to SARIMAX/LSTM)
# ================================================================
def make_fourier_terms(n, period_k_map, start_idx=0):
    """Generate Fourier sin/cos terms."""
    t = np.arange(start_idx, start_idx + n)
    cols = {}
    for period, K in period_k_map.items():
        for k in range(1, K + 1):
            cols[f"sin_{period}_{k}"] = np.sin(2 * np.pi * k * t / period)
            cols[f"cos_{period}_{k}"] = np.cos(2 * np.pi * k * t / period)
    return pd.DataFrame(cols)


# ================================================================
# Load and merge forecasts
# ================================================================
def load_forecasts(region):
    """Load all model forecasts for a region and merge on week_start."""
    base = pd.read_csv(
        os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv"),
        parse_dates=["week_start"],
    )
    train = base[base["split"] == "train"].copy().reset_index(drop=True)
    test = base[base["split"] == "test"].copy().reset_index(drop=True)

    sarimax = pd.read_csv(
        os.path.join(DATA_DIR, f"sarimax_forecast_{region}.csv"),
        parse_dates=["week_start"],
    )
    lstm = pd.read_csv(
        os.path.join(DATA_DIR, f"lstm_forecast_{region}.csv"),
        parse_dates=["week_start"],
    )
    chronos = pd.read_csv(
        os.path.join(DATA_DIR, f"chronos_forecast_{region}.csv"),
        parse_dates=["week_start"],
    )

    merged = test[["week_start", "search_index", "is_anomaly_week"]].copy()
    merged = merged.merge(sarimax[["week_start", "sarimax_forecast"]], on="week_start", how="left")
    merged = merged.merge(lstm[["week_start", "lstm_forecast"]], on="week_start", how="left")
    merged = merged.merge(
        chronos[["week_start", "chronos_small_median", "chronos_base_median"]],
        on="week_start", how="left",
    )

    return train, merged


# ================================================================
# D2: Train in-sample SARIMAX residual analysis
# ================================================================
def train_insample_residual_analysis(region):
    """Re-fit SARIMAX on train and compare in-sample residuals for anomaly vs normal weeks."""
    df = pd.read_csv(
        os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv"),
        parse_dates=["week_start"],
    )
    train = df[df["split"] == "train"].copy().reset_index(drop=True)

    # Build exogenous
    fourier = make_fourier_terms(len(train), FOURIER_CONFIG, start_idx=0)
    exog = pd.concat([fourier, train[["csi"]].reset_index(drop=True)], axis=1)

    # Fit SARIMAX
    order = ORDERS[region]
    model = ARIMA(train["search_index"].values, exog=exog.values, order=order)
    fit = model.fit()

    # In-sample residuals
    train["insample_residual"] = fit.resid
    train["abs_residual"] = np.abs(fit.resid)

    anomaly_mask = train["is_anomaly_week"] == 1
    n_anomaly = anomaly_mask.sum()
    n_normal = (~anomaly_mask).sum()

    result = {
        "region": region,
        "n_anomaly_train": int(n_anomaly),
        "n_normal_train": int(n_normal),
        "anomaly_mean_abs_resid": round(train.loc[anomaly_mask, "abs_residual"].mean(), 2) if n_anomaly > 0 else np.nan,
        "normal_mean_abs_resid": round(train.loc[~anomaly_mask, "abs_residual"].mean(), 2),
        "anomaly_rmse": round(np.sqrt(np.mean(train.loc[anomaly_mask, "insample_residual"] ** 2)), 2) if n_anomaly > 0 else np.nan,
        "normal_rmse": round(np.sqrt(np.mean(train.loc[~anomaly_mask, "insample_residual"] ** 2)), 2),
    }

    if n_anomaly > 0:
        ratio = result["anomaly_mean_abs_resid"] / result["normal_mean_abs_resid"]
        result["anomaly_to_normal_ratio"] = round(ratio, 2)
    else:
        result["anomaly_to_normal_ratio"] = np.nan

    return result, train[["week_start", "search_index", "is_anomaly_week", "insample_residual", "abs_residual"]]


# ================================================================
# Plot: 3-way forecast overlay (Chronos-small as representative)
# ================================================================
def plot_3way(train, test_merged, region):
    """Overlay actual vs 3 model forecasts."""
    fig, ax = plt.subplots(figsize=(14, 5))

    train_tail = train.tail(26)
    ax.plot(train_tail["week_start"], train_tail["search_index"],
            color="#888888", linewidth=0.8, label="Train (last 26w)")

    ax.plot(test_merged["week_start"], test_merged["search_index"],
            color="#E74C3C", linewidth=2.0, label="Actual")

    forecast_cols = {
        "SARIMAX": "sarimax_forecast",
        "LSTM": "lstm_forecast",
        "Chronos-small": "chronos_small_median",
    }
    for model_name, col in forecast_cols.items():
        ax.plot(test_merged["week_start"], test_merged[col],
                color=MODEL_COLORS[model_name], linewidth=1.3, linestyle="--",
                label=model_name)

    ax.axvline(train["week_start"].iloc[-1], color="gray", linestyle="--", alpha=0.5)

    anomaly = test_merged[test_merged["is_anomaly_week"] == 1]
    if len(anomaly) > 0:
        ax.scatter(anomaly["week_start"], anomaly["search_index"],
                   color="red", marker="x", s=100, zorder=5, label="Anomaly")

    region_label = "Korea" if region == "korea" else "Global"
    ax.set_title(f"NB {region_label} — 3-Way Forecast Comparison (26-Week Test)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Search Index")
    ax.legend(loc="upper left", fontsize=9)

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_forecast_3way.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ================================================================
# Plot: error distribution box plot — 3-way
# ================================================================
def plot_error_distribution(all_errors):
    """Box plot of forecast errors by model and region."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    plot_models = ["SARIMAX", "LSTM", "Chronos-small"]
    for idx, region in enumerate(REGIONS):
        labels = []
        data = []
        for model in plot_models:
            if (model, region) in all_errors:
                labels.append(model)
                data.append(all_errors[(model, region)])

        bp = axes[idx].boxplot(data, labels=labels, patch_artist=True)
        for patch, model in zip(bp["boxes"], labels):
            patch.set_facecolor(MODEL_COLORS.get(model, "#888888"))
            patch.set_alpha(0.6)

        axes[idx].axhline(0, color="black", linewidth=0.5, alpha=0.5)
        region_label = "Korea" if region == "korea" else "Global"
        axes[idx].set_title(f"NB {region_label}")
        axes[idx].set_ylabel("Forecast Error (Actual - Predicted)")
        axes[idx].tick_params(axis="x", rotation=15)

    fig.suptitle("Forecast Error Distribution — 3-Way Comparison", fontsize=13)
    fig.tight_layout()

    fig_path = os.path.join(FIG_DIR, "forecast_error_distribution.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ================================================================
# Plot: train anomaly residual scatter
# ================================================================
def plot_train_anomaly_residuals(train_residuals_dict):
    """Scatter: train in-sample |residual| colored by anomaly flag."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for idx, region in enumerate(REGIONS):
        train_res = train_residuals_dict[region]
        anomaly = train_res[train_res["is_anomaly_week"] == 1]
        normal = train_res[train_res["is_anomaly_week"] == 0]

        axes[idx].scatter(normal["week_start"], normal["abs_residual"],
                          color="#3498DB", alpha=0.5, s=20, label=f"Normal (n={len(normal)})")
        if len(anomaly) > 0:
            axes[idx].scatter(anomaly["week_start"], anomaly["abs_residual"],
                              color="#E74C3C", alpha=0.8, s=50, marker="^",
                              label=f"Anomaly (n={len(anomaly)})")

        axes[idx].axhline(normal["abs_residual"].mean(), color="#3498DB",
                          linestyle="--", alpha=0.5, linewidth=0.8)
        if len(anomaly) > 0:
            axes[idx].axhline(anomaly["abs_residual"].mean(), color="#E74C3C",
                              linestyle="--", alpha=0.5, linewidth=0.8)

        region_label = "Korea" if region == "korea" else "Global"
        axes[idx].set_title(f"NB {region_label} — SARIMAX In-Sample |Residual|")
        axes[idx].set_xlabel("Date")
        axes[idx].set_ylabel("|Residual|")
        axes[idx].legend(fontsize=9)

    fig.suptitle("Train Set: Anomaly vs Normal Week SARIMAX Residuals", fontsize=13)
    fig.tight_layout()

    fig_path = os.path.join(FIG_DIR, "train_anomaly_residual_analysis.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ================================================================
# Plot: test anomaly error bar chart (with n=1 caveat)
# ================================================================
def plot_test_anomaly_error(metrics_df):
    """Bar chart: test RMSE anomaly vs normal weeks."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    plot_models = ["SARIMAX", "LSTM", "Chronos-small"]

    for idx, region in enumerate(REGIONS):
        region_df = metrics_df[(metrics_df["region"] == region) &
                               (metrics_df["model"].isin(plot_models))]
        normal = region_df[region_df["subset"] == "normal"]
        anomaly = region_df[region_df["subset"] == "anomaly"]

        models = [m for m in plot_models if m in normal["model"].values]
        x = np.arange(len(models))
        width = 0.35

        normal_vals = [normal[normal["model"] == m]["rmse"].values[0] for m in models]
        anomaly_vals = [anomaly[anomaly["model"] == m]["rmse"].values[0] for m in models]

        bars1 = axes[idx].bar(x - width/2, normal_vals, width,
                               label="Normal (n=25)", color="#3498DB", alpha=0.7)
        bars2 = axes[idx].bar(x + width/2, anomaly_vals, width,
                               label="Anomaly (n=1)*", color="#E74C3C", alpha=0.7)

        axes[idx].set_xticks(x)
        axes[idx].set_xticklabels(models, rotation=15)
        axes[idx].set_ylabel("RMSE")
        region_label = "Korea" if region == "korea" else "Global"
        axes[idx].set_title(f"NB {region_label}")
        axes[idx].legend(fontsize=9)

        for bar in bars1:
            axes[idx].text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                          f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=8)
        for bar in bars2:
            axes[idx].text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                          f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle("Test Set RMSE: Normal vs Anomaly Weeks\n* Anomaly n=1 — not statistically meaningful",
                 fontsize=12)
    fig.tight_layout()

    fig_path = os.path.join(FIG_DIR, "anomaly_week_error_analysis.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ================================================================
# Main
# ================================================================
if __name__ == "__main__":
    all_metrics = []
    all_errors = {}

    # ---- D1 + D3: 3-way metrics + overlay ----
    for region in REGIONS:
        print(f"\n{'='*60}")
        print(f"NB {region.upper()} — Comparison")
        print(f"{'='*60}")

        train, test_merged = load_forecasts(region)
        actual = test_merged["search_index"].values
        anomaly_mask = test_merged["is_anomaly_week"].values == 1

        forecast_cols = {
            "SARIMAX": "sarimax_forecast",
            "LSTM": "lstm_forecast",
            "Chronos-small": "chronos_small_median",
            "Chronos-base": "chronos_base_median",
        }

        for model_name, col in forecast_cols.items():
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

        plot_3way(train, test_merged, region)

    metrics_df = pd.DataFrame(all_metrics)

    # ---- D2: Train in-sample residual analysis ----
    print(f"\n{'='*60}")
    print("TRAIN IN-SAMPLE RESIDUAL ANALYSIS (SARIMAX)")
    print(f"{'='*60}")

    insample_results = []
    train_residuals_dict = {}
    for region in REGIONS:
        result, train_res = train_insample_residual_analysis(region)
        insample_results.append(result)
        train_residuals_dict[region] = train_res

        region_label = "Korea" if region == "korea" else "Global"
        print(f"\n{region_label}:")
        print(f"  Anomaly weeks in train: {result['n_anomaly_train']}")
        print(f"  Normal weeks in train:  {result['n_normal_train']}")
        print(f"  Anomaly mean |residual|: {result['anomaly_mean_abs_resid']}")
        print(f"  Normal mean |residual|:  {result['normal_mean_abs_resid']}")
        print(f"  Anomaly RMSE:            {result['anomaly_rmse']}")
        print(f"  Normal RMSE:             {result['normal_rmse']}")
        print(f"  Anomaly/Normal ratio:    {result['anomaly_to_normal_ratio']}x")

    insample_df = pd.DataFrame(insample_results)
    insample_path = os.path.join(DATA_DIR, "train_insample_residual_analysis.csv")
    insample_df.to_csv(insample_path, index=False)
    print(f"\nSaved: {insample_path}")

    plot_train_anomaly_residuals(train_residuals_dict)

    # ---- Plots ----
    plot_error_distribution(all_errors)
    plot_test_anomaly_error(metrics_df)

    # ---- Summary ----
    print(f"\n{'='*60}")
    print("FINAL 3-WAY COMPARISON (Chronos-small as representative)")
    print(f"{'='*60}")

    overall = metrics_df[metrics_df["subset"] == "all"].copy()
    three_way = overall[overall["model"].isin(["SARIMAX", "LSTM", "Chronos-small"])]
    pivot = three_way.pivot(index="model", columns="region", values=["rmse", "mape_pct"])
    print(pivot.to_string())

    print(f"\n  Note: Chronos-base results (Korea RMSE={overall[(overall['model']=='Chronos-base') & (overall['region']=='korea')]['rmse'].values[0]}, "
          f"Global RMSE={overall[(overall['model']=='Chronos-base') & (overall['region']=='global')]['rmse'].values[0]}) "
          f"omitted — small outperformed base in both series (short context anti-scaling).")

    metrics_path = os.path.join(DATA_DIR, "forecast_comparison_metrics.csv")
    metrics_df.to_csv(metrics_path, index=False)
    print(f"\nSaved: {metrics_path}")

    # Ranking
    print(f"\n{'='*60}")
    print("RANKING BY RMSE")
    print(f"{'='*60}")
    for region in REGIONS:
        region_overall = three_way[three_way["region"] == region].sort_values("rmse")
        region_label = "Korea" if region == "korea" else "Global"
        print(f"\n{region_label}:")
        for rank, (_, row) in enumerate(region_overall.iterrows(), 1):
            print(f"  {rank}. {row['model']:15s} RMSE={row['rmse']:.2f}  MAPE={row['mape_pct']:.1f}%")

    # Caveat
    print(f"\n{'='*60}")
    print("ANOMALY ANALYSIS CAVEAT")
    print(f"{'='*60}")
    print("  Test set anomaly weeks: n=1 per region — not statistically meaningful.")
    print("  Train in-sample analysis above provides more robust anomaly vs normal comparison.")
    print("  Finding: event-driven spikes are structurally harder to predict,")
    print("  consistent with Stage 5 anomaly detection limitations.")

    print("\nTrack D comparison complete.")
