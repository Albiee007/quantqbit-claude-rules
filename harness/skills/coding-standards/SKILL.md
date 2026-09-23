---
name: coding-standards
description: Language-agnostic engineering standards for writing and reviewing production code — SOLID, DRY/KISS/YAGNI, naming, error handling, testing, OWASP security, logging, performance, git hygiene, plus per-language idioms (TypeScript, Python, Kotlin, Go, bash). Use when writing, refactoring, or reviewing code in any stack; when unsure how to name, structure, test, secure, or log something; before opening a PR; or when a rule file says "load skill coding-standards".
---

# Coding Standards

Precedence: **project conventions override this skill.** Order of authority:
1. Explicit user instruction in the current task.
2. Project docs (`CLAUDE.md`, `CONTRIBUTING.md`, ADRs), linters, formatters, CI config.
3. The dominant idiom in the surrounding code (match it even if you would choose differently).
4. This skill.

If project style conflicts with a *security* rule here, flag it; do not silently follow either.

## Principles (one screen)

| Principle | Apply as |
|---|---|
| **SRP** | One reason to change per module/function. Split when two actors would edit it for unrelated reasons. |
| **OCP** | Add behavior by adding code, not editing stable code — *only* at proven variation points. |
| **LSP** | Subtypes honor the base contract: no stricter inputs, no weaker outputs, no surprise throws. |
| **ISP** | Small, client-shaped interfaces. No client depends on methods it does not call. |
| **DIP** | Policy depends on abstractions it owns; I/O details plug in at the edge. |
| **DRY** | One source of truth for *knowledge*, not for similar-looking text. **Rule of three:** tolerate duplication until the 3rd real occurrence; wrong abstraction costs more than duplication. |
| **KISS** | Choose the most boring construct that works. Cleverness is a cost paid by every reader. |
| **YAGNI** | Build for today's requirement. No hooks, flags, params, or layers for hypothetical futures. |
| **Least surprise** | Names, return types, side effects, and errors behave as a reader would guess. |
| **Composition > inheritance** | Inherit only for true is-a with LSP; otherwise compose/delegate. Max 1-2 levels. |
| **Explicit > implicit** | No hidden globals, magic config, implicit conversions, or action at a distance. |
| **Fail fast** | Validate preconditions early; crash loudly on programmer errors; never continue in a corrupt state. |
| **Boundaries validate, interior trusts** | Parse untrusted input once at the edge (HTTP, CLI, queue, file, env) into typed values; inner code relies on types, not re-checks. |

Before adding any abstraction, pattern, or layer: **load skill `design-patterns`** and pass its Decision Gate.

## Workflow: writing code

1. **Read conventions first.** Scan neighboring files, config (lint/format/tsconfig/pyproject/gradle/go.mod), tests, and project docs. Identify error style, naming, DI style, test framework, logging lib.
2. **Match surrounding idiom.** Reuse existing helpers, types, and patterns. Search before creating (`grep` for similar names). New dependency? Justify it; prefer what is already installed.
3. **Make the smallest change** that fully solves the task. No drive-by refactors, renames, or reformatting outside scope (propose them separately).
4. **Write/adjust tests** alongside the change: one failing test for a bug fix first; behavior tests for new features; cover the error path.
5. **Verify.** Run the project's formatter, linter, type-checker, and relevant tests. Read the actual output; do not claim success you did not observe.
6. **Self-review** the diff against [code-review-checklist](references/code-review-checklist.md) before declaring done. Remove debug output, dead code, stray TODOs.

## Workflow: reviewing code

1. Understand intent (ticket/PR description) before reading the diff.
2. Check correctness and security first, then design, then readability, then nits.
3. Rank findings by severity (blocker / major / minor / nit) per the checklist.
4. Every finding: location, problem, concrete fix. Distinguish facts from preferences.
5. Do not demand abstractions the change does not need (see `design-patterns` anti-patterns).

## Always / never

- Always: guard clauses over nesting; small functions (aim < 40 lines, one level of abstraction); named constants for domain numbers; typed errors; structured logs; deterministic tests.
- Never: commit secrets or `.env`; swallow errors; leave commented-out code; add `any`/untyped escape hatches without a reason comment; log PII, tokens, or passwords; concatenate untrusted input into SQL/shell/HTML.

## References

| Topic | File |
|---|---|
| SOLID with before/after examples | [solid](references/solid.md) |
| Naming | [naming](references/naming.md) |
| Error handling, retries, user messages | [error-handling](references/error-handling.md) |
| Testing strategy, doubles, flakiness | [testing](references/testing.md) |
| Security (OWASP Top 10:2025, ASVS 5.0) | [security-owasp](references/security-owasp.md) |
| Review checklist (severity-ranked) | [code-review-checklist](references/code-review-checklist.md) |
| Logging, metrics, traces | [logging-observability](references/logging-observability.md) |
| Git commits | [git-commits](references/git-commits.md) |
| Performance | [performance](references/performance.md) |
| TypeScript / JavaScript | [typescript](references/language-notes/typescript.md) |
| Python | [python](references/language-notes/python.md) |
| Kotlin / Android | [kotlin](references/language-notes/kotlin.md) |
| Go | [go](references/language-notes/go.md) |
| Bash / shell | [bash](references/language-notes/bash.md) |

Load only the reference relevant to the current task.
