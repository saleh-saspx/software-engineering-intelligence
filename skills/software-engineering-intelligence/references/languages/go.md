# Go

Conventions: Effective Go, Go Code Review Comments, standard library style (X11). Go idioms
override several generic Clean Code heuristics (T-01, T-02, T-11).

## Identify
- `go.mod`: module path and `go` version (generics need 1.18+; `log/slog` 1.21+; loop-variable
  per-iteration semantics changed in 1.22). Layout often `cmd/<app>/main.go`, `internal/`, `pkg/`.

## Idioms to follow (and not flag)
- `gofmt`/`goimports` formatting is non-negotiable and not a review topic.
- **Explicit error returns** with `if err != nil` are idiomatic; repetition is not duplication.
  Exceptions/`panic` for expected failures are wrong (CODE-ERR-02).
- **Longer linear functions** with early returns are fine when they read top-down (T-01).
- **Small interfaces defined by the consumer**; "accept interfaces, return structs". Defining an
  interface next to its only implementation "for DI" is interface pollution (DES-SIMP-03).
- **Manual wiring in `main`** (no DI framework) is idiomatic (DES-DI-01).
- Naming: `MixedCaps`; short receiver names; no `Get` prefix on getters; package names short,
  lowercase, no underscores; avoid stutter (`order.Order` fine, `order.OrderService` stutters);
  error strings lowercase without trailing punctuation; `ctx context.Context` first parameter,
  never stored in structs.
- Exported fields on plain data structs are normal.

## Real issues to look for
- **Ignored errors**: `_ = f()`, unchecked `err`, unchecked `rows.Err()`, ignored `Close()` errors
  on writers (CODE-ERR-01). **Log and return** the same error at every level (noise, REL-OBS-01).
- **Unwrapped errors** losing context — use `fmt.Errorf("load order %d: %w", id, err)`;
  `errors.Is/As` for checks (CODE-ERR-03).
- **Data races**: maps written from several goroutines (the runtime aborts on concurrent map
  writes); shared struct fields without a mutex; closures capturing loop variables (before Go
  1.22) (REL-CONC-01). Run `go test -race`.
- **Goroutine leaks**: goroutines without exit path, blocked sends on unbuffered channels nobody
  reads, missing `ctx.Done()` handling (REL-CONC-03). `context.Background()` deep in request paths.
- **No timeouts**: `http.DefaultClient`/`http.Get` have no timeout; servers without
  `ReadHeaderTimeout` etc. (REL-TIME-01). Response bodies not closed (REL-RES-01).
- **SQL built with `fmt.Sprintf`** (SEC-INJ-01) — use placeholders (`$1` for PostgreSQL drivers,
  `?` for MySQL); forgetting `rows.Close()`.
- **`text/template` for HTML** or `template.HTML(userInput)` (SEC-OUT-01).
- **`exec.Command("sh", "-c", …)`** with input (SEC-INJ-02); `InsecureSkipVerify: true`
  (SEC-CRYPTO-01); `math/rand` for tokens instead of `crypto/rand` (SEC-CRYPTO-01).
- **Panics across API boundaries** in libraries; `init()` doing I/O; mutable package-level state
  (DES-DI-02).

## Testing
Table-driven tests with `t.Run` subtests; `t.Helper()`; `httptest` for handlers; golden files
for complex output (refactoring.md §3); fuzzing with `go test -fuzz`; `-race` in CI; `goleak`
for goroutine leaks; avoid sleeps — synchronise with channels or polling helpers.

## Tools
`go vet`, `staticcheck`, `golangci-lint` (incl. `errcheck`, `bodyclose`, `gosec`), `govulncheck`
(advisories with reachability), `go test -race -cover ./...`, `gocyclo`/`gocognit` for complexity.
