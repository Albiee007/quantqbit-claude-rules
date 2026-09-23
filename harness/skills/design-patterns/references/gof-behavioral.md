# GoF Behavioral Patterns

Run the Decision Gate in [SKILL.md](../SKILL.md) first. Most behavioral patterns collapse to functions, closures, or exhaustive matching over union types in modern languages.

## Chain of Responsibility

**Intent:** Pass a request along a chain of handlers; each handles it or passes it on, decoupling sender from receivers.

**Forces:** ordered, configurable processing steps that can short-circuit (HTTP middleware, validation pipelines, fraud rules, approval escalation), assembled differently per context.

```ts
type Ctx = { req: Request; user?: User; tenantId?: string };
type Next = () => Promise<Response>;
type Middleware = (ctx: Ctx, next: Next) => Promise<Response>;

export function compose(stack: Middleware[], final: (ctx: Ctx) => Promise<Response>) {
  return (ctx: Ctx) => {
    const run = (i: number): Promise<Response> =>
      i === stack.length ? final(ctx) : stack[i](ctx, () => run(i + 1));
    return run(0);
  };
}

const authenticate: Middleware = async (ctx, next) => {
  ctx.user = await verifyBearer(ctx.req.headers.get("authorization"));
  return ctx.user ? next() : new Response("Unauthorized", { status: 401 });
};
const rateLimit: Middleware = async (ctx, next) =>
  (await limiter.allow(ctx.user!.id)) ? next() : new Response("Too Many Requests", { status: 429 });

const handler = compose([authenticate, rateLimit], ctx => listOrders(ctx.user!));
```

**Overuse smell:** a chain for 2 fixed checks; handler classes with `setNext()` wiring; chains where order dependencies are implicit and undocumented.

**Simpler alternative / refactor-away:** sequential guard clauses in one function; an array of validator functions reduced to errors.

**Kotlin/Python:** OkHttp/Ktor interceptors, Spring filters; Python WSGI/ASGI middleware or a list of callables.

## Command

**Intent:** Encapsulate a request as an object, allowing parameterization, queuing, logging, and undo.

**Forces:** operations must be queued, persisted, retried, audited, or undone; the invoker must not know the operation's details (job queues, undo stacks, CQRS commands).

```ts
type Command =
  | { type: "RenameProject"; projectId: string; name: string }
  | { type: "ArchiveProject"; projectId: string };

type Handler<C> = (cmd: C, deps: Deps) => Promise<void>;

const handlers: { [K in Command["type"]]: Handler<Extract<Command, { type: K }>> } = {
  RenameProject: async (c, d) => d.projects.rename(c.projectId, c.name),
  ArchiveProject: async (c, d) => d.projects.archive(c.projectId),
};

export async function dispatch(cmd: Command, deps: Deps) {
  await deps.audit.record(cmd);                       // serializable: log, queue, replay
  await (handlers[cmd.type] as Handler<Command>)(cmd, deps);
}

await queue.enqueue<Command>({ type: "ArchiveProject", projectId: "p_42" });
```

**Overuse smell:** `ICommand` classes with `execute()` for every button click; command bus in a small app where direct function calls suffice.

**Simpler alternative / refactor-away:** closures (`const undo = () => setName(prev)`); call the function directly unless you need to serialize/queue/undo.

**Kotlin/Python:** Kotlin `sealed interface Command` + `when`; lambdas `() -> Unit` for undo. Python dataclasses + dict of handlers, or plain callables.

## Interpreter

**Intent:** Define a representation for a grammar and an interpreter that evaluates sentences in it.

**Forces:** end users or config authors need a small, safe expression language (pricing rules, feature-flag targeting, search filters) and a data format can't express it.

```ts
type Expr =
  | { op: "eq"; field: string; value: string | number | boolean }
  | { op: "gt"; field: string; value: number }
  | { op: "in"; field: string; values: (string | number)[] }
  | { op: "and" | "or"; args: Expr[] }
  | { op: "not"; arg: Expr };

type Attrs = Record<string, string | number | boolean | undefined>;

export function evaluate(e: Expr, a: Attrs): boolean {
  switch (e.op) {
    case "eq": return a[e.field] === e.value;
    case "gt": return typeof a[e.field] === "number" && (a[e.field] as number) > e.value;
    case "in": return e.values.includes(a[e.field] as string | number);
    case "and": return e.args.every(x => evaluate(x, a));
    case "or": return e.args.some(x => evaluate(x, a));
    case "not": return !evaluate(e.arg, a);
  }
}

// flag targeting: country in [DE, FR] and plan != free
evaluate({ op: "and", args: [
  { op: "in", field: "country", values: ["DE", "FR"] },
  { op: "not", arg: { op: "eq", field: "plan", value: "free" } },
] }, { country: "DE", plan: "pro" });
```

