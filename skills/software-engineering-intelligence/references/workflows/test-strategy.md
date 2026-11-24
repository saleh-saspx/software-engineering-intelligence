# Workflow: test strategy, verification and validation

For planning how a system, feature or release will be verified and validated, for choosing the tests
a specific change needs, and for assessing whether an existing test suite deserves trust. Rules:
`../rules/testing.md` (foundations) and `../rules/testing-execution.md` (selection, engines,
environments, skipped tests, cost, reporting). Knowledge: `../testing/levels.md` (what each level proves),
`../testing/selection.md` (tests for a change), `../testing/database-matrix.md` (which engines),
`../testing/execution.md` (stages, optimisation, flaky tests, reporting). Templates:
`../../assets/templates/test-strategy.md` (system or release plan) and
`../../assets/templates/test-execution-report.md` (plan and results for a change). Adding a safety
net to legacy code before a refactoring is covered in `refactoring.md`.

Verification asks "did we build it right?" (against the specification); validation asks "did we
build the right thing?" (against the need) — S8 §10.2.3. Testing shows the presence of defects,
never their absence (S7 §1.2, S8 Ch.10): a strategy decides where the remaining risk is acceptable.

## Contents
1. Risks, quality goals and stack · 2. Verification and validation map · 3. Portfolio shape · 4. Test
design per risk · 5. Oracles · 6. Non-functional verification · 7. Adequacy · 8. Environments and
data · 9. Pipeline economics · 10. Release verification · 11. Assessing an existing suite ·
12. Tests for a specific change · 13. Report

## 1. Risks, quality goals and stack
- What would a failure cost — money, data, safety, reputation — and where have defects escaped
  before (bug history, incidents, `scripts/hotspots.py`)?
- Quality requirements with measurable fit criteria (TEST-VV-01, ARCH-QA-01); unknown ones become
  stated assumptions.
- Constraints: coverage criteria mandated by a domain standard are constraints (T-22); the team's
  existing tools and CI.
- Stack: languages, frameworks, test runners, and the database engines and versions in production
  and in tests (`scripts/repo_survey.py` reports what it can detect). Anything not established is
  UNKNOWN, with the conclusions that depend on it named.

## 2. Verification and validation map
- For each requirement in scope: acceptance criteria as Given/When/Then examples → the tests that
  automate them (TEST-VV-01). Flag must-haves with no passing scenario.
- Validation that tests cannot do: demos, user acceptance, beta, experiments, production monitoring.
- A disagreement between specification and code found while mapping is a finding — a `defect` or a
  `question` about the requirement — not something to "fix" silently in either direction.

## 3. Portfolio shape
Rules and calculations → unit tests; adapters → integration tests on real engines; service and API
boundaries → contract tests; critical journeys → a few end-to-end tests; every deploy → a smoke test
(TEST-STRAT-01, TEST-STRAT-02). Avoid the ice-cream cone of slow end-to-end tests; an
integration-heavy shape is right for thin-logic services (T-17). What each level proves and does not:
`../testing/levels.md`.

## 4. Test design per risk
| Risk | Technique | Rules |
|---|---|---|
| Input handling, calculations | Equivalence classes (valid and invalid) and boundaries (below, at, above), table-driven | TEST-DESIGN-01, TEST-BND-01 |
| Complex decisions | Decision tables; MC/DC pairs for critical compound conditions | TEST-COV-02 |
| Workflows and states | Transition tests, including invalid and out-of-order transitions | SEC-BIZ-01 |
| Many options, flags or platforms | Pairwise combinations; 3-way for critical subsystems | TEST-DESIGN-01, DLV-FLAG-01 |
| Invariants, parsers, serializers | Property-based tests and round-trips | TEST-PROP-01 |
| Parsers of untrusted input | Fuzzing in a non-blocking stage | TEST-FUZZ-01 |
| Concurrency | Stress tests, race detectors, parallel-request tests | TEST-CONC-01 |
| Security controls | Negative and abuse cases per control | TEST-SEC-01 |
| Data layer | Real engine chosen by the database matrix; migrations applied in CI; constraint tests | TEST-DATA-01, TEST-DATA-02, DATA-MIG-03 |
| Money, rates, quantities | Exact expected values at the rounding boundaries; precision and overflow limits of the stored types | DATA-TYPE-01, DATA-TYPE-02 |
| Fixed defects | Regression test seen failing before the fix | TEST-REG-01 |

## 5. Oracles
In order of preference (TEST-ORACLE-01, S8 §10.1.4): exact expected values from the specification
or worked examples → properties, invariants and round-trips → differential comparison with a
reference implementation or the previous release (useful for refactorings and migrations) → recorded
human judgement (approval tests). Red flags: expected values computed by the code under test,
snapshots updated whenever they fail, generated tests that assert the code's current output.

## 6. Non-functional verification
- Performance and load — fit criteria, warm-up, percentiles, repeated runs, production-like data
  (TEST-PERF-01, PERF-SCALE-03).
- Concurrency — TEST-CONC-01.
- Security — gates at the right stages (SEC-GATE-01), negative tests, fuzzing, WSTG test IDs for
  dynamic checks.
