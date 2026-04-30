# Stage 1 Checkpoint — Data Collection Pipeline COMPLETED

**Date:** 2026-04-30
**Status:** COMPLETED
**Total rows in raw schema:** 23,292

---

## Collector Status

| # | Collector | File | Strategy | Rows | UPSERT/Dedup Key |
|---|---|---|---|---|---|
| 1 | Naver DataLab | `collectors/collector_naver_datalab.py` | API UPSERT | 1,201 | `(source_type, keyword_group, keyword, period_start)` |
| 2 | Google Trends | `collectors/collector_google_trends.py` | CSV UPSERT | 8,698 | `(layer, keyword, region, search_type, week_start)` |
| 3 | YouTube | `collectors/collector_youtube.py` | API `--clear` INSERT | 3,325 | `--clear` flag per brand |
| 4 | Naver Blog/Cafe | `collectors/collector_naver_blog.py` | API `--clear` INSERT | 10,000 | `--clear` flag per brand |
| 5 | ECOS | `collectors/collector_ecos.py` | API UPSERT | 52 | `(stat_code, item_code, period)` |
| 6 | Financials | `collectors/collector_financials.py` | CSV UPSERT | 16 | `(brand, fiscal_period, metric_name, source_type)` |

---

## Data Coverage

### Naver DataLab (1,201 rows)
- Period: 2024-04-01 ~ 2026-04-27
- 4 groups: brand(436), nb_product(436), nb_social(61), nb_channel(268)
- nb_social/nb_channel sparse — Stage 0 viability threshold below, raw 보존

### Google Trends (8,698 rows)
- Period: 2022-12-25 ~ 2026-04-19
- 8 CSVs: brands_kr (web/youtube/shopping), brands_ww (web/youtube), products (kr/ww), padding_competitive_kr
- Stitched via stitch_gtrends.py (Stage 0)

### YouTube (3,325 rows)
- 90 videos + 3,235 comments across 4 brands
- NB: 30 videos / 1,210 comments (3 queries)
- Nike/Adidas/Puma: 20 videos each (2 queries each)

### Naver Blog/Cafe (10,000 rows)
- 4 brands × 2 sources × 2-4 queries × 500 results
- NB: 4,000 (2,000 blog + 2,000 cafe)
- Others: 2,000 each

### ECOS (52 rows)
- CSI (소비자심리지수): stat_code 511Y002, item FME, item2 99988
- Period: 2022-01 ~ 2026-04 (monthly)

### Financials (16 rows)
- Nike: 6 rows (FY2024 Q1-Q3 + FY2025 Q1-Q3), T1 SEC 10-Q
- Adidas: 2 rows (FY2023, FY2024), T1 IR report
- Puma: 2 rows (FY2023, FY2024), T1 IR report
- NB Global: 2 rows (FY2023 $6.5B, FY2024 $7.8B), T4 CEO statement
- NB Korea: 4 rows (nb_share T2, revenue_korea T4, eland_fashion T1 × 2)

---

## Schema Decisions Made

1. **naver_datalab_raw**: Existing schema preserved. UNIQUE constraint added by collector.
2. **google_trends_raw**: Existing schema preserved. UNIQUE constraint added by collector.
3. **youtube_raw / naver_blog_raw**: No UNIQUE — `--clear` + INSERT pattern.
4. **ecos_raw**: UNIQUE `(stat_code, item_code, period)` added by collector.
5. **financials_raw**: Source tier governance (T1-T4), `source_tier` + `note` columns added. `value` widened to `NUMERIC(20,4)` for KRW. UNIQUE expanded to include `source_type`.

---

## DB Connection Pattern

- `from database.connection import get_conn`
- `get_conn()` returns context manager: `with get_conn() as conn:`
- `.env`: `POSTGRES_PORT=5433`, user `nb_admin`, db `nb_monitor`

---

## Files Created in Stage 1

```
collectors/
├── __init__.py
├── collector_naver_datalab.py
├── collector_google_trends.py
├── collector_youtube.py
├── collector_naver_blog.py
├── collector_ecos.py
└── collector_financials.py

database/migrations/
└── 003_financials_governance.sql

data/raw/financials/
└── financials_seed.csv (16 rows, git-tracked)
```

---

## Pending Items

### Completed (Stage 2 진입 시)

- [x] schema_init.sql: `financials_raw.value` → `NUMERIC(20,4)` 반영
- [x] schema_init.sql: `financials_raw` 에 `source_tier`, `note` 컬럼 추가 반영
- [x] schema_init.sql: collector UPSERT 키 UNIQUE 제약조건 동기화 (google_trends, naver_datalab, ecos, financials)
- [x] schema_init.sql: percentage 컬럼 `NUMERIC(6,4)` → `NUMERIC(7,4)` 수정 (sov_pct, share_within_nb_pct, share_pct, gross_margin_pct, dtp_revenue_pct)

### Open

- [ ] financials_seed.csv: DART 패션부문 매출 수치 직접 확인 (뉴스 인용 vs DART 원문)
- [ ] financials_seed.csv: 추가 큐레이션 가능 (Nike FY2024 Q4/연간, gross_margin 등)
- [ ] Blog/Cafe collector: `--clear` → `(source_type, link)` 자연키 UPSERT 전환 (Stage 4 진입 전, 4~6h 소요). link 정규화 필수 (query string strip + canonical URL 추출)
- [ ] naver_datalab_raw: `group_id` / `is_complete` 컬럼 추가 — collector 미구현 미래 컬럼. `group_id` 역할은 현재 `keyword_group`이 수행 중. collector 수정 시 migration으로 추가.

---

## Stage 2 Decisions

### Decision #2: Social 시계열 → Plan X 채택

**검증 과정:**

| 단계 | 검증 내용 | 결과 |
|---|---|---|
| Blog post_date 적재율 | blog 100%, cafearticle 0% | Cafe 시계열 불가 |
| Blog 주간 커버리지 | nike 2주, adidas 3주, puma 19주, NB 13주 | 전 브랜드 30주 미달 |
| YouTube 영상 기반 | nike 14주, adidas 17주, puma 17주, NB 25주 | 전 브랜드 30주 미달 |
| YouTube 댓글 기반 | NB 68.6%, adidas 74.5%, puma 47.0%, nike 32.8% | 커버리지 개선되나 갭 30~50% |

**결론:**
- Blog: Naver Search API 관련도순 500건 반환 → 시간적 편중은 API 구조적 한계, 재수집 불가
- Cafe: `post_date` 전량 NULL → 시계열 자체 불가
- YouTube: 전 브랜드 영상 기반 30주 미달. 댓글 기반 전환해도 브랜드 간 커버리지 편차 과대
- **Plan X 채택**: Granger Chain을 Social → Search → Sales 3-stage에서 Search → Sales 2-stage로 축소. Social은 감성/토픽 cross-sectional 변수로 전환.

### Decision #3: nb_social / nb_channel staging 제외 (옵션 B)

- nb_social: 인스타 60행, 틱톡 1행 — Granger 최소 요건 미달
- nb_channel: 무신사 37행, 쿠팡 16행 — sparse
- raw 보존, staging.search_weekly에서 `WHERE keyword_group NOT IN ('nb_social', 'nb_channel')` 적용
- 의도적 제외 사유: sparse data, viability threshold below

---

## Next: Stage 3 — Analysis & Visualization

- Granger causality test (Search → Sales, 2-stage)
- Blog/Cafe 텍스트 코퍼스 감성/토픽 분석 (cross-sectional)
- Power BI / Streamlit dashboard 연결
- anomaly_log ↔ events_calendar 매칭
