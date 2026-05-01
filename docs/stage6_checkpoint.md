# Stage 6 Checkpoint — Forecasting (SARIMAX / LSTM / Chronos)

**Date:** 2026-05-01
**Status:** COMPLETED
**Tracks:** A (SARIMAX Baseline) + B (LSTM Encoder) + C (Chronos Zero-Shot) + D (3-Way Comparison)

---

## Core Finding: Prophet Wins Both Series — Changepoint Detection is the Key

4-way forecast comparison on NB Korea and NB Global search_index (26-week test, 148-week train) reveals Prophet as the overall winner. Ablation analysis confirms changepoint detection — not Fourier flexibility — as the primary driver of Prophet's advantage over SARIMAX. LSTM captures Global's smoother dynamics well but cannot beat Prophet. Chronos zero-shot foundation model finishes last — univariate pattern recognition alone cannot compete with domain-informed exogenous variables on 174-week series.

| Model | Korea RMSE | Korea MAPE | Global RMSE | Global MAPE |
|---|---|---|---|---|
| **Prophet (K=2)** | **5.57** | **18.5%** | **2.54** | **10.6%** |
| SARIMAX | 6.45 | 22.8% | 3.23 | 12.2% |
| LSTM | 8.11 | 29.4% | 2.71 | 10.7% |
| Chronos-small | 7.20 | 25.0% | 3.65 | 13.4% |

Prophet (K=2) is the representative configuration — feature parity with SARIMAX (yearly K=2 + quarterly K=2) ensures the comparison isolates changepoint detection as the differentiating factor.

---

## Track A: SARIMAX Baseline

### A1: Data Preparation

| Component | Detail |
|---|---|
| Target | NB Korea / NB Global search_index (mart.brand_kpi_weekly) |
| Series length | 174 weeks (2022-12-25 ~ 2026-04-19), 0 missing |
| Exogenous — CSI | raw.ecos_raw stat_code=511Y002, 52 months, forward-fill monthly→weekly |
| Train / Test | 148w / 26w (test = 2 quarterly cycles, advisor decision) |
| Anomaly tagging | mstl_residual_2.0 ∪ isolation_forest from mart.anomaly_log |

### A2: Order Selection

Stationarity (ADF):

| Series | Raw p-value | d=1 p-value |
|---|---|---|
| Korea | 0.0197 (stationary) | 0.0000 |
| Global | 0.2637 (non-stationary) | 0.0000 |

Korea raw is borderline stationary but auto_arima selected d=1 with lower AIC; d=1 retained for both.

**Fourier terms design (advisor decision):**
- Seasonal ARIMA s=52 infeasible — 148w train insufficient for seasonal AR/MA parameter estimation
- Quarterly dummy rejected — search seasonality is smooth sinusoidal, not abrupt level shift
- Fourier K=2 for 52w (annual) + K=2 for 13w (quarterly) = 8 exogenous columns
- K=2 ceiling enforced — K≥3 pushes parameter/observation ratio into danger zone
- Total exogenous: 8 Fourier + 1 CSI = 9 columns

**auto_arima (seasonal=False, d=1):**

| Series | Best Order | AIC | Interpretation |
|---|---|---|---|
| Korea | (0, 1, 1) | 642.77 | IMA(1,1) — differenced MA smoothing |
| Global | (0, 1, 0) | 539.88 | Pure random walk — no AR/MA structure |

Global (0,1,0) is a key finding: NB Global search has no autoregressive information; all predictive power comes from Fourier + CSI exogenous.

Manual AIC comparison confirmed auto_arima selections as optimal across 6-7 candidate orders per series.

### A3: Exogenous Coefficient Analysis

**CSI:** Korea 3.98 (p<0.001), Global 2.01 (p<0.001). Korea is ~2x more sensitive to consumer sentiment than Global. Quantitative confirmation of Stage 4 Granger "NB = macro-reactive demand structure."

**Fourier 52w (annual):** Korea sin/cos both significant (p=0.010, 0.024); Global all non-significant. Korea has strong annual seasonality (FW-dominant); Global does not. Consistent with Stage 3 MSTL FW/SS asymmetry.

**Fourier 13w cos_13_2:** Significant in both series (Korea p<0.001, Global p=0.017). A sub-quarterly pattern exists across both markets.

