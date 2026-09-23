---
paths:
  - "**/*.{ts,tsx,js,jsx,mjs,cjs,py,go,kt,kts,java,swift,rb,php,cs,rs,dart}"
---

# Coding Rules (always apply to source files)

Project conventions (CLAUDE.md, linters, formatters, surrounding code) override these. When they conflict with a security rule, flag it.

## Before writing
- Read neighboring files and config first; match the existing idiom, error style, naming, and test framework.
- Search for an existing helper/type before creating one. Prefer installed dependencies; justify any new one.
- Make the smallest change that fully solves the task. No drive-by refactors or reformatting outside scope.
- **Load skill `design-patterns` BEFORE adding any abstraction** (interface, base class, factory, new layer, pattern) and pass its Decision Gate. Default: write the simple version.

## Naming
- Follow the language casing convention. Names reveal intent; use domain vocabulary; one word per concept.
- Functions are verbs, values are nouns, booleans are predicates (`isActive`, `hasAccess`).
- Put units in names when types don't carry them (`timeoutMs`, `priceCents`).
- No noise names (`data`, `info`, `manager`, `utils`, `tmp`) or invented abbreviations.

## Structure
- Small functions (aim < 40 lines), one level of abstraction, guard clauses over deep nesting.
- Soft cap ~500 lines per file; split by responsibility when exceeded (don't split just to hit a number).
- Composition over inheritance; max 1-2 inheritance levels.
- Pure logic separated from I/O; dependencies passed in (constructor/params), not constructed inside business logic.
- Validate untrusted input at boundaries into typed values; trust types in the interior.

## Hygiene
- No dead code, no commented-out code, no debug prints, no TODOs without a ticket reference.
- No magic numbers/strings: name domain constants (`MAX_LOGIN_ATTEMPTS = 5`). `0`, `1`, `-1`, `""` in obvious contexts are fine.
- No `any`/untyped escape hatches, `!!`, `as` casts, or lint-disables without a one-line reason comment.
- Comments explain *why*, not *what*. Public APIs documented per project convention.
- Immutable by default (`const`, `val`, `readonly`, frozen dataclasses).

## Errors
- Never swallow errors (`catch {}`, `except: pass`, ignored Go `err`). Catch the narrowest type you can handle.
- Use typed/domain errors and preserve cause chains; match on type/code, not message text.
- Log an error once, at the boundary that handles it. Fail fast on programmer errors.
- Timeouts on every network call; clean up with `finally`/`defer`/`use`/`with`.
- Every promise/coroutine/goroutine awaited or supervised.

## Security (always)
- No secrets, tokens, keys, or `.env` values in code, logs, tests, or commits. Read from env/secret manager.
- No string-built SQL, shell commands, HTML, or file paths from untrusted input — parameterize, use argv arrays, encode output.
- No `eval`/dynamic code execution; no unsafe deserialization of untrusted data.
- Never log passwords, tokens, or PII.

## Before declaring done
- Run the project's formatter, linter, type-checker, and relevant tests; report real results.
- Self-review the diff; remove anything unrelated to the task.
- For detail (SOLID, naming, error handling, testing, security, logging, performance, language idioms): **load skill `coding-standards`**.
