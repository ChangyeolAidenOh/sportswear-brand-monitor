"""
Stage 7 Step 0 — Weekly Stationarity Re-Test for Korea-Global Bridge

Re-tests stationarity at weekly frequency to commit transformation decisions
before Track A1 (VARX) and A1' (Mediation).

Per Stage 7 Decision 2:
  - ADF + KPSS joint test (level + diff1) on all Bridge-relevant series
  - Engle-Granger cointegration on Korea<->Global endogenous pair + CSI pairs
  - Forward-filled CSI distortion sanity check
  - Commit transformation decision per variable

Outputs:
  - data/bridge/stationarity_report.json
  - data/bridge/stationarity_report.md
"""

import os
import sys
import json
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss, coint

# KPSS clips p-values to [0.01, 0.10] table bounds; suppress interpolation warning
warnings.filterwarnings("ignore", category=Warning, module="statsmodels")

# Local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import get_conn

# Constants
DATA_DIR = "data/bridge"
JSON_PATH = os.path.join(DATA_DIR, "stationarity_report.json")
MD_PATH = os.path.join(DATA_DIR, "stationarity_report.md")
CSI_STAT_CODE = "511Y002"
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


# =========================================================================
# Data extraction
# =========================================================================

def extract_data():
    """Return weekly-aligned DataFrame with 5 columns on shared week_start index."""
    log("Loading data from PostgreSQL...")
    with get_conn() as conn:
        df_search = pd.read_sql(
            """
            SELECT week_start, region, search_index::float AS search_index
            FROM mart.brand_kpi_weekly
            WHERE brand = 'new_balance'
              AND region IN ('korea', 'global')
            ORDER BY region, week_start
            """,
            conn,
        )

        # mart.seasonal_components format: trend/seasonal/residual-columns##
        df_trend = pd.read_sql(
            """
            SELECT week_start, region, trend::float AS trend
            FROM mart.seasonal_components
            WHERE brand = 'new_balance'
              AND region IN ('korea', 'global')
              AND decomposition_method = 'MSTL'
              AND product_line IS NULL
            ORDER BY region, week_start
            """,
            conn,
        )

        df_csi_m = pd.read_sql(
            """
            SELECT period, value::float AS csi
            FROM raw.ecos_raw
            WHERE stat_code = %s
            ORDER BY period
            """,
            conn,
            params=(CSI_STAT_CODE,),
        )

    df_search["week_start"] = pd.to_datetime(df_search["week_start"])
    df_trend["week_start"] = pd.to_datetime(df_trend["week_start"])

    korea_search = df_search.query("region == 'korea'").set_index("week_start")["search_index"]
    global_search = df_search.query("region == 'global'").set_index("week_start")["search_index"]
    korea_trend = df_trend.query("region == 'korea'").set_index("week_start")["trend"]
    global_trend = df_trend.query("region == 'global'").set_index("week_start")["trend"]

    assert len(korea_trend) == korea_trend.index.nunique(), \
        "Duplicate week_start in korea_trend -- check filter"
    assert len(global_trend) == global_trend.index.nunique(), \
        "Duplicate week_start in global_trend -- check filter"

    csi_weekly = forward_fill_csi(df_csi_m, korea_search.index)

    df = pd.concat(
        {
            "korea_search": korea_search,
            "global_search": global_search,
            "korea_trend": korea_trend,
            "global_trend": global_trend,
            "csi": csi_weekly,
        },
        axis=1,
    ).dropna()

    log(f"  search: korea {korea_search.size}w  global {global_search.size}w")
    log(f"  trend:  korea {korea_trend.size}w  global {global_trend.size}w")
    log(f"  csi:    {df_csi_m.shape[0]} months -> {csi_weekly.dropna().size} weeks (forward-fill)")
    log(f"  common: {df.index.min().date()} ~ {df.index.max().date()}  ({len(df)} weeks)")
    return df


