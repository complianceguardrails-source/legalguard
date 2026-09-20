"""
Database access layer for the LegalGuard ingestion engine.

Connects to whatever Postgres instance DATABASE_URL points at (Neon.tech
free tier, Supabase free tier, or local Postgres for development). No ORM --
just psycopg3 with explicit SQL, since the schema is small and stable.
"""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Point it at your free Neon/Supabase "
            "Postgres instance, e.g. postgres://user:pass@host/dbname?sslmode=require"
        )
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def is_unchanged(conn: psycopg.Connection, cache_key: str, content_hash: str) -> bool:
    """Returns True if this document's content hash matches what we saw last time."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content_sha256 FROM ingestion_cache WHERE cache_key = %s", (cache_key,)
        )
        row = cur.fetchone()
        return row is not None and row[0] == content_hash


def upsert_cache(conn: psycopg.Connection, cache_key: str, content_hash: str, status: str = "active") -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion_cache (cache_key, content_sha256, last_checked_at, status)
            VALUES (%s, %s, now(), %s)
            ON CONFLICT (cache_key) DO UPDATE
                SET content_sha256 = EXCLUDED.content_sha256,
                    last_checked_at = now(),
                    status = EXCLUDED.status
            """,
            (cache_key, content_hash, status),
        )


def upsert_regulation(
    conn: psycopg.Connection,
    *,
    jurisdiction: str,
    issuing_body: str,
    clause_identifier: str,
    official_title: str,
    source_url: str,
    statutory_text: str,
    version_label: str,
    publication_date: Optional[str],
    effective_date: Optional[str],
    risk_level: Optional[str],
    ingestion_source: str,
    origin_driver_category: Optional[str] = None,
    origin_driver_description: Optional[str] = None,
    title: Optional[str] = None,
    impact_level: Optional[str] = None,
    remediation_blueprint: Optional[str] = None,
    supersession_note: Optional[str] = None,
) -> str:
    """Inserts (or updates, if the same version_label reappears with new text)
    a single, un-merged regulation row. Returns the reg_id."""
    content_hash = sha256_of(statutory_text)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO specific_regulations
                (jurisdiction, issuing_body, clause_identifier, official_title, source_url,
                 statutory_text, version_label, publication_date, effective_date, risk_level,
                 origin_driver_category, origin_driver_description, content_sha256, ingestion_source,
                 title, impact_level, remediation_blueprint, supersession_note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (jurisdiction, issuing_body, clause_identifier, version_label)
            DO UPDATE SET
                official_title = EXCLUDED.official_title,
                source_url = EXCLUDED.source_url,
                statutory_text = EXCLUDED.statutory_text,
                content_sha256 = EXCLUDED.content_sha256,
                -- Only overwrite fields this upsert actually computed a value
                -- for; a manual/curated correction (e.g. a human-authored
                -- remediation_blueprint) shouldn't be clobbered back to NULL
                -- by a later automated re-ingest that doesn't set it.
                origin_driver_category = COALESCE(EXCLUDED.origin_driver_category, specific_regulations.origin_driver_category),
                origin_driver_description = COALESCE(EXCLUDED.origin_driver_description, specific_regulations.origin_driver_description),
                title = COALESCE(EXCLUDED.title, specific_regulations.title),
                impact_level = COALESCE(EXCLUDED.impact_level, specific_regulations.impact_level),
                remediation_blueprint = COALESCE(EXCLUDED.remediation_blueprint, specific_regulations.remediation_blueprint),
                supersession_note = COALESCE(EXCLUDED.supersession_note, specific_regulations.supersession_note)
            RETURNING reg_id
            """,
            (
                jurisdiction, issuing_body, clause_identifier, official_title, source_url,
                statutory_text, version_label, publication_date, effective_date, risk_level,
                origin_driver_category, origin_driver_description, content_hash, ingestion_source,
                title, impact_level, remediation_blueprint, supersession_note,
            ),
        )
        return str(cur.fetchone()[0])


def set_affected_use_cases(conn: psycopg.Connection, reg_id: str, use_case_ids: list[str]) -> None:
    """Overwrites specific_regulations.affected_use_case_ids for one regulation
    with the tagger's current candidate blast-radius matches."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE specific_regulations SET affected_use_case_ids = %s WHERE reg_id = %s",
            (use_case_ids, reg_id),
        )


