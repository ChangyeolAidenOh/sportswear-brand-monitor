# Comprehensive Advisor Handoff — NB Korea BDC 포트폴리오 프로젝트

**작성일:** 2026-04-30
**최종 업데이트:** 2026-05-01 (Stage 6 COMPLETED 반영)
**용도:** 새 종합 어드바이저 채팅 시작 시 컨텍스트 인수인계
**대체 채팅:** 기존 종합 어드바이저 채팅 (Stage 0~4 전 과정 추적)

---

## 1. 프로젝트 정의

**대상:** 뉴발란스코리아 2026 신입 공채 — Commercial / Business Data Coordinator (BDC)
**프로젝트명:** Global Sportswear Brand Performance Monitor
**핵심:** 검색 트렌드 + 소셜 시그널 + 거시 지표 + 재무 데이터 통합 → "소셜 → 검색 → 매출" 선행 지표 체인 검증 + Korea ↔ Global Bridge 분석 + Streamlit/Power BI 대시보드

**JD 우대사항 매핑:** SQL, Power BI, 데이터 분석, 글로벌 스포츠웨어 산업 관심

---

## 2. 운영 구조 — 3채팅 시스템

| 채팅 | 역할 | 토큰 사이클 |
|---|---|---|
| **종합 어드바이저** | 전체 흐름 + stage 간 정합성 + 큰 결정 + narrative 통합 | 프로젝트 전체 (토큰 한계 시 인수인계로 이전) |
| **단계별 어드바이저** | stage 내 의사결정 상의 (코드 작성 금지) | stage 종료 시 닫고 새로 |
| **단계별 진행** | 코드/문서 직접 작성 | stage 종료 시 닫고 새로 |

**프로토콜:**
- Stage 시작 시: 종합 어드바이저가 stage 진입 메시지 작성 → 단계별 두 채팅에 전달
- Stage 진행 중: 진행 채팅이 코드 작성, 막힘 시 단계별 어드바이저로, 큰 결정은 종합 어드바이저로
- Stage 종료 시: 진행 채팅이 stage_N_checkpoint.md 작성 → 종합 어드바이저가 검토 → 다음 stage 진입 메시지 작성 → 단계별 두 채팅 새로 시작

**Stage 진입 메시지 작성 시 4가지 필수 보강 (Stage 1~5 검증):**
1. 어드바이저 메시지에 **핵심 우려사항** 섹션 명시 — 첫 응답 우선순위 결정
2. 진행 메시지에 **즉시 착수 가능 vs 어드바이저 결정 대기** 분리 — 병렬 효율
3. 진행 메시지에 **Step 0 데이터 검증 쿼리** — 컨텍스트 동기화 + 잠재 문제 조기 발견
4. 어드바이저 메시지에 **전 stage 영향 구체화** — "무엇을 발견" + "현 stage에 어떻게 영향"

---

## 3. 환경 정보

- **하드웨어:** M2 MacBook 16GB, macOS
- **IDE:** PyCharm
- **위치:** `/Users/aiden/PycharmProjects/sportswear-brand-monitor`
- **Python:** 3.11 (`.venv/`)
- **DB:** PostgreSQL 16 Docker Compose (port **5433**, db `nb_monitor`, user `nb_admin`)
- **GitHub:** `ChangyeolAidenOh/sportswear-brand-monitor`
- **폴더 컨벤션:** `database/` (계획서의 `db/` 대신), `collectors/`, `analysis/`, `notebooks/sql/`, `figures/`, `docs/`

---

## 4. 프로젝트 지식에 반드시 있어야 하는 문서

종합 어드바이저가 컨텍스트 재구축 시 다음 문서를 읽으면 즉시 동기화됨:

1. **v3 계획서** (`sportswear_brand_monitor_project_plan_v3.md`) — 전체 설계, §4.5/§4.7/§4.8/§12에 Stage 4/6/7 결과 반영됨 (Stage 7 close 2026-05-03 동기화)
2. **methodology.md** — §1~12 완비 (Granger 축소, sentiment, MSTL, DTW, Granger 해석, Anomaly Detection, Forecasting, Korea-Global Bridge Methodology Validation Stage)
3. **exploratory_findings.md** — Stage 0 H1~H6 + Stage 3 Cross-cutting + Stage 4 Leading Indicator [Sign Correction Applied 2026-05-03] + Stage 5 Anomaly + Stage 6 Forecasting + Stage 7 Korea-Global Bridge (Data Point 1~24, KPI 13종)
4. **stage1_checkpoint.md** — Collector 6개, raw 23,292행
5. **stage2_checkpoint.md** — SQL ETL 8개, staging 11,037행, mart 5 + VIEW 5
6. **stage3_checkpoint.md** — MSTL + Hybrid Sentiment
7. **stage4_checkpoint.md** — Granger 4-pattern + DTW 3-way [Sign Correction Notice footnote applied 2026-05-03]
8. **stage5_checkpoint.md** — 3-way anomaly comparison + event matching
9. **stage6_checkpoint.md** — SARIMAX/LSTM/Chronos/Prophet 4-way forecasting
10. **stage7_checkpoint.md** — 5-dim orthogonal null + DP24 sign correction cascade + Track A3 degradation outcome
11. **docs/stage7_bridge_report.md** — Stage 7 1-page narrative summary (4-layer climax, 면접 자료 직접 활용)
12. **docs/stage8_checkpoint.md** — Stage 8 dashboard complete (6-tab, 13 KPI, dual data source, live URL)
12. **coding_conventions.md** — Stage 0 spike 패턴 기반 코딩 컨벤션

