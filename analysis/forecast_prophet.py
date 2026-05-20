"""
Stage 6 Forecasting — Track E: Prophet Forecast

Prophet with additive seasonality (yearly + quarterly 13w custom) + CSI regressor.
Added post-completion as v3 plan alignment — SARIMAX vs Prophet comparison axis.

Inputs:
    data/forecast/nb_korea_forecast_data.csv
    data/forecast/nb_global_forecast_data.csv

Outputs:
    data/forecast/prophet_forecast_korea.csv
    data/forecast/prophet_forecast_global.csv
    data/forecast/prophet_metrics.csv
    figures/forecast/nb_korea_prophet_forecast.png
    figures/forecast/nb_global_prophet_forecast.png

Usage:
    python -m analysis.forecast_prophet
"""

import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from prophet import Prophet

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

# Constants
DATA_DIR = "data/forecast"
FIG_DIR = "figures/forecast"
REGIONS = ["korea", "global"]


# Evaluation metrics
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


# Build Prophet dataframe
def build_prophet_df(df):
    """Convert forecast data to Prophet format (ds, y, csi)."""
    pdf = pd.DataFrame({
        "ds": df["week_start"],
        "y": df["search_index"],
        "csi": df["csi"],
    })
    return pdf


# Forecast plot
def plot_forecast(train_df, test_df, forecast_values, lower, upper, region, metrics):
    """Plot actual vs Prophet forecast."""
    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(train_df["week_start"], train_df["search_index"],
            color="#888888", linewidth=0.8, label="Train")
    ax.plot(test_df["week_start"], test_df["search_index"],
            color="#E74C3C", linewidth=1.5, label="Actual (Test)")
    ax.plot(test_df["week_start"], forecast_values,
            color="#F39C12", linewidth=1.5, linestyle="--", label="Prophet Forecast")
    ax.fill_between(test_df["week_start"], lower, upper,
                     color="#F39C12", alpha=0.15, label="95% CI")

    ax.axvline(train_df["week_start"].iloc[-1], color="gray", linestyle="--", alpha=0.5)

    anomaly_test = test_df[test_df["is_anomaly_week"] == 1]
    if len(anomaly_test) > 0:
        ax.scatter(anomaly_test["week_start"], anomaly_test["search_index"],
                   color="red", marker="x", s=80, zorder=5, label="Anomaly Week")

    region_label = "Korea" if region == "korea" else "Global"
    ax.set_title(
        f"NB {region_label} — Prophet Forecast (additive, quarterly custom, CSI regressor)\n"
        f"RMSE={metrics['rmse']:.2f}  MAE={metrics['mae']:.2f}  MAPE={metrics['mape_pct']:.1f}%"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Search Index")
    ax.legend(loc="upper left", fontsize=9)

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_prophet_forecast.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# Main
if __name__ == "__main__":
    all_metrics = []

    for region in REGIONS:
        print(f"\n{'='*60}")
        print(f"NB {region.upper()} — Prophet Forecast")
        print(f"{'='*60}")

        # Load data
        csv_path = os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv")
        df = pd.read_csv(csv_path, parse_dates=["week_start"])

        train = df[df["split"] == "train"].copy().reset_index(drop=True)
        test = df[df["split"] == "test"].copy().reset_index(drop=True)

        # Build Prophet dataframes
        train_prophet = build_prophet_df(train)
        test_prophet = build_prophet_df(test)

        # Fit Prophet
        m = Prophet(
            seasonality_mode="additive",
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
        )
        # Custom quarterly seasonality: 13 weeks = 91.25 days
        m.add_seasonality(name="quarterly", period=91.25, fourier_order=2)
        # CSI as external regressor
        m.add_regressor("csi")

        m.fit(train_prophet)

        # Predict on test period
        forecast = m.predict(test_prophet[["ds", "csi"]])

        forecast_values = forecast["yhat"].values
        lower = forecast["yhat_lower"].values
        upper = forecast["yhat_upper"].values
        actual = test["search_index"].values

        # Evaluation — overall
        metrics_all = compute_metrics(actual, forecast_values, f"{region}_all")
        print(f"\n  Overall: RMSE={metrics_all['rmse']:.2f}, MAE={metrics_all['mae']:.2f}, MAPE={metrics_all['mape_pct']:.1f}%")

        # Evaluation — anomaly vs non-anomaly
        anomaly_mask = test["is_anomaly_week"].values == 1
        if anomaly_mask.sum() > 0:
            metrics_anom = compute_metrics(actual[anomaly_mask], forecast_values[anomaly_mask], f"{region}_anomaly")
            print(f"  Anomaly weeks ({anomaly_mask.sum()}): RMSE={metrics_anom['rmse']:.2f}")
            all_metrics.append(metrics_anom)

        non_anomaly_mask = ~anomaly_mask
        if non_anomaly_mask.sum() > 0:
            metrics_normal = compute_metrics(actual[non_anomaly_mask], forecast_values[non_anomaly_mask], f"{region}_normal")
            print(f"  Normal weeks ({non_anomaly_mask.sum()}): RMSE={metrics_normal['rmse']:.2f}")
            all_metrics.append(metrics_normal)

        all_metrics.append(metrics_all)

        # Save forecast
        forecast_df = test[["week_start", "search_index", "is_anomaly_week"]].copy()
        forecast_df["prophet_forecast"] = forecast_values
        forecast_df["prophet_lower"] = lower
        forecast_df["prophet_upper"] = upper
        forecast_df["prophet_error"] = actual - forecast_values
        forecast_csv = os.path.join(DATA_DIR, f"prophet_forecast_{region}.csv")
        forecast_df.to_csv(forecast_csv, index=False)
        print(f"  Saved: {forecast_csv}")

        # Prophet component breakdown
        print(f"\n  Changepoints detected: {len(m.changepoints)}")
        print(f"  Components: {list(forecast.columns[forecast.columns.str.contains('weekly|yearly|quarterly|csi|trend')])}")

        # Plot
        plot_forecast(train, test, forecast_values, lower, upper, region, metrics_all)

    # Save metrics
    metrics_df = pd.DataFrame(all_metrics)
    metrics_path = os.path.join(DATA_DIR, "prophet_metrics.csv")
    metrics_df.to_csv(metrics_path, index=False)
    print(f"\nSaved: {metrics_path}")
    print("\nTrack E Prophet complete.")
