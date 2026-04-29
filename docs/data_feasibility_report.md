# Data Feasibility Spike Report — Final

**Date:** 2026-04-29  
**Author:** Changyeol Oh  
**Stage:** 0 (Data Feasibility Spike)  
**Status:** COMPLETED

---

## Executive Summary

Stage 0 Data Feasibility Spike에서 5개 검증 항목을 실행하여, 본 파이프라인의 데이터 수집 전략과 분석 스코프를 확정하였다.

| 검증 항목 | 결과 | 최종 결정 |
|---|---|---|
| Check 1: Naver DataLab API | 200 OK, 주간 106주 | API 자동 수집 채택 |
| Check 2: NB 제품 라인 검색량 | 530, 992 생존 / 2002R, 327 탈락 | 530 vs 992 이원 구조 (Naver 기준) |
| Check 3: TikTok/Instagram 프록시 | Instagram 강한 신호 발견 | Instagram 프록시 + YouTube API 직접 |
| Check 4: Naver 쇼핑인사이트 채널 | Plan A 불가, 공식몰만 생존 | Plan B(D2C) + Plan C(나머지) |
| Check 5: Google Trends 수집 | pytrends 차단, 수동 CSV 확정 | 8개 CSV 스티칭 완료, 파싱 PASS |

---

## Check 1: Naver DataLab Search Trend API

**목적:** API 호출 가능 여부, 응답 포맷, 주간 해상도 확인.

**검증 키워드:** 나이키, 아디다스, 푸마, 뉴발란스 (4개 브랜드)

### 결과

- API 상태: 200 OK
- 데이터포인트: 106주 (2024-04-22 ~ 2026-04-27)
- 값 형식: ratio (0~100 상대값)
- 초기 401 에러 발생 → 원인: 네이버 개발자 센터에서 데이터랩 API 권한 미활성화 (errorCode 024). 활성화 후 정상 동작.

### 판정

**PASS.** API 기반 자동 수집 파이프라인 구축 가능. incomplete week 처리 로직 필요.

---

## Check 2: NB Product Line Search Volume Sufficiency

**목적:** NB 제품 라인별 Naver 검색량이 시계열 분석에 충분한지 검증.

### 결과

| Product Line | Avg Ratio | Max Ratio | Min Ratio | Zero Weeks | Verdict |
|---|---|---|---|---|---|
| NB 530 | 39.8 | 100.0 | 3.1 | 0 | VIABLE |
| NB 992 | 6.2 | 36.5 | 0.6 | 0 | VIABLE |
| NB 2002R | 3.4 | 5.8 | 0.3 | 0 | BELOW THRESHOLD |
| NB 327 | 4.9 | 11.3 | 0.4 | 0 | BELOW THRESHOLD |

임계치: avg ratio >= 5

### 판정

530 vs 992 이원 구조 (Naver 기준). 530이 NB 한국 검색의 ~85%를 견인 — 제품 집중도 리스크 또는 히트 모델 전략의 증거.

---

## Check 3: TikTok/Instagram Proxy Search Volume

**목적:** TikTok, Instagram이 Naver 검색 프록시로 소셜 신호를 포착할 수 있는지 검증.

### 결과

| Proxy Keyword | Avg Ratio | Max Ratio | Zero Weeks (%) | Verdict |
|---|---|---|---|---|
| NB TikTok | 6.3 | 6.3 | 0% | USABLE (weak) |
| Nike TikTok | - | - | - | INSUFFICIENT |
| NB Instagram | 20.6 | 100.0 | 0% | USABLE (strong) |
| NB YouTube | - | - | - | INSUFFICIENT |

### 핵심 발견

한국 소비자의 소셜 채널 탐색 = Instagram 중심. TikTok 중심 글로벌 트렌드와의 구조적 차이.

### 판정

- Instagram 프록시: 채택 (avg 20.6, 강한 신호)
- TikTok 프록시: 보조 참고 수준
- YouTube: Naver 프록시 불가 → API v3 직접 수집

---

## Check 4: Naver Shopping Insight — Channel Data Availability

**목적:** 플랫폼별(무신사/쿠팡/D2C) 클릭 데이터 제공 여부 검증, Plan A/B/C 확정.

### 결과

- Category Trend API: 200 OK (카테고리 수준 데이터 확인)
- 플랫폼별 분해 엔드포인트: 존재하지 않음
- Plan A(직접 플랫폼 데이터): NOT FEASIBLE

### Channel Proxy Search Volume (Plan B 검증)

| Channel Proxy | Avg Ratio | Max Ratio | Zero Weeks (%) | Verdict |
|---|---|---|---|---|
| NB Official (자사몰/공식몰/공홈) | 35.4 | 100.0 | 0% | VIABLE |
| NB Musinsa | 0.5 | 1.3 | 0% | INSUFFICIENT |
| NB Coupang | 0.4 | 0.9 | 0% | INSUFFICIENT |
| NB Kream | 1.4 | 3.8 | 0% | INSUFFICIENT |

### 판정

