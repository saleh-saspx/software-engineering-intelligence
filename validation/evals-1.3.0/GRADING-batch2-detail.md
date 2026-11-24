# Grading: batch 2 (independent grader, 2026-11-24)

Skill under test: working tree at commit 6e18b64 (`skills/software-engineering-intelligence`).
Inputs read for each case: `case.yaml`, `prompt.md`, every fixture file under `files/`, every
criterion in `graders/`, and the executor's answer plus trace in `/home/claude/work/eval-runs/<case>.md`.
I checked fixture facts myself. Apart from read-only `git`, `ls` and `grep` commands, the only thing
I ran was the fixture's own `scripts/summary.sh` on the two JUnit files, which only reads them. I ran no skill scripts, because the
working tree has changed since the runs (see the last section). My statements about the scripts come
from the traces, checked against the 6e18b64 sources (`git show`).
All criteria have `focus: trace`, so I graded each one against the answer and its trace together.
Rule applied: PASS only if every substantive element of the criterion is stated, in any wording.
Elements that are only implied don't count.

| Case | Score |
|---|---|
| ci-flaky-duplication | 6/8 |
| mysql-large-table-precision | 7/8 |
| normalization-tradeoffs | 7/7 |
| cross-database-migration | 7/8 (the FAIL is on a criterion I judge partly wrong about the fixture) |
| concurrency-durability-internals | 5/6 |
| **Overall** | **32/37** |

---

## 1. ci-flaky-duplication: 6/8

Fixture facts I verified:
- Each JUnit file has 9 test cases and 2 skipped (`test_reserve_concurrently`, `test_locking`).
- run-1041 has 1 failure (`test_expired_cart`, 2.10 s) and run-1042 has 0. There are no `<error>`
  elements.
- Test time sums are 7.72 s and 7.37 s.
- The original `summary.sh` prints 88 %, 100 % and 94 % (run 1041, run 1042, both files).
- The matrix is `postgres:16, mysql:8.0, sqlite`. The skip condition compares with `"postgres"`.
- The workflow triggers on `[pull_request, push]`. There is no `services:` block.

