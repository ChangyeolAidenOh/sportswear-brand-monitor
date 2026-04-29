"""
Stage 1 — Naver DataLab Search Trend Collector

Fetches weekly search trend data from Naver DataLab API for 4 keyword groups
(each called independently for separate scale normalization) and inserts
into raw.naver_datalab_raw via UPSERT.

Groups:
  1. brand        — 나이키, 아디다스, 푸마, 뉴발란스
  2. nb_product   — 뉴발란스 530, 뉴발란스 992, 뉴발란스 574, 뉴발란스 2002R
  3. nb_social    — 뉴발란스 인스타, 뉴발란스 틱톡, 뉴발란스 유튜브
  4. nb_channel   — 뉴발란스 공식몰, 뉴발란스 무신사, 뉴발란스 쿠팡, 뉴발란스 크림

Note: Groups 2-4 include keywords below Stage 0 viability threshold
(e.g. 2002R avg 3.4, 무신사 avg 0.5). Retained in raw for completeness;
staging.search_weekly applies is_viable filter.

Demographic filters (device/gender/age_group) are not used — all calls
fetch aggregate totals. If demographic breakdowns are needed later,
a separate collector + raw.naver_datalab_demographic_raw table is the plan.

UPSERT key: (source_type, keyword_group, keyword, period_start)

Usage:
    python -m collectors.collector_naver_datalab
    python -m collectors.collector_naver_datalab --dry-run
    python -m collectors.collector_naver_datalab --start-date 2024-01-01
"""

# stdlib
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

# third-party
import requests
from dotenv import load_dotenv

load_dotenv()

# local
from database.connection import get_conn

# ================================================================
# Constants
# ================================================================

NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_HEADERS = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    "Content-Type": "application/json",
}

CALL_INTERVAL = 5
BACKOFF_BASE = 10
MAX_RETRIES = 3

# Each group called independently for separate scale normalization.
# Naver DataLab API: keywords within a keywordGroup are summed;
# multiple keywordGroups in one call share the same 0-100 scale.
KEYWORD_GROUPS = {
    "brand": [
        {"groupName": "나이키",   "keywords": ["나이키"]},
        {"groupName": "아디다스", "keywords": ["아디다스"]},
        {"groupName": "푸마",     "keywords": ["푸마"]},
        {"groupName": "뉴발란스", "keywords": ["뉴발란스"]},
    ],
    "nb_product": [
        {"groupName": "뉴발란스 530",   "keywords": ["뉴발란스 530", "뉴발란스530"]},
        {"groupName": "뉴발란스 992",   "keywords": ["뉴발란스 992", "뉴발란스992"]},
        {"groupName": "뉴발란스 574",   "keywords": ["뉴발란스 574", "뉴발란스574"]},
        {"groupName": "뉴발란스 2002R", "keywords": ["뉴발란스 2002R", "뉴발란스2002R"]},
    ],
    "nb_social": [
        {"groupName": "뉴발란스 인스타", "keywords": ["뉴발란스 인스타", "뉴발란스 인스타그램"]},
        {"groupName": "뉴발란스 틱톡",   "keywords": ["뉴발란스 틱톡"]},
        {"groupName": "뉴발란스 유튜브", "keywords": ["뉴발란스 유튜브"]},
    ],
    "nb_channel": [
        {"groupName": "뉴발란스 공식몰", "keywords": ["뉴발란스 공식몰", "뉴발란스 자사몰", "뉴발란스 공홈"]},
        {"groupName": "뉴발란스 무신사",  "keywords": ["뉴발란스 무신사"]},
        {"groupName": "뉴발란스 쿠팡",    "keywords": ["뉴발란스 쿠팡"]},
        {"groupName": "뉴발란스 크림",    "keywords": ["뉴발란스 크림"]},
    ],
}

DEFAULT_START_DATE = "2024-04-01"


# ================================================================
# Schema migration (idempotent — adds UNIQUE constraint only)
# ================================================================

ENSURE_CONSTRAINT_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'raw.naver_datalab_raw'::regclass
          AND conname  = 'uq_ndl_type_group_kw_period'
    ) THEN
        ALTER TABLE raw.naver_datalab_raw
            ADD CONSTRAINT uq_ndl_type_group_kw_period
            UNIQUE (source_type, keyword_group, keyword, period_start);
    END IF;
END $$;
"""

UPSERT_SQL = """
INSERT INTO raw.naver_datalab_raw
    (source_type, keyword_group, keyword, period_start, period_end,
     ratio, device, gender, age_group, category, raw_json, collected_at)
VALUES
    (%s, %s, %s, %s, %s,
     %s, NULL, NULL, NULL, NULL, %s, NOW())
ON CONFLICT ON CONSTRAINT uq_ndl_type_group_kw_period
DO UPDATE SET
    period_end   = EXCLUDED.period_end,
    ratio        = EXCLUDED.ratio,
    raw_json     = EXCLUDED.raw_json,
    collected_at = NOW();
