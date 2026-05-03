"""
Stage 7 supplementary -- Lagged cointegration test (Engle-Granger, lag grid 9/10/11)

Per Stage 7 Decision 4 (advisor):
  Direction primary  : Global_trend_t = a + b * Korea_trend_{t-lag} + e_t
                       (LHS = Global; Stage 6 Global ARIMA(0,1,0) -> endogenous side)
  Direction robustness: Korea_trend_t = a + b * Global_trend_{t+lag} + e_t
  Lag grid           : {9, 10, 11} weeks (Stage 4 DTW +10.4w; lag-sensitivity check)
  Cointegration test : statsmodels.tsa.stattools.coint, method='aeg', trend='c',
                       autolag='BIC' (small sample 174-lag obs)
                       => Engle-Granger critical values applied automatically

Outputs:
  - data/bridge/lagged_cointegration.json
  - data/bridge/lagged_cointegration.md
"""

import os
import sys
import json
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

warnings.filterwarnings("ignore", category=Warning, module="statsmodels")
warnings.filterwarnings("ignore", category=UserWarning, message=".*SQLAlchemy.*")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.bridge_chain_analysis import extract_data

DATA_DIR = "data/bridge"
JSON_PATH = os.path.join(DATA_DIR, "lagged_cointegration.json")
MD_PATH = os.path.join(DATA_DIR, "lagged_cointegration.md")
LAG_GRID = [9, 10, 11]
SIGNIFICANCE = 0.05

os.makedirs(DATA_DIR, exist_ok=True)

REPORT_LINES = []


def log(msg=""):
    print(msg)
    REPORT_LINES.append(msg)


def section(title):
    log("")
    log(f"## {title}")
    log("")


def run_engle_granger(lhs_series, rhs_series, label):
    """statsmodels coint() with method='aeg', trend='c', autolag='BIC'.

    Returns dict with t-statistic, p-value (EG critical value mapping),
    1/5/10% EG critical values, and verdict.
    """
    df = pd.concat([lhs_series.rename("lhs"), rhs_series.rename("rhs")], axis=1).dropna()
    n = len(df)
    coint_t, p_value, crit_values = coint(
        df["lhs"], df["rhs"],
        trend="c",
        method="aeg",
        autolag="BIC",
    )
    cointegrated = bool(p_value < SIGNIFICANCE)
    return {
        "label": label,
        "n_obs": int(n),
        "coint_t": float(coint_t),
        "p_value": float(p_value),
        "crit_1pct": float(crit_values[0]),
        "crit_5pct": float(crit_values[1]),
        "crit_10pct": float(crit_values[2]),
        "cointegrated": cointegrated,
        "verdict": "cointegrated" if cointegrated else "no_cointegration",
    }


def classify_robustness(results_by_lag):
    """Classify lag-sensitivity across the 9/10/11 grid for one direction.

    All cointegrated  -> robust_cointegrated
    All not          -> robust_no_cointegration
    Mixed            -> lag_sensitive (advisor caveat in section 12.6)
    """
    verdicts = {lag: r["cointegrated"] for lag, r in results_by_lag.items()}
    n_cointegrated = sum(verdicts.values())
    n_total = len(verdicts)
    if n_cointegrated == n_total:
        return "robust_cointegrated"
    if n_cointegrated == 0:
        return "robust_no_cointegration"
    return "lag_sensitive"


