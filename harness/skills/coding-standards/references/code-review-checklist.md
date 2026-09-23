# Code Review Checklist

Use for self-review before declaring done and for reviewing others' changes. Work top-down: stop and fix blockers before polishing nits.

## Severity levels

| Level | Meaning | Merge? |
|---|---|---|
| **Blocker** | Incorrect, insecure, data-losing, or breaks build/tests/contract | No |
| **Major** | Likely bug, missing tests for changed behavior, maintainability hazard | Fix before merge unless explicitly deferred with ticket |
| **Minor** | Clarity, naming, small design improvement | Author's call |
| **Nit** | Style preference not enforced by tooling | Optional; prefix with "nit:" |

## Blocker

- [ ] Does it do what the task/ticket asks? Edge cases: empty, null, zero, negative, max, unicode, duplicates, concurrency.
- [ ] Secrets, tokens, `.env`, private keys, or credentials in the diff.
- [ ] Injection: string-built SQL/shell/HTML/paths from untrusted input.
- [ ] Missing authorization or ownership check on a new/changed endpoint or query.
- [ ] Errors swallowed, or failure path leaves partial state (no transaction/rollback/compensation).
- [ ] Data migrations: irreversible without backup, locks large tables, not backward-compatible with running code.
- [ ] Breaking change to a public API/schema/event without versioning or migration.
- [ ] Build, type-check, lint, or tests fail; tests weakened/skipped to pass.
- [ ] Race conditions: check-then-act on shared state, non-atomic read-modify-write, missing locks/unique constraints.
- [ ] Resource leaks: unclosed files/connections/streams, unbounded goroutines/listeners, missing timeouts on network calls.

## Major

- [ ] Changed behavior has tests; bug fix has a regression test; error paths are tested.
- [ ] Input validated at the boundary; types trusted in the interior.
- [ ] No new abstraction/pattern without passing the `design-patterns` Decision Gate.
- [ ] No duplication of *knowledge* (same business rule in two places) — duplication of shape is fine below 3 occurrences.
- [ ] Performance: no N+1 queries, no unbounded result sets (pagination), no O(n²) on growing data, no blocking I/O on hot/UI threads.
- [ ] Logging: meaningful events at correct level, structured, no PII/secrets, correlation id propagated.
- [ ] Backward/forward compatibility for serialized data, config, feature flags.
- [ ] New dependency justified, maintained, license-compatible, lockfile updated.
- [ ] Concurrency primitives used correctly (await all promises, cancellation propagated, no shared mutable state without sync).
- [ ] Idempotency for retried operations (webhooks, queue consumers, payments).

## Minor

- [ ] Names reveal intent; units in names where types don't carry them.
- [ ] Functions small, single level of abstraction; guard clauses instead of deep nesting.
- [ ] No magic numbers/strings; constants named.
- [ ] No dead code, commented-out code, debug prints, stray TODOs without ticket.
- [ ] Comments explain *why*, not *what*; public APIs documented.
- [ ] Matches surrounding conventions (error style, file layout, test style).
- [ ] Scope is focused — unrelated refactors split out.

## Nit

- [ ] Formatting not caught by the formatter; import order; wording in comments.

## Review etiquette

- Be specific: file:line, problem, suggested fix. Ask questions when unsure ("What happens if `items` is empty?").
- Separate facts ("this throws on null") from preferences ("I'd name this...").
- Approve with minors/nits outstanding when appropriate; don't block on taste.
- Review the tests as carefully as the code — they define the behavior.

## Sources

- Google Engineering Practices, "What to look for in a code review": https://google.github.io/eng-practices/review/reviewer/looking-for.html
- OWASP Code Review Guide: https://owasp.org/www-project-code-review-guide/
- Conventional Comments: https://conventionalcomments.org/
