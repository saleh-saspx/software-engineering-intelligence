# CI review: run time and the "100% pass"

## Summary
**Verdict:** changes requested.

**The 100% isn't real.** `summary.sh` counts skipped tests as passes and only runs after both pytest steps have passed, so whenever it prints, it prints 100%. In both of your runs, 2 of the 9 tests never ran, and they're the only two concurrency tests in those runs. One of them, `test_locking`, doesn't run on any CI engine, PostgreSQL included, because of a string mismatch. If unit tests and DB tests on PostgreSQL are both meant to run, run 1042 is **not verified** and run 1041 **failed**.

**Time:** each push to a PR branch starts the workflow twice, and each run tests three engines. So the unit and DB suites each run 6 times where once is enough. The changes below cut 8 jobs to 3 without losing coverage of anything the product ships with, and they add `test_locking`. I can't promise minutes: your JUnit test cases total about 7.5 s per run, so most of the 45 minutes is in things these files don't record.

## Scope
- **Read in full:** README.md, ci.yml, summary.sh, pytest.ini, both JUnit files and the three test files.
- **Not reviewed (not provided):** `shop/`, `conftest.py` (where the `db` fixture lives), `requirements-dev.txt`, `test_inventory.py`, `test_reports.py`, `tests/e2e/`, and the Actions logs with step timings. Neither JUnit file says which engine it ran on, or whether 1041 and 1042 were the same commit.
- **Assumptions:** PostgreSQL 16 is the only production engine, and unit tests use no database (both from the README). Your default branch is `main`.

## Verification
| Check | Command | Result |
|---|---|---|
| Your summary on each file, then both | `bash scripts/summary.sh reports/…` | 88% / 100% / 94% |
| Both runs as reruns of one commit, against a plan requiring unit tests and DB tests on PostgreSQL | `python3 test_report.py --same-environment --plan plan.json run1041=… run1042=…` | 7 of 9 ran per run; same 2 skipped in both; `test_expired_cart` failed, then passed; **not verified** (1042 alone: same) |
| Your `test_orders.py` under each `DB_ENGINE` value (pytest 9.1.1 on Python 3.13 here, not your 3.12) | `DB_ENGINE=<value> pytest tests/db/test_orders.py -rs` | `test_locking` skipped for `postgres:16`, `mysql:8.0`, `sqlite` and unset; runs only for exactly `postgres` (`test_upsert` errors here: no `db` fixture) |
| Your summary on pytest's XML from that `postgres:16` run (0 passed, 1 error, 1 skipped) | `bash scripts/summary.sh …` | `pass rate: 100%` |
| pytest's exit code when every selected test is skipped | `pytest … -k locking` | 0, so the job is green |
| `--reruns` without the rerun plugin installed | `pytest --reruns 3 …` | usage error, exit 4 |
| Test-smell scan | `python3 test_smells.py tests` | 1 lead: `time.sleep(2)` at `test_cart.py:13` |
| New summary and fixed skip, on the same inputs | as above | 1042: "ran 7: 7 passed … skipped, not run: 2", both named; error, empty or missing input exit 1; `postgres:16` now reaches `test_locking` |
| New ci.yml | PyYAML parse | parses; not schema-checked (no actionlint here); not run on GitHub |

Not run: your unit and DB tests against your code (no `shop` package, `db` fixture or database server here).

## Findings

### F-01 [major · confirmed] `test_locking` never runs, not even on PostgreSQL
- **Where:** `tests/db/test_orders.py:11`, `.github/workflows/ci.yml:15`
- **Type:** test-gap · **Rule:** TEST-SKIP-01
- **What:** the test is skipped unless `DB_ENGINE == "postgres"`. CI sets `postgres:16`, `mysql:8.0` or `sqlite`, so it's skipped on every leg, and anywhere else without that exact value.
- **Why it matters:** order locking is never checked. pytest exits 0 when tests are skipped, so nothing turns red.
- **Fix:** match the prefix (diff below). Or delete the skip, since the product and the new DB job are PostgreSQL-only.
- **Evidence:** I ran the real file under each value. It's also skipped in both JUnit files.