| Criterion | Verdict | Evidence |
|---|---|---|
| 01-the-response-identifies-that-the.md | PASS | F-05: "each run has three engine legs … The unit suite runs 6 times as the exact same command (the unit step doesn't even set `DB_ENGINE`)". Proposed changes: "Unit tests run once, in their own job · none lost: the three runs were identical". The new ci.yml keeps a separate PostgreSQL `db` job. Trace 12 grepped `tests/unit` for database use. "6 per push" counts both the `push` and `pull_request` runs, which is correct for a branch with an open PR. |
| 02-the-response-questions-the-mysql.md | PASS | F-05: "MySQL and SQLite results say nothing about a PostgreSQL-only product (SQLite differs on locking and types), yet their failures still turn the PR red". Proposed changes: "DB tests run on PostgreSQL 16 only · none lost for the product, which doesn't support MySQL or SQLite". The evidence cites the README, which confirms this (line 3). |
| 03-using-the-two-result-files.md | **FAIL** | Covered: flaky across runs (F-03 "it failed in 1041 and passed in 1042"; trace 10–11, `test_report.py --same-environment`); the cause is tied to the sleep and clock ("sleeps exactly 2 s … depends on clock resolution"; trace 7, `test_smells` lead at test_cart.py:13); an injected-clock fix (FakeClock sketch); dropping `--reruns`. **Missing:** no visible quarantine with an owner for `test_expired_cart`. The answer says to fix it and "Drop `--reruns` in the same PR". It gives an owner and date only for #881 (`test_reserve_concurrently`, F-04). See flawed criteria: possibly too narrow. |
| 04-the-response-explains-that-the.md | PASS | Summary: "The 100% isn't real. `summary.sh` counts skipped tests as passes and only runs after both pytest steps have passed". F-02: "skipped tests count as passed … retries are invisible". F-03: "Retries turn flaky failures into passes". The skipped tests are named (F-04, F-01). "run 1041 **failed**". Separate counts: "7 of 9 ran per run; same 2 skipped in both; `test_expired_cart` failed, then passed", and for 1042 "ran 7: 7 passed … skipped, not run: 2". The replacement script prints ran, passed, failed, errors and skipped separately. Minor gap: the passed count for run 1041 (6) appears only in trace 17, not in the answer. |
| 05-the-response-points-out-that.md | PASS | F-01: "`test_locking` never runs, not even on PostgreSQL … skipped unless `DB_ENGINE == "postgres"`. CI sets `postgres:16` … order locking is never checked." Trace 12 ran the real file under each `DB_ENGINE` value. |
| 06-the-response-proposes-which-suites.md | **FAIL** | The only stage change is to triggers: `pull_request` plus `push` to `main`, with cancel-in-progress. Every suite (unit, db, e2e) runs on both. There is no nightly or pre-release stage and no assignment of suites to stages, although the answer itself says most of the 45 minutes lies outside the recorded tests (e2e and setup) and leaves e2e on every PR. The executor read `references/testing/execution.md` (whose §2 is a stage-policy table) but didn't apply it. |
| 07-the-response-does-not-recommend.md | PASS | No test is deleted. The matrix legs go with a stated reason (unsupported engines; identical unit runs). `test_expired_cart` is replaced by a clock-controlled test that covers both sides of the limit. For `test_locking` it offers "delete the skip", not the test. |
| 08-counts-and-timings-the-response.md | PASS | 9 per run, 2 skipped, 1 failure in 1041: correct. "About 7.5 s per run" matches 7.72 and 7.37 s. 88 %, 100 % and 94 %: correct (I re-ran the script). "8 jobs per push" is correct: 2 workflow runs × (3 matrix jobs + e2e). Every claim of having run something maps to trace steps 7, 9–14 and 16–20. |

Honesty: one inaccuracy. Line 28 of the answer ("Not run: … no `shop` package, `db` fixture or
database server here") and trace 4 ("only a psql client (no PostgreSQL … server)") are wrong:
PostgreSQL 16.15 server binaries were installed under `/usr/lib/postgresql/16/bin`. They aren't on
PATH, so `command -v` missed them. This doesn't affect any conclusion, because the DB tests also need
the missing `shop` package and `db` fixture. No claim of having run something lacks support in the
trace. Things it didn't reproduce are labelled: the cause of the flaky test ("I didn't reproduce it"),
the clock sketch ("untested") and the workflow ("parses; … not run on GitHub").

Technical notes:
- F-02 says setup and fixture errors "aren't counted at all". That's imprecise: they're counted in the
  total and so reported as passes, which is what the answer's own evidence row shows (100 % for a run
  with 0 passed and 1 error).
- "Only runs after both pytest steps have passed, so whenever it prints, it prints 100 %" is correct,
  given GitHub Actions' implicit `success()` condition.
- The flaky-test mechanism ("clock resolution, `>` vs `>=`") is plausible and labelled as read from
  the code. The failing run took longer (2.10 s) than the passing one (2.05 s), so a too-short sleep
  isn't the explanation. The real cause depends on `Cart`'s time source; I can't tell which.
- These findings are correct and useful: no `services:` block (F-06); the e2e job installs nothing and
  `--reruns` without the plugin is a usage error with exit code 4 (trace 20); pytest exits 0 when every
  selected test is skipped.

## 2. mysql-large-table-precision: 7/8

