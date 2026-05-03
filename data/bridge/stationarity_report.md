# Stage 7 Step 0 -- Weekly Stationarity Re-Test

**Date:** 2026-05-01 18:29
**Significance:** alpha = 0.05


## 1. Data Extraction

Loading data from PostgreSQL...
  search: korea 174w  global 174w
  trend:  korea 174w  global 174w
  csi:    52 months -> 174 weeks (forward-fill)
  common: 2022-12-25 ~ 2026-04-19  (174 weeks)

## 2. Univariate Stationarity Tests (ADF + KPSS)

  korea_search   level  ADF p=0.1175  KPSS p=0.0100  -> unit_root
  korea_search   diff1  ADF p=0.0000  KPSS p=0.1000  -> stationary

  global_search  level  ADF p=0.1706  KPSS p=0.0100  -> unit_root
  global_search  diff1  ADF p=0.0000  KPSS p=0.1000  -> stationary

  korea_trend    level  ADF p=0.9822  KPSS p=0.0100  -> unit_root
  korea_trend    diff1  ADF p=0.5173  KPSS p=0.0100  -> unit_root

  global_trend   level  ADF p=0.0130  KPSS p=0.0100  -> trend_stationary
  global_trend   diff1  ADF p=0.5272  KPSS p=0.0100  -> unit_root

  csi            level  ADF p=0.2395  KPSS p=0.0100  -> unit_root
  csi            diff1  ADF p=0.0000  KPSS p=0.1000  -> stationary


## 3. Engle-Granger Cointegration Tests

  korea_search_x_global_search              coint p=0.0896  -> no
  korea_search_x_csi                        coint p=0.0887  -> no
  global_search_x_csi                       coint p=0.4256  -> no
  korea_trend_x_global_trend                coint p=0.9433  -> no
  korea_trend_x_csi                         coint p=0.9934  -> no
  global_trend_x_csi                        coint p=0.6128  -> no


## 4. Transformation Decisions (committed)

  korea_search    diff1   (Level non-stationary (ADF p=0.1175, KPSS p=0.0100); diff1 stationary)
  global_search   diff1   (Level non-stationary (ADF p=0.1706, KPSS p=0.0100); diff1 stationary)
  korea_trend     review  (Neither level nor diff1 cleanly stationary (level: unit_root, diff1: unit_root))
  global_trend    review  (Neither level nor diff1 cleanly stationary (level: trend_stationary, diff1: unit_root))
  csi             diff1   (Level non-stationary (ADF p=0.2395, KPSS p=0.0100); diff1 stationary)

## 5. Advisor Escalation Triggers

**ESCALATION REQUIRED -- return to advisor before Track A1:**
  - AMBIGUOUS_TRANSFORM: ['korea_trend', 'global_trend'] -- neither level nor diff1 cleanly stationary

JSON saved:     data/bridge/stationarity_report.json
