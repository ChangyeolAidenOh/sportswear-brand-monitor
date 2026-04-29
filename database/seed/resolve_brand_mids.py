"""
Stage 0 — Resolve Google Trends Entity/Topic MIDs
1. pytrends suggestions() -> all candidates per brand
2. build_payload() per mid -> 3-year time-series validation
3. Output: ranked candidates with avg, continuity score

Usage:
  python database/seed/resolve_brand_mids.py --dry-run          # probe 1 call, check IP status
  python database/seed/resolve_brand_mids.py --skip-validation  # suggestions only, no build_payload
  python database/seed/resolve_brand_mids.py                    # full run
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

import pandas as pd

try:
    from pytrends.request import TrendReq
except ImportError:
    print("[ERROR] pytrends not installed. Run: pip install pytrends")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Resolve Google Trends MIDs")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Single probe call to check IP block status, then ask for confirmation",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Run suggestions() only, skip build_payload() time-series validation",
    )
    return parser.parse_args()


BRANDS = {
    "nike": {
        "queries": ["Nike", "nike", "나이키"],
        "is_core": True,
    },
    "adidas": {
        "queries": ["Adidas", "adidas", "아디다스"],
        "is_core": True,
    },
    "puma": {
        "queries": ["Puma", "puma", "푸마"],
        "is_core": True,
    },
    "new_balance": {
        "queries": ["New Balance", "new balance", "뉴발란스"],
        "is_core": True,
    },
    "lululemon": {
        "queries": ["lululemon", "Lululemon", "룰루레몬"],
        "is_core": False,
    },
    "asics": {
        "queries": ["Asics", "ASICS", "아식스"],
        "is_core": False,
    },
}

CALL_INTERVAL = 5
BACKOFF_BASE = 10
OUTPUT_DIR = "database/seed"
REPORT_PATH = "docs/mid_resolution_report.md"


def get_suggestions(pytrends, brand_key, queries):
    """Get all unique topic/entity suggestions for a brand."""
    seen_mids = set()
    candidates = []

    for q in queries:
        try:
            results = pytrends.suggestions(keyword=q)
            time.sleep(CALL_INTERVAL)
        except Exception as e:
            print(f"  [WARN] suggestions('{q}') failed: {e}")
            time.sleep(BACKOFF_BASE)
            continue

        for r in results:
            mid = r.get("mid", "")
            if not mid or mid in seen_mids:
                continue
            seen_mids.add(mid)
            candidates.append({
                "brand": brand_key,
                "mid": mid,
                "title": r.get("title", ""),
                "type": r.get("type", ""),
                "query_source": q,
            })

    return candidates


def validate_timeseries(pytrends, mid, title, retries=2):
    """
    Fetch 3-year weekly data for a single mid.
    Returns dict with avg, min, max, zero_weeks, total_weeks, continuous flag.
    """
    for attempt in range(retries + 1):
        try:
            pytrends.build_payload(
                kw_list=[mid],
                timeframe="2023-04-01 2026-04-01",
                geo="",
            )
            df = pytrends.interest_over_time()
            time.sleep(CALL_INTERVAL)

            if df.empty:
                return {
                    "avg": 0, "max": 0, "min": 0,
                    "zero_weeks": 0, "total_weeks": 0,
                    "continuous": False,
                    "status": "empty",
                }

            col = df.columns[0]
            vals = df[col].values
            total = len(vals)
            avg = float(vals.mean())
            mx = float(vals.max())
            mn = float(vals.min())
            zero_count = int((vals == 0).sum())

            # Continuity check: no stretch of 8+ consecutive zeros
            max_consecutive_zeros = 0
            current_zeros = 0
            for v in vals:
                if v == 0:
                    current_zeros += 1
                    max_consecutive_zeros = max(max_consecutive_zeros, current_zeros)
                else:
                    current_zeros = 0

            continuous = max_consecutive_zeros < 8

            # Check 2023 H1 data (first 26 weeks)
            early_avg = float(vals[:26].mean()) if len(vals) >= 26 else 0

            return {
                "avg": round(avg, 1),
                "max": round(mx, 1),
                "min": round(mn, 1),
                "zero_weeks": zero_count,
                "total_weeks": total,
                "max_consecutive_zeros": max_consecutive_zeros,
                "early_avg_2023h1": round(early_avg, 1),
                "continuous": continuous,
                "status": "ok",
            }

        except Exception as e:
            err_name = type(e).__name__
            if "TooManyRequests" in err_name or "429" in str(e):
                wait = BACKOFF_BASE * (2 ** attempt)
                print(f"    [RATE LIMITED] attempt {attempt+1}/{retries+1}, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    [ERROR] {err_name}: {e}")
                time.sleep(CALL_INTERVAL)

    return {
        "avg": 0, "max": 0, "min": 0,
        "zero_weeks": 0, "total_weeks": 0,
        "continuous": False,
        "status": "rate_limited",
    }


def rank_candidates(candidates_with_stats):
    """Rank candidates: continuous + highest avg + highest early_avg."""
    def score(c):
        s = c.get("stats", {})
        if s.get("status") != "ok":
            return -999
        cont_bonus = 100 if s.get("continuous") else 0
        return cont_bonus + s.get("avg", 0) + s.get("early_avg_2023h1", 0) * 0.5

    return sorted(candidates_with_stats, key=score, reverse=True)


def generate_report(all_results, mode="full"):
    """Generate markdown report."""
    lines = []
    lines.append("# MID Resolution Report")
    lines.append("")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    mode_label = {
        "full": "pytrends suggestions() + build_payload() validation",
        "skip_validation": "pytrends suggestions() only (validation skipped)",
    }
    lines.append(f"**Method:** {mode_label.get(mode, mode)}")
    lines.append("")

    for brand_key, data in all_results.items():
        is_core = data["is_core"]
        lines.append(f"## {brand_key} {'(core)' if is_core else '(extended)'}")
        lines.append("")

        candidates = data.get("candidates", [])
        if not candidates:
            lines.append("No candidates found.")
            lines.append("")
            continue

        lines.append("| Rank | Title | Type | MID | Avg | 2023H1 Avg | Zeros | Continuous | Status |")
        lines.append("|---|---|---|---|---|---|---|---|---|")

        ranked = rank_candidates(candidates)
        for i, c in enumerate(ranked):
            s = c.get("stats", {})
            lines.append(
                f"| {i+1} | {c['title']} | {c['type']} | `{c['mid']}` "
                f"| {s.get('avg', '-')} | {s.get('early_avg_2023h1', '-')} "
                f"| {s.get('zero_weeks', '-')}/{s.get('total_weeks', '-')} "
                f"| {'YES' if s.get('continuous') else 'NO'} | {s.get('status', '-')} |"
            )

        if ranked and ranked[0].get("stats", {}).get("status") == "ok":
            primary = ranked[0]
            lines.append("")
            lines.append(f"**Primary:** {primary['title']} ({primary['type']}) — `{primary['mid']}`")
            if len(ranked) > 1 and ranked[1].get("stats", {}).get("status") == "ok":
                fb = ranked[1]
                lines.append(f"**Fallback:** {fb['title']} ({fb['type']}) — `{fb['mid']}`")

        lines.append("")

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"\nReport saved: {REPORT_PATH}")


def update_brand_topics_csv(all_results):
    """Update brand_topics.csv with resolved mids."""
    rows = []
    for brand_key, data in all_results.items():
        ranked = rank_candidates(data.get("candidates", []))
        ok_candidates = [c for c in ranked if c.get("stats", {}).get("status") == "ok"]

        primary = ok_candidates[0] if len(ok_candidates) >= 1 else None
        fallback = ok_candidates[1] if len(ok_candidates) >= 2 else None

        rows.append({
            "brand": brand_key,
            "is_core": 1 if data["is_core"] else 0,
            "primary_label": f"{primary['title']} - {primary['type']}" if primary else "",
            "primary_type": primary["type"] if primary else "",
            "primary_mid": primary["mid"] if primary else "",
            "primary_avg": primary["stats"]["avg"] if primary else "",
            "primary_2023h1_avg": primary["stats"]["early_avg_2023h1"] if primary else "",
            "fallback_label": f"{fallback['title']} - {fallback['type']}" if fallback else "",
            "fallback_type": fallback["type"] if fallback else "",
            "fallback_mid": fallback["mid"] if fallback else "",
            "resolved_at": datetime.now().strftime("%Y-%m-%d"),
            "notes": "",
        })

    csv_path = os.path.join(OUTPUT_DIR, "brand_topics.csv")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fieldnames = [
        "brand", "is_core",
        "primary_label", "primary_type", "primary_mid",
        "primary_avg", "primary_2023h1_avg",
        "fallback_label", "fallback_type", "fallback_mid",
        "resolved_at", "notes",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated: {csv_path}")


def dry_run_probe(pytrends):
    """Single call to check if IP is blocked. Returns True if OK."""
    print("\n[DRY RUN] Probing Google Trends API...")
    print("  Testing suggestions('Nike')...")
    try:
        results = pytrends.suggestions(keyword="Nike")
        print(f"  suggestions() OK — {len(results)} results")
    except Exception as e:
        print(f"  suggestions() FAILED: {e}")
        print("  -> suggestions endpoint is blocked. Try switching network.")
        return False

    time.sleep(3)
    print("  Testing build_payload('Nike')...")
    try:
        pytrends.build_payload(kw_list=["Nike"], timeframe="today 3-m", geo="")
        df = pytrends.interest_over_time()
        if df.empty:
            print("  build_payload() returned empty (possibly soft-blocked)")
            print("  -> suggestions works but build_payload may be unreliable.")
            print("  -> Consider --skip-validation and manual verification.")
            return False
        print(f"  build_payload() OK — {df.shape[0]} rows")
        return True
    except Exception as e:
        err_name = type(e).__name__
        print(f"  build_payload() FAILED: {err_name}: {e}")
        if "TooManyRequests" in err_name or "429" in str(e):
            print("  -> build_payload is rate-limited. suggestions may still work.")
            print("  -> Use --skip-validation to collect mids without time-series check.")
        else:
            print("  -> Unexpected error. Try switching to hotspot.")
        return False


def main():
    args = parse_args()

    print("=" * 60)
    print("MID Resolution: Google Trends Entity/Topic Mapping")
    if args.dry_run:
        print("  Mode: DRY RUN (single probe)")
    elif args.skip_validation:
        print("  Mode: SKIP VALIDATION (suggestions only)")
    else:
        print("  Mode: FULL (suggestions + time-series validation)")
    print("=" * 60)

    pytrends = TrendReq(hl="ko", tz=540, retries=2, backoff_factor=1.0)

    # -- Dry run: probe and exit --
    if args.dry_run:
        ok = dry_run_probe(pytrends)
        print(f"\n{'='*60}")
        if ok:
            print("IP is CLEAR. Safe to run full resolution.")
            print("  python database/seed/resolve_brand_mids.py")
        else:
            print("IP is BLOCKED or LIMITED.")
            print("  Option 1: Switch to mobile hotspot, then re-run --dry-run")
            print("  Option 2: python database/seed/resolve_brand_mids.py --skip-validation")
        return

    all_results = {}
    skip_validation = args.skip_validation

    for brand_key, config in BRANDS.items():
        print(f"\n--- {brand_key} ---")
        is_core = config["is_core"]
        queries = config["queries"]

        # Step 1: Get suggestions
        print(f"  Step 1: Fetching suggestions...")
        candidates = get_suggestions(pytrends, brand_key, queries)
        print(f"  Found {len(candidates)} unique candidates:")
        for c in candidates:
            print(f"    - {c['title']} ({c['type']}) mid={c['mid']}")

        # Step 2: Validate time-series
        if skip_validation:
            print(f"  Step 2: SKIPPED (--skip-validation)")
            for c in candidates:
                c["stats"] = {"status": "skipped_by_flag"}
        elif is_core and candidates:
            print(f"  Step 2: Validating time-series...")
            for c in candidates:
                print(f"    Testing: {c['title']} ({c['type']})...")
                stats = validate_timeseries(pytrends, c["mid"], c["title"])
                c["stats"] = stats
                status = stats["status"]
                if status == "ok":
                    print(f"      avg={stats['avg']}, 2023H1={stats['early_avg_2023h1']}, "
                          f"zeros={stats['zero_weeks']}/{stats['total_weeks']}, "
                          f"continuous={'YES' if stats['continuous'] else 'NO'}")
                elif status == "rate_limited":
                    print(f"      RATE LIMITED - skipping remaining candidates for {brand_key}")
                    break
                else:
                    print(f"      {status}")
        elif not is_core:
            print(f"  Step 2: Skipped (extended brand, not core)")
            for c in candidates:
                c["stats"] = {"status": "skipped_extended"}
        else:
            print(f"  Step 2: No candidates to validate")

        all_results[brand_key] = {
            "is_core": is_core,
            "candidates": candidates,
        }

    # Step 3: Generate outputs
    print(f"\n{'='*60}")
    print("Generating outputs...")
    mode = "skip_validation" if skip_validation else "full"
    generate_report(all_results, mode=mode)
    update_brand_topics_csv(all_results)

    print(f"\n{'='*60}")
    print("Done. Next steps:")
    if skip_validation:
        print("  [!] Validation was skipped. MIDs collected but not ranked.")
        print("  1. Review docs/mid_resolution_report.md for candidate list")
        print("  2. Manually verify on trends.google.com (pick continuous Topic)")
        print("  3. Hand-edit database/seed/brand_topics.csv with selections")
        print("  4. Proceed with 9 CSV downloads per gtrends_download_protocol.md")
    else:
        print("  1. Review docs/mid_resolution_report.md")
        print("  2. Verify brand_topics.csv primary/fallback selections")
        print("  3. If rate-limited: manually verify on trends.google.com")
        print("  4. Proceed with 9 CSV downloads per gtrends_download_protocol.md")


if __name__ == "__main__":
    main()