| 채널 | Plan | 비고 |
|---|---|---|
| D2C/공식몰 | Plan B (검색 프록시) | avg 35.4, 강한 신호 |
| 무신사/쿠팡/크림 | Plan C (카테고리 또는 제외) | 검색 프록시 불가 |

D2C 검색만 유의미 — 무신사/쿠팡은 소비자가 앱 직접 진입 추정.

---

## Check 5: Google Trends Manual CSV Validation

**목적:** pytrends 자동 수집 가능 여부 + 수동 CSV 다운로드 파이프라인 검증.

### 5a. pytrends Rate Limit Test

15회 순차 호출(2s 간격), 첫 호출부터 TooManyRequestsError 발생. 모바일 핫스팟 전환 후에도 `build_payload()`는 차단, `suggestions()`만 동작.

**판정:** pytrends 자동 수집 현 환경에서 불가. 수동 CSV 다운로드를 primary로 채택.

### 5b. Google Trends Entity/Topic 구조 조사

**핵심 발견:**
- Search term = 문자열 그대로 매칭. "나이키"는 Worldwide에서 0.
- Entity = Knowledge Graph 엔티티. 다국어 통합, 범주 한정.
- Topic = 가장 넓은 개념. 노이즈 포함 가능성.

**브랜드별 Entity 유형 불일치:**
Nike(Footwear company), Adidas(Fashion brand), Puma(Footwear corporation), NB(Footwear company vs Topic 3개). Entity 유형이 다르면 SoV 비교 시 스코프 왜곡.

**2023 후반 Google Topic 재편 발견:**
Adidas와 NB에서 동시에 2023 후반~2024 초 새 Entity/Topic이 생성되어 이전 데이터가 부재하는 현상 확인. 시계열 연속성 기준으로 선택 필요.

**해결 전략:**
- Korea: Search term + 한글/영어 개별 입력
- Worldwide: Entity 브랜드별 최적 선택 (시계열 연속성 기준)

### 5c. MID Resolution

`resolve_brand_mids.py --skip-validation`으로 6개 브랜드 후보 수집. 수동 시계열 검증 수행.

**확정 매핑:**

| Brand | Primary | Type | MID | 근거 |
|---|---|---|---|---|
| Nike | 나이키 (기업) | Entity | /m/0lwkh | 2023부터 연속 |
| Adidas | ADIDAS (패션 브랜드) | Entity | /g/1ym_1qtkc | Apparel company는 2024 이전 데이터 없음 |
| Puma | PUMA (신발 회사) | Entity | /m/03r_n_ | avg 82, Topic(66) 대비 우위 |
| New Balance | NB (Footwear company) | Entity | /m/08dr90 | 4사 동일 유형 일관성 |

### 5d. Chunking & Stitching

Google Trends가 다중 키워드 비교 시 월간 데이터를 반환하는 문제 발견. 1년 단위 4청크 + 1개월 overlap + stitch_gtrends.py로 해결.

### 5e. CSV 파싱 검증

9개 파일 전부 **PASS.** weekly granularity 확인.

| 파일 | Rows | Date Range | Keywords |
|---|---|---|---|
| brands_kr_web.csv | 174 | 2022-12-25 ~ 2026-04-19 | 뉴발란스, New Balance, 나이키, Nike, 아디다스, Adidas, 푸마, Puma |
| brands_kr_youtube.csv | 174 | 2022-12-25 ~ 2026-04-19 | (same 8) |
| brands_kr_shopping.csv | 174 | 2022-12-25 ~ 2026-04-19 | (same 8) |
| brands_ww_web.csv | 174 | 2022-12-25 ~ 2026-04-19 | New Balance, Nike, ADIDAS, PUMA |
| brands_ww_youtube.csv | 174 | 2022-12-25 ~ 2026-04-19 | (same 4) |
| products_kr_web.csv | 174 | 2022-12-25 ~ 2026-04-19 | 뉴발란스 530/992/574/2002R/327 |
| products_ww_web.csv | 174 | 2022-12-25 ~ 2026-04-19 | NB 990/574/9060/2002R/1906R |
| padding_competitive_kr.csv | 278 | 2020-12-27 ~ 2026-04-19 | NB/나이키/아디다스/노스페이스 패딩, 뉴발란스 574 |

### 5f. Google Trends에서 발견된 인사이트

**한글 vs 영어 검색 비중:**

| 채널 | 패턴 |
|---|---|
| Web Search | 나이키(41.0) > Nike(27.0) — 한글 우세 |
| YouTube Search | 나이키(46.8) vs Nike(4.7) — 한글 10배 |
| Google Shopping | Nike(13.6) vs 나이키(45.5) — 영어도 의미 있음 |

**NB 제품 포트폴리오 — Korea vs Global:**

| Korea (D1) | Avg | Global (D2) | Avg |
|---|---|---|---|
| 530 | 32.2 | 9060 | 50.9 |
| 574 | 22.7 | 574 | 16.0 |
| 992 | 8.5 | 2002R | 12.9 |
| 2002R | 1.4 | 1906R | 6.6 |
| 327 | 1.6 | 990 | 5.5 |

