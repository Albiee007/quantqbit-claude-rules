# Naming

A name is the cheapest documentation. It should tell the reader *what* and *why*, never *how*.

## Rules

1. **Follow the language/project casing convention** — do not mix.
   | Lang | Types | Functions/vars | Constants | Files |
   |---|---|---|---|---|
   | TS/JS | `PascalCase` | `camelCase` | `UPPER_SNAKE` (module-level true constants) | project convention (`kebab-case` or `camelCase`) |
   | Python | `PascalCase` | `snake_case` | `UPPER_SNAKE` | `snake_case.py` |
   | Kotlin/Java | `PascalCase` | `camelCase` | `UPPER_SNAKE` (`const val`) | `PascalCase.kt` |
   | Go | exported `PascalCase`, unexported `camelCase` | same | same (no `UPPER_SNAKE`) | `snake_case.go` |
   | Bash | — | `snake_case` functions/locals | `UPPER_SNAKE` env/exported | `kebab-case.sh` |
2. **Length scales with scope.** `i` in a 3-line loop is fine; a module-level variable needs a full descriptive name.
3. **Use domain vocabulary** (ubiquitous language). If the business says "policy holder", do not write `customer`. One concept = one word across the codebase (`fetch`/`get`/`retrieve` — pick one).
4. **Functions are verbs, values are nouns.** `calculateTax()`, `sendInvite()`; `invoice`, `retryCount`.
5. **Booleans read as predicates:** `isActive`, `hasAccess`, `canRetry`, `shouldNotify`. Avoid negatives (`isNotDisabled`).
6. **Include units** when the type doesn't: `timeoutMs`, `sizeBytes`, `priceCents`, `ttlSeconds`. Prefer a unit-carrying type (`Duration`, `Money`) when available.
7. **Collections are plural** (`users`), maps say what maps to what (`priceBySku`, `usersById`).
8. **No type encoding / Hungarian** (`strName`, `IUser` unless the project uses it, `userList` when it's a Set).
9. **No noise words:** `data`, `info`, `manager`, `helper`, `util`, `handle`, `process`, `do`, `obj`, `tmp` — unless nothing more specific exists. `utils.ts` becomes a dumping ground; name modules by capability (`money.ts`, `retry.ts`).
10. **Avoid abbreviations** except universally known ones (`id`, `url`, `http`, `db`, `ctx` in Go). Never invent them (`usrMgrSvc`).
11. **Name side effects honestly.** `getUser()` must not create one; use `getOrCreateUser()`. A function that mutates says so (`sortInPlace`, `applyDiscount`).
12. **Symmetric pairs:** `open/close`, `start/stop`, `acquire/release`, `add/remove`, `min/max`, `begin/end`.
13. **Tests describe behavior:** `rejects expired tokens`, `test_refund_exceeding_balance_raises`, `TestParse_EmptyInput_ReturnsError`.
14. **Errors are named by condition:** `NotFoundError`, `InsufficientFundsError`, `ErrTimeout` (Go).
15. **Rename when meaning drifts.** A misleading name is a bug. Rename in a separate commit if the diff is large.

## Smells

- You need a comment to explain what a variable holds → rename it.
- Name contains `And` → function does two things.
- `flag`, `mode`, `type` boolean/string parameters → consider two functions or an enum.
- Numbered names (`user1`, `user2`, `handler2`) → missing concept.
- Same name means different things in two modules → introduce distinct names or namespaces.

## Before / after

```ts
// before
function proc(d: any[], f: boolean) { /* ... */ }
const t = 86400;

// after
function archiveExpiredSessions(sessions: Session[], dryRun: boolean) { /* ... */ }
const SESSION_TTL_SECONDS = 24 * 60 * 60;
```

## Sources

- Robert C. Martin, *Clean Code* (2008), ch. 2 "Meaningful Names".
- Eric Evans, *Domain-Driven Design* (2003), "Ubiquitous Language".
- Google style guides: https://google.github.io/styleguide/
- PEP 8 naming conventions: https://peps.python.org/pep-0008/#naming-conventions
- Effective Go, Names: https://go.dev/doc/effective_go#names
