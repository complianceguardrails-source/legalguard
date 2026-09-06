"""
Anti-hallucination guard for the regulation<->use-case tagging pipeline.

Neither this tagging step nor guardrail template generation (see
guardrailTemplate.js's assertRegulationProvenance) calls an LLM today --
tag_regulation() in tagger.py is a deterministic keyword/phrase-overlap
matcher. So the real risk here isn't generative hallucination, it's
keyword-match precision drift: a regulation's affected_use_case_ids can go
stale or wrong relative to what a fresh run of the same tagger would
produce, silently, with no error anywhere. This already happened twice in
this project: a stray "trading" substring in a provenance suffix
misclassified generic library repos as CIB use cases, and a batch of
NAIC-model state regulations initially matched zero use cases because
their administrative legal language shares no keywords with any use case
description.

This script is the automated version of the manual review that caught both
of those bugs: it re-runs tag_regulation() fresh against every regulation's
real statutory_text and diffs the result against what's currently stored,
logging any mismatch for a human to look at. Read-only -- it never writes
back a "correction" on its own, since a keyword-tagger disagreeing with the
stored value isn't proof the stored value is wrong (some matches came from
a human override, a different tagger version, or manual seeding).

Run manually, or as a non-blocking step after ingest.yml's nightly run:
    DATABASE_URL=postgres://... python ingestion/audit_tagging.py
"""
from __future__ import annotations

import logging

import db
from tagger import tag_regulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.audit_tagging")


def main() -> None:
    with db.get_conn() as conn:
        use_cases = db.fetch_use_cases(conn)
        regulations = db.fetch_regulations_for_tagging_audit(conn)

        mismatch_count = 0
        for reg in regulations:
            # affected_use_case_ids is UUID[] -- psycopg returns native UUID
            # objects, while tag_regulation() returns str(uc["id"]). Compare
            # as strings on both sides or every stored id spuriously looks
            # "missing" (a type mismatch, not a real tagging disagreement).
            stored_ids = {str(u) for u in (reg["affected_use_case_ids"] or [])}
            fresh_matches = tag_regulation(reg["statutory_text"], use_cases)
            fresh_ids = {m.use_case_id for m in fresh_matches}

            added = fresh_ids - stored_ids
            missing = stored_ids - fresh_ids
            if not added and not missing:
                continue

            mismatch_count += 1
            label = reg["official_title"] or reg["reg_id"]
            if added:
                names = [m.use_case_name for m in fresh_matches if m.use_case_id in added]
                logger.warning("%s: fresh tagger found %d new match(es) not in affected_use_case_ids: %s", label, len(added), ", ".join(names))
            if missing:
                logger.warning("%s: %d stored use-case tag(s) no longer match the fresh tagger: %s", label, len(missing), ", ".join(sorted(missing)))

        logger.info(
            "Audit complete: %d/%d regulation(s) had a tagging mismatch -- review the warnings above, this script does not auto-correct.",
            mismatch_count, len(regulations),
        )


if __name__ == "__main__":
    main()
