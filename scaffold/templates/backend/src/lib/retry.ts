// src/lib/retry.ts
// Exponential-backoff retry helper. Retries the supplied async function up to
// `attempts` times, doubling the delay each time. Throws the last error if
// every attempt fails.

interface RetryOptions {
  attempts?: number;
  initialDelayMs?: number;
  maxDelayMs?: number;
}

export async function retry<T>(fn: () => Promise<T>, opts: RetryOptions = {}): Promise<T> {
  const attempts = opts.attempts ?? 3;
  const initialDelayMs = opts.initialDelayMs ?? 100;
  const maxDelayMs = opts.maxDelayMs ?? 5_000;

  let delay = initialDelayMs;
  let lastErr: unknown;

  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (i === attempts - 1) break;
      await new Promise((r) => setTimeout(r, delay));
      delay = Math.min(delay * 2, maxDelayMs);
    }
  }
  throw lastErr;
}
