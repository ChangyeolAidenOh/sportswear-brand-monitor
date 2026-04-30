-- ============================================================
-- Stage 2 Pre-flight: YouTube Social Time-Series Viability
-- Decision #2 critical path — determines Granger Chain scope
-- ============================================================

-- Q4: YouTube brand-level weekly coverage
-- Granger threshold: 30+ weeks per brand
SELECT brand,
       COUNT(DISTINCT DATE_TRUNC('week', published_at)) AS weeks_covered,
       MIN(published_at)::DATE                          AS earliest,
       MAX(published_at)::DATE                          AS latest
FROM raw.youtube_raw
WHERE published_at IS NOT NULL
GROUP BY brand
ORDER BY brand;

-- Q5: Weekly density — gap analysis per brand
-- Generates full weekly spine from each brand's min to max,
-- then checks how many weeks have zero video observations.
-- Also compares video-based vs comment-based weekly coverage.
WITH brand_range AS (
    SELECT brand,
           DATE_TRUNC('week', MIN(published_at))::DATE AS first_week,
           DATE_TRUNC('week', MAX(published_at))::DATE AS last_week
    FROM raw.youtube_raw
    WHERE published_at IS NOT NULL
    GROUP BY brand
),
week_spine AS (
    SELECT br.brand,
           gs::DATE AS week_start
    FROM brand_range br,
         GENERATE_SERIES(br.first_week, br.last_week, '1 week'::INTERVAL) gs
),
video_weeks AS (
    SELECT brand,
           DATE_TRUNC('week', published_at)::DATE AS week_start,
           COUNT(DISTINCT video_id)               AS video_count
    FROM raw.youtube_raw
    WHERE published_at IS NOT NULL
    GROUP BY brand, DATE_TRUNC('week', published_at)
),
comment_weeks AS (
    SELECT brand,
           DATE_TRUNC('week', comment_date)::DATE AS week_start,
           COUNT(*)                               AS comment_count
    FROM raw.youtube_raw
    WHERE comment_date IS NOT NULL
    GROUP BY brand, DATE_TRUNC('week', comment_date)
)
SELECT ws.brand,
       COUNT(*)                                          AS total_weeks_in_span,
       COUNT(vw.video_count)                             AS weeks_with_videos,
       COUNT(*) - COUNT(vw.video_count)                  AS weeks_without_videos,
       ROUND(100.0 * (COUNT(*) - COUNT(vw.video_count))
             / COUNT(*), 1)                              AS gap_pct,
       COUNT(cw.comment_count)                           AS weeks_with_comments,
       ROUND(100.0 * COUNT(cw.comment_count)
             / COUNT(*), 1)                              AS comment_coverage_pct
FROM week_spine ws
LEFT JOIN video_weeks vw
    ON ws.brand = vw.brand AND ws.week_start = vw.week_start
LEFT JOIN comment_weeks cw
    ON ws.brand = cw.brand AND ws.week_start = cw.week_start
GROUP BY ws.brand
ORDER BY ws.brand;