- Data — migration rehearsal (DATA-MIG-03) and restore drills (DATA-BACKUP-01).
- Resilience — injected timeouts and dependency failures (REL-ERR-01, REL-TIME-01).

## 7. Adequacy
- Coverage is a floor and an alarm on risky code, never a target (TEST-COV-01, T-22); stronger
  criteria only for critical decisions (TEST-COV-02).
- Every new test is seen failing; critical modules get mutation testing on a schedule, and
  surviving mutants are triaged (TEST-MUT-01).
- Flaky tests are quarantined with an owner and a date, never retried blindly (TEST-ISO-02).

## 8. Environments and data
Engines and major versions match production; containers pinned; data masked or synthetic but
realistic in volume and distribution where it matters; fakes checked against the real dependency
(TEST-ENV-01, TEST-CONTRACT-01). Decide per test category which engines it needs — none, the
production engine, a specific engine, or every supported engine (`../testing/database-matrix.md`);
an embedded stand-in is never the evidence for engine behaviour (T-32).

## 9. Pipeline economics
Stages ordered by cost, with merge-blocking stages around ten minutes (DLV-CI-02); change-based
selection and prioritisation when the suite grows, with the full suite still running at or behind
the merge gate (S8 §10.1.6, TEST-SEL-01, T-31) — never silent skipping (TEST-SKIP-01); fuzzing,
mutation testing, full engine matrices and long load tests in scheduled or release stages. Stage
policy, optimisation techniques, flaky-test diagnosis and duplicate removal:
`../testing/execution.md` (TEST-COST-01). When the request is to cut pipeline time, place every
suite in a stage — a short table of suite → local, pull request, main, nightly or release, each with
its reason — and say what leaves the pull-request path and what still guards it there. Estimate the
saving from recorded step timings and measure it after the change (`../testing/execution.md` §5).

## 10. Release verification
Smoke test after each deploy, canary health gates, a rehearsed rollback (DLV-REL-02); both states of
each live feature flag tested (DLV-FLAG-01); every engine and version production runs.

## 11. Assessing an existing suite
1. **Inventory**: `python3 scripts/repo_survey.py PATH` (tests, CI, database engines) and
   `python3 scripts/test_smells.py PATH` — skipped or focused tests, sleeps, wall-clock and
   unseeded randomness, real network calls, assertion-free tests, tests that only verify mocks,
   expected values derived from the code under test, duplicated test bodies. These are leads;
   confirm by reading.
2. **Run** the suite and record duration and failures; run it twice, or in random order, if cheap.
   With JUnit XML or `go test -json` output, `python3 scripts/test_report.py RESULTS…` gives totals
   and the slowest tests; add `--same-environment` when the files are reruns of the same commit on
   the same environment, so tests that flip between them are reported as flaky (otherwise runs are
   treated as different environments, such as engines, and a failure in one counts as a failure).
3. **Read** the tests of the riskiest modules (hotspots, money, authorisation): oracles,
   boundaries, negative cases, coupling to implementation details.
4. **Seed a few plausible defects** into a scratch copy of a critical module — flip a comparison,
   drop a rounding step, skip a permission check — or run the project's mutation tool, and see
   which survive. This is the most persuasive single measure of a suite's strength.
5. **Check the execution economics**: duplicated jobs, DB-free tests multiplied across engines,
   end-to-end tests re-testing unit-level rules, blanket retries (TEST-COST-01, TEST-ISO-02).
6. **Rate** the testing-and-verification dimension (`../quality-model.md` §3.4) with evidence and
   confidence.

## 12. Tests for a specific change
For a pull request, a fix or a release candidate — "which tests should run, and did they?":
1. `python3 scripts/test_impact.py PATH --base <ref>` for leads: changed files by type, tests that
   import or are named after them, database and contract signals, engine-specific SQL.
2. Trace what the tool cannot see (DI wiring, configuration, dynamic SQL) and map each way the
   change could fail to the lowest level that can observe it (`../testing/levels.md` §1).
3. Classify each test group Required, Recommended, Optional or Not necessary with a technical reason
   (`../testing/selection.md` §3) and choose engines by category (`../testing/database-matrix.md`).
4. Write the plan in the execution-report template before running; run; record observed results,
   skipped and unrun groups with reasons, engines and versions, durations, failures and flaky
   retries (TEST-REPORT-01).
5. Give the verdict in the template's vocabulary — verified for the stated scope, partially
   verified, not verified, failed — and name the remaining risks. Keep the reply proportionate: a
   small change gets the plan and results in a few lines, not the full template.

## 13. Report
System and release plans use the test-strategy template; plans and results for a change use the
execution-report template. Assessments use the review-report format, with findings typed `test-gap`
(or `defect` when a test exposes wrong behaviour). Lead with the three to five changes that most
reduce risk, each with a first step and a way to check it worked (for example, "the new boundary
tests fail on the seeded `>=` mutant"). Never count a test that did not run as passed, and never
present a green run as proof that the application is correct.
