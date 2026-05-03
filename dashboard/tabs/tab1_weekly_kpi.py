"""
Tab 1: Weekly KPI Summary — NB Korea search demand WoW, SoV%, Top/Bottom.
KPI coverage: 1 (530 dependency), 2 (D2C search), 3 (category gap),
              5 (search-sentiment gap), 6 (CSI MA), 10 (CSI elasticity).
Usage: tab1_weekly_kpi.render() called from app.py
"""

# third-party
import streamlit as st
import plotly.graph_objects as go

# local
from dashboard.config import BRAND_COLORS, BRAND_LABELS
from dashboard.data.queries import fetch_brand_kpi, fetch_product_portfolio, fetch_csi_macro
from dashboard.components.kpi_card import render_kpi_row
from dashboard.components.tooltip import render_tooltip


# ================================================================
# Data loading (cached)
# ================================================================
@st.cache_data(ttl=600)
def load_brand_kpi():
    """Load and cache brand KPI data."""
    return fetch_brand_kpi()


@st.cache_data(ttl=600)
def load_product_portfolio():
    """Load and cache product portfolio data."""
    return fetch_product_portfolio()


@st.cache_data(ttl=600)
def load_csi():
    """Load and cache CSI macro data."""
    return fetch_csi_macro()


# ================================================================
# KPI card helpers
# ================================================================
def _format_pct(val):
    """Format a percentage value for display."""
    if val is None:
        return "N/A"
    return f"{val:+.1f}%"


def _get_latest_nb_korea(df):
    """Extract latest week NB Korea metrics."""
    if df is None or df.empty:
        return None
    nb_korea = df[(df["brand"] == "new_balance") & (df["region"] == "korea")]
    if nb_korea.empty:
        return None
    return nb_korea.sort_values("week_start").iloc[-1]


def _get_530_dependency(df_prod):
    """Calculate latest 530 share within NB Korea products."""
    if df_prod is None or df_prod.empty:
        return None, None
    korea_530 = df_prod[
        (df_prod["product_line"] == "530") & (df_prod["region"] == "korea")
    ]
    if korea_530.empty:
        return None, None
    latest = korea_530.sort_values("week_start").iloc[-1]
    share = latest.get("share_within_nb_pct")
    return share, latest.get("week_start")