### F-02 [major · confirmed] The pass rate can only ever say 100%
- **Where:** `scripts/summary.sh:3-6`, `.github/workflows/ci.yml:16`
- **Type:** defect · **Rule:** TEST-REPORT-01
- **What:** it counts `<testcase` tags and subtracts `<failure` tags. So skipped tests count as passed, setup and fixture errors (`<error>`) aren't counted at all, and retries are invisible. The step has no `if:`, so it only runs when both pytest steps passed.
- **Why it matters:** the number on the PR tells you nothing. For run 1042 it says 100% while 2 of the 9 tests didn't run.
- **Fix:** the replacement below prints counts and names every skipped test. It also runs when tests fail, and exits 1 if nothing ran.
- **Evidence:** it printed 100% for a pytest run in which nothing passed.

### F-03 [major · likely] `test_expired_cart` is flaky, and `--reruns 3` hides it
- **Where:** `tests/unit/test_cart.py:11-14`, `.github/workflows/ci.yml:13,15,21`
- **Type:** test-gap · **Rule:** TEST-ISO-02
- **What:** the test gives a cart a 2 s lifetime, sleeps exactly 2 s and then asserts that it has expired. That's right on the boundary, so the result depends on clock resolution and on whether `Cart` compares with `>` or `>=`. It also can't catch a cart that counts as expired from the start. And every job retries a failing test up to 3 more times.
- **Why it matters:** it's the only failure in run 1041, and it runs 6 times per push. Retries turn flaky failures into passes, and a failing test can run up to 4 times.
- **Fix:** inject a clock and test both sides of the 2 s limit (sketch below). That needs a small change to `shop/cart.py`, which I haven't seen. Drop `--reruns` in the same PR.
- **Evidence:** it failed in 1041 and passed in 1042. If both runs were the same commit, that makes it flaky by definition. The cause comes from reading the code; I didn't reproduce it.

### F-04 [major · confirmed] Both concurrency tests are switched off
- **Where:** `tests.unit.test_inventory::test_reserve_concurrently`, `tests.db.test_orders::test_locking`
- **Type:** test-gap · **Rule:** TEST-CONC-01
- **What:** the first is skipped as "flaky, see #881", with no owner or date that I can see. The second is F-01.
- **Why it matters:** nothing in the unit or DB suites checks that stock can't be reserved twice or that an order lock holds. When concurrent code fails only some of the time, the cause is often a real race. So #881 may be a bug in the product, not in the test.
- **Fix:** give #881 an owner and a date. Then un-skip the test on your machine and run it a few hundred times in a loop to see whether the test or the reservation code is racy.
- **Evidence:** skipped in both JUnit files. I didn't have the test's source.

### F-05 [major · confirmed] Most of the test work is duplicated
- **Where:** `.github/workflows/ci.yml:2,6-8,13,15`
- **Type:** performance · **Rule:** TEST-COST-01
- **What:** `on: [pull_request, push]` starts the workflow twice for every push to a PR branch, and each run has three engine legs. That's 8 jobs per push. The unit suite runs 6 times as the exact same command (the unit step doesn't even set `DB_ENGINE`). The DB suite runs 6 times, and only 2 of those runs are on the PostgreSQL leg.
- **Why it matters:** runner time and queueing. MySQL and SQLite results say nothing about a PostgreSQL-only product (SQLite differs on locking and types), yet their failures still turn the PR red.
- **Fix:** the ci.yml below. That's 3 jobs per push, with each suite running once.
- **Evidence:** read from ci.yml and the README. I haven't measured the minutes saved.

### F-06 [major · possible] Is the PostgreSQL leg actually running on PostgreSQL 16?
- **Where:** `.github/workflows/ci.yml:4-15`, `conftest.py` (not provided)
- **Type:** question · **Rule:** TEST-DATA-02
- **What:** there's no `services:` block, so the `db` fixture has to start or choose the database itself. If it checks `DB_ENGINE == "postgres"` the way the skip did, `postgres:16` may be getting a different engine.
- **Why it matters:** in that case the DB suite isn't running on your production engine.
- **Fix:** have the fixture log the result of `SELECT version()` once in the DB job. I kept `DB_ENGINE: postgres:16` so the fixture gets the same value it gets today.
- **Evidence:** there's no database setup in any of the files I had.

