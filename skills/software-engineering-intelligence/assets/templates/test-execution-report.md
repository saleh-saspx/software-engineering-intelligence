# Test plan and execution report: <change, PR or release>

<!-- One document for the plan (fill before running) and the results (fill after). Selection:
     references/testing/selection.md; engines: references/testing/database-matrix.md; stages and
     reporting rules: references/testing/execution.md (TEST-SEL-01, TEST-DATA-02, TEST-REPORT-01).
     Never count a test that did not run as passed. Drop sections with nothing to say. -->

## Changed scope
<!-- What changed: files or modules, contracts, migrations, configuration, dependencies.
     Stack and engines as established; anything not established is UNKNOWN. -->
- **Change:** <PR #, commit range or release>
- **Areas:** <modules / contracts / migrations / config touched>
- **Stack and engines:** <language, framework; production DB engine and version or UNKNOWN; test DB engine>

## Risk assessment
<!-- What could break, how badly, and how likely; defect history of the touched areas. -->
| Risk | Impact | Likelihood | Observed by (level) |
|---|---|---|---|
| <rounding change breaks invoice totals> | high | medium | unit, API |

## Selected tests
<!-- The plan. Every group gets a class and a one-line technical reason. -->
| Test group | Level | Class | Reason | Stage | Engines |
|---|---|---|---|---|---|
| <pricing unit tests> | unit | Required | <changed rule; boundaries 99.99/100.00/100.01> | PR | none (A) |
| <order repository tests> | database | Required | <new ON CONFLICT upsert, PostgreSQL-specific> | PR | PostgreSQL 16 (C) |
| <checkout E2E smoke> | end-to-end | Recommended | <form selectors changed> | merge queue | PostgreSQL 16 |
| <reporting module tests> | unit | Not necessary | <no import, data or config path from the change> | — | — |

## Executed tests
<!-- Commands actually run and their observed results. -->
| Command | Tests | Passed | Failed | Skipped | Duration |
|---|---|---|---|---|---|
| <`pytest tests/pricing -q`> | <42> | <42> | <0> | <0> | <3.1 s> |

## Skipped or not run
<!-- Every Required or Recommended group that did not run, and every skipped/quarantined test. -->
| Test group or test | Status | Reason | Residual risk |
|---|---|---|---|
| <SQL Server data-access suite> | not run | <no SQL Server image in this environment> | <upsert path unverified on SQL Server> |

## Database engines tested
| Category | Engines and versions | Tests | Result |
|---|---|---|---|
| A | none | | |
| B | | | |
| C | | | |
| D | | | |

## Duration
<!-- Totals per stage; the slowest suites if they matter for the budget. -->

## Failures
<!-- Each failure: test, observed error, classification (defect, test defect, environment, flaky),
     and the next step. Tests that passed only on retry are listed here as flaky. -->

## Remaining risks
<!-- What this run does not show: untested engines or versions, no production-sized data, contracts
     whose consumers were not run, behaviour only validation can judge. -->

## Verdict
<!-- One of, checked in this order: failed (a test that ran failed) · not verified (a Required
     group did not run, or passed only on retry) · partially verified (Required groups passed;
     Recommended ones did not run or were flaky) · verified for the stated scope.
     State the scope. A passing run is evidence about the tests that ran, not proof of correctness. -->
