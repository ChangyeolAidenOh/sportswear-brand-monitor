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

> **Stage 3 Correction (MSTL 재검증):**
> ~~530 SS/FW=1.18 (SS-dominant), 992 SS/FW=0.93 (약한 FW)~~ → MSTL(periods=[13, 52]) 적용 후 **530 SS/FW=0.86 (FW-dominant), 992 SS/FW=0.89 (FW-dominant)**로 역전.
> 단일 시즌 STL이 분기(~13주) 패턴을 연간에 흡수시켜 SS를 과대 측정한 것이 원인. MSTL 잔차 분산 48–75% 감소로 이중 시즌 구조 확인.
> Korea 5개 제품 전부 FW-dominant (0.71–0.99), Global 대부분 SS-dominant (1.07–1.44). **"시즌 신호 약함"이 아니라 "분석 도구의 한계"**였음. See methodology.md §5.

---

### H1: Korea-Global Season Cycle — Method Limitation

**Question:** 한국(530)과 글로벌(9060)의 시즌 사이클이 동기화되어 있는가?

- 530 vs 9060: max cross-corr = **-0.232 at lag = -14 weeks** (약한 역상관)
- 574 KR vs WW: max cross-corr = **0.296 at lag = -167 weeks** (비정상)

![H1](figures/exploratory/h1_korea_global_alignment.png)

**Verdict:** 단순 Cross-correlation은 부적합. 574 lag=-167주는 전체 데이터 길이에 가까워 의미 없음. 한국과 글로벌의 인기 모델 자체가 다르기 때문(530 vs 9060) 시계열 형태가 다르다. Stage 4에서 **DTW(Dynamic Time Warping)**로 비선형 시간 정렬 재검증.

> **Stage 4 Correction (DTW 3-way 재검증):**
> ~~574 KR vs WW CC lag=-167w~~ → DTW 3-way 비교로 교정. NB brand-level DTW trend lag = **+10.4w (Korea leads Global)**. CC +9w와 수렴. Raw DTW +48w는 Korea FW / Global SS 시즌 위상차 artifact. 시즌 제거 후 실제 구조적 선행 = ~2.5개월. See methodology.md §8.

---

## Hypothesis Status Summary

| # | Hypothesis | Result | Status | Next Step |
|---|---|---|---|---|
| H3 | 530 dependency trend | **+2.36%p/Q, p=0.021** | ✅ Confirmed | KPI 승격 |
| H5 | D2C search trend | **-0.179/wk, p=0.0001** | ✅ Confirmed (warning) | 주간 모니터링 |
| H6 | Padding timing | **NB 2.6주 빠름** | ✅ Confirmed | 캠페인 타이밍 |
| H4 | Instagram → Search | **역방향 (Search → Insta, 2주)** | ⚠️ Reversed | Stage 4 Granger 재검증 |
| H2 | 530/992 season split | ~~SS/FW 1.18/0.93~~ → **0.86/0.89 (reversed)** | ✅ Corrected (Stage 3) | MSTL 이중 시즌 구조 확인 |
| H1 | Korea-Global alignment | ~~CC -167w~~ → **DTW trend +10.4w** | ✅ Corrected (Stage 4) | Korea leads Global ~10w |

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

## Stage 3 Cross-cutting Insights — 시즌 구조 + 감성 비대칭

Stage 3 시즌 분해(Track A) + 감성 분석(Track B) + 채널 믹스(A3)의 결과를 종합하면, Stage 0에서 발견된 NB Korea 구조적 비대칭이 3개 차원에서 동시에 확인된다.

### Data Point 1: 이중 시즌 구조 발견 (MSTL)

연간(52w) + 분기(13w) 이중 시즌 구조가 4개 브랜드 × 2개 지역 = 8개 시계열 전부에서 확인됨. MSTL 잔차 분산 48–75% 감소. 이는 Stage 0 H2에서 "시즌 신호 약함"이라고 판단한 것이 단일 시즌 분석 도구의 한계였음을 보여준다.

### Data Point 2: SS/FW Ratio 역전

530 Korea: Stage 0 SS/FW=1.18 → Stage 3 SS/FW=0.86 (FW-dominant로 역전). 단일 시즌 STL이 분기 패턴을 연간에 흡수하여 SS를 과대 측정한 것이 원인.

### Data Point 3: Korea FW vs Global SS 구조적 비대칭

