-- ============================================================
-- 06_mart_anomaly_residuals.sql
-- Moving average + standard deviation window — anomaly detection
--
-- Source: mart.brand_kpi_weekly (search_index)
-- Target: mart.anomaly_log
--
-- Method:
--   8-week rolling mean and std dev of search_index.
--   Z-score = (current - rolling_mean) / rolling_std.
--   |z_score| > 2.0 flagged as anomaly.
--
-- Plan X adjustment:
--   Search-based anomalies only (no social time-series).
--   Social time-series failed Granger viability check.
--
-- anomaly_type classification:
--   'spike'   — z_score > +2.0 (unexpected surge)
--   'dip'     — z_score < -2.0 (unexpected decline)
--
-- severity_score: abs(z_score), capped at 5.0
-- matched_event_id: NULL (Stage 3 event matching)
--
-- Idempotent: DELETE detection_method rows + INSERT
-- ============================================================

BEGIN;

-- Clear previous z-score detections (preserve other methods)
DELETE FROM mart.anomaly_log
WHERE detection_method = 'rolling_zscore_8w';

WITH rolling_stats AS (
    SELECT
        brand,
        'search_index'  AS metric_name,
        region,
        week_start,
        search_index,
        AVG(search_index) OVER w   AS rolling_mean,
        STDDEV(search_index) OVER w AS rolling_std
    FROM mart.brand_kpi_weekly
    WINDOW w AS (
        PARTITION BY brand, region
        ORDER BY week_start
        ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
    )
),
z_scores AS (
    SELECT
        brand,
        metric_name,
        region,
        week_start,
        search_index,
        rolling_mean,
        rolling_std,
        CASE
            WHEN rolling_std > 0
            THEN ROUND((search_index - rolling_mean) / rolling_std, 4)
            ELSE NULL
        END AS z_score
    FROM rolling_stats
    -- Require at least 8 data points for stable stats
    WHERE rolling_std IS NOT NULL
)
INSERT INTO mart.anomaly_log
    (brand, product_line, metric_name, detected_date,
     anomaly_type, detection_method, severity_score,
     z_score, matched_event_id, description)
SELECT
    brand,
    NULL                        AS product_line,
    metric_name,
    week_start                  AS detected_date,
    CASE
        WHEN z_score > 2.0  THEN 'spike'
        WHEN z_score < -2.0 THEN 'dip'
    END                         AS anomaly_type,
    'rolling_zscore_8w'         AS detection_method,
    LEAST(ABS(z_score), 5.0)    AS severity_score,
    z_score,
    NULL                        AS matched_event_id,
    region || ': search_index ' ||
        CASE WHEN z_score > 0 THEN 'spike' ELSE 'dip' END
        || ' (z=' || ROUND(z_score, 2) || ')'
                                AS description
FROM z_scores
WHERE ABS(z_score) > 2.0
;

COMMIT;

-- ============================================================
-- Verification
-- ============================================================

-- V1: anomaly counts by brand and type
SELECT brand, anomaly_type, COUNT(*) AS anomalies
FROM mart.anomaly_log
WHERE detection_method = 'rolling_zscore_8w'
GROUP BY brand, anomaly_type
ORDER BY brand, anomaly_type;

-- V2: top 5 most severe anomalies
SELECT brand, detected_date, anomaly_type,
       z_score, description
FROM mart.anomaly_log
WHERE detection_method = 'rolling_zscore_8w'
ORDER BY severity_score DESC
LIMIT 5;
