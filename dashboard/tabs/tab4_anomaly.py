"""
Tab 4: Anomaly — 3-way anomaly detection, event stacking, sentiment.
KPI coverage: 4 (NB sentiment, cross-ref), 8 (event stacking density),
              9 (anomaly method agreement).
Usage: tab4_anomaly.render() called from app.py
"""

# third-party
import streamlit as st


# ================================================================
# Render
# ================================================================
def render():
    """Render Tab 4 content."""
    st.header("Anomaly")
    st.info(
        "Stage 8.4 — 3-way anomaly comparison (Z-score / MSTL / IF), "
        "event stacking, and sentiment cross-reference will be implemented here."
    )

    st.markdown(
        "**KPI coverage:** "
        "KPI 4 (NB Sentiment), "
        "KPI 8 (Event Stacking Density), "
        "KPI 9 (Anomaly Method Agreement)"
    )
