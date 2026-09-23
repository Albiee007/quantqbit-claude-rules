# GoF Creational Patterns

Run the Decision Gate in [SKILL.md](../SKILL.md) first. In most modern code, a constructor or a plain function is the right "creational pattern".

## Factory Method

**Intent:** Define an interface for creating an object, but let subclasses (or a supplied function) decide which concrete class to instantiate.

**Forces:** a framework/library creates objects whose concrete type is chosen by its users; creation needs a hook that varies per context; construction logic (selection by config/input) is non-trivial and repeated.

```ts
interface Notifier { send(to: string, body: string): Promise<void> }

class EmailNotifier implements Notifier { async send(to: string, body: string) { /* SMTP */ } }
class SmsNotifier implements Notifier { async send(to: string, body: string) { /* Twilio */ } }
class PushNotifier implements Notifier { async send(to: string, body: string) { /* FCM */ } }

type Channel = "email" | "sms" | "push";

// Factory function: the idiomatic TS form of Factory Method
export function createNotifier(channel: Channel, cfg: AppConfig): Notifier {
  switch (channel) {
    case "email": return new EmailNotifier();
    case "sms": return new SmsNotifier();
    case "push": return new PushNotifier();
  }
}

// usage: user preference decides the product at runtime
const notifier = createNotifier(user.preferredChannel, config);
await notifier.send(user.contact, "Your order shipped");
```

**Overuse smell:** `XFactory` that only ever returns `new X()`; factory classes with a single `create` method and no selection logic; `FactoryFactory`.

**Simpler alternative / refactor-away:** call the constructor directly; pass a creator function (`makeClient: () => Client`) where a caller must control creation. Inline factories that have one product.

**Kotlin/Python:** Kotlin uses top-level functions or `companion object { operator fun invoke(...) }`; Python uses a plain function or `@classmethod` alternative constructors (`Date.from_iso(...)`).

## Abstract Factory

**Intent:** Provide an interface for creating families of related objects without specifying their concrete classes, guaranteeing products from one family are used together.

**Forces:** ≥ 2 real families exist today (e.g. cloud providers, UI themes/platforms, test vs prod infrastructure) and mixing products across families would be a bug.

```ts
interface Storage { put(key: string, data: Uint8Array): Promise<void> }
interface Queue { publish(topic: string, msg: unknown): Promise<void> }

interface CloudKit { storage(): Storage; queue(): Queue }

const awsKit = (region: string): CloudKit => ({
  storage: () => new S3Storage(region),
  queue: () => new SqsQueue(region),
});
const gcpKit = (project: string): CloudKit => ({
  storage: () => new GcsStorage(project),
  queue: () => new PubSubQueue(project),
});

export function bootstrap(kit: CloudKit) {
  const storage = kit.storage();
  const queue = kit.queue();          // always matching family
  return new ReportService(storage, queue);
}

const app = bootstrap(env.CLOUD === "gcp" ? gcpKit(env.GCP_PROJECT) : awsKit(env.AWS_REGION));
```

**Overuse smell:** one family only ("we might go multi-cloud"); abstract factory used where DI wiring in the composition root already chooses implementations.

**Simpler alternative / refactor-away:** wire concrete implementations once in the composition root (`main`). If there's one family, delete the kit and construct directly.

**Kotlin/Python:** a data class/record of constructor lambdas or DI modules (Hilt/Koin modules per flavor) fills this role; Python uses a module per family or a dict of callables.

## Builder

**Intent:** Separate the construction of a complex object from its representation, allowing step-by-step construction and validation before producing an (often immutable) result.

**Forces:** many optional parts; construction must be validated as a whole; the same process yields different representations; fluent incremental assembly (queries, HTTP requests, test data).

```ts
class HttpRequestBuilder {
  private headers = new Map<string, string>();
  private query = new URLSearchParams();
  private body?: string;
  constructor(private method: "GET" | "POST", private url: string) {}

  header(k: string, v: string) { this.headers.set(k, v); return this; }
  param(k: string, v: string) { this.query.append(k, v); return this; }
  json(data: unknown) { this.body = JSON.stringify(data); return this.header("content-type", "application/json"); }

  build(): Request {
    if (this.method === "GET" && this.body) throw new Error("GET cannot have a body");
    const qs = this.query.toString();
    return new Request(qs ? `${this.url}?${qs}` : this.url,
      { method: this.method, headers: Object.fromEntries(this.headers), body: this.body });
  }
}

const req = new HttpRequestBuilder("POST", "https://api.example.com/orders")
  .header("idempotency-key", key).json({ sku, qty }).build();
```