| Criterion | Verdict | Evidence |
|---|---|---|
| 01-the-response-explains-that-changing.md | PASS | "copies the full table and blocks writes while it runs. MySQL 8.0 can't change a DECIMAL's precision or scale in place, so it uses the COPY algorithm … reads continue, but writes wait … tens of minutes to hours (an estimate) … Each replica starts it only after the primary has finished and applies nothing else in the meantime". |
| 02-the-response-recommends-a-safer.md | PASS | "run this change with gh-ost or pt-online-schema-change", with their requirements (row-based binlog, foreign keys, a primary or unique key). Also: "add explicit `ALGORITHM` and `LOCK` clauses, so MySQL fails with an error instead of quietly choosing a blocking method". |
| 03-the-response-says-card-expires.md | PASS | "TIMESTAMP stops at 2038-01-19 03:14:07 UTC … converts values through the session time zone, which your connection config doesn't set … Fix: `$table->date('card_expires_at')->nullable()` with a `'date'` cast". `config/database.php` indeed sets no time zone. |
| 04-the-response-notes-that-the.md | **FAIL** | Covered: online and in place ("Built online on the primary; writes continue", `ALGORITHM=INPLACE, LOCK=NONE`); a separate migration from the type change; replica lag ("each replica repeats it afterwards. Reporting will be behind for as long as the build takes"). **Missing:** the I/O and load cost on the primary. The answer says only "B still takes a while on 80M rows". A narrow miss. |
| 05-the-response-points-out-that.md | PASS | "The model still casts `amount` to `decimal:2`, so Eloquent returns amounts rounded to 2 places … Switch the cast to `decimal:4` once the column is widened". |
| 06-the-response-recommends-a-rehearsal.md | PASS | "Restore a recent backup onto a production-sized server running the same MySQL version … Time the tool run there". "Stop if … replica lag goes beyond what reporting can accept". For the index: "time it on a copy first". |
| 07-the-response-does-not-give.md | PASS | Uses MySQL's own `lock_wait_timeout` (default 31,536,000 s, which is the "one year" it cites). No CONCURRENTLY and no NOT VALID. |
| 08-the-response-gives-an-explicit.md | PASS | "**No. Don't run it as written** … The other two changes can go on Friday with small fixes". "Verdict: blocked". The checks table says "Migration on MySQL · none · not run". Trace 3–4 confirm there was no MySQL server and no Laravel. |

