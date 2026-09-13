-- Real, general-purpose LLM extraction (ingestion/llm_compiler.py): reads
-- a use case's actual GitHub README and asks an LLM whether it implies a
-- concrete, specific compliance-relevant guardrail obligation, grounded in
-- a verbatim quote from that real text. Only a *validated* extraction
-- (llm_compiler.py::validate_extraction -- the quote must be a real
-- substring of the evidence text, not a paraphrase) is ever written here.
-- NULL means either no requirement was found, or one was found but failed
-- validation (a rejected/likely-hallucinated extraction is never stored) --
-- both are indistinguishable from "not yet attempted" at the DB level by
-- design, matching this table's existing null-means-no-evidence convention
-- (see migration 005's comment).

ALTER TABLE banking_use_cases
    ADD COLUMN IF NOT EXISTS llm_compiled_requirement JSONB,
    ADD COLUMN IF NOT EXISTS llm_evidence_text TEXT;

COMMENT ON COLUMN banking_use_cases.llm_compiled_requirement IS
    'Validated LLM extraction {requirement_id, action_type, approval_flag, evidence_quote, rationale} from this use case''s real README (ingestion/llm_compiler.py). NULL if no concrete obligation was found, or if one was extracted but failed grounding validation (evidence_quote not a verbatim substring of llm_evidence_text) -- never a guessed/unvalidated value.';
COMMENT ON COLUMN banking_use_cases.llm_evidence_text IS
    'The real evidence text (GitHub README) the extraction above was derived from, stored alongside it so evidence_quote can always be independently re-verified against the exact text the LLM actually saw.';
