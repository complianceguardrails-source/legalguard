# App Store Connect Metadata

Copy-paste source for filling in the App Store Connect listing. Verify the
app name is still available before relying on it -- I can't check
availability from here.

## App Information

- **Name:** LegalGuard
- **Subtitle** (30 char max): `AI Regulation Guardrail Orchestrator`
- **Primary category:** Business
- **Secondary category:** Finance
- **Age rating:** 4+ (no objectionable content; straightforward business/
  productivity tool)

## Keywords (100 char max, comma-separated, no spaces after commas)

```
ai compliance,regulation tracker,fintech,opa,policy as code,github,guardrail,ai governance,ai risk
```

## Promotional text (170 char max, editable without a new build)

```
Track global AI regulation, map it to your financial AI use cases, and
push versioned OPA guardrails straight to GitHub -- all from your phone.
```

## Description (4000 char max)

```
LegalGuard tracks AI regulation worldwide -- EU AI Act, US CFPB, UK FCA,
and more -- and maps each change to the specific financial AI use cases
it affects: consumer lending, mortgages, green financing, voice-agent
customer support, AML/KYC, and dozens more.

WHAT IT DOES
• Radar: a live dashboard of your guardrails' compliance posture
• Use Cases: a searchable knowledge base of financial AI patterns,
  sourced from open-source repositories and your own submissions
• Audit: side-by-side legal text and the generated policy diff for any
  tracked regulation
• Horizon: forecasts of upcoming regulatory shifts and what's likely to
  drive them
• Dispatch: connect your own GitHub account to generate versioned Open
  Policy Agent (OPA) guardrail repositories -- reviewed as pull requests,
  never auto-merged

HOW IT HANDLES YOUR GITHUB ACCOUNT
Your GitHub Personal Access Token is stored only in this device's secure
keychain. Every GitHub action runs directly from your phone to GitHub's
API -- LegalGuard's backend never sees or stores your token.

OPEN SOURCE
LegalGuard's full source -- the ingestion pipeline, database schema, and
this app -- is open source and free to self-host.
```

## Support URL / Marketing URL

- Support URL: `mailto:compliance.guardrails@gmail.com`
- Marketing URL (optional): none yet -- leave blank unless a project site goes up later.

## Privacy Policy URL

Point this at a hosted copy of `docs/PRIVACY_POLICY.md` (e.g. via GitHub
Pages) -- fill in the bracketed placeholders in that file first (date,
contact, hosting provider name).

## App Privacy (Privacy Nutrition Label) questionnaire

Based on the actual implementation:

- **Data collected linked to the user:** None by LegalGuard's own backend.
  The GitHub token never reaches it.
- **Data collected but not linked to identity:** Use-case submissions via
  "Add your own use case" (free-text description you choose to submit,
  optionally tagged with your GitHub username if connected).
- **Third-party data sharing:** None beyond GitHub itself, which you are
  directly authenticating to with your own token -- this is standard
  "user-initiated third-party API" behavior, not LegalGuard sharing data
  with GitHub.
- **Tracking:** None. No advertising identifiers, no analytics SDKs.

## App Review notes (paste into the "Notes" field for reviewers)

```
LegalGuard is a compliance-tracking tool for financial-industry AI use
cases. Most functionality (Radar, Use Cases, Audit, Horizon tabs) is
browsable immediately with no sign-in -- it reads a shared, public
regulatory knowledge base.

The "Dispatch" tab lets a user optionally connect their OWN GitHub
account via a Personal Access Token (pasted in-app, stored in the
device's secure keychain, never sent to our backend) to generate
Open Policy Agent guardrail files as a GitHub pull request under their
own account. This is equivalent in kind to any app that lets a user
connect their own GitHub/Google/etc. account -- no LegalGuard-operated
credentials are involved.

To evaluate the Dispatch flow without a personal GitHub account, [EITHER:
"a demo GitHub account and scoped Personal Access Token are provided
below, restricted to a disposable test repository" -- OR, more simply --
"the flow can be evaluated by reading the code path in
app/lib/githubClient.js, and by inspecting real example output at
<paste one of your real guardrail repo/PR URLs here as a live
reference>."]
```

Fill in whichever bracketed option you're comfortable with -- if you
provide real demo credentials, use a token scoped to a single disposable
repo, not one with broad account access, and rotate/revoke it after
review completes.

## Screenshots

Required sizes: 6.7" (iPhone 15/16 Pro Max class) and 6.5" or 5.5" for
older device support, plus iPad sizes if `supportsTablet` stays enabled.
Capture these from the iOS Simulator once a dev build is running --
Radar, Use Cases, Audit (with a diff open), and Horizon are the strongest
screens to feature.