**Overuse smell:** inventing a string DSL + parser when JSON rules suffice; growing the DSL into a general-purpose language; `eval` of user expressions (security).

**Simpler alternative / refactor-away:** plain code, config data + switch, or an existing engine (CEL, JSONLogic, SQL `WHERE` builders). Never `eval`.

**Kotlin/Python:** sealed classes + recursive `when`; Python dataclasses + `match`, or `ast.literal_eval` for literals only.

## Iterator

**Intent:** Access elements of an aggregate sequentially without exposing its underlying representation.

**Forces:** a custom data source (paginated API, tree, stream, file) should be consumed with standard loops lazily.

```ts
export async function* listAllInvoices(client: BillingClient, customerId: string) {
  let cursor: string | undefined;
  do {
    const page = await client.listInvoices({ customerId, cursor, limit: 100 });
    yield* page.items;
    cursor = page.nextCursor;
  } while (cursor);
}

let overdueCents = 0;
for await (const inv of listAllInvoices(client, "cus_123")) {
  if (inv.status === "overdue") overdueCents += inv.amountCents;
}
```

**Overuse smell:** hand-written `hasNext()/next()` classes over arrays; custom iterator interfaces duplicating the language protocol.

**Simpler alternative / refactor-away:** built-in collections and their methods; generators.

**Kotlin/Python:** Kotlin `sequence { yield(...) }` / `flow { emit(...) }` for async; Python generators / async generators. Go 1.23+ `iter.Seq`.

## Mediator

**Intent:** Define an object that encapsulates how a set of objects interact, so peers don't reference each other directly.

**Forces:** many-to-many interactions among peers become tangled (form fields enabling/disabling each other, multi-widget dashboards, chat rooms, air-traffic-style coordination).

```ts
type Field = "country" | "state" | "zip" | "shippingMethod";
type FormState = Record<Field, string> & { enabled: Record<Field, boolean>; options: { shippingMethod: string[] } };

// The mediator: a single reducer owns cross-field rules; fields only emit changes.
export function addressFormMediator(s: FormState, changed: Field, value: string): FormState {
  const next: FormState = { ...s, [changed]: value, enabled: { ...s.enabled }, options: { ...s.options } };
  if (changed === "country") {
    next.enabled.state = value === "US" || value === "CA";
    if (!next.enabled.state) next.state = "";
    next.options.shippingMethod = value === "US" ? ["ground", "express"] : ["international"];
    if (!next.options.shippingMethod.includes(next.shippingMethod)) next.shippingMethod = next.options.shippingMethod[0];
  }
  if (changed === "zip") next.enabled.shippingMethod = /^\d{5}$/.test(value) || next.country !== "US";
  return next;
}
```

**Overuse smell:** a mediator between 2 components; mediator becomes a god object containing all business logic; generic "mediator library" dispatching every call in a small app.

**Simpler alternative / refactor-away:** lift state to the common parent (React/Compose state hoisting); direct calls between a few collaborators.

**Kotlin/Python:** a ViewModel commonly acts as mediator for its screen; Python a controller object.

## Memento

**Intent:** Capture and externalize an object's internal state so it can be restored later, without violating encapsulation.

**Forces:** undo/redo, draft autosave, snapshot/rollback of editor or game state.

```ts
export class History<S> {
  private past: S[] = [];
  private future: S[] = [];
  constructor(private present: S, private limit = 100) {}

  get current(): S { return this.present; }
  apply(next: S) {
    this.past.push(this.present);
    if (this.past.length > this.limit) this.past.shift();
    this.present = next;
    this.future = [];
  }
  undo() { const prev = this.past.pop(); if (prev !== undefined) { this.future.push(this.present); this.present = prev; } }
  redo() { const nxt = this.future.pop(); if (nxt !== undefined) { this.past.push(this.present); this.present = nxt; } }
}

// With immutable state, the snapshot *is* the state:
const doc = new History<Readonly<EditorState>>(initialState);
doc.apply({ ...doc.current, title: "Q3 plan" });
doc.undo();
```

