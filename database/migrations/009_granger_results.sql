-- ============================================================
-- Migration 009: Granger Causality Test Results (Bidirectional)
-- Stage 4 Track A output table
-- Supports: Search->CSI, CSI->Search, web_residual, shopping
-- ============================================================

CREATE TABLE IF NOT EXISTS mart.granger_results (
    id                  BIGSERIAL PRIMARY KEY,
    brand               brand_enum    NOT NULL,
    region              region_enum   NOT NULL,
    direction           VARCHAR(20)   NOT NULL,   -- 'Search->CSI','CSI->Search'
    cause_variable      VARCHAR(50)   NOT NULL,   -- 'search_residual','csi','shopping'
    effect_variable     VARCHAR(50)   NOT NULL,   -- 'csi','search_residual'
    lag_months          SMALLINT      NOT NULL,
    f_statistic         NUMERIC(10,4),
    p_value             NUMERIC(8,6),
    significant         BOOLEAN,
    input_type          VARCHAR(30)   DEFAULT 'web_residual',  -- 'web_residual','shopping'
    n_obs               SMALLINT,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, region, direction, cause_variable, lag_months, input_type)
);
