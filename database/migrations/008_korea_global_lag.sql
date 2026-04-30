
-- Stage 4 Migration: Korea-Global DTW lag metrics
CREATE TABLE IF NOT EXISTS mart.korea_global_lag (
    id                  BIGSERIAL PRIMARY KEY,
    brand               brand_enum    NOT NULL,
    dtw_distance        NUMERIC(10,4),
    dtw_normalized      NUMERIC(10,6),
    mean_lag_weeks      NUMERIC(6,2),
    median_lag_weeks    NUMERIC(6,2),
    lag_direction       VARCHAR(20),          -- 'Korea leads','Global leads','Synchronous'
    cc_best_lag_weeks   SMALLINT,
    cc_max_corr         NUMERIC(6,4),
    deseason_method     VARCHAR(30),
    n_weeks             SMALLINT,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, deseason_method)
);
