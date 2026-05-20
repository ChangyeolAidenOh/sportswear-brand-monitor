"""
Stage 0 — H4/H5 Rerun with Group Separation
Fixes Naver DataLab relative scale compression issue.

Problem: When "뉴발란스 인스타" (small) and "뉴발란스" (large) are in
the same API call, the small keyword gets compressed to ~0.

Solution: Call each group independently, then merge externally.

Usage: python spike_check_h4_h5_rerun.py
"""

import os
import time
import warnings
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from scipy import stats

load_dotenv()
warnings.filterwarnings("ignore", category=FutureWarning)

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (14, 8),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

FIG_DIR = "figures/exploratory"
os.makedirs(FIG_DIR, exist_ok=True)

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_HEADERS = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    "Content-Type": "application/json",
}

END_DATE = datetime.now().strftime("%Y-%m-%d")
START_DATE = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")


def fetch_naver_single_group(group_name, keywords, start_date, end_date):
    """Fetch a single keyword group from Naver DataLab (independent scale)."""
    url = "https://openapi.naver.com/v1/datalab/search"
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "week",
        "keywordGroups": [
            {"groupName": group_name, "keywords": keywords},
        ],
    }
    try:
        resp = requests.post(url, headers=NAVER_HEADERS, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "results" in data and data["results"]:
            r = data["results"][0]
            df = pd.DataFrame(r["data"])
            df["period"] = pd.to_datetime(df["period"])
            df = df.rename(columns={"period": "date", "ratio": group_name})
            return df
    except Exception as e:
        print(f"  [ERROR] {group_name}: {e}")
    return None


def compute_ccf(s1, s2, max_lag=12):
    """Compute cross-correlation function for lags -max_lag to +max_lag."""
    s1_norm = (s1 - s1.mean()) / (s1.std() + 1e-8)
    s2_norm = (s2 - s2.mean()) / (s2.std() + 1e-8)

    lags = list(range(-max_lag, max_lag + 1))
    ccf = []
    for lag in lags:
        if lag >= 0:
            c = np.corrcoef(s1_norm[:len(s1_norm) - lag] if lag > 0 else s1_norm,
                            s2_norm[lag:] if lag > 0 else s2_norm)[0, 1]
        else:
            c = np.corrcoef(s1_norm[-lag:], s2_norm[:len(s2_norm) + lag])[0, 1]
        ccf.append(c)
    return lags, ccf


# H4 RERUN: Instagram Lead (Separated Groups)
def h4_rerun():
    print("\n" + "=" * 60)
    print("H4 RERUN: Instagram Proxy -> NB Search (Separated Groups)")
    print("=" * 60)

    # Fetch independently
    print("  Fetching NB Instagram proxy (independent)...")
    ig_df = fetch_naver_single_group(
        "NB_Instagram",
        ["뉴발란스 인스타", "뉴발란스 인스타그램"],
        START_DATE, END_DATE,
    )
    time.sleep(2)

    print("  Fetching NB Total (independent)...")
    nb_df = fetch_naver_single_group(
        "NB_Total",
        ["뉴발란스"],
        START_DATE, END_DATE,
    )

    if ig_df is None or nb_df is None:
        print("  [FAIL] API calls failed. Check credentials.")
        return None

    merged = pd.merge(ig_df, nb_df, on="date", how="inner")
    print(f"  Merged: {len(merged)} weeks")
    print(f"  NB Instagram: mean={merged['NB_Instagram'].mean():.1f}, "
          f"max={merged['NB_Instagram'].max():.1f}")
    print(f"  NB Total:     mean={merged['NB_Total'].mean():.1f}, "
          f"max={merged['NB_Total'].max():.1f}")

    # Cross-correlation
    s_ig = merged["NB_Instagram"].values.astype(float)
    s_nb = merged["NB_Total"].values.astype(float)
    lags, ccf = compute_ccf(s_ig, s_nb, max_lag=12)
    significance = 2 / np.sqrt(len(s_ig))

    best_idx = np.argmax(ccf)
    best_lag = lags[best_idx]
    best_corr = ccf[best_idx]

    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))

    ax1 = axes[0]
    ax1_twin = ax1.twinx()
    l1, = ax1.plot(merged["date"], merged["NB_Total"], label="NB Total (left)",
                   color="#3498DB", linewidth=1.5)
    l2, = ax1_twin.plot(merged["date"], merged["NB_Instagram"],
                        label="NB Instagram (right)", color="#C13584", linewidth=1.5)
    ax1.set_ylabel("NB Total (ratio)", color="#3498DB")
    ax1_twin.set_ylabel("NB Instagram (ratio)", color="#C13584")
    ax1.set_title("H4 RERUN: Instagram Proxy vs NB Search (Independent Scales)")
    ax1.legend(handles=[l1, l2], loc="upper left")

    ax2 = axes[1]
    colors = ["#C13584" if l > 0 else "#3498DB" if l < 0 else "gray" for l in lags]
    ax2.bar(lags, ccf, color=colors)
    ax2.axhline(y=0, color="black", linewidth=0.5)
    ax2.axhline(y=significance, color="red", linestyle="--", alpha=0.5,
                label=f"95% CI: +/-{significance:.3f}")
    ax2.axhline(y=-significance, color="red", linestyle="--", alpha=0.5)
    ax2.set_xlabel("Lag (weeks, positive = Instagram leads)")
    ax2.set_ylabel("Cross-correlation")
    ax2.set_title(f"H4 RERUN: CCF (best: r={best_corr:.3f} at lag={best_lag})")
    ax2.legend()

    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "h4_instagram_lead.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")

    # Verdict
    print(f"\n  Best cross-correlation: {best_corr:.3f} at lag = {best_lag} weeks")
    print(f"  95% significance: +/-{significance:.3f}")
    if best_lag > 0 and best_corr > significance:
        verdict = (f"Instagram leads NB search by {best_lag} week(s) "
                   f"(r={best_corr:.3f}). Layer 3 Granger evidence.")
    elif best_lag == 0:
        verdict = f"Contemporaneous (r={best_corr:.3f}). No clear lead."
    elif best_lag < 0 and best_corr > significance:
        verdict = (f"NB search leads Instagram by {abs(best_lag)} week(s) "
                   f"(r={best_corr:.3f}). Reverse direction.")
    else:
        verdict = f"No significant relationship detected."
    print(f"  Verdict: {verdict}")

    return {
        "best_lag": best_lag,
        "best_corr": best_corr,
        "significance": significance,
        "verdict": verdict,
        "ig_mean": merged["NB_Instagram"].mean(),
        "nb_mean": merged["NB_Total"].mean(),
        "fig_path": fig_path,
    }


