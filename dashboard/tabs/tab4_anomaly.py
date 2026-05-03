"""
Tab 4: Anomaly — 3-way anomaly detection, event stacking, method agreement.
KPI coverage: 4 (NB sentiment, cross-ref), 8 (event stacking density),
              9 (anomaly method agreement).
Data: mart.anomaly_log (detected_date, no region column — parsed from description).
Usage: tab4_anomaly.render() called from app.py
"""

# third-party
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# local
from dashboard.config import BRAND_COLORS, BRAND_LABELS
from dashboard.data.queries import fetch_anomaly_log, fetch_events_calendar


# ================================================================
# Data loading (cached)
# ================================================================
@st.cache_data(ttl=600)
def load_anomaly_log():
    """Load anomaly log and extract region from description."""
    df = fetch_anomaly_log()
    if df is None or df.empty:
        return None
    # Extract region from description (e.g., "global: search_index dip")
    df["region"] = df["description"].str.extract(r"^(korea|global):", expand=False)
    df["region"] = df["region"].fillna("unknown")
    return df


@st.cache_data(ttl=600)
def load_events():
    """Load and cache events calendar."""
    return fetch_events_calendar()


# ================================================================
# Chart builders
# ================================================================
def _build_anomaly_timeline(df, brand="new_balance", region="korea"):
    """Build anomaly detection timeline — dots colored by method."""
    subset = df[
        (df["brand"] == brand) & (df["region"] == region)
    ].copy()

    if subset.empty:
        return None

    method_colors = {
        "rolling_zscore_8w": "#E74C3C",
        "mstl_residual_2.0": "#3498DB",
        "mstl_residual_3.0": "#1A5276",
        "isolation_forest": "#2ECC71",
    }

    short_names = {
        "rolling_zscore_8w": "Z-score 8w",
        "mstl_residual_2.0": "MSTL 2.0",
        "mstl_residual_3.0": "MSTL 3.0",
        "isolation_forest": "Isolation Forest",
    }

    fig = go.Figure()
    for method in sorted(subset["detection_method"].unique()):
        m_df = subset[subset["detection_method"] == method].sort_values("detected_date")
        label = short_names.get(method, method)

        # Size by severity
        sizes = m_df["severity_score"].fillna(1).clip(lower=1) * 5

        fig.add_trace(go.Scatter(
            x=m_df["detected_date"],
            y=[label] * len(m_df),
            mode="markers",
            name=label,
            marker=dict(
                color=method_colors.get(method, "#888"),
                size=sizes,
            ),
            customdata=m_df[["anomaly_type", "z_score", "description"]].values,
            hovertemplate=(
                "%{x|%Y-%m-%d}<br>"
                "Type: %{customdata[0]}<br>"
                "Z-score: %{customdata[1]:.2f}<br>"
                "%{customdata[2]}<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=f"Anomaly Timeline — {BRAND_LABELS.get(brand, brand)} ({region.title()})",
        xaxis_title="",
        yaxis_title="",
        height=300,
        margin=dict(l=120, r=20, t=50, b=40),
        showlegend=True,
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


def _build_method_agreement_chart(df):
    """Build KPI 9: monthly 3-way agreement count."""
    df = df.copy()
    df["year_month"] = df["detected_date"].dt.to_period("M").dt.to_timestamp()

    # Count methods per (brand, region, detected_date)
    agreement = df.groupby(
        ["brand", "region", "detected_date"]
    )["detection_method"].nunique().reset_index()
    agreement.columns = ["brand", "region", "detected_date", "method_count"]
    agreement["year_month"] = agreement["detected_date"].dt.to_period("M").dt.to_timestamp()

    monthly_2plus = agreement[agreement["method_count"] >= 2].groupby(
        "year_month"
    ).size().reset_index(name="agree_2plus")
    monthly_3 = agreement[agreement["method_count"] >= 3].groupby(
        "year_month"
    ).size().reset_index(name="agree_3")

    monthly = pd.merge(monthly_2plus, monthly_3, on="year_month", how="outer").fillna(0)
    monthly = monthly.sort_values("year_month")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly["year_month"], y=monthly["agree_2plus"],
        name="2+ methods agree",
        marker_color="#3498DB",
    ))
    fig.add_trace(go.Bar(
        x=monthly["year_month"], y=monthly["agree_3"],
        name="3+ methods agree",
        marker_color="#E74C3C",
    ))

    fig.update_layout(
        title="KPI 9: Anomaly Method Agreement (Monthly)",
        xaxis_title="",
        yaxis_title="Count",
        barmode="overlay",
        legend=dict(orientation="h", y=-0.15),
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_method_distribution(df):
    """Build detection method count distribution."""
    method_counts = df["detection_method"].value_counts().reset_index()
    method_counts.columns = ["method", "count"]

    method_colors = {
        "rolling_zscore_8w": "#E74C3C",
        "mstl_residual_2.0": "#3498DB",
        "mstl_residual_3.0": "#1A5276",
        "isolation_forest": "#2ECC71",
    }

    short_names = {
        "rolling_zscore_8w": "Z-score 8w",
        "mstl_residual_2.0": "MSTL 2.0",
        "mstl_residual_3.0": "MSTL 3.0",
        "isolation_forest": "IF",
    }

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[short_names.get(m, m) for m in method_counts["method"]],
        y=method_counts["count"],
        marker_color=[method_colors.get(m, "#888") for m in method_counts["method"]],
        text=method_counts["count"],
        textposition="outside",
    ))
    fig.update_layout(
        title="Detection Count by Method",
        xaxis_title="",
        yaxis_title="Anomalies Detected",
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_anomaly_type_chart(df):
    """Build spike vs dip breakdown by brand."""
    if "anomaly_type" not in df.columns:
        return None

    type_brand = df.groupby(["brand", "anomaly_type"]).size().reset_index(name="count")

    fig = go.Figure()
    for atype in ["spike", "dip"]:
        subset = type_brand[type_brand["anomaly_type"] == atype]
        labels = [BRAND_LABELS.get(b, b) for b in subset["brand"]]
        color = "#E74C3C" if atype == "spike" else "#3498DB"
        fig.add_trace(go.Bar(
            x=labels, y=subset["count"],
            name=atype.title(),
            marker_color=color,
        ))

    fig.update_layout(
        title="Anomaly Type by Brand (Spike vs Dip)",
        xaxis_title="",
        yaxis_title="Count",
        barmode="group",
        legend=dict(orientation="h", y=-0.15),
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_event_stacking_chart(df_events):
    """Build KPI 8: event stacking density — events per week."""
    if df_events is None or df_events.empty:
        return None

    df_events = df_events.copy()
    df_events["week_start"] = df_events["event_date"].dt.to_period("W").apply(
        lambda x: x.start_time
    )
    weekly_count = df_events.groupby("week_start").size().reset_index(name="event_count")
    weekly_count = weekly_count.sort_values("week_start")

    colors = ["#E74C3C" if c >= 2 else "#3498DB" for c in weekly_count["event_count"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=weekly_count["week_start"],
        y=weekly_count["event_count"],
        marker_color=colors,
        hovertemplate="%{x|%Y-%m-%d}: %{y} events<extra></extra>",
    ))
    fig.add_hline(y=2, line_dash="dash", line_color="orange",
                  annotation_text="Stacking threshold", annotation_position="top right")

    fig.update_layout(
        title="KPI 8: Event Stacking Density (Events per Week)",
        xaxis_title="",
        yaxis_title="Event Count",
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


# ================================================================
# Render
# ================================================================
def render():
    """Render Tab 4 content."""
    st.header("Anomaly")

    df_anomaly = load_anomaly_log()
    df_events = load_events()

    if df_anomaly is None or df_anomaly.empty:
        st.warning("Anomaly log data not available.")
        return

    # -- Summary metrics
    total = len(df_anomaly)
    methods = df_anomaly["detection_method"].nunique()
    spikes = len(df_anomaly[df_anomaly["anomaly_type"] == "spike"])
    dips = len(df_anomaly[df_anomaly["anomaly_type"] == "dip"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Anomalies", total)
    with col2:
        st.metric("Detection Methods", methods)
    with col3:
        st.metric("Spikes", spikes)
    with col4:
        st.metric("Dips", dips)

    st.markdown("---")

    # -- Brand/region selector
    col_brand, col_region = st.columns(2)
    with col_brand:
        brand = st.selectbox(
            "Brand",
            ["new_balance", "nike", "adidas", "puma"],
            format_func=lambda x: BRAND_LABELS.get(x, x),
            key="tab4_brand",
        )
    with col_region:
        region = st.selectbox(
            "Region", ["korea", "global"], key="tab4_region",
        )

    # -- Anomaly timeline
    fig_timeline = _build_anomaly_timeline(df_anomaly, brand=brand, region=region)
    if fig_timeline:
        st.plotly_chart(fig_timeline, use_container_width=True, key="anomaly_timeline")
    else:
        st.info(f"No anomalies detected for {BRAND_LABELS.get(brand, brand)} ({region}).")

    # -- Method agreement + type breakdown
    col_agree, col_type = st.columns(2)

    with col_agree:
        fig_agree = _build_method_agreement_chart(df_anomaly)
        if fig_agree:
            st.plotly_chart(fig_agree, use_container_width=True, key="method_agreement")

    with col_type:
        fig_type = _build_anomaly_type_chart(df_anomaly)
        if fig_type:
            st.plotly_chart(fig_type, use_container_width=True, key="anomaly_type")

    # -- Method distribution
    fig_dist = _build_method_distribution(df_anomaly)
    if fig_dist:
        st.plotly_chart(fig_dist, use_container_width=True, key="method_dist")

    # -- Event stacking
    st.markdown("---")
    fig_events = _build_event_stacking_chart(df_events)
    if fig_events:
        st.plotly_chart(fig_events, use_container_width=True, key="event_stacking")
    elif df_events is None or df_events.empty:
        st.info("Events calendar data not available.")

    # -- Methodology reference
    with st.expander("Anomaly Detection Methodology"):
        st.markdown(
            "**3-Way Comparison:** Z-score (rolling 8-week) vs MSTL residual vs Isolation Forest.  \n"
            "**Methods:** rolling_zscore_8w (69), mstl_residual (81), isolation_forest (72).  \n"
            "**Tier 1 Precision:** 71.4% (events matching anomaly within 1-week window).  \n"
            "**Scheduled EDR:** 85.7% (scheduled events detected).  \n"
            "**Curated Events:** 25 total (7 scheduled, 18 investigated)."
        )
