"""
Tooltip component for Stage 7 narrative and operational context.
Usage: from dashboard.components.tooltip import render_tooltip
"""

# third-party
import streamlit as st


# ================================================================
# Tooltip definitions
# ================================================================
TOOLTIPS = {
    "monitoring_vs_predictive": (
        "Global signal serves as monitoring leading indicator "
        "(directional reference, ~10 week lead). "
        "NOT a predictive feature for Korea forecast model. "
        "Prophet -9.01% / SARIMAX -10.94% RMSE degradation "
        "when Global lagged regressor added (DM p<0.001)."
    ),
    "csi_elasticity": (
        "Korea CSI elasticity = 3.98. "
        "A 1-point CSI change corresponds to approximately "
        "3.98-point Korea search index movement."
    ),
    "sign_correction": (
        "Stage 7 DP24: Sign convention inversion detected and corrected "
        "before dashboard implementation. "
        "Migration 011 applied 2026-05-03. "
        "Original analysis preserved in stage4_checkpoint.md."
    ),
    "methodology_validation": (
        "Stage 7 is a methodology validation stage, not just a hypothesis test. "
        "4-layer narrative: 5-dim null (Layer 1) -> self-diagnostic chain (Layer 2) "
        "-> quantitative signatures (Layer 3) -> operational refinement (Layer 4)."
    ),
}


# ================================================================
# Render helper
# ================================================================
def render_tooltip(key):
    """Render a tooltip text by key. Returns the tooltip string."""
    return TOOLTIPS.get(key, "")


def render_info_expander(title, key):
    """Render an expandable info section with tooltip content."""
    text = TOOLTIPS.get(key, "")
    if text:
        with st.expander(title):
            st.markdown(text)
