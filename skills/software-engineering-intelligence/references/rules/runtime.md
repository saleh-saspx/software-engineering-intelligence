# Runtime rules: reliability (REL-*) and performance (PERF-*)

Failure behaviour, resources, concurrency, consistency, timeouts and retries, time handling,
observability, and performance. Field meanings: `index.md`. Most of this area is beyond the
corpus; rules marked `extension` are expert practice — weigh them accordingly, and label
performance claims that weren't measured.

Areas: REL-ERR · REL-RES · REL-CONC · REL-CONS · REL-TIME · REL-OBS · PERF-MEAS · PERF-IO · PERF-ALGO · PERF-CACHE

## Reliability

### REL-ERR-01 · Define the failure behaviour of every external interaction
- level: strong | severity: major | provenance: synthesized
- sources: S1 Ch.7 (Define the Normal Flow; Write Your Try-Catch-Finally Statement First); X6
- why: Calls to databases, services, queues and files fail in ways the happy path ignores; undefined behaviour becomes cascading failure or corrupted state.
- signals: Remote calls with no error handling beyond logging; partial failures in multi-step flows with no rollback or compensation; "should never happen" branches that do nothing.
- fix: Decide per call: retry (if idempotent), fall back, degrade, or fail fast with a clear error; make the decision visible in code.
- verify: Tests or fault injection exercise the failure branch.
- related: CODE-ERR-01, REL-TIME-01, REL-CONS-01

### REL-RES-01 · Release resources on every path
- level: mandatory | severity: major | provenance: synthesized
- sources: S1 Ch.7 (Write Your Try-Catch-Finally Statement First); X11 (try-with-resources, `with`, `using`, `defer`)
- why: Leaked connections, file handles, locks and goroutines exhaust pools and hang services under load, usually only in production.
- signals: `open()`/`getConnection()`/`Lock()` without `with`/`try-with-resources`/`using`/`defer`; early returns skipping cleanup; HTTP response bodies not closed in Go; subscriptions/listeners never removed (JS).
- fix: Scoped resource constructs; `defer` immediately after acquisition; centralised pool management.
- verify: Tests or load runs show stable resource counts; linters (`bodyclose`, SpotBugs, ESLint plugins) clean.
- related: REL-CONC-03, CODE-ERR-01

### REL-RES-02 · Bound resource consumption
- level: strong | severity: major | provenance: extension
- sources: X6; X14
- why: Unbounded queues, caches, uploads, result sets and goroutine/thread creation turn traffic spikes into outages.
- signals: Loading whole tables or files into memory; unbounded in-memory queues; a goroutine/thread per request without limits; no request size limits.
- fix: Pagination/streaming, bounded queues with backpressure, worker pools, size limits, memory caps.
- verify: Load/soak test or reasoning shows memory, queue length and concurrency stay bounded under peak input.
- related: PERF-IO-02, API-PAGE-01, PERF-CACHE-01

### REL-CONC-01 · Protect or eliminate shared mutable state
- level: mandatory | severity: major–blocker | provenance: direct
- sources: S1 Ch.13 (Concurrency Defense Principles — Limit the Scope of Data; Use Copies of Data; Threads Should Be as Independent as Possible); S5 Race Conditions
- why: Unsynchronised access to shared data produces lost updates, corrupted structures and crashes that are rare in tests and frequent in production.
- signals: Maps/lists mutated from several goroutines/threads/async tasks without locks; singleton services with mutable fields (Spring beans, Node module state); lazy initialisation without synchronisation; `static` mutable caches.
- fix: Confine state to one owner (actor/channel), use immutable data and copies, thread-safe collections, or minimal locking; run the race detector (`go test -race`) or concurrency tests.
- verify: Race detector/thread-sanitizer clean on the relevant tests; stress test with more threads than cores (S1 Ch.13).
- related: REL-CONC-02, SEC-RACE-01, TEST-ISO-02

### REL-CONC-02 · Keep critical sections small and lock ordering consistent
- level: strong | severity: major | provenance: direct
- sources: S1 Ch.13 (Keep Synchronized Sections Small; Beware Dependencies Between Synchronized Methods; Know Your Execution Models — Dining Philosophers)
- why: Long or nested critical sections cause contention and deadlocks; calling unknown code while holding a lock invites both.
- signals: I/O or callbacks inside `synchronized`/`lock` blocks; locks acquired in different orders in different places; several synchronised methods on one object used together without an outer lock.
- fix: Narrow the locked region; define a global lock order; prefer higher-level concurrency utilities (executors, channels, concurrent collections).
- verify: No I/O or callbacks run under locks; lock acquisition order is documented and consistent.
- related: REL-CONC-01

