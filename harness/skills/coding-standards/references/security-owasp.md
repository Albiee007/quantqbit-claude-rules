# Security (OWASP Top 10:2025, ASVS 5.0)

The current OWASP Top 10 is the **2025 edition** (final). SSRF, a standalone category in 2021, is now part of A01. Secure defaults first; every "don't" below has shipped a real breach.

## OWASP Top 10:2025

### A01 Broken Access Control (includes SSRF)
- Do: deny by default; enforce authorization **server-side on every request** in one reusable layer (middleware/policy), checking ownership of the specific resource (`WHERE id = $1 AND tenant_id = $2`).
- Do: test authz with a second user/tenant (IDOR tests); check function-level (role) *and* object-level (ownership) access.
- Don't: rely on hidden UI, client-side checks, unguessable IDs, or `role` fields sent by the client. Don't allow mass assignment — map request DTOs to allowlisted fields.
- CORS: explicit origin allowlist; never reflect `Origin` with credentials.
- SSRF: see dedicated section below.

### A02 Security Misconfiguration
- Do: hardened, repeatable config per environment; security headers (`Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `frame-ancestors`); disable directory listing, debug endpoints, default accounts, sample apps.
- Do: least-privilege IAM, DB users, containers (non-root, read-only FS where possible, drop capabilities).
- Don't: ship `DEBUG=true`, verbose errors, open admin consoles, public buckets, wildcard CORS, or XML parsers with external entities enabled (XXE).

### A03 Software Supply Chain Failures
- Do: commit lockfiles; install with frozen/CI mode (`npm ci`, `pnpm i --frozen-lockfile`, `pip install --require-hashes`, `go mod verify`); pin CI actions to commit SHAs; enable Dependabot/Renovate + audit (`npm audit`, `pip-audit`, `govulncheck`, OSV-Scanner) in CI.
- Do: verify new packages before adding — maintainer activity, download count, typosquat names, install scripts; prefer stdlib or existing deps.
- Do: generate SBOMs and sign/verify build artifacts (Sigstore, SLSA provenance) where the project supports it.
- Don't: `curl | sh` in builds, unpinned `latest` base images, or install scripts from unreviewed packages.

### A04 Cryptographic Failures
- Do: TLS 1.2+ everywhere (1.3 preferred); encrypt sensitive data at rest; use vetted libraries (libsodium, platform crypto, `crypto/*` in Go) with AEAD (AES-GCM, ChaCha20-Poly1305).
- Passwords: Argon2id (preferred), scrypt, bcrypt (cost ≥ 10), or PBKDF2-HMAC-SHA256 (≥ 600,000 iterations). Never MD5/SHA-1/plain SHA-256 for passwords.
- Randomness for tokens/IDs: CSPRNG (`crypto.randomUUID`, `crypto.getRandomValues`, `secrets`, `crypto/rand`, `SecureRandom`). Never `Math.random`/`random`.
- Don't: roll your own crypto, use ECB, reuse IVs/nonces, hard-code keys, or compare secrets with `==` (use constant-time compare).

### A05 Injection (SQL, NoSQL, OS command, LDAP, XSS, template)
- Do: parameterized queries / query builders; ORM without raw string interpolation.
- Do: pass argv arrays to processes (`execFile`, `subprocess.run([...], shell=False)`, `exec.Command(name, args...)`), never a shell string.
- Do: contextual output encoding; framework auto-escaping (React, Jinja2 autoescape, Compose). Sanitize HTML with a vetted library (DOMPurify) if you must render user HTML. Add CSP.
- Don't: `eval`, `new Function`, `dangerouslySetInnerHTML`/`v-html`/`innerHTML` with untrusted data, dynamic table/column names from input (allowlist them), `pickle`/`yaml.load`/Java native deserialization of untrusted data.

### A06 Insecure Design
- Do: threat-model new features touching auth, money, PII, or file handling (STRIDE-lite: who can abuse this and how?).
- Do: business-logic limits — rate limits, quotas, amount caps, anti-automation on sensitive flows (signup, OTP, password reset, checkout).
- Do: idempotency keys for payment-like operations; server-side state machines for multi-step flows (can't skip step 2).
- Don't: trust client-computed prices, totals, or state transitions.

### A07 Authentication Failures
- Do: use a proven identity provider/library (OIDC, platform auth) over custom auth; MFA available (required for admin); passkeys/WebAuthn where possible.
- Passwords: min 8 chars (encourage ≥ 15), allow ≥ 64 and all characters, check against breached-password lists, no composition rules, no forced periodic rotation.
- Sessions: regenerate ID on login/privilege change; cookies `HttpOnly; Secure; SameSite=Lax|Strict`; server-side invalidation on logout; idle + absolute timeouts.
- Brute force: rate-limit and progressive delay per account and per IP; generic error messages (no user enumeration).
- JWT: verify signature, `alg` allowlist (never `none`), `exp`, `iss`, `aud`; short-lived access tokens; rotation for refresh tokens.

### A08 Software or Data Integrity Failures
- Do: verify signatures/checksums of updates, plugins, and downloaded artifacts; protect CI/CD pipelines (least privilege tokens, protected branches, required reviews).
- Do: sign or MAC data that round-trips through the client (cookies, hidden fields) or keep it server-side.
- Don't: deserialize untrusted data into objects with behavior; auto-update from unsigned sources.

### A09 Security Logging & Alerting Failures
- Do: log security events — login success/failure, MFA changes, authz denials, password resets, admin actions, input validation failures at scale — with user id, source IP, correlation id, timestamp.
- Do: alert on anomalies (spikes in 401/403, lockouts); make logs tamper-evident and retained per policy.
- Don't: log secrets, tokens, passwords, full card numbers, or unnecessary PII. Neutralize CR/LF in logged user input (log injection) — structured logging handles this.

### A10 Mishandling of Exceptional Conditions
- Do: fail **closed** — on error in an authz/validation path, deny. Handle every error path explicitly; set timeouts; release resources in `finally`/`defer`.
- Do: return generic error messages to clients; log details server-side (see [error-handling](error-handling.md)).
- Don't: swallow exceptions, leave transactions half-committed, or expose stack traces. Don't let a parsing error default to "allowed".

## Secrets

- Never commit secrets. `.env*` (except `.env.example` with placeholders) is gitignored. Run secret scanning (gitleaks, trufflehog, GitHub push protection).
- Load from env or a secret manager (Vault, AWS/GCP/Azure secret managers, Kubernetes secrets with encryption); validate presence at startup.
- A leaked secret is **rotated**, not just deleted from git history.
- Mobile/front-end bundles are public: never embed private API keys, signing keys, or admin tokens. Proxy through a backend.
- Scope tokens minimally; prefer short-lived credentials (OIDC federation in CI instead of static cloud keys).

## Input validation

- Validate at every trust boundary with a schema: type, length, range, format, allowlisted enums. Reject, don't "fix", invalid input.
- Allowlist over denylist. Canonicalize (decode, normalize Unicode, resolve paths) **before** validating.
- File uploads: size limit, content-type sniffing (magic bytes) not just extension, random server-side filenames, store outside web root, scan if required, never execute.
- Paths: resolve and verify the result stays inside the intended base directory (path traversal).
- Limit request body size, JSON depth, array lengths, regex complexity (ReDoS).

## Authorization

- Centralize policy (`can(user, action, resource)`); call it in every handler — ideally enforced by middleware so forgetting is impossible.
- Check object ownership/tenancy in the data query, not after fetching everything.
- Re-check authorization on every state-changing request, including websocket messages and background jobs triggered by users.
- Least privilege for service accounts; separate admin surfaces.
- Write negative tests: user B cannot read/update/delete user A's resource.

## SSRF (part of A01:2025)

When the server fetches a URL influenced by user input (webhooks, image fetch, URL preview, import-from-URL):
- Allowlist schemes (`https`) and, ideally, destination hosts.
- Resolve DNS and block private/reserved ranges (127.0.0.0/8, 10/8, 172.16/12, 192.168/16, 169.254/16 incl. cloud metadata 169.254.169.254, ::1, fc00::/7, fe80::/10); re-check after redirects, or disable redirects; pin the resolved IP for the connection (DNS rebinding).
- Run fetchers in a network-restricted egress zone; enforce IMDSv2 on AWS.
- Don't return raw fetched responses or error details to the user.

## Dependency hygiene

- Add a dependency only when it saves meaningful effort and is maintained; prefer the standard library.
- Keep lockfiles committed; update regularly in small batches; read changelogs for majors.
- Fail CI on known critical/high vulnerabilities with an exception process.
- Remove unused dependencies.

## ASVS 5.0 Level 1 highlights (minimum bar for any internet-facing app)

ASVS 5.0.0 (May 2025) is organized into 17 chapters; L1 is the baseline, L2 the recommended default for most apps handling sensitive data, L3 for high-assurance.
- **Encoding & sanitization:** output encoding for the interpreter in use; parameterized queries; no dynamic code eval of user data.
- **Validation & business logic:** server-side validation with allowlists; business flows enforced in sequence.
- **Web frontend:** cookies with `Secure`/`HttpOnly`/`SameSite`; anti-CSRF where cookies authenticate; CSP; no sensitive data in URLs.
- **Authentication:** breached-password check, length ≥ 8, rate limiting, no default credentials, secure recovery.
- **Session management:** new session token on authentication; server-side invalidation on logout/timeout.
- **Authorization:** enforced at a trusted service layer; object-level checks; deny by default.
- **Self-contained tokens (JWT):** signature and algorithm validated; expiry and audience checked.
- **Cryptography & secure communication:** TLS for all traffic; approved algorithms; no hard-coded keys.
- **Configuration & data protection:** secrets not in source; debug off in production; sensitive data not cached/logged.
- **Logging & error handling:** security events logged without sensitive data; generic error responses.

## Sources

- OWASP Top 10:2025: https://top10.owasp.org/2025/0x00_2025-Introduction
- OWASP ASVS 5.0: https://github.com/OWASP/ASVS
- OWASP Cheat Sheet Series (Password Storage, SSRF Prevention, Authorization, Session Management): https://cheatsheetseries.owasp.org/
- NIST SP 800-63B Digital Identity Guidelines: https://pages.nist.gov/800-63-4/sp800-63b.html
- SLSA supply-chain framework: https://slsa.dev/
