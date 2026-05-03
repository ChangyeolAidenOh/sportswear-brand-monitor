"""
Mart table query functions for dashboard data layer.
Each function queries PostgreSQL or falls back to CSV based on config.
Usage: from dashboard.data.queries import fetch_brand_kpi
"""

# stdlib
import os

# third-party
import pandas as pd

# local
from dashboard.config import CSV_DIR, USE_CSV_FALLBACK
from database.connection import get_conn


# ================================================================
# Helpers
# ================================================================
def _read_csv_fallback(filename):
    """Read a CSV file from data/exports/ directory."""
    path = os.path.join(CSV_DIR, filename)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, parse_dates=True)


def _query_or_csv(query, csv_filename, parse_dates=None):
    """Execute SQL query or fall back to CSV. Returns DataFrame or None."""
    if USE_CSV_FALLBACK:
        df = _read_csv_fallback(csv_filename)
        if df is not None and parse_dates:
            for col in parse_dates:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
        return df
    try:
        with get_conn() as conn:
            df = pd.read_sql(query, conn, parse_dates=parse_dates)
        return df
    except Exception as e:
        print(f"DB query failed: {e}")
        df = _read_csv_fallback(csv_filename)
        if df is not None and parse_dates:
            for col in parse_dates:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
        return df


# ================================================================
# KPI 1, 2, 3: mart.brand_kpi_weekly
# ================================================================
BRAND_KPI_SQL = """
SELECT
    week_start,
    brand,
    region,
    search_index,
    sov_pct,
    search_wow_pct,
    search_mom_pct,
    search_yoy_pct,
    season_label,
    season_week_num
FROM mart.brand_kpi_weekly
ORDER BY week_start, brand, region
"""


def fetch_brand_kpi():
    """Fetch weekly brand KPI data (KPI 1, 2, 3)."""
    return _query_or_csv(
        BRAND_KPI_SQL,
        "brand_kpi_weekly.csv",
        parse_dates=["week_start"],
    )


# ================================================================
# Product portfolio (530 dependency, Tab 1)
# ================================================================
PRODUCT_PORTFOLIO_SQL = """
SELECT
    week_start,
    product_line,
    region,
    search_index,
    search_wow_pct,
    share_within_nb_pct,
    season_label
FROM mart.product_portfolio_weekly
ORDER BY week_start, product_line, region
"""


def fetch_product_portfolio():
    """Fetch NB product portfolio weekly data (530 dependency)."""
    return _query_or_csv(
        PRODUCT_PORTFOLIO_SQL,
        "product_portfolio_weekly.csv",
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
# KPI 6, 10: CSI from staging.macro_monthly
# ================================================================
CSI_MACRO_SQL = """
SELECT
    period AS year_month,
    value AS csi_value
FROM raw.ecos_raw
WHERE stat_code = '511Y002' AND item_code = 'FME'
ORDER BY period
"""


def fetch_csi_macro():
    """Fetch CSI macro data from raw.ecos_raw (KPI 6, 10)."""
    return _query_or_csv(
        CSI_MACRO_SQL,
        "csi_macro.csv",
        parse_dates=["year_month"],
    )


# ================================================================
# KPI 7: mart.korea_global_lag (Migration 011 sign-corrected)
# ================================================================
KOREA_GLOBAL_LAG_SQL = """
SELECT *
FROM mart.korea_global_lag
ORDER BY brand, deseason_method
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
SELECT
    id,
    brand,
    product_line,
    metric_name,
    detected_date,
    anomaly_type,
    detection_method,
    severity_score,
    z_score,
    matched_event_id,
    description
FROM mart.anomaly_log
ORDER BY detected_date, brand, detection_method
"""


def fetch_anomaly_log():
    """Fetch anomaly detection log for 3-way comparison (KPI 9)."""
    return _query_or_csv(
        ANOMALY_LOG_SQL,
        "anomaly_log.csv",
        parse_dates=["detected_date"],
    )


# ================================================================
# KPI 11: mart.forecast_results
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
# Korea vs Global comparison
# ================================================================
KOREA_GLOBAL_COMP_SQL = """
SELECT *
FROM mart.korea_global_comparison
ORDER BY week_start, brand, metric_name
"""


def fetch_korea_global_comparison():
    """Fetch Korea vs Global comparison data."""
    return _query_or_csv(
        KOREA_GLOBAL_COMP_SQL,
        "korea_global_comparison.csv",
        parse_dates=["week_start"],
    )


# ================================================================
# Table existence check
# ================================================================
REQUIRED_TABLES = [
    "mart.brand_kpi_weekly",
    "mart.product_portfolio_weekly",
    "mart.anomaly_log",
    "mart.korea_global_comparison",
]

OPTIONAL_TABLES = [
    "mart.forecast_results",
    "mart.sentiment_quarterly",
    "mart.korea_global_lag",
    "staging.macro_monthly",
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
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(query, (schema, name, schema, name))
            result = cur.fetchone()[0]
            cur.close()
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
