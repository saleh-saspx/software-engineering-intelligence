# Review: MySQL 8 → PostgreSQL 16 migration plan

## Summary
**Verdict:** changes requested. Copying the data with pgloader during a write freeze can work. But steps 3–5 rest on false assumptions, and I reproduced the main failures on PostgreSQL 16:
- **Step 3:** both `StockRepository` methods fail. Eloquent doesn't translate raw SQL.
- **Step 4:** SQLite runs `lowStock()` exactly as written, so a passing SQLite suite says nothing about PostgreSQL.
- **Step 5:** switching back after writes resume throws away everything written to PostgreSQL.
- **Step 1:** pgloader would quietly change how email uniqueness, zero dates, booleans and timestamps behave. Nobody has measured whether the 2-hour window is enough.

## Findings

### F-01 [blocker · confirmed] Raw SQL in StockRepository fails on PostgreSQL 16
- **Where:** `app/Repositories/StockRepository.php:11-20`
- **Type:** defect · **Rule:** DATA-PORT-01
- **What:** `DB::statement()` and `DB::select()` send SQL exactly as written. On 16.15, `add()` fails at `ON DUPLICATE KEY UPDATE`. `lowStock()` fails in three separate ways:
  - backticks: syntax error;
  - `IFNULL`: `function ifnull(integer, integer) does not exist`;
  - `LIMIT 0, 100`: `LIMIT #,# syntax is not supported`.
- **Why it matters:** after cutover, stock can't be added or listed. Any other raw SQL in the app fails the same way.
- **Fix:** both statements below ran correctly on 16.15.
```php
DB::statement(
    'INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES (?, ?, ?)
     ON CONFLICT (warehouse_id, sku)
     DO UPDATE SET quantity = stock_levels.quantity + EXCLUDED.quantity',
    [$warehouseId, $sku, $qty]
);

return DB::select(
    'SELECT sku, warehouse_id, quantity AS qty FROM stock_levels
     WHERE quantity < 5 ORDER BY quantity, warehouse_id, sku LIMIT 100'
);
```
  - `IFNULL` did nothing, because `quantity` is `NOT NULL`.
  - The `ORDER BY` is new. Without it, `LIMIT` returns whichever rows come first, and InnoDB and PostgreSQL store rows in different orders.
  - Then search the rest of the code for raw SQL: `DB::raw`, `DB::select`, `DB::statement`, `DB::unprepared` and the `…Raw(` methods. In each, look for MySQL-only syntax: `IFNULL`, `GROUP_CONCAT`, `DATE_FORMAT`, `FIELD(`, `ON DUPLICATE KEY`, backticks and `LIMIT n, m`.
- **Evidence:** I ran your file unmodified through a minimal stand-in for the `DB` facade over PDO. I then ran the rewritten upsert from 8 processes at once, 500 calls each, on one key. It ended with one row and quantity 4,000. That is one clean run, not proof.

### F-02 [blocker · confirmed] SQLite in CI passes code that breaks on PostgreSQL
- **Where:** `phpunit.xml:3-4`. It already uses SQLite in memory, so step 4 is how CI works today.
- **Type:** test-gap · **Rule:** TEST-DATA-02
- **What:**
  - On SQLite 3.45.1, `lowStock()` runs unchanged.
  - The obvious SQLite fix for `add()` is `SET quantity = quantity + excluded.quantity`. It passes on SQLite and fails on PostgreSQL with `column reference "quantity" is ambiguous`.
  - SQLite accepted four things PostgreSQL rejected: a 50-character SKU in `varchar(40)`, `'abc'` in the integer `quantity`, an order for a user that doesn't exist, and the zero date. SQLite enforces foreign keys only when each connection turns them on. Check your `config/database.php`; I didn't have it.
  - `add()` as written is a syntax error on SQLite too, so no test of it can pass today.
