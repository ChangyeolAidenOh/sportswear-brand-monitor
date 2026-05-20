"""
Tab 3: Channel — search type mix, Korea vs Global divergence, over-index.
KPI coverage: 2 (D2C search trend, cross-ref with Tab 1).
Data sources: mart.korea_global_comparison, staging.search_weekly (search_type).
Usage: tab3_channel.render() called from app.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from dashboard.config import (
    BRAND_COLORS, BRAND_LABELS, BRAND_LINE_OPACITY,
    CHART_FONT, CHART_AXIS_TICKFONT, CHART_LEGEND_FONT, CHART_TITLE_FONT,
)
from dashboard.data.queries import (
    fetch_brand_kpi,
    fetch_korea_global_comparison,
)


# Data loading (cached)
@st.cache_data(ttl=600)
def load_brand_kpi():
    """Load and cache brand KPI data."""
    return fetch_brand_kpi()


@st.cache_data(ttl=600)
def load_korea_global():
    """Load and cache Korea vs Global comparison data."""
    return fetch_korea_global_comparison()


# Chart builders
def _build_korea_global_trend(df, metric="search_index"):
    """Build Korea vs Global dual-axis trend for NB."""
    nb = df[
        (df["brand"] == "new_balance") & (df["metric_name"] == metric)
    ].sort_values("week_start")

    if nb.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nb["week_start"], y=nb["korea_value"],
        name="Korea",
        line=dict(color="#E63946", width=2.5),
        hovertemplate="Korea: %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=nb["week_start"], y=nb["global_value"],
        name="Global",
        line=dict(color="#C44569", width=2, dash="dot"),
        hovertemplate="Global: %{y:.1f}<extra></extra>",
    ))

    title_map = {
        "search_index": "NB Search Index",
        "sov_pct": "NB Share of Voice",
    }
    fig.update_layout(
        title=dict(text=f"Korea vs Global — {title_map.get(metric, metric)}", font=CHART_TITLE_FONT),
        xaxis_title="",
        yaxis_title=metric.replace("_", " ").title(),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15, font=CHART_LEGEND_FONT),
        font=CHART_FONT,
        xaxis=dict(tickfont=CHART_AXIS_TICKFONT),
        yaxis=dict(tickfont=CHART_AXIS_TICKFONT),
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_divergence_chart(df, metric="search_index"):
    """Build Korea over-index divergence chart."""
    nb = df[
        (df["brand"] == "new_balance") & (df["metric_name"] == metric)
    ].sort_values("week_start")

    if nb.empty or "divergence_pct" not in nb.columns:
        return None

    fig = go.Figure()
    colors = ["#E74C3C" if v >= 0 else "#3498DB" for v in nb["divergence_pct"]]

    fig.add_trace(go.Bar(
        x=nb["week_start"], y=nb["divergence_pct"],
        marker_color=colors,
        hovertemplate="%{x|%Y-%m-%d}: %{y:+.1f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="white", line_width=0.5)

    fig.update_layout(
        title=dict(text=f"Korea Over-Index — {metric.replace('_', ' ').title()} Divergence %", font=CHART_TITLE_FONT),
        xaxis_title="",
        yaxis_title="Divergence %",
        font=CHART_FONT,
        xaxis=dict(tickfont=CHART_AXIS_TICKFONT),
        yaxis=dict(tickfont=CHART_AXIS_TICKFONT),
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_sov_comparison_chart(df_kpi):
    """Build 4-brand SoV comparison — Korea vs Global latest snapshot."""
    if df_kpi is None or df_kpi.empty:
        return None

    latest_week = df_kpi["week_start"].max()
    latest = df_kpi[df_kpi["week_start"] == latest_week].copy()

    brands = ["new_balance", "nike", "adidas", "puma"]
    korea_sov = []
    global_sov = []

    for b in brands:
        kr = latest[(latest["brand"] == b) & (latest["region"] == "korea")]
        gl = latest[(latest["brand"] == b) & (latest["region"] == "global")]
        kr_val = kr["sov_pct"].iloc[0] if not kr.empty else 0
        gl_val = gl["sov_pct"].iloc[0] if not gl.empty else 0
        # Convert if stored as fraction
        if kr_val <= 1:
            kr_val *= 100
        if gl_val <= 1:
            gl_val *= 100
        korea_sov.append(kr_val)
        global_sov.append(gl_val)

    labels = [BRAND_LABELS.get(b, b) for b in brands]
    colors = [BRAND_COLORS.get(b, "#888") for b in brands]
    # Per-brand base opacity (NB full, competitors muted)
    base_opacity = [BRAND_LINE_OPACITY.get(b, 0.70) for b in brands]

    fig = go.Figure()
    # Korea: solid fill
    fig.add_trace(go.Bar(
        name="Korea (solid)", x=labels, y=korea_sov,
        marker=dict(color=colors, opacity=base_opacity),
        text=[f"{v:.1f}%" for v in korea_sov], textposition="inside",
    ))
    # Global: same color but pattern fill (diagonal stripes)
    fig.add_trace(go.Bar(
        name="Global (striped)", x=labels, y=global_sov,
        marker=dict(
            color=colors,
            opacity=base_opacity,
            pattern=dict(shape="/", size=8, solidity=0.4, fgcolor="white"),
        ),
        text=[f"{v:.1f}%" for v in global_sov], textposition="inside",
    ))

    fig.update_layout(
        title=dict(text=f"SoV Comparison — Korea vs Global (Week of {latest_week.strftime('%Y-%m-%d')})", font=CHART_TITLE_FONT),
        yaxis_title="SoV %",
        barmode="group",
        legend=dict(orientation="h", y=-0.15, font=CHART_LEGEND_FONT),
        font=CHART_FONT,
        xaxis=dict(tickfont=CHART_AXIS_TICKFONT),
        yaxis=dict(tickfont=CHART_AXIS_TICKFONT),
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_product_divergence_chart(df):
    """Build product-level Korea vs Global divergence snapshot."""
    if df is None or df.empty:
        return None

    product_metrics = df[
        df["metric_name"].str.startswith("product_")
    ].copy()

    if product_metrics.empty:
        return None

    latest_week = product_metrics["week_start"].max()
    latest = product_metrics[product_metrics["week_start"] == latest_week].copy()

    if latest.empty:
        return None

    latest["product"] = latest["metric_name"].str.replace("product_", "").str.replace("_share", "")
    latest = latest.sort_values("divergence_pct", ascending=True)

    colors = ["#E74C3C" if v >= 0 else "#3498DB" for v in latest["divergence_pct"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=latest["divergence_pct"],
        y=latest["product"].astype(str),
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in latest["divergence_pct"]],
        textposition="outside",
    ))

    fig.update_layout(
        title=dict(text="Product Divergence — Korea vs Global (Latest Week)", font=CHART_TITLE_FONT),
        xaxis_title="Divergence % (positive = Korea over-index)",
        yaxis=dict(type="category", tickfont=CHART_AXIS_TICKFONT),
        xaxis=dict(tickfont=CHART_AXIS_TICKFONT),
        font=CHART_FONT,
        height=300,
        margin=dict(l=80, r=60, t=50, b=40),
    )
    return fig


# Render
def render():
    """Render Tab 3 content."""
    st.header("Channel")

    df_kpi = load_brand_kpi()
    df_kg = load_korea_global()

    # -- SoV comparison (Korea vs Global)
    if df_kpi is not None and not df_kpi.empty:
        fig_sov = _build_sov_comparison_chart(df_kpi)
        if fig_sov:
            st.plotly_chart(fig_sov, width="stretch", key="sov_comparison")

    st.markdown("---")

    if df_kg is None or df_kg.empty:
        st.warning("Korea vs Global comparison data not available.")
        return

    # -- Korea vs Global trend + divergence
    metric = st.radio(
        "Metric", ["search_index", "sov_pct"], horizontal=True,
        format_func=lambda x: "Search Index" if x == "search_index" else "SoV %",
        key="tab3_metric",
    )

    col_trend, col_div = st.columns(2)

    with col_trend:
        fig_trend = _build_korea_global_trend(df_kg, metric=metric)
        if fig_trend:
            st.plotly_chart(fig_trend, width="stretch", key="kg_trend")

    with col_div:
        fig_div = _build_divergence_chart(df_kg, metric=metric)
        if fig_div:
            st.plotly_chart(fig_div, width="stretch", key="kg_divergence")

    # -- Product divergence
    fig_prod = _build_product_divergence_chart(df_kg)
    if fig_prod:
        st.plotly_chart(fig_prod, width="stretch", key="product_divergence")

    # -- Key finding callout
    with st.expander("Channel Findings Summary"):
        st.markdown(
            "**NB Korea Over-Index:** Korea search +34.9%, SoV +16.4% vs Global.  \n"
            "**574 = Cross-Region Anchor:** Divergence +82.3% (Korea values 574 more).  \n"
            "**2002r Gap:** Korea divergence -85.0% (Korea barely searches 2002r).  \n"
            "**D2C Declining:** Official mall search slope -0.191/week (p < 0.00001).  \n"
            "**Shopping Share:** NB 4.5% vs Nike 32.1% — NB consumers use app-direct (Musinsa, Coupang)."
        )
