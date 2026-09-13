# App Review response — Submission ID 404adc06-1b23-4ce5-b91b-c21446995e9f

Paste this into the App Store Connect reply, and also into App Review
Information > Notes, as requested.

---

**2. App purpose and target audience**

LegalGuard tracks AI regulation worldwide (EU AI Act, US federal and
state laws, UK FCA guidance, and more) and maps each regulatory change to
the specific financial-industry AI use cases it affects -- consumer
lending, mortgages, green/sustainable finance, voice-agent customer
support, AML/KYC, algorithmic trading, and others.

Target audience: compliance officers, risk managers, and engineers at
banks, insurers, and fintech companies who need to (a) stay current on
AI-specific regulation across jurisdictions, (b) understand which of
their own AI systems a given regulatory change actually affects, and (c)
generate a versioned, reviewable starting policy (Open Policy Agent
rules) to enforce that compliance in code, rather than tracking it only
in a spreadsheet or legal memo.

**3. Setup and main features**

No login or account is required for the app's core functionality. All of
the following are immediately usable with no sign-in:
- **Radar**: dashboard of tracked use cases, regulations, and pending
  regulatory items
- **Use Cases**: a searchable knowledge base of financial AI system
  patterns, sourced from open-source repositories and community
  submissions
- **Audit**: side-by-side legal text and generated policy diff for any
  tracked regulation
- **Horizon**: forecasts of upcoming regulatory shifts

**Add your own use case** (in the Use Cases tab): lets a user submit a
short name, sector/modality classification, and free-text description of
a financial AI system pattern to the shared knowledge base, optionally
linking a real open-source repo it's based on. This is the only
user-generated content in the app -- it is a narrow, non-social text
field (a system-pattern description, not user posts, images, or links
between users), reviewed in the context of a compliance knowledge base
rather than a social feed. Given its narrow scope and low-risk content
type, we have not built dedicated reporting/blocking tooling for it yet;
happy to add it if Review flags this as required.

**Dispatch** tab (optional, not required for any core functionality):
lets a user connect their OWN GitHub account via a Personal Access Token
they generate and paste in-app, to generate versioned Open Policy Agent
guardrail files as a pull request under their own GitHub account. This is
not a LegalGuard-issued account or credential -- it is the same pattern
as any app that lets a user connect their own GitHub/Google/etc. account.
There is no LegalGuard-provisioned demo account to provide, since the app
itself has no accounts.

To evaluate the Dispatch flow specifically without generating your own
GitHub PAT: the flow can be evaluated by reading the code path in
app/lib/githubClient.js (open source, linked below), and by inspecting
real, already-generated example output from this exact flow:
https://github.com/complianceguardrails-source/guardrail-front-office-voice-agent-mortgage-escalation-support

**4. External services used for core functionality**

- **Neon.tech** (managed Postgres): hosts the shared regulatory/use-case
  knowledge base
- **PostgREST**, hosted on **Render.com**: turns that database into a
  read-only REST API the app queries directly (no custom backend server)
- **GitHub REST API** (api.github.com): called directly from the user's
  own device, using the user's own Personal Access Token, only when they
  use the optional Dispatch feature. LegalGuard's backend never receives
  or stores this token
- No LLM/generative-AI API is called by the app at runtime. "AI" in the
  app's name and description refers to it being a tracker of regulation
  *about* AI systems -- the guardrail code it generates is produced by
  deterministic template logic (Open Policy Agent policy skeletons), not
  by calling a language model

**5. Regional differences**

The app functions identically in every region -- no feature is
geo-gated. The tracked regulatory *content* spans multiple jurisdictions
(EU, US federal and state, UK, and others) since that reflects the real
regulatory landscape financial institutions operate in, but this is data
displayed to all users everywhere, not a region-based feature
difference.

**6. Regulated industry / third-party material**

LegalGuard is used by people working in a regulated industry (financial
services) as a compliance-research and code-generation tool, but the app
itself does not provide any licensed or regulated financial service --
it does not execute trades, extend credit, underwrite insurance, or give
individualized financial/legal advice. It summarizes publicly available
regulatory text (statutes, agency guidance, model bulletins) in its own
words, with a citation and source URL back to the original public source
for every entry, rather than reproducing copyrighted material verbatim.
No special license or regulatory authorization is required to operate a
compliance-tracking/research tool of this kind, the same way legal- or
regulatory-research software generally does not require the publisher to
hold a financial license.
