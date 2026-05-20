"""
Stage 3 Step B2 — Full Corpus Sentiment Scoring

Applies keyword dictionary (product category) to all raw.naver_blog_raw texts.
Generates Anthropic Batch API JSONL for uncertain cases.

Pipeline:
  1. Keyword scoring → staging.blog_sentiment (all rows)
  2. Uncertain + non-sponsored → data/batch/sentiment_batch.jsonl
  3. Submit JSONL to Anthropic Batch API (manual or via --submit)
  4. After API response: python -m analysis.sentiment_scorer --ingest-results

Usage:
    python -m analysis.sentiment_scorer
    python -m analysis.sentiment_scorer --dry-run
    python -m analysis.sentiment_scorer --ingest-results data/batch/sentiment_results.jsonl
"""

import matplotlib

import argparse
import json
import os
import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from database.connection import get_conn
from analysis.sentiment_dictionary import (
    score_text, classify_sentiment, detect_sponsorship,
    BRAND_COLORS,
)

# CONSTANTS

FIG_DIR = "figures/sentiment"
BATCH_DIR = "data/batch"
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(BATCH_DIR, exist_ok=True)

BATCH_JSONL_PATH = os.path.join(BATCH_DIR, "sentiment_batch.jsonl")
COST_LOG_PATH = os.path.join(BATCH_DIR, "cost_log.csv")

THRESHOLD = 0.3
BATCH_MODEL = "claude-haiku-4-5-20251001"

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (12, 6),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

# System prompt for API sentiment classification
API_SYSTEM_PROMPT = """You are a Korean sportswear product sentiment classifier.
Classify the following blog/cafe text about a sportswear brand into exactly one label:
- positive: the author expresses satisfaction with the product
- negative: the author expresses dissatisfaction with the product
- neutral: the text is informational with no clear sentiment

Respond with ONLY a JSON object: {"label": "positive|negative|neutral", "confidence": 0.0-1.0}
No other text."""


# DATA FETCH

