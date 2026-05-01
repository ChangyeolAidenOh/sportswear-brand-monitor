-- Migration 010: Add event_origin column to staging.events_calendar
-- Stage 5: Distinguishes independently known events from anomaly-investigated ones
-- for honest Precision/Recall (Event Detection Rate) reporting.

ALTER TABLE staging.events_calendar
    ADD COLUMN IF NOT EXISTS event_origin VARCHAR(20);

COMMENT ON COLUMN staging.events_calendar.event_origin IS
    'scheduled = known independently of anomaly detection; '
    'investigated = found via anomaly-driven retroactive research';
