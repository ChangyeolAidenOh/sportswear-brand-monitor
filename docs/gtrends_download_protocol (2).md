# Google Trends CSV Download Protocol v3

**Date:** 2026-04-29
**Author:** Changyeol Oh
**Revision:** v3 — Macro/Pre-Validation 폐기, Apparel Seasonality(E1/E2) 신설

---

## Architecture

| Layer | Purpose | Downloads | Period |
|---|---|---|---|
| **Brand** | 4-brand competitive SoV, 한글/영어 비중 | A1-3, B1-2 | 3 years |
| **Product (Micro)** | NB model-level portfolio | D1, D2 | 3 years |
| **Apparel Seasonality** | NB 시즌 타이밍 + 경쟁사 패딩 비교 | E1, E2 | **5 years** |

## Key decisions

1. **Korea: Search term (한글+영어 개별 입력)** — A1에서 8 columns, 한글/영어 비중 자동 분리
2. **Worldwide: Entity per brand** — brand_topics.csv 기준
3. **Chunking:** 1년 단위, 1개월 overlap, stitch_gtrends.py
4. **B3 제외:** Worldwide Shopping Entity 데이터 2025 이전 부재
5. **C1 제외:** A1에서 한글/영어 분리 수집으로 대체
6. **M1/M2 폐기:** "뉴발란스 의류" 검색 0. 카테고리 단어로는 검색 안 함
7. **P-KR/P-WW 폐기:** Stage 0 그래프로 이미 검증 완료
8. **E1/E2 5년:** 시즌 사이클 4~5회 반복 확인 필수

## Chunking protocol (3-year groups)

| Chunk | Period | Overlap |
|---|---|---|
| 1 | 2023-01-01 ~ 2023-12-31 | — |
| 2 | 2023-12-01 ~ 2024-11-30 | 2023-12 |
| 3 | 2024-11-01 ~ 2025-10-31 | 2024-11 |
| 4 | 2025-10-01 ~ 2026-04-19 | 2025-10 |

## Chunking protocol (5-year groups — E1, E2 only)

| Chunk | Period | Overlap |
|---|---|---|
| 1 | 2021-01-01 ~ 2021-12-31 | — |
| 2 | 2021-12-01 ~ 2022-11-30 | 2021-12 |
| 3 | 2022-11-01 ~ 2023-10-31 | 2022-11 |
| 4 | 2023-10-01 ~ 2024-09-30 | 2023-10 |
| 5 | 2024-09-01 ~ 2025-08-31 | 2024-09 |
| 6 | 2025-08-01 ~ 2026-04-19 | 2025-08 |

## Entity mapping (confirmed)

| Brand | Selected | Type | MID |
|---|---|---|---|
| Nike | 나이키 (기업) | Entity | /m/0lwkh |
| Adidas | ADIDAS (패션 브랜드) | Entity | /g/1ym_1qtkc |
| Puma | PUMA (신발 회사) | Entity | /m/03r_n_ |
| New Balance | NB (Footwear company) | Entity | /m/08dr90 |

---

## Download matrix

### Group A: Brand — Korea (Search term) ✅ COMPLETED

| # | File | Keywords | Type |
|---|---|---|---|
| A1 | brands_kr_web.csv | 뉴발란스, New Balance, 나이키, Nike, 아디다스, Adidas, 푸마, Puma | Web |
| A2 | brands_kr_youtube.csv | (same) | YouTube |
| A3 | brands_kr_shopping.csv | (same) | Shopping |

### Group B: Brand — Worldwide (Entity) ✅ COMPLETED

| # | File | Keywords (Entity) | Type |
|---|---|---|---|
| B1 | brands_ww_web.csv | NB / Nike / ADIDAS / PUMA | Web |
| B2 | brands_ww_youtube.csv | (same) | YouTube |

### Group D: Product — NB Model Portfolio

