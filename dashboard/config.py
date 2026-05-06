"""
Dashboard configuration — DB connection, CSV fallback, constants.
Usage: imported by app.py and data/queries.py
"""

# stdlib
import os

# third-party
from dotenv import load_dotenv

load_dotenv()

# ================================================================
# Data source configuration
# ================================================================
# When True, read from data/exports/ CSV instead of PostgreSQL.
# Streamlit Cloud deploy uses CSV; local dev uses PostgreSQL.
USE_CSV_FALLBACK = os.getenv("USE_CSV_FALLBACK", "false").lower() == "true"

CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "exports")

# ================================================================
# PostgreSQL connection
# ================================================================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "dbname": os.getenv("DB_NAME", "nb_monitor"),
    "user": os.getenv("DB_USER", "nb_admin"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# ================================================================
# Project paths
# ================================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHAIN_DIAGRAM_PATH = os.path.join(PROJECT_ROOT, "data", "bridge", "chain_diagram_data.json")
CHAIN_SUMMARY_PNG = os.path.join(PROJECT_ROOT, "figures", "bridge", "chain_summary.png")
STAGE7_BRIDGE_REPORT = os.path.join(PROJECT_ROOT, "docs", "stage7_bridge_report.md")
STYLE_CSS = os.path.join(os.path.dirname(__file__), "assets", "style.css")

# ================================================================
# Brand constants
# ================================================================
BRAND_COLORS = {
    "new_balance": "#E63946",  # NB Red — primary subject
    "nike":        "#FF6B00",  # Nike orange (industry standard)
    "adidas":      "#3498DB",  # adidas blue (industry standard)
    "puma":        "#2ECC71",  # PUMA green (industry standard)
}

# Visual hierarchy — NB emphasized via line width + opacity, not color reduction
BRAND_LINE_WIDTH = {
    "new_balance": 3.5,
    "nike":        1.0,
    "adidas":      1.0,
    "puma":        1.0,
}

BRAND_LINE_OPACITY = {
    "new_balance": 1.0,
    "nike":        0.55,
    "adidas":      0.55,
    "puma":        0.55,
}

BRAND_LABELS = {
    "new_balance": "New Balance",
    "nike": "Nike",
    "adidas": "adidas",
    "puma": "PUMA",
}

# ================================================================
# KPI registry — 13 KPIs mapped to tabs
# ================================================================
# KPI 1-11: operational metrics (Tabs 1-5)
# KPI 12-13: governance assets (Methodology Doc tab)
KPI_TAB_MAP = {
    1: {"tab": "tab1", "name": "530 Dependency Ratio", "alert": "> 60%"},
    2: {"tab": "tab1,tab3", "name": "D2C Search Trend", "alert": "4-week decline"},
    3: {"tab": "tab1", "name": "Category Gap Auto-detect", "alert": "padding gap"},
    4: {"tab": "tab2,tab4", "name": "NB Sentiment Quarterly", "alert": "quarterly"},
    5: {"tab": "tab1", "name": "Search-Sentiment Gap", "alert": "over-index"},
    6: {"tab": "tab1,tab5", "name": "CSI Moving Average", "alert": "campaign trigger"},
    7: {"tab": "tab5", "name": "Global Trend MA", "alert": "monitoring only"},
    8: {"tab": "tab4", "name": "Event Stacking Density", "alert": "same-week count"},
    9: {"tab": "tab4", "name": "Anomaly Method Agreement", "alert": "3-way agreement"},
    10: {"tab": "tab1,tab5", "name": "CSI Elasticity", "alert": "Korea 3.98"},
    11: {"tab": "tab5", "name": "Prophet Baseline 26w", "alert": "monthly update"},
    12: {"tab": "methodology", "name": "5-Dim Verification Pattern", "alert": "governance"},
    13: {"tab": "methodology", "name": "Methodology Validation Stage", "alert": "governance"},
}
