"""
Tab 2: Season Tracker — SS/FW cycle position, YoY comparison.
KPI coverage: 4 (NB sentiment quarterly).
Visualizations: season position indicator, YoY overlay, seasonal heatmap.
Usage: tab2_season.render() called from app.py
"""

# third-party
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# local
from dashboard.config import BRAND_COLORS, BRAND_LABELS
from dashboard.data.queries import fetch_brand_kpi, fetch_product_portfolio


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


# ================================================================
# Season helpers
# ================================================================
def _get_current_season(df):
    """Extract current season label and week number for NB Korea."""
    if df is None or df.empty:
        return None, None, None
    nb_korea = df[
        (df["brand"] == "new_balance") & (df["region"] == "korea")
    ].sort_values("week_start")
    if nb_korea.empty:
        return None, None, None
    latest = nb_korea.iloc[-1]
    return (
        latest.get("season_label"),
        latest.get("season_week_num"),
        latest.get("week_start"),
    )


def _extract_season_type(label):
    """Extract 'SS' or 'FW' from season label like 'SS26' or 'FW25'."""
    if label and len(label) >= 2:
        return label[:2].upper()
    return None


def _extract_season_year(label):
    """Extract year from season label like 'SS26' -> 2026."""
    if label and len(label) >= 3:
        try:
            yr = int(label[2:])
            return 2000 + yr if yr < 100 else yr
        except ValueError:
            pass
    return None