### F-07 [minor · possible] The e2e job can't run as written, and nobody sees its results
- **Where:** `.github/workflows/ci.yml:17-21`
- **Type:** reliability-risk · **Rule:** DLV-CI-02
- **What:** it installs nothing, then calls `pytest --reruns 3`; without the rerun plugin pytest stops with a usage error (checked here). It can only pass if the runner image already has pytest, the plugin and your dependencies. It writes no JUnit, so it isn't in the summary.
- **Why it matters:** if it fails every time, people learn to ignore it. If it passes, nobody knows what it ran.
- **Fix:** I've added an install step and JUnit output below. Check its recent logs. If it needs a database, it needs `DB_ENGINE` too.
- **Evidence:** read from ci.yml. I couldn't check what's on the runner image, and I haven't seen `tests/e2e`.

## Proposed changes
| Change | Effect on coverage |
|---|---|
| Unit tests run once, in their own job | none lost: the three runs were identical |
| DB tests run on PostgreSQL 16 only | none lost for the product, which doesn't support MySQL or SQLite |
| `push` triggers only on `main`, and a newer push cancels the PR's older run | commits on PR branches are still tested once, through `pull_request`. Trade-off: a branch without a PR gets no CI |
| `--reruns` removed | none lost, and flaky tests show up. Ship it together with the `test_expired_cart` fix, or you'll see more red at first |
| pip cache, Python pinned to 3.12 | faster installs, and CI uses the same Python as production |
| Skip condition fixed | **gained:** `test_locking` runs on PostgreSQL |
| `addopts = -q -ra` in pytest.ini | the log lists every skipped test with its reason |

To measure the saving, compare per-step durations of runs 1041 and 1042 in the Actions UI with the first runs after the change; if the minutes are in e2e or setup, cut there next.

`.github/workflows/ci.yml`:
```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]   # your default branch; pushes to PR branches are covered by pull_request
concurrency:           # a newer push to the same PR cancels that PR's older run
  group: ci-${{ github.event.pull_request.number || github.run_id }}
  cancel-in-progress: true

jobs:
  unit:                # no database (README): run once, not once per engine
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"   # production version (README); was unpinned
          cache: pip
          cache-dependency-path: requirements-dev.txt
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/unit --junitxml=reports/unit.xml
      - if: success() || failure()   # report failures too, not only green runs
        run: bash scripts/summary.sh reports/unit.xml

  db:                  # PostgreSQL 16 only: the one engine the product supports
    runs-on: ubuntu-latest
    env:
      DB_ENGINE: postgres:16   # same value the old postgres leg gave the db fixture
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements-dev.txt
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/db --junitxml=reports/db.xml
      - if: success() || failure()
        run: bash scripts/summary.sh reports/db.xml

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements-dev.txt
      - run: pip install -r requirements-dev.txt   # the old e2e job installed nothing
      - run: pytest tests/e2e --junitxml=reports/e2e.xml
      - if: success() || failure()
        run: bash scripts/summary.sh reports/e2e.xml
```

`scripts/summary.sh`:
```bash
#!/usr/bin/env bash
# Prints what the JUnit files say actually ran. Skipped tests are listed and never counted
# as passed. Exits 1 if any test failed or errored, or if no test ran at all.
set -euo pipefail
python3 - "$@" <<'PY'
import sys
import xml.etree.ElementTree as ET

passed = failed = errors = 0
skipped = []
for path in sys.argv[1:]:
    try:
        tree = ET.parse(path)
    except FileNotFoundError:
        sys.exit(f"no results file {path}: those tests did not run")
    for case in tree.iter("testcase"):
        if case.find("failure") is not None:
            failed += 1
        elif case.find("error") is not None:
            errors += 1
        elif (skip := case.find("skipped")) is not None:
            reason = skip.get("message") or "no reason given"
            skipped.append(f'{case.get("classname")}::{case.get("name")} ({reason})')
        else:
            passed += 1

ran = passed + failed + errors
print(f"ran {ran}: {passed} passed, {failed} failed, {errors} errors"
      f" | skipped, not run: {len(skipped)}")
for line in skipped:
    print(f"  skipped: {line}")
sys.exit(1 if failed or errors or ran == 0 else 0)
PY
```

