"""
Registers the admin's own hand-built reference guardrail repos against the
use cases they cover, so the app can tell an end user "a reference
implementation already exists" at dispatch time instead of only offering to
generate a fresh one (see app/screens/ImpactDiffScreen.js).

This is an admin-only, infrequent, manually-run script -- NOT a PostgREST
write path. Only the project maintainer curates these entries; end users
never write to guardrail_packages (see docs/POSTGREST.md's read-only
web_anon grant, which is intentionally left unchanged by this script).

Run manually after pushing a new reference repo:
    DATABASE_URL=postgres://... python ingestion/register_admin_reference.py
"""
from __future__ import annotations

import logging

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.register_admin_reference")

# Edit this list by hand each time you finish curating a new reference repo.
# use_case_name must exactly match banking_use_cases.name.
ADMIN_REFERENCES = [
    # {
    #     "use_case_name": "Voice Agent: Mortgage Escalation Support",
    #     "github_owner": "complianceguardrails-source",
    #     "github_repo_url": "https://github.com/complianceguardrails-source/guardrail-voice-agentic-customer-support",
    # },
]


def main() -> None:
    if not ADMIN_REFERENCES:
        logger.info("ADMIN_REFERENCES is empty -- nothing to register. Add entries to this file first.")
        return
    with db.get_conn() as conn:
        for entry in ADMIN_REFERENCES:
            use_case_id = db.register_admin_reference_guardrail(conn, **entry)
            if use_case_id is None:
                logger.warning("No use case found matching name=%r -- skipped", entry["use_case_name"])
            else:
                logger.info(
                    "Registered admin reference for use_case_id=%s (%s) -> %s",
                    use_case_id, entry["use_case_name"], entry["github_repo_url"],
                )


if __name__ == "__main__":
    main()
