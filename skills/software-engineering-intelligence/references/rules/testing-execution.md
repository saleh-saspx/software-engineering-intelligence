# Testing rules, part 2: selection, engines, environments and reporting (TEST-*)

Which tests run for a change and why, which database engines and environments they need, how
skipped tests are handled, what duplicated execution costs, and how a run is reported so that
nothing unrun is counted as passed. Foundations — strategy, oracles, isolation and flakiness, test
design, coverage, contracts, concurrency, performance and security tests — are in `testing.md`.
Field meanings: `index.md`. Knowledge: `../testing/selection.md`, `../testing/database-matrix.md`,
`../testing/execution.md`. Procedure: `../workflows/test-strategy.md`. Report format:
`../../assets/templates/test-execution-report.md`.

Areas: SEL · DATA · ENV · SKIP · COST · REPORT

### TEST-SEL-01 · Select the tests for a change from its impact, and justify every selection and omission
- level: strong | severity: minor–major | provenance: synthesized
- sources: S8 §10.1.6 (Selecting from the Suite: Regression Selection and Prioritization — selection is sound only when the tests a change can affect are known; run the full suite while that is practical, then decide explicitly what runs at the merge gate and what runs behind it), §10.2.4 (find defects low and early); S1 Ch.12 (Simple Design Rule 1: Runs All the Tests); T-31
- why: Running everything on every change makes feedback slow until people stop running it; running only the tests next to the edited file misses failures that travel through callers, contracts, data and configuration. A plan whose omissions are unexplained cannot be reviewed.
- signals: The same full suite (or the same end-to-end batch) for a typo fix and for a migration; only tests matching the changed file's name run; changes to shared code, contracts, migrations or configuration verified by unit tests alone; "ran the tests" with no statement of which; levels skipped with no reason; no full run anywhere behind a selective merge gate.
- fix: Classify the changed files, trace their reach (callers, contracts, data, configuration, flags), map it to the levels that can observe the failure, and label each test group Required, Recommended, Optional or Not necessary with a one-line reason (`../testing/selection.md`); keep a full run at the merge queue, a scheduled build or release verification to catch selection misses, and widen the selection rules after each miss.
- verify: The plan lists every changed area with its selected tests and reasons and names where the full suite runs; escaped defects are checked against the plan.
- auto: `scripts/test_impact.py` (changed-file classification, mapped test files, database and contract signals — leads for the plan).
- except: Suites that run in a few minutes: run them all and say so.
- related: TEST-STRAT-01, TEST-DATA-02, TEST-REPORT-01, DLV-CI-02

### TEST-DATA-01 · Test query and persistence logic against a real engine
- level: contextual | severity: minor | provenance: extension
- sources: X14; S2 Ch.23 (Database Gateways)
- why: In-memory substitutes and mocks hide dialect, constraint, transaction and locking behaviour.
- signals: SQL tested only via mocks; H2/SQLite standing in for PostgreSQL/MySQL with dialect-specific queries.
- fix: Ephemeral real databases (Testcontainers, Docker) for repository/gateway tests; keep business-rule tests DB-free.
- related: TEST-BEH-02, DATA-SCHEMA-01, TEST-ENV-01, TEST-DATA-02

### TEST-DATA-02 · Run database tests on the engines their behaviour depends on — no more, no fewer
- level: strong | severity: minor–major | provenance: synthesized
- sources: X27 (engine manuals — type, NULL, collation, constraint, DDL and isolation semantics differ between engines); S8 §7.5.2 (fakes can diverge from the real server); X14; T-32
- applies: Code and tests that touch a relational database.
- why: Business rules need no database; SQL whose meaning depends on the engine needs that engine; only products that promise several engines need tests on several. Running every test on every engine buys time cost without evidence, while an embedded stand-in passes tests that the production engine would fail — or fails tests it would pass.
- signals: The whole suite duplicated across engines, DB-free tests included; engine-specific SQL (upserts, JSON operators, locking clauses, sequences, date arithmetic) tested only on SQLite or H2; an Oracle or SQL Server production with tests on an embedded database described as "database tested"; SQLite tests with foreign-key enforcement off; a product sold for several engines with no tests on all of them; CI engine versions differing from production.
- fix: Classify tests A (no database), B (real database, engine-neutral), C (specific engine) and D (several engines for portability) per `../testing/database-matrix.md`; run A once without a database, B on the production engine and major version, C on its engine, D as a focused data-access suite on each supported engine — not the whole suite once per engine.
- verify: The test report names the engines and versions each category ran on; a test that relies on engine semantics is tagged and runs on that engine.
- related: TEST-DATA-01, TEST-ENV-01, DATA-PORT-01, TEST-SEL-01

