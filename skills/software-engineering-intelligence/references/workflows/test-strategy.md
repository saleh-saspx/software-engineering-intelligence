# Workflow: test strategy, verification and validation

For planning how a system, feature or release will be verified and validated, and for assessing
whether an existing test suite deserves trust. Rules: `../rules/testing.md`. Plan template:
`../../assets/templates/test-strategy.md`. Adding a safety net to legacy code before a refactoring
is covered in `refactoring.md`.

Verification asks "did we build it right?" (against the specification); validation asks "did we
build the right thing?" (against the need) — S8 §10.2.3. Testing shows the presence of defects,
never their absence (S7 §1.2, S8 Ch.10): a strategy decides where the remaining risk is acceptable.

## Contents
1. Risks and quality goals · 2. Verification and validation map · 3. Portfolio shape · 4. Test
design per risk · 5. Oracles · 6. Non-functional verification · 7. Adequacy · 8. Environments and
data · 9. Pipeline economics · 10. Release verification · 11. Assessing an existing suite ·
12. Report

## 1. Risks and quality goals
- What would a failure cost — money, data, safety, reputation — and where have defects escaped
  before (bug history, incidents, `scripts/hotspots.py`)?
- Quality requirements with measurable fit criteria (TEST-VV-01, ARCH-QA-01); unknown ones become
  stated assumptions.
- Constraints: coverage criteria mandated by a domain standard are constraints (T-22); the team's
  existing tools and CI.

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
integration-heavy shape is right for thin-logic services (T-17).

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
| Data layer | Real engine; migrations applied in CI; constraint tests | TEST-DATA-01, DATA-MIG-03 |
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
(TEST-ENV-01, TEST-CONTRACT-01).

## 9. Pipeline economics
Stages ordered by cost, with merge-blocking stages around ten minutes (DLV-CI-02); test selection
and prioritisation when the suite grows (S8 §10.1.6) — never silent skipping (TEST-SKIP-01);
fuzzing, mutation testing and long load tests in scheduled or non-blocking stages.

## 10. Release verification
Smoke test after each deploy, canary health gates, a rehearsed rollback (DLV-REL-02); both states of
each live feature flag tested (DLV-FLAG-01).

## 11. Assessing an existing suite
1. **Inventory**: `python3 scripts/repo_survey.py PATH` (tests, CI) and
   `python3 scripts/test_smells.py PATH` — skipped or focused tests, sleeps, wall-clock and
   unseeded randomness, real network calls, assertion-free tests, tests that only verify mocks,
   expected values derived from the code under test. These are leads; confirm by reading.
2. **Run** the suite and record duration and failures; run it twice, or in random order, if cheap.
3. **Read** the tests of the riskiest modules (hotspots, money, authorisation): oracles,
   boundaries, negative cases, coupling to implementation details.
4. **Seed a few plausible defects** into a scratch copy of a critical module — flip a comparison,
   drop a rounding step, skip a permission check — or run the project's mutation tool, and see
   which survive. This is the most persuasive single measure of a suite's strength.
5. **Rate** the testing-and-verification dimension (`../quality-model.md` §3.4) with evidence and
   confidence.

## 12. Report
Plans use the test-strategy template. Assessments use the review-report format, with findings
typed `test-gap` (or `defect` when a test exposes wrong behaviour). Lead with the three to five
changes that most reduce risk, each with a first step and a way to check it worked (for example,
"the new boundary tests fail on the seeded `>=` mutant").