**Overuse smell:** builder for a class with 3-5 fields and no cross-field validation; builder that mirrors every setter with no logic; hand-written builders duplicated alongside data classes.

**Simpler alternative / refactor-away:** object literal parameter with defaults (`createUser({ name, role = "member" })`); test-data factories with overrides (`aUser({ role: "admin" })`).

**Kotlin/Python:** named + default arguments and `copy()` remove most builders; type-safe DSL builders (`buildList {}`, `apply {}`) for nested structures. Python: keyword arguments with defaults, `dataclasses.replace`.

## Prototype

**Intent:** Create new objects by copying an existing, pre-configured instance.

**Forces:** creation is expensive (parsing, remote config, large graphs) and copies differ slightly; users define templates at runtime (e.g. "duplicate this dashboard/campaign").

```ts
interface Dashboard {
  id: string; name: string; ownerId: string;
  widgets: { type: string; query: string; position: [number, number] }[];
  createdAt: Date;
}

export function duplicateDashboard(src: Dashboard, newOwnerId: string): Dashboard {
  const copy = structuredClone(src);         // deep copy: widgets not shared
  return {
    ...copy,
    id: crypto.randomUUID(),
    name: `${src.name} (copy)`,
    ownerId: newOwnerId,
    createdAt: new Date(),
  };
}

// templates chosen by users at runtime
const templates = await templateRepo.list();
const fresh = duplicateDashboard(templates[0], currentUser.id);
```

**Overuse smell:** `clone()` hierarchies with `Cloneable` interfaces for cheap objects; shallow copies silently sharing nested mutable state.

**Simpler alternative / refactor-away:** immutable data + spread/copy; just construct a new object when construction is cheap.

**Kotlin/Python:** `data class .copy(name = ...)` (shallow — copy nested collections explicitly); Python `copy.deepcopy` or `dataclasses.replace`.

## Singleton

**Intent:** Ensure a class has one instance and provide a global access point to it.

**Forces:** a genuinely process-wide resource (connection pool, config loaded once, logger) **and** no DI mechanism to share one instance. Rarely both are true.

```ts
// Idiomatic TS: the module system gives you a single instance.
// db.ts
import { Pool } from "pg";
export const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 10 });

// Better for testability: create once in the composition root and inject.
// main.ts
const pool = new Pool({ connectionString: config.databaseUrl, max: 10 });
const users = new UserRepo(pool);
const app = buildServer({ users });

// user-repo.ts
export class UserRepo {
  constructor(private pool: Pool) {}          // tests pass a test pool
  async byId(id: string) {
    const { rows } = await this.pool.query("SELECT * FROM users WHERE id = $1", [id]);
    return rows[0] ?? null;
  }
}
```

**Overuse smell:** `getInstance()` everywhere; hidden global mutable state; tests that interfere through shared singletons; order-dependent initialization.

**Simpler alternative / refactor-away:** construct one instance in `main`/composition root and pass it down (constructor injection); DI container scope `singleton` if a container already exists. To refactor away: add a constructor param defaulting to the singleton, migrate callers, then remove the default.

**Kotlin/Python:** Kotlin `object` is fine for stateless helpers; stateful ones should be DI-scoped (`@Singleton` in Hilt). Python modules are singletons; avoid module-level mutable state and create resources in the entry point.

## Sources

- Gamma, Helm, Johnson, Vlissides, *Design Patterns* (1994), ch. 3.
- Refactoring.Guru, Creational Patterns: https://refactoring.guru/design-patterns/creational-patterns
- Joshua Bloch, *Effective Java* 3rd ed., Items 1-3 (static factories, builders, singletons).
- Kotlin docs, Object declarations: https://kotlinlang.org/docs/object-declarations.html
