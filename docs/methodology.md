# Methodology — Analysis Design Decisions

**Project:** Global Sportswear Brand Performance Monitor
**Author:** Changyeol Oh
**Last updated:** 2026-05-01 (Prophet Track E added)

---

## 1. Granger Causality Chain: 3-Stage → 2-Stage Reduction

### 1.1 Original Design (3-Stage)

The initial analysis pipeline proposed a 3-stage Granger causality chain to model how consumer attention propagates from social media buzz to search behavior to purchase signals:

```
Social Signal → Search Interest → Sales Proxy
(YouTube/Blog)    (GT/Naver)       (ECOS/Financials)
```

This 3-stage design was the project's methodological differentiator — most brand monitoring projects treat social and search as independent signals. The hypothesis was that social mentions temporally lead search interest (Social → Search hop), which in turn leads purchase behavior (Search → Sales hop).

### 1.2 Data Viability Check

Before committing to the 3-stage design, Stage 2 pre-flight verification queries assessed whether the raw social data met the minimum requirements for time-series causal inference.

**Granger causality prerequisite:** Stationary or near-stationary time series with sufficient consecutive observations. The practical threshold was set at 30 weeks of non-zero weekly data per brand, which is the minimum for reliable VAR model estimation with seasonal controls.

**Blog/Cafe verification (Q1, Q3):**

| Source | Issue | Verdict |
|---|---|---|
| Naver Blog | `post_date` present but weekly coverage 2-19 weeks per brand | Insufficient |
| Naver Cafe | `post_date` 100% NULL (Naver Search API does not return dates for cafearticle) | Structurally impossible |

The blog coverage failure is a structural limitation of the Naver Search API, which returns results by relevance ranking (500 results per query). This causes temporal concentration — most results cluster around recent high-activity periods. Re-collection cannot solve this because the API does not support date-range filtering for blog search.

**YouTube verification (Q4, Q5):**

| Brand | Weeks (videos) | Weeks (comments) | Comment coverage % |
|---|---|---|---|
| new_balance | 25 | 203 | 68.6% |
| adidas | 17 | 76 | 74.5% |
| puma | 17 | 85 | 47.0% |
| nike | 14 | 96 | 32.8% |

Video-based weekly counts failed the 30-week threshold for all brands. Comment-based timestamps improved coverage substantially (NB 203 weeks, 68.6%), but with 30-50% gap weeks and severe cross-brand inconsistency (Nike 32.8% vs Adidas 74.5%). Applying interpolation to fill 30-50% gaps would undermine the causal inference that Granger testing is designed to provide.

### 1.3 Decision: Plan X Adopted

The Social → Search hop was removed from the Granger chain. The analysis proceeds with a 2-stage design:

```
Search Interest → Sales Proxy
(GT/Naver)         (ECOS/Financials)
```

**Framing:** This reduction was not a concession to data scarcity but a methodological decision based on quantitative validation. The project attempted the 3-stage design, verified the data requirements against empirical thresholds, and concluded that the social time-series resolution did not meet the minimum standard for causal inference. Documenting this process — hypothesis, verification protocol, threshold-based rejection — demonstrates analytical governance.

**Alternative considered (Plan Y):** Rebuild the YouTube collector for weekly repeated collection and defer Stage 4 by 4-6 weeks to accumulate sufficient data. Rejected because the timeline cost was disproportionate to the uncertain benefit, and the remaining 2-stage chain (Search → Sales) retains the core analytical value.

---

## 2. Social Data Repositioning

Under Plan X, social data (YouTube, Blog, Cafe) is repositioned from time-series causal input to cross-sectional auxiliary variables:

| Data Source | Original Role | Revised Role |
|---|---|---|
| YouTube | Weekly social buzz time-series for Granger | Cross-sectional: mention count, view/like aggregates per brand |
| Naver Blog | Weekly mention frequency for Granger | Text corpus: sentiment analysis, topic modeling (Stage 3) |
| Naver Cafe | Weekly mention frequency for Granger | Text corpus: sentiment analysis (post_date unavailable) |

Social metrics appear in `mart.brand_kpi_weekly` as `social_mention_count` and `social_sentiment_static` (populated in Stage 3), but these are descriptive context variables — not inputs to the Granger VAR model. The `_static` suffix signals that sentiment is a brand-level cross-sectional constant, not a weekly time-series value.

---

## 3. Stage 0 Hypothesis Disposition

### H4: "Search → Social Direction Reversal"

Stage 0 hypothesized that the causal direction between search and social might be reversed for certain brands — i.e., search interest could lead social buzz rather than the conventional assumption that social leads search.

**Status: Cannot be verified in this analysis.**

The Social → Search hop was removed from the Granger chain (Section 1.3), which means neither direction of the search-social relationship can be tested with the current data. H4 remains an open question that would require weekly-cadence social data collection over 30+ consecutive weeks to address.

This is recorded as a known limitation, not an oversight. The data gap was identified through systematic verification (not assumed), and the hypothesis is preserved for future investigation if social data collection is expanded.

---

## 4. Sparse Data Exclusions

### Naver DataLab: nb_social, nb_channel Groups

| Group | Keywords | Issue |
|---|---|---|
| nb_social | 뉴발란스 인스타 (60 rows), 뉴발란스 틱톡 (1 row) | Below viability threshold |
| nb_channel | 뉴발란스 무신사 (37), 뉴발란스 쿠팡 (16) | Sparse, inconsistent coverage |

These groups are retained in `raw.naver_datalab_raw` for completeness but excluded from `staging.search_weekly` via `WHERE keyword_group NOT IN ('nb_social', 'nb_channel')`.

Exclusion rationale: Sparse data with irregular coverage cannot support weekly trend analysis or meaningful Share of Voice calculation. Including them would produce misleading metrics (e.g., zero-inflated time series artifacts).

---

## 5. Seasonal Decomposition — STL to MSTL Transition (Stage 3)

### 5.1 Initial Approach: STL (period=52)

Stage 3 began with standard STL decomposition (period=52, robust=True) as the baseline for seasonal analysis. This is the conventional approach for weekly data with annual seasonality.

### 5.2 Discovery: Sub-annual Quarterly Seasonality

MSTL (periods=[13, 52]) was run as a planned comparison (v3 §5.2: "잔차 분산 감소 정도"). The result was unexpected — residual variance reduction of 48–75% across all 8 brand×region time series. This was far above the 5% significance threshold, indicating a genuine quarterly (~13 week) sub-cycle exists in all sportswear search time series.

This discovery contradicted the initial expectation from Stage 0 H2, where weak SS/FW ratios (530=1.18, 992=0.93) suggested seasonality was minimal. The weak signal was an artifact of single-season analysis: STL absorbed the quarterly pattern into the annual component, distorting both.