→ 한국 = 530 중심, 글로벌 = 9060 중심. 574가 유일한 공통 앵커.

**의류 카테고리:**
- "뉴발란스 의류" 검색 0 — 소비자는 제품명(패딩, 바람막이)으로 검색
- 패딩: 노스페이스 지배 (avg 13.9, max 100), NB 패딩 avg 1.2
- 바람막이/반팔: 대부분 0에 수렴, 분석 제외
- 시즌 시작 주차 정량화(7주 MA baseline +30%)는 Stage 2~3에서 수행

---

## Final Decisions Summary

### 데이터 수집 전략 확정

| 데이터 소스 | 수집 방법 | 비고 |
|---|---|---|
| Naver DataLab | API 자동 수집 | Check 1 통과 |
| Naver Shopping Insight | API 자동 수집 | 카테고리 수준만 |
| Google Trends | 수동 CSV + stitch_gtrends.py | 8개 CSV 완료 |
| YouTube | API v3 직접 수집 | cnp-voc-pipeline 전이 |
| Naver Blog/Cafe | API 자동 수집 | cnp-voc-pipeline 전이 |
| ECOS | API 자동 수집 | 키 발급 완료 |
| KOSIS | API 또는 수동 | 키 불필요 |

### Google Trends 수집 완료 매트릭스

| # | 파일 | Layer | Region | Type | Period |
|---|---|---|---|---|---|
| A1 | brands_kr_web.csv | Brand | Korea | Web | 3yr |
| A2 | brands_kr_youtube.csv | Brand | Korea | YouTube | 3yr |
| A3 | brands_kr_shopping.csv | Brand | Korea | Shopping | 3yr |
| B1 | brands_ww_web.csv | Brand | Worldwide | Web | 3yr |
| B2 | brands_ww_youtube.csv | Brand | Worldwide | YouTube | 3yr |
| D1 | products_kr_web.csv | Product | Korea | Web | 3yr |
| D2 | products_ww_web.csv | Product | Worldwide | Web | 3yr |
| E | padding_competitive_kr.csv | Apparel | Korea | Web | 5yr |

### 폐기된 다운로드

| 원래 계획 | 폐기 사유 |
|---|---|
| B3 brands_ww_shopping | Worldwide Shopping Entity 데이터 2025 이전 부재 |
| C1 brands_kr_hangul_web | A1에서 한글/영어 분리 수집으로 대체 |
| M1/M2 category macro | "뉴발란스 의류" 검색 0 |
| P-KR/P-WW prevalidation | Stage 0 스크린샷으로 이미 검증 완료 |

### 분석 스코프 확정

| 항목 | 원래 계획 | 확정 스코프 |
|---|---|---|
| NB 제품 (Naver) | 530, 992, 2002R, 327 | 530, 992 |
| NB 제품 (Google, Korea) | — | 530, 574, (992 이벤트) |
| NB 제품 (Google, Global) | — | 9060, 574, 2002R |
| Korea ↔ Global 앵커 | 2002R | 574 |
| 소셜 프록시 | TikTok + Instagram | Instagram 프록시 + YouTube API |
| 채널 믹스 | Plan A/B/C | Plan B(D2C) + Plan C(나머지) |
| 의류 분석 | Macro Layer | E(패딩 경쟁사 시즌 타이밍) |

### 신규 인사이트 후보 (10개)

1. 530이 NB 한국 검색의 ~85% 견인
2. Korea = 530 중심, Global = 9060 중심
3. 574가 유일한 Korea ↔ Global 공통 앵커
4. 한국 소비자 소셜 탐색 = Instagram 중심
5. D2C 검색만 유의미한 채널 신호
6. YouTube에서 한글 검색 10배
7. Shopping에서 영어 검색 비중 상승
8. NB 패딩 = 노스페이스 대비 1/10
9. Google Trends Entity/Topic 2023 후반 재편
10. "뉴발란스 의류" 검색 0 — 소비자는 제품명으로 검색

---

## Stage 0 산출물 목록

| 파일 | 용도 |
|---|---|
| docs/data_feasibility_report.md | 본 리포트 |
| docs/gtrends_download_protocol.md | Google Trends 다운로드 절차서 v3 |
| docs/mid_resolution_report.md | Entity/Topic MID 매핑 리포트 |
| docs/check5_gtrends_result.md | CSV 파싱 검증 결과 |
| database/seed/brand_topics.csv | 브랜드 Entity/Topic 매핑 |
| database/seed/resolve_brand_mids.py | MID 해석 스크립트 |
| data/raw/google_trends/*.csv | 스티칭 완료 CSV 8개 |
| spike_feasibility.py | Check 1-4 실행 스크립트 |
| spike_check5_gtrends.py | Check 5 CSV 파싱 검증 |
| stitch_gtrends.py | 청크 스티칭 유틸리티 |

---

*본 리포트는 Stage 0 Data Feasibility Spike의 최종 산출물이며, 본 파이프라인 설계의 근거 문서로 활용된다.*

*Stage 0 Data Feasibility Spike: COMPLETED.*
