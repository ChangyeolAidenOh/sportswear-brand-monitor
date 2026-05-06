"""
Tab 5: Forecast & Bridge — Prophet forecast (top) + chain diagram (bottom).
KPI coverage: 6 (CSI MA), 7 (Global trend MA, monitoring only),
              10 (CSI elasticity), 11 (Prophet baseline 26w).
Layout: Top row = Prophet forecast + 4-way comparison (region-dependent).
        Bottom row = chain diagram + Global MA + operational narrative (static).
Usage: tab5_forecast_bridge.render() called from app.py
"""

# stdlib
import json
import os

# third-party
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# local
from dashboard.config import (
    BRAND_COLORS, PROJECT_ROOT, CHAIN_DIAGRAM_PATH, CHAIN_SUMMARY_PNG,
)
from dashboard.data.queries import fetch_brand_kpi, fetch_korea_global_lag
from dashboard.components.tooltip import render_tooltip


# ================================================================
# Data loading (cached)
# ================================================================
FORECAST_DIR = os.path.join(PROJECT_ROOT, "data", "forecast")


@st.cache_data(ttl=600)
def load_prophet_forecast(region="korea"):
    """Load Prophet forecast CSV for a given region."""
    path = os.path.join(FORECAST_DIR, f"prophet_forecast_{region}.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, parse_dates=["week_start"])


@st.cache_data(ttl=600)
def load_prophet_metrics():
    """Load Prophet metrics CSV."""
    path = os.path.join(FORECAST_DIR, "prophet_metrics.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_forecast_comparison():
    """Load 4-way forecast comparison metrics."""
    path = os.path.join(FORECAST_DIR, "forecast_comparison_4way.csv")
    if not os.path.exists(path):
        path = os.path.join(FORECAST_DIR, "forecast_comparison_metrics.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_brand_kpi_data():
    """Load brand KPI for actual time series."""
    return fetch_brand_kpi()


@st.cache_data(ttl=600)
def load_chain_diagram():
    """Load chain_diagram_data.json."""
    if not os.path.exists(CHAIN_DIAGRAM_PATH):
        return None
    with open(CHAIN_DIAGRAM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ================================================================
# Top row: Prophet forecast
# ================================================================
def _build_prophet_chart(df_forecast, df_actual, region="korea"):
    """Build Prophet forecast chart with actual + forecast + CI band."""
    fig = go.Figure()

    if df_actual is not None and not df_actual.empty:
        nb_actual = df_actual[
            (df_actual["brand"] == "new_balance") & (df_actual["region"] == region)
        ].sort_values("week_start")

        fig.add_trace(go.Scatter(
            x=nb_actual["week_start"], y=nb_actual["search_index"],
            name="Actual",
            line=dict(color="#E63946", width=2),
            hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra></extra>",
        ))

    if df_forecast is not None and not df_forecast.empty:
        fig.add_trace(go.Scatter(
            x=df_forecast["week_start"], y=df_forecast["search_index"],
            name="Test Actual", mode="markers",
            marker=dict(color="#E63946", size=5),
            hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=df_forecast["week_start"], y=df_forecast["prophet_forecast"],
            name="Prophet Forecast",
            line=dict(color="#F77F00", width=2.5, dash="dash"),
            hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=pd.concat([df_forecast["week_start"], df_forecast["week_start"][::-1]]),
            y=pd.concat([df_forecast["prophet_upper"], df_forecast["prophet_lower"][::-1]]),
            fill="toself", fillcolor="rgba(247, 127, 0, 0.15)",
            line=dict(color="rgba(0,0,0,0)"), name="95% CI", hoverinfo="skip",
        ))
        anomaly_weeks = df_forecast[df_forecast["is_anomaly_week"] == 1]
        if not anomaly_weeks.empty:
            fig.add_trace(go.Scatter(
                x=anomaly_weeks["week_start"], y=anomaly_weeks["search_index"],
                name="Anomaly Week", mode="markers",
                marker=dict(color="#F39C12", size=10, symbol="diamond"),
            ))

    region_label = "Korea" if region == "korea" else "Global"
    fig.update_layout(
        title=f"KPI 11: NB {region_label} Prophet 26-Week Forecast",
        xaxis_title="", yaxis_title="Search Index",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=420, margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _build_model_comparison_chart(df_metrics, region="korea"):
    """Build 4-way model comparison bar chart."""
    if df_metrics is None or df_metrics.empty:
        return None

    model_colors = {
        "Prophet": "#E63946",   # NB Red — winner emphasis
        "SARIMAX": "#3498DB",   # Blue
        "LSTM":    "#FF6B00",   # Orange (was NB color, now Nike-like)
        "Chronos": "#2ECC71",   # Green
    }
    subset = df_metrics[
        (df_metrics["region"] == region) & (df_metrics["subset"] == "all")
    ].copy()
    if subset.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=subset["model"], y=subset["rmse"],
        marker_color=[model_colors.get(m, "#888") for m in subset["model"]],
        text=[f"{v:.2f}" for v in subset["rmse"]],
        textposition="outside",
    ))
    region_label = "Korea" if region == "korea" else "Global"
    fig.update_layout(
        title=f"4-Way Model Comparison — {region_label} RMSE",
        xaxis_title="", yaxis_title="RMSE",
        height=420, margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


# ================================================================
# Bottom row: Chain diagram + Global MA
# ================================================================
def _render_chain_diagram_visual(chain_data):
    """Render Stage 7 chain diagram as structured visualization."""
    if chain_data is None:
        st.info("chain_diagram_data.json not found.")
        return

    nodes = chain_data.get("nodes", [])
    edges = chain_data.get("edges", [])
    narrative = chain_data.get("narrative", {})
    test_summary = chain_data.get("test_summary", {})

    if os.path.exists(CHAIN_SUMMARY_PNG):
        st.image(CHAIN_SUMMARY_PNG, caption="Stage 7 Korea-Global Bridge — Sign-Corrected Chain Diagram")
    else:
        st.markdown("#### Chain Diagram — Sign-Corrected")
        for node in nodes:
            st.markdown(f"**{node['label']}** ({node.get('role', '')})")
        for edge in edges:
            from_l = next((n["label"] for n in nodes if n["id"] == edge["from"]), edge["from"])
            to_l = next((n["label"] for n in nodes if n["id"] == edge["to"]), edge["to"])
            st.markdown(f"**{from_l}** → **{to_l}** ({edge.get('relationship', '')})")
            st.caption(edge.get("evidence", ""))

    st.markdown(f"**Framing:** {narrative.get('framing_label', '')}")
    st.caption(narrative.get("framing_description", ""))

    op = narrative.get("operational_distinction", {})
    if op:
        col_m, col_p = st.columns(2)
        with col_m:
            st.markdown("**Monitoring**")
            st.markdown(op.get("monitoring", ""))
        with col_p:
            st.markdown("**Predictive**")
            st.markdown(op.get("predictive", ""))

    if test_summary:
        with st.expander(f"5-Dim Null Test Summary ({test_summary.get('n_tests_total', '')} tests)"):
            st.markdown(f"**All reject chain hypothesis:** {'Yes' if test_summary.get('all_reject_chain') else 'No'}")
            tests = test_summary.get("tests", [])
            if tests:
                st.dataframe(pd.DataFrame(tests), width="stretch")


def _build_global_trend_ma_chart(df_actual):
    """Build Global trend 4-week MA for monitoring (KPI 7)."""
    if df_actual is None or df_actual.empty:
        return None
    nb_global = df_actual[
        (df_actual["brand"] == "new_balance") & (df_actual["region"] == "global")
    ].sort_values("week_start").copy()
    if nb_global.empty:
        return None

    nb_global["ma_4w"] = nb_global["search_index"].rolling(4, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nb_global["week_start"], y=nb_global["search_index"],
        name="Global Raw", line=dict(color="#3498DB", width=1), opacity=0.4,
    ))
    fig.add_trace(go.Scatter(
        x=nb_global["week_start"], y=nb_global["ma_4w"],
        name="Global 4w MA", line=dict(color="#3498DB", width=2.5),
    ))
    fig.update_layout(
        title="KPI 7: NB Global Trend 4-Week MA (Monitoring Only)",
        xaxis_title="", yaxis_title="Search Index",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=350, margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


# ================================================================
# Render
# ================================================================
def render():
    """Render Tab 5 content."""
    st.header("Forecast & Bridge")

    df_actual = load_brand_kpi_data()
    chain_data = load_chain_diagram()
    df_comparison = load_forecast_comparison()
    df_metrics = load_prophet_metrics()

    # ── Top row: region-dependent forecast ──
    region = st.radio(
        "Forecast Region", ["korea", "global"], horizontal=True, key="tab5_region"
    )

    # KPI cards
    if df_metrics is not None and not df_metrics.empty:
        region_m = df_metrics[df_metrics["label"].str.contains(region, case=False, na=False)]
        overall = region_m[region_m["label"].str.contains("overall|normal", case=False, na=False)]
        if not overall.empty:
            row = overall.iloc[0]
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Prophet RMSE", f"{row['rmse']:.2f}")
            with c2:
                st.metric("MAE", f"{row['mae']:.2f}")
            with c3:
                st.metric("MAPE", f"{row['mape_pct']:.1f}%")

    # Prophet forecast + Model comparison side by side
    df_forecast = load_prophet_forecast(region)

    col_forecast, col_compare = st.columns(2)

    with col_forecast:
        if df_forecast is not None:
            fig_prophet = _build_prophet_chart(df_forecast, df_actual, region=region)
            st.plotly_chart(fig_prophet, width="stretch", key="prophet_forecast")
        else:
            st.warning(f"Prophet forecast CSV not found for {region}.")

    with col_compare:
        if df_comparison is not None:
            fig_comp = _build_model_comparison_chart(df_comparison, region=region)
            if fig_comp:
                st.plotly_chart(fig_comp, width="stretch", key="model_comparison")

    st.caption(
        "CSI (Consumer Sentiment Index) is the sole exogenous variable. "
        "CSI elasticity: Korea 3.98 vs Global 2.01 (SARIMAX-specific)."
    )

    # ── Bottom row: static bridge content ──
    st.markdown("---")
    st.subheader("Korea-Global Bridge")

    col_chain, col_global = st.columns(2)

    with col_chain:
        _render_chain_diagram_visual(chain_data)

    with col_global:
        fig_global = _build_global_trend_ma_chart(df_actual)
        if fig_global:
            st.plotly_chart(fig_global, width="stretch", key="global_ma")

        st.caption(render_tooltip("monitoring_vs_predictive"))

    # Degradation evidence
    with st.expander("Why Global Signal is Excluded from Forecast"):
        st.markdown(
            "**Triple comparison results (Stage 7 Track A3):**\n\n"
            "| Model | RMSE | vs Baseline |\n"
            "|---|---|---|\n"
            "| Prophet baseline | 4.75 | — |\n"
            "| Prophet + CSI | 5.57 | +17.3% |\n"
            "| Prophet + CSI + Global_lag11 | 6.07 | **+9.0% degradation** |\n"
            "| SARIMAX + CSI | 6.49 | — |\n"
            "| SARIMAX + CSI + Global_lag11 | 7.20 | **+10.9% degradation** |\n\n"
            "Both models show statistically significant degradation when Global lagged "
            "signal is added (DM test p < 0.001). Global signal actively interferes with "
            "the forecast model despite being a valid monitoring indicator."
        )