# H5 RERUN: D2C Share (Separated Groups)
def h5_rerun():
    print("\n" + "=" * 60)
    print("H5 RERUN: D2C Search Share (Separated Groups)")
    print("=" * 60)

    print("  Fetching NB D2C proxy (independent)...")
    d2c_df = fetch_naver_single_group(
        "NB_D2C",
        ["뉴발란스 공식몰", "뉴발란스 자사몰", "뉴발란스 공홈"],
        START_DATE, END_DATE,
    )
    time.sleep(2)

    print("  Fetching NB Total (independent)...")
    nb_df = fetch_naver_single_group(
        "NB_Total",
        ["뉴발란스"],
        START_DATE, END_DATE,
    )

    if d2c_df is None or nb_df is None:
        print("  [FAIL] API calls failed.")
        return None

    merged = pd.merge(d2c_df, nb_df, on="date", how="inner")
    print(f"  Merged: {len(merged)} weeks")
    print(f"  NB D2C:   mean={merged['NB_D2C'].mean():.1f}, "
          f"max={merged['NB_D2C'].max():.1f}")
    print(f"  NB Total: mean={merged['NB_Total'].mean():.1f}, "
          f"max={merged['NB_Total'].max():.1f}")

    # D2C share (independent scales -> ratio of means, not raw division)
    # Since each is independently 0-100, we interpret as relative intensity
    merged["d2c_intensity_ratio"] = merged["NB_D2C"] / merged["NB_Total"].replace(0, np.nan)

    # Trend analysis on D2C standalone
    x = np.arange(len(merged))
    y_d2c = merged["NB_D2C"].values.astype(float)
    slope_d2c, intercept_d2c, r_val, p_val_d2c, _ = stats.linregress(x, y_d2c)

    y_nb = merged["NB_Total"].values.astype(float)
    slope_nb, _, _, p_val_nb, _ = stats.linregress(x, y_nb)

    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))

    ax1 = axes[0]
    ax1_twin = ax1.twinx()
    l1, = ax1.plot(merged["date"], merged["NB_Total"], label="NB Total (left)",
                   color="#3498DB", linewidth=1.5)
    l2, = ax1_twin.plot(merged["date"], merged["NB_D2C"],
                        label="NB D2C (right)", color="#27AE60", linewidth=1.5)
    ax1.set_ylabel("NB Total (ratio)", color="#3498DB")
    ax1_twin.set_ylabel("NB D2C (ratio)", color="#27AE60")
    ax1.set_title("H5 RERUN: D2C vs NB Total (Independent Scales)")
    ax1.legend(handles=[l1, l2], loc="upper left")

    ax2 = axes[1]
    ax2.plot(merged["date"], merged["NB_D2C"], color="#27AE60", linewidth=1.5,
             label="NB D2C")
    trend = slope_d2c * x + intercept_d2c
    ax2.plot(merged["date"], trend, "--", color="red", alpha=0.7,
             label=f"Trend: {slope_d2c:.3f}/week, p={p_val_d2c:.4f}")
    ax2.set_ylabel("D2C Search Intensity (0-100)")
    ax2.set_title("H5 RERUN: D2C Search Trend (Independent Scale)")
    ax2.legend()
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "h5_d2c_share.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")

    # Cross-correlation (D2C leads NB Total?)
    lags, ccf = compute_ccf(y_d2c, y_nb, max_lag=8)
    best_idx = np.argmax(ccf)
    best_lag = lags[best_idx]
    best_corr = ccf[best_idx]

    print(f"\n  D2C trend: slope={slope_d2c:.3f}/week, p={p_val_d2c:.4f}")
    print(f"  NB Total trend: slope={slope_nb:.3f}/week, p={p_val_nb:.4f}")
    print(f"  D2C mean: {merged['NB_D2C'].mean():.1f}")
    print(f"  D2C-NB cross-corr: best r={best_corr:.3f} at lag={best_lag}")

    if p_val_d2c < 0.05:
        direction = "increasing" if slope_d2c > 0 else "decreasing"
        verdict = (f"D2C search is {direction} (slope={slope_d2c:.3f}/week, p={p_val_d2c:.4f}). "
                   f"D2C mean intensity: {merged['NB_D2C'].mean():.1f}/100.")
    else:
        verdict = f"D2C search is stable (p={p_val_d2c:.4f}). Mean: {merged['NB_D2C'].mean():.1f}/100."

    print(f"  Verdict: {verdict}")

    return {
        "d2c_mean": merged["NB_D2C"].mean(),
        "d2c_slope": slope_d2c,
        "d2c_p": p_val_d2c,
        "nb_slope": slope_nb,
        "nb_p": p_val_nb,
        "ccf_best_lag": best_lag,
        "ccf_best_corr": best_corr,
        "verdict": verdict,
        "fig_path": fig_path,
    }


# MAIN
def main():
    print("=" * 60)
    print("H4/H5 RERUN — Group Separation Fix")
    print(f"Period: {START_DATE} ~ {END_DATE}")
    print("=" * 60)

    h4_result = h4_rerun()
    time.sleep(2)
    h5_result = h5_rerun()

    # Summary
    print("\n" + "=" * 60)
    print("=" * 60)

    if h4_result:
        print(f"\nH4: {h4_result['verdict']}")
    if h5_result:
        print(f"\nH5: {h5_result['verdict']}")

    print(f"\nPlots saved to {FIG_DIR}/")
    print("Update docs/exploratory_findings.md with these results.")


if __name__ == "__main__":
    main()
