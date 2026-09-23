# SOLID

SOLID is a set of heuristics for managing *change*, not goals in themselves. Apply a principle when you can name the change it protects against.

## S — Single Responsibility Principle

**Definition:** A module should have one reason to change — i.e. be answerable to one actor (Martin's later formulation).

**Violation smells:** class name contains "And"/"Manager"/"Util"; method mixes parsing, business rules, persistence, and formatting; unrelated tests share one fixture; edits for billing break reporting.

Before:
```ts
class InvoiceService {
  async issue(orderId: string): Promise<string> {
    const order = await db.query("SELECT * FROM orders WHERE id = $1", [orderId]);
    const total = order.lines.reduce((s, l) => s + l.qty * l.unitPrice, 0) * 1.2;
    const html = `<h1>Invoice ${order.id}</h1><p>Total: ${total.toFixed(2)}</p>`;
    await smtp.send(order.customerEmail, "Your invoice", html);
    return html;
  }
}
```
After:
```ts
const VAT_RATE = 0.2;
export const invoiceTotal = (lines: OrderLine[]): number =>
  lines.reduce((s, l) => s + l.qty * l.unitPrice, 0) * (1 + VAT_RATE);

class IssueInvoice {
  constructor(private orders: OrderRepo, private render: InvoiceRenderer, private mail: Mailer) {}
  async run(orderId: string): Promise<void> {
    const order = await this.orders.get(orderId);
    const doc = this.render(order, invoiceTotal(order.lines));
    await this.mail.send(order.customerEmail, "Your invoice", doc);
  }
}
```
**Don't over-apply:** a 20-line script or a cohesive function that does one user-visible thing does not need four classes. Split when a second actor or a test pain appears, not preemptively. "One reason to change" is not "one line of code".

## O — Open/Closed Principle

**Definition:** Open for extension, closed for modification — new variants are added without editing existing, tested code.

**Violation smells:** the same `switch (type)` repeated across several files; every new provider/format touches a core module; shotgun surgery.

Before:
```ts
function shippingCost(method: string, kg: number): number {
  if (method === "standard") return 5 + kg * 0.5;
  if (method === "express") return 15 + kg * 1.2;
  if (method === "drone") return 30;          // each new method edits this
  throw new Error(`unknown method ${method}`);
}
```
After (only if methods are added often or by other teams):
```ts
type CostFn = (kg: number) => number;
const shippingRates: Record<ShippingMethod, CostFn> = {
  standard: kg => 5 + kg * 0.5,
  express: kg => 15 + kg * 1.2,
  drone: () => 30,
};
const shippingCost = (m: ShippingMethod, kg: number) => shippingRates[m](kg);
```
**Don't over-apply:** a single `switch` in one place over a closed, stable set is fine — and with an exhaustive union type the compiler flags missing cases, which is often *safer* than a registry. Do not build plugin systems for variation that has never happened.

## L — Liskov Substitution Principle

**Definition:** Objects of a subtype must be usable wherever the base type is expected without altering correctness: preconditions not strengthened, postconditions not weakened, invariants preserved, no new unchecked exceptions.

**Violation smells:** `instanceof` checks on a base-typed variable; overridden methods that throw `NotImplemented`; subclasses that ignore arguments; Square-extends-Rectangle.

Before:
```ts
class FileStore { write(path: string, data: Buffer): void { /* ... */ } }
class ReadOnlyStore extends FileStore {
  write(): void { throw new Error("read-only"); } // callers of FileStore now break
}
```
After:
```ts
interface Readable { read(path: string): Buffer }
interface Writable { write(path: string, data: Buffer): void }
class FileStore implements Readable, Writable { /* ... */ }
class ReadOnlyStore implements Readable { /* ... */ }
```
**Don't over-apply:** LSP is about behavioral contracts callers rely on; it does not forbid subclasses from adding behavior. If there is no polymorphic use, there is no substitution to protect.

## I — Interface Segregation Principle

**Definition:** Clients should not be forced to depend on methods they do not use. Shape interfaces around consumers.

**Violation smells:** fat `IRepository` with 25 methods; test doubles stubbing methods the test never touches; a change to an unused method forces recompiles/redeploys of unrelated clients.

Before:
```ts
interface UserService {
  get(id: string): Promise<User>; list(q: Query): Promise<User[]>;
  create(u: NewUser): Promise<User>; delete(id: string): Promise<void>;
  exportCsv(): Promise<string>; resetPassword(id: string): Promise<void>;
}
function greet(users: UserService, id: string) { /* only calls get() */ }
```
After:
```ts
type GetUser = Pick<UserService, "get">;
async function greet(users: GetUser, id: string) {
  const u = await users.get(id);
  return `Hello, ${u.displayName}`;
}
```
**Don't over-apply:** do not create one interface per method across a codebase. In TS/Go structural typing (`Pick`, small consumer-side interfaces) gives ISP for free; use it at the consumer, not as ceremony at the provider.

## D — Dependency Inversion Principle

**Definition:** High-level policy should not depend on low-level details; both depend on abstractions, and the abstraction is owned by the policy side.

**Violation smells:** domain code imports the ORM, HTTP client, or `process.env`; tests need a real DB or network to exercise business rules; `new` of infrastructure inside business logic.

Before:
```ts
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
export async function archiveReport(r: Report) {
  const s3 = new S3Client({});
  await s3.send(new PutObjectCommand({ Bucket: "reports", Key: r.id, Body: r.pdf }));
}
```
After:
```ts
export interface BlobStore { put(key: string, body: Uint8Array): Promise<void> }
export const archiveReport = (store: BlobStore) => (r: Report) => store.put(r.id, r.pdf);

// composition root (edge)
const archive = archiveReport(new S3BlobStore(new S3Client({}), "reports"));
```
**Don't over-apply:** do not invert dependencies on stable, pure libraries (date-fns, lodash, the standard library). An interface with exactly one implementation that exists only "for mocking" is usually noise — prefer a fake at the I/O boundary or pass a function. DI containers are optional; constructor/parameter injection is enough for most codebases.

## Summary heuristics

- Apply SOLID at **seams where change has happened or is contractually expected**.
- Prefer functions and data over class hierarchies when the language allows.
- If applying a principle adds more code than the change it protects against, skip it and revisit on the third occurrence.

## Sources

- Robert C. Martin, *Clean Architecture* (2017), Part III "Design Principles".
- Barbara Liskov & Jeannette Wing, "A Behavioral Notion of Subtyping" (1994).
- Martin Fowler, "Is Design Dead?" and *Refactoring* 2nd ed. (2018): https://martinfowler.com/articles/designDead.html
