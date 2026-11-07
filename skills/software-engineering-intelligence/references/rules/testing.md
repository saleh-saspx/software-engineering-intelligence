# Testing rules (TEST-*)

Test strategy, verification versus validation, oracles, test-design criteria, unit-test quality,
isolation, behavioural focus, boundaries, regression, coverage interpretation and criteria,
property-based and mutation testing, contracts, data, concurrency, performance, environments,
fuzzing and security tests. Field meanings: `index.md`. Planning and assessing a test suite:
`../workflows/test-strategy.md`; the safe refactoring procedure that depends on these rules is
`../workflows/refactoring.md`.

Areas: STRAT · VV · ORACLE · DESIGN · UNIT · ISO · BEH · BND · REG · COV · PROP · MUT · CONTRACT ·
DATA · CONC · PERF · ENV · FUZZ · SEC · SKIP

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
- sources: X5 (test pyramid); S1 T9 (Tests Should Be Fast); S2 Ch.28 (The Test Boundary); S8 §10.2.4 (Testing Pyramid — detect defects low and early; the ice-cream-cone anti-pattern); T-17
- why: Slow suites stop being run; suites of only unit tests miss integration failures. The right shape depends on where the logic lives.
- signals: Suite takes so long that developers skip it; majority of tests are browser/E2E; or plenty of unit tests on mocks but no test touches the real database queries.
- fix: Rule-rich core → many unit tests; integration-heavy CRUD services → more integration tests against real dependencies in containers, fewer mocks ("honeycomb"); a few E2E smoke tests. Parallelise and split slow tiers in CI.
- verify: Local suite runs in minutes; CI runs slower tiers on merge.
- related: TEST-DATA-01, TEST-CONTRACT-01

### TEST-VV-01 · Verify against the specification and validate against the need: acceptance criteria become executable tests
- level: strong | severity: major | provenance: direct
- sources: S8 §10.2.3 (verification — did we build the product right? — versus validation — did we build the right product?, after Boehm; acceptance and user acceptance testing; Given/When/Then criteria become acceptance tests), §3.4.1 (acceptance criteria define done and seed tests), §3.4.4 (Tracing Requirements to Tests — forward and backward tracing through a stable story key), §3.1.3 (measurable fit criteria for quality requirements)
- why: Code can pass every test and still be wrong when the tests encode the developer's reading of the requirement instead of the requirement; without traceability nobody can tell which requirements are verified, or what to retest when one changes.
- signals: Features merged without acceptance criteria; tests derived only from the implementation; a must-have requirement with no passing scenario; quality requirements with no fit criterion or test; specification and code disagreeing (a rounding rule, a limit) unnoticed; hand-maintained traceability matrices gone stale.
- fix: Write acceptance criteria as concrete examples (Given/When/Then) carrying the requirement's key; automate them at the cheapest level that exercises the behaviour; reference the key from tests and commits; give quality requirements measurable fit criteria and a test or monitor; validate with users (demo, UAT, beta) what tests cannot.
- verify: Every must-have requirement in scope maps to at least one passing acceptance test; each quality requirement maps to a test or monitor with a threshold.
- related: ARCH-QA-01, TEST-ORACLE-01, TEST-STRAT-01, AGT-UNC-01