def delete_regulations_by_source(conn: psycopg.Connection, ingestion_source: str) -> int:
    """Removes every regulation row from a given ingestion_source -- used to
    purge a source that turned out to be low-quality (e.g. a news RSS feed
    that was never going to produce clean regulation entries)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM specific_regulations WHERE ingestion_source = %s", (ingestion_source,))
        return cur.rowcount


_STATEFUL_MODALITIES = {"voice_agentic", "multi_agent", "rag_document"}
_STATELESS_MODALITIES = {"structured", "vision"}


def derive_data_interception_state(modality: str) -> Optional[str]:
    """Pure derivation from an existing, already-classified modality value --
    no external lookup needed. voice_agentic/multi_agent/rag_document are
    inherently multi-turn interactions; structured/vision are inherently
    single-shot input->output tasks. Returns None for any modality value
    outside the known five (never guessed)."""
    if modality in _STATEFUL_MODALITIES:
        return "stateful-trace"
    if modality in _STATELESS_MODALITIES:
        return "stateless-payload"
    return None


def upsert_mined_use_case(
    conn: psycopg.Connection,
    *,
    name: str,
    parent_sector: str,
    modality: str,
    description: Optional[str],
    github_reference_url: Optional[str] = None,
    risk_tier: Optional[str] = None,
    hf_model_id: Optional[str] = None,
    model_modality: Optional[str] = None,
) -> Optional[str]:
    """Inserts a mined use case, from either GitHub (github_reference_url
    set, source='github_mined' -- the original/default behavior) or
    Hugging Face (hf_model_id set, source='huggingface_mined',
    model_modality carrying the real pipeline_tag-derived classification).
    Skips silently (returns None) if it collides with an existing row on
    the name/github_reference_url/hf_model_id unique constraints -- ON
    CONFLICT DO NOTHING with no target applies to any unique/exclusion
    violation, which is what we want here since a curated seed row and a
    mined row can legitimately describe the same use case under a
    different name. risk_tier defaults to None so the column's own
    'unclassified' default applies when a caller doesn't run the
    risk-tier classifier. data_interception_state is always derived here
    from modality, regardless of which mining source calls this -- a
    single source of truth rather than duplicating the mapping in every
    source module."""
    source = "huggingface_mined" if hf_model_id else "github_mined"
    data_interception_state = derive_data_interception_state(modality)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO banking_use_cases
                (name, parent_sector, modality, description, github_reference_url,
                 risk_tier, source, hf_model_id, model_modality, data_interception_state)
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s, 'unclassified'), %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (name, parent_sector, modality, description, github_reference_url,
             risk_tier, source, hf_model_id, model_modality, data_interception_state),
        )
        row = cur.fetchone()
        return str(row[0]) if row else None


def fetch_use_cases(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, parent_sector, modality, description FROM banking_use_cases")
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            # This connection's driver config returns some TEXT columns as
            # bytes rather than str -- decode defensively either way.
            for key in ("name", "parent_sector", "modality", "description"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def fetch_use_cases_missing_architecture_signal(conn: psycopg.Connection) -> list[dict]:
    """Use cases with a linked repo but no architecture_signal backfilled
    yet -- see ingestion/enrich_architecture.py."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, github_reference_url
            FROM banking_use_cases
            WHERE github_reference_url IS NOT NULL
              AND architecture_signal IS NULL
            ORDER BY name
            """
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            # This connection's driver config returns some TEXT columns as
            # bytes rather than str -- decode defensively either way.
            for key in ("name", "github_reference_url"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def set_architecture_signal(conn: psycopg.Connection, use_case_id: str, architecture_signal: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET architecture_signal = %s WHERE id = %s",
            (architecture_signal, use_case_id),
        )


def set_model_modality(conn: psycopg.Connection, use_case_id: str, model_modality: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET model_modality = %s WHERE id = %s",
            (model_modality, use_case_id),
        )


def set_system_interface_type(conn: psycopg.Connection, use_case_id: str, system_interface_type: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET system_interface_type = %s WHERE id = %s",
            (system_interface_type, use_case_id),
        )


def set_agent_operational_tools(conn: psycopg.Connection, use_case_id: str, tools: list[str]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET agent_operational_tools = %s WHERE id = %s",
            (tools, use_case_id),
        )


def fetch_use_cases_missing_system_signals(conn: psycopg.Connection) -> list[dict]:
    """GitHub-sourced use cases with no system_interface_type/
    agent_operational_tools backfilled yet -- see
    ingestion/enrich_system_signals.py. Only one of the two needs to be
    missing to qualify, since a repo might legitimately have real evidence
    for one dimension but not the other (e.g. a manifest naming fastapi
    but no recognized DB/execution-tool dependency)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, github_reference_url
            FROM banking_use_cases
            WHERE github_reference_url IS NOT NULL
              AND (system_interface_type IS NULL OR agent_operational_tools IS NULL)
            ORDER BY name
            """
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("name", "github_reference_url"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def fetch_uncategorized_use_cases(conn: psycopg.Connection) -> list[dict]:
    """Use cases still sitting at the classifier's 'Uncategorized' fallback --
    candidates for ingestion/reclassify_use_cases.py to re-run through an
    updated usecase_classifier.py without touching already-classified rows."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, description FROM banking_use_cases WHERE parent_sector = 'Uncategorized'"
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("name", "description"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def update_use_case_classification(conn: psycopg.Connection, use_case_id: str, parent_sector: str, modality: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET parent_sector = %s, modality = %s WHERE id = %s",
            (parent_sector, modality, use_case_id),
        )


def fetch_unclassified_risk_tier_use_cases(conn: psycopg.Connection) -> list[dict]:
    """Use cases still sitting at the risk_tier schema default -- candidates
    for ingestion/reclassify_risk_tier.py to re-run through an updated
    risk_tier_classifier.py without touching rows that already have a real
    tier, whether hand-curated or previously classified successfully."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, description FROM banking_use_cases WHERE risk_tier = 'unclassified'"
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("name", "description"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def update_risk_tier(conn: psycopg.Connection, use_case_id: str, risk_tier: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET risk_tier = %s WHERE id = %s",
            (risk_tier, use_case_id),
        )


def fetch_use_cases_with_awesome_list_provenance(conn: psycopg.Connection) -> list[dict]:
    """Every use case whose description carries the "(curated in owner/repo's
    awesome-list)" provenance suffix -- regardless of its current
    parent_sector/risk_tier, unlike fetch_uncategorized_use_cases /
    fetch_unclassified_risk_tier_use_cases, which only look at rows still at
    the fallback default. Needed because this suffix's owner/repo name can
    spuriously match a real keyword (e.g. "trading" in
    "awesome-systematic-trading", "backtest" in "paperswithbacktest"),
    producing a wrong but non-default label that those two fetchers would
    never revisit -- see ingestion/fix_awesome_list_contamination.py."""
    with conn.cursor() as cur:
        cur.execute(
            r"SELECT id, name, description, parent_sector, risk_tier FROM banking_use_cases "
            r"WHERE description ~ '\(curated in [^)]+''s awesome-list\)$'"
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("name", "description", "parent_sector", "risk_tier"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def fetch_all_mined_use_cases(conn: psycopg.Connection) -> list[dict]:
    """Every use case from an automated source (github_mined /
    huggingface_mined), regardless of its current parent_sector/risk_tier --
    unlike the fallback-only fetchers, and broader than
    fetch_use_cases_with_awesome_list_provenance (which only covers one known
    contamination pattern). A validation pass found that classifier fixes
    don't retroactively help rows that already hold a plausible-but-stale
    non-default label from before the fix -- those rows are invisible to
    every fetcher that only looks at the schema default. Deliberately
    excludes 'curated' and 'user_submitted' rows: those are human-authored
    labels, not something a heuristic classifier should ever overwrite. See
    ingestion/reclassify_all_mined.py."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, description, parent_sector, modality, risk_tier FROM banking_use_cases "
            "WHERE source IN ('github_mined', 'huggingface_mined')"
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("name", "description", "parent_sector", "modality", "risk_tier"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def fetch_regulations_for_trend_analysis(conn: psycopg.Connection) -> list[dict]:
    """Every regulation with enough data to feed a real trend signal (see
    ingestion/generate_horizon_forecasts.py) -- needs both a publication
    date and a classified origin_driver_category to be groupable by
    jurisdiction/category/quarter the same way origin_driver_trend_summary
    aggregates them."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT reg_id, jurisdiction, origin_driver_category, publication_date,
                   COALESCE(title, official_title) AS display_title, affected_use_case_ids
            FROM specific_regulations
            WHERE publication_date IS NOT NULL
              AND origin_driver_category IS NOT NULL
            """
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("jurisdiction", "origin_driver_category", "display_title"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def upsert_trend_forecast(
    conn: psycopg.Connection,
    *,
    trend_key: str,
    target_jurisdiction: str,
    projected_bill_name: str,
    estimated_arrival_window: str,
    probability_percentage: int,
    upstream_catalyst_drivers: list[str],
    underlying_driver_description: str,
    impact_blast_radius_summary: str,
    affected_use_case_ids: list[str],
) -> None:
    """Upserts one real, trend-derived horizon forecast row, keyed on
    trend_key so re-running the generator updates the same row as the
    underlying regulation data changes rather than duplicating it."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO regulatory_horizon_forecast
                (trend_key, target_jurisdiction, projected_bill_name, estimated_arrival_window,
                 probability_percentage, upstream_catalyst_drivers, underlying_driver_description,
                 impact_blast_radius_summary, affected_use_case_ids)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trend_key) DO UPDATE SET
                projected_bill_name = EXCLUDED.projected_bill_name,
                estimated_arrival_window = EXCLUDED.estimated_arrival_window,
                probability_percentage = EXCLUDED.probability_percentage,
                upstream_catalyst_drivers = EXCLUDED.upstream_catalyst_drivers,
                underlying_driver_description = EXCLUDED.underlying_driver_description,
                impact_blast_radius_summary = EXCLUDED.impact_blast_radius_summary,
                affected_use_case_ids = EXCLUDED.affected_use_case_ids,
                updated_at = now()
            """,
            (
                trend_key, target_jurisdiction, projected_bill_name, estimated_arrival_window,
                probability_percentage, upstream_catalyst_drivers, underlying_driver_description,
                impact_blast_radius_summary, affected_use_case_ids,
            ),
        )


def delete_stale_trend_forecasts(conn: psycopg.Connection, current_trend_keys: list[str]) -> int:
    """Removes previously-generated trend forecasts whose signal no longer
    holds (e.g. a jurisdiction/category pair that was accelerating last run
    but isn't anymore) -- only ever touches trend_key-tagged rows, never the
    hand-authored seed ones."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM regulatory_horizon_forecast WHERE trend_key IS NOT NULL AND NOT (trend_key = ANY(%s))",
            (current_trend_keys,),
        )
        return cur.rowcount


def link_regulation_to_guardrail(
    conn: psycopg.Connection, reg_id: str, guardrail_id: str, impact_tier: str, mandate_summary: str
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO guardrail_regulatory_mapping (reg_id, guardrail_id, impact_tier, mandate_summary)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (reg_id, guardrail_id) DO NOTHING
            """,
            (reg_id, guardrail_id, impact_tier, mandate_summary),
        )


