# Test levels: what each one proves, what it cannot see, and when to choose it

A test's level is set by the failure it must be able to observe. Pick the lowest level that can see
that failure with a trustworthy oracle; going higher adds cost and flakiness without adding evidence,
going lower produces tests that pass while the real failure is invisible to them. Not every project
needs every level — the portfolio follows where the logic and the risk live (TEST-STRAT-02, T-17).

S8 §10.2 names unit, integration, functional, system and acceptance testing and smoke tests, and
gives the economics (find defects low and early; avoid the ice-cream cone of slow end-to-end tests).
The other levels below are common industry practice (extension). Selection for a specific change:
`selection.md`; which database engines a test needs: `database-matrix.md`; where each level runs
and how results are reported: `execution.md`.

## Contents
1. Quick chooser · 2. The levels · 3. Cross-cutting purposes · 4. Common mistakes

## 1. Quick chooser

| The failure you fear | Lowest level that can observe it |
|---|---|
| A rule, calculation, parser or state transition is wrong | Unit |
| A module's collaborators are wired or called wrongly inside the process | Component |
| SQL, ORM mapping, transaction, serializer or framework configuration is wrong | Integration / database |
| A provider and its consumers disagree about a payload or its meaning | Contract |
| An HTTP or RPC endpoint mishandles status codes, validation, auth or errors | API |
| A schema change breaks running code, locks a table, or loses data | Migration |
| A user journey across services or screens breaks | End-to-end (a few) |
| Latency, throughput or capacity misses a stated target | Performance / load |
| A control can be bypassed or input abused | Security |
| A forbidden dependency or layering violation appears | Architecture |
| The system does the wrong thing for the user even though it meets the spec | Acceptance (validation) |

## 2. The levels

Format: **purpose and scope** · **verify** · **do not verify here** · **depends on** · **cost** ·
**typical tooling** · **select when**.

**Unit** — one function, class or small module, isolated from I/O. Verify: outputs per equivalence
class and boundary, error paths, invariants and round-trips (TEST-DESIGN-01, TEST-PROP-01). Not
here: SQL semantics, framework wiring, network, configuration — mocking those tests the mock
(TEST-BEH-02). Depends on: nothing external; injected clock and randomness. Cost: milliseconds; every
commit. Tooling: pytest/Hypothesis, JUnit 5/jqwik, Go `testing`, PHPUnit/Pest, Jest/Vitest/fast-check,
xUnit. Select when: logic changed; always for a logic bug fix (TEST-REG-01).

**Component** — one deployable module or service through its public interface, with its own
in-process collaborators real and its external dependencies faked at the boundary. Verify: use
cases end to end inside the process, wiring, validation, error mapping. Not here: the real
database's semantics or other services' behaviour. Depends on: fakes or stubs for owned ports
(checked against the real thing by contract or integration tests). Cost: tens to hundreds of
milliseconds. Tooling: framework test slices (Spring `@WebMvcTest`, Laravel feature tests, Django
test client), in-process HTTP servers. Select when: orchestration or application-service code
changed.

**Integration** — your code against one real dependency: database, message broker, cache, file
system, a third-party sandbox. Verify: queries and mappings, transactions, serialization, retries
and timeouts, configuration. Not here: business rules already pinned by unit tests. Depends on: the
real dependency in a container at the production major version (TEST-ENV-01). Cost: seconds per
test plus container start. Tooling: Testcontainers, Docker Compose, framework test databases.
Select when: an adapter, repository, query, mapping or client configuration changed.

**Contract** — the agreement between a provider and its consumers: fields, types, status codes,
error shapes, event schemas and the semantics consumers rely on (TEST-CONTRACT-01/02). Verify:
backward compatibility and that each implementation of a shared interface behaves alike. Not here:
full behaviour of either side. Depends on: contract files (OpenAPI, Protobuf, Avro, Pact). Cost:
seconds; every PR touching a contract. Select when: a published API, event, schema or shared
interface changed — including "internal" ones other teams deploy against.

**API** — the running service's endpoints over the real protocol. Verify: routing, authentication
and authorisation (including negative cases, TEST-SEC-01), validation, status codes, pagination,
idempotency (API-IDEMP-01). Not here: every rule permutation (unit level does that). Depends on:
the service with its real database or a seeded copy. Cost: tens of milliseconds to seconds per
call. Tooling: REST Assured, supertest, pytest with httpx, Postman/Newman. Select when: endpoint,
middleware, security filter or serialization changed.

