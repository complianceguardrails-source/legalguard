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

### 4. Guardrail generation service

Generates each use case's guardrail package and verifies it with the real
`opa` binary before returning it -- `opa check --strict` plus the package's
own generated test suite. The app never receives a policy that fails its
own tests, and a rule change ships without an App Store release. Holds no
credentials; the GitHub push still happens from the app.

```bash
cd service
npm install
PORT=8787 node server.js        # needs `opa` on PATH
curl localhost:8787/healthz     # {"ok":true,"opa_version":"1.20.2"}
```

`service/Dockerfile` bakes in a pinned, checksum-verified `opa`; `render.yaml`
deploys it as `legalguard-generator`. The adversarial harness also lives here:
`npm run harness`.

### 5. Mobile app

```bash
cd app
npm install
EXPO_PUBLIC_API_URL=http://localhost:3000 \
EXPO_PUBLIC_GENERATOR_URL=http://localhost:8787 npx expo start
```

Without `EXPO_PUBLIC_API_URL` set, the app runs against bundled mock data
(`app/lib/mockData.js`) so you can see every screen before any backend is deployed.
`EXPO_PUBLIC_GENERATOR_URL` has no mock fallback on purpose: an unverified
policy is the one thing the service exists to prevent, so without it the
Audit screen says so and dispatch stays disabled.

### 6. Connect GitHub in the app

Open the **Dispatch** tab → paste a **classic** [Personal Access Token](https://github.com/settings/tokens/new?scopes=repo,workflow)
with both `repo` **and** `workflow` scope → set a target repo for whichever
use cases you want guardrail PRs opened against. Both scopes are required:
`repo` alone can create the repo and branch, but every generated guardrail
includes `.github/workflows/compliance_eval.yml`, and GitHub silently
404s any tree/commit write touching `.github/workflows/` without the
separate `workflow` scope -- confirmed by direct API testing, since the
failure mode gives no indication it's scope-related. Use classic, not
fine-grained: fine-grained tokens return `403 Resource not accessible by
personal access token` on repo creation unless you separately grant
"Administration" under Account permissions, which is easy to miss. The
token is written to the device's
secure keychain (`expo-secure-store`) and is never sent to the
Postgres/PostgREST backend.

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
ingestion/    Regulation crawler (Federal Register API + RSS) + GitHub
              use-case miner, dedup, origin-driver & blast-radius taggers
.github/      Free nightly (regs) + weekly (use cases) cron workflows
app/          Expo/React Native mobile app
service/      Guardrail generation + opa verification service, and the
              adversarial harness against its generated policies
docs/         Architecture notes and PostgREST setup guide
```

## Known limitations (see docs/ARCHITECTURE.md for the full table)

The legal-text → policy-code compiler described in the original design
session is **not implemented** here -- the generation service produces a
deterministic draft template (`service/lib/guardrailTemplate.js`), verified
with `opa` but not a genuine neuro-symbolic translation.
Every guardrail this app proposes should be treated as a draft for human
review, not an auto-mergeable patch, until that compiler exists.
