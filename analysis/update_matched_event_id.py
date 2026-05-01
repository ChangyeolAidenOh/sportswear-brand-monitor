"""
Stage 5 — Update mart.anomaly_log matched_event_id

Links anomaly rows to their primary matched event in staging.events_calendar.
Uses the same matching logic as anomaly_event_matching.py (strict window, brand rules).

Run AFTER load_events_calendar.py.

Usage:
    python analysis/update_matched_event_id.py
    python analysis/update_matched_event_id.py --dry-run
"""

import argparse
import os
import sys
from datetime import timedelta

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import get_conn


def fetch_events(conn):
    """Fetch events_calendar with IDs assigned by DB."""
    df = pd.read_sql("""
        SELECT id, event_date, event_end_date, brand, event_type, event_name
        FROM staging.events_calendar
        ORDER BY event_date;
    """, conn)
    df["event_date"] = pd.to_datetime(df["event_date"])
    df["event_end_date"] = pd.to_datetime(df["event_end_date"])
    print(f"Loaded {len(df)} events from staging.events_calendar")
    return df


def fetch_anomalies(conn):
    """Fetch all anomaly_log rows that could be matched."""
    df = pd.read_sql("""
        SELECT id, brand, detected_date, detection_method, description
        FROM mart.anomaly_log
        ORDER BY brand, detected_date;
    """, conn)
    df["detected_date"] = pd.to_datetime(df["detected_date"])
    print(f"Loaded {len(df)} anomaly rows from mart.anomaly_log")
    return df


def extract_region(description):
    """Extract region from description field."""
    if pd.isna(description):
        return None
    desc = str(description).lower()
    if "(korea)" in desc:
        return "korea"
    elif "(global)" in desc:
        return "global"
    return None


def match_anomaly(anom_row, events_df):
    """Match a single anomaly to its primary event. Returns event_id or None."""
    ws = anom_row["detected_date"]
    week_end = ws + timedelta(days=6)
    brand = anom_row["brand"]

    matches = []
    for _, evt in events_df.iterrows():
        # Window check
        if pd.notna(evt["event_end_date"]):
            in_window = evt["event_date"] <= week_end and evt["event_end_date"] >= ws
        else:
            in_window = ws <= evt["event_date"] <= week_end

        if not in_window:
            continue

        # Brand check
        evt_brand = evt["brand"]
        if pd.isna(evt_brand) or evt_brand == "":
            matches.append(evt)
        elif evt_brand == brand:
            matches.append(evt)

    if not matches:
        return None

    # Primary = closest date
    matches_df = pd.DataFrame(matches)
    matches_df["date_diff"] = (matches_df["event_date"] - ws).abs()
    matches_df = matches_df.sort_values("date_diff")
    return int(matches_df.iloc[0]["id"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with get_conn() as conn:
        events = fetch_events(conn)
        anomalies = fetch_anomalies(conn)

        # Clear existing matched_event_id
        with conn.cursor() as cur:
            cur.execute("UPDATE mart.anomaly_log SET matched_event_id = NULL;")
            print(f"Cleared {cur.rowcount} existing matched_event_id values")

        # Match each anomaly
        matched_count = 0
        updates = []

        for _, anom in anomalies.iterrows():
            event_id = match_anomaly(anom, events)
            if event_id is not None:
                updates.append((event_id, int(anom["id"])))
                matched_count += 1

        print(f"\nMatched: {matched_count} / {len(anomalies)} anomalies")

        # Execute updates
        if updates:
            with conn.cursor() as cur:
                for event_id, anom_id in updates:
                    cur.execute("""
                        UPDATE mart.anomaly_log
                        SET matched_event_id = %s
                        WHERE id = %s;
                    """, (event_id, anom_id))

        if args.dry_run:
            conn.rollback()
            print("[DRY RUN] Rolled back")
        else:
            conn.commit()
            print(f"Updated {matched_count} matched_event_id values")

        # Summary by method
        summary = pd.read_sql("""
            SELECT detection_method,
                   COUNT(*) AS total,
                   COUNT(matched_event_id) AS matched
            FROM mart.anomaly_log
            GROUP BY detection_method
            ORDER BY detection_method;
        """, conn)
        print(f"\nMatching summary by method:\n{summary.to_string(index=False)}")


if __name__ == "__main__":
    main()
