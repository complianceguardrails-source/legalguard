# Free REST API layer: PostgREST

The mobile app never talks to Postgres directly (phones can't hold a
persistent DB driver connection well, and you'd have to ship DB credentials
inside the app bundle). Instead, [PostgREST](https://postgrest.org) -- a
single open-source binary -- sits in front of your Postgres instance and
turns every table/view into a REST endpoint automatically, with zero
backend code to write or maintain.

This is what `EXPO_PUBLIC_API_URL` in the app points at (see `app/lib/api.js`).

## 1. Why PostgREST instead of a custom API server

- It's a single static binary (or a tiny Docker image) with no application
  code -- nothing for you to write, patch, or have vulnerabilities in.
- It reads your schema and exposes `banking_use_cases`, `specific_regulations`,
  `guardrail_packages`, `guardrail_regulatory_mapping`, and
  `regulatory_horizon_forecast` as REST resources with full filtering
  (`?parent_sector=eq.Consumer%20Finance`), ordering, and embedding
  (`?select=*,guardrail_regulatory_mapping(*)`) for free.
- It's free and open source (MIT), matching the zero-budget constraint.

## 2. Local development

```bash
# macOS (Homebrew) or download a release binary from
# https://github.com/PostgREST/postgrest/releases
brew install postgrest

# postgrest.conf
cat > postgrest.conf <<'EOF'
db-uri = "postgres://USER:PASSWORD@HOST:5432/DBNAME"
db-schemas = "public"
db-anon-role = "web_anon"
server-port = 3000
EOF

postgrest postgrest.conf
```

Then `EXPO_PUBLIC_API_URL=http://localhost:3000` when running `expo start`.

## 3. The anonymous read-only role

PostgREST requires a Postgres role for unauthenticated requests. Since this
knowledge base has no secrets in it (GitHub tokens live only on-device --
see `app/lib/auth.js`), a read-only anonymous role is sufficient for the
free/open version of the app:

```sql
CREATE ROLE web_anon NOLOGIN;
GRANT USAGE ON SCHEMA public TO web_anon;
GRANT SELECT ON
    banking_use_cases,
    specific_regulations,
    guardrail_packages,
    guardrail_regulatory_mapping,
    regulatory_horizon_forecast,
    origin_driver_trend_summary,
    guardrail_compliance_summary
TO web_anon;
```

If you later want the app to write back (e.g. mark a guardrail `status`
as `staged` after a successful PR), grant `INSERT`/`UPDATE` on that specific
table to `web_anon` too, or add JWT-based auth (PostgREST supports this
natively) once you're past the free single-user prototype.

### Self-service use-case submission

The Knowledge Base screen's "Add your own use case" flow (`app/lib/api.js`
`submitUseCase()`) needs `INSERT` on `banking_use_cases` specifically --
grant only that, not broad write access. Applied to both the local dev DB
and production (Neon):

```sql
GRANT INSERT (name, parent_sector, modality, description, source, submitted_by_github_username,
              github_reference_url, operating_jurisdictions, risk_tier)
    ON banking_use_cases TO web_anon;
```

This is intentionally column-scoped: `web_anon` can create a new row but
can't set `id`, or overwrite existing rows (no `UPDATE` grant).
`github_reference_url` IS writable here -- a submitter linking the
open-source repo their use case is based on is just as legitimate a source
as what the GitHub-mining pipeline itself would find, so it's treated the
same as the other free-text fields, not held to the same
system-controlled standard as `id`. `risk_tier` is also writable, but not
as a raw free-choice field -- the app computes it client-side
(`app/lib/riskTierHeuristic.js::deriveRiskTier()`) from two structured
proxy answers ("does this decide something about a specific person?",
"does a human review before action?") that mirror the actual legal trigger
most profiling/automated-decision laws in this database use, rather than
asking a submitter to self-assign EU AI Act risk-tier terminology directly.
Since there's no real user auth in the free/open prototype, anyone with
the API URL can call this endpoint -- acceptable for a personal/community
instance, but add
row-level throttling or move to JWT-authenticated writes before treating
this as a public multi-tenant service.

## 4. Free hosting for the always-on PostgREST process