def fetch_all_blog_cafe():
    """Fetch all blog/cafe texts from raw."""
    query = """
        SELECT id, source_type, brand, query_keyword, title, description
        FROM raw.naver_blog_raw
        WHERE description IS NOT NULL
        ORDER BY id
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn)
    return df


# KEYWORD SCORING (1ST PASS)

def score_all(df):
    """Apply keyword scoring to all rows."""
    print(f"  Scoring {len(df)} texts...")

    scores = []
    n_matches_list = []
    labels = []
    confidences = []
    sponsored = []

    for i, row in df.iterrows():
        text = f"{row['title'] or ''} {row['description'] or ''}"

        spons = detect_sponsorship(text)
        sponsored.append(spons)

        score, n_matches, matched = score_text(text, category_filter="product")
        label, confidence = classify_sentiment(score, THRESHOLD)

        scores.append(score)
        n_matches_list.append(n_matches)
        labels.append(label)
        confidences.append(confidence)

        if (i + 1) % 2000 == 0:
            print(f"    Scored {i + 1}/{len(df)}...")

    df["keyword_score"] = scores
    df["keyword_n_matches"] = n_matches_list
    df["keyword_label"] = labels
    df["confidence_source"] = confidences
    df["is_sponsored"] = sponsored

    # Final label: for keyword-resolved cases, set immediately
    df["final_label"] = df["keyword_label"]
    df["final_source"] = "keyword"
    # Uncertain cases: final_label stays 'uncertain' until API resolves
    df.loc[df["keyword_label"] == "uncertain", "final_source"] = "pending"

    return df


# DATABASE WRITE

def save_to_db(df):
    """Insert scoring results into staging.blog_sentiment."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clear previous results
            cur.execute("TRUNCATE staging.blog_sentiment RESTART IDENTITY")
            print("  Truncated staging.blog_sentiment")

            total = 0
            for _, row in df.iterrows():
                cur.execute("""
                    INSERT INTO staging.blog_sentiment
                        (raw_id, source_type, brand,
                         keyword_score, keyword_label, keyword_n_matches,
                         is_sponsored, final_label, final_source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    int(row["id"]), row["source_type"], row["brand"],
                    float(row["keyword_score"]), row["keyword_label"],
                    int(row["keyword_n_matches"]),
                    bool(row["is_sponsored"]),
                    row["final_label"], row["final_source"],
                ))
                total += 1

            conn.commit()
            print(f"  Inserted {total} rows into staging.blog_sentiment")


# BATCH API JSONL GENERATION

def generate_batch_jsonl(df):
    """Generate JSONL for uncertain + non-sponsored cases."""
    # Filter: uncertain AND not sponsored
    uncertain = df[
        (df["keyword_label"] == "uncertain") &
        (~df["is_sponsored"])
    ].copy()

    n_uncertain = len(uncertain)
    print(f"\n  === Batch API Preparation ===")
    print(f"  Uncertain cases: {n_uncertain}")

    if n_uncertain == 0:
        print("  No uncertain cases to submit")
        return 0

    # Generate JSONL
    with open(BATCH_JSONL_PATH, "w", encoding="utf-8") as f:
        for _, row in uncertain.iterrows():
            text = f"{row['title'] or ''}\n{row['description'] or ''}"
            # Truncate to ~500 chars to control token usage
            text = text[:500]

            request = {
                "custom_id": f"raw_{int(row['id'])}",
                "params": {
                    "model": BATCH_MODEL,
                    "max_tokens": 50,
                    "system": API_SYSTEM_PROMPT,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Brand: {row['brand']}\n\n{text}",
                        }
                    ],
                },
            }
            f.write(json.dumps(request, ensure_ascii=False) + "\n")

    print(f"  JSONL saved: {BATCH_JSONL_PATH}")
    print(f"  Total requests: {n_uncertain}")

    # Cost estimate
    avg_input_tokens = 120  # system + text
    avg_output_tokens = 25   # JSON response
    # Batch API: 50% discount on standard pricing
    # Haiku: $0.80/1M input, $4.00/1M output (standard), halved for batch
    input_cost = n_uncertain * avg_input_tokens * 0.40 / 1e6
    output_cost = n_uncertain * avg_output_tokens * 2.00 / 1e6
    total_cost = input_cost + output_cost
    total_krw = total_cost * 1400

    print(f"\n  === Batch Cost Estimate ===")
    print(f"  Input: {n_uncertain} x ~{avg_input_tokens} tokens = ${input_cost:.6f}")
    print(f"  Output: {n_uncertain} x ~{avg_output_tokens} tokens = ${output_cost:.6f}")
    print(f"  Total: ${total_cost:.6f} (~{total_krw:.1f} KRW)")
    print(f"  (Batch API 50% discount applied)")

    # Initialize cost log
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "stage": "B2_batch_submit",
        "n_requests": n_uncertain,
        "model": BATCH_MODEL,
        "est_cost_usd": round(total_cost, 6),
        "est_cost_krw": round(total_krw, 1),
        "status": "prepared",
    }
    log_df = pd.DataFrame([log_entry])
    if os.path.exists(COST_LOG_PATH):
        existing = pd.read_csv(COST_LOG_PATH)
        log_df = pd.concat([existing, log_df], ignore_index=True)
    log_df.to_csv(COST_LOG_PATH, index=False)
    print(f"  Cost log: {COST_LOG_PATH}")

    return n_uncertain


# INGEST API RESULTS

def ingest_results(results_path):
    """Ingest Batch API results and update staging.blog_sentiment."""
    print(f"  Reading results from: {results_path}")

    results = []
    with open(results_path, "r", encoding="utf-8") as f:
        for line in f:
            results.append(json.loads(line))

    print(f"  Total results: {len(results)}")

    updated = 0
    errors = 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            for result in results:
                custom_id = result.get("custom_id", "")
                raw_id = int(custom_id.replace("raw_", ""))

                # Extract response
                try:
                    response = result.get("result", {})
                    message = response.get("message", {})
                    content = message.get("content", [{}])
                    text = content[0].get("text", "{}") if content else "{}"
                    # Strip code fences
                    text = text.strip().removeprefix("```json").removesuffix("```").strip()
                    parsed = json.loads(text)

                    # Parse JSON response
                    parsed = json.loads(text.strip())
                    api_label = parsed.get("label", "neutral")
                    api_confidence = float(parsed.get("confidence", 0.5))

                    # Validate label
                    if api_label not in ("positive", "negative", "neutral"):
                        api_label = "neutral"

                except (json.JSONDecodeError, KeyError, IndexError, ValueError):
                    api_label = "neutral"
                    api_confidence = 0.0
                    errors += 1

                cur.execute("""
                    UPDATE staging.blog_sentiment
                    SET api_label = %s,
                        api_confidence = %s,
                        final_label = %s,
                        final_source = 'api'
                    WHERE raw_id = %s
                """, (api_label, api_confidence, api_label, raw_id))
                updated += 1

            conn.commit()

    print(f"  Updated: {updated}")
    if errors > 0:
        print(f"  Parse errors (defaulted to neutral): {errors}")

    # Update cost log
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "stage": "B2_batch_ingest",
        "n_requests": len(results),
        "model": BATCH_MODEL,
        "est_cost_usd": 0,
        "est_cost_krw": 0,
        "status": "ingested",
    }
    log_df = pd.DataFrame([log_entry])
    if os.path.exists(COST_LOG_PATH):
        existing = pd.read_csv(COST_LOG_PATH)
        log_df = pd.concat([existing, log_df], ignore_index=True)
    log_df.to_csv(COST_LOG_PATH, index=False)


# SUMMARY

def print_summary(df):
    """Print full corpus scoring summary."""
    n = len(df)
    n_sponsored = df["is_sponsored"].sum()
    n_organic = n - n_sponsored

    print(f"\n  === Full Corpus Scoring Summary ===")
    print(f"  Total texts: {n}")
    print(f"  Sponsored: {n_sponsored} ({n_sponsored/n*100:.1f}%)")
    print(f"  Organic: {n_organic} ({n_organic/n*100:.1f}%)")

    # Classification breakdown
    print(f"\n  --- All texts (threshold={THRESHOLD}) ---")
    for lbl in ["positive", "negative", "neutral", "uncertain"]:
        cnt = (df["keyword_label"] == lbl).sum()
        print(f"  {lbl:<12}: {cnt:>6} ({cnt/n*100:>5.1f}%)")

    # Routing
    keyword_count = (df["confidence_source"] == "keyword").sum()
    api_count = (df["confidence_source"] == "needs_api").sum()
    print(f"\n  --- Routing ---")
    print(f"  Keyword resolved: {keyword_count} ({keyword_count/n*100:.1f}%)")
    print(f"  Needs API:        {api_count} ({api_count/n*100:.1f}%)")

    # By brand (organic only)
    organic = df[~df["is_sponsored"]]
    print(f"\n  --- By Brand (organic, n={len(organic)}) ---")
    print(f"  {'Brand':<15} {'n':>5} {'pos':>5} {'neg':>5} {'neu':>5} {'unc':>5} {'avg':>8}")
    for brand in ["new_balance", "nike", "adidas", "puma"]:
        bdf = organic[organic["brand"] == brand]
        if bdf.empty:
            continue
        bn = len(bdf)
        pos = (bdf["keyword_label"] == "positive").sum()
        neg = (bdf["keyword_label"] == "negative").sum()
        neu = (bdf["keyword_label"] == "neutral").sum()
        unc = (bdf["keyword_label"] == "uncertain").sum()
        avg = bdf["keyword_score"].mean()
        print(f"  {brand:<15} {bn:>5} {pos:>5} {neg:>5} {neu:>5} {unc:>5} {avg:>+8.4f}")

    # By source type
    print(f"\n  --- By Source Type ---")
    for st in df["source_type"].unique():
        sdf = df[df["source_type"] == st]
        sn = len(sdf)
        avg = sdf["keyword_score"].mean()
        print(f"  {st:<15} n={sn:>5}  avg={avg:>+.4f}")


# VISUALIZATION

def plot_full_distribution(df):
    """Score distribution for full corpus."""
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.hist(df["keyword_score"], bins=50, color="#3498DB", alpha=0.7, edgecolor="white")
    ax.axvline(x=THRESHOLD, color="red", linewidth=1.5, linestyle="--",
               label=f"threshold={THRESHOLD}")
    ax.axvline(x=-THRESHOLD, color="red", linewidth=1.5, linestyle="--")
    ax.set_title(f"Full Corpus Product Score Distribution (n={len(df)})",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("Product Keyword Score")
    ax.set_ylabel("Count")
    ax.legend()

    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, "full_corpus_score_distribution.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"\n  Saved: {fig_path}")


# CLI / MAIN

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 3 Step B2: Full corpus keyword scoring + Batch API prep"
    )
    parser.add_argument("--submit", action="store_true",
                        help="Submit JSONL to Anthropic Batch API")
    parser.add_argument("--dry-run", action="store_true",
                        help="Score and print summary without DB write")
    parser.add_argument("--ingest-results", type=str, default=None,
                        help="Path to Batch API results JSONL to ingest")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Stage 3 Step B2: Full Corpus Sentiment Scoring")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Ingest mode
    if args.ingest_results:
        ingest_results(args.ingest_results)
        print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return

    # Submit mode
    if args.submit:
        from dotenv import load_dotenv
        import requests as req
        load_dotenv()

        if not os.path.exists(BATCH_JSONL_PATH):
            print(f"  [ERROR] JSONL not found: {BATCH_JSONL_PATH}")
            return

        print(f"  Submitting {BATCH_JSONL_PATH} to Anthropic Batch API...")
        api_key = os.getenv("ANTHROPIC_API_KEY")

        with open(BATCH_JSONL_PATH, "r", encoding="utf-8") as f:
            requests_list = [json.loads(line) for line in f]

        resp = req.post(
            "https://api.anthropic.com/v1/messages/batches",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"requests": requests_list},
            timeout=120,
        )

        if resp.status_code == 200:
            data = resp.json()
            print(f"  Batch ID: {data['id']}")
            print(f"  Status: {data['processing_status']}")
        else:
            print(f"  [ERROR] {resp.status_code}: {resp.text[:500]}")
        return

    # Score mode
    df = fetch_all_blog_cafe()
    print(f"  Fetched {len(df)} texts from raw.naver_blog_raw")

    df = score_all(df)
    print_summary(df)

    if not args.dry_run:
        save_to_db(df)
        n_batch = generate_batch_jsonl(df)
        plot_full_distribution(df)

        if n_batch > 0:
            print(f"\n  === Next Steps ===")
            print(f"  1. Submit batch: anthropic batches create --file {BATCH_JSONL_PATH}")
            print(f"  2. Check status: anthropic batches list")
            print(f"  3. Download results when complete")
            print(f"  4. Ingest: python -m analysis.sentiment_scorer --ingest-results <results.jsonl>")

    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