**Overuse smell:** Originator/Caretaker/Memento classes when state is already immutable; snapshots of huge state without limits (memory).

**Simpler alternative / refactor-away:** keep previous immutable values; store diffs/commands for large state.

**Kotlin/Python:** immutable `data class` snapshots in a list; `@Parcelize`/`SavedStateHandle` for Android process death. Python frozen dataclasses or `copy.deepcopy`.

## Observer

**Intent:** Define a one-to-many dependency so that when one object changes state, all dependents are notified.

**Forces:** multiple, independently developed consumers react to changes (UI bindings, domain events inside a process, cache invalidation) and the producer must not know them.

```ts
type Events = {
  "order.placed": { orderId: string; customerId: string; totalCents: number };
  "order.cancelled": { orderId: string; reason: string };
};

export class TypedEmitter<E extends Record<string, unknown>> {
  private handlers: { [K in keyof E]?: Set<(p: E[K]) => void> } = {};
  on<K extends keyof E>(event: K, fn: (p: E[K]) => void): () => void {
    (this.handlers[event] ??= new Set()).add(fn);
    return () => this.handlers[event]?.delete(fn);           // unsubscribe
  }
  emit<K extends keyof E>(event: K, payload: E[K]) {
    this.handlers[event]?.forEach(fn => {
      try { fn(payload); } catch (err) { logger.error({ err, event }, "listener failed"); }
    });
  }
}

const bus = new TypedEmitter<Events>();
const off = bus.on("order.placed", e => analytics.track("purchase", e));
```

**Overuse smell:** event spaghetti — control flow you can't follow with "go to definition"; events used for request/response; forgotten unsubscribes (leaks); one listener that could be a direct call.

**Simpler alternative / refactor-away:** direct function call or callback param when there is one known consumer; framework reactivity (signals, React state, Compose state).

**Kotlin/Python:** `StateFlow`/`SharedFlow`; LiveData in legacy Android. Python callback lists, `blinker` signals, or `asyncio.Queue`.

## State

**Intent:** Allow an object to alter its behavior when its internal state changes; transitions are explicit.

**Forces:** a lifecycle with several states where allowed operations differ per state and illegal transitions must be impossible (orders, subscriptions, connections, document workflows).

```ts
type Subscription =
  | { status: "trialing"; trialEndsAt: Date }
  | { status: "active"; renewsAt: Date }
  | { status: "past_due"; since: Date; retries: number }
  | { status: "canceled"; canceledAt: Date };

type Event = { type: "PAYMENT_SUCCEEDED"; periodEnd: Date } | { type: "PAYMENT_FAILED"; at: Date } | { type: "CANCEL"; at: Date };

export function transition(s: Subscription, e: Event): Subscription {
  switch (s.status) {
    case "trialing":
    case "active":
      if (e.type === "PAYMENT_SUCCEEDED") return { status: "active", renewsAt: e.periodEnd };
      if (e.type === "PAYMENT_FAILED") return { status: "past_due", since: e.at, retries: 0 };
      return { status: "canceled", canceledAt: e.at };
    case "past_due":
      if (e.type === "PAYMENT_SUCCEEDED") return { status: "active", renewsAt: e.periodEnd };
      if (e.type === "PAYMENT_FAILED") return s.retries >= 3 ? { status: "canceled", canceledAt: e.at } : { ...s, retries: s.retries + 1 };
      return { status: "canceled", canceledAt: e.at };
    case "canceled":
      throw new InvalidTransitionError(s.status, e.type);
  }
}
```

**Overuse smell:** a State class per state for 2-3 states with one operation; state classes that all share most code.

**Simpler alternative / refactor-away:** enum + `switch` (above is the functional State pattern); a transition table `Record<Status, Partial<Record<EventType, Status>>>`; XState-like libraries for complex UI flows.

**Kotlin/Python:** sealed classes + exhaustive `when`; Python `Enum` + dict of allowed transitions, or `match`.

## Strategy

**Intent:** Define a family of algorithms, encapsulate each, and make them interchangeable at runtime.

**Forces:** ≥ 3 algorithms chosen at runtime by config, tenant, or input (pricing rules, tax calculation per region, ranking models, compression).

