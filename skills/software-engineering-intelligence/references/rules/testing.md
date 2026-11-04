# Testing rules (TEST-*)

Test strategy, unit-test quality, isolation, behavioural focus, boundaries, regression,
coverage interpretation, contracts, security tests. Field meanings: `index.md`. The safe
refactoring procedure that depends on these rules is `../workflows/refactoring.md`.

Areas: STRAT · UNIT · ISO · BEH · BND · REG · COV · CONTRACT · DATA · SEC · SKIP

### TEST-STRAT-01 · Every behaviour change ships with tests at the cheapest level that pins it
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 Ch.9 (The Three Laws of TDD; Tests Enable the -ilities); S1 Ch.12 (Simple Design Rule 1: Runs All the Tests); S1 T1 (Insufficient Tests)
- why: Untested behaviour can't be refactored safely and regresses silently; tests at the lowest sufficient level stay fast and precise.
- signals: Feature/bug-fix diffs with no test changes; logic only exercised by end-to-end tests; "will add tests later".
- fix: Add unit tests for rules and edge cases, integration tests for wiring and queries, and a thin end-to-end check for critical paths. TDD is one way, not the requirement.
- verify: The new tests fail without the change (or on the bug) and pass with it — run them and report the result.
- except: Pure configuration/copy changes; spikes explicitly marked throwaway.
- related: TEST-REG-01, TEST-STRAT-02, AGT-EVID-01

### TEST-STRAT-02 · The test portfolio fits the architecture and keeps feedback fast
- level: contextual | severity: minor | provenance: extension
- sources: X5 (test pyramid); S1 T9 (Tests Should Be Fast); S2 Ch.28 (The Test Boundary)
- why: Slow suites stop being run; suites of only unit tests miss integration failures. The right shape depends on where the logic lives.
- signals: Suite takes so long that developers skip it; majority of tests are browser/E2E; or plenty of unit tests on mocks but no test touches the real database queries.
- fix: Rule-rich core → many unit tests; integration-heavy CRUD services → more integration tests against real dependencies in containers, fewer mocks ("honeycomb"); a few E2E smoke tests. Parallelise and split slow tiers in CI.
- verify: Local suite runs in minutes; CI runs slower tiers on merge.
- related: TEST-DATA-01, TEST-CONTRACT-01

### TEST-UNIT-01 · Tests are F.I.R.S.T.
- level: strong | severity: minor–major | provenance: direct
- sources: S1 Ch.9 (F.I.R.S.T. — Fast, Independent, Repeatable, Self-Validating, Timely)
- why: Each property removes a reason to stop trusting or running the tests.
- signals: Sleeps and real timeouts; tests depending on execution order; output that must be inspected manually; tests that pass only on one machine or time zone.
- fix: Inject clocks and randomness; isolate state per test; assert, don't print; run in random order.
- verify: Suite passes repeatedly in random order and in parallel.
- related: TEST-ISO-01, REL-TIME-03

### TEST-UNIT-02 · One concept per test, named for the behaviour
- level: strong | severity: minor | provenance: direct
- sources: S1 Ch.9 (One Assert per Test; Single Concept per Test); T-09
- why: A failing test should tell you what behaviour broke without debugging.
- signals: `test1`, `testOrder`; long tests covering several scenarios; assertions about unrelated behaviours in one test.
- fix: Split by scenario; names like `rejects_negative_quantity` / `returnsCachedValueWhenFresh`; clear arrange–act–assert (given–when–then) structure. Several assertions about one outcome are fine.
- verify: Each test name states one behaviour; a failure message identifies the broken behaviour.
- related: TEST-UNIT-03

### TEST-UNIT-03 · Test code is clean code
- level: strong | severity: minor | provenance: direct
- sources: S1 Ch.9 (Keeping Tests Clean; Clean Tests; Domain-Specific Testing Language)
- why: Messy tests become a liability that blocks change instead of enabling it.
- signals: Copy-pasted setup walls; conditionals/loops computing expected values; magic fixtures shared across hundreds of tests.
- fix: Builders/factories and small helper DSLs; expected values as literals; local fixtures.
- verify: Tests read as specifications; no loops/conditionals compute expected values.
- related: TEST-UNIT-02