---

## 5. Stage 0~7 진행 요약

### Stage 0 — Quick Exploratory Pass (COMPLETED)

**H3 (확정):** 530 의존도 51.2%, +2.36%p/Q (p=0.0213) — KPI 1
**H5 (확정):** D2C 검색 -0.179%/week (p=0.0001) — KPI 2
**H6 (확정):** NB 패딩 시즌 시작 38주차 (노스페이스 대비 2.6주 빠름), 절대 규모 정체
**H4 (방향 반전):** NB 검색 → Instagram 2주 선행 (가설 정반대)
**H1, H2 (보류):** Stage 3/4에서 정밀 분석

핵심 의사결정:
- 의류 카테고리 분석은 D1/D2 신발 분석과 분리, "뉴발란스 의류" 자체 검색량 0이라 데이터 한계
- NB 패딩 + 노스페이스 비교를 별도 분석으로 추가 (Past 5y)
- Google Trends 메인 키워드는 Korea = Search term `+` 연산자, Worldwide = Topic mid

### Stage 1 — Data Collection (COMPLETED)

6개 collector, raw 23,292행:
- Naver DataLab 1,201 (4 그룹: brand/nb_product/nb_social/nb_channel)
- Google Trends 8,698 (8 CSV stitched)
- YouTube 3,325 (90 videos + 3,235 comments)
- Naver Blog/Cafe 10,000
- ECOS 52 (CSI 월별)
- Financials 16 (T1-T4 source tier governance)

핵심 의사결정:
- Naver Blog/Cafe `--clear` INSERT 패턴 → post_date 기반 시계열 변환 가능 (Cafe는 0% NULL 한계 확정)
- demographic 분해는 추후 별도 collector로 분리 (YAGNI)
- nb_social/nb_channel sparse 데이터는 raw 보존, staging 제외

### Stage 2 — SQL ETL (COMPLETED)

8개 SQL 파일, staging 11,037행, mart 5 테이블 + 5 VIEW:
- 530 Korea avg share **54.98%** (Stage 0 H3 51% 대비 심화)
- Korea=530 vs Global=9060 dominant 52~55%
- 574 = cross-region anchor (Korea +82.28% divergence)
- **NB Korea over-index +34.94% search, +16.43% SoV vs Global** (신규 발견)

핵심 의사결정:
- Granger Chain 3→2 stage 축소 (소셜 시계열 본질적 불가능 확정)
- methodology.md §1 narrative 작성 (Plan Y 검토 후 기각)
- 30주 임계값 명시

### Stage 3 — Seasonal + Sentiment (COMPLETED)

**Track A — MSTL 시즌 분해:**
- STL → MSTL 주축 전환 (잔차 분산 48~75% 감소, 8개 시계열 모두)
- 분기(13주) sub-annual 시즌 발견 — Stage 0 H2 재해석
- **SS/FW Ratio 반전:** 530 Korea 1.18 → **0.86** (FW-dominant)
- **Korea 5개 제품 모두 FW-dominant vs Global SS-dominant** 비대칭
- 992 Korea +43pt residual spike (Stage 5 ground truth)

**Track B — Hybrid Sentiment:**
- 키워드 사전 v2: Product 96 / Channel 14 / Resale 2 (3-way)
- 협찬 필터 11 패턴 (1.3% flagged, t=4.48 p=0.0005)
- Hybrid 라우팅: Keyword 97.4% + Claude Batch API 2.6%
- 비용 35.8 KRW/만건 (예상치 정확 일치)
- **NB sentiment +0.289 (4사 최저), neutral 45.6% (최고)** — 검색-감성 비대칭

핵심 의사결정:
- methodology.md §5 (MSTL transition), §6 (Hybrid Sentiment) 신설
- social_sentiment_static 비정규화 (의도적 denormalization)
- v3 §5.1: SARIMAX with quarterly exogenous dummies (Stage 6)
- v3 §5.1: Chronos foundation model 추가

### Stage 4 — Leading Indicator Validation (COMPLETED)

