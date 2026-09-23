# GoF Structural Patterns

Run the Decision Gate in [SKILL.md](../SKILL.md) first. Structural patterns are the most commonly justified GoF patterns (Adapter, Decorator, Facade) — and the most commonly overbuilt as pass-through wrappers.

## Adapter

**Intent:** Convert the interface of a class into another interface clients expect, letting incompatible interfaces work together.

**Forces:** a third-party/legacy API has a shape you don't want leaking into domain code; you need to swap vendors or fake the dependency in tests; the port is defined by your domain (hexagonal architecture).

```ts
// Port owned by the domain
export interface PaymentGateway {
  charge(input: { amountCents: number; currency: string; token: string; idempotencyKey: string }):
    Promise<{ chargeId: string; status: "succeeded" | "declined" }>;
}

// Adapter for a vendor SDK
export class StripeGateway implements PaymentGateway {
  constructor(private stripe: Stripe) {}
  async charge(i: Parameters<PaymentGateway["charge"]>[0]) {
    try {
      const pi = await this.stripe.paymentIntents.create(
        { amount: i.amountCents, currency: i.currency, payment_method: i.token, confirm: true },
        { idempotencyKey: i.idempotencyKey },
      );
      return { chargeId: pi.id, status: pi.status === "succeeded" ? "succeeded" : "declined" } as const;
    } catch (e) {
      if (e instanceof Stripe.errors.StripeCardError) return { chargeId: "", status: "declined" } as const;
      throw new PaymentUnavailableError("stripe charge failed", { cause: e });
    }
  }
}
```

**Overuse smell:** adapters that rename methods 1:1 around APIs you already own; wrapping stable standard-library APIs; an adapter per call site.

**Simpler alternative / refactor-away:** if you own both sides, change the interface. For one usage, a single function wrapping the SDK call is enough.

**Kotlin/Python:** Kotlin adapters are often a class implementing the port or an extension function mapping DTOs; Python uses a `Protocol` for the port and a thin class/function adapter.

## Bridge

**Intent:** Decouple an abstraction from its implementation so the two can vary independently.

**Forces:** two orthogonal dimensions, each with ≥ 2 real variants, would otherwise produce an M×N subclass explosion (e.g. report type × output format, shape × renderer).

```ts
// Implementation dimension
interface Renderer { heading(t: string): string; table(rows: string[][]): string; done(parts: string[]): Uint8Array }
const htmlRenderer: Renderer = {
  heading: t => `<h1>${escapeHtml(t)}</h1>`,
  table: r => `<table>${r.map(c => `<tr>${c.map(x => `<td>${escapeHtml(x)}</td>`).join("")}</tr>`).join("")}</table>`,
  done: p => new TextEncoder().encode(p.join("\n")),
};
const csvRenderer: Renderer = {
  heading: () => "",
  table: r => r.map(c => c.map(csvEscape).join(",")).join("\n"),
  done: p => new TextEncoder().encode(p.filter(Boolean).join("\n")),
};

// Abstraction dimension
abstract class Report {
  constructor(protected r: Renderer) {}
  abstract render(): Uint8Array;
}
class SalesReport extends Report {
  constructor(r: Renderer, private rows: string[][]) { super(r); }
  render() { return this.r.done([this.r.heading("Sales"), this.r.table(this.rows)]); }
}
class InventoryReport extends Report { /* same shape, different data */ render() { return new Uint8Array(); } }
```

**Overuse smell:** a "bridge" where only one side ever varies; abstraction hierarchies of one class.

**Simpler alternative / refactor-away:** pass the varying part as a parameter or function (`renderSales(rows, renderer)`). Bridge is just composition — don't add an abstract class unless the abstraction side truly has variants.

**Kotlin/Python:** interface + constructor parameter; Python passes a renderer object/module.

## Composite

**Intent:** Compose objects into tree structures and let clients treat individual objects and compositions uniformly.

**Forces:** recursive part-whole data (menus, org charts, file trees, pricing bundles, UI trees, expression ASTs) where operations apply to both leaves and groups.

