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

### Data Point 9: NB Korea → Global Structural Lead (+10.4 weeks) [Sign Correction Applied 2026-05-03]

> **Sign correction notice (2026-05-03):** Stage 7 Track A2 (DP24) detected Stage 4 sign convention error. Corrected statement: **NB Global → Korea structural lead ~10.4w** (direction inverted; magnitude robust within ±2w via leakage-free replication). Original DP9 body below preserved as-is for trace value. See DP24 + stage7_checkpoint.md §12.4.4 for cumulative quantitative validation.

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


## Stage 5 Anomaly Detection Insights

### Data Point 11: Celebrity-Driven Search Dominance in NB Korea

2024-09-15 주간 (z=+2.15, 3-way agreement)은 세 가지 NB Korea 이벤트가 동시에 겹쳤다: 송혜교 밀라노 SNS 착용샷(전 사이즈 품절 대란), 아이유 글로벌 앰버서더 가을 화보, Stone Island x NB 991V2 GHOST 콜라보 공개. 셀럽 효과가 제품 출시 효과를 압도하는 구조가 확인되었다.

Stage 5 전체 최고 severity (z=+4.24, 2025-04-20)도 992 팝업스토어 + 하프마라톤 대회 + 키즈 샌들 완판이라는 복합 이벤트 구조였다. NB Korea의 anomaly spike는 단일 제품보다 **이벤트 적층(event stacking)**에 의해 발생하는 패턴이 반복적으로 관찰된다.

BDC 시사점: NB Korea 캠페인 기획 시 셀럽 콘텐츠 + 제품 출시 + 이벤트를 의도적으로 같은 주에 집중시키는 "event stacking" 전략의 검색 효과가 실증적으로 확인되었다.

### Data Point 12: CSI 급락과 Multi-Brand Dip 매칭

2024-12 CSI 87.9 (전월 대비 -12.7pt)와 2025-02 CSI 95.0 저점은 각각 NB+puma korea dip 클러스터와 adidas+nike+puma korea dip을 설명한다. 이 매칭은 Stage 4 Granger 결과(NB: CSI→Search 단방향)와 일관된다 — 거시 경기 하락이 NB 검색 수요를 직접적으로 억제하는 구조가 anomaly 수준에서도 확인되었다.

특히 2025-03-23 (z=+3.00)과 2025-04-20 (z=+4.24)이 CSI 93~94 수준에서 발생한 positive spike라는 점이 주목할 만하다. 낮은 CSI에서도 NB-specific 이벤트(Stone Island 콜라보, 992 팝업)가 macro를 override할 수 있음을 보여준다. 이는 "NB는 CSI에 수동적으로 끌려다닌다"는 단순 해석에 대한 nuance다.

### Data Point 13: Air Max Day 경쟁사 검색 교란 효과

Nike Air Max Day (3/26)는 Nike 자체 시계열에서는 anomaly로 잡히지 않았다(MSTL seasonal이 흡수). 그러나 같은 주 adidas global과 NB global에서 anomaly가 검출되었다. 매년 반복되는 Nike 이벤트가 **Nike에겐 예측 가능한 연례 행사이지만, 경쟁사에겐 비예측적 검색 교란 이벤트**로 작용하는 비대칭 구조다.

이는 MSTL 기반 anomaly detection의 방법론적 장점을 보여준다: 브랜드별 독립 seasonal model이 "해당 브랜드에게 예측 가능한 패턴"과 "비예측적 외부 충격"을 자동으로 구분한다.

### Data Point 14: 2024 봄 올림픽 연도 초과 수요

2024-03-24 ~ 2024-04-28 4주 연속 글로벌 전 브랜드 동반 spike는 MSTL residual에서 검출되었다 — 매년 반복되는 "봄 시즌"은 이미 52주 seasonal이 흡수했으므로, 이 residual spike는 2024년 봄이 **평년 대비 비정상적으로 강했음**을 의미한다.