**Track A — Search ↔ CSI Granger:**
- 8 brand×region 양방향 검정, 4-pattern 발견
- **Original hypothesis 25% 지지** — 정직한 가설 부정
- **NB Korea/Global 모두 CSI→Search 단방향** (양 지역 일관)
- adidas/global robust (lag 4 p=0.0140)
- 5/8 Engle-Granger cointegration (NB Korea 강함 p=0.0008)

**Track B — DTW Korea-Global Lead-Lag:**
- 3-way 비교 (Raw/Trend/Residual)
- **NB trend lag +10.4w** (CC +9w 수렴)
- Stage 0 H1 correction chain: -167w → +48w → +10.4w
- Nike/Adidas/Puma 불안정 (norm DTW 분리)

핵심 의사결정:
- methodology.md §7 (Granger validation), §8 (DTW methodology), §9 (Granger interpretation) 신설
- exploratory_findings.md Data Point 9, 10 + 3-stage chain 가설 추가
- v3 §4.5, §12 업데이트

### Stage 5 — Anomaly Detection Refinement (COMPLETED)

**Track A — Z-score Baseline Verification:**
- Stage 2 anomaly_log 재검증: 69행, rolling_zscore_8w, |z| > 2.0
- MSTL residual z-score (동일 threshold) 대비 confusion matrix 산출

**Track B — MSTL Residual Anomaly Detection:**
- 1,392행 (8 brand×region) residual 추출
- |z| > 2.0: 70행, |z| > 3.0: 11행
- **핵심 발견: Stage 2 anomaly의 91.3% (63/69)가 false positive** — 분기 패턴 seasonal artifact

**Track C — Isolation Forest:**
- contamination=0.05, per-series 독립 모델, 72행 검출
- M+IF agreement 52/54건이지만 동일 입력(MSTL residual) → 독립 검증 아님
- 이 한계를 Tier 구조로 해결 (Tier 1: Z-score 포함 = 독립 교차검증)

**Track D — Event Matching & Evaluation:**
- events_calendar 25건 수동 큐레이션 (event_origin: scheduled 7 / investigated 18)
- 매칭 결과: 53/222 anomaly_log 행 matched
  - mstl_residual_2.0: 23/70 (33%), isolation_forest: 20/72 (28%), rolling_zscore_8w: 6/69 (9%)
- Tier 1 Precision 71.4% (5/7), Scheduled EDR 85.7% (6/7)
- "Recall" → "Event Detection Rate" 명명 변경 (anomaly-driven calendar caveat)

핵심 의사결정:
- methodology.md §10 신설
- exploratory_findings.md Data Points 11-14
- DBSCAN 미채택, LSTM Autoencoder 미채택
- 올림픽 indicator — Stage 6 SARIMAX exogenous 보류 (관측치 1회, 자유도 부족)

DB 변경:
- mart.anomaly_log: INSERT mstl_residual_2.0 (70행), mstl_residual_3.0 (11행), isolation_forest (72행)
- staging.events_calendar: INSERT 25행 + event_origin 컬럼 추가 (migration 010)
- mart.anomaly_log: UPDATE matched_event_id 53행

### Stage 6 — Forecasting (COMPLETED)

**Track A — SARIMAX Baseline:**
- NB Korea SARIMAX(0,1,1) + Fourier K=2(52w/13w) + CSI exogenous → RMSE 6.45, MAPE 22.8%
- NB Global SARIMAX(0,1,0) + 동일 exogenous → RMSE 3.23, MAPE 12.2%
- **Global (0,1,0) = random walk** — AR/MA 구조 없음, trend는 drift, 계절성+거시는 exogenous
- **CSI 계수: Korea 3.98 vs Global 2.01** — Korea가 CSI에 2배 민감 (SARIMAX-specific finding)
- Train/Test: 148w/26w (2 quarterly cycles)

**Track B — Stacked LSTM:**
- 2-layer, hidden=64, dropout=0.3, lookback=13w, Attention 없음
- 467:1 param/sample ratio — 구조적 과적합
- Korea RMSE 8.11 (4위) / Global RMSE 2.71 (2위)

**Track C — Chronos Zero-Shot:**
- chronos-t5-small(46M) vs base(200M), univariate only
- **Anti-scaling 발견: small > base (양 시계열 모두)** — 174주 context 불충분으로 base의 complex prior가 noise로 작용

**Track E — Prophet (v3 plan alignment으로 추가):**
- Prophet(additive, quarterly custom, CSI regressor, changepoint_prior_scale=0.05)
- **Prophet 전승: Korea RMSE 5.57, Global RMSE 2.54** — 4개 모델 중 양쪽 모두 1위
- **Ablation 결과: changepoint detection이 주된 이유** (Korea 147%, Global 66%)
- K=10 Fourier는 Korea에서 해로움 — K=2가 최적 (feature parity + changepoint 효과 분리)
- Prophet CSI 계수 소멸 (Korea -0.09, Global +0.002) — changepoint trend가 CSI 흡수

