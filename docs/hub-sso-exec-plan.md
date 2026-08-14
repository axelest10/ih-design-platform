# Hub SSO ExecPlan

Status: local implementation and regression gates complete; Staging release pending

Scope: Staging only

Design baseline: `8ec64fabfa2601528f56ee5fbae964368071ee88` (`origin/main`)

Design branch: `codex/hub-sso`

Hub baseline: `b74f57876d14cf265f2c914ebc5ab5ebcb99ea59` (`origin/main`)

Hub branch: `codex/ih-latam-identity-oidc`

## Goal and boundaries

Integrate the independent Design Platform with the IH LATAM Hub through OpenID Connect Authorization Code Flow with PKCE `S256`. The Hub owns authentication and immutable identity. Design continues to own its Django users, groups, permissions, content, and sessions. The repositories, migrations, CI, PRs, and Railway services remain independent.

This plan is Staging-only. It does not authorize Production variables, data, DNS, deployment, real-user migration, or real email. Production currently exists in Railway and must remain untouched.

## Audited baseline

Design uses Django 5.1/DRF, PostgreSQL, Redis, Django server sessions, Django's built-in User, and local groups (`platform_admin`, `marketing`, `designer`, `reviewer`, `viewer`). The existing password route checks a corporate-domain allowlist and preserves local role enforcement through server-side viewset permissions. Session lifetime is currently Django's longer default and must be shortened only for Hub-authenticated sessions.

Hub uses Auth.js passwordless sessions in Next.js, NestJS/Prisma APIs, PostgreSQL, and Redis. It revalidates active users and current authorization for API requests. Hub `User.id`, not email, is the immutable identity subject.

## Shared contract

`docs/identity-contract.v1.json` is the byte-identical contract stored in both repositories. Staging uses issuer `https://dev-hub.ihlatam.com/oidc`, client ID `ih-design-platform-staging`, exact callback `https://ih-design-platform-staging.up.railway.app/api/v1/auth/hub/callback/`, scopes `openid profile email`, `RS256`, a 60-second single-use code, five-minute tokens, no refresh token, and a 15-minute local Design session.

Only `sub`, `email`, truthful Boolean `email_verified`, and optional `name` cross the boundary. Hub roles and organisation data never do.

## Implementation sequence

1. Pin Authlib v1.7.2 and add environment-validated OIDC settings. The integration is disabled unless explicitly enabled and Production requires a distinct approval flag not configured here.
2. Add `/api/v1/auth/hub/login/` and `/api/v1/auth/hub/callback/`. Use discovery, exact issuer/client/callback, confidential client authentication, state, nonce, PKCE `S256`, and signature/audience/expiry validation. Never persist tokens.
3. Bind a relative-only `next` path to the server session. Reject external, scheme-relative, backslash, host-confusing, or stale return targets.
4. Add `HubIdentity` with unique immutable subject and one-to-one local user, plus append-only `HubIdentityEvent` audit records.
5. Resolve in a transaction: existing subject first; otherwise one unique case-insensitive email match for first link; otherwise create a local user with unusable password and only `viewer`. Conflicts and ambiguous email matches fail closed.
6. Preserve all groups for existing linked users and deny inactive local users. Mark the session as Hub-authenticated and expire it at 900 seconds.
7. Adapt the corporate-domain permission so an authenticated session with a matching Hub subject link is accepted without treating email as identity. Legacy password sessions keep the current domain rule.
8. Make Hub SSO the primary login choice. Retain the password form as an explicit secondary Staging path; a future Production plan addresses normal-login retirement and break-glass control.
9. Add authenticated deep-link handling for protected HTML entry points without changing deliberately public brand/catalogue pages.
10. Add unit/integration tests, update security/deployment docs, `DECISIONS.md`, and `TASKS.md`, then run Ruff, Django checks, migrations checks, pytest, and the repository's brand gates.

## Security and failure tests

Tests must prove correct login and also reject bad state, nonce, issuer, audience, signature, algorithm, expired tokens, reused callbacks, missing or downgraded PKCE, wrong client/callback, unsafe `next`, conflicting subject links, ambiguous email matches, unverified email, inactive Hub assertions, and inactive Design users. They must show that first provisioning receives only `viewer`, existing local role sets remain unchanged, local object/action permissions still deny cross-role operations, logout destroys the Design session, and provider failure is explicit.

Logs and durable audit rows must not contain access tokens, ID tokens, codes, client secrets, session cookies, passwords, or passwordless links. Audit events retain only event type, local user reference where available, Hub subject where required for immutable traceability, result, timestamps, and bounded non-secret metadata.

## Staging release and evidence

After local gates pass, commit and push only `codex/hub-sso`, open a Design draft PR cross-linked to the Hub draft PR, and wait for Design CI. Deploy this exact branch only to Design Staging. Run its additive migration, verify the exact served revision, callback and discovery behavior, security matrix, synthetic persona/browser flows, logout, deep links, and a stable log window.

If synthetic Hub passwordless authentication cannot be completed without real email or extracting a token, report that as an explicit UAT blocker. Do not weaken the login ceremony or access Production to create evidence.

## Rollback

Disable Design Hub SSO and redeploy the prior Design Staging revision. The legacy Staging password path remains available. Additive subject-link and event tables stay in place to preserve history; rollback never deletes links or audit records. The Hub provider can be disabled and rolled back separately.

## Future Production migration (not part of this change)

A separately approved plan must create a new Production client ID/secret/callback, signing keys and rotation rehearsal, backups, synthetic pilot users, role-parity evidence, monitoring, and a rollback drill. Only after that evidence may ordinary Design password login be disabled, with one separately controlled, audited break-glass administrator retained. Nothing in this Staging pass changes Production behavior.

## Progress and decisions

- 2026-08-14: cloned the official private repository as a sibling, verified its exact origin, fetched both remotes, and created clean worktrees from `origin/main`.
- 2026-08-14: read all repository instructions and audited authentication, permissions, sessions, persistence, tests, CI, and read-only Staging deployment metadata.
- 2026-08-14: selected and pinned Authlib 1.7.2 after reviewing its official Django client documentation, current release and security advisory history. It supplies maintained discovery, state/nonce, PKCE and token validation; the small local subclass pins ID-token verification to RS256. Also selected subject-first additive linkage, least-privilege provisioning, local authorization preservation, and 15-minute relying-party sessions.
- 2026-08-14: local Design validation completed with Ruff, Django system/migration checks, 145 focused identity/authorization regressions and 399 full tests. CI, Staging deployment, migration readback and browser UAT remain separate gates.
- Rejected shared databases, copied password records, proprietary tokens, email-as-key, Hub-role mapping, wildcard callbacks, refresh tokens, and automatic privileged provisioning.

Completion remains pending until local tests, CI, exact Staging deployment, migration state, cross-application security evidence, browser UAT, and stable logs are reconciled. Missing gates make the final result AMBER or RED, not assumed GREEN.
