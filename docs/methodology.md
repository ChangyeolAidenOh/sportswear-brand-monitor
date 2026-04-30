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

Social metrics appear in `mart.brand_kpi_weekly` as `social_mention_count` and `social_sentiment_avg` (Stage 3), but these are descriptive context variables — not inputs to the Granger VAR model.

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
