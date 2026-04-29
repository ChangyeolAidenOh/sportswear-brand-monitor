"""
Stage 1 — YouTube Data Collector

Collects YouTube videos and comments for 4 sportswear brands via Data API v3
and inserts into raw.youtube_raw.

Adapted from cnp-voc-pipeline/collector_youtube.py with:
  - CSV output → PostgreSQL INSERT
  - Brand-specific queries with brand_enum mapping
  - Video statistics (view_count, like_count, comment_count) via videos().list()
  - Rate limiting and API quota awareness

API quota estimate: ~1,300 units per full run (daily limit: 10,000).

Dedup strategy: --clear flag deletes existing brand rows before INSERT

Usage:
    python -m collectors.collector_youtube
    python -m collectors.collector_youtube --dry-run
    python -m collectors.collector_youtube --brand new_balance
    python -m collectors.collector_youtube --clear
    python -m collectors.collector_youtube --max-videos 5 --max-comments 50
"""

# stdlib
import argparse
import os
import sys
import time
from datetime import datetime

# third-party
from dotenv import load_dotenv

load_dotenv()

try:
    from googleapiclient.discovery import build
except ImportError:
    print("[ERROR] google-api-python-client not installed. Run: pip install google-api-python-client")
    sys.exit(1)

# local
from database.connection import get_conn

# ================================================================
# Constants
# ================================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Brand-specific search queries
# Each query maps to a brand_enum value for DB insertion
BRAND_QUERIES = {
    "new_balance": [
        "뉴발란스 리뷰",
        "뉴발란스 530 리뷰",
        "뉴발란스 992",
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

DEFAULT_MAX_VIDEOS = 10
DEFAULT_MAX_COMMENTS = 100
RATE_LIMIT_DELAY = 0.3


# ================================================================
# YouTube API helpers
# ================================================================

def build_youtube_client():
    """Build YouTube Data API v3 client."""
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def search_videos(youtube, query, max_results=10):
    """Search YouTube videos for a query. Returns list of video metadata dicts."""
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=max_results,
        order="relevance",
        relevanceLanguage="ko",
        regionCode="KR",
    )
    response = request.execute()

    videos = []
    for item in response.get("items", []):
        videos.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel_title": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
        })
    return videos


def get_video_statistics(youtube, video_ids):
    """Fetch view/like/comment counts for a batch of video IDs.

    videos().list() accepts up to 50 IDs per call.
    Returns dict: {video_id: {view_count, like_count, comment_count}}.
    """
    stats = {}
    # Process in batches of 50
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        request = youtube.videos().list(
            part="statistics",
            id=",".join(batch),
        )
        response = request.execute()
        for item in response.get("items", []):
            s = item["statistics"]
            stats[item["id"]] = {
                "view_count": int(s.get("viewCount", 0)),
                "like_count": int(s.get("likeCount", 0)),
                "comment_count": int(s.get("commentCount", 0)),
            }
        time.sleep(RATE_LIMIT_DELAY)
    return stats


def get_comments(youtube, video_id, max_results=100):
    """Collect top-level comments from a YouTube video.

    Returns list of comment dicts. Handles pagination.
    Silently returns empty list if comments are disabled.
    """
    comments = []
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(max_results, 100),
            order="relevance",
            textFormat="plainText",
        )
        response = request.execute()

        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "comment_text": top["textDisplay"],
                "comment_author": top["authorDisplayName"],
                "comment_date": top["publishedAt"],
            })

        # Paginate
        while "nextPageToken" in response and len(comments) < max_results:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                pageToken=response["nextPageToken"],
                order="relevance",
                textFormat="plainText",
            )
            response = request.execute()
            for item in response.get("items", []):
                top = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "comment_text": top["textDisplay"],
                    "comment_author": top["authorDisplayName"],
                    "comment_date": top["publishedAt"],
                })

    except Exception as e:
        # Comments disabled or other API error
        print(f"      [WARN] Comments unavailable ({video_id}): {e}")

    return comments[:max_results]


# ================================================================
# DB operations
# ================================================================

INSERT_SQL = """
INSERT INTO raw.youtube_raw
    (video_id, brand, title, channel_title, published_at,
     view_count, like_count, comment_count,
     comment_text, comment_author, comment_date, collected_at)
VALUES
    (%s, %s, %s, %s, %s,
     %s, %s, %s,
     %s, %s, %s, NOW());
"""

CLEAR_BRAND_SQL = """
DELETE FROM raw.youtube_raw WHERE brand = %s;
"""


