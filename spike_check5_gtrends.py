"""
Check 5: Google Trends Manual CSV Download Validation
Run after downloading CSV from trends.google.com into data/raw/google_trends/

Usage: python spike_check5_gtrends.py
"""

import glob
import os
import sys
import time

import pandas as pd


RAW_DIR = "data/raw/google_trends"


def find_csv_files():
    """Find all CSV files in the raw directory."""
    if not os.path.isdir(RAW_DIR):
        print(f"[ERROR] Directory not found: {RAW_DIR}")
        print(f"Create it and place Google Trends CSV files inside:")
        print(f"  mkdir -p {RAW_DIR}")
        return []

    files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
    if not files:
        print(f"[ERROR] No CSV files found in {RAW_DIR}")
        print("Download from trends.google.com and place here.")
    return files


def parse_google_trends_csv(filepath):
    """
    Parse Google Trends CSV.
    Google Trends CSV format:
    - First 1-2 rows: metadata (category, region info)
    - Then header row + data rows
    - Columns: date/week, keyword1, keyword2, ...
    - Values can be '<1' (below 1) or integers 0-100
    """
    filename = os.path.basename(filepath)
    print(f"\n{'='*60}")
    print(f"File: {filename}")
    print(f"{'='*60}")

    # Read raw lines to detect structure
    with open(filepath, "r", encoding="utf-8-sig") as f:
        raw_lines = f.readlines()

    print(f"Total lines: {len(raw_lines)}")
    print(f"First 5 lines (raw):")
    for i, line in enumerate(raw_lines[:5]):
        print(f"  [{i}] {line.rstrip()}")

    # Find the header row (contains date-like pattern)
    header_row = None
    for i, line in enumerate(raw_lines):
        lower = line.lower()
        if "주" in lower or "week" in lower or "날짜" in lower or "일" in lower or "day" in lower:
            header_row = i
            break
        # Also check if line starts with a date pattern like 2024-
        parts = line.strip().split(",")
        if len(parts) >= 2 and parts[0].startswith("20"):
            header_row = max(0, i - 1)
            break

    if header_row is None:
        # Try skiprows=1,2,3 until we get a valid dataframe
        for skip in range(4):
            try:
                df = pd.read_csv(filepath, skiprows=skip, encoding="utf-8-sig")
                if len(df.columns) >= 2 and len(df) > 10:
                    header_row = skip
                    break
            except Exception:
                continue

    if header_row is None:
        print("[WARN] Could not auto-detect header row. Trying skiprows=1...")
        header_row = 1

    print(f"Detected header row: {header_row}")

    # Parse with detected header
    try:
        df = pd.read_csv(filepath, skiprows=header_row, encoding="utf-8-sig")
    except Exception as e:
        print(f"[ERROR] Failed to parse CSV: {e}")
        return None

    print(f"\nParsed shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")

    # Identify date column (first column)
    date_col = df.columns[0]
    keyword_cols = list(df.columns[1:])
    print(f"Date column: '{date_col}'")
    print(f"Keyword columns: {keyword_cols}")

    # Handle '<1' values -> 0.5
    for col in keyword_cols:
        if df[col].dtype == object:
            df[col] = df[col].replace("<1", "0.5")
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Parse dates
    df[date_col] = pd.to_datetime(df[date_col].str.strip(), errors="coerce")
    valid_dates = df[date_col].notna().sum()
    print(f"Valid date rows: {valid_dates}/{len(df)}")

    # Drop rows with invalid dates
    df = df.dropna(subset=[date_col])

    if df.empty:
        print("[ERROR] No valid data after parsing.")
        return None

    # Stats
    print(f"\nDate range: {df[date_col].min().strftime('%Y-%m-%d')} ~ {df[date_col].max().strftime('%Y-%m-%d')}")
    print(f"Data points: {len(df)}")

    # Detect granularity
    if len(df) >= 2:
        diff = (df[date_col].iloc[1] - df[date_col].iloc[0]).days
        granularity = "weekly" if 5 <= diff <= 9 else "daily" if diff <= 2 else "monthly"
        print(f"Granularity: {granularity} (interval: {diff} days)")

    print(f"\nKeyword statistics:")
    print(f"{'Keyword':<30} {'Mean':>8} {'Max':>8} {'Min':>8} {'Zeros':>8}")
    print("-" * 70)
    for col in keyword_cols:
        vals = df[col].dropna()
        if len(vals) == 0:
            print(f"{col:<30} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>8}")
            continue
        mean = vals.mean()
        mx = vals.max()
        mn = vals.min()
        zeros = (vals == 0).sum()
        print(f"{col:<30} {mean:>8.1f} {mx:>8.1f} {mn:>8.1f} {zeros:>8}")

    print(f"\nSample data (first 5 rows):")
    print(df.head().to_string(index=False))

    print(f"\nSample data (last 5 rows):")
    print(df.tail().to_string(index=False))

    return df


