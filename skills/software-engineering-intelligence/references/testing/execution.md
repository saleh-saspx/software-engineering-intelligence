# Running tests: optimisation, stage policy and reporting

Make the selected tests (`selection.md`) give trustworthy answers quickly, place each group in the
stage where its cost fits, and report the result without overstating it. The constraint throughout:
**speed is bought with smarter scheduling, never with unverified changes.** A speed-up that drops
Required verification is not an optimisation; if it happens, the report says so (TEST-REPORT-01).

## Contents
1. Optimisation techniques · 2. Stage policy · 3. Flaky tests · 4. Duplication and waste ·
5. Measuring cost · 6. Reporting rules

## 1. Optimisation techniques

| Technique | Use it when | Watch out for |
|---|---|---|
| Avoid duplicate runs | The same tests run in several jobs, workflows or matrix entries with no differing dimension | Removing a job that differs in an unnoticed way (engine version, flag state, locale) — compare definitions first |
| Incremental selection | The suite outgrows the feedback budget (S8 §10.1.6) | Static impact analysis misses reflection, DI wiring and configuration; keep a full run behind it |
| Dependency mapping | Monorepos and multi-module builds | Build-tool graphs (Gradle, Maven, Bazel, Nx, Go packages) are more complete than import scans; prefer them |
| Prioritisation | Long suites: run recently failed, changed-area and historically fragile tests first | Prioritising is not skipping — the rest still runs |
| Parallel execution | Tests are independent: no shared rows, files, ports, global state | Hidden order dependence appears as flakiness; run in random order to expose it (TEST-ISO-01) |
| Serial execution | Tests share an external resource by design: one schema, a singleton broker, a rate-limited sandbox | Isolate them into their own serial group instead of serialising the whole suite |
| Test isolation | Always: per-test data, unique identifiers, injected clocks | Shared fixtures mutated by tests |
| Database isolation | Transaction-per-test rollback; schema or database per worker; template databases cloned per worker | Rollback hides commit-time behaviour (deferred constraints, triggers, isolation): tests of those need real commits and their own cleanup |
| Caching | Dependency downloads, build outputs, container images | Caching test results only when the key covers every input: source, lockfiles, migrations, configuration, engine version |
| Failure-based stopping | Fast feedback stages: stop a job early when a critical group fails | Not in release verification, where the full list of failures is the point |
| Timeouts | Every test and every job; concurrent tests in particular (TEST-CONC-01) | A timeout raised to hide slowness instead of finding it |
| Resource limits | Containers and parallel workers on shared runners | Over-parallelising until database or CPU contention causes timeouts that look like flakiness |
| CI layout | Split by recorded timings, shard evenly, cache, run slow suites behind the merge gate | Sharding that hides which shard skipped what — reports must aggregate |

## 2. Stage policy

| Stage | Budget (guide) | Runs | Database engines | Never skipped |
|---|---|---|---|---|
| Local development | Seconds to a few minutes | Tests of the code being edited; affected unit and component tests; quick database tests if a container is running | Production engine in a container when touching data code; none otherwise | Tests you are adding (see them fail first, TEST-MUT-01) |
| Pull-request validation | About ten minutes for blocking checks (DLV-CI-02, S8 §14.2.4) | Required and Recommended groups from the plan; lint, type checks, static analysis; contract tests for changed contracts; migration apply checks | Production engine for B and C groups; the primary engine for D | Required groups — if one cannot run, the PR is "not verified", not "green" |
| Main branch or merge queue | Tens of minutes | Full unit, component and integration suites on the production engine; selection safety net (S8 §10.1.6) | Production engine; D on the primary engine | The full suite somewhere at or behind this gate |
| Scheduled (nightly) | Hours | Full engine matrix (D), full end-to-end suite, fuzzing, mutation testing on critical modules, longer performance runs | All supported engines and versions | Rotation of long suites so each runs at a known frequency |
| Release verification | As long as the risk needs | Full regression on a production-like environment; migration rehearsal on production-sized data (DATA-MIG-03); load test for capacity-relevant releases; security scans; rollback rehearsal (DLV-REL-02) | Every engine and version production runs | Migrations, both states of live flags, smoke tests |
| Production deployment gate | Minutes | Smoke tests, canary health metrics, synthetic checks; no long suites | Production itself (read-only checks) | Automatic rollback criteria |

Budgets are guides: a regulated domain or a small team may choose differently — state the choice.

## 3. Flaky tests

A test that both passes and fails on the same commit is flaky (S8 §10.2.4 lists the usual causes:
asynchronous timing, shared mutable state, order dependence, unstable external dependencies).
Diagnose instead of rerunning everything:

1. **Confirm** with run history: the same test, same commit, same environment, different outcomes —
   `scripts/test_report.py --same-environment RUN1 RUN2 …` flags tests that pass in one report file and
   fail in another. Without that flag the files are treated as different environments (engines,
   versions, platforms): a test that fails on one engine and passes on another is a failure on that
   engine, not a flake.
2. **Locate the cause**: rerun the single test many times; rerun the suite in random order with a
   recorded seed; run it alone; compare failing runs' timing, parallelism and data; look for sleeps,
   wall-clock reads, shared fixtures, real network (`scripts/test_smells.py` leads).
3. **Act**: when the cause is known and the fix is small, fix it now and remove its retries in the
   same change; otherwise quarantine it visibly — it still runs and is reported, without blocking —
   with an owner and a date, then fix or delete it (TEST-ISO-02). Retries are acceptable only as data
   gathering — a test that passes on retry is reported as flaky, not as passed.
4. **Suspect real defects**: intermittent failures in concurrent code are often races (TEST-CONC-01).

## 4. Duplication and waste

Look for identical test bodies (`scripts/test_smells.py` duplicate-test leads), suites run by several
workflows, DB-free tests run once per engine, end-to-end tests re-checking rules the unit tests already
pin, and blanket reruns of whole jobs. Before removing anything, show what else covers the same
behaviour — coverage per test, mutation results, or a reasoned trace — and keep any test that is the
only check of a path, an integration or a past defect (TEST-COST-01). Measure the time saved.

## 5. Measuring cost

Use recorded durations, not impressions: `scripts/test_report.py` reads JUnit XML (pytest
`--junitxml`, Maven Surefire and Failsafe, Gradle, PHPUnit `--log-junit`, Jest and Vitest JUnit
reporters, .NET loggers) and `go test -json` output, and prints the slowest tests and suites, totals
per report and planned-but-not-run groups. Track the pull-request stage's wall-clock time and its
variance; a budget that is regularly exceeded leads to skipped runs.

## 6. Reporting rules

Use `../../assets/templates/test-execution-report.md`. The invariants:

- A test that was not executed is never reported as passed. Skipped, quarantined, filtered,
  not-selected and not-run tests are listed separately, each group with its reason.
- A successful test command is evidence about the tests it ran, on the engines and environment it
  ran on — not proof that the application is correct (P-36, AGT-EVID-03).
- Flaky passes after retries are reported as flaky.
- Engines and versions are named for every database category.
- The verdict is one of: **failed** (a test that ran failed, in any group — a defect or a broken
  test, and either way not verified), **not verified** (a Required group did not run, or passed only
  on retry), **partially verified** (every Required group passed, but Recommended ones did not run or
  were flaky — residual risks listed), **verified for the stated scope** (every Required group ran and
  passed, and nothing failed).
- Remaining risks name what was not covered and why: no production-sized data, engine not
  available, contract consumer not reachable.