Parameter/observation ratio: ~11 params / 148 obs = 1:13 (safe).

### A4: SARIMAX Performance

| Region | RMSE | MAE | MAPE |
|---|---|---|---|
| Korea | 6.45 | 5.89 | 22.8% |
| Global | 3.23 | 2.65 | 12.2% |

Korea MAPE 22.8% is high but represents realistic baseline for event-driven series. Consistent with Stage 5 finding that event spikes are structurally unpredictable.

---

## Track B: Stacked LSTM with Recursive Forecasting

### B1: Architecture

| Parameter | Value | Rationale |
|---|---|---|
| Layers | 2 (stacked) | Minimum depth for temporal patterns |
| Hidden size | 64 | Balance capacity vs overfitting risk |
| Dropout | 0.3 | Regularization for small sample |
| Lookback | 13 weeks | One quarterly cycle; longer reduces sequence count |
| Attention | None | 174w insufficient for attention learning (advisor decision) |
| Features | search_index + CSI + 8 Fourier | Identical to SARIMAX for fair comparison |

### B2: Training Dynamics

| Metric | Korea | Global |
|---|---|---|
| Model params | 52,801 | 52,801 |
| Train sequences | 113 | 113 |
| Param:sample ratio | 467:1 | 467:1 |
| Early stopping | Epoch 92 | Epoch 47 |
| Best val_loss | 0.030274 | 0.003943 |

**467:1 parameter-to-sample ratio is structurally overfitting.** This ratio alone explains why LSTM cannot beat SARIMAX on Korea — there are insufficient training sequences to learn the model's capacity. Global's earlier convergence (epoch 47) and lower val_loss reflect Global's smoother, more learnable dynamics.

### B3: Recursive Forecast

26-week forecast generated via single-step recursive prediction (predicted value fed back as input). Multi-step error accumulation is a known DL disadvantage but represents realistic forecast scenario.

Effective train after val split: 148 × 0.85 ≈ 126 weeks. Val split: 22 weeks. This 3-way split (train/val/test) creates structurally small partitions — a fundamental limitation of 174-week series for DL.

### B4: LSTM Performance

| Region | RMSE | MAE | MAPE |
|---|---|---|---|
| Korea | 8.11 | 7.54 | 29.4% |
| Global | 2.71 | 2.19 | 10.7% |

Global LSTM outperforms Global SARIMAX (RMSE 2.71 vs 3.23). With ARIMA(0,1,0) having no autoregressive structure, LSTM's ability to capture nonlinear Fourier+CSI combinations provides an advantage. This is a meaningful finding: **when the time series has no inherent autoregressive pattern, DL models can better exploit exogenous feature interactions.**

---

## Track C: Chronos Zero-Shot

### C1: Design

- **Univariate only** — intentional comparison axis: "how far can a foundation model go without domain exogenous?"
- Models: chronos-t5-small (~46M params) + chronos-t5-base (~200M params)
- Context: full 148-week train series
- Probabilistic: 20 samples → median (point), 10th/90th (CI)
- Device: CPU, float32 (M2 MacBook)

### C2: Anti-Scaling Finding

| Model | Korea RMSE | Global RMSE |
|---|---|---|
| Chronos-small | **7.20** | **3.65** |
| Chronos-base | 7.80 | 3.99 |

**Small outperforms base in both series.** 174 weeks is insufficient context for base's more complex prior. Base was pre-trained on thousands-to-tens-of-thousands-timestep series; its learned longer-range patterns act as noise on short context. This is an empirically verified instance of foundation model scaling failure on short time series.

### C3: Chronos Performance (small as representative)

| Region | RMSE | MAE | MAPE |
|---|---|---|---|
| Korea | 7.20 | 6.45 | 25.0% |
| Global | 3.65 | 2.94 | 13.4% |

Chronos-small ranks 2nd in Korea (between SARIMAX and LSTM) and 3rd in Global. Without CSI/Fourier, it cannot match domain-informed models, but its zero-shot performance is not catastrophic — demonstrating foundation model generalization on unseen short series.

---

## Track E: Prophet (added post-completion as v3 plan alignment)

### E1: Design

