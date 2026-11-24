# Selecting tests for a change

How to decide which tests a change needs, with the least unnecessary cost and no unverified risk
(TEST-SEL-01, P-71). S8 §10.1.6 frames the problem: minimisation removes redundant tests for good,
selection chooses the tests relevant to a change, prioritisation orders them so likely failures
come first; selection is only sound when you can tell which tests a change can affect, so the full
suite keeps running somewhere — at the merge gate while that is practical, behind it once it is not,
and never quietly nowhere. Levels: `levels.md`; database engines: `database-matrix.md`; stages,
optimisation and reporting: `execution.md`; plan and report format:
`../../assets/templates/test-execution-report.md`.

## Contents
1. Inputs · 2. Procedure · 3. The four classes · 4. Change types and their tests · 5. Signals that
widen the selection · 6. Safety nets · 7. Anti-patterns · 8. Worked examples

## 1. Inputs

Gather what exists; record what does not as UNKNOWN rather than guessing.

| Input | Where it comes from | What it tells you |
|---|---|---|
| Diff and changed files | `git diff --name-status <base>...HEAD`; `scripts/test_impact.py PATH --base <ref>` | What changed and its kind (code, test, migration, contract, config, docs, CI) |
| Dependency graph | `scripts/deps.py`, `scripts/test_impact.py` (reverse imports), the build tool's module graph | Who can be affected through imports — a lower bound: reflection, DI wiring and configuration are invisible |
| Public contracts | OpenAPI, Protobuf, Avro, GraphQL schemas, published library APIs, event payloads, shared interfaces | Consumers outside the diff that can break |
| Database changes | Migrations, SQL files, ORM mappings, raw queries, engine-specific constructs | Which database tests and engines are needed (`database-matrix.md`) |
| Configuration and build | Manifests and lockfiles, feature flags, environment files, CI definitions | Behaviour changes without code changes; both flag states (DLV-FLAG-01) |
| Defect history | Bug tracker, incident notes, `scripts/hotspots.py`, files that often change together | Where regressions have escaped before |
| Coverage data | Per-test coverage if the project records it | Which existing tests execute the changed lines — the most direct selection evidence |
| Regression risk | Criticality (money, auth, data loss), blast radius, reversibility | How much residual risk is acceptable |

## 2. Procedure

1. **Classify the change.** Each changed file gets a type (§4). Note mixed diffs: a "docs" PR that
   also edits a config file is not docs-only.
2. **Trace its reach.** Callers and importers, contracts it implements or consumes, tables and
   queries it touches, flags and configuration it reads, jobs and consumers downstream.
3. **Map reach to observing levels.** For each way the change could fail, the lowest level that can
   see that failure (`levels.md` §1).
4. **Find existing tests and gaps.** Tests that already exercise the reach (by coverage, imports,
   naming conventions); the behaviours nothing pins yet become tests to write first (TEST-STRAT-01).
5. **Classify each test group** Required, Recommended, Optional or Not necessary, each with a
   one-line technical reason (§3).
6. **Choose database engines** for the data-layer groups (`database-matrix.md`).
7. **Place each group in a stage** — local, PR, merge queue, scheduled, release (`execution.md` §2).
8. **Write the plan before running**, run it, then record results against the plan
   (TEST-REPORT-01). Unrun Required items make the verdict "not verified", whatever else passed.

## 3. The four classes

| Class | Meaning | Reason it must state |
|---|---|---|
| **Required** | The change can break behaviour that this test group is the cheapest reliable way to observe, and the risk is not acceptable unverified: new or changed behaviour, the regression test for a fixed defect, consumers of a changed contract, engine-specific SQL on that engine, a migration on the real engine, a touched security control | The failure it observes and why nothing cheaper observes it |
| **Recommended** | Plausible impact through a dependency, shared state or configuration; an adjacent critical area; a file with a defect history | The path by which the change could reach it; the residual risk if it is skipped |
| **Optional** | Low probability of impact, or already covered by Required groups; worth running when cheap or in a scheduled stage | Why the probability is low |
| **Not necessary** | No causal path from the change to what the test observes | The missing path — e.g. "CSS only; no data, API or logic change" |

"Not necessary" is a claim and can be wrong: a renamed CSS class used by an end-to-end selector, a
translation string parsed by code, a "comment" in a SQL migration that is actually a hint. Check the
path, then write the reason.

## 4. Change types and their tests

