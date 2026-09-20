-- Hugging Face model card text for HF-mined use cases
-- (ingestion/enrich_hf_model_cards.py).
--
-- The Hub's list endpoint returns no card text, so HF rows were mined with
-- the placeholder description "Hugging Face model (<pipeline_tag>)" and the
-- keyword classifiers saw only the model ID and tags. After the tag/org
-- discovery expansion (932 HF rows), 43% sat at Uncategorized and 94% at
-- unclassified risk -- including an AML sanctions screener. The card README
-- is the evidence the classifiers need; this stores it so the
-- classification can be re-run and independently re-checked against the
-- exact text it was derived from, same rationale as llm_evidence_text.
--
-- Deliberately a separate column from llm_evidence_text: that column's
-- non-null state is the "LLM extraction attempted" marker
-- (db.fetch_use_cases_needing_llm_extraction), and populating it here
-- would make every HF row look already-extracted.
--
-- model_card_fetched_at is the "attempted" marker for THIS backfill, so a
-- gated (401) or card-less (404) model is not re-fetched on every run.
-- model_card_text NULL with a non-null fetched_at means no card text was
-- obtainable, not "not tried yet".

ALTER TABLE banking_use_cases
    ADD COLUMN IF NOT EXISTS model_card_text TEXT,
    ADD COLUMN IF NOT EXISTS model_card_fetched_at TIMESTAMPTZ;

COMMENT ON COLUMN banking_use_cases.model_card_text IS
    'The Hugging Face model card (README.md) this use case''s classification was derived from, truncated to the first MODEL_CARD_MAX_CHARS (ingestion/sources/huggingface_usecases.py). NULL when the card is gated, absent, or not yet fetched -- see model_card_fetched_at to tell those apart.';
COMMENT ON COLUMN banking_use_cases.model_card_fetched_at IS
    'When ingestion/enrich_hf_model_cards.py last attempted to fetch this row''s model card. NULL means never attempted; non-null with model_card_text NULL means attempted but no text was obtainable (gated or 404).';
