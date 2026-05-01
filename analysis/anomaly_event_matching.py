"""
Stage 5 Track D — Event Matching & Evaluation

Matches anomalies to events_calendar entries and computes:
  - Precision (dual: Tier 1 only, Tier 1+2; each with/without macro match)
  - Event Detection Rate (dual: scheduled only, all events)

Matching rules:
  1. Window: event_date BETWEEN week_start AND week_start + 6
     For range events: week_start BETWEEN event_date AND event_end_date
  2. Brand: macro_event (brand=NULL) matches any brand anomaly in that week.
     Brand-specific events match only that brand.
  3. Coverage: Precision denominator uses only anomalies within
     events_calendar coverage period (2024-02 ~ 2025-04).

Usage:
    python analysis/anomaly_event_matching.py
"""

# stdlib
import os
import sys
from datetime import timedelta

# third-party
import pandas as pd
import numpy as np

# ================================================================
# CONSTANTS
# ================================================================

EVENTS_CSV = "data/events_calendar.csv"
TARGETS_CSV = "data/anomaly/investigation_targets.csv"
COMP_CSV = "data/anomaly/three_way_comparison.csv"
MSTL_CSV = "data/anomaly/mstl_residual_anomalies_2.0.csv"
OUT_DIR = "data/anomaly"
FIG_DIR = "figures/anomaly"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

# Coverage period (events_calendar range)
COVERAGE_START = pd.Timestamp("2024-02-01")
COVERAGE_END = pd.Timestamp("2025-04-30")


# ================================================================
# DATA LOADING
# ================================================================

def load_events():
    """Load events_calendar.csv."""
    df = pd.read_csv(EVENTS_CSV)
    df["event_date"] = pd.to_datetime(df["event_date"])
    df["event_end_date"] = pd.to_datetime(df["event_end_date"])
    df["brand"] = df["brand"].replace("", np.nan)
    df["event_id"] = range(1, len(df) + 1)
    print(f"Loaded {len(df)} events "
          f"(scheduled: {(df['event_origin'] == 'scheduled').sum()}, "
          f"investigated: {(df['event_origin'] == 'investigated').sum()})")
    return df


def load_targets():
    """Load investigation targets (Tier 1 + Tier 2 anomalies)."""
    df = pd.read_csv(TARGETS_CSV)
    df["week_start"] = pd.to_datetime(df["week_start"])
    print(f"Loaded {len(df)} investigation targets "
          f"(Tier 1: {(df['tier'] == 1).sum()}, Tier 2: {(df['tier'] == 2).sum()})")
    return df


def load_all_anomalies():
    """Load full 3-way comparison for Event Detection Rate calculation."""
    df = pd.read_csv(COMP_CSV)
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


# ================================================================
# MATCHING ENGINE
# ================================================================

def match_anomaly_to_events(anomaly_row, events_df):
    """
    Match a single anomaly to events using strict window.

    Returns list of (event_id, match_type) tuples.
    match_type: 'primary' (closest date) or 'secondary'.
    """
    ws = anomaly_row["week_start"]
    week_end = ws + timedelta(days=6)
    brand = anomaly_row["brand"]

    matches = []

    for _, evt in events_df.iterrows():
        # Window check
        if pd.notna(evt["event_end_date"]):
            # Range event: week_start falls within event period
            in_window = evt["event_date"] <= week_end and evt["event_end_date"] >= ws
        else:
            # Point event: event_date falls within anomaly week
            in_window = ws <= evt["event_date"] <= week_end

        if not in_window:
            continue

        # Brand check
        if pd.isna(evt["brand"]):
            # macro_event matches any brand
            matches.append(evt)
        elif evt["brand"] == brand:
            # Brand-specific match
            matches.append(evt)

    if not matches:
        return [], None

    # Sort by date proximity to week_start
    matches_df = pd.DataFrame(matches)
    matches_df["date_diff"] = (matches_df["event_date"] - ws).abs()
    matches_df = matches_df.sort_values("date_diff")

    primary_id = int(matches_df.iloc[0]["event_id"])
    is_macro = pd.isna(matches_df.iloc[0]["brand"])

    return matches_df["event_id"].tolist(), primary_id, is_macro


def run_matching(targets, events):
    """Match all anomalies to events. Returns enriched targets DataFrame."""
    results = []
    for idx, row in targets.iterrows():
        match_result = match_anomaly_to_events(row, events)

        if not match_result[0]:
            row_out = row.copy()
            row_out["matched"] = False
            row_out["primary_event_id"] = None
            row_out["n_matches"] = 0
            row_out["is_macro_match"] = False
            results.append(row_out)
        else:
            event_ids, primary_id, is_macro = match_result
            row_out = row.copy()
            row_out["matched"] = True
            row_out["primary_event_id"] = primary_id
            row_out["n_matches"] = len(event_ids)
            row_out["is_macro_match"] = is_macro
            results.append(row_out)

    result_df = pd.DataFrame(results)
    return result_df