원인: Paris 2024 올림픽 D-100 캠페인 총공세 (Nike On Air 파리 쇼케이스 + adidas 41종목 올림픽 신발 공개 + NB "We Got Now" 캠페인 + Puma "FOREVER.FASTER." 10년 만의 글로벌 캠페인) + Euro 2024/Copa America 국가대표 키트 공개 + Air Max Day + London Marathon. 올림픽 연도는 정의상 4년에 1회이므로 연간 seasonal에 흡수되지 않으며, 이런 구조적 초과 수요는 올림픽 연도 특유의 패턴이다.

Stage 6 Forecasting 시사점: SARIMAX exogenous 변수로 "올림픽 연도 여부" binary indicator를 포함할 근거가 된다.

### Integrated Business Diagnosis (Stage 5 업데이트)

Stage 4 진단: **"수요-전환 갭 + CSI 수동형 수요 구조 + Korea→Global 10주 선행"**

Stage 5 업데이트: 91.3% false positive 제거 후, NB Korea의 진짜 anomaly 패턴이 드러남:

1. **Event stacking이 핵심 전략**: 단일 이벤트보다 셀럽 + 콜라보 + 이벤트의 동시 집중이 검색 spike를 만든다 (Data Point 11)
2. **CSI 하락은 dip를 만들지만, 강한 이벤트는 CSI를 override**: NB의 CSI→Search 수동 구조에도 불구하고, 이벤트 적층은 macro 역풍을 돌파할 수 있다 (Data Point 12)
3. **경쟁사 이벤트도 기회**: Nike Air Max Day 같은 업계 주목 이벤트가 NB 검색을 동반 상승시킬 수 있다 (Data Point 13)

### BDC Implication (Stage 5 추가)

Stage 4 KPI 7종에 추가:
8. **Event Stacking Density** — 같은 주에 겹치는 이벤트 수와 검색 spike 크기의 상관. 이벤트 기획 시 분산보다 집중이 효과적인지 정량 검증.
9. **Anomaly Detection Method Agreement** — 3-way agreement 건수 월별 추적. 높은 agreement = 높은 신뢰 anomaly.

---



*Stage 0 Quick Exploratory Pass: COMPLETED.*
*Stage 3 Cross-cutting Insights: APPENDED (2026-04-30).*

## Stage 6 Forecasting Insights

### Data Point 15: NB Global ARIMA(0,1,0) — 자기회귀 정보 부재

NB Global 검색 지수의 SARIMAX 최적 order는 (0,1,0), 즉 AR항도 MA항도 없는 random walk with drift다. AR/MA 구조가 없으므로 시계열의 자기상관(autocorrelation)에서 오는 예측 정보가 없고, trend는 drift로, 계절성과 거시 환경은 Fourier + CSI exogenous로 설명된다.

이는 NB Global 검색이 "자체적인 모멘텀이나 관성 없이, 외부 요인에 의해서만 움직이는 수요"임을 시사한다. Stage 4에서 NB Korea가 Global을 ~10주 선행한다는 발견과 결합하면, Global 검색은 Korea의 선행 신호 + CSI 거시 환경이라는 두 외부 요인의 함수일 가능성이 높다.

**BDC 시사점:** NB Global 검색 수요 예측에서 자체 과거 데이터보다 CSI 전망 + NB Korea 추세 모니터링이 더 가치 있다.

### Data Point 16: CSI 탄력성 비대칭 — Korea가 Global 대비 2배 민감

SARIMAX CSI 계수: Korea 3.98 vs Global 2.01 (둘 다 p<0.001). CSI 1pt 상승 시 Korea 검색 ~4pt, Global ~2pt 증가. Korea의 CSI 탄력성이 Global의 약 2배다.

Stage 4 Granger 결과("NB는 거시 경기 후행 수요 구조")의 정량적 확인이면서, 추가 발견이다. Korea가 더 민감한 이유는 두 가지로 해석 가능하다: (1) 한국 소비자의 NB에 대한 수요가 더 재량적(discretionary)이어서 경기 변동에 탄력적, (2) 한국 시장이 브랜드 관성이 약한 신생 시장이라 외부 환경에 더 반응적.