Korea 5개 NB 제품: 전부 FW-dominant (0.71–0.99). Global 4/5 제품: SS-dominant (1.07–1.44). 한국 소비자 가을/겨울 아웃도어 착용 빈도가 FW 검색 수요 집중을 견인하고, 글로벌(주로 북미/유럽)은 back-to-school + 봄/여름 러닝 시즌이 검색을 견인하는 것으로 추정. Stage 7 Korea↔Global Bridge에서 정량 검증 대상.

### Data Point 4: 574 Cross-Region Anchor (시즌 분해 레벨 확인)

574 Korea SS/FW=0.99, Global SS/FW=1.07 — 양 지역에서 거의 중립. Stage 2에서 확인한 "574 = cross-region anchor" 역할이 시즌 분해 수준에서도 확인됨.

### Data Point 5: NB Shopping Share 4.5% (채널 단절)

GT Korea brand 기준, Nike shopping share 32.1%, Adidas 24.5%인 반면 NB는 4.5%. NB 소비자는 GT shopping에서 검색하지 않음 — 무신사/쿠팡 앱 직접 진입 추정. 이는 D2C 하락(Data Point 6)과 결합되어 "NB가 검색 채널에서 구매 전환을 잡지 못하는" 구조적 문제를 시사.

### Data Point 6: D2C 하락 재확인 (Stage 0 H5)

공식몰 검색 slope=-0.191/week (p=0.000005). Stage 0 추정(-0.179)과 일관. 추가 발견: 크림(리셀) 검색도 하락 중 (-0.016/week, p<0.000001). 무신사/쿠팡은 신호 자체 없음(앱 직접 진입 확인).

### Data Point 7: NB 감성 비대칭 (+0.289, 최저)

Organic 제품 감성에서 NB +0.289 < Puma +0.367 < Adidas +0.436 < Nike +0.474. NB neutral 비율 45.6% (Nike 13.7%, Adidas 17.0%). NB 블로그에 정보성/뉴스성 글 비중이 높아 제품 리뷰 비율이 낮은 것이 원인.

### Data Point 8: 검색-감성 비대칭

Stage 2: NB Korea search +34.94% over-index (Global 대비). Stage 3: NB sentiment +0.289 (4개 브랜드 최저). **검색 수요는 가장 높은데 블로그 감성은 가장 낮다.** 530 의존도 54.98%(단일 모델 집중)와 결합하면, NB Korea는 "530 단일 모델에 검색 수요가 집중되지만, 그 수요가 깊은 제품 만족으로 전환되기보다 정보 탐색 수준에 머무르는" 구조일 가능성.

### Integrated Business Diagnosis (Stage 3 업데이트)

Stage 0 진단: "트렌드 감지력 OK, 채널/포트폴리오 다각화 약점."
Stage 3 업데이트: **"수요는 있으나 전환이 약하다"** — 3개 차원에서 동시 확인.

1. **시즌 차원**: FW 시즌에 수요 집중(FW-dominant)이나, 시즌 내 모멘텀 확장 실패(패딩 1.2 vs 노스페이스 13.9, Stage 0 H6)
2. **채널 차원**: 검색은 하되 공식몰/쇼핑 채널로 전환 안 됨 (D2C -0.191/week, shopping 4.5%)
3. **감성 차원**: 검색 수요 대비 제품 감성 낮음 (search +34.94% vs sentiment 최저)

이 "수요-전환 갭"이 530 의존 심화(+2.36%p/Q, Stage 0 H3)의 근본 원인일 수 있다: 530 이외의 모델에서 수요→만족 전환이 이루어지지 않아, 소비자가 계속 530으로 회귀하는 구조.

### BDC Implication (Stage 3 추가)

Stage 0 KPI 3종에 추가:
4. **NB 제품 감성 비율** — positive/neutral/negative 분기별 추적. neutral 비율 감소 = 제품 리뷰 증가 신호.
5. **검색-감성 갭** — search over-index와 sentiment ranking의 괴리 모니터링. 갭 축소 = 수요→만족 전환 개선.

---

## Stage 4 Leading Indicator Insights

### Data Point 9: NB Korea → Global Structural Lead (+10.4 weeks)

DTW 3-way 비교 (raw → trend → residual)를 통해 Stage 0 H1의 cross-correlation -167주 비정상 결과를 교정했다.

