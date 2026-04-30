-- ============================================================
-- Migration 006: staging.blog_sentiment
-- Stage 3 Step B2 — Hybrid sentiment scoring results
-- ============================================================

CREATE TABLE IF NOT EXISTS staging.blog_sentiment (
    id              BIGSERIAL PRIMARY KEY,
    raw_id          BIGINT NOT NULL,          -- raw.naver_blog_raw.id
    source_type     VARCHAR(20),              -- 'blog' / 'cafearticle'
    brand           brand_enum,

    -- Keyword scoring (1st pass)
    keyword_score   NUMERIC(5,4),
    keyword_label   VARCHAR(20),              -- 'positive','negative','neutral','uncertain'
    keyword_n_matches INTEGER DEFAULT 0,
    is_sponsored    BOOLEAN DEFAULT FALSE,

    -- API scoring (2nd pass, uncertain cases only)
    api_label       VARCHAR(20),              -- NULL until API response
    api_confidence  NUMERIC(5,4),             -- NULL until API response

    -- Final result
    final_label     VARCHAR(20),              -- keyword_label or api_label
    final_source    VARCHAR(10),              -- 'keyword' or 'api'

    scored_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (raw_id)
);

CREATE INDEX IF NOT EXISTS idx_bs_brand_label
    ON staging.blog_sentiment (brand, final_label);

CREATE INDEX IF NOT EXISTS idx_bs_needs_api
    ON staging.blog_sentiment (keyword_label)
    WHERE keyword_label = 'uncertain' AND api_label IS NULL;
