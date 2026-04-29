"""
Stage 1 — Financials CSV Seed Loader

Loads manually curated financial data from CSV into raw.financials_raw
via UPSERT. Covers Nike (SEC 10-Q/10-K), Adidas/Puma (IR reports),
NB global (CEO statement), and NB Korea (DART + licensee PR).

Source tier system:
  Tier 1 — Primary disclosure (SEC, DART, IR annual report)
  Tier 2 — Licensee official PR
  Tier 3 — Credit rating agency
  Tier 4 — Media / CEO statement

UPSERT key: (brand, fiscal_period, metric_name, source_type)
Expanded key allows multiple estimates per metric at different tiers.

Usage:
    python -m collectors.collector_financials
    python -m collectors.collector_financials --dry-run
    python -m collectors.collector_financials --csv-path data/raw/financials/custom.csv
"""

# stdlib
import argparse
import os
import re
import sys

# third-party
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# local
from database.connection import get_conn

# ================================================================
# Constants
# ================================================================

DEFAULT_CSV_PATH = "data/raw/financials/financials_seed.csv"

VALID_BRANDS = {"nike", "adidas", "puma", "new_balance"}
FISCAL_PERIOD_RE = re.compile(r"^FY\d{4}(-Q[1-4]|-H[12])?$")
CURRENCY_RE = re.compile(r"^[A-Z]{3,5}$")  # USD, EUR, KRW, RATIO

SOURCE_TIER_MAP = {
    # Tier 1 — Primary disclosure
    "sec_10q": 1,
    "sec_10k": 1,
    "ir_report": 1,
    "dart_audit": 1,
    "dart_quarterly": 1,
    # Tier 2 — Licensee official
    "licensee_official_pr": 2,
    # Tier 3 — Credit rating
    "credit_rating": 3,
    # Tier 4 — Media/statement
    "ceo_statement": 4,
    "news_attribution": 4,
}


# ================================================================
# Schema migration (idempotent)
# ================================================================

ENSURE_SCHEMA_SQL = """
-- Add source_tier if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'raw'
          AND table_name   = 'financials_raw'
          AND column_name  = 'source_tier'
    ) THEN
        ALTER TABLE raw.financials_raw
            ADD COLUMN source_tier SMALLINT NOT NULL DEFAULT 4
            CHECK (source_tier BETWEEN 1 AND 4);
    END IF;
END $$;

-- Add note if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'raw'
          AND table_name   = 'financials_raw'
          AND column_name  = 'note'
    ) THEN
        ALTER TABLE raw.financials_raw ADD COLUMN note TEXT;
    END IF;
END $$;

-- Ensure 4-column UNIQUE (brand, fiscal_period, metric_name, source_type)
DO $$
DECLARE
    old_constraint TEXT;
BEGIN
    -- Drop old 3-col constraint if exists
    SELECT conname INTO old_constraint
    FROM pg_constraint
    WHERE conrelid = 'raw.financials_raw'::regclass
      AND conname  = 'uq_fin_brand_period_metric';

    IF old_constraint IS NOT NULL THEN
        EXECUTE format(
            'ALTER TABLE raw.financials_raw DROP CONSTRAINT %I',
            old_constraint
        );
    END IF;

    -- Add 4-col constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'raw.financials_raw'::regclass
          AND conname  = 'uq_fin_brand_period_metric_source'
    ) THEN
        ALTER TABLE raw.financials_raw
            ADD CONSTRAINT uq_fin_brand_period_metric_source
            UNIQUE (brand, fiscal_period, metric_name, source_type);
    END IF;
END $$;
"""

UPSERT_SQL = """
INSERT INTO raw.financials_raw
    (brand, fiscal_period, metric_name, value, currency,
     source_url, source_type, source_tier, note, collected_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
ON CONFLICT ON CONSTRAINT uq_fin_brand_period_metric_source
DO UPDATE SET
    value        = EXCLUDED.value,
    currency     = EXCLUDED.currency,
    source_url   = EXCLUDED.source_url,
    source_tier  = EXCLUDED.source_tier,
    note         = EXCLUDED.note,
    collected_at = NOW();
"""


