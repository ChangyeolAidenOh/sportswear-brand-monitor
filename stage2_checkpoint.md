# Stage 2 Checkpoint — SQL-native ETL Pipeline COMPLETED

**Date:** 2026-04-30
**Status:** COMPLETED
**Pipeline:** raw → staging → mart (8 SQL files)
**Total rows produced:** 11,037 (staging) + mart tables/views

---

## SQL File Summary

| # | File | Type | Rows | Key SQL Techniques |
|---|---|---|---|---|
| 01 | `staging_search_weekly.sql` | TRUNCATE+INSERT | 6,092 | CTE, UNION ALL, CASE WHEN mapping, SUM aggregate (한글+영문 merge) |
| 02 | `staging_social_weekly.sql` | TRUNCATE+INSERT | 73 | DISTINCT ON (video dedup), DATE_TRUNC (ISO week) |
| 03 | `mart_brand_kpi.sql` | TRUNCATE+INSERT | 1,392 | LAG(1/4/52) WoW/MoM/YoY, SUM OVER PARTITION (SoV), LEFT JOIN (social) |
| 04 | `mart_sov_analysis.sql` | VIEW + INSERT | 1,740 | SUM OVER PARTITION BY, NULLIF division safety, product share calc |
| 05 | `mart_seasonal_classifier.sql` | 2 VIEWs | — | CASE WHEN, 7-week MA window, MIN per group (season start detection) |
| 06 | `mart_anomaly_residuals.sql` | DELETE+INSERT | 69 | AVG/STDDEV OVER ROWS BETWEEN, z-score threshold, LEAST cap |
| 07 | `mart_top_bottom_ranking.sql` | 2 VIEWs | — | RANK, DENSE_RANK, multi-column PARTITION BY |
| 08 | `mart_korea_global_join.sql` | TRUNCATE+INSERT | 1,740 | Self-JOIN (Korea vs Global), UNION ALL (multi-metric), divergence calc |

---

## Staging Layer

### staging.search_weekly (6,092 rows)

| Source | Keyword Group | Region | Rows |
|---|---|---|---|
| google_trends | brand | global | 1,392 |
| google_trends | brand | korea | 2,088 |
| google_trends | product | global | 870 |
| google_trends | product | korea | 870 |
| naver_datalab | brand | korea | 436 |
| naver_datalab | nb_product | korea | 436 |

- Korea GT brand: 한글+영문 8 keywords → 4 brands SUM aggregation
- search_type: GT uses 'web'/'youtube'/'shopping', Naver uses 'naver_search'
- Week convention: GT Sunday-start (from CSV), Naver Monday-start (from API)

**Excluded from staging:**
- GT apparel layer (노스페이스 outside brand_enum → 05 VIEW handles via raw CTE)
- Naver nb_social (인스타 60 rows, 틱톡 1 row — sparse)
- Naver nb_channel (무신사 37, 쿠팡 16 rows — sparse)

### staging.social_weekly (73 rows)

| Brand | Weeks | Videos | Earliest | Latest |
|---|---|---|---|---|
| nike | 14 | 16 | 2020-09-21 | 2026-04-27 |
| adidas | 17 | 17 | 2024-05-20 | 2026-04-27 |
| puma | 17 | 18 | 2022-10-24 | 2026-04-06 |
| new_balance | 25 | 29 | 2020-04-13 | 2025-12-08 |

- YouTube only (Plan X). Blog/Cafe excluded from time-series staging.
- Video dedup via DISTINCT ON (video_id) — raw has comment-level rows.
- avg_sentiment: NULL until Stage 3 NLP pipeline.

---

## Mart Layer

### mart.brand_kpi_weekly (1,392 rows)
- 4 brands × 2 regions × 174 weeks
- Primary search index: Google Trends web search
- SoV sanity check: sum = 100% for all region×week combinations (0 violations)
- Social columns: 59/696 Korea rows have social data (sparse YouTube coverage)
- Season labels: FW22–SS26, distribution proportional

