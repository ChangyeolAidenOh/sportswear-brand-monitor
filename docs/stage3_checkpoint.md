# Stage 3 Checkpoint — Seasonal Decomposition & Hybrid Sentiment Analysis

**Date:** 2026-04-30
**Status:** COMPLETED
**Tracks:** A (Seasonal Decomposition & EDA) + B (Hybrid Sentiment Analysis)

---

## Track A: Seasonal Decomposition & EDA

### A1: STL → MSTL Transition

**Initial approach:** STL (period=52) — standard single-season annual decomposition.

**Discovery:** MSTL (periods=[13, 52]) comparison showed residual variance reduction of 48–75% across all 8 brand×region time series:

| Brand | Region | STL Var | MSTL Var | Reduction |
|---|---|---|---|---|
| nike | global | 43.24 | 10.64 | 75.4% |
| nike | korea | 51.37 | 20.37 | 60.4% |
| adidas | global | 4.67 | 1.51 | 67.8% |
| adidas | korea | 12.24 | 5.30 | 56.7% |
| new_balance | global | 3.20 | 0.87 | 72.7% |
| new_balance | korea | 4.75 | 1.84 | 61.3% |
| puma | global | 0.68 | 0.23 | 66.1% |
| puma | korea | 1.35 | 0.70 | 48.3% |

**Decision:** MSTL adopted as primary method. STL retained as comparison in documentation only.

**Narrative:** "STL로 시작했으나 MSTL 비교에서 분기 sub-annual 구조를 발견, 잔차 분산 48–75% 감소를 확인하고 MSTL로 전환. 발견 → 판단 → 전환의 데이터 기반 의사결정."

**Implication for Stage 6:** Dual-season structure means single seasonal order SARIMA is insufficient. Stage 6 will use SARIMAX with quarterly exogenous dummies, TBATS, or Chronos comparison.

### A2: NB Product Line Decomposition

All 10 product-region pairs decomposed (174 weeks each, all ≥ 104 threshold):

| Product | Region | Ann_Amp | Qtr_Amp | Resid_Std | SS/FW | S0_H2_Ref |
|---|---|---|---|---|---|---|
| 530 | korea | 53.98 | 22.06 | 5.54 | 0.86 | 1.18 |
| 574 | korea | 51.10 | 29.92 | 6.06 | 0.99 | — |
| 992 | korea | 60.13 | 29.17 | 6.94 | 0.89 | 0.93 |
| 2002r | korea | 45.49 | 23.43 | 3.03 | 0.71 | — |
| 327 | korea | 28.35 | 23.38 | 2.50 | 0.86 | — |
| 9060 | global | 44.96 | 13.91 | 2.55 | 1.44 | — |
| 574 | global | 17.24 | 6.77 | 1.34 | 1.07 | — |
| 2002r | global | 9.13 | 4.16 | 0.71 | 1.42 | — |
| 1906r | global | 5.41 | 2.26 | 0.57 | 0.99 | — |
| 990 | global | 3.47 | 1.94 | 0.34 | 1.31 | — |

**Stage 0 H2 Correction — SS/FW Ratio Reversal:**

~~Stage 0 H2: 530 SS/FW=1.18 (SS-dominant), 992 SS/FW=0.93 (weak FW). "시즌 신호 약함."~~

Stage 3 correction: 530 SS/FW=**0.86 (FW-dominant)**, 992 SS/FW=**0.89 (FW-dominant)**. Single-season STL absorbed quarterly patterns into the annual component, inflating SS estimates. With MSTL properly separating the two cycles, all Korea products are FW-dominant.

**Korea vs Global Season Structure:**

- Korea 5 products: ALL FW-dominant (0.71–0.99)
- Global 4/5 products: SS-dominant (1.07–1.44), 1906r neutral (0.99)
- Hypothesis for "why": Korean consumers have higher fall/winter outdoor wearing frequency, concentrating search demand in FW. Global (primarily NA/EU) is driven by back-to-school + spring/summer running seasons. To be quantitatively verified in Stage 7 Korea↔Global Bridge.

