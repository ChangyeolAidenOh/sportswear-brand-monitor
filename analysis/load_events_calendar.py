"""
Stage 5 — Load events_calendar.csv into staging.events_calendar

Reads data/events_calendar.csv and INSERTs into the staging table.
Idempotent: clears existing rows before insert.

Usage:
    python analysis/load_events_calendar.py
    python analysis/load_events_calendar.py --dry-run
"""

import argparse
import os
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import get_conn

CSV_PATH = "data/events_calendar.csv"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(CSV_PATH)
    df["event_date"] = pd.to_datetime(df["event_date"])
    df["event_end_date"] = pd.to_datetime(df["event_end_date"])
    print(f"Loaded {len(df)} events from {CSV_PATH}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clear existing
            cur.execute("DELETE FROM staging.events_calendar;")
            deleted = cur.rowcount
            if deleted > 0:
                print(f"Cleared {deleted} existing rows")

            for _, row in df.iterrows():
                brand = row["brand"] if pd.notna(row["brand"]) and row["brand"] != "" else None
                event_end = row["event_end_date"].date() if pd.notna(row["event_end_date"]) else None
                event_origin = row["event_origin"] if "event_origin" in df.columns and pd.notna(row["event_origin"]) else None

                cur.execute("""
                    INSERT INTO staging.events_calendar
                        (event_date, event_end_date, brand, event_type,
                         event_name, description, impact_expected, source, event_origin)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    row["event_date"].date(),
                    event_end,
                    brand,
                    row["event_type"],
                    row["event_name"],
                    row["description"],
                    row["impact_expected"],
                    row["source"],
                    event_origin,
                ))

            if args.dry_run:
                conn.rollback()
                print(f"[DRY RUN] Would insert {len(df)} rows")
            else:
                conn.commit()
                print(f"Inserted {len(df)} rows into staging.events_calendar")


if __name__ == "__main__":
    main()