### mart.product_portfolio_weekly (1,740 rows)
- Korea: 530/574/992/2002r/327 × 174 weeks
- Global: 9060/574/2002r/1906r/990 × 174 weeks
- **530 Korea avg share: 54.98%** (Stage 0 finding confirmed — dominant product line)
- **Global: 9060 avg share: 52.26%** (Korea=530 vs Global=9060 structure confirmed)
- **574: cross-region anchor** (Korea 32.19%, Global 18.73%, both rank #2)
- Share sum sanity: 100% all region×week (0 violations)

### mart.anomaly_log (69 rows)
- Detection method: 8-week rolling z-score, threshold |z| > 2.0
- Spike-heavy distribution (56 spikes vs 13 dips)
- 69/1392 = 5.0% anomaly rate (expected ~4.6% for 2σ)
- Top severity: NB global dip 2023-06-04 (z=-2.47), Puma global spikes

### mart.korea_global_comparison (1,740 rows)
- search_index: 696 rows (4 brands × 174 weeks)
- sov_pct: 696 rows
- product_574_share: 174 rows (cross-region anchor)
- product_2002r_share: 174 rows
- **NB Korea over-indexes Global: +34.94% search, +16.43% SoV**
- **574 divergence: +82.28%** (Korea values 574 much more than Global)
- **2002r divergence: -85.00%** (Korea barely searches 2002r vs Global)

### VIEWs (5 total)
- `mart.vw_sov_by_search_type` — brand SoV by web/youtube/shopping
- `mart.vw_padding_competitive` — 4-brand padding landscape with 7-week MA
- `mart.vw_padding_season_start` — FW season start timing per brand
- `mart.vw_brand_ranking` — RANK/DENSE_RANK by search, SoV, momentum
- `mart.vw_product_ranking` — NB product share and momentum ranking

---

## Key Decisions Made

### Decision #2: Plan X — Granger 3-stage → 2-stage

| Source | Issue | Verdict |
|---|---|---|
| Blog | post_date coverage 2-19 weeks (all brands < 30) | Time-series infeasible |
| Cafe | post_date 100% NULL | Structurally impossible |
| YouTube (video) | 14-25 weeks (all brands < 30) | Below threshold |
| YouTube (comment) | 32.8-74.5% coverage, cross-brand inconsistency | Insufficient for Granger |

**Result:** Social → Search hop removed. Granger chain: Search → Sales (2-stage).
Social repositioned as cross-sectional auxiliary variable.
See `docs/methodology.md` for full narrative.

### Decision #3: nb_social / nb_channel excluded (Option B)

Sparse data below viability threshold. Retained in raw, excluded from staging.

---

## Verification Results

All sanity checks passed:

| Check | Status |
|---|---|
| SoV sum = 100% per region×week (brand_kpi) | ✓ 0 violations |
| SoV sum = 100% per region×week (product_portfolio) | ✓ 0 violations |
| LAG first-week NULL count = 4 (one per brand) | ✓ wow_filled 692/696 |
| Anomaly rate ~5% (2σ theoretical 4.6%) | ✓ 69/1392 = 5.0% |
| Social JOIN offset (GT Sunday +1 = YouTube Monday) | ✓ 59 matches |

---

## Schema Sync

`schema_init.sql` fully synchronized with live DB:
- staging.search_weekly: DDL updated (search_type, keyword_group, interest columns)
- 5 percentage columns: `NUMERIC(6,4)` → `NUMERIC(7,4)`
- 5 VIEWs added to init for idempotent setup
- All UNIQUE constraints match collector UPSERT keys

---

## Files Created in Stage 2

```
notebooks/sql/
├── 01_staging_search_weekly.sql
├── 02_staging_social_weekly.sql
├── 03_mart_brand_kpi.sql
├── 04_mart_sov_analysis.sql
├── 05_mart_seasonal_classifier.sql
├── 06_mart_anomaly_residuals.sql
├── 07_mart_top_bottom_ranking.sql
├── 08_mart_korea_global_join.sql
├── stage2_preflight_queries.sql
├── stage2_verify_raw_values.sql
└── stage2_youtube_viability.sql

docs/
└── methodology.md
```

---

## Quantified Insights (mart에서 직접 산출)

1. **530 의존도:** NB Korea search의 54.98% (GT 5-product 기준). Korea rank #1 = 126/174주.
2. **Korea=530 vs Global=9060:** 양 지역 top product share 52-55% 범위로 구조적 대칭.
3. **574 = cross-region anchor:** 양 지역 rank #2. Korea divergence +82.28% (한국이 574를 더 중시).
4. **패딩 모멘텀:** NB는 노스페이스 대비 매년 5-7주 늦게 패딩 시즌 진입 (FW21-FW25 일관).
5. **NB Korea over-index:** Global 대비 search +34.94%, SoV +16.43%.
6. **Momentum 리더:** Puma가 양 지역 WoW 성장률 1위 빈도 최다 (Korea 63/174주).

---

## Next: Stage 3 — Analysis & Visualization

- Granger causality test: Search → Sales (2-stage, ECOS CSI + financials)
- Blog/Cafe 텍스트 코퍼스: 감성 분석 + 토픽 모델링 (cross-sectional)
- anomaly_log ↔ events_calendar 매칭
- Power BI / Streamlit dashboard 연결
- `social_sentiment_avg` 컬럼 업데이트 (Stage 3 NLP 결과)