**Track D — 4-Way 비교:**
- **Korea: Prophet (5.57) > SARIMAX (6.45) > Chronos-small (7.20) > LSTM (8.11)**
- **Global: Prophet (2.54) > LSTM (2.71) > SARIMAX (3.23) > Chronos-small (3.65)**
- Prophet 전승 — changepoint detection이 짧은 시계열의 structural break 포착에 유리

핵심 의사결정:
- methodology.md §11 완비 (§11.5 Prophet + ablation 포함)
- exploratory_findings.md Data Points 15-18
- **Stage 8 대시보드 모델 (완료): Prophet for both series** (단일 프레임워크)
- Schema 변경 없음 (forecast CSV 저장, mart.forecast_results는 Stage 8에서 필요 시 생성)

### Stage 7 — Korea-Global Bridge: Methodology Validation Stage (COMPLETED)

**원래 설계:** CSI → NB Korea → NB Global 3-stage chain 검증
**실제 정체성:** Methodology Validation Stage — 누적된 self-diagnostic finding으로 stage 정체성 재정의

**Layer 1 — 5-Dimension Orthogonal Null × 11 Tests:**
- VARX(2) bidirectional null (Korea→Global F=1.45 p=0.23 / Global→Korea F=0.23 p=0.63)
- Monthly Granger bidirectional null (min p=0.14, marginal 0.06)
- Trend mediation bidirectional MBB BCa CI both include 0
- Diff1 mediation bidirectional MBB BCa CI both include 0
- Lagged cointegration bidirectional × 3 lags all p>0.40
- 11개 검정 모두 chain hypothesis reject

**Layer 2 — Self-Diagnostic Chain (DP20 → DP23 → DP24):**
- **DP20**: Step 0 mediation spurious correlation 사전 차단 (alternative specification commit)
- **DP23**: Track A3 narrative-negative 결과 → MSTL forward-looking leakage 자기진단 (3-step trail: Pattern recognition → Algorithm inspection → Quantification, ratio 0.2689/0.2612 above 0.15 threshold)
- **DP24**: Stage 4 sign convention inversion 검증 부산물 (Track A3 leakage-free replication)

**Layer 3 — DP24 Three Quantitative Signatures of Sign Correction Validity:**
1. Synthetic Korea-leads-by-5w probe → Stage 4 code returns CC -5, DTW -4.57 (magnitude robust ±0.43w, sign inverted)
2. Mediation re-run with corrected direction: % indirect 120% → 11% + BCa CI 47% narrowing
3. Track A3 degradation magnitude reduction: Korea→Global +41~59% → Global→Korea +9~11% (1/4–1/5)

**Layer 4 — Operational Refinement (Mirror Sentinel + Differential Reactivity):**
- BDC 본질 역할 (Korea ↔ Global translator) 보존, 방향 반전 (Global signal → Korea translator)
- KPI 7 redefinition: Global trend MA → Korea monitoring leading indicator (operational scope explicit)
- Track A3 4-way outcome matrix (Large/Small/No gain + degradation 4th scenario added)
- Auto-classifier patch (signed delta + 4-way branch) self-detected and applied
- B1 nested seasonal split: FW −3.64% / SS −1.78% season-robust degradation
- Stage 8 Forecast tab "Forecast & Bridge" 우측 패널 reference visualization, NOT model input

핵심 의사결정:
- methodology.md §12 완비 (§12.1~§12.7, §12.3.5 Methodology Validation expansion + §12.6 Mechanism 3가설 + §12.7 Stage 8 handoff 5 sub-sections)
- exploratory_findings.md Data Points 19-24 + KPI 7 redefinition + KPI 12/13 추가
- **Mirror Sentinel + Differential Reactivity 채택** ((i) BDC role 보존 + (iii) mechanism 보강)
- Migration 011 applied 2026-05-03 (mart.korea_global_lag 12 rows sign-flipped + labels swapped)
- stage4_checkpoint.md Sign Correction Notice footnote applied (trace 보존)
- DP22 [DEPRECATED 2026-05-03] tag + DP24 successor cross-reference (본문 보존)
- Track A3 재설계 (Global → Korea direction, raw global_search lagged primary, leakage-free)
- Track B2 (Product-line sentiment) deferred to post-Stage 8

DB 변경:
- migration 011: `mart.korea_global_lag.lag_weeks` + `cc_best_lag_weeks` 부호 반전, `lag_direction` 라벨 swap (12 rows, NB 4 deseason × 1 + 다른 brand 8)
- 모든 NB deseason method 일관 "Global leads" direction

산출물 (Track C):
- `data/bridge/chain_diagram_data.json` — Stage 8 dashboard 직접 입력 (operational_use object 5 fields)
- `figures/bridge/chain_summary.png` — 1-slide 면접 시각화 (sign-corrected direction + monitoring vs predictive 분리 visual cue)
- `docs/stage7_bridge_report.md` — 1-page narrative summary (4-layer climax)