- **Why it matters:** a green run would vouch for exactly the code that breaks in production.
- **Fix:**
  - Pure-logic tests: no database.
  - Database tests: a PostgreSQL 16 service container, the same major version as production. Migrate once per job, roll each test back in a transaction, and give each parallel worker its own database.
  - While switching back to MySQL is still possible (F-03), also run the data-access tests on MySQL 8.
  - SQLite: at most a local fast lane, never the evidence.
- **Evidence:** I ran these checks on both engines. I also measured the speed cost here, over a local socket that will be faster than your CI. A test wrapped in a transaction took about 0.13 ms on PostgreSQL and 0.004 ms on SQLite, roughly a quarter of a second per 2,000 tests. Starting the container and running migrations cost more, and each happens once per job.

### F-03 [blocker · confirmed] Switching DB_CONNECTION back loses data and won't run
- **Where:** `docs/migration-plan.md` step 5
- **Type:** reliability-risk · **Rule:** DATA-MIG-03
- **What:** once writes resume on PostgreSQL, MySQL is out of date. After F-01, `add()` also uses `ON CONFLICT`, which MySQL doesn't support.
- **Why it matters:** a "rollback" would silently drop every order, stock movement and sign-up made since cutover. Then it would fail on the first stock update.
- **Fix:**
  - **Until writes reopen:** keep MySQL read-only and untouched. Aborting means discarding PostgreSQL and setting MySQL back to read-write.
  - **After writes reopen:** roll forward. Agree go/no-go criteria in advance and keep a verified PostgreSQL backup.
  - **A real way back to MySQL:** that needs syncing PostgreSQL → MySQL and code tested on both engines. Build it only if the business needs it.
- **Evidence:** this follows directly from the plan's own steps. I traced it; there was nothing to run.

### F-04 [major · confirmed] Email uniqueness and lookups become case-sensitive
- **Where:** `database/schema-mysql.sql:7-8`
- **Type:** defect · **Rule:** DATA-PORT-01
- **What:** `users_email_unique` uses the `utf8mb4_0900_ai_ci` collation, which ignores case and accents. So MySQL rejects `alice@…` when `Alice@…` exists, and a lookup for `ALICE@…` finds it. PostgreSQL's default collations match strings exactly. On 16.15, both inserts succeeded and the upper-case lookup found nothing. pgloader copies the index but not these matching rules.
- **Why it matters:** after cutover you get duplicate accounts and failed logins and password resets.
- **Fix:**
  - Lower-case emails before saving, and add `CREATE UNIQUE INDEX users_email_lower_unique ON users (lower(email))`.
  - Look users up with `lower(email) = lower(?)`. On 16.15 the index rejected the case variant, and the lookup can use it. The `citext` extension is an alternative.
  - Check other columns where code relies on `=`, `LIKE` or sorting that ignores case or accents.
- **Evidence:** I ran the PostgreSQL side. The MySQL side comes from its documentation; there's no MySQL server here.

### F-05 [major · confirmed] Type mappings that change meaning
- **Where:** `database/schema-mysql.sql:2-5`
- **Type:** defect · **Rule:** DATA-TYPE-04
- **What:**
  - **`last_login_at DEFAULT '0000-00-00 00:00:00'`:** PostgreSQL rejects both the value and the default (`date/time field value out of range`). MySQL 8's default strict `sql_mode` would refuse that default too, so your server probably runs a looser mode (not checked).
  - **`is_admin tinyint(1)` → `boolean`:** a literal `WHERE is_admin = 1` fails with `operator does not exist: boolean = integer`. Bound parameters work. PDO returns PHP `true` from PostgreSQL, where MySQL returns an integer today (MySQL side not run).
  - **`datetime` → `timestamptz`:** the loader's session time zone decides which moment each value becomes. The same text became 10:00 UTC with the zone set to `UTC`, and 15:00 UTC with `America/New_York`.
  - **`bigint unsigned`:** PostgreSQL has no unsigned types.