# ================================================================
# Chart builders
# ================================================================
def _build_season_overlay_chart(df, brand="new_balance", region="korea"):
    """Build YoY season overlay — same season across years on shared x-axis."""
    brand_df = df[
        (df["brand"] == brand) & (df["region"] == region)
    ].copy()

    if brand_df.empty or "season_label" not in brand_df.columns:
        return None

    brand_df = brand_df.dropna(subset=["season_label", "season_week_num"])
    brand_df["season_type"] = brand_df["season_label"].apply(_extract_season_type)
    brand_df["season_year"] = brand_df["season_label"].apply(_extract_season_year)

    # Get the current season type
    latest_label = brand_df.sort_values("week_start").iloc[-1]["season_label"]
    current_type = _extract_season_type(latest_label)

    # Filter to same season type (SS or FW)
    same_type = brand_df[brand_df["season_type"] == current_type].copy()
    if same_type.empty:
        return None

    fig = go.Figure()
    seasons = sorted(same_type["season_label"].unique())

    # Color gradient: older = lighter, current = bold
    for i, season in enumerate(seasons):
        season_df = same_type[same_type["season_label"] == season].sort_values("season_week_num")
        opacity = 0.3 + 0.7 * (i / max(len(seasons) - 1, 1))
        width = 3 if i == len(seasons) - 1 else 1.5

        fig.add_trace(go.Scatter(
            x=season_df["season_week_num"],
            y=season_df["search_index"],
            name=season,
            line=dict(
                color=BRAND_COLORS.get(brand, "#E74C3C"),
                width=width,
            ),
            opacity=opacity,
            hovertemplate=f"{season} W%{{x}}: %{{y:.1f}}<extra></extra>",
        ))

    fig.update_layout(
        title=f"{BRAND_LABELS.get(brand, brand)} — {current_type} Season YoY Overlay ({region.title()})",
        xaxis_title="Week within Season",
        yaxis_title="Search Index",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_seasonal_pattern_chart(df, region="korea"):
    """Build 4-brand seasonal pattern — search index by week-of-year."""
    region_df = df[df["region"] == region].copy()
    if region_df.empty:
        return None

    region_df["week_of_year"] = region_df["week_start"].dt.isocalendar().week.astype(int)

    fig = go.Figure()
    for brand in ["new_balance", "nike", "adidas", "puma"]:
        brand_df = region_df[region_df["brand"] == brand]
        weekly_avg = brand_df.groupby("week_of_year")["search_index"].mean().reset_index()
        weekly_avg = weekly_avg.sort_values("week_of_year")

        fig.add_trace(go.Scatter(
            x=weekly_avg["week_of_year"],
            y=weekly_avg["search_index"],
            name=BRAND_LABELS.get(brand, brand),
            line=dict(color=BRAND_COLORS.get(brand, "#888"), width=2),
            hovertemplate="W%{x}: %{y:.1f}<extra></extra>",
        ))

    # Season boundary annotations
    fig.add_vrect(x0=1, x1=13, fillcolor="rgba(52,152,219,0.05)",
                  layer="below", line_width=0,
                  annotation_text="FW (tail)", annotation_position="top left")
    fig.add_vrect(x0=14, x1=26, fillcolor="rgba(231,76,60,0.05)",
                  layer="below", line_width=0,
                  annotation_text="SS", annotation_position="top left")
    fig.add_vrect(x0=27, x1=39, fillcolor="rgba(52,152,219,0.05)",
                  layer="below", line_width=0,
                  annotation_text="FW (ramp)", annotation_position="top left")
    fig.add_vrect(x0=40, x1=52, fillcolor="rgba(52,152,219,0.08)",
                  layer="below", line_width=0,
                  annotation_text="FW (peak)", annotation_position="top left")

    fig.update_layout(
        title=f"Average Weekly Seasonal Pattern — {region.title()}",
        xaxis_title="Week of Year",
        yaxis_title="Avg Search Index",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_product_season_chart(df_prod, region="korea"):
    """Build NB product mix shift across seasons."""
    korea = df_prod[df_prod["region"] == region].copy()
    if korea.empty or "season_label" not in korea.columns:
        return None

    korea = korea.dropna(subset=["season_label"])
    season_avg = korea.groupby(
        ["season_label", "product_line"]
    )["share_within_nb_pct"].mean().reset_index()

    if season_avg.empty:
        return None

    # Multiply if stored as fraction
    if season_avg["share_within_nb_pct"].max() <= 1:
        season_avg["share_within_nb_pct"] = season_avg["share_within_nb_pct"] * 100

    product_colors = {
        "530": "#E74C3C", "574": "#3498DB", "992": "#F39C12",
        "2002r": "#2ECC71", "327": "#9B59B6",
        "9060": "#E74C3C", "1906r": "#9B59B6", "990": "#1ABC9C",
    }

    fig = go.Figure()
    seasons = sorted(season_avg["season_label"].unique())
    products = sorted(season_avg["product_line"].unique())

    for prod in products:
        prod_df = season_avg[season_avg["product_line"] == prod]
        fig.add_trace(go.Bar(
            x=prod_df["season_label"],
            y=prod_df["share_within_nb_pct"],
            name=prod,
            marker_color=product_colors.get(prod, "#888"),
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        ))

    fig.update_layout(
        title=f"NB Product Mix by Season — {region.title()}",
        xaxis_title="",
        yaxis_title="Share within NB (%)",
        barmode="stack",
        legend=dict(orientation="h", y=-0.15),
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


# ================================================================
# Render
# ================================================================
def render():
    """Render Tab 2 content."""
    st.header("Season Tracker")

    df_kpi = load_brand_kpi()
    df_prod = load_product_portfolio()

    if df_kpi is None or df_kpi.empty:
        st.warning("Brand KPI data not available.")
        return

    # -- Season position indicator
    season_label, season_week, latest_date = _get_current_season(df_kpi)

    if season_label:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Season", season_label)
        with col2:
            st.metric("Week in Season", f"W{int(season_week)}" if season_week else "N/A")
        with col3:
            st.metric("Latest Data", latest_date.strftime("%Y-%m-%d") if latest_date else "N/A")

    st.markdown("---")

    # -- Region selector
    region = st.radio(
        "Region", ["korea", "global"], horizontal=True, key="tab2_region"
    )

    # -- Season overlay chart (YoY same season)
    fig_overlay = _build_season_overlay_chart(df_kpi, brand="new_balance", region=region)
    if fig_overlay:
        st.plotly_chart(fig_overlay, use_container_width=True, key="season_overlay")

    # -- Seasonal pattern + Product mix side by side
    col_pattern, col_product = st.columns(2)

    with col_pattern:
        fig_pattern = _build_seasonal_pattern_chart(df_kpi, region=region)
        if fig_pattern:
            st.plotly_chart(fig_pattern, use_container_width=True, key="season_pattern")

    with col_product:
        if df_prod is not None and not df_prod.empty:
            fig_product = _build_product_season_chart(df_prod, region=region)
            if fig_product:
                st.plotly_chart(fig_product, use_container_width=True, key="product_season")
        else:
            st.info("Product portfolio data not available.")
