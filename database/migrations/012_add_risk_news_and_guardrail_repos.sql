-- Two feeds that map the world onto the risk taxonomy
-- (ingestion/risk_taxonomy.py slugs and family keys).
--
-- risk_news_stories: headlines from trusted financial outlets and
-- regulators, kept only when they are about AI and match at least one
-- risk. Title and summary come from the outlet's own RSS; the story is
-- linked, never copied. One row per URL.
--
-- guardrail_repos: open-source repositories (GitHub) and Hub artefacts
-- (Hugging Face) that implement a technical control for one or more
-- risks -- drift detection, explainers, bias audits, prompt-injection
-- filters, deepfake detectors. Found by per-risk searches in
-- ingestion/guardrail_repo_queries.py and stored with the evidence that
-- matched. One row per platform + repo id.
CREATE TABLE IF NOT EXISTS risk_news_stories (
    story_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url           TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    summary       TEXT,
    outlet        VARCHAR(120) NOT NULL,        -- e.g. "Financial Times", "SEC"
    outlet_kind   VARCHAR(20) NOT NULL          -- news | regulator
        CHECK (outlet_kind IN ('news', 'regulator')),
    published_at  TIMESTAMPTZ,
    risk_slugs    TEXT[] NOT NULL,              -- risk_taxonomy slugs matched
    families      TEXT[] NOT NULL,              -- their families, deduped
    matched_terms TEXT[] NOT NULL,              -- the phrases that matched, for review
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_risk_news_published ON risk_news_stories (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_news_families ON risk_news_stories USING GIN (families);
CREATE INDEX IF NOT EXISTS idx_risk_news_risks ON risk_news_stories USING GIN (risk_slugs);

CREATE TABLE IF NOT EXISTS guardrail_repos (
    repo_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform      VARCHAR(20) NOT NULL CHECK (platform IN ('github', 'huggingface')),
    external_id   TEXT NOT NULL,                -- "owner/name" on either platform
    url           TEXT NOT NULL,
    name          TEXT NOT NULL,
    description   TEXT,
    stars         INTEGER,                      -- GitHub stars / Hub likes
    downloads     INTEGER,                      -- Hub downloads, NULL on GitHub
    language      VARCHAR(60),
    license       VARCHAR(80),
    last_pushed_at TIMESTAMPTZ,
    risk_slugs    TEXT[] NOT NULL,
    families      TEXT[] NOT NULL,
    evidence      JSONB NOT NULL,               -- [{risk, query, matched}] how each risk was assigned
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (platform, external_id)
);
CREATE INDEX IF NOT EXISTS idx_guardrail_repos_risks ON guardrail_repos USING GIN (risk_slugs);
CREATE INDEX IF NOT EXISTS idx_guardrail_repos_stars ON guardrail_repos (stars DESC NULLS LAST);

GRANT SELECT ON risk_news_stories, guardrail_repos TO web_anon;
