"""
Stage 6 Forecasting — Track C: Chronos Zero-Shot Forecast

Univariate zero-shot inference using Amazon Chronos-T5 (small + base).
No exogenous variables — tests foundation model pattern recognition alone.

Inputs:
    data/forecast/nb_korea_forecast_data.csv
    data/forecast/nb_global_forecast_data.csv

Outputs:
    data/forecast/chronos_forecast_korea.csv
    data/forecast/chronos_forecast_global.csv
    data/forecast/chronos_metrics.csv
    figures/forecast/nb_korea_chronos_forecast.png
    figures/forecast/nb_global_chronos_forecast.png

Usage:
    python -m analysis.forecast_chronos
"""

# stdlib
import os
import time
import warnings

# third-party
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from chronos import ChronosPipeline

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
FORECAST_HORIZON = 26
NUM_SAMPLES = 20  # probabilistic samples for quantile estimation

MODELS = {
    "small": "amazon/chronos-t5-small",
    "base": "amazon/chronos-t5-base",
}

# M2 MacBook: use CPU with float32 (bfloat16 not supported on MPS)
DEVICE = "cpu"
DTYPE = torch.float32


# ================================================================
# Evaluation metrics
# ================================================================
def compute_metrics(actual, predicted, label=""):
    """Compute RMSE, MAE, MAPE (excluding zeros)."""
    residuals = actual - predicted
    rmse = np.sqrt(np.mean(residuals ** 2))
    mae = np.mean(np.abs(residuals))

    nonzero_mask = actual != 0
    if nonzero_mask.sum() > 0:
        mape = np.mean(np.abs(residuals[nonzero_mask] / actual[nonzero_mask])) * 100
    else:
        mape = np.nan

    return {"label": label, "rmse": rmse, "mae": mae, "mape_pct": mape}


