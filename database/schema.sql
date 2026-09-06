-- LegalGuard core schema
-- Target: any managed Postgres (Neon.tech free tier, Supabase free tier, or local Postgres).
-- Design principle: regulations are NEVER merged/deduped across jurisdictions, even when
-- near-identical in substance. A single guardrail package may be indexed by MANY regulations
-- (many-to-many), and one regulation may motivate MANY guardrail packages.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- for gen_random_uuid() fallback on some hosts

-- ---------------------------------------------------------------------------
-- 1. Banking / financial AI use-case registry (the "knowledge base")
-- ---------------------------------------------------------------------------
CREATE TABLE banking_use_cases (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(200) NOT NULL,               -- e.g. "Buy-to-Let Rental Stress Testing"
    parent_sector       VARCHAR(100) NOT NULL,               -- Consumer Finance | CIB | Wealth Mgmt | Ops & Risk | Front Office
    modality            VARCHAR(50)  NOT NULL,               -- structured | vision | voice_agentic | rag_document | multi_agent
    description         TEXT,
    github_reference_url TEXT,                               -- open-source repo this use case was mined from
    -- Real signal read from that repo via the GitHub API: a recognized
    -- agent/AI framework detected in its topics (e.g. "LangChain", "Google
    -- ADK"), falling back to the repo's primary language (e.g. "Python")
    -- when no known framework topic is present. NULL when there's no linked
    -- repo, or the API call found nothing usable -- never a guessed value.
    -- See ingestion/sources/architecture_enricher.py.
    architecture_signal  TEXT,
    risk_tier            VARCHAR(30) DEFAULT 'unclassified'
        CHECK (risk_tier IN ('unclassified', 'prohibited', 'high_risk', 'limited_risk', 'minimal_risk')),
    source                VARCHAR(30) NOT NULL DEFAULT 'curated'
        CHECK (source IN ('curated', 'github_mined', 'user_submitted')),
    submitted_by_github_username VARCHAR(150), -- set when source = 'user_submitted'
    -- Self-reported coarse country/region codes (US, EU, UK, OTHER) --
    -- biases the client-side match preview toward relevant jurisdictions,
    -- not a certified determination. See
    -- database/migrations/004_add_operating_jurisdictions.sql.
    operating_jurisdictions TEXT[],
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (name)
);

CREATE INDEX idx_use_cases_sector   ON banking_use_cases(parent_sector);
CREATE INDEX idx_use_cases_modality ON banking_use_cases(modality);
CREATE INDEX idx_use_cases_source   ON banking_use_cases(source);

-- Prevents the GitHub miner from inserting the same repo twice under a
-- slightly different name; NULLs (curated/user_submitted rows with no repo
-- link) are unconstrained since a partial index only covers non-null values.
CREATE UNIQUE INDEX idx_use_cases_github_url ON banking_use_cases(github_reference_url)
    WHERE github_reference_url IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 2. Individual regulations / statutory clauses -- one row per distinct clause
--    version. Two jurisdictions with similar text get two separate rows.
-- ---------------------------------------------------------------------------
CREATE TABLE specific_regulations (
    reg_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jurisdiction        VARCHAR(50)  NOT NULL,   -- EU | US | US-CA | UK | CN | SG ...
    issuing_body        VARCHAR(400) NOT NULL,   -- EBA | CFPB | FCA | EU AI Office | Federal Register agency slug
                                                  -- (wide enough for joint interagency filings, e.g. a single
                                                  -- CFPB+Fed+OCC+FDIC+FinCEN document's combined agency-name string,
                                                  -- confirmed to exceed 150 chars via a real API response)
    clause_identifier   VARCHAR(150) NOT NULL,   -- e.g. "Art.10(2)_DataGovernance" or a Federal Register document number
    official_title      TEXT,
    source_url          TEXT NOT NULL,
    statutory_text       TEXT NOT NULL,
    version_label        VARCHAR(30)  NOT NULL DEFAULT 'v1',
    publication_date     DATE,
    effective_date       DATE,
    enforcement_penalty_max NUMERIC(18, 2),
    risk_level           VARCHAR(30),             -- prohibited | high_risk | limited_risk | minimal_risk
    content_sha256        CHAR(64) NOT NULL,       -- dedup fingerprint (see ingestion/cache dedup)
    ingestion_source      VARCHAR(50) NOT NULL,    -- federal_register | rss | manual | horizon_llm
    -- What upstream force plausibly produced this regulation. This is what
    -- lets the Horizon screen argue "regulator X will likely act next"
    -- instead of just listing manually-seeded guesses -- see
    -- origin_driver_trend_summary below. Coarse/heuristic by design (see
    -- ingestion/tagger.py::classify_origin_driver); treat as a hypothesis
    -- to confirm, not a certified causal claim.
    origin_driver_category VARCHAR(30)
        CHECK (origin_driver_category IN (
            'market_scandal',            -- reactive: bias/fraud/harm incidents forced the regulator's hand
            'capability_leap',           -- a new model/agent capability outran existing rules
            'geopolitical_sovereignty',  -- data residency / national-security driven
            'standards_harmonization'    -- codifies an existing ISO/NIST/OECD-style standard into binding law
        )),
    origin_driver_description TEXT,     -- human-readable justification for the category above
    -- Short display name, distinct from official_title (which holds the
    -- full formal citation, e.g. "EU AI Act Article 10 -- Data and Data
    -- Governance (Regulation (EU) 2024/1689)"). e.g. "EU AI Act -- Data &
    -- Data Governance (Art. 10)". Nullable: falls back to official_title
    -- in the UI when not set.
    title                  VARCHAR(300),
    -- How big a deal this regulation is for guardrail work, independent of
    -- which specific guardrail(s) end up mapped to it via
    -- guardrail_regulatory_mapping.impact_tier (that table's value is
    -- per-guardrail; this one is the regulation's own overall classification).
    impact_level            VARCHAR(50)
        CHECK (impact_level IN ('Brand New Guardrail Required', 'Version Revision Trigger')),
    -- Whether a guardrail action has actually been taken in response to this
    -- regulation yet -- distinct from any single guardrail_packages.status,
    -- since one regulation can motivate several guardrails at different
    -- stages.
    dispatch_status         VARCHAR(30) NOT NULL DEFAULT 'Not Dispatched'
        CHECK (dispatch_status IN ('Not Dispatched', 'Dispatched')),
    -- A specific, actionable one-line instruction for what to actually
    -- change in code (e.g. "Lower max_dti_ratio 0.45->0.40"), not a
    -- generic template. Left NULL for auto-ingested rows: producing a good
    -- one requires either human review or a real LLM call, not the
    -- keyword-heuristic classifiers this pipeline uses elsewhere -- see
    -- docs/ARCHITECTURE.md's "what's real vs a stub" table.
    remediation_blueprint    TEXT,
    -- Free-text note when this regulation supersedes or is superseded by
    -- another (e.g. "Supersedes SR 11-7"). NULL when not applicable.
    supersession_note        TEXT,
    -- Direct "blast radius" onto use cases, populated by
    -- ingestion/tagger.py::tag_regulation. This is denormalized on purpose:
    -- it's a candidate list for a human to confirm, computed even before
    -- any guardrail_packages row exists for this regulation, whereas
    -- guardrail_regulatory_mapping only links regs to guardrails that
    -- already exist.
    affected_use_case_ids    UUID[] NOT NULL DEFAULT '{}',
    -- Whether source_url actually points at the issuing regulator's own
    -- page, or a secondary mirror/summary (news, think tank, commercial
    -- compliance tool, Wikipedia) -- see ingestion/source_url_classifier.py.
    -- 'unknown' means the domain didn't match a recognized pattern either
    -- way and needs manual verification, not an unearned "primary" label.
    source_url_classification VARCHAR(20)
        CHECK (source_url_classification IN ('primary', 'secondary', 'unknown')),
    source_url_classification_note TEXT,
    created_at            TIMESTAMPTZ DEFAULT now(),
    UNIQUE (jurisdiction, issuing_body, clause_identifier, version_label)
);

CREATE INDEX idx_reg_jurisdiction   ON specific_regulations(jurisdiction);
CREATE INDEX idx_reg_hash           ON specific_regulations(content_sha256);
CREATE INDEX idx_reg_effective      ON specific_regulations(effective_date);
CREATE INDEX idx_reg_impact_level   ON specific_regulations(impact_level);
CREATE INDEX idx_reg_dispatch       ON specific_regulations(dispatch_status);
CREATE INDEX idx_reg_origin_driver  ON specific_regulations(origin_driver_category);

-- ---------------------------------------------------------------------------
-- 3. Guardrail packages -- the artifacts LegalGuard actually pushes to GitHub
-- ---------------------------------------------------------------------------
CREATE TABLE guardrail_packages (
    guardrail_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    use_case_id            UUID REFERENCES banking_use_cases(id) ON DELETE SET NULL,
    name                   VARCHAR(150) NOT NULL,   -- e.g. "guardrail-voice-agentic-customer-support"
    github_owner           VARCHAR(150),            -- populated per-user at push time, nullable in shared KB
    github_repo_url        TEXT,
    policy_framework       VARCHAR(50) NOT NULL DEFAULT 'open_policy_agent', -- open_policy_agent | cedar | python_middleware
    current_semver         VARCHAR(20) NOT NULL DEFAULT 'v1.0.0',
    compiled_code_payload  TEXT NOT NULL,           -- the actual .rego / .py template text
    status                 VARCHAR(30) NOT NULL DEFAULT 'draft', -- draft | proposed | staged | merged | deprecated (git lifecycle)
    -- Separate from `status` above on purpose: `status` tracks where the
    -- PR/repo is in the git workflow, `compliance_status` tracks whether
    -- the *policy itself* currently satisfies its mapped regulations. A
    -- guardrail can be `merged` (git-wise done) yet `action_required`
    -- (compliance-wise stale) if a regulation changed since the last merge.
    -- This is exactly the Compliant/Action Required/Breaches split on
    -- Base44's Radar dashboard tiles.
    compliance_status      VARCHAR(30) NOT NULL DEFAULT 'action_required'
        CHECK (compliance_status IN ('compliant', 'action_required', 'deprecated', 'critical_breach')),
    -- true only for a real, hand-built reference repo registered by the
    -- admin via ingestion/register_admin_reference.py -- distinguishes it
    -- from the demo placeholder rows in seed.sql (NULL github_owner/
    -- github_repo_url) and from any future per-user-generated row. See
    -- database/migrations/003_add_admin_reference_guardrails.sql.
    is_admin_reference     BOOLEAN NOT NULL DEFAULT false,
    created_at             TIMESTAMPTZ DEFAULT now(),
    updated_at             TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_guardrail_use_case        ON guardrail_packages(use_case_id);
CREATE INDEX idx_guardrail_status          ON guardrail_packages(status);
CREATE INDEX idx_guardrail_compliance      ON guardrail_packages(compliance_status);

-- At most one admin-curated reference repo per use case.
CREATE UNIQUE INDEX idx_guardrail_admin_reference_per_use_case
    ON guardrail_packages(use_case_id)
    WHERE is_admin_reference = true;

-- ---------------------------------------------------------------------------
-- 4. Many-to-many junction: which regulations justify which guardrail package.
--    This is the table that keeps regulations UN-merged: a guardrail can carry
--    provenance from N distinct regulations; a regulation can motivate N
--    distinct guardrails (e.g. one clause affects both a voice-agent guardrail
--    and a document-processing guardrail).
-- ---------------------------------------------------------------------------
CREATE TABLE guardrail_regulatory_mapping (
    mapping_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reg_id         UUID NOT NULL REFERENCES specific_regulations(reg_id) ON DELETE RESTRICT,
    guardrail_id   UUID NOT NULL REFERENCES guardrail_packages(guardrail_id) ON DELETE CASCADE,
    impact_tier    VARCHAR(50) NOT NULL DEFAULT 'version_revision', -- version_revision | new_guardrail_required
    mandate_summary TEXT,          -- human-readable: what this specific reg requires of this guardrail
    indexed_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE (reg_id, guardrail_id)
);

CREATE INDEX idx_mapping_reg        ON guardrail_regulatory_mapping(reg_id);
CREATE INDEX idx_mapping_guardrail  ON guardrail_regulatory_mapping(guardrail_id);

-- ---------------------------------------------------------------------------
-- 5. Predictive "Horizon" forecasts -- upcoming/speculative regulatory shifts
-- ---------------------------------------------------------------------------
CREATE TABLE regulatory_horizon_forecast (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    projected_bill_name         VARCHAR(200) NOT NULL,
    target_jurisdiction         VARCHAR(50) NOT NULL,
    estimated_arrival_window    VARCHAR(50) NOT NULL,   -- e.g. "Q3 2027"
    probability_percentage      INT CHECK (probability_percentage BETWEEN 0 AND 100),
    upstream_catalyst_drivers   TEXT[] NOT NULL DEFAULT '{}', -- {"market_scandal","capability_leap","geopolitics"}
    underlying_driver_description TEXT NOT NULL,
    impact_blast_radius_summary TEXT NOT NULL,
    affected_use_case_ids       UUID[] NOT NULL DEFAULT '{}',
    suggested_proactive_guardrail_logic TEXT,
    status                       VARCHAR(30) NOT NULL DEFAULT 'watching', -- watching | pre_staged | superseded_by_law
    -- Set only on rows generated by ingestion/generate_horizon_forecasts.py
    -- from real origin_driver_trend_summary data (see section 8 below) --
    -- format 'trend:{jurisdiction}:{origin_driver_category}'. NULL for
    -- hand-authored seed rows. Lets that script upsert idempotently instead
    -- of duplicating a forecast every time it re-runs.
    trend_key                    TEXT,
    created_at                   TIMESTAMPTZ DEFAULT now(),
    updated_at                   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_horizon_jurisdiction ON regulatory_horizon_forecast(target_jurisdiction);
CREATE INDEX idx_horizon_status       ON regulatory_horizon_forecast(status);
CREATE UNIQUE INDEX idx_horizon_trend_key ON regulatory_horizon_forecast(trend_key)
    WHERE trend_key IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 6. Ingestion dedup cache -- replaces a Redis dependency for the zero-budget
--    build. One row per (source, document_id); the content hash is compared
--    on every crawl pass to skip unchanged documents.
-- ---------------------------------------------------------------------------
CREATE TABLE ingestion_cache (
    cache_key       TEXT PRIMARY KEY,     -- '{source}:{jurisdiction}:{issuing_body}:{document_id}'
    content_sha256  CHAR(64) NOT NULL,
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          VARCHAR(30) NOT NULL DEFAULT 'active' -- active | proactive_draft
);

-- ---------------------------------------------------------------------------
-- 7. Per-user app state (no passwords stored -- auth is GitHub OAuth/PAT held
--    client-side only; this table just remembers which use cases/repos a
--    given GitHub login has opted into tracking, and their notification prefs)
-- ---------------------------------------------------------------------------
CREATE TABLE user_subscriptions (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_username  VARCHAR(150) NOT NULL,
    use_case_id      UUID NOT NULL REFERENCES banking_use_cases(id) ON DELETE CASCADE,
    target_repo_url  TEXT,              -- which of the user's own repos guardrails get pushed to
    notify_push      BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE (github_username, use_case_id)
);

CREATE INDEX idx_subscriptions_user ON user_subscriptions(github_username);

-- ---------------------------------------------------------------------------
-- 8. Origin-driver trend summary -- aggregates labeled regulations by
--    category/jurisdiction/quarter so the Horizon screen's predictions can
--    point at actual counts ("6 capability_leap-driven rules in the UK over
--    the last 3 quarters") instead of being purely hand-authored guesses.
--    Exposed read-only via PostgREST like any other view.
-- ---------------------------------------------------------------------------
CREATE VIEW origin_driver_trend_summary AS
SELECT
    jurisdiction,
    origin_driver_category,
    date_trunc('quarter', publication_date)::date AS quarter,
    count(*) AS regulation_count
FROM specific_regulations
WHERE origin_driver_category IS NOT NULL
  AND publication_date IS NOT NULL
GROUP BY jurisdiction, origin_driver_category, date_trunc('quarter', publication_date)
ORDER BY quarter DESC, regulation_count DESC;

-- ---------------------------------------------------------------------------
-- 9. Guardrail compliance summary -- the exact three counts the Radar
--    dashboard tiles show (Compliant / Action Req. / Breaches). PostgREST
--    can't GROUP BY on the fly, so this view does the aggregation once.
-- ---------------------------------------------------------------------------
CREATE VIEW guardrail_compliance_summary AS
SELECT compliance_status, count(*) AS guardrail_count
FROM guardrail_packages
GROUP BY compliance_status;

-- ---------------------------------------------------------------------------
-- Row-Level Security: left OFF by default (single shared knowledge base, no
-- multi-tenant secrets live in Postgres -- GitHub tokens never touch this DB).
-- If you later add server-held tokens, enable RLS keyed on github_username.
--
-- One exception worth calling out: banking_use_cases now accepts
-- user-submitted rows (source = 'user_submitted') via PostgREST INSERT --
-- see docs/POSTGREST.md for the narrow grant this requires and why it's
-- scoped to just that one table/operation rather than opening writes
-- broadly.
-- ---------------------------------------------------------------------------
