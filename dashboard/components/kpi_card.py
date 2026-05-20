"""
Reusable KPI card component for dashboard metrics display.
Usage: from dashboard.components.kpi_card import render_kpi_card
"""

import streamlit as st


# KPI card
def render_kpi_card(label, value, delta=None, delta_color="normal", help_text=None):
    """Render a single KPI metric card using st.metric.

    Args:
        label: metric name
        value: current value (str or number)
        delta: change value (str or number, optional)
        delta_color: "normal", "inverse", or "off"
        help_text: tooltip text (optional)
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text,
    )


def render_kpi_row(metrics, cols_per_row=4):
    """Render a row of KPI cards.

    Args:
        metrics: list of dicts with keys matching render_kpi_card params
        cols_per_row: number of columns per row
    """
    cols = st.columns(cols_per_row)
    for i, m in enumerate(metrics):
        with cols[i % cols_per_row]:
            render_kpi_card(**m)