- **Why it matters:** the load can fail, timestamps can shift, and un-cast attributes change from `1` to `true` in API responses and strict comparisons.
- **Fix:**
  - **Zero dates:** count them in every date column, check `@@GLOBAL.sql_mode`, and map them to NULL, meaning "never logged in".
  - **Booleans:** add `boolean` casts to the models. They weren't in the files I had.
  - **Timestamps:** choose `timestamp` or `timestamptz` to match your migrations, and load in the time zone the app wrote in.
  - **Ids:** map unsigned ids to `bigint`.
  - **Schema:** build it by running your Laravel migrations on PostgreSQL, so CI and production match. Then use pgloader for data only, with every mapping written out. I couldn't check pgloader's defaults, because it isn't installed here.
- **Evidence:** I ran each PostgreSQL behaviour above on 16.15.

### F-06 [major · confirmed] Sequences and a foreign-key index after the load
- **Where:** `database/schema-mysql.sql:2,11,21,25`
- **Type:** defect · **Rule:** DATA-IDX-01
- **What:**
  - Loading rows with their existing ids doesn't advance the id sequences. The next normal insert failed with `duplicate key value violates unique constraint "users_pkey"`. It succeeded once I ran `setval` up to `max(id)`.
  - MySQL indexes foreign-key columns automatically; PostgreSQL doesn't. `orders` ended up with only its primary-key index.
- **Why it matters:** inserts fail right after go-live. Joins on `orders` and user deletes slow down as `orders` grows.
- **Fix:** after the load, compare every sequence with `max(id)`. Index `orders.user_id`. `stock_levels.warehouse_id` is already covered by its unique index.
- **Evidence:** I ran both on 16.15.

### F-07 [major · possible] The 2-hour freeze is a guess until rehearsed
- **Where:** `docs/migration-plan.md` steps 1–2
- **Type:** question
- **What:** the plan has no data sizes, no timing and no verification steps.
- **Why it matters:** an overrun means a longer outage or a rushed go/no-go decision.
- **Fix:**
  - **Rehearse:** time a full run on a production-sized copy: load, index builds, verification and smoke tests. Verify row counts, per-table totals such as `sum(quantity)`, sequences and zero dates.
  - **Stopping writes:** maintenance mode, queue workers and scheduler stopped, MySQL `super_read_only`.
  - **Switching:** host, port and credentials change too. Rebuild the config cache and restart the queue workers.
  - **Schema location:** from memory, pgloader may put tables in a schema named after the source database (`shop`) rather than `public`. I couldn't verify that, so check.
- **Evidence:** no data volumes were provided, and I didn't run pgloader.

## Revised plan
1. Fix engine-specific SQL. Record one mapping decision per type and collation (F-01, F-04, F-05).
2. Run CI on PostgreSQL 16. Also run the data-access tests on MySQL 8 until MySQL is retired (F-02).
3. Build the schema from your migrations, plus the two new indexes. Use pgloader for data only (F-05, F-06).
4. Rehearse on a production-sized copy until it goes without surprises (F-07).
5. Cut over in order: stop writes, load, verify, smoke-test, go/no-go, reopen. Before reopening, aborting means putting MySQL back to read-write. After reopening, roll forward (F-03).

## Verification
| Check | Command | Result |
|---|---|---|
| Engines referenced | `python3 scripts/repo_survey.py .` | MySQL in `.env.example`, SQLite in `phpunit.xml` |
| PostgreSQL schema leads | `python3 scripts/schema_lint.py database --dialect postgresql` | 3 leads; the relevant one is the unindexed `orders.user_id` |
| Your `StockRepository.php` | `php run_repo.php`: PHP 8.3.6 PDO with a stand-in `DB` facade (no Laravel here), on SQLite 3.45.1 in memory and a scratch PostgreSQL 16.15 | `add()` fails on both. `lowStock()` passes on SQLite and fails on PostgreSQL |
| Schema behaviour | `php semantics.php`, `php booleans.php`, on my translation of your schema | As quoted in F-02 and F-04 to F-06 |
| Upsert under concurrency | `php conc.php`: 8 processes × 500 calls | 1 row, quantity 4,000, no errors |
| Per-test overhead | `php bench.php`: 2,000 transactions, run twice | PostgreSQL 0.12–0.13 ms; SQLite 0.004 ms |
| Not run | MySQL 8 (no server here), pgloader (not installed), Laravel, your test suite | — |