**BDC 시사점:** CSI 하락 전환 시 Korea 캠페인 강화 우선순위가 Global보다 높다. Korea의 CSI 민감도가 2배이므로 같은 macro 하락에서 Korea 검색 감소폭이 더 크다.

> *This elasticity is SARIMAX-specific. Prophet's piecewise trend absorbs CSI-correlated structural variation, reducing CSI regressor marginal effect to near-zero (Korea -0.09, Global 0.002). The elasticity asymmetry reflects real demand structure but is observable only in models with rigid trend specification.*

### Data Point 17: Foundation Model Anti-Scaling — 짧은 시계열에서의 역전

Chronos-base(200M params)가 Chronos-small(46M params)보다 NB Korea, NB Global 모두에서 성능이 떨어졌다 (Korea RMSE: small 7.20 vs base 7.80, Global: 3.65 vs 3.99). 일반적인 scaling law 기대와 반대.

174주 context는 base 모델의 사전학습 과정에서 학습된 장기 패턴을 정당화하기에 불충분하다. base가 수천~수만 시점 시계열에서 학습한 longer-range dependency는 174주에서 데이터 근거가 없으므로 noise로 작용한다. 모델의 prior가 evidence를 압도하는 구조.

**실무 시사점:** 200시점 미만의 짧은 시계열에 foundation model을 적용할 때, 모델 크기를 키우는 것이 성능 개선을 보장하지 않는다. 오히려 smaller variant가 데이터 규모에 맞는 prior complexity를 제공할 수 있다.

### Data Point 18: Prophet 메커니즘 3각 분석 — Changepoint 우위, CSI 흡수, Fourier 과적합

Prophet이 SARIMAX를 이긴 이유를 3가지 각도에서 분석:

**첫째, Changepoint가 왜 이겼는가 (ablation).** Prophet ablation (yearly fourier_order K=2 vs K=10): changepoint detection이 Prophet 우위의 주된 원인. Korea에서 changepoint 기여 147%, Global 66%. SARIMAX의 단순 drift는 COVID 회복 → 올림픽 효과 → 2025 전환 등 구조적 break를 포착하지 못한다.

**둘째, CSI 정보가 어디로 갔는가 (흡수).** Prophet CSI 계수: Korea -0.09, Global +0.002 (거의 소멸). SARIMAX: Korea +3.98, Global +2.01. Prophet의 25개 changepoint가 CSI와 상관된 "거시 환경에 따른 수요 레벨 변화"를 trend로 먼저 흡수하여, CSI regressor에 남는 marginal effect가 없다. 이건 Prophet이 CSI 없이도 비슷한 정보를 trend로 잡고 있다는 뜻이다. SARIMAX는 drift뿐이라 CSI가 그 역할을 전부 떠안는다. Prophet이 이긴 이유와 CSI 계수 소멸은 같은 현상의 양면.

**셋째, Fourier 과적합이 왜 발생하는가 (K=10 역효과).** Korea에서 K=10이 K=2보다 RMSE가 높다 (5.85 > 5.57). 174주에서 연간 시즌의 고차 하모닉(K≥3)은 데이터 근거가 불충분하여 event-driven noise를 fit한다. Global에서는 smoother dynamics 덕에 K=10이 약간 유리하지만, 개선폭(34%)은 changepoint(66%)에 비해 부차적.

Data Point 15와 함께 읽어야 한다 — SARIMAX는 Global에서 AR/MA 구조 부재를 확인하고, Prophet은 같은 현상을 "자기회귀 모멘텀 없는 piecewise linear trend"로 재해석한다. 두 모델이 같은 결론에 수렴: NB Global 검색은 자체 추진력이 없다.

**BDC 시사점:** 예측 모델 선택 시 "더 복잡한 모델 = 더 좋은 성능"은 보장되지 않는다. 데이터 규모와 구조에 맞는 적정 복잡도가 핵심.

### Integrated Business Diagnosis (Stage 6 업데이트)

Stage 5 진단: **"Event stacking 전략 + CSI override 가능성 + 경쟁사 이벤트 기회"**