Honesty: clean. A global disclaimer ("I couldn't run anything on MySQL or Laravel, so every duration
below is an estimate"), "likely" labels on the findings, and an explicit "couldn't verify" on the
Laravel 11 `change()` and Eloquent dirty-check points. One wording ambiguity: "Laravel sends them as
separate ALTER statements (`migrate --pretend` shows them)" reads like an observation, although
Laravel wasn't available. The checks table says it wasn't run.

Technical notes: the main claims are correct as far as I know:
- A DECIMAL type change uses COPY with reads allowed.
- DDL replicates as one statement after the commit.
- INSTANT ADD COLUMN works from 8.0.12 when the column goes last.
- TIMESTAMP's range ends in 2038 and the type converts through the session time zone.
- 20 writes/s × 3,600 s = 72,000 writes per hour.
- DECIMAL(10,2) tops out at 99,999,999.99, so narrowing back fails under strict mode.
- In Laravel 11, `change()` drops modifiers that aren't repeated.
- Eloquent's dirty check compares casted decimals; this is labelled as the executor's belief.

One nuance: if the index step fails, a re-run would likely repeat the full-table MODIFY before it
fails on the duplicate column, so a re-run costs more than the answer says. I'm unsure of Laravel 11's
statement order.

## 3. normalization-tradeoffs: 7/7

| Criterion | Verdict | Evidence |
|---|---|---|
| 01-the-response-says-order-lines.md | PASS | "It isn't a copy of `products.price`. It's a different fact: the price this line was sold at. Removing it would rewrite every past order …". F-01: "Totals, invoices, refunds and revenue reports would silently follow every price edit". Reproduced as 20.00 against 24.00 (trace 15). |
| 02-the-response-treats-orders-customer.md | PASS | F-05: "If a customer always has one email across all their orders, the column is a redundant copy and should go. If it means 'where this order's confirmation went', it's a snapshot like `unit_price`". Fix: "Check what reads it. Keep … if you need the historical value. Otherwise … drop it". |
| 03-the-response-identifies-products-tags.md | PASS | F-03: "A list in one column breaks first normal form. You can't index, constrain or rename a single tag". `LIKE '%sale%'` also matched `wholesale` (trace 15). Fix: `product_tags(product_id, tag)`, plus a `tags` table if the list is curated; `text[]` with GIN, with its limit stated. "Joins per tag" isn't named, but per-tag querying is covered by the LIKE example, so PASS on substance. |
| 04-the-response-says-the-street.md | PASS | "Over-normalised, and it lets past ship-to addresses change". F-02: "The chain doesn't give you 'one fact in one place'. It does cost five joins per shipping label … Lookup tables for them add joins, not integrity". Fix: copy the ship-to onto the order; store addresses as text plus a country key. The stopping rule is given as applied to this case, not as a general statement. |
| 05-the-response-discusses-the-eav.md | PASS | Costs: types, required attributes and allowed values can't be declared; `'heavy'` and a misspelt `wieght_kg` were accepted; a numeric filter failed at run time (trace 15). Alternatives: typed columns with checks for common or computed attributes, a per-category table, EAV or `jsonb` only for a sparse display-only long tail, and EAV for user-defined attributes. The trade-offs come as "when each fits" rather than explicit pros and cons: thin, but present. |
| 06-the-response-does-not-endorse.md | PASS | "'3NF everywhere' isn't a sufficient quality bar". It recommends no denormalising for speed. Each change rests on meaning, a dependency, 1NF or integrity. The FK-index advice is labelled "expected effect, not measured". |
| 07-the-response-explains-its-reasoning.md | PASS | FD reasoning in F-01 ("3NF only objects to a column that another non-key column determines … 'product → unit price'"), in F-05 (customer → email, with drift reproduced as an update anomaly) and in the Summary ("normal forms are about which column determines which"). |

Honesty: clean. Every database claim is backed by a throwaway PostgreSQL 16.15 instance (trace
13–20), labelled "made-up data, not your systems". The GIN check is labelled as 2 rows, "not a
performance measurement".

Technical: correct. That includes the case-sensitive unique email under the default collation, the
invalid index left by a failed `CREATE UNIQUE INDEX CONCURRENTLY`, how `NOT VALID` behaves, and
`SET NOT NULL` skipping the scan once a validated `IS NOT NULL` check exists.

## 4. cross-database-migration: 7/8

Fixture facts:
- `users_email_unique` is on a table with `utf8mb4_0900_ai_ci`.
- `stock_levels.warehouse_id` is the leading column of the unique key `(warehouse_id, sku)`.
  `orders.user_id` has no explicit index.
- `warehouses` is referenced but never defined.
- `phpunit.xml` already uses in-memory SQLite.

| Criterion | Verdict | Evidence |
|---|---|---|
| 01-the-response-rejects-running-ci.md | PASS | F-02: on SQLite 3.45.1 `lowStock()` runs unchanged, but it fails on PostgreSQL; `add()` is a syntax error on SQLite too (trace 13–14). Fix: DB tests on a PostgreSQL 16 service container, and "also run the data-access tests on MySQL 8" while switching back is possible. Revised plan, step 2. |
| 02-the-response-identifies-that-the.md | **FAIL** | Covered: reliance on ai_ci (F-04), PostgreSQL's exact matching (reproduced, trace 15), a `lower(email)` unique index (trace 18) and citext as an alternative. **Missing:** any check of existing data for near-duplicates before the move. F-04's fix and F-07's rehearsal checks list row counts, totals, sequences and zero dates, but not email duplicates. See flawed criteria: this element is wrong about the fixture. |
| 03-the-response-says-the-mysql.md | PASS | F-01 names `ON DUPLICATE KEY UPDATE`, backticks, `IFNULL` and `LIMIT 0, 100`, each with PostgreSQL's error. The rewrite `ON CONFLICT (warehouse_id, sku) DO UPDATE SET quantity = stock_levels.quantity + EXCLUDED.quantity` ran on 16.15. The answer also shows why the unqualified SQLite form is "ambiguous" on PostgreSQL. |
| 04-the-response-covers-type-mapping.md | PASS | F-05: PostgreSQL rejects zero dates; count them and map them to NULL ("never logged in"). `tinyint(1)` becomes boolean, with `WHERE is_admin = 1` failing and PHP getting `true` instead of an integer. "bigint unsigned: PostgreSQL has no unsigned types". |
| 05-the-response-notes-that-after.md | PASS | F-06: "Loading rows with their existing ids doesn't advance the id sequences … duplicate key … succeeded once I ran `setval` … compare every sequence with `max(id)`". |
| 06-the-response-points-out-that.md | PASS | F-06: "MySQL indexes foreign-key columns automatically; PostgreSQL doesn't … Index `orders.user_id`. `stock_levels.warehouse_id` is already covered by its unique index", which is correct against the fixture. |
| 07-the-response-adds-verification-to.md | PASS | F-07: rehearse on a production-sized copy; "Verify row counts, per-table totals such as `sum(quantity)`, sequences and zero dates". F-03 gives a realistic rollback: writes after cut-over would be lost; before reopening, abort to MySQL; after reopening, roll forward. |
| 08-the-response-does-not-claim.md | PASS | "Eloquent doesn't translate raw SQL". Step 3 of the plan is treated as a false assumption. |

Honesty:
- Every claim of having run something is backed by trace 10–20. PHP runs through a stand-in `DB`
  facade are labelled as such ("no Laravel here").
- Scope says MySQL behaviour comes from documentation.
- pgloader claims are labelled ("couldn't check pgloader's defaults", "from memory … check"), with one
  exception: F-04's "pgloader copies the index but not these matching rules" is unlabelled, though
  plausible.

Technical notes: the answer is correct, and it rightly notes that MySQL 8's default strict
`sql_mode` would reject the zero-date default. Two nuances, not errors:
1. `lower()` and citext restore case-insensitivity but not the accent-insensitivity of `ai_ci`. A
   nondeterministic ICU collation would restore both. The answer mentions accents only for "other
   columns".
2. If pgloader built the schema, it would probably copy InnoDB's implicit FK index. The missing
   index bites when the schema comes from Laravel migrations, which is what the answer recommends, so
   its advice holds for its own plan. I'm unsure of pgloader's exact behaviour.

## 5. concurrency-durability-internals: 5/6

| Criterion | Verdict | Evidence |
|---|---|---|
| 01-the-response-explains-that-transfer.md | PASS | F-02 explains argument-order locking and the A→B / B→A cycle. Fix: sorted lock order (code), plus "A bounded automatic retry of the whole transaction on 40P01". In the sandbox, the code as written had 32 of 146 deadlocks; with ordered locks there were 0 (trace 12–14). |
| 02-the-response-explains-that-the.md | PASS | F-03: "VACUUM may remove a dead row version only when no open snapshot can still see it … about 3 hours". Reproduced "189762 are dead but not yet removable", with the cutoff equal to `backend_xmin` (trace 15–16). Fixes: keyset batches in short transactions, a replica (with the `hot_standby_feedback` caveat), timeouts and an alert on the oldest snapshot. |
| 03-the-response-explains-that-synchronous.md | PASS | F-01: "the database is still consistent … corruption is the risk of `fsync = off`, not this setting. But the latest acknowledged transfers are gone". It advises "Undo it first", and `SET LOCAL` plus an ADR if a workload truly tolerates loss. Crash test: 0 of 20 commits survived with `off`, 20 of 20 with `on` (trace 17). |
| 04-the-response-explains-the-b.md | **FAIL** | The second half is covered: deadlocks need lock ordering and retries in any store, and a move means rebuilding constraints, transactions, backups and PITR. The first half is only asserted: "LSM trees excel at high-rate ingest. A ledger is read-modify-write … B-tree OLTP territory" and "'No vacuum' means compaction instead, which is tuned background I/O". **Missing:** the buffer-then-merge mechanism, read amplification (several files per lookup) and space amplification (obsolete versions and tombstones until compaction). All of these are in `references/data/internals.md` §4, which the executor read in full. |
| 05-the-response-asks-for-or.md | PASS | It asks for the DETAIL of each `deadlock detected` log entry, `n_dead_tup` per table from `pg_stat_user_tables`, and the oldest-`backend_xmin` query on `pg_stat_activity`. It also uses its own sandbox evidence (pgbench, VACUUM VERBOSE, the server log). |
| 06-the-response-does-not-claim.md | PASS | It doesn't say LSM is universally faster, and it doesn't recommend RocksDB ("only through an ADR backed by numbers"). Its numbers were measured in the sandbox and labelled. "About 1,800 transfers" is marked as an estimate, from the documented bound of 3 × `wal_writer_delay` at 3k/s. |

Honesty: clean. RocksDB claims are labelled ("as I recall them; not verified"), as are claims from the
manual ("manual, not tested") and the sandbox scale ("not production magnitudes").

Technical: correct:
- The loss window is 3 × `wal_writer_delay`.
- `transaction_timeout` only arrives in PostgreSQL 17.
- The xmin horizon covers the whole database.
- "cannot be removed yet" is the wording of VACUUM VERBOSE in 14 and earlier.
- RocksDB doesn't sync each write by default.
- The open question about dead rows in an insert-only `postings` table is a good catch.

---

## Honesty notes (all cases)

- No fabricated runs. Every claim of having executed, reproduced or measured something matches a
  trace step. MySQL facts are labelled as documentation or "likely" (mysql, cross-db).
- ci-flaky-duplication: the answer wrongly says there was no database server. PostgreSQL 16.15
  binaries existed but weren't on PATH. This doesn't change any conclusion.
- mysql-large-table-precision: "(`migrate --pretend` shows them)" reads like an observation, but
  Laravel wasn't available.
- cross-database-migration: "pgloader copies the index but not these matching rules" is unlabelled,
  although pgloader wasn't available.

## Technical-correctness notes (summary)

None of the main claims is wrong. Imprecisions:
- ci: `<error>` test cases "aren't counted at all". In fact they count as passes.
- mysql: the cost of re-running after a partial failure is understated (unsure).
- cross-db: the email fix loses accent-insensitivity. Whether pgloader carries the implicit FK index
  across is open (unsure).

## Flawed or imprecise criteria

1. **ci-flaky-duplication/03: too narrow.** It requires quarantine with an owner even when the answer
   fixes the test now and removes the retries in the same PR, which is at least as good. Suggested:
   "…and recommends fixing it with a controlled clock, or quarantining it visibly with an owner and a
   date until it is fixed, rather than hiding it with blanket reruns." (TEST-ISO-02 and
   execution.md §3 already say "quarantine …, fix or delete".)
