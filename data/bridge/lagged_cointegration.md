# Stage 7 supplementary -- Lagged cointegration (Engle-Granger AEG)

**Date:** 2026-05-03 01:09
**Lag grid:** [9, 10, 11] weeks
**Method:** aeg, trend='c', autolag='BIC'
**LHS primary:** Global_trend_t (Stage 6 ARIMA(0,1,0) -> endogenous)
**Significance:** alpha = 0.05

## 1. Data Preparation

  korea_trend:  174w  range [15.32, 24.85]
  global_trend: 174w  range [3.89, 20.63]

## 2. Primary direction -- Global_t ~ Korea_{t-lag}

  (LHS=Global, RHS=lagged Korea; model-consistent per Stage 6)

  lag= 9w  n=165  t= -2.182  p=0.4338  crit5%=-3.374  -> no_cointegration
  lag=10w  n=164  t= -2.217  p=0.4159  crit5%=-3.374  -> no_cointegration
  lag=11w  n=163  t= -2.249  p=0.3991  crit5%=-3.374  -> no_cointegration
  Primary lag-grid classification: robust_no_cointegration

## 3. Robustness direction -- Korea_t ~ Global_{t+lag}

  (Symmetric check; lag inversion realized via leading Global)

  lag= 9w  n=165  t= -0.441  p=0.9682  crit5%=-3.374  -> no_cointegration
  lag=10w  n=164  t= -0.455  p=0.9674  crit5%=-3.374  -> no_cointegration
  lag=11w  n=163  t= -0.714  p=0.9451  crit5%=-3.374  -> no_cointegration
  Reverse lag-grid classification: robust_no_cointegration

## 4. Cross-direction consistency

  Cross-direction: consistent
  Interpretation:  No lagged level equilibrium in either direction -- shape similarity (DTW) but level independence; purer differential-reactivity evidence

## 5. Section 12.6 narrative slot

Lagged cointegration rejected across the 9/10/11w grid. Korea trend and Global trend share shape similarity (Stage 4 DTW +10.4w) but no level equilibrium at any tested lag. This supports the strongest form of the differential-reactivity hypothesis: Korea and Global respond to overlapping drivers at different speeds without converging to a shared level.

JSON saved:     data/bridge/lagged_cointegration.json
