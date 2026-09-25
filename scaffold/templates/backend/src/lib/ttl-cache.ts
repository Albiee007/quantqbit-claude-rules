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

  constructor(
    private readonly defaultTtlMs: number = 60_000,
    private readonly maxEntries: number = 1_000,
  ) {
    if (!Number.isFinite(defaultTtlMs) || defaultTtlMs < 0) {
      throw new RangeError('defaultTtlMs must be finite and non-negative');
    }
    if (!Number.isSafeInteger(maxEntries) || maxEntries < 1) {
      throw new RangeError('maxEntries must be a positive integer');
    }
  }

  set(key: K, value: V, ttlMs: number = this.defaultTtlMs): void {
    if (!Number.isFinite(ttlMs) || ttlMs < 0) {
      throw new RangeError('ttlMs must be finite and non-negative');
    }
    this.store.delete(key);
    if (ttlMs === 0) return;
    // FIFO eviction bounds memory even when expired keys are never read again.
    if (this.store.size >= this.maxEntries) {
      const oldest = this.store.keys().next();
      if (!oldest.done) this.store.delete(oldest.value);
    }
    this.store.set(key, { value, expiresAt: Date.now() + ttlMs });
  }

  get(key: K): V | undefined {
    const entry = this.store.get(key);
    if (!entry) return undefined;
    if (entry.expiresAt <= Date.now()) {
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
