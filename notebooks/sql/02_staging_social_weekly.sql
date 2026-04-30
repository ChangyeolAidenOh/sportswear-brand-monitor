-- ============================================================
-- 02_staging_social_weekly.sql
-- ETL: raw.youtube_raw -> staging.social_weekly
--
-- Plan X scope (Decision #2):
--   Social time-series failed Granger viability (all brands < 30 weeks).
--   Granger Chain reduced to Search -> Sales (2-stage).
--   YouTube retained as cross-sectional auxiliary variable,
--   NOT as causal time-series input.
--
-- Sources included:
--   YouTube — video-level weekly aggregation (published_at based)
--
-- Sources excluded:
--   Naver Blog  — post_date coverage 2-19 weeks per brand; text corpus only
--   Naver Cafe  — post_date 100% NULL; text corpus only
--   Blog/Cafe remain in raw for Stage 3 sentiment/topic analysis
--
-- Deduplication:
--   youtube_raw stores one row per comment + one video-level row per video.
--   Video metrics (view_count, like_count) repeat across comment rows.
--   DISTINCT ON (video_id) extracts unique video-level metrics.
--
-- Week convention:
--   DATE_TRUNC('week', published_at) -> ISO Monday-start weeks
--   Different from GT (Sunday-start) in staging.search_weekly;
--   mart layer handles cross-table alignment if needed
--
-- avg_sentiment: NULL — populated in Stage 3 (NLP pipeline)
--
-- Idempotent: TRUNCATE + INSERT within transaction
-- ============================================================

BEGIN;

TRUNCATE staging.social_weekly;

-- ============================================================
-- CTE: deduplicate video metrics from comment-level rows
-- Each video_id appears once with latest snapshot values
-- ============================================================
WITH video_metrics AS (
    SELECT DISTINCT ON (video_id)
        video_id,
        brand,
        published_at,
        view_count,
        like_count
    FROM raw.youtube_raw
    ORDER BY video_id, collected_at DESC
)
INSERT INTO staging.social_weekly
    (brand, platform, week_start, mention_count,
     total_views, total_likes, avg_sentiment)
SELECT
    brand,
    'youtube'                                AS platform,
    DATE_TRUNC('week', published_at)::DATE   AS week_start,
    COUNT(*)                                 AS mention_count,
    SUM(view_count)                          AS total_views,
    SUM(like_count)                          AS total_likes,
    NULL::NUMERIC                            AS avg_sentiment
FROM video_metrics
GROUP BY brand, DATE_TRUNC('week', published_at)
;

COMMIT;

-- ============================================================
-- Verification: brand-level coverage summary
-- Compare weeks_covered against Granger threshold (30 weeks)
-- ============================================================
SELECT
    brand,
    COUNT(*)              AS weeks_with_data,
    SUM(mention_count)    AS total_videos,
    MIN(week_start)       AS earliest,
    MAX(week_start)       AS latest
FROM staging.social_weekly
GROUP BY brand
ORDER BY brand;
