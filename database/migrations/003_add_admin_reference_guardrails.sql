-- Distinguishes an admin-curated real reference guardrail repo (hand-built
-- by the LegalGuard maintainer under their own GitHub account) from the
-- hand-authored demo placeholder rows in seed.sql (NULL github_owner/
-- github_repo_url, present only so Radar's dashboard tiles have non-zero
-- counts) and from any future per-user-generated row. Written by
-- ingestion/register_admin_reference.py -- an admin-run script, not a
-- PostgREST write grant, since only the maintainer curates these.

ALTER TABLE guardrail_packages
    ADD COLUMN IF NOT EXISTS is_admin_reference BOOLEAN NOT NULL DEFAULT false;

-- At most one admin-curated reference repo per use case -- a second admin
-- registration for the same use_case_id updates the existing row instead of
-- creating a competing one. Partial index so ordinary rows
-- (is_admin_reference = false, including the seed.sql placeholders) stay
-- unconstrained, same as today.
CREATE UNIQUE INDEX IF NOT EXISTS idx_guardrail_admin_reference_per_use_case
    ON guardrail_packages(use_case_id)
    WHERE is_admin_reference = true;

COMMENT ON COLUMN guardrail_packages.is_admin_reference IS
    'true only for rows registered via ingestion/register_admin_reference.py -- a real, hand-built reference guardrail repo under the admin''s own GitHub account for this use case. false for seed.sql demo placeholders and any other row.';
