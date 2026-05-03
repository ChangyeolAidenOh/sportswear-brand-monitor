# Stage 8 Checkpoint — Streamlit Dashboard

**Date:** 2026-05-03
**Status:** COMPLETED
**Live URL:** https://sportswear-brand-monitor-newbalance.streamlit.app/

---

## Deliverables

### 6-Tab Dashboard (13 KPIs)

| Tab | Content | KPIs |
|-----|---------|------|
| Weekly KPI | KPI cards + search trend + SoV + 530 dependency | 1, 2, 3, 5, 6, 10 |
| Season | Season position + YoY overlay + seasonal pattern + product mix | 4 |
| Channel | SoV Korea vs Global + divergence + product gap | 2 |
| Anomaly | 3-way timeline + method agreement + event stacking | 4, 8, 9 |
| Forecast & Bridge | Prophet 26w + 4-way comparison + chain diagram + Global MA | 6, 7, 10, 11 |
| Methodology Doc | 5-dim verification + validation stage pattern | 12, 13 |

### Architecture

- Data layer: PostgreSQL (local) / CSV fallback (Streamlit Cloud)
- CSV export: 7 mart tables + 4 forecast CSVs = 5,253+ rows
- `USE_CSV_FALLBACK` env var toggles data source
- `database.connection.get_conn()` reused from existing codebase

### Stage 7 Narrative Surfacing

- Sidebar About: 4-layer narrative summary
- Tab 5 right panel: chain_diagram_data.json visualization
- Tab 5 caption: monitoring vs predictive distinction
- Methodology Doc tab: KPI 12, 13 governance assets
- Expander: degradation evidence table

### Sub-stage History

| Sub-stage | Scope |
|-----------|-------|
| 8.0 | Directory structure + 5-tab skeleton + KPI mapping |
| 8.1 | Tab 1 Weekly KPI — cards + charts |
| 8.2 | Tab 2 Season — YoY overlay + seasonal pattern |
| 8.3 | Tab 3 Channel — SoV comparison + divergence |
| 8.4 | Tab 4 Anomaly — 3-way detection + event stacking |
| 8.5 | Tab 5 Forecast & Bridge — Prophet + chain diagram |
| 8.6 | CSI data connected + deprecation fixes |
| 8.7 | CSV export + CSV fallback mode verified |
| 8.8 | Streamlit Cloud deploy — live URL active |

---

## Next: Stage 9 — Weekly Performance Report PDF