Stage 6 업데이트: 예측 모델 4-way 비교(SARIMAX/Prophet/LSTM/Chronos)를 통해 NB 검색 수요의 구조적 특성이 정량적으로 확인됨:

1. **Prophet 전승 — changepoint detection이 핵심**: piecewise linear trend가 COVID 회복 → 올림픽 효과 → 2025 전환 등 구조적 break를 포착. SARIMAX의 단순 drift보다 우수.
2. **Korea는 CSI에 2배 민감 — 거시 방어 우선 시장**: CSI 하락 시 Korea 검색이 가장 먼저, 가장 크게 타격. 캠페인 자원 배분에서 Korea 방어가 우선. (SARIMAX-specific, Prophet에서는 trend가 흡수)
3. **Global은 자기 모멘텀이 없다**: ARIMA(0,1,0) — Global 수요 예측은 자체 과거보다 Korea 선행 신호 + CSI 추적이 핵심.
4. **짧은 시계열에서 통계 모델 > DL**: 174주 규모에서 Prophet/SARIMAX의 파라미터 효율성이 LSTM의 모델 용량을 압도.
5. **대시보드 모델 단일화**: Prophet이 양쪽 모두 1위 → Stage 8 Streamlit에서 단일 프레임워크로 구현 가능.

### BDC Implication (Stage 6 추가)

Stage 5 KPI 9종에 추가:
10. **CSI 탄력성 모니터링** — CSI 변동 × Korea 탄력성(3.98) 기반 검색 영향 추정. CSI 3pt 하락 시 Korea 검색 ~12pt 감소 예상.
11. **26주 검색 예측 Prophet Baseline** — CSI + Fourier K=2 + changepoint 기반 분기 예측을 월 1회 업데이트. RMSE 5.57(Korea)/2.54(Global) 기준 ±2σ 경고 밴드.

---

## Stage 7 Korea-Global Bridge Insights

Stage 7는 CSI → NB Korea → NB Global 3단계 chain 가설을 검증하는 stage로 시작했으나, 검증 과정에서 누적된 self-diagnostic findings (DP20 → DP23 → DP24)이 발견되며 **methodology validation stage**로 재정의됐다. 각 DP는 외부 review 없이 internal sanity check만으로 detection됐다.

### Data Point 19: 5-Dimension Orthogonal Null × 11 Tests (Sign-Corrected)

Stage 7은 chain 가설을 5가지 직교 차원(VARX 양방향 + monthly Granger 양방향 + trend mediation 양방향 + diff1 mediation 양방향 + lagged cointegration 양방향)에서 11개 검정으로 verify했고, **모두 reject**됐다.

| 차원 | 검정 | 방향 | 결과 |
|---|---|---|---|
| 단기 (weekly diff1) | VARX(2) Granger | Korea→Global | F=1.45 p=0.23 |
| 단기 (weekly diff1) | VARX(2) Granger | Global→Korea | F=0.23 p=0.63 |
| 단기 (weekly diff1) | VARX(2) joint LR (CSI dist. lag) | — | chi2=13.75 p=0.09 marginal |
| 중기 (monthly mean) | Monthly Granger | Korea→Global | min p=0.14 |
| 중기 (monthly mean) | Monthly Granger | Global→Korea | min p=0.06 marginal |
| Trend mediation (original direction) | MBB BCa CI | K→G | [−0.39, +0.18] |
| Trend mediation (sign-corrected) | MBB BCa CI | G→K | [−0.12, +0.18] |
| Diff1 mediation (original direction) | MBB BCa CI | K→G | [−0.04, +0.003] |
| Diff1 mediation (sign-corrected) | MBB BCa CI | G→K | [−0.06, +0.007] |
| Lagged cointegration | Engle-Granger AEG | Korea_{t-lag} → Global | all p > 0.40 |
| Lagged cointegration | Engle-Granger AEG | Global_{t-lag} → Korea | all p > 0.94 |