**574 = cross-region anchor (season-level confirmation):** Korea 0.99, Global 1.07 — near-neutral in both regions. Confirms Stage 2 finding at decomposition level.

**Trend Patterns (product-level):**

- **530 korea:** 35→31 (2023H2 decline) → 34 (2024 mid bounce) → 29 (2026 early re-decline). Not simple decay — bounce-then-decline pattern. Stage 5 anomaly should separately capture the 2024 bounce and 2026 decline for external event mapping.
- **992 korea:** 25→5 structural decline. +43pt MSTL residual spike (event-based, confirmed by surviving dual-season removal). Exact week to be matched against 992 re-release news in Stage 5.
- **9060 global:** 2→68 explosive growth. NB's global growth engine.

### A3: Channel Mix Analysis

**Part 1 — Search Type Mix (GT Korea brand):**

| Brand | Web | YouTube | Shopping |
|---|---|---|---|
| nike | 38.5% | 29.3% | **32.1%** |
| adidas | 40.3% | 35.3% | **24.5%** |
| new_balance | 51.9% | 43.7% | **4.5%** |
| puma | 50.8% | 45.8% | **3.4%** |

NB/Puma shopping share is negligible (3–5%) vs Nike/Adidas (24–32%). NB consumers don't use Google Shopping search — purchase channel is app-direct (Musinsa, Coupang).

**Part 2 — D2C Trend Re-verification:**

| Keyword | N | Slope | p-value | Verdict |
|---|---|---|---|---|
| 뉴발란스 공식몰 | 109 | **-0.191/week** | **0.000005** | DECLINING |
| 뉴발란스 크림 | 106 | **-0.016/week** | **<0.000001** | DECLINING |
| 뉴발란스 무신사 | 37 | -0.000/week | 0.998 | No trend |
| 뉴발란스 쿠팡 | 16 | +0.003/week | 0.835 | No trend |

Stage 0 H5 confirmed: D2C slope -0.191 (Stage 0: -0.179, consistent). Resale platform (크림) also declining. Musinsa/Coupang: no signal at all (app-direct entry).

---

## Track B: Hybrid Sentiment Analysis

### B1: Keyword Dictionary (v2)

- **112 keywords** initially → 3-way category separation:
  - Product: 96 (56 pos, 40 neg) — main input for social_sentiment_static
  - Channel: 14 (2 pos, 12 neg) — excluded from sentiment calculation
  - Resale: 2 (1 pos, 1 neg) — separate label for NB limited edition analysis
- "배송" removed (neutral/positive context contamination), replaced with "배송 늦"/"배송 느" n-grams
- "가품"/"짝퉁"/"가짜" moved from product → channel (distribution trust issue, not product quality)
- "가성비"/"합리적" moved from product → channel (price-related). Post-hoc impact assessment: restoring to product (w=+0.3) shifts brand averages by +0.002~0.006 (all < 0.01). Current classification retained. Note: "가성비" is arguably a product evaluation ("price-performance ratio"), but the impact is negligible so the conservative channel assignment stands.

**Sponsorship Filter:** 11 patterns (협찬, 체험단, 제공받, etc.). 1.3% of corpus flagged.

**Sponsorship Bias Test:** Welch t-test: t=4.48, **p=0.0005**. Sponsored mean +0.136 vs Organic +0.378. Statistically significant — sponsored posts excluded from social_sentiment_static.

### B2: Full Corpus Scoring

- 10,000 texts scored (product category only, sponsorship filtered)
- Keyword resolved: **97.4%**, API needed: **2.6%** (261 cases)
- Threshold 0.3 confirmed: keyword coverage 72.5%, classification rate 97.4%

### B3: Claude API Batch

- Model: claude-haiku-4-5-20251001
- 261 requests submitted via Anthropic Batch API (50% discount)
- All 261 succeeded, 0 errors
- Total cost: **35.8 KRW** ($0.026 USD), 0.0036 KRW/text

