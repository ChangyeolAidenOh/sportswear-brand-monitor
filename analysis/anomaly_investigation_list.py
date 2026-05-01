"""
Stage 5 Track D Step 1 — Investigation Target List

Extracts anomalies where 2+ detection methods agree,
enriches with severity info, and outputs a prioritized
list for manual events_calendar research.

Usage:
    python analysis/anomaly_investigation_list.py
"""

# stdlib
import os
import sys

# third-party
import pandas as pd
import numpy as np

# ================================================================
# CONSTANTS
# ================================================================

COMP_CSV = "data/anomaly/three_way_comparison.csv"
MSTL_CSV = "data/anomaly/mstl_residual_anomalies_2.0.csv"
IF_CSV = "data/anomaly/isolation_forest_anomalies.csv"
OUT_DIR = "data/anomaly"


# ================================================================
# MAIN
# ================================================================

def main():
    # Load 3-way comparison
    comp = pd.read_csv(COMP_CSV)
    comp["week_start"] = pd.to_datetime(comp["week_start"])

    # Load MSTL z-scores
    mstl = pd.read_csv(MSTL_CSV)
    mstl["week_start"] = pd.to_datetime(mstl["week_start"])
    mstl_z = mstl[["brand", "region", "week_start", "z_score", "residual"]].rename(
        columns={"z_score": "mstl_z", "residual": "mstl_residual"}
    )

    # Load IF scores
    if_df = pd.read_csv(IF_CSV)
    if_df["week_start"] = pd.to_datetime(if_df["week_start"])
    if_scores = if_df[["brand", "region", "week_start", "if_score"]].copy()

    # Filter: 2+ methods agree
    multi = comp.loc[comp["n_methods"] >= 2].copy()
    multi = multi.merge(mstl_z, on=["brand", "region", "week_start"], how="left")
    multi = multi.merge(if_scores, on=["brand", "region", "week_start"], how="left")

    # Method agreement label
    multi["methods"] = multi.apply(
        lambda r: "+".join(
            [m for m, flag in [("Z", r["zscore"]), ("M", r["mstl"]),
                               ("IF", r["isolation_forest"])] if flag]
        ), axis=1
    )
    multi["abs_z"] = multi["mstl_z"].abs()

    # ============================================================
    # TIER 1: Z-score included in agreement (independent cross-validation)
    # ============================================================
    tier1 = multi.loc[multi["zscore"] == True].copy()
    tier1["tier"] = 1

    # ============================================================
    # TIER 2: M+IF only, macro_event or multi_brand weeks only
    # (brand_specific excluded — no independent cross-validation)
    # ============================================================
    mif_only = multi.loc[multi["zscore"] == False].copy()

    # Count unique brands per week among M+IF anomalies
    week_brand_counts = (
        mif_only.groupby("week_start")["brand"]
        .nunique()
        .reset_index(name="n_brands_in_week")
    )
    mif_only = mif_only.merge(week_brand_counts, on="week_start", how="left")

    # Keep only weeks with 2+ brands (macro_event or multi_brand)
    tier2 = mif_only.loc[mif_only["n_brands_in_week"] >= 2].copy()
    tier2["tier"] = 2

    # ============================================================
    # Combine and classify
    # ============================================================
    targets = pd.concat([tier1, tier2], ignore_index=True)

    # Classify investigation type
    week_brand_all = (
        targets.groupby("week_start")["brand"]
        .nunique()
        .reset_index(name="n_brands_week")
    )
    targets = targets.merge(week_brand_all, on="week_start", how="left")

    def classify_type(row):
        if row["n_brands_week"] >= 3:
            return "macro_event"
        elif row["n_brands_week"] == 2:
            return "multi_brand"
        elif row["brand"] == "new_balance":
            return "nb_specific"
        else:
            return "brand_specific"

    targets["likely_type"] = targets.apply(classify_type, axis=1)

    # Sort: tier first, then by abs_z
    targets = targets.sort_values(["tier", "abs_z"], ascending=[True, False])

    # Output columns
    out_cols = [
        "tier", "brand", "region", "week_start", "n_methods", "methods",
        "mstl_z", "if_score", "likely_type"
    ]
    out = targets[out_cols].copy()
    out["mstl_z"] = out["mstl_z"].round(2)
    out["if_score"] = out["if_score"].round(4)

    # Print
    print("=" * 80)
    print(f"INVESTIGATION TARGET LIST — TIERED ({len(out)} total)")
    print("=" * 80)

    t1 = out.loc[out["tier"] == 1]
    print(f"\nTIER 1: Z-score cross-validated ({len(t1)} anomalies)")
    print("  Independent cross-validation: raw z-score + MSTL residual agree")
    print(t1.to_string(index=False))

    t2 = out.loc[out["tier"] == 2]
    print(f"\nTIER 2: M+IF with high severity or multi-brand ({len(t2)} anomalies)")
    print("  Caveat: M and IF share same input — agreement is not independent")
    print(t2.to_string(index=False))

    # Summary
    print(f"\nTotal: {len(out)} (Tier 1: {len(t1)}, Tier 2: {len(t2)})")
    unique_weeks = sorted(out["week_start"].unique())
    print(f"Unique weeks: {len(unique_weeks)}")

    print("\nBy investigation type:")
    for t, grp in out.groupby("likely_type"):
        print(f"  {t:15s} {len(grp):3d}")

    # Precision/Recall note
    print("\nPrecision/Recall reporting plan:")
    print(f"  Tier 1 Precision: matched / {len(t1)} (independent cross-validation)")
    print(f"  Tier 1+2 Precision: matched / {len(out)} (full scope, separate report)")

    # ============================================================       <-- 여기부터
    # WEEK-GROUPED INVESTIGATION PLAN
    # ============================================================
    print("\n" + "=" * 80)
    print("INVESTIGATION PLAN (grouped by week_start)")
    print("=" * 80)

    week_groups = []
    for ws, grp in targets.groupby("week_start"):
        tiers = sorted(grp["tier"].unique())
        brands = sorted(grp["brand"].unique())
        regions = sorted(grp["region"].unique())
        top_z = grp["mstl_z"].abs().max()
        week_groups.append({
            "week_start": ws,
            "tiers": "+".join([f"T{t}" for t in tiers]),
            "n_anomalies": len(grp),
            "brands": ", ".join(brands),
            "regions": ", ".join(set(regions)),
            "max_abs_z": round(top_z, 2) if not pd.isna(top_z) else None,
        })

    week_df = pd.DataFrame(week_groups).sort_values("week_start")
    print(week_df.to_string(index=False))
    print(f"\nTotal investigation weeks: {len(week_df)}")
    print(f"Total anomaly rows covered: {len(targets)}")

    week_path = os.path.join(OUT_DIR, "investigation_weeks.csv")
    week_df.to_csv(week_path, index=False)
    print(f"Saved: {week_path}")

    # Save
    out_path = os.path.join(OUT_DIR, "investigation_targets.csv")
    out.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
