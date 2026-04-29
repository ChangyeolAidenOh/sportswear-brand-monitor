# Google Trends CSV Download Protocol v2

**Date:** 2026-04-29
**Author:** Changyeol Oh
**Purpose:** Check 5 data collection — standardized download procedure
**Revision:** v2 — Layer separation + Pre-Validation integrated

---

## Architecture

| Layer | Purpose | Scope | Downloads |
|---|---|---|---|
| **Brand** | 4-brand competitive SoV | KR + WW × Web/YouTube/Shopping | A1-3, B1-2 |
| **Macro (Category)** | NB footwear vs apparel trend | KR + WW | M1, M2 |
| **Micro (Product)** | NB model-level portfolio | KR + WW, pre-validated | P-KR, P-WW → D1, D2 |

## Key decisions

1. **Korea: Search term (한글+영어 개별 입력)** — A1 검증 완료, 8 columns으로 한글/영어 비중 자동 분리
2. **Worldwide: Entity/Topic per brand** — brand_topics.csv 기준
3. **Period: 2023-01-01 ~ 2026-04-19** (3년+, weekly via 1-year chunking)
4. **Chunking:** 1년 단위 4청크, 1개월 overlap, stitch_gtrends.py로 스티칭
5. **Pre-Validation:** 제품 모델은 데이터가 선정. 임계값 avg ≥ 10
6. **B3 제외:** Worldwide Google Shopping Entity 데이터 2025 이전 부재 확인
7. **C1 제외:** A1에서 한글/영어 분리 수집으로 대체됨

## Chunking protocol

| Chunk | Period | Overlap |
|---|---|---|
| 1 | 2023-01-01 ~ 2023-12-31 | — |
| 2 | 2023-12-01 ~ 2024-11-30 | 2023-12 (1 month) |
| 3 | 2024-11-01 ~ 2025-10-31 | 2024-11 (1 month) |
| 4 | 2025-10-01 ~ 2026-04-19 | 2025-10 (1 month) |

Stitching: `python stitch_gtrends.py <chunk_files> -o <output.csv>`

## Entity mapping (confirmed)

| Brand | Selected | Type | MID | Note |
|---|---|---|---|---|
| Nike | 나이키 (기업) | Entity | /m/0lwkh | Continuous from 2023 |
| Adidas | ADIDAS (패션 브랜드) | Entity | /g/1ym_1qtkc | Apparel company has no data pre-2024 |
| Puma | PUMA (신발 회사) | Entity | /m/03r_n_ | Footwear corp. avg 82 |
| New Balance | NB (Footwear company) | Entity | /m/08dr90 | Company for brand-level consistency |

See `database/seed/brand_topics.csv` for full mapping with fallbacks.

---

## Download matrix

### Layer: Brand (A1-A3, B1-B2) — COMPLETED

| # | File | Keywords | Region | Type | Status |
|---|---|---|---|---|---|
| A1 | brands_kr_web.csv | 뉴발란스, New Balance, 나이키, Nike, 아디다스, Adidas, 푸마, Puma | Korea | Web | ✅ |
| A2 | brands_kr_youtube.csv | (same) | Korea | YouTube | ✅ |
| A3 | brands_kr_shopping.csv | (same) | Korea | Shopping | ✅ |
| B1 | brands_ww_web.csv | NB/Nike/ADIDAS/PUMA (Entity) | Worldwide | Web | ✅ |
| B2 | brands_ww_youtube.csv | (same Entity) | Worldwide | YouTube | ✅ |

### Layer: Macro — NB Category (M1, M2)

NB 비즈니스 체질 변화 추적: 신발 → 의류 확장 트렌드.
검색량 스케일이 모델과 완전히 다르므로 반드시 별도 Layer.

| # | File | Keywords (Search term) | Region | Type |
|---|---|---|---|---|
| M1 | nb_category_macro_kr.csv | 뉴발란스 신발, 뉴발란스 의류 | Korea | Web |
| M2 | nb_category_macro_ww.csv | new balance shoes, new balance clothing | Worldwide | Web |

