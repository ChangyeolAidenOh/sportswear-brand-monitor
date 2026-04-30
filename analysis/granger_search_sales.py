"""
Stage 4 Track A: Search <-> CSI Leading Indicator Validation
Tests whether brand-level search demand (micro) serves as a leading indicator
for consumer sentiment (macro CSI), or vice versa.

Key design decisions (Advisor 2026-04-30):
  - Input: MSTL residual (search side), 1st diff or ADF-based (CSI side)
  - Bidirectional: Search->CSI AND CSI->Search
  - Sub-analysis: shopping search channel as purchase-intent proxy
  - maxlag=4 months, AIC auto-selection via VAR.select_order
  - Neural Granger excluded (40 obs, overfitting risk documented)

Steps:
  A1: Data extraction (brand_kpi_weekly, seasonal_components, ecos_raw)
  A2: MSTL residual -> monthly aggregation + CSI alignment
  A3: Stationarity tests (ADF + KPSS) on residual & CSI
  A4: Bidirectional Granger causality (4 brands x 2 regions x 2 directions)
  A5: VAR + IRF visualization
  A6: Shopping search sub-analysis

Usage:
  python analysis/granger_search_sales.py              # full pipeline
  python analysis/granger_search_sales.py --step a3    # stationarity only
  python analysis/granger_search_sales.py --step a4    # Granger tests
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

# stdlib
import os
import sys

import argparse
import warnings
from datetime import datetime

# third-party
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss, grangercausalitytests, coint
from statsmodels.tsa.api import VAR

# local
from database.connection import get_conn

# ================================================================
# CONSTANTS
# ================================================================

BRANDS = ["nike", "adidas", "puma", "new_balance"]
REGIONS = ["korea", "global"]
MAX_LAG = 4  # advisor decision: 4 months

FIG_DIR = "figures/var"
DOCS_DIR = "docs"
REPORT_PATH = os.path.join(DOCS_DIR, "stage4_stationarity_report.md")

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

REPORT_LINES = []


def log(msg=""):
    print(msg)
    REPORT_LINES.append(msg)


def section(title):
    log("")
    log(f"## {title}")
    log("")


# ================================================================
# STEP A1: Data Extraction
# ================================================================

def extract_search_weekly():
    """Extract brand-level search_index from mart.brand_kpi_weekly."""
    query = """
        SELECT brand, region, week_start, search_index
        FROM mart.brand_kpi_weekly
        WHERE search_index IS NOT NULL
        ORDER BY brand, region, week_start
    """
    with get_conn() as conn:
        df = pd.read_sql(query, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    log(f"  search_weekly: {len(df)} rows, {df['week_start'].min()} ~ {df['week_start'].max()}")
    return df


def extract_seasonal_residual():
    """Extract MSTL residual from mart.seasonal_components (brand-level only)."""
    query = """
        SELECT brand, region, week_start, residual
        FROM mart.seasonal_components
        WHERE product_line IS NULL
        ORDER BY brand, region, week_start
    """
    with get_conn() as conn:
        df = pd.read_sql(query, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    log(f"  seasonal_components (residual): {len(df)} rows")
    return df


def extract_shopping_search():
    """Extract shopping-type search for purchase-intent sub-analysis."""
    query = """
        SELECT brand, region, week_start, search_index
        FROM mart.brand_kpi_weekly
        WHERE search_index IS NOT NULL
        ORDER BY brand, region, week_start
    """
    # Shopping search is in staging.search_weekly with search_type='shopping'
    query_shopping = """
            SELECT brand, region, week_start, SUM(interest) AS shopping_interest
            FROM staging.search_weekly
            WHERE search_type = 'shopping'
              AND product_line IS NULL
            GROUP BY brand, region, week_start
            ORDER BY brand, region, week_start
        """
    with get_conn() as conn:
        df = pd.read_sql(query_shopping, conn)
    df["week_start"] = pd.to_datetime(df["week_start"])
    log(f"  shopping_search: {len(df)} rows")
    return df


def extract_csi():
    """Extract Consumer Sentiment Index from raw.ecos_raw (monthly)."""
    query = """
        SELECT period, value AS csi
        FROM raw.ecos_raw
        WHERE stat_code = '511Y002'
          AND item_code = 'FME'
        ORDER BY period
    """
    with get_conn() as conn:
        df = pd.read_sql(query, conn)
    df["year_month"] = pd.to_datetime(df["period"] + "-01")
    df = df.drop(columns=["period"])
    df["csi"] = pd.to_numeric(df["csi"], errors="coerce")
    log(f"  csi: {len(df)} months, {df['year_month'].min()} ~ {df['year_month'].max()}")
    return df


def step_a1():
    """Execute Step A1: extract all data sources."""
    section("Step A1: Data Extraction")

    search_df = extract_search_weekly()
    residual_df = extract_seasonal_residual()
    shopping_df = extract_shopping_search()
    csi_df = extract_csi()

    return {
        "search": search_df,
        "residual": residual_df,
        "shopping": shopping_df,
        "csi": csi_df,
    }


# ================================================================
# STEP A2: MSTL Residual -> Monthly + CSI Alignment
# ================================================================

def aggregate_residual_to_monthly(residual_df):
    """Aggregate weekly MSTL residual to monthly mean per brand x region.
    week_start determines month assignment (no fractional allocation)."""
    df = residual_df.copy()
    df["year_month"] = df["week_start"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        df.groupby(["brand", "region", "year_month"])
        .agg(
            residual_mean=("residual", "mean"),
            residual_std=("residual", "std"),
            n_weeks=("residual", "count"),
        )
        .reset_index()
    )
    return monthly


def aggregate_shopping_to_monthly(shopping_df):
    """Aggregate weekly shopping search to monthly mean."""
    df = shopping_df.copy()
    df["year_month"] = df["week_start"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        df.groupby(["brand", "region", "year_month"])
        .agg(shopping_mean=("shopping_interest", "mean"))
        .reset_index()
    )
    return monthly


def step_a2(data):
    """Execute Step A2: monthly aggregation + CSI alignment."""
    section("Step A2: MSTL Residual -> Monthly + CSI Alignment")

    residual_monthly = aggregate_residual_to_monthly(data["residual"])
    csi_df = data["csi"]

    # Align residual with CSI
    aligned = pd.merge(residual_monthly, csi_df, on="year_month", how="inner")

    t_min = aligned["year_month"].min()
    t_max = aligned["year_month"].max()
    n_months = aligned.groupby(["brand", "region"])["year_month"].count().min()
    log(f"  common period: {t_min.strftime('%Y-%m')} ~ {t_max.strftime('%Y-%m')}")
    log(f"  observations per series: {n_months} months")

    log("")
    log("| Brand | Region | N_months | Residual Mean | Residual Std | CSI Mean |")
    log("|---|---|---|---|---|---|")
    for (brand, region), grp in aligned.groupby(["brand", "region"]):
        log(
            f"| {brand} | {region} | {len(grp)} "
            f"| {grp['residual_mean'].mean():.4f} "
            f"| {grp['residual_mean'].std():.4f} "
            f"| {grp['csi'].mean():.1f} |"
        )

    data["aligned"] = aligned

    # Shopping sub-analysis alignment
    if not data["shopping"].empty:
        shopping_monthly = aggregate_shopping_to_monthly(data["shopping"])
        shopping_aligned = pd.merge(shopping_monthly, csi_df, on="year_month", how="inner")
        data["shopping_aligned"] = shopping_aligned
        log(f"  shopping aligned: {len(shopping_aligned)} rows")
    else:
        data["shopping_aligned"] = pd.DataFrame()
        log("  shopping search: no data available")

    return data


# ================================================================
# STEP A3: Stationarity Tests (ADF + KPSS)
# ================================================================

def run_adf(series, name):
    """Run Augmented Dickey-Fuller test."""
    clean = series.dropna()
    if len(clean) < 10:
        return {"series": name, "test": "ADF", "statistic": np.nan,
                "p_value": np.nan, "lags_used": 0, "stationary": False}
    result = adfuller(clean, autolag="AIC")
    return {
        "series": name,
        "test": "ADF",
        "statistic": round(result[0], 4),
        "p_value": round(result[1], 4),
        "lags_used": result[2],
        "stationary": result[1] < 0.05,
    }


def run_kpss(series, name, regression="c"):
    """Run KPSS test (H0 = stationary)."""
    clean = series.dropna()
    if len(clean) < 10:
        return {"series": name, "test": "KPSS", "statistic": np.nan,
                "p_value": np.nan, "lags_used": 0, "stationary": False}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = kpss(clean, regression=regression, nlags="auto")
    return {
        "series": name,
        "test": "KPSS",
        "statistic": round(result[0], 4),
        "p_value": round(result[1], 4),
        "lags_used": result[2],
        "stationary": result[1] >= 0.05,
    }


def diagnose_stationarity(adf_result, kpss_result):
    """Combine ADF + KPSS into joint verdict."""
    adf_s = adf_result["stationary"]
    kpss_s = kpss_result["stationary"]
    if adf_s and kpss_s:
        return "Stationary"
    elif not adf_s and not kpss_s:
        return "Non-stationary"
    elif adf_s and not kpss_s:
        return "Trend-stationary"
    else:
        return "Difference-stationary"


def step_a3(data):
    """Execute Step A3: stationarity on MSTL residual (monthly) and CSI."""
    section("Step A3: Stationarity Tests")

    aligned = data["aligned"]
    results = []

    # CSI (single series)
    csi_series = aligned.drop_duplicates("year_month").sort_values("year_month")["csi"]
    adf_r = run_adf(csi_series, "CSI_level")
    kpss_r = run_kpss(csi_series, "CSI_level")
    verdict = diagnose_stationarity(adf_r, kpss_r)
    results.append({**adf_r, "verdict": verdict})
    results.append({**kpss_r, "verdict": verdict})

    # CSI 1st difference
    csi_diff = csi_series.diff().dropna()
    adf_r = run_adf(csi_diff, "CSI_diff1")
    kpss_r = run_kpss(csi_diff, "CSI_diff1")
    verdict = diagnose_stationarity(adf_r, kpss_r)
    results.append({**adf_r, "verdict": verdict})
    results.append({**kpss_r, "verdict": verdict})

    # MSTL residual per brand x region
    for (brand, region), grp in aligned.groupby(["brand", "region"]):
        grp = grp.sort_values("year_month")
        name = f"{brand}_{region}_residual"

        adf_r = run_adf(grp["residual_mean"], name)
        kpss_r = run_kpss(grp["residual_mean"], name)
        verdict = diagnose_stationarity(adf_r, kpss_r)
        results.append({**adf_r, "verdict": verdict})
        results.append({**kpss_r, "verdict": verdict})

    results_df = pd.DataFrame(results)
    data["stationarity"] = results_df

    # Report table
    adf_only = results_df[results_df["test"] == "ADF"].copy()
    log("")
    log("| Series | ADF stat | ADF p | KPSS p | Verdict |")
    log("|---|---|---|---|---|")
    for _, row in adf_only.iterrows():
        kpss_match = results_df[
            (results_df["series"] == row["series"]) & (results_df["test"] == "KPSS")
        ]
        kpss_p = kpss_match.iloc[0]["p_value"] if len(kpss_match) > 0 else np.nan
        log(
            f"| {row['series']} | {row['statistic']:.4f} "
            f"| {row['p_value']:.4f} | {kpss_p:.4f} "
            f"| {row['verdict']} |"
        )

    # Determine CSI preprocessing
    csi_level_verdict = adf_only[adf_only["series"] == "CSI_level"]["verdict"].iloc[0]
    csi_diff_verdict = adf_only[adf_only["series"] == "CSI_diff1"]["verdict"].iloc[0]
    if csi_level_verdict == "Stationary":
        data["csi_transform"] = "level"
        log("  CSI: stationary at level, no differencing needed")
    else:
        data["csi_transform"] = "diff1"
        log(f"  CSI: {csi_level_verdict} at level -> 1st differencing applied")
        log(f"  CSI diff1 verdict: {csi_diff_verdict}")

    # Residual should already be stationary (MSTL strips trend+seasonal)
    non_stat = adf_only[
        (adf_only["series"].str.contains("residual")) & (~adf_only["stationary"])
    ]
    if len(non_stat) > 0:
        log(f"  [NOTE] {len(non_stat)} residual series not stationary at 5%")
        for _, row in non_stat.iterrows():
            log(f"    {row['series']}: p={row['p_value']:.4f}")

    return data


# ================================================================
# STEP A4: Bidirectional Granger Causality
# ================================================================

def prepare_granger_pair(search_series, csi_series, csi_transform):
    """Prepare paired stationary series for Granger test.
    Search: MSTL residual (expected stationary).
    CSI: level or 1st diff based on A3 result."""
    search_clean = search_series.values.copy()

    if csi_transform == "diff1":
        csi_clean = np.diff(csi_series.values)
        search_clean = search_clean[1:]  # align after differencing
    else:
        csi_clean = csi_series.values.copy()

    # Drop any NaN
    mask = ~(np.isnan(search_clean) | np.isnan(csi_clean))
    return search_clean[mask], csi_clean[mask]


def run_granger_bidirectional(search_vals, csi_vals, max_lag=MAX_LAG):
    """Run Granger in both directions, return results list."""
    results = []
    n_obs = len(search_vals)

    if n_obs < max_lag + 5:
        return results

    # Direction 1: Search -> CSI (does search Granger-cause CSI?)
    # statsmodels format: [y, x] tests if x causes y
    data_s2c = np.column_stack([csi_vals, search_vals])
    try:
        gc_s2c = grangercausalitytests(data_s2c, maxlag=max_lag, verbose=False)
        for lag_i in range(1, max_lag + 1):
            f_stat = gc_s2c[lag_i][0]["ssr_ftest"][0]
            p_val = gc_s2c[lag_i][0]["ssr_ftest"][1]
            results.append({
                "direction": "Search->CSI",
                "lag": lag_i,
                "f_statistic": round(f_stat, 4),
                "p_value": round(p_val, 6),
                "significant": p_val < 0.05,
                "n_obs": n_obs,
            })
    except Exception as e:
        results.append({
            "direction": "Search->CSI", "lag": 0,
            "f_statistic": np.nan, "p_value": np.nan,
            "significant": False, "n_obs": n_obs,
            "error": str(e),
        })

    # Direction 2: CSI -> Search (does CSI Granger-cause search?)
    data_c2s = np.column_stack([search_vals, csi_vals])
    try:
        gc_c2s = grangercausalitytests(data_c2s, maxlag=max_lag, verbose=False)
        for lag_i in range(1, max_lag + 1):
            f_stat = gc_c2s[lag_i][0]["ssr_ftest"][0]
            p_val = gc_c2s[lag_i][0]["ssr_ftest"][1]
            results.append({
                "direction": "CSI->Search",
                "lag": lag_i,
                "f_statistic": round(f_stat, 4),
                "p_value": round(p_val, 6),
                "significant": p_val < 0.05,
                "n_obs": n_obs,
            })
    except Exception as e:
        results.append({
            "direction": "CSI->Search", "lag": 0,
            "f_statistic": np.nan, "p_value": np.nan,
            "significant": False, "n_obs": n_obs,
            "error": str(e),
        })

    return results


def classify_granger_pattern(brand_results):
    """Classify brand's Granger result into one of 4 patterns."""
    s2c_sig = any(r["significant"] for r in brand_results if r["direction"] == "Search->CSI")
    c2s_sig = any(r["significant"] for r in brand_results if r["direction"] == "CSI->Search")
    if s2c_sig and c2s_sig:
        return "Feedback loop"
    elif s2c_sig:
        return "Search leads CSI"
    elif c2s_sig:
        return "CSI leads Search"
    else:
        return "Independent"