### REL-CONC-03 · Support cancellation and graceful shutdown; don't leak workers
- level: strong | severity: major | provenance: direct
- sources: S1 Ch.13 (Writing Correct Shut-Down Code Is Hard)
- why: Workers that ignore cancellation leak, keep connections open, and lose in-flight work at deploy time.
- signals: Goroutines without exit conditions or `ctx.Done()` handling; `context.Background()` deep in request paths; background threads not joined; no SIGTERM handling in services; unawaited promises.
- fix: Propagate cancellation (`context.Context`, `CancellationToken`, `AbortController`); drain and stop workers on shutdown; await or explicitly detach async work.
- verify: Shutdown test or goroutine-leak check (e.g. `goleak`) passes.
- related: REL-RES-01, REL-TIME-01

### REL-CONS-01 · Multi-step state changes are atomic or compensated
- level: mandatory | severity: major–blocker | provenance: synthesized
- sources: S1 G26 (Be Precise — don't skip transactions or locks because conflicts seem unlikely); X13
- why: A crash or error between steps leaves money moved without a record, orders without stock, or rows without parents.
- signals: Several writes without a transaction; DB write plus message publish/HTTP call with no outbox or saga; error paths that skip rollback.
- fix: One transaction for one consistency boundary; transactional outbox for DB+message; sagas with compensating actions across services.
- verify: A test that fails midway leaves no partial state.
- related: DES-DOM-02, DATA-TXN-01, ARCH-STYLE-03

### REL-CONS-02 · Operations that may be retried or redelivered are idempotent
- level: strong | severity: major | provenance: extension
- sources: X13; X6
- why: Networks, queues and users retry; non-idempotent handlers double-charge and double-ship.
- signals: Message consumers without deduplication; payment/create endpoints without idempotency keys; retries around non-idempotent calls.
- fix: Idempotency keys, natural keys with unique constraints, upserts, processed-message tables.
- verify: Processing the same request/message twice yields one effect (test it).
- related: API-IDEMP-01, REL-TIME-02

### REL-CONS-03 · Check-then-act on shared data uses atomic primitives
- level: strong | severity: major | provenance: synthesized
- sources: S1 G26; S5 Race Conditions
- why: Reading, deciding and writing in separate steps loses updates under concurrency.
- signals: `if (!exists) insert`; `balance = read(); write(balance - x)`; counters incremented in application code.
- fix: Unique constraints with conflict handling, conditional updates, `SELECT … FOR UPDATE`, optimistic locking (version columns), atomic increments.
- verify: A concurrent test (parallel requests/threads) cannot create duplicates or lost updates.
- related: SEC-RACE-01, DATA-SCHEMA-01

### REL-TIME-01 · Every network or IPC call has a timeout
- level: strong | severity: major | provenance: extension
- sources: X6
- why: A call without a timeout can wait forever; one slow dependency then exhausts all threads/connections.
- signals: Default HTTP clients with no timeout (Go `http.DefaultClient`, Python `requests` without `timeout=`, Java `HttpURLConnection` defaults); DB queries without statement timeouts; awaiting promises with no deadline.
- fix: Explicit connect/read/overall timeouts, budgets propagated through contexts/deadlines.
- verify: Code inspection plus a test with a stalled fake dependency.
- related: REL-TIME-02, REL-ERR-01

### REL-TIME-02 · Retry with backoff, jitter and limits; isolate failing dependencies
- level: contextual | severity: major | provenance: extension
- sources: X6
- why: Immediate unbounded retries amplify outages (retry storms); a failing dependency should be cut off quickly.
- signals: `while True: try … except: continue`; fixed-interval retries; retries at several layers multiplying; no circuit breaker on critical, flaky dependencies.
- fix: Exponential backoff with jitter, max attempts and overall deadline; retry only idempotent operations; circuit breakers/bulkheads where warranted.
- related: REL-CONS-02, REL-TIME-01

### REL-TIME-03 · Handle time explicitly: UTC storage, zone-aware values, injectable clocks
- level: strong | severity: minor–major | provenance: extension
- sources: X14; S1 Ch.9 (Repeatable tests)
- why: Naive local times break across DST and regions; wall-clock durations jump; untestable `now()` calls cause flaky tests.
- signals: Naive `datetime.now()`, `new Date()` string parsing, `LocalDateTime` for instants; durations measured with wall clock; time-zone conversion in business logic scattered.
- fix: Store instants in UTC; carry zones explicitly for local business times; monotonic clocks for durations; inject a clock.
- verify: Tests run under a different TZ and across a DST boundary with an injected clock and pass.
- related: TEST-UNIT-01, DES-DOM-01

### REL-OBS-01 · Structured logs with correlation at boundaries
- level: strong | severity: minor | provenance: synthesized
- sources: S5 Reviewing Logging Code; X14
- why: Without context and correlation, production failures can't be traced across components.
- signals: `print` debugging left in; logs without request/correlation IDs; inconsistent levels (errors logged as info); logging and rethrowing at every layer (duplicate noise).
- fix: Structured logger, correlation ID propagated through calls and messages, log once at the handling boundary, meaningful levels.
- verify: A single request can be followed across components by its correlation ID in the logs.
- related: SEC-DATA-02, REL-OBS-02

### REL-OBS-02 · Services expose health and key metrics
- level: contextual | severity: minor | provenance: extension
- sources: X14
- why: You can't operate what you can't see; alerts should fire on user-visible symptoms.
- signals: No health/readiness endpoints; no latency/error-rate/saturation metrics; alerts only on CPU.
- fix: Health and readiness checks; RED/USE metrics; tracing for distributed calls; alerts on SLO symptoms.
- related: REL-OBS-01, SEC-MON-01

## Performance

### PERF-MEAS-01 · Optimise from measurement; label unmeasured claims
- level: strong | severity: minor | provenance: extension
- sources: X12; S1 G21 (Understand the Algorithm)
- why: Intuition about bottlenecks is often wrong, and optimisations cost readability.
- signals: Micro-optimisations (manual loop tricks, caching trivial computations) without benchmarks; performance arguments in review without numbers.
- fix: Profile or benchmark; optimise the measured hotspot; keep the benchmark. In findings, write "likely cost (unmeasured)" when you haven't measured.
- verify: A benchmark or profile before/after is attached to the change, or the claim is labelled unmeasured.
- related: PERF-IO-01, PERF-ALGO-01

### PERF-IO-01 · No N+1 queries or chatty remote calls in loops
- level: strong | severity: major | provenance: extension
- sources: X14
- why: Per-item queries or service calls turn one request into hundreds of round trips; it is the most common real performance defect in ORM-based code.
- signals: Lazy-loaded relations accessed in loops/templates (`$order->customer->name` in a `foreach`, Django FK access in templates, JPA lazy collections in loops); HTTP calls inside loops.
- fix: Eager loading (`with()`, `select_related`/`prefetch_related`, `JOIN FETCH`, entity graphs), batching, bulk APIs.
- verify: Query count per request measured (debug toolbar, query log, assertion in tests).
- related: PERF-IO-02, DATA-IDX-01

### PERF-IO-02 · Bound queries and payloads
- level: strong | severity: major | provenance: extension
- sources: X14
- why: Unbounded `SELECT *` and full-table loads work in development and fail in production data volumes.
- signals: `->all()`, `findAll()`, `.objects.all()` on growing tables for display; no `LIMIT`; selecting all columns including blobs.
- fix: Pagination, limits, projections of needed columns, streaming/cursors for exports.
- verify: Queries carry LIMIT/pagination; memory use is flat as table size grows (test with large fixture).
- related: API-PAGE-01, REL-RES-02

### PERF-ALGO-01 · Avoid accidental quadratic work on unbounded inputs
- level: strong | severity: minor–major | provenance: extension
- sources: S1 G21; X14
- why: Nested scans over growing collections and repeated string concatenation in loops scale badly and silently.
- signals: `list.contains`/`in list` inside loops; nested loops joining collections; repeated sorting; string concatenation in loops in languages where it copies.
- fix: Hash-based lookups, single-pass algorithms, builders/joins.
- verify: Complexity is linear/log-linear in input size; a scaled input test runs in expected time.
- related: PERF-MEAS-01

### PERF-CACHE-01 · Caches are bounded, invalidated and never the source of truth
- level: contextual | severity: minor–major | provenance: extension
- sources: X14
- why: Unbounded caches leak memory; stale caches serve wrong data; simultaneous expiry floods the backend.
- signals: In-process maps used as caches without eviction; no TTL or invalidation on writes; security decisions based on cached permissions without expiry; caching per-user data under shared keys.
- fix: Bounded LRU/TTL caches; invalidate on writes or accept bounded staleness explicitly; request coalescing; include tenant/user in keys.
- related: REL-RES-02, SEC-DATA-01