def ensure_schema():
    """Add governance columns and UNIQUE constraint if not present."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ENSURE_SCHEMA_SQL)
        conn.commit()
        print("  Schema verified: source_tier + note + uq_fin_brand_period_metric_source")


# ================================================================
# CSV loading and validation
# ================================================================

def load_seed_csv(csv_path):
    """Load financials seed CSV into DataFrame."""
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV not found: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path, dtype=str)

    # note column is optional — fill with empty string if missing
    if "note" not in df.columns:
        df["note"] = ""
    df["note"] = df["note"].fillna("")

    required_cols = {"brand", "fiscal_period", "metric_name", "value",
                     "currency", "source_url", "source_type"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"[ERROR] Missing columns: {missing}")
        sys.exit(1)

    return df


def check_brand_enum(df):
    """Validate brand values against brand_enum."""
    invalid = df[~df["brand"].isin(VALID_BRANDS)]
    if len(invalid) > 0:
        for _, row in invalid.iterrows():
            print(f"  [ERROR] Invalid brand '{row['brand']}' at {row['fiscal_period']}/{row['metric_name']}")
        return False
    return True


def check_fiscal_period_format(df):
    """Validate fiscal_period matches FY naming convention."""
    invalid = df[~df["fiscal_period"].apply(lambda x: bool(FISCAL_PERIOD_RE.match(str(x))))]
    if len(invalid) > 0:
        for _, row in invalid.iterrows():
            print(f"  [ERROR] Invalid fiscal_period '{row['fiscal_period']}'")
        return False
    return True


def check_currency_iso(df):
    """Validate currency is 3-5 letter code (USD, EUR, KRW, RATIO)."""
    invalid = df[~df["currency"].apply(lambda x: bool(CURRENCY_RE.match(str(x))))]
    if len(invalid) > 0:
        for _, row in invalid.iterrows():
            print(f"  [ERROR] Invalid currency '{row['currency']}' at {row['brand']}/{row['fiscal_period']}")
        return False
    return True


def check_source_url(df):
    """Validate source_url is not empty."""
    empty = df[df["source_url"].isna() | (df["source_url"].str.strip() == "")]
    if len(empty) > 0:
        for _, row in empty.iterrows():
            print(f"  [ERROR] Empty source_url at {row['brand']}/{row['fiscal_period']}/{row['metric_name']}")
        return False
    return True


def check_no_null_values(df):
    """Validate value column has no NULLs."""
    null_vals = df[df["value"].isna() | (df["value"].str.strip() == "")]
    if len(null_vals) > 0:
        for _, row in null_vals.iterrows():
            print(f"  [ERROR] NULL value at {row['brand']}/{row['fiscal_period']}/{row['metric_name']}")
        return False
    return True


def check_source_type(df):
    """Validate source_type is in SOURCE_TIER_MAP."""
    invalid = df[~df["source_type"].isin(SOURCE_TIER_MAP.keys())]
    if len(invalid) > 0:
        for _, row in invalid.iterrows():
            print(f"  [ERROR] Unknown source_type '{row['source_type']}' at {row['brand']}/{row['fiscal_period']}")
            print(f"          Valid: {list(SOURCE_TIER_MAP.keys())}")
        return False
    return True


def validate_rows(df):
    """Run all validation checks. Returns True if all pass."""
    checks = [
        check_brand_enum,
        check_fiscal_period_format,
        check_currency_iso,
        check_source_url,
        check_no_null_values,
        check_source_type,
    ]

    all_pass = True
    for check_fn in checks:
        if not check_fn(df):
            all_pass = False

    return all_pass


# ================================================================
# DB insert
# ================================================================

def upsert_to_db(df):
    """Batch upsert validated rows with auto-assigned source_tier."""
    rows = []
    for _, r in df.iterrows():
        tier = SOURCE_TIER_MAP.get(r["source_type"], 4)
        rows.append((
            r["brand"],
            r["fiscal_period"],
            r["metric_name"],
            float(r["value"]),
            r["currency"],
            r["source_url"],
            r["source_type"],
            tier,
            r.get("note", ""),
        ))

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
            print(f"  [ERROR] DB upsert failed: {e}")
            return 0


# ================================================================
# CLI
# ================================================================

def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Load financials seed CSV into raw.financials_raw"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate CSV but do not write to DB"
    )
    parser.add_argument(
        "--csv-path", type=str, default=DEFAULT_CSV_PATH,
        help=f"Path to seed CSV (default: {DEFAULT_CSV_PATH})"
    )
    return parser.parse_args()


def main():
    """Entry point for financials seed loader."""
    args = parse_args()

    print("Financials Seed Loader")
    print(f"  CSV: {args.csv_path}")
    if args.dry_run:
        print("  Mode: DRY-RUN")

    df = load_seed_csv(args.csv_path)
    print(f"  Loaded {len(df)} rows")

    print("  Validating...")
    if not validate_rows(df):
        print("\n[ERROR] Validation failed. Fix CSV and retry.")
        sys.exit(1)
    print("  Validation passed")

    # Summary by brand and tier
    for brand in sorted(df["brand"].unique()):
        brand_df = df[df["brand"] == brand]
        tiers = [SOURCE_TIER_MAP.get(st, 4) for st in brand_df["source_type"]]
        tier_str = ",".join(sorted(set(f"T{t}" for t in tiers)))
        periods = sorted(brand_df["fiscal_period"].unique())
        print(f"    {brand}: {len(brand_df)} rows, {tier_str}, {periods[0]} ~ {periods[-1]}")

    if args.dry_run:
        for _, r in df.head(5).iterrows():
            tier = SOURCE_TIER_MAP.get(r["source_type"], 4)
            print(f"    [DRY-RUN] {r['brand']} | {r['fiscal_period']} | {r['metric_name']} | {r['value']} {r['currency']} | T{tier}")
        if len(df) > 5:
            print(f"    [DRY-RUN] ... and {len(df) - 5} more")
        print("\nDry run complete. No rows written.")
    else:
        ensure_schema()
        inserted = upsert_to_db(df)
        print(f"\nLoad complete. Total upserted: {inserted} rows")


if __name__ == "__main__":
    main()
