"""
Stage 3 Step B1 — Keyword-based Sentiment Dictionary (v2)

Sportswear domain sentiment dictionary with 3-way category separation:
  1. Product sentiment — comfort, design, quality (main input for social_sentiment_static)
  2. Channel/Service sentiment — shipping, returns, price (excluded from analysis)
  3. Resale sentiment — premium, limited, resale (separate label for NB limited edition)

Includes sponsorship filter to separate sponsored vs organic content.
social_sentiment_static uses non-sponsored + product sentiment only.

Usage:
    python -m analysis.sentiment_dictionary --show-dict
    python -m analysis.sentiment_dictionary --sample-test
    python -m analysis.sentiment_dictionary --sample-test --threshold 0.5
"""

# stdlib
import argparse
import os
import warnings
from collections import Counter
from datetime import datetime

# third-party
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# local
from database.connection import get_conn

# ================================================================
# CONSTANTS
# ================================================================

FIG_DIR = "figures/sentiment"
os.makedirs(FIG_DIR, exist_ok=True)

DEFAULT_N_SAMPLES = 1000

plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (12, 6),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

BRAND_COLORS = {
    "new_balance": "#E74C3C",
    "nike": "#FF6B00",
    "adidas": "#3498DB",
    "puma": "#2ECC71",
}

# ================================================================
# SPONSORSHIP FILTER
# ================================================================

SPONSORSHIP_PATTERNS = [
    "협찬", "체험단", "제공받", "소정의 원고료", "원고료",
    "광고", "협업", "제품을 제공", "무상으로 제공",
    "내돈내산 아닙", "업체로부터",
]


def detect_sponsorship(text):
    """Detect sponsorship indicators in text."""
    if not text or not isinstance(text, str):
        return False
    text_lower = text.lower()
    for pattern in SPONSORSHIP_PATTERNS:
        if pattern in text_lower:
            return True
    return False


# ================================================================
# SENTIMENT DICTIONARY — 3-WAY CATEGORY
# ================================================================
# Each keyword: (weight, category)
# Categories: 'product', 'channel', 'resale'
# ================================================================

POSITIVE_KEYWORDS = {
    # --- Product: comfort & fit ---
    "편하다": (1.0, "product"), "편해요": (1.0, "product"),
    "편함": (1.0, "product"), "편한": (1.0, "product"),
    "편하고": (1.0, "product"), "착화감": (1.0, "product"),
    "발이 편": (1.0, "product"),
    "쿠셔닝": (0.5, "product"), "가볍다": (0.5, "product"),
    "가벼워": (0.5, "product"), "가벼운": (0.5, "product"),
    "부드럽": (0.5, "product"), "푹신": (0.5, "product"),
    # --- Product: style & design ---
    "예쁘다": (0.5, "product"), "예뻐요": (0.5, "product"),
    "예쁜": (0.5, "product"), "이쁘다": (0.5, "product"),
    "이뻐요": (0.5, "product"),
    "디자인": (0.3, "product"), "감각적": (0.5, "product"),
    "세련": (0.5, "product"), "깔끔": (0.5, "product"),
    "컬러": (0.3, "product"), "색감": (0.3, "product"),
    "컬러웨이": (0.3, "product"),
    # --- Product: satisfaction ---
    "만족": (1.0, "product"), "만족스럽": (1.0, "product"),
    "대만족": (1.0, "product"),
    "추천": (0.5, "product"), "강추": (1.0, "product"),
    "강력추천": (1.0, "product"),
    "재구매": (1.0, "product"), "리오더": (1.0, "product"),
    # --- Product: durability & function ---
    "내구성": (0.5, "product"), "튼튼": (0.5, "product"),
    "오래": (0.3, "product"),
    "방수": (0.3, "product"), "통기성": (0.3, "product"),
    "접지력": (0.5, "product"),
    # --- Product: emotional ---
    "좋아요": (0.5, "product"), "좋다": (0.5, "product"),
    "좋은": (0.3, "product"), "최고": (1.0, "product"),
    "사랑": (0.5, "product"), "소장": (0.5, "product"),
    "소장가치": (0.5, "product"),
    # --- Product: purchase ---
    "득템": (0.5, "product"), "겟했": (0.5, "product"),
    "질렀다": (0.3, "product"), "질렀어": (0.3, "product"),
    # --- Product: brand perception ---
    "트렌드": (0.3, "product"), "트렌디": (0.5, "product"),
    "핫한": (0.3, "product"), "인기": (0.3, "product"),
    "고급": (0.5, "product"), "고퀄": (0.5, "product"),
    # --- Channel/Service ---
    "가성비": (0.5, "channel"), "합리적": (0.5, "channel"),
    # --- Resale ---
    "프리미엄": (0.3, "resale"),
}