def generate_check5_report(results):
    """Append Check 5 results to feasibility report."""

    lines = []
    lines.append("")
    lines.append("## Check 5: Google Trends Manual CSV Validation")
    lines.append("")
    lines.append(f"**Test date:** {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Method:** Manual CSV download from trends.google.com")
    lines.append(f"**Files found:** {len(results)}")
    lines.append("")

    for filename, info in results.items():
        lines.append(f"### {filename}")
        lines.append("")
        if info is None:
            lines.append("- **Status:** PARSE FAILED")
        else:
            lines.append(f"- **Status:** OK")
            lines.append(f"- **Shape:** {info['shape']}")
            lines.append(f"- **Date range:** {info['date_range']}")
            lines.append(f"- **Granularity:** {info['granularity']}")
            lines.append(f"- **Keywords:** {', '.join(info['keywords'])}")
        lines.append("")

    lines.append("### Verdict")
    lines.append("")
    ok_count = sum(1 for v in results.values() if v is not None)
    if ok_count == len(results) and ok_count > 0:
        lines.append("**PASS.** Google Trends CSV parsing pipeline works correctly.")
        lines.append("Manual CSV download is a viable primary collection method.")
    elif ok_count > 0:
        lines.append(f"**PARTIAL.** {ok_count}/{len(results)} files parsed successfully.")
        lines.append("Check failed files for encoding or format issues.")
    else:
        lines.append("**FAIL.** No CSV files parsed successfully.")
    lines.append("")
    lines.append("### Collection strategy")
    lines.append("")
    lines.append("| Download | Keywords | Region | Estimated |")
    lines.append("|---|---|---|---|")
    lines.append("| 4 brands comparison | nike, adidas, puma, new balance | Global | 1 CSV |")
    lines.append("| 4 brands comparison | nike, adidas, puma, new balance | Korea (KR) | 1 CSV |")
    lines.append("| NB product lines | new balance 530, new balance 992 | Global | 1 CSV |")
    lines.append("| NB product lines | new balance 530, new balance 992 | Korea (KR) | 1 CSV |")
    lines.append("| Cross-reference anchor | new balance 530, new balance 992, nike | Global | 1 CSV |")
    lines.append("")
    lines.append("**Total: 5 manual downloads. collector_google_trends.py will support CSV load (primary) + pytrends (optional fallback).**")

    report_path = "docs/check5_gtrends_result.md"
    os.makedirs("docs", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"\nCheck 5 report saved: {report_path}")


def main():
    print("=" * 60)
    print("Check 5: Google Trends Manual CSV Validation")
    print("=" * 60)

    files = find_csv_files()
    if not files:
        print(f"\nPlease download CSV from Google Trends:")
        print(f"  1. Go to trends.google.com")
        print(f"  2. Search: 나이키, 아디다스, 푸마, 뉴발란스")
        print(f"  3. Region: South Korea, Period: Past 2 years")
        print(f"  4. Click download (arrow icon)")
        print(f"  5. Save to: {RAW_DIR}/")
        print(f"  6. Re-run this script")
        sys.exit(1)

    print(f"\nFound {len(files)} CSV file(s):")
    for f in files:
        print(f"  - {os.path.basename(f)}")

    results = {}
    for filepath in files:
        df = parse_google_trends_csv(filepath)
        filename = os.path.basename(filepath)
        if df is not None:
            date_col = df.columns[0]
            diff = 7
            if len(df) >= 2:
                diff = (df[date_col].iloc[1] - df[date_col].iloc[0]).days
            results[filename] = {
                "shape": f"{df.shape[0]} rows x {df.shape[1]} cols",
                "date_range": f"{df[date_col].min().strftime('%Y-%m-%d')} ~ {df[date_col].max().strftime('%Y-%m-%d')}",
                "granularity": "weekly" if 5 <= diff <= 9 else "daily" if diff <= 2 else "monthly",
                "keywords": list(df.columns[1:]),
            }
        else:
            results[filename] = None

    generate_check5_report(results)

    print("\n" + "=" * 60)
    print("Check 5 complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