**해석:** CSI는 Korea와 Global을 **직접 그리고 독립적으로** 구동하고, 두 region 사이에는 mediation channel이 없다. Korea와 Global의 trend 형태 유사성(DTW + CC, sign-corrected)은 common driver에 대한 differential reactivity의 결과이지 인과 chain의 증거가 아니다. **5차원 직교 null은 단일 false-negative 가능성을 배제**하며, 본 프로젝트에서 가장 광범위하게 검정된 null hypothesis이다.

**BDC Implication:** Korea 수요 변동을 Global 수요 driver로 해석하지 않는다. CSI 또는 그 외 macro driver를 직접 monitoring하는 것이 더 정확한 forecast input이다. Cross-region 변동성은 monitoring view (dashboard reference)이지 predictive feature가 아니다.

### Data Point 20: Mediation Spurious Correlation Pre-emption (Step 0 Mitigation Pattern)

Stage 7 Step 0에서 trend 시계열에 ADF + KPSS + cointegration 전수 검사를 실행한 결과, korea_trend ≈ I(1) borderline + global_trend ≈ near-integrated + zero-lag cointegration p=0.9433로 **trend regression이 spurious correlation 위험에 직접 노출**됨이 사전 식별됐다.

대응으로 mediation analysis를 **두 specification 병행**하도록 사전 commit (Decision 4):
1. **Trend regression** (primary): MSTL trend lagged → mediation indirect coefficient
2. **Diff1 regression** (robustness): search diff1 lagged → mediation indirect coefficient (stationary, spurious-safe)

검정 결과 trend mediation은 inconsistent signature (% indirect 120%, MBB CI sign-unstable)을 보였고, diff1 mediation은 tight near-zero CI를 반환하며 disambiguating. Step 0 사전 commit이 post-hoc result chasing 가능성을 차단한 사례.

**Methodology validation 가치:** 본 design choice는 사전에 식별 안 된 다른 위험(DP23 MSTL forward-looking leakage)에 대해서도 robustness check로 기능했다. 단일 design choice가 두 독립 위험에 대한 안전장치로 작동한 사례 — DP23 본문 참조.

**BDC Implication:** 비정상성 검사 + alternative specification 사전 commit은 시계열 분석의 default 위생 절차여야 한다. spurious result를 회의적으로 검증하는 design 자체가 분석 결과의 신뢰성을 보장한다.

### Data Point 21: Three-Dimensional Separation Robust [Sign Correction Applied 2026-05-03]

DTW + cointegration + mediation 세 검정의 결과 패턴은 Stage 4부터 다음과 같이 robust:

| 검정 차원 | 결과 |
|---|---|
| Shape similarity (DTW + CC) | 존재 (~10w lag, sign-corrected) |
| Level equilibrium (cointegration) | 부재 (lagged cointegration null bidirectional) |
| Causal mediation (mediation) | 부재 (5-dim orthogonal null per DP19) |

**3-dimensional separation 결론:** Korea와 Global trend는 형태가 닮았지만 균형 관계도, 인과 매개도 없다. 이는 common driver(CSI 등)에 의한 parallel response의 시그니처이지, 두 region 사이의 직접 연결의 증거가 아니다.

**Sign correction 영향 (DP24):** 라벨 정정 후 결론은 다음으로 정정된다:

> "**NB Global이 Korea를 ~10주 선행하는 shape similarity** (lead direction inverted from Stage 4 original labeling), 단 level equilibrium 부재 + causal mediation 부재."

3-dimensional separation logic 자체는 robust — 어느 방향이 lead인지에 무관하게 "shape exists, equilibrium absent, mediation absent" 구조가 보존된다. 부호 정정은 lead 방향 라벨링만 영향.

**BDC Implication:** Korea-Global 관계는 **monitoring view** (Global 트렌드 시각적 reference로 Korea 수요 anticipation)에 적합하나, **predictive view** (Global을 Korea forecast input으로 직접 투입)는 부적합 — DP24 + Track A3 degradation outcome 참조.

### Data Point 22: Sentinel Framing — Korea = Common Driver Sentinel [DEPRECATED 2026-05-03]