`tests/db/test_orders.py`:
```diff
-@pytest.mark.skipif(os.getenv("DB_ENGINE") != "postgres", reason="needs PostgreSQL")
+# CI passes "postgres:16"; an exact match against "postgres" skipped this test everywhere.
+@pytest.mark.skipif(
+    not os.getenv("DB_ENGINE", "").startswith("postgres"), reason="needs PostgreSQL"
+)
```

`tests/unit/test_cart.py`: a sketch, untested. It needs `Cart` to accept a clock, and I haven't seen `shop/cart.py`.
```python
class FakeClock:
    def __init__(self, now=1_000.0):
        self.now = now

    def __call__(self):
        return self.now


def test_cart_expires_only_after_ttl():
    clock = FakeClock()
    cart = Cart(items={}, ttl_seconds=2, clock=clock)
    clock.now += 1.9
    assert not cart.expired
    clock.now += 0.2
    assert cart.expired
```
Decide what should happen at exactly 2 s and add that case as well. This version also drops a 2 s sleep from every run.

## Trace

`<skill>` = `/home/claude/work/repo/skills/software-engineering-intelligence`. Workspace: `/tmp/eval-ci`. Scratch files went in `/tmp/eval-ci/_scratch/`. Nothing under `/home/claude/work/repo` was modified, nothing was installed, and the case's `graders/` folder and `case.yaml` were never opened.