### TEST-ENV-01 · System and integration tests run against production-like environments and data shapes
- level: contextual | severity: minor–major | provenance: synthesized
- sources: S8 §10.2.3 (system testing in a production-like environment, including non-functional requirements), §14.4.1 (immutable images; pinned versions), §7.5.2 (fakes can diverge; integration tests against real servers remain necessary); X7 (dev/prod parity)
- why: Tests that pass on other engine versions, empty databases, permissive configuration or fakes miss the failures production has: dialect differences, timeouts, TLS, permissions, data volume.
- signals: Integration tests on SQLite or H2 for a PostgreSQL production; dependency versions in test differing from production; tiny or uniform test data, or production data copied without masking; staging configured differently (debug on, authentication off); fakes never checked against the real service.
- fix: Run integration and system tests on the same engines and major versions as production (containers pinned to the production tag); seed realistic masked or synthetic data with production-like volume and distribution where performance matters; keep configuration differences explicit and few; verify fakes against the real dependency periodically (contract or sandbox tests).
- verify: Test and production versions match (compare manifests); fakes are covered by contract or sandbox tests.
- related: TEST-DATA-01, TEST-CONTRACT-01, DATA-PRIV-01, DLV-CFG-01

### TEST-SKIP-01 · No silently skipped or disabled tests
- level: strong | severity: minor | provenance: direct
- sources: S1 T4 (An Ignored Test Is a Question about an Ambiguity); S1 G4 (Overridden Safeties)
- why: A skipped test is an unanswered question about behaviour; it rots into permanent blindness.
- signals: `@Disabled`, `@Ignore`, `skip`, `xit`, `t.Skip()` without reason or ticket; commented-out tests.
- fix: Fix or delete; if a skip is necessary, give a reason and a tracking issue.
- verify: No skip/ignore without reason and issue link in the diff.
- related: CODE-STRUCT-05, TEST-ISO-02

### TEST-COST-01 · Remove duplicated test execution, not unique coverage
- level: contextual | severity: minor | provenance: synthesized
- sources: S8 §10.1.6 (minimisation removes redundant tests; tests overlap in what they detect), §10.2.4 (the ice-cream cone of slow end-to-end tests); X14
- why: Duplicate tests and duplicate jobs cost minutes on every run and make failures noisier, but a test that looks redundant may be the only one exercising a path with real wiring, data or configuration. Deleting by appearance trades a measured cost for an unmeasured risk.
- signals: Identical or near-identical test bodies in several files; the same suite run by several CI workflows or matrix entries with no differing dimension; end-to-end tests re-checking rules already pinned by unit tests; DB-free tests run once per database engine; blanket reruns of whole jobs.
- fix: List the overlap (`scripts/test_smells.py` duplicate-body leads, CI definitions, timings from `scripts/test_report.py`); for each candidate show what else covers the same behaviour — coverage per test, mutation results or a reasoned trace — before merging or removing it; deduplicate jobs and matrix dimensions; move overlapping end-to-end checks down a level; keep any test that is the only check of a path, an integration or a past defect.
- verify: Coverage of the affected code and the mutation score of critical modules are unchanged afterwards, and the time saved is measured.
- related: TEST-STRAT-02, DLV-CI-02, TEST-SEL-01, TEST-MUT-01

### TEST-REPORT-01 · A test report accounts for the plan: what ran, what did not, where, and what remains unverified
- level: strong | severity: minor–major | provenance: synthesized
- sources: S7 §1.2 (testing shows the presence of defects, not their absence); S8 §10.1.6 (decide explicitly what runs where; a slow suite must not quietly become an unrun suite), §10.2.4 (flaky tests are quarantined, then fixed or deleted)
- why: "All tests passed" usually means "the tests that ran passed". Skipped categories, engines not covered, tests that passed only on retry and stages that never ran disappear from a green summary, and readers take the summary as evidence that the application is correct.
- signals: Pass counts that include skipped or unrun tests; reports without the commands run, engines and versions, or durations; tests that passed on retry reported as plain passes; "CI is green" used as a release decision while required stages did not run; no list of remaining risks.
- fix: Report the changed scope and risk, the selected tests with their class, the executed tests with commands and results, skipped and unrun tests with reasons, engines and versions per category, durations, failures and retries, remaining risks, and a scoped verdict (`../../assets/templates/test-execution-report.md`); never count a test that did not run as passed.
- verify: Planned and executed counts reconcile; every Required group has an observed result or is listed as not run, and the verdict follows from them.
- auto: `scripts/test_report.py` (JUnit XML and `go test -json` results, optionally against a plan: executed, failed, skipped, groups not run or incomplete, flaky tests, results that differ between environments, durations).
- related: AGT-EVID-01, AGT-EVID-03, TEST-ISO-02, TEST-SEL-01
