# Methodology — Analysis Design Decisions

**Project:** Global Sportswear Brand Performance Monitor
**Author:** Changyeol Oh
**Last updated:** 2026-04-30

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