---

## 6. NB Korea Cross-cutting Insights — 본 프로젝트 핵심 narrative

### 누적 데이터 포인트 18개

**Stage 0~3 (약점 위주):**
1. 530 의존도 51% → 54.98% (단일 모델 집중 심화)
2. D2C slope -0.179 → -0.191/week (D2C 채널 약화)
3. 패딩 시즌 빠르나 모멘텀 정체
4. NB Korea over-index +34.94% search
5. 검색 over-index인데 sentiment +0.289 최저
6. neutral 45.6% (사용 후기 비중 낮음)
7. Shopping search 4.5% (앱 직진입)
8. 모든 한국 제품 FW-dominant (글로벌 SS와 비대칭)

**Stage 4 (강점 추가) [Sign Correction Applied 2026-05-03]:**
9. **NB Global trend가 Korea trend ~10w 선행** (DTW + CC 수렴, sign-corrected via DP24 — magnitude robust ±2w, direction inverted from Stage 4 original labeling)
10. **NB CSI→Search 단방향** — 거시 경기 후행 demand 구조

**Stage 5 (actionable insight):**
11. **Celebrity event stacking** — 셀럽+콜라보+이벤트 동시 집중이 검색 spike 핵심 메커니즘
12. **CSI 급락 ↔ multi-brand dip** + **이벤트가 macro override 가능** — Granger 평균 구조 vs anomaly 극단의 구분
13. **Air Max Day spillover** — Nike에겐 예측 가능, 경쟁사에겐 비예측 충격
14. **올림픽 연도 초과 수요** — 2024 봄 4주 전 브랜드 글로벌 spike. 올림픽 indicator 관측치 1회로 Stage 6 보류

**Stage 6 (정량적 확인 + 구조적 발견):**
15. **NB Global ARIMA(0,1,0)** — 자기회귀 정보 없음, 외부 요인(CSI + Korea 선행)의 함수
16. **CSI 탄력성 비대칭** — Korea 3.98 vs Global 2.01, Korea가 2배 민감 (SARIMAX-specific, Prophet에서는 trend가 흡수)
17. **Foundation model anti-scaling** — Chronos-base > small 역전, 174주에서 scaling law 불성립
18. **Prophet 메커니즘 3각 분석** — changepoint 우위(ablation) + CSI 흡수(trend가 CSI 정보 내재화) + Fourier K=10 Korea 과적합

**Stage 7 (Methodology Validation Stage):**
19. **5-Dimension Orthogonal Null × 11 Tests** — chain hypothesis 모두 reject (VARX 양방향 + monthly Granger 양방향 + trend mediation 양방향 + diff1 mediation 양방향 + lagged cointegration 양방향). 본 프로젝트 most-tested null hypothesis.
20. **Mediation Spurious Pre-emption** (Step 0 mitigation) — 단일 design choice (diff1 robustness specification)가 spurious regression risk + DP23 MSTL leakage risk 둘 다에 incidentally 안전장치로 작동
21. **Three-Dimensional Separation Robust [Sign Correction Applied]** — Shape similarity (DTW + CC) 존재 / Level equilibrium (cointegration) 부재 / Causal mediation 부재. 3-dim separation logic 자체는 sign correction에 robust
22. **DP22 Sentinel Framing [DEPRECATED 2026-05-03 — replaced by DP24]** — 본문 보존 + DP24 successor cross-reference (trace preservation pattern)
23. **MSTL Forward-Looking Leakage** (Self-Diagnostic) — 3-step detection trail: Pattern recognition (lag grid CV monotonic increasing) → Algorithm inspection (two-sided STL filter) → Quantification (recompute ratio 0.2689/0.2612 above 0.15 threshold)
24. **Stage 4 Sign Convention Inversion** (DP22 Successor) — Mathematical inversion confirmed via 3 quantitative signatures stack (synthetic probe / mediation re-run / Track A3 degradation). Self-diagnostic detection without external review = analytical governance discipline. Stage 7 = methodology validation stage 정의

### 종합 진단 narrative (Stage 1~7 누적)

**약점:** 530 단일 의존, D2C 약화, 검색-감성/검색-구매 비대칭, 거시 경기 의존 (Korea CSI 탄력성 2배, SARIMAX 기준), Stage 2 z-score 91.3% false positive (→ 자기 교정 증거), **Global signal forecast input integration 불가** (Stage 7 Track A3) — 모든 layer에서 single dependency 작동
**강점:** Global → Korea ~10w 선행 (sign-corrected, monitoring indicator), event stacking 전략 실증, 경쟁사 이벤트 spillover 활용 가능, Global 자기 모멘텀 부재 → Korea-Global lead가 dashboard reference 가치 극대화, Prophet changepoint detection 활용 + analytical governance discipline (DP20/23/24 self-diagnostic chain)
**Stage 7 narrative climax:** "Stage 7's value lies less in the hypothesis test result (chain rejected) than in the verification process. Three critical findings were surfaced without external reviewer — DP20 (mediation spurious pre-emption) → DP23 (MSTL forward-looking leakage) → DP24 (Stage 4 sign convention inversion). Analytical discipline transferable to enterprise contexts."