# ================================================================
# COVERAGE PERIOD FILTER
# ================================================================

def filter_coverage_period(df):
    """Filter anomalies within events_calendar coverage period."""
    mask = (df["week_start"] >= COVERAGE_START) & (df["week_start"] <= COVERAGE_END)
    filtered = df.loc[mask].copy()
    excluded = len(df) - len(filtered)
    if excluded > 0:
        print(f"  Coverage filter: {excluded} anomalies outside "
              f"{COVERAGE_START.strftime('%Y-%m')} ~ "
              f"{COVERAGE_END.strftime('%Y-%m')}, excluded from Precision")
    return filtered


# ================================================================
# PRECISION CALCULATION
# ================================================================

def compute_precision(matched_df, label):
    """Compute Precision variants for a given anomaly set."""
    total = len(matched_df)
    if total == 0:
        print(f"\n  {label}: no anomalies in scope")
        return {}

    n_matched = matched_df["matched"].sum()
    n_macro = matched_df["is_macro_match"].sum()
    n_brand_only = n_matched - n_macro

    precision_all = n_matched / total
    precision_ex_macro = n_brand_only / total

    print(f"\n  {label}:")
    print(f"    Anomalies in scope: {total}")
    print(f"    Matched: {n_matched} ({precision_all:.1%})")
    print(f"    - via macro_event: {n_macro}")
    print(f"    - via brand-specific: {n_brand_only}")
    print(f"    Unmatched: {total - n_matched}")
    print(f"    Precision (all): {precision_all:.1%}")
    print(f"    Precision (ex macro): {precision_ex_macro:.1%}")

    return {
        "scope": label,
        "total": total,
        "matched": int(n_matched),
        "macro_match": int(n_macro),
        "brand_match": int(n_brand_only),
        "unmatched": int(total - n_matched),
        "precision_all": round(precision_all, 3),
        "precision_ex_macro": round(precision_ex_macro, 3),
    }


# ================================================================
# EVENT DETECTION RATE
# ================================================================

def compute_event_detection_rate(events, all_anomalies):
    """
    Compute Event Detection Rate: how many events had a co-occurring anomaly?

    Dual reporting:
      - scheduled events only (independent ground truth)
      - all events (upper bound, caveat: anomaly-driven construction)
    """
    print("\n" + "=" * 64)
    print("EVENT DETECTION RATE")
    print("=" * 64)

    results = []

    for origin_filter, label in [
        ("scheduled", "Scheduled events only (independent ground truth)"),
        (None, "All events (upper bound, anomaly-driven caveat)"),
    ]:
        if origin_filter:
            evt_subset = events.loc[events["event_origin"] == origin_filter].copy()
        else:
            evt_subset = events.copy()

        detected = 0
        not_detected = 0
        details = []

        for _, evt in evt_subset.iterrows():
            ws_candidates = []
            evt_date = evt["event_date"]
            evt_end = evt["event_end_date"]

            for _, anom in all_anomalies.iterrows():
                anom_ws = anom["week_start"]
                anom_we = anom_ws + timedelta(days=6)

                # Window check
                if pd.notna(evt_end):
                    in_window = evt_date <= anom_we and evt_end >= anom_ws
                else:
                    in_window = anom_ws <= evt_date <= anom_we

                if not in_window:
                    continue

                # Brand check
                if pd.isna(evt["brand"]):
                    ws_candidates.append(anom)
                elif evt["brand"] == anom.get("brand"):
                    ws_candidates.append(anom)

            is_detected = len(ws_candidates) > 0
            if is_detected:
                detected += 1
            else:
                not_detected += 1

            details.append({
                "event_id": evt["event_id"],
                "event_name": evt["event_name"],
                "event_origin": evt["event_origin"],
                "detected": is_detected,
                "n_anomalies": len(ws_candidates),
            })

        total = len(evt_subset)
        rate = detected / total if total > 0 else 0

        print(f"\n  {label}:")
        print(f"    Events: {total}")
        print(f"    Detected by anomaly: {detected} ({rate:.1%})")
        print(f"    Not detected: {not_detected}")

        if not_detected > 0:
            print("    Undetected events:")
            for d in details:
                if not d["detected"]:
                    print(f"      [{d['event_id']}] {d['event_name']}")

        results.append({
            "scope": origin_filter or "all",
            "total_events": total,
            "detected": detected,
            "not_detected": not_detected,
            "detection_rate": round(rate, 3),
        })

    return results


# ================================================================
# REPORTING
# ================================================================

