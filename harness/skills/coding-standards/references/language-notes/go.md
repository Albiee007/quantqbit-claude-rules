# Go Notes

## Idioms

- `gofmt`/`goimports` always; `go vet` and `staticcheck`/golangci-lint per project.
- Errors are values: check every error immediately; return early.
  ```go
  u, err := repo.Get(ctx, id)
  if err != nil {
      return nil, fmt.Errorf("get user %s: %w", id, err)
  }
  ```
- Wrap with `%w` to add context; inspect with `errors.Is`/`errors.As`. Sentinel errors (`var ErrNotFound = errors.New(...)`) or typed errors for callers that branch.
- Error strings lowercase, no trailing punctuation; don't prefix with "failed to" chains at every level — say what was being done.
- `context.Context` is the first parameter of anything doing I/O or long work; never store it in structs; respect cancellation.
- Accept interfaces, return concrete types. Define small interfaces at the **consumer** side (`io.Reader` style); don't pre-declare interfaces next to their only implementation.
- Zero values useful: design structs so the zero value is valid where possible (`sync.Mutex`, `bytes.Buffer`).
- Composition via struct embedding sparingly; explicit fields when the embedded API would leak.
- Functional options or a config struct for many optional params; not builders.
- Package names short, lowercase, no `util`/`common`/`helpers`; avoid stutter (`user.User` ok, `user.UserService` → `user.Service`).
- `internal/` for non-public packages; `cmd/<app>/main.go` for binaries.
- Table-driven tests with `t.Run` subtests; `t.Helper()` in helpers; `t.Parallel()` where safe.
- `slog` for structured logging (Go 1.21+).
- Generics for container/algorithm code, not to emulate class hierarchies.

## Concurrency

- Don't start goroutines without knowing how they stop. Tie lifetime to a `context` or `sync.WaitGroup`/`errgroup.Group`.
- `errgroup.WithContext` for parallel work with first-error cancellation; `SetLimit` to bound concurrency.
- Channels to transfer ownership/signal; mutexes to protect state — whichever is simpler.
- Close channels only from the sender; never close twice.
- Run tests with `-race`.
- `recover` only at goroutine/request boundaries to convert panics to errors and log them.

## Pitfalls

- Loop variable capture: fixed in Go 1.22+ (per-iteration variables); on older versions copy (`v := v`).
- Nil interface vs interface holding a nil pointer (`err != nil` true for a typed nil) — return literal `nil`.
- Nil map writes panic; initialize with `make`.
- Slices share backing arrays: `append` may mutate caller data; copy when retaining (`slices.Clone`).
- `defer` in loops runs at function end — wrap the body in a function.
- `defer resp.Body.Close()` after checking err; drain/close bodies to reuse connections.
- `http.DefaultClient` has no timeout — set `Timeout` or use context deadlines.
- Unhandled `rows.Err()` after iterating `sql.Rows`; forgetting `rows.Close()`.
- `time.Now()` in logic — inject a clock for tests.
- JSON: unexported fields are ignored; use struct tags; `DisallowUnknownFields` for strict input.
- Integer overflow and `int` size are platform-dependent; use explicit sizes in protocols.

## Sources

- Effective Go: https://go.dev/doc/effective_go
- Go Code Review Comments: https://go.dev/wiki/CodeReviewComments
- Go blog, "Working with Errors in Go 1.13": https://go.dev/blog/go1.13-errors
- Go 1.22 loop variable change: https://go.dev/blog/loopvar-preview