def step_a4(data):
    """Execute Step A4: bidirectional Granger for all brand x region pairs."""
    section("Step A4: Bidirectional Granger Causality")

    aligned = data["aligned"]
    csi_transform = data.get("csi_transform", "diff1")
    log(f"  CSI preprocessing: {csi_transform}")
    log(f"  Search preprocessing: MSTL residual (monthly mean)")
    log(f"  Max lag: {MAX_LAG} months")

    all_results = []

    for (brand, region), grp in aligned.groupby(["brand", "region"]):
        grp = grp.sort_values("year_month").reset_index(drop=True)
        search_vals, csi_vals = prepare_granger_pair(
            grp["residual_mean"], grp["csi"], csi_transform
        )

        results = run_granger_bidirectional(search_vals, csi_vals)
        for r in results:
            r["brand"] = brand
            r["region"] = region
        all_results.extend(results)

        # Classify pattern
        pattern = classify_granger_pattern(results)
        log(f"  {brand}/{region}: {pattern}")

    granger_df = pd.DataFrame(all_results)
    data["granger"] = granger_df

    # Detailed p-value matrix
    log("")
    log("### P-value Matrix (Search -> CSI)")
    log("")
    log("| Brand | Region | Lag 1 | Lag 2 | Lag 3 | Lag 4 |")
    log("|---|---|---|---|---|---|")
    for (brand, region), grp in granger_df[
        granger_df["direction"] == "Search->CSI"
    ].groupby(["brand", "region"]):
        row_str = f"| {brand} | {region}"
        for lag_i in range(1, MAX_LAG + 1):
            match = grp[grp["lag"] == lag_i]
            if len(match) > 0:
                p = match.iloc[0]["p_value"]
                sig = "**" if p < 0.05 else ""
                row_str += f" | {sig}{p:.4f}{sig}"
            else:
                row_str += " | -"
        row_str += " |"
        log(row_str)

    log("")
    log("### P-value Matrix (CSI -> Search)")
    log("")
    log("| Brand | Region | Lag 1 | Lag 2 | Lag 3 | Lag 4 |")
    log("|---|---|---|---|---|---|")
    for (brand, region), grp in granger_df[
        granger_df["direction"] == "CSI->Search"
    ].groupby(["brand", "region"]):
        row_str = f"| {brand} | {region}"
        for lag_i in range(1, MAX_LAG + 1):
            match = grp[grp["lag"] == lag_i]
            if len(match) > 0:
                p = match.iloc[0]["p_value"]
                sig = "**" if p < 0.05 else ""
                row_str += f" | {sig}{p:.4f}{sig}"
            else:
                row_str += " | -"
        row_str += " |"
        log(row_str)

    # Summary classification
    log("")
    log("### Causality Pattern Summary")
    log("")
    log("| Brand | Region | Pattern |")
    log("|---|---|---|")
    for (brand, region), grp in granger_df.groupby(["brand", "region"]):
        pattern = classify_granger_pattern(grp.to_dict("records"))
        log(f"| {brand} | {region} | {pattern} |")

    return data


