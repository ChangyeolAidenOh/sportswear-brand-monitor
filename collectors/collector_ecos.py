"""
Stage 1 — ECOS (Bank of Korea) Macro Indicator Collector

Fetches monthly macro indicators from Bank of Korea ECOS API
and inserts into raw.ecos_raw via UPSERT.

Indicators:
  - CSI (소비자심리지수): stat_code 085Y003
  - Additional indicators can be added to INDICATORS config.

ECOS API docs: https://ecos.bok.or.kr/api/#/

UPSERT key: (stat_code, item_code, period)

Usage:
    python -m collectors.collector_ecos
    python -m collectors.collector_ecos --dry-run
    python -m collectors.collector_ecos --start-period 202201
"""

import argparse
import os
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

from database.connection import get_conn

# Constants

ECOS_API_KEY = os.getenv("ECOS_API_KEY")
ECOS_BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"

CALL_INTERVAL = 1

# Indicator config: each entry defines a stat to collect
# stat_code, item_code, and a human-readable name for logging
INDICATORS = [
    {
        "stat_code": "511Y002",
        "item_code": "FME",
        "item_code2": "99988",
        "name": "CSI (소비자심리지수)",
    },
]

DEFAULT_START_PERIOD = "202201"  # Jan 2022


# Schema migration (idempotent)

ENSURE_CONSTRAINT_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'raw.ecos_raw'::regclass
          AND conname  = 'uq_ecos_stat_item_period'
    ) THEN
        ALTER TABLE raw.ecos_raw
            ADD CONSTRAINT uq_ecos_stat_item_period
            UNIQUE (stat_code, item_code, period);
    END IF;
END $$;
"""

UPSERT_SQL = """
INSERT INTO raw.ecos_raw
    (stat_code, stat_name, item_code, item_name, period, value, unit, collected_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
ON CONFLICT ON CONSTRAINT uq_ecos_stat_item_period
DO UPDATE SET
    stat_name    = EXCLUDED.stat_name,
    item_name    = EXCLUDED.item_name,
    value        = EXCLUDED.value,
    unit         = EXCLUDED.unit,
    collected_at = NOW();
"""


def ensure_schema():
    """Add UNIQUE constraint if not present."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ENSURE_CONSTRAINT_SQL)
        conn.commit()
        print("  Constraint verified: uq_ecos_stat_item_period")


# ECOS API fetch

def fetch_ecos_indicator(stat_code, item_code, item_code2, start_period, end_period):
    """Fetch monthly data from ECOS API for a single indicator.

    API URL format:
      /StatisticSearch/{key}/json/kr/{start_idx}/{end_idx}/{stat_code}/M/{start}/{end}/{item_code}

    Returns list of row tuples or None on failure.
    """
    url = (
        f"{ECOS_BASE_URL}/{ECOS_API_KEY}/json/kr/1/1000"
        f"/{stat_code}/M/{start_period}/{end_period}/{item_code}/{item_code2}"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"  [ERROR] ECOS API HTTP {e.response.status_code}: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] ECOS API call failed: {e}")
        return None

    # Check for API-level error
    if "StatisticSearch" not in data:
        error = data.get("RESULT", {})
        print(f"  [ERROR] ECOS API error: {error.get('MESSAGE', 'Unknown')}")
        return None

    search_result = data["StatisticSearch"]
    raw_rows = search_result.get("row", [])

    rows = []
    for r in raw_rows:
        value_str = r.get("DATA_VALUE", "")
        try:
            value = float(value_str) if value_str else None
        except ValueError:
            value = None

        # Convert TIME "202401" → "2024-01" for period column
        time_str = r.get("TIME", "")
        if len(time_str) == 6:
            period = f"{time_str[:4]}-{time_str[4:]}"
        else:
            period = time_str

        rows.append((
            r.get("STAT_CODE", stat_code),
            r.get("STAT_NAME", ""),
            r.get("ITEM_CODE1", item_code),
            r.get("ITEM_NAME1", ""),
            period,
            value,
            r.get("UNIT_NAME", ""),
        ))

    return rows


# DB insert

def insert_rows(rows):
    """Batch upsert rows into raw.ecos_raw in one transaction."""
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


# Main collection logic

def collect_all(start_period, end_period, dry_run=False):
    """Fetch all configured ECOS indicators and insert into DB."""
    total_rows = 0

    for indicator in INDICATORS:
        stat_code = indicator["stat_code"]
        item_code = indicator["item_code"]
        name = indicator["name"]

        print(f"  Fetching: {name} ({stat_code}/{item_code})")
        item_code2 = indicator["item_code2"]
        rows = fetch_ecos_indicator(stat_code, item_code, item_code2, start_period, end_period)

        if rows is None:
            print(f"  [WARN] Skipping {name} due to API failure")
            continue

        print(f"    Received {len(rows)} months")
        if rows:
            print(f"    Period: {rows[0][4]} ~ {rows[-1][4]}")

        if dry_run:
            for r in rows[:3]:
                print(f"    [DRY-RUN] {r[4]} | {r[3]} | value={r[5]} {r[6]}")
            if len(rows) > 3:
                print(f"    [DRY-RUN] ... and {len(rows) - 3} more")
        else:
            inserted = insert_rows(rows)
            total_rows += inserted
            print(f"    Upserted {inserted} rows")

        time.sleep(CALL_INTERVAL)

    return total_rows


# CLI

def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Collect ECOS macro indicators into raw.ecos_raw"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch from API but do not write to DB"
    )
    parser.add_argument(
        "--start-period", type=str, default=DEFAULT_START_PERIOD,
        help=f"Start period YYYYMM (default: {DEFAULT_START_PERIOD})"
    )
    parser.add_argument(
        "--end-period", type=str, default=None,
        help="End period YYYYMM (default: current month)"
    )
    return parser.parse_args()


def main():
    """Entry point for ECOS collector."""
    args = parse_args()

    if not ECOS_API_KEY:
        print("[ERROR] ECOS_API_KEY not set in .env")
        sys.exit(1)

    start_period = args.start_period
    end_period = args.end_period or datetime.now().strftime("%Y%m")

    indicator_names = [i["name"] for i in INDICATORS]
    print("ECOS Collector")
    print(f"  Period: {start_period} ~ {end_period}")
    print(f"  Indicators: {', '.join(indicator_names)}")
    if args.dry_run:
        print("  Mode: DRY-RUN")

    if not args.dry_run:
        ensure_schema()

    total = collect_all(start_period, end_period, dry_run=args.dry_run)

    if args.dry_run:
        print("\nDry run complete. No rows written.")
    else:
        print(f"\nCollection complete. Total upserted: {total} rows")


if __name__ == "__main__":
    main()
