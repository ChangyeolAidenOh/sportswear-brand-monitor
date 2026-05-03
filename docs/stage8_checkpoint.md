# Stage 8 Checkpoint — Streamlit Dashboard

**Date:** 2026-05-03
**Status:** COMPLETED
**Live URL:** https://sportswear-brand-monitor-newbalance.streamlit.app/

---

## Deliverables

### 6-Tab Dashboard (13 KPIs)

| Tab | Content | KPIs |
|-----|---------|------|
| Weekly KPI | KPI cards (search, SoV, 530 dep, CSI) + 4-brand trend + SoV area + 530 ratio | 1, 2, 3, 5, 6, 10 |
| Season | Season position (SS26 W7) + YoY overlay + seasonal pattern + product mix | 4 |
| Channel | SoV Korea vs Global + divergence bar + product gap (574/2002r) | 2 |
| Anomaly | 222 anomalies, 4 methods, timeline + method agreement + event stacking | 4, 8, 9 |
| Forecast & Bridge | Prophet 26w + 4-way RMSE + chain diagram + Global 4w MA | 6, 7, 10, 11 |
| Methodology Doc | 5-dim heatmap + DP20→23→24 cascade + DP24 signatures + 4-layer cards | 12, 13 |

### Architecture

- **Dual data source:** PostgreSQL (local dev) / CSV fallback (Streamlit Cloud)
- **CSV export:** `dashboard/export_csv.py` — 7 mart queries + 4 forecast CSVs
- **Toggle:** `USE_CSV_FALLBACK` env var or auto-fallback on DB import failure
- **DB connection:** `database.connection.get_conn()` reused (context manager)
- **Conditional import:** `queries.py` skips `psycopg2` when CSV mode active

### Data Summary

| Export | Rows |
|--------|------|
| brand_kpi_weekly.csv | 1,392 |
| product_portfolio_weekly.csv | 1,740 |
| korea_global_comparison.csv | 1,740 |
| anomaly_log.csv | 222 |
| events_calendar.csv | 25 |
| korea_global_lag.csv | (schema mismatch, re-exported) |
| csi_macro.csv | 52 |
| prophet_forecast_korea.csv | 26 |
| prophet_forecast_global.csv | 26 |
| prophet_metrics.csv | 6 |
| forecast_comparison_4way.csv | 24 |

### Stage 7 Narrative Surfacing

- **Sidebar About:** 4-layer narrative one-line summary
- **Tab 5 right panel:** chain_diagram_data.json visualization + chain_summary.png
- **Tab 5 caption:** monitoring vs predictive distinction (KPI 7)
- **Tab 5 expander:** degradation evidence table (Prophet -9.0% / SARIMAX -10.9%)
- **Methodology Doc:** chain_summary.png + 5-dim heatmap + cascade flow + DP24 signatures
- **Methodology Doc:** 4-layer cards with color-coded border

### Sub-stage History

| Sub-stage | Scope | Status |
|-----------|-------|--------|
| 8.0 | Directory structure + 5-tab skeleton + KPI mapping | DONE |
| 8.1 | Tab 1 Weekly KPI — cards + search trend + SoV + 530 dependency | DONE |
| 8.2 | Tab 2 Season — YoY overlay + seasonal pattern + product mix | DONE |
| 8.3 | Tab 3 Channel — SoV comparison + Korea-Global divergence | DONE |
| 8.4 | Tab 4 Anomaly — 3-way timeline + method agreement + event stacking | DONE |
| 8.5 | Tab 5 Forecast & Bridge — Prophet + 4-way + chain diagram + Global MA | DONE |
| 8.6 | CSI data connected (raw.ecos_raw) + deprecation fixes | DONE |
| 8.7 | CSV export + CSV fallback mode verified | DONE |
| 8.8 | Streamlit Cloud deploy — live URL active | DONE |
| 8.9 | Methodology Doc visual redesign — heatmap + cascade + signatures | DONE |

### Files Created
dashboard/
├── init.py
├── app.py
├── config.py
├── export_csv.py
├── requirements.txt
├── data/
│   ├── init.py
│   ├── queries.py
│   └── chain_diagram.py
├── tabs/
│   ├── init.py
│   ├── tab1_weekly_kpi.py
│   ├── tab2_season.py
│   ├── tab3_channel.py
│   ├── tab4_anomaly.py
│   ├── tab5_forecast_bridge.py
│   └── methodology_doc.py
├── components/
│   ├── init.py
│   ├── kpi_card.py
│   └── tooltip.py
└── assets/
└── style.css
.streamlit/
├── config.toml
└── secrets.toml (gitignored)
requirements.txt (root, for Streamlit Cloud)
requirements_dashboard.txt (full, for local dev)
data/exports/ (CSV fallback files)
docs/stage8_checkpoint.md

### Bugs Fixed During Stage 8

1. `ModuleNotFoundError: dashboard` — added `sys.path.insert` to `app.py`
2. `ModuleNotFoundError: dashboard.config` — added `dashboard/__init__.py`
3. DB password mismatch — switched to `database.connection.get_conn()`
4. `anomaly_log` column `week_start` → `detected_date`
5. `forecast_comparison_4way.csv` column `label` → `model`
6. CSI N/A — `staging.macro_monthly` empty, switched to `raw.ecos_raw`
7. `use_container_width` deprecation → `width="stretch"`
8. CSV fallback date parsing — `pd.to_datetime` in `_query_or_csv`
9. Product divergence chart y-axis — `yaxis=dict(type="category")`
10. `psycopg2` import on Streamlit Cloud — conditional import

---

## Next: Stage 9 — Weekly Performance Report PDF