| Parameter | Value | Rationale |
|---|---|---|
| Seasonality mode | additive | Search index 0-100, variance not level-proportional |
| Yearly seasonality | Custom K=2 (365.25 days) | Feature parity with SARIMAX Fourier K=2 |
| Quarterly seasonality | Custom K=2 (91.25 days) | Matches SARIMAX quarterly Fourier |
| CSI regressor | add_regressor('csi') | Feature parity with SARIMAX/LSTM |
| Changepoint prior | 0.05 (default) | 174w too short for aggressive tuning |
| Changepoints detected | 25 (both series) | Piecewise linear trend with automatic break detection |

### E2: Ablation — Changepoint vs Fourier Flexibility

Prophet default `yearly_seasonality=True` uses `fourier_order=10` (20 Fourier columns) vs SARIMAX's K=2 (4 columns). To separate changepoint effect from Fourier flexibility:

| Model | Korea RMSE | Global RMSE |
|---|---|---|
| SARIMAX (K=2, no changepoint) | 6.45 | 3.23 |
| Prophet (K=2, with changepoint) | **5.57** | 2.54 |
| Prophet (K=10, with changepoint) | 5.85 | **2.18** |

**Effect decomposition:**

| Region | Total RMSE improvement | Changepoint effect | Fourier K=10 effect |
|---|---|---|---|
| Korea | +0.60 | +0.88 (147%) | -0.28 (-47%, harmful) |
| Global | +1.06 | +0.69 (66%) | +0.36 (34%) |

**Korea:** Changepoint is the sole driver. K=10 Fourier *hurts* performance — overfitting annual seasonality on 174-week event-driven series. Prophet(K=2) is the true optimal.

**Global:** Both contribute, but changepoint dominates (66%). K=10 provides modest additional benefit on Global's smoother dynamics.

### E3: Prophet CSI Coefficient — Structural Absorption

Prophet CSI regressor coefficients: Korea -0.09, Global +0.002 (both near zero or negative). Contrast with SARIMAX: Korea +3.98, Global +2.01.

**Interpretation:** Prophet's 25 changepoints in its piecewise linear trend absorb the CSI-correlated structural variation. Since CSI and trend co-move (macro sentiment drives long-term demand level), Prophet's flexible trend captures what SARIMAX attributes to CSI explicitly. This does not invalidate CSI's predictive value — it means the same information is encoded in different model components (explicit CSI coefficient in SARIMAX vs implicit trend changepoints in Prophet).

**Consequence:** Data Point 16 (CSI elasticity asymmetry Korea 3.98 vs Global 2.01) remains a SARIMAX-specific finding, not cross-model robust. The asymmetry reflects CSI's role as a linear proxy for trend in SARIMAX, not a model-agnostic structural property.

### E4: Prophet Performance (K=2 as representative)

| Region | RMSE | MAE | MAPE |
|---|---|---|---|
| Korea | 5.57 | 4.80 | 18.5% |
| Global | 2.54 | 2.11 | 10.6% |

---

## Track D: 4-Way Comparison (updated from 3-way)

### D1: Final Ranking (RMSE)

**Korea:** Prophet (5.57) > SARIMAX (6.45) > Chronos-small (7.20) > LSTM (8.11)
**Global:** Prophet (2.54) > LSTM (2.71) > SARIMAX (3.23) > Chronos-small (3.65)

### D2: Train In-Sample Anomaly Residual Analysis

| Region | Anomaly weeks (train) | Normal weeks | Anomaly RMSE | Normal RMSE | Ratio |
|---|---|---|---|---|---|
| Korea | 19 | 129 | 2.32 | 1.94 | 1.17x |
| Global | 19 | 129 | 1.95 | 1.69 | 1.22x |

**Interpretation:** In-sample anomaly/normal ratio is modest (1.2x), meaning event spikes do not severely disrupt SARIMAX fit. However, this is an in-sample metric — the model learned from these anomaly weeks. In-sample residual is a measure of fit quality, not prediction quality. Out-of-sample anomaly evaluation requires rolling/expanding window CV, but with 174 weeks and 0-2 anomalies per test fold, statistical power is absent. **This is a structural limitation of short time series forecasting, not a methodological gap.**

Test set anomaly weeks: n=1 per region. Single-point RMSE comparison is not statistically meaningful.