### 5.3 Decision: MSTL Adopted as Primary

MSTL replaced STL as the primary decomposition method. STL is retained as a comparison baseline in documentation only. MSTL results (decomposition_method='MSTL') are stored in `mart.seasonal_components` alongside STL results for reproducibility.

### 5.4 SS/FW Ratio Reversal

With MSTL properly separating annual and quarterly cycles:

- **530 Korea:** ~~SS/FW=1.18 (Stage 0, STL)~~ → **SS/FW=0.86 (Stage 3, MSTL)** — reversed from SS-dominant to FW-dominant
- **992 Korea:** SS/FW=0.93 (Stage 0) → **SS/FW=0.89 (Stage 3)** — direction consistent, magnitude refined

All 5 Korea products are FW-dominant (0.71–0.99). All Global products except 1906r are SS-dominant (1.07–1.44). This Korea-FW vs Global-SS structural asymmetry is hypothesized to reflect: Korean consumers' higher fall/winter outdoor wearing frequency concentrating FW search demand, while global (primarily NA/EU) is driven by back-to-school and spring/summer running seasons. To be quantitatively verified in Stage 7.

### 5.5 Implications for Downstream Stages

- **Stage 5 (Anomaly Detection):** MSTL residuals should replace Stage 2 z-score baseline. Quarterly seasonal patterns may have caused false-positive spikes in the original `mart.anomaly_log`.
- **Stage 6 (Forecasting):** Dual-season structure means single seasonal order SARIMA is insufficient. SARIMAX with quarterly exogenous dummies, TBATS, or Chronos comparison required.
- **Stage 7 (Korea↔Global Bridge):** SS/FW ratio by product line provides a quantitative axis for cross-region structural comparison.

---

## 6. Hybrid Sentiment Analysis Methodology (Stage 3)

### 6.1 3-Way Keyword Dictionary

The sentiment dictionary (112 keywords) is divided into three categories to isolate product-level sentiment from confounding signals:

| Category | Keywords | Purpose |
|---|---|---|
| **Product** (96) | Comfort, design, quality, satisfaction | Main input for `social_sentiment_static` |
| **Channel** (14) | Shipping, returns, price, counterfeit | Excluded — reflects distribution/service, not product |
| **Resale** (2) | Premium, overprice | Separate label for NB limited edition analysis |

**"가성비"/"합리적" classification note:** Initially moved from product → channel. Post-hoc impact assessment showed restoring to product (w=+0.3) shifts brand averages by +0.002–0.006 (all < 0.01). Current channel classification retained — conservative assignment with negligible impact.

### 6.2 Sponsorship Filter

11 patterns (협찬, 체험단, 제공받, etc.) detect sponsored content. 1.3% of the 10,000-text corpus flagged. Welch t-test confirmed statistically significant sentiment difference between sponsored (+0.136) and organic (+0.378) groups (t=4.48, p=0.0005). Sponsored posts are excluded from `social_sentiment_static`.

### 6.3 Hybrid Routing: Keyword + Claude API

Keyword scoring (product category only) resolves 97.4% of texts at threshold |s| ≥ 0.3. The remaining 2.6% (261 uncertain cases) are routed to Anthropic Batch API (claude-haiku-4-5, 50% batch discount). Total cost: 35.8 KRW for 10,000 texts.

This design is intentional: BDC-relevant "case-appropriate tool + cost governance" thinking. The keyword dictionary provides transparency and reproducibility; the LLM handles edge cases where lexical rules are insufficient.

### 6.4 social_sentiment_static: Intentional Denormalization

Sentiment is broadcast as a brand-level constant to all rows in `mart.brand_kpi_weekly`, rather than stored in a separate dimension table.

**Rationale:** Social data was repositioned as cross-sectional (§2). A single scalar per brand does not justify a JOIN in every downstream query. The `_static` suffix in the column name makes the non-temporal nature explicit at the schema level.

| Brand | social_sentiment_static |
|---|---|
| new_balance | +0.289 |
| nike | +0.474 |
| adidas | +0.436 |
| puma | +0.367 |

### 6.5 Future Extension: Product-Line Sentiment Segmentation

NB's high neutral ratio (45.6%) and lowest brand sentiment (+0.289) suggest product-line-level sentiment profiles may differ significantly — 530 (comfort/착화감) vs 992 (fashion/스타일) may have distinct sentiment structures. This requires `query_keyword`-based product mapping in `raw.naver_blog_raw` and is preserved as a future extension.

---

## 7. Search ↔ CSI Leading Indicator Validation (Stage 4)

### 7.1 Question Reframing

Original framing: "Search → Sales". Revised to:

> Does brand-level micro search demand serve as a leading indicator for macro consumer sentiment (CSI), or vice versa?

CSI is not a sales proxy but a meaningful dependent variable in its own right. For an unlisted company (NB), public sales data is structurally unavailable — this is a project constraint, not a defect. The search ↔ macro-sentiment relationship itself is an actionable BDC question: "does consumer search behavior anticipate or respond to market-wide consumption temperature?"

### 7.2 Asymmetric Preprocessing

- **Search side:** MSTL residual (innovation component). Trend and seasonal are deterministic/known patterns; causal information resides in the residual's innovation. MSTL decomposition was completed in Stage 3, reusing that asset maintains project consistency.
- **CSI side:** 1st differencing (ADF-determined). CSI is monthly and cannot be MSTL-decomposed with the same [13, 52] periods. The preprocessing asymmetry is intentional and documented.

### 7.3 Multiple Testing Environment

64 tests conducted (8 brand×region pairs × 2 directions × 4 lags). At α=0.05, expected false positives ≈ 3.2. Observed significant results exceed this count, suggesting the cross-brand patterns are substantive. Individual p-values are interpreted with caution; the primary interpretation basis is the consistency of cross-brand patterns rather than any single test's significance.

### 7.4 Robustness Check: Non-stationary Residuals

adidas/global (ADF p=0.2703) and nike/global (ADF p=0.0562) residuals failed the 5% stationarity threshold. 1st differencing was applied and Granger tests re-run.

- **adidas/global:** residual diff1 ADF p=0.0000 (stationary). Search→CSI lag 3 (p=0.0409), lag 4 (p=0.0140) significance survives. Reverse direction all lags non-significant. Verdict: **robust**.
- **nike/global:** residual diff1 ADF p=0.0000 (stationary). Both directions all lags non-significant. Verdict: **Independent confirmed**, consistent with original result.

### 7.5 Causality Pattern Summary

| Brand | Global | Korea |
|---|---|---|
| adidas | Search→CSI (robust) | Feedback loop |
| new_balance | CSI→Search | CSI→Search |
| nike | Independent | Search→CSI |
| puma | CSI→Search | Independent |

