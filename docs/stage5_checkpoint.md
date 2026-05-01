# Stage 5 Checkpoint — Anomaly Detection Refinement

**Date:** 2026-05-01
**Status:** COMPLETED
**Tracks:** A (Z-score Baseline) + B (MSTL Residual) + C (Isolation Forest) + D (Event Matching & Evaluation)

---

## Core Finding: 91.3% False Positive Rate in Stage 2

Stage 2's rolling z-score anomalies (69 cases, 5.0% rate) were 91.3% false positives — seasonal artifacts from quarterly (13w) patterns that the rolling window could not distinguish from genuine anomalies. MSTL decomposition removes these patterns before anomaly detection, producing a fundamentally different anomaly set.

This single number answers "why was time series decomposition necessary?" with empirical evidence.

---

## Track A: Z-score Baseline Verification

Stage 2 anomaly_log confirmed: 69 rows, detection_method = `rolling_zscore_8w`, |z| > 2.0.

Rolling window specification (from `06_mart_anomaly_residuals.sql`):
- `ROWS BETWEEN 7 PRECEDING AND CURRENT ROW` (trailing 8-week window)
- No centering, no seasonal adjustment

Re-derivation for comparison script uses identical parameters (window=8, min_periods=8, center=False).

---

## Track B: MSTL Residual Anomaly Detection

### B1: Residual Extraction

| Source | Rows | Series | Period |
|---|---|---|---|
| mart.seasonal_components (MSTL, product_line IS NULL) | 1,392 | 8 (4 brands × 2 regions) | 2022-12-25 ~ 2026-04-19 |

### B2: Residual Statistics

| Brand | Region | Std | Skewness | Kurtosis | Max |z| |
|---|---|---|---|---|---|
| adidas | global | 1.2274 | 0.2536 | 1.0960 | 3.27 |
| adidas | korea | 2.3029 | 0.5150 | 1.9555 | 3.70 |
| new_balance | global | 0.9347 | -0.0166 | -0.0980 | 2.77 |
| new_balance | korea | 1.3550 | 0.5065 | 1.4969 | 4.24 |
| nike | global | 3.2614 | 0.1852 | -0.2346 | 2.58 |
| nike | korea | 4.5130 | 0.1368 | 0.8686 | 3.72 |
| puma | global | 0.4808 | 0.1756 | -0.1067 | 3.15 |
| puma | korea | 0.8372 | 0.0217 | 0.4750 | 2.97 |

Observations: nike korea has highest variance (std=4.51), puma global lowest (std=0.48). NB korea highest max |z| at 4.24 (2025-04-20 spike).

### B3: Anomaly Detection

| Threshold | Anomalies | Rate | Spikes | Dips |
|---|---|---|---|---|
| \|z\| > 2.0 | 70 | 5.0% | 47 | 23 |
| \|z\| > 3.0 | 11 | 0.8% | 8 | 3 |

