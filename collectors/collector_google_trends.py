"""
Stage 1 — Google Trends CSV Loader

Parses 8 manually-downloaded, stitched Google Trends CSV files and inserts
into raw.google_trends_raw via UPSERT.

pytrends was blocked during Stage 0 (Check 5), so Google Trends data is
collected as manual CSV downloads processed by stitch_gtrends.py.
This collector loads the final stitched CSVs, not raw chunks.

CSV matrix (Stage 0 confirmed):
  A1  brands_kr_web.csv          — brand,   korea,  web
  A2  brands_kr_youtube.csv      — brand,   korea,  youtube
  A3  brands_kr_shopping.csv     — brand,   korea,  shopping
  B1  brands_ww_web.csv          — brand,   global, web
  B2  brands_ww_youtube.csv      — brand,   global, youtube
  D1  products_kr_web.csv        — product, korea,  web
  D2  products_ww_web.csv        — product, global, web
  E   padding_competitive_kr.csv — apparel, korea,  web

UPSERT key: (layer, keyword, region, search_type, week_start)

Usage:
    python -m collectors.collector_google_trends
    python -m collectors.collector_google_trends --dry-run
    python -m collectors.collector_google_trends --file brands_kr_web.csv
"""

import argparse
import os
import sys
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from database.connection import get_conn

# Constants

GTRENDS_DIR = "data/raw/google_trends"

# Explicit config — no filename parsing ambiguity
CSV_CONFIG = {
    "brands_kr_web.csv":           {"layer": "brand",   "region": "korea",  "search_type": "web"},
    "brands_kr_youtube.csv":       {"layer": "brand",   "region": "korea",  "search_type": "youtube"},
    "brands_kr_shopping.csv":      {"layer": "brand",   "region": "korea",  "search_type": "shopping"},
    "brands_ww_web.csv":           {"layer": "brand",   "region": "global", "search_type": "web"},
    "brands_ww_youtube.csv":       {"layer": "brand",   "region": "global", "search_type": "youtube"},
    "products_kr_web.csv":         {"layer": "product", "region": "korea",  "search_type": "web"},
    "products_ww_web.csv":         {"layer": "product", "region": "global", "search_type": "web"},
    "padding_competitive_kr.csv":  {"layer": "apparel", "region": "korea",  "search_type": "web"},
}


# Schema migration (idempotent — adds UNIQUE constraint only)

ENSURE_CONSTRAINT_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'raw.google_trends_raw'::regclass
          AND conname  = 'uq_gtr_layer_kw_region_type_week'
    ) THEN
        ALTER TABLE raw.google_trends_raw
            ADD CONSTRAINT uq_gtr_layer_kw_region_type_week
            UNIQUE (layer, keyword, region, search_type, week_start);
    END IF;
END $$;
"""

UPSERT_SQL = """
INSERT INTO raw.google_trends_raw
    (layer, keyword, region, search_type, week_start, interest, collected_at)
VALUES (%s, %s, %s, %s, %s, %s, NOW())
ON CONFLICT ON CONSTRAINT uq_gtr_layer_kw_region_type_week
DO UPDATE SET
    interest     = EXCLUDED.interest,
    collected_at = NOW();
"""


def ensure_schema():
    """Add UNIQUE constraint if not present. Table assumed created by schema_init.sql."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ENSURE_CONSTRAINT_SQL)
        conn.commit()
        print("  Constraint verified: uq_gtr_layer_kw_region_type_week")


# CSV parsing

def parse_csv(filepath, layer, region, search_type):
    """Parse a stitched Google Trends CSV into row tuples for UPSERT.

    Handles:
      - '<1' values -> 0.5
      - Wide-to-long melt (date + keyword columns)
      - NaN/null drop
    """
    df = pd.read_csv(filepath)

    # Standardize date column
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col].str.strip(), errors="coerce")
    df = df.rename(columns={date_col: "date"})

    # Keyword columns = everything except date
    keyword_cols = [c for c in df.columns if c != "date"]

    # Handle '<1' values -> 0.5
    for col in keyword_cols:
        if df[col].dtype == object:
            df[col] = df[col].replace("<1", "0.5")
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Wide to long
    df_long = df.melt(
        id_vars=["date"],
        value_vars=keyword_cols,
        var_name="keyword",
        value_name="interest",
    )

    # Drop rows with no data
    df_long = df_long.dropna(subset=["date", "interest"])
    df_long = df_long.sort_values(["keyword", "date"]).reset_index(drop=True)

    # Build row tuples: (layer, keyword, region, search_type, week_start, interest)
    rows = []
    for _, row in df_long.iterrows():
        rows.append((
            layer,
            row["keyword"],
            region,
            search_type,
            row["date"].date(),
            float(row["interest"]),
        ))

    return rows


# DB insert

def insert_rows(rows):
    """Batch upsert rows into raw.google_trends_raw in one transaction."""
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

def collect_all(target_file=None, dry_run=False):
    """Parse CSV files and insert into DB."""
    total_rows = 0

    for filename, meta in CSV_CONFIG.items():
        if target_file and filename != target_file:
            continue

        filepath = os.path.join(GTRENDS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  [WARN] File not found: {filepath}")
            continue

        print(f"  Loading: {filename} (layer={meta['layer']}, region={meta['region']}, type={meta['search_type']})")
        rows = parse_csv(filepath, meta["layer"], meta["region"], meta["search_type"])

        # Summary stats
        keywords = sorted(set(r[1] for r in rows))
        weeks = sorted(set(r[4] for r in rows))
        print(f"    {len(rows)} rows, {len(keywords)} keywords, {len(weeks)} weeks")
        print(f"    Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
        print(f"    Period: {weeks[0]} ~ {weeks[-1]}")

        if dry_run:
            for r in rows[:3]:
                print(f"    [DRY-RUN] {r[4]} | {r[1]} | interest={r[5]}")
            if len(rows) > 3:
                print(f"    [DRY-RUN] ... and {len(rows) - 3} more")
        else:
            inserted = insert_rows(rows)
            total_rows += inserted
            print(f"    Upserted {inserted} rows")

    return total_rows


# CLI

def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Load stitched Google Trends CSVs into raw.google_trends_raw"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse CSVs but do not write to DB"
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="Load a single CSV file (e.g. brands_kr_web.csv)"
    )
    return parser.parse_args()


def main():
    """Entry point for Google Trends CSV loader."""
    args = parse_args()

    if args.file and args.file not in CSV_CONFIG:
        print(f"[ERROR] Unknown file: {args.file}")
        print(f"  Available: {', '.join(CSV_CONFIG.keys())}")
        sys.exit(1)

    print("Google Trends CSV Loader")
    print(f"  Source: {GTRENDS_DIR}/")
    print(f"  Files: {args.file or 'all 8'}")
    if args.dry_run:
        print("  Mode: DRY-RUN")

    if not args.dry_run:
        ensure_schema()

    total = collect_all(target_file=args.file, dry_run=args.dry_run)

    if args.dry_run:
        print("\nDry run complete. No rows written.")
    else:
        print(f"\nLoad complete. Total upserted: {total} rows")


if __name__ == "__main__":
    main()