**Database** — the data layer's own guarantees on the real engine: constraints reject invalid rows,
uniqueness under concurrency, isolation-dependent invariants, triggers, views, stored procedures,
query results including NULL, collation and ordering. Verify: what the schema promises (DATA-SCHEMA-01)
and engine-specific behaviour the code relies on. Not here: business rules expressible without the
database. Depends on: the production engine and version (category B/C in `database-matrix.md`).
Cost: seconds. Select when: schema, query, transaction or engine-specific SQL changed.

**Migration** — schema and data changes applied to realistic states. Verify: apply from an empty
database and from the previous release; old and new application versions work against the
intermediate schema; backfills are idempotent and resumable; duration and locks on a production-sized
copy (DATA-MIG-03). Not here: application features. Depends on: production engine and version,
production-like volume for timing. Cost: minutes to hours for rehearsal; run the fast part on every
migration PR, rehearsal before release. Tooling: the migration tool, `scripts/migration_lint.py`
for leads. Select when: any migration, type change, index on a large table or data backfill.

**End-to-end** — a deployed system exercised through its outer interface (browser, mobile client,
public API) across services. Verify: a handful of critical journeys and the wiring between
deployables. Not here: rules, permutations, error codes — they belong lower. Depends on: a full
environment and test data. Cost: seconds to minutes per test; most flake-prone (S8 §10.2.4). Tooling:
Playwright, Cypress, Selenium, Appium. Select when: a journey's wiring changed; keep the suite small
and reliable.

**Performance** — response time and resource use of a path against a fit criterion (TEST-PERF-01).
Verify: percentiles and spread over repeated runs, with warm-up, on representative data. Not here:
correctness. Cost: minutes; scheduled or before release. Tooling: JMH, pytest-benchmark, Go
benchmarks, BenchmarkDotNet; `EXPLAIN ANALYZE` for single queries. Select when: a change claims to
speed something up, touches a latency-sensitive path, or changes query plans on large tables.

**Load and stress** — the system under expected peak (load) and beyond it until it degrades
(stress), including recovery. Verify: throughput, saturation points, back-pressure, connection-pool
and lock behaviour, failure mode under overload. Cost: hours of environment time; scheduled or
pre-release. Tooling: k6, Gatling, JMeter, Locust. Select when: capacity-relevant changes,
pooling or timeout changes, new hot paths, launches.

**Security** — controls under attack: negative and abuse cases (TEST-SEC-01), fuzzing of parsers
(TEST-FUZZ-01), static and dependency analysis, dynamic scanning with WSTG test IDs. Not here: a
claim that the system is secure (SEC-PROC-04). Cost: from milliseconds (negative unit tests) to hours
(DAST, fuzzing). Select when: authentication, authorisation, input handling, crypto, tenancy, new
trust boundary or dependency changed.

**Architecture** — structural rules checked automatically: dependency direction, forbidden imports,
cycles, layering, naming of packages (ARCH-DEP-01). Cost: seconds. Tooling: ArchUnit, deptrac,
import-linter, `go vet`-style custom checks, `scripts/deps.py --forbid`. Select when: the codebase
has stated boundaries worth protecting; run on every PR once they exist.

**Acceptance** — validation that the right thing was built: acceptance criteria as executable
examples (TEST-VV-01), plus user acceptance, demos, beta and production monitoring for what tests
cannot judge (S8 §10.2.3). Not here: internal design. Cost: varies; executable criteria are usually
component or API tests. Select when: a requirement is new or changed.

**Smoke** — a fast, shallow check that a build or deployment is alive (S8 §10.2.3). Gate after every
deploy and in each release verification (DLV-REL-02); never a substitute for the levels above.

## 3. Cross-cutting purposes

**Regression** is a purpose, not a level: re-running existing tests after a change to see that
nothing that worked broke. Which regression tests to run is the selection question (`selection.md`);
every fixed defect adds a regression test at the level where it was observable (TEST-REG-01).
Performance and security are likewise types that appear at several levels; choose their level by
the failure they target, as in §1.

## 4. Common mistakes

- Pushing database behaviour into unit tests with mocked repositories: the SQL is never executed, so
  dialect, constraint and transaction defects pass.
- Testing rules end to end: slow, flaky and unable to cover the boundaries.
- Calling a component test with an in-memory database an "integration test" of the real engine.
- A contract changed with only the provider's tests run.
- Load tests on empty databases or uniform data: plans and lock behaviour differ from production.
- Adding an end-to-end test for every change until the suite is too slow to run (S8 §10.2.4).
