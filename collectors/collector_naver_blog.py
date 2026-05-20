"""
Stage 1 — Naver Blog/Cafe Collector

Collects blog and cafe posts for 4 sportswear brands via Naver Search API
and inserts into raw.naver_blog_raw.

Adapted from cnp-voc-pipeline/collector_naver.py with:
  - CSV output → PostgreSQL INSERT
  - Brand-specific queries with brand_enum mapping
  - Pagination (up to 1000 results per query, API limit)
  - HTML tag stripping from title/description
  - Both blog and cafearticle sources per brand

Dedup strategy: --clear flag deletes existing brand rows before INSERT

Usage:
    python -m collectors.collector_naver_blog
    python -m collectors.collector_naver_blog --dry-run
    python -m collectors.collector_naver_blog --brand new_balance
    python -m collectors.collector_naver_blog --source blog
    python -m collectors.collector_naver_blog --clear --max-pages 3
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

from database.connection import get_conn

# Constants

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_HEADERS = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
}

NAVER_SEARCH_URL = "https://openapi.naver.com/v1/search"

CALL_INTERVAL = 0.5
DISPLAY_PER_PAGE = 100  # max per request
DEFAULT_MAX_PAGES = 5   # 5 pages × 100 = 500 results per query

# HTML tag pattern (Naver API returns <b>, </b> etc.)
HTML_TAG_RE = re.compile(r"<[^>]+>")

BRAND_QUERIES = {
    "new_balance": [
        "뉴발란스 리뷰",
        "뉴발란스 530",
        "뉴발란스 992",
        "뉴발란스 운동화",
    ],
    "nike": [
        "나이키 운동화 리뷰",
        "나이키 신발 추천",
    ],
    "adidas": [
        "아디다스 운동화 리뷰",
        "아디다스 신발 추천",
    ],
    "puma": [
        "푸마 운동화 리뷰",
        "푸마 신발 추천",
    ],
}

SOURCES = ["blog", "cafearticle"]


# Naver Search API

def strip_html(text):
    """Remove HTML tags from Naver API response text."""
    if not text:
        return text
    return HTML_TAG_RE.sub("", text).strip()


def parse_post_date(date_str):
    """Parse Naver post date (YYYYMMDD) to date object. Returns None on failure."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y%m%d").date()
    except ValueError:
        return None


