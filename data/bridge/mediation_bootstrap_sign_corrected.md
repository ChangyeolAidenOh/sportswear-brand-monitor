# Stage 7 Track A1' SIGN-CORRECTED -- Global_{t-lag} -> Korea Mediation

**Date:** 2026-05-03 02:22
**Direction:** Global trend lagged -> Korea trend (sign-corrected per DP24)
**lag*:** +10w (Stage 4 magnitude preserved)
**CSI distributed lags:** [0, 4, 8, 12]
**Block length:** 13w
**Bootstrap iterations:** 5000

## 1. Data Preparation

  trend mediation rows: 162
    cols: ['outcome_korea_trend', 'mediator_global_trend_lag', 'csi_l0', 'csi_l4', 'csi_l8', 'csi_l12']
  diff1 mediation rows: 161
    cols: ['outcome_korea_d1', 'mediator_global_d1_lag', 'csi_d1_l0', 'csi_d1_l4', 'csi_d1_l8', 'csi_d1_l12']

## 2. Trend Mediation -- Point Estimate (Sign-Corrected)

  a_coef                 = +0.0470
  b_coef                 = +0.2614
  c_coef                 = +0.1135
  c_prime_coef           = +0.1012
  indirect_a_times_b     = +0.0123
  total_effect_c         = +0.1135
  pct_indirect           = +10.8245
  primary_treatment      = csi_l0

## 3. Diff1 Mediation -- Point Estimate (Sign-Corrected Robustness)

  a_coef                 = +0.0671
  b_coef                 = -0.1836
  c_coef                 = +0.1347
  c_prime_coef           = +0.1471
  indirect_a_times_b     = -0.0123
  total_effect_c         = +0.1347
  pct_indirect           = -9.1483
  primary_treatment      = csi_d1_l0

## 4. Bootstrap Inference -- 4 cells

  Running trend_mbb: n_iter=5000, blocks=(13,), n_obs=162
  trend_mbb: point=+0.0123  BCa 95% CI=[-0.1211, +0.1764]  (skipped 0/5000)
  Running trend_sb: n_iter=5000, blocks=(13,), n_obs=162
  trend_sb: point=+0.0123  BCa 95% CI=[-0.0659, +0.1701]  (skipped 0/5000)
  Running diff1_mbb: n_iter=5000, blocks=(13,), n_obs=161
  diff1_mbb: point=-0.0123  BCa 95% CI=[-0.0561, +0.0066]  (skipped 0/5000)
  Running diff1_sb: n_iter=5000, blocks=(13,), n_obs=161
  diff1_sb: point=-0.0123  BCa 95% CI=[-0.0505, +0.0044]  (skipped 0/5000)

## 5. Scenario Classification + Paired Comparison vs Original

  Matrix row: row_3_full_parallel
  Narrative:  Sign-corrected: both null. Combined with original-direction null, channel absence is bidirectionally confirmed. CSI is common direct driver of both Korea and Global; no intermediary. 5-dimension orthogonal null (mediation x 2 directions + VARX + monthly Granger + lagged cointegration).
  Decision 7 scenario: B_parallel

  Paired comparison vs original (Korea -> Global):
  | Component         | Original (K->G) | Sign-corrected (G->K) |
  |---|---|---|
  | Trend a path      | +0.0928         | +0.0470              |
  | Trend b path      | +0.5272         | +0.2614              |
  | Trend indirect    | +0.0489         | +0.0123              |
  | Trend MBB BCa CI  | [-0.39, +0.18]  | [-0.1211, +0.1764] |
  | Diff1 a path      | +0.1216         | +0.0671              |
  | Diff1 b path      | -0.0390         | -0.1836              |
  | Diff1 indirect    | -0.0047         | -0.0123              |
  | Diff1 MBB BCa CI  | [-0.04, +0.003] | [-0.0561, +0.0066] |

## 6. Distribution Plot

  Distribution figure saved: figures/bridge/mediation_distribution_sign_corrected.png

JSON saved:     data/bridge/mediation_bootstrap_sign_corrected.json
