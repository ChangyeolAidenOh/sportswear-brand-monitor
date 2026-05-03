"""
Tab 1: Weekly KPI Summary — NB Korea search demand WoW, SoV%, Top/Bottom.
KPI coverage: 1 (530 dependency), 2 (D2C search), 3 (category gap),
              5 (search-sentiment gap), 6 (CSI MA), 10 (CSI elasticity).
Usage: tab1_weekly_kpi.render() called from app.py
"""

# third-party
import streamlit as st


# ================================================================
# Render
# ================================================================
def render():
    """Render Tab 1 content."""
    st.header("Weekly KPI Summary")
    st.info("Stage 8.1 — KPI cards and weekly trend charts will be implemented here.")

    st.markdown("**KPI coverage:**")
    st.markdown(
        "KPI 1 (530 Dependency Ratio), "
        "KPI 2 (D2C Search Trend), "
        "KPI 3 (Category Gap), "
        "KPI 5 (Search-Sentiment Gap), "
        "KPI 6 (CSI MA), "
        "KPI 10 (CSI Elasticity 3.98)"
    )
