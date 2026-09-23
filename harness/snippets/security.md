# Security — checklist (OWASP Top 10:2025)
- AuthZ server-side on every request; deny by default; check ownership/tenant in the query.
- Validate input with a schema at the boundary; allowlists; size limits.
- Parameterized SQL; argv arrays for processes; contextual output encoding; no eval/unsafe deserialization.
- No secrets in code, logs, or commits; env/secret manager; leaked -> rotate.
- Auth via proven library; Argon2id/bcrypt; secure cookies; JWT alg allowlist + exp/aud/iss.
- SSRF: allowlist outbound hosts; block private/metadata IPs after DNS + redirects.
- Fail closed on errors; generic client messages; log security events without PII/tokens.
- Dependencies: lockfile, audit in CI, vet new packages; pinned base images, non-root containers.
Load skill: coding-standards (reference: security-owasp) before changing auth, API, SQL, or infra code.
