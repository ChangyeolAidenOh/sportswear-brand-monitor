"""
Mart table query functions for dashboard data layer.
Each function queries PostgreSQL or falls back to CSV based on config.
Usage: from dashboard.data.queries import fetch_weekly_search_index
"""

# stdlib
import os

# third-party
import pandas as pd
import psycopg2

# local
from dashboard.config import DB_CONFIG, CSV_DIR, USE_CSV_FALLBACK


# ================================================================
# Connection helper
# ================================================================
def get_connection():
    """Return a psycopg2 connection using DB_CONFIG."""
    return psycopg2.connect(**DB_CONFIG)


def _read_csv_fallback(filename):
    """Read a CSV file from data/exports/ directory."""
    path = os.path.join(CSV_DIR, filename)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, parse_dates=True)


def _query_or_csv(query, csv_filename, parse_dates=None):
    """Execute SQL query or fall back to CSV. Returns DataFrame or None."""
    if USE_CSV_FALLBACK:
        return _read_csv_fallback(csv_filename)
    try:
        conn = get_connection()
        df = pd.read_sql(query, conn, parse_dates=parse_dates)
        conn.close()
        return df
    except Exception as e:
        print(f"DB query failed: {e}")
        return _read_csv_fallback(csv_filename)


# ================================================================
# KPI 1, 2, 3: mart.brand_kpi
# ================================================================
WEEKLY_SEARCH_SQL = """
SELECT
    week_start,
    brand,
    region,
    keyword_group,
    search_index,
    sov_pct,
    wow_change,
    mom_change,
    yoy_change
FROM mart.brand_kpi
ORDER BY week_start, brand, region
"""


def fetch_weekly_search_index():
    """Fetch weekly search index data (KPI 1, 2, 3)."""
    return _query_or_csv(
        WEEKLY_SEARCH_SQL,
        "brand_kpi_weekly.csv",
        parse_dates=["week_start"],
    )


# ================================================================
# KPI 4, 5: mart.sentiment_quarterly
# ================================================================
SENTIMENT_SQL = """
SELECT *
FROM mart.sentiment_quarterly
ORDER BY quarter, brand
"""


def fetch_sentiment_quarterly():
    """Fetch quarterly sentiment data (KPI 4, 5)."""
    return _query_or_csv(
        SENTIMENT_SQL,
        "sentiment_quarterly.csv",
    )


# ================================================================
# KPI 6, 10: mart.csi_macro
# ================================================================
CSI_MACRO_SQL = """
SELECT *
FROM mart.csi_macro
ORDER BY date
"""


def fetch_csi_macro():
    """Fetch CSI macro data (KPI 6, 10)."""
    return _query_or_csv(
        CSI_MACRO_SQL,
        "csi_macro.csv",
        parse_dates=["date"],
    )


# ================================================================
# KPI 7: mart.korea_global_lag (Migration 011 sign-corrected)
# ================================================================
KOREA_GLOBAL_LAG_SQL = """
SELECT *
FROM mart.korea_global_lag
ORDER BY method, deseason
"""


def fetch_korea_global_lag():
    """Fetch Korea-Global lag data, sign-corrected (KPI 7)."""
    return _query_or_csv(
        KOREA_GLOBAL_LAG_SQL,
        "korea_global_lag.csv",
    )


# ================================================================
# KPI 8: staging.events_calendar
# ================================================================
EVENTS_CALENDAR_SQL = """
SELECT *
FROM staging.events_calendar
ORDER BY event_date
"""


def fetch_events_calendar():
    """Fetch events calendar for event stacking analysis (KPI 8)."""
    return _query_or_csv(
        EVENTS_CALENDAR_SQL,
        "events_calendar.csv",
        parse_dates=["event_date"],
    )


# ================================================================
# KPI 9: mart.anomaly_log
# ================================================================
ANOMALY_LOG_SQL = """
SELECT *
FROM mart.anomaly_log
ORDER BY week_start, brand, detection_method
"""


def fetch_anomaly_log():
    """Fetch anomaly detection log for 3-way comparison (KPI 9)."""
    return _query_or_csv(
        ANOMALY_LOG_SQL,
        "anomaly_log.csv",
        parse_dates=["week_start"],
    )


# ================================================================
# KPI 11: mart.forecast_results (created in Stage 8.5 if absent)
# ================================================================
FORECAST_SQL = """
SELECT *
FROM mart.forecast_results
ORDER BY ds, region
"""


def fetch_forecast_results():
    """Fetch Prophet forecast results (KPI 11). May not exist until Stage 8.5."""
    return _query_or_csv(
        FORECAST_SQL,
        "forecast_results.csv",
        parse_dates=["ds"],
    )


# ================================================================
# SoV analysis (Tab 1, Tab 3)
# ================================================================
SOV_SQL = """
SELECT *
FROM mart.sov_analysis
ORDER BY week_start, brand, region
"""


def fetch_sov_analysis():
    """Fetch share-of-voice analysis data."""
    return _query_or_csv(
        SOV_SQL,
        "sov_analysis.csv",
        parse_dates=["week_start"],
    )


# ================================================================
# Seasonal classifier (Tab 2)
# ================================================================
SEASONAL_SQL = """
SELECT *
FROM mart.seasonal_phase
ORDER BY week_start
"""


def fetch_seasonal_phase():
    """Fetch seasonal phase classification data."""
    return _query_or_csv(
        SEASONAL_SQL,
        "seasonal_phase.csv",
        parse_dates=["week_start"],
    )


# ================================================================
# Table existence check
# ================================================================
REQUIRED_TABLES = [
    "mart.brand_kpi",
    "mart.sov_analysis",
    "mart.anomaly_log",
    "mart.csi_macro",
    "mart.korea_global_lag",
]

OPTIONAL_TABLES = [
    "mart.forecast_results",
    "mart.sentiment_quarterly",
    "mart.seasonal_phase",
    "staging.events_calendar",
]


def check_table_exists(table_name):
    """Check if a table/view exists in PostgreSQL."""
    if USE_CSV_FALLBACK:
        return True
    schema, name = table_name.split(".")
    query = """
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        UNION
        SELECT 1 FROM information_schema.views
        WHERE table_schema = %s AND table_name = %s
    )
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, (schema, name, schema, name))
        result = cur.fetchone()[0]
        cur.close()
        conn.close()
        return result
    except Exception:
        return False


def check_all_tables():
    """Check all required and optional tables. Returns dict of status."""
    status = {}
    for t in REQUIRED_TABLES + OPTIONAL_TABLES:
        status[t] = {
            "exists": check_table_exists(t),
            "required": t in REQUIRED_TABLES,
        }
    return status
