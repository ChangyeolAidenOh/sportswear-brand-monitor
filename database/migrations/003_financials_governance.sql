-- Migration 003: financials_raw governance columns
-- Adds source_tier, note, and expands UNIQUE to include source_type

-- 1. source_tier
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'raw'
          AND table_name   = 'financials_raw'
          AND column_name  = 'source_tier'
    ) THEN
        ALTER TABLE raw.financials_raw
            ADD COLUMN source_tier SMALLINT NOT NULL DEFAULT 4
            CHECK (source_tier BETWEEN 1 AND 4);
    END IF;
END $$;

COMMENT ON COLUMN raw.financials_raw.source_tier IS
    '1=Primary disclosure (SEC/DART/IR), 2=Licensee official PR, 3=Credit rating, 4=Media/CEO statement';

-- 2. note
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'raw'
          AND table_name   = 'financials_raw'
          AND column_name  = 'note'
    ) THEN
        ALTER TABLE raw.financials_raw ADD COLUMN note TEXT;
    END IF;
END $$;

-- 3. Expand UNIQUE to include source_type
DO $$
DECLARE
    old_constraint TEXT;
BEGIN
    -- Drop old 3-col constraint if exists
    SELECT conname INTO old_constraint
    FROM pg_constraint
    WHERE conrelid = 'raw.financials_raw'::regclass
      AND conname  = 'uq_fin_brand_period_metric';

    IF old_constraint IS NOT NULL THEN
        EXECUTE format(
            'ALTER TABLE raw.financials_raw DROP CONSTRAINT %I',
            old_constraint
        );
    END IF;

    -- Add 4-col constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'raw.financials_raw'::regclass
          AND conname  = 'uq_fin_brand_period_metric_source'
    ) THEN
        ALTER TABLE raw.financials_raw
            ADD CONSTRAINT uq_fin_brand_period_metric_source
            UNIQUE (brand, fiscal_period, metric_name, source_type);
    END IF;
END $$;