**Cross-brand interpretation:**

- adidas/nike의 검색은 CSI를 선행하거나 독립적이다 — 브랜드 관성(inertia)이 거시 경기와 무관하게 검색 수요를 유지하는 구조.
- NB는 양 지역 모두 CSI→Search — 소비 심리 개선이 선행해야 검색 수요가 따라오는 경기 탄력적(elastic) 구조. 대안 해석: 상대적으로 신생/소규모 브랜드의 검색 수요가 "여유 있을 때 찾아보는" 재량적 탐색에 의존. 두 해석 모두 동일한 actionable implication으로 수렴 — **NB는 경기 하강기에 검색 수요 방어가 필요한 브랜드**이다.
- 이 비대칭은 Stage 3의 "수요-전환 갭"과 맞물린다: NB 한국은 검색 over-index(+34.94%) 대비 감성은 최하위(+0.289), 시장 선도가 아닌 시장 반응 구조에서 수요를 전환하지 못하는 패턴이 확인된다.

### 7.6 Shopping Search Caveat

Shopping-type search (Google Trends shopping category) showed no significant Granger relationship with CSI for any brand. However, this sub-analysis is limited to Google Shopping, which is not the primary shopping search channel in Korea (Naver Shopping dominates). The null result reflects channel coverage limitations, not necessarily the absence of purchase-intent ↔ CSI linkage.

### 7.7 Cointegration Finding

Engle-Granger cointegration detected in 5/8 brand×region pairs:

| Brand | Region | Coint p-value |
|---|---|---|
| adidas | korea | 0.0135 |
| new_balance | global | 0.0190 |
| new_balance | korea | 0.0008 |
| nike | korea | 0.0070 |
| puma | korea | 0.0033 |

Cointegration implies a long-run equilibrium relationship between search demand and consumer sentiment — an independent finding from Granger causality. Even when short-run dynamics differ by brand, the series revert to a shared equilibrium. NB/korea's strongest cointegration (p=0.0008) reinforces the "demand-conversion gap" narrative: NB search and consumer sentiment are tightly coupled in the long run, yet NB fails to convert this coupling into market leadership (search leads). VECM estimation deferred to Stage 7 (Korea-Global Bridge extension).

### 7.8 Neural Granger Exclusion

Neural Granger Causality (Tank et al., ICLR 2019) was considered but excluded. With 40 monthly observations, MLP/LSTM-based nonlinear causal inference faces structural overfitting risk — the original paper's experiments use thousands of timesteps. This follows the same governance pattern as the 3→2 stage Granger chain reduction (§1): attempt assessment, threshold-based rejection, documented rationale. Revisitable if data accumulation extends the time series.


---

## 8. Korea-Global Lead-Lag: DTW Methodology (Stage 4)


### Stage 4 DTW Methodology Note

Korea-Global lead-lag analysis (Stage 4 Track B) compared three input variants: raw search index, MSTL trend component, and MSTL residual. The 3-way comparison revealed that raw DTW captures seasonal phase difference (NB raw lag +48w ≈ seasonal cycle, consistent with Korea-FW vs Global-SS asymmetry from §5.4), while trend DTW isolates structural growth divergence (NB trend lag +10.4w, converging with cross-correlation +9w).

Residual DTW is excluded from primary interpretation. MSTL residuals approximate white noise, and DTW alignment between noise series produces arbitrary large lags without causal meaning. The trend component DTW is the primary basis for lead-lag inference; residual DTW is reported in supplementary tables only.

This 3-way comparison itself is a methodological contribution — demonstrating that naïve DTW on raw seasonal time series mistakes seasonal phase for lead-lag, a common pitfall in cross-region time-series analysis.


### 8.1 Why DTW Over Cross-Correlation

Stage 0 H1 used standard cross-correlation to measure Korea-Global lead-lag, producing a -167-week result for NB — a physically implausible value exceeding the entire observation window. Cross-correlation assumes a fixed, uniform time shift across the entire series, which fails when:

- The lead-lag relationship varies over time (e.g., one region leads during product launches but lags during seasonal troughs)
- Scale differences between regions distort the correlation surface
- Seasonal phase differences create phantom peaks at ~52-week multiples

Dynamic Time Warping (DTW) addresses these limitations by finding the optimal nonlinear alignment between two time series, allowing the lag to vary across the observation window.

### 8.2 3-Way Deseasonalization Protocol

A critical methodological contribution of this analysis: **raw DTW on search time series with seasonal structure produces misleading lead-lag estimates.**

Stage 3 established that Korea is FW-dominant (SS/FW ratio 0.71–0.99) while Global is SS-dominant (1.07–1.44). This structural seasonal asymmetry causes DTW to align the FW peak of one region with the SS peak of the other, producing ~52-week phantom lags.

To separate seasonal artifact from real lead-lag, three DTW variants are computed:

| Variant | Input | Measures |
|---|---|---|
| Raw | search_index | Composite signal (trend + season + noise) |
| Trend | MSTL trend component | Structural growth trajectory lead-lag |
| Residual | MSTL residual component | Innovation/shock propagation speed |

**Diagnostic:** If raw lag ≈ 52w but trend lag ≈ 5–15w, the raw result is a seasonal phase artifact. This pattern was observed for NB (48w → 10.4w), confirming the necessity of deseasonalized DTW.

### 8.3 Z-Normalization

All series are z-normalized (zero mean, unit variance) before DTW computation to ensure scale-invariant distance measurement. Without normalization, brands with larger absolute search volumes (Nike ~61 vs Puma ~11) would dominate the distance metric.

### 8.4 Residual DTW Caveat

MSTL residuals approximate white noise after trend and seasonal extraction. DTW on near-white-noise series can find spurious alignments with arbitrary large lags, because the warping path optimizer will align coincidental peaks/troughs across the series. Residual DTW results are reported for completeness but are **not used as primary evidence** for lead-lag conclusions. The trend variant is the primary analytical input.

### 8.5 NB Lead-Lag Convergence

NB's trend DTW (+10.4w) and cross-correlation (+9w) converge, providing dual-method confirmation. This convergence is the strongest evidence standard: when parametric (CC) and nonparametric (DTW) methods agree on both direction and magnitude, the result is robust to methodological assumptions.

---

## 9. Granger Interpretation Narrative (Stage 4)

### 9.1 Honest Negative Result

The primary hypothesis — "brand search Granger-causes CSI" — was supported in only 2/8 brand×region pairs (25%). This is documented as a negative result on the original question. The analytical value lies not in hypothesis confirmation but in the discovery of 4 distinct causality patterns across brands, which was not hypothesized ex ante.

### 9.2 Why Pattern Diversity Is the Finding

