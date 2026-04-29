# Quick Exploratory Pass — Findings Report (Final)

**Date:** 2026-04-29  
**Author:** Changyeol Oh  
**Stage:** 0 (Quick Exploratory Pass)

---

## Overview

Stage 0 Data Feasibility Spike에서 수집한 Google Trends 8개 CSV + Naver DataLab 데이터를 기반으로 6개 가설을 검증하였다. 본 파이프라인(Stage 1~8)의 분석 방향을 확정한다.

---

## Confirmed Insights (본 파이프라인 KPI/인사이트로 승격)

### H3: 530 Dependency is INTENSIFYING

**Question:** NB 한국 제품 검색에서 530 비중이 시간에 따라 심화/완화 중인가?

- Overall avg 530 share: **51.2%**
- Linear trend slope: **+2.36%p per quarter**
- R-squared: 0.345, **p-value: 0.0213**
- Direction: **INTENSIFYING**

![H3](figures/exploratory/h3_530_dependency.png)

**Verdict:** 통계적으로 유의한 추세 (p=0.0213). NB 한국 제품 검색에서 530 의존도가 매 분기 심화 중. 2023년 ~45%에서 2026년 ~60%로 상승. 이 추세가 지속되면 530 단일 모델 리스크가 가속된다.

**BDC Action:** 530 의존도를 분기별 KPI로 모니터링. 60% 초과 시 경고.

---

### H5: D2C Search is DECLINING (Warning Signal)

**Question:** NB D2C(공식몰) 검색이 NB 전체 대비 어떤 추세인가?

- NB Total trend: slope ≈ 0, **p=0.9995 (완전 안정)**
- NB D2C trend: slope = **-0.179/week, p=0.0001 (유의하게 하락)**
- D2C mean intensity: 35.3/100
- D2C-NB cross-corr: r=0.799 at lag=0 (동시 이동)

![H5](figures/exploratory/h5_d2c_share.png)

**Verdict:** NB 전체 검색은 안정적인데 공식몰 검색만 하락. 소비자의 NB 관심은 유지되나, 구매 채널이 공식몰에서 다른 플랫폼(무신사/쿠팡 등)으로 이동 중일 가능성. D2C 전략 효과에 대한 경고 신호.

**BDC Action:** D2C 검색 추이를 주간 모니터링. 공식몰 전용 프로모션 → 검색 반등 여부 추적.

---

### H6: NB Padding Starts 2.6 Weeks EARLIER than North Face

**Question:** NB 패딩은 노스페이스 대비 시즌 시작이 빠른가, 늦은가?
**Method:** 7-week MA가 연간 baseline 대비 +30% 처음 도달하는 주.

| Brand | Years | Avg Start Week | Std | Earliest | Latest |
|---|---|---|---|---|---|
| 뉴발란스 | 5 | **42.6** | 4.9 | 38 | 52 |
| 나이키 | 5 | 44.8 | 5.9 | 39 | 52 |
| 아디다스 | 5 | 45.2 | 5.6 | 40 | 52 |
| 노스페이스 | 5 | 45.2 | 5.6 | 40 | 52 |

![H6](figures/exploratory/h6_padding_timing.png)

**Verdict:** NB 패딩 시즌 시작이 노스페이스 대비 평균 **2.6주 빠르다**. 예상과 반대 — NB가 시장 선도. 단, 절대 규모에서 노스페이스가 압도적(avg 13.9 vs NB 1.2). **"타이밍은 빠른데 모멘텀은 못 키우고 있다"** — 시즌 진입 전략은 맞지만 시즌 내 확장이 안 되는 구조적 문제.

**BDC Action:** 패딩 시즌 시작 주차(~38주, 9월 중순)를 연간 캠페인 타이밍 기준점으로 활용.

---

## Reversed Hypothesis (가설 방향 전환)

### H4: NB Search LEADS Instagram (Reverse Direction)

**Question:** Instagram 프록시가 NB 전체 검색을 선행하는가?

- NB Instagram mean: 20.6, NB Total mean: 44.0 (독립 스케일)
- Best cross-correlation: **r=0.504 at lag = -2 weeks**
- 95% significance threshold: ±0.263

![H4](figures/exploratory/h4_instagram_lead.png)

**Verdict:** 가설과 반대. **NB 검색이 Instagram 프록시를 2주 선행한다.** 소비자가 먼저 "뉴발란스"를 검색하고, 이후 "뉴발란스 인스타"를 검색하는 순서. v3 Layer 3의 "Social → Search" Granger 가설은 한국에서 **"Search → Social"** 방향으로 수정 필요.

**Implication:** 한국 NB 소비자의 정보 탐색 경로가 검색 → 소셜이라면, 소셜 마케팅은 신규 수요 창출보다 기존 검색 수요의 전환/강화 역할. Stage 4 Granger 분석에서 방향성 재검증.

---

## Weak Signals (본 파이프라인에서 정밀 분석)

### H2: 530 vs 992 Season Separation — Weak

**Question:** 530은 SS, 992는 FW 피크를 보이는가?

- 530: SS avg = 34.6, FW avg = 29.3, **SS/FW ratio = 1.18**
- 992: SS avg = 7.7, FW avg = 8.3, **SS/FW ratio = 0.93**

![H2](figures/exploratory/h2_season_separation.png)

**Verdict:** 방향은 맞지만 차이가 작다. 530은 약한 SS 경향, 992는 약한 FW 경향. 뚜렷한 시즌 분리는 아님. Stage 3 STL 분해에서 시즌 성분을 정밀 분리하여 재검증.

---

### H1: Korea-Global Season Cycle — Method Limitation