NEGATIVE_KEYWORDS = {
    # --- Product: discomfort ---
    "불편": (-1.0, "product"), "불편하다": (-1.0, "product"),
    "불편해요": (-1.0, "product"),
    "좁다": (-0.5, "product"), "좁아": (-0.5, "product"),
    "좁은": (-0.5, "product"),
    "무겁다": (-0.5, "product"), "무거워": (-0.5, "product"),
    "무거운": (-0.5, "product"),
    "딱딱": (-0.5, "product"), "미끄럽": (-0.5, "product"),
    "미끄러": (-0.5, "product"),
    "발이 아프": (-1.0, "product"), "물집": (-1.0, "product"),
    "까짐": (-0.5, "product"),
    # --- Product: quality defects ---
    "하자": (-1.0, "product"), "불량": (-1.0, "product"),
    "뜯어": (-0.5, "product"), "찢어": (-0.5, "product"),
    "벗겨": (-0.5, "product"), "변색": (-0.5, "product"),
    "냄새": (-0.5, "product"), "악취": (-1.0, "product"),
    # --- Product: regret ---
    "후회": (-1.0, "product"), "실망": (-1.0, "product"),
    "실망스럽": (-1.0, "product"),
    "아쉽": (-0.5, "product"), "아쉬운": (-0.5, "product"),
    "아쉬워": (-0.5, "product"),
    "별로": (-0.5, "product"), "그저그래": (-0.5, "product"),
    "안 예쁘": (-0.5, "product"), "촌스럽": (-0.5, "product"),
    # --- Product: emotional ---
    "싫다": (-0.5, "product"), "최악": (-1.0, "product"),
    "쓰레기": (-1.0, "product"), "망했": (-0.5, "product"),
    # --- Channel/Service ---
    "비싸다": (-0.5, "channel"), "비싸": (-0.5, "channel"),
    "비싼": (-0.5, "channel"), "가격이": (-0.3, "channel"),
    "가격대": (-0.3, "channel"), "바가지": (-1.0, "channel"),
    "반품": (-1.0, "channel"), "환불": (-1.0, "channel"),
    "교환": (-0.5, "channel"),
    "배송 늦": (-0.5, "channel"), "배송 느": (-0.5, "channel"),
    "느리": (-0.3, "channel"), "가품": (-1.0, "channel"),
    "짝퉁": (-1.0, "channel"), "가짜": (-1.0, "channel"),
    # --- Resale ---
    "오버프라이스": (-0.5, "resale"),
}

# Flat lookup combining both dicts
SENTIMENT_DICT = {**POSITIVE_KEYWORDS, **NEGATIVE_KEYWORDS}


# ================================================================
# SCORING FUNCTION
# ================================================================

def score_text(text, category_filter="product"):
    """
    Score a single text using keyword dictionary.

    Args:
        text: input text
        category_filter: 'product', 'channel', 'resale', or 'all'

    Returns:
        score, n_matches, matched_keywords
    """
    if not text or not isinstance(text, str):
        return 0.0, 0, []

    text_lower = text.lower()
    matched = []
    score = 0.0

    for keyword, (weight, category) in SENTIMENT_DICT.items():
        if category_filter != "all" and category != category_filter:
            continue
        if keyword in text_lower:
            score += weight
            matched.append((keyword, weight, category))

    n_matches = len(matched)
    if n_matches > 0:
        score = score / n_matches

    return score, n_matches, matched


def classify_sentiment(score, threshold=0.3):
    """Classify sentiment based on score."""
    abs_score = abs(score)
    if abs_score >= threshold:
        label = "positive" if score > 0 else "negative"
        return label, "keyword"
    elif abs_score == 0.0:
        return "neutral", "keyword"
    else:
        return "uncertain", "needs_api"


# ================================================================
# DATA FETCH
# ================================================================

