---
paths:
  - "**/auth/**"
  - "**/*auth*.*"
  - "**/api/**"
  - "**/routes/**"
  - "**/*controller*.*"
  - "**/*route*.*"
  - "**/middleware*/**"
  - "**/migrations/**"
  - "**/*.sql"
  - "**/Dockerfile*"
---

# Security Rules (auth, API, routes, middleware, SQL, containers)

Security-sensitive file. Baseline: OWASP Top 10:2025 and ASVS 5.0 Level 1. When in doubt, deny.

## Access control (A01)
- Deny by default. Every handler enforces authentication **and** authorization server-side, preferably via shared middleware/policy.
- Check object-level ownership/tenancy in the query itself (`WHERE id = $1 AND tenant_id = $2`), not only role.
- Never trust client-supplied roles, prices, user ids, or state transitions. Map request bodies to allowlisted fields (no mass assignment).
- CORS: explicit origin allowlist; never reflect `Origin` with credentials.
- SSRF: user-influenced outbound URLs → allowlist scheme/host, block private/link-local/metadata IPs after DNS resolution and redirects.

## Input and injection (A05)
- Validate every input with a schema at the boundary (type, length, range, format, enum allowlist); reject invalid input.
- Parameterized queries only; allowlist dynamic identifiers (sort columns, table names).
- Processes: argv arrays, never shell strings. No `eval`/unsafe deserialization.
- Limit body size, pagination size, JSON depth; guard regexes against ReDoS.
- File paths: resolve and confirm they stay under the intended base dir.

## Authentication and sessions (A07)
- Use the project's established auth library/IdP; don't hand-roll crypto, tokens, or password handling.
- Passwords: Argon2id/scrypt/bcrypt; breached-password check; rate-limit and generic errors (no user enumeration).
- Sessions: regenerate on login; cookies `HttpOnly; Secure; SameSite`; invalidate server-side on logout; CSRF protection for cookie auth.
- JWT: verify signature with an algorithm allowlist (never `none`), `exp`, `iss`, `aud`; short-lived access tokens.
- Tokens, reset codes, ids: CSPRNG only; constant-time comparison for secrets.

## Errors and logging (A09, A10)
- Fail closed: an exception in an auth/validation path denies the request.
- Clients get generic messages + correlation id; no stack traces, SQL, or internal hosts.
- Log security events (login success/failure, authz denials, privilege changes) without secrets, tokens, or PII.

## Migrations and SQL
- Migrations are forward-safe and backward-compatible with the running code (expand → migrate → contract).
- No destructive changes (drop/rename column/table) without an explicit plan and backup; avoid long table locks (create indexes concurrently where supported).
- Least-privilege DB roles; no credentials or real personal data in migration/seed files.
- Constraints (unique, foreign key, not null) enforce invariants the code relies on.

## Containers (Dockerfile)
- Pin base images by version (ideally digest); use minimal/distroless images; multi-stage builds.
- Run as a non-root `USER`; no secrets in `ENV`/`ARG`/layers — use build secrets or runtime injection.
- `COPY` specific paths with a `.dockerignore` (exclude `.env`, `.git`, keys); no `curl | sh`.

## Secrets and dependencies (A02, A03)
- No secrets in code, config, tests, or commits; load from env/secret manager and validate at startup. Leaked → rotate.
- New dependencies: vet maintenance/popularity/typosquatting; commit lockfiles; don't loosen versions.
- Security headers and hardened defaults (debug off, no default credentials, no verbose errors) in production config.

For detail (each Top 10 category with do/don't, SSRF, ASVS highlights): **load skill `coding-standards`** (reference: security-owasp).
