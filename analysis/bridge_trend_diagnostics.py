"""
Stage 7 Step 0 follow-up -- Trend stationarity diagnostics for advisor handoff.

Step 0 escalated AMBIGUOUS_TRANSFORM for korea_trend, global_trend.
This script gathers additional evidence to inform advisor's transformation choice:
  - ADF with regression='ct' (deterministic trend in test eqn)
  - KPSS with regression='ct' (trend-stationary null)
  - 2nd differencing
  - Linear detrending + residual stationarity

Outputs:
  - data/bridge/trend_diagnostics.json
"""

import os
import sys
import json
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.bridge_stationarity_check import extract_data

warnings.filterwarnings("ignore", category=Warning, module="statsmodels")

DATA_DIR = "data/bridge"
JSON_PATH = os.path.join(DATA_DIR, "trend_diagnostics.json")
os.makedirs(DATA_DIR, exist_ok=True)


def adf_p(series, regression):
    s = pd.Series(series).dropna().astype(float)
    stat, p, *_ = adfuller(s, autolag="AIC", regression=regression)
    return float(stat), float(p)


def kpss_p(series, regression):
    s = pd.Series(series).dropna().astype(float)
    stat, p, *_ = kpss(s, regression=regression, nlags="auto")
    return float(stat), float(p)


def main():
    df = extract_data()
    out = {"date": datetime.now().isoformat(), "tests": []}

    print("\n=== ADF with deterministic trend (regression='ct') ===")
    for var in ["korea_trend", "global_trend"]:
        for label, s in [
            ("level", df[var]),
            ("diff1", df[var].diff()),
            ("diff2", df[var].diff().diff()),
        ]:
            stat, p = adf_p(s, "ct")
            print(f"  {var:<14} {label:<6}  ADF(ct) stat={stat:.3f}  p={p:.4f}")
            out["tests"].append(
                {"test": "adf_ct", "var": var, "transform": label, "stat": stat, "p": p}
            )

    print("\n=== KPSS trend-stationary (regression='ct') ===")
    for var in ["korea_trend", "global_trend"]:
        for label, s in [("level", df[var]), ("diff1", df[var].diff())]:
            stat, p = kpss_p(s, "ct")
            print(f"  {var:<14} {label:<6}  KPSS(ct) stat={stat:.3f}  p={p:.4f}")
            out["tests"].append(
                {"test": "kpss_ct", "var": var, "transform": label, "stat": stat, "p": p}
            )

    print("\n=== Linear detrended residual stationarity ===")
    t = np.arange(len(df), dtype=float)
    for var in ["korea_trend", "global_trend"]:
        s = df[var].astype(float).values
        coef = np.polyfit(t, s, 1)
        resid = s - np.polyval(coef, t)
        a_stat, a_p = adfuller(resid, autolag="AIC")[:2]
        k_stat, k_p, *_ = kpss(resid, regression="c", nlags="auto")
        print(
            f"  {var:<14}  slope/wk={coef[0]:.4f}  intercept={coef[1]:.2f}"
        )
        print(
            f"                resid ADF p={a_p:.4f}  KPSS p={k_p:.4f}"
        )
        out["tests"].append(
            {
                "test": "linear_detrend_residual",
                "var": var,
                "slope_per_week": float(coef[0]),
                "intercept": float(coef[1]),
                "adf_p": float(a_p),
                "kpss_p": float(k_p),
            }
        )

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nJSON saved: {JSON_PATH}")


if __name__ == "__main__":
    main()