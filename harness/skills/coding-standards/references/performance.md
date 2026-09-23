# Performance

## Measure first

1. Define the target: which operation, which percentile (p95/p99), what budget (e.g. API p95 < 200 ms, list scroll 60 fps, cold start < 2 s).
2. Reproduce with realistic data volume. Profile (Chrome DevTools/Lighthouse, `node --prof`/clinic, `py-spy`/`cProfile`, `pprof`, Android Studio Profiler/Perfetto, DB `EXPLAIN ANALYZE`).
3. Fix the biggest measured bottleneck; re-measure; stop when the target is met.
4. Don't micro-optimize without a profile. Readability wins unless the code is on a measured hot path.

Exception: avoid known algorithmic traps (below) up front — they are design, not micro-optimization.

## N+1 queries

Symptom: one query for a list, then one per item.
```ts
// bad
const orders = await db.order.findMany({ where: { userId } });
for (const o of orders) o.items = await db.item.findMany({ where: { orderId: o.id } });

// good: eager load or batch
const orders = await db.order.findMany({ where: { userId }, include: { items: true } });
// or: SELECT ... WHERE order_id = ANY($1)  then group in memory
```
- Same pattern exists for HTTP calls in loops — batch endpoints, `Promise.all` with a concurrency limit, or DataLoader in GraphQL.
- Enable query logging in dev/tests to spot it; some teams assert query counts in tests.

## Database

- Index columns used in `WHERE`, `JOIN`, `ORDER BY` of hot queries; verify with `EXPLAIN`. Don't index everything (write cost).
- Always paginate (keyset/cursor pagination for large or infinite lists; offset degrades linearly).
- Select only needed columns; avoid `SELECT *` over wide rows.
- Keep transactions short; no network calls inside a DB transaction.
- Connection pools sized to the DB limit, not "as big as possible".

## Big-O on hot paths

- Nested loop over two growing collections → build a `Map`/`Set`/dict index first (O(n·m) → O(n+m)).
- `array.includes`/`indexOf`/`list.contains` inside a loop → `Set`.
- Repeated string concatenation in loops → builder/`join`.
- Sorting inside a loop; re-computing derived values per render/frame → compute once, memoize.
- Unbounded in-memory accumulation of streams/files → stream/iterate in chunks.
- Regex: avoid catastrophic backtracking on user input; precompile in hot paths.

## Caching rules

Cache only when measured need exists and you can answer all of:
1. **What is the key?** Includes every input that changes the result (tenant, locale, permissions, version).
2. **How is it invalidated?** TTL, explicit invalidation on write, or versioned keys. "Never" is rarely right.
3. **What staleness is acceptable?** Stated in the code/ADR.
4. **What bounds size?** LRU/max entries/memory cap. Unbounded maps are memory leaks.
5. **What happens on a miss storm?** Request coalescing/single-flight, jittered TTLs to avoid thundering herd.
6. **Is it safe?** Never cache per-user/authorized data under a shared key. Respect `Cache-Control` for HTTP.

Layers, nearest first: memoization in-process → in-memory LRU → distributed (Redis) → HTTP/CDN. Each layer adds a consistency problem.

## Concurrency & I/O

- Parallelize independent I/O (`Promise.all`, `asyncio.gather`, errgroup, `coroutineScope { async }`) with a concurrency cap.
- Never block the event loop / main/UI thread with CPU work or sync I/O (move to worker threads, `Dispatchers.Default`/`IO`, goroutines).
- Set timeouts on every network call.
- Reuse clients/connections (HTTP keep-alive, one DB pool, one `HttpClient`/`OkHttpClient`).

## Front-end / mobile

- Budget bundle size; code-split routes; lazy-load heavy components; tree-shakeable imports.
- Avoid unnecessary re-renders/recompositions (stable keys, memoization where profiled, stable lambdas/state in Compose).
- Virtualize long lists (`FlatList`/`FlashList`, `LazyColumn`, react-window).
- Images: correct size, modern formats, lazy loading, caching.
- Core Web Vitals (LCP, INP, CLS) are the web targets.

## Sources

- Donald Knuth, "Structured Programming with go to Statements" (1974) — "premature optimization" in context.
- Use The Index, Luke (SQL indexing): https://use-the-index-luke.com/
- web.dev Core Web Vitals: https://web.dev/articles/vitals
- Android performance guidance: https://developer.android.com/topic/performance