Unlike the ingestion crawler (which runs as a scheduled GitHub Action and
needs no always-on host), PostgREST must stay running so the app can query
it any time. Free-tier options that can run a long-lived Docker container
or binary:

- **Render.com** free web service tier (spins down on inactivity, spins
  back up on the next request -- acceptable for a personal/open-source
  prototype). **This is what LegalGuard actually uses** -- see the
  walkthrough below.
- **Fly.io** free allowance (small always-on VM).
- Your own always-on machine (Raspberry Pi, home server) if you have one --
  genuinely $0.

Point `db-uri` at your Neon Postgres connection string either way;
PostgREST itself is stateless.

### 4a. Deploying to Render

PostgREST publishes an official Docker image
(`docker.io/postgrest/postgrest`), so Render can run it directly as an
"existing image" web service -- no Dockerfile, no build step, no
application code of ours involved.

**Manual dashboard path (simplest, no YAML to get right):**

1. In the Render dashboard: **New +** -> **Web Service** -> **Existing
   Image**.
2. Image URL: `docker.io/postgrest/postgrest:v14.13`.
3. Name it (e.g. `legalguard-postgrest`) -- this becomes part of the public
   URL: `https://<name>.onrender.com`.
4. Instance type: **Free**.
5. Add these environment variables (Render's *Environment* tab):

   | Key | Value |
   |---|---|
   | `PGRST_DB_URI` | your Neon connection string, e.g. `postgresql://neondb_owner:PASSWORD@ep-falling-wildflower-zacvk80y-pooler.c-2.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require` |
   | `PGRST_DB_SCHEMAS` | `public` |
   | `PGRST_DB_ANON_ROLE` | `web_anon` |
   | `PGRST_SERVER_HOST` | `0.0.0.0` |
   | `PGRST_SERVER_PORT` | `10000` |

   Render's own `PORT` env var defaults to `10000` and Render forwards
   inbound traffic to whatever port you bind to, so `PGRST_SERVER_PORT`
   just needs to match it.

   Use Render's actual dashboard, entering the value yourself -- this
   connection string contains your database password, so it shouldn't be
   typed into a browser session anyone else is driving, pasted into this
   repo, or committed to `render.yaml`.

   Note: Render's Docker containers run on modern, current libpq, so
   unlike this Mac's old system `psql`/PostgREST binary you do **not**
   need the `?options=endpoint%3D...` SNI workaround here -- the plain
   connection string with `channel_binding=require` works as-is.

6. Deploy. Once live, verify with:
   ```bash
   curl -i "https://<name>.onrender.com/banking_use_cases?select=id&limit=1" \
     -H "Prefer: count=exact"
   ```
   Expect `HTTP/1.1 206 Partial Content` with a `Content-Range` header
   showing the real row count.
7. Point the app at it: set `EXPO_PUBLIC_API_URL=https://<name>.onrender.com`
   (see `app/eas.json` build-profile `env` blocks, and your local `.env`
   / shell export for `expo start`).

**Blueprint path (declarative, reproducible):** this repo's
[`render.yaml`](../render.yaml) defines the same service. In the Render
dashboard: **New +** -> **Blueprint**, point it at this repo. Render reads
`render.yaml`, provisions `legalguard-postgrest` with the non-secret env
vars pre-filled, and -- because `PGRST_DB_URI` is marked `sync: false` in
the file -- prompts you once, in Render's own UI, to paste in the Neon
connection string yourself. It's never written into the blueprint or the
repo.

Either path free-tier spins the service down after ~15 minutes idle and
takes a few seconds to cold-start on the next request -- fine for a
personal/community instance; upgrade to a paid instance type later if that
latency becomes a problem for real users.

## 5. Where this fits in the bigger picture

```
GitHub Actions (free cron) --writes--> Postgres (Neon/Supabase free tier)
                                              |
                                      PostgREST (free host)
                                              |
                                   Expo app on user's phone
                                              |
                              (GitHub API calls made directly
                               from the phone using the user's
                               own PAT -- see githubClient.js)
```

Postgres/PostgREST never see a user's GitHub token. The mobile app is the
only thing that ever holds it, in the OS keychain.