이 4-layer narrative (5-dim null + self-diagnostic chain + 3-stack quantitative signatures + operational refinement)가 본 프로젝트에서 가장 강한 면접 자료. BDC 본질 역할(글로벌 본사 ↔ 한국 시장 통역사) — Mirror Sentinel + Differential Reactivity framing으로 보존, 신호 방향만 반전 (Global signal → Korea translator).

### KPI 13종 (Stage 0 → Stage 7 누적 진화)

1. 530 분기별 의존도 (60% 초과 알림)
2. D2C 검색 점유율 주간 추세 (4주 연속 하락 알림)
3. 카테고리별 NB 점유 갭 (패딩처럼 NB 점유 미달 자동 탐지)
4. NB 제품 감성 비율 (positive/neutral/negative 분기별)
5. 검색-감성 갭 (search over-index vs sentiment ranking 괴리)
6. CSI 3개월 이동평균 (하락 시 NB 검색 방어 캠페인 트리거)
7. **NB Global 검색 trend 4주 이동평균 — Korea 수요 monitoring leading indicator** (sign-corrected DP24 + operational scope explicit: 사용 O dashboard 시각화 / 사용 X forecast 모델 input — Track A3 degradation evidence)
8. Event Stacking Density — 같은 주 겹치는 이벤트 수 vs 검색 spike 크기
9. Anomaly Detection Method Agreement — 3-way agreement 건수 월별 추적
10. CSI 탄력성 모니터링 — CSI 변동 × Korea 탄력성(3.98) 기반 검색 영향 추정
11. 26주 검색 예측 Prophet Baseline — CSI + Fourier K=2 + changepoint 기반 분기 예측 월 1회 업데이트
12. **5-Dimension Orthogonal Null Verification Pattern (methodology asset)** — VARX × monthly Granger × mediation × cointegration 11-test framework default protocol (Stage 7 신규)
13. **Methodology Validation Stage Pattern (governance asset)** — DP20 (사전 차단) → DP23 (self-diagnostic) → DP24 (검증 부산물) 3단 cascade default 패턴 (Stage 7 신규, 면접 narrative climax)

이 KPI 13종이 Stage 8 Streamlit + Power BI 대시보드의 핵심 지표 (KPI 1-11) + Methodology Documentation tab의 governance assets (KPI 12-13).

---

## 7. 남은 stage 진행 계획

### Stage 8 — Streamlit Dashboard (COMPLETED 2026-05-03)

**Stage 8 실행 결과:**
- **Live URL:** https://sportswear-brand-monitor-newbalance.streamlit.app/
- **6-Tab Dashboard:** Weekly KPI / Season / Channel / Anomaly / Forecast & Bridge / Methodology Doc
- **13 KPI 전수 매핑:** KPI 1-11 operational (Tab 1-5), KPI 12-13 governance (Methodology Doc tab)
- **Dual Data Source:** PostgreSQL (local dev) / CSV fallback (Streamlit Cloud, 비용 0)
- **CSV Export:** `dashboard/export_csv.py` — 7 mart queries + 4 forecast CSVs = 5,253+ rows
- **Stage 7 Narrative Surfacing 5 위치:** Sidebar About / Tab 5 chain diagram / Tab 5 caption / Tab 5 expander / Methodology Doc tab
- **Sub-stages:** 8.0 (skeleton) → 8.1 (Weekly KPI) → 8.2 (Season) → 8.3 (Channel) → 8.4 (Anomaly) → 8.5 (Forecast & Bridge) → 8.6 (CSI connect) → 8.7 (CSV export) → 8.8 (deploy) → 8.9 (Methodology visual)
- **Bugs Fixed:** 10건 (ModuleNotFoundError x2, DB password, anomaly_log schema, forecast CSV schema, CSI source, deprecation, CSV date parsing, product chart y-axis, psycopg2 conditional import)
- DB connection reuse: `database.connection.get_conn()` context manager
- Migration 011 sign-corrected table direct query confirmed
- chain_diagram_data.json `operational_use` branching logic implemented


- **Streamlit 5탭** (Weekly KPI / Season / Channel / Anomaly / **Forecast & Bridge**)
  - Forecast & Bridge tab: Korea Prophet forecast (좌측 패널, CSI exogenous only) + chain_diagram visualization (우측 패널, sign-corrected, operational_use metadata 활용)
  - Bridge 6번째 탭 신설 X — Forecast tab 확장으로 통합