**Shell commands, in order:**
1. `ls -la <skill>/ <skill>/references/ <skill>/scripts/ <skill>/assets/`: listed the skill layout (SKILL.md, references, scripts, templates).
2. `mkdir -p /tmp/eval-ci && cd /tmp/eval-ci && bash <skill>/evals/ci-flaky-duplication/place-files.sh && find … && wc -l …`: placed the 9 fixture files (115 lines).
3. `ls -la <skill>/references/testing/ <skill>/assets/templates/ && wc -l <skill>/references/testing/*.md`: listed 4 testing references and 11 templates.
4. `python3 --version; python3 -c "import pytest…"; python3 -c "import pytest_rerunfailures"; pip list | grep …; command -v psql postgres pg_ctl initdb mysql mysqld sqlite3 docker bash; bash --version`: Python 3.13.18 and pytest 9.1.1 present; pytest-rerunfailures absent; only a psql client (no PostgreSQL or MySQL server, no sqlite3 CLI); docker binary present but unused; bash 5.2.21.
5. `python3 <skill>/scripts/rules.py show TEST-COST-01 TEST-ISO-02 TEST-SKIP-01 TEST-REPORT-01 TEST-DATA-02 DLV-CI-02`: printed the six rules.
6. `python3 <skill>/scripts/repo_survey.py /tmp/eval-ci`: found 3 Python test files, 1 shell script and CI. It reported database engines as UNKNOWN because it didn't pick up the README or the CI matrix. No git history.
7. `python3 <skill>/scripts/test_smells.py /tmp/eval-ci/tests`: 1 lead, the fixed sleep at unit/test_cart.py:13.
8. `python3 <skill>/scripts/test_report.py --help`: showed usage.
9. `bash scripts/summary.sh` on run-1041, run-1042 and `reports/*.xml`, plus per-file `grep -c` counts: 88% / 100% / 94%, all exit 0. Each file has 9 testcases, 2 skipped and 0 errors; 1041 has 1 failure.
10. `python3 <skill>/scripts/test_report.py run1041=reports/run-1041.xml run1042=reports/run-1042.xml`: 7 executed per run, 2 skipped each, 1 failure (test_expired_cart), results differ between runs; verdict "failed".
11. Same as 10 with `--same-environment`: test_expired_cart reported as flaky; verdict "no plan".
12. `grep -rn -E "DB_ENGINE|\bdb\b" tests/unit`, `grep -n "DB_ENGINE\|matrix.db" .github/workflows/ci.yml`, then `DB_ENGINE=<v> pytest tests/db/test_orders.py -p no:cacheprovider -rs --junitxml=_scratch/db-<v>.xml` for postgres:16, mysql:8.0, sqlite, postgres and unset (`env -u`): the unit tests have no DB references, and the unit CI step sets no DB_ENGINE. test_locking was skipped for every value except exactly "postgres". test_upsert errored every time ("fixture 'db' not found").
13. `python3 -c "<print testcase children>" _scratch/db-postgres_16.xml`, `bash scripts/summary.sh _scratch/db-postgres_16.xml`, `bash scripts/summary.sh _scratch/does-not-exist-*.xml`: the XML had test_upsert as an error and test_locking as skipped. The old summary printed "pass rate: 100%" (exit 0). With no matching file it hit "division by 0", exit 1.
14. `cat > _scratch/plan.json` (two Required groups), then `test_report.py --plan … run1042=…` and `test_report.py --same-environment --plan … run1041=… run1042=…`: both verdicts "not verified" (both groups incomplete).
15. `python3 -c "import yaml"`, `command -v actionlint yamllint check-jsonschema`: PyYAML 6.0.3 present; no workflow or YAML linters.
16. `mkdir -p _scratch/orig && cp --parents <ci.yml, summary.sh, pytest.ini, test_orders.py> _scratch/orig/`, then `DB_ENGINE=mysql:8.0 pytest tests/db/test_orders.py -k locking -p no:cacheprovider`: backups made; "1 skipped, 1 deselected", pytest exit 0.
17. `bash -n scripts/summary.sh`, then the new summary.sh on run-1041, run-1042, both files, db-postgres_16.xml, a missing file and no arguments: syntax OK. Results were 6 passed / 1 failed (exit 1); 7 passed / 2 skipped and named (exit 0); exit 1; 1 error (exit 1); "no results file…" (exit 1); "ran 0" (exit 1).
18. `DB_ENGINE=<v> pytest tests/db/test_orders.py -p no:cacheprovider` on the fixed file, for postgres:16, mysql:8.0, sqlite and unset: postgres:16 now reaches test_locking's setup and errors only on the missing fixture. The others still skip, with the reason printed via the new `-ra`.
19. `python3 -c "<yaml.safe_load ci.yml; print triggers, jobs, steps>"`, `grep -n -E "reruns|matrix" ci.yml`, line-diff counts against `_scratch/orig`: parses; jobs are unit, db and e2e, with no matrix and no reruns. Lines changed: ci.yml 54, summary.sh 37, pytest.ini 2, test_orders.py 5.
20. `pytest --reruns 3 -p no:cacheprovider tests/unit/test_tax.py`, then a PyYAML re-parse: "unrecognized arguments: --reruns", exit 4; the new concurrency group parses.
21. `python3 <skill>/scripts/check_report.py --help`: showed usage.
22. `sed -i` to change the summary step conditions to `success() || failure()`, then `grep -n "if:"` and a PyYAML parse: 3 conditions changed; parses.
23. `python3 <skill>/scripts/check_report.py _scratch/answer.md`: 0 errors, 2 warnings (Scope lacked a "not reviewed" line; 1,856 words).
24. The same check after a rewrite, plus a Python check that the answer's yaml and bash blocks equal the workspace files: 1 warning (1,804 words); both blocks match.
25. A python3 string-replacement script (11 wording cuts) plus `check_report.py`: 0 errors, 0 warnings.
26. A python3 string-replacement script (5 accuracy fixes) plus `check_report.py`: 0 errors, 0 warnings.

**Workspace files edited with the editor tools (not shell):** `tests/db/test_orders.py`, `scripts/summary.sh`, `pytest.ini`, `.github/workflows/ci.yml`, and the scratch draft `_scratch/answer.md`.

**Skill files read:** `SKILL.md`, `references/workflows/test-strategy.md`, `references/testing/execution.md`, `references/testing/database-matrix.md`, `assets/templates/test-execution-report.md`, `assets/templates/review-report.md`, plus the six rules shown via `scripts/rules.py`. Scripts run: `repo_survey.py`, `test_smells.py`, `test_report.py`, `rules.py`, `check_report.py`. Sandbox tools used, labelled as such in the answer: pytest 9.1.1 on Python 3.13.18, and PyYAML 6.0.3.