def search_naver(query, source="blog", display=100, start=1):
    """Query Naver Search API for blog or cafe posts.

    Returns response JSON dict or None on failure.
    """
    url = f"{NAVER_SEARCH_URL}/{source}"
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": "date",
    }

    try:
        resp = requests.get(url, headers=NAVER_HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "N/A"
        print(f"      [ERROR] API HTTP {status}: {e}")
        return None
    except Exception as e:
        print(f"      [ERROR] API call failed: {e}")
        return None


def collect_posts(brand, query, source, max_pages):
    """Collect paginated posts for a single query + source combination.

    Returns list of row tuples for DB insertion.
    """
    rows = []

    for page in range(max_pages):
        start = page * DISPLAY_PER_PAGE + 1
        if start > 1000:  # Naver API hard limit
            break

        result = search_naver(query, source=source, display=DISPLAY_PER_PAGE, start=start)
        if result is None or "items" not in result:
            break

        items = result["items"]
        if not items:
            break

        for item in items:
            rows.append((
                source,                                  # source_type
                brand,                                   # brand
                query,                                   # query_keyword
                strip_html(item.get("title", "")),       # title
                strip_html(item.get("description", "")), # description
                item.get("bloggername", item.get("cafename", "")),  # blogger_name
                item.get("link", item.get("cafeurl", "")),          # blog_link
                parse_post_date(item.get("postdate", "")),          # post_date
            ))

        time.sleep(CALL_INTERVAL)

    return rows


# DB operations

INSERT_SQL = """
INSERT INTO raw.naver_blog_raw
    (source_type, brand, query_keyword, title, description,
     blogger_name, blog_link, post_date, collected_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW());
"""

CLEAR_BRAND_SQL = """
DELETE FROM raw.naver_blog_raw WHERE brand = %s;
"""


def insert_rows(rows):
    """Batch insert rows into raw.naver_blog_raw in one transaction."""
    if not rows:
        return 0
    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.executemany(INSERT_SQL, rows)
            conn.commit()
            return len(rows)
        except Exception as e:
            conn.rollback()
            print(f"  [ERROR] DB insert failed: {e}")
            return 0


def clear_brand(brand):
    """Delete all existing rows for a brand before re-collection."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(CLEAR_BRAND_SQL, (brand,))
            deleted = cur.rowcount
        conn.commit()
        return deleted


# Main collection logic

def collect_all(target_brand=None, target_source=None,
                max_pages=DEFAULT_MAX_PAGES, clear=False, dry_run=False):
    """Collect Naver blog/cafe data for all brands."""
    total_rows = 0
    sources = [target_source] if target_source else SOURCES

    for brand, queries in BRAND_QUERIES.items():
        if target_brand and brand != target_brand:
            continue

        print(f"  Brand: {brand} ({len(queries)} queries)")

        if clear and not dry_run:
            deleted = clear_brand(brand)
            if deleted > 0:
                print(f"    Cleared {deleted} existing rows")

        brand_rows = []

        for source in sources:
            for query in queries:
                print(f"    [{source}] '{query}' (max {max_pages} pages)")
                rows = collect_posts(brand, query, source, max_pages)
                brand_rows.extend(rows)
                print(f"      Collected {len(rows)} posts")

        # Summary
        blog_count = sum(1 for r in brand_rows if r[0] == "blog")
        cafe_count = sum(1 for r in brand_rows if r[0] == "cafearticle")
        print(f"    Total: {blog_count} blog + {cafe_count} cafe = {len(brand_rows)}")

        if dry_run:
            for r in brand_rows[:3]:
                date_str = r[7].isoformat() if r[7] else "N/A"
                print(f"    [DRY-RUN] [{r[0]}] {date_str} | {r[3][:50]}")
            if len(brand_rows) > 3:
                print(f"    [DRY-RUN] ... and {len(brand_rows) - 3} more")
        else:
            inserted = insert_rows(brand_rows)
            total_rows += inserted
            print(f"    Inserted {inserted} rows")

    return total_rows


# CLI

def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Collect Naver blog/cafe posts into raw.naver_blog_raw"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch from API but do not write to DB"
    )
    parser.add_argument(
        "--brand", type=str, default=None,
        choices=list(BRAND_QUERIES.keys()),
        help="Collect for a single brand only"
    )
    parser.add_argument(
        "--source", type=str, default=None,
        choices=SOURCES,
        help="Collect from a single source only (blog or cafearticle)"
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Delete existing rows for target brand(s) before inserting"
    )
    parser.add_argument(
        "--max-pages", type=int, default=DEFAULT_MAX_PAGES,
        help=f"Max pages per query (default: {DEFAULT_MAX_PAGES}, 100 results/page)"
    )
    return parser.parse_args()


def main():
    """Entry point for Naver blog/cafe collector."""
    args = parse_args()

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[ERROR] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET not set in .env")
        sys.exit(1)

    print("Naver Blog/Cafe Collector")
    print(f"  Brands: {args.brand or 'all 4'}")
    print(f"  Sources: {args.source or 'blog + cafearticle'}")
    print(f"  Max pages/query: {args.max_pages} ({args.max_pages * DISPLAY_PER_PAGE} results)")
    if args.clear:
        print("  Mode: CLEAR + INSERT")
    if args.dry_run:
        print("  Mode: DRY-RUN")

    total = collect_all(
        target_brand=args.brand,
        target_source=args.source,
        max_pages=args.max_pages,
        clear=args.clear,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("\nDry run complete. No rows written.")
    else:
        print(f"\nCollection complete. Total inserted: {total} rows")


if __name__ == "__main__":
    main()
