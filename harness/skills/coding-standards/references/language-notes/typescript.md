# TypeScript / JavaScript Notes

## Idioms

- `strict: true` (plus `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` if the project allows). Never loosen config to silence an error.
- `unknown` over `any` for untrusted data; narrow with a schema (zod/valibot) at boundaries. `any` only with a `// reason:` comment.
- Model states with discriminated unions; enforce exhaustiveness:
  ```ts
  type Result<T> = { ok: true; value: T } | { ok: false; error: AppError };
  function assertNever(x: never): never { throw new Error(`unhandled: ${JSON.stringify(x)}`); }
  ```
- Prefer `type`/`interface` per project convention; union literal types or `as const` objects over `enum` (enums emit runtime code and have numeric pitfalls).
- `const` by default; `let` only when reassigned; never `var`.
- `readonly` fields/arrays for data that should not mutate; return new objects instead of mutating inputs.
- Optional chaining `?.` and nullish `??` (not `||`, which treats `0`/`""` as missing).
- ES modules, named exports (easier refactors/grep) unless framework requires default.
- `satisfies` to check a value against a type without widening it.
- Branded types for ids/units when mix-ups are a real risk: `type UserId = string & { __brand: "UserId" }`.
- Dates: store/transport ISO-8601 UTC; use `Temporal` (where available) or a date library for arithmetic; never parse ambiguous strings with `new Date(str)`.
- Money: integer minor units (`priceCents`) or a decimal library; never floats.

## Async

- Every promise awaited or explicitly handled; lint with `@typescript-eslint/no-floating-promises` and `no-misused-promises`.
- Independent work in parallel: `await Promise.all([...])`; use `Promise.allSettled` when partial failure is acceptable; cap concurrency (p-limit) for large fan-out.
- `for...of` with `await` for sequential; never `array.forEach(async ...)` (does not await).
- Pass `AbortSignal` for cancellable work and timeouts (`AbortSignal.timeout(ms)`).
- Errors: `throw new Error(msg, { cause })`; catch variables are `unknown` — narrow before use.

## Pitfalls

- `==` coercion — use `===` (except deliberate `x == null`).
- `this` lost in callbacks — use arrow functions or bind.
- `JSON.parse` returns `any` — validate immediately.
- `Array.prototype.sort` mutates and sorts lexicographically by default: `nums.sort((a, b) => a - b)`, or `toSorted`.
- Floating point: `0.1 + 0.2 !== 0.3`.
- Object spread is shallow; `structuredClone` for deep copies.
- `parseInt(x)` without radix; `Number("")` is `0`.
- Type assertions (`as Foo`) and non-null `!` bypass the checker — treat as a smell.
- Barrel files (`index.ts` re-exporting everything) can create cycles and bloat bundles.
- Node: don't block the event loop (sync fs/crypto in request path, heavy JSON on huge payloads).
- Prototype pollution: never merge untrusted objects into plain objects recursively; use `Object.create(null)`/`Map` for dictionaries of user keys.

## React / React Native specifics

- Components pure; side effects in `useEffect` with complete dependency arrays (lint `react-hooks/exhaustive-deps`) — and prefer derived state over effects.
- Keys stable and unique (not array index for dynamic lists).
- Memoize (`useMemo`, `useCallback`, `React.memo`) only when profiling shows a need, or when referential stability is required.
- Server state via a query library (TanStack Query, RTK Query) rather than hand-rolled effects.
- RN: `FlatList`/`FlashList` for long lists; avoid inline heavy work in render; secure storage (Keychain/Keystore) for tokens, never AsyncStorage.

## Tooling

- Run the project's `tsc --noEmit`, ESLint, Prettier (or Biome) before finishing.
- Tests: Vitest/Jest; Testing Library for UI (query by role/label, not test ids first); Playwright for E2E.

## Sources

- TypeScript Handbook: https://www.typescriptlang.org/docs/handbook/
- typescript-eslint rules: https://typescript-eslint.io/rules/
- React docs, "You Might Not Need an Effect": https://react.dev/learn/you-might-not-need-an-effect
