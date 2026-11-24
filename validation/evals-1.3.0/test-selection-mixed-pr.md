**No, keep the DB job.** It's the only job that tests the changed SQL against PostgreSQL 16, and it isn't what makes CI slow. Per the README, e2e takes ~25 min and the DB job ~9 min. The jobs in `ci.yml` have no `needs:`, so they run in parallel: dropping the DB job saves runner minutes, not wall-clock time (unless your runners queue jobs). Unit tests alone wouldn't verify this PR either. It changes no tests, and the one pricing test passes under the old and the new rounding alike.

Scope: all 15 files you sent, read in full. Not among them: `conftest.py`, `requirements.txt`, the schema or migrations, the checkout code, and the old versions of the changed files.

### What needs to run before merge

| Test group | Class | Why |
|---|---|---|
| DB job on PostgreSQL 16, with fixes 1–3 | **Required** | `ON CONFLICT (external_id) DO UPDATE … RETURNING` is engine-specific and only works if `orders.external_id` has a unique constraint or unique index. The PR adds no migration and I can't see your schema. If the constraint is missing, every sync fails, and only a real PostgreSQL with your schema shows that (TEST-DATA-02). |
| Unit job, plus fix 4 | **Required** | The money rule changed. The existing test (10.00 × 2, no discount) gives 20.00 under either rule, so it can't catch a mistake (DATA-TYPE-02). |
| E2E checkout | **Recommended** | It isn't needed for the CSS: `.checkout-button`, the class it clicks, is unchanged. It can't see a wrong total, since it only asserts "Paid". But it's the only end-to-end check of checkout. And `ci.yml` runs only on `pull_request`, with no merge-queue, push or nightly run, so whatever you skip here runs nowhere. If you must save time, defer *this* job to a post-merge run as an explicit decision, not the DB job. |
| A look at the checkout page in the preview | Recommended (manual) | The CSS change is spacing only, and no automated test checks layout. |
| `SPLIT_PAYMENTS_ENABLED` tests | Not necessary yet | Nothing in these files reads the flag, and it defaults to off. Test both states in the PR that first uses it (DLV-FLAG-01). |
| `docs/checkout.md` | Not necessary | Docs only. It's the spec for fix 4. |

### Fixes so those jobs test the change

1. **[major · confirmed] The DB test can't pass as written.** `tests/db/test_orders_repo.py` calls `upsert_order` without importing it. Running its body with stub fixtures gave `NameError: name 'upsert_order' is not defined`. Its `pg_conn` and `order_factory` fixtures aren't defined in any file you sent. If the DB job is green today, check that it actually runs this file.
2. **[major · confirmed] The path that changed, the conflict, has no test.** Sync the same `external_id` twice and expect the same id, one row and the exact new total. Also recommended: two sessions upserting the same new key at once, expecting one row and no error.
3. **[question · confirmed] A re-sync overwrites status.** On conflict, the statement replaces `total` and sets `status = 'synced'` for any existing order. On a scratch PostgreSQL 16.15, an order I'd set to `paid` came back `synced` with the new total. I don't have the old select-then-insert code. If it left existing orders alone, this changes what happens to paid orders. Confirm it's intended and pin it in a test.
4. **[major · confirmed] Add rounding tests with exact values from `docs/checkout.md`.** I checked these against the current code:
   ```python
   # Line = namedtuple("Line", "unit_price quantity discount_rate")
   assert line_total(Decimal("0.97"), 1, Decimal("0.5")) == Decimal("0.49")  # 0.485 rounds up
   assert line_total(Decimal("0.99"), 1, Decimal("0.5")) == Decimal("0.50")  # 0.495 rounds up
   assert order_total([Line(Decimal("0.99"), 1, Decimal("0.5"))] * 2) == Decimal("1.00")
   # rounding the order total instead (the old rule, per PR.md) gives 0.99
   ```
   The last case is the one that pins per-line rounding. It also shows that some discounted orders' totals change by a cent.

**Checks run:**

| Command / check | Result |
|---|---|
| `pytest -m "not db and not e2e"` (README) | 0 tests ran. Collection failed with `No module named 'app'`: nothing in these files puts the repo root on the import path (presumably your requirements install does). |
| `python3 -m pytest -m "not db and not e2e"` | 1 passed, 2 deselected, 0.01 s |
| Scratch calls to `app.pricing` | The values in fix 4. The existing test's inputs give 20.00 under both rules. |
| DB test body with stub fixtures (no database) | `NameError` (fix 1) |
| The PR's upsert SQL on a throwaway PostgreSQL 16.15, with a minimal `orders` table I wrote (not your schema) | Without a unique constraint: `ERROR: there is no unique or exclusion constraint matching the ON CONFLICT specification`. With `UNIQUE (external_id)`: the re-sync returned the same id, the total became 12.34, `paid` became `synced`, still 1 row. |
| `test_impact.py --files <5 changed files>` | Leads matched the above. It tagged `config.py` as money because of the word PAYMENTS. That's a false positive, so I dropped it. |

