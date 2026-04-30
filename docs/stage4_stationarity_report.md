# Stage 4 Track A: Search <-> CSI Leading Indicator Report

**Date:** 2026-04-30 18:02
**Question:** Does brand-level search demand (micro) serve as a leading indicator for consumer sentiment (macro CSI), or vice versa?

**Design Decisions:**
- Search input: MSTL residual (innovation component)
- CSI input: level or 1st difference (ADF-determined)
- Bidirectional: Search->CSI + CSI->Search
- Sub-analysis: shopping search (purchase-intent proxy)
- Max lag: 4 months, AIC-selected VAR order
- Neural Granger: excluded (40 obs, overfitting risk)

---
Stage 4 Track A: Search <-> CSI Leading Indicator Validation
Started: 2026-04-30 18:02:10.441956

## Step A1: Data Extraction

  search_weekly: 1392 rows, 2022-12-25 00:00:00 ~ 2026-04-19 00:00:00
  seasonal_components (residual): 2784 rows
  shopping_search: 696 rows
  csi: 52 months, 2022-01-01 00:00:00 ~ 2026-04-01 00:00:00

## Step A2: MSTL Residual -> Monthly + CSI Alignment

  common period: 2022-12 ~ 2026-04
  observations per series: 41 months

| Brand | Region | N_months | Residual Mean | Residual Std | CSI Mean |
|---|---|---|---|---|---|
| adidas | global | 41 | 0.3995 | 1.3019 | 100.7 |
| adidas | korea | 41 | -0.4049 | 2.3690 | 100.7 |
| new_balance | global | 41 | 0.4861 | 1.1338 | 100.7 |
| new_balance | korea | 41 | -0.4184 | 1.3081 | 100.7 |
| nike | global | 41 | 1.5957 | 4.2415 | 100.7 |
| nike | korea | 41 | -1.3342 | 4.0883 | 100.7 |
| puma | global | 41 | 0.1883 | 0.5228 | 100.7 |
| puma | korea | 41 | -0.0511 | 0.7426 | 100.7 |
  shopping aligned: 164 rows

## Step A3: Stationarity Tests


| Series | ADF stat | ADF p | KPSS p | Verdict |
|---|---|---|---|---|
| CSI_level | -2.7695 | 0.0628 | 0.0541 | Difference-stationary |
| CSI_diff1 | -4.4781 | 0.0002 | 0.1000 | Stationary |
| adidas_global_residual | -2.0377 | 0.2703 | 0.1000 | Difference-stationary |
| adidas_korea_residual | -4.0410 | 0.0012 | 0.1000 | Stationary |
| new_balance_global_residual | -3.6302 | 0.0052 | 0.1000 | Stationary |
| new_balance_korea_residual | -4.4300 | 0.0003 | 0.1000 | Stationary |
| nike_global_residual | -2.8151 | 0.0562 | 0.1000 | Difference-stationary |
| nike_korea_residual | -4.3039 | 0.0004 | 0.1000 | Stationary |
| puma_global_residual | -2.9634 | 0.0385 | 0.1000 | Stationary |
| puma_korea_residual | -4.5113 | 0.0002 | 0.1000 | Stationary |
  CSI: Difference-stationary at level -> 1st differencing applied
  CSI diff1 verdict: Stationary
  [NOTE] 2 residual series not stationary at 5%
    adidas_global_residual: p=0.2703
    nike_global_residual: p=0.0562

## Step A4: Bidirectional Granger Causality

  CSI preprocessing: diff1
  Search preprocessing: MSTL residual (monthly mean)
  Max lag: 4 months
  adidas/global: Search leads CSI
  adidas/korea: Feedback loop
  new_balance/global: CSI leads Search
  new_balance/korea: CSI leads Search
  nike/global: Independent
  nike/korea: Search leads CSI
  puma/global: CSI leads Search
  puma/korea: Independent

### P-value Matrix (Search -> CSI)

