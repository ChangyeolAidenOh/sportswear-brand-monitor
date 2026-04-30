-- ============================================================
-- 04_mart_sov_analysis.sql
-- SUM OVER PARTITION BY — Share of Voice analysis
--
-- Part A: VIEW for brand-level SoV broken down by search_type.
--   mart.brand_kpi_weekly has a single sov_pct (GT web only).
--   This VIEW exposes SoV across web/youtube/shopping separately,
--   enabling cross-channel brand positioning analysis.
--
-- Part B: Populate mart.product_portfolio_weekly.
--   Core metric: share_within_nb_pct = product search / total NB search.
--   This is the "530 의존도" KPI — quantifies NB Korea's dependency
--   on the 530 line (~85% of NB Korea search per Stage 0 finding).
--
-- Source: Google Trends product layer (web search only).
--   GT chosen over Naver nb_product for global comparability.
--   Naver nb_product remains in staging for cross-validation.
--
-- Idempotent: CREATE OR REPLACE VIEW + TRUNCATE + INSERT
-- ============================================================

-- ============================================================
-- Part A: Brand SoV by search type (VIEW)
-- Usage: SELECT * FROM mart.vw_sov_by_search_type
--        WHERE region = 'korea' AND search_type = 'shopping';
-- ============================================================
CREATE OR REPLACE VIEW mart.vw_sov_by_search_type AS
SELECT
    brand,
    region,
    search_type,
    week_start,
    interest                                            AS search_index,
    ROUND(
        100.0 * interest
        / NULLIF(
            SUM(interest) OVER (PARTITION BY region, search_type, week_start),
            0),
        4
    )                                                   AS sov_pct
FROM staging.search_weekly
WHERE keyword_group = 'brand'
  AND source = 'google_trends';


-- ============================================================
-- Part B: Product portfolio — 530 dependency metric
-- ============================================================
BEGIN;

TRUNCATE mart.product_portfolio_weekly;

WITH product_base AS (
    SELECT
        product_line,
        region,
        week_start,
        interest AS search_index
    FROM staging.search_weekly
    WHERE keyword_group = 'product'
      AND source        = 'google_trends'
),

-- Share within NB: each product's % of total NB product search
product_shares AS (
    SELECT
        product_line, region, week_start, search_index,
        ROUND(
            100.0 * search_index
            / NULLIF(
                SUM(search_index)
                    OVER (PARTITION BY region, week_start),
                0),
            4
        ) AS share_within_nb_pct
    FROM product_base
),

-- WoW trend per product line
product_trends AS (
    SELECT
        product_line, region, week_start,
        search_index, share_within_nb_pct,
        ROUND(
            100.0 * (search_index - LAG(search_index, 1) OVER w)
            / NULLIF(LAG(search_index, 1) OVER w, 0),
            4
        ) AS search_wow_pct
    FROM product_shares
    WINDOW w AS (PARTITION BY product_line, region ORDER BY week_start)
)

INSERT INTO mart.product_portfolio_weekly
    (product_line, region, week_start,
     search_index, search_wow_pct, share_within_nb_pct,
     season_label)
SELECT
    product_line,
    region,
    week_start,
    search_index,
    search_wow_pct,
    share_within_nb_pct,
    CASE
        WHEN EXTRACT(WEEK FROM week_start) BETWEEN 10 AND 35
            THEN 'SS' || TO_CHAR(week_start, 'YY')
        WHEN EXTRACT(WEEK FROM week_start) >= 36
            THEN 'FW' || TO_CHAR(week_start, 'YY')
        ELSE 'FW' || TO_CHAR(week_start - INTERVAL '1 year', 'YY')
    END
FROM product_trends
;

COMMIT;

-- ============================================================
-- Verification
-- ============================================================

-- V1: product portfolio row counts
SELECT region, product_line, COUNT(*) AS weeks,
       ROUND(AVG(share_within_nb_pct), 2) AS avg_share_pct
FROM mart.product_portfolio_weekly
GROUP BY region, product_line
ORDER BY region, avg_share_pct DESC;

-- V2: 530 dependency confirmation (Stage 0 finding: ~85% in Korea)
SELECT region,
       ROUND(AVG(share_within_nb_pct), 2) AS avg_530_share
FROM mart.product_portfolio_weekly
WHERE product_line = '530'
GROUP BY region;

-- V3: share sum sanity check — should be ~100 per region per week
SELECT region, week_start, ROUND(SUM(share_within_nb_pct), 2) AS share_total
FROM mart.product_portfolio_weekly
GROUP BY region, week_start
HAVING ABS(SUM(share_within_nb_pct) - 100) > 0.1
LIMIT 5;