# ================================================================
# Forecast plot (overlays both model sizes)
# ================================================================
def plot_forecast(train_df, test_df, forecasts_dict, region, metrics_dict):
    """Plot actual vs Chronos forecasts for all model sizes."""
    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(train_df["week_start"], train_df["search_index"],
            color="#888888", linewidth=0.8, label="Train")
    ax.plot(test_df["week_start"], test_df["search_index"],
            color="#E74C3C", linewidth=1.5, label="Actual (Test)")

    colors = {"small": "#9B59B6", "base": "#E67E22"}
    for model_size, forecast_data in forecasts_dict.items():
        median = forecast_data["median"]
        lower = forecast_data["lower"]
        upper = forecast_data["upper"]
        m = metrics_dict[model_size]

        ax.plot(test_df["week_start"], median,
                color=colors[model_size], linewidth=1.5, linestyle="--",
                label=f"Chronos-{model_size} (RMSE={m['rmse']:.2f})")
        ax.fill_between(test_df["week_start"], lower, upper,
                         color=colors[model_size], alpha=0.1)

    ax.axvline(train_df["week_start"].iloc[-1], color="gray", linestyle="--", alpha=0.5)

    anomaly_test = test_df[test_df["is_anomaly_week"] == 1]
    if len(anomaly_test) > 0:
        ax.scatter(anomaly_test["week_start"], anomaly_test["search_index"],
                   color="red", marker="x", s=80, zorder=5, label="Anomaly Week")

    region_label = "Korea" if region == "korea" else "Global"
    ax.set_title(f"NB {region_label} — Chronos Zero-Shot Forecast (small vs base)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Search Index")
    ax.legend(loc="upper left", fontsize=9)

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_chronos_forecast.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ================================================================
# Main
# ================================================================
if __name__ == "__main__":
    all_metrics = []

    # Load models once (reuse across regions)
    pipelines = {}
    for model_size, model_id in MODELS.items():
        print(f"Loading {model_id}...")
        t0 = time.time()
        pipelines[model_size] = ChronosPipeline.from_pretrained(
            model_id,
            device_map=DEVICE,
            torch_dtype=DTYPE,
        )
        print(f"  Loaded in {time.time() - t0:.1f}s")

    for region in REGIONS:
        print(f"\n{'='*60}")
        print(f"NB {region.upper()} — Chronos Zero-Shot Forecast")
        print(f"{'='*60}")

        # Load data
        csv_path = os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv")
        df = pd.read_csv(csv_path, parse_dates=["week_start"])
        train = df[df["split"] == "train"].copy().reset_index(drop=True)
        test = df[df["split"] == "test"].copy().reset_index(drop=True)
        actual = test["search_index"].values

        # Context: full train series as torch tensor
        context = torch.tensor(train["search_index"].values, dtype=DTYPE)

        forecasts_dict = {}
        metrics_dict = {}

        for model_size, pipeline in pipelines.items():
            print(f"\n  --- Chronos-{model_size} ---")
            t0 = time.time()

            # Predict: returns (num_samples, forecast_horizon) tensor
            samples = pipeline.predict(
                context,
                prediction_length=FORECAST_HORIZON,
                num_samples=NUM_SAMPLES,
            )
            elapsed = time.time() - t0
            print(f"  Inference: {elapsed:.1f}s ({NUM_SAMPLES} samples)")

            # Extract quantiles
            sample_arr = samples[0].numpy()  # (num_samples, forecast_horizon)
            median = np.quantile(sample_arr, 0.5, axis=0)
            lower = np.quantile(sample_arr, 0.1, axis=0)
            upper = np.quantile(sample_arr, 0.9, axis=0)

            forecasts_dict[model_size] = {
                "median": median, "lower": lower, "upper": upper
            }

            # Metrics — overall
            m_all = compute_metrics(actual, median, f"{region}_{model_size}_all")
            print(f"  Overall: RMSE={m_all['rmse']:.2f}, MAE={m_all['mae']:.2f}, MAPE={m_all['mape_pct']:.1f}%")

            # Metrics — anomaly vs normal
            anomaly_mask = test["is_anomaly_week"].values == 1
            if anomaly_mask.sum() > 0:
                m_anom = compute_metrics(actual[anomaly_mask], median[anomaly_mask],
                                         f"{region}_{model_size}_anomaly")
                print(f"  Anomaly weeks ({anomaly_mask.sum()}): RMSE={m_anom['rmse']:.2f}")
                all_metrics.append(m_anom)

            non_anomaly_mask = ~anomaly_mask
            if non_anomaly_mask.sum() > 0:
                m_norm = compute_metrics(actual[non_anomaly_mask], median[non_anomaly_mask],
                                         f"{region}_{model_size}_normal")
                print(f"  Normal weeks ({non_anomaly_mask.sum()}): RMSE={m_norm['rmse']:.2f}")
                all_metrics.append(m_norm)

            all_metrics.append(m_all)
            metrics_dict[model_size] = m_all

        # Save forecast CSV (both sizes)
        forecast_df = test[["week_start", "search_index", "is_anomaly_week"]].copy()
        for model_size, fdata in forecasts_dict.items():
            forecast_df[f"chronos_{model_size}_median"] = fdata["median"]
            forecast_df[f"chronos_{model_size}_lower"] = fdata["lower"]
            forecast_df[f"chronos_{model_size}_upper"] = fdata["upper"]
            forecast_df[f"chronos_{model_size}_error"] = actual - fdata["median"]
        forecast_csv = os.path.join(DATA_DIR, f"chronos_forecast_{region}.csv")
        forecast_df.to_csv(forecast_csv, index=False)
        print(f"\n  Saved: {forecast_csv}")

        # Plot
        plot_forecast(train, test, forecasts_dict, region, metrics_dict)

    # Save metrics
    metrics_df = pd.DataFrame(all_metrics)
    metrics_path = os.path.join(DATA_DIR, "chronos_metrics.csv")
    metrics_df.to_csv(metrics_path, index=False)
    print(f"\nSaved: {metrics_path}")
    print("\nTrack C Chronos complete.")