def fetch_blog_cafe_sample(n_samples=DEFAULT_N_SAMPLES):
    """Fetch random sample from raw.naver_blog_raw."""
    query = """
        SELECT id, source_type, brand, query_keyword, title, description
        FROM raw.naver_blog_raw
        WHERE description IS NOT NULL
          AND LENGTH(description) > 20
        ORDER BY RANDOM()
        LIMIT %s
    """
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
            df = pd.read_sql(query, conn, params=(n_samples,))
    return df


# ================================================================
# SAMPLE TEST
# ================================================================

def run_sample_test(n_samples=DEFAULT_N_SAMPLES, threshold=0.3):
    """Run keyword scoring on random sample with sponsorship detection."""
    print(f"  Fetching {n_samples} random samples from raw.naver_blog_raw...")
    df = fetch_blog_cafe_sample(n_samples)
    actual_n = len(df)
    print(f"  Retrieved: {actual_n} samples")

    if actual_n == 0:
        print("  [ERROR] No samples retrieved")
        return None

    # Score and classify all samples
    print("  Scoring samples (product category only)...")
    scores = []
    n_matches_list = []
    all_matched = []
    labels = []
    confidences = []
    is_sponsored = []

    for _, row in df.iterrows():
        text = f"{row['title'] or ''} {row['description'] or ''}"

        # Sponsorship detection
        sponsored = detect_sponsorship(text)
        is_sponsored.append(sponsored)

        # Product-only scoring
        score, n_matches, matched = score_text(text, category_filter="product")
        label, confidence = classify_sentiment(score, threshold)

        scores.append(score)
        n_matches_list.append(n_matches)
        all_matched.extend(matched)
        labels.append(label)
        confidences.append(confidence)

    df["score"] = scores
    df["n_matches"] = n_matches_list
    df["label"] = labels
    df["confidence"] = confidences
    df["abs_score"] = df["score"].abs()
    df["is_sponsored"] = is_sponsored

    # === Reports ===

    # 1. Sponsorship detection
    n_sponsored = df["is_sponsored"].sum()
    n_organic = actual_n - n_sponsored
    print(f"\n  === Sponsorship Detection ===")
    print(f"  Sponsored: {n_sponsored} ({n_sponsored/actual_n*100:.1f}%)")
    print(f"  Organic:   {n_organic} ({n_organic/actual_n*100:.1f}%)")

    # 2. Coverage (product keywords only)
    has_match = (df["n_matches"] > 0).sum()
    coverage = has_match / actual_n * 100
    print(f"\n  === Product Keyword Coverage ===")
    print(f"  Texts with >= 1 match: {has_match}/{actual_n} ({coverage:.1f}%)")

    # 3. Classification (product-only, all samples)
    label_counts = Counter(labels)
    print(f"\n  === Classification (threshold={threshold}, product-only) ===")
    for lbl in ["positive", "negative", "neutral", "uncertain"]:
        cnt = label_counts.get(lbl, 0)
        pct = cnt / actual_n * 100
        print(f"  {lbl:<12}: {cnt:>5} ({pct:>5.1f}%)")

    # 4. Routing
    keyword_resolved = sum(1 for c in confidences if c == "keyword")
    needs_api = sum(1 for c in confidences if c == "needs_api")
    print(f"\n  === Routing ===")
    print(f"  Keyword resolved: {keyword_resolved} ({keyword_resolved/actual_n*100:.1f}%)")
    print(f"  Needs API:        {needs_api} ({needs_api/actual_n*100:.1f}%)")

    # 5. Cost estimate
    est_total = 10000
    api_pct = needs_api / actual_n * 100
    est_api_calls = int(est_total * api_pct / 100)
    est_cost_usd = est_api_calls * (100 * 0.25 / 1e6 + 20 * 1.25 / 1e6)
    est_cost_krw = est_cost_usd * 1400
    print(f"\n  === Cost Estimate (10,000 texts) ===")
    print(f"  Estimated API calls: {est_api_calls}")
    print(f"  Estimated cost: ${est_cost_usd:.4f} (~{est_cost_krw:.0f} KRW)")

    # 6. Top keywords (product only)
    kw_freq = Counter([(kw, cat) for kw, w, cat in all_matched])
    print(f"\n  === Top 20 Product Keywords ===")
    for (kw, cat), cnt in kw_freq.most_common(20):
        weight = SENTIMENT_DICT[kw][0]
        print(f"  {kw:<15} {cnt:>5} hits  (w={weight:+.1f}, cat={cat})")

    # 7. Sponsored vs Organic comparison
    print(f"\n  === Sponsored vs Organic Sentiment ===")
    spons_df = df[df["is_sponsored"]]
    organ_df = df[~df["is_sponsored"]]

    if len(spons_df) > 0 and len(organ_df) > 0:
        spons_mean = spons_df["score"].mean()
        organ_mean = organ_df["score"].mean()
        t_stat, p_val = stats.ttest_ind(
            organ_df["score"].values,
            spons_df["score"].values,
            equal_var=False,
        )
        print(f"  Organic  mean: {organ_mean:+.4f} (n={len(organ_df)})")
        print(f"  Sponsored mean: {spons_mean:+.4f} (n={len(spons_df)})")
        print(f"  Welch t-test: t={t_stat:.4f}, p={p_val:.6f}")
        if p_val < 0.05:
            print(f"  Result: Significant difference (p < 0.05)")
        else:
            print(f"  Result: No significant difference (p >= 0.05)")
    else:
        print(f"  Organic: n={len(organ_df)}, Sponsored: n={len(spons_df)}")
        print(f"  Insufficient data for t-test")

    # 8. By brand (organic only)
    print(f"\n  === By Brand (organic only) ===")
    for brand in ["new_balance", "nike", "adidas", "puma"]:
        brand_df = organ_df[organ_df["brand"] == brand]
        if brand_df.empty:
            continue
        n = len(brand_df)
        pos = (brand_df["label"] == "positive").sum()
        neg = (brand_df["label"] == "negative").sum()
        neu = (brand_df["label"] == "neutral").sum()
        unc = (brand_df["label"] == "uncertain").sum()
        avg = brand_df["score"].mean()
        print(f"  {brand:<15} n={n:>4}  pos={pos:>3}  neg={neg:>3}  "
              f"neu={neu:>3}  unc={unc:>3}  avg={avg:+.4f}")

    return df