2. **cross-database-migration/02: wrong about the fixture in one element.** MySQL's `ai_ci` unique
   key already rejects case and accent variants, so the existing data can't contain near-duplicates
   that `lower()` or citext would reject. A duplicate check before the move finds nothing by
   construction. `case.yaml` ("existing near-duplicates surface") shares the error. Suggested: "…it
   recommends citext, a unique index on `lower(email)` or a case-insensitive ICU collation, in place
   before writes reopen on PostgreSQL, with case-insensitive lookups (a plus: noting that
   lower()/citext don't keep accent-insensitivity)."
3. **mysql-large-table-precision/02: the "and/or" is loose.** An answer offering only ALGORITHM/LOCK
   clauses would pass, but those make the change fail fast. They aren't a way to perform it.
   Suggested: "recommends a safer route for the type change: an online schema-change tool, expand and
   contract with a batched backfill, or a planned outage sized by rehearsal. Explicit ALGORITHM/LOCK
   is a guard in addition, not a substitute." (It didn't affect this grade.)
4. Minor ambiguities, graded on substance:
   - **normalization/03:** "constraints, indexing and joins per tag" could be read as all required.
     Suggest "e.g." wording.
   - **normalization/04:** "explains that normalisation stops where…": a general principle or one
     applied to the case? Suggest "explains, for the address chain, that further decomposition removes
     no anomaly and so isn't worth its joins".
   - **normalization/05:** "with their trade-offs": how explicit? Suggest "says for each alternative
     when it fits and what it costs".
   - **ci/04:** "reports executed, passed, failed and skipped separately": per run, or through the
     proposed script? Suggest "gives each run's executed, passed, failed and skipped counts (7/6/1/2
     and 7/7/0/2)".
   - **ci/01:** "three times per pipeline" is right per workflow run, but with
     `on: [pull_request, push]` a push to a PR branch runs it six times. Suggest saying "per workflow
     run".

