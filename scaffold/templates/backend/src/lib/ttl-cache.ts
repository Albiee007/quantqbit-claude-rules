// src/lib/ttl-cache.ts
// Tiny in-process TTL cache. Not Redis — not even close — but enough to
// memoise an upstream call for a few seconds without pulling in another
// dependency.

interface Entry<V> {
  value: V;
  expiresAt: number;
}

export class TtlCache<K, V> {
  private store = new Map<K, Entry<V>>();

  constructor(private readonly defaultTtlMs: number = 60_000) {}

  set(key: K, value: V, ttlMs: number = this.defaultTtlMs): void {
    this.store.set(key, { value, expiresAt: Date.now() + ttlMs });
  }

  get(key: K): V | undefined {
    const entry = this.store.get(key);
    if (!entry) return undefined;
    if (entry.expiresAt < Date.now()) {
      this.store.delete(key);
      return undefined;
    }
    return entry.value;
  }

  delete(key: K): boolean {
    return this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }
}