- **Power BI Service 3탭** (Publish to web)
  - Weekly KPI / Competitive / HQ Bridge (영문 UI)
  - HQ Bridge tab summary card: Global trend direction + "Korea demand directional reference — not predictive input" 캡션
- **KPI 7 dual surface** — monitoring vs predictive 분리 tooltip 양 dashboard 일관 적용
- **Migration 011 sign-corrected table 직접 query** — `mart.korea_global_lag` no further translation logic
- 라이브 URL 면접 자료

---

## 8. 종합 어드바이저로서 유의해야 할 패턴

### 8.1 의사결정 추적 패턴

매 stage마다 결정사항이 누적된다. 단계별 어드바이저는 stage 내부 결정만 보지만, 종합 어드바이저는 stage 간 영향을 본다:

- **Stage 0 의류 분석 보류** → Stage 3에서 padding 카테고리 분리로 부분 처리
- **Stage 1 --clear 패턴 결정** → Stage 2에서 시계열 변환 한계 발견 → methodology §1 narrative
- **Stage 2 Granger 3→2 축소** → Stage 4에서 결과적으로 가설 자체가 부정 → 4-pattern으로 전환
- **Stage 3 MSTL 발견** → Stage 4 DTW 3-way 비교로 시즌 artifact 검증 → Stage 6 SARIMAX 설계
- **Stage 5 M+IF 독립성 한계 인식** → Tier 구조로 해결 → Stage 8 대시보드 anomaly 탭에서 Tier 표시 필요
- **Stage 5 올림픽 indicator 보류** → Stage 6 SARIMAX exogenous = CSI만 사용 (확정)
- **Stage 5 events_calendar anomaly-driven caveat** → Recall 대신 EDR 사용 → Stage 8 보고서에 caveat 반영
- **Stage 6 Prophet 전승** → Stage 8 Forecast 탭 모델: Prophet for both series (단일 프레임워크)
- **Stage 6 Prophet ablation** → changepoint detection이 핵심, Fourier K=10은 Korea에서 과적합
- **Stage 6 Global ARIMA(0,1,0) 발견** → Stage 7에서 Korea trend를 Global exogenous로 추가 실험 근거 (그러나 DP23 leakage + DP24 sign inversion으로 design invalidated)
- **Stage 6 CSI 탄력성 비대칭 (2x, SARIMAX-specific)** → Stage 7 first hop 정량화 완료 (chain 검증으로 5-dim null 확정)
- **Stage 7 5-dim orthogonal null 확정** → Mirror Sentinel + Differential Reactivity framing 채택 (chain hypothesis reject, BDC role 보존)
- **Stage 7 DP24 sign convention inversion** → Stage 4 cascade (DP9/DP21/DP22→DP24) + KPI 7 redefinition + migration 011 retrofit + stage4_checkpoint footnote (trace 보존)
- **Stage 7 Track A3 degradation outcome** → 4-way outcome matrix officialization + auto-classifier signed delta patch + Stage 8 Forecast tab 우측 패널 reference visualization (NOT model input)
- **Stage 7 Mirror Sentinel + Differential Reactivity 채택** → Stage 8 dashboard에 monitoring vs predictive 분리 tooltip 일관 적용
- **Stage 7 KPI 12/13 신규 추가** (methodology asset + governance asset) → Stage 8 Methodology Documentation tab에 surfacing


이런 stage 간 영향이 종합 어드바이저의 핵심 책임.

### 8.2 면접 narrative 균형 유지

본 프로젝트 narrative는 약점→강점→양면성→methodology validation 구조로 진화:
- Stage 0~3: 약점 위주 (530, D2C, sentiment)
- Stage 4: 첫 강점 추가 (10주 선행 — 후일 sign inversion 정정)
- Stage 5: actionable insight 추가 (event stacking, CSI override, spillover)
- Stage 6: 정량적 확인 (CSI 2x 탄력성 SARIMAX-specific, Global 자기 모멘텀 부재, Prophet 전승 + changepoint ablation)
- **Stage 7: methodology validation stage** ← climax
  - 5-dim orthogonal null로 chain hypothesis reject
  - 3가지 self-diagnostic finding (DP20+23+24 chain)
  - sentinel framing pivot으로 BDC 본질 역할 보존, 방향만 반전
  - Stage 4 magnitude robust 확인 → 분석 신뢰성 evidence
  - Stage 8 dashboard 진입 직전에 발견 → timing의 self-skepticism narrative credibility

**약점만 나열되면 면접 자료로 약함.** 종합 어드바이저는 stage마다 강점/약점 균형 점검 필요.

### 8.3 v3 계획서 동기화 의무

stage 결과가 나올 때마다 v3 계획서를 최신 상태로 유지해야 다음 stage 어드바이저/진행 채팅이 정확한 컨텍스트로 시작. v3가 outdated되면 새 Claude가 잘못된 가설을 전제로 작업 설계할 위험.

