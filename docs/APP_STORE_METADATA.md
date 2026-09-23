# App Store Connect Metadata

Copy-paste source for filling in the App Store Connect listing. Verify the
app name is still available before relying on it -- I can't check
availability from here.

## App Information

- **Name:** LegalGuard
- **Subtitle** (30 char max): `Responsible AI in Action` (24 chars; the original was 36 and would have been rejected)
- **Primary category:** Business
- **Secondary category:** Finance
- **Age rating:** 4+ (no objectionable content; straightforward business/
  productivity tool)

## Keywords (100 char max, comma-separated, no spaces after commas)

```
ai risk,ai compliance,regulation tracker,fintech,ai governance,guardrails,model risk,eu ai act,esg
```

## Promotional text (170 char max, editable without a new build)

```
Real financial AI systems, the risks each one carries, the regulations
that reach it, and the open-source guardrails that control those risks.
```

## Description (4000 char max)

```
LegalGuard maps real-world financial AI to its risks and its rules.
Every use case is a system actually published on GitHub or the Hugging
Face Hub -- credit scoring, fraud detection, trading, customer chatbots,
ESG analytics and more -- classified by what it does, how risky it is,
and why.

WHAT IT DOES
• Discover: pick categories, then swipe through use cases as cards.
  Each one shows its risk tier and the granular risks that tier is made
  of -- fifty-nine risks across seven families, from data drift and
  hallucination to greenwashing and vendor concentration.
• Regulations: every use case is linked to the instruments that reach it
  -- EU AI Act, SFDR, MiFID II, MAR, DORA, ECOA, AML rules, state AI and
  privacy laws, and more -- with the reason each one applies stated
  plainly.
• Existing guardrails: for each risk, the open-source controls that
  address it -- real repositories and models with their own stars,
  licence and last activity, linked out.
• Trending: today's stories from trusted financial outlets and
  regulators, placed against the risk each one reports on.
• Radar and Horizon: the numbers, pending regulations, and forecasts of
  what regulators are likely to do next.

NOTHING INVENTED
Use cases are mined from public repositories and the Hub. Regulation
text comes from EUR-Lex, the Federal Register, legislation.gov.uk and
regulators' own sites. Stories are the outlets' own headlines, linked to
the source. Where a risk has no known control, the app says so.

OPEN SOURCE
LegalGuard's full source -- the ingestion pipeline, database schema, and
this app -- is open source and free to self-host.
```

## What's New (version 1.1.0)

```
• New Discover flow: category cloud and swipe cards
• Risk tiers explained: the granular risks behind each tier
• Regulations linked by category with the reason stated
• Existing open-source guardrails per risk
• Trending: daily AI-risk stories from financial outlets and regulators
• Sustainable-finance rules: SFDR, Taxonomy, CSRD, green claims, EUDR, BNG
• New-since-your-last-visit counts on Discover, Trending and Radar
• Removed the GitHub dispatch flow; no account connection needed
```

## Support URL / Marketing URL

- Support URL: `https://github.com/complianceguardrails-source/legalguard/issues`
- Marketing URL (optional): none yet -- leave blank unless a project site goes up later.

## Privacy Policy URL

https://github.com/complianceguardrails-source/legalguard/blob/main/docs/PRIVACY_POLICY.md

GitHub renders this as a formatted page, not raw markdown, since the repo
is now public -- Apple accepts this directly, no separate hosting (GitHub
Pages, etc.) needed.

## App Privacy (Privacy Nutrition Label) questionnaire

Based on the actual implementation:

- **Data collected linked to the user:** None. The app has no account,
  no sign-in and no token; it reads a public database.
- **Data collected but not linked to identity:** None. Starred cards,
  dismissed cards and last-visit timestamps stay on the device.
- **Third-party data sharing:** None. Tapping a story or a repository
  opens the outlet's or platform's own site in the browser.
- **Tracking:** None. No advertising identifiers, no analytics SDKs.

## App Review notes (paste into the "Notes" field for reviewers)

```
LegalGuard is a reference tool for financial-industry AI risk. All
functionality is browsable immediately with no sign-in, no account and
no credentials: the app reads a shared, public knowledge base of AI use
cases (mined from public GitHub repositories and the Hugging Face Hub),
regulations (from EUR-Lex, the Federal Register, legislation.gov.uk and
regulators' own sites), open-source guardrail repositories, and news
headlines from financial outlets' public RSS feeds. Links open the
source in the browser. Starred/dismissed cards are stored only on the
device. Version 1.1.0 removes the previous GitHub-connection flow.
```
