"""
Stage 7 supplementary check -- Monthly Granger NB Korea -> Global search.

Per advisor decision 2:
  Stage 4 monthly Granger covered Search<->CSI in 8 brand x region pairs but did
  not test Korea_NB_search -> Global_NB_search. This script fills that gap.

  Variables : NB search_index aggregated to monthly mean
  Direction : bidirectional Granger maxlag=4
  Stationarity : ADF level + diff1 (Stage 4 protocol)
  CSI control : intentionally omitted (5-min sanity check; CSI control reserved
                for Track A1' trend mediation)

Outputs:
  - data/bridge/monthly_korea_global_granger.json
"""

import os
import sys
import json
import warnings
from datetime import datetime

import pandas as pd
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

warnings.filterwarnings("ignore", category=Warning, module="statsmodels")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, message=".*SQLAlchemy.*")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.bridge_stationarity_check import extract_data

DATA_DIR = "data/bridge"
JSON_PATH = os.path.join(DATA_DIR, "monthly_korea_global_granger.json")
SIGNIFICANCE = 0.05
MAXLAG = 4

os.makedirs(DATA_DIR, exist_ok=True)


def aggregate_monthly(weekly_df, cols):
    """Weekly -> monthly mean, indexed by month-start."""
    monthly = weekly_df[cols].copy()
    monthly.index = monthly.index.to_period("M").to_timestamp()
    return monthly.groupby(level=0).mean()


def adf_p(series):
    s = series.dropna().astype(float)
    return float(adfuller(s, autolag="AIC")[1])


def transform_for_stationarity(series, label, log_lines):
    """Stage 4 protocol: ADF level, diff1 if non-stationary."""
    p_level = adf_p(series)
    if p_level < SIGNIFICANCE:
        log_lines.append(f"  {label:<14}  ADF level p={p_level:.4f}  -> level (stationary)")
        return series.dropna(), "level", p_level, None
    p_diff = adf_p(series.diff())
    log_lines.append(
        f"  {label:<14}  ADF level p={p_level:.4f}  diff1 p={p_diff:.4f}  -> diff1"
    )
    return series.diff().dropna(), "diff1", p_level, p_diff


def granger_bidirectional(s_caused, s_causing, label_dir, maxlag, log_lines):
    """statsmodels grangercausalitytests with H0: causing does not Granger-cause caused.

    grangercausalitytests expects 2-col [caused, causing]. Returns p-values per lag
    using the F-test (ssr_ftest) consistent with Stage 4.
    """
    df = pd.concat([s_caused.rename("caused"), s_causing.rename("causing")], axis=1).dropna()
    res = grangercausalitytests(df[["caused", "causing"]], maxlag=maxlag, verbose=False)
    per_lag = {}
    for lag in range(1, maxlag + 1):
        f_stat, p_value, df_num, df_den = res[lag][0]["ssr_ftest"]
        per_lag[lag] = {
            "f_stat": float(f_stat),
            "p_value": float(p_value),
            "significant": bool(p_value < SIGNIFICANCE),
        }
    min_p_lag = min(per_lag, key=lambda k: per_lag[k]["p_value"])
    min_p = per_lag[min_p_lag]["p_value"]
    log_lines.append(
        f"  {label_dir:<22}  min p={min_p:.4f} @ lag {min_p_lag}  "
        f"({'reject' if min_p < SIGNIFICANCE else 'fail_to_reject'})"
    )
    return {
        "n_obs": int(len(df)),
        "per_lag": per_lag,
        "min_p_lag": int(min_p_lag),
        "min_p_value": float(min_p),
        "any_significant": bool(any(v["significant"] for v in per_lag.values())),
    }


def main():
    print("# Stage 7 supplementary -- Monthly NB Korea <-> Global search Granger")
    print(f"# Date: {datetime.now():%Y-%m-%d %H:%M}")

    df_weekly = extract_data()

    print("\n## 1. Weekly -> monthly aggregation")
    monthly = aggregate_monthly(df_weekly, ["korea_search", "global_search"])
    print(
        f"  monthly: {monthly.index.min().date()} ~ {monthly.index.max().date()}  "
        f"({len(monthly)} months)"
    )

    print("\n## 2. ADF + transformation decision (Stage 4 protocol)")
    log_lines = []
    korea_t, korea_form, korea_p_level, korea_p_diff = transform_for_stationarity(
        monthly["korea_search"], "korea_search", log_lines
    )
    global_t, global_form, global_p_level, global_p_diff = transform_for_stationarity(
        monthly["global_search"], "global_search", log_lines
    )
    for line in log_lines:
        print(line)

    print("\n## 3. Bidirectional Granger (maxlag=4)")
    log_lines = []
    k2g = granger_bidirectional(global_t, korea_t, "korea_to_global", MAXLAG, log_lines)
    g2k = granger_bidirectional(korea_t, global_t, "global_to_korea", MAXLAG, log_lines)
    for line in log_lines:
        print(line)

    print("\n## 4. Verdict")
    if not k2g["any_significant"] and not g2k["any_significant"]:
        verdict = "monthly_null_both_directions"
        print(
            "  Monthly null both directions -> frequency-robust short/mid-term absence; "
            "trend channel hypothesis strengthened"
        )
    elif k2g["any_significant"] and not g2k["any_significant"]:
        verdict = "monthly_korea_to_global_only"
        print(
            "  Monthly korea_to_global only -> information smoothing effect; "
            "section 12.1 frequency mismatch has empirical support"
        )
    elif not k2g["any_significant"] and g2k["any_significant"]:
        verdict = "monthly_global_to_korea_only"
        print(
            "  Monthly global_to_korea only -> contradicts Stage 4 lead direction; "
            "advisor escalation"
        )
    else:
        verdict = "monthly_bidirectional_significant"
        print(
            "  Monthly bidirectional significance -> feedback emerges at monthly "
            "frequency; advisor escalation"
        )

    output = {
        "date": datetime.now().isoformat(),
        "stage": "7_supplementary_monthly_granger",
        "spec": {
            "input": "NB Korea/Global search_index, monthly mean",
            "directions": "bidirectional",
            "maxlag": MAXLAG,
            "csi_control": False,
            "stationarity_protocol": "Stage 4 (ADF level, diff1 if non-stationary)",
        },
        "n_months": int(len(monthly)),
        "stationarity": {
            "korea_search": {
                "transform": korea_form,
                "adf_level_p": korea_p_level,
                "adf_diff1_p": korea_p_diff,
            },
            "global_search": {
                "transform": global_form,
                "adf_level_p": global_p_level,
                "adf_diff1_p": global_p_diff,
            },
        },
        "granger": {
            "korea_to_global": k2g,
            "global_to_korea": g2k,
        },
        "verdict": verdict,
    }

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nJSON saved: {JSON_PATH}")


if __name__ == "__main__":
    main()