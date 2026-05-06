# Global Sportswear Brand Performance Monitor

A weekly performance monitoring system that integrates search trends, social signals, macro indicators, and financial data across four global sportswear brands (Nike, Adidas, Puma, New Balance) to deliver actionable KPIs for Business Data Coordinator workflows. The pipeline tests the hypothesized **Macro → Korea → Global** demand chain via 5-dimension orthogonal causality framework, surfaces three critical analytical findings through self-diagnostic protocols, and serves a 6-tab Streamlit dashboard with 13 production-ready KPIs.

**Live Dashboard:** [https://sportswear-brand-monitor-newbalance.streamlit.app/](https://sportswear-brand-monitor-newbalance.streamlit.app/)

**Independent Project**

---

## Table of Contents

- [Motivation](#motivation)
- [Data Sources](#data-sources)
- [Pipeline](#pipeline)
- [Methodology](#methodology)
- [Key Findings — 24 Data Points](#key-findings--24-data-points)
  - [NB Korea Structural Diagnosis](#nb-korea-structural-diagnosis)
  - [Methodology Validation Findings](#methodology-validation-findings)
  - [The 4-Layer Narrative](#the-4-layer-narrative)
- [Dashboard](#dashboard)
- [13 Production KPIs](#13-production-kpis)
- [Project Structure](#project-structure)
- [Analytical Governance](#analytical-governance)
- [Data Policy](#data-policy)
- [How to Run](#how-to-run)
- [Dependencies](#dependencies)

---

## Motivation

This project addresses four questions that a New Balance Korea Business Data Coordinator would need to answer weekly:

### 1. What drives NB Korea's search demand structurally?

Is it Korean macro consumer sentiment, global brand momentum, or autonomous brand inertia? Bidirectional Granger causality testing across 8 brand×region pairs (4 brands × 2 regions, max lag 4) reveals four distinct patterns:

| Brand | Global | Korea |
|---|---|---|
| Adidas | Search → CSI (robust) | Feedback loop |
| **New Balance** | **CSI → Search** | **CSI → Search** |
| Nike | Independent | Search → CSI |
| Puma | CSI → Search | Independent |

NB is the only brand showing **CSI → Search single direction in both regions** (Korea lag 3 p=0.0229, Global lag 2 p=0.0321). This indicates NB Korea is structurally **macro-reactive demand** — search rises after consumer sentiment improves, unlike Nike/Adidas which retain brand inertia that sustains search regardless of macro conditions.

### 2. Does Korea lead Global, or does Global lead Korea?

Initial Stage 4 DTW analysis suggested Korea leads Global by ~10 weeks. Stage 7 self-diagnostic with three independent verification tests revealed a sign convention error in the original implementation:

- **Test 1 — Synthetic data probe:** Generated time series where Korea leads Global by exactly 5 weeks. Stage 4 code returned lag = -5 (sign inverted relative to its labeling convention).
- **Test 2 — Leakage-free replication:** Re-computed CC and DTW on actual NB Korea/Global series using one-sided trend estimation. 8/8 series classified as direction_flipped relative to Stage 4 labels.
- **Test 3 — Mediation re-run signature:** Sign-corrected mediation reduced inconsistent mediation from 120.35% indirect effect to 10.82%, and BCa CI width narrowed 47%.

**Corrected statement:** Global trend leads Korea by ~10 weeks (DTW ~10w, CC ~9w). Korea is a follower market, but **the Global trend serves as a 10-week monitoring indicator** for Korean demand — a dashboard reference value, not a forecast model input.

### 3. How can statistical anomaly detection separate seasonal patterns from real events?

Stage 2's rolling z-score baseline (8-week window, |z| > 2.0) produced 69 anomalies (5.0% rate). MSTL residual-based detection with the same threshold produced 70 anomalies but only **6 overlapped** between the two sets. The remaining 63 z-score anomalies were quarterly seasonal artifacts — a **91.3% false positive rate** that motivated the methodology shift.

This single number empirically justifies the time series decomposition step: rolling windows cannot distinguish quarterly patterns from genuine anomalies on dual-season (annual + quarterly) series, while MSTL decomposition removes both periodicities before flagging residuals.

### 4. Which forecasting model wins on a 174-week dataset with quarterly seasonality?

A 4-way comparison reveals Prophet wins both regions:

| Model | Korea RMSE | Korea MAPE | Global RMSE | Global MAPE |
|---|---|---|---|---|
| SARIMAX (Fourier K=2 + CSI) | 6.45 | 22.8% | 3.23 | 12.2% |
| **Prophet (changepoint + CSI)** | **5.57** | **18.5%** | **2.54** | **10.6%** |
| LSTM (2-layer stacked, 13w lookback) | 8.11 | 29.4% | 2.71 | 10.7% |
| Chronos-small (zero-shot) | 7.20 | 25.0% | 3.65 | 13.4% |
| Chronos-base (zero-shot) | 7.80 | 27.4% | 3.99 | 14.1% |

Ablation analysis isolates **automatic changepoint detection** as the dominant factor — not the model class itself, but the algorithm's ability to handle non-stationary trend changes in event-driven series. LSTM's 467:1 parameter-to-sample ratio causes structural overfitting, and Chronos shows anti-scaling (small > base) on short context windows, an empirically verified case of foundation model scaling failure on 174-week series.

---

## Data Sources

| Source | Period | Volume | Role |
|---|---|---|---|
| Naver DataLab | 2 years rolling | 1,201 rows | Korean search trends in 4 keyword groups (brand / nb_product / nb_social / nb_channel) |
| Google Trends | 3.5 years | 8,698 rows | Brand-level + product-level search index, 8 CSVs stitched (Korea/Global × Web/YouTube/Shopping) |
| YouTube Data API | snapshot | 90 videos + 3,235 comments | Cross-sectional social volume (4 brands × 2-3 queries × top results) |
| Naver Blog/Cafe | snapshot | 10,000 posts | Sentiment corpus (post_date for time series, query_keyword for product-line attribution) |
| ECOS (한국은행) | 4 years monthly | 52 monthly | Consumer Sentiment Index (CSI), stat_code 511Y002 |
| Financials | FY2023-2024 | 16 rows | T1 SEC 10-Q (Nike), T1 IR (Adidas, Puma), T4 CEO statement (NB Global), T2 sector estimates (NB Korea) |

**Sample period:** 174 weeks for primary search analysis.

**Data governance:** Financial data tagged with source tier (T1=primary regulatory filing, T2=industry estimates, T3=secondary sources, T4=executive statement) for credibility weighting. T4 entries are not used in causal inference; only T1-T3 enter Granger inputs.

**Sparse data exclusions:** Two Naver DataLab keyword groups (nb_social: 61 rows, nb_channel: 268 rows) showed insufficient observation density for time-series decomposition. These are preserved in raw schema for future expansion but excluded from staging/mart layers per data governance protocol documented in methodology.md §4.

---

## Pipeline

The pipeline runs across 8 sequential stages, each producing a checkpoint document with quantified findings, decisions made, and stage-to-stage influence tracking.

### Stage 0 — Data Feasibility Spike + Quick Exploratory Pass

Two-phase preliminary work: (1) data availability verification across 6 sources with viability thresholds, (2) 6 hypothesis-driven exploratory analyses to confirm which directions are worth pursuing in main pipeline.

**Hypothesis verdicts:**

| Hypothesis | Result | Evidence |
|---|---|---|
| H1: Korea-Global cycle alignment | Method limitation (CC -167w artifact) | Deferred to Stage 4 DTW |
| H2: 530 SS vs 992 FW separation | Weak signal (530 SS/FW=1.18, 992 SS/FW=0.93) | Deferred to Stage 3 STL/MSTL |
| H3: 530 dependency intensifying | **CONFIRMED** — slope +2.36pp/Q, p=0.0213 | Promoted to KPI 1 |
| H4: Social → Search lead | **REVERSED** — NB search leads Instagram by 2 weeks (r=0.504) | Stage 4 Granger re-test |
| H5: D2C decline | **CONFIRMED** — slope -0.179/week, p=0.0001 | Promoted to KPI 2 |
| H6: NB padding timing | **CONFIRMED with twist** — NB starts 2.6w earlier (week 42.6 vs 45.2), but absolute scale 1.2 vs 13.9 | "Timing leads, momentum lags" |

### Stage 1 — Multi-Source Data Collection

6 collectors covering 6 data sources, raw schema 23,292 rows total. Per-source UPSERT vs --clear strategy chosen based on data semantics:

| Collector | Strategy | Rationale |
|---|---|---|
| Naver DataLab | UPSERT on (source_type, keyword_group, keyword, period_start) | Time series with relative-scale normalization per group, append-only |
| Google Trends | UPSERT on (geo, search_type, week_start, keyword) | Time series with absolute weekly index |
| YouTube | --clear + INSERT per brand | Snapshot semantics, full refresh on each run |
| Naver Blog/Cafe | --clear + INSERT per brand | Same; post_date used for time series reconstruction |
| ECOS | UPSERT on (stat_code, item_code, time) | Append-only macro time series |
| Financials | UPSERT on (brand, fiscal_period, metric_name, source_type) | Multi-source with tier governance |

### Stage 2 — SQL-Native ETL (raw → staging → mart)

8 SQL files implementing the 3-tier transformation:

```
raw schema (23,292 rows)
    ↓ 01_staging_search_weekly.sql       — UNION ALL across 4 sources, weekly bucketing
    ↓ 02_staging_social_weekly.sql       — JSON extraction, comment aggregation
    ↓ 03_mart_brand_kpi.sql              — LAG window functions, WoW/MoM/YoY
    ↓ 04_mart_sov_analysis.sql           — SUM OVER PARTITION BY for SoV percentage
    ↓ 05_mart_seasonal_classifier.sql    — CASE WHEN for SS/FW classification
    ↓ 06_mart_anomaly_residuals.sql      — moving avg, std deviation rolling windows
    ↓ 07_mart_top_bottom_ranking.sql     — RANK, DENSE_RANK
    ↓ 08_mart_korea_global_join.sql      — multi-key time-aligned joins
staging (11,037 rows) → mart (5 tables + 5 views)
```

**Quantified findings from mart layer:**
- 530 Korea avg share **54.98%** (Stage 0 H3 confirmed and intensified from 51.2%)
- Korea = 530 / Global = 9060 dominant model structure (52-55% share in each region)
- 574 = cross-region anchor (Korea +82.28% divergence vs Global, both regions rank #2)
- NB Korea over-index **+34.94% search, +16.43% SoV** vs Global (new finding from mart)

### Stage 3 — Seasonal Decomposition + Hybrid Sentiment

**Track A — Seasonal Decomposition:** STL initially adopted, MSTL comparison run as ablation. Result: MSTL reduces residual variance by 48-75% across all 8 brand×region series, indicating dual-season structure (annual 52w + quarterly 13w). MSTL becomes primary; STL retained for documentation only.

**SS/FW Ratio Reversal:** Stage 0's H2 measurement re-interpreted. STL's single-period assumption absorbed quarterly patterns into the annual seasonal component, biasing the SS/FW ratio. With MSTL's clean separation, 530 Korea ratio inverts from 1.18 to **0.86 (FW-dominant)**, and all 5 Korean NB products show FW-dominance (0.71-0.99) while 4/5 Global products show SS-dominance (1.07-1.44). This Korea-FW vs Global-SS structural asymmetry is a Stage 7 Bridge analysis input.

**Track B — Hybrid Sentiment Analysis:** 3-way keyword dictionary (Product 96 / Channel 14 / Resale 2, total 112 keywords), sponsorship filter (11 patterns, 1.3% flagged, t=4.48 p=0.0005 between sponsored/organic groups), threshold-based routing.

| Stage | Method | Resolution | Cost |
|---|---|---|---|
| 1st pass | Keyword dictionary | 97.4% (9,742 of 10,003 texts) | free |
| 2nd pass | Claude Batch API | 2.6% (261 ambiguous cases, |score| < 0.3) | 35.8 KRW total |

**Sentiment results by brand (organic only, sponsored filtered):**

| Brand | avg_sentiment | neutral % |
|---|---|---|
| Nike | +0.474 | 13.7% |
| Adidas | +0.436 | 17.0% |
| Puma | +0.367 | 27.4% |
| **New Balance** | **+0.289 (lowest)** | **45.6% (highest)** |

NB has lowest average sentiment despite highest search over-index (+34.94%), with neutral ratio 45.6% vs others 13-27%. Interpretation: NB blog posts skew toward informational/news content rather than user reviews, suggesting search demand does not convert to deep engagement.

### Stage 4 — Leading Indicator Validation

**Track A — Bidirectional Granger Causality:**
- 64 tests total (8 pairs × 2 directions × 4 lags)
- 4-pattern classification with NB as outlier (CSI→Search both regions)
- Stationarity: ADF + KPSS, asymmetric preprocessing (CSI 1st-differenced, search MSTL residual)
- Robustness: adidas/global lag 4 p=0.0140 after differencing (robust); nike/global Independent confirmed

**Track B — DTW Korea-Global Lead-Lag (3-way comparison):**

| Brand | Raw DTW | Trend DTW | Residual DTW | Verdict |
|---|---|---|---|---|
| New Balance | +48.0w | **+10.4w** | +42.2w | seasonal artifact stripped |
| Adidas | -14.0w | +17.3w | +12.8w | direction flip, magnitude stable |
| Nike | -70.4w | +99.1w | +26.8w | trend shapes too dissimilar |
| Puma | +57.0w | +26.2w | +25.1w | partial reduction |

Raw DTW lags cluster near 52w (annual cycle), capturing Korea-FW vs Global-SS phase difference rather than true lead-lag. Trend DTW removes seasonal contamination. Residual DTW excluded from primary interpretation (white noise alignment produces arbitrary lags).

**NB result (sign-corrected in Stage 7):** Trend DTW +10.4w with cross-correlation +9w convergence. **Originally interpreted as "Korea leads Global"; corrected interpretation: Global leads Korea.**

**Cointegration finding:** Engle-Granger test on 8 pairs, 5/8 cointegrated (NB Korea strongest p=0.0008). Long-run equilibrium between search and CSI confirms macro-reactive demand structure.

### Stage 5 — Anomaly Detection Refinement

**Three-method comparison:**

| Method | Anomalies | Rate | Detection Type |
|---|---|---|---|
| Stage 2 rolling z-score | 69 | 5.0% | direction-aware, raw series |
| MSTL residual z-score (\|z\|>2.0) | 70 | 5.0% | direction-aware, deseasonalized |
| Isolation Forest (contamination=0.05) | 72 | 5.2% | direction-agnostic, deseasonalized |

**Confusion matrix (z-score vs MSTL):**
- Both anomaly: 6 (true cross-method agreement)
- Z-score only: 63 (**91.3% false positive rate** in Stage 2 baseline)
- MSTL only: 64 (new discoveries after deseasonalizing)
- Both normal: 1,259

**Tier structure for investigation prioritization:**

| Tier | Criteria | Anomalies | Rationale |
|---|---|---|---|
| 1 | Z-score included in 3-way agreement | 7 | Independent cross-validation (z-score uses raw series, MSTL/IF use residual) |
| 2 | M+IF only, in macro_event or multi-brand co-occurring weeks | 31 | Same MSTL input dependency; co-occurrence pattern adds value |

M+IF agreement alone is **not independent cross-validation** because both operate on MSTL residual. Only Z-score inclusion constitutes true cross-method validation. This methodological distinction motivates Tier 1 prioritization.

**events_calendar (25 entries):** Manually curated via anomaly-driven retroactive investigation. Categories: product_launch (4), campaign (10), collab (7), macro_event (4). Origin tagged: scheduled (7, independent ground truth like Olympics, Air Max Day, Black Friday) vs investigated (18, anomaly-driven discoveries).

**Evaluation:**

| Scope | Matched | Total | Precision | Note |
|---|---|---|---|---|
| Tier 1 | 5 | 7 | **71.4%** | Independent cross-validation precision |
| Tier 1 + 2 | 17 | 38 | 44.7% | Includes same-input M+IF cases |
| Scheduled events | 6 | 7 | **85.7%** | Event Detection Rate (independent ground truth) |

**Narrative findings:**
- Celebrity endorsement creates search spikes exceeding typical product launches (NB Korea 2024-09-15: 송혜교 + 아이유 + Stone Island simultaneous, z=+2.15)
- CSI macro events explain multi-brand dips (2024-12 CSI -12.7pt drop matched co-occurring NB+Puma Korea anomalies)
- Air Max Day creates competitor spillover anomalies (Nike's seasonal model absorbs the predictable annual event, but adidas/NB anomalies appear in the same week)
- 2024 spring 4-week global spike was Olympics D-100 campaign convergence (Nike On Air, adidas Olympic kit, Puma FOREVER.FASTER, NB "We Got Now")

### Stage 6 — 4-Way Forecasting Comparison

**Train/test split:** 148/26 weeks (test = 2 quarterly cycles).

**SARIMAX design decisions:**
- Seasonal order s=52 infeasible (148-week train insufficient for seasonal AR/MA estimation)
- Quarterly dummy rejected (search seasonality is smooth sinusoidal, not abrupt level shift)
- Fourier K=2 for 52w + K=2 for 13w = 8 exogenous columns + 1 CSI = 9 total
- K=2 ceiling enforced (K≥3 pushes parameter/observation ratio into danger zone)
- auto_arima selection: Korea (0,1,1), Global (0,1,0) — Global is pure random walk

**Exogenous coefficient findings:**

| Variable | Korea | Global | Interpretation |
|---|---|---|---|
| CSI | 3.98 (p<0.001) | 2.01 (p<0.001) | Korea is 2x more sensitive to consumer sentiment |
| sin_52, cos_52 | sig (p=0.010, 0.024) | non-sig | Korea has annual seasonality, Global does not |
| cos_13_2 | sig | sig | Sub-quarterly pattern in both markets |

**Global ARIMA(0,1,0) finding:** No autoregressive structure. All predictive power comes from exogenous variables. This justifies adding Korea trend as exogenous in future Global forecasting (Stage 7 hypothesis input).

**LSTM:** Stacked 2-layer, hidden 64, dropout 0.3, 13-week lookback, no attention (174w insufficient). Param/sample ratio 467:1 = structural overfitting. Recursive forecasting accumulates error.

**Chronos:** Univariate zero-shot, small (46M) and base (200M) compared. **Anti-scaling result: small outperforms base in both regions.** 174 weeks insufficient context for base's complex prior; pre-trained longer-range patterns become noise on short context.

**Prophet (final winner):** RMSE 5.57 (Korea), 2.54 (Global). Both regions wins. Ablation isolates automatic changepoint detection as the dominant factor.

### Stage 7 — Korea-Global Bridge: Methodology Validation Stage

The originally planned analytical objective was **quantitative validation of the CSI → NB Korea → NB Global 3-stage chain hypothesis** using path-analytic mediation. Stage 7 design adopted a 5-dimension orthogonal null framework — testing the chain hypothesis across 5 independent statistical perspectives that combine to 11 specific tests:

1. **Mediation — Korea → Global direction** (joint block bootstrap, BCa CI)
2. **Mediation — Global → Korea direction** (joint block bootstrap, BCa CI)
3. **VARX bidirectional** — joint impulse response with CSI exogenous
4. **Monthly Granger bidirectional** — re-test at monthly resolution to control for weekly noise
5. **Lagged cointegration bidirectional** — Engle-Granger long-run equilibrium test

**Null hypothesis result: chain rejected** across all 5 dimensions, all 11 tests.

**However, the verification process surfaced three critical findings without external review:**

#### DP20 — Pre-emptive design block

The 5-dimension orthogonal null framework was designed before any data was processed, preventing false positive chain confirmation that single-method analysis (e.g., naive mediation only) might have produced. Pre-commitment to multi-dimensional rejection criteria is a structural defense against confirmation bias.

#### DP23 — MSTL forward-looking leakage detected

The two-sided MSTL filter used in Stage 3 introduces look-ahead bias when applied to lead-lag analysis: the filter at time t uses information from t+k (k > 0). Detected via residual autocorrelation at non-zero lags. One-sided trend estimation (recursive filter with no future information) replacement applied in Stage 7 re-runs.

#### DP24 — Stage 4 sign convention error caught

Stage 4's headline finding "NB Korea leads Global by ~10 weeks" was direction-inverted. Detected via three independent verification tests:

| Test | Method | Result |
|---|---|---|
| 1 — Synthetic probe | Generate series with known +5w lead, run through Stage 4 code | Returns -5w (sign inverted) |
| 2 — Leakage-free replication | Re-compute with one-sided trend, all 4 brands × 2 transformations | 8/8 direction_flipped |
| 3 — Mediation signature | Re-run with corrected direction | %indirect 120.35% → 10.82%, BCa CI width -47% |

**Magnitude robust** within ±2w of original; **direction reversed**.

**Cascade corrections applied:**

| Cascade Source | Dependent Finding | Action |
|---|---|---|
| DP24 | DP9 (Stage 4 lead direction) | Sign-flipped in exploratory_findings.md |
| DP24 | DP21 (3D separation labels) | Direction labels corrected |
| DP24 | DP22 (Sentinel framing) | Deprecated, replaced by DP24 |
| DP24 | KPI 7 | Redefined: Korea trend MA → Global trend MA, with operational scope tooltip |
| DP24 | Migration 011 | Database retrofit applied |
| DP24 | Stage 8 dashboard Tab 5 | Chain diagram direction corrected, Global MA panel added |

**Stage 7 climax narrative:**

> "Stage 7's value lies less in the hypothesis test result (chain rejected) than in the verification process. Three critical findings were surfaced without external reviewer, indicating analytical discipline transferable to enterprise contexts."

This is a **methodology validation stage** — its primary deliverable is the analytical governance pattern (DP20 → DP23 → DP24 cascade) itself, registered as KPI 13 (governance asset).

### Stage 8 — Streamlit Dashboard

6-tab production dashboard with 13 KPIs, dual data source architecture (PostgreSQL local development / CSV fallback for Streamlit Cloud), automatic fallback on DB import failure.

**Sub-stage breakdown:**

| Sub-stage | Scope |
|---|---|
| 8.0 | Directory structure + 5-tab skeleton + KPI mapping |
| 8.1 | Tab 1 Weekly KPI — cards + search trend + SoV + 530 dependency |
| 8.2 | Tab 2 Season — YoY overlay + seasonal pattern + product mix |
| 8.3 | Tab 3 Channel — SoV Korea vs Global + divergence + product gap |
| 8.4 | Tab 4 Anomaly — 3-way timeline + method agreement + event stacking |
| 8.5 | Tab 5 Forecast & Bridge — Prophet 26w + 4-way RMSE + chain diagram + Global MA |
| 8.6 | CSI data connected (raw.ecos_raw) + deprecation fixes |
| 8.7 | CSV export pipeline + CSV fallback verified |
| 8.8 | Streamlit Cloud deploy — live URL active |
| 8.9 | Methodology Doc visual redesign — 5-dim heatmap + DP20→23→24 cascade + DP24 signatures + 4-Layer cards |

---

## Methodology

Each analytical task is solved with a Traditional baseline + Advanced/Foundation alternative for empirical comparison:

| Task | Traditional | Advanced | SOTA / Foundation | Winning Approach |
|---|---|---|---|---|
| Seasonal Decomposition | STL (period=52) | MSTL (52w + 13w) | — | **MSTL** (48-75% residual variance reduction across all 8 series) |
| Causal Inference | Linear Granger | VARX + Mediation (block bootstrap) | 5-dim Orthogonal Null | **5-dim** (chain hypothesis rejected with 11 tests across 5 dimensions) |
| Anomaly Detection | Rolling z-score | MSTL residual z-score | Isolation Forest + Tier structure | **Tier 1** (z-score independent validation only, 71.4% precision) |
| Demand Forecasting | SARIMAX (Fourier K=2 + CSI) | Prophet (changepoint detection) | LSTM Enc-Dec / Chronos foundation model | **Prophet** (4-way ablation isolates changepoint as primary factor) |
| Sentiment Analysis | Keyword dictionary | Hybrid (keyword + Claude API routing) | KcBERT fine-tuning (deferred) | **Hybrid** (35.8 KRW per 10K texts, 95% of LLM-only accuracy) |
| Lead-Lag Analysis | Cross-correlation | DTW (3-way: raw/trend/residual) | — | **Trend DTW** (raw DTW reveals seasonal artifact, +48w → +10w correction) |

### Why Hybrid Sentiment over LLM-only

Full LLM API for 10,000 texts would cost ~$10. The hybrid approach uses keyword dictionary for 97.4% of clear cases (|score| ≥ 0.3) and routes only the 2.6% ambiguous cases to Claude API via Batch API (50% discount). Total cost: **35.8 KRW**, maintaining 95% of LLM-only accuracy on validation samples. This demonstrates **case-by-case tool selection + cost governance** — core BDC operational skills, transferable to any cost-sensitive analytical workflow.

### Why Prophet wins (and what it means)

Prophet's automatic changepoint detection captures structural breaks that SARIMAX (parametric, fixed AR order) and LSTM (severe overfitting at 467:1) cannot. The 4-way ablation isolates this as the dominant factor — not the model class itself, but **the algorithm's ability to handle non-stationary trend changes** in event-driven series. This finding generalizes: for short, event-driven business time series, models with explicit changepoint mechanisms outperform both classical statistical and deep learning approaches.

### 5-Dimension Orthogonal Null Framework

A research-grade methodology asset developed in Stage 7 to guard against false positive causal chain confirmation. Five orthogonal dimensions of testing combine to 11 specific statistical tests:

1. **Mediation — Korea → Global direction** (joint block bootstrap, BCa CI)
2. **Mediation — Global → Korea direction** (joint block bootstrap, BCa CI)
3. **VARX bidirectional** — Direct impulse response with macro exogenous control
4. **Monthly Granger bidirectional** — Resolution sensitivity check (weekly noise control)
5. **Lagged cointegration bidirectional** — Engle-Granger long-run equilibrium test

If the chain hypothesis holds, all 5 dimensions should produce convergent evidence. If even one rejects, the hypothesis is provisionally rejected pending additional investigation. This framework is registered as **KPI 12 (methodology asset)** for transferable use in future causal analyses.

---

## Key Findings — 24 Data Points

Across 8 stages, 24 quantified data points form a cumulative diagnosis of NB Korea's market structure and the project's methodology validation findings.

### NB Korea Structural Diagnosis

#### Stage 0-3 Findings (Data Points 1-8): Demand-Conversion Gap

| # | Finding | Quantified Evidence | Source |
|---|---|---|---|
| 1 | Dual-season structure (52w + 13w) | MSTL residual variance reduction 48-75% across all 8 series | Stage 3 |
| 2 | SS/FW Ratio reversal | 530 Korea STL ratio 1.18 → MSTL 0.86 (FW-dominant) | Stage 3 |
| 3 | Korea FW vs Global SS asymmetry | All 5 Korea NB products FW (0.71-0.99), 4/5 Global products SS (1.07-1.44) | Stage 3 |
| 4 | 574 cross-region anchor | Korea +82.28% divergence vs Global, both regions rank #2 | Stage 2-3 |
| 5 | NB Shopping Search 4.5% (channel disconnect) | Nike 32.1%, Adidas 24.5%, NB 4.5% — app direct entry | Stage 3 |
| 6 | D2C decline | slope -0.191/week, p=0.000005 (Stage 0 -0.179 confirmed and intensified) | Stage 0 H5 → Stage 3 |
| 7 | NB sentiment lowest | +0.289 vs Nike +0.474, neutral 45.6% (highest) | Stage 3 |
| 8 | Search-sentiment asymmetry | Search +34.94% over-index but sentiment lowest of 4 brands | Stage 2 + 3 |

**Stage 3 Integrated Diagnosis:** "Demand exists but conversion fails." Three dimensions confirm:
- **Season:** FW demand concentrates but momentum doesn't expand (Stage 0 H6: padding 1.2 vs North Face 13.9)
- **Channel:** Search high but D2C/Shopping channels weak (D2C -0.191/week, Shopping 4.5%)
- **Sentiment:** Search demand far exceeds product engagement signal

The "demand-conversion gap" is hypothesized to drive 530 dependency intensification (+2.36pp/Q): consumers cannot find conversion satisfaction in non-530 models, defaulting back to 530 as the only product line with consistent positive engagement.

#### Stage 4-6 Findings (Data Points 9-18): Macro-Reactive Structure

| # | Finding | Quantified Evidence | Source |
|---|---|---|---|
| 9 | **Global trend leads Korea ~10w (sign-corrected)** | DTW +10.4w, CC +9w convergence, validated via 3 independent tests | Stage 4 → Stage 7 correction |
| 10 | NB CSI→Search single direction | Korea lag 3 p=0.0229, Global lag 2 p=0.0321, both robust | Stage 4 |
| 11 | Celebrity-driven search dominance | Single weeks combine 3+ celebrity endorsements, exceed typical launch impact | Stage 5 |
| 12 | CSI dips → multi-brand search dips | 2024-12 CSI -12.7pt matched co-occurring NB+Puma anomalies | Stage 5 |
| 13 | Air Max Day competitor spillover | Nike absorbs predictable annual event; adidas/NB anomalies appear same week | Stage 5 |
| 14 | Olympics-driven supra-seasonal demand | 2024 spring 4-week global spike across all brands | Stage 5 |
| 15 | Global ARIMA(0,1,0) — no autoregressive structure | Pure random walk, all predictive power from exogenous | Stage 6 |
| 16 | CSI elasticity asymmetry | Korea coefficient 3.98 vs Global 2.01 (~2x more sensitive) | Stage 6 SARIMAX |
| 17 | Foundation model anti-scaling | Chronos-base (200M) underperforms small (46M) on 174-week context | Stage 6 |
| 18 | Prophet changepoint dominance | 4-way ablation isolates changepoint detection as primary driver of Prophet's win | Stage 6 |

**Stage 4 Integrated Diagnosis (sign-corrected):** NB Korea is a follower market driven by external signals. The Global trend serves as a 10-week monitoring indicator for Korean demand — **a dashboard reference value, not a forecast model input**. This distinction is critical for KPI 7's operational scope.

**Stage 6 mechanism finding:** Prophet 4-way ablation reveals automatic changepoint detection as dominant. Removing changepoint capability (Prophet without changepoints = essentially Fourier+CSI baseline) collapses Prophet's win, confirming that the win is method-driven, not data-luck.

#### Stage 7 Findings (Data Points 19-24): Methodology Validation Assets

| # | Finding | Type | Source |
|---|---|---|---|
| 19 | 5-dim orthogonal null × 11 tests reject chain hypothesis | Statistical | Stage 7 Track A1 |
| 20 | Mediation spurious correlation pre-emption pattern | Methodology | Stage 7 Track A0 |
| 21 | Three-dimensional separation robust (sign-corrected) | Statistical | Stage 7 Track A1' |
| 22 | Sentinel framing — DEPRECATED | Methodology | Stage 7 (replaced by DP24) |
| 23 | MSTL forward-looking leakage | Methodology | Stage 7 self-diagnostic |
| 24 | Stage 4 sign convention inversion | Methodology | Stage 7 cascade detection |

### Methodology Validation Findings

The project's analytical governance produces transferable methodology assets beyond the immediate business diagnosis:

| Finding | Stage | Quantified Evidence |
|---|---|---|
| z-score 91.3% false positive | 5 | 63/69 Stage 2 anomalies were quarterly seasonal artifacts |
| MSTL dual-season structure | 3 | 48-75% residual variance reduction across all 8 series |
| Stage 4 sign convention error caught | 7 | Synthetic probe + leakage-free replication + mediation signature (3 independent tests) |
| Prophet changepoint dominance | 6 | 4-way ablation isolates changepoint detection as primary driver |
| Foundation model anti-scaling | 6 | Chronos-base underperforms small on 174-week context, empirically verified |
| Inconsistent mediation signature | 7 | %indirect 120.35% (sign error) → 10.82% (corrected) |
| MSTL forward-looking leakage | 7 | Two-sided filter introduces look-ahead bias, one-sided replacement applied |

### The 4-Layer Narrative

The original 3-stage chain hypothesis (CSI → NB Korea → NB Global) was **rejected** through 5-dimension orthogonal null testing. However, the 4-layer narrative restructures Stage 7's deliverable around its actual contribution:

```
Layer 1: Original Hypothesis (CSI → Korea → Global)
         ↓ Tested via 5-dim × 11 statistical tests
Layer 2: Hypothesis Rejection (statistical result)
         ↓ Reframed as: "What did the verification process surface?"
Layer 3: Three Self-Diagnostic Findings (DP20, DP23, DP24)
         ↓ Cascaded into: Sign correction + leakage fix + retroactive validation framework
Layer 4: Methodology Validation Stage Pattern (KPI 13 — governance asset)
         ↓ Final deliverable: Analytical governance discipline transferable to enterprise contexts
```

> "Stage 7's value lies less in the hypothesis test result (chain rejected) than in the verification process. Three critical findings were surfaced without external reviewer, indicating analytical discipline transferable to enterprise contexts."

---

## Dashboard

**Live URL:** [https://sportswear-brand-monitor-newbalance.streamlit.app/](https://sportswear-brand-monitor-newbalance.streamlit.app/)

| Tab | Content | KPIs |
|---|---|---|
| **Weekly KPI** | KPI cards (search index, SoV, 530 dependency, CSI snapshot) + 4-brand search trend (174w) + SoV stacked area + 530 ratio over time with 60% threshold line | 1, 2, 3, 5, 6, 10 |
| **Season** | Season position indicator + YoY overlay (this year vs last year) + seasonal decomposition pattern + NB product mix breakdown | 4 |
| **Channel** | SoV Korea vs Global side-by-side + divergence bar chart (574/2002R cross-region anchors) + product gap analysis | 2 |
| **Anomaly** | 222 anomaly records across 4 detection methods (z-score 69 + MSTL z2.0 70 + MSTL z3.0 11 + Isolation Forest 72) + interactive timeline + method agreement matrix + event stacking density visualization | 4, 8, 9 |
| **Forecast & Bridge** | Prophet 26-week forecast + 4-way RMSE comparison bar chart + chain diagram (sign-corrected) + Global trend 4-week MA monitoring panel with operational scope tooltip | 6, 7, 10, 11 |
| **Methodology Doc** | 5-dim orthogonal null heatmap + DP20→DP23→DP24 cascade flow + DP24 verification signatures (3 tests) + 4-Layer Narrative cards (color-coded borders) | 12, 13 |

KPI 7 in Tab 5 explicitly distinguishes monitoring use (dashboard visualization, ✓) from predictive use (forecast model input, ✗) per Stage 7 sign-correction findings — a Migration 011 retrofit applied directly to the dashboard layer.

**Architecture:**
- Dual data source: PostgreSQL (local dev) / CSV fallback (Streamlit Cloud)
- CSV export pipeline: `dashboard/export_csv.py` runs 7 mart queries + 4 forecast CSVs
- Toggle: `USE_CSV_FALLBACK` env var or auto-fallback on DB import failure
- DB connection: shared `database.connection.get_conn()` context manager
- Conditional import: `queries.py` skips `psycopg2` when CSV mode active

---

## 13 Production KPIs

Each KPI has been promoted from a confirmed finding through the pipeline. Operational use (alert / monitoring / methodology) is explicitly tagged.

| # | KPI | Operational Use | Source |
|---|---|---|---|
| 1 | 530 quarterly dependency | Alert when > 60% | Stage 0 H3 → Stage 2 |
| 2 | D2C search share weekly trend | Alert on 4-week consecutive decline | Stage 0 H5 → Stage 3 |
| 3 | Category-level NB share gap | Auto-detect under-indexed categories (e.g., padding 1.2 vs North Face 13.9) | Stage 0 H6 |
| 4 | NB product sentiment ratio | Quarterly tracking of positive/neutral/negative shifts | Stage 3 |
| 5 | Search-sentiment gap | Monitor over-index vs sentiment ranking divergence | Stage 2 + 3 |
| 6 | CSI 3-month moving average | Trigger NB search defense campaign on downturn | Stage 4 |
| 7 | NB Global trend 4-week MA | **Korea demand monitoring** indicator (✓ dashboard, ✗ forecast input) — sign-corrected | Stage 7 DP24 |
| 8 | Event Stacking Density | Same-week overlapping events vs search spike magnitude | Stage 5 |
| 9 | Anomaly detection method agreement | Monthly tracking of 3-way agreement count | Stage 5 |
| 10 | CSI elasticity monitoring | CSI variation × Korea elasticity (3.98) → estimated search impact | Stage 6 |
| 11 | 26-week search forecast (Prophet baseline) | Quarterly forecast with CSI + Fourier K=2 + changepoints | Stage 6 |
| 12 | 5-Dimension Orthogonal Null Verification Pattern | **Methodology asset** — VARX × monthly Granger × mediation × cointegration 11-test framework | Stage 7 |
| 13 | Methodology Validation Stage Pattern | **Governance asset** — DP20 (pre-emptive) → DP23 (self-diagnostic) → DP24 (verification byproduct) cascade | Stage 7 |

KPIs 12 and 13 are not weekly monitoring metrics but **transferable analytical assets** — they represent the project's contribution to methodology and governance practice itself.

---

## Project Structure

```
sportswear-brand-monitor/
├── README.md                                    # this file
├── docs/
│   ├── sportswear_brand_monitor_project_plan_v3.md
│   ├── methodology.md                           # §1-12 analytical decisions narrative
│   ├── exploratory_findings.md                  # 24 data points + diagnoses
│   ├── data_feasibility_report.md               # Stage 0 spike report
│   ├── stage1_checkpoint.md ~ stage8_checkpoint.md
│   └── coding_conventions.md
│
├── database/
│   ├── schema_init.sql                          # 4 schemas: raw, staging, mart, public
│   ├── connection.py                            # ThreadedConnectionPool context manager
│   └── migrations/
│       ├── 008_korea_global_lag.sql
│       ├── 009_granger_results.sql
│       ├── 010_events_calendar_origin.sql
│       └── 011_kpi7_sign_correction.sql         # Stage 7 retrofit
│
├── collectors/                                  # Stage 1
│   ├── collector_naver_datalab.py               # 4 keyword groups, UPSERT pattern
│   ├── collector_google_trends.py               # 8 CSV stitched
│   ├── collector_youtube.py                     # API + --clear pattern
│   ├── collector_naver_blog.py                  # blog + cafe, post_date for time series
│   ├── collector_ecos.py                        # CSI macro
│   └── collector_financials.py                  # T1-T4 source tier governance
│
├── notebooks/sql/                               # Stage 2 (8 SQL files)
│   ├── 01_staging_search_weekly.sql             # UNION ALL across 4 sources
│   ├── 02_staging_social_weekly.sql             # JSON extraction, aggregation
│   ├── 03_mart_brand_kpi.sql                    # LAG window functions, WoW/MoM/YoY
│   ├── 04_mart_sov_analysis.sql                 # SUM OVER PARTITION BY for SoV
│   ├── 05_mart_seasonal_classifier.sql          # CASE WHEN for SS/FW classification
│   ├── 06_mart_anomaly_residuals.sql            # rolling moving avg, std deviation
│   ├── 07_mart_top_bottom_ranking.sql           # RANK, DENSE_RANK
│   └── 08_mart_korea_global_join.sql            # multi-key time-aligned joins
│
├── analysis/                                    # Stage 3-7
│   ├── seasonal_decomposer.py                   # MSTL primary, STL ablation
│   ├── sentiment_dictionary.py                  # 3-way keyword (Product/Channel/Resale)
│   ├── sentiment_hybrid.py                      # Keyword + Claude Batch API routing
│   ├── granger_search_sales.py                  # 8 brand × region × 4 lags × 2 directions
│   ├── granger_robustness.py                    # non-stationary differencing check
│   ├── dtw_korea_global.py                      # 3-way DTW (raw/trend/residual)
│   ├── anomaly_mstl_residual.py                 # |z| > 2.0 on MSTL residual
│   ├── anomaly_isolation_forest.py              # contamination=0.05
│   ├── anomaly_comparison.py                    # 3-way confusion matrix + Tier structure
│   ├── anomaly_event_matching.py                # strict window matching + evaluation
│   ├── load_events_calendar.py                  # CSV → staging.events_calendar
│   ├── update_matched_event_id.py               # mart.anomaly_log FK update
│   ├── forecast_data_prep.py                    # CSI forward-fill, train/test split
│   ├── forecast_sarimax.py                      # Fourier K=2 + CSI exogenous
│   ├── forecast_prophet.py                      # changepoint + CSI regressor
│   ├── forecast_lstm.py                         # 2-layer stacked, 13w lookback
│   ├── forecast_chronos.py                      # zero-shot small + base
│   ├── forecast_comparison.py                   # 4-way RMSE/MAPE + ablation
│   ├── bridge_orthogonal_null.py                # 5-dim 11 tests
│   ├── bridge_mediation.py                      # joint block bootstrap, BCa CI
│   └── bridge_sign_correction.py                # DP24 3-test verification
│
├── dashboard/                                   # Stage 8
│   ├── app.py                                   # main entry, sys.path setup
│   ├── config.py                                # env vars, fallback toggle
│   ├── export_csv.py                            # PostgreSQL → CSV pipeline
│   ├── data/
│   │   ├── queries.py                           # mart queries (conditional psycopg2 import)
│   │   └── chain_diagram.py                     # JSON → Plotly visualization
│   ├── tabs/
│   │   ├── tab1_weekly_kpi.py
│   │   ├── tab2_season.py
│   │   ├── tab3_channel.py
│   │   ├── tab4_anomaly.py
│   │   ├── tab5_forecast_bridge.py
│   │   └── methodology_doc.py
│   ├── components/
│   │   ├── kpi_card.py                          # custom KPI card with delta + tooltip
│   │   └── tooltip.py                           # operational scope tooltip
│   └── assets/
│       └── style.css
│
├── data/
│   ├── events_calendar.csv                      # 25 curated events (scheduled + investigated)
│   ├── anomaly/                                 # 11 CSV outputs from Stage 5
│   ├── forecast/                                # 4-way model outputs
│   ├── exports/                                 # CSV fallback for Streamlit Cloud
│   └── bridge/                                  # Stage 7 outputs
│
└── figures/                                     # 60+ visualizations
    ├── exploratory/                             # H1-H6 hypothesis plots
    ├── seasonal/                                # MSTL decomposition × 8 series
    ├── var/irf/                                 # 8 impulse response plots
    ├── dtw/                                     # 4 brands × 3 variants alignment
    ├── anomaly/                                 # 5 comparison plots
    ├── forecast/                                # 4-way comparison + ablation
    └── bridge/                                  # 5-dim heatmap + cascade flow

# Root-level Stage 0 spike scripts (preserved as reproducibility trail)
quick_exploratory_pass.py                        # 6 hypothesis tests
spike_feasibility.py                             # data feasibility verification
spike_check5_gtrends.py                          # Google Trends viability
spike_check_h4_h5_rerun.py                       # H4/H5 re-verification
stitch_gtrends.py                                # 8 CSV stitching utility
docker-compose.yml                               # PostgreSQL 16 setup
.env.example                                     # API key template
requirements.txt                                 # Streamlit Cloud deps
requirements_dashboard.txt                       # full local dev deps
```

---

## Analytical Governance

### Decision Documentation Pattern

Every major analytical decision is documented in `methodology.md` (§1-12) with consistent structure:
- **Original design** (what was initially planned)
- **Verification protocol** (how it was tested)
- **Decision** (which approach was adopted)
- **Cascade impact** (which downstream stages are affected)

This produces a self-documenting audit trail. Each stage's checkpoint references methodology sections, and methodology sections reference verification figures and code modules. The result is a navigable graph of decisions, evidence, and consequences.

### Self-Diagnostic Discipline (Stage 7 Climax)

Stage 7 represents the project's analytical governance climax. Three critical findings were surfaced through self-diagnostic without external review:

| Finding | Type | Detection Method |
|---|---|---|
| DP20 — Pre-emptive design block | Methodology | 5-dim framework designed before data processing prevented confirmation bias |
| DP23 — MSTL forward-looking leakage | Methodology | Detected via residual autocorrelation at non-zero lags |
| DP24 — Stage 4 sign convention error | Methodology | 3 independent tests (synthetic + leakage-free + mediation signature) |

These findings would have been invisible without **deliberate self-diagnostic protocols**. The Methodology Validation Stage Pattern (DP20 → DP23 → DP24 cascade) is itself a transferable analytical asset, registered as KPI 13.

---

## Data Policy

**Public artifacts:** Aggregated metrics, statistical analysis results, and visualization artifacts are committed for portfolio reproducibility (`data/anomaly/`, `data/bridge/`, `data/exports/`, `data/forecast/`).

**Local-only artifacts:** Raw social media text (Naver blog/cafe content) and Batch API request/response payloads are gitignored due to source licensing. Sentiment analysis results are integrated into `mart.sentiment_static` and surfaced via `sentiment_aggregator.py` — raw text is not required for reproducibility.

**Trace preservation:** Pre-DP24 sign-corrected analysis artifacts (e.g., `bridge_global_enhanced.py`, `mediation_bootstrap.json`, `triple_comparison_*.png`) are retained as evidence of analytical governance discipline. See `docs/stage7_checkpoint.md` §12.4.4 (DP22 deprecation pattern + stage4_checkpoint footnote).

**Database:** PostgreSQL schema in `database/schema_init.sql` + numbered migrations 003~011. Migrations 001/002 are integrated into `schema_init.sql` (consolidated initial schema). Migration 011 (sign correction retrofit) applied 2026-05-03 — see `docs/stage7_checkpoint.md` §12.4.4 for cascade detail.

---

## How to Run

### Prerequisites

- Docker (for PostgreSQL 16) or local Postgres
- Python 3.11
- macOS / Linux (tested on M2 MacBook 16GB)

### Setup

```bash
# 1. Clone repository
git clone https://github.com/ChangyeolAidenOh/sportswear-brand-monitor.git
cd sportswear-brand-monitor

# 2. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Start PostgreSQL
docker compose up -d

# 4. Initialize schema
psql -h localhost -p 5433 -U nb_admin -d nb_monitor -f database/schema_init.sql

# 5. Configure API keys
cp .env.example .env
# Edit .env with NAVER_CLIENT_ID, ANTHROPIC_API_KEY, etc.
```

### Run Pipeline (Sequential by Stage)

```bash
# Stage 1: Data collection
python -m collectors.collector_naver_datalab
python -m collectors.collector_google_trends
python -m collectors.collector_youtube
python -m collectors.collector_naver_blog
python -m collectors.collector_ecos
python -m collectors.collector_financials

# Stage 2: SQL ETL (sequential 01-08)
for f in notebooks/sql/0*.sql; do
    psql -h localhost -p 5433 -U nb_admin -d nb_monitor -f "$f"
done

# Stage 3: Seasonal decomposition + sentiment
python analysis/seasonal_decomposer.py
python analysis/sentiment_hybrid.py

# Stage 4: Granger + DTW
python analysis/granger_search_sales.py
python analysis/granger_robustness.py
python analysis/dtw_korea_global.py

# Stage 5: Anomaly detection
python analysis/anomaly_mstl_residual.py
python analysis/anomaly_isolation_forest.py
python analysis/anomaly_comparison.py
python analysis/load_events_calendar.py
python analysis/anomaly_event_matching.py

# Stage 6: Forecasting
python analysis/forecast_data_prep.py
python analysis/forecast_sarimax.py
python analysis/forecast_prophet.py
python analysis/forecast_lstm.py
python analysis/forecast_chronos.py
python analysis/forecast_comparison.py

# Stage 7: Bridge validation
python analysis/bridge_orthogonal_null.py
python analysis/bridge_mediation.py
python analysis/bridge_sign_correction.py

# Stage 8: Dashboard (local)
streamlit run dashboard/app.py
```

### View Live Dashboard

Visit [https://sportswear-brand-monitor-newbalance.streamlit.app/](https://sportswear-brand-monitor-newbalance.streamlit.app/)

If the dashboard appears to be sleeping, it will wake within 30 seconds on first request.

---

## Dependencies

Core libraries:

```
pandas, numpy, scipy
statsmodels                # SARIMAX, MSTL, Granger, VARX, Johansen
scikit-learn               # IsolationForest, DBSCAN
prophet                    # Forecasting with changepoint detection
torch                      # LSTM
transformers               # HuggingFace
chronos-forecasting        # Amazon foundation model
tslearn                    # DTW
psycopg2-binary
sqlalchemy
streamlit
plotly
anthropic                  # Claude Batch API
python-dotenv
```

Full list in `requirements.txt` (root, for Streamlit Cloud) and `requirements_dashboard.txt` (full local dev).

---

## Project Status

| Stage | Status | Deliverable |
|---|---|---|
| Stage 0 — Data Feasibility + Quick Exploratory | COMPLETED | 6 hypothesis verdicts, viability thresholds |
| Stage 1 — Data Collection | COMPLETED | 6 collectors, raw 23,292 rows |
| Stage 2 — SQL ETL | COMPLETED | 8 SQL files, mart 5 tables + 5 views |
| Stage 3 — Seasonal + Sentiment | COMPLETED | MSTL primary, hybrid sentiment 35.8 KRW |
| Stage 4 — Leading Indicator | COMPLETED (sign-corrected in Stage 7) | 4-pattern Granger, 3-way DTW |
| Stage 5 — Anomaly Detection | COMPLETED | 91.3% false positive finding, Tier structure, 25 events |
| Stage 6 — Forecasting | COMPLETED | 4-way comparison, Prophet wins, ablation |
| Stage 7 — Bridge Validation | COMPLETED | 5-dim orthogonal null, DP20/23/24 cascade |
| Stage 8 — Streamlit Dashboard | COMPLETED, live URL active | 6 tabs, 13 KPIs, dual data source |
| Stage 8b — Power BI Service | DEFERRED | Streamlit provides equivalent interactive layer |
| Stage 9 — Weekly PDF Report | DEFERRED | Streamlit dashboard covers same KPIs interactively |

**Deferred items rationale:** Streamlit dashboard provides equivalent or richer interactive visualization compared to Power BI / static PDF. Both deferred items are designed to be implementable within 2 days post-employment, integrated with the existing mart layer via the same data contract.

---

## Author

**Changyeol (Aiden) Oh**
This project was independently developed for the New Balance Korea 2026 Business Data Coordinator application.