A uniform result (all brands showing Search→CSI) would have validated the hypothesis but provided limited practical insight — if all brands behave identically, the finding is not brand-differentiating. The observed 4-pattern classification provides brand-specific actionable intelligence:

| Pattern | Brands | BDC Implication |
|---|---|---|
| Search→CSI | adidas/global, nike/korea | Monitor as market movers — their search can signal macro shifts |
| CSI→Search | NB (both), puma/global | Macro-reactive — watch CSI as demand leading indicator |
| Feedback | adidas/korea | Bidirectional reinforcement — complex dynamics |
| Independent | nike/global, puma/korea | Brand-specific factors dominate over macro sensitivity |

### 9.3 NB-Specific Actionable Insight

For BDC's NB Korea focus, CSI→Search is the most important finding: NB Korea search demand is a lagging indicator of consumer sentiment. This means:

1. **Forecasting:** CSI (publicly available monthly) can be used as a ~2–4 month leading indicator for NB search demand.
2. **Campaign timing:** Search demand defense campaigns should be triggered proactively when CSI trends downward, not reactively after search declines are observed.
3. **Budget allocation:** During macro downturns, NB requires proportionally higher marketing investment than brands with search inertia (adidas, Nike).

### 9.4 Limitations and Future Extensions

1. **CSI as single macro proxy:** CSI reflects overall consumer sentiment, not sportswear-specific demand. Sector-specific indicators (e.g., clothing/footwear retail index) would sharpen the analysis. Currently unavailable in the ECOS collection scope.
2. **Sales data gap:** NB is unlisted, making public revenue data structurally unavailable. If BDC provides internal sales figures, the Search→Sales hop can be directly tested — the current pipeline architecture (mart.granger_results) supports this extension without schema changes.
3. **40-month observation window:** Marginal for Granger with 4 lags. Continued data collection will improve statistical power and enable re-testing with longer horizons.

---

## 10. Anomaly Detection — 3-Way Comparison (Stage 5)

### 10.1 Problem Statement

Stage 2 used rolling z-score (8-week trailing window, |z| > 2.0) on raw search_index for anomaly detection, producing 69 flagged weeks (5.0% rate). However, MSTL decomposition (Stage 3) revealed that quarterly (13w) and annual (52w) seasonal patterns dominate the raw signal. Rolling z-score cannot distinguish between a genuine anomaly and a predictable seasonal peak, because the 8-week window is shorter than the 13-week quarterly cycle.

Stage 5 quantifies this problem: 91.3% of Stage 2 anomalies were seasonal artifacts — false positives caused by quarterly pattern peaks/troughs falling within the z-score threshold.

### 10.2 Three Methods

| Method | Input | Anomaly Criterion | Rationale |
|---|---|---|---|
| Rolling Z-score (baseline) | Raw search_index | \|z\| > 2.0, 8-week trailing window | Stage 2 replication for comparison |
| MSTL Residual Z-score | MSTL residual (trend + season removed) | \|residual / std\| > 2.0 | Deseasonalized anomaly detection |
| Isolation Forest | MSTL residual | contamination=0.05 | Non-parametric, distribution-free |

All three methods use identical threshold/rate parameters (|z| > 2.0 or contamination=0.05) to enable fair comparison. Per advisor decision, brand-specific thresholds were explicitly avoided — uniform thresholds allow anomaly rate differences between brands to emerge as findings rather than artifacts of parameter tuning.

### 10.3 Per-Series Independent Analysis

Each of the 8 brand × region time series is analyzed independently. Rationale: Stage 3 MSTL showed that variance structures differ substantially across series (puma global std=0.48 vs nike korea std=4.51). Multivariate Isolation Forest would conflate these scales, causing one brand's normal range to overlap with another's anomaly zone.

This decision is consistent with Stage 4 Granger findings — each brand has a structurally different relationship with macro sentiment, so anomaly patterns should also be brand-specific.

### 10.4 M+IF Independence Limitation

MSTL Residual and Isolation Forest both operate on the same input (MSTL residual). Their agreement (52 of 54 two-way cases) reflects input sharing, not methodological convergence. This is not independent cross-validation.

Only agreement that includes the Z-score method constitutes true cross-validation, because Z-score uses the raw time series with a rolling window — an entirely different input and methodology.

This distinction motivated the Tier structure for investigation prioritization:
- **Tier 1 (Z included):** Independent cross-validation. 7 anomalies.
- **Tier 2 (M+IF only, macro/multi-brand):** Same-input agreement with co-occurrence pattern adding value. Investigation limited to multi-brand weeks.
- **Excluded:** M+IF only, single-brand — no independent validation, insufficient investigation value.

### 10.5 Event Matching Design

**Window:** Strict `event_date BETWEEN week_start AND week_start + 6`. For range events: `week_start BETWEEN event_date AND event_end_date`. No ±1 week extension — extending would create false matches where events from adjacent weeks (e.g., 3 NB events in 9/10, 9/15, 9/17) inflate Precision.

**Brand logic:** macro_event (brand=NULL) matches any brand anomaly in the matching week. Brand-specific events match only that brand. When multiple events match one anomaly, the closest date is designated primary; others are secondary.

**Coverage period filter:** Precision denominator includes only anomalies within events_calendar coverage period (2024-02 ~ 2025-04, 14 of 40 months). Anomalies outside this range have no matchable events by construction, and would artificially depress Precision.

### 10.6 Evaluation Framework

**Precision** is reported in a 2×2 matrix: {Tier 1, Tier 1+2} × {all matches, ex-macro matches}. This structure prevents macro_event matches (which match all brands in a week) from inflating the headline number.

**Event Detection Rate** replaces "Recall" because events_calendar was constructed anomaly-driven (anomaly first → event retroactive search). This means the calendar structurally overrepresents events that coincide with anomalies, inflating any Recall metric. The `event_origin` tag separates:
- `scheduled` (7 events): Known independently of anomaly detection (Olympics, Air Max Day, Black Friday, CSI data, London Marathon, AJ3 Black Cement). These form an honest Recall denominator.
- `investigated` (18 events): Found by searching for what caused a detected anomaly. These cannot form a Recall denominator without circular reasoning.

### 10.7 Air Max Day Spillover Finding

Air Max Day 2024 (March 26, brand=nike) was undetected — not because the matching window missed it, but because Nike had no anomaly in that week. Instead, adidas and NB showed anomalies. Interpretation: Air Max Day is absorbed by Nike's own MSTL seasonal component (predictable annual event), but generates search spillover to competitors whose seasonal models do not anticipate it. This is a methodologically meaningful asymmetry, not a matching failure.

---

## 11. Forecasting Methodology (Stage 6) — DRAFT

### 11.1 Forecast Target and Horizon