### TEST-ISO-01 · Tests are isolated from shared state and uncontrolled environment
- level: strong | severity: major | provenance: direct
- sources: S1 Ch.9 (F.I.R.S.T. — Independent, Repeatable); S1 Ch.13 (Testing Threaded Code)
- why: Shared databases, global singletons, real network, wall-clock time and unseeded randomness make tests flaky and order-dependent.
- signals: Tests that fail when run alone or in parallel; reliance on data from earlier tests; network calls to real third parties; `datetime.now()` in assertions.
- fix: Per-test transactions or fresh containers; fakes for third-party services at the boundary; injected clocks; seeded randomness.
- verify: The suite passes in random order, in parallel, and offline.
- related: TEST-ISO-02, DES-DI-02

### TEST-ISO-02 · Flaky tests are defects, not noise
- level: strong | severity: major | provenance: synthesized
- sources: S1 Ch.13 (Treat Spurious Failures as Candidate Threading Issues); S1 T4 (An Ignored Test Is a Question about an Ambiguity)
- why: Retrying until green trains everyone to ignore red builds, and intermittent failures often signal real concurrency bugs.
- signals: CI auto-retry of tests; "known flaky" lists without owners; tests re-run until they pass.
- fix: Quarantine with an owner and deadline, diagnose (ordering, timing, shared state, races), fix.
- verify: Quarantined tests have owners and dates; CI has no blanket retries.
- related: TEST-ISO-01, REL-CONC-01

### TEST-BEH-01 · Test behaviour through stable interfaces, not implementation details
- level: strong | severity: minor–major | provenance: direct
- sources: S2 Ch.28 (Tests as System Components; Design for Testability — the Fragile Tests Problem; The Testing API)
- why: Tests coupled to internal structure break on every refactoring, so people stop refactoring or stop trusting tests.
- signals: Tests asserting private method calls or call order of internals; tests reaching into private fields; GUI tests for business rules; mocks verifying every interaction.
- fix: Test through public behaviour or a dedicated testing API; assert outcomes (returned values, persisted state, emitted events), not steps.
- verify: A behaviour-preserving refactoring leaves tests green.
- related: TEST-BEH-02, ARCH-BND-04

### TEST-BEH-02 · Mock at boundaries you own; don't mock what you don't own or value types
- level: contextual | severity: minor | provenance: synthesized
- sources: S2 Ch.28; S1 Ch.8 (Learning Tests; Using Code That Does Not Yet Exist)
- why: Mocking third-party APIs encodes your assumptions about them (often wrong); mocking everything tests the mocks.
- signals: Mocks of HTTP client libraries, ORMs or SDK classes; mocked value objects; the class under test partially mocked.
- fix: Wrap the third party in an adapter you own (CODE-BND-01) and fake that; cover the adapter with integration or learning tests; use real value objects.
- related: CODE-BND-01, TEST-DATA-01

### TEST-BND-01 · Test boundary conditions and the neighbourhood of bugs
- level: strong | severity: minor–major | provenance: direct
- sources: S1 T5 (Test Boundary Conditions), T6 (Exhaustively Test Near Bugs), T7 (Patterns of Failure Are Revealing); S1 G3
- why: Defects cluster at edges and near other defects.
- signals: No tests for empty, one, many, max, negative, null, Unicode, time-zone and leap cases; a bug fixed with a single test.
- fix: Table-driven/parameterised tests over boundary values; property-based tests where invariants are clear.
- verify: Parameterised cases cover empty/one/many/max/invalid inputs.
- related: CODE-CPLX-04, TEST-REG-01

### TEST-REG-01 · Every fixed defect gets a test that failed before the fix
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 T6; S1 Ch.9; X14
- why: Without it, the same bug returns with the next refactoring.
- signals: Bug-fix commits without test changes.
- fix: Reproduce the bug in a test first, watch it fail, then fix.
- verify: Report the before/after test runs you actually observed.
- related: TEST-STRAT-01, AGT-EVID-01

