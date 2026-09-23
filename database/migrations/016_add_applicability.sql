-- Whether a use case is a financial system, or a system a financial firm
-- could adapt.
--
-- 'deployed' is everything the catalogue held until now: built for
-- finance, and shown as such. 'translatable' is an earth-observation
-- capability that was not built for finance -- a flood model, a building
-- footprint segmenter -- together with the financial decision it could
-- feed and what a firm would have to supply first
-- (ingestion/spatial_translation.py). The app keeps the two apart: the
-- main deck and the counts are 'deployed' only, and translatable systems
-- are reached through their own clearly-labelled section, so a card is
-- never mistaken for a system already doing the job.
ALTER TABLE banking_use_cases ADD COLUMN IF NOT EXISTS applicability VARCHAR(16) NOT NULL DEFAULT 'deployed'
    CHECK (applicability IN ('deployed', 'translatable'));
ALTER TABLE banking_use_cases ADD COLUMN IF NOT EXISTS translation JSONB;
CREATE INDEX IF NOT EXISTS idx_use_cases_applicability ON banking_use_cases (applicability);
