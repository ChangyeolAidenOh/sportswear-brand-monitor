"""
Tab 5: Forecast & Bridge — Korea Prophet (left) + chain diagram (right).
KPI coverage: 6 (CSI MA, cross-ref), 7 (Global trend MA, right panel),
              10 (CSI elasticity, cross-ref), 11 (Prophet baseline 26w).
Design: Left panel = Korea Prophet forecast (CSI exogenous only).
        Right panel = chain_diagram visualization + Global trend MA overlay.
        Operational asymmetry: right panel is monitoring reference,
        NOT forecast model input. This distinction is surfaced in tooltip.
Usage: tab5_forecast_bridge.render() called from app.py
"""

# third-party
import streamlit as st


# ================================================================
# Render
# ================================================================
def render():
    """Render Tab 5 content."""
    st.header("Forecast & Bridge")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Korea Prophet Forecast")
        st.info(
            "Stage 8.5 — Prophet 26-week forecast with CSI exogenous. "
            "Global lagged signal explicitly excluded (RMSE degradation)."
        )
        st.markdown("**KPI coverage:** KPI 11 (Prophet Baseline 26w), KPI 6 (CSI MA)")

    with col_right:
        st.subheader("Korea-Global Bridge")
        st.info(
            "Stage 8.5 — chain_diagram_data.json visualization + "
            "Global trend 4-week MA overlay. Monitoring reference only."
        )
        st.markdown(
            "**KPI coverage:** KPI 7 (Global Trend MA — monitoring O / predictive X)"
        )
        st.caption(
            "Global signal is a directional reference for Korea demand anticipation "
            "(~10 week lead). Not a predictive input for the forecast model. "
            "Prophet -9.0% / SARIMAX -10.9% RMSE degradation when added as regressor."
        )