# ================================================================
# VISUALIZATION
# ================================================================

def plot_score_distribution(df, threshold=0.3):
    """Score distribution with threshold line."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Panel 1: Raw score
    ax1 = axes[0]
    ax1.hist(df["score"], bins=50, color="#3498DB", alpha=0.7, edgecolor="white")
    ax1.axvline(x=threshold, color="red", linewidth=1.5, linestyle="--",
                label=f"threshold={threshold}")
    ax1.axvline(x=-threshold, color="red", linewidth=1.5, linestyle="--")
    ax1.axvline(x=0, color="gray", linewidth=0.8)
    ax1.set_title("Product Score Distribution", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Keyword Score")
    ax1.set_ylabel("Count")
    ax1.legend()

    # Panel 2: |score| with zone annotation
    ax2 = axes[1]
    abs_scores = df["abs_score"]
    zero_count = (abs_scores == 0).sum()
    uncertain_count = ((abs_scores > 0) & (abs_scores < threshold)).sum()
    classified_count = (abs_scores >= threshold).sum()

    ax2.hist(abs_scores[abs_scores > 0], bins=40, color="#2ECC71", alpha=0.7,
             edgecolor="white")
    ax2.axvline(x=threshold, color="red", linewidth=1.5, linestyle="--",
                label=f"threshold={threshold}")
    ax2.set_title("|Score| Distribution (non-zero)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("|Keyword Score|")
    ax2.set_ylabel("Count")

    n = len(df)
    ax2.text(0.02, 0.95,
             f"Zero (neutral): {zero_count} ({zero_count/n*100:.1f}%)\n"
             f"|s| < {threshold} (API): {uncertain_count} ({uncertain_count/n*100:.1f}%)\n"
             f"|s| >= {threshold} (keyword): {classified_count} ({classified_count/n*100:.1f}%)",
             transform=ax2.transAxes, fontsize=9, verticalalignment="top",
             bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))
    ax2.legend()

    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, f"keyword_score_distribution_t{threshold}.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"\n  Saved: {fig_path}")


def plot_sponsorship_bias(df):
    """Compare score distributions: sponsored vs organic."""
    spons_df = df[df["is_sponsored"]]
    organ_df = df[~df["is_sponsored"]]

    if len(spons_df) < 5:
        print("  [WARN] Too few sponsored samples for bias plot")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Panel 1: Overlapping histograms
    ax1 = axes[0]
    ax1.hist(organ_df["score"], bins=30, alpha=0.6, label=f"Organic (n={len(organ_df)})",
             color="#3498DB", edgecolor="white")
    ax1.hist(spons_df["score"], bins=30, alpha=0.6, label=f"Sponsored (n={len(spons_df)})",
             color="#E74C3C", edgecolor="white")
    ax1.set_title("Score Distribution: Sponsored vs Organic", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Product Score")
    ax1.set_ylabel("Count")
    ax1.legend()

    # Panel 2: Box plot by brand × sponsorship
    ax2 = axes[1]
    brands = ["new_balance", "nike", "adidas", "puma"]
    positions = []
    data = []
    colors = []
    tick_labels = []

    for i, brand in enumerate(brands):
        org = organ_df[organ_df["brand"] == brand]["score"].values
        spo = spons_df[spons_df["brand"] == brand]["score"].values

        if len(org) > 0:
            data.append(org)
            positions.append(i * 3)
            colors.append(BRAND_COLORS[brand])
            tick_labels.append(f"{brand}\norganic")

        if len(spo) > 0:
            data.append(spo)
            positions.append(i * 3 + 1)
            colors.append(BRAND_COLORS[brand])
            tick_labels.append(f"{brand}\nsponsored")

    if data:
        bp = ax2.boxplot(data, positions=positions, patch_artist=True, widths=0.7)
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.5)
        ax2.set_xticks(positions)
        ax2.set_xticklabels(tick_labels, fontsize=7, rotation=45)
        ax2.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
        ax2.set_title("Score by Brand x Sponsorship", fontsize=12, fontweight="bold")
        ax2.set_ylabel("Product Score")

    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, "sponsorship_bias.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


def plot_brand_comparison(df):
    """Box plot of product scores by brand (organic only)."""
    organ_df = df[~df["is_sponsored"]]

    fig, ax = plt.subplots(figsize=(10, 5))
    brands = ["new_balance", "nike", "adidas", "puma"]
    data = [organ_df[organ_df["brand"] == b]["score"].values for b in brands]
    colors = [BRAND_COLORS.get(b, "#333") for b in brands]

    bp = ax.boxplot(data, labels=brands, patch_artist=True)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_title("Product Sentiment Score by Brand (organic only)",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("Score")

    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, "keyword_score_by_brand_organic.png")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ================================================================
# DICTIONARY INFO
# ================================================================

def show_dict():
    """Print dictionary summary by category."""
    categories = {"product": [], "channel": [], "resale": []}

    for kw, (weight, cat) in sorted(SENTIMENT_DICT.items(), key=lambda x: (-abs(x[1][0]), x[0])):
        categories[cat].append((kw, weight))

    print(f"\n  === Sentiment Dictionary Summary (v2: 3-way) ===\n")

    for cat in ["product", "channel", "resale"]:
        items = categories[cat]
        pos = [x for x in items if x[1] > 0]
        neg = [x for x in items if x[1] < 0]
        print(f"  [{cat.upper()}] {len(items)} total ({len(pos)} pos, {len(neg)} neg)")
        for kw, w in sorted(items, key=lambda x: -x[1]):
            print(f"    {kw:<15} {w:+.1f}")
        print()

    print(f"  === Sponsorship Filter Patterns ===")
    for p in SPONSORSHIP_PATTERNS:
        print(f"    {p}")
    print()


# ================================================================
# CLI / MAIN
# ================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage 3 Step B1: Sportswear sentiment dictionary (v2)"
    )
    parser.add_argument("--sample-test", action="store_true",
                        help="Run sample test with sponsorship detection")
    parser.add_argument("--n-samples", type=int, default=DEFAULT_N_SAMPLES,
                        help="Number of samples (default: 1000)")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="Classification threshold (default: 0.3)")
    parser.add_argument("--show-dict", action="store_true",
                        help="Print dictionary by category")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Stage 3 Step B1: Sentiment Dictionary (v2)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.show_dict:
        show_dict()
        return

    if args.sample_test:
        df = run_sample_test(
            n_samples=args.n_samples,
            threshold=args.threshold,
        )
        if df is not None:
            plot_score_distribution(df, threshold=args.threshold)
            plot_sponsorship_bias(df)
            plot_brand_comparison(df)
        return

    print("  No action specified. Use --sample-test or --show-dict")

    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
