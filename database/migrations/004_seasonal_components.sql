-- ============================================================
-- Migration 004: mart.seasonal_components
-- Stage 3 Step A1 — STL seasonal decomposition output
-- ============================================================

CREATE TABLE IF NOT EXISTS mart.seasonal_components (
    id              BIGSERIAL PRIMARY KEY,
    brand           brand_enum    NOT NULL,
    region          region_enum   NOT NULL,
    week_start      DATE          NOT NULL,
    metric_name     VARCHAR(50)   NOT NULL DEFAULT 'search_index',

    observed        NUMERIC(10,4),
    trend           NUMERIC(10,4),
    seasonal        NUMERIC(10,4),
    residual        NUMERIC(10,4),

    decomposition_method VARCHAR(10) NOT NULL DEFAULT 'STL',
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    UNIQUE (brand, region, week_start, metric_name, decomposition_method)
);

CREATE INDEX IF NOT EXISTS idx_sc_brand_region_week
    ON mart.seasonal_components (brand, region, week_start);