> **DEPRECATED 2026-05-03 — replaced by DP24.** DP22 was authored Stage 5 / early Stage 7 prior to detection of Stage 4 sign convention error (DP24). DP22's "Korea sentinel of common drivers via differential reactivity" framing inverted direction with sign correction: Global is the precursor, Korea is the receiver. The Mirror Sentinel + Differential Reactivity successor framing (DP24) preserves the BDC operational role (Korea ↔ Global translator) with direction reversed. DP22 body below preserved as-is for trace value (advisor decision: trace preservation pattern, identical to stage4_checkpoint.md footnote handling).

**[Body preserved as authored pre-DP24]**

CSI → NB Korea → NB Global 3-stage chain 검증 결과 chain hypothesis는 reject되나, 이를 reframe할 때 BDC 활용 시각이 가장 강한 narrative를 제공한다. NB Korea 수요는 Global 수요의 직접 driver는 아니지만, common driver(CSI 등 macro signal)에 대해 Global보다 빠른 반응을 보이는 **sentinel** 역할을 한다. Korea의 빠른 macro 반응성(elasticity 3.98, Stage 6 DP16) + DTW shape similarity(+10.4w, Stage 4 DP9) + Stage 7 lagged cointegration null이 함께 이 framing을 지지한다.

**BDC Implication (DEPRECATED):** Korea 검색 trend의 4주 이동평균을 Global 수요 예측의 leading indicator로 활용. KPI 7 dashboard에 직접 surface.

→ **Successor: DP24 + KPI 7 redefinition (sentinel direction inverted, BDC role preserved)**

### Data Point 23: MSTL Forward-Looking Leakage (Self-Diagnostic)

Track A3 (Korea trend exogenous → Global Prophet)의 narrative-negative 결과(Prophet RMSE +59% degradation)가 self-diagnostic을 trigger했다.

**Detection trail (3 steps):**

1. **Pattern recognition.** Lag grid CV 결과가 lag 6w best mean RMSE 4.38, lag 14w 6.69로 **monotonic increasing** — 짧은 lag일수록 미래 정보 누설이 더 많다는 leakage signature와 정확히 일치.

2. **Algorithm inspection.** `statsmodels.MSTL`은 two-sided STL filter를 사용 — trend at week T가 T+w 데이터까지 사용해 추정됨. Lagged regression의 input으로 쓰면 미래 정보가 누설.

3. **Quantification.** `bridge_mstl_leakage_check.py` — expanding-window MSTL real-time trend 추정 후 bulk-fit trend과의 차이 측정. korea_trend ratio 0.2689, global_trend ratio 0.2612, 둘 다 0.15 significance threshold 초과. **Significant leakage 확정.**

**대응 — Track A3 재설계:** 부호 정정 + MSTL 미사용 + leakage-free trend (raw search lagged 또는 expanding-window MSTL trend)로 재설계 → DP24 narrative와 결합.

**Methodology validation 가치:** Step 0의 diff1 robustness specification (DP20에서 사전 commit)이 spurious regression risk와 MSTL leakage risk **둘 다에 대한 robustness check**로 incidentally 기능했다. 단일 design choice, 두 독립 risk 대응. 본 프로젝트의 가장 강한 design value 사례.

**BDC Implication:** ML/통계 라이브러리의 default behavior가 forecast pipeline에 미세하게 leakage를 일으킬 수 있다. 자체 진단 routine + alternative specification 병행이 default 위생 절차여야 한다.

### Data Point 24: Stage 4 Sign Convention Inversion (DP22 Successor)

Track A3 self-diagnostic (DP23) 진행 중 leakage-free DTW + CC 재계산이 Stage 4 결과와 `direction_flipped` 분류를 출력. 이를 sanity check한 결과 Stage 4 sign convention error가 발견됐다 — DP22가 deprecated된 successor evidence.

**Mathematical inversion:**

