-- ============================================================
-- Stage 2 Pre-flight: Raw Data Verification Queries
-- Run against nb_monitor DB before starting ETL SQL files
-- ============================================================

-- Q1: Naver Blog/Cafe post_date fill rate by source_type
-- Purpose: Check if cafearticle has lower date coverage than blog
SELECT source_type,
       COUNT(*)            AS total,
       COUNT(post_date)    AS filled,
       ROUND(100.0 * COUNT(post_date) / COUNT(*), 1) AS pct
FROM raw.naver_blog_raw
GROUP BY source_type;

-- Q2: YouTube published_at date range and weekly bucket count
-- Purpose: Determine time span available for weekly aggregation
SELECT MIN(published_at)::DATE                          AS earliest,
       MAX(published_at)::DATE                          AS latest,
       COUNT(DISTINCT DATE_TRUNC('week', published_at)) AS week_buckets
FROM raw.youtube_raw;

-- Q3: Blog time-series sufficiency per brand (blog only, date-filled)
-- Purpose: Decide if blog can serve as social time-series backbone
--          for Granger Chain (need 30+ weeks per brand for reliability)
SELECT brand,
       COUNT(*)            AS total_posts,
       COUNT(DISTINCT DATE_TRUNC('week', post_date)) AS weeks_covered,
       ROUND(
           COUNT(*)::NUMERIC
           / NULLIF(COUNT(DISTINCT DATE_TRUNC('week', post_date)), 0),
           1
       ) AS avg_posts_per_week
FROM raw.naver_blog_raw
WHERE source_type = 'blog'
  AND post_date IS NOT NULL
GROUP BY brand
ORDER BY brand;