# ================================================================
# STEP A5: VAR + Impulse Response Function
# ================================================================

def step_a5(data):
    """Execute Step A5: VAR model fitting + IRF plots."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "AppleGothic",
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "axes.grid": True,
        "grid.alpha": 0.3,
    })

    section("Step A5: VAR Model + Impulse Response Function")

    aligned = data["aligned"]
    csi_transform = data.get("csi_transform", "diff1")
    irf_dir = os.path.join(FIG_DIR, "irf")
    os.makedirs(irf_dir, exist_ok=True)

    var_summary = []

    for (brand, region), grp in aligned.groupby(["brand", "region"]):
        grp = grp.sort_values("year_month").reset_index(drop=True)
        search_vals, csi_vals = prepare_granger_pair(
            grp["residual_mean"], grp["csi"], csi_transform
        )

        if len(search_vals) < 15:
            log(f"  [WARN] {brand}/{region}: too few obs ({len(search_vals)})")
            continue

        var_data = pd.DataFrame({"search_residual": search_vals, "csi": csi_vals})

        try:
            model = VAR(var_data)

            # AIC-based lag selection (advisor: maxlags=4)
            lag_order = model.select_order(maxlags=MAX_LAG)
            best_lag = lag_order.aic
            if best_lag == 0:
                best_lag = 1  # minimum 1 lag

            fitted = model.fit(best_lag)
            log(f"  {brand}/{region}: VAR({fitted.k_ar}), AIC={fitted.aic:.2f}")

            var_summary.append({
                "brand": brand,
                "region": region,
                "var_lag": fitted.k_ar,
                "aic": round(fitted.aic, 4),
                "bic": round(fitted.bic, 4),
            })

            # IRF: 12 months horizon
            irf = fitted.irf(periods=12)
            fig = irf.plot(orth=True)
            fig_path = os.path.join(irf_dir, f"irf_{brand}_{region}.png")
            fig.savefig(fig_path, bbox_inches="tight")
            plt.close(fig)
            log(f"    saved: {fig_path}")

            # Cointegration check (for potential VECM)
            if csi_transform == "diff1":
                # Test on original levels
                orig_search = grp["residual_mean"].values
                orig_csi = grp["csi"].values
                try:
                    coint_stat, coint_p, _ = coint(orig_search, orig_csi)
                    if coint_p < 0.05:
                        log(f"    cointegration detected (p={coint_p:.4f}) -> VECM candidate")
                except Exception:
                    pass

        except Exception as e:
            log(f"  [WARN] {brand}/{region}: VAR failed: {e}")

    data["var_summary"] = pd.DataFrame(var_summary) if var_summary else pd.DataFrame()
    return data


# ================================================================
# STEP A6: Shopping Search Sub-analysis
# ================================================================

def step_a6(data):
    """Execute Step A6: shopping search as purchase-intent Granger input."""
    section("Step A6: Shopping Search Sub-analysis")

    shopping_aligned = data.get("shopping_aligned", pd.DataFrame())
    if shopping_aligned.empty:
        log("  no shopping search data available, skipping")
        return data

    csi_transform = data.get("csi_transform", "diff1")
    log(f"  input: shopping search monthly mean")
    log(f"  CSI preprocessing: {csi_transform}")

    shopping_results = []

    for (brand, region), grp in shopping_aligned.groupby(["brand", "region"]):
        grp = grp.sort_values("year_month").reset_index(drop=True)

        # Shopping search doesn't have MSTL residual, use raw monthly mean
        # Apply ADF check
        shopping_vals = grp["shopping_mean"].values
        csi_vals = grp["csi"].values

        if csi_transform == "diff1":
            csi_clean = np.diff(csi_vals)
            shopping_clean = shopping_vals[1:]
        else:
            csi_clean = csi_vals
            shopping_clean = shopping_vals

        mask = ~(np.isnan(shopping_clean) | np.isnan(csi_clean))
        shopping_clean = shopping_clean[mask]
        csi_clean = csi_clean[mask]

        if len(shopping_clean) < MAX_LAG + 5:
            continue

        results = run_granger_bidirectional(shopping_clean, csi_clean)
        for r in results:
            r["brand"] = brand
            r["region"] = region
            r["input_type"] = "shopping"
        shopping_results.extend(results)

    if shopping_results:
        shop_df = pd.DataFrame(shopping_results)
        data["shopping_granger"] = shop_df

        # Report
        log("")
        log("| Brand | Region | Direction | Best Lag | p-value | Sig |")
        log("|---|---|---|---|---|---|")
        for (brand, region, direction), grp in shop_df.groupby(
            ["brand", "region", "direction"]
        ):
            if len(grp) == 0:
                continue
            best = grp.loc[grp["p_value"].idxmin()]
            sig = "Yes" if best["significant"] else "No"
            log(
                f"| {brand} | {region} | {direction} "
                f"| {best['lag']} | {best['p_value']:.4f} | {sig} |"
            )
    else:
        log("  insufficient shopping search data for Granger tests")

    return data


# ================================================================
# MART INSERT: granger_results
# ================================================================

def insert_granger_to_mart(data):
    """Write Granger results to mart.granger_results table."""
    section("Mart Insert: granger_results")

    granger_df = data.get("granger", pd.DataFrame())
    if granger_df.empty:
        log("  no Granger results to insert")
        return data

    migration_sql = """
