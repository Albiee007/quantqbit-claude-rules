---
name: design-patterns
description: Decision gate and catalog for design patterns and abstractions — all 23 GoF patterns, architectural patterns (hexagonal, clean, repository, CQRS, saga, outbox, circuit breaker, etc.), language idioms that replace patterns, and anti-patterns of over-engineering. Use when about to introduce a pattern, interface, base class, factory, new layer, module boundary, or framework-like indirection; when a user or reviewer names a pattern; when refactoring duplicated or branching code; or when judging whether existing abstractions are over-engineered.
---

# Design Patterns

Patterns are named solutions to **recurring, present** forces. Applied without the force, they are pure cost: more types, more files, more indirection, harder debugging. Default answer: **write the simple version.**

## Decision Gate (mandatory before adding any pattern, abstraction, or layer)

Answer all five, concretely:

1. **Force:** What concrete, *current* variation or pressure exists? Name the actual cases in the code or requirement today. Hypothetical futures ("we might add another provider") do not count.
2. **Rule of three:** Are there ≥ 3 real cases, or an explicit external requirement (contract, regulation, plugin API, multiple teams)?
3. **Simplest alternative:** What is the plain version — function, parameter, `if`/`switch`/`when`, map of functions, composition, a language feature — and **why is it insufficient**?
4. **Cost vs benefit:** How many new types/files/levels of indirection? What exactly gets easier (testing, adding case N+1, isolating a dependency)?
5. **Reversibility:** Can it be removed or inlined cheaply if the force disappears?

**If any answer is weak → do NOT apply the pattern. Write the simple version.** Revisit when the third case arrives.

When you *do* add a pattern, **state the five gate answers** in your plan and in the PR/commit description. Example:
> Gate: (1) 3 payment providers live (Stripe, Adyen, PayPal) with distinct auth/retry; (2) 3 cases + contract for a 4th in Q3; (3) `switch` duplicated in 4 call sites already; (4) +1 interface, +3 adapters, removes 4 switches; (5) adapters are thin, inlinable.

Also check [anti-patterns](references/anti-patterns.md) before and during review.

## GoF patterns at a glance

| Pattern | Intent | Use when | Don't use when | Simpler alternative |
|---|---|---|---|---|
| **Factory Method** | Defer which class to instantiate to subclasses/callers | Framework must create caller-defined types | One product type | Constructor, or pass a creator function |
| **Abstract Factory** | Create families of related objects consistently | ≥ 2 real families that must not mix (e.g. platform UI kits) | One family | Module of functions per family; DI config |
| **Builder** | Construct complex objects step by step | Many optional parts, validation at build, immutable result | ≤ ~5 params | Named/default args, object literal, `copy()` |
| **Prototype** | Create by cloning an existing instance | Expensive init; runtime-configured templates | Cheap construction | `structuredClone`, spread, `copy()` |
| **Singleton** | One instance, global access | Truly one resource *and* DI unavailable | Anything testable/stateful | Module instance, DI-scoped single instance |
| **Adapter** | Convert an interface to one clients expect | Integrating third-party/legacy API behind your port | You own both sides | Change the call site; one wrapper function |
| **Bridge** | Vary abstraction and implementation independently | Two orthogonal dimensions each with ≥ 2 variants | One dimension varies | Composition + a function param |
| **Composite** | Treat trees of objects uniformly | Recursive part-whole structures (UI, filesystems, ASTs) | Flat lists | Recursive function over a union type |
| **Decorator** | Add responsibilities by wrapping | Stackable cross-cutting concerns (retry, cache, metrics) | One fixed extra behavior | Higher-order function; middleware |
| **Facade** | Simple interface over a subsystem | Callers repeat the same multi-step subsystem choreography | Wrapping a single call | A plain module/function |
| **Flyweight** | Share intrinsic state among many objects | Measured memory pressure from millions of similar objects | No profile shows the problem | Interning, IDs + lookup table |
| **Proxy** | Control access to an object (lazy, remote, auth, cache) | Transparent access control is needed at the object boundary | Plain delegation suffices | Decorator/HOF; framework interceptors |
| **Chain of Responsibility** | Pass a request along handlers until handled | Ordered, configurable pipeline (middleware, validators) | Fixed 2-3 checks | Sequential `if`s; array of functions |
| **Command** | Encapsulate a request as an object | Undo/redo, queuing, persistence, audit of operations | Just calling later | Closure/lambda; data record + handler |
| **Interpreter** | Evaluate sentences of a small grammar | A real DSL/rule language defined by users | Config you can express as data | JSON/YAML + switch; an existing parser/engine |
| **Iterator** | Sequential access without exposing structure | Custom traversal of a custom structure | Built-in collections | Language iterators/generators/sequences |
| **Mediator** | Centralize complex interactions between peers | Many-to-many chatter among components | 2-3 collaborators | Direct calls; parent component owns state |
| **Memento** | Capture/restore state without breaking encapsulation | Undo, snapshots, drafts | State is already immutable data | Keep previous immutable values |
| **Observer** | Notify dependents of state changes | Many unknown subscribers; decoupled UI updates | One known listener | Callback param; framework reactivity |
| **State** | Behavior changes with internal state | Many states × many operations, transitions enforced | 2-3 states, few ops | Enum + `switch`; state-machine table |
| **Strategy** | Swap algorithms at runtime | ≥ 3 interchangeable algorithms selected at runtime | One algorithm, or chosen at compile time | Function parameter; map of functions |
| **Template Method** | Fixed skeleton with overridable steps | Framework hooks with invariant ordering | Few steps vary | Function taking step callbacks |
| **Visitor** | Add operations over a stable type hierarchy | Many operations over a *closed* AST-like hierarchy | Types change often | Exhaustive `switch`/`when`/`match` on a sealed union |

