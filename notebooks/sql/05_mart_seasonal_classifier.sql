-- ============================================================
-- 05_mart_seasonal_classifier.sql
-- CASE WHEN — Season classification + padding momentum detection
--
-- Part A: VIEW for padding competitive landscape.
--   GT apparel layer contains 노스페이스 (outside brand_enum),
--   so this VIEW reads raw directly with VARCHAR brand mapping.
--   '뉴발란스 574' excluded (product keyword, not padding).
--
-- Part B: VIEW for season start detection.
--   7-week moving average baseline + 30% threshold.
--   Flags the first FW week per brand per year where padding
--   search exceeds baseline — quantifies "패딩 모멘텀" KPI.
--   Stage 0 finding: 노스페이스 dominates (avg 13.9, NB avg 1.2).
--
-- Data span: 5 years (padding_competitive_kr.csv, 278 weeks)
--
-- No table writes — both outputs are VIEWs on raw data.
-- ============================================================

-- ============================================================
-- Part A: Padding competitive landscape with moving average
-- ============================================================
CREATE OR REPLACE VIEW mart.vw_padding_competitive AS
SELECT
    CASE keyword
        WHEN '나이키 패딩'     THEN 'nike'
        WHEN '아디다스 패딩'   THEN 'adidas'
        WHEN '뉴발란스 패딩'   THEN 'new_balance'
        WHEN '노스페이스 패딩' THEN 'north_face'
    END                                         AS brand,
    week_start,
    interest,
    ROUND(
        AVG(interest) OVER (
            PARTITION BY keyword
            ORDER BY week_start
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2
    )                                           AS ma_7w,
    EXTRACT(WEEK FROM week_start)::SMALLINT     AS iso_week,
    CASE
        WHEN EXTRACT(WEEK FROM week_start) BETWEEN 10 AND 35
            THEN 'SS' || TO_CHAR(week_start, 'YY')
        WHEN EXTRACT(WEEK FROM week_start) >= 36
            THEN 'FW' || TO_CHAR(week_start, 'YY')
        ELSE 'FW' || TO_CHAR(week_start - INTERVAL '1 year', 'YY')
    END                                         AS season_label
FROM raw.google_trends_raw
WHERE layer   = 'apparel'
  AND keyword LIKE '%패딩';

-- ============================================================
-- Part B: Season start detector
-- First week per brand per FW season where interest > MA * 1.3
-- Window restricted to ISO weeks 30-50 (late July ~ mid December)
-- ============================================================
CREATE OR REPLACE VIEW mart.vw_padding_season_start AS
WITH candidates AS (
    SELECT
        brand,
        week_start,
        interest,
        ma_7w,
        season_label,
        iso_week,
        -- Flag weeks where padding surges above baseline
        CASE
            WHEN interest > ma_7w * 1.3
             AND iso_week BETWEEN 30 AND 50
            THEN TRUE
            ELSE FALSE
        END AS is_surge
    FROM mart.vw_padding_competitive
),
first_surge AS (
    SELECT
        brand,
        season_label,
        MIN(week_start) AS season_start_date,
        MIN(iso_week)   AS season_start_week
    FROM candidates
    WHERE is_surge
      AND season_label LIKE 'FW%'
    GROUP BY brand, season_label
)
SELECT
    fs.brand,
    fs.season_label,
    fs.season_start_date,
    fs.season_start_week,
    -- Relative timing: how many weeks ahead/behind North Face?
    fs.season_start_week - nf.season_start_week AS weeks_vs_northface
FROM first_surge fs
LEFT JOIN first_surge nf
    ON fs.season_label = nf.season_label
    AND nf.brand = 'north_face'
ORDER BY fs.season_label, fs.season_start_week;


-- ============================================================
-- Verification
-- ============================================================

-- V1: padding competitive row count per brand
SELECT brand, COUNT(*) AS weeks,
       ROUND(AVG(interest), 2) AS avg_interest
FROM mart.vw_padding_competitive
GROUP BY brand
ORDER BY avg_interest DESC;

-- V2: season start timing per brand per FW season
SELECT * FROM mart.vw_padding_season_start
ORDER BY season_label, season_start_week;