`scipy.signal.correlate(kr, gl)` returns `corr[k] = Σ_n kr[n+k] * gl[n]`. 양수 lag k에서 maximize란 의미: kr를 +k만큼 shift해서 gl과 align되는 시점이 가장 강한 상관 — 즉 `kr[n+k] ≈ gl[n]` → Korea의 미래 시점(n+k) = Global의 현재 시점(n) → **Global이 Korea를 k만큼 선행**.

DTW도 동일 패턴: `path[:,0] - path[:,1]` (Korea idx − Global idx) > 0이면 Korea의 늦은 시점이 Global의 이른 시점에 align — **Global이 Korea를 선행**.

Stage 4 코드는 이를 "Korea leads"로 라벨링 — verbal-mathematical inversion. 두 메서드 모두 동일 convention 사용으로 인해 시그니처 패턴이 일관되게 inverted.

**3 Independent Quantitative Signatures Stack:**

| # | Signature | Pre-correction | Post-correction | Finding |
|---|---|---|---|---|
| 1 | Synthetic Korea-leads-by-5w probe | — | Stage 4 code returns CC −5, DTW −4.57 | Magnitude correct, sign inverted |
| 2 | Mediation re-run with corrected direction | % indirect 120%, MBB CI [−0.39, +0.18] | % indirect 11%, MBB CI [−0.12, +0.18] | Inconsistent signature dissipates + CI 47% narrowing |
| 3 | Track A3 degradation magnitude | Korea→Global Prophet/SARIMAX +41/+59% | Global→Korea Prophet/SARIMAX +9/+11% | Magnitude reduction 1/4–1/5 — sign correction removes both DP23 leakage amplifier and direction interference |

**Three signatures observable only when point estimate aligns with true direction.** Their joint dissipation under sign correction constitutes the strongest quantitative evidence stack for Stage 4 sign convention error.

**Cascade applied:**

| 영역 | Original | Corrected |
|---|---|---|
| DP9 lead direction | Korea → Global +10.4w | **Global → Korea +10.4w** |
| DP21 shape similarity label | Korea leads shape | **Global leads shape** (3-dim separation logic robust) |
| DP22 sentinel framing | Korea = sentinel | **Mirror Sentinel** — Global = precursor, Korea = receiver, BDC translator role preserved |
| KPI 7 leading indicator | Korea trend MA | **Global trend MA** (KPI 7 redefinition + operational scope refined) |
| `mart.korea_global_lag` | Stage 4 raw | **Migration 011 applied 2026-05-03** — 12 rows sign-flipped + labels swapped |
| `stage4_checkpoint.md` | original analysis preserved | **Sign Correction Notice footnote applied 2026-05-03** (trace value, cross-ref to §12.4.4) |

**Methodology Validation Climax:**

> Self-diagnostic detection of sign convention error in own analytical pipeline — without external review — is the demonstrable evidence of analytical governance discipline.

DP20 (사전 차단) → DP23 (self-diagnostic) → DP24 (검증 부산물의 critical finding)의 3단 stack은 Stage 7을 단순 hypothesis test stage가 아닌 **methodology validation stage**로 정의한다.

**BDC Implication:** 분석 pipeline의 sign convention은 verbal과 mathematical convention이 일치하는지 사전 검증해야 한다. Self-diagnostic routines (synthetic test data probe, multi-method cross-validation, alternative specification 병행)이 enterprise-grade 분석 governance의 핵심이다. 본 발견이 Stage 8 dashboard 진입 전에 잡혔다는 점이 중요 — 면접 narrative에서 가장 강한 self-skepticism evidence.

### KPI 7 Redefinition (Sign-Corrected + Operational Scope Explicit)

**Original (pre-DP24):** "NB Korea 검색 trend 4주 이동평균 — Global 수요 예측 선행 지표"

**Corrected (post-DP24 + post-Track-A3):**

> "NB Global 검색 trend 4주 이동평균 — Korea 수요 monitoring leading indicator (directional reference; predictive feature로는 active interference detected)"
>
> **Operational scope:**
> - 사용 O: BDC 대시보드 시각화 (Korea 수요 방향성 reference, 선행 ~10주)
> - 사용 X: Korea forecast 모델 input (Track A3 결과 Prophet/SARIMAX 모두 RMSE 9~11% 악화 — interference detected)

