"""
Stage 6 Forecasting — A3/A4: SARIMAX Model Fit + Forecast + Evaluation

Fits ARIMA + Fourier + CSI exogenous for NB Korea (0,1,1) and NB Global (0,1,0).
Generates 26-week forecast, evaluates RMSE/MAE/MAPE, and analyzes anomaly week errors.

Inputs:
    data/forecast/nb_korea_forecast_data.csv
    data/forecast/nb_global_forecast_data.csv

Outputs:
    data/forecast/sarimax_forecast_korea.csv
    data/forecast/sarimax_forecast_global.csv
    data/forecast/sarimax_metrics.csv
    figures/forecast/nb_korea_sarimax_forecast.png
    figures/forecast/nb_global_sarimax_forecast.png

Usage:
    python -m analysis.forecast_sarimax
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
FOURIER_CONFIG = {52: 2, 13: 2}

ORDERS = {
    "korea": (0, 1, 1),
    "global": (0, 1, 0),
}

REGIONS = ["korea", "global"]


# ================================================================
# Fourier terms (must match A2 exactly)
# ================================================================
def make_fourier_terms(n, period_k_map, start_idx=0):
    """Generate Fourier sin/cos terms.

    Args:
        n: number of time steps
        period_k_map: dict {period: K}
        start_idx: starting index (for extending to test period)
    """
    t = np.arange(start_idx, start_idx + n)
    cols = {}
    for period, K in period_k_map.items():
        for k in range(1, K + 1):
            cols[f"sin_{period}_{k}"] = np.sin(2 * np.pi * k * t / period)
            cols[f"cos_{period}_{k}"] = np.cos(2 * np.pi * k * t / period)
    return pd.DataFrame(cols)


# ================================================================
# Build exogenous matrix
# ================================================================
def build_exog(df, start_idx=0):
    """Build exogenous matrix: Fourier terms + CSI."""
    n = len(df)
    fourier = make_fourier_terms(n, FOURIER_CONFIG, start_idx=start_idx)
    exog = pd.concat([
        fourier,
        df[["csi"]].reset_index(drop=True),
    ], axis=1)
    return exog


# ================================================================
# Evaluation metrics
# ================================================================
def compute_metrics(actual, predicted, label=""):
    """Compute RMSE, MAE, MAPE (excluding zeros)."""
    residuals = actual - predicted
    rmse = np.sqrt(np.mean(residuals ** 2))
    mae = np.mean(np.abs(residuals))

    # MAPE excluding zeros
    nonzero_mask = actual != 0
    if nonzero_mask.sum() > 0:
        mape = np.mean(np.abs(residuals[nonzero_mask] / actual[nonzero_mask])) * 100
    else:
        mape = np.nan

    return {"label": label, "rmse": rmse, "mae": mae, "mape_pct": mape}


# ================================================================
# Forecast plot
# ================================================================
def plot_forecast(train, test, forecast_values, conf_int, region, metrics):
    """Plot actual vs forecast with confidence interval."""
    fig, ax = plt.subplots(figsize=(14, 5))

    # Train
    ax.plot(train["week_start"], train["search_index"],
            color="#888888", linewidth=0.8, label="Train")

    # Test actual
    ax.plot(test["week_start"], test["search_index"],
            color="#E74C3C", linewidth=1.5, label="Actual (Test)")

    # Forecast
    ax.plot(test["week_start"], forecast_values,
            color="#3498DB", linewidth=1.5, linestyle="--", label="SARIMAX Forecast")

    # Confidence interval
    ax.fill_between(test["week_start"], conf_int[:, 0], conf_int[:, 1],
                     color="#3498DB", alpha=0.15, label="95% CI")

    # Train/Test split line
    ax.axvline(train["week_start"].iloc[-1], color="gray", linestyle="--", alpha=0.5)

    # Anomaly weeks in test
    anomaly_test = test[test["is_anomaly_week"] == 1]
    if len(anomaly_test) > 0:
        ax.scatter(anomaly_test["week_start"], anomaly_test["search_index"],
                   color="red", marker="x", s=80, zorder=5, label="Anomaly Week")

    region_label = "Korea" if region == "korea" else "Global"
    order_str = f"ARIMA{ORDERS[region]}"
    ax.set_title(
        f"NB {region_label} — SARIMAX Forecast ({order_str} + Fourier + CSI)\n"
        f"RMSE={metrics['rmse']:.2f}  MAE={metrics['mae']:.2f}  MAPE={metrics['mape_pct']:.1f}%"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Search Index")
    ax.legend(loc="upper left", fontsize=9)

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_sarimax_forecast.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ================================================================
# Main
# ================================================================
if __name__ == "__main__":
    all_metrics = []

    for region in REGIONS:
        print(f"\n{'='*60}")
        print(f"NB {region.upper()} — SARIMAX Forecast")
        print(f"{'='*60}")

        # Load data
        csv_path = os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv")
        df = pd.read_csv(csv_path, parse_dates=["week_start"])

        train = df[df["split"] == "train"].copy().reset_index(drop=True)
        test = df[df["split"] == "test"].copy().reset_index(drop=True)

        n_train = len(train)
        n_test = len(test)

        # Build exogenous
        train_exog = build_exog(train, start_idx=0)
        test_exog = build_exog(test, start_idx=n_train)

        # Fit model
        order = ORDERS[region]
        print(f"\n  Fitting ARIMA{order} with {train_exog.shape[1]} exogenous columns...")
        model = ARIMA(
            train["search_index"].values,
            exog=train_exog.values,
            order=order,
        )
        fit = model.fit()
        print(f"  AIC={fit.aic:.2f}, BIC={fit.bic:.2f}")

        # Forecast
        forecast_result = fit.get_forecast(steps=n_test, exog=test_exog.values)
        forecast_values = forecast_result.predicted_mean
        conf_int = forecast_result.conf_int(alpha=0.05)

        # Evaluation — overall
        actual = test["search_index"].values
        metrics_all = compute_metrics(actual, forecast_values, f"{region}_all")
        print(f"\n  Overall: RMSE={metrics_all['rmse']:.2f}, MAE={metrics_all['mae']:.2f}, MAPE={metrics_all['mape_pct']:.1f}%")

        # Evaluation — anomaly vs non-anomaly weeks
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
        forecast_df["sarimax_forecast"] = forecast_values
        forecast_df["sarimax_lower"] = conf_int[:, 0]
        forecast_df["sarimax_upper"] = conf_int[:, 1]
        forecast_df["sarimax_error"] = actual - forecast_values
        forecast_csv = os.path.join(DATA_DIR, f"sarimax_forecast_{region}.csv")
        forecast_df.to_csv(forecast_csv, index=False)
        print(f"  Saved: {forecast_csv}")

        # Plot
        plot_forecast(train, test, forecast_values, conf_int, region, metrics_all)

        # Coefficient summary
        print(f"\n  Exogenous coefficients:")
        exog_names = list(make_fourier_terms(1, FOURIER_CONFIG).columns) + ["csi"]
        params = fit.params
        # ARIMA params come first, then exog
        n_arima = len(params) - len(exog_names)
        for i, name in enumerate(exog_names):
            coef = params[n_arima + i]
            pval = fit.pvalues[n_arima + i]
            sig = "*" if pval < 0.05 else ""
            print(f"    {name:>12s}: {coef:>8.4f} (p={pval:.3f}) {sig}")

    # Save metrics summary
    metrics_df = pd.DataFrame(all_metrics)
    metrics_path = os.path.join(DATA_DIR, "sarimax_metrics.csv")
    metrics_df.to_csv(metrics_path, index=False)
    print(f"\nSaved: {metrics_path}")
    print("\nA3/A4 SARIMAX complete.")
