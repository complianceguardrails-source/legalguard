-- The FINOS AI Governance Framework (github.com/finos/ai-governance-framework):
-- 23 risks and 23 mitigations agreed by member banks, each carrying
-- cross-references to EU AI Act articles, ISO 42001, NIST SP 800-53 and
-- the FFIEC booklets. Fetched by ingestion/ingest_finos_framework.py.
--
-- risk_slugs maps a FINOS risk onto this app's own granular risks
-- (ingestion/finos_crosswalk.py); crosswalk_note is why. Both are NULL on
-- a mitigation, which reaches our risks through the risks it mitigates.
-- "references" is reserved in Postgres, hence framework_references.
CREATE TABLE IF NOT EXISTS finos_framework_entries (
    entry_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id          TEXT NOT NULL UNIQUE,          -- "ri-17", "mi-13"
    kind                 VARCHAR(12) NOT NULL CHECK (kind IN ('risk', 'mitigation')),
    sequence             INTEGER NOT NULL,
    title                TEXT NOT NULL,
    type_code            VARCHAR(8),                    -- OP | SEC | RC | PREV | DET | COR
    type_label           TEXT,
    doc_status           TEXT,
    summary              TEXT,                          -- the entry's own opening prose
    framework_references JSONB,                         -- {"eu-ai-act": [...], "iso-42001": [...], ...}
    mitigates            TEXT[],                        -- mitigation -> the FINOS risks it addresses
    risk_slugs           TEXT[],                        -- risk -> our risk_taxonomy slugs
    crosswalk_note       TEXT,
    url                  TEXT NOT NULL,
    fetched_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_finos_risk_slugs ON finos_framework_entries USING GIN (risk_slugs);
CREATE INDEX IF NOT EXISTS idx_finos_mitigates ON finos_framework_entries USING GIN (mitigates);

GRANT SELECT ON finos_framework_entries TO web_anon;
