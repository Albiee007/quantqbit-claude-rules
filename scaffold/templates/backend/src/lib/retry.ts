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

  if (!Number.isSafeInteger(attempts) || attempts < 1) {
    throw new RangeError('attempts must be a positive integer');
  }
  if (![initialDelayMs, maxDelayMs].every((n) => Number.isFinite(n) && n >= 0 && n <= 2_147_483_647)) {
    throw new RangeError('delays must be finite and within the timer range');
  }

  let delay = Math.min(initialDelayMs, maxDelayMs);
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
