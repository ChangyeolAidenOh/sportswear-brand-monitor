# Stage 7 Bridge Report — Korea-Global Methodology Validation

**Project:** NB Korea BDC Sportswear Brand Monitor
**Stage:** 7 (Korea-Global Bridge Analysis)
**Date:** 2026-05-03
**Purpose:** 1-page narrative summary for interview / portfolio reference. Full methodology in `methodology.md` §12; quantitative artifacts in `stage7_checkpoint.md`.

---

## What Stage 7 Set Out To Do

Stages 0–6 produced converging evidence — Stage 0 H1 cross-correlation, Stage 4 trend DTW + CC, Stage 5 anomaly density asymmetry, Stage 6 CSI elasticity gap — pointing at a 3-stage chain hypothesis: **CSI → NB Korea Search → NB Global Search**. Stage 7 was designed to formally verify this chain through bidirectional VARX, mediation, and cointegration analysis at weekly resolution.

## What Stage 7 Found

The chain hypothesis was rejected, but the rejection itself is not the story.

**Layer 1 — 5-Dimension Orthogonal Null × 11 Tests.** The verification spanned five methodological dimensions: VARX bidirectional Granger, monthly Granger bidirectional, mediation bidirectional × two transformations (trend + diff1), and lagged cointegration bidirectional. Eleven individual tests, all rejecting the chain. CSI directly and independently drives both Korea and Global search demand; neither region mediates the other. This is the most thoroughly verified null hypothesis in the project — the breadth of evidence eliminates single-test false-negative possibilities.

**Layer 2 — Self-Diagnostic Chain (DP20 → DP23 → DP24).** The verification process itself surfaced three critical findings, each detected through internal sanity checks without external review:

- **DP20 — Mediation spurious correlation pre-emption.** Step 0 stationarity re-check identified that monthly-aggregated trend regressions would produce spurious mediation coefficients regardless of true causal structure. Diff1 robustness specifications were committed pre-execution, preventing post-hoc result chasing.

- **DP23 — MSTL forward-looking leakage.** A narrative-negative Track A3 result (Korea trend exogenous degrading Prophet RMSE +59%) triggered self-diagnostic that revealed `statsmodels.MSTL` uses a two-sided STL filter, leaking future information into the trend component. Track A3 was invalidated as a result; replication framework established.

- **DP24 — Stage 4 sign convention inversion.** Leakage-free DTW + CC re-computation produced direction-flipped results relative to Stage 4 labels. A synthetic Korea-leads-by-5w probe confirmed: Stage 4 code returns CC −5, DTW −4.57. Magnitude correct, sign convention inverted. Cascade applied through DP9 / DP21 / DP22 / KPI 7.

**Layer 3 — Three Quantitative Signatures of Sign Correction Validity.** DP24 was not asserted on a single test. Three independent quantitative signatures stack:

1. *Inconsistent mediation signature dissipates.* % indirect effect 120.35% → 10.82% under sign correction.
2. *BCa CI width narrows 47%.* Trend MBB CI [−0.39, +0.18] → [−0.12, +0.18], same data, same bootstrap, same parameters.
3. *Track A3 degradation magnitude reduces 1/4–1/5.* Korea→Global pre-correction Prophet/SARIMAX +41/+59% → Global→Korea post-correction +9/+11%. Sign correction removes both DP23 leakage amplification and direction misspecification interference.

These signatures are observable only when point estimate aligns with true direction. Their joint dissipation is the strongest quantitative anchor for Stage 4 sign convention error.

**Layer 4 — Operational Refinement (Mirror Sentinel + Differential Reactivity).** Sign correction inverts the BDC sentinel framing direction without abandoning it. **Global precedes Korea by ~10 weeks** (DTW + CC, sign-corrected); the BDC role of Korea ↔ Global translator is preserved. The mechanism — three plausible hypotheses (Global brand attention precedence, HQ marketing trigger, differential reactivity to common drivers) — remains testable only with BDC internal data, defining the project-vs-in-role boundary.

Track A3 sign-corrected re-design produced a fourth quantitative refinement: Global signal as forecast feature **degrades** Korea forecast in both Prophet (−9.01%) and SARIMAX (−10.94%, both DM p<0.001). The operational distinction:

- **Monitoring indicator** (preserved): Global trend MA → Korea demand directional reference, dashboard right panel
- **Predictive feature** (newly explicit): NOT used in forecast model, active interference detected

This operational asymmetry between visualization and prediction propagates directly to Stage 8 dashboard design.

---

## Why This Matters For BDC Roles

The interview narrative is not "I found a 3-stage chain that turned out to be null." It is:

> "I designed a 5-dimensional verification that detected three critical findings in my own analytical pipeline — including a sign convention error in earlier stages — without external review. The detection chain was DP20 (pre-emption design) → DP23 (self-diagnostic) → DP24 (verification byproduct). These are the analytical governance protocols transferable to enterprise contexts where external review is rare."

KPI 12 (5-Dimension Orthogonal Null Verification Pattern) and KPI 13 (Methodology Validation Stage Pattern) explicitly index these as governance assets for future analyses. The Stage 4 sign correction was caught before Stage 8 dashboard implementation, not after — timing matters for the credibility of the self-skepticism claim.

---

## Stage 8 Handoff

The dashboard implementation honors the operational refinement:

1. **Korea Prophet forecast** — CSI exogenous only, Global lagged signal explicitly excluded
2. **Bridge tab right panel** — `chain_diagram_data.json` rendering with sign-corrected direction labels and `operational_use` metadata distinguishing monitoring vs predictive scope
3. **KPI 7 dual surface** — Streamlit Forecast tab Global trend MA overlay + Power BI HQ Bridge summary card with "Korea demand directional reference — not predictive input" caption
4. **Migration 011 applied** (2026-05-03) — `mart.korea_global_lag` 12 rows sign-flipped + labels swapped; Stage 8 queries this table directly with no further translation logic

Trace preservation: `stage4_checkpoint.md` retains original analysis with Sign Correction Notice footnote.

---

## Cross-references

- Full quantitative artifacts: `stage7_checkpoint.md`
- Methodology source-of-truth: `methodology.md` §12
- Data Points: `exploratory_findings.md` DP19 (5-dim null), DP20 (pre-emption), DP21 (3-dim separation), DP22 [DEPRECATED 2026-05-03], DP23 (MSTL leakage), DP24 (sign inversion)
- Database retrofit: `database/migrations/011_korea_global_lag_sign_correction.sql`
- Visualization: `figures/bridge/chain_summary.png`

*Stage 7 closing narrative: methodology validation stage. Hypothesis test result is one finding among four governance findings.*
