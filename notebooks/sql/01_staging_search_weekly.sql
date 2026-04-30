-- ============================================================
-- 01_staging_search_weekly.sql
-- ETL: raw search sources -> staging.search_weekly
--
-- Sources included:
--   Google Trends  — brand layer (한글+영문 SUM), product layer
--   Naver DataLab  — brand group, nb_product group
--
-- Sources excluded:
--   GT apparel layer   — contains 노스페이스 (outside brand_enum);
--                        handled via CTE in 05_mart_seasonal_classifier.sql
--   Naver nb_social    — sparse (인스타 60 rows, 틱톡 1 row)
--   Naver nb_channel   — sparse (무신사 37, 쿠팡 16 rows)
--   Decision #3: nb_social/nb_channel below viability threshold
--
-- Week convention:
--   Google Trends week_start = Sunday (from CSV download)
--   Naver DataLab period_start = Monday (from API)
--   Both kept as-is in staging; mart handles alignment if needed
--
-- Idempotent: TRUNCATE + INSERT within transaction
-- ============================================================

BEGIN;

TRUNCATE staging.search_weekly;

-- ============================================================
-- CTE: Google Trends brand layer — merge 한글 + 영문 keywords
-- Korea has 8 keywords (4 brands × 2 languages) per search_type;
-- SUM to single brand-level interest per week
-- Global has 4 keywords (English only); SUM is identity
-- ============================================================
WITH gt_brand AS (
    SELECT
        CASE
            WHEN keyword IN ('Nike', '나이키')              THEN 'nike'::brand_enum
            WHEN keyword IN ('Adidas', 'ADIDAS', '아디다스') THEN 'adidas'::brand_enum
            WHEN keyword IN ('Puma', 'PUMA', '푸마')        THEN 'puma'::brand_enum
            WHEN keyword IN ('New Balance', '뉴발란스')     THEN 'new_balance'::brand_enum
        END         AS brand,
        region,
        search_type,
        week_start,
        SUM(interest) AS interest
    FROM raw.google_trends_raw
    WHERE layer = 'brand'
    GROUP BY 1, region, search_type, week_start
)
INSERT INTO staging.search_weekly
    (brand, product_line, source, region, search_type,
     keyword_group, week_start, interest)

-- ============================================================
-- Block 1: Google Trends — brand (aggregated)
-- ============================================================
SELECT
    brand,
    NULL::VARCHAR(50)       AS product_line,
    'google_trends'         AS source,
    region,
    search_type,
    'brand'                 AS keyword_group,
    week_start,
    interest
FROM gt_brand

UNION ALL

-- ============================================================
-- Block 2: Google Trends — product
-- Korea: 뉴발란스 530/992/574/2002R/327
-- Global: New Balance 990/574/9060/2002R/1906R
-- ============================================================
SELECT
    'new_balance'::brand_enum   AS brand,
    LOWER(
        CASE
            WHEN keyword LIKE '뉴발란스 %'
                THEN REPLACE(keyword, '뉴발란스 ', '')
            WHEN keyword LIKE 'New Balance %'
                THEN REPLACE(keyword, 'New Balance ', '')
        END
    )                           AS product_line,
    'google_trends'             AS source,
    region,
    search_type,
    'product'                   AS keyword_group,
    week_start,
    interest
FROM raw.google_trends_raw
WHERE layer = 'product'

UNION ALL

-- ============================================================
-- Block 3: Naver DataLab — brand group
-- search_type = 'naver_search' to avoid NULL in UNIQUE constraint
-- ============================================================
SELECT
    CASE keyword
        WHEN '나이키'   THEN 'nike'::brand_enum
        WHEN '아디다스' THEN 'adidas'::brand_enum
        WHEN '푸마'     THEN 'puma'::brand_enum
        WHEN '뉴발란스' THEN 'new_balance'::brand_enum
    END                         AS brand,
    NULL::VARCHAR(50)           AS product_line,
    'naver_datalab'             AS source,
    'korea'::region_enum        AS region,
    'naver_search'              AS search_type,
    'brand'                     AS keyword_group,
    period_start                AS week_start,
    ratio                       AS interest
FROM raw.naver_datalab_raw
WHERE keyword_group = 'brand'

UNION ALL

-- ============================================================
-- Block 4: Naver DataLab — nb_product group
-- ============================================================
SELECT
    'new_balance'::brand_enum   AS brand,
    LOWER(REPLACE(keyword, '뉴발란스 ', ''))
                                AS product_line,
    'naver_datalab'             AS source,
    'korea'::region_enum        AS region,
    'naver_search'              AS search_type,
    'nb_product'                AS keyword_group,
    period_start                AS week_start,
    ratio                       AS interest
FROM raw.naver_datalab_raw
WHERE keyword_group = 'nb_product'

;

COMMIT;

-- ============================================================
-- Verification: row counts by source and keyword_group
-- ============================================================
SELECT source, keyword_group, region, COUNT(*) AS rows
FROM staging.search_weekly
GROUP BY source, keyword_group, region
ORDER BY source, keyword_group, region;
