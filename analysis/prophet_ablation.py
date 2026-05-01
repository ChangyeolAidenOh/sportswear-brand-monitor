"""
Stage 6 — Prophet Ablation: Yearly Fourier Order 2 vs 10

Separates changepoint effect from Fourier flexibility effect.
Runs Prophet with yearly_seasonality fourier_order=2 (SARIMAX parity)
and compares against original fourier_order=10 results.

Usage:
    python -m analysis.prophet_ablation
"""

# stdlib
import os
import warnings

# third-party
import numpy as np
import pandas as pd
from prophet import Prophet

warnings.filterwarnings("ignore")

# ================================================================
# Constants
# ================================================================
DATA_DIR = "data/forecast"
REGIONS = ["korea", "global"]


def compute_metrics(actual, predicted):
    residuals = actual - predicted
    rmse = np.sqrt(np.mean(residuals ** 2))
    mae = np.mean(np.abs(residuals))
    nonzero = actual != 0
    mape = np.mean(np.abs(residuals[nonzero] / actual[nonzero])) * 100 if nonzero.sum() > 0 else np.nan
    return rmse, mae, mape


def run_prophet(train, test, yearly_fourier_order):
    """Run Prophet with specified yearly fourier_order."""
    train_p = pd.DataFrame({"ds": train["week_start"], "y": train["search_index"], "csi": train["csi"]})
    test_p = pd.DataFrame({"ds": test["week_start"], "csi": test["csi"]})

    m = Prophet(
        seasonality_mode="additive",
        yearly_seasonality=False,  # disable default, add manually
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
    )
    m.add_seasonality(name="yearly", period=365.25, fourier_order=yearly_fourier_order)
    m.add_seasonality(name="quarterly", period=91.25, fourier_order=2)
    m.add_regressor("csi")
    m.fit(train_p)

    forecast = m.predict(test_p)
    return forecast["yhat"].values


if __name__ == "__main__":
    print(f"{'='*70}")
    print("PROPHET ABLATION: Yearly Fourier Order Effect")
    print(f"{'='*70}")

    for region in REGIONS:
        df = pd.read_csv(os.path.join(DATA_DIR, f"nb_{region}_forecast_data.csv"), parse_dates=["week_start"])
        train = df[df["split"] == "train"].reset_index(drop=True)
        test = df[df["split"] == "test"].reset_index(drop=True)
        actual = test["search_index"].values

        # Ablation: K=2 (SARIMAX parity)
        pred_k2 = run_prophet(train, test, yearly_fourier_order=2)
        rmse_k2, mae_k2, mape_k2 = compute_metrics(actual, pred_k2)

        # Original: K=10 (Prophet default)
        pred_k10 = run_prophet(train, test, yearly_fourier_order=10)
        rmse_k10, mae_k10, mape_k10 = compute_metrics(actual, pred_k10)

        # SARIMAX reference (from saved metrics)
        sarimax_df = pd.read_csv(os.path.join(DATA_DIR, f"sarimax_forecast_{region}.csv"))
        sarimax_pred = sarimax_df["sarimax_forecast"].values
        rmse_s, mae_s, mape_s = compute_metrics(actual, sarimax_pred)

        region_label = "Korea" if region == "korea" else "Global"
        print(f"\n--- NB {region_label} ---")
        print(f"  {'Model':<25s} {'RMSE':>7s} {'MAE':>7s} {'MAPE':>7s}")
        print(f"  {'SARIMAX (K=2, no CP)':<25s} {rmse_s:>7.2f} {mae_s:>7.2f} {mape_s:>6.1f}%")
        print(f"  {'Prophet (K=2, with CP)':<25s} {rmse_k2:>7.2f} {mae_k2:>7.2f} {mape_k2:>6.1f}%")
        print(f"  {'Prophet (K=10, with CP)':<25s} {rmse_k10:>7.2f} {mae_k10:>7.2f} {mape_k10:>6.1f}%")

        # Effect decomposition
        cp_effect = rmse_s - rmse_k2      # changepoint contribution
        fourier_effect = rmse_k2 - rmse_k10  # fourier flexibility contribution
        total = rmse_s - rmse_k10

        print(f"\n  Effect decomposition (RMSE reduction vs SARIMAX):")
        print(f"    Total improvement:     {total:+.2f}")
        print(f"    Changepoint effect:    {cp_effect:+.2f} ({cp_effect/total*100:.0f}%)" if total != 0 else "    Changepoint effect:    0.00")
        print(f"    Fourier K=10 effect:   {fourier_effect:+.2f} ({fourier_effect/total*100:.0f}%)" if total != 0 else "    Fourier K=10 effect:   0.00")

    print(f"\nAblation complete.")
