-- ============================================================================
-- Migration 011 — Stage 4 sign convention error retrofit (DP24 cascade)
-- ============================================================================
-- Date:   2026-05-03
-- Stage:  7 close
-- Source: Stage 7 Track A2 (Sign Convention Validation), DP24 detection
--
-- Background:
--   Stage 4's DTW + CC implementations used scipy.signal.correlate(kr, gl)
--   and path[:,0] - path[:,1] (Korea idx - Global idx) conventions. Both
--   produce positive values when GLOBAL leads Korea, but Stage 4 labeled
--   positive values as "Korea leads". This is verbal-mathematical inversion.
--
--   DP24 confirmed via three independent tests:
--     1. Synthetic Korea-leads-by-5w data -> Stage 4 code returns CC -5,
--        DTW -4.57 (sign inverted)
--     2. Leakage-free DTW + CC replication -> direction_flipped against labels
--     3. Mediation re-run with corrected direction -> 3 quantitative
--        signatures (inconsistent mediation dissipation, CI 47% narrowing,
--        Track A3 degradation magnitude 1/4-1/5 reduction)
--
-- Scope:
--   mart.korea_global_lag — all 12 rows (4 brands × 3 deseason_method)
--   Columns to flip:
--     - mean_lag_weeks    : numeric, multiplied by -1
--     - median_lag_weeks  : numeric, multiplied by -1
--     - cc_best_lag_weeks : smallint, multiplied by -1
--   Column to swap labels:
--     - lag_direction     : "Korea leads" <-> "Global leads"
--                           "Synchronous" preserved (none in current data)
--   Columns NOT changed (magnitudes, identifiers):
--     - dtw_distance, dtw_normalized, cc_max_corr, n_weeks, brand,
--       deseason_method, id, created_at
--
-- Trace preservation:
--   stage4_checkpoint.md body preserved with header footnote referencing
--   this migration + DP24 detection (per advisor decision 4).
--
-- Verification:
--   Pre-migration row count: 12 (all 4 brands × 3 deseason_method)
--   Post-migration: same 12 rows, sign-flipped values, swapped labels.
--   No rows dropped/created/added. No schema change.
--
-- Rollback:
--   Re-running this migration restores original signs/labels (idempotent on
--   even applications). For explicit rollback after odd applications, run
--   the same UPDATE again.
--
-- Recommended dry-run before commit:
--   BEGIN;
--   <run UPDATEs below>
--   <run verification SELECTs below>
--   ROLLBACK;  -- inspect, then re-run with COMMIT if correct
-- ============================================================================

-- Wrap in transaction for atomicity
BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Flip lag value signs
-- ----------------------------------------------------------------------------
UPDATE mart.korea_global_lag
SET
    mean_lag_weeks    = -mean_lag_weeks,
    median_lag_weeks  = -median_lag_weeks,
    cc_best_lag_weeks = -cc_best_lag_weeks;

-- ----------------------------------------------------------------------------
-- 2. Swap lag_direction labels
--    "Korea leads"  -> "Global leads"
--    "Global leads" -> "Korea leads"
--    "Synchronous"  -> "Synchronous" (preserved; |mean_lag| < 0.5 case)
-- ----------------------------------------------------------------------------
UPDATE mart.korea_global_lag
SET lag_direction = CASE
    WHEN lag_direction = 'Korea leads'  THEN 'Global leads'
    WHEN lag_direction = 'Global leads' THEN 'Korea leads'
    WHEN lag_direction = 'Synchronous'  THEN 'Synchronous'
    ELSE lag_direction  -- defensive: unknown label, leave untouched
END;

-- ----------------------------------------------------------------------------
-- 3. Verification queries (run these and inspect before COMMIT)
-- ----------------------------------------------------------------------------
-- Expected post-migration NB results (sign-corrected):
--   new_balance / trend       : mean_lag = -10.40, direction = 'Global leads'
--   new_balance / residual    : mean_lag = -42.19, direction = 'Global leads'
--   new_balance / search_index: mean_lag = -48.02, direction = 'Global leads'

-- Row count sanity (should equal 12)
SELECT 'row_count' AS check_name, COUNT(*) AS value
FROM mart.korea_global_lag;

-- Direction distribution (Korea/Global/Synchronous count)
SELECT 'direction_distribution' AS check_name, lag_direction, COUNT(*) AS n
FROM mart.korea_global_lag
GROUP BY lag_direction
ORDER BY lag_direction;

-- NB sign-corrected values (key reference for Stage 7 narrative)
SELECT 'nb_post_migration' AS check_name, brand, deseason_method,
       mean_lag_weeks, median_lag_weeks, cc_best_lag_weeks, lag_direction
FROM mart.korea_global_lag
WHERE brand = 'new_balance'
ORDER BY deseason_method;

-- Full result table for visual confirmation
SELECT brand, deseason_method,
       mean_lag_weeks, median_lag_weeks, cc_best_lag_weeks, lag_direction
FROM mart.korea_global_lag
ORDER BY brand, deseason_method;

-- ----------------------------------------------------------------------------
-- 4. Commit decision
-- ----------------------------------------------------------------------------
-- Applied 2026-05-03 (advisor decision 4, post-Track-A3 Stage 7 close).
-- Dry-run verification confirmed:
--   - 12 rows correctly sign-flipped (mean_lag_weeks, median_lag_weeks,
--     cc_best_lag_weeks)
--   - lag_direction labels swapped per CASE rule
--   - rollback verification: post-rollback state matches pre-migration
-- Post-commit distribution: Global leads = 10, Korea leads = 2
-- (NB rows uniformly 'Global leads' across all deseason_method, consistent
-- with Stage 7 §12.6 sentinel framing -- Global precedes Korea).

COMMIT;
