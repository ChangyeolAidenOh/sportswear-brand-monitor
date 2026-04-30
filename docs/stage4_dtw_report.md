# Stage 4 Track B: Korea-Global Lead-Lag (DTW) Report

**Date:** 2026-04-30 19:14
**Method:** Dynamic Time Warping (tslearn/fastdtw)
**Context:** Re-examination of Stage 0 H1 cross-correlation -167w anomaly

---
Stage 4 Track B: DTW Korea-Global Lead-Lag
Started: 2026-04-30 19:14:48.056996

## Step B1: Time Series Extraction

  rows: 2784
  period: 2022-12-25 00:00:00 ~ 2026-04-19 00:00:00
  brands: ['adidas', 'new_balance', 'nike', 'puma']

| Brand | Region | N_weeks | Search Mean | Search Std |
|---|---|---|---|---|
| adidas | global | 348 | 41.49 | 6.24 |
| adidas | korea | 348 | 37.33 | 6.56 |
| new_balance | global | 348 | 16.82 | 5.55 |
| new_balance | korea | 348 | 18.22 | 4.23 |
| nike | global | 348 | 61.27 | 14.31 |
| nike | korea | 348 | 68.04 | 13.93 |
| puma | global | 348 | 11.47 | 2.40 |
| puma | korea | 348 | 8.96 | 1.69 |

## Step B2: DTW Distance Computation

  input series: residual
  nike: DTW=13.98, norm=0.0402, lag=26.8w (Korea leads), CC best lag=35
  adidas: DTW=12.35, norm=0.0355, lag=12.8w (Korea leads), CC best lag=10
  puma: DTW=11.39, norm=0.0327, lag=25.1w (Korea leads), CC best lag=42
  new_balance: DTW=13.52, norm=0.0389, lag=42.2w (Korea leads), CC best lag=34

| Brand | DTW dist | Norm DTW | Mean Lag | Direction | CC Lag | Stage 0 Ref |
|---|---|---|---|---|---|---|
| nike | 13.98 | 0.0402 | 26.8w | Korea leads | 35w |  |
| adidas | 12.35 | 0.0355 | 12.8w | Korea leads | 10w |  |
| puma | 11.39 | 0.0327 | 25.1w | Korea leads | 42w |  |
| new_balance | 13.52 | 0.0389 | 42.2w | Korea leads | 34w | -167w |

## Step B3: Visualization

  saved: figures/dtw/dtw_alignment_nike.png
  saved: figures/dtw/dtw_alignment_adidas.png
  saved: figures/dtw/dtw_alignment_puma.png
  saved: figures/dtw/dtw_alignment_new_balance.png
  saved: figures/dtw/dtw_summary.png

## Step B4: Mart Table Output

  migration written: database/migrations/008_korea_global_lag.sql
  inserted 4 rows into mart.korea_global_lag
