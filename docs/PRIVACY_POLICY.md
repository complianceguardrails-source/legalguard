# LegalGuard Privacy Policy

**Last updated:** 2026-09-05

LegalGuard is an open-source guardrail-orchestration app. This policy
describes exactly what the app does with data, matching its actual
implementation -- not a generic template.

## GitHub Personal Access Token

If you connect a GitHub account, your Personal Access Token is stored
**only on your device**, in the OS-provided secure credential store (iOS
Keychain via `expo-secure-store`). It is never transmitted to any server
operated by LegalGuard, never logged, and never leaves your device except
in direct HTTPS requests you initiate to `api.github.com` -- GitHub's own
servers, under GitHub's own privacy policy (https://docs.github.com/en/site-policy/privacy-policies/github-privacy-statement).

You can remove the stored token at any time from the app's Dispatch/GitOps
Console screen, which deletes it from the device's secure store immediately.

## Data sent to GitHub

When you approve a guardrail action (creating a repository, branch,
commit, or pull request), the app sends the relevant repository name,
file contents, and commit/PR metadata directly to the GitHub REST API
using your token. This traffic goes directly from your device to GitHub;
LegalGuard's own backend is never in this path.

## Shared knowledge-base backend

LegalGuard maintains a shared, non-personal database of AI regulations and
financial-industry use cases (regulatory text, jurisdiction, effective
dates, open-source repository references). This data is sourced from
public government/regulatory websites and public GitHub repositories --
it is not about you.

If you use the "Add your own use case" feature, the use case description
you enter is stored in this shared database so other users benefit from
it, along with your GitHub username (if connected) so it can be
attributed as a community contribution. No other personal information is
collected through this feature.

## What we do not collect

LegalGuard does not use analytics SDKs, advertising identifiers,
crash-reporting services, or any third-party tracking. The app does not
request access to your contacts, location, camera, microphone, or photo
library.

## Data retention and deletion

- Your GitHub token: deleted immediately when you disconnect in the app,
  or when you uninstall the app (device secure storage is cleared with
  the app).
- Use cases you submit to the shared knowledge base: since this is a
  shared community resource, contact compliance.guardrails@gmail.com to
  request removal of a specific submission.

## Third-party services

- **GitHub** (api.github.com): receives requests directly from your
  device using your own token, governed by GitHub's privacy policy.
- **Neon.tech** (Postgres) and its PostgREST hosting provider: hosts the
  shared, non-personal regulatory knowledge base described above.

## Changes to this policy

Since LegalGuard is open source, changes to this policy will be committed
to the project repository alongside the corresponding code changes, so
the policy and the app's actual behavior stay in sync.

## Contact

For privacy questions or requests, contact compliance.guardrails@gmail.com.