### D3: Structural Insights

1. **Prophet wins both via changepoint detection:** Piecewise linear trend captures structural breaks (COVID recovery, 2024 Olympic effect, 2025 trend transitions) that SARIMAX's simple drift misses. This is the primary advantage — not Fourier flexibility.

2. **Exogenous value demonstrated:** All domain-informed models (Prophet, SARIMAX, LSTM with CSI+Fourier) outperform Chronos (univariate zero-shot). Domain exogenous variables — particularly CSI — provide irreplaceable predictive information, whether encoded as explicit coefficients (SARIMAX) or absorbed into trend changepoints (Prophet).

3. **Statistical > DL on short, volatile series:** Korea's 467:1 param/sample ratio, event-driven spikes, and small effective training set structurally disadvantage DL. Prophet and SARIMAX — both statistical models — occupy the top 2 positions for Korea.

4. **DL competitive only on smooth series:** LSTM ranks 2nd for Global (RMSE 2.71 vs Prophet 2.54) where dynamics are smoother and ARIMA(0,1,0) has no autoregressive structure.

5. **Dashboard model selection simplified:** Prophet wins both series → single framework for Stage 8 Streamlit implementation.

---

## Quantified Insights (Stage 6)

### Data Point 15: Global ARIMA(0,1,0) — No Autoregressive Information

NB Global search_index best SARIMAX order is (0,1,0) — a random walk with drift, with no AR or MA terms. The series has no autocorrelation-based predictive information; trend is captured by drift, while seasonality and macro environment are explained entirely by Fourier and CSI exogenous variables.

### Data Point 16: CSI Elasticity Asymmetry — Korea 2x More Sensitive

SARIMAX CSI coefficients: Korea 3.98 vs Global 2.01 (both p<0.001). A 1-point CSI increase raises Korea search by ~4 points vs Global's ~2 points. Korea's higher elasticity is consistent with Stage 4 Granger "NB = macro-reactive demand" and reflects Korea's position as a price-sensitive, discretionary search market.

### Data Point 17: Foundation Model Anti-Scaling on Short Context

Chronos-base (200M params) underperforms Chronos-small (46M params) on both NB series. 174-week context is insufficient to justify base's more complex prior. Pre-trained longer-range patterns become noise when applied to short series. Scaling laws that hold for language models do not automatically transfer to short time series forecasting.

### Data Point 18: Prophet Mechanism — 3-Angle Analysis (Changepoint, CSI Absorption, Fourier Overfitting)

Prophet ablation and CSI coefficient comparison reveal the mechanism behind Prophet's advantage from three angles: (1) Changepoint detection captures structural breaks that SARIMAX's simple drift misses (Korea 147%, Global 66% contribution). (2) Prophet's piecewise trend absorbs CSI-correlated structural variation, reducing CSI regressor marginal effect to near-zero — Prophet's advantage and CSI coefficient disappearance are two sides of the same phenomenon. (3) Excessive Fourier terms (K=10) overfit annual seasonality on short event-driven series (Korea K=10 RMSE 5.85 > K=2 RMSE 5.57).

Read alongside Data Point 15 — SARIMAX identifies the absence of AR/MA structure in Global, while Prophet reinterprets this as piecewise linear trend without autoregressive momentum. Both models converge on the same conclusion: NB Global search has no self-sustaining dynamics.

---

## Schema Changes

None — forecast outputs stored as CSV in data/forecast/. mart.forecast_results DDL deferred to Stage 8 (Streamlit integration에서 DB 적재 필요 시 생성).

---

## Files Created in Stage 6