```ts
type TaxStrategy = (net: number, ctx: { country: string; category: string }) => number;

const euVat: TaxStrategy = (net, { country }) => net * (VAT_RATES[country] ?? 0);
const usSalesTax: TaxStrategy = (net, { category }) => (category === "grocery" ? 0 : net * 0.07);
const noTax: TaxStrategy = () => 0;

const taxByRegion: Record<Region, TaxStrategy> = { EU: euVat, US: usSalesTax, EXEMPT: noTax };

export function priceWithTax(net: number, region: Region, ctx: { country: string; category: string }) {
  return net + taxByRegion[region](net, ctx);
}
```

**Overuse smell:** `IStrategy` interface + `StrategyContext` class + one implementation; strategies selected once at compile time.

**Simpler alternative / refactor-away:** a function parameter; a `switch` for 2 cases; a map of functions (above) instead of classes.

**Kotlin/Python:** function types `(Money) -> Money`, `enum class` with abstract method or lambda property; Python functions in a dict.

## Template Method

**Intent:** Define the skeleton of an algorithm in a base operation, deferring some steps to subclasses without changing the structure.

**Forces:** a fixed sequence with invariant steps (logging, transactions, locking, retries) where only a few steps vary across ≥ 3 variants (import jobs, ETL, report generation).

```ts
type ImportSteps<Raw, Row> = {
  name: string;
  fetch: () => AsyncIterable<Raw>;
  parse: (raw: Raw) => Row | null;          // null = skip invalid
  save: (batch: Row[]) => Promise<void>;
};

export async function runImport<Raw, Row>(s: ImportSteps<Raw, Row>, log: Logger, batchSize = 500) {
  const started = Date.now();
  let batch: Row[] = [], saved = 0, skipped = 0;
  for await (const raw of s.fetch()) {
    const row = s.parse(raw);
    if (!row) { skipped++; continue; }
    batch.push(row);
    if (batch.length >= batchSize) { await s.save(batch); saved += batch.length; batch = []; }
  }
  if (batch.length) { await s.save(batch); saved += batch.length; }
  log.info({ job: s.name, saved, skipped, ms: Date.now() - started }, "import.completed");
}
```

**Overuse smell:** deep abstract base classes with many hooks, most overridden as no-ops; subclasses that must call `super` in the right order.

**Simpler alternative / refactor-away:** a function that takes step functions (above) — composition instead of inheritance.

**Kotlin/Python:** higher-order function with lambda params, or interface with default methods; Python function taking callables, or ABC only if a framework demands it.

## Visitor

**Intent:** Represent an operation to be performed on elements of an object structure, letting you add operations without changing element classes.

**Forces:** a *stable, closed* set of node types (AST, document model, IR) and a growing set of operations (render, validate, optimize, export).

```ts
type Node =
  | { kind: "text"; value: string }
  | { kind: "bold"; children: Node[] }
  | { kind: "link"; href: string; children: Node[] };

// Each "visitor" is a function with an exhaustive switch — adding a Node kind breaks compilation everywhere it matters.
export function toHtml(n: Node): string {
  switch (n.kind) {
    case "text": return escapeHtml(n.value);
    case "bold": return `<strong>${n.children.map(toHtml).join("")}</strong>`;
    case "link": return `<a href="${escapeAttr(safeUrl(n.href))}">${n.children.map(toHtml).join("")}</a>`;
  }
}

export function toPlainText(n: Node): string {
  switch (n.kind) {
    case "text": return n.value;
    case "bold": case "link": return n.children.map(toPlainText).join("");
  }
}
```

**Overuse smell:** double-dispatch `accept(visitor)` boilerplate in languages with pattern matching; Visitor on a hierarchy whose types change often (every new type touches every visitor).

**Simpler alternative / refactor-away:** discriminated unions + exhaustive switch (above); keep classic Visitor only in languages without sum types or when a library requires it.

**Kotlin/Python:** `sealed interface` + exhaustive `when`; Python 3.10+ `match` with dataclasses, `functools.singledispatch`.

## Sources

- Gamma et al., *Design Patterns* (1994), ch. 5.
- Refactoring.Guru, Behavioral Patterns: https://refactoring.guru/design-patterns/behavioral-patterns
- Peter Norvig, "Design Patterns in Dynamic Languages" (1996): https://norvig.com/design-patterns/
- TypeScript Handbook, Narrowing / discriminated unions: https://www.typescriptlang.org/docs/handbook/2/narrowing.html
