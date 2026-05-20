"""
Methodology Documentation tab — governance assets (KPI 12, 13).
Visually optimized for 30-second interview impression.
Usage: methodology_doc.render() called from app.py
"""

import os

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from dashboard.config import CHAIN_SUMMARY_PNG


# Visual builders
def _build_5dim_heatmap():
    """Build 5-dim null test as clean heatmap — all red = all reject."""
    dimensions = [
        "VARX",
        "Monthly Granger",
        "Trend Mediation",
        "Diff1 Mediation",
        "Lagged Cointegration",
    ]
    directions = ["Korea → Global", "Global → Korea"]

    # All reject = 1 everywhere
    z = [[1, 1], [1, 1], [1, 1], [1, 1], [1, 1]]
    text = [["REJECT<br>p<0.05", "REJECT<br>p<0.001"],
            ["REJECT<br>p<0.001", "REJECT<br>p<0.001"],
            ["REJECT<br>p<0.001", "REJECT<br>p<0.001"],
            ["REJECT<br>p<0.001", "REJECT<br>p<0.001"],
            ["REJECT<br>p<0.001", "REJECT<br>p<0.001"]]

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=directions,
        y=dimensions,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=12, color="#FAFAFA"),
        colorscale=[[0, "#2C3E50"], [1, "#34495E"]],
        showscale=False,
        hoverinfo="skip",
    ))

    # Add 11th test row (forecast degradation)
    fig.add_annotation(
        x=0.5, y=-0.8,
        xref="x", yref="y",
        text="+ Forecast Degradation: Prophet -9.0% / SARIMAX -10.9% (DM p<0.001)",
        showarrow=False,
        font=dict(size=11, color="#E67E22"),
        bgcolor="rgba(230,126,34,0.08)",
        bordercolor="#E67E22",
        borderwidth=1,
        borderpad=6,
    )

    fig.update_layout(
        title="KPI 12: 5-Dim Orthogonal Null — 11/11 Reject",
        height=380,
        margin=dict(l=140, r=20, t=50, b=60),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def _build_cascade_flow():
    """Build DP20 → DP23 → DP24 cascade as horizontal flow."""
    fig = go.Figure()

    steps = [
        {"x": 0.17, "label": "DP20", "title": "Pre-emption",
         "desc": "Mediation spurious\ncorrelation pre-emption",
         "color": "#3498DB"},
        {"x": 0.50, "label": "DP23", "title": "Self-Diagnostic",
         "desc": "MSTL forward-looking\nleakage detection",
         "color": "#F39C12"},
        {"x": 0.83, "label": "DP24", "title": "Critical Finding",
         "desc": "Sign convention\ninversion corrected",
         "color": "#E74C3C"},
    ]

    for s in steps:
        # Box
        fig.add_shape(
            type="rect",
            x0=s["x"] - 0.14, y0=0.15,
            x1=s["x"] + 0.14, y1=0.85,
            fillcolor=s["color"], opacity=0.12,
            line=dict(color=s["color"], width=2.5),
        )
        # Label
        fig.add_annotation(
            x=s["x"], y=0.70,
            text=f"<b>{s['label']}</b>",
            showarrow=False, font=dict(size=22, color=s["color"]),
        )
        # Title
        fig.add_annotation(
            x=s["x"], y=0.50,
            text=f"<b>{s['title']}</b>",
            showarrow=False, font=dict(size=13),
        )
        # Description
        fig.add_annotation(
            x=s["x"], y=0.30,
            text=s["desc"],
            showarrow=False, font=dict(size=10, color="#AAA"),
            align="center",
        )

    # Arrows between boxes
    for ax, bx in [(0.31, 0.36), (0.64, 0.69)]:
        fig.add_annotation(
            x=bx, y=0.50, ax=ax, ay=0.50,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True,
            arrowhead=3, arrowsize=2, arrowwidth=2.5,
            arrowcolor="#FAFAFA",
        )

    fig.update_layout(
        title="KPI 13: Self-Diagnostic Cascade",
        xaxis=dict(range=[0, 1], visible=False),
        yaxis=dict(range=[0, 1], visible=False),
        height=280,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _build_signature_chart():
    """Build DP24 before/after comparison — clean grouped bar."""
    categories = ["% Indirect", "BCa CI Width", "Track A3 Degradation"]
    before = [120, 100, 50]
    after = [11, 53, 10]
    before_labels = ["120%", "100%", "+41~59%"]
    after_labels = ["11%", "53%", "+9~11%"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories, y=before, name="Before DP24",
        marker_color="#E74C3C", opacity=0.75,
        text=before_labels, textposition="inside",
        textfont=dict(size=13),
    ))
    fig.add_trace(go.Bar(
        x=categories, y=after, name="After DP24",
        marker_color="#2ECC71", opacity=0.75,
        text=after_labels, textposition="inside",
        textfont=dict(size=13),
    ))

    fig.update_layout(
        title="DP24 Impact — Before vs After Sign Correction",
        yaxis_title="",
        barmode="group",
        legend=dict(orientation="h", y=-0.2),
        height=320,
        margin=dict(l=40, r=20, t=50, b=50),
        yaxis=dict(showticklabels=False, showgrid=False),
    )
    return fig


# Render
def render():
    """Render Methodology Documentation tab content."""
    st.header("Methodology Documentation")
    st.caption("Governance assets — not operational metrics (KPI 12, 13)")

    # -- Chain diagram
    if os.path.exists(CHAIN_SUMMARY_PNG):
        st.image(CHAIN_SUMMARY_PNG)

    st.markdown("---")

    # -- KPI 12: 5-Dim Null heatmap + description
    col_heat, col_desc12 = st.columns([3, 2])

    with col_heat:
        st.plotly_chart(_build_5dim_heatmap(), width="stretch", key="null_heatmap")

    with col_desc12:
        st.markdown("### KPI 12")
        st.markdown("**5-Dimension Orthogonal Null Verification**")
        st.markdown(
            "5 independent statistical dimensions, each tested bidirectionally = "
            "**11 tests total**. All 11 independently rejected the Korea-Global "
            "chain hypothesis — convergent evidence no single test could provide."
        )
        st.markdown(
            "**Transferability:** Any team testing causal chain hypotheses can "
            "adopt this 11-test framework as a default verification protocol."
        )

    st.markdown("---")

    # -- KPI 13: Cascade flow
    st.plotly_chart(_build_cascade_flow(), width="stretch", key="cascade_flow")

    # -- DP24 signatures + description
    col_sig, col_desc13 = st.columns([3, 2])

    with col_sig:
        st.plotly_chart(_build_signature_chart(), width="stretch", key="sig_chart")

    with col_desc13:
        st.markdown("### KPI 13")
        st.markdown("**Methodology Validation Stage**")
        st.markdown(
            "Three findings detected **without external review**, "
            "**before** dashboard implementation. "
            "Timing strengthens the self-skepticism claim."
        )
        st.markdown(
            "**DP24 signatures:**  \n"
            "Mediation: 120% → 11%  \n"
            "BCa CI: 47% narrowing  \n"
            "Degradation: 1/4 ~ 1/5 reduction"
        )

    st.markdown("---")

    # -- 4-Layer summary
    st.subheader("Stage 7 — 4-Layer Narrative")

    cols = st.columns(4)
    layers = [
        {"n": "1", "title": "Orthogonal Null", "desc": "5-dim x 11 tests\nAll reject chain", "color": "#E74C3C"},
        {"n": "2", "title": "Self-Diagnostic", "desc": "DP20 → DP23 → DP24\nNo external review", "color": "#F39C12"},
        {"n": "3", "title": "Signatures", "desc": "3 quantitative\nDP24 signatures", "color": "#2ECC71"},
        {"n": "4", "title": "Operational", "desc": "Mirror Sentinel +\nDiff. Reactivity", "color": "#3498DB"},
    ]
    for col, layer in zip(cols, layers):
        with col:
            st.markdown(
                f"<div style='border-left: 4px solid {layer['color']}; "
                f"padding: 8px 12px; margin-bottom: 8px;'>"
                f"<strong style='color: {layer['color']};'>Layer {layer['n']}</strong><br>"
                f"<strong>{layer['title']}</strong><br>"
                f"<span style='font-size: 0.85em; color: #AAA;'>{layer['desc']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.caption(
        "Full narrative: docs/stage7_bridge_report.md | "
        "Artifacts: stage7_checkpoint.md | "
        "Source: methodology.md §12"
    )
