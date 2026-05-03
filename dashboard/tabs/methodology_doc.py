"""
Methodology Documentation tab — governance assets (KPI 12, 13).
Not operational metrics. Separated from Tabs 1-5 by design.
KPI 12: 5-Dimension Orthogonal Null Verification Pattern
KPI 13: Methodology Validation Stage Pattern (DP20 -> DP23 -> DP24)
Usage: methodology_doc.render() called from app.py
"""

# third-party
import streamlit as st


# ================================================================
# Content constants
# ================================================================
KPI_12_TITLE = "KPI 12: 5-Dimension Orthogonal Null Verification Pattern"
KPI_12_BODY = """
**Default protocol for cross-region / cross-channel hypothesis testing.**

Framework: VARX bidirectional + monthly Granger bidirectional + \
trend mediation bidirectional + diff1 mediation bidirectional + \
lagged cointegration bidirectional (11 tests total).

**Why this matters:**
Single-test hypothesis verification is fragile. This 5-dimension framework \
detects false positives that any single method would miss. \
In this project, all 11 tests independently rejected the Korea-Global \
chain hypothesis — convergent evidence that no single test could provide alone.

**Transferability:**
Any enterprise analytics team testing causal chain hypotheses \
(e.g., "does regional demand drive global demand?") can adopt this \
11-test framework as a default verification protocol.
"""

KPI_13_TITLE = "KPI 13: Methodology Validation Stage Pattern"
KPI_13_BODY = """
**Default self-diagnostic cascade for analytical governance.**

Pattern: DP20 (pre-emption design) -> DP23 (self-diagnostic) -> \
DP24 (verification byproduct critical finding).

**Three-stage cascade:**
1. **DP20 — Pre-emption:** Mediation spurious correlation pre-emption \
design (Step 0 before Track A).
2. **DP23 — Self-diagnostic:** MSTL forward-looking leakage detection \
during Track A3 narrative-negative result investigation.
3. **DP24 — Verification byproduct:** Stage 4 sign convention inversion \
discovered as byproduct of DP23 leakage-free re-analysis.

**Why this matters:**
All three findings were detected without external review. \
The detection happened before Stage 8 dashboard implementation — \
timing strengthens the self-skepticism claim. \
This cascade pattern is transferable to any enterprise context \
where external review is rare.

**Quantitative signatures of DP24:**
- Inconsistent mediation signature dissipation (% indirect 120% -> 11%)
- BCa CI 47% narrowing
- Track A3 degradation magnitude 1/4 to 1/5 reduction \
(Korea->Global +41~59% -> Global->Korea +9~11%)
"""

LAYER_NARRATIVE = """
**Stage 7 — 4-Layer Narrative Climax:**

| Layer | Content |
|:------|:--------|
| Layer 1 | 5-dim orthogonal null x 11 tests — all reject chain hypothesis |
| Layer 2 | Self-diagnostic chain: DP20 -> DP23 -> DP24 |
| Layer 3 | Three quantitative signatures of DP24 |
| Layer 4 | Operational refinement: Mirror Sentinel + Differential Reactivity |
"""


# ================================================================
# Render
# ================================================================
def render():
    """Render Methodology Documentation tab content."""
    st.header("Methodology Documentation")
    st.caption("Governance assets — not operational metrics (KPI 12, 13)")

    st.markdown("---")
    st.subheader(KPI_12_TITLE)
    st.markdown(KPI_12_BODY)

    st.markdown("---")
    st.subheader(KPI_13_TITLE)
    st.markdown(KPI_13_BODY)

    st.markdown("---")
    st.subheader("Stage 7 Narrative Summary")
    st.markdown(LAYER_NARRATIVE)
    st.caption(
        "Full narrative: docs/stage7_bridge_report.md | "
        "Quantitative artifacts: stage7_checkpoint.md | "
        "Methodology source: methodology.md section 12"
    )