def print_report(precision_results, edr_results):
    """Print final 2x2 reporting matrix."""
    print("\n" + "=" * 64)
    print("FINAL REPORTING MATRIX")
    print("=" * 64)
    print(f"Coverage: {COVERAGE_START.strftime('%Y-%m')} ~ "
          f"{COVERAGE_END.strftime('%Y-%m')} (14/40 months)")

    print("\n--- PRECISION ---")
    for p in precision_results:
        print(f"  {p['scope']:30s}  "
              f"{p['matched']}/{p['total']} = {p['precision_all']:.1%} "
              f"(ex macro: {p['precision_ex_macro']:.1%})")

    print("\n--- EVENT DETECTION RATE ---")
    for e in edr_results:
        caveat = " [upper bound, anomaly-driven]" if e["scope"] == "all" else ""
        print(f"  {e['scope']:30s}  "
              f"{e['detected']}/{e['total_events']} = {e['detection_rate']:.1%}"
              f"{caveat}")

    print("\nNote: 'Event Detection Rate' is used instead of 'Recall' because "
          "events_calendar was constructed anomaly-driven, structurally "
          "overestimating true Recall.")


# ================================================================
# VISUALIZATION
# ================================================================

def plot_matching_summary(matched_df, events):
    """Plot matching result summary."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "AppleGothic",
        "axes.unicode_minus": False,
        "figure.dpi": 150,
    })

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: matched vs unmatched by tier
    t1 = matched_df.loc[matched_df["tier"] == 1]
    t2 = matched_df.loc[matched_df["tier"] == 2]
    categories = ["Tier 1", "Tier 2"]
    matched_counts = [t1["matched"].sum(), t2["matched"].sum()]
    unmatched_counts = [
        len(t1) - t1["matched"].sum(),
        len(t2) - t2["matched"].sum(),
    ]

    x = range(len(categories))
    w = 0.35
    axes[0].bar([i - w/2 for i in x], matched_counts, w,
                label="Matched", color="#2ECC71")
    axes[0].bar([i + w/2 for i in x], unmatched_counts, w,
                label="Unmatched", color="#E74C3C")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(categories)
    axes[0].set_ylabel("Anomaly count")
    axes[0].set_title("Event Matching by Tier")
    axes[0].legend()

    for i, (m, u) in enumerate(zip(matched_counts, unmatched_counts)):
        axes[0].text(i - w/2, m + 0.3, str(int(m)), ha="center", fontsize=11)
        axes[0].text(i + w/2, u + 0.3, str(int(u)), ha="center", fontsize=11)

    # Right: event detection rate
    evt_types = events["event_origin"].value_counts()
    labels = evt_types.index.tolist()
    counts = evt_types.values.tolist()
    colors = ["#3498DB", "#F39C12"]
    axes[1].bar(labels, counts, color=colors)
    axes[1].set_ylabel("Event count")
    axes[1].set_title("Events by Origin")

    for i, c in enumerate(counts):
        axes[1].text(i, c + 0.3, str(c), ha="center", fontsize=11)

    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, "event_matching_summary.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig_path}")


# ================================================================
# SAVE OUTPUTS
# ================================================================

def save_outputs(matched_df, precision_results, edr_results):
    """Save matching results and evaluation metrics."""
    matched_df.to_csv(
        os.path.join(OUT_DIR, "matched_anomalies.csv"), index=False
    )

    metrics = pd.DataFrame(precision_results + edr_results)
    metrics.to_csv(
        os.path.join(OUT_DIR, "evaluation_metrics.csv"), index=False
    )

    print(f"Saved: {OUT_DIR}/matched_anomalies.csv")
    print(f"Saved: {OUT_DIR}/evaluation_metrics.csv")


# ================================================================
# MAIN
# ================================================================

def main():
    # Load data
    events = load_events()
    targets = load_targets()
    all_anomalies = load_all_anomalies()

    # Run matching
    print("\nRunning event matching")
    matched = run_matching(targets, events)

    # Filter to coverage period for Precision
    print("\nApplying coverage period filter")
    matched_cov = filter_coverage_period(matched)

    # Precision: Tier 1 only
    print("\n" + "=" * 64)
    print("PRECISION")
    print("=" * 64)

    precision_results = []

    t1_cov = matched_cov.loc[matched_cov["tier"] == 1]
    p1 = compute_precision(t1_cov, "Tier 1 only")
    if p1:
        precision_results.append(p1)

    # Precision: Tier 1 + 2
    p12 = compute_precision(matched_cov, "Tier 1 + Tier 2")
    if p12:
        precision_results.append(p12)

    # Event Detection Rate
    # Use all anomalies (not just targets) for checking if events were detected
    edr_results = compute_event_detection_rate(events, all_anomalies)

    # Final report
    print_report(precision_results, edr_results)

    # Visualization
    print("\nGenerating plots")
    plot_matching_summary(matched_cov, events)

    # Save
    save_outputs(matched, precision_results, edr_results)


if __name__ == "__main__":
    main()