"""


def ensure_schema():
    """Add UNIQUE constraint if not present. Table assumed created by schema_init.sql."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ENSURE_CONSTRAINT_SQL)
        conn.commit()
        print("  Constraint verified: uq_ndl_type_group_kw_period")


# ================================================================
# API fetch
# ================================================================

def fetch_naver_single_group(group_id, keyword_groups, start_date, end_date):
    """Fetch a single keyword group from Naver DataLab (independent scale).

    Returns list of row tuples matching UPSERT_SQL parameter order,
    or None on failure.
    """
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "week",
        "keywordGroups": keyword_groups,
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(
                NAVER_DATALAB_URL,
                headers=NAVER_HEADERS,
                json=body,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "N/A"
            if status == 429 and attempt < MAX_RETRIES:
                wait = BACKOFF_BASE * (2 ** attempt)
                print(f"    [RATE LIMITED] attempt {attempt+1}/{MAX_RETRIES+1}, waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"  [ERROR] API HTTP {status}: {e}")
            if e.response:
                print(f"  [ERROR] Response: {e.response.text[:500]}")
            return None
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
            return None

    # Parse response into row tuples
    # Column order: source_type, keyword_group, keyword,
    #               period_start, period_end, ratio, raw_json
    rows = []
    raw_json_str = json.dumps(data, ensure_ascii=False)

    for result in data.get("results", []):
        kw_name = result["title"]
        for point in result.get("data", []):
            period_start = datetime.strptime(point["period"], "%Y-%m-%d").date()
            period_end = period_start + timedelta(days=6)
            rows.append((
                "search_trend",     # source_type
                group_id,           # keyword_group
                kw_name,            # keyword
                period_start,       # period_start
                period_end,         # period_end
                point["ratio"],     # ratio
                raw_json_str,       # raw_json
            ))

    return rows


# ================================================================
# DB insert (single transaction per group)
# ================================================================

def insert_rows(rows):
    """Batch upsert rows into raw.naver_datalab_raw in one transaction."""
    if not rows:
        return 0
    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.executemany(UPSERT_SQL, rows)
            conn.commit()
            return len(rows)
        except Exception as e:
            conn.rollback()
            print(f"  [ERROR] DB insert failed: {e}")
            return 0


# ================================================================
# Main collection logic
# ================================================================

def collect_all(start_date, end_date, dry_run=False):
    """Fetch all 4 keyword groups and insert into DB."""
    total_rows = 0
    today = datetime.now().date()

    for group_id, kw_groups in KEYWORD_GROUPS.items():
        print(f"  Fetching group: {group_id} ({len(kw_groups)} keyword sets)")
        rows = fetch_naver_single_group(group_id, kw_groups, start_date, end_date)

        if rows is None:
            print(f"  [WARN] Skipping group '{group_id}' due to API failure")
            continue

        # Count incomplete weeks (period_end > today)
        incomplete_count = sum(1 for r in rows if r[4] > today)
        print(f"    Received {len(rows)} rows ({incomplete_count} incomplete week)")

        if dry_run:
            for r in rows[:3]:
                print(f"    [DRY-RUN] {r[3]} ~ {r[4]} | {r[2]} | ratio={r[5]}")
            if len(rows) > 3:
                print(f"    [DRY-RUN] ... and {len(rows) - 3} more")
        else:
            inserted = insert_rows(rows)
            total_rows += inserted
            print(f"    Upserted {inserted} rows")

        time.sleep(CALL_INTERVAL)

    return total_rows


# ================================================================
# CLI
# ================================================================

def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Collect Naver DataLab search trends into raw.naver_datalab_raw"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch from API but do not write to DB"
    )
    parser.add_argument(
        "--start-date", type=str, default=DEFAULT_START_DATE,
        help=f"Start date YYYY-MM-DD (default: {DEFAULT_START_DATE})"
    )
    parser.add_argument(
        "--end-date", type=str, default=None,
        help="End date YYYY-MM-DD (default: today)"
    )
    return parser.parse_args()


def main():
    """Entry point for Naver DataLab collector."""
    args = parse_args()

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[ERROR] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET not set in .env")
        sys.exit(1)

    start_date = args.start_date
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")

    print("Naver DataLab Collector")
    print(f"  Period: {start_date} ~ {end_date}")
    print(f"  Groups: {list(KEYWORD_GROUPS.keys())}")
    if args.dry_run:
        print("  Mode: DRY-RUN")

    if not args.dry_run:
        ensure_schema()

    total = collect_all(start_date, end_date, dry_run=args.dry_run)

    if args.dry_run:
        print("\nDry run complete. No rows written.")
    else:
        print(f"\nCollection complete. Total upserted: {total} rows")


if __name__ == "__main__":
    main()
