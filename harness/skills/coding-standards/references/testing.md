# Testing

Tests exist to let you change code with confidence. Optimize for **confidence per unit of maintenance cost**.

## Shape: pyramid vs trophy

- **Pyramid** (Cohn): many unit, fewer integration, few E2E. Fits libraries, domain-heavy backends, algorithmic code.
- **Trophy** (Dodds): static analysis base, *most* tests at integration level, some unit, few E2E. Fits UI apps and glue-heavy services where the risk is in the wiring.
- Choose per codebase; follow what the project already does. Either way: static types + lint catch a class of bugs for free; E2E is slow and flaky, reserve for critical user journeys (login, checkout, core happy path).

| Level | Scope | Speed | Real deps |
|---|---|---|---|
| Unit | function/class, pure logic | ms | none |
| Integration | module + real DB/queue/HTTP via containers or in-memory equivalents | 100ms-s | yes, local |
| Contract | consumer/provider API agreement (Pact, schema tests) | fast | no |
| E2E | full deployed system via UI/API | s-min | all |

## Structure: Arrange-Act-Assert

```ts
it("applies 10% discount for orders over 100", () => {
  // Arrange
  const order = anOrder({ subtotal: 120 });
  // Act
  const total = priceOrder(order);
  // Assert
  expect(total).toBe(108);
});
```
- One behavior per test; one Act. Multiple asserts OK if they check one outcome.
- Name tests by behavior and condition, not method name (`returns 404 when user missing`).
- Test builders/factories (`anOrder({...})`) with sensible defaults; override only what matters to the test.
- No logic in tests (loops/ifs computing expected values). Use table-driven/parametrized tests for cases.
- Assert on observable behavior (return values, state, emitted events, HTTP responses), not private internals or call order unless order *is* the contract.

## Determinism (non-negotiable)

- **Time:** inject a clock or use fake timers. Never `sleep` to wait; poll with timeout or await the event.
- **Randomness:** seed it or inject the generator. UUIDs: inject or assert on shape.
- **Order:** no dependence on test execution order or map/set iteration order. Each test sets up and tears down its own state.
- **Network:** unit/integration tests never hit the public internet. Use local containers, in-memory fakes, or recorded fixtures.
- **Environment:** no reliance on local machine TZ, locale, file paths, env vars — set them explicitly in the test.
- **Concurrency:** use deterministic schedulers (`runTest`/`TestDispatcher` in Kotlin, `-race` in Go) and explicit synchronization.

## Test doubles taxonomy (Meszaros)

| Double | What it does | Use for |
|---|---|---|
| Dummy | passed but never used | filling parameter lists |
| Stub | returns canned answers | driving the SUT down a path |
| Spy | stub that records calls | verifying an outgoing side effect |
| Mock | pre-programmed expectations, verifies itself | strict interaction protocols (rare) |
| Fake | working lightweight implementation (in-memory repo, fake clock) | most boundary replacements — preferred |

## What to mock

- **Mock/fake:** things you do not own and that are slow/non-deterministic/costly at the boundary — network, payment providers, email, clock, randomness, filesystem when needed.
- **Don't mock:** your own pure logic, value objects, the unit under test, simple collaborators. Don't mock types you don't own directly — wrap them in an adapter you own and fake the adapter; cover the adapter with a narrow integration test.
- **Prefer real DB** in integration tests (Testcontainers, SQLite only if prod is SQLite). Mocked ORMs test nothing.
- A test that needs >3 mocks signals a design problem (too many dependencies) — fix the design.
- Over-mocking produces tests that pass when production breaks and break on every refactor.

## Coverage stance

- Coverage is a **floor detector, not a target**. Low coverage reveals untested areas; high coverage proves nothing about assertion quality.
- Follow the project threshold if one exists. Otherwise aim for all business rules and error paths covered, not a number.
- Every bug fix ships with a regression test that fails before the fix.
- Mutation testing (Stryker, mutmut, PIT) is the better signal for critical modules.

## Flaky-test rules

1. A flaky test is a failing test. Do not re-run until green and merge.
2. Quarantine immediately (skip with a linked ticket and owner), fix within a set window, or delete.
3. Never "fix" flakiness by adding sleeps or increasing timeouts blindly — find the race/shared state/time dependency.
4. Never add automatic retries to hide flakes in unit/integration suites. E2E retries only with flake reporting.
5. Common causes: shared mutable state, test order, real time, async not awaited, port collisions, external services, unseeded randomness, animation in UI tests.

## Agent rules

- Run the tests you wrote and the affected suite; report real results.
- Do not weaken, skip, or delete a failing test to make a change pass. If the test is wrong, say why and fix it explicitly.
- Do not edit snapshot files blindly; review the diff.
- Keep tests fast: unit suite in seconds.

## Sources

- Martin Fowler, "The Practical Test Pyramid": https://martinfowler.com/articles/practical-test-pyramid.html
- Kent C. Dodds, "The Testing Trophy and Testing Classifications": https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications
- Gerard Meszaros, *xUnit Test Patterns* (2007) — test double taxonomy.
- Martin Fowler, "Mocks Aren't Stubs": https://martinfowler.com/articles/mocksArentStubs.html
- Google Testing Blog, "Flaky Tests at Google": https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html
