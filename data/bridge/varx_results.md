# Stage 7 Track A1 -- VARX on Search diff1 with CSI Distributed-Lag Exogenous

**Date:** 2026-05-03 00:29
**Endogenous:** (korea_d1, global_d1)  -- Step 0 + Option 6 advisor decision
**Exogenous CSI lags:** [0, 4, 8, 12]
**Cholesky ordering:** Korea first (Stage 4 +10.4w lead hypothesis)
**Significance:** alpha = 0.05

## 1. Data Preparation

  endog cols: ['korea_d1', 'global_d1']
  exog cols:  ['csi_d1_l0', 'csi_d1_l4', 'csi_d1_l8', 'csi_d1_l12']
  effective sample: 2023-03-26 ~ 2026-04-19  (161 weeks)

## 2. Lag Selection (Decision 3 -- BIC primary)


Lag selection on grid 1..13 with CSI distributed-lag exogenous...
  Selected lags  AIC=1  BIC=1  HQIC=1  FPE=1
  Lag selection plot saved: figures/bridge/varx_lag_selection.png
  Selected p = 1 (BIC)

## 3. VAR(p) Fit with CSI Exogenous

  Effective observations: 160
  Number of equations:    2
  AIC=2.6638  BIC=2.9328  HQIC=2.7730  Log-Lik=-653.1620

## 4. Bidirectional Granger Causality (within VARX)

  korea_to_global         F= 1.4521  p=0.2291  -> fail_to_reject
  global_to_korea         F= 0.2310  p=0.6311  -> fail_to_reject

## 5. Joint Significance of CSI Distributed Lags (LR test)

  LL_full       = -653.1620
  LL_restricted = -660.0359
  LR statistic  = 13.7476  df=8  p=0.0886  -> fail_to_reject

## 6. CSI Per-Lag Coefficients

  Equation       Regressor            Coef          p
  korea_d1       csi_d1_l0          0.1714     0.1228
  korea_d1       csi_d1_l4          0.1237     0.2893
  korea_d1       csi_d1_l8         -0.0923     0.4445
  korea_d1       csi_d1_l12         0.0599     0.6145
  global_d1      csi_d1_l0          0.1772     0.0161 *
  global_d1      csi_d1_l4          0.1023     0.1861
  global_d1      csi_d1_l8          0.0742     0.3542
  global_d1      csi_d1_l12        -0.0084     0.9152

## 7. IRF (Cumulative Orthogonalized)

  Cumulative response of Global to Korea shock @ h=20: +0.0444
  Cumulative response of Korea to Global shock @ h=20: +0.0434
  IRF figures saved: figures/bridge/varx_irf_*.png

JSON saved:     data/bridge/varx_results.json