```ts
type PriceNode =
  | { kind: "item"; sku: string; priceCents: number }
  | { kind: "bundle"; name: string; discountPct: number; children: PriceNode[] };

export function totalCents(node: PriceNode): number {
  switch (node.kind) {
    case "item":
      return node.priceCents;
    case "bundle": {
      const sum = node.children.reduce((acc, c) => acc + totalCents(c), 0);
      return Math.round(sum * (1 - node.discountPct / 100));
    }
  }
}

const cart: PriceNode = {
  kind: "bundle", name: "Starter kit", discountPct: 10,
  children: [
    { kind: "item", sku: "CAM-1", priceCents: 49_900 },
    { kind: "bundle", name: "Accessories", discountPct: 5,
      children: [{ kind: "item", sku: "SD-64", priceCents: 1_999 }, { kind: "item", sku: "BAG", priceCents: 2_999 }] },
  ],
};
```

**Overuse smell:** Component/Leaf/Composite class hierarchies for flat lists; `add/remove` methods on leaves that throw.

**Simpler alternative / refactor-away:** a recursive union type and recursive functions (above) is Composite without classes.

**Kotlin/Python:** Kotlin `sealed interface Node` with `data class Leaf`/`Group`; Python dataclasses + `match`.

## Decorator

**Intent:** Attach additional responsibilities to an object dynamically by wrapping it with the same interface.

**Forces:** stackable, orthogonal cross-cutting behaviors (caching, retry, metrics, logging, authorization) applied in different combinations to the same port.

```ts
interface ProductCatalog { get(sku: string): Promise<Product | null> }

export const withCache = (inner: ProductCatalog, cache: Cache<Product>, ttlMs: number): ProductCatalog => ({
  async get(sku) {
    const hit = cache.get(sku);
    if (hit) return hit;
    const p = await inner.get(sku);
    if (p) cache.set(sku, p, ttlMs);
    return p;
  },
});

export const withTiming = (inner: ProductCatalog, metrics: Metrics): ProductCatalog => ({
  async get(sku) {
    const start = performance.now();
    try { return await inner.get(sku); }
    finally { metrics.histogram("catalog.get.ms", performance.now() - start); }
  },
});

const catalog = withTiming(withCache(new HttpCatalog(baseUrl), new LruCache(10_000), 60_000), metrics);
```

**Overuse smell:** one decorator that is always applied (just put the behavior in the class); decorator stacks so deep debugging is painful; decorators that change semantics (not just add behavior).

**Simpler alternative / refactor-away:** higher-order function wrapping a single function; framework middleware/interceptors (Express/Koa middleware, OkHttp interceptors, gRPC interceptors).

**Kotlin/Python:** Kotlin class delegation `class Cached(private val inner: Catalog) : Catalog by inner { override fun get(...) }`; Python `@functools.wraps` decorators (e.g. `@cache`, `@retry`).

## Facade

**Intent:** Provide a unified, simpler interface to a set of interfaces in a subsystem.

**Forces:** callers repeatedly perform the same multi-step choreography across several subsystem objects; you want to shield callers from subsystem churn.

```ts
export class CheckoutFacade {
  constructor(
    private inventory: InventoryService,
    private pricing: PricingService,
    private payments: PaymentGateway,
    private orders: OrderRepo,
    private events: EventBus,
  ) {}

  async placeOrder(cart: Cart, payToken: string, idemKey: string): Promise<OrderId> {
    const reservation = await this.inventory.reserve(cart.lines);
    try {
      const quote = await this.pricing.quote(cart);
      const charge = await this.payments.charge({ amountCents: quote.totalCents, currency: quote.currency, token: payToken, idempotencyKey: idemKey });
      if (charge.status !== "succeeded") throw new PaymentDeclinedError();
      const id = await this.orders.create({ cart, quote, chargeId: charge.chargeId, reservationId: reservation.id });
      await this.events.publish("order.placed", { orderId: id });
      return id;
    } catch (e) {
      await this.inventory.release(reservation.id);
      throw e;
    }
  }
}
```