**Not run:** your DB and e2e jobs. This machine has no Docker daemon, no PostgreSQL driver and none of the project's dependencies, and the files had no schema, migrations or fixtures. The e2e job also needs a deployed preview. PostgreSQL 16 binaries do exist here; I used them only for the scratch SQL check above.

**Verdict: not verified.** The only project test that ran can't tell the old rounding from the new. Three risks stay open until the fixed DB job and the new unit tests run: a missing unique constraint, the status overwrite, and concurrent syncs.

**Also noticed:** the e2e job in `ci.yml` has no install step and nothing pointing it at a preview. Check its logs to be sure it really runs the checkout test. Longer term: run the DB job on PRs that touch `app/repo/`, SQL or migrations, move e2e to a merge queue or nightly run, and keep a full run after merge.

## Trace

`$SKILL` = `/home/claude/work/repo/skills/software-engineering-intelligence`. Workspace: `/tmp/eval-tsel`. Nothing under `/home/claude/work/repo` was modified, and `graders/` and `case.yaml` were not opened.

**Shell commands run (in order):**
1. `mkdir -p /tmp/eval-tsel && cd /tmp/eval-tsel && bash $SKILL/evals/test-selection-mixed-pr/place-files.sh && find /tmp/eval-tsel -type f | sort` → placed the 15 fixture files.
2. `git rev-parse --is-inside-work-tree; python3 --version; python3 -B -c "import pytest…"`, import probes for psycopg/psycopg2/fastapi/playwright, `command -v docker psql pg_ctl postgres` → not a git repo; Python 3.13.18; pytest 9.1.1; psycopg, psycopg2 and fastapi not importable; playwright importable; `docker` and `psql` CLIs on PATH.
3. `python3 -B $SKILL/scripts/test_impact.py --help` → usage shown; `--files` works without git.
4. `python3 -B $SKILL/scripts/test_impact.py /tmp/eval-tsel --files app/pricing.py app/repo/orders.py app/config.py static/css/checkout.css docs/checkout.md` → leads: pricing.py: source, money, 1 test; orders.py: data-access, PostgreSQL-specific SQL, no tests found; config.py: tagged money (false positive); CSS: ui-style; docs: docs; engines: PostgreSQL.
5. `psql --version; ls -d /usr/lib/postgresql/*/bin; command -v initdb pg_ctl postgres pg_ctlcluster; timeout 10 docker info; timeout 10 docker images postgres; python3 -B -c "import pytest_playwright"` → psql 16.15; server binaries in `/usr/lib/postgresql/16/bin`; Docker daemon not reachable; pytest_playwright not importable. Note: this contradicts the stated premise of "no PostgreSQL here".
6. `rules.py show` for TEST-SEL-01 TEST-SKIP-01 TEST-DATA-02 TEST-REPORT-01 DATA-TYPE-02 DLV-FLAG-01 → printed the six rules.
7. `grep -rn -i "on conflict" --include=*.md` (in `$SKILL/references`) → 5 hits.
8. Searches for SPLIT_PAYMENTS_ENABLED, order_total, line_total, upsert_order, conftest.py, requirements, migrations, `.checkout-button` → the flag is defined but never read; the DB test uses upsert_order without importing it; `.checkout-button` appears only in the CSS and the e2e test.
9. `sed -n '60,85p' $SKILL/references/data/engines.md` → engine-difference list, including "Upserts and conflicts".
10. `pytest --collect-only` and `pytest -m "not db and not e2e"` → collection error, `ModuleNotFoundError: No module named 'app'`; 0 tests ran.
11. Inline scripts: (a) app.pricing values above; (b) DB test with stub fixtures → NameError.
12. Checked postgres user and binaries.
13. `python3 -m pytest -m "not db and not e2e" -q -rA` → 1 passed, 2 deselected.
14. Throwaway PostgreSQL 16.15 in `/tmp/eval-tsel/.scratch-pg` (initdb, pg_ctl start on a unix socket, psql script, pg_ctl stop, cleanup) → results in the table above.
15–17. `check_report.py --help`, then on two drafts (light mode: 1,015 then 918 words against a 450-word light budget; missing "Checks run:" label) → draft tightened and deleted.

**Skill files read:** SKILL.md, references/workflows/test-strategy.md, references/testing/selection.md, references/testing/database-matrix.md, assets/templates/test-execution-report.md (in full); references/data/engines.md lines 60–85; six rules via rules.py. Not read: levels.md, execution.md, knowledge-model.md, the full rule files, languages/python.md.