Forecast target: NB Korea and NB Global weekly search_index from mart.brand_kpi_weekly. These two series form the core CSI → NB Korea → NB Global chain narrative (Stage 4). Other brands excluded — 4-brand × 2-region expansion offers low marginal value relative to implementation cost, and NB is the project's primary analytical subject.

Forecast horizon: 26 weeks (test set). This spans two quarterly cycles (13w × 2), ensuring the test window contains at least one full period of both annual (52w) and quarterly (13w) seasonality discovered in Stage 3 MSTL decomposition. A 12-week test would not complete a single quarterly cycle, making it impossible to evaluate whether models capture seasonal patterns.

Train: 148 weeks. This is short for deep learning but sufficient for SARIMAX with exogenous variables.

### 11.2 Exogenous Variable: CSI Forward-Fill

ECOS Consumer Sentiment Index (stat_code 511Y002) is the sole exogenous variable, justified by Stage 4 Granger causality (CSI → NB Korea search, unidirectional, p<0.05).

CSI is published monthly. Conversion to weekly granularity uses forward-fill: each week inherits the CSI value of its containing month. This assumes "the published CSI for a given month is the best available estimate of consumer sentiment for all weeks within that month." No interpolation or smoothing is applied — forward-fill is the most conservative assumption and avoids introducing artificial high-frequency variation.

### 11.3 Seasonality Handling: Fourier Terms

Stage 3 MSTL confirmed dual seasonality: annual (52w) and quarterly (13w). Three options were evaluated for incorporating seasonality into SARIMAX:

**Option 1: Seasonal ARIMA (seasonal_order with s=52).** Rejected. With 148 training observations, estimating seasonal AR/MA parameters at s=52 creates severe degrees-of-freedom constraints. The model would need to estimate parameters linking observations 52 weeks apart, with fewer than 3 complete annual cycles available. Convergence failures are expected.

**Option 2: Quarterly dummy variables.** Rejected. Dummy variables model seasonality as abrupt level shifts at quarter boundaries. Stage 3 MSTL seasonal components showed smooth sinusoidal patterns, not step functions. Dummies would misrepresent the shape of seasonal variation and waste parameters on an incorrect functional form.

**Option 3: Fourier terms as exogenous regressors.** Selected. Fourier pairs sin(2πkt/T) and cos(2πkt/T) for period T and harmonic k naturally represent smooth cyclical patterns. This follows Hyndman & Athanasopoulos's recommended "ARIMA + Fourier" approach for long-period seasonality.

Configuration: K=2 for T=52 (annual) + K=2 for T=13 (quarterly) = 8 Fourier columns. K=2 captures the fundamental frequency and first harmonic for each period. K≥3 was rejected because total parameter count (ARIMA order + 9 exogenous + intercept ≈ 12-14 parameters) against 148 observations must maintain at least 10:1 ratio.

The Fourier index t is sequential (0, 1, ..., n-1) starting from the first training observation. For test-period forecasting, t continues seamlessly (148, 149, ..., 173), ensuring phase continuity.

### 11.4 SARIMAX Order Selection

**Stationarity:** ADF test on raw series: Korea p=0.020 (borderline stationary), Global p=0.264 (non-stationary). d=1 differencing applied to both — Korea's ADF is marginal, and auto_arima with d=1 yields lower AIC.

**Order search:** pmdarima auto_arima with seasonal=False (seasonal structure handled by Fourier exogenous), d=1 fixed, max_p=5, max_q=5, stepwise=True, information_criterion=AIC.

**Results:** Korea (0,1,1), Global (0,1,0). Manual comparison of 6-7 candidate orders confirmed auto_arima selections as AIC-optimal in both series.

**Global (0,1,0) interpretation:** A random walk with drift. The series has no AR or MA structure, meaning no autocorrelation-based predictive information exists. Trend is captured by the drift term, while seasonality and macro environment are explained by Fourier and CSI exogenous variables. This is recorded as Data Point 15.

### 11.5 Prophet Design and Ablation

Prophet (Facebook/Meta, 2017) decomposes time series into trend + seasonality + regressors using a Bayesian structural model. Its key differentiator from SARIMAX is **automatic changepoint detection** — the trend is modeled as a piecewise linear function with changepoints selected from the training data.

**Configuration:** `seasonality_mode='additive'` (search index 0-100, variance not level-proportional), `changepoint_prior_scale=0.05` (default, conservative on 174 weeks). CSI added via `add_regressor('csi')` for feature parity with SARIMAX/LSTM.

**Custom seasonality:** Prophet default `yearly_seasonality=True` uses `fourier_order=10` (20 Fourier columns). To ensure fair comparison with SARIMAX (K=2, 4 columns), yearly seasonality was manually set to `fourier_order=2`. Quarterly seasonality added as `period=91.25` days (13 weeks × 7), `fourier_order=2`.

**Ablation methodology:** Two Prophet variants were compared — K=2 (SARIMAX parity) and K=10 (Prophet default) — to separate changepoint detection effect from Fourier flexibility effect:

| Region | Changepoint contribution | Fourier K=10 contribution |
|---|---|---|
| Korea | 147% (sole driver; K=10 harmful) | -47% (overfitting) |
| Global | 66% (primary) | 34% (secondary) |

This ablation demonstrates that changepoint detection is the primary source of Prophet's advantage. For short event-driven series (Korea), excessive Fourier terms actively degrade performance by overfitting annual seasonality with insufficient data support.

**CSI regressor coefficient comparison:** Prophet CSI regressor coefficients (Korea -0.09, Global +0.002) are near-zero, contrasting sharply with SARIMAX (Korea +3.98, Global +2.01). This divergence is not a contradiction but a consequence of model architecture: Prophet's flexible trend and SARIMAX's rigid drift partition the same variance differently.

Prophet's 25 piecewise trend changepoints absorb CSI-correlated structural variation because both CSI and the piecewise trend capture the same underlying signal — macro-environment-driven demand level shifts. When Prophet's trend component claims this variance first, the CSI regressor has no marginal effect remaining. SARIMAX's ARIMA(0,1,0)/(0,1,1) has only a simple drift for trend, so CSI must absorb all level-change information, producing the large positive coefficients.

This means Prophet's advantage (changepoint detection) and CSI coefficient disappearance are two sides of the same phenomenon. Prophet implicitly encodes CSI-equivalent information through trend breakpoints. Data Point 16's CSI elasticity asymmetry (Korea 3.98 vs Global 2.01) reflects real demand structure but is observable only in models with rigid trend specification.

### 11.6 LSTM Architecture Decisions

**Feature parity:** LSTM receives identical input features to SARIMAX (search_index + CSI + 8 Fourier terms = 10 features). This ensures the 3-way comparison tests model architecture differences, not feature engineering differences. Adding LSTM-only features would confound the comparison.

