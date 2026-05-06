"""
Stage 0 — Quick Exploratory Pass
6 hypotheses tested with 1-2 plots each.
Outputs: figures/exploratory/ + docs/exploratory_findings.md

Usage: python quick_exploratory_pass.py
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
from scipy import signal, stats

load_dotenv()
warnings.filterwarnings("ignore", category=FutureWarning)

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (12, 5),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

GTRENDS_DIR = "data/raw/google_trends"
FIG_DIR = "figures/exploratory"
REPORT_PATH = "docs/exploratory_findings.md"
REPORT_LINES = []

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs("docs", exist_ok=True)


def log(msg=""):
    print(msg)
    REPORT_LINES.append(msg)


def section(title):
    log("")
    log(f"## {title}")
    log("")


def load_gtrends(filename):
    path = os.path.join(GTRENDS_DIR, filename)
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ================================================================
# NAVER DATALAB API HELPER
# ================================================================
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_HEADERS = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    "Content-Type": "application/json",
}


def fetch_naver_datalab(keyword_groups, start_date, end_date):
    """Fetch Naver DataLab search trend data."""
    url = "https://openapi.naver.com/v1/datalab/search"
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "week",
        "keywordGroups": keyword_groups,
    }
    try:
        resp = requests.post(url, headers=NAVER_HEADERS, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = {}
        for r in data.get("results", []):
            title = r["title"]
            df = pd.DataFrame(r["data"])
            df["period"] = pd.to_datetime(df["period"])
            df = df.rename(columns={"period": "date"})
            results[title] = df
        return results
    except Exception as e:
        print(f"  [WARN] Naver API error: {e}")
        return None


# ================================================================
# H1: Korea-Global Season Cycle Alignment
# ================================================================
def h1_korea_global_alignment():
    section("H1: Korea-Global Season Cycle Alignment")
    log("**Question:** 한국(530)과 글로벌(9060)의 시즌 사이클이 얼마나 동기화되어 있는가?")
    log("**Common anchor:** 574 (양쪽 생존 모델)")
    log("")

    kr = load_gtrends("products_kr_web.csv")
    ww = load_gtrends("products_ww_web.csv")

    merged = pd.merge(kr[["date", "뉴발란스 530", "뉴발란스 574"]],
                       ww[["date", "New Balance 9060", "New Balance 574"]],
                       on="date", how="inner")

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # Plot 1: 530 vs 9060 (dominant models)
    ax1 = axes[0]
    ax1.plot(merged["date"], merged["뉴발란스 530"], label="Korea: 530", color="#E74C3C", linewidth=1.5)
    ax1.plot(merged["date"], merged["New Balance 9060"], label="Global: 9060", color="#3498DB", linewidth=1.5)
    ax1.set_title("H1a: Korea Dominant (530) vs Global Dominant (9060)")
    ax1.legend()
    ax1.set_ylabel("Interest (0-100)")

    # Plot 2: 574 anchor comparison
    ax2 = axes[1]
    ax2.plot(merged["date"], merged["뉴발란스 574"], label="Korea: 574", color="#E74C3C", linewidth=1.5)
    ax2.plot(merged["date"], merged["New Balance 574"], label="Global: 574", color="#3498DB", linewidth=1.5)
    ax2.set_title("H1b: Common Anchor — 574 Korea vs Global")
    ax2.legend()
    ax2.set_ylabel("Interest (0-100)")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "h1_korea_global_alignment.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    # Cross-correlation
    for label, col_kr, col_ww in [
        ("530 vs 9060", "뉴발란스 530", "New Balance 9060"),
        ("574 KR vs WW", "뉴발란스 574", "New Balance 574"),
    ]:
        s1 = merged[col_kr].values
        s2 = merged[col_ww].values
        s1_norm = (s1 - s1.mean()) / (s1.std() + 1e-8)
        s2_norm = (s2 - s2.mean()) / (s2.std() + 1e-8)
        corr = np.correlate(s1_norm, s2_norm, mode="full") / len(s1)
        lags = np.arange(-len(s1) + 1, len(s1))
        max_idx = np.argmax(np.abs(corr))
        max_lag = lags[max_idx]
        max_corr = corr[max_idx]
        log(f"- **{label}:** max cross-corr = {max_corr:.3f} at lag = {max_lag} weeks")

    log("")
    log(f"![H1]({fig_path})")
    log("")
    log("**Verdict:** TBD based on lag values. Positive lag = Korea leads.")


# ================================================================
# H2: 530 vs 992 Season Separation
# ================================================================
def h2_season_separation():
    section("H2: 530 vs 992 Season Separation")
    log("**Question:** 530은 SS, 992는 FW 피크를 보이는가?")
    log("")

    kr = load_gtrends("products_kr_web.csv")
    kr["month"] = kr["date"].dt.month

    monthly_530 = kr.groupby("month")["뉴발란스 530"].mean()
    monthly_992 = kr.groupby("month")["뉴발란스 992"].mean()

    fig, ax = plt.subplots(figsize=(10, 5))
    months = range(1, 13)
    ax.bar([m - 0.2 for m in months], [monthly_530.get(m, 0) for m in months],
           width=0.35, label="530", color="#E74C3C", alpha=0.8)
    ax.bar([m + 0.2 for m in months], [monthly_992.get(m, 0) for m in months],
           width=0.35, label="992", color="#3498DB", alpha=0.8)
    ax.set_xlabel("Month")
    ax.set_ylabel("Average Interest")
    ax.set_title("H2: Monthly Average — 530 vs 992 (Korea, Google Trends)")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.legend()
    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "h2_season_separation.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    # SS vs FW stats
    ss_months = [3, 4, 5, 6, 7, 8]
    fw_months = [9, 10, 11, 12, 1, 2]

    for name, series in [("530", monthly_530), ("992", monthly_992)]:
        ss_avg = series[series.index.isin(ss_months)].mean()
        fw_avg = series[series.index.isin(fw_months)].mean()
        ratio = ss_avg / fw_avg if fw_avg > 0 else 0
        log(f"- **{name}:** SS avg = {ss_avg:.1f}, FW avg = {fw_avg:.1f}, SS/FW ratio = {ratio:.2f}")

    log("")
    log(f"![H2]({fig_path})")
    log("")
    log("**Verdict:** SS/FW ratio > 1.2 → SS dominant. < 0.8 → FW dominant.")


# ================================================================
# H3: 530 Dependency Trend
# ================================================================
def h3_dependency_trend():
    section("H3: 530 Dependency Trend")
    log("**Question:** NB 한국 제품 검색에서 530 비중이 시간에 따라 심화/완화 중인가?")
    log("")

    kr = load_gtrends("products_kr_web.csv")
    product_cols = ["뉴발란스 530", "뉴발란스 992", "뉴발란스 574", "뉴발란스 2002R", "뉴발란스 327"]
    kr["total"] = kr[product_cols].sum(axis=1)
    kr["share_530"] = kr["뉴발란스 530"] / kr["total"].replace(0, np.nan) * 100
    kr["quarter"] = kr["date"].dt.to_period("Q")

    quarterly = kr.groupby("quarter").agg(
        share_530_mean=("share_530", "mean"),
        share_530_std=("share_530", "std"),
    ).reset_index()
    quarterly["quarter_str"] = quarterly["quarter"].astype(str)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(range(len(quarterly)), quarterly["share_530_mean"],
            marker="o", color="#E74C3C", linewidth=2, markersize=5)
    ax.fill_between(range(len(quarterly)),
                     quarterly["share_530_mean"] - quarterly["share_530_std"],
                     quarterly["share_530_mean"] + quarterly["share_530_std"],
                     alpha=0.2, color="#E74C3C")
    ax.set_xticks(range(len(quarterly)))
    ax.set_xticklabels(quarterly["quarter_str"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("530 Share of NB Product Search (%)")
    ax.set_title("H3: 530 Dependency Trend (Quarterly)")
    ax.axhline(y=quarterly["share_530_mean"].mean(), color="gray",
               linestyle="--", alpha=0.5, label=f'Overall avg: {quarterly["share_530_mean"].mean():.1f}%')
    ax.legend()
    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "h3_530_dependency.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    # Trend test
    x = np.arange(len(quarterly))
    y = quarterly["share_530_mean"].values
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    log(f"- Overall avg 530 share: {y.mean():.1f}%")
    log(f"- Linear trend slope: {slope:.2f}%p per quarter")
    log(f"- R-squared: {r_value**2:.3f}, p-value: {p_value:.4f}")
    log(f"- Direction: {'INTENSIFYING' if slope > 0 else 'WEAKENING'}")
    log("")
    log(f"![H3]({fig_path})")
    log("")
    if p_value < 0.05:
        log(f"**Verdict:** Statistically significant trend (p={p_value:.4f}). "
            f"530 dependency is {'intensifying' if slope > 0 else 'weakening'}.")
    else:
        log(f"**Verdict:** No significant trend (p={p_value:.4f}). 530 dependency is stable.")


# ================================================================
# H4: Instagram Proxy → NB Search Lead
# ================================================================
def h4_instagram_lead():
    section("H4: Instagram Proxy → NB Search Lead")
    log("**Question:** Instagram 프록시가 NB 전체 검색을 선행하는가?")
    log("")

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

    keyword_groups = [
        {"groupName": "NB Instagram", "keywords": ["뉴발란스 인스타", "뉴발란스 인스타그램"]},
        {"groupName": "NB Total", "keywords": ["뉴발란스"]},
    ]

    data = fetch_naver_datalab(keyword_groups, start_date, end_date)
    if data is None or len(data) < 2:
        log("**SKIPPED:** Naver API call failed. Run separately or check API keys.")
        return

    ig = data["NB Instagram"]
    nb = data["NB Total"]
    merged = pd.merge(ig, nb, on="date", suffixes=("_ig", "_nb"))

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # Time series
    ax1 = axes[0]
    ax1.plot(merged["date"], merged["ratio_ig"], label="NB Instagram proxy", color="#C13584", linewidth=1.5)
    ax1.plot(merged["date"], merged["ratio_nb"], label="NB Total search", color="#3498DB", linewidth=1.5)
    ax1.set_title("H4: Instagram Proxy vs NB Total Search (Naver)")
    ax1.legend()
    ax1.set_ylabel("Ratio")

    # Cross-correlation
    ax2 = axes[1]
    s1 = merged["ratio_ig"].values.astype(float)
    s2 = merged["ratio_nb"].values.astype(float)
    s1_norm = (s1 - s1.mean()) / (s1.std() + 1e-8)
    s2_norm = (s2 - s2.mean()) / (s2.std() + 1e-8)

    max_lag = 12
    lags = range(-max_lag, max_lag + 1)
    ccf = []
    for lag in lags:
        if lag >= 0:
            c = np.corrcoef(s1_norm[:len(s1_norm)-lag], s2_norm[lag:])[0, 1]
        else:
            c = np.corrcoef(s1_norm[-lag:], s2_norm[:len(s2_norm)+lag])[0, 1]
        ccf.append(c)

    ax2.bar(lags, ccf, color=["#C13584" if l > 0 else "#3498DB" if l < 0 else "gray" for l in lags])
    ax2.set_xlabel("Lag (weeks, positive = Instagram leads)")
    ax2.set_ylabel("Cross-correlation")
    ax2.set_title("H4: Cross-Correlation Function (Instagram → NB Search)")
    ax2.axhline(y=0, color="black", linewidth=0.5)
    significance = 2 / np.sqrt(len(s1))
    ax2.axhline(y=significance, color="red", linestyle="--", alpha=0.5, label=f"95% CI: ±{significance:.3f}")
    ax2.axhline(y=-significance, color="red", linestyle="--", alpha=0.5)
    ax2.legend()

    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "h4_instagram_lead.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    best_lag = lags[np.argmax(ccf)]
    best_corr = max(ccf)
    log(f"- Best cross-correlation: {best_corr:.3f} at lag = {best_lag} weeks")
    log(f"- 95% significance threshold: ±{significance:.3f}")
    log("")
    log(f"![H4]({fig_path})")
    log("")
    if best_lag > 0 and best_corr > significance:
        log(f"**Verdict:** Instagram leads NB search by {best_lag} week(s). "
            f"Layer 3 Social→Search Granger 사전 evidence 확보.")
    elif best_lag == 0:
        log("**Verdict:** Contemporaneous relationship. No clear lead.")
    else:
        log("**Verdict:** NB search leads Instagram proxy. Reverse direction.")


# ================================================================
# H5: D2C Search Share
# ================================================================
def h5_d2c_share():
    section("H5: D2C Search Share Trend")
    log("**Question:** NB D2C(공식몰) 검색이 NB 전체 대비 어떤 비중이고, 추세가 있는가?")
    log("")

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

    keyword_groups = [
        {"groupName": "NB D2C", "keywords": ["뉴발란스 공식몰", "뉴발란스 자사몰", "뉴발란스 공홈"]},
        {"groupName": "NB Total", "keywords": ["뉴발란스"]},
    ]

    data = fetch_naver_datalab(keyword_groups, start_date, end_date)
    if data is None or len(data) < 2:
        log("**SKIPPED:** Naver API call failed.")
        return

    d2c = data["NB D2C"]
    nb = data["NB Total"]
    merged = pd.merge(d2c, nb, on="date", suffixes=("_d2c", "_nb"))
    merged["d2c_share"] = merged["ratio_d2c"] / merged["ratio_nb"].replace(0, np.nan) * 100

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    ax1 = axes[0]
    ax1.plot(merged["date"], merged["ratio_d2c"], label="NB D2C search", color="#27AE60", linewidth=1.5)
    ax1.plot(merged["date"], merged["ratio_nb"], label="NB Total search", color="#3498DB", linewidth=1.5)
    ax1.set_title("H5: D2C vs Total NB Search (Naver)")
    ax1.legend()
    ax1.set_ylabel("Ratio")

    ax2 = axes[1]
    ax2.plot(merged["date"], merged["d2c_share"], color="#27AE60", linewidth=1.5)
    ax2.set_title("H5: D2C Share of NB Total Search (%)")
    ax2.set_ylabel("D2C Share (%)")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    # Trend line
    x = np.arange(len(merged))
    y = merged["d2c_share"].dropna().values
    if len(y) > 10:
        slope, intercept, r_value, p_value, _ = stats.linregress(x[:len(y)], y)
        trend_line = slope * x[:len(y)] + intercept
        ax2.plot(merged["date"].iloc[:len(y)], trend_line, "--", color="red",
                 alpha=0.7, label=f"Trend: {slope:.3f}%/week, p={p_value:.3f}")
        ax2.legend()

    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "h5_d2c_share.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    avg_share = merged["d2c_share"].mean()
    log(f"- Average D2C share: {avg_share:.1f}%")
    if len(y) > 10:
        log(f"- Trend slope: {slope:.3f}% per week")
        log(f"- p-value: {p_value:.4f}")
    log("")
    log(f"![H5]({fig_path})")
    log("")
    if len(y) > 10 and p_value < 0.05:
        log(f"**Verdict:** D2C share {'increasing' if slope > 0 else 'decreasing'} "
            f"(p={p_value:.4f}). D2C strategy effect is measurable.")
    else:
        log("**Verdict:** No significant trend. D2C share is stable.")


# ================================================================
# H6: Padding Season Start Timing — NB vs North Face
# ================================================================
def h6_padding_timing():
    section("H6: Padding Season Start Timing — NB vs North Face")
    log("**Question:** NB 패딩은 노스페이스 대비 시즌 시작이 빠른가, 늦은가?")
    log("**Method:** 7-week MA가 연간 baseline(52주 평균) 대비 +30% 처음 도달하는 주.")
    log("")

    df = load_gtrends("padding_competitive_kr.csv")
    padding_cols = ["뉴발란스 패딩", "나이키 패딩", "아디다스 패딩", "노스페이스 패딩"]

    # Compute 7-week MA
    for col in padding_cols:
        df[f"{col}_ma7"] = df[col].rolling(7, center=True).mean()

    df["year"] = df["date"].dt.year
    df["week"] = df["date"].dt.isocalendar().week.astype(int)

    # Find season start per brand per year
    results = {}
    for col in padding_cols:
        brand_name = col.replace(" 패딩", "").replace("패딩", "")
        results[brand_name] = []

        for year in sorted(df["year"].unique()):
            year_data = df[df["year"] == year].copy()
            if len(year_data) < 20:
                continue

            baseline = year_data[col].mean()
            threshold = baseline * 1.3

            ma_col = f"{col}_ma7"
            above = year_data[year_data[ma_col] >= threshold]

            if len(above) > 0:
                # Find first crossing in Jul-Dec (week 27-52) for winter padding
                winter = above[(above["week"] >= 27) & (above["week"] <= 52)]
                if len(winter) > 0:
                    start_week = winter["week"].iloc[0]
                    start_date = winter["date"].iloc[0]
                    results[brand_name].append({
                        "year": year,
                        "start_week": start_week,
                        "start_date": start_date,
                        "baseline": baseline,
                        "threshold": threshold,
                    })

    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))

    # Plot 1: Full time series with season markers
    ax1 = axes[0]
    colors = {"뉴발란스": "#E74C3C", "나이키": "#FF6B00", "아디다스": "#3498DB", "노스페이스": "#2ECC71"}
    for col in padding_cols:
        brand = col.replace(" 패딩", "").replace("패딩", "")
        ax1.plot(df["date"], df[f"{col}_ma7"], label=col, color=colors.get(brand, "gray"), linewidth=1.2)
    ax1.set_title("H6: Padding Search — 7-Week Moving Average (5 Years)")
    ax1.legend(loc="upper left")
    ax1.set_ylabel("Interest (MA7)")

    # Plot 2: Season start week comparison
    ax2 = axes[1]
    brand_names = list(results.keys())
    x_positions = np.arange(len(brand_names))
    width = 0.15

    years_all = sorted(set(r["year"] for rlist in results.values() for r in rlist))
    for i, year in enumerate(years_all):
        weeks = []
        for brand in brand_names:
            year_data = [r for r in results[brand] if r["year"] == year]
            weeks.append(year_data[0]["start_week"] if year_data else 0)
        ax2.bar(x_positions + i * width, weeks, width, label=str(year), alpha=0.8)

    ax2.set_xticks(x_positions + width * (len(years_all) - 1) / 2)
    ax2.set_xticklabels(brand_names)
    ax2.set_ylabel("Season Start Week Number")
    ax2.set_title("H6: Padding Season Start Week by Brand and Year")
    ax2.legend(title="Year", loc="upper right")

    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "h6_padding_timing.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    # Summary stats
    log("### Season Start Week Summary (Week 27-52)")
    log("")
    log("| Brand | Years Detected | Avg Start Week | Std | Earliest | Latest |")
    log("|---|---|---|---|---|---|")

    brand_avgs = {}
    for brand, data_list in results.items():
        if not data_list:
            log(f"| {brand} | 0 | - | - | - | - |")
            continue
        weeks = [d["start_week"] for d in data_list]
        avg_w = np.mean(weeks)
        std_w = np.std(weeks)
        brand_avgs[brand] = avg_w
        log(f"| {brand} | {len(weeks)} | {avg_w:.1f} | {std_w:.1f} | {min(weeks)} | {max(weeks)} |")

    log("")
    log(f"![H6]({fig_path})")
    log("")

    if "뉴발란스" in brand_avgs and "노스페이스" in brand_avgs:
        gap = brand_avgs["뉴발란스"] - brand_avgs["노스페이스"]
        if gap > 0:
            log(f"**Verdict:** NB 패딩 시즌 시작이 노스페이스 대비 평균 {gap:.1f}주 늦다. "
                f"마케팅 타이밍 조정의 데이터 근거.")
        elif gap < 0:
            log(f"**Verdict:** NB 패딩 시즌 시작이 노스페이스 대비 평균 {abs(gap):.1f}주 빠르다.")
        else:
            log("**Verdict:** NB와 노스페이스 패딩 시즌 시작이 동일.")
    else:
        log("**Verdict:** Insufficient data for timing comparison.")


# ================================================================
# REPORT GENERATOR
# ================================================================
def generate_report():
    header = [
        "# Quick Exploratory Pass — Findings Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Author:** Changyeol Oh",
        f"**Stage:** 0 (Quick Exploratory Pass)",
        "",
        "---",
        "",
        "## Overview",
        "",
        "Stage 0 Data Feasibility Spike에서 수집한 Google Trends 8개 CSV + Naver DataLab 데이터를 기반으로,",
        "6개 가설을 1-2 plot으로 빠르게 검증하여 본 파이프라인(Stage 1~8)의 분석 방향을 확정한다.",
        "",
        "---",
    ]

    footer = [
        "",
        "---",
        "",
        "## Hypothesis Status Summary",
        "",
        "| Hypothesis | Status | Action |",
        "|---|---|---|",
        "| H1: Korea-Global alignment | See above | → Layer 4 Bridge if significant lag |",
        "| H2: 530 vs 992 season | See above | → Stage 2 시즌 분해 baseline |",
        "| H3: 530 dependency trend | See above | → 제품 집중도 인사이트 |",
        "| H4: Instagram → Search lead | See above | → Layer 3 Granger 사전 evidence |",
        "| H5: D2C search share | See above | → D2C 전략 효과 측정 |",
        "| H6: Padding timing | See above | → 마케팅 타이밍 인사이트 |",
        "",
        "---",
        "",
        "*본 리포트는 Stage 0 Quick Exploratory Pass의 산출물이다.*",
    ]

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        for line in header + REPORT_LINES + footer:
            f.write(line + "\n")

    print(f"\nReport saved: {REPORT_PATH}")


# ================================================================
# MAIN
# ================================================================
def main():
    print("=" * 60)
    print("Quick Exploratory Pass — 6 Hypotheses")
    print("=" * 60)

    h1_korea_global_alignment()
    h2_season_separation()
    h3_dependency_trend()

    print("\n--- Naver API calls for H4, H5 ---")
    h4_instagram_lead()
    time.sleep(1)
    h5_d2c_share()

    h6_padding_timing()

    generate_report()

    print(f"\n{'='*60}")
    print("Quick Exploratory Pass complete.")
    print(f"  Report: {REPORT_PATH}")
    print(f"  Figures: {FIG_DIR}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
