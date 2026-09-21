# LegalGuard Privacy Policy

**Last updated:** 2026-09-20

LegalGuard is an open-source reference app for financial-industry AI
risk. This policy describes exactly what the app does with data, matching
its actual implementation -- not a generic template.

## No account, no credentials

The app has no sign-in, no account and asks for no tokens or passwords.
Every screen reads from a shared, public knowledge base. (Versions before
1.1.0 offered an optional GitHub connection; that flow and its on-device
token storage were removed in 1.1.0.)

## What the app reads

LegalGuard maintains a shared, non-personal database of AI use cases
(mined from public GitHub repositories and the Hugging Face Hub), AI
regulations (regulatory text from public government sites), open-source
guardrail repositories (public GitHub and Hub metadata), and news
headlines (public RSS feeds of financial outlets and regulators, stored
as title, summary and link). None of it is about you.

## What stays on your device

Which cards you have starred or dismissed, and which categories you last
selected, are stored only on the device and are removed when you delete
the app. They are never sent anywhere.

## Links to other sites

Tapping a story, a regulation's source, a use case's repository or a
guardrail repository opens that site in your browser, under that site's
own privacy policy. LegalGuard passes nothing about you to it.

## What we do not collect

LegalGuard does not use analytics SDKs, advertising identifiers,
crash-reporting services, or any third-party tracking. The app does not
request access to your contacts, location, camera, microphone, or photo
library.

## Third-party services

- **Neon.tech** (Postgres) and **Render** (PostgREST hosting): host the
  shared, non-personal knowledge base described above. Requests from the
  app to it carry no identifier of you beyond what any HTTPS request
  carries (your IP address, seen by the hosting provider).

## Changes to this policy

Since LegalGuard is open source, changes to this policy are committed to
the project repository alongside the corresponding code changes, so the
policy and the app's actual behavior stay in sync.

## Contact

For privacy questions or requests, contact compliance.guardrails@gmail.com.
