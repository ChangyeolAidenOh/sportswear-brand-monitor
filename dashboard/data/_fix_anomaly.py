# Quick check: anomaly_log sample data
from database.connection import get_conn
with get_conn() as conn:
    import pandas as pd
    df = pd.read_sql("SELECT * FROM mart.anomaly_log LIMIT 5", conn)
    print(df.columns.tolist())
    print(df.head())
    print(f"\nTotal rows: {pd.read_sql('SELECT COUNT(*) FROM mart.anomaly_log', conn).iloc[0,0]}")
    print(f"\nMethods: {pd.read_sql('SELECT DISTINCT detection_method FROM mart.anomaly_log', conn)['detection_method'].tolist()}")
    print(f"\nBrands: {pd.read_sql('SELECT DISTINCT brand FROM mart.anomaly_log', conn)['brand'].tolist()}")
