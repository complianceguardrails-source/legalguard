"""
Link every visible use case to the regulations that reach it, from the use
case side, using ingestion/category_regulation_map.py. Writes each use
case's regulation_basis (the working) and rebuilds each regulation's
affected_use_case_ids as

    (links not made by these rules)  UNION  (links these rules make now)

so the run is idempotent and a rule that is removed or narrowed takes its
links away with it, while word-overlap links made at regulation ingestion
(ingestion/tagger.py) are left exactly as they were.

    python link_regulations_by_category.py [--dry-run]

Every selector that resolves to no regulation row is reported: it means
the map names an instrument the corpus doesn't hold, and the answer is to
ingest it, not to quietly link nothing.
"""
from __future__ import annotations

import argparse
import fnmatch
import logging
from collections import Counter, defaultdict

import db
from category_regulation_map import RULES, rules_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("legalguard.link_regulations")


def resolve_selectors(regulations: list[tuple[str, str, list[str]]]) -> tuple[dict[str, list[str]], list[str]]:
    """Rule id -> reg_ids, plus every selector that matched nothing."""
    by_clause: dict[str, list[str]] = defaultdict(list)
    for reg_id, clause, _ in regulations:
        by_clause[clause].append(reg_id)
    resolved: dict[str, list[str]] = {}
    unresolved: list[str] = []
    for rule in RULES:
        ids: list[str] = []
        for selector in rule.clauses:
            if "*" in selector:
                hits = [rid for clause, rids in by_clause.items() if fnmatch.fnmatchcase(clause, selector) for rid in rids]
            else:
                hits = by_clause.get(selector, [])
            if not hits:
                unresolved.append(f"{rule.id}: {selector}")
            ids.extend(hits)
        resolved[rule.id] = sorted(set(ids))
    return resolved, unresolved


def run(dry_run: bool) -> None:
    with db.get_conn() as conn:
        use_cases = db.fetch_visible_use_cases_for_linking(conn)
        regulations = db.fetch_regulation_ids_by_clause(conn)
        resolved, unresolved = resolve_selectors(regulations)
        for line in unresolved:
            logger.warning("selector matched no regulation -- %s", line)

        # Links these rules made last time, per regulation, so they can be
        # withdrawn before being remade.
        previously_ruled: dict[str, set[str]] = defaultdict(set)
        for uc in use_cases:
            for entry in uc.get("regulation_basis") or []:
                for reg_id in entry.get("reg_ids", []):
                    previously_ruled[reg_id].add(str(uc["id"]))

        now_ruled: dict[str, set[str]] = defaultdict(set)
        per_rule: Counter[str] = Counter()
        links_per_use_case: list[int] = []
        for uc in use_cases:
            basis = []
            for rule in rules_for(uc):
                reg_ids = resolved[rule.id]
                if not reg_ids:
                    continue
                per_rule[rule.id] += 1
                basis.append({"rule": rule.id, "kind": rule.kind, "why": rule.why, "reg_ids": reg_ids})
                for reg_id in reg_ids:
                    now_ruled[reg_id].add(str(uc["id"]))
            links_per_use_case.append(len({r for b in basis for r in b["reg_ids"]}))
            if not dry_run:
                db.set_regulation_basis(conn, uc["id"], basis)

        changed = 0
        for reg_id, _, stored in regulations:
            keyword_links = set(stored) - previously_ruled.get(reg_id, set())
            new_links = sorted(keyword_links | now_ruled.get(reg_id, set()))
            if new_links != sorted(stored):
                changed += 1
                if not dry_run:
                    db.set_affected_use_cases(conn, reg_id, new_links)
                    conn.commit()

    with_any = sum(1 for n in links_per_use_case if n)
    logger.info("%d visible use case(s); %d now have at least one regulation (was measured at 68 before rules)", len(use_cases), with_any)
    logger.info("links per use case: min %d, median %d, max %d",
                min(links_per_use_case), sorted(links_per_use_case)[len(links_per_use_case) // 2], max(links_per_use_case))
    logger.info("use cases per rule: %s", dict(per_rule.most_common()))
    logger.info("%d regulation row(s) %s", changed, "would change" if dry_run else "updated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args().dry_run)
