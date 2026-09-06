-- Self-reported operating-region signal for user-submitted use cases, used
-- to bias the client-side match preview (app/lib/tagger.js) toward
-- jurisdictions actually relevant to the submitter -- coarse country/region
-- codes (US, EU, UK, OTHER), not a certified jurisdiction determination.
-- See app/screens/KnowledgeBaseScreen.js's "Where does this operate?"
-- question.

ALTER TABLE banking_use_cases ADD COLUMN IF NOT EXISTS operating_jurisdictions TEXT[];

COMMENT ON COLUMN banking_use_cases.operating_jurisdictions IS
    'Self-reported by the submitter (or inferred for mined/curated rows later) -- coarse country/region codes (US, EU, UK, OTHER), used to bias the client-side match preview toward relevant jurisdictions, not a certified determination.';