## Scope
- **Reviewed:** the five files, read in full. `warehouses` is referenced but not defined in the schema file, so I stubbed it.
- **Not reviewed:** not available here: your Laravel version, `config/database.php`, migrations, models, tests, data volumes and MySQL's `sql_mode`.
- **Assumptions:** production is MySQL 8.x and the target is PostgreSQL 16.x (exact minor versions unknown). Every MySQL behaviour above comes from MySQL's documentation, not a run. The schemas I tested are my own translations, not pgloader or Laravel output.

## Trace

**Shell commands run, in order** (SKILL = `/home/claude/work/repo/skills/software-engineering-intelligence`; S = `/tmp/eval-xdb/scratch`):
1. `mkdir -p /tmp/eval-xdb && cd /tmp/eval-xdb && bash SKILL/evals/cross-database-migration/place-files.sh && find /tmp/eval-xdb -type f | sort`: copied the 5 fixture files into the workspace.
2. `cd SKILL && ls references references/data references/testing references/languages references/workflows assets/templates scripts`: listed the reference, template and script files.
3. `wc -l` on 4 guide files, `command -v` for sqlite3/psql/postgres/pg_ctl/initdb/mysql/mysqld/mariadb/php/pgloader/docker, `ls /usr/lib/postgresql`, a Python sqlite3 version print: psql, php and the docker CLI were found. There was no sqlite3 CLI, no MySQL/MariaDB and no pgloader. `/usr/lib/postgresql/16` exists, and Python's SQLite is 3.53.1.
4. `ls /usr/lib/postgresql/16/bin; psql --version; php --version; php -m | grep …; docker info; id -un`: PostgreSQL 16.15 server binaries (initdb, pg_ctl, postgres) are present. PHP 8.3.6 has pdo_sqlite, pdo_pgsql and pdo_mysql. The Docker daemon was unreachable. Running as root.
5. `python3 scripts/rules.py show DATA-PORT-01 TEST-DATA-01 TEST-DATA-02 DATA-MIG-03 DATA-BACKUP-01 DATA-TYPE-04` plus `grep` for the T-32/T-34 rows in `references/knowledge-model.md`: printed the rule texts and both tension rows.
6. `python3 SKILL/scripts/repo_survey.py /tmp/eval-xdb`: MySQL is referenced in `.env.example` and SQLite in `phpunit.xml`, with an engine-mismatch note. No tests, CI or migrations were found.
7. `python3 SKILL/scripts/schema_lint.py /tmp/eval-xdb/database/schema-mysql.sql --dialect postgresql` (and `mysql`): error "not a directory"; the script takes a directory.
8. `python3 SKILL/scripts/schema_lint.py /tmp/eval-xdb/database --dialect postgresql` and `--dialect mysql`: PostgreSQL gave 3 leads (FK `orders.user_id` without index, free-text `status`, `datetime` without zone). MySQL gave 2 leads (no FK-index lead).
9. `getent passwd postgres; ls -ld /tmp/eval-xdb`: a `postgres` system user exists.
10. `mkdir` and `chown` of `S/pgdata` and `S/pgsock`; `initdb`; `pg_ctl start -l S/pg.log …`; `psql …`: initdb succeeded. The start failed because the log file wasn't writable by postgres, so psql couldn't connect.
11. `mkdir` and `chown` of `S/pglog`; `pg_ctl start` on port 54329, Unix socket only; `psql -c "select version(); show lc_collate; …"`: the server started (PostgreSQL 16.15). `show lc_collate` errored, because that setting no longer exists in PostgreSQL 16.
12. `psql -c "create database shop_test"`; a `pg_database` collation query; `php -r` printing the pdo_sqlite version: the database was created with collation C.UTF-8 and encoding UTF8. pdo_sqlite uses SQLite 3.45.1.
13. `php S/php/run_repo.php` (first version): `add()` failed on both engines. `lowStock()` passed on SQLite and failed on PostgreSQL. The SQLite-style upsert was "ambiguous" on PostgreSQL. The qualified upsert gave 7 on both.
14. `php S/php/run_repo.php` (one MySQL-ism per variant): backticks, `IFNULL` and `LIMIT 0, 100` each failed alone on PostgreSQL and passed on SQLite. The rewritten query passed on both.
15. `php S/php/semantics.php`:
    - SQLite accepted the `varchar(40)` overflow, `'abc'` in an integer column, an orphan FK (`foreign_keys` = 0) and the zero date. PostgreSQL rejected all four.
    - Both engines accepted case-variant emails, and the upper-case lookup returned 0 rows on both.
    - PostgreSQL: `boolean = integer` error; duplicate `users_pkey` until `setval`; `orders` had only its primary-key index; the same text in `timestamptz` became 10:00 vs 15:00 UTC.