**Question:** 한국(530)과 글로벌(9060)의 시즌 사이클이 동기화되어 있는가?

- 530 vs 9060: max cross-corr = **-0.232 at lag = -14 weeks** (약한 역상관)
- 574 KR vs WW: max cross-corr = **0.296 at lag = -167 weeks** (비정상)

![H1](figures/exploratory/h1_korea_global_alignment.png)

**Verdict:** 단순 Cross-correlation은 부적합. 574 lag=-167주는 전체 데이터 길이에 가까워 의미 없음. 한국과 글로벌의 인기 모델 자체가 다르기 때문(530 vs 9060) 시계열 형태가 다르다. Stage 4에서 **DTW(Dynamic Time Warping)**로 비선형 시간 정렬 재검증.

---

## Hypothesis Status Summary

| # | Hypothesis | Result | Status | Next Step |
|---|---|---|---|---|
| H3 | 530 dependency trend | **+2.36%p/Q, p=0.021** | ✅ Confirmed | KPI 승격 |
| H5 | D2C search trend | **-0.179/wk, p=0.0001** | ✅ Confirmed (warning) | 주간 모니터링 |
| H6 | Padding timing | **NB 2.6주 빠름** | ✅ Confirmed | 캠페인 타이밍 |
| H4 | Instagram → Search | **역방향 (Search → Insta, 2주)** | ⚠️ Reversed | Stage 4 Granger 재검증 |
| H2 | 530/992 season split | SS/FW ratio 1.18/0.93 | 🔍 Weak | Stage 3 STL 분해 |
| H1 | Korea-Global alignment | Cross-corr 부적합 | 🔍 Method limit | Stage 4 DTW |

---

## Stage 0 Insights Summary (11 findings)

### From Data Feasibility Spike (Check 1-5):

1. **530이 NB 한국 검색의 ~85% 견인** (Naver DataLab)
2. **Korea = 530 중심, Global = 9060 중심** (Google Trends D1/D2)
3. **574가 유일한 Korea ↔ Global 공통 앵커**
4. **한국 소비자 소셜 탐색 = Instagram 중심** (avg 20.6 vs TikTok 6.3)
5. **D2C 검색만 유의미한 채널 신호** (무신사/쿠팡 앱 직접 진입 추정)
6. **YouTube에서 한글 검색 10배** (플랫폼별 언어 행동 차이)
7. **NB 패딩 = 노스페이스 대비 1/10 규모**

### From Quick Exploratory Pass (H1-H6):

8. **530 의존도 심화 중** (+2.36%p/Q, p=0.021) — H3
9. **D2C 검색 하락, NB 전체는 안정** (채널 이동 경고) — H5
10. **NB 패딩 시즌 2.6주 빠르지만 모멘텀 부족** — H6
11. **검색 → 소셜 방향 (Instagram 가설 역전)** — H4

---

## Cross-cutting Insights — NB Korea의 구조적 비대칭

개별 가설을 넘어 H3, H5, H6를 함께 보면 일관된 패턴이 드러난다.

### Pattern 1: 시장 신호는 잡고 있다

- **H6**: NB 패딩 시즌 시작 38주차 — 노스페이스 대비 2.6주 빠름. 트렌드 감지 능력 입증.
- **H3**: 530 모델은 한국 시장에서 NB 검색의 ~50%를 점유 — 한국 소비자 취향에 맞는 제품 보유.

### Pattern 2: 자기 채널로 끌어오지 못한다

- **H5**: NB Total 검색은 안정 (p=0.9995)인데 D2C 검색만 통계적으로 유의하게 감소 (slope=-0.179/week, p=0.0001). 소비자가 NB는 계속 찾지만 공식몰을 점점 안 찾는다.
- **H6**: NB 패딩은 시즌 시작은 빠른데 절대 규모는 정체 (avg 1.2 vs 노스페이스 13.9). 시즌 진입 후 모멘텀 확장 실패.

### Pattern 3: 단일 모델 의존이 심화된다

- **H3**: 530 의존도가 매 분기 +2.36%p 통계적으로 유의하게 상승 (p=0.0213). 2023년 ~45%에서 2026년 ~60%까지 가속.

### Business Diagnosis

NB 한국은 **트렌드 감지력은 있으나 채널/포트폴리오 다각화에서 약점**을 보인다.

- **단기 위험**: D2C 약화로 직영 채널 가치 잠식 진행 중. 무신사/쿠팡 등 외부 플랫폼에 의존도가 높아질 경우 마진 압박 + 고객 데이터 직접 수집력 약화.
- **장기 위험**: 530 의존 심화 추세가 지속되면 단일 모델 라이프사이클 종료 시점에 매출 절벽 위험. 530 후속 히트 모델의 부재가 구조적 문제.
- **반대 신호**: 패딩 카테고리에서 시즌 진입 타이밍이 시장 선도 — 이 능력을 상품 라인 확장 + 채널 다각화에 활용할 여지 존재.

### BDC Implication

본 프로젝트의 핵심 모니터링 KPI 3종:
1. **530 분기별 의존도** — 60% 초과 시 알림
2. **D2C 검색 점유율 주간 추세** — 4주 연속 하락 시 알림
3. **NB Total vs 카테고리별 검색 갭** — 패딩처럼 "수요 있으나 NB 점유 미달" 카테고리 자동 탐지

이 3종 KPI가 Streamlit 대시보드 Tab 1 (Weekly KPI Summary)와 Power BI Service Tab 1의 핵심 지표가 된다.

---

*Stage 0 Quick Exploratory Pass: COMPLETED.*
*Stage 0 전체: COMPLETED.*
*다음: Stage 1 — Data Collection Pipeline 구축.*
