-- Which use-case categories a forthcoming regulation would reach, and the
-- phrases in the forecast's own text that placed it there. Derived by
-- ingestion/tag_horizon_categories.py with the same matcher that
-- categorises use cases, so a forecast and a use case are placed against
-- the same vocabulary. NULL = no category matched, which the app states
-- rather than hides.
ALTER TABLE regulatory_horizon_forecast ADD COLUMN IF NOT EXISTS affected_categories TEXT[];
ALTER TABLE regulatory_horizon_forecast ADD COLUMN IF NOT EXISTS category_evidence JSONB;
