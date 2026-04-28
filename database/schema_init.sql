-- ============================================================
-- nb_monitor: 3-Tier Schema Initialization
-- Database : PostgreSQL 16
-- Project  : Global Sportswear Brand Performance Monitor
-- Author   : Changyeol Oh
-- ============================================================

-- ============================================================
-- SCHEMA CREATION
-- ============================================================
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS mart;

-- ============================================================
-- SHARED TYPES
-- ============================================================
DO $$ BEGIN
    CREATE TYPE brand_enum AS ENUM ('nike','adidas','puma','new_balance');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE region_enum AS ENUM ('global','korea');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- RAW SCHEMA  (Python collectors -> raw tables)
-- ============================================================

-- Google Trends (pytrends)
CREATE TABLE IF NOT EXISTS raw.google_trends_raw (
    id            BIGSERIAL PRIMARY KEY,
    keyword       VARCHAR(200)  NOT NULL,
    region        region_enum   NOT NULL DEFAULT 'global',
    week_start    DATE          NOT NULL,
    interest      SMALLINT,                 -- 0-100 relative index
    collected_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gtr_keyword_week
    ON raw.google_trends_raw (keyword, week_start);

-- Naver DataLab (search trend + shopping insight)
CREATE TABLE IF NOT EXISTS raw.naver_datalab_raw (
    id            BIGSERIAL PRIMARY KEY,
    source_type   VARCHAR(30)   NOT NULL,   -- 'search_trend' | 'shopping_insight'
    keyword_group VARCHAR(200)  NOT NULL,
    keyword       VARCHAR(200)  NOT NULL,
    period_start  DATE          NOT NULL,
    period_end    DATE          NOT NULL,
    ratio         NUMERIC(8,4),             -- relative search ratio
    device        VARCHAR(10),              -- 'pc' | 'mobile' | 'all'
    gender        VARCHAR(10),              -- 'male' | 'female' | 'all'
    age_group     VARCHAR(20),              -- '10' | '20' | '30' | ... | 'all'
    category      VARCHAR(200),             -- shopping insight category path
    raw_json      JSONB,
    collected_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ndl_keyword_period
    ON raw.naver_datalab_raw (keyword, period_start);

-- YouTube (Data API v3)
CREATE TABLE IF NOT EXISTS raw.youtube_raw (
    id              BIGSERIAL PRIMARY KEY,
    video_id        VARCHAR(20)   NOT NULL,
    brand           brand_enum,
    title           TEXT,
    channel_title   VARCHAR(200),
    published_at    TIMESTAMPTZ,
    view_count      BIGINT,
    like_count      INTEGER,
    comment_count   INTEGER,
    comment_text    TEXT,                    -- individual comment text
    comment_author  VARCHAR(200),
    comment_date    TIMESTAMPTZ,
    collected_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_yt_brand_pub
    ON raw.youtube_raw (brand, published_at);

-- Naver Blog/Cafe
CREATE TABLE IF NOT EXISTS raw.naver_blog_raw (
    id              BIGSERIAL PRIMARY KEY,
    source_type     VARCHAR(20)   NOT NULL,  -- 'blog' | 'cafearticle'
    brand           brand_enum,
    query_keyword   VARCHAR(200),
    title           TEXT,
    description     TEXT,
    blogger_name    VARCHAR(200),
    blog_link       TEXT,
    post_date       DATE,
    collected_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_nb_brand_date
    ON raw.naver_blog_raw (brand, post_date);

-- KOSIS (Statistics Korea: retail sales index)
CREATE TABLE IF NOT EXISTS raw.kosis_raw (
    id              BIGSERIAL PRIMARY KEY,
    indicator_code  VARCHAR(50)   NOT NULL,
    indicator_name  VARCHAR(200),
    category        VARCHAR(200),            -- e.g. 'clothing_footwear'
    period          VARCHAR(10)   NOT NULL,   -- 'YYYY-MM'
    value           NUMERIC(12,4),
    unit            VARCHAR(30),
    collected_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ECOS (Bank of Korea: CSI, exchange rate)
CREATE TABLE IF NOT EXISTS raw.ecos_raw (
    id              BIGSERIAL PRIMARY KEY,
    stat_code       VARCHAR(30)   NOT NULL,
    stat_name       VARCHAR(200),
    item_code       VARCHAR(30),
    item_name       VARCHAR(200),
    period          VARCHAR(10)   NOT NULL,   -- 'YYYY-MM'
    value           NUMERIC(14,4),
    unit            VARCHAR(30),
    collected_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Financial data (SEC EDGAR 10-Q/10-K, Adidas/Puma IR, NB news)
CREATE TABLE IF NOT EXISTS raw.financials_raw (
    id              BIGSERIAL PRIMARY KEY,
    brand           brand_enum    NOT NULL,
    fiscal_period   VARCHAR(20)   NOT NULL,   -- 'FY2025-Q3', 'FY2025-H1', 'FY2025'
    metric_name     VARCHAR(100)  NOT NULL,   -- 'revenue', 'gross_margin', 'dtp_revenue'
    value           NUMERIC(16,4),
    currency        VARCHAR(5)    DEFAULT 'USD',
    source_url      TEXT,
    source_type     VARCHAR(30),              -- 'sec_10q','ir_report','news_estimate'
    collected_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fin_brand_period
    ON raw.financials_raw (brand, fiscal_period);


-- ============================================================
-- STAGING SCHEMA  (SQL transforms: clean, unify, align)
-- ============================================================

-- All search sources unified to weekly grain
CREATE TABLE IF NOT EXISTS staging.search_weekly (
    id              BIGSERIAL PRIMARY KEY,
    brand           brand_enum    NOT NULL,
    product_line    VARCHAR(50),              -- '530','992','2002r','327', NULL=brand-level
    source          VARCHAR(30)   NOT NULL,   -- 'google_trends' | 'naver_datalab'
    region          region_enum   NOT NULL,
    week_start      DATE          NOT NULL,
    week_end        DATE          NOT NULL,
    interest_index  NUMERIC(8,4),             -- normalized 0-100
    raw_id          BIGINT,
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, product_line, source, region, week_start)
);

-- YouTube + Blog social signals unified to weekly grain
CREATE TABLE IF NOT EXISTS staging.social_weekly (
    id              BIGSERIAL PRIMARY KEY,
    brand           brand_enum    NOT NULL,
    platform        VARCHAR(20)   NOT NULL,   -- 'youtube' | 'naver_blog' | 'naver_cafe'
    week_start      DATE          NOT NULL,
    mention_count   INTEGER       DEFAULT 0,
    total_views     BIGINT        DEFAULT 0,
    total_likes     INTEGER       DEFAULT 0,
    avg_sentiment   NUMERIC(5,4),             -- -1.0 to 1.0
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, platform, week_start)
);

-- Macro indicators aligned to monthly grain
CREATE TABLE IF NOT EXISTS staging.macro_monthly (
    id              BIGSERIAL PRIMARY KEY,
    indicator       VARCHAR(50)   NOT NULL,   -- 'csi', 'retail_sales_index', 'import_footwear'
    year_month      DATE          NOT NULL,   -- first day of month
    value           NUMERIC(14,4),
    yoy_pct         NUMERIC(8,4),             -- year-over-year % change
    source          VARCHAR(30)   NOT NULL,   -- 'ecos' | 'kosis' | 'customs'
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (indicator, year_month)
);

-- Financial data aligned to quarterly/semi-annual/annual
CREATE TABLE IF NOT EXISTS staging.financials_quarterly (
    id              BIGSERIAL PRIMARY KEY,
    brand           brand_enum    NOT NULL,
    fiscal_year     SMALLINT      NOT NULL,
    fiscal_quarter  SMALLINT,                 -- NULL for annual-only brands
    revenue         NUMERIC(16,4),
    revenue_currency VARCHAR(5),
    revenue_usd     NUMERIC(16,4),            -- converted to USD for comparison
    gross_margin_pct NUMERIC(6,4),
    dtp_revenue_pct  NUMERIC(6,4),            -- Direct-to-Consumer share
    source_type     VARCHAR(30),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, fiscal_year, fiscal_quarter)
);

-- Business events calendar (manual + detected)
CREATE TABLE IF NOT EXISTS staging.events_calendar (
    id              BIGSERIAL PRIMARY KEY,
    event_date      DATE          NOT NULL,
    event_end_date  DATE,
    brand           brand_enum,               -- NULL = industry-wide
    event_type      VARCHAR(50)   NOT NULL,   -- 'product_launch','campaign','macro_event','collab'
    event_name      VARCHAR(300)  NOT NULL,
    description     TEXT,
    impact_expected VARCHAR(20),               -- 'positive' | 'negative' | 'neutral'
    source          VARCHAR(100)
);


-- ============================================================
-- MART SCHEMA  (analysis & dashboard-ready tables)
-- ============================================================

-- Weekly brand KPI: the core dashboard table
CREATE TABLE IF NOT EXISTS mart.brand_kpi_weekly (
    id                  BIGSERIAL PRIMARY KEY,
    brand               brand_enum    NOT NULL,
    region              region_enum   NOT NULL,
    week_start          DATE          NOT NULL,

    -- Search metrics
    search_index        NUMERIC(8,4),
    search_wow_pct      NUMERIC(8,4),          -- week-over-week %
    search_mom_pct      NUMERIC(8,4),          -- month-over-month %
    search_yoy_pct      NUMERIC(8,4),          -- year-over-year %

    -- Share of Voice (search-based)
    sov_pct             NUMERIC(6,4),          -- brand search / total 4-brand search

    -- Social buzz composite
    social_mention_count INTEGER,
    social_sentiment_avg NUMERIC(5,4),

    -- Season context
    season_label        VARCHAR(10),            -- 'SS26','FW25', etc.
    season_week_num     SMALLINT,               -- week within season

    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, region, week_start)
);

-- NB product line weekly performance
CREATE TABLE IF NOT EXISTS mart.product_portfolio_weekly (
    id                  BIGSERIAL PRIMARY KEY,
    product_line        VARCHAR(50)   NOT NULL,  -- '530','992','2002r','327'
    region              region_enum   NOT NULL,
    week_start          DATE          NOT NULL,

    search_index        NUMERIC(8,4),
    search_wow_pct      NUMERIC(8,4),
    share_within_nb_pct NUMERIC(6,4),            -- this product / total NB search
    season_label        VARCHAR(10),

    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (product_line, region, week_start)
);

-- Channel mix weekly (contingent on Stage 0 Plan A/B/C)
CREATE TABLE IF NOT EXISTS mart.channel_mix_weekly (
    id                  BIGSERIAL PRIMARY KEY,
    brand               brand_enum    NOT NULL DEFAULT 'new_balance',
    channel             VARCHAR(50)   NOT NULL,  -- 'musinsa','d2c','coupang','search_proxy'
    data_source_plan    CHAR(1)       NOT NULL DEFAULT 'B',  -- 'A','B','C'
    week_start          DATE          NOT NULL,

    signal_value        NUMERIC(10,4),
    signal_type         VARCHAR(30),             -- 'click_share','search_ratio','ranking'
    share_pct           NUMERIC(6,4),

    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, channel, week_start)
);

-- Korea vs Global comparison (HQ Bridge)
CREATE TABLE IF NOT EXISTS mart.korea_global_comparison (
    id                  BIGSERIAL PRIMARY KEY,
    brand               brand_enum    NOT NULL,
    metric_name         VARCHAR(50)   NOT NULL,  -- 'search_index','sov_pct','social_buzz'
    week_start          DATE          NOT NULL,

    korea_value         NUMERIC(10,4),
    global_value        NUMERIC(10,4),
    divergence_pct      NUMERIC(8,4),            -- (korea - global) / global * 100
    lead_lag_weeks      SMALLINT,                -- positive = korea leads

    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (brand, metric_name, week_start)
);

-- Anomaly detection log
CREATE TABLE IF NOT EXISTS mart.anomaly_log (
    id                  BIGSERIAL PRIMARY KEY,
    brand               brand_enum,
    product_line        VARCHAR(50),
    metric_name         VARCHAR(50)   NOT NULL,
    detected_date       DATE          NOT NULL,
    anomaly_type        VARCHAR(30)   NOT NULL,  -- 'spike','dip','structural_break'
    detection_method    VARCHAR(50),              -- 'z_score','isolation_forest','stl_residual'
    severity_score      NUMERIC(6,4),
    z_score             NUMERIC(8,4),
    matched_event_id    BIGINT REFERENCES staging.events_calendar(id),
    description         TEXT,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_anom_date
    ON mart.anomaly_log (detected_date);


-- ============================================================
-- METADATA TABLE (public schema)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pipeline_run_log (
    id              BIGSERIAL PRIMARY KEY,
    stage           VARCHAR(50)   NOT NULL,     -- 'collect_google_trends','transform_staging', etc.
    status          VARCHAR(20)   NOT NULL,     -- 'started','completed','failed'
    rows_affected   INTEGER,
    error_message   TEXT,
    started_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);

-- ============================================================
-- GRANT (collector role writes raw; analyst role reads all)
-- ============================================================
-- Uncomment and adjust when deploying with role separation:
-- GRANT USAGE ON SCHEMA raw     TO collector_role;
-- GRANT INSERT, SELECT ON ALL TABLES IN SCHEMA raw TO collector_role;
-- GRANT USAGE ON SCHEMA staging TO analyst_role;
-- GRANT USAGE ON SCHEMA mart    TO analyst_role;
-- GRANT SELECT ON ALL TABLES IN SCHEMA staging TO analyst_role;
-- GRANT SELECT ON ALL TABLES IN SCHEMA mart    TO analyst_role;
