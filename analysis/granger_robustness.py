"""
Stage 4 Track A — Robustness Check
adidas/global and nike/global residuals failed ADF at 5%.
This script applies 1st differencing to non-stationary residuals
and re-runs Granger to verify whether significance survives.

Usage:
  python analysis/granger_robustness.py
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

from database.connection import get_conn

# CONSTANTS

MAX_LAG = 4
NON_STATIONARY_PAIRS = [
    ("adidas", "global"),   # ADF p=0.2703, Granger: Search->CSI sig at lag 4
    ("nike", "global"),     # ADF p=0.0562, Granger: Independent (less concern)
]

REPORT_LINES = []


def log(msg=""):
    print(msg)
    REPORT_LINES.append(msg)


def section(title):
    log("")
    log(f"## {title}")
    log("")


# DATA EXTRACTION (reuse from main script)

def load_aligned_data():
    """Load MSTL residual monthly + CSI aligned data."""
    query_residual = """
        SELECT brand, region, week_start, residual
        FROM mart.seasonal_components
        WHERE product_line IS NULL
        ORDER BY brand, region, week_start
    """
    query_csi = """
        SELECT period, value AS csi
        FROM raw.ecos_raw
        WHERE stat_code = '511Y002' AND item_code = 'FME'
        ORDER BY period
    """
    with get_conn() as conn:
        residual_df = pd.read_sql(query_residual, conn)
        csi_df = pd.read_sql(query_csi, conn)

    residual_df["week_start"] = pd.to_datetime(residual_df["week_start"])
    residual_df["year_month"] = residual_df["week_start"].dt.to_period("M").dt.to_timestamp()

    monthly = (
        residual_df.groupby(["brand", "region", "year_month"])
        .agg(residual_mean=("residual", "mean"))
        .reset_index()
    )

    csi_df["year_month"] = pd.to_datetime(csi_df["period"] + "-01")
    csi_df["csi"] = pd.to_numeric(csi_df["csi"], errors="coerce")
    csi_df = csi_df[["year_month", "csi"]]

    aligned = pd.merge(monthly, csi_df, on="year_month", how="inner")
    return aligned


# ROBUSTNESS CHECK

def robustness_check(aligned):
    """Apply 1st diff to non-stationary residuals, re-run Granger."""
    section("Robustness Check: Non-stationary Residual Series")

    log("Non-stationary series identified in Step A3:")
    log("  adidas/global: ADF p=0.2703 (Search->CSI sig at lag 4, p=0.0443)")
    log("  nike/global: ADF p=0.0562 (Independent — null result, lower concern)")
    log("")
    log("Procedure: apply 1st differencing to residual, verify ADF, re-run Granger.")

    for brand, region in NON_STATIONARY_PAIRS:
        log("")
        log(f"### {brand}/{region}")

        grp = aligned[
            (aligned["brand"] == brand) & (aligned["region"] == region)
        ].sort_values("year_month").reset_index(drop=True)

        residual = grp["residual_mean"].values
        csi = grp["csi"].values

        # 1st diff residual
        residual_d1 = np.diff(residual)
        # CSI also 1st diff (same as main analysis)
        csi_d1 = np.diff(csi)

        # ADF on differenced residual
        adf_result = adfuller(residual_d1, autolag="AIC")
        log(f"  residual diff1 ADF: stat={adf_result[0]:.4f}, p={adf_result[1]:.4f}")

        if adf_result[1] >= 0.05:
            log(f"  [WARN] still non-stationary after differencing")
            continue

        log(f"  residual diff1: stationary (p={adf_result[1]:.4f})")

        # Re-run bidirectional Granger with both series differenced
        n_obs = len(residual_d1)
        log(f"  observations: {n_obs}")

        # Search -> CSI
        data_s2c = np.column_stack([csi_d1, residual_d1])
        log("")
        log(f"  Search(d1) -> CSI(d1):")
        log(f"  | Lag | F-stat | p-value | Sig |")
        log(f"  |---|---|---|---|")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                gc = grangercausalitytests(data_s2c, maxlag=MAX_LAG, verbose=False)
            any_sig_s2c = False
            for lag_i in range(1, MAX_LAG + 1):
                f_stat = gc[lag_i][0]["ssr_ftest"][0]
                p_val = gc[lag_i][0]["ssr_ftest"][1]
                sig = p_val < 0.05
                if sig:
                    any_sig_s2c = True
                sig_mark = "**Yes**" if sig else "No"
                log(f"  | {lag_i} | {f_stat:.4f} | {p_val:.4f} | {sig_mark} |")
        except Exception as e:
            log(f"  [ERROR] {e}")
            any_sig_s2c = False

        # CSI -> Search
        data_c2s = np.column_stack([residual_d1, csi_d1])
        log("")
        log(f"  CSI(d1) -> Search(d1):")
        log(f"  | Lag | F-stat | p-value | Sig |")
        log(f"  |---|---|---|---|")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                gc = grangercausalitytests(data_c2s, maxlag=MAX_LAG, verbose=False)
            any_sig_c2s = False
            for lag_i in range(1, MAX_LAG + 1):
                f_stat = gc[lag_i][0]["ssr_ftest"][0]
                p_val = gc[lag_i][0]["ssr_ftest"][1]
                sig = p_val < 0.05
                if sig:
                    any_sig_c2s = True
                sig_mark = "**Yes**" if sig else "No"
                log(f"  | {lag_i} | {f_stat:.4f} | {p_val:.4f} | {sig_mark} |")
        except Exception as e:
            log(f"  [ERROR] {e}")
            any_sig_c2s = False

        # Verdict
        log("")
        if brand == "adidas" and region == "global":
            if any_sig_s2c:
                log(f"  Verdict: Search->CSI significance SURVIVES after differencing")
                log(f"  -> adidas/global 'Search leads CSI' result is robust")
            else:
                log(f"  Verdict: Search->CSI significance DOES NOT SURVIVE after differencing")
                log(f"  -> adidas/global result reclassified as SPURIOUS")
                log(f"  -> original lag 4 p=0.0443 was likely driven by non-stationary residual")
        else:
            # nike/global was Independent, just confirming
            if any_sig_s2c or any_sig_c2s:
                log(f"  Verdict: significance emerges after differencing")
            else:
                log(f"  Verdict: remains Independent after differencing (consistent)")


# REPORT

def generate_report():
    """Write robustness check report."""
    report_path = "docs/stage4_robustness_check.md"
    header = [
        "# Stage 4 Track A — Robustness Check",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "**Purpose:** Verify Granger results for non-stationary residual series",
        "**Method:** 1st differencing of MSTL residual, re-run bidirectional Granger",
        "",
        "---",
    ]
    with open(report_path, "w", encoding="utf-8") as f:
        for line in header + REPORT_LINES:
            f.write(line + "\n")
    print(f"\nReport saved: {report_path}")


# MAIN

def main():
    log(f"Stage 4 Track A: Robustness Check")
    log(f"Started: {datetime.now()}")

    aligned = load_aligned_data()
    robustness_check(aligned)
    generate_report()


if __name__ == "__main__":
    main()
