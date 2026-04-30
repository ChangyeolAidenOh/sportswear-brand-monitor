-- ============================================================
-- Migration 007: Rename social_sentiment_avg → social_sentiment_static
-- Rationale: cross-sectional single value, not weekly time-series.
-- Intentional denormalization — JOIN overhead unnecessary for
-- a brand-level constant. See stage3_checkpoint.md.
-- ============================================================

ALTER TABLE mart.brand_kpi_weekly
    RENAME COLUMN social_sentiment_avg TO social_sentiment_static;