| Method | NB Lag | 판정 |
|---|---|---|
| Stage 0 CC | -167w | artifact (비정상) |
| DTW raw | +48.0w | 시즌 오염 (Korea FW ↔ Global SS 위상차) |
| DTW trend | **+10.4w** | 정제된 구조적 선행 (CC +9w 수렴) |
| DTW residual | +42.2w | noise alignment 한계 |

NB Korea의 구조적 성장 추세가 Global을 약 10주(~2.5개월) 선행한다. Raw DTW 48w는 Stage 3에서 확인된 Korea=FW dominant / Global=SS dominant 시즌 비대칭이 DTW alignment을 오염시킨 결과였으며, trend DTW로 시즌 성분을 제거한 뒤 10.4w로 수렴했다.

이 발견은 BDC 실무에서 NB Korea 검색 추세를 Global 수요 예측의 leading indicator로 활용할 수 있는 근거를 제공한다.

### Data Point 10: NB는 거시 경기 후행 수요 구조

Granger 양방향 검정 결과, NB는 양 지역 모두 CSI→Search 단방향 인과로 분류되었다 (korea lag 3 p=0.0229, global lag 2 p=0.0321).

| Brand | Global | Korea | 해석 |
|---|---|---|---|
| adidas | Search→CSI | Feedback | 브랜드 관성으로 시장 선도 |
| NB | CSI→Search | CSI→Search | **거시 경기 후행** |
| nike | Independent | Search→CSI | 한국에서만 시장 영향력 |
| puma | CSI→Search | Independent | 글로벌은 경기 민감 |

NB의 검색 수요는 소비 심리(CSI)가 개선된 후에 따라 상승하는 구조다. 두 가지 해석이 가능하다:
1. **반응적 수요:** 시장을 선도하지 못하고, 소비 심리에 의존 — "수요-전환 갭" (Stage 3)과 일관
2. **탄력적 수요:** 상대적 신생 브랜드로서, 소비자가 "여유 있을 때 찾아보는" 재량적 탐색 대상

어느 해석이든 actionable implication은 동일하다: **NB는 경기 하강기에 검색 수요 방어가 필요한 브랜드**이다.

### Integrated Business Diagnosis (Stage 4 업데이트)

Stage 3 진단: "수요는 있으나 전환이 약하다."
Stage 4 업데이트: NB 한국은 **거시 경기에 반응적이나 글로벌 수요의 선행 신호** 역할을 한다.

**약점 — 거시 경기 의존:**
- CSI→Search 단방향 인과: 소비 심리 하락 시 검색 수요 동반 하락 구조
- adidas/Nike와 달리 브랜드 관성이 부족, 경기 하강기 검색 방어 불가
- Stage 3의 D2C 하락(-0.191/week), 530 단일 모델 의존 심화와 결합하면, 경기 하강 + D2C 약화 + 포트폴리오 집중이라는 복합 위험 구조

**강점 — 글로벌 선행 신호:**
- NB Korea trend가 Global을 ~10주 선행 (DTW + CC 수렴)
- BDC가 Korea 검색 추세를 모니터링하면 Global 수요 변화를 ~2.5개월 전에 예측 가능
- CSI → NB Korea → NB Global 3-stage chain 가능성 (Stage 7 검증 후보)

### Stage 7 검증 핵심 가설 — CSI → NB Korea → NB Global 3-stage Chain

Stage 4 Track A의 NB CSI→Search 단방향 인과 + Track B의 NB Korea trend +10.4w 선행 결과를 결합하면, 거시 소비 심리(CSI)가 NB Korea 검색을 선행하고, NB Korea trend가 NB Global trend를 ~10주 선행한다는 3-stage chain이 가설로 도출된다. 즉 CSI → NB Korea Search → NB Global Search의 인과 구조가 가능하며, 한국이 거시 신호를 글로벌로 변환하는 중간 노드 역할일 수 있다. Stage 7 Korea-Global Bridge 분석에서 정량 검증할 본 프로젝트의 핵심 가설 중 하나.

### BDC Implication (Stage 4 추가)

Stage 3 KPI 5종에 추가:
6. **CSI 3개월 이동평균** — 하락 전환 시 NB 검색 방어 캠페인 트리거
7. **NB Korea 검색 trend 4주 이동평균** — Global 수요 예측 선행 지표

---

*Stage 0 Quick Exploratory Pass: COMPLETED.*
*Stage 3 Cross-cutting Insights: APPENDED (2026-04-30).*
*Stage 4 Leading Indicator Insights: APPENDED (2026-04-30).*