### 8.4 채팅 토큰 관리

종합 어드바이저 채팅도 토큰 쌓이면 인수인계 필요. 인수인계 시 이 문서 형태로 핵심만 정리해서 새 채팅에 전달. 단계별 채팅들은 stage 종료 시 닫는 게 기본.

---

## 9. 새 종합 어드바이저 채팅 시작 시 메시지 템플릿

```
이 채팅은 NB Korea BDC 포트폴리오 프로젝트의 종합 어드바이저 역할을 이어받는다.
이전 종합 어드바이저 채팅이 토큰 한계로 닫혀 새로 시작.

프로젝트 지식의 다음 문서를 읽고 컨텍스트 동기화:
1. v3 계획서 (전체 설계, §4.5/§4.7/§4.8/§12 Stage 4/6/7 결과 반영)
2. methodology.md (§1~12, 분석 결정 narrative + Stage 7 Methodology Validation)
3. exploratory_findings.md (Data Point 1~24, KPI 13종)
4. stage1~7 checkpoint + docs/stage7_bridge_report.md (Stage 7 1-page narrative)
5. comprehensive_advisor_handoff.md (이 인수인계 문서)

현재 Stage 7 COMPLETED, Stage 8 진입 직전.

종합 어드바이저 책임:
- Stage 진입 메시지 작성 (단계별 어드바이저 + 단계별 진행 채팅용)
- Stage 종료 시 checkpoint 검토 + 다음 stage 영향 정리
- stage 간 정합성 유지 + narrative 통합 + v3 계획서 동기화
- 단계별 채팅에서 가져오는 큰 결정 사항 상의

본 프로젝트 핵심 narrative (Stage 7 close 이후):
"Stage 7's value lies less in the hypothesis test result (chain rejected) than
in the verification process. Three critical findings were surfaced without
external reviewer (DP20 mediation pre-emption → DP23 MSTL leakage → DP24 sign
convention inversion). Mirror Sentinel + Differential Reactivity framing:
Global signal precedes Korea by ~10w as monitoring indicator (sign-corrected),
NOT predictive feature. BDC role preserved (Korea ↔ Global translator),
direction reversed."

이 4-layer narrative (5-dim null + self-diagnostic chain + 3-stack quantitative
signatures + operational refinement) 보존 + 강화하는 방향으로 Stage 8 진행 가이드.
```

---

## 10. 즉시 다음 작업 — Stage 8 진입

Stage 7 COMPLETED 확인됨. Stage 8 진입 준비 완료.

Stage 8 어드바이저 + Stage 8 진행 채팅용 시작 메시지 작성 필요.

**Stage 8 핵심 작업:**
- Streamlit 5탭 (Weekly KPI / Season / Channel / Anomaly / **Forecast & Bridge**)
- Power BI Service 3탭 (Weekly KPI / Competitive / HQ Bridge — 영문 UI)
- Stage 9: 1-page Weekly Performance Report PDF 자동 생성
- 라이브 URL 면접 자료 (Streamlit Cloud + Power BI Publish to web)

**Stage 8 사전 결정 사항 (Stage 7 cascade 반영):**
- **Forecast & Bridge tab 통합 구조** — Korea Prophet forecast (좌측, CSI exogenous only) + chain_diagram visualization (우측, sign-corrected operational_use metadata)
- **KPI 7 dual surface** — Streamlit Forecast 탭 Global trend MA overlay + Power BI HQ Bridge tab summary card. monitoring vs predictive 분리 tooltip 양 dashboard 일관 적용
- **Methodology Documentation tab** — KPI 12 (5-Dim Verification Pattern) + KPI 13 (Methodology Validation Stage Pattern) governance asset surfacing
- **Migration 011 sign-corrected table 직접 query** — `mart.korea_global_lag` no further translation logic
- **chain_diagram_data.json 활용** — Streamlit `if edge.operational_use.predictive_feature: ...` 분기 logic 사전 commit
- **Stage 7 4-layer narrative** dashboard tooltip / About section에 surfacing
- **stage7_bridge_report.md** 면접 자료로 Live Demo URL과 함께 README에 link

**Stage 8 위험 관리:**
- Power BI Service 무료 티어 기능 제한 → 핵심 3탭은 KPI 카드/바/라인/도넛 단순 구성, 복잡한 분석은 Streamlit
- Publish to web 공개 데이터 적합성 → 본 프로젝트 전부 공개 데이터 (검색량, 공시 매출 등) 안전
- KPI 12/13 governance asset의 dashboard 표현 → Methodology Documentation tab으로 분리 (operational metrics에 섞지 않음)

---

*인수인계 문서 Stage 7 close 갱신 완료 (2026-05-03). 새 종합 어드바이저 채팅 시작 시 이 문서를 프로젝트 지식에 업로드하고 위 §9 메시지로 시작.*
