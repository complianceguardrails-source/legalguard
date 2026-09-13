-- Four real classification dimensions, each backed by genuine, checkable
-- evidence (never a guessed/fabricated default -- null means "no real
-- evidence found", not "not applicable"):
--
-- hf_model_id / model_modality: set by ingestion/sources/huggingface_usecases.py
--   from the real Hugging Face Hub pipeline_tag/library_name for mined models.
-- system_interface_type / agent_operational_tools: set by
--   ingestion/sources/architecture_enricher.py's manifest-dependency scan
--   (requirements.txt / pyproject.toml / package.json) for GitHub-sourced repos.
-- data_interception_state: derived directly from the existing `modality`
--   column (voice_agentic/multi_agent/rag_document -> stateful-trace,
--   structured/vision -> stateless-payload).

ALTER TABLE banking_use_cases
    ADD COLUMN IF NOT EXISTS hf_model_id TEXT,
    ADD COLUMN IF NOT EXISTS model_modality VARCHAR(30)
        CHECK (model_modality IN ('decoder-only', 'encoder-only', 'tabular-regressor')),
    ADD COLUMN IF NOT EXISTS system_interface_type VARCHAR(30)
        CHECK (system_interface_type IN ('rest-api', 'rpc-gateway', 'websocket-stream')),
    ADD COLUMN IF NOT EXISTS agent_operational_tools TEXT[],
    ADD COLUMN IF NOT EXISTS data_interception_state VARCHAR(30)
        CHECK (data_interception_state IN ('stateless-payload', 'stateful-trace'));

-- Same partial-unique pattern as github_reference_url -- HF-mined rows get
-- their own dedup key distinct from GitHub-sourced rows.
CREATE UNIQUE INDEX IF NOT EXISTS idx_use_cases_hf_model_id ON banking_use_cases(hf_model_id)
    WHERE hf_model_id IS NOT NULL;

COMMENT ON COLUMN banking_use_cases.hf_model_id IS
    'Hugging Face Hub model id (e.g. "ProsusAI/finbert") for HF-mined rows. NULL for GitHub-sourced/curated rows.';
COMMENT ON COLUMN banking_use_cases.model_modality IS
    'Derived from the real HF pipeline_tag (or library_name fallback for sklearn/xgboost/etc). NULL where HF has no usable metadata for this model -- common for community uploads, not a classification failure.';
COMMENT ON COLUMN banking_use_cases.system_interface_type IS
    'Derived from a real dependency match in the repo''s requirements.txt/pyproject.toml/package.json (e.g. fastapi -> rest-api). NULL where no manifest file was found or no recognized dependency matched.';
COMMENT ON COLUMN banking_use_cases.agent_operational_tools IS
    'Real dependency matches indicating DB/vector-store or trade-execution SDKs (e.g. sqlalchemy, ccxt). A repo can have both; empty/NULL means no recognized dependency matched.';
COMMENT ON COLUMN banking_use_cases.data_interception_state IS
    'Derived directly from modality: voice_agentic/multi_agent/rag_document -> stateful-trace, structured/vision -> stateless-payload.';

-- New source value for the Hugging Face mining pipeline (ingestion/sources/
-- huggingface_usecases.py), distinct from github_mined/curated/user_submitted.
ALTER TABLE banking_use_cases DROP CONSTRAINT IF EXISTS banking_use_cases_source_check;
ALTER TABLE banking_use_cases ADD CONSTRAINT banking_use_cases_source_check
    CHECK (source IN ('curated', 'github_mined', 'user_submitted', 'huggingface_mined'));

-- One-time backfill for existing rows -- purely derived, no external
-- lookup needed, safe to run immediately for every existing use case.
UPDATE banking_use_cases
SET data_interception_state = CASE
    WHEN modality IN ('voice_agentic', 'multi_agent', 'rag_document') THEN 'stateful-trace'
    WHEN modality IN ('structured', 'vision') THEN 'stateless-payload'
    ELSE NULL
END
WHERE data_interception_state IS NULL;
