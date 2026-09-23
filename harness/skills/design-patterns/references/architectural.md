# Architectural Patterns

Run the Decision Gate in [SKILL.md](../SKILL.md) first. Architecture changes are the most expensive to reverse — follow the existing architecture unless a task explicitly asks to change it. ⚠ = high complexity cost; demand strong justification.

## Structure

### Layered
- **Intent:** separate presentation, application/domain, and data access; dependencies point downward.
- **When:** most business apps; teams familiar with it; moderate domain complexity.
- **When not:** layers that only pass data through (controller → service → repo with no logic) — collapse them.
- **Sketch:** `routes/ → services/ → repositories/ → db`. No layer skipping upward; no DB types in routes.

### Hexagonal (Ports & Adapters)
- **Intent:** domain core defines ports (interfaces); adapters implement them for HTTP, DB, queues, vendors.
- **When:** valuable domain logic; multiple adapters per port (prod/test, vendor A/B); want fast tests without infra.
- **When not:** thin CRUD over one database; the ports would mirror the ORM 1:1.
- **Sketch:** `domain/ports/PaymentGateway.ts` ← `adapters/stripe/StripeGateway.ts`; driving adapters (HTTP handlers) call use cases; wiring in `main`.

### Clean Architecture
- **Intent:** concentric layers (entities → use cases → interface adapters → frameworks); dependency rule points inward.
- **When:** long-lived systems with complex rules, multiple delivery mechanisms, framework independence required.
- **When not:** small services, prototypes, apps whose value is mostly UI/framework integration. Mapping between 4 layers of DTOs is real cost.
- **Sketch:** `entities/`, `usecases/` (one class/function per use case, input/output models), `adapters/`, `infrastructure/`. Inner layers import nothing outward.

### Feature-sliced / Vertical-slice modules
- **Intent:** organize by feature (`orders/`, `billing/`) with each slice owning its UI/handlers, logic, and data access.
- **When:** growing codebases; features change independently; teams own features.
- **When not:** very small apps. Don't create cross-slice imports into internals — expose a small public API per slice.
- **Sketch:** `features/orders/{api.ts, handlers.ts, service.ts, repo.ts, index.ts}`; `shared/` only for truly generic code.

## Persistence & application

### Repository
- **Intent:** collection-like interface for aggregates, hiding persistence details from the domain.
- **When:** domain logic should not know the ORM/SQL; aggregates are loaded/saved as units; need in-memory fakes for tests.
- **When not:** the ORM already provides a clean repository and there is one store; generic `Repository<T>` with 20 methods — prefer specific methods (`findActiveByEmail`).
- **Sketch:** `interface OrderRepo { get(id): Promise<Order>; save(o: Order): Promise<void> }` + `PgOrderRepo`.

### Unit of Work
- **Intent:** track changes during a business transaction and commit them atomically.
- **When:** a use case changes multiple aggregates/tables that must commit together.
- **When not:** ORMs with sessions/`DbContext` already implement it — use theirs; single-row writes.
- **Sketch:** `await db.transaction(async tx => { await orders.save(o, tx); await outbox.add(evt, tx); })`.

### Service Layer
- **Intent:** application boundary exposing use cases; coordinates domain objects, transactions, authorization.
- **When:** several entry points (HTTP, CLI, jobs, consumers) share use cases.
- **When not:** it becomes a god service holding all logic while entities are anemic — push invariants into domain types.
- **Sketch:** `placeOrder(cmd, deps)`; handlers parse input → call use case → map result.

### Dependency Injection
- **Intent:** components receive dependencies instead of constructing them.
- **When:** always, in its simplest form: **constructor or parameter injection**, wired in a composition root (`main`).
- **When not (containers):** don't add a DI container/framework until manual wiring is genuinely painful (dozens of graphs, scoping needs) — or the platform standard (Spring, Hilt, NestJS) is already in use; then follow it.
- **Sketch:** `const svc = new OrderService(new PgOrderRepo(pool), stripeGateway, clock)`.

### MVC / MVVM / MVI (UI)
- **Intent:** separate UI rendering from state and logic. MVC: controller mediates; MVVM: view binds to observable ViewModel state; MVI: unidirectional — intents → reducer → immutable state → view.
- **When:** follow the platform idiom: Android → MVVM/UDF with ViewModel + StateFlow; React/RN → components + hooks/stores (MVI-like with reducers); server-rendered web → MVC.
- **When not:** don't impose MVI boilerplate on simple screens; don't fight the framework.
- **Sketch:** `data class UiState(...)`; `ViewModel` exposes `StateFlow<UiState>` and `fun onEvent(e: UiEvent)`.

### CQRS ⚠
- **Intent:** separate write model (commands, invariants) from read model(s) (queries, denormalized views).
- **When:** read and write shapes/scale diverge strongly (complex reporting, high read fan-out), often with async projections.
- **When not:** CRUD where one model serves both — CQRS adds eventual consistency, duplication, and sync bugs. A "light" form (separate query functions/read SQL in the same DB) is usually enough.
- **Sketch:** `commands/placeOrder.ts` writes `orders`; projector updates `order_summaries`; `queries/listOrders.ts` reads the view.

### Event Sourcing ⚠⚠
- **Intent:** persist state as an append-only sequence of events; current state is a fold over events.
- **When:** full history/temporal queries/audit are core business requirements (ledgers, compliance) and the team has experience.
- **When not:** you want an audit trail (use an audit table/CDC); CRUD domains; teams new to it. Costs: event versioning/upcasting, projections, snapshots, GDPR erasure, rebuild times.
- **Sketch:** `events(stream_id, version, type, payload)` with unique `(stream_id, version)`; `state = events.reduce(apply, initial)`.