### B4: Brand Sentiment Distribution

**Organic only, product-only scoring:**

| Brand | n | pos | neg | neu | pos% | neg% | avg_score |
|---|---|---|---|---|---|---|---|
| new_balance | 3,922 | 2,059 | 73 | 1,790 | 52.5% | 1.9% | **+0.289** |
| nike | 1,980 | 1,691 | 17 | 272 | 85.4% | 0.9% | **+0.474** |
| adidas | 1,982 | 1,623 | 23 | 336 | 81.9% | 1.2% | **+0.436** |
| puma | 1,984 | 1,419 | 21 | 544 | 71.5% | 1.1% | **+0.367** |

**NB Sentiment Asymmetry:** NB avg +0.289 is the lowest across all 4 brands. NB neutral ratio 45.6% (vs Nike 13.7%, Adidas 17.0%, Puma 27.4%) — NB blog posts are disproportionately informational/news-based rather than product reviews. This connects to the Cross-cutting Insight: "NB Korea is search over-indexed (+34.94%) but sentiment-lowest — search-sentiment asymmetry."

**social_sentiment_static values broadcast to mart.brand_kpi_weekly:**

| Brand | Value | Rows Updated |
|---|---|---|
| new_balance | +0.2890 | 348 |
| nike | +0.4738 | 348 |
| adidas | +0.4361 | 348 |
| puma | +0.3666 | 348 |

Column renamed from `social_sentiment_avg` → `social_sentiment_static` to signal cross-sectional constant, not weekly time-series. Intentional denormalization — JOIN overhead unnecessary for a brand-level constant (methodology.md §2: social data repositioned as cross-sectional auxiliary variable).

### B5: Cost & Accuracy Verification

**Routing:** Keyword 97.4% + API 2.6% = 100% coverage.

**Cost:** 35.8 KRW total (estimate was ~35.8 KRW — exact match).

**Sample Representativeness (B1 1K vs B2 10K):**

| Brand | B1 (1K) | B2 (10K) | Delta | Status |
|---|---|---|---|---|
| new_balance | +0.297 | +0.289 | -0.008 | Representative |
| nike | +0.509 | +0.474 | -0.035 | Minor deviation |
| adidas | +0.429 | +0.436 | +0.007 | Representative |
| puma | +0.357 | +0.367 | +0.010 | Representative |

Nike minor deviation: 1K sample had n=194 Nike posts, positively skewed. 10K full corpus is the more stable estimate (regression to the mean).

---

## Stage 4 Impact Items

1. **social_sentiment_static** is NOT a Granger VAR input. It is a descriptive context variable per methodology.md §2.
2. **MSTL residual** should be used for Stage 5 anomaly detection (replaces Stage 2 z-score baseline). Quarterly seasonal pattern may have caused false-positive spikes in the original anomaly_log.
3. **Dual-season structure** affects Stage 6 SARIMA specification: single seasonal order insufficient → SARIMAX/TBATS/Chronos comparison.
4. **992 +43pt residual spike** is the cleanest ground truth for Stage 5 anomaly detection validation.
5. **NB product-line sentiment segmentation** — NB's high variance (neutral 45.6%) suggests product-line-level sentiment profiles may differ significantly (530: comfort/착화감 vs 992: fashion/스타일). Breaking NB sentiment by product line is a future extension that could explain the brand-level asymmetry. Requires query_keyword-based product mapping in raw.naver_blog_raw.

---

## Schema Changes (Migrations 004–007)

| # | File | Change |
|---|---|---|
| 004 | `004_seasonal_components.sql` | CREATE mart.seasonal_components |
| 005 | `005_seasonal_product_line.sql` | ADD product_line column + COALESCE unique index |
| 006 | `006_blog_sentiment.sql` | CREATE staging.blog_sentiment |
| 007 | `007_rename_sentiment_static.sql` | RENAME social_sentiment_avg → social_sentiment_static |

---

## Files Created in Stage 3

