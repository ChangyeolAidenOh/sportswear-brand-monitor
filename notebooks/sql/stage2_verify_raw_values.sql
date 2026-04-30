-- ============================================================
-- Pre-01: Verify raw data values before writing staging SQL
-- Run once; results determine CASE WHEN mapping in 01
-- ============================================================

-- V1: Google Trends distinct layer values
SELECT DISTINCT layer, COUNT(*) AS rows
FROM raw.google_trends_raw
GROUP BY layer
ORDER BY layer;

-- V2: Google Trends brand-layer keywords
SELECT DISTINCT keyword, region, search_type
FROM raw.google_trends_raw
WHERE layer = 'brand'
ORDER BY region, keyword;

-- V3: Google Trends product-layer keywords (check exact layer name)
SELECT DISTINCT layer, keyword, region
FROM raw.google_trends_raw
WHERE layer != 'brand'
ORDER BY layer, region, keyword;

-- V4: Naver DataLab keyword_group and keywords
SELECT keyword_group, keyword, COUNT(*) AS rows
FROM raw.naver_datalab_raw
GROUP BY keyword_group, keyword
ORDER BY keyword_group, keyword;
