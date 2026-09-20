# LegalGuard

A free, open-source prototype that tracks global AI/financial regulation,
maps changes to a knowledge base of banking AI use cases, and lets a user
push the resulting guardrail changes to their own GitHub repos with one tap
from their phone -- with zero infrastructure cost.

See `docs/ARCHITECTURE.md` for what's real vs. a documented next step, and
`docs/POSTGREST.md` for the API layer specifically.

## Stack (all free tiers)

- **Database**: Postgres on [Neon.tech](https://neon.tech) or Supabase free tier
- **API**: [PostgREST](https://postgrest.org) (open source, auto-generates REST from the schema)
- **Ingestion**: Python script run nightly by a free GitHub Actions cron job
- **Mobile app**: Expo / React Native
- **Guardrail generation**: a small Node service with a pinned `opa` binary that verifies every package before the app sees it (Render free tier)
- **GitOps**: the phone calls the GitHub REST API directly using a user-supplied Personal Access Token stored in the OS keychain -- no server ever sees it

## Setup

### 1. Database

1. Create a free project at [neon.tech](https://neon.tech) (or supabase.com) and copy its connection string.
2. Run the schema, then the seed data:
   ```bash
   psql "$DATABASE_URL" -f database/schema.sql
   psql "$DATABASE_URL" -f database/seed.sql
   ```

### 2. Ingestion crawler + use-case miner

1. Push this repo to GitHub.
2. Repo Settings → Secrets and variables → Actions → add `DATABASE_URL`.
3. `.github/workflows/ingest.yml` (nightly) pulls regulatory changes;
   `.github/workflows/mine_use_cases.yml` (weekly) discovers new financial
   AI repos on GitHub across the full tier taxonomy and adds them to
   `banking_use_cases`. Trigger either manually from the Actions tab to
   test immediately.
4. To run locally instead:
   ```bash
   cd ingestion
   pip install -r requirements.txt
   DATABASE_URL="postgres://..." python main.py              # regulations
   DATABASE_URL="postgres://..." python mine_use_cases.py    # use cases
   ```

### 3. REST API (PostgREST)

Follow `docs/POSTGREST.md`. For local development:
```bash
brew install postgrest
postgrest postgrest.conf   # see docs/POSTGREST.md for the conf contents
```

### 4. Risk feeds: news and existing guardrails

Two nightly feeds map the outside world onto the risk taxonomy
(`ingestion/risk_taxonomy.py`: seven families, sixty-one granular risks):

```bash
cd ingestion
DATABASE_URL=... python ingest_risk_news.py        # allowlisted outlets + regulators, via RSS
GITHUB_TOKEN=... DATABASE_URL=... python ingest_guardrail_repos.py   # open-source controls per risk
```

Stories come only from the outlets and regulators named in
`sources/risk_news.py` (title + summary from their own feeds, linked out);
a story is kept when it is about AI and matches a risk's phrases in
`risk_news_keywords.py`. Guardrail repositories are the curated seeds and
searches in `guardrail_repo_queries.py`, resolved live against the GitHub
and Hugging Face APIs so stars, licence and last push are real. Risks with
no known technical control are reported, not filled.

### 5. Mobile app

```bash
cd app
npm install
EXPO_PUBLIC_API_URL=http://localhost:3000 npx expo start
```

Without `EXPO_PUBLIC_API_URL` set, the app runs against bundled mock data
(`app/lib/mockData.js`) so you can see every screen before any backend is deployed.

Four tabs: **Discover** (category cloud, swipe deck, use-case detail with
tier, granular risks, regulations and existing guardrails), **Trending**
(today's stories per risk family), **Radar** (counts and pending
regulations), **Horizon** (forecasts).

### 6. Generation service (optional, not used by the app)

`service/` still holds the opa-verified Rego generation service and its
adversarial harness (`npm run harness`); `render.yaml` deploys it as
`legalguard-generator`. The app no longer calls it -- guardrails in the
product are existing open-source controls mapped to risks -- but the
service is kept for anyone who wants generated policy from a use case and
its matched regulations.

### 7. Ship to the App Store

See `docs/APP_STORE_METADATA.md` for listing copy/reviewer notes and
`docs/PRIVACY_POLICY.md` for the privacy policy text (fill in the
bracketed placeholders in both before submitting). `app/eas.json` has
build/submit profiles ready for `eas build --platform ios` and
`eas submit` once you're logged into `eas` and have linked your Apple
Developer account.

## Repo layout

```
database/     Postgres schema + seed data
ingestion/    Regulation crawler (Federal Register, EUR-Lex, legislation.gov.uk,
              RSS) + GitHub/Hub use-case miner, category/risk/regulation
              rules, risk-news and guardrail-repo feeds
.github/      Free nightly (regs) + weekly (use cases) cron workflows
app/          Expo/React Native mobile app
service/      Optional opa-verified guardrail generation service and its
              adversarial harness (not called by the app)
docs/         Architecture notes and PostgREST setup guide
```

## Known limitations (see docs/ARCHITECTURE.md for the full table)

The legal-text → policy-code compiler described in the original design
session is **not implemented** here -- the generation service produces a
deterministic draft template (`service/lib/guardrailTemplate.js`), verified
with `opa` but not a genuine neuro-symbolic translation.
Every guardrail this app proposes should be treated as a draft for human
review, not an auto-mergeable patch, until that compiler exists.