Details, examples, overuse smells, refactor-away paths: [creational](references/gof-creational.md), [structural](references/gof-structural.md), [behavioral](references/gof-behavioral.md).

## Architectural patterns at a glance

| Pattern | Use when | Don't use when |
|---|---|---|
| Layered | Most CRUD-ish apps; clear presentation/domain/data split | Layers become pass-through boilerplate |
| Hexagonal (ports & adapters) | Domain logic valuable; multiple I/O adapters or heavy testing needs | Thin CRUD over one DB |
| Clean Architecture | Long-lived, rule-heavy domain; many delivery mechanisms | Small services, prototypes |
| Feature/vertical slices | Growing codebase; teams own features | Tiny apps (one module is fine) |
| Repository | Domain needs collection-like persistence abstraction | ORM already gives it and there is one store |
| Unit of Work | Multiple aggregates change atomically | Single-row writes; ORM session already does it |
| Service Layer | Several entry points (HTTP, CLI, jobs) share use cases | One controller, one use |
| Dependency Injection | Always via constructor/params | Containers before manual wiring hurts |
| MVC / MVVM / MVI | UI state management per platform convention | Fighting the framework's idiom |
| CQRS ⚠ | Read and write models truly diverge in shape/scale | Same model serves both fine |
| Event Sourcing ⚠⚠ | Audit/temporal queries are core requirements | You just want an audit log |
| Saga | Multi-service business transaction needs compensation | One DB transaction can do it |
| Transactional Outbox | Must publish events reliably with a DB write | No messaging, or broker supports transactions with your DB |
| Circuit Breaker | Remote dependency fails in ways that cascade | In-process calls |
| Retry + backoff + jitter | Transient failures of idempotent ops | Non-idempotent ops without keys; 4xx |
| Bulkhead | One dependency can exhaust shared pools | Single-dependency service |
| Strangler Fig | Incremental legacy replacement | Greenfield |
| BFF | Distinct clients need different API shapes | One client |
| Pub/Sub | Fan-out to independent consumers | Request/response needed |
| Specification | Composable business rules reused in queries and validation | One or two predicates |
| Idempotency keys | Client retries of side-effecting requests (payments, orders) | Naturally idempotent PUT/DELETE |

Details and sketches: [architectural](references/architectural.md).

## Language idioms that replace patterns

| Pattern | TypeScript/JS | Kotlin | Python | Go |
|---|---|---|---|---|
| Singleton | module-level instance (ES module is cached) | `object` (stateless only) or DI `@Singleton` | module-level instance | package-level var set in `main` |
| Strategy | function parameter / `Record<K, Fn>` | lambda / function type | function / dict of functions | func value / map of funcs |
| Command | closure; data object + handler | lambda; `sealed` command + `when` | callable / dataclass | func / struct + method |
| Iterator | `for...of`, generators, iterables | `Sequence`, `Iterable`, `sequence {}` | generators, `__iter__` | `range`, `iter.Seq` (1.23+) |
| Observer | `EventTarget`/`EventEmitter`, signals, RxJS | `Flow`/`StateFlow`, `SharedFlow` | callbacks, blinker, asyncio queues | channels, callbacks |
| Builder | object literal with defaults | named + default args, `copy()`, DSL builders | kwargs with defaults, `dataclasses.replace` | functional options / config struct |
| Decorator | higher-order function, middleware | delegation `by`, extension wrapper | `@decorator` functions | handler wrapping (`func(h) h`) |
| Template Method | pass hook functions | higher-order functions / default interface methods | pass callables | pass funcs / small interface |
| Visitor | discriminated union + exhaustive `switch` | `sealed` + exhaustive `when` | `match` statement (3.10+) | type switch |
| Prototype | spread / `structuredClone` | `data class copy()` | `copy.copy`/`replace` | struct value copy |
| Factory | plain function returning an object | top-level function / companion `invoke` | function / `classmethod` | `NewX(...)` constructor func |
| State | union type + reducer | sealed class + `when` | Enum + dict transitions | const iota + switch |

## Workflow

1. Write the straightforward version first (or identify the existing code).
2. If you feel a pattern "pulling", run the Decision Gate. Record answers.
3. Prefer the language idiom column above over the classic OO form.
4. Keep the pattern local; don't spread it across the codebase "for consistency" without forces there too.
5. In review, flag patterns without gate answers and propose the simpler alternative.

## References

- [gof-creational](references/gof-creational.md) — Factory Method, Abstract Factory, Builder, Prototype, Singleton
- [gof-structural](references/gof-structural.md) — Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy
- [gof-behavioral](references/gof-behavioral.md) — Chain of Responsibility, Command, Interpreter, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor
- [architectural](references/architectural.md) — layering, hexagonal, clean, slices, persistence, distributed-systems and resilience patterns
- [anti-patterns](references/anti-patterns.md) — over-engineering smells and fixes