16. `php conc.php setup && for i in 1..8; do php conc.php worker 500 & done; wait; php conc.php check`: rows=1, total=4000, about 0.8 s wall time.
17. `php S/php/bench.php && php S/php/bench.php`: per transaction, PostgreSQL took 0.132 and 0.123 ms, SQLite 0.004 ms. Creating the schema took 15.2 and 9.7 ms on PostgreSQL, 0.3 ms on SQLite.
18. `psql` heredoc testing a `lower(email)` unique index: the case variant was rejected (duplicate key), the `lower()` lookup returned the row, and with `enable_seqscan=off` the plan used an Index Scan on `users_email_lower_unique`.
19. `pg_ctl stop; pgrep -a postgres; find /tmp/eval-xdb …`: my server stopped. The other postgres processes listed belong to other workspaces (`/tmp/eval-norm`, `/tmp/eval-ledger`); I left them alone. Listed the workspace files.
20. `pg_ctl start …; php S/php/booleans.php; pg_ctl stop`: the literal `is_admin = 1` failed, while bound int, string and bool parameters worked (count=1). The fetched value is a PHP bool `true`. Server stopped again.
21. `python3 SKILL/scripts/check_report.py S/answer.md` plus `wc`/`awk` word counts: first draft had 9 errors (missing "Why it matters"/"What"/"Fix" fields) and 1 warning (1,984 words).
22. `grep` of `SKILL/scripts/check_report.py`: the required finding fields are Where, Type, What, Why it matters, Fix and Evidence; the review budget is about 1,800 words.
23. `python3 SKILL/scripts/check_report.py S/answer.md` (second draft): 0 errors, 1 warning (1,827 words).
24. `python3 SKILL/scripts/check_report.py S/answer.md` (final draft, the answer above): 0 errors, 0 warnings.

**Scratch files written** (Write/Edit tools, not shell; all under `S/`): `php/harness.php` (stand-in `DB` facade, per-engine schemas), `php/run_repo.php`, `php/semantics.php`, `php/conc.php`, `php/bench.php`, `php/booleans.php`, `answer.md`. Nothing under `/home/claude/work/repo` was modified.

**Skill files read:**
- **In full:** `SKILL.md`, `references/workflows/database-review.md`, `references/data/engines.md`, `references/testing/database-matrix.md`, `references/languages/php-laravel.md`, `assets/templates/migration-plan.md`, `assets/templates/review-report.md`.
- **In part, via shell:** the T-32/T-34 rows of `references/knowledge-model.md` (grep); six rule entries via `scripts/rules.py show`; the field list and budget in `scripts/check_report.py` (grep).
- **Scripts executed:** `repo_survey.py`, `schema_lint.py`, `rules.py`, `check_report.py`.
- **Not opened:** the case's `graders/` folder, `case.yaml`, and the contents of `place-files.sh` (only executed). I also didn't read the routed but unneeded `references/workflows/test-strategy.md`, `references/languages/sql.md` or `references/data/types.md`.