```
analysis/
├── seasonal_decomposer.py          # A1: STL + MSTL brand decomposition
├── product_decomposer.py           # A2: NB product line MSTL decomposition
├── channel_mix.py                  # A3: search type mix + D2C trend
├── sentiment_dictionary.py         # B1: keyword dictionary v2 (3-way)
├── sentiment_scorer.py             # B2+B3: full corpus scoring + Batch API
└── sentiment_aggregator.py         # B4+B5: brand aggregation + mart update

database/migrations/
├── 004_seasonal_components.sql
├── 005_seasonal_product_line.sql
├── 006_blog_sentiment.sql
└── 007_rename_sentiment_static.sql

data/batch/
├── sentiment_batch.jsonl           # Batch API input (261 requests)
├── sentiment_results.jsonl         # Batch API output (261 results)
└── cost_log.csv                    # Cost tracking

figures/seasonal/
├── stl_*.png                       # 8 STL decomposition + 2 overlays
├── mstl_*.png                      # 8 MSTL decomposition + 2 overlays
└── products/
    ├── mstl_*.png                  # 10 product decompositions
    └── mstl_product_overlay_*.png  # 2 product overlays

figures/channel_mix/
├── search_type_mix_stacked.png
├── shopping_share_trend.png
└── d2c_trend_reverification.png

figures/sentiment/
├── keyword_score_distribution_t0.3.png
├── sponsorship_bias.png
├── keyword_score_by_brand_organic.png
├── brand_sentiment_distribution.png
├── sample_vs_full_comparison.png
└── full_corpus_score_distribution.png
```

---

## Quantified Insights (Stage 3 산출)

1. **Dual-season structure:** Annual (52w) + quarterly (13w), MSTL residual variance 48–75% reduction
2. **SS/FW ratio reversal:** 530 Korea 1.18→0.86, all Korea products FW-dominant
3. **Korea FW vs Global SS:** Structural season asymmetry across regions
4. **574 cross-region anchor:** Seasonal-level confirmation (0.99 vs 1.07)
5. **530 trend:** Bounce-then-decline (35→31→34→29), not simple decay
6. **9060 global:** 2→68 explosive growth trajectory
7. **992 residual spike:** +43pt event-driven (post dual-season removal)
8. **NB Shopping share:** 4.5% (vs Nike 32.1%) — app-direct purchase channel
9. **D2C slope:** -0.191/week (p=0.000005), Stage 0 H5 confirmed
10. **Resale (크림) also declining:** -0.016/week (p<0.000001)
11. **Hybrid sentiment cost:** 35.8 KRW / 10,000 texts (keyword 97.4% + API 2.6%)
12. **NB sentiment asymmetry:** +0.289 (lowest), neutral 45.6% (highest)
13. **Search-sentiment asymmetry:** NB search +34.94% over-index but sentiment lowest

---

## Next: Stage 4 — Leading Indicator Validation

- Granger Causality: Search → Sales (2-stage, ECOS CSI + financials)
- Neural Granger Causality (PyTorch, if data permits)
- VAR + Impulse Response Function
- Macro indicator (CSI) validity test per brand

*Stage 3 Seasonal Decomposition & Hybrid Sentiment Analysis: COMPLETED.*

---

## Documentation Updates

- `methodology.md` §2: `social_sentiment_avg` → `social_sentiment_static` 반영
- `methodology.md` §5 신설: STL→MSTL 전환, SS/FW 반전, 이중 시즌 구조, downstream stage 영향
- `methodology.md` §6 신설: Hybrid 감성 분석 (3-way 사전, 협찬 필터, threshold, sentiment_static 비정규화)
- `exploratory_findings.md` H2: Stage 3 correction 주석 추가 (~~1.18~~ → 0.86, 취소선 보존)
- `exploratory_findings.md` H2 summary table: status 업데이트 (🔍 Weak → ✅ Corrected)
- `exploratory_findings.md` Stage 3 Cross-cutting Insights 섹션 신설 (8개 data point narrative + Integrated Business Diagnosis 업데이트)
