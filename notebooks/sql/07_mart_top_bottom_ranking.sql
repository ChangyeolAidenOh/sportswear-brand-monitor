-- ============================================================
-- 07_mart_top_bottom_ranking.sql
-- RANK / DENSE_RANK — brand and product performance ranking
--
-- Part A: VIEW for weekly brand ranking by search_index per region.
--   RANK for ordinal position, DENSE_RANK for tie handling.
--   Also ranks by sov_pct and search_wow_pct (momentum).
--
-- Part B: VIEW for NB product ranking by share_within_nb_pct.
--   Demonstrates RANK within a single brand's product portfolio.
--   Shows which product drives NB search per region per week.
--
-- No table writes — both outputs are VIEWs.
-- ============================================================

-- ============================================================
-- Part A: Brand ranking per region per week
-- ============================================================
CREATE OR REPLACE VIEW mart.vw_brand_ranking AS
SELECT
    brand,
    region,
    week_start,
    search_index,
    sov_pct,
    search_wow_pct,

    -- Search volume ranking (highest = rank 1)
    RANK() OVER (
        PARTITION BY region, week_start
        ORDER BY search_index DESC NULLS LAST
    ) AS search_rank,

    -- SoV ranking
    DENSE_RANK() OVER (
        PARTITION BY region, week_start
        ORDER BY sov_pct DESC NULLS LAST
    ) AS sov_rank,

    -- Momentum ranking (highest WoW growth = rank 1)
    RANK() OVER (
        PARTITION BY region, week_start
        ORDER BY search_wow_pct DESC NULLS LAST
    ) AS momentum_rank,

    season_label

FROM mart.brand_kpi_weekly;

-- ============================================================
-- Part B: NB product ranking per region per week
-- ============================================================
CREATE OR REPLACE VIEW mart.vw_product_ranking AS
SELECT
    product_line,
    region,
    week_start,
    search_index,
    share_within_nb_pct,
    search_wow_pct,

    -- Portfolio share ranking (highest share = rank 1)
    RANK() OVER (
        PARTITION BY region, week_start
        ORDER BY share_within_nb_pct DESC NULLS LAST
    ) AS share_rank,

    -- Product momentum ranking
    DENSE_RANK() OVER (
        PARTITION BY region, week_start
        ORDER BY search_wow_pct DESC NULLS LAST
    ) AS momentum_rank,

    season_label

FROM mart.product_portfolio_weekly;


-- ============================================================
-- Verification
-- ============================================================

-- V1: brand rank #1 distribution (who leads most often?)
SELECT region, brand, COUNT(*) AS weeks_at_rank1
FROM mart.vw_brand_ranking
WHERE search_rank = 1
GROUP BY region, brand
ORDER BY region, weeks_at_rank1 DESC;

-- V2: NB product rank #1 distribution (530 dominance check)
SELECT region, product_line, COUNT(*) AS weeks_at_rank1
FROM mart.vw_product_ranking
WHERE share_rank = 1
GROUP BY region, product_line
ORDER BY region, weeks_at_rank1 DESC;

-- V3: momentum leaders — which brand leads WoW growth most often?
SELECT region, brand, COUNT(*) AS weeks_at_momentum_rank1
FROM mart.vw_brand_ranking
WHERE momentum_rank = 1
GROUP BY region, brand
ORDER BY region, weeks_at_momentum_rank1 DESC;