def fetch_regulations_for_tagging_audit(conn: psycopg.Connection) -> list[dict]:
    """Every regulation's real statutory_text plus its currently-stored
    affected_use_case_ids -- used by audit_tagging.py to re-derive matches
    fresh and diff against what's actually stored, catching keyword-overlap
    drift (false positives/negatives) automatically instead of by chance."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT reg_id, official_title, statutory_text, affected_use_case_ids FROM specific_regulations"
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("official_title", "statutory_text"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def register_admin_reference_guardrail(
    conn: psycopg.Connection,
    *,
    use_case_name: str,
    github_owner: str,
    github_repo_url: str,
    name: Optional[str] = None,
    policy_framework: str = "open_policy_agent",
    current_semver: str = "v1.0.0",
    status: str = "merged",
    compliance_status: str = "compliant",
) -> Optional[str]:
    """Registers (or updates) the admin's own hand-built reference guardrail
    repo for a given use case, by exact name lookup against
    banking_use_cases. Upserts on the partial unique index (use_case_id
    WHERE is_admin_reference = true) so re-running this for the same use
    case updates the existing registration rather than creating a competing
    one. compiled_code_payload is stored empty -- the real code lives in the
    real GitHub repo, the DB row is just a pointer into it, not a mirror.
    Returns the resolved use_case_id, or None if use_case_name matched
    nothing (the caller logs this, rather than silently skipping it)."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM banking_use_cases WHERE name = %s", (use_case_name,))
        row = cur.fetchone()
        if row is None:
            return None
        use_case_id = row[0]
        cur.execute(
            """
            INSERT INTO guardrail_packages
                (use_case_id, name, github_owner, github_repo_url, policy_framework,
                 current_semver, compiled_code_payload, status, compliance_status,
                 is_admin_reference)
            VALUES (%s, %s, %s, %s, %s, %s, '', %s, %s, true)
            ON CONFLICT (use_case_id) WHERE is_admin_reference = true
            DO UPDATE SET
                name = EXCLUDED.name,
                github_owner = EXCLUDED.github_owner,
                github_repo_url = EXCLUDED.github_repo_url,
                policy_framework = EXCLUDED.policy_framework,
                current_semver = EXCLUDED.current_semver,
                status = EXCLUDED.status,
                compliance_status = EXCLUDED.compliance_status,
                updated_at = now()
            """,
            (
                use_case_id, name or f"guardrail-{use_case_name}", github_owner, github_repo_url,
                policy_framework, current_semver, status, compliance_status,
            ),
        )
        return str(use_case_id)