CREATE TABLE IF NOT EXISTS mart.granger_results (
    id                  BIGSERIAL PRIMARY KEY,
    brand               brand_enum    NOT NULL,
    region              region_enum   NOT NULL,
    direction           VARCHAR(20)   NOT NULL,
    cause_variable      VARCHAR(50)   NOT NULL,
    effect_variable     VARCHAR(50)   NOT NULL,
    lag_months          SMALLINT      NOT NULL,
    f_statistic         NUMERIC(10,4),
    p_value             NUMERIC(8,6),
    significant         BOOLEAN,
    input_type          VARCHAR(30)   DEFAULT 'web_residual',
    n_obs               SMALLINT,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, region, direction, cause_variable, lag_months, input_type)
);
"""

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(migration_sql)
                inserted = 0
                for _, row in granger_df.iterrows():
                    if pd.isna(row.get("f_statistic")):
                        continue
                    cause = "search_residual" if row["direction"] == "Search->CSI" else "csi"
                    effect = "csi" if row["direction"] == "Search->CSI" else "search_residual"
                    cur.execute("""
                        INSERT INTO mart.granger_results
                            (brand, region, direction, cause_variable, effect_variable,
                             lag_months, f_statistic, p_value, significant, input_type, n_obs)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (brand, region, direction, cause_variable, lag_months, input_type)
                        DO UPDATE SET
                            f_statistic = EXCLUDED.f_statistic,
                            p_value = EXCLUDED.p_value,
                            significant = EXCLUDED.significant,
                            n_obs = EXCLUDED.n_obs,
                            created_at = NOW()
                    """, (
                        row["brand"], row["region"], row["direction"],
                        cause, effect, row["lag"], row["f_statistic"],
                        row["p_value"], row["significant"],
                        row.get("input_type", "web_residual"), row["n_obs"],
                    ))
                    inserted += 1
            conn.commit()
        log(f"  inserted {inserted} rows into mart.granger_results")
    except Exception as e:
        log(f"  [WARN] DB insert failed: {e}")

    return data


# ================================================================
# REPORT GENERATION
# ================================================================

def generate_report():
    """Write full Stage 4 Track A report to markdown."""
    header = [
        "# Stage 4 Track A: Search <-> CSI Leading Indicator Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "**Question:** Does brand-level search demand (micro) serve as a "
        "leading indicator for consumer sentiment (macro CSI), or vice versa?",
        "",
        "**Design Decisions:**",
        "- Search input: MSTL residual (innovation component)",
        "- CSI input: level or 1st difference (ADF-determined)",
        "- Bidirectional: Search->CSI + CSI->Search",
        "- Sub-analysis: shopping search (purchase-intent proxy)",
        f"- Max lag: {MAX_LAG} months, AIC-selected VAR order",
        "- Neural Granger: excluded (40 obs, overfitting risk)",
        "",
        "---",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        for line in header + REPORT_LINES:
            f.write(line + "\n")
    print(f"\nReport saved: {REPORT_PATH}")


# ================================================================
# MAIN
# ================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 4 Track A: Search <-> CSI Leading Indicator"
    )
    parser.add_argument(
        "--step", type=str, default="all",
        choices=["a1", "a2", "a3", "a4", "a5", "a6", "all"],
        help="Run a specific step or all",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    log(f"Stage 4 Track A: Search <-> CSI Leading Indicator Validation")
    log(f"Started: {datetime.now()}")

    # A1 always runs (data needed for all steps)
    data = step_a1()

    if args.step in ("a2", "a3", "a4", "a5", "a6", "all"):
        data = step_a2(data)

    if args.step in ("a3", "a4", "a5", "a6", "all"):
        data = step_a3(data)

    if args.step in ("a4", "a5", "a6", "all"):
        data = step_a4(data)

    if args.step in ("a5", "a6", "all"):
        data = step_a5(data)

    if args.step in ("a6", "all"):
        data = step_a6(data)

    if args.step == "all":
        insert_granger_to_mart(data)

    generate_report()


if __name__ == "__main__":
    main()