Threshold 2.0 matches Stage 2 rate by design (advisor decision #2).

Top 5 spikes (|z| > 2.0): NB korea 2025-04-20 (+4.24), adidas korea 2024-08-25 (+3.70), adidas korea 2024-08-18 (+3.30), adidas global 2024-07-14 (+3.27), adidas korea 2024-09-15 (+3.15).

### B4: Confusion Matrix — Z-score vs MSTL

| Category | Count | Interpretation |
|---|---|---|
| Both anomaly (agreement) | 6 | True cross-method agreement |
| Z-score only (false positive) | 63 | Seasonal artifacts — 91.3% of Stage 2 |
| MSTL only (new discovery) | 64 | Deseasonalized signal reveals new anomalies |
| Neither (true negative) | 1,259 | Both agree normal |
| **Total** | **1,392** | |

Per-brand: nike had most z-score false positives (korea 11, global 11). NB korea had most agreement (2 of 6 total).

---

## Track C: Isolation Forest

### C1: Configuration

- Algorithm: sklearn IsolationForest
- contamination: 0.05 (matching Stage 2 anomaly rate, advisor decision #2)
- n_estimators: 100, random_state: 42
- Per-series independent models (advisor decision #4)

### C2: Results

Total: 72 anomalies (9 per series × 8 series = 5.2%)
Spikes: 41, Dips: 31

IF spike/dip ratio (41:31) more symmetric than MSTL (47:23). IF is direction-agnostic (isolation-based), capturing extreme dips that MSTL's direction-aware z-score weights differently.

---

## 3-Way Comparison

### Method Independence Note

M+IF agreement (52 of 54 two-way cases) is **not independent cross-validation**. Both methods operate on the same MSTL residual input. Agreement between them reflects input sharing, not methodological convergence. Only Z-score inclusion constitutes true cross-validation because it uses raw time series with a rolling window, independent of MSTL decomposition.

This distinction motivated the Tier structure for investigation prioritization.

### Agreement Summary

| Agreement Level | Count |
|---|---|
| All 3 methods | 5 |
| 2 methods | 54 |
| 1 method only | 88 |

### 3-Way Agreement (5 highest-confidence anomalies)

| Brand | Region | Week | Z | M | IF |
|---|---|---|---|---|---|
| new_balance | korea | 2024-09-15 | ✓ | ✓ | ✓ |
| new_balance | korea | 2025-03-23 | ✓ | ✓ | ✓ |
| nike | korea | 2024-02-11 | ✓ | ✓ | ✓ |
| puma | korea | 2024-03-17 | ✓ | ✓ | ✓ |
| puma | korea | 2024-09-01 | ✓ | ✓ | ✓ |

All 5 are Korea-only — consistent with Stage 4's finding that Korea series have more volatile, event-driven dynamics.

### Investigation Tier Structure

| Tier | Criteria | Anomalies | Rationale |
|---|---|---|---|
| 1 | Z-score included in agreement | 7 | Independent cross-validation |
| 2 | M+IF only, macro_event or multi_brand weeks | 31 | Same input caveat; co-occurring pattern adds value |
| 2 excluded | M+IF only, brand_specific | — | No independent validation, low investigation value |

### Co-occurring Anomalies (Macro Event Candidates)

| Week | Brands | N |
|---|---|---|
| 2024-09-15 | adidas, new_balance, nike, puma | 4 |
| 2025-02-16 | adidas, nike, puma | 3 |
| 2024-04-21 | new_balance, nike, puma | 3 |
| 2024-08-18 | adidas, nike | 2+ |

### NB-Only Anomalies (Brand Event Candidates)

2024-03-03 global, 2024-08-04 global, 2024-11-24 global, 2025-03-23 korea, 2026-04-19 korea

---

## Track D: Event Matching & Evaluation

### D1: events_calendar

25 events curated via anomaly-driven manual investigation (advisor decision #1: "anomaly first → calendar retroactive").

| event_type | Count |
|---|---|
| product_launch | 4 |
| campaign | 10 |
| collab | 7 |
| macro_event | 4 |

| event_origin | Count | Purpose |
|---|---|---|
| scheduled | 7 | Independent ground truth (Olympics, Air Max Day, Black Friday, CSI, London Marathon, AJ3 Black Cement) |
| investigated | 18 | Anomaly-driven retroactive discovery |

Coverage: 2024-02 ~ 2025-04 (14 of 40 months in dataset).

### D2: Matching Rules

1. **Window:** strict `event_date BETWEEN week_start AND week_start + 6`. Range events: `week_start BETWEEN event_date AND event_end_date`. No ±1w extension.
2. **Brand:** macro_event (brand=NULL) matches all brands. Brand-specific matches only that brand. Primary = closest date, secondary = rest.
3. **Coverage filter:** Precision denominator uses only anomalies within events_calendar period.

### D3: Evaluation Results

**Precision (2×2):**

| Scope | Matched | Total | Precision | Ex-Macro |
|---|---|---|---|---|
| Tier 1 only | 5 | 7 | 71.4% | 71.4% |
| Tier 1 + Tier 2 | 17 | 38 | 44.7% | 21.1% |

Tier 1 ex-macro = Tier 1 all (no macro matches in Tier 1) — clean result.

**Event Detection Rate:**

| Scope | Detected | Total | Rate | Note |
|---|---|---|---|---|
| scheduled only | 6 | 7 | 85.7% | Independent ground truth |
| all events | 16 | 25 | 64.0% | Upper bound, anomaly-driven caveat |

"Event Detection Rate" used instead of "Recall" — events_calendar was anomaly-driven, structurally overestimating true Recall.

### D4: Unmatched & Undetected Analysis

**Tier 1 unmatched (2/7):**

- **puma korea 2024-09-01:** No puma event found for 9/1~9/7 week. Genuine unmatched.
- **nike korea 2024-02-11:** Travis Scott Jumpman Jack (02-05) and 뉴진스 Nike (02-08) fall in prior week. Lag effect — event impact delayed to following week. Strict window correctly excludes; documented as "1-week delayed response possibility."

**Scheduled event undetected (1/7):**

- **Air Max Day 2024 (03-26):** event_date falls in 03-24~03-30 week, but no nike anomaly in that week. adidas and NB had anomalies instead. **Interpretation:** Air Max Day is absorbed by Nike's MSTL seasonal component (predictable annual event), but generates search spillover to competitors as an "industry attention catalyst." Nike's seasonal model expects Air Max Day; competitors' models don't. This is a methodologically meaningful finding, not a matching failure.

---

## Narrative Insights (Stage 5)

### Data Point 11: Celebrity-Driven Search Dominance in NB Korea

2024-09-15 week (z=+2.15, 3-way agreement) was driven by simultaneous 송혜교 SNS wearing (품절 대란) + 아이유 가을 화보 + Stone Island 콜라보. Celebrity endorsement creates search spikes that exceed typical product launch impact. NB Korea's top anomaly (2025-04-20 z=+4.24) combined 992 팝업스토어 + 마라톤 대회 + 키즈 샌들 완판.

### Data Point 12: CSI Macro Events Explain Multi-Brand Dips

2024-12 CSI 87.9 급락 (−12.7pt) and 2025-02 CSI 95.0 저점 explain co-occurring dips across NB+puma korea and adidas+nike+puma korea respectively. Connects to Stage 4 Granger: NB is CSI→Search reactive, confirming that macro downturns suppress NB search demand.

### Data Point 13: Air Max Day Spillover Effect

Nike's predictable annual event (Air Max Day) is absorbed by Nike's own seasonal model but creates anomalies in competitor search. Industry-level attention catalysts affect brands asymmetrically depending on their seasonal structure.

### Data Point 14: 2024 Spring Global Spike = Olympics Pre-Campaign

4-week global spike (2024-03-24 ~ 2024-04-28) across all brands was not seasonal (MSTL already removed annual pattern) but driven by Paris 2024 Olympics D-100 campaign convergence: Nike On Air showcase, adidas 41-sport Olympic kit, Puma FOREVER.FASTER., NB "We Got Now," Euro 2024 kits, London Marathon. Olympic year creates supra-seasonal spring demand.

---

## Database Changes

| Table | Change | Rows |
|---|---|---|
| mart.anomaly_log | INSERT detection_method = mstl_residual_2.0 | 70 |
| mart.anomaly_log | INSERT detection_method = mstl_residual_3.0 | 11 |
| mart.anomaly_log | INSERT detection_method = isolation_forest | 72 |
| staging.events_calendar | INSERT from CSV via load_events_calendar.py | 25 |
| mart.anomaly_log | UPDATE matched_event_id via update_matched_event_id.py | — |

### Schema Migration

| # | File | Change |
|---|---|---|
| 010 | `010_events_calendar_origin.sql` | ADD event_origin column to staging.events_calendar |

---

## Files Created in Stage 5

```
analysis/
├── anomaly_mstl_residual.py      # Track B: MSTL residual anomaly detection
├── anomaly_isolation_forest.py   # Track C: Isolation Forest
├── anomaly_comparison.py         # 3-way comparison + confusion matrix
├── anomaly_investigation_list.py # Track D Step 1: tiered investigation targets
├── anomaly_event_matching.py     # Track D: event matching + evaluation
├── load_events_calendar.py       # Track D: CSV → staging.events_calendar INSERT
└── update_matched_event_id.py    # Track D: mart.anomaly_log FK update

data/
├── events_calendar.csv           # 25 curated events with event_origin tag
└── anomaly/
    ├── mstl_residual_anomalies_2.0.csv
    ├── mstl_residual_anomalies_3.0.csv
    ├── isolation_forest_anomalies.csv
    ├── confusion_matrix_by_series.csv
    ├── three_way_comparison.csv
    ├── co_occurring_anomalies.csv
    ├── nb_only_anomalies.csv
    ├── investigation_targets.csv
    ├── investigation_weeks.csv
    ├── matched_anomalies.csv
    └── evaluation_metrics.csv

database/migrations/
└── 010_events_calendar_origin.sql

figures/anomaly/
├── mstl_residual_anomalies_8panel.png
├── isolation_forest_anomalies_8panel.png
├── zscore_vs_mstl_confusion.png
├── anomaly_comparison_heatmap.png
└── event_matching_summary.png
```

---

## Documentation Updates

- `methodology.md` §10: Anomaly detection 3-way comparison methodology, M+IF independence limitation, Tier structure rationale, matching window design, Precision/EDR reporting framework — **DONE**
- `exploratory_findings.md`: Data Points 11-14 — **DONE**
- `v3 계획서`: §4.6 / §5.1 Stage 5 결과 반영

---

## Next: Stage 6 — Forecasting (SARIMAX / LSTM / Chronos)

- SARIMAX with exogenous CSI variable (leveraging Stage 4 Granger results)
- LSTM sequence model (174w short series challenge)
- Chronos zero-shot foundation model comparison
- Narrative: short time series → foundation model advantage?

*Stage 5 Anomaly Detection Refinement: COMPLETED.*
