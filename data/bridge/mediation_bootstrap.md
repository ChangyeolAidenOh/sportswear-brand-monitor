# Stage 7 Track A1' -- Mediation with Joint Block Bootstrap

**Date:** 2026-05-03 00:51
**lag* fixed at:** +10w (Stage 4 DTW finding; A3 will refine)
**CSI distributed lags:** [0, 4, 8, 12]
**Block length:** 13w (sqrt(n) heuristic)
**Bootstrap iterations:** 5000

## 1. Data Preparation

  trend mediation rows: 162
    cols: ['outcome_global_trend', 'mediator_korea_trend_lag', 'csi_l0', 'csi_l4', 'csi_l8', 'csi_l12']
  diff1 mediation rows: 161
    cols: ['outcome_global_d1', 'mediator_korea_d1_lag', 'csi_d1_l0', 'csi_d1_l4', 'csi_d1_l8', 'csi_d1_l12']

## 2. Trend Mediation -- Point Estimate (Primary)

  a_coef                 = +0.0928
  b_coef                 = +0.5272
  c_coef                 = +0.0407
  c_prime_coef           = -0.0083
  indirect_a_times_b     = +0.0489
  total_effect_c         = +0.0407
  pct_indirect           = +120.3537
  primary_treatment      = csi_l0

## 3. Diff1 Mediation -- Point Estimate (Robustness)

  a_coef                 = +0.1216
  b_coef                 = -0.0390
  c_coef                 = +0.1828
  c_prime_coef           = +0.1876
  indirect_a_times_b     = -0.0047
  total_effect_c         = +0.1828
  pct_indirect           = -2.5945
  primary_treatment      = csi_d1_l0

## 4. Bootstrap Inference -- 4 cells (trend/diff1 x MBB/SB)

  Running trend_mbb: n_iter=5000, blocks=(13,), n_obs=162
  trend_mbb: point=+0.0489  BCa 95% CI=[-0.3933, +0.1753]  (skipped 0/5000)
  Running trend_sb: n_iter=5000, blocks=(13,), n_obs=162
  trend_sb: point=+0.0489  BCa 95% CI=[-0.0246, +0.3436]  (skipped 0/5000)
  Running diff1_mbb: n_iter=5000, blocks=(13,), n_obs=161
  diff1_mbb: point=-0.0047  BCa 95% CI=[-0.0351, +0.0034]  (skipped 0/5000)
  Running diff1_sb: n_iter=5000, blocks=(13,), n_obs=161
  diff1_sb: point=-0.0047  BCa 95% CI=[-0.0352, +0.0029]  (skipped 0/5000)

## 5. Scenario Classification (Decision 7 + advisor matrix)

  Matrix row: row_3_full_parallel
  Narrative:  Full parallel structure -- Scenario B confirmed, 'early reactor' pivot
  Decision 7 scenario: B_parallel

## 6. Distribution Plot

  Distribution figure saved: figures/bridge/mediation_distribution.png

JSON saved:     data/bridge/mediation_bootstrap.json