def forward_fill_csi(df_csi_monthly, week_grid):
    """Map monthly CSI ('YYYY-MM') to weekly grid via week_start's calendar month."""
    csi = df_csi_monthly.copy()
    # ECOS schema: period VARCHAR(10) 'YYYY-MM'=====> Format
    csi["month"] = pd.to_datetime(csi["period"].astype(str), format="%Y-%m")
    csi = csi[["month", "csi"]].sort_values("month")

    weekly = pd.DataFrame({"week_start": pd.to_datetime(week_grid)})
    weekly["month"] = weekly["week_start"].dt.to_period("M").dt.to_timestamp()

    merged = pd.merge(weekly, csi, on="month", how="left").sort_values("week_start")
    merged["csi"] = merged["csi"].ffill().bfill()
    return merged.set_index("week_start")["csi"]


# =========================================================================
# Statistical tests
# =========================================================================

def adf_kpss(series, label):
    """ADF + KPSS joint test. Returns dict with both p-values and combined verdict."""
    s = pd.Series(series).dropna()
    if len(s) < 30:
        return {"label": label, "n": int(len(s)), "verdict": "insufficient_data"}

    adf_stat, adf_p, *_ = adfuller(s, autolag="AIC")
    kpss_stat, kpss_p, *_ = kpss(s, regression="c", nlags="auto")

    # ADF H0: unit root        -> reject (p < alpha) means stationary
    # KPSS H0: stationarity    -> reject (p < alpha) means non-stationary
    adf_reject = adf_p < SIGNIFICANCE
    kpss_reject = kpss_p < SIGNIFICANCE

    if adf_reject and not kpss_reject:
        verdict = "stationary"
    elif (not adf_reject) and kpss_reject:
        verdict = "unit_root"
    elif adf_reject and kpss_reject:
        verdict = "trend_stationary"
    else:
        verdict = "ambiguous"

    return {
        "label": label,
        "n": int(len(s)),
        "adf_stat": float(adf_stat),
        "adf_p": float(adf_p),
        "kpss_stat": float(kpss_stat),
        "kpss_p": float(kpss_p),
        "verdict": verdict,
    }


def coint_test(y0, y1, label):
    """Engle-Granger cointegration test. H0: no cointegration."""
    df = pd.concat([y0.rename("a"), y1.rename("b")], axis=1).dropna()
    if len(df) < 30:
        return {"label": label, "n": int(len(df)), "verdict": "insufficient_data"}

    coint_stat, coint_p, _ = coint(df["a"], df["b"], autolag="AIC")
    return {
        "label": label,
        "n": int(len(df)),
        "coint_stat": float(coint_stat),
        "coint_p": float(coint_p),
        "cointegrated": bool(coint_p < SIGNIFICANCE),
    }


# =========================================================================
# Decision logic + escalation
# =========================================================================

def make_decisions(univariate):
    """Map test results to per-variable transformation choice."""
    uv = {r["label"]: r for r in univariate}
    decisions = {}
    for var in ["korea_search", "global_search", "korea_trend", "global_trend", "csi"]:
        level = uv[f"{var}_level"]
        diff1 = uv[f"{var}_diff1"]

        if level["verdict"] == "stationary":
            decisions[var] = {
                "transform": "level",
                "rationale": (
                    f"ADF+KPSS agree stationary at level "
                    f"(ADF p={level['adf_p']:.4f}, KPSS p={level['kpss_p']:.4f})"
                ),
            }
        elif diff1["verdict"] == "stationary":
            decisions[var] = {
                "transform": "diff1",
                "rationale": (
                    f"Level non-stationary (ADF p={level['adf_p']:.4f}, "
                    f"KPSS p={level['kpss_p']:.4f}); diff1 stationary"
                ),
            }
        else:
            decisions[var] = {
                "transform": "review",
                "rationale": (
                    f"Neither level nor diff1 cleanly stationary "
                    f"(level: {level['verdict']}, diff1: {diff1['verdict']})"
                ),
            }
    return decisions


