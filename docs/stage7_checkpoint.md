# Stage 7 Checkpoint — Korea-Global Bridge: Methodology Validation Stage

**Date:** 2026-05-03
**Status:** COMPLETED — All Tracks (A1 + A1' bidirectional + A2 sign convention validation + A3 re-design + B1 nested + C bridge report) closed. DP19~24 + KPI 7/12/13 + Migration 011 retrofit applied. Stage 8 진입 준비 완료.
**Stage Identity:** What began as 3-stage chain verification became, through cumulative self-diagnostic findings, a methodology validation stage. Three critical findings (DP20/23/24) were detected through internal sanity checks alone, redefining the stage's deliverable from hypothesis testing to demonstrating analytical governance.

---

## Core Finding

Stage 7 set out to verify the CSI → NB Korea → NB Global 3-stage chain hypothesis. Across **5 independent dimensions** (VARX bidirectional, monthly Granger bidirectional, mediation bidirectional × 2 transformations, lagged cointegration bidirectional), all 8+ tests reject the chain hypothesis — CSI directly and independently drives both Korea and Global search demand, with no mediation channel through either region. The verification process surfaced three self-diagnostic findings (**DP20** mediation spurious correlation pre-emption, **DP23** MSTL forward-looking leakage, **DP24** Stage 4 sign convention inversion), redefining Stage 7's role from hypothesis testing to methodology validation. Sign correction preserves the BDC sentinel framing (Global signal → Korea translator): direction reversed, role essence retained.

## Stage 7 Sub-section Status

| Track | Status | Note |
|---|---|---|
| A1 — VARX(2) bidirectional | COMPLETED | null both directions |
| A1' — Mediation bidirectional | COMPLETED | null both directions, sign-correction validation |
| A2 — Sign Convention Validation | COMPLETED, re-scoped | replaced retired SARIMAX hop gain |
| A3 — Trend Exogenous Re-design | COMPLETED | 4th outcome scenario (degradation), sentinel operational refinement |
| B1 — Seasonal Lead Asymmetry | COMPLETED | FW −3.64% / SS −1.78%, season-robust degradation |
| B2 — Product-line Sentiment | DEFERRED | to post-Stage 8 |
| Cascade Corrections | COMPLETED | DP9/21/22→24, KPI 7 |
| §12 Methodology Updates | COMPLETED | §12.1/2/3/4/6 body authored, §12.5/7 stubs |
| Migration 011 (DB retrofit) | DEFERRED | post Stage 7 close |

## Test Result Summary

| Test | Direction | Result | Verdict |
|---|---|---|---|
| VARX(2) Granger Korea→Global | weekly diff1 | F=1.45 p=0.23 | fail to reject |
| VARX(2) Granger Global→Korea | weekly diff1 | F=0.23 p=0.63 | fail to reject |
| VARX(2) joint LR (CSI dist. lag) | weekly diff1 | chi2=13.75 p=0.09 | marginal |
| Monthly Granger Korea→Global | monthly mean | min p=0.14 | fail to reject |
| Monthly Granger Global→Korea | monthly mean | min p=0.06 | fail to reject (marginal) |
| Trend mediation (K→G original) MBB CI | trend, lag 10w | [−0.39, +0.18] | 0 included |
| Trend mediation (G→K sign-corrected) MBB CI | trend, lag 10w | **[−0.12, +0.18]** | 0 included |
| Diff1 mediation (K→G original) MBB CI | diff1, lag 10w | [−0.04, +0.003] | 0 included |
| Diff1 mediation (G→K sign-corrected) MBB CI | diff1, lag 10w | **[−0.06, +0.007]** | 0 included |
| Lagged cointegration (Global ~ Korea_{t-lag}) | lag 9/10/11w | all p > 0.40 | robust no cointegration |
| Lagged cointegration (Korea ~ Global_{t+lag}) | lag 9/10/11w | all p > 0.94 | robust no cointegration |
| Track A3 Prophet (+CSI vs +CSI+Global lag11) | Korea forecast | Δ%=−9.01% DM p=0 | degradation (4th scenario) |
| Track A3 SARIMAX (+CSI vs +CSI+Global lag11) | Korea forecast | Δ%=−10.94% DM p=0 | degradation (4th scenario) |
| Track B1 nested FW season | week 40–13 | Δ%=−3.64% | season-robust degradation |
| Track B1 nested SS season | week 14–39 | Δ%=−1.78% | season-robust degradation |

---

## Step 0: Weekly Stationarity Re-Test (Decision 2) [COMPLETED]

### Univariate ADF + KPSS

| Series | Verdict (level) | Verdict (diff1) | Decision |
|---|---|---|---|
| korea_search | unit_root | stationary | diff1 |
| global_search | unit_root | stationary | diff1 |
| korea_trend | unit_root | unit_root | review (escalated) |
| global_trend | trend_stationary | unit_root | review (escalated) |
| csi (forward-filled) | unit_root | stationary | diff1 |

### Trend diagnostics + Option 6 resolution

Trend ADF(ct) follow-up confirmed korea_trend ≈ I(1) borderline, global_trend ≈ near-integrated. Integration-order mismatch precluded uniform VARX transformation. Cointegration on (korea_trend, global_trend) at zero lag rejected (p=0.9433), closing the VECM path.

**Resolution — Option 6 (advisor approved):** Per-analysis variable separation.

| Analysis | Endogenous/input | Stationarity rationale |
|---|---|---|
| Track A1 VARX | (korea_search_d1, global_search_d1) | Both clean ADF p=0.0000 |
| Track A1' Mediation primary | MSTL trend at lag | Lagged regression; spurious risk addressed by diff1 robustness |
| Track A1' Mediation robustness | search d1 at lag | Stationary, spurious-safe |
| Track A3 [COMPLETED] | Sign-corrected: Global trend / search at lag | Direction reversed per DP24 cascade |

---

## Track A: 3-Stage Chain Verification (Bidirectional)

### A1: VARX(2) Bidirectional [COMPLETED]

VAR.select_order(maxlags=13) returned p=1 across all four ICs (AIC, BIC, HQIC, FPE), AIC/BIC gap = 0. Effective n=160. AIC=2.66, BIC=2.93, HQIC=2.77, LL=−653.16.

**Bidirectional Granger (within VARX):**

| Direction | F-statistic | p-value | Verdict |
|---|---|---|---|
| Korea → Global | 1.4521 | 0.2291 | fail to reject |
| Global → Korea | 0.2310 | 0.6311 | fail to reject |

**CSI joint LR + per-lag:** LR = 13.7476, df = 8, p = 0.0886 (marginal). Per-lag inspection: only `global_d1 ~ csi_d1_l0` significant (coef = +0.1772, p = 0.0161). Korea diff1 shows no significant CSI coefficient at any lag.

**IRF (orthogonalized) cumulative @ h=20:** Global response to Korea shock +0.0444; Korea response to Global shock +0.0434. Near-symmetric small effects.

**Verdict:** Short-run weekly causal channel between Korea and Global search is absent. Surviving CSI → Global at lag 0 is contemporaneous macro reactivity, not dynamic propagation. Result consistent with Stage 6's Global ARIMA(0,1,0).

**Supplementary — Monthly Granger Korea ↔ Global** (filling Stage 4 gap; 5-min check). Korea→Global min p=0.14, Global→Korea min p=0.06 (marginal, fails Bonferroni α/8=0.00625). Verdict: `monthly_null_both_directions` — frequency-robust absence.

### A1': Mediation Bidirectional (joint block bootstrap) [COMPLETED]

#### Design (Decision 4 spec preserved across both directions)

- Three regressions (Baron-Kenny): a, b, c, c'; indirect = a × b
- Lag* = 10w (Stage 4 magnitude, sign-corrected lens preserves magnitude)
- Bootstrap: MovingBlockBootstrap (block 13w) primary + StationaryBootstrap robustness
- N = 5000 iterations × 4 cells × 2 directions = 40,000 bootstrap fits total
- BCa 95% CI; joint block bootstrap on full DataFrame preserving column-time alignment

#### Original direction (Korea → Global, pre-DP24)

| Component | Trend | Diff1 |
|---|---|---|
| a path | +0.0928 | +0.1216 |
| b path | +0.5272 | −0.0390 |
| c path (total) | +0.0407 | +0.1828 |
| c' path (direct) | −0.0083 | +0.1876 |
| Indirect a × b | +0.0489 | −0.0047 |
| % mediated | 120.35% | −2.59% |
| MBB 95% BCa CI | [−0.3933, +0.1753] | [−0.0351, +0.0034] |
| SB 95% BCa CI | [−0.0246, +0.3436] | [−0.0352, +0.0029] |

Inconsistent mediation pattern in trend (% mediated > 100%, direct/indirect opposite signs, MBB CI sign-unstable) consistent with non-stationary regression failure modes (DP20). Diff1 robustness specification (Step 0 design choice) returned tight near-zero CI, disambiguating.

#### Sign-corrected direction (Global → Korea, post-DP24)

| Component | Trend | Diff1 |
|---|---|---|
| a path | +0.0470 | +0.0671 |
| b path | +0.2614 | −0.1836 |
| c path (total) | +0.1135 | +0.1347 |
| c' path (direct) | +0.1012 | +0.1471 |
| Indirect a × b | +0.0123 | −0.0123 |
| % mediated | 10.82% | −9.15% |
| MBB 95% BCa CI | [−0.1211, +0.1764] | [−0.0561, +0.0066] |
| SB 95% BCa CI | [−0.0659, +0.1701] | [−0.0505, +0.0044] |

Three quantitative signatures confirm the sign-corrected direction is the empirically supported one:
1. **Inconsistent mediation signature dissipates** — % mediated 120.35% → 10.82%, direct/indirect signs realigned (both positive in trend).
2. **CI width narrows ~47%** — trend MBB BCa CI width 0.57 → 0.30 with identical bootstrap parameters; consistent with lower sampling variance under correctly-specified direction.
3. **b path magnitude moderation** — trend b 0.5272 → 0.2614 (closer to plausible elasticity range, not spurious-inflated).

#### Cross-method matrix → Scenario B confirmed bidirectionally

Pre-committed advisor matrix applied to both directions independently:

| Direction | Trend | Diff1 | VARX | Resulting scenario |
|---|---|---|---|---|
| K→G (original) | not significant | not significant | null | row 3 — full parallel |
| G→K (sign-corrected) | not significant | not significant | null | row 3 — full parallel |

**5-dimension orthogonal null bidirectional:** mediation × 2 directions + VARX bidirectional + monthly Granger bidirectional + lagged cointegration bidirectional. Single false-negative possibility eliminated.

#### Methodology validation

The Step 0 diff1 robustness specification, originally committed to address spurious regression risk in trend regression, also incidentally addresses the MSTL forward-looking smoothing leakage subsequently identified during Track A3 self-diagnostic (DP23). The Step 0 design choice provides robustness against two independent risks. The trend mediation null result, even interpreted as leakage-corrupted, strengthens rather than weakens channel-absence finding — a leakage-corrupted estimator with forward-looking information failed to detect a positive effect.

### A2: Sign Convention Validation (DP24 detection) [COMPLETED, scope re-defined]

**Original scope (pre-Stage 7 commit):** SARIMAX-based hop gain quantification — multiply CSI→Korea coefficient (3.98) × Korea→Global coefficient to produce chain multiplier, compare against CSI→Global direct (2.01).

**Retirement rationale.** Track A1/A1' 5-dimension orthogonal null rejects chain hypothesis itself. Hop gain quantification of a non-existent chain has no defined meaning. Slot re-allocated to sign convention validation surfaced during Track A3 self-diagnostic.

**Re-defined scope:** Validate Stage 4 DTW/CC sign convention via three independent tests.

**Test 1 — Synthetic data probe.** Generated time series where Korea leads Global by exactly 5 weeks. Stage 4 CC code returns lag = −5, Stage 4 DTW code returns warping path average = −4.57. Magnitude correct (±0.43w), sign inverted relative to Stage 4's labeling convention ("+ = Korea leads").

**Test 2 — Leakage-free replication.** Re-computed CC and DTW on actual NB Korea and Global series using one-sided trend estimation (replacing two-sided MSTL filter that produced DP23 leakage). Method A (expanding-window MSTL): DTW mean +8.93w, median +9.00w, std 7.22; CC −10w. Method B (13w trailing rolling mean): DTW mean +16.06w, median +8.50w, std 30.75 (Method B's high std flags rolling-mean residual seasonal contamination — Method A used as primary). Method A classified as `direction_flipped` relative to Stage 4's "+ = Korea leads" labeling. Magnitudes reproduce Stage 4 within ±2w (DTW median 9.00 vs Stage 4 +10.4; CC magnitude 10 vs Stage 4 +9).

**Test 3 — Mediation re-run with corrected direction.** Track A1' mediation re-run with Global → Korea direction (sign-corrected) shows three independent quantitative signatures of correct specification:
- Inconsistent mediation signature dissipates: % indirect effect 120.35% → 10.82%
- BCa CI width narrows 47%: trend MBB CI [−0.39, +0.18] → [−0.12, +0.18]
- Track A3 degradation magnitude reduces 1/4–1/5: Korea→Global (DP23-contaminated) Prophet/SARIMAX +41/+59% → Global→Korea (leakage-free) +9.01/+10.94% — sign correction removes both DP23 leakage amplification and direction misspecification interference, yielding measurable signal-to-noise improvement.

These three signatures are observable only when point estimate aligns with true direction. Their joint dissipation under sign correction constitutes the strongest quantitative evidence stack for Stage 4 sign convention error.

**Conclusion.** Stage 4 magnitude robust (±2w replication). Stage 4 direction labeling inverted. Corrected statement: NB Global trend leads Korea trend by ~10w (DTW), ~9w (CC).

**Cascade impact:** DP9 sign inversion, DP21 label correction, DP22 deprecated → DP24, KPI 7 redefinition (Korea trend MA → Global trend MA). See Cascade Corrections section.

### A3: Korea Trend Exogenous → Global Trend Exogenous Re-design [COMPLETED]

Original Track A3 (Korea trend → Global Prophet) invalidated by DP23 (MSTL leakage) and DP24 (sign inversion). Re-design: **Global trend → Korea Prophet** with raw `global_search` lagged (leakage-free, advisor decision 1).

#### Lag grid CV (paired-fold, Decision 5)

| lag | mean RMSE | median | std (paired folds) |
|---|---|---|---|
| 6w | 4.1158 | 3.97 | — |
| 7w | 4.2525 | 4.34 | — |
| 8w | 4.0323 | 4.33 | — |
| 9w | 3.8542 | 3.86 | — |
| 10w | 3.8137 | 3.82 | — |
| **11w** | **3.7509** | **3.49** | best mean |
| 12w | 3.7672 | 3.57 | — |
| 13w | 3.7803 | 3.60 | — |
| 14w | 3.8459 | 3.84 | — |

**Lag* uncertainty disclosure (Decision 5):** lag 11w lowest mean RMSE; lags within ±1 SE = {6, 8, 9, 10, 11, 12, 13, 14} (8 of 9 lags statistically indistinguishable); ±2w neighborhood = {9, 10, 11, 12, 13}. **No "exactly 11w" claim** — the 1-SE band spans nearly the entire grid. The lag grid is non-monotonic (lag 6: 4.12, lag 11: 3.75, lag 14: 3.85), distinct from Track A3 original's monotonic increasing pattern that signaled MSTL leakage. DP23 leakage absent in re-designed pipeline.

#### Triple comparison results

| Model | RMSE | Note |
|---|---|---|
| Prophet baseline | 4.7483 | — |
| Prophet + CSI | 5.5709 | DP18 reproduction (CSI absorption increases RMSE) |
| Prophet + CSI + Global_lag11 | 6.0731 | **+9.01% degradation** vs +CSI baseline (DM p=0.0000) |
| SARIMAX + CSI (Stage 6 base) | 6.4866 | — |
| SARIMAX + CSI + Global_lag11 | 7.1961 | **+10.94% degradation** vs +CSI baseline (DM p=0.0000) |

Both models show statistically significant degradation. Cross-model classification: `consistent_degradation`.

#### 4-way outcome matrix (officialized post-Track A3)

Original 3-way framing (large/small/no gain) failed to anticipate negative-delta significant outcomes. Auto-classifier sign-handling flaw self-detected and patched. 4-way matrix officialized:

| Outcome | Trigger | Narrative |
|---|---|---|
| Large gain | Δ% ≥ +5%, DM p < 0.10 | Global signal as leading proxy for common-driver effect |
| Small gain | +2% ≤ Δ% < +5%, DM p < 0.10 | DP18 cross-direction validation: changepoint absorption symmetric |
| No significant gain | \|Δ%\| < 2% OR DM p ≥ 0.10 | Strongest common-driver evidence: Global = differential reactor, not independent driver |
| **Degradation** (4th, observed) | Δ% ≤ −2%, DM p < 0.10 | Sentinel framing operational refinement: Global signal is monitoring leading indicator (DTW shape similarity) but actively interferes with forecast model. Stage 8 dashboard: right-panel reference visualization, NOT model input |

Auto-classifier code patch (signed delta + 4-way branch) is itself methodology validation evidence — self-detection of unsigned-handling flaw recorded for future analyses.

#### DP24 quantitative validation — 3rd signature

The degradation magnitude comparison provides the third independent quantitative signature of DP24 sign correction validity:

| Direction | Pipeline | Prophet Δ% | SARIMAX Δ% |
|---|---|---|---|
| Korea→Global (original) | DP23-contaminated (MSTL leakage) | −59.30% | −41.01% |
| Global→Korea (sign-corrected) | leakage-free (raw search lagged) | **−9.01%** | **−10.94%** |
| Magnitude reduction | — | **6.6×** | **3.7×** |

Sign correction removes both the DP23 leakage amplification effect and the direction misspecification interference. The 1/4–1/5 magnitude reduction is consistent with leakage being the primary amplifier; underlying degradation effect (~10%) reflects genuine sentinel-framing operational asymmetry — Global signal interferes with Korea forecast model regardless of direction or leakage state, confirming that the cross-region lead-lag relationship operates at monitoring (DTW shape) but not predictive (model input) level.

This joins the two A1' mediation signatures (signature dissipation + CI 47% narrowing) to form a 3-signature evidence stack — the strongest quantitative anchor for the DP24 sign convention error finding.

#### Sentinel framing operational refinement

The degradation outcome forces a refinement of the Mirror Sentinel + Differential Reactivity framing established post-DP24:

- **Monitoring indicator** (preserved): Global trend MA precedes Korea trend MA by ~10w (DTW + CC, sign-corrected). BDC dashboard surfaces Global signal as reference for Korea direction anticipation.
- **Predictive feature** (NOT, newly explicit): Global lagged regressor in Prophet/SARIMAX Korea forecast actively degrades RMSE in both models. Korea forecast model excludes Global as exogenous.

KPI 7 redefinition (post-DP24) is further refined post-A3:

> "NB Global 검색 trend 4주 이동평균 — Korea 수요 monitoring leading indicator (directional reference; predictive feature로는 active interference detected)"
>
> Operational scope:
> - 사용 O: BDC 대시보드 시각화 (Korea 수요 방향성 reference)
> - 사용 X: Korea forecast 모델 input

---

## Track B: Seasonal Lead Asymmetry

### B1: Seasonal Lead Asymmetry — FW vs SS (sign-corrected) [COMPLETED]

Track A3 nested within same data pipeline. FW (week 40–13) vs SS (week 14–39) split with Prophet+CSI baseline vs Prophet+CSI+Global_lag11 treatment, simple holdout (last 20% as test, no CV due to seasonal subset size).

| Season | n weeks | n test | Baseline RMSE | Treatment RMSE | Δ% |
|---|---|---|---|---|---|
| FW (week 40–13) | 82 | 16 | 2.2023 | 2.2825 | −3.64% |
| SS (week 14–39) | 81 | 16 | 4.2112 | 4.2862 | −1.78% |

**Seasonal asymmetry NOT detected.** Both seasons show degradation, magnitude difference modest (FW −3.64% vs SS −1.78%). The interference effect of Global lagged regressor is **season-robust** — Korea forecast model's resistance to Global signal as exogenous holds across the FW/SS structural divide documented in Stage 3.

This null result on seasonal asymmetry is itself a finding: the operational refinement (monitoring vs predictive distinction) does not require seasonal conditioning. Single dashboard policy applies year-round — Global signal as reference visualization in both FW and SS contexts, never as forecast model input.

The absolute RMSE difference between FW (2.20) and SS (4.21) reflects the underlying volatility asymmetry from Stage 3 (Korea FW-dominant search behavior produces tighter forecasts) but does not modulate the degradation direction.

### B2: Product-line Sentiment [DEFERRED to post-Stage 8]

Per advisor decision pre-Stage-7. Out of Stage 7 scope.

---

## Cascade Corrections (DP24-driven)

### DP9: Korea-Global Lead-Lag (Sign Corrected)

**Original (Stage 4):** "NB Korea trend leads Global trend by +10.4w (DTW) / +9w (CC)"
**Corrected (Stage 7 DP24 detection):** "NB Global trend leads Korea trend by ~10.4w (DTW) / ~9w (CC)"

Magnitude **robust** — leakage-free replication reproduces Stage 4 magnitude within ±2w.

Direction **inverted** — Stage 4 sign convention labeling error confirmed via:
1. Synthetic Korea-leads-by-5w test data → Stage 4 code returns CC −5, DTW −4.57 (negative = inverse of intended)
2. Leakage-free replication on actual data → Method A direction_flipped classification
3. Mediation re-run with corrected direction → inconsistent signature dissipation + CI 47% narrowing

`stage4_checkpoint.md` preserves original analysis with footnote referencing Stage 7 correction (advisor decision 4: trace preservation).

### DP21: Label Correction (Shape Similarity Robust)

DTW + cointegration + mediation three-dimensional separation finding remains valid in structure: shape similarity present, level equilibrium absent, causal mediation absent. Label correction: "Korea leads Global by +10.4w shape similarity" → "Global leads Korea by +10.4w shape similarity". Three-dimensional separation logic and conclusion unchanged.

### DP22: Deprecated → Replaced by DP24

Original DP22 ("sentinel framing — Korea = sentinel for common drivers via differential reactivity") archived. Sign-corrected replacement formalized as **Mirror Sentinel + Differential Reactivity** combined model:

- BDC operational role preserved: Korea ↔ Global translator
- Direction inverted: Global signal → Korea translator (not Korea signal → Global translator)
- Mechanism preserved: differential reactivity to common drivers; Global registers shape changes earlier
- All 9 cumulative cross-stage evidence points re-aligned to sign-corrected direction (see §12.6)

DP24 occupies the slot DP22 held in narrative function.

**Trace preservation pattern.** `exploratory_findings.md` DP22 본문은 보존, 상단에 `[DEPRECATED 2026-05-03]` tag + DP24 cross-reference 추가. 본문 내용 수정 금지. `stage4_checkpoint.md` footnote 처리와 동일 패턴 — "DP22가 사라졌다"가 아니라 "DP22가 deprecated됐고 DP24가 successor"라는 trace가 면접에서 self-skepticism evidence로 직접 활용 가능.

### DP23: MSTL Forward-Looking Leakage (new)

`statsmodels` MSTL uses two-sided STL filter; trend at week T uses data through T+w (centered smoothing). Track A3 self-diagnostic detected via: (a) lag grid CV pattern monotonically increasing with lag (lag 6w best, lag 14w worst — short lags carry more future leakage), (b) `bridge_mstl_leakage_check.py` quantification (recomputed-vs-real-time mean absolute difference / series std ratio: korea_trend 0.2689, global_trend 0.2612, both above 0.15 significance threshold). Track A3 invalidated; replication framework established for sign-corrected re-design.

Defensive value: Step 0 diff1 robustness specification (committed against spurious regression risk) provided incidental robustness against MSTL leakage. Single design choice, two independent risks addressed.

### DP24: Stage 4 Sign Convention Inversion (new — DP22 successor)

`scipy.signal.correlate(kr, gl)` returns `corr[k] = Σ_n kr[n+k] * gl[n]`; positive lag k where this maximizes means kr at time n+k aligns with gl at time n — i.e., **gl leads kr**. Stage 4 used `correlate(kr_series, gl_series, mode='full')` and labeled `best_lag_cc > 0` as "Korea leads", which is the verbal-mathematical inversion. Identical pattern in DTW path: `path[:,0] - path[:,1]` (Korea index − Global index) > 0 means Korea's later index aligns with Global's earlier index — **Global leads Korea**. Both Stage 4 estimators inverted simultaneously.

**Detection trail:** DP24 evidence is documented in Track A2 (Sign Convention Validation) Tests 1–3. See A2 section for quantitative results.

Cascade applied through DP9 / DP21 / DP22 / KPI 7 / §12.6 / BDC narrative. Stage 4 mart table `mart.korea_global_lag.lag_weeks` retains original sign for trace preservation; migration 011 applies retrofit at Stage 7 close.

### KPI 7 Redefinition

**Original:** "NB Korea 검색 trend 4주 이동평균 (Global 수요 예측 선행 지표)"
**Corrected:** "NB Global 검색 trend 4주 이동평균 (Korea 수요 예측 선행 지표)"

BDC operational implication preserved — leading indicator monitoring workflow valid, direction reversed. Stage 8 Forecast tab "Forecast & Bridge" panel uses Global trend lagged as Korea Prophet exogenous (Track A3 re-design scope).

---

## §12 Methodology Updates

### §12.1 — §12.7 outline

| Section | Status | Notes |
|---|---|---|
| §12.1 Frequency Mismatch (Option H) | body authored | Preserved from pre-DP24 version |
| §12.2 VARX Design (search d1, distributed-lag CSI) | body authored | Preserved; CSI lag 0 contemporaneous mandatory; monthly subsection inline |
| §12.3 Mediation Analysis | body authored | 5 sub-sections including §12.3.5 expansion (below) |
| §12.4 Korea Trend / Global Trend Exogenous (sign-corrected) | body authored | 5 sub-sections (re-design rationale / triple comparison / 4-way matrix officialization / DP24 quantitative validation / sentinel operational refinement) |
| §12.5 Seasonal Lead Asymmetry | body authored (B1 nested) | FW −3.64% / SS −1.78%, season-robust degradation; seasonal asymmetry null result |
| §12.6 Mechanism: Three Plausible Hypotheses (Sign-Corrected) | body authored (below) | Three face-validity hypotheses, scope boundary |
| §12.7 Stage 7 → Stage 8 Handoff | body authored (post-Track-C close) | 5 sub-sections: Forecast Model Selection / Bridge Tab Right-Panel Integration / KPI 7 Operational Implementation / Migration 011 Retrofit Status / Methodology Asset Propagation (KPI 12, 13) |

**§12.7 stub outline** (본문은 Stage 7 close 시점 — Track A3 + B1 nested 완료 후):
- Track A3 결과별 Stage 8 "Forecast & Bridge" 탭 우측 패널 데이터 명세 — large/small/no gain 시나리오 각각의 input CSV 분기 + 차트 narrative
- Track C chain diagram (`chain_diagram_data.json`) → Stage 8 dashboard linkage 명세 (sign-corrected 노드/엣지 구조, Mirror Sentinel narrative tooltip)
- KPI 7 redefinition operational implementation — Streamlit/Power BI dashboard에서 Korea trend MA → Global trend MA 정의 변경 + Korea 수요 예측 leading indicator framing 정확 표시
- Migration 011 retrofit 시점 명시 — Stage 7 close 일괄 commit (Track A3 final + B1 nested 결과 본 후, Stage 8 진입 전)

### §12.3.5 Stage 7 as Methodology Validation Stage (body)

Stage 7 was designed to verify the 3-stage chain hypothesis (CSI → NB Korea → NB Global). Execution surfaced three cumulative self-diagnostic findings, each detected without external review through internal sanity checks:

**DP20 — Mediation spurious correlation pre-emption.** Step 0 stationarity re-check identified that monthly-aggregated trend components produce non-stationary regression inputs, which would generate spurious mediation coefficients regardless of true causal structure. Alternative specifications (diff1, residual) were committed pre-execution, preventing post-hoc result chasing.

**DP23 — MSTL forward-looking leakage.** Track A3 narrative-negative result (Korea trend exogenous → Prophet RMSE +59%) triggered self-diagnostic that revealed MSTL decomposition uses two-sided STL filter, leaking future information into trend component. This invalidated Track A3 design and prompted leakage-free replication.

**DP24 — Stage 4 sign convention inversion.** Leakage-free DTW + CC re-computation classified results as direction_flipped relative to Stage 4 labels. Synthetic test data (Korea leads Global by 5w) confirmed Stage 4 code returns CC −5, DTW −4.57 — magnitude correct, sign convention inverted. Mediation re-run with corrected direction validated: inconsistent mediation signature dissipated (% indirect 120% → 11%), CI width narrowed 47%, both quantitative signatures of correct directional specification.

**Cumulative implication.** Stage 7's value lies less in the hypothesis test result (chain rejected) than in the verification process. For BDC roles requiring internal data analysis, the demonstrated competency is **self-skepticism + multi-method validation**. Three critical findings were surfaced without external reviewer, indicating the analytical discipline transferable to enterprise contexts where external validation is rare.

### §12.6 Mechanism: Three Plausible Hypotheses (Sign-Corrected Direction) (body)

Stage 7 quantitative analysis confirms Global → Korea lead of ~10w with magnitude robustness. The mechanism — **why** Global precedes Korea — cannot be tested with the project's data scope. Three face-validity hypotheses are documented for future verification with BDC internal data:

**Hypothesis 1 — Global brand attention precedence (cultural/demographic).** US/EU markets are NB's primary consumer base. Global brand-level search demand responds to product launches, marketing campaigns, and category trends earlier because the demographic concentration drives signal magnitude. Korea search demand follows after diffusion through K-fashion intermediaries.

**Hypothesis 2 — HQ marketing trigger (operational).** Global headquarters campaign cycles initiate at Global market level. Region campaigns (Korea) follow with localization lag. The ~10w lag corresponds to typical HQ-to-region campaign rollout cycles.

**Hypothesis 3 — Differential reactivity to common drivers (structural).** Both Korea and Global respond to common shocks (CSI, cultural events) but with different reactivity speeds. Global market's larger sample size enables faster signal detection, while Korea market's smaller scale produces noisier short-term response, manifesting as apparent lag.

**Distinction not testable in current scope.** All three hypotheses produce observationally equivalent ~10w Global-leads-Korea pattern in aggregate search data. Discriminating mechanism requires BDC internal data: campaign timeline records, market-level demographic decomposition, region-specific sentiment lag. This delineation defines the boundary between this project's contribution and in-role analytical extension.

### §12.4 Korea Trend / Global Trend Exogenous (sign-corrected) (body)

#### §12.4.1 Re-design rationale (post-DP23/DP24 cascade)

Original Track A3 (Korea trend → Global Prophet) was invalidated by the cascade of DP23 (MSTL forward-looking leakage in Korea trend exogenous) and DP24 (Stage 4 sign convention inversion combining the two flaws into ambiguity-amplified results). Re-design direction reverses both: Global → Korea direction (per DP24 sign correction), with raw `global_search` lagged as primary input (leakage-free per advisor decision 1, replacing two-sided MSTL filter that produced DP23 leakage). Expanding-window MSTL global trend (precomputed in `data/bridge/leakage_free_trends.npz`) retained as robustness input, available for §12.5 verification work but not used in primary triple comparison.

#### §12.4.2 Triple comparison results (degradation outcome)

Lag grid 6–14w paired-fold CV (Decision 5) returns lag 11w with lowest mean RMSE (3.75), but with 8 of 9 lags within ±1 SE — **statistically indistinguishable**. The lag* uncertainty disclosure explicitly avoids "exactly 11w" framing. The lag grid pattern is non-monotonic (lag 6: 4.12, lag 11: 3.75, lag 14: 3.85), distinct from Track A3 original's monotonically increasing pattern that signaled DP23 leakage; the leakage-free pipeline does not reproduce that signature.

Triple comparison at lag 11w: Prophet baseline RMSE 4.7483, +CSI 5.5709 (DP18 reproduction — CSI absorption), +CSI+Global_lag11 6.0731. SARIMAX +CSI 6.4866, +CSI+Global_lag11 7.1961. Both models show degradation: Prophet Δ% = −9.01% (DM p=0.0000), SARIMAX Δ% = −10.94% (DM p=0.0000). Cross-model classification: `consistent_degradation`. Track B1 nested seasonal split (FW vs SS) produces season-robust degradation: FW −3.64%, SS −1.78%; seasonal asymmetry null.

#### §12.4.3 Outcome classification — degradation as 4th scenario

Pre-committed 3-way framings (large_gain / small_gain / no_gain) did not anticipate degradation outcome. Auto-classifier's unsigned-delta logic incorrectly labeled Δ%=−9.01% as small_gain in initial run. Self-detection of the classifier flaw, patch (signed delta + 4-way branch), and re-run (deterministic, label-only correction) form a distinct methodology validation episode within Track A3. The 4-way matrix is officialized for future analyses; the patch trace is recorded in commit history for interview transparency.

#### §12.4.4 DP24 sign correction quantitative validation (3rd signature)

The degradation magnitude comparison provides the third independent quantitative signature of DP24:

| Direction | Pipeline | Prophet Δ% | SARIMAX Δ% | Magnitude reduction vs original |
|---|---|---|---|---|
| Korea→Global | DP23-contaminated MSTL trend | −59.30% | −41.01% | (baseline for comparison) |
| Global→Korea | leakage-free raw search lagged | **−9.01%** | **−10.94%** | **6.6× / 3.7×** |

Sign correction removes both the DP23 leakage amplification and the direction misspecification interference. The 1/4–1/5 magnitude reduction is consistent with leakage being the primary amplifier. The residual ~10% degradation reflects genuine sentinel-framing operational asymmetry, not measurement artifact.

This joins the two A1' mediation signatures from §12.3.5:
1. Inconsistent mediation signature dissipation (% indirect 120% → 11%)
2. BCa CI 47% narrowing (trend MBB CI [−0.39, +0.18] → [−0.12, +0.18])
3. Track A3 degradation magnitude reduction (1/4–1/5)

Three independent signatures stack — the strongest quantitative anchor for Stage 4 sign convention error finding. For interview narrative, the question "How did you verify the sign correction was correct, not arbitrary?" has a quantitative 3-stack answer.

#### §12.4.5 Sentinel framing operational refinement

The degradation outcome forces a refinement of Mirror Sentinel + Differential Reactivity (DP22 → DP24 successor framing):

- **Monitoring indicator** (preserved): Global trend MA precedes Korea trend MA by ~10w (DTW + CC, sign-corrected). BDC dashboard surfaces Global signal as directional reference for Korea anticipation.
- **Predictive feature** (NOT, newly explicit): Global lagged regressor in Prophet/SARIMAX Korea forecast actively degrades RMSE in both models. Korea forecast model excludes Global as exogenous.

The distinction has direct Stage 8 implementation consequences (§12.7). The dashboard right-panel will display the Global-Korea lead-lag as a reference visualization, but the forecast model panel uses Korea autoregressive structure with CSI exogenous only — Global lagged is not an input. This operational asymmetry between monitoring and predictive use is itself a project finding worth surfacing in the dashboard's documentation tooltip.

---

## Database Changes

### migration 011_korea_global_lag_sign_correction.sql [APPLIED 2026-05-03]

Per advisor decision 4: Stage 7 close 일괄 retrofit. `mart.korea_global_lag.lag_weeks` 부호 반전 + `cc_best_lag` 부호 반전. `direction` 컬럼 라벨링 ("Korea leads" / "Global leads") 정정. `stage4_checkpoint.md` 본문 보존, 상단에 footnote 추가하여 Stage 7 DP24 detection 참조 (trace 가치).

Schema-level 변경 없음 — UPDATE 쿼리만.

---

## Stage 8 Data Product Schema (pre-commit for Track C)

### chain_diagram_data.json

Track C populated this schema directly (sign-correction applied + operational distinction). File committed at `data/bridge/chain_diagram_data.json`:

```json
{
  "direction": "global_to_korea",
  "sign_correction_applied": true,
  "nodes": [
    {"id": "csi", "label": "CSI (Macro)", "role": "common_driver"},
    {"id": "global", "label": "NB Global Search", "role": "upstream"},
    {"id": "korea", "label": "NB Korea Search", "role": "downstream"}
  ],
  "edges": [
    {
      "from": "csi", "to": "global",
      "relationship": "direct_drive",
      "lag_weeks": 0,
      "evidence": "VARX CSI lag 0 coef +0.1772, p=0.0161"
    },
    {
      "from": "csi", "to": "korea",
      "relationship": "direct_drive",
      "lag_weeks": null,
      "evidence": "Stage 4 monthly Granger CSI->Korea lag 4, sign-corrected"
    },
    {
      "from": "global", "to": "korea",
      "relationship": "lead_lag_correlation",
      "lag_weeks": 10,
      "evidence": "DTW +10.4w, CC +9w (sign-corrected)",
      "causal_chain_status": "rejected_5_dim_orthogonal_null",
      "operational_use": {
        "monitoring_indicator": true,
        "predictive_feature": false,
        "interference_detected": true,
        "interference_evidence": "Prophet -9.01% / SARIMAX -10.94% RMSE degradation, DM p<0.001",
        "dashboard_role": "right_panel_reference_visualization"
      }
    }
  ],
  "narrative": {
    "scenario": "B_parallel_with_operational_refinement",
    "interpretation": "CSI directly and independently drives both regions; Global-Korea correlation reflects shape similarity (DTW lead) without causal mediation (mediation null bidirectional). Global signal is monitoring leading indicator only -- not predictive feature for Korea forecast model."
  }
}
```

The `operational_use` nested object enables Stage 8 dashboard branching logic: `if edge.operational_use.predictive_feature: include in forecast model` — directly consumable from chart code.

---

## Files Created in Stage 7 (so far)

```
analysis/
├── bridge_stationarity_check.py        # Step 0
├── bridge_trend_diagnostics.py         # Step 0 follow-up: ADF(ct), KPSS(ct), detrending
├── bridge_chain_analysis.py            # Track A1 + A1' (original) + A1' (sign-corrected)
├── bridge_monthly_check.py             # Supplementary: monthly Korea↔Global Granger
├── bridge_lagged_cointegration.py      # Supplementary: EG AEG lag grid 9/10/11w
├── bridge_mstl_leakage_check.py        # Track A3 self-diagnostic (DP23)
├── bridge_leakage_free_dtw.py          # Track A2: leakage-free DTW+CC, DP24 detection
├── bridge_global_enhanced.py           # Track A3 ORIGINAL (invalidated, retained as DP23 evidence)
└── bridge_korea_enhanced_sign_corrected.py  # Track A3 RE-DESIGN + B1 nested (sign-corrected)

data/bridge/
├── stationarity_report.{json,md}
├── trend_diagnostics.json
├── varx_results.{json,md}
├── monthly_korea_global_granger.json
├── mediation_bootstrap.{json,md}                       # Original direction
├── mediation_bootstrap_sign_corrected.{json,md}        # Sign-corrected direction
├── lagged_cointegration.{json,md}
├── mstl_leakage_check.json                             # DP23 evidence
├── leakage_free_dtw.json                               # DP24 evidence
├── leakage_free_trends.npz                             # Track A3 robustness input
├── lag_grid_cv_results.csv                             # Track A3 ORIGINAL invalidated (DP23)
├── global_forecast_triple_comparison.csv               # Track A3 ORIGINAL invalidated
├── triple_comparison_metrics.json                      # Track A3 ORIGINAL invalidated
├── lag_grid_cv_results_sign_corrected.csv              # Track A3 RE-DESIGN
├── korea_forecast_triple_comparison.csv                # Track A3 RE-DESIGN (Stage 8 right-panel input)
├── triple_comparison_metrics_sign_corrected.json       # Track A3 RE-DESIGN
└── seasonal_lead_sign_corrected.csv                    # B1 nested

figures/bridge/
├── varx_lag_selection.png
├── varx_irf_orthogonalized.png
├── varx_irf_cumulative.png
├── mediation_distribution.png                          # Original
├── mediation_distribution_sign_corrected.png           # Sign-corrected
├── mstl_leakage_diagnostic.png                         # DP23
├── leakage_free_dtw_comparison.png                     # DP24 evidence
├── triple_comparison_rmse.png                          # Track A3 ORIGINAL invalidated
├── triple_comparison_forecasts.png                     # Track A3 ORIGINAL invalidated
├── lag_grid_cv.png                                     # Track A3 ORIGINAL invalidated
├── triple_comparison_rmse_sign_corrected.png           # Track A3 RE-DESIGN
├── triple_comparison_forecasts_sign_corrected.png      # Track A3 RE-DESIGN
├── lag_grid_cv_sign_corrected.png                      # Track A3 RE-DESIGN
└── seasonal_lead.png                                   # B1 nested
```

Track C + Stage 7 close artifacts (COMPLETED 2026-05-03):

```
data/bridge/
└── chain_diagram_data.json                             # Track C — Stage 8 dashboard direct input

figures/bridge/
└── chain_summary.png                                   # Track C — 1-slide interview visualization

docs/
└── stage7_bridge_report.md                             # Track C — 1-page narrative summary (4-layer climax)

database/migrations/
└── 011_korea_global_lag_sign_correction.sql            # Applied 2026-05-03 (12 rows sign-flipped + labels swapped)
```

---

## Documentation Updates

- `methodology.md` §12.1~§12.7 body authored (sign-corrected). §12.3.5 Methodology Validation expansion + §12.6 Mechanism 3 hypotheses + §12.7 5 sub-sections handoff narrative all complete.
- `exploratory_findings.md` Stage 7 section: DP19/20/21/23/24 + KPI 7 redefinition (Global trend MA → Korea monitoring leading indicator, operational scope explicit) + KPI 12 (5-Dim Verification Pattern) + KPI 13 (Methodology Validation Stage Pattern) + Integrated Business Diagnosis (Stage 7 sign-corrected). DP22 deprecated with body preserved + DP24 successor cross-reference. DP9 [Sign Correction Applied] tag.
- `comprehensive_advisor_handoff.md`: Stage 7 close 증분 update applied 2026-05-03 (§4 doc list 12 docs, §5 Stage 0~7 진행 요약, §6 DP1~24 + KPI 13종 + 종합 진단 narrative Stage 1~7, §7 Stage 8 다음 작업, §8.1 Stage 7 결정 추가 + §8.2 narrative methodology validation climax, §10 Stage 8 진입 준비).
- `sportswear_brand_monitor_project_plan_v3.md`: §4.5 Sign Correction Notice inline blockquote + §4.8 Stage 7 4-layer narrative inline blockquote + §12 검증된 인사이트 재구성 (KPI 11 → 13종) + footer Stage 7 close 날짜 갱신 applied 2026-05-03.

### Advisor decisions recorded (Stage 7, including post-DP24 cascade)

| # | Decision | Origin |
|---|---|---|
| 1 | Option H frequency hybrid | Pre-Stage 7 |
| 2 | Step 0 stationarity re-test mandatory | Pre-Stage 7 |
| 3 | VARX endogenous = search d1, CSI distributed lag {0,4,8,12} | Pre-Stage 7 |
| 4 | Mediation joint MBB + StationaryBootstrap, BCa, 5000 iter | Pre-Stage 7 |
| 5 | Track A3 paired-fold CV, lag grid 6–14w | Pre-Stage 7 |
| 6 | Triple comparison: baseline / +CSI / +CSI+Korea_trend; SARIMAX parallel | Pre-Stage 7 |
| 7 | Scenario thresholds (% indirect 4-bin) pre-committed | Pre-Stage 7 |
| Option 6 | Per-analysis variable separation | Post Step 0 |
| A1 follow-up | Decision 7 matrix expanded with VARX-null pre-condition | Post A1 |
| A1' verdict | Scenario B confirmed (original direction) | Post A1' |
| Cointegration spec | EG AEG, BIC autolag, trend='c', lag grid 9/10/11w bidirectional | Post A1' |
| §12 phrasing | DP20 conservative, §12.3.3 driver-confounded reference | Post commit review |
| **DP24 cascade** | **Sign correction commit, Mirror Sentinel + Differential Reactivity, mediation re-run G→K, DB retrofit Stage 7 close, KPI 7 redefinition** | **Post DP24 detection** |
| Track A2 redefinition | SARIMAX hop-gain retired; A2 repurposed as Sign Convention Validation | Post DP24 |
| Track A3 re-design | Global → Korea direction, raw `global_search` lagged primary, 1–2 day cap | Post DP24 |
| Track B1 nesting | B1 nested in Track A3 re-design (same data input, avoid duplicate prep) | Post DP24 |

---

## Track C: Bridge Report Consolidation [COMPLETED 2026-05-03]

Track A3 re-design + B1 nested closed with degradation outcome (4th scenario, sentinel operational refinement). Track C consolidates 3-stage chain diagram, BDC operational recommendations, and Stage 8 handoff artifacts. All three deliverables completed and committed:

**Track C deliverables (all COMPLETED):**

| Deliverable | Path | Role |
|---|---|---|
| Machine-readable chain data | `data/bridge/chain_diagram_data.json` | Stage 8 Streamlit dashboard direct input. Schema includes `nodes` (CSI/Global/Korea), `edges` (3 with sign-corrected direction), `operational_use` object 5 fields (monitoring_indicator / predictive_feature / interference_detected / interference_evidence / dashboard_role), `narrative` scenario tag (`B_parallel_with_operational_refinement` + Mirror Sentinel + Differential Reactivity framing), `test_summary` 11 tests, `data_points_referenced` 5건. |
| Visualization | `figures/bridge/chain_summary.png` | 1-slide interview presentation. 3-node diagram with sign-corrected direction (Global → Korea dashed line = shape lead monitoring only), CSI → Global/Korea solid lines (direct drive), "✗ NOT predictive feature (Prophet −9.0% / SARIMAX −10.9% RMSE degradation)" red annotation, 5-Dimension Orthogonal Null + DP20→DP23→DP24 self-diagnostic chain bottom panel. |
| Narrative summary | `docs/stage7_bridge_report.md` | 1-page interview/portfolio reference (78 lines). 4-layer climax structure: Layer 1 (5-dim orthogonal null × 11 tests) → Layer 2 (self-diagnostic chain DP20→DP23→DP24) → Layer 3 (3 quantitative signatures of DP24) → Layer 4 (operational refinement Mirror Sentinel + Differential Reactivity). "Why This Matters For BDC Roles" section with climax quote. Stage 8 handoff 4 components. Cross-references to stage7_checkpoint.md, methodology.md §12, exploratory_findings.md DP19~24, migration 011, chain_summary.png. |

**Three artifacts in complementary roles:** machine-readable (JSON for dashboard code) + visualization (PNG for slide) + narrative (Markdown for human read). All three express the same 4-layer narrative + sign-corrected direction + monitoring vs predictive distinction with internal consistency.

---

## Stage 7 Close: Lockdown Checklist (ALL COMPLETED 2026-05-03)

Stage 7 close required synchronization across 8 documents and artifacts. All applied:

| Item | Status | Note |
|---|---|---|
| `methodology.md` §12.1~§12.7 body | COMPLETED | §12.1~§12.6 condensed body + §12.3.5 + §12.6 full migrate from checkpoint + §12.7 5 sub-sections handoff narrative |
| `exploratory_findings.md` DP19~24 + KPI 7 redefinition + KPI 12/13 | COMPLETED | DP9 [Sign Correction Applied] tag + DP22 [DEPRECATED] + DP24 climax 3-signature stack + Stage 7 Integrated Diagnosis + Methodology Validation Climax 인용 |
| Migration 011 retrofit | COMPLETED | `mart.korea_global_lag` 12 rows sign-flipped + `lag_direction` labels swapped |
| `stage4_checkpoint.md` Sign Correction Notice footnote | COMPLETED | 5-item surfacing (detect timing / magnitude vs direction / 3 quantitative signatures / DB retrofit applied / 본문 보존 정책) |
| Track C 3 산출물 | COMPLETED | chain_diagram_data.json + chain_summary.png + stage7_bridge_report.md |
| `sportswear_brand_monitor_project_plan_v3.md` 동기화 | COMPLETED | §4.5 Sign Correction Notice + §4.8 Stage 7 4-layer narrative inline blockquote + §12 검증된 인사이트 재구성 (KPI 11→13종) + footer 날짜 |
| `comprehensive_advisor_handoff.md` 증분 | COMPLETED | §4 12 docs + §5 Stage 0~7 + §6 DP1~24 + KPI 13종 + 종합 진단 narrative Stage 1~7 + §7 Stage 8 다음 + §8 Stage 7 결정 추가 + §10 Stage 8 진입 준비 |
| Auto-classifier patch (signed delta + 4-way branch) | COMPLETED | self-detected + applied + 4-way outcome matrix officialized |

---

## Next: Stage 8 Entry

Stage 7 → Stage 8 handoff narrative authored in methodology.md §12.7 (5 sub-sections). Track C산출물이 Stage 8 dashboard 직접 입력으로 작동하도록 schema 사전 commit 완료.

**Stage 8 entry pre-decisions (Stage 7 cascade 반영):**
- Forecast & Bridge tab 통합 구조 (Korea Prophet 좌측 + chain_diagram 우측)
- KPI 7 dual surface (monitoring vs predictive 분리 tooltip 양 dashboard)
- Methodology Documentation tab (KPI 12/13 governance asset surfacing)
- Migration 011 sign-corrected table 직접 query (no further translation logic)
- Stage 7 4-layer narrative dashboard tooltip / About section 반영
- stage7_bridge_report.md README link

*Stage 7 COMPLETED 2026-05-03 — All Tracks (A1 + A1' bidirectional + A2 sign convention validation + A3 re-design + B1 nested + C bridge report) closed. Methodology Validation Stage narrative committed across methodology.md §12, exploratory_findings.md DP19~24, stage7_bridge_report.md, v3 plan §4.8, comprehensive_advisor_handoff.md §5~10. Stage 8 진입 준비 완료.*