**No Attention mechanism:** With 174 total observations and lookback=13, the maximum number of training sequences is ~113. Attention mechanisms require sufficient batch diversity to learn "where to attend" within the lookback window. At 113 sequences, attention parameters would overfit to training-specific patterns. A simpler 2-layer stacked LSTM is more appropriate.

**Model capacity vs sample size:** The LSTM has 52,801 parameters against 113 training sequences — a 467:1 ratio. This is structurally overfitting and explains why LSTM underperforms SARIMAX on Korea. Early stopping (patience=30) and dropout (0.3) mitigate but cannot overcome this fundamental mismatch. For comparison, well-performing LSTM applications typically operate at 1:10 to 1:100 parameter-to-sample ratios.

**Validation split:** 15% of training data (~22 weeks) held for early stopping validation. Effective training set: ~126 weeks. The 3-way train/val/test partition creates structurally small datasets at each stage — an inherent limitation of applying DL to 174-week series.

**Recursive forecasting:** 26-week horizon generated one step at a time, with each predicted value fed back as input for the next step. This accumulates prediction errors but represents the realistic operational scenario where future actuals are unavailable.

### 11.7 Chronos Zero-Shot Design

Chronos (Amazon, 2024) is a T5-based pretrained time series foundation model. It tokenizes time series values via scaling and quantization, then generates probabilistic forecasts through autoregressive sampling.

**Univariate design is intentional.** Chronos receives only the search_index series — no CSI, no Fourier terms. This is not an oversight but a deliberate comparison axis: "what can a foundation model achieve with temporal patterns alone, without domain exogenous variables?" If Chronos outperforms SARIMAX+CSI, it demonstrates that foundation model pattern recognition exceeds domain feature engineering. If it loses, it demonstrates that domain exogenous variables (CSI) provide irreplaceable predictive information that pre-training cannot substitute.

**Two model sizes:** chronos-t5-small (~46M params) and chronos-t5-base (~200M params) run on M2 MacBook CPU. Both produce 20 probabilistic samples; median serves as point forecast, 10th/90th percentiles as uncertainty bounds.

### 11.8 Anti-Scaling Finding

Chronos-small outperforms Chronos-base in both NB Korea and NB Global. This contradicts the general scaling law expectation that larger models perform better.

Explanation: Chronos was pre-trained on diverse time series datasets with thousands to tens of thousands of timesteps. The base model's larger capacity encodes longer-range temporal dependencies learned from these long series. When applied to a 174-week context, these longer-range patterns have no empirical support in the data and act as noise — the model's prior overwhelms the evidence.

This is recorded as Data Point 17 and has practical implications: for short time series (< 200 timesteps), smaller foundation models may be preferred over larger variants.

### 11.9 Evaluation Framework

**Primary metric: RMSE.** Chosen because all three models produce forecasts on the same scale (search_index 0-100), enabling direct comparison. RMSE penalizes large errors, which is desirable for detecting whether models miss event-driven spikes.

**Secondary metrics: MAE and MAPE.** MAPE excludes weeks with search_index = 0 to avoid division artifacts. MAPE provides scale-independent interpretability.

**Anomaly-week analysis caveat:** Test set contains n=1 anomaly week per region. Single-observation RMSE comparison is not statistically meaningful and should not be interpreted as evidence of anomaly prediction capability.

**Train in-sample residual analysis (supplementary):** SARIMAX re-fit on training data, in-sample residuals compared for anomaly vs normal weeks. Anomaly/normal mean |residual| ratio: Korea 1.17x, Global 1.22x. However, in-sample residuals measure fit quality (the model learned from these weeks), not prediction quality. Out-of-sample anomaly-specific evaluation would require rolling/expanding window cross-validation, but with 0-2 anomalies per test fold, statistical power is absent. This is a structural limitation of short time series forecasting, not a methodological gap.

**CSI elasticity vs event override:** The SARIMAX CSI coefficients (Korea 3.98, Global 2.01) describe the average structural relationship between consumer sentiment and search demand. However, Stage 5 Data Point 12 demonstrates that strong event stacking can produce positive search spikes even during CSI troughs (e.g., 2025-03-23 z=+3.00 and 2025-04-20 z=+4.24 occurred at CSI 93-94). The CSI-based forecast captures baseline demand trajectory; event-driven spikes operate on a separate, structurally unpredictable layer. This dual-layer framing — predictable baseline (CSI + seasonality) vs unpredictable spikes (events) — is the honest characterization of forecast capability on this series.

### 11.10 Korea-Global Performance Divergence

The finding that Korea favors SARIMAX while Global favors LSTM is not random — it follows from the series' structural properties:

**Korea:** Strong annual seasonality (Fourier 52w significant), event-driven spikes (Stage 5 anomaly density), CSI-reactive demand. SARIMAX's explicit Fourier terms and CSI coefficient capture these structures parsimoniously. LSTM's 467:1 param/sample ratio cannot learn the same structures more efficiently.

**Global:** No autoregressive pattern (ARIMA 0,1,0), weak annual seasonality (Fourier 52w non-significant), smoother dynamics. LSTM's ability to model nonlinear interactions between CSI and sub-quarterly Fourier terms provides an advantage that the linear random walk model cannot achieve.

This divergence supports the methodological choice to run multiple model families rather than selecting a single "best" approach ex ante. It also validates the decision to forecast both NB Korea and NB Global rather than selecting one — a single-series analysis would have missed the structural split and led to a misleading generalization about model superiority.

## 12. Korea-Global Bridge — Methodology Validation Stage (Stage 7)

Stage 7 was designed to verify the CSI → NB Korea → NB Global 3-stage chain hypothesis. Across **5 independent methodological dimensions** (VARX bidirectional, monthly Granger bidirectional, mediation bidirectional × 2 transformations, lagged cointegration bidirectional), all 11 individual tests rejected the chain hypothesis. The verification process surfaced three self-diagnostic findings — DP20 (mediation spurious correlation pre-emption), DP23 (MSTL forward-looking leakage), DP24 (Stage 4 sign convention inversion) — redefining Stage 7's role from hypothesis testing to methodology validation. Sub-sections below summarize each methodology component; full quantitative details and analytical artifacts are documented in `stage7_checkpoint.md`.

### 12.1 Frequency Mismatch — Option H Hybrid Resolution

CSI exists at monthly frequency (41 observations) while Korea/Global search operate at weekly frequency (174 observations). Three resolution options were considered: full monthly aggregation (Option M, lag resolution loss), full weekly forward-fill (Option W, spurious autocorrelation), and hybrid Option H. Option H was adopted: Stage 4's existing monthly Granger results re-used for the CSI→Korea/Global hop, with Stage 7's new bidirectional analysis at weekly resolution using forward-filled CSI as control covariate. This preserves Stage 4's quantitative findings while exploiting weekly degrees of freedom for the new Korea↔Global tests. Limitation acknowledged: forward-fill introduces step-function artifact in CSI series, addressed via diff1 robustness checks (DP20).