| Brand | Region | Lag 1 | Lag 2 | Lag 3 | Lag 4 |
|---|---|---|---|---|---|
| adidas | global | 0.6895 | 0.0632 | 0.1664 | **0.0443** |
| adidas | korea | 0.7462 | 0.0889 | **0.0374** | **0.0253** |
| new_balance | global | 0.3174 | 0.7971 | 0.7146 | 0.7926 |
| new_balance | korea | 0.3508 | 0.5855 | 0.1915 | 0.1564 |
| nike | global | 0.3398 | 0.6250 | 0.4013 | 0.5722 |
| nike | korea | 0.9594 | 0.3559 | **0.0171** | **0.0279** |
| puma | global | 0.3491 | 0.7295 | 0.8014 | 0.8837 |
| puma | korea | 0.3222 | 0.0725 | 0.0664 | 0.1260 |

### P-value Matrix (CSI -> Search)

| Brand | Region | Lag 1 | Lag 2 | Lag 3 | Lag 4 |
|---|---|---|---|---|---|
| adidas | global | 0.4779 | 0.5198 | 0.7199 | 0.8327 |
| adidas | korea | 0.6308 | 0.0553 | **0.0409** | 0.0517 |
| new_balance | global | 0.4173 | **0.0321** | **0.0016** | **0.0079** |
| new_balance | korea | 0.5801 | 0.0709 | **0.0229** | **0.0161** |
| nike | global | 0.7173 | 0.3948 | 0.0812 | 0.2174 |
| nike | korea | 0.8367 | 0.3312 | 0.2342 | 0.3833 |
| puma | global | 0.9105 | 0.0952 | **0.0004** | **0.0023** |
| puma | korea | 0.4657 | 0.0558 | 0.1016 | 0.2338 |

### Causality Pattern Summary

| Brand | Region | Pattern |
|---|---|---|
| adidas | global | Search leads CSI |
| adidas | korea | Feedback loop |
| new_balance | global | CSI leads Search |
| new_balance | korea | CSI leads Search |
| nike | global | Independent |
| nike | korea | Search leads CSI |
| puma | global | CSI leads Search |
| puma | korea | Independent |

## Step A5: VAR Model + Impulse Response Function

  adidas/global: VAR(2), AIC=2.36
    saved: figures/var/irf/irf_adidas_global.png
  adidas/korea: VAR(3), AIC=3.75
    saved: figures/var/irf/irf_adidas_korea.png
    cointegration detected (p=0.0135) -> VECM candidate
  new_balance/global: VAR(3), AIC=1.95
    saved: figures/var/irf/irf_new_balance_global.png
    cointegration detected (p=0.0190) -> VECM candidate
  new_balance/korea: VAR(4), AIC=2.45
    saved: figures/var/irf/irf_new_balance_korea.png
    cointegration detected (p=0.0008) -> VECM candidate
  nike/global: VAR(3), AIC=4.76
    saved: figures/var/irf/irf_nike_global.png
  nike/korea: VAR(3), AIC=4.70
    saved: figures/var/irf/irf_nike_korea.png
    cointegration detected (p=0.0070) -> VECM candidate
  puma/global: VAR(3), AIC=0.47
    saved: figures/var/irf/irf_puma_global.png
  puma/korea: VAR(2), AIC=1.38
    saved: figures/var/irf/irf_puma_korea.png
    cointegration detected (p=0.0033) -> VECM candidate

## Step A6: Shopping Search Sub-analysis

  input: shopping search monthly mean
  CSI preprocessing: diff1

| Brand | Region | Direction | Best Lag | p-value | Sig |
|---|---|---|---|---|---|
| adidas | korea | CSI->Search | 1 | 0.0721 | No |
| adidas | korea | Search->CSI | 1 | 0.1101 | No |
| new_balance | korea | CSI->Search | 1 | 0.3830 | No |
| new_balance | korea | Search->CSI | 1 | 0.0942 | No |
| nike | korea | CSI->Search | 2 | 0.3284 | No |
| nike | korea | Search->CSI | 4 | 0.6604 | No |
| puma | korea | CSI->Search | 4 | 0.6195 | No |
| puma | korea | Search->CSI | 1 | 0.4226 | No |

## Mart Insert: granger_results

  inserted 64 rows into mart.granger_results
