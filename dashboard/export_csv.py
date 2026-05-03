"""
Export mart/raw data to data/exports/ for Streamlit Cloud deploy.
Usage: python dashboard/export_csv.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database.connection import get_conn

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exports")


def export_query(query, filename, parse_dates=None):
    """Execute query and save as CSV."""
    try:
        with get_conn() as conn:
            df = pd.read_sql(query, conn, parse_dates=parse_dates)
        path = os.path.join(EXPORT_DIR, filename)
        df.to_csv(path, index=False)
        print(f"{filename}: {len(df)} rows")
        return len(df)
    except Exception as e:
        print(f"{filename}: FAILED — {e}")
        return 0


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    total = 0

    exports = [
        # Tab 1, 2, 3: brand KPI
        ("""SELECT week_start, brand, region, search_index, sov_pct,
            search_wow_pct, search_mom_pct, search_yoy_pct,
            season_label, season_week_num
           FROM mart.brand_kpi_weekly
           ORDER BY week_start, brand, region""",
         "brand_kpi_weekly.csv"),

        # Tab 1, 2: product portfolio
        ("""SELECT week_start, product_line, region, search_index,
            search_wow_pct, share_within_nb_pct, season_label
           FROM mart.product_portfolio_weekly
           ORDER BY week_start, product_line, region""",
         "product_portfolio_weekly.csv"),

        # Tab 3: Korea vs Global comparison
        ("""SELECT * FROM mart.korea_global_comparison
           ORDER BY week_start, brand, metric_name""",
         "korea_global_comparison.csv"),

        # Tab 4: anomaly log
        ("""SELECT id, brand, product_line, metric_name, detected_date,
            anomaly_type, detection_method, severity_score, z_score,
            matched_event_id, description
           FROM mart.anomaly_log
           ORDER BY detected_date, brand, detection_method""",
         "anomaly_log.csv"),

        # Tab 4: events calendar
        ("""SELECT * FROM staging.events_calendar
           ORDER BY event_date""",
         "events_calendar.csv"),

        # Tab 5: Korea-Global lag
        ("""SELECT * FROM mart.korea_global_lag
           ORDER BY method, deseason""",
         "korea_global_lag.csv"),

        # Tab 1: CSI macro
        ("""SELECT period AS year_month, value AS csi_value
           FROM raw.ecos_raw
           WHERE stat_code = '511Y002' AND item_code = 'FME'
           ORDER BY period""",
         "csi_macro.csv"),
    ]

    for query, filename in exports:
        total += export_query(query, filename)

    # Copy Prophet forecast CSVs (already exist in data/forecast/)
    forecast_dir = os.path.join(os.path.dirname(EXPORT_DIR), "forecast")
    for f in ["prophet_forecast_korea.csv", "prophet_forecast_global.csv",
              "prophet_metrics.csv", "forecast_comparison_4way.csv"]:
        src = os.path.join(forecast_dir, f)
        if os.path.exists(src):
            import shutil
            shutil.copy2(src, os.path.join(EXPORT_DIR, f))
            df = pd.read_csv(src)
            print(f"{f}: {len(df)} rows (copied)")
            total += len(df)

    print(f"\nTotal: {total} rows exported to {EXPORT_DIR}/")


if __name__ == "__main__":
    main()