### TEST-ORACLE-01 · Every test has an oracle independent of the code under test
- level: strong | severity: major | provenance: direct
- sources: S8 §10.1.4 (Test Oracles — the oracle problem; strategies from exact expected values, through property and round-trip oracles and differential oracles, to human judgement), §13.2.7 (a generated test encodes the model's belief about correct behaviour, which may match a misunderstanding in the code; humans own the oracle)
- why: A test whose expected value comes from the implementation — computed by the same function, copied from its output, or a regenerated snapshot — passes when the code is wrong; it pins the bug instead of catching it.
- signals: Expected values computed by calling the code under test or by re-implementing its formula in the test; snapshots or golden files updated whenever they fail; AI-generated tests that assert whatever the code currently returns; assertions that only check "no exception"; mocks returning the values the assertion then checks.
- fix: Take expected values from the specification, worked examples or independently computed literals. Where exact values are impractical, use properties and round-trips (decode(encode(x)) equals x), metamorphic relations, or a differential comparison with a reference implementation or the previous release. Review snapshot updates as behaviour changes.
- verify: Each expected value traces to a requirement, an example or an independent computation; seeded defects make the tests fail (TEST-MUT-01).
- related: TEST-VV-01, TEST-MUT-01, TEST-PROP-01, TEST-BEH-01

### TEST-DESIGN-01 · Select test inputs by explicit criteria: partitions, boundaries, iterations and combinations
- level: strong | severity: minor–major | provenance: direct
- sources: S8 §10.1.2 (Test Selection — black-box and white-box criteria; mature teams use both), §10.4.1 (Equivalence-Class Coverage — valid and invalid classes, after Myers), §10.4.2 (Boundary-Value Coverage — just below, at and just above each boundary), §10.3.2 (zero, one and many loop iterations), §10.6 (Combinatorial Testing — pairwise covers most interaction faults; 3-way or higher for critical subsystems, after Kuhn et al.)
- why: Tests chosen by intuition cluster on the happy path. Explicit criteria find the cases where defects hide and make "do we have enough tests?" a checkable question.
- signals: One or two valid inputs per rule; no invalid classes (wrong type, out of range, empty, malformed); boundaries tested on one side only; loops never run zero times; options and feature flags tested only in their default combination; tests added without saying which class or boundary they cover.
- fix: For each rule list the valid and invalid equivalence classes and test one representative of each; test just below, at and just above every boundary; zero, one and many for loops and collections; for interacting parameters (options, flags, platforms) generate a pairwise set — 3-way for critical subsystems; keep the cases visible in table-driven tests.
- verify: The test table names its classes and boundaries; every boundary has below/at/above cases; combination tests come from a stated model.
- related: TEST-BND-01, TEST-PROP-01, TEST-UNIT-02, DLV-FLAG-01

### TEST-UNIT-01 · Tests are F.I.R.S.T.
- level: strong | severity: minor–major | provenance: direct
- sources: S1 Ch.9 (F.I.R.S.T. — Fast, Independent, Repeatable, Self-Validating, Timely); S8 §10.2.1 (FIRST properties of unit tests)
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
- sources: S1 Ch.13 (Treat Spurious Failures as Candidate Threading Issues); S1 T4 (An Ignored Test Is a Question about an Ambiguity); S8 §10.2.4 (flaky-test causes — races and async timing, shared mutable state, order dependence, unstable dependencies; quarantine, then fix or delete)
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
- sources: S2 Ch.28; S1 Ch.8 (Learning Tests; Using Code That Does Not Yet Exist); S8 §10.2.1 (stubs, mocks and fakes), §7.5.2 (fakes can diverge from the real server, so integration tests against real servers remain necessary)
- why: Mocking third-party APIs encodes your assumptions about them (often wrong); mocking everything tests the mocks.
- signals: Mocks of HTTP client libraries, ORMs or SDK classes; mocked value objects; the class under test partially mocked.
- fix: Wrap the third party in an adapter you own (CODE-BND-01) and fake that; cover the adapter with integration or learning tests; use real value objects.
- related: CODE-BND-01, TEST-DATA-01

### TEST-BND-01 · Test boundary conditions and the neighbourhood of bugs
- level: strong | severity: minor–major | provenance: direct
- sources: S1 T5 (Test Boundary Conditions), T6 (Exhaustively Test Near Bugs), T7 (Patterns of Failure Are Revealing); S1 G3; S8 §10.4.2 (below, at and above each boundary), §10.3.2 (zero, one and many loop iterations)
- why: Defects cluster at edges and near other defects.
- signals: No tests for empty, one, many, max, negative, null, Unicode, time-zone and leap cases; a bug fixed with a single test.
- fix: Table-driven/parameterised tests over boundary values; property-based tests where invariants are clear.
- verify: Parameterised cases cover empty/one/many/max/invalid inputs.
- related: CODE-CPLX-04, TEST-REG-01

### TEST-REG-01 · Every fixed defect gets a test that failed before the fix
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 T6; S1 Ch.9; S8 §10.1.5 (never trust a test you have never seen fail); X14
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
- sources: S1 T2 (Use a Coverage Tool!), T8 (Test Coverage Patterns Can Be Revealing); S7 §1.2 (testing shows presence, not absence, of bugs); S8 §10.1.3 (coverage is a floor, not a ceiling; low coverage is a real alarm; managing to a number yields assertion-free tests)
- why: Coverage proves code ran, not that outcomes were checked; 100% coverage with weak assertions verifies little, and coverage targets invite assertion-free tests.
- signals: Coverage gates without review of assertions; tests with no assertions; high coverage on getters, low on rules.
- fix: Use coverage to find untested risky code (rules, error paths, security checks); consider mutation testing for critical modules.
- verify: Coverage gaps on risky code are listed; mutation score checked where adopted.
- related: TEST-STRAT-01, AGT-EVID-03, TEST-COV-02, TEST-MUT-01

### TEST-COV-02 · Choose coverage criteria by risk; complex decisions in critical code need condition-level coverage
- level: contextual | severity: minor–major | provenance: direct
- sources: S8 §10.1.3 (coverage is a floor, not a ceiling), §10.3.2 (statement, branch and path coverage; path implies branch implies statement), §10.5 (condition versus decision coverage; MC/DC — each condition shown to flip the outcome independently, usually with N + 1 tests; required at DO-178C Level A; splitting compound conditions into nested ifs can hide untested conditions); T-22
- applies: Safety-, money- or security-critical decision logic, and regulated domains whose standards prescribe coverage criteria (those criteria are constraints).
- why: Line coverage says a compound condition ran, not that each part of it was ever decisive: `isAdmin || (isOwner && !locked)` can be fully line-covered while the `locked` case is never tested.
- signals: Critical boolean decisions with several conditions exercised by one or two tests; a uniform branch-coverage gate while critical modules have no stronger criterion; nested ifs introduced to raise branch coverage of a compound condition.
- fix: Branch coverage as the default floor where the team tracks coverage; for critical compound decisions, MC/DC pairs or an explicit decision table; treat low coverage on risky code as an alarm and never a high number as proof.
- verify: Critical decisions list their condition cases; each condition has a pair of tests that differ only in that condition.
- related: TEST-COV-01, TEST-DESIGN-01, SEC-AUTHZ-01

### TEST-PROP-01 · Check invariants and round-trips with generated inputs where they exist
- level: contextual | severity: minor–major | provenance: synthesized
- sources: S8 §10.1.4 (property-based testing generates many inputs and checks properties on each; Hypothesis, jqwik, fast-check, rapid, PropCheck); X21 Ch.2 (loop invariants as correctness arguments)
- applies: Code with clear invariants: parsers and serializers, calculations (money, pricing, scheduling), data structures, sorting and merging, state machines, encoders.
- why: Hand-picked examples miss the inputs nobody thought of; a property checked against thousands of generated inputs, shrunk to a minimal counter-example on failure, finds edge cases cheaply.
- signals: Parsers and serializers tested with a few hand-written examples; pricing or allocation code with no test of conservation properties (totals preserved, never negative, independent of item order); custom data structures tested only on happy paths.
- fix: State the invariant (round-trip, idempotence, conservation, ordering, commutativity, "the result is one of the inputs") and check it with the ecosystem's property-based tool; keep shrunk counter-examples as regression cases; for critical algorithms, also write the loop invariant as an assertion or comment.
- verify: Property tests run in CI with a fixed or logged seed; counter-examples found are kept as example tests.
- related: TEST-ORACLE-01, TEST-DESIGN-01, TEST-FUZZ-01

### TEST-MUT-01 · See every test fail before trusting it; use mutation testing selectively on critical code
- level: strong | severity: minor–major | provenance: direct
- sources: S8 §10.1.5 (Mutation Testing — never trust a test you have never seen fail; mutants killed or surviving; mutation score; survivors point to missing assertions; expensive, so use it selectively; PIT, Stryker, mutmut, go-mutesting, mutant), §13.2.7 (introduce the defect, confirm the expected failure, then count the pass)
- why: A test that cannot fail verifies nothing. Wrong assertions, assertions on mocks and tests that never reach the code all pass forever, and coverage reports count them as protection.
- signals: New tests added green without anyone seeing them red; high line coverage with few assertions; critical calculations or authorisation logic never mutation-tested; surviving mutants on boundary operators (`<` versus `<=`) in money or limit checks.
- fix: For each new test, break the behaviour (or revert the fix) and confirm the test fails for the expected reason; run a mutation tool on critical modules (pricing, authorisation, parsing) on a schedule or on changed files, and add tests for surviving mutants that matter.
- verify: The red run is shown in the change description or log; the mutation score of critical modules is tracked and surviving mutants are triaged.
- related: TEST-COV-01, TEST-REG-01, TEST-ORACLE-01, AGT-EVID-01

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
- related: TEST-BEH-02, DATA-SCHEMA-01, TEST-ENV-01

### TEST-CONC-01 · Test concurrent code for safety and liveness under real interleavings
- level: strong | severity: major | provenance: synthesized
- sources: S1 Ch.13 (Testing Threaded Code — more threads than processors, varied configurations, instrumentation to force failures); X17 Ch.12 (Testing Concurrent Programs — testing for correctness and for liveness; generating more interleavings; pitfalls); S8 §10.2.4 (race conditions and async timing as causes of flaky tests)
- why: Sequential unit tests cannot show a race, a deadlock or a lost update. Concurrency defects appear only under contention, and then look like flaky tests.
- signals: Locks, atomics, queues or async workers covered only by sequential tests; tests that wait with sleep; no race detector or thread sanitizer in CI where the language has one; check-then-act code (stock, balances, coupons) never tested with parallel requests; concurrent tests without timeouts, which hang on a deadlock.
- fix: Stress tests that release many workers at once (barrier or latch), with more threads than cores, asserting invariants afterwards; race detectors and stress harnesses where available (Go `-race`, ThreadSanitizer, OpenJDK `jcstress`); parallel-request tests for check-then-act paths; a timeout on every concurrent test; waiting on conditions instead of sleeping.
- verify: The race detector or sanitizer runs in CI for concurrent packages; the stress test fails when a deliberate race is introduced.
- related: REL-CONC-01, SEC-RACE-01, TEST-ISO-02, REL-CONC-04

### TEST-PERF-01 · Performance and load tests are representative and statistically honest
- level: contextual | severity: minor–major | provenance: synthesized
- sources: X19 Ch.2 (An Approach to Performance Testing — micro-, meso- and macrobenchmarks; throughput, batching and response time; variability; test early, test often); S8 §12.6–12.8 (dispersion, quartiles and confidence intervals; never report a before/after change without an interval), §3.1.3 (fit criteria such as p95 latency at a stated load), §10.2.3 (system testing covers non-functional requirements)
- applies: Changes justified by performance, capacity planning, latency-sensitive paths, and quality requirements with performance fit criteria.
- why: One run of a microbenchmark on a laptop measures warm-up, caches and noise; averages hide the tail users feel; a "20% faster" claim from two runs is often variance.
- signals: Hand-rolled timing loops without warm-up; benchmarks whose result is never used (dead-code elimination); single runs; averages without percentiles or spread; load tests against empty databases or unrealistic data; performance claims in reviews with no numbers.
- fix: A benchmark harness with warm-up for microbenchmarks (JMH, pytest-benchmark, Go `testing.B`, BenchmarkDotNet); end-to-end measurement for decisions; p50/p95/p99 and spread over repeated runs, with an interval for before/after comparisons; load tests with production-like data volume and traffic mix; the benchmark kept next to the code.
- verify: Results state warm-up, run count, percentiles and spread; the before/after difference lies outside run-to-run variation.
- related: PERF-MEAS-01, PERF-SCALE-03, TEST-ENV-01

### TEST-ENV-01 · System and integration tests run against production-like environments and data shapes
- level: contextual | severity: minor–major | provenance: synthesized
- sources: S8 §10.2.3 (system testing in a production-like environment, including non-functional requirements), §14.4.1 (immutable images; pinned versions), §7.5.2 (fakes can diverge; integration tests against real servers remain necessary); X7 (dev/prod parity)
- why: Tests that pass on other engine versions, empty databases, permissive configuration or fakes miss the failures production has: dialect differences, timeouts, TLS, permissions, data volume.
- signals: Integration tests on SQLite or H2 for a PostgreSQL production; dependency versions in test differing from production; tiny or uniform test data, or production data copied without masking; staging configured differently (debug on, authentication off); fakes never checked against the real service.
- fix: Run integration and system tests on the same engines and major versions as production (containers pinned to the production tag); seed realistic masked or synthetic data with production-like volume and distribution where performance matters; keep configuration differences explicit and few; verify fakes against the real dependency periodically (contract or sandbox tests).
- verify: Test and production versions match (compare manifests); fakes are covered by contract or sandbox tests.
- related: TEST-DATA-01, TEST-CONTRACT-01, DATA-PRIV-01, DLV-CFG-01

### TEST-FUZZ-01 · Fuzz parsers and decoders that take untrusted input
- level: contextual | severity: major | provenance: direct
- sources: S8 §10.4.2 (fuzz testing sends random or malformed inputs and checks for crashes, hangs and memory errors; a security mainstay, after Miller et al.; it belongs in a non-blocking pipeline stage)
- applies: Code that parses files, network protocols, documents, images, archives, query languages, templates or serialized data from untrusted sources — above all in memory-unsafe languages, and custom parsers anywhere.
- why: Parsers face an unbounded input space. Example tests cover the shapes developers imagine; attackers send the others. Fuzzers find the crashes, hangs and memory errors that become denial of service or code execution.
- signals: Hand-written parsers or decoders of external formats with only example tests; C, C++ or `unsafe` Rust parsing code without fuzz targets; production crashes on malformed input; no size or depth limits on nested input.
- fix: Fuzz targets for each parser entry point with the ecosystem's tooling (Go native fuzzing, libFuzzer or AFL++, Jazzer, Atheris, cargo-fuzz), seeded with real samples; run them with sanitizers in a scheduled or non-blocking CI stage; keep crashing inputs as regression tests; enforce size, depth and time limits.
- verify: Fuzz targets exist for the parser entry points and run on a schedule; crashes found are fixed and kept as regression inputs.
- related: SEC-MEM-01, SEC-VAL-01, TEST-PROP-01, SEC-GATE-01

### TEST-SEC-01 · Security controls have tests, including negative cases
- level: strong | severity: major | provenance: direct
- sources: S5 How to Use the Code Review Guide (testing code reviews — each security control should have appropriate unit test cases); S6 §2.9 (Deriving Security Test Requirements), §2.10 (Security Tests Integrated in Development and Testing Workflows); S8 §11.2.1 (access control needs explicit design review because feature tests may not reveal it)
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
