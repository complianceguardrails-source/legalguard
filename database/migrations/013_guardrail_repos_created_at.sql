-- When the repository was created on its platform, so "emerging" (new
-- this quarter) can be shown from the row itself rather than inferred.
ALTER TABLE guardrail_repos ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
