"""
Google Trends Chunk Stitcher
Merges overlapping CSV chunks into a single continuous weekly time series.

Each chunk is independently normalized 0-100 by Google.
Overlap periods are used to compute scale ratios between adjacent chunks.

Usage:
  python stitch_gtrends.py data/raw/google_trends/brands_kr_web_chunk*.csv \
    --output data/raw/google_trends/brands_kr_web.csv

Naming convention for chunks (download order):
  brands_kr_web_chunk1.csv   (2023-04-01 ~ 2024-04-15)
  brands_kr_web_chunk2.csv   (2024-04-01 ~ 2025-04-15)
  brands_kr_web_chunk3.csv   (2025-04-01 ~ 2026-04-15)
"""

import argparse
import glob
import os
import sys

import pandas as pd


def parse_google_trends_csv(filepath):
    """Parse a single Google Trends CSV, return DataFrame with datetime index."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        raw_lines = f.readlines()

    # Detect header row
    header_row = None
    for skip in range(4):
        try:
            df = pd.read_csv(filepath, skiprows=skip, encoding="utf-8-sig")
            if len(df.columns) >= 2 and len(df) > 3:
                first_val = str(df.iloc[0, 0]).strip()
                if first_val[:2] == "20":
                    header_row = skip
                    break
        except Exception:
            continue

    if header_row is None:
        header_row = 0

    df = pd.read_csv(filepath, skiprows=header_row, encoding="utf-8-sig")
    date_col = df.columns[0]
    keyword_cols = list(df.columns[1:])

    # Handle '<1' values
    for col in keyword_cols:
        if df[col].dtype == object:
            df[col] = df[col].replace("<1", "0.5")
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df[date_col] = pd.to_datetime(df[date_col].str.strip(), errors="coerce")
    df = df.dropna(subset=[date_col])
    df = df.rename(columns={date_col: "date"})
    df = df.sort_values("date").reset_index(drop=True)

    return df, keyword_cols


def find_overlap(df_prev, df_curr):
    """Find overlapping date range between two chunks."""
    prev_end = df_prev["date"].max()
    curr_start = df_curr["date"].min()

    if curr_start > prev_end:
        return None, None

    overlap_mask_prev = df_prev["date"] >= curr_start
    overlap_mask_curr = df_curr["date"] <= prev_end

    return overlap_mask_prev, overlap_mask_curr


def compute_scale_ratio(df_prev, df_curr, keyword_cols, overlap_prev, overlap_curr):
    """
    Compute scale ratio using overlap period.
    ratio = mean(prev_overlap) / mean(curr_overlap) for each keyword.
    """
    ratios = {}
    for col in keyword_cols:
        prev_vals = df_prev.loc[overlap_prev, col].values
        curr_vals = df_curr.loc[overlap_curr, col].values

        # Align by date
        prev_dates = df_prev.loc[overlap_prev, "date"].values
        curr_dates = df_curr.loc[overlap_curr, "date"].values
        common_dates = set(prev_dates) & set(curr_dates)

        if not common_dates:
            ratios[col] = 1.0
            continue

        prev_mean = df_prev.loc[
            overlap_prev & df_prev["date"].isin(common_dates), col
        ].mean()
        curr_mean = df_curr.loc[
            overlap_curr & df_curr["date"].isin(common_dates), col
        ].mean()

        if curr_mean > 0:
            ratios[col] = prev_mean / curr_mean
        else:
            ratios[col] = 1.0

    return ratios


def stitch_chunks(chunks, keyword_cols):
    """
    Stitch multiple chunks into a single DataFrame.
    First chunk is the reference (scale = 1.0).
    Each subsequent chunk is scaled using overlap with the previous.
    """
    if not chunks:
        return pd.DataFrame()

    # Start with first chunk as reference
    stitched = chunks[0].copy()
    cumulative_ratios = {col: 1.0 for col in keyword_cols}

    for i in range(1, len(chunks)):
        df_prev = chunks[i - 1]
        df_curr = chunks[i]

        overlap_prev, overlap_curr = find_overlap(df_prev, df_curr)

        if overlap_prev is None or overlap_prev.sum() == 0:
            print(f"  [WARN] No overlap between chunk {i} and chunk {i+1}.")
            print(f"    Prev ends: {df_prev['date'].max()}")
            print(f"    Curr starts: {df_curr['date'].min()}")
            print(f"    Appending without scaling.")
            ratios = {col: 1.0 for col in keyword_cols}
        else:
            overlap_count = overlap_prev.sum()
            print(f"  Chunk {i} -> {i+1}: {overlap_count} overlapping data points")
            ratios = compute_scale_ratio(
                df_prev, df_curr, keyword_cols, overlap_prev, overlap_curr
            )
            for col in keyword_cols:
                print(f"    {col}: ratio = {ratios[col]:.4f}")

        # Update cumulative ratios
        for col in keyword_cols:
            cumulative_ratios[col] *= ratios[col]

        # Scale current chunk
        scaled = df_curr.copy()
        for col in keyword_cols:
            scaled[col] = scaled[col] * cumulative_ratios[col]

        # Remove overlap dates from current chunk (keep prev's version)
        if overlap_curr is not None:
            prev_max_date = df_prev["date"].max()
            scaled = scaled[scaled["date"] > prev_max_date]

        stitched = pd.concat([stitched, scaled], ignore_index=True)

    # Re-normalize to 0-100 (max across all keywords = 100)
    max_val = stitched[keyword_cols].max().max()
    if max_val > 0:
        for col in keyword_cols:
            stitched[col] = (stitched[col] / max_val * 100).round(2)

    stitched = stitched.sort_values("date").reset_index(drop=True)
    return stitched


def main():
    parser = argparse.ArgumentParser(description="Stitch Google Trends CSV chunks")
    parser.add_argument(
        "files",
        nargs="+",
        help="CSV chunk files in chronological order, or glob pattern",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output path for stitched CSV",
    )
    args = parser.parse_args()

    # Expand globs and sort
    files = []
    for f in args.files:
        expanded = glob.glob(f)
        files.extend(expanded)
    files = sorted(set(files))

    if len(files) < 2:
        print(f"[ERROR] Need at least 2 chunk files. Found: {len(files)}")
        print("  For a single file, no stitching needed.")
        sys.exit(1)

    print(f"Stitching {len(files)} chunks:")
    for f in files:
        print(f"  - {os.path.basename(f)}")

    # Parse all chunks
    chunks = []
    keyword_cols = None
    for f in files:
        df, cols = parse_google_trends_csv(f)
        if keyword_cols is None:
            keyword_cols = cols
        else:
            if set(cols) != set(keyword_cols):
                print(f"  [WARN] Column mismatch in {os.path.basename(f)}")
                print(f"    Expected: {keyword_cols}")
                print(f"    Got: {cols}")
        chunks.append(df)
        print(f"  {os.path.basename(f)}: {len(df)} rows, "
              f"{df['date'].min().strftime('%Y-%m-%d')} ~ "
              f"{df['date'].max().strftime('%Y-%m-%d')}")

    # Stitch
    print(f"\nStitching...")
    result = stitch_chunks(chunks, keyword_cols)

    # Save
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    result.to_csv(args.output, index=False)

    print(f"\nDone.")
    print(f"  Output: {args.output}")
    print(f"  Rows: {len(result)}")
    print(f"  Date range: {result['date'].min().strftime('%Y-%m-%d')} ~ "
          f"{result['date'].max().strftime('%Y-%m-%d')}")
    print(f"  Keywords: {keyword_cols}")

    # Quick stats
    print(f"\nKeyword statistics (stitched, re-normalized 0-100):")
    print(f"{'Keyword':<30} {'Mean':>8} {'Max':>8} {'Min':>8}")
    print("-" * 60)
    for col in keyword_cols:
        vals = result[col].dropna()
        print(f"{col:<30} {vals.mean():>8.1f} {vals.max():>8.1f} {vals.min():>8.1f}")


if __name__ == "__main__":
    main()