def insert_rows(rows):
    """Batch insert rows into raw.youtube_raw in one transaction."""
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


# ================================================================
# Main collection logic
# ================================================================

def collect_brand(youtube, brand, queries, max_videos, max_comments, dry_run=False):
    """Collect videos and comments for a single brand."""
    rows = []

    for query in queries:
        print(f"    Searching: '{query}'")
        videos = search_videos(youtube, query, max_results=max_videos)
        print(f"      Found {len(videos)} videos")

        if not videos:
            continue

        # Fetch statistics for all videos in this query
        video_ids = [v["video_id"] for v in videos]
        stats = get_video_statistics(youtube, video_ids)

        for video in videos:
            vid = video["video_id"]
            s = stats.get(vid, {"view_count": 0, "like_count": 0, "comment_count": 0})

            # Video-level row (comment fields NULL)
            rows.append((
                vid,
                brand,
                video["title"],
                video["channel_title"],
                video["published_at"],
                s["view_count"],
                s["like_count"],
                s["comment_count"],
                None,   # comment_text
                None,   # comment_author
                None,   # comment_date
            ))

            # Collect comments
            print(f"      Comments: {video['title'][:40]}...")
            comments = get_comments(youtube, vid, max_results=max_comments)
            for c in comments:
                rows.append((
                    vid,
                    brand,
                    video["title"],
                    video["channel_title"],
                    video["published_at"],
                    s["view_count"],
                    s["like_count"],
                    s["comment_count"],
                    c["comment_text"],
                    c["comment_author"],
                    c["comment_date"],
                ))

            time.sleep(RATE_LIMIT_DELAY)

    return rows


def collect_all(target_brand=None, max_videos=DEFAULT_MAX_VIDEOS,
                max_comments=DEFAULT_MAX_COMMENTS, clear=False, dry_run=False):
    """Collect YouTube data for all brands (or a single brand)."""
    youtube = build_youtube_client()
    total_rows = 0

    for brand, queries in BRAND_QUERIES.items():
        if target_brand and brand != target_brand:
            continue

        print(f"  Brand: {brand} ({len(queries)} queries)")

        if clear and not dry_run:
            deleted = clear_brand(brand)
            if deleted > 0:
                print(f"    Cleared {deleted} existing rows")

        rows = collect_brand(
            youtube, brand, queries, max_videos, max_comments, dry_run=dry_run,
        )

        video_count = sum(1 for r in rows if r[8] is None)  # comment_text is None
        comment_count = len(rows) - video_count
        print(f"    Total: {video_count} videos, {comment_count} comments")

        if dry_run:
            for r in rows[:3]:
                label = "VIDEO" if r[8] is None else "COMMENT"
                print(f"    [DRY-RUN] [{label}] {r[0]} | {r[2][:40]}")
            if len(rows) > 3:
                print(f"    [DRY-RUN] ... and {len(rows) - 3} more")
        else:
            inserted = insert_rows(rows)
            total_rows += inserted
            print(f"    Inserted {inserted} rows")

    return total_rows


# ================================================================
# CLI
# ================================================================

def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Collect YouTube videos and comments into raw.youtube_raw"
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
        "--clear", action="store_true",
        help="Delete existing rows for target brand(s) before inserting"
    )
    parser.add_argument(
        "--max-videos", type=int, default=DEFAULT_MAX_VIDEOS,
        help=f"Max videos per query (default: {DEFAULT_MAX_VIDEOS})"
    )
    parser.add_argument(
        "--max-comments", type=int, default=DEFAULT_MAX_COMMENTS,
        help=f"Max comments per video (default: {DEFAULT_MAX_COMMENTS})"
    )
    return parser.parse_args()


def main():
    """Entry point for YouTube collector."""
    args = parse_args()

    if not YOUTUBE_API_KEY:
        print("[ERROR] YOUTUBE_API_KEY not set in .env")
        sys.exit(1)

    print("YouTube Collector")
    print(f"  Brands: {args.brand or 'all 4'}")
    print(f"  Max videos/query: {args.max_videos}, Max comments/video: {args.max_comments}")
    if args.clear:
        print("  Mode: CLEAR + INSERT")
    if args.dry_run:
        print("  Mode: DRY-RUN")

    total = collect_all(
        target_brand=args.brand,
        max_videos=args.max_videos,
        max_comments=args.max_comments,
        clear=args.clear,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("\nDry run complete. No rows written.")
    else:
        print(f"\nCollection complete. Total inserted: {total} rows")


if __name__ == "__main__":
    main()
