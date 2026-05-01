"""
Stage 6 Forecasting — A2: SARIMAX Order Selection

1. d=1 differenced ACF/PACF for non-seasonal (p, q) identification
2. pmdarima auto_arima (seasonal=False, d=1) for automated order search
3. Fourier terms construction (K=2 for 52w annual + K=2 for 13w quarterly)
4. Manual vs auto_arima AIC comparison

Inputs:
    data/forecast/nb_korea_forecast_data.csv
    data/forecast/nb_global_forecast_data.csv

Outputs:
    figures/forecast/nb_korea_diff_acf_pacf.png
    figures/forecast/nb_global_diff_acf_pacf.png
    (console) auto_arima results + AIC comparison

Usage:
    python -m analysis.forecast_sarimax_order
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
import pmdarima as pm
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.stattools import adfuller

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
FOURIER_CONFIG = {52: 2, 13: 2}  # {period: K}


# ================================================================
# Fourier terms construction
# ================================================================
def make_fourier_terms(n, period_k_map):
    """Generate Fourier sin/cos terms for given periods and harmonics.

    Args:
        n: number of time steps (integer index 0..n-1)
        period_k_map: dict {period: K} e.g. {52: 2, 13: 2}

    Returns:
        DataFrame with columns like sin_52_1, cos_52_1, ..., sin_13_2, cos_13_2
    """
    t = np.arange(n)
    cols = {}
    for period, K in period_k_map.items():
        for k in range(1, K + 1):
            cols[f"sin_{period}_{k}"] = np.sin(2 * np.pi * k * t / period)
            cols[f"cos_{period}_{k}"] = np.cos(2 * np.pi * k * t / period)
    return pd.DataFrame(cols)


# ================================================================
# ADF stationarity test
# ================================================================
def run_adf_test(series, label):
    """Run Augmented Dickey-Fuller test and print result."""
    result = adfuller(series.dropna(), autolag="AIC")
    stationary = "YES" if result[1] < 0.05 else "NO"
    print(f"  ADF ({label}): stat={result[0]:.4f}, p={result[1]:.4f} -> stationary={stationary}")
    return result[1] < 0.05


# ================================================================
# Differenced ACF/PACF plot
# ================================================================
def plot_diff_acf_pacf(series, region):
    """Generate ACF/PACF plots for d=1 differenced series."""
    diff = series.diff().dropna()

    fig, axes = plt.subplots(1, 2, figsize=(14, 4))

    plot_acf(diff, ax=axes[0], lags=52, alpha=0.05)
    axes[0].set_title("ACF (d=1)")

    plot_pacf(diff, ax=axes[1], lags=52, alpha=0.05, method="ywm")
    axes[1].set_title("PACF (d=1)")

    region_label = "Korea" if region == "korea" else "Global"
    fig.suptitle(f"NB {region_label} Search Index — Differenced ACF / PACF", fontsize=13)
    fig.tight_layout()

    fig_path = os.path.join(FIG_DIR, f"nb_{region}_diff_acf_pacf.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ================================================================
# auto_arima search
# ================================================================
def run_auto_arima(train_y, train_exog, region):
    """Run pmdarima auto_arima with seasonal=False, d=1."""
    print(f"  Running auto_arima (seasonal=False, d=1, max_p=5, max_q=5)...")
    model = pm.auto_arima(
        train_y,
        exogenous=train_exog,
        d=1,
        seasonal=False,
        max_p=5,
        max_q=5,
        stepwise=True,
        suppress_warnings=True,
        error_action="ignore",
        trace=False,
        information_criterion="aic",
    )
    print(f"  Best order: {model.order}, AIC={model.aic():.2f}")
    print(f"  Summary: {model.order[0]}d{model.order[1]}q{model.order[2]}")
    return model


# ================================================================
# Manual candidate AIC comparison
# ================================================================
def compare_manual_orders(train_y, train_exog, candidates, region):
    """Fit ARIMA with manual candidate orders and compare AIC."""
    from statsmodels.tsa.arima.model import ARIMA

    results = []
    for order in candidates:
        try:
            model = ARIMA(train_y, exog=train_exog, order=order)
            fit = model.fit()
            results.append({"order": str(order), "aic": fit.aic, "bic": fit.bic})
        except Exception as e:
            results.append({"order": str(order), "aic": np.nan, "bic": np.nan})
            print(f"  {order} failed: {e}")

    result_df = pd.DataFrame(results).sort_values("aic")
    print(f"\n  Manual order comparison ({region.upper()}):")
    print(f"  {result_df.to_string(index=False)}")
    return result_df


# ================================================================
# Main
# ================================================================
if __name__ == "__main__":
    for region in REGIONS:
        print(f"\n{'='*60}")
        print(f"NB {region.upper()} — Order Selection")
        print(f"{'='*60}")

        # Load prepared data
        csv_path = os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv")
        df = pd.read_csv(csv_path, parse_dates=["week_start"])
        train = df[df["split"] == "train"].copy().reset_index(drop=True)

        # ADF test: raw vs differenced
        print("\n[1] Stationarity tests:")
        run_adf_test(train["search_index"], "raw")
        run_adf_test(train["search_index"].diff().dropna(), "d=1")

        # Differenced ACF/PACF
        print("\n[2] Differenced ACF/PACF:")
        plot_diff_acf_pacf(train["search_index"], region)

        # Build Fourier + CSI exogenous for train
        fourier_train = make_fourier_terms(len(train), FOURIER_CONFIG)
        train_exog = pd.concat([
            fourier_train,
            train[["csi"]].reset_index(drop=True),
        ], axis=1)

        # auto_arima
        print("\n[3] auto_arima:")
        auto_model = run_auto_arima(
            train["search_index"].values,
            train_exog.values,
            region,
        )

        # Manual candidates based on ACF/PACF visual inspection
        print("\n[4] Manual order comparison:")
        auto_order = auto_model.order
        candidates = [
            (1, 1, 0),
            (2, 1, 0),
            (1, 1, 1),
            (2, 1, 1),
            (3, 1, 0),
            (2, 1, 2),
        ]
        # Add auto_arima result if not already in list
        if auto_order not in candidates:
            candidates.append(auto_order)

        compare_manual_orders(
            train["search_index"].values,
            train_exog.values,
            candidates,
            region,
        )

        # Report Fourier terms structure
        print(f"\n[5] Exogenous columns ({train_exog.shape[1]} total):")
        print(f"  Fourier: {list(fourier_train.columns)}")
        print(f"  CSI: 1 column (forward-filled monthly)")
        total_params = auto_order[0] + auto_order[2] + train_exog.shape[1] + 1  # +1 for intercept-ish
        print(f"  Estimated total params: ~{total_params} / {len(train)} obs = 1:{len(train)//total_params} ratio")

    print("\nA2 order selection complete.")