# ================================================================
# Chart builders
# ================================================================
def _build_search_trend_chart(df, region="korea"):
    """Build 4-brand search index line chart."""
    fig = go.Figure()
    region_df = df[df["region"] == region].copy()

    for brand in ["new_balance", "nike", "adidas", "puma"]:
        brand_df = region_df[region_df["brand"] == brand].sort_values("week_start")
        fig.add_trace(go.Scatter(
            x=brand_df["week_start"],
            y=brand_df["search_index"],
            name=BRAND_LABELS.get(brand, brand),
            line=dict(color=BRAND_COLORS.get(brand, "#888"), width=2),
            hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra></extra>",
        ))

    fig.update_layout(
        title=f"Brand Search Index — {region.title()}",
        xaxis_title="",
        yaxis_title="Search Index",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_sov_chart(df, region="korea"):
    """Build SoV stacked area chart."""
    fig = go.Figure()
    region_df = df[df["region"] == region].copy()

    for brand in ["new_balance", "nike", "adidas", "puma"]:
        brand_df = region_df[region_df["brand"] == brand].sort_values("week_start")
        sov_vals = brand_df["sov_pct"] * 100 if brand_df["sov_pct"].max() <= 1 else brand_df["sov_pct"]
        fig.add_trace(go.Scatter(
            x=brand_df["week_start"],
            y=sov_vals,
            name=BRAND_LABELS.get(brand, brand),
            stackgroup="sov",
            line=dict(color=BRAND_COLORS.get(brand, "#888"), width=0),
            hovertemplate="%{y:.1f}%<extra></extra>",
        ))

    fig.update_layout(
        title=f"Share of Voice — {region.title()}",
        xaxis_title="",
        yaxis_title="SoV %",
        yaxis=dict(range=[0, 100]),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_530_dependency_chart(df_prod):
    """Build 530 dependency ratio line chart over time."""
    korea_530 = df_prod[
        (df_prod["product_line"] == "530") & (df_prod["region"] == "korea")
    ].sort_values("week_start")

    if korea_530.empty:
        return None

    share_vals = korea_530["share_within_nb_pct"]
    if share_vals.max() <= 1:
        share_vals = share_vals * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=korea_530["week_start"],
        y=share_vals,
        name="530 Share",
        line=dict(color=BRAND_COLORS["new_balance"], width=2),
        fill="tozeroy",
        fillcolor="rgba(231, 76, 60, 0.1)",
        hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}%<extra></extra>",
    ))

    # Alert threshold line at 60%
    fig.add_hline(
        y=60, line_dash="dash", line_color="orange",
        annotation_text="Alert: 60%", annotation_position="top right",
    )

    fig.update_layout(
        title="KPI 1: 530 Dependency Ratio — Korea",
        xaxis_title="",
        yaxis_title="530 Share within NB (%)",
        yaxis=dict(range=[0, 100]),
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


# ================================================================
# Render
# ================================================================
def render():
    """Render Tab 1 content."""
    st.header("Weekly KPI Summary")

    df_kpi = load_brand_kpi()
    df_prod = load_product_portfolio()
    df_csi = load_csi()

    # -- Check data availability
    if df_kpi is None or df_kpi.empty:
        st.warning("Brand KPI data not available. Check DB connection or CSV exports.")
        return

    # -- KPI cards row
    latest = _get_latest_nb_korea(df_kpi)
    dep_share, _ = _get_530_dependency(df_prod)

    if latest is not None:
        dep_display = f"{dep_share * 100:.1f}%" if dep_share and dep_share <= 1 else (
            f"{dep_share:.1f}%" if dep_share else "N/A"
        )
        dep_alert = None
        if dep_share:
            dep_val = dep_share * 100 if dep_share <= 1 else dep_share
            if dep_val > 60:
                dep_alert = "Above 60%"

        latest_csi = None
        if df_csi is not None and not df_csi.empty:
            latest_csi = df_csi.sort_values("year_month").iloc[-1]["csi_value"]

        wow_val = latest.get("search_wow_pct")
        sov_val = latest.get("sov_pct")
        sov_display = f"{sov_val * 100:.1f}%" if sov_val and sov_val <= 1 else (
            f"{sov_val:.1f}%" if sov_val else "N/A"
        )

        metrics = [
            {
                "label": "NB Korea Search",
                "value": f"{latest['search_index']:.1f}",
                "delta": _format_pct(wow_val * 100 if wow_val and abs(wow_val) < 1 else wow_val),
                "help_text": "NB Korea weekly search index (Google Trends)",
            },
            {
                "label": "NB Korea SoV",
                "value": sov_display,
                "help_text": "NB share of 4-brand total search volume",
            },
            {
                "label": "530 Dependency",
                "value": dep_display,
                "delta": dep_alert,
                "delta_color": "inverse" if dep_alert else "normal",
                "help_text": render_tooltip("csi_elasticity"),
            },
            {
                "label": "CSI (Latest)",
                "value": f"{latest_csi:.1f}" if latest_csi else "N/A",
                "help_text": render_tooltip("csi_elasticity"),
            },
        ]

        render_kpi_row(metrics, cols_per_row=4)

    st.markdown("---")

    # -- Region selector
    region = st.radio(
        "Region", ["korea", "global"], horizontal=True, key="tab1_region"
    )

    # -- Search trend chart
    st.plotly_chart(
        _build_search_trend_chart(df_kpi, region),
        width="stretch",
        key="search_trend",
    )

    # -- SoV chart + 530 dependency side by side
    col_sov, col_dep = st.columns(2)

    with col_sov:
        st.plotly_chart(
            _build_sov_chart(df_kpi, region),
            width="stretch",
            key="sov_chart",
        )

    with col_dep:
        if df_prod is not None and not df_prod.empty:
            fig_dep = _build_530_dependency_chart(df_prod)
            if fig_dep:
                st.plotly_chart(
                    fig_dep, width="stretch", key="dep_chart"
                )
        else:
            st.info("Product portfolio data not available.")

    # -- Latest week detail table
    with st.expander("Latest Week Detail — All Brands"):
        latest_week = df_kpi["week_start"].max()
        latest_df = df_kpi[
            (df_kpi["week_start"] == latest_week) & (df_kpi["region"] == region)
        ][["brand", "search_index", "sov_pct", "search_wow_pct"]].copy()

        latest_df["brand"] = latest_df["brand"].map(BRAND_LABELS).fillna(latest_df["brand"])
        latest_df.columns = ["Brand", "Search Index", "SoV %", "WoW %"]
        st.dataframe(latest_df.reset_index(drop=True), width="stretch")