## Skill-side observations (from the traces)

1. `repo_survey.py` (6e18b64) reported database engines as UNKNOWN for the CI matrix
   `db: [postgres:16, mysql:8.0, sqlite]` (ci trace 6).
2. `schema_lint.py` refused a single file ("not a directory", cross-db trace 7).
3. `schema_lint.py`'s MySQL TIMESTAMP lead suggested DATETIME even for a calendar date (mysql
   trace 8). The executor overrode it with DATE, per types.md.
4. `migration_lint.py --dialect mysql` raised only the type change. It gave no lead for the missing
   `lock_wait_timeout`, the several DDL statements in one migration (implicit commits), or the cost
   of an index build on a large table (mysql trace 7).
5. `migration_lint.py` analysed 0 files when PATH was the migrations folder itself and `--files` was
   absent (normalization trace 17).
6. The word budgets disagree. SKILL.md §8 says Tier 2 is "usually 600–1,500 words". `check_report.py`
   defaults to 1,800 for reviews and 450 for the light format:
   - The mysql executor used the light format for a Tier-2 migration review and had to pass
     `--budget 1500`.
   - Three executors trimmed drafts of about 2,000–2,200 words down to 1,800.
   - Hypothesis, not verified: the budget may be crowding out explanation. Three of the five FAILs
     are content the references hold (internals.md §4 on LSM, execution.md §2's stage policy,
     TEST-ISO-02's quarantine) and the executors read.
7. The CI-review guidance doesn't require a stage table as output. Test-strategy §9 and §11.5 point
   to execution.md, but nothing makes "PR / main / nightly / release" a required section when a user
   asks to cut CI time. Consider requiring it, and say in execution.md §3 that an immediate fix may
   replace quarantine.
8. Finding local engines is ad hoc. The ci executor used `command -v` and missed
   `/usr/lib/postgresql/16/bin`; three others found it and ran real PostgreSQL checks. Evidence depth
   is uneven across cases for this reason, as batch 1 also noted. SKILL.md gives no hint, such as
   checking versioned install paths or `pg_lsclusters`.
9. Positive:
   - `test_report.py` worked as designed: "failed" without a plan, flaky only with
     `--same-environment`, "not verified" with a plan.
   - `test_smells.py` found the sleep.
   - `check_report.py` caught missing finding fields (cross-db trace 21).
   - `rules.py show` was used for traceability in every case.

## Note on the working tree

Since the runs (answers written 16:24; the scripts changed 16:28–16:31), the working tree has
uncommitted changes to `_db.py`, `migration_lint.py`, `schema_lint.py`, the tests and `CHANGELOG.md`.
From the diff, they appear to address observations 1–5:
- CI-matrix engine detection.
- `schema_lint` accepting a single file and advising DATE.
- MySQL info-level leads for `lock_wait_timeout` and multiple DDL statements.
- `migration_lint` discovering files when PATH is the migrations folder.

I didn't run or verify them. They aren't part of the version graded here. The CHANGELOG has a
`<<B2SCORE>>` placeholder for this batch's score.
