# Error Handling

Goal: every failure is either **handled meaningfully** or **propagated with context** to a boundary that can report it. Nothing disappears.

## Classify first

| Kind | Examples | Response |
|---|---|---|
| **Programmer error / bug** | null deref, violated invariant, impossible branch | Fail fast. Do not catch locally. Let it reach the top-level handler, log, alert. |
| **Expected domain failure** | not found, insufficient funds, validation failed, conflict | Model explicitly: typed error, `Result`/sealed type, or error value. Caller must handle. |
| **Transient infrastructure failure** | timeout, 503, connection reset, lock contention | Retry with backoff *if idempotent*; otherwise surface. |
| **Permanent infrastructure failure** | auth rejected, 400/404 from dependency, disk full | Do not retry. Surface with context. |

## Typed errors

- Define a small hierarchy/union per domain, not per call site. Carry machine-readable `code` plus context fields; keep `message` for humans/logs.
- Preserve the cause chain: TS `new AppError(msg, { cause })`, Python `raise X from e`, Go `fmt.Errorf("load user %s: %w", id, err)`, Kotlin/Java `Exception(msg, cause)`.
- Match on type/code, never on message strings.

```ts
export class DomainError extends Error {
  constructor(readonly code: string, message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = new.target.name;
  }
}
export class NotFoundError extends DomainError {
  constructor(entity: string, id: string) { super("NOT_FOUND", `${entity} ${id} not found`); }
}
```
```go
var ErrNotFound = errors.New("not found")
if errors.Is(err, ErrNotFound) { /* ... */ }
var ve *ValidationError
if errors.As(err, &ve) { /* ... */ }
```

## Never swallow

Forbidden:
```ts
try { await charge(order); } catch {}                    // silent
try { await charge(order); } catch (e) { console.log(e) } // logged and forgotten
```
```python
except Exception:  # bare / overly broad, then pass
    pass
```
Allowed only with: a narrow exception type, a comment explaining why ignoring is correct, and (usually) a debug log. Example: deleting a temp file that may already be gone.

- Catch the **narrowest** type you can handle. Re-throw everything else.
- Do not catch just to log and re-throw at every layer — log **once**, at the boundary that handles it (avoids duplicate log spam).
- `finally`/`defer`/`use`/`with` for cleanup; never rely on happy-path cleanup.
- Async: every promise is awaited or explicitly handled (`void` + `.catch`). Enable `no-floating-promises`. Goroutines and coroutines report errors back (errgroup, structured concurrency).

## Boundaries

Boundaries = HTTP handler, message consumer, CLI entrypoint, job runner, UI event handler.

- Boundary translates errors into the protocol: domain `NotFound` → 404; `Validation` → 400/422 with field errors; `Conflict` → 409; auth → 401/403; unknown → 500.
- Boundary logs unexpected errors once with correlation id and stack; returns a generic message plus the correlation id.
- Interior code throws/returns typed errors; it does not know about HTTP status codes.
- Validate input at the boundary with a schema (zod, pydantic, kotlinx.serialization + checks, go-playground/validator). Reject early with all field errors at once.
- Messages from consumers (queues): decide per error → retry, dead-letter, or drop-with-log. Never infinite redelivery.

## Retries

Retry only when **all** are true: the error is transient, the operation is idempotent (or has an idempotency key), and a caller is still waiting/it is a background job.

- Exponential backoff **with jitter** (full jitter: `sleep = random(0, min(cap, base * 2^attempt))`).
- Cap attempts (typically 3-5) and total elapsed time; respect deadlines/cancellation (`AbortSignal`, `context.Context`, coroutine cancellation).
- Honor `Retry-After` headers.
- Retry at **one** layer only — nested retries multiply (3 × 3 × 3 = 27 calls).
- Combine with timeouts on every network call and a circuit breaker for dependencies that fail persistently.
- Never retry 4xx (except 408/429), auth errors, or validation errors.

## User-facing messages

- Say what happened and what the user can do: "Payment was declined. Try another card." — not "Error 0x80004005" or a stack trace.
- Never expose stack traces, SQL, internal hostnames, file paths, or whether an account exists (login/reset flows: generic "If that email exists, we sent a link").
- Include a reference/correlation id for support.
- Localizable: user text comes from a message catalog keyed by error `code`, not from `err.message`.

## Other rules

- Do not use exceptions for normal control flow (e.g. loop exit, expected lookups — return `null`/`Option`/`(v, ok)`).
- Assertions/invariant checks stay on in production for cheap checks that guard data integrity.
- Crash the process on unrecoverable state (corrupt config at startup); let the supervisor restart it.
- Validate configuration at startup, not at first use.
- Kotlin: do not catch `CancellationException` (or rethrow it). Python: do not catch `BaseException`/`KeyboardInterrupt`. Go: do not `panic` for expected errors; `recover` only at goroutine/request boundaries.

## Sources

- OWASP Top 10:2025 A10 Mishandling of Exceptional Conditions: https://top10.owasp.org/2025/
- OWASP Error Handling Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html
- AWS Architecture Blog, "Exponential Backoff and Jitter": https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- Go blog, "Working with Errors in Go 1.13": https://go.dev/blog/go1.13-errors
