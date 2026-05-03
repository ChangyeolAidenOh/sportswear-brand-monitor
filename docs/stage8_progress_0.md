# Stage 8.0 Checkpoint — Environment Setup + 5-Tab Skeleton

**Date:** 2026-05-03
**Status:** COMPLETED
**Scope:** Directory structure + file skeletons + KPI mapping + CSV fallback design

---

## Deliverables

### A. Directory Structure

```
dashboard/
├── app.py                         # Streamlit entry point (6 tabs)
├── config.py                      # DB config + CSV fallback + KPI registry
├── data/
│   ├── __init__.py
│   ├── queries.py                 # mart table queries + CSV fallback
│   └── chain_diagram.py           # chain_diagram_data.json loader
├── tabs/
│   ├── __init__.py
│   ├── tab1_weekly_kpi.py         # KPI 1, 2, 3, 5, 6, 10
│   ├── tab2_season.py             # KPI 4
│   ├── tab3_channel.py            # KPI 2 (cross-ref)
│   ├── tab4_anomaly.py            # KPI 4, 8, 9
│   ├── tab5_forecast_bridge.py    # KPI 6, 7, 10, 11
│   └── methodology_doc.py         # KPI 12, 13 (governance)
├── components/
│   ├── __init__.py
│   ├── kpi_card.py                # Reusable metric card
│   └── tooltip.py                 # Stage 7 narrative tooltips
└── assets/
    └── style.css                  # Custom styles
```

### B. requirements_dashboard.txt

streamlit>=1.31, pandas>=2.0, plotly>=5.18, psycopg2-binary>=2.9,
python-dotenv>=1.0, prophet>=1.1

### C. KPI 13 -> Tab Mapping (in config.py KPI_TAB_MAP)

| KPI | Tab | Name |
|-----|-----|------|
| 1 | tab1 | 530 Dependency Ratio |
| 2 | tab1, tab3 | D2C Search Trend |
| 3 | tab1 | Category Gap Auto-detect |
| 4 | tab2, tab4 | NB Sentiment Quarterly |
| 5 | tab1 | Search-Sentiment Gap |
| 6 | tab1, tab5 | CSI Moving Average |
| 7 | tab5 (right panel) | Global Trend MA (monitoring O / predictive X) |
| 8 | tab4 | Event Stacking Density |
| 9 | tab4 | Anomaly Method Agreement |
| 10 | tab1, tab5 | CSI Elasticity (3.98) |
| 11 | tab5 (left panel) | Prophet Baseline 26w |
| 12 | methodology | 5-Dim Verification Pattern |
| 13 | methodology | Methodology Validation Stage |

### D. Data Layer Design Decisions

1. **CSV fallback as first-class citizen:** `USE_CSV_FALLBACK` env var toggles
   between PostgreSQL (local dev) and CSV (Streamlit Cloud deploy).
   `_query_or_csv()` in queries.py handles both paths transparently.

2. **Graceful degradation:** DB connection failure auto-falls back to CSV.
   Missing CSV returns None; tabs display "Data not available" placeholder.

3. **Table existence check:** `check_all_tables()` validates mart layer
   before rendering. Required vs optional tables distinguished.

4. **chain_diagram_data.json loader:** `operational_use` branching logic
   implemented — `get_monitoring_edges()` vs `get_predictive_edges()`
   enables Tab 5 right panel `if edge.operational_use.predictive_feature`
   conditional rendering.

### E. Stage 7 Narrative Surfacing

- **Sidebar About:** 4-layer narrative one-line summary
- **Tab 5 right panel:** monitoring vs predictive tooltip (KPI 7)
- **Methodology Doc tab:** KPI 12 + KPI 13 full governance asset text
- **Tooltip component:** 4 predefined tooltips (monitoring_vs_predictive,
  csi_elasticity, sign_correction, methodology_validation)

### F. Coding Conventions Compliance

- All comments in English
- snake_case function names with verb prefix (fetch_, check_, render_, get_)
- Section separators: `# ===` 64 chars
- Import order: stdlib -> third-party -> local
- Module docstrings with Usage line
- Constants in UPPER_SNAKE_CASE
- Minimal print messages, no emojis

---

## Verification

- All 13 .py files pass AST parse check
- `streamlit run dashboard/app.py` renders 6-tab skeleton with sidebar

---

## Next: Stage 8.1

Tab 1 (Weekly KPI) implementation — KPI cards, weekly trend charts,
530 dependency ratio, D2C trend, category gap auto-detect.
Requires: `mart.brand_kpi` + `mart.sov_analysis` queries active.