| # | File | Keywords (Search term) | Region | Type |
|---|---|---|---|---|
| D1 | products_kr_web.csv | 뉴발란스 530, 뉴발란스 992, 뉴발란스 574, 뉴발란스 2002R, 뉴발란스 327 | Korea | Web |
| D2 | products_ww_web.csv | new balance 990, new balance 574, new balance 9060, new balance 2002R, new balance 1906R | Worldwide | Web |

**2002R: Korea/Worldwide 양쪽 공통 앵커.**

**선정 근거:**
- Korea: 530(누적 200만, 이랜드 제안 복각), 992(2025 재발매), 574(스테디), 2002R(앵커), 327(여성 인기)
- Worldwide: 990(헤리티지 플래그십), 574(글로벌 검색 1위), 9060(StockX 바이럴), 2002R(앵커), 1906R(콜라보)

**임계 필터:** 스티칭 후 avg ratio < 10인 모델은 분석에서 제외. 근거는 data_feasibility_report.md에 기록.

### Group E: Apparel Seasonality & Competitive (5 years)

**분석 목적:** 단순 "겨울에 패딩 올라간다"가 아닌 운영 인사이트 추출.

**인사이트 1 — 시즌 시작 타이밍:**
NB 패딩/바람막이/반팔의 시즌 시작 주차를 5년간 정량화.
정의: 7주 이동평균이 연간 baseline(52주 평균) 대비 +30% 처음 도달하는 주.
→ "NB 패딩은 매년 평균 N월 M주차에 검색 상승 시작" = BDC 운영 룰

**인사이트 2 — 경쟁사 타이밍 비교:**
NB vs 나이키 vs 아디다스 vs 노스페이스 패딩의 시즌 시작 주차 차이.
→ "NB 패딩은 노스페이스 대비 N주 늦게/빨리 검색 상승 시작" = 마케팅 타이밍 조정 근거

| # | File | Keywords (Search term) | Region | Type | Period |
|---|---|---|---|---|---|
| E1 | nb_apparel_seasonality_kr.csv | 뉴발란스 패딩, 뉴발란스 바람막이, 뉴발란스 반팔, 뉴발란스 신발 | Korea | Web | **5 years** |
| E2 | padding_competitive_kr.csv | 뉴발란스 패딩, 나이키 패딩, 아디다스 패딩, 노스페이스 패딩 | Korea | Web | **5 years** |

**제외 키워드 (검증 결과 검색량 부족):**
- "뉴발란스 의류" — 카테고리 단어, 5년 평균 0
- "뉴발란스 맨투맨" — 5년 평균 0

---

## Cancelled downloads (with rationale)

| Original | Reason |
|---|---|
| M1 nb_category_macro_kr | "뉴발란스 의류" 검색 0 |
| M2 nb_category_macro_ww | "new balance clothing" 검색 0 추정 |
| P-KR products_kr_prevalidation | Stage 0 스크린샷으로 이미 검증 완료 |
| P-WW products_ww_prevalidation | Stage 0 스크린샷으로 이미 검증 완료 |
| B3 brands_ww_shopping | Worldwide Shopping Entity 데이터 2025 이전 부재 |
| C1 brands_kr_hangul_web | A1에서 한글/영어 분리 수집으로 대체 |

---

## Total: 11 downloads (5 done + 6 remaining)

| Group | Downloads | Chunk files | Status |
|---|---|---|---|
| Brand A (Korea) | 3 | 12 | ✅ Done |
| Brand B (Worldwide) | 2 | 8 | ✅ Done |
| Product D | 2 | 8 (or fewer if ≤5 keywords) | Pending |
| Apparel E | 2 | 12 (6 chunks × 2, 5-year) | Pending |

## Schema impact

`raw.google_trends_raw` 테이블 `layer` 컬럼 값:
- `brand` — A1-3, B1-2
- `micro_product` — D1, D2
- `apparel_seasonality` — E1
- `apparel_competitive` — E2

## Season start week analysis method (E1/E2)

```
season_start_week = first week where:
  7-week MA(interest) >= baseline(annual_mean) * 1.3

Compute per keyword, per year (5 years).
Output: mean ± std of season_start_week across years.
```