### TEST-REG-02 · Pin current behaviour before refactoring
- level: strong | severity: major | provenance: synthesized
- sources: S1 Ch.16 (First, Make It Work; Then Make It Right); S1 Ch.14 (On Incrementalism); X4 (characterization tests)
- why: Refactoring is only safe if something tells you when behaviour changed; legacy code rarely has tests.
- signals: Refactoring plans with no test step; "it's just moving code".
- fix: Write characterization tests capturing current outputs (including odd ones) for the code paths you will touch; then refactor in small steps, running them each time.
- verify: Characterization tests pass before and after each step; differences are investigated, not "updated".
- related: AGT-MIN-02, TEST-BEH-01

### TEST-COV-01 · Read coverage as "what was never executed", not "what was verified"
- level: strong | severity: minor | provenance: synthesized
- sources: S1 T2 (Use a Coverage Tool!), T8 (Test Coverage Patterns Can Be Revealing); S7 §1.2 (testing shows presence, not absence, of bugs)
- why: Coverage proves code ran, not that outcomes were checked; 100% coverage with weak assertions verifies little, and coverage targets invite assertion-free tests.
- signals: Coverage gates without review of assertions; tests with no assertions; high coverage on getters, low on rules.
- fix: Use coverage to find untested risky code (rules, error paths, security checks); consider mutation testing for critical modules.
- verify: Coverage gaps on risky code are listed; mutation score checked where adopted.
- related: TEST-STRAT-01, AGT-EVID-03

### TEST-CONTRACT-01 · Verify contracts at service and API boundaries
- level: contextual | severity: major | provenance: extension
- sources: X14 (consumer-driven contracts, schema checks); S4 (interfaces and published contracts as architectural decisions)
- why: Independently deployed services break each other through unverified assumptions about payloads and semantics.
- signals: Integration only tested in shared staging; breaking changes found in production; no schema validation in CI.
- fix: Consumer-driven contract tests or schema compatibility checks (OpenAPI diff, Protobuf/Avro compatibility rules) in CI.
- related: API-CONTRACT-01, DES-LSP-01

### TEST-DATA-01 · Test query and persistence logic against a real engine
- level: contextual | severity: minor | provenance: extension
- sources: X14; S2 Ch.23 (Database Gateways)
- why: In-memory substitutes and mocks hide dialect, constraint, transaction and locking behaviour.
- signals: SQL tested only via mocks; H2/SQLite standing in for PostgreSQL/MySQL with dialect-specific queries.
- fix: Ephemeral real databases (Testcontainers, Docker) for repository/gateway tests; keep business-rule tests DB-free.
- related: TEST-BEH-02, DATA-SCHEMA-01

### TEST-SEC-01 · Security controls have tests, including negative cases
- level: strong | severity: major | provenance: direct
- sources: S5 How to Use the Code Review Guide (testing code reviews — each security control should have appropriate unit test cases); S6 §2.9 (Deriving Security Test Requirements), §2.10 (Security Tests Integrated in Development and Testing Workflows)
- why: Authorisation and validation code is easy to break in refactoring and its failures are silent (everything still "works").
- signals: No test asserting a 403 for another user's object; no tests for rejected inputs; security fixes without regression tests.
- fix: Abuse-case tests: wrong user, wrong tenant, anonymous, tampered IDs, oversized/malicious input, replay.
- verify: Negative tests exist for each authorisation and validation control in the change.
- related: SEC-AUTHZ-02, SEC-VAL-01, TEST-REG-01

### TEST-SKIP-01 · No silently skipped or disabled tests
- level: strong | severity: minor | provenance: direct
- sources: S1 T4 (An Ignored Test Is a Question about an Ambiguity); S1 G4 (Overridden Safeties)
- why: A skipped test is an unanswered question about behaviour; it rots into permanent blindness.
- signals: `@Disabled`, `@Ignore`, `skip`, `xit`, `t.Skip()` without reason or ticket; commented-out tests.
- fix: Fix or delete; if a skip is necessary, give a reason and a tracking issue.
- verify: No skip/ignore without reason and issue link in the diff.
- related: CODE-STRUCT-05, TEST-ISO-02
