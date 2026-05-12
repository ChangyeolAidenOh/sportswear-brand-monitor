"""
NB Korea BDC Monitor — Streamlit Dashboard Entry Point.
Stage 8 sportswear-brand-monitor project.
Usage: streamlit run dashboard/app.py
"""

# stdlib
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# third-party
import streamlit as st

# local
from dashboard.config import USE_CSV_FALLBACK, STYLE_CSS
from dashboard.tabs import tab1_weekly_kpi
from dashboard.tabs import tab2_season
from dashboard.tabs import tab3_channel
from dashboard.tabs import tab4_anomaly
from dashboard.tabs import tab5_forecast_bridge
from dashboard.tabs import methodology_doc

# ================================================================
# Page config
# ================================================================
st.set_page_config(
    page_title="NB Korea BDC Monitor",
    page_icon="NB",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================================================================
# Custom CSS
# ================================================================
if os.path.exists(STYLE_CSS):
    with open(STYLE_CSS, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ================================================================
# Sidebar — About + data source
# ================================================================
with st.sidebar:
    st.markdown("### NB Korea BDC Monitor")
    st.caption("Sportswear Brand Demand & Competitive Intelligence")

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        "This dashboard surfaces **13 KPIs** across 5 operational tabs "
        "and 1 methodology documentation tab, built from 23,000+ rows "
        "of public data (Naver DataLab, Google Trends, YouTube, ECOS, "
        "corporate filings)."
    )

    st.markdown("#### Stage 7 Narrative")
    st.markdown(
        "**Layer 1** — 5-dim orthogonal null x 11 tests  \n"
        "**Layer 2** — Self-diagnostic chain: DP20 -> DP23 -> DP24  \n"
        "**Layer 3** — Three quantitative signatures of DP24  \n"
        "**Layer 4** — Operational refinement: Mirror Sentinel + Differential Reactivity"
    )
    st.caption(
        "Stage 7 validated that Korea and Global demand are independently "
        "driven by CSI. Global leads Korea by ~10 weeks (monitoring only, "
        "not predictive). Full narrative: stage7_bridge_report.md"
    )

    st.markdown("---")
    st.markdown("### Data Source")
    if USE_CSV_FALLBACK:
        st.info("CSV mode (static export)")
    else:
        st.success("PostgreSQL (live)")

    st.markdown("---")
    st.caption(
        ""
        ""
    )

# ================================================================
# Main — 6-tab layout
# ================================================================
tab1, tab2, tab3, tab4, tab5, tab_method = st.tabs([
    "Weekly KPI",
    "Season",
    "Channel",
    "Anomaly",
    "Forecast & Bridge",
    "Methodology Doc",
])

with tab1:
    tab1_weekly_kpi.render()

with tab2:
    tab2_season.render()

with tab3:
    tab3_channel.render()

with tab4:
    tab4_anomaly.render()

with tab5:
    tab5_forecast_bridge.render()

with tab_method:
    methodology_doc.render()