**Refinement rationale (post-Track-A3):** Track A3 sign-corrected (Global → Korea) 결과 Global signal을 Korea forecast 모델 input으로 추가 시 양 모델 모두 RMSE degradation (Prophet −9.01%, SARIMAX −10.94%, DM p<0.001). Sentinel framing 자체는 robust (DTW shape similarity + lagged cointegration null bidirectional + mediation null bidirectional)하나, **monitoring과 predictive 사용은 작동 영역이 분리됨** — DTW에서 보이는 shape lead는 dashboard reference에 적합하되, Prophet changepoint absorption + SARIMAX explicit drift 모두 Global lagged regressor에 대해 active interference. 

KPI 7의 BDC 활용은 dashboard 시각화 layer로 한정되며 forecast model layer로는 propagate되지 않는다. 이 operational asymmetry 자체가 finding — Stage 8 dashboard tooltip에 직접 반영될 design rationale.

### Integrated Business Diagnosis (Stage 7 업데이트)

Stage 6 진단: "수요는 있으나 자기 채널로 전환되지 않는다 + 외부 거시 의존이 강하다."

Stage 7 업데이트:

> NB Korea 수요는 NB Global 수요를 직접 구동하지 않는다 (5-dim orthogonal null). 두 region 모두 CSI 등 macro driver를 직접 받으며, 그중 Global이 Korea를 ~10주 선행하는 monitoring signal로 작동한다. 단 Global signal을 Korea forecast 모델 input으로 직접 투입하면 RMSE가 악화 — **BDC의 Korea forecast pipeline은 CSI exogenous + Korea autoregressive 구조로 운영하고, Global signal은 dashboard reference layer에서만 활용**해야 한다.

**약점 재정의:**

NB Korea의 **거시 경기 의존** (Stage 4 DP10) + **자기 채널 부재** (Stage 3 + Stage 6) 위에, **Global 신호도 forecast input으로 통합 안 됨** (Stage 7 Track A3) — 모든 layer에서 single dependency가 작동하고 있다. CSI 단일 driver가 양 region 모두를 직접 구동하는 구조라 다양화 전략이 필요.

**시사점:**

NB Korea/Global 양 region을 위한 BDC analytics framework는:

1. **Forecast layer**: 각 region 독립 모델 (CSI exogenous + 지역 autoregressive)
2. **Monitoring layer**: Cross-region leading indicator (Global → Korea ~10w, sign-corrected) for direction anticipation
3. **Methodology validation layer**: 자체 diagnostic routines (sign convention, leakage detection, alternative specification 병행)

### BDC Implication (Stage 7 추가)

Stage 6 KPI 11종에 추가 + 정밀화 + 신규 KPI:

12. **5-Dimension Orthogonal Null Verification Pattern** (KPI 7과 별개의 methodology asset) — 향후 cross-region/cross-channel 가설 검정 시 본 프로젝트의 11-test framework (VARX × monthly Granger × mediation × cointegration, 모두 양방향)를 default verification protocol로 적용. 단일 검정 의존 회피.

13. **Methodology Validation Stage Pattern** (governance asset) — 신규 stage 진입 시 reflexive self-diagnostic routine을 commit. DP20 (사전 차단) → DP23 (self-diagnostic) → DP24 (검증 부산물) 3단 cascade가 default 적용 패턴. Stage 7이 본 프로젝트의 governance climax — 면접 자료의 핵심 narrative.

**KPI 7 운영 정밀화 (DP24 + Track A3 cascade):** dashboard 시각화 layer × forecast model layer 분리 운영. Global signal은 monitoring O / predictive X.

---


*Stage 6 Forecasting Insights: APPENDED (2026-05-01, updated with Track E Prophet + DP18).*
*Stage 7 Korea-Global Bridge Insights: APPENDED (2026-05-03, DP19~24 + KPI 7 redefinition + DP9 sign correction tag + DP22 deprecated).*
*다음: Stage 8 — BDC Analytics Dashboard Construction.*
