# Logging & Observability

Three signals: **logs** (discrete events, debugging detail), **metrics** (aggregated numbers, alerting), **traces** (request flow across services, latency). Use the project's existing library; if none, prefer OpenTelemetry-compatible tooling.

## Structured logs

- Log **events with fields**, not interpolated sentences. Machine-parseable (JSON in production).
  ```ts
  logger.info({ orderId, amountCents, durationMs }, "order.charged");      // pino-style
  ```
  ```python
  log.info("order.charged", order_id=order_id, amount_cents=amt)           # structlog
  ```
  ```go
  slog.Info("order.charged", "order_id", id, "amount_cents", amt)
  ```
- Stable event names (`noun.verb` past tense) and stable field names (`user_id` everywhere, not `uid`/`userId` mixed).
- Include context: service, env, version, correlation/trace id, user/tenant id (pseudonymous), operation, outcome, duration.
- Log errors with the error object (stack + cause chain), not just `err.message`.
- Use a logger, not `console.log`/`print`/`println`, outside scripts.

## Levels

| Level | Use for | Prod default |
|---|---|---|
| `ERROR` | Operation failed and needs attention; unexpected exceptions | on, alert-worthy in aggregate |
| `WARN` | Degraded but handled: retry succeeded after failures, fallback used, deprecated usage | on |
| `INFO` | Significant business/lifecycle events: startup, config summary (no secrets), request summary, job done | on |
| `DEBUG` | Diagnostic detail for developers | off |
| `TRACE` | Very verbose (payload-level) | off |

- Log an error **once**, where it is handled — not at every layer it passes through.
- Expected domain outcomes (validation failed, not found) are `INFO`/`WARN` at most, not `ERROR`.
- No logging inside tight loops; sample or aggregate.

## Never log

- Passwords, tokens, API keys, session ids, auth headers, cookies, private keys, OTPs.
- Full card numbers, CVV, bank details, government IDs.
- Unnecessary PII (email, phone, address, name, precise location, health data). Use internal ids or hashes; mask if required (`j***@example.com`).
- Whole request/response bodies by default — use an allowlist of fields or redaction config (`pino.redact`, structlog processors, logback masking).
- Raw user input unescaped into text logs (log injection) — structured logging handles this.

## Correlation ids

- Accept an incoming id (`traceparent` W3C Trace Context, or `X-Request-Id`) or generate one at the edge.
- Propagate it through async context (AsyncLocalStorage, `contextvars`, `context.Context`, coroutine context/MDC) to every log line and every outbound call/message header.
- Return it to the client in error responses so support can find the logs.

## Metrics

- **RED** for request-driven services: Rate, Errors, Duration (histogram, not average).
- **USE** for resources: Utilization, Saturation, Errors (pools, queues, CPU, memory).
- Business metrics for key flows (signups, orders, payments failed).
- Watch cardinality: never use user id, email, raw URL path, or request id as a label. Use route templates (`/users/:id`).
- Alert on symptoms users feel (error rate, latency SLO burn), not on every cause.

## Traces

- Instrument with OpenTelemetry auto-instrumentation for HTTP/DB/queue; add manual spans only around significant internal operations.
- Span names are low-cardinality (`GET /orders/:id`, `db.query orders.select`); details go in attributes.
- Record exceptions on spans and set error status.
- Sample appropriately (head or tail-based); always keep errors.

## Mobile / front-end

- Crash reporting (Crashlytics, Sentry) with release version and breadcrumbs; scrub PII.
- Strip debug logs in release builds (R8/ProGuard rules, build-time flags).
- Don't ship verbose console logging of API responses to production.

## Sources

- OpenTelemetry documentation: https://opentelemetry.io/docs/
- W3C Trace Context: https://www.w3.org/TR/trace-context/
- OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- Brendan Gregg, "The USE Method": https://www.brendangregg.com/usemethod.html
- Tom Wilkie, "The RED Method" (Grafana Labs): https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/
