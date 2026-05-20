"""
Stage 0 - Data Feasibility Spike
Tests 5 verification items and generates docs/data_feasibility_report.md

Run: python spike_feasibility.py
"""

import json
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_HEADERS = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    "Content-Type": "application/json",
}

TODAY = datetime.now().strftime("%Y-%m-%d")
TWO_YEARS_AGO = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

REPORT_LINES = []


def log(msg):
    print(msg)
    REPORT_LINES.append(msg)


def section(title):
    log("")
    log(f"## {title}")
    log("")


# CHECK 1: Naver DataLab Search Trend API - response format
def check_naver_datalab_api():
    section("Check 1: Naver DataLab Search Trend API")

    url = "https://openapi.naver.com/v1/datalab/search"
    body = {
        "startDate": TWO_YEARS_AGO,
        "endDate": TODAY,
        "timeUnit": "week",
        "keywordGroups": [
            {"groupName": "Nike", "keywords": ["나이키"]},
            {"groupName": "Adidas", "keywords": ["아디다스"]},
            {"groupName": "Puma", "keywords": ["푸마"]},
            {"groupName": "New Balance", "keywords": ["뉴발란스"]},
        ],
    }

    try:
        resp = requests.post(url, headers=NAVER_HEADERS, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        log("- API status: OK")
        log(f"- Response keys: {list(data.keys())}")
        log(f"- Number of keyword groups returned: {len(data.get('results', []))}")

        if "results" in data and len(data["results"]) > 0:
            first = data["results"][0]
            log(f"- First group title: {first.get('title')}")
            log(f"- Data points count: {len(first.get('data', []))}")
            if first.get("data"):
                sample = first["data"][:3]
                log(f"- Sample data (first 3 weeks):")
                for s in sample:
                    log(f"  - period: {s['period']}, ratio: {s['ratio']}")

                last3 = first["data"][-3:]
                log(f"- Sample data (last 3 weeks):")
                for s in last3:
                    log(f"  - period: {s['period']}, ratio: {s['ratio']}")

        log("")
        log("**Result: Naver DataLab Search API works. Weekly granularity confirmed.**")
        return data

    except Exception as e:
        log(f"- API FAILED: {e}")
        log("**Result: FAIL. Fallback to manual CSV download from datalab.naver.com.**")
        return None


# CHECK 2: NB product line search volume sufficiency
def check_nb_product_lines():
    section("Check 2: NB Product Line Search Volume (530/992/2002R/327)")

    url = "https://openapi.naver.com/v1/datalab/search"
    body = {
        "startDate": TWO_YEARS_AGO,
        "endDate": TODAY,
        "timeUnit": "week",
        "keywordGroups": [
            {"groupName": "NB 530", "keywords": ["뉴발란스 530", "뉴발 530"]},
            {"groupName": "NB 992", "keywords": ["뉴발란스 992", "뉴발 992"]},
            {"groupName": "NB 2002R", "keywords": ["뉴발란스 2002R", "뉴발 2002R", "뉴발란스 2002r"]},
            {"groupName": "NB 327", "keywords": ["뉴발란스 327", "뉴발 327"]},
        ],
    }

    try:
        resp = requests.post(url, headers=NAVER_HEADERS, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        log("| Product Line | Avg Ratio | Max Ratio | Min Ratio | Zero Weeks | Total Weeks | Verdict |")
        log("|---|---|---|---|---|---|---|")

        threshold = 5
        viable = []

        for result in data.get("results", []):
            title = result["title"]
            ratios = [d["ratio"] for d in result.get("data", [])]
            if not ratios:
                log(f"| {title} | - | - | - | - | - | NO DATA |")
                continue

            avg_r = sum(ratios) / len(ratios)
            max_r = max(ratios)
            min_r = min(ratios)
            zero_count = sum(1 for r in ratios if r == 0)
            total = len(ratios)
            verdict = "VIABLE" if avg_r >= threshold else "BELOW THRESHOLD"

            if avg_r >= threshold:
                viable.append(title)

            log(f"| {title} | {avg_r:.1f} | {max_r:.1f} | {min_r:.1f} | {zero_count} | {total} | {verdict} |")

        log("")
        log(f"**Threshold: avg ratio >= {threshold}**")
        log(f"**Viable product lines: {', '.join(viable) if viable else 'NONE'}**")
        log(f"**Below-threshold lines will be excluded from product portfolio analysis.**")
        return data

    except Exception as e:
        log(f"- API FAILED: {e}")
        return None


# CHECK 3: TikTok proxy search volume
def check_tiktok_proxy():
    section("Check 3: TikTok Proxy Search Volume")

    url = "https://openapi.naver.com/v1/datalab/search"
    body = {
        "startDate": TWO_YEARS_AGO,
        "endDate": TODAY,
        "timeUnit": "week",
        "keywordGroups": [
            {"groupName": "NB TikTok", "keywords": ["뉴발란스 틱톡"]},
            {"groupName": "Nike TikTok", "keywords": ["나이키 틱톡"]},
            {"groupName": "NB Instagram", "keywords": ["뉴발란스 인스타", "뉴발란스 인스타그램"]},
            {"groupName": "NB YouTube", "keywords": ["뉴발란스 유튜브"]},
        ],
    }

    try:
        resp = requests.post(url, headers=NAVER_HEADERS, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        log("| Proxy Keyword | Avg Ratio | Max Ratio | Zero Weeks (%) | Verdict |")
        log("|---|---|---|---|---|")

        for result in data.get("results", []):
            title = result["title"]
            ratios = [d["ratio"] for d in result.get("data", [])]
            if not ratios:
                log(f"| {title} | - | - | - | INSUFFICIENT |")
                continue

            avg_r = sum(ratios) / len(ratios)
            max_r = max(ratios)
            zero_pct = sum(1 for r in ratios if r == 0) / len(ratios) * 100
            verdict = "USABLE" if avg_r >= 3 and zero_pct < 50 else "INSUFFICIENT"
            log(f"| {title} | {avg_r:.1f} | {max_r:.1f} | {zero_pct:.0f}% | {verdict} |")

        log("")
        log("**If TikTok proxy is INSUFFICIENT: fall back to YouTube-only social analysis.**")
        log("**Instagram proxy tested as supplementary signal.**")
        return data

    except Exception as e:
        log(f"- API FAILED: {e}")
        return None


# CHECK 4: Naver Shopping Insight - channel data availability
def check_shopping_insight():
    section("Check 4: Naver Shopping Insight - Channel Data Availability (Plan A/B/C)")

    log("### 4a. Shopping Insight Category Trend API")

    url_cat = "https://openapi.naver.com/v1/datalab/shopping/categories"
    body_cat = {
        "startDate": TWO_YEARS_AGO,
        "endDate": TODAY,
        "timeUnit": "month",
        "category": [
            {"name": "sportswear_sneakers", "param": ["50000804"]},
        ],
    }

    cat_ok = False
    try:
        resp = requests.post(url_cat, headers=NAVER_HEADERS, json=body_cat, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        log(f"- Category API status: OK")
        log(f"- Response keys: {list(data.keys())}")
        if "results" in data and data["results"]:
            log(f"- Data points: {len(data['results'][0].get('data', []))}")
            cat_ok = True
        else:
            log(f"- Results empty. Category code 50000804 may be invalid.")
            log(f"- Raw response: {json.dumps(data, ensure_ascii=False)[:500]}")
    except requests.exceptions.HTTPError as e:
        log(f"- Category API HTTP error: {e}")
        log(f"- Response body: {e.response.text[:500] if e.response else 'N/A'}")
    except Exception as e:
        log(f"- Category API error: {e}")

    log("")
    log("### 4b. Shopping Insight Keyword Device/Gender/Age Breakdown")

    url_keyword = "https://openapi.naver.com/v1/datalab/shopping/category/keyword"
    body_keyword = {
        "startDate": TWO_YEARS_AGO,
        "endDate": TODAY,
        "timeUnit": "month",
        "category": "50000804",
        "keyword": "뉴발란스",
    }

    try:
        resp = requests.post(url_keyword, headers=NAVER_HEADERS, json=body_keyword, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        log(f"- Keyword trend API status: OK")
        log(f"- Response keys: {list(data.keys())}")
        if "results" in data and data["results"]:
            log(f"- Data points: {len(data['results'][0].get('data', []))}")
    except requests.exceptions.HTTPError as e:
        log(f"- Keyword trend API HTTP error: {e}")
        log(f"- Response body: {e.response.text[:500] if e.response else 'N/A'}")
    except Exception as e:
        log(f"- Keyword trend API error: {e}")

    log("")
    log("### 4c. Platform/Channel Breakdown Assessment")
    log("")
    log("Naver Shopping Insight API provides the following breakdowns:")
    log("- /category/keyword : keyword trend within category")
    log("- /category/keyword/age : age group breakdown")
    log("- /category/keyword/device : PC vs Mobile breakdown")
    log("- /category/keyword/gender : gender breakdown")
    log("")
    log("**There is NO endpoint for platform-level breakdown (Musinsa/Coupang/D2C).**")
    log("**The API does not expose which shopping platform generated the clicks.**")
    log("")
    log("### Plan Decision")
    log("")
    log("- **Plan A (direct platform data): NOT FEASIBLE** - API has no platform-level endpoint")
    log("- **Plan B (search proxy): RECOMMENDED** - use Naver DataLab search for")
    log('  "뉴발란스 무신사", "뉴발란스 자사몰", "뉴발란스 쿠팡" as channel proxies')
    log("- **Plan C (category-level only): FALLBACK** - if Plan B search volume is insufficient")

    return cat_ok


# CHECK 4d: Plan B - channel proxy search volume validation
def check_channel_proxy():
    section("Check 4d: Plan B Channel Proxy Search Volume")

    url = "https://openapi.naver.com/v1/datalab/search"
    body = {
        "startDate": TWO_YEARS_AGO,
        "endDate": TODAY,
        "timeUnit": "week",
        "keywordGroups": [
            {"groupName": "NB Musinsa", "keywords": ["뉴발란스 무신사"]},
            {"groupName": "NB Official", "keywords": ["뉴발란스 자사몰", "뉴발란스 공식몰", "뉴발란스 공홈"]},
            {"groupName": "NB Coupang", "keywords": ["뉴발란스 쿠팡"]},
            {"groupName": "NB Kream", "keywords": ["뉴발란스 크림", "뉴발란스 KREAM"]},
        ],
    }

    try:
        resp = requests.post(url, headers=NAVER_HEADERS, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        log("| Channel Proxy | Avg Ratio | Max Ratio | Zero Weeks (%) | Verdict |")
        log("|---|---|---|---|---|")

        plan_b_viable = []
        for result in data.get("results", []):
            title = result["title"]
            ratios = [d["ratio"] for d in result.get("data", [])]
            if not ratios:
                log(f"| {title} | - | - | - | INSUFFICIENT |")
                continue

            avg_r = sum(ratios) / len(ratios)
            max_r = max(ratios)
            zero_pct = sum(1 for r in ratios if r == 0) / len(ratios) * 100
            verdict = "VIABLE" if avg_r >= 2 and zero_pct < 60 else "INSUFFICIENT"
            if verdict == "VIABLE":
                plan_b_viable.append(title)
            log(f"| {title} | {avg_r:.1f} | {max_r:.1f} | {zero_pct:.0f}% | {verdict} |")

        log("")
        if plan_b_viable:
            log(f"**Plan B viable channels: {', '.join(plan_b_viable)}**")
            log("**Decision: Adopt Plan B for viable channels, Plan C for insufficient ones.**")
        else:
            log("**All channel proxies below threshold. Adopt Plan C (category-level only).**")
        return data

    except Exception as e:
        log(f"- API FAILED: {e}")
        return None


# CHECK 5: pytrends rate limit
def check_pytrends_rate_limit():
    section("Check 5: pytrends Rate Limit Test")

    try:
        from pytrends.request import TrendReq
    except ImportError:
        log("- pytrends not installed. Run: pip install pytrends")
        log("**Result: SKIPPED. Install pytrends and re-run.**")
        return

    pytrends = TrendReq(hl="ko", tz=540)
    test_keywords = ["nike", "adidas", "puma", "new balance"]

    n_calls = 15
    log(f"- Testing {n_calls} sequential calls with 2s interval...")
    log(f"- Keywords: {test_keywords}")

    success = 0
    fail = 0
    times = []
    rate_limited_at = None

    for i in range(n_calls):
        start = time.time()
        try:
            pytrends.build_payload(test_keywords, timeframe="today 3-m", geo="KR")
            df = pytrends.interest_over_time()
            elapsed = time.time() - start
            times.append(elapsed)
            success += 1

            if i == 0:
                log(f"- First call response shape: {df.shape}")
                log(f"- Columns: {list(df.columns)}")

        except Exception as e:
            elapsed = time.time() - start
            fail += 1
            if rate_limited_at is None:
                rate_limited_at = i + 1
            log(f"- Call {i+1} FAILED after {elapsed:.1f}s: {type(e).__name__}")

        time.sleep(2)

    avg_time = sum(times) / len(times) if times else 0
    log("")
    log(f"- Success: {success}/{n_calls}")
    log(f"- Failed: {fail}/{n_calls}")
    log(f"- Avg response time: {avg_time:.2f}s")
    if rate_limited_at:
        log(f"- Rate limited at call #{rate_limited_at}")
        log(f"- Estimated safe interval: {max(3, 60 // rate_limited_at)}s between calls")
    else:
        log(f"- No rate limiting detected at 2s intervals")

    log("")
    log("**Caching strategy recommendation:**")
    if fail == 0:
        log("- 2s interval is safe. Batch all keyword groups with 2s delay.")
        log("- Cache responses to data/raw/ as CSV to avoid repeat calls.")
    else:
        safe_interval = max(5, 60 // max(rate_limited_at - 1, 1))
        log(f"- Use {safe_interval}s interval between calls.")
        log("- Implement exponential backoff on 429 errors.")
        log("- Cache all responses to data/raw/ as CSV.")


# REPORT GENERATOR
def generate_report():
    os.makedirs("docs", exist_ok=True)
    report_path = "docs/data_feasibility_report.md"

    header = [
        "# Data Feasibility Spike Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ""
        f"**Stage:** 0 (Data Feasibility Spike)",
        f"**Query period:** {TWO_YEARS_AGO} ~ {TODAY}",
        "",
        "---",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        for line in header + REPORT_LINES:
            f.write(line + "\n")

    print(f"\nReport saved: {report_path}")


# MAIN
def main():
    log("# Data Feasibility Spike - Execution Log")
    log(f"Timestamp: {datetime.now().isoformat()}")

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        log("ERROR: NAVER_CLIENT_ID or NAVER_CLIENT_SECRET not found in .env")
        log("Set these values and re-run.")
        generate_report()
        return

    check_naver_datalab_api()
    time.sleep(1)

    check_nb_product_lines()
    time.sleep(1)

    check_tiktok_proxy()
    time.sleep(1)

    check_shopping_insight()
    time.sleep(1)

    check_channel_proxy()
    time.sleep(1)

    check_pytrends_rate_limit()

    section("Summary & Decisions")
    log("| Item | Status | Decision |")
    log("|---|---|---|")
    log("| Naver DataLab API | See Check 1 | API or manual CSV |")
    log("| NB Product Lines | See Check 2 | Viable lines only |")
    log("| TikTok Proxy | See Check 3 | YouTube fallback if insufficient |")
    log("| Shopping Insight Channel | See Check 4 | Plan B (search proxy) |")
    log("| Channel Proxy Volume | See Check 4d | Viable channels only |")
    log("| pytrends Rate Limit | See Check 5 | Caching + interval |")

    generate_report()


if __name__ == "__main__":
    main()