Cross-reference: `stage7_checkpoint.md` Step 0 + Decision 1.

### 12.2 VARX(2) Design — Search d1 Endogenous + CSI Distributed Lag

VARX(2) endogenous variables: `korea_search_d1`, `global_search_d1` (both ADF stationary p=0.0000). Lag selection via VAR.select_order(maxlags=13) returned p=1 across AIC/BIC/HQIC/FPE. CSI exogenous treated as distributed lag {0, 4, 8, 12} weeks per Stage 4 monthly Granger pattern (NB significant at 1–4 month lags = 4–16 weeks); lag 0 contemporaneous mandatory to avoid underspecification of macro reactivity. Bidirectional Granger within VARX returned null (Korea→Global F=1.45 p=0.23; Global→Korea F=0.23 p=0.63); joint LR for CSI distributed lag marginal (p=0.0886) with only `csi_d1_l0` significant in the Global equation. Result: short-run weekly causal channel absent in both directions, with contemporaneous CSI macro reactivity preserved.

Cross-reference: `stage7_checkpoint.md` Track A1 + Decision 3.

### 12.3 Mediation Analysis — Bidirectional Joint Block Bootstrap

Baron-Kenny three-regression mediation with joint Moving Block Bootstrap (13w block, Hall-Horowitz √n) primary + Stationary Bootstrap robustness, 5000 iterations, BCa 95% CI. Pre-committed Decision 7 thresholds (4-bin % indirect classification) prevent HARKing. Two transformations (trend, diff1) × two directions (Korea→Global pre-DP24, Global→Korea post-DP24) = 4 cells × 5000 iter = 20,000 bootstrap fits per direction. All four cells return BCa CI containing zero — mediation channel absent in both directions and both transformations. Sign correction comparison surfaces three quantitative signatures of correct directional specification (§12.3.5 expansion below + §12.4 Track A3 third signature).

Cross-reference: `stage7_checkpoint.md` Track A1' + Decision 4.

### 12.3.5 Stage 7 as Methodology Validation Stage

Stage 7 was designed to verify the 3-stage chain hypothesis (CSI → NB Korea → NB Global). Execution surfaced three cumulative self-diagnostic findings, each detected without external review through internal sanity checks:

**DP20 — Mediation spurious correlation pre-emption.** Step 0 stationarity re-check identified that monthly-aggregated trend components produce non-stationary regression inputs, which would generate spurious mediation coefficients regardless of true causal structure. Alternative specifications (diff1, residual) were committed pre-execution, preventing post-hoc result chasing.

**DP23 — MSTL forward-looking leakage.** Track A3 narrative-negative result (Korea trend exogenous → Prophet RMSE +59%) triggered self-diagnostic that revealed MSTL decomposition uses two-sided STL filter, leaking future information into trend component. This invalidated Track A3 design and prompted leakage-free replication.

**DP24 — Stage 4 sign convention inversion.** Leakage-free DTW + CC re-computation classified results as direction_flipped relative to Stage 4 labels. Synthetic test data (Korea leads Global by 5w) confirmed Stage 4 code returns CC −5, DTW −4.57 — magnitude correct, sign convention inverted. Mediation re-run with corrected direction validated: inconsistent mediation signature dissipated (% indirect 120% → 11%), CI width narrowed 47%, both quantitative signatures of correct directional specification.

**Cumulative implication.** Stage 7's value lies less in the hypothesis test result (chain rejected) than in the verification process. For BDC roles requiring internal data analysis, the demonstrated competency is **self-skepticism + multi-method validation**. Three critical findings were surfaced without external reviewer, indicating the analytical discipline transferable to enterprise contexts where external validation is rare.

### 12.4 Korea Trend / Global Trend Exogenous (Sign-Corrected, Track A3)

Original Track A3 (Korea trend → Global Prophet) invalidated by DP23 (MSTL forward-looking leakage) and DP24 (Stage 4 sign convention inversion). Re-design: Global trend → Korea Prophet, raw `global_search` lagged primary (leakage-free), expanding-window MSTL fallback. Triple comparison (Prophet baseline / +CSI / +CSI+Global_lag11) at lag 11w (paired-fold CV winner, 8/9 lags within ±1 SE — statistically indistinguishable, ±1–2w uncertainty disclosed). Both Prophet and SARIMAX show consistent degradation: Prophet −9.01%, SARIMAX −10.94%, both DM p<0.001. Outcome: 4th scenario (degradation) added to the pre-committed 3-way matrix; auto-classifier patch (unsigned→signed delta) self-detected and applied. DP24 quantitative validation third signature: pre-correction Korea→Global degradation +41~59% → post-correction Global→Korea degradation +9~11% = 1/4–1/5 magnitude reduction. Sentinel framing operational refinement: Global signal serves as monitoring leading indicator (directional reference) but not as predictive feature in forecast models.

Cross-reference: `stage7_checkpoint.md` Track A3 + §12.4.1–§12.4.5.

### 12.5 Seasonal Lead Asymmetry — Track B1 (Nested in A3 Re-design)

Sign-corrected Global → Korea lag estimation split by Korea's FW (Week 40–13) vs SS (Week 14–39) seasons. Both seasons show degradation (FW −3.64%, SS −1.78%); seasonal magnitude difference modest. Korea forecast model's resistance to Global signal as exogenous holds across the FW/SS structural divide documented in Stage 3. Absolute RMSE asymmetry (FW 2.20, SS 4.21) reflects Stage 3's Korea FW-dominant search behavior producing tighter seasonal forecasts but does not modulate the degradation direction. Seasonal asymmetry null result — interference effect is season-robust.

Cross-reference: `stage7_checkpoint.md` Track B1.

### 12.6 Mechanism — Three Plausible Hypotheses (Sign-Corrected Direction)

Stage 7 quantitative analysis confirms Global → Korea lead of ~10w with magnitude robustness. The mechanism — **why** Global precedes Korea — cannot be tested with the project's data scope. Three face-validity hypotheses are documented for future verification with BDC internal data:

**Hypothesis 1 — Global brand attention precedence (cultural/demographic).** US/EU markets are NB's primary consumer base. Global brand-level search demand responds to product launches, marketing campaigns, and category trends earlier because the demographic concentration drives signal magnitude. Korea search demand follows after diffusion through K-fashion intermediaries.

**Hypothesis 2 — HQ marketing trigger (operational).** Global headquarters campaign cycles initiate at Global market level. Region campaigns (Korea) follow with localization lag. The ~10w lag corresponds to typical HQ-to-region campaign rollout cycles.