def main():
    log("# Stage 7 supplementary -- Lagged cointegration (Engle-Granger AEG)")
    log("")
    log(f"**Date:** {datetime.now():%Y-%m-%d %H:%M}")
    log(f"**Lag grid:** {LAG_GRID} weeks")
    log(f"**Method:** aeg, trend='c', autolag='BIC'")
    log(f"**LHS primary:** Global_trend_t (Stage 6 ARIMA(0,1,0) -> endogenous)")
    log(f"**Significance:** alpha = {SIGNIFICANCE}")

    section("1. Data Preparation")
    weekly_df = extract_data()
    korea_trend = weekly_df["korea_trend"]
    global_trend = weekly_df["global_trend"]
    log(f"  korea_trend:  {korea_trend.size}w  range "
        f"[{korea_trend.min():.2f}, {korea_trend.max():.2f}]")
    log(f"  global_trend: {global_trend.size}w  range "
        f"[{global_trend.min():.2f}, {global_trend.max():.2f}]")

    section("2. Primary direction -- Global_t ~ Korea_{t-lag}")
    log("  (LHS=Global, RHS=lagged Korea; model-consistent per Stage 6)")
    log("")
    primary = {}
    for lag in LAG_GRID:
        korea_lagged = korea_trend.shift(lag)
        r = run_engle_granger(
            global_trend, korea_lagged,
            label=f"primary_lag_{lag}w",
        )
        primary[lag] = r
        log(
            f"  lag={lag:>2}w  n={r['n_obs']:>3}  t={r['coint_t']:>7.3f}  "
            f"p={r['p_value']:.4f}  crit5%={r['crit_5pct']:>6.3f}  "
            f"-> {r['verdict']}"
        )
    primary_classification = classify_robustness(primary)
    log(f"  Primary lag-grid classification: {primary_classification}")

    section("3. Robustness direction -- Korea_t ~ Global_{t+lag}")
    log("  (Symmetric check; lag inversion realized via leading Global)")
    log("")
    reverse = {}
    for lag in LAG_GRID:
        global_leading = global_trend.shift(-lag)
        r = run_engle_granger(
            korea_trend, global_leading,
            label=f"reverse_lag_{lag}w",
        )
        reverse[lag] = r
        log(
            f"  lag={lag:>2}w  n={r['n_obs']:>3}  t={r['coint_t']:>7.3f}  "
            f"p={r['p_value']:.4f}  crit5%={r['crit_5pct']:>6.3f}  "
            f"-> {r['verdict']}"
        )
    reverse_classification = classify_robustness(reverse)
    log(f"  Reverse lag-grid classification: {reverse_classification}")

    section("4. Cross-direction consistency")
    if primary_classification == reverse_classification:
        cross_dir = "consistent"
        if primary_classification == "robust_cointegrated":
            interp = ("Lagged level equilibrium present in both directions -- "
                      "common-driver long-run co-movement quantified")
        elif primary_classification == "robust_no_cointegration":
            interp = ("No lagged level equilibrium in either direction -- "
                      "shape similarity (DTW) but level independence; "
                      "purer differential-reactivity evidence")
        else:
            interp = ("Both directions lag-sensitive -- common-driver hypothesis "
                      "weakly supported, mechanism nuance for section 12.6")
    else:
        cross_dir = "asymmetric"
        interp = (f"Direction asymmetry: primary={primary_classification}, "
                  f"reverse={reverse_classification} -- caveat for section 12.6 "
                  f"(Engle-Granger LHS choice finite-sample sensitivity)")
    log(f"  Cross-direction: {cross_dir}")
    log(f"  Interpretation:  {interp}")

    section("5. Section 12.6 narrative slot")
    if primary_classification == "robust_cointegrated":
        narrative_slot = (
            "Lagged cointegration confirmed at the +10w window (lag-grid robust). "
            "Korea and Global trends share a long-run level equilibrium under a "
            "10-week shift, while same-period Engle-Granger (Stage 4) was rejected "
            "(p=0.9433). Combined with Track A1' mediation null, this characterizes "
            "the relationship as level co-movement without causal mediation -- "
            "consistent with common-driver early-reactor model."
        )
    elif primary_classification == "robust_no_cointegration":
        narrative_slot = (
            "Lagged cointegration rejected across the 9/10/11w grid. Korea trend "
            "and Global trend share shape similarity (Stage 4 DTW +10.4w) but no "
            "level equilibrium at any tested lag. This supports the strongest form "
            "of the differential-reactivity hypothesis: Korea and Global respond "
            "to overlapping drivers at different speeds without converging to a "
            "shared level."
        )
    else:
        narrative_slot = (
            "Lagged cointegration is lag-sensitive within the 9/10/11w grid. "
            "Equilibrium presence depends on the chosen lag, weakening claims of "
            "robust long-run co-movement. The 10w lead remains shape evidence "
            "(DTW + CC) but level equilibrium claims should be qualified."
        )
    log(narrative_slot)

    output = {
        "date": datetime.now().isoformat(),
        "stage": "7_supplementary_lagged_cointegration",
        "spec": {
            "method": "aeg",
            "trend": "c",
            "autolag": "BIC",
            "lag_grid": LAG_GRID,
            "primary_direction": "Global_t ~ Korea_{t-lag}",
            "reverse_direction": "Korea_t ~ Global_{t+lag}",
        },
        "primary": {str(k): v for k, v in primary.items()},
        "reverse": {str(k): v for k, v in reverse.items()},
        "primary_classification": primary_classification,
        "reverse_classification": reverse_classification,
        "cross_direction": cross_dir,
        "interpretation": interp,
        "section_12_6_narrative_slot": narrative_slot,
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    log("")
    log(f"JSON saved:     {JSON_PATH}")

    with open(MD_PATH, "w", encoding="utf-8") as f:
        for line in REPORT_LINES:
            f.write(line + "\n")
    log(f"Markdown saved: {MD_PATH}")


if __name__ == "__main__":
    main()