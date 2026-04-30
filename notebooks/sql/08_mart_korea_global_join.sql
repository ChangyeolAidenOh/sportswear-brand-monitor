-- ============================================================
-- 08_mart_korea_global_join.sql
-- Multi-join — Korea vs Global comparison (HQ Bridge)
--
-- Populates mart.korea_global_comparison by self-joining
-- mart.brand_kpi_weekly (Korea vs Global) on brand + week.
--
-- Metrics compared:
--   search_index  — raw search interest
--   sov_pct       — share of voice within region
--
-- divergence_pct = (korea_value - global_value) / global_value * 100
--   Positive = Korea over-indexes vs global
--   Negative = Korea under-indexes vs global
--
-- lead_lag_weeks: NULL — requires cross-correlation analysis (Stage 3).
--   Placeholder for future: positive = Korea leads global trend.
--
-- Also inserts product-level comparison for 574 (cross-region anchor)
-- and 2002r (shared product between Korea and Global).
--
-- Week alignment:
--   Both Korea and Global use GT web (Sunday-start) from same CSV set.
--   Direct week_start match is valid (same source, same week convention).
--
-- Idempotent: TRUNCATE + INSERT within transaction
-- ============================================================

BEGIN;

TRUNCATE mart.korea_global_comparison;

INSERT INTO mart.korea_global_comparison
    (brand, metric_name, week_start,
     korea_value, global_value, divergence_pct, lead_lag_weeks)

-- ============================================================
-- Block 1: search_index comparison (brand-level)
-- ============================================================
SELECT
    kr.brand,
    'search_index'                      AS metric_name,
    kr.week_start,
    kr.search_index                     AS korea_value,
    gl.search_index                     AS global_value,
    ROUND(
        100.0 * (kr.search_index - gl.search_index)
        / NULLIF(gl.search_index, 0),
        4
    )                                   AS divergence_pct,
    NULL::SMALLINT                      AS lead_lag_weeks
FROM mart.brand_kpi_weekly kr
JOIN mart.brand_kpi_weekly gl
    ON kr.brand      = gl.brand
    AND kr.week_start = gl.week_start
WHERE kr.region = 'korea'
  AND gl.region = 'global'

UNION ALL

-- ============================================================
-- Block 2: sov_pct comparison (brand-level)
-- ============================================================
SELECT
    kr.brand,
    'sov_pct'                           AS metric_name,
    kr.week_start,
    kr.sov_pct                          AS korea_value,
    gl.sov_pct                          AS global_value,
    ROUND(
        100.0 * (kr.sov_pct - gl.sov_pct)
        / NULLIF(gl.sov_pct, 0),
        4
    )                                   AS divergence_pct,
    NULL::SMALLINT                      AS lead_lag_weeks
FROM mart.brand_kpi_weekly kr
JOIN mart.brand_kpi_weekly gl
    ON kr.brand      = gl.brand
    AND kr.week_start = gl.week_start
WHERE kr.region = 'korea'
  AND gl.region = 'global'

UNION ALL

-- ============================================================
-- Block 3: product-level comparison (574 = cross-region anchor)
-- ============================================================
SELECT
    'new_balance'::brand_enum           AS brand,
    'product_574_share'                 AS metric_name,
    kr.week_start,
    kr.share_within_nb_pct              AS korea_value,
    gl.share_within_nb_pct              AS global_value,
    ROUND(
        100.0 * (kr.share_within_nb_pct - gl.share_within_nb_pct)
        / NULLIF(gl.share_within_nb_pct, 0),
        4
    )                                   AS divergence_pct,
    NULL::SMALLINT                      AS lead_lag_weeks
FROM mart.product_portfolio_weekly kr
JOIN mart.product_portfolio_weekly gl
    ON kr.product_line = gl.product_line
    AND kr.week_start   = gl.week_start
WHERE kr.region       = 'korea'
  AND gl.region       = 'global'
  AND kr.product_line = '574'

UNION ALL

-- ============================================================
-- Block 4: product-level comparison (2002r = shared product)
-- ============================================================
SELECT
    'new_balance'::brand_enum           AS brand,
    'product_2002r_share'               AS metric_name,
    kr.week_start,
    kr.share_within_nb_pct              AS korea_value,
    gl.share_within_nb_pct              AS global_value,
    ROUND(
        100.0 * (kr.share_within_nb_pct - gl.share_within_nb_pct)
        / NULLIF(gl.share_within_nb_pct, 0),
        4
    )                                   AS divergence_pct,
    NULL::SMALLINT                      AS lead_lag_weeks
FROM mart.product_portfolio_weekly kr
JOIN mart.product_portfolio_weekly gl
    ON kr.product_line = gl.product_line
    AND kr.week_start   = gl.week_start
WHERE kr.region       = 'korea'
  AND gl.region       = 'global'
  AND kr.product_line = '2002r'

;

COMMIT;

-- ============================================================
-- Verification
-- ============================================================

-- V1: row counts by metric
SELECT metric_name, COUNT(*) AS rows
FROM mart.korea_global_comparison
GROUP BY metric_name
ORDER BY metric_name;

-- V2: NB divergence summary (Korea vs Global positioning)
SELECT
    metric_name,
    ROUND(AVG(divergence_pct), 2) AS avg_divergence,
    ROUND(MIN(divergence_pct), 2) AS min_divergence,
    ROUND(MAX(divergence_pct), 2) AS max_divergence
FROM mart.korea_global_comparison
WHERE brand = 'new_balance'
GROUP BY metric_name
ORDER BY metric_name;

-- V3: which brand over-indexes most in Korea vs Global?
SELECT
    brand,
    ROUND(AVG(divergence_pct), 2) AS avg_search_divergence
FROM mart.korea_global_comparison
WHERE metric_name = 'search_index'
GROUP BY brand
ORDER BY avg_search_divergence DESC;
