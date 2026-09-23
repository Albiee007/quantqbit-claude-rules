# Anti-patterns of Over- (and Under-) Engineering

Each entry: **Smell** (how to spot it) → **Fix**. Use in self-review and code review.

## Speculative generality
- **Smell:** parameters, hooks, abstract classes, plugin points, or config options with no current caller or only one; comments like "for future flexibility"; generic type params always instantiated with one type.
- **Fix:** delete unused flexibility; inline single-use abstractions; re-introduce when a real second/third case appears (YAGNI, rule of three).

## Factory for a single product
- **Smell:** `UserFactory.create()` that returns `new User(...)`; factory + interface + impl for one concrete type.
- **Fix:** call the constructor. If construction is complex, a named function (`userFromSignup(dto)`) is enough.

## Interface with one implementation "for testing"
- **Smell:** `IFooService` + `FooServiceImpl`, never another implementation; interfaces mirror the class 1:1; mocks for every internal class.
- **Fix:** depend on the concrete class for internal collaborators. Put interfaces only at real I/O boundaries (ports) where fakes pay off. In TS/Go use structural typing at the consumer (`Pick<Foo, "bar">`, small consumer-side interface). Test with fakes of the boundary, not mocks of internals.

## Anemic domain model vs god service
- **Smell (anemic):** entities are bags of getters/setters; all rules live in `XService` classes that mutate them; invariants checked (or forgotten) in many places.
- **Smell (god service):** `OrderService` with 3,000 lines and 60 methods; every feature edits it.
- **Fix:** move invariants and behavior next to the data they protect (`order.addLine()`, `account.withdraw()` validating balance); split services by use case/feature. Keep application services thin: load → call domain → save → publish.

## Premature microservices
- **Smell:** multiple deployables for a small team/product; services sharing a database; synchronous call chains across services for one request; distributed transactions for simple workflows; most changes require coordinated deploys.
- **Fix:** modular monolith with enforced module boundaries (feature slices, public APIs per module, lint rules on imports). Extract a service only for a proven need: independent scaling, isolation, different release cadence, team autonomy.

## Over-abstracted wrappers of framework APIs
- **Smell:** `MyHttpClient` wrapping `fetch`/`axios` 1:1; `DatabaseHelper` re-exposing the ORM; custom `Logger` wrapping the logger with identical methods; "in case we switch frameworks".
- **Fix:** use the framework directly in adapters. Wrap only to add real value (auth headers, retries, error mapping, domain-shaped API) or to isolate an unstable/vendor API behind a domain port.

## Deep inheritance
- **Smell:** > 2 levels of class inheritance; base classes with flags controlling subclass behavior; `super` call order matters; "fragile base class" breakage; `BaseController`/`BaseService` with grab-bag utilities.
- **Fix:** composition and delegation; pass behavior as functions; extract utilities into modules; use interfaces/traits for shared contracts. Inherit only for true is-a with LSP-safe contracts.

## Singletons as global state
- **Smell:** `Config.getInstance()`, `Db.instance`, mutable module-level state used across the codebase; tests interfere with each other; hidden initialization order.
- **Fix:** create instances in the composition root and inject them. Keep module-level values immutable. For caches/registries, pass an instance.

## Event spaghetti
- **Smell:** can't find who reacts to an event without global search; events triggering events triggering events; events used to request data and wait for an answer; ordering bugs; no schema for payloads.
- **Fix:** use direct calls for in-process request/response and single known consumers. Keep events for genuine fan-out, named in past tense (`order.placed`), with typed/versioned payloads and a documented list of consumers. Prefer orchestration for multi-step workflows.

## Config-driven everything
- **Smell:** business logic encoded in YAML/JSON/DB flags; "soft-coded" rules nobody can test; feature flags never removed; a homemade DSL grows loops and conditionals.
- **Fix:** keep logic in code (typed, tested, reviewed). Config for environment-varying values (URLs, limits, credentials) and genuine operator-tunable knobs. Remove feature flags after rollout. If users truly need rules, use a bounded, validated rule format or an existing engine.

## Other frequent smells

| Smell | Fix |
|---|---|
| Layers that only pass through (controller → service → repo with identical signatures) | Collapse the empty layer; add it back when logic appears |
| `utils`/`helpers`/`common` dumping ground | Move functions next to their callers or into capability-named modules |
| Generic `Repository<T>` with every CRUD method for every entity | Specific methods per aggregate, only those used |
| DTO ↔ entity ↔ model mappers identical at every layer | Share a type until shapes actually diverge |
| Boolean/mode parameters switching whole behaviors (`save(x, true, false)`) | Separate functions or an options object with named fields |
| Reinvented standard library (custom `deepEqual`, date math, retry loops everywhere) | Use stdlib or one well-maintained dependency |
| Premature caching | Measure first; see coding-standards performance reference |
| Under-engineering: copy-pasted business rule in 4 places | Now the rule of three is met — extract one function/module |

## Sources

- Martin Fowler, *Refactoring* 2nd ed. (2018), "Bad Smells in Code" (Speculative Generality, Shotgun Surgery): https://refactoring.com/catalog/
- Martin Fowler, "AnemicDomainModel": https://martinfowler.com/bliki/AnemicDomainModel.html
- Martin Fowler, "MonolithFirst": https://martinfowler.com/bliki/MonolithFirst.html
- Sandi Metz, "The Wrong Abstraction": https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction
- Martin Fowler, "What do you mean by 'Event-Driven'?": https://martinfowler.com/articles/201701-event-driven.html
- Refactoring.Guru, Code Smells: https://refactoring.guru/refactoring/smells
