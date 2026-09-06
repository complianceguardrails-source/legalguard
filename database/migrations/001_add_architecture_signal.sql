-- Adds a real (never fabricated) architecture/framework signal to
-- banking_use_cases, sourced from the GitHub repo each use case was mined
-- from. Safe to run against an existing populated database -- additive,
-- nullable, no data loss. See ingestion/sources/architecture_enricher.py
-- for the backfill script that populates it.

ALTER TABLE banking_use_cases ADD COLUMN IF NOT EXISTS architecture_signal TEXT;

COMMENT ON COLUMN banking_use_cases.architecture_signal IS
    'Real signal from the GitHub repo this use case was mined from: a recognized agent/AI framework detected in its topics, or failing that, the repo''s primary language from the GitHub API. NULL when unset or nothing usable was found -- never fabricated.';