| Change type | Usually Required | Usually Recommended | Usually Not necessary |
|---|---|---|---|
| Documentation or comments only | — (link and spelling checks if configured) | — | All test levels, once the diff is confirmed docs-only |
| UI styling or markup only | Visual or component test of the touched view, if one exists | E2E smoke of the screen if selectors or markup structure changed | Unit tests of domain logic, database tests, contract tests |
| UI component logic | Component tests of the component; unit tests of extracted logic | E2E journey that uses it | Database and migration tests |
| Pure domain logic (rules, calculations) | Unit tests for every changed rule, boundaries on both sides, properties where invariants exist | Component or API tests that exercise the use case | Multi-engine database runs, load tests |
| Application service or orchestration | Component tests of the use case, including error paths | API tests of endpoints using it | Engine matrix unless queries changed |
| Repository, ORM mapping or query | Integration/database tests on the production engine (category B or C) | Tests of callers relying on result order, NULLs or pagination | Unit tests unrelated to the mapping |
| Engine-specific SQL (upsert, JSON operators, locking clauses, window functions, sequences, date arithmetic) | Database tests on that engine and production version (category C) | Concurrency test if locking or isolation is involved (TEST-CONC-01) | Runs on engines the product does not support |
| Migration or schema change | Apply from scratch and from previous release; old/new code against intermediate schema; `scripts/migration_lint.py` leads triaged | Rehearsal on production-sized copy for large tables (DATA-MIG-03) | Unrelated unit tests |
| Public API, event or shared interface | Contract tests for every consumer; API tests of changed endpoints | Consumer-side integration tests | — |
| Widely shared library or utility | Its own unit tests plus the test suites of its main dependents (by reverse dependency) | Full suite of the module if fan-in is high | — |
| Configuration or feature flag | Tests of both flag states (DLV-FLAG-01); startup validation (DLV-CFG-01) | Smoke test in a production-like environment | — |
| Dependency upgrade (lockfile) | Full unit and integration suites of modules using the dependency; contract tests if it serializes data | Full suite, performance check for runtime upgrades | — |
| Build or CI pipeline | A full pipeline run proving every stage still executes and reports | — | — |
| Concurrency, transactions, locking | Concurrency tests that interleave real transactions on the real engine (TEST-CONC-01, DATA-TXN-02) | Load test of the affected path | Single-threaded unit tests as the only evidence |
| Security control (authn, authz, validation, crypto, tenancy) | Negative and abuse tests for the control (TEST-SEC-01); cross-tenant tests (DATA-TENANT-01) | Security scan or DAST of affected endpoints | — |
| Performance-sensitive path | Benchmark or plan comparison on representative data (TEST-PERF-01) | Load test before release | — |

## 5. Signals that widen the selection

Move groups up a class when the change touches a hotspot or a file with past defects; code with high
fan-in; generated code (regeneration changes many paths at once); reflection, dependency-injection
configuration, annotations or conventions that a static graph cannot see; persisted or exchanged
data formats (DATA-EVOL-01); shared test fixtures; anything whose failure is irreversible (money
movement, data deletion, migrations).

## 6. Safety nets

- A full run behind the selective stages: merge queue, scheduled build or release verification
  (S8 §10.1.6). Without one, selection errors accumulate silently.
- Escapes feed back: when a later stage or production finds a defect that a skipped test would have
  caught, record it as a selection miss and widen the rule that skipped it.
- Static impact analysis is a lower bound: where it cannot see (DI containers, configuration,
  dynamic dispatch, SQL built at run time), fall back to the module's full suite.

## 7. Anti-patterns

- Running the whole suite for every change until it is so slow that people skip it.
- Running only tests whose file names match the changed files.
- Verifying a migration or a query with mocked repositories (`database-matrix.md` §4).
- Multiplying the whole suite across database engines when only the data layer depends on them.
- Adding an end-to-end test per change instead of testing at the level that sees the failure.
- Counting "Not necessary" or skipped groups as passed in the report (TEST-REPORT-01).
- Retrying failures until green instead of diagnosing them (TEST-ISO-02).

## 8. Worked examples

**A. Checkout page restyle plus a discount-rule fix, in an application that supports PostgreSQL
and SQL Server.** CSS and template markup: Not necessary for unit, database and contract tests
(no logic or data path); Recommended: the checkout E2E smoke, because the template's form selectors
changed. Discount rule: Required unit tests at 99.99 / 100.00 / 100.01 and a regression test for the
reported bug; Recommended: the API test of the quote endpoint. The rule is pure arithmetic with no
query change, so running it on both engines is Not necessary — the engine matrix is reserved for the
data-access suite.

**B. A repository method rewritten with PostgreSQL `INSERT … ON CONFLICT … DO UPDATE` and a new
unique index, in a service whose tests use SQLite.** Required: database tests on PostgreSQL at the
production major version (category C) — SQLite accepts the same `ON CONFLICT` syntax, but its
types, constraints, locking and concurrency differ, so a pass there is not evidence; a concurrency test with two transactions upserting the same key;
migration applied from scratch and from the previous release; `scripts/migration_lint.py` leads
triaged for the index build. Recommended: API test of the endpoint using the method. Not necessary: unrelated
unit tests.

**C. A JSON library upgrade in a service that publishes events.** Required: the modules' unit and
integration suites that serialize or parse; contract tests against stored and published payload
fixtures (DATA-EVOL-01). Recommended: full suite in the merge queue. Optional: performance check of
the serialization hot path.
