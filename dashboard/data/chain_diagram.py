"""
Chain diagram data loader for Stage 7 bridge visualization.
Loads chain_diagram_data.json and provides operational_use branching.
Usage: from dashboard.data.chain_diagram import load_chain_diagram
"""

import json
import os

from dashboard.config import CHAIN_DIAGRAM_PATH


# Loader
def load_chain_diagram():
    """Load chain_diagram_data.json. Returns dict or None if missing."""
    if not os.path.exists(CHAIN_DIAGRAM_PATH):
        return None
    with open(CHAIN_DIAGRAM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Operational use helpers
def get_nodes(data):
    """Extract node list from chain diagram data."""
    if data is None:
        return []
    return data.get("nodes", [])


def get_edges(data):
    """Extract edge list from chain diagram data."""
    if data is None:
        return []
    return data.get("edges", [])


def get_monitoring_edges(data):
    """Return edges where operational_use.monitoring_indicator is True."""
    edges = get_edges(data)
    return [
        e for e in edges
        if e.get("operational_use", {}).get("monitoring_indicator", False)
    ]


def get_predictive_edges(data):
    """Return edges where operational_use.predictive_feature is True."""
    edges = get_edges(data)
    return [
        e for e in edges
        if e.get("operational_use", {}).get("predictive_feature", False)
    ]


def get_narrative(data):
    """Extract narrative object from chain diagram data."""
    if data is None:
        return {}
    return data.get("narrative", {})


def is_interference_detected(data):
    """Check if any edge has interference_detected = True."""
    edges = get_edges(data)
    return any(
        e.get("operational_use", {}).get("interference_detected", False)
        for e in edges
    )
