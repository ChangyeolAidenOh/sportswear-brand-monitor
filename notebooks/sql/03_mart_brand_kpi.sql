-- ============================================================
-- 03_mart_brand_kpi.sql
-- ETL: staging.search_weekly + staging.social_weekly
--      -> mart.brand_kpi_weekly
--
-- Core dashboard table: one row per (brand, region, week).
--
-- Search index source:
--   Google Trends web search (keyword_group = 'brand', search_type = 'web')
--   Chosen for cross-region comparability and longest time span (174 weeks).
--   Naver DataLab remains in staging for Korea-specific deep dives.
--
-- Window functions:
--   WoW  — LAG(1)  week-over-week % change
--   MoM  — LAG(4)  month-over-month (4-week proxy)
--   YoY  — LAG(52) year-over-year
--
-- Share of Voice:
--   brand search_index / SUM(all 4 brands) per region per week
--
-- Social columns (Plan X — cross-sectional auxiliary):
--   LEFT JOIN with staging.social_weekly (YouTube only).
--   Most rows NULL due to sparse coverage (14-25 weeks vs 174 search weeks).
--   avg_sentiment NULL until Stage 3 NLP pipeline.
--
-- Week alignment:
--   staging.search_weekly (GT) uses Sunday-start weeks.
--   staging.social_weekly (YouTube) uses Monday-start ISO weeks.
--   JOIN offset: GT.week_start + 1 = YouTube.week_start
--
-- Season classification (fashion industry convention):
--   SS (Spring/Summer): ISO weeks 10-35
--   FW (Fall/Winter): ISO weeks 36-52 + 1-9
--   Label format: 'SS25', 'FW25', etc.
--
-- Idempotent: TRUNCATE + INSERT within transaction
-- ============================================================

BEGIN;

TRUNCATE mart.brand_kpi_weekly;

-- ============================================================
-- CTE 1: extract brand-level GT web search as primary index
-- ============================================================
WITH search_base AS (
    SELECT brand, region, week_start, interest AS search_index
    FROM staging.search_weekly
    WHERE keyword_group = 'brand'
      AND source       = 'google_trends'
      AND search_type  = 'web'
),

-- ============================================================
-- CTE 2: Share of Voice per region per week
-- ============================================================
search_sov AS (
    SELECT
        brand, region, week_start, search_index,
        ROUND(
            100.0 * search_index
            / NULLIF(SUM(search_index) OVER (PARTITION BY region, week_start), 0),
            4
        ) AS sov_pct
    FROM search_base
),

-- ============================================================
-- CTE 3: WoW / MoM / YoY via LAG window functions
-- ============================================================
search_trends AS (
    SELECT
        brand, region, week_start, search_index, sov_pct,

        ROUND(100.0 * (search_index - LAG(search_index, 1) OVER w)
              / NULLIF(LAG(search_index, 1) OVER w, 0), 4)
            AS search_wow_pct,

        ROUND(100.0 * (search_index - LAG(search_index, 4) OVER w)
              / NULLIF(LAG(search_index, 4) OVER w, 0), 4)
            AS search_mom_pct,

        ROUND(100.0 * (search_index - LAG(search_index, 52) OVER w)
              / NULLIF(LAG(search_index, 52) OVER w, 0), 4)
            AS search_yoy_pct

    FROM search_sov
    WINDOW w AS (PARTITION BY brand, region ORDER BY week_start)
)

-- ============================================================
-- Final INSERT: join social + compute season
-- ============================================================
INSERT INTO mart.brand_kpi_weekly
    (brand, region, week_start,
     search_index, search_wow_pct, search_mom_pct, search_yoy_pct,
     sov_pct, social_mention_count, social_sentiment_avg,
     season_label, season_week_num)
SELECT
    st.brand,
    st.region,
    st.week_start,

    -- Search metrics
    st.search_index,
    st.search_wow_pct,
    st.search_mom_pct,
    st.search_yoy_pct,
    st.sov_pct,

    -- Social metrics (YouTube only; NULL for global rows)
    sw.mention_count,
    sw.avg_sentiment,

    -- Season classification
    CASE
        WHEN EXTRACT(WEEK FROM st.week_start) BETWEEN 10 AND 35
            THEN 'SS' || TO_CHAR(st.week_start, 'YY')
        WHEN EXTRACT(WEEK FROM st.week_start) >= 36
            THEN 'FW' || TO_CHAR(st.week_start, 'YY')
        ELSE 'FW' || TO_CHAR(st.week_start - INTERVAL '1 year', 'YY')
    END AS season_label,

    CASE
        WHEN EXTRACT(WEEK FROM st.week_start) BETWEEN 10 AND 35
            THEN (EXTRACT(WEEK FROM st.week_start) - 9)::SMALLINT
        WHEN EXTRACT(WEEK FROM st.week_start) >= 36
            THEN (EXTRACT(WEEK FROM st.week_start) - 35)::SMALLINT
        ELSE (17 + EXTRACT(WEEK FROM st.week_start))::SMALLINT
    END AS season_week_num

FROM search_trends st
LEFT JOIN staging.social_weekly sw
    ON st.brand = sw.brand
    AND st.week_start + 1 = sw.week_start  -- GT Sunday -> YouTube Monday
    AND st.region = 'korea'::region_enum   -- social data is Korea-only

;

COMMIT;

-- ============================================================
-- Verification
-- ============================================================

-- V1: row counts by region
SELECT region, COUNT(*) AS rows,
       COUNT(search_wow_pct) AS wow_filled,
       COUNT(social_mention_count) AS social_filled
FROM mart.brand_kpi_weekly
GROUP BY region;

-- V2: SoV sanity check — should sum to ~100 per region per week
SELECT region, week_start, ROUND(SUM(sov_pct), 2) AS sov_total
FROM mart.brand_kpi_weekly
GROUP BY region, week_start
HAVING ABS(SUM(sov_pct) - 100) > 0.1
LIMIT 5;

-- V3: season distribution
SELECT season_label, COUNT(*) AS rows
FROM mart.brand_kpi_weekly
GROUP BY season_label
ORDER BY season_label;
