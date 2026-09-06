"""
Database access layer for the LegalGuard ingestion engine.

Connects to whatever Postgres instance DATABASE_URL points at (Neon.tech
free tier, Supabase free tier, or local Postgres for development). No ORM --
just psycopg3 with explicit SQL, since the schema is small and stable.
"""
from __future__ import annotations

import hashlib
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


def upsert_mined_use_case(
    conn: psycopg.Connection,
    *,
    name: str,
    parent_sector: str,
    modality: str,
    description: Optional[str],
    github_reference_url: str,
    risk_tier: Optional[str] = None,
) -> Optional[str]:
    """Inserts a GitHub-mined use case. Skips silently (returns None) if it
    collides with an existing row on either the name or github_reference_url
    unique constraints -- ON CONFLICT DO NOTHING with no target applies to
    any unique/exclusion violation, which is what we want here since a
    curated seed row and a mined row can legitimately describe the same
    use case under a different name. risk_tier defaults to None so the
    column's own 'unclassified' default applies when a caller doesn't run
    the risk-tier classifier."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO banking_use_cases
                (name, parent_sector, modality, description, github_reference_url, risk_tier, source)
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s, 'unclassified'), 'github_mined')
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (name, parent_sector, modality, description, github_reference_url, risk_tier),
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