**Overuse smell:** facade wrapping a single service 1:1; facade that grows into a god object exposing everything in the subsystem.

**Simpler alternative / refactor-away:** a plain use-case function (`placeOrder(deps, cart, ...)`). Often a "service layer" method *is* the facade — don't add another layer above it.

**Kotlin/Python:** a use-case class or top-level suspend function; Python module-level function taking dependencies.

## Flyweight

**Intent:** Use sharing to support large numbers of fine-grained objects efficiently by separating intrinsic (shared) from extrinsic (per-use) state.

**Forces:** a profile shows memory dominated by many duplicate immutable sub-objects (glyphs, map tiles, style objects, parsed tokens).

```ts
interface TileStyle { readonly fill: string; readonly stroke: string; readonly texture: ImageBitmap }

class TileStyleRegistry {
  private styles = new Map<string, TileStyle>();
  constructor(private loadTexture: (name: string) => ImageBitmap) {}

  get(fill: string, stroke: string, textureName: string): TileStyle {
    const key = `${fill}|${stroke}|${textureName}`;
    let s = this.styles.get(key);
    if (!s) {
      s = Object.freeze({ fill, stroke, texture: this.loadTexture(textureName) });
      this.styles.set(key, s);
    }
    return s;                                   // shared intrinsic state
  }
}

// 1M tiles share a handful of styles; only x/y are per-tile (extrinsic)
type Tile = { x: number; y: number; style: TileStyle };
```

**Overuse smell:** applied without a memory profile; shared objects that are mutable (action at a distance).

**Simpler alternative / refactor-away:** store ids and look up in a table; string interning; typed arrays / struct-of-arrays for numeric data.

**Kotlin/Python:** Kotlin enums/`object`s are natural flyweights; Python `sys.intern`, `__slots__`, `functools.cache` on a factory.

## Proxy

**Intent:** Provide a surrogate for another object to control access to it — lazy initialization, remote access, access control, caching, or rate limiting.

**Forces:** access must be controlled transparently at the object boundary (callers must not bypass it), e.g. lazy loading an expensive resource, enforcing permissions on a shared service, or a client stub for a remote service.

```ts
interface DocumentStore {
  read(docId: string): Promise<Doc>;
  write(docId: string, doc: Doc): Promise<void>;
}

export class AuthorizingDocumentStore implements DocumentStore {
  constructor(private inner: DocumentStore, private policy: Policy, private user: User) {}

  async read(docId: string) {
    if (!(await this.policy.can(this.user, "read", docId))) throw new ForbiddenError("read", docId);
    return this.inner.read(docId);
  }
  async write(docId: string, doc: Doc) {
    if (!(await this.policy.can(this.user, "write", docId))) throw new ForbiddenError("write", docId);
    return this.inner.write(docId, doc);
  }
}

// Lazy proxy: defer an expensive client until first use
export const lazy = <T>(make: () => T) => { let v: T | undefined; return () => (v ??= make()); };
```

**Overuse smell:** proxy layers that only delegate; JS `Proxy` metaprogramming for things a plain wrapper does; proxy vs decorator debates — the structure is the same, pick the name that reflects intent.

**Simpler alternative / refactor-away:** middleware at the boundary (authz), `lazy` helpers, generated RPC clients.

**Kotlin/Python:** Kotlin `by lazy {}` and interface delegation `by inner`; Python `functools.cached_property`, `__getattr__` delegation (sparingly).

## Sources

- Gamma et al., *Design Patterns* (1994), ch. 4.
- Refactoring.Guru, Structural Patterns: https://refactoring.guru/design-patterns/structural-patterns
- Alistair Cockburn, "Hexagonal Architecture" (ports & adapters): https://alistair.cockburn.us/hexagonal-architecture/
- Kotlin docs, Delegation: https://kotlinlang.org/docs/delegation.html
