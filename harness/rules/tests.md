---
paths:
  - "**/*.{test,spec}.*"
  - "**/__tests__/**"
  - "**/test/**"
  - "**/tests/**"
  - "**/*_test.go"
  - "**/src/test/**"
  - "**/androidTest/**"
---

# Test Rules

Follow the project's test framework, layout, naming, and helpers. Read an existing test in the same area before writing a new one.

## Structure
- Arrange-Act-Assert; one behavior per test; one Act.
- Name tests by behavior and condition: `rejects expired token`, `test_refund_over_balance_raises`, `TestParse_Empty_ReturnsError`.
- Use builders/factories with defaults (`aUser({ role: "admin" })`); override only what the test cares about.
- Table-driven / parametrized tests for input variations. No loops or conditionals computing expected values.
- Assert on observable behavior (outputs, state, responses, emitted events), not private internals.
- Cover the error paths and edge cases (empty, null, zero, max, unicode, duplicates), not just the happy path.

## Determinism (non-negotiable)
- No real time: inject a clock or use fake timers. Never `sleep` to wait — await the condition with a timeout.
- Seed or inject randomness; inject id generators.
- No dependence on test order, shared mutable state, map/set iteration order, local TZ/locale, or machine paths.
- No calls to the public internet. Use local containers, in-memory fakes, or recorded fixtures.
- Each test creates and cleans up its own data.
- Concurrency: deterministic dispatchers (`runTest`), `-race` in Go, await all async work.

## Doubles
- Prefer fakes (in-memory repo, fake clock) over mocks. Mock only at boundaries you don't control (network, payments, email, clock).
- Don't mock the unit under test, value objects, or pure logic. Don't mock types you don't own — wrap them in an adapter and fake the adapter.
- More than 3 mocks in one test signals a design problem; report it.
- Integration tests use a real database engine matching production (e.g. Testcontainers), not a mocked ORM.

## Integrity
- Never weaken, skip, or delete a failing test to make a change pass. If the test is wrong, say why and fix it explicitly.
- Every bug fix includes a regression test that fails without the fix.
- Don't update snapshots/golden files blindly — review the diff.
- A flaky test is a failing test: find the root cause (race, shared state, time) instead of adding sleeps, bigger timeouts, or retries. Quarantine only with a linked ticket.
- Coverage is a floor detector, not a target; meet the project threshold with meaningful assertions.

## Hygiene
- No secrets or real personal data in fixtures; use obviously fake values (`user@example.com`).
- Keep unit tests fast (ms each). Mark slow/integration tests per project convention.
- Test code follows the same quality rules as production code: clear names, no dead code, no commented-out tests.
- Run the tests you wrote and the affected suite; report actual output.

For strategy (pyramid vs trophy, doubles taxonomy, flaky-test policy): **load skill `coding-standards`** (reference: testing).