def fetch_use_cases_needing_llm_extraction(conn: psycopg.Connection, limit: int = 25) -> list[dict]:
    """GitHub-mined use cases with a real repo URL that haven't had
    ingestion/llm_compiler.py's extraction attempted yet (llm_evidence_text
    IS NULL is the "attempted" marker, set regardless of whether a
    requirement was actually found -- see store_llm_extraction). Scoped to
    github_mined only: llm_compiler.py fetches a GitHub README, and this
    fetcher has no equivalent evidence source for HF-mined/curated rows yet."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, github_reference_url FROM banking_use_cases "
            "WHERE source = 'github_mined' AND github_reference_url IS NOT NULL "
            "AND llm_evidence_text IS NULL "
            "ORDER BY random() LIMIT %s",
            (limit,),
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("name", "github_reference_url"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def store_llm_extraction(conn: psycopg.Connection, use_case_id: str, extraction: Optional[dict], evidence_text: str) -> None:
    """Records the outcome of an extraction attempt. evidence_text is
    always stored (even when extraction is None) so llm_evidence_text IS
    NULL reliably means "not yet attempted", never "attempted and found
    nothing" -- those two states must stay distinguishable so this
    function's own caller (fetch_use_cases_needing_llm_extraction) never
    re-attempts a use case for free every run."""
    import json as _json

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET llm_compiled_requirement = %s, llm_evidence_text = %s WHERE id = %s",
            (_json.dumps(extraction) if extraction else None, evidence_text, use_case_id),
        )


def fetch_hf_use_cases_needing_model_card(conn: psycopg.Connection, limit: Optional[int] = None) -> list[dict]:
    """HF-mined use cases whose model card has never been fetched.
    model_card_fetched_at IS NULL is the "attempted" marker -- set on every
    attempt regardless of outcome (see set_hf_model_card_enrichment), so a
    gated or card-less model is recorded once rather than retried on every
    run. Returns the current classification alongside, so the runner can
    report what actually changed."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, hf_model_id, description, parent_sector, modality, risk_tier, model_modality "
            "FROM banking_use_cases "
            "WHERE source = 'huggingface_mined' AND hf_model_id IS NOT NULL "
            "AND model_card_fetched_at IS NULL "
            "ORDER BY id" + (" LIMIT %s" if limit else ""),
            (limit,) if limit else (),
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("name", "hf_model_id", "description", "parent_sector", "modality", "risk_tier", "model_modality"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def set_hf_model_card_enrichment(
    conn: psycopg.Connection,
    use_case_id: str,
    *,
    card_text: Optional[str],
    description: Optional[str],
    parent_sector: str,
    modality: str,
    risk_tier: str,
    model_modality: Optional[str],
) -> None:
    """Writes the fetched card (or NULL) and every field re-derived from
    it in one statement, and stamps model_card_fetched_at either way so the
    attempt is never repeated. description None keeps the existing value --
    the caller passes None when no card prose was available to replace the
    mining-time placeholder with. data_interception_state is re-derived
    here from the new modality, as upsert_mined_use_case derives it at
    insert: a modality that changes on re-classification must carry its
    derived column with it, or the two silently disagree."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET "
            "model_card_text = %s, model_card_fetched_at = now(), "
            "description = COALESCE(%s, description), "
            "parent_sector = %s, modality = %s, risk_tier = %s, model_modality = %s, "
            "data_interception_state = %s, updated_at = now() "
            "WHERE id = %s",
            (card_text, description, parent_sector, modality, risk_tier, model_modality,
             derive_data_interception_state(modality), use_case_id),
        )


def fetch_use_cases_for_categorisation(conn: psycopg.Connection) -> list[dict]:
    """Every use case with the evidence the category tagger reads: name,
    description, and whichever real prose the row has -- its model card
    (HF-mined) or README (GitHub-mined, from the LLM extraction step). All
    sources, including curated: categories describe what a system does,
    and a hand-entered row does that as much as a mined one."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, description, source, categories, model_card_text, llm_evidence_text "
            "FROM banking_use_cases ORDER BY name"
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("name", "description", "model_card_text", "llm_evidence_text"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def set_use_case_categories(conn: psycopg.Connection, use_case_id: str, categories: list[str]) -> None:
    """Empty list is stored as NULL, which is what the app filters on."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET categories = %s, updated_at = now() WHERE id = %s",
            (categories or None, use_case_id),
        )


def fetch_use_cases_for_risk_basis(conn: psycopg.Connection) -> list[dict]:
    """Every use case with a risk tier, plus the text the tier was (or
    could have been) derived from. Repo topics / Hub tags were never
    stored, so the backfill can only reproduce tiers the stored text
    supports on its own."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, description, source, risk_tier, risk_basis, model_card_text "
            "FROM banking_use_cases WHERE risk_tier <> 'unclassified' ORDER BY name"
        )
        cols = [d.name for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("name", "description", "model_card_text"):
                if isinstance(record.get(key), (bytes, bytearray)):
                    record[key] = record[key].decode("utf-8")
            rows.append(record)
        return rows


def set_risk_basis(conn: psycopg.Connection, use_case_id: str, basis: dict | None) -> None:
    """Writes the risk tier's working (see migrations/009). None clears it."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET risk_basis = %s, updated_at = now() WHERE id = %s",
            (json.dumps(basis) if basis is not None else None, use_case_id),
        )
    conn.commit()


def fetch_visible_use_cases_for_linking(conn: psycopg.Connection) -> list[dict]:
    """The use cases the app shows (categorised, or curated), with what the
    category-regulation rules read: categories, risk_basis, source, and
    the previous regulation_basis so a re-run can undo its own links."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, description, source, categories, risk_tier, risk_basis, regulation_basis, model_modality "
            "FROM banking_use_cases WHERE categories IS NOT NULL OR source = 'curated' ORDER BY name"
        )
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_regulation_ids_by_clause(conn: psycopg.Connection) -> list[tuple[str, str, list[str]]]:
    """(reg_id, clause_identifier, affected_use_case_ids) for every regulation."""
    with conn.cursor() as cur:
        cur.execute("SELECT reg_id, clause_identifier, COALESCE(affected_use_case_ids, '{}') FROM specific_regulations")
        return [(str(r[0]), r[1], [str(u) for u in r[2]]) for r in cur.fetchall()]


def set_regulation_basis(conn: psycopg.Connection, use_case_id: str, basis: list[dict] | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET regulation_basis = %s, updated_at = now() WHERE id = %s",
            (json.dumps(basis) if basis else None, use_case_id),
        )
    conn.commit()


def fetch_unclassified_categorised_use_cases(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, categories, description, source, model_card_text FROM banking_use_cases "
            "WHERE risk_tier = 'unclassified' AND categories IS NOT NULL ORDER BY name"
        )
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def fetch_visible_use_cases_for_risk_factors(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, source, categories, modality, model_modality, system_interface_type, risk_tier, risk_basis, risk_factors "
            "FROM banking_use_cases WHERE categories IS NOT NULL OR source = 'curated' ORDER BY name"
        )
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def set_risk_factors(conn: psycopg.Connection, use_case_id: str, factors: list[str]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE banking_use_cases SET risk_factors = %s, updated_at = now() WHERE id = %s",
            (factors or None, use_case_id),
        )
    conn.commit()


def upsert_risk_news_story(conn: psycopg.Connection, story: dict) -> bool:
    """Inserts a story by URL; an existing URL is left as first seen (a
    feed's later edit of a title is not a new story). Returns True if new."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO risk_news_stories (url, title, summary, outlet, outlet_kind, published_at, risk_slugs, families, matched_terms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            """,
            (story["url"], story["title"], story.get("summary"), story["outlet"], story["outlet_kind"],
             story.get("published_at"), story["risk_slugs"], story["families"], story["matched_terms"]),
        )
        inserted = cur.rowcount == 1
    conn.commit()
    return inserted


def upsert_guardrail_repo(conn: psycopg.Connection, row: dict) -> None:
    """One row per platform + id; a re-run refreshes stars, description
    and the risk mapping in place."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO guardrail_repos
                (platform, external_id, url, name, description, stars, downloads, language, license,
                 last_pushed_at, risk_slugs, families, evidence, fetched_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (platform, external_id) DO UPDATE SET
                url = EXCLUDED.url, name = EXCLUDED.name, description = EXCLUDED.description,
                stars = EXCLUDED.stars, downloads = EXCLUDED.downloads, language = EXCLUDED.language,
                license = EXCLUDED.license, last_pushed_at = EXCLUDED.last_pushed_at,
                risk_slugs = EXCLUDED.risk_slugs, families = EXCLUDED.families,
                evidence = EXCLUDED.evidence, fetched_at = now()
            """,
            (row["platform"], row["external_id"], row["url"], row["name"], row.get("description"),
             row.get("stars"), row.get("downloads"), row.get("language"), row.get("license"),
             row.get("last_pushed_at"), row["risk_slugs"], row["families"], json.dumps(row["evidence"])),
        )
    conn.commit()