## Distributed systems & integration

### Saga
- **Intent:** manage a business transaction across services as a sequence of local transactions with compensating actions.
- **When:** a workflow spans services/DBs that cannot share a transaction (order → payment → shipping).
- **When not:** everything lives in one DB — use a transaction. Prefer orchestration (explicit coordinator/workflow engine like Temporal) over choreography once > 3 steps.
- **Sketch:** `reserveStock → chargePayment → createShipment`; on failure run `refund → releaseStock`. Every step and compensation idempotent.

### Transactional Outbox
- **Intent:** write domain changes and outgoing events in the same DB transaction; a relay publishes events afterward.
- **When:** you must not lose or phantom-publish events when saving state (dual-write problem).
- **When not:** no messaging; or CDC (Debezium) already streams your tables.
- **Sketch:** `tx: INSERT order; INSERT outbox(id, topic, payload)`; relay polls `outbox WHERE published_at IS NULL`, publishes, marks published. Consumers dedupe by event id (at-least-once).

### Circuit Breaker
- **Intent:** stop calling a failing dependency for a cool-down period; fail fast instead of piling up.
- **When:** remote dependencies whose outages would exhaust threads/connections or cascade.
- **When not:** in-process calls; when a timeout + limited retry is enough for low-traffic paths.
- **Sketch:** states closed → open (after N failures/error rate) → half-open (trial request) → closed. Use a library (opossum, resilience4j, Polly, gobreaker); pair with fallback.

### Retry with backoff + jitter
- **Intent:** recover from transient failures without synchronized retry storms.
- **When:** idempotent operations failing with timeouts/5xx/429/connection resets.
- **When not:** non-idempotent ops without idempotency keys; 4xx; retries at multiple layers.
- **Sketch:** `delay = random(0, min(capMs, baseMs * 2 ** attempt))`; max 3-5 attempts; honor `Retry-After`; respect deadline/cancellation.

### Bulkhead
- **Intent:** isolate resources (pools, threads, queues) per dependency or tenant so one failure can't sink everything.
- **When:** one slow dependency or noisy tenant can exhaust a shared pool.
- **When not:** single-dependency services with ample capacity.
- **Sketch:** separate HTTP agents/connection pools with max sockets per upstream; per-tenant concurrency limits; separate worker queues.

### Strangler Fig
- **Intent:** incrementally replace a legacy system by routing slices of functionality to the new one.
- **When:** rewriting legacy with production traffic; big-bang rewrite too risky.
- **When not:** greenfield; tiny systems where a rewrite is days of work.
- **Sketch:** proxy/gateway routes `/billing/*` to new service, rest to legacy; migrate route by route; delete legacy code as routes move.

### BFF (Backend for Frontend)
- **Intent:** a dedicated backend per client type shaping APIs for that client's needs.
- **When:** web and mobile need different aggregation/payload shapes or release cadences; hide internal service topology.
- **When not:** single client; the BFF would duplicate business logic (keep BFFs thin: aggregation, auth translation, shaping).
- **Sketch:** `mobile-bff` calls `orders`, `catalog`, `profile` and returns one screen-shaped response.

### Pub/Sub
- **Intent:** publishers emit messages to topics; any number of subscribers consume independently.
- **When:** fan-out to independent consumers (notifications, analytics, search indexing); decoupled deploys.
- **When not:** caller needs a result (request/response); strict ordering across entities without partition keys; one consumer where a direct call is clearer.
- **Sketch:** `publish("order.placed", {eventId, orderId, ...})`; consumers idempotent, versioned schemas, dead-letter queues.

## Domain & API

### Specification
- **Intent:** encapsulate a business rule as a composable predicate usable for validation, selection, and query building.
- **When:** the same rules combine in many ways and must run both in memory and as DB queries.
- **When not:** one or two predicates — a function is enough.
- **Sketch:** `const eligible = and(isActive, not(isDelinquent), minTenureMonths(6)); eligible.isSatisfiedBy(c); eligible.toSql()`.

### Idempotency keys
- **Intent:** make side-effecting requests safe to retry by deduplicating on a client-supplied key.
- **When:** payments, order creation, any POST a client or queue may retry; webhook consumers.
- **When not:** naturally idempotent operations (PUT of full resource, DELETE by id) — though still dedupe webhooks.
- **Sketch:** `Idempotency-Key` header; table `(key, request_hash, status, response, created_at)` with unique key; on repeat: same hash → return stored response; different hash → 422; in progress → 409. Expire after 24h+.

## Sources

- Martin Fowler, *Patterns of Enterprise Application Architecture* (2002): https://martinfowler.com/eaaCatalog/
- Alistair Cockburn, Hexagonal Architecture: https://alistair.cockburn.us/hexagonal-architecture/
- Robert C. Martin, "The Clean Architecture": https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Jimmy Bogard, "Vertical Slice Architecture": https://www.jimmybogard.com/vertical-slice-architecture/
- Martin Fowler, CQRS: https://martinfowler.com/bliki/CQRS.html and Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html
- Chris Richardson, microservices.io patterns (Saga, Transactional Outbox): https://microservices.io/patterns/
- Microsoft Azure Architecture Center, Cloud Design Patterns (Circuit Breaker, Bulkhead, Retry, Strangler Fig, BFF): https://learn.microsoft.com/en-us/azure/architecture/patterns/
- Stripe API, Idempotent requests: https://docs.stripe.com/api/idempotent_requests
- Evans & Fowler, "Specifications": https://martinfowler.com/apsupp/spec.pdf
- Android app architecture guide: https://developer.android.com/topic/architecture