def check_escalation_triggers(univariate, coint_results, decisions):
    """Identify advisor-escalation conditions per Stage 7 concerns list."""
    triggers = []
    uv = {r["label"]: r for r in univariate}
    coint_dict = {r["label"]: r for r in coint_results}

    # Trigger 1: VARX endogenous pair cointegrated AND non-stationary at level -> VECM review
    for label in ["korea_search_x_global_search", "korea_trend_x_global_trend"]:
        c = coint_dict.get(label, {})
        if not c.get("cointegrated"):
            continue
        v0, v1 = label.split("_x_")
        ns0 = uv[f"{v0}_level"]["verdict"] != "stationary"
        ns1 = uv[f"{v1}_level"]["verdict"] != "stationary"
        if ns0 and ns1:
            triggers.append(
                f"VECM_REVIEW: {label} cointegrated (p={c['coint_p']:.4f}) "
                f"with both series non-stationary at level"
            )

    # Trigger 2: forward-filled CSI plausibility (step function distortion)
    csi_level = uv.get("csi_level", {})
    if csi_level.get("kpss_p", 0) >= 0.099 and csi_level.get("adf_p", 1) > 0.5:
        triggers.append(
            f"CSI_FFILL_DISTORTION: ADF p={csi_level['adf_p']:.4f} "
            f"KPSS p={csi_level['kpss_p']:.4f} "
            f"-- monthly step function may distort weekly tests"
        )

    # Trigger 3: any 'review' decision
    review_vars = [v for v, d in decisions.items() if d["transform"] == "review"]
    if review_vars:
        triggers.append(
            f"AMBIGUOUS_TRANSFORM: {review_vars} "
            f"-- neither level nor diff1 cleanly stationary"
        )

    return triggers


# =========================================================================
# Main
# =========================================================================

def main():
    log(f"# Stage 7 Step 0 -- Weekly Stationarity Re-Test")
    log("")
    log(f"**Date:** {datetime.now():%Y-%m-%d %H:%M}")
    log(f"**Significance:** alpha = {SIGNIFICANCE}")
    log("")

    section("1. Data Extraction")
    df = extract_data()

    section("2. Univariate Stationarity Tests (ADF + KPSS)")
    univariate = []
    for var in ["korea_search", "global_search", "korea_trend", "global_trend", "csi"]:
        for transform_label, s_t in [("level", df[var]), ("diff1", df[var].diff())]:
            r = adf_kpss(s_t, f"{var}_{transform_label}")
            univariate.append(r)
            log(
                f"  {var:<14} {transform_label:<5}  "
                f"ADF p={r['adf_p']:.4f}  KPSS p={r['kpss_p']:.4f}  -> {r['verdict']}"
            )
        log("")

    section("3. Engle-Granger Cointegration Tests")
    pairs = [
        ("korea_search", "global_search"),
        ("korea_search", "csi"),
        ("global_search", "csi"),
        ("korea_trend", "global_trend"),
        ("korea_trend", "csi"),
        ("global_trend", "csi"),
    ]
    coint_results = []
    for a, b in pairs:
        label = f"{a}_x_{b}"
        r = coint_test(df[a], df[b], label)
        coint_results.append(r)
        flag = "COINTEGRATED" if r["cointegrated"] else "no"
        log(f"  {label:<40}  coint p={r['coint_p']:.4f}  -> {flag}")
    log("")

    section("4. Transformation Decisions (committed)")
    decisions = make_decisions(univariate)
    for var, d in decisions.items():
        log(f"  {var:<14}  {d['transform']:<6}  ({d['rationale']})")

    section("5. Advisor Escalation Triggers")
    triggers = check_escalation_triggers(univariate, coint_results, decisions)
    if triggers:
        log("**ESCALATION REQUIRED -- return to advisor before Track A1:**")
        for t in triggers:
            log(f"  - {t}")
    else:
        log("None detected. Proceed to Track A1 (VARX).")

    report = {
        "date": datetime.now().isoformat(),
        "stage": "7_step0_stationarity",
        "n_observations": int(len(df)),
        "significance_level": SIGNIFICANCE,
        "univariate": univariate,
        "cointegration": coint_results,
        "transformation_decisions": decisions,
        "escalation_triggers": triggers,
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    log("")
    log(f"JSON saved:     {JSON_PATH}")

    with open(MD_PATH, "w", encoding="utf-8") as f:
        for line in REPORT_LINES:
            f.write(line + "\n")
    log(f"Markdown saved: {MD_PATH}")


if __name__ == "__main__":
    main()