**Hypothesis 3 — Differential reactivity to common drivers (structural).** Both Korea and Global respond to common shocks (CSI, cultural events) but with different reactivity speeds. Global market's larger sample size enables faster signal detection, while Korea market's smaller scale produces noisier short-term response, manifesting as apparent lag.

**Distinction not testable in current scope.** All three hypotheses produce observationally equivalent ~10w Global-leads-Korea pattern in aggregate search data. Discriminating mechanism requires BDC internal data: campaign timeline records, market-level demographic decomposition, region-specific sentiment lag. This delineation defines the boundary between this project's contribution and in-role analytical extension.

### 12.7 Stage 7 → Stage 8 Handoff: Forecast & Bridge Tab Integration

Stage 8 implements a unified BDC analytics dashboard (Streamlit primary + Power BI Service auxiliary) consuming Stage 7's quantitative outputs. The handoff has five operational components.

#### 12.7.1 Forecast Model Selection (Stage 6 + Stage 7 cascade)

Stage 6 4-way comparison established Prophet as primary forecast model for both Korea and Global series (Korea RMSE 5.57, Global 2.54, both first ranked). Stage 7 Track A3 refines this for Korea forecast specifically: Korea Prophet input scope = CSI exogenous only (Korea autoregressive structure preserved); Global lagged signal explicitly excluded due to documented degradation (Prophet −9.01%, SARIMAX −10.94%, DM p<0.001). Stage 8 Forecast tab implements Prophet for both regions with this asymmetric exogenous structure: Korea (CSI only), Global (CSI only), preventing the cross-region interference identified in Track A3.

#### 12.7.2 Bridge Tab Right-Panel Integration

Stage 8 dashboard adopts a "Forecast & Bridge" tab consolidating Stage 6's forecasting output with Stage 7's chain diagram visualization (Track C). The right panel surfaces three artifacts: (1) Global trend MA as monitoring leading indicator visualization (KPI 7 redefinition), (2) `chain_diagram_data.json` node/edge structure rendering CSI/Global/Korea relationships with sign-corrected direction labels and `operational_use` metadata distinguishing monitoring vs predictive scope, (3) Mirror Sentinel + Differential Reactivity narrative tooltip surfacing the BDC operational interpretation. Korea Prophet forecast chart occupies the left panel; the right panel does not feed into the forecast model — operational asymmetry between visualization and prediction is itself documented in the dashboard tooltip as design rationale.

#### 12.7.3 KPI 7 Operational Implementation

KPI 7 redefinition (Korea trend MA → Global trend MA) propagates to two dashboard locations: (a) Streamlit Forecast tab right panel with 4-week moving average overlay on Global search index time series, displayed with ~10w forward-shift annotation indicating typical Korea anticipation horizon; (b) Power BI HQ Bridge tab summary card displaying current Global trend direction (rising / flat / declining) with interpretive caption "Korea demand directional reference — not predictive input." The monitoring-vs-predictive scope distinction is surfaced in tooltip help text on both implementations to prevent misuse as forecast model input.

#### 12.7.4 Migration 011 Retrofit Status

Migration 011 (`011_korea_global_lag_sign_correction.sql`) applied 2026-05-03 to `mart.korea_global_lag` table: 12 rows sign-flipped (`mean_lag_weeks`, `median_lag_weeks`, `cc_best_lag_weeks`) + `lag_direction` labels swapped. NB deseason methods now consistently report "Global leads" direction. Stage 8 dashboard Streamlit code queries this table directly with sign-corrected direction labels — no further translation logic required. `stage4_checkpoint.md` preserves original analysis with Sign Correction Notice footnote (trace value).

#### 12.7.5 Methodology Asset Propagation (KPI 12, KPI 13)

Two new KPIs from Stage 7 represent governance assets transferable to future analyses: KPI 12 (5-Dimension Orthogonal Null Verification Pattern) and KPI 13 (Methodology Validation Stage Pattern). These are surfaced in the Stage 8 Methodology Documentation tab (6th tab) as governance assets, separated from operational metrics (Tab 1-5) by design. Implementation includes 5-dim null heatmap (11/11 REJECT visualization), DP20→DP23→DP24 cascade flow diagram, and DP24 before/after signature chart. Interview narrative: KPI 12/13 represent transferable analytical discipline — Stage 7's value extends beyond project-specific findings to enterprise-grade analytical governance protocols. For interview narrative, KPI 12/13 represent the "transferable analytical discipline" framing — Stage 7's value extends beyond project-specific findings to enterprise-grade analytical governance protocols.


### 12.8 Stage 8 Dashboard Implementation Record (2026-05-03)

Stage 8 implemented the BDC analytics dashboard as Streamlit web application, deployed to Streamlit Cloud. Live URL: https://sportswear-brand-monitor-newbalance.streamlit.app/

**Architecture:** Dual data source design — PostgreSQL (local development via `database.connection.get_conn()` context manager) with automatic CSV fallback (Streamlit Cloud deployment, zero infrastructure cost). Toggle: `USE_CSV_FALLBACK` environment variable or auto-fallback on `psycopg2` import failure.

**6-Tab Structure:**

| Tab | KPIs | Key Visualizations |
|-----|------|--------------------|
| Weekly KPI | 1, 2, 3, 5, 6, 10 | 4 KPI cards + 4-brand search trend + SoV stacked area + 530 dependency ratio |
| Season | 4 | Season position (SS/FW) + YoY overlay + weekly seasonal pattern + product mix by season |
| Channel | 2 | SoV Korea vs Global grouped bar + divergence timeline + product gap (574/2002r) |
| Anomaly | 4, 8, 9 | 3-way detection timeline + method agreement monthly + spike/dip breakdown + event stacking |
| Forecast & Bridge | 6, 7, 10, 11 | Prophet 26w with CI + 4-way model comparison + chain diagram + Global 4w MA |
| Methodology Doc | 12, 13 | 5-dim null heatmap + DP cascade flow + DP24 signature chart + 4-layer narrative cards |

**Stage 7 Narrative Surfacing (5 locations):** (1) Sidebar About — 4-layer one-line summary, (2) Tab 5 chain_summary.png + chain_diagram_data.json visualization, (3) Tab 5 monitoring vs predictive caption, (4) Tab 5 degradation evidence expander, (5) Methodology Doc tab — KPI 12/13 full governance asset visualization.

**Migration 011 Verification:** `mart.korea_global_lag` queried directly with sign-corrected column names (`deseason_method`, `lag_direction = 'Global leads'`). CSV export post-Migration 011 confirmed 12 rows.

**Data Export:** `dashboard/export_csv.py` produces 11 CSV files (7 mart queries + 4 forecast CSVs) totaling 5,253+ rows for Streamlit Cloud static deployment.
