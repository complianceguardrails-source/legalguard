# LegalGuard architecture (as implemented in this repo)

This documents what's actually built here versus what's a documented
extension point for later, so you can tell the difference at a glance.

## Data flow

```
Federal Register API + RSS feeds        GitHub Search API
(ingestion/main.py, nightly)             (ingestion/mine_use_cases.py, weekly)
        |                                        |
        v                                        v
              Postgres  (database/schema.sql, seed.sql)
                             |
                             v
              PostgREST  (docs/POSTGREST.md -- free auto-REST layer)
                             |
                             v
              Expo app on the user's phone  (app/)
               |  read: fetch* in lib/api.js         ^
               |  write: submitUseCase() for          |  matchRegulationsForUseCase()
               |  self-submitted use cases             |  (lib/tagger.js, runs client-side,
               v                                        |   no server round-trip)
   GitHub REST API, called directly from the phone
   (app/lib/githubClient.js, using a PAT stored in
   the OS keychain via app/lib/auth.js)
```

No component in this chain costs money to run at prototype scale, and no
custom backend server holds a user's GitHub credentials.

## What's real vs. a documented stub

| Component | Status |
|---|---|
| Postgres schema (many-to-many reg↔guardrail mapping) | Real, runnable DDL |
| Federal Register ingestion | Real API integration (federalregister.gov, no key needed) |
| RSS ingestion | Real, but feed URLs need verifying against live regulator sites |
| Dedup cache | Real (`ingestion_cache` table, sha256 content hash) |
| Blast-radius tagger | Real keyword/Jaccard matcher; `tag_regulation_llm()` is a documented stub for a future semantic upgrade |
| Neuro-symbolic Rego compiler (E, C from the design doc) | **Not implemented.** `draftRegoStub()` in `ImpactDiffScreen.js` is a deterministic template, not a legal-text-to-code compiler. Treat every generated policy as a draft a human must review before merging. |
| GitHub GitOps client | Real, working REST calls (branch, commit, PR, create-repo). New-repo initialization uses the Git Data API (blobs/tree/commit) so all ~8 template files land in one atomic commit, not a partial multi-step push |
| Guardrail repo naming (`guardrailNaming.js`) | Real, deterministic `guardrail-{sector}-{usecase}` slug, so the same use case always maps to the same repo name |
| Guardrail repo template (`guardrailTemplate.js`) | Real, runnable file set: `policies/rules.rego` + `rules_test.rego` (passes `opa test`), `middleware/safety_hook.py` (shells out to `opa eval`), `metadata.json`, `REGULATORY_PROVENANCE.md`, `.github/workflows/compliance_eval.yml`. Policy logic itself is still a conservative default-deny stub -- see the compiler row below |
| Mobile UI (5 screens) | Real, functional against either PostgREST or bundled mock data |
| Horizon predictive forecasts | Data model + UI are real; the forecasts themselves are seeded/manual, not machine-generated predictions. `origin_driver_trend_summary` (a real SQL view) now gives them *some* empirical backing -- see below |
| Multi-tenant auth / enterprise RLS | Intentionally **not** built -- this is the single-user, open-source prototype path from your design discussion, not the enterprise SaaS variant |
| GitHub use-case miner (`sources/github_usecases.py`) | Real GitHub Search API integration across 15 finance-AI query strings spanning the full tier taxonomy. Sector/modality classification (`usecase_classifier.py`) is keyword-heuristic, same caveat as the regulation tagger -- expect misclassifications, not a verified taxonomy |
| Origin-driver labeling (`classify_origin_driver()`) | Real, but explicitly coarse keyword heuristic across 4 categories (market_scandal / capability_leap / geopolitical_sovereignty / standards_harmonization). Treat as a hypothesis for a human to confirm, not a causal analysis |
| Self-service use-case submission | Real end-to-end: `KnowledgeBaseScreen.js`'s "+" form writes to Postgres via PostgREST (`submitUseCase()`), then immediately runs `matchRegulationsForUseCase()` (client-side JS port of the Python tagger) against loaded regulations so the user sees candidate compliance matches without waiting for a server round-trip |

## Why regulations are never merged

`guardrail_regulatory_mapping` is a many-to-many join table specifically so
that a UK FCA clause and an EU AI Act clause that look similar remain two
distinct rows in `specific_regulations` -- each with its own jurisdiction,
penalty tier, and enforcement date -- while a single guardrail package (say,
`guardrail-voice-agentic-customer-support`) can carry provenance from both.
See `database/schema.sql` section 4 and the worked example in `seed.sql`.

## How origin-driver labels feed the Horizon predictions

Every ingested regulation gets a best-guess `origin_driver_category`
(`ingestion/tagger.py::classify_origin_driver`) explaining *why* it likely
came into being -- a market scandal, a capability leap outrunning old rules,
geopolitical/data-sovereignty pressure, or codification of an existing
standard. `origin_driver_trend_summary` (schema.sql section 8) aggregates
those labels by jurisdiction/category/quarter.

This turns "predict upcoming regulation" from pure hand-authored guessing
into something with a real, if crude, empirical signal: if `capability_leap`
-labeled regulations from the UK have been climbing quarter over quarter,
that's a concrete reason to expect the next one, not just a hunch. The
`regulatory_horizon_forecast` table's `upstream_catalyst_drivers` field is
still manually seeded in this pass -- wiring it to actually read from
`origin_driver_trend_summary` (e.g. flag a jurisdiction/category pair whose
count is accelerating) is the natural next step once there's enough
ingested history for the trend to mean anything.

## Extension points, in priority order

1. **Real compiler**: replace `draftRegoStub()` with an actual LLM-backed
   extraction+compilation pipeline (the `E`/`C` functions from your ICLR
   draft). This is the single highest-leverage next step -- everything else
   in this repo is plumbing built to receive that compiler's output.
2. **`tag_regulation_llm()`**: swap keyword tagging for real semantic
   matching once you're ready to spend on API calls.
3. **Push notifications**: wire Expo push notifications so the "double
   notification" (regulatory change + guardrail versioning event) reaches
   the user without opening the app -- not implemented in this pass.
4. **Compliance certificate export**: the audit-trail PDF feature discussed
   in your design session is not built; `guardrail_regulatory_mapping` has
   the data needed to generate one.
5. **Horizon forecasts reading `origin_driver_trend_summary`**: connect the
   predictive tab to the real trend data instead of manually seeded rows
   (see the section above).
6. **User auth on self-service submission**: `submitUseCase()` currently
   writes through an unauthenticated `web_anon` PostgREST role scoped to
   just that one table/columns (see docs/POSTGREST.md) -- fine for a
   personal instance, not for a public multi-user one.