**분석 목적:** 기울기(slope) 비교. 의류 검색이 신발 대비 얼마나 빠르게 성장하는가.
**인사이트:** "NB는 신발 회사에서 라이프스타일 브랜드로 전환 중" 서사의 데이터 근거.

### Layer: Micro Pre-Validation (P-KR, P-WW)

후보 모델을 Google Trends에 넣고, avg ≥ 10 기준으로 데이터가 선정.
Pre-Validation 결과도 raw에 적재 (products_*_prevalidation.csv).

| # | File | Keywords (Search term) | Region | Type |
|---|---|---|---|---|
| P-KR | products_kr_prevalidation.csv | 뉴발란스 530, 뉴발란스 992, 뉴발란스 574, 뉴발란스 2002R, 뉴발란스 327 | Korea | Web |
| P-WW | products_ww_prevalidation.csv | new balance 990, new balance 574, new balance 9060, new balance 2002R, new balance 1906R | Worldwide | Web |

**선정 근거:**
- Korea 후보: 530(누적 200만 켤레, 나무위키), 992(2025 재발매), 574(스테디셀러), 2002R(라이프스타일), 327(여성 인기)
- Worldwide 후보: 990(헤리티지 플래그십), 574(글로벌 검색 1위, accio.com/Google Trends), 9060(StockX TikTok 바이럴), 2002R(공통 앵커), 1906R(스트리트웨어 콜라보)
- 출처 한계: 모델별 판매량 데이터는 Circana(유료)에만 존재. 공개 데이터(StockX 리포트, NB IR, 커뮤니티)와 검색량 자체를 선정 도구로 활용.

**임계값:** Pre-Validation 결과에서 avg ratio ≥ 10인 모델만 D1/D2로 승격.
**2002R:** Korea/Worldwide 양쪽 공통 앵커. 교차 비교 기준점.

### Layer: Micro Final (D1, D2)

P-KR, P-WW 검증 결과 살아남은 모델로 구성. 최대 4~5개.

| # | File | Keywords | Region | Type |
|---|---|---|---|---|
| D1 | products_kr_web.csv | P-KR 통과 모델 (최대 5개) | Korea | Web |
| D2 | products_ww_web.csv | P-WW 통과 모델 (최대 5개) | Worldwide | Web |

**Note:** P-KR/P-WW에서 전체 5개가 통과하면 D1=P-KR, D2=P-WW 그대로 사용 (재다운로드 불필요).
탈락 모델이 있으면 재구성 후 다운로드.

---

## Total: 12 downloads

| Layer | Downloads | Chunking | Status |
|---|---|---|---|
| Brand (A1-3, B1-2) | 5 | 4 chunks each = 20 chunk files | ✅ Done |
| Macro (M1, M2) | 2 | 4 chunks each = 8 chunk files | Pending |
| Pre-Validation (P-KR, P-WW) | 2 | TBD (2-5 keywords, may not need chunking) | Pending |
| Final (D1, D2) | 2 | Same as P if pass-through | Pending |

## Execution order

1. M1, M2 (Macro) — 지금 바로
2. P-KR, P-WW (Pre-Validation) — M 다음
3. Pre-Validation 결과 분석 → avg ≥ 10 필터링
4. D1, D2 확정 (P가 pass-through이면 재다운로드 불필요)
5. spike_check5_gtrends.py 전체 파싱 검증
6. data_feasibility_report.md 최종 업데이트

## MID Resolution

MIDs are NOT in CSV headers. Resolved via:
- `python database/seed/resolve_brand_mids.py --skip-validation`
- Manual verification on trends.google.com
- Results in `database/seed/brand_topics.csv` and `docs/mid_resolution_report.md`

## Schema impact

`raw.google_trends_raw` 테이블에 `layer` 컬럼 추가 권고:
- `brand` — A1-3, B1-2
- `macro_category` — M1, M2
- `micro_product_prevalidation` — P-KR, P-WW
- `micro_product_final` — D1, D2

mart 단계에서 Layer별 분석 분리에 활용.