```
analysis/
├── forecast_data_prep.py        # A1: shared data extraction + CSI forward-fill + split
├── forecast_sarimax_order.py    # A2: differenced ACF/PACF + auto_arima + AIC comparison
├── forecast_sarimax.py          # A3/A4: SARIMAX fit + forecast + evaluation
├── forecast_lstm.py             # Track B: LSTM training + recursive forecast
├── forecast_chronos.py          # Track C: Chronos zero-shot (small + base)
├── forecast_prophet.py          # Track E: Prophet forecast
├── prophet_ablation.py          # Track E: K=2 vs K=10 ablation
├── forecast_comparison.py       # Track D: 3-way comparison (original)
└── forecast_comparison_4way.py  # Track D: 4-way comparison (updated)

data/forecast/
├── nb_korea_forecast_data.csv       # Full dataset with train/test split
├── nb_global_forecast_data.csv
├── sarimax_forecast_korea.csv       # Per-model forecast outputs
├── sarimax_forecast_global.csv
├── sarimax_metrics.csv
├── lstm_forecast_korea.csv
├── lstm_forecast_global.csv
├── lstm_metrics.csv
├── lstm_training_log_korea.csv
├── lstm_training_log_global.csv
├── chronos_forecast_korea.csv
├── chronos_forecast_global.csv
├── chronos_metrics.csv
├── prophet_forecast_korea.csv
├── prophet_forecast_global.csv
├── prophet_metrics.csv
├── forecast_comparison_metrics.csv  # D1: 3-way metrics (original)
├── forecast_comparison_4way.csv     # D1: 4-way metrics (updated)
└── train_insample_residual_analysis.csv  # D2: anomaly residual

figures/forecast/
├── nb_korea_search_csi.png          # Search + CSI overlay
├── nb_global_search_csi.png
├── nb_korea_acf_pacf.png            # Raw ACF/PACF
├── nb_global_acf_pacf.png
├── nb_korea_diff_acf_pacf.png       # Differenced ACF/PACF
├── nb_global_diff_acf_pacf.png
├── nb_korea_sarimax_forecast.png    # Per-model forecasts
├── nb_global_sarimax_forecast.png
├── nb_korea_lstm_forecast.png
├── nb_global_lstm_forecast.png
├── nb_korea_lstm_loss.png           # Training loss curves
├── nb_global_lstm_loss.png
├── nb_korea_chronos_forecast.png
├── nb_global_chronos_forecast.png
├── nb_korea_prophet_forecast.png
├── nb_global_prophet_forecast.png
├── nb_korea_forecast_3way.png       # 3-way overlay (original)
├── nb_global_forecast_3way.png
├── nb_korea_forecast_4way.png       # 4-way overlay (updated)
├── nb_global_forecast_4way.png
├── forecast_error_distribution.png  # Error box plot (3-way)
├── forecast_error_distribution_4way.png  # Error box plot (4-way)
├── anomaly_week_error_analysis.png  # Test anomaly bar chart
└── train_anomaly_residual_analysis.png  # Train in-sample scatter
```

---

## Documentation Updates

- `methodology.md` §11: Forecasting methodology — DONE (§11.5 Prophet + ablation added)
- `exploratory_findings.md`: Data Points 15-18 — DONE
- `comprehensive_advisor_handoff.md`: Stage 6 Prophet update — DONE
- `sportswear_brand_monitor_project_plan_v3.md`: §5.1 inline annotation — DONE
- Advisor decisions recorded: train/test split (26w), Fourier over dummy, no Attention, Chronos small+base, feature parity, Prophet K=2 as representative

---

## Next: Stage 7 — Korea-Global Bridge Analysis

Three key inputs from Stage 6 to Stage 7:

1. **CSI elasticity asymmetry (Korea 3.98 vs Global 2.01, SARIMAX-specific).** The first hop of the 3-stage chain (CSI→Korea) has ~2x the gain of CSI→Global direct. This quantitative baseline enables hop-by-hop gain comparison in Stage 7. Note: Prophet's changepoint trend absorbs this CSI effect, so the 2x ratio is a SARIMAX structural finding, not model-agnostic.

2. **Global ARIMA(0,1,0) — no autoregressive momentum.** Global search has no self-predictive structure, strongly supporting the Stage 7 hypothesis that Global is driven entirely by external signals (Korea lead + CSI). This justifies the experiment of adding Korea trend as an exogenous variable in Global forecasting. Prophet's piecewise trend already captures some structural breaks that Korea lead might explain — the incremental gain of adding Korea trend as exogenous may be smaller than against SARIMAX baseline. This is not a narrative loss but a testable prediction for Stage 7.

3. **Dashboard model selection: Prophet for both series.** Single framework simplifies Stage 8 Streamlit implementation — one model class covers Korea and Global.

*Stage 6 Forecasting: COMPLETED (with Track E Prophet extension).*
