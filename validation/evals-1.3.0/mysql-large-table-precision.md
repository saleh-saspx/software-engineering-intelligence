**No. Don't run it as written, and the quiet Friday-night window doesn't change that.** Widening `amount` makes MySQL copy the whole 80M-row `payments` table, and every insert and update is blocked until the copy finishes. Afterwards each reporting replica repeats the copy and falls behind. Low traffic only means fewer payments fail per minute. The other two changes can go on Friday with small fixes. The `amount` change needs an online schema-change tool (or a planned payments outage) and a decision about rounding first.

Verdict: blocked. Split the migration and give the type change its own plan.

What I assumed (from the README and your message): MySQL 8.0 on InnoDB, exact 8.0.x version unknown; about 80M rows; about 20 writes/s on Friday night and 150/s at peak; two reporting replicas. I couldn't run anything on MySQL or Laravel, so every duration below is an estimate.

**Findings, most severe first**

- [blocker · likely] `database/migrations/2026_11_20_000000_widen_payment_amounts.php:11`: changing `amount` from `DECIMAL(10,2)` to `(19,4)` copies the full table and blocks writes while it runs. MySQL 8.0 can't change a DECIMAL's precision or scale in place, so it uses the COPY algorithm. That rebuilds the table and all its indexes; reads continue, but writes wait. At 80M rows, expect anything from tens of minutes to hours (an estimate; row width, indexes and disks decide). At 20 writes/s, each hour leaves about 72,000 payment writes stuck behind the lock. Expect requests to time out and connections to pile up. The ALTER then replicates as a single statement. Each replica starts it only after the primary has finished and applies nothing else in the meantime, so reporting data stays out of date for about as long again. The copy also needs enough free disk for a full copy of the table on all three servers. Fix: run this change with gh-ost or pt-online-schema-change. Both copy the rows into a shadow table in chunks, slow down when the replicas fall behind, and swap the tables briefly at the end. Check their requirements first: gh-ost needs row-based binary logs and doesn't support foreign keys (pt-online-schema-change handles them, with care), and both need a primary or unique key. The other option is a planned payments outage, sized by a measured rehearsal. (DATA-MIG-03)
- [major · likely] `app/Models/Payment.php:10`: the precision change is only half done. The model still casts `amount` to `decimal:2`, so Eloquent returns amounts rounded to 2 places. Meanwhile the column holds 4, and the reporting app sees 4 because it reads the replicas directly. Once anything writes a third or fourth decimal place, the app and the reports disagree. Anything calculated from `$payment->amount` (refunds, totals) silently loses digits. I also believe Eloquent compares decimal fields after casting when it checks what changed. If so, an update that only changes the last two decimals may not be saved at all. I couldn't check this because Laravel isn't installed here, so it's worth a test. Fix: first settle why the column is being widened. If you only need larger amounts, use `DECIMAL(19,2)` and nobody's rounding changes. If you need 4 decimals, write down where rounding happens and which rounding mode applies. Switch the cast to `decimal:4` once the column is widened; before that, MySQL would round 4-decimal writes back to 2. Tell the reporting team, and test values like 12.3456, 0.0050 and 100,000,000.0000 going in and out of the database on MySQL, not SQLite. (DATA-TYPE-02)
- [major · likely] `…widen_payment_amounts.php:12`: `TIMESTAMP` is the wrong type for `card_expires_at`. A card expiry is a calendar date, not a point in time. MySQL `TIMESTAMP` stops at 2038-01-19 03:14:07 UTC, so a 5-year card issued from January 2033 onwards can't be stored. It also converts values through the session time zone, which your connection config doesn't set. As a result, 2031-08-31 00:00 can come back as 30 August in a session with a different time zone (the reporting app's, for example). Also, midnight on the 31st marks the start of the last valid day, not its end. Fix: `$table->date('card_expires_at')->nullable()` with a `'date'` cast. That costs nothing now; changing it later means another migration on 80M rows. (DATA-TYPE-04)
- [major · likely] `…widen_payment_amounts.php:10-14`: three schema changes in one migration, with no lock timeout. Laravel sends them as separate ALTER statements (`migrate --pretend` shows them), and MySQL commits each one as soon as it finishes. If the index build fails after the type change has committed, the schema is left half-changed. Laravel doesn't record the migration as run, so a second attempt fails on the column that already exists. Every ALTER, even an instant one, also needs a brief exclusive metadata lock on the table. If a long transaction is open on `payments`, the ALTER waits for it (MySQL's default `lock_wait_timeout` is one year), and every new query on the table queues behind the ALTER. Fix: one change per migration, plus `SET SESSION lock_wait_timeout = 5` and a retry. Also add explicit `ALGORITHM` and `LOCK` clauses, so MySQL fails with an error instead of quietly choosing a blocking method. (DATA-MIG-02)
- [major · likely] `…widen_payment_amounts.php:17-24`: `down()` can't safely undo this. Narrowing back to `DECIMAL(10,2)` is another blocking full copy. It rounds away any extra decimals written in the meantime, and under MySQL 8.0's default strict mode it fails on any amount above 99,999,999.99. Treat the widening as one-way: take a backup and test that it restores, and plan how you would fix forward. (DATA-BACKUP-01)
- [minor · possible] `…widen_payment_amounts.php:11,20`: in Laravel 11, `->change()` rewrites the whole column definition, and any attribute you don't repeat (nullable, default, unsigned, comment) is dropped. This comes from the Laravel 11 upgrade notes; I couldn't verify it here. Compare the migration with `SHOW CREATE TABLE payments` and repeat those attributes in `up()` and `down()`.

**What can go on Friday:** two separate migrations (a sketch I haven't run):

```php
// A: expiry column. Metadata-only on 8.0.12+; with ALGORITHM=INSTANT MySQL refuses rather than copies.
DB::statement('SET SESSION lock_wait_timeout = 5');
DB::statement('ALTER TABLE payments ADD COLUMN card_expires_at DATE NULL, ALGORITHM=INSTANT');

// B: index. Built online on the primary; writes continue.
DB::statement('SET SESSION lock_wait_timeout = 5');
DB::statement('ALTER TABLE payments ADD INDEX payments_merchant_id_created_at_index (merchant_id, created_at), ALGORITHM=INPLACE, LOCK=NONE');
```

B still takes a while on 80M rows, and each replica repeats it afterwards. Reporting will be behind for as long as the build takes, so time it on a copy first. During both migrations, pause long-running reports. On the replicas, a long report holds a metadata lock that the replicated change must wait for, and new reports queue behind it. Deploy code that writes `card_expires_at` only after A has run.

**The `amount` change, later**
1. Decide the scale and the rounding rules (see above).
2. Restore a recent backup onto a production-sized server running the same MySQL version. That proves the backup works and gives you a rehearsal. Time the tool run there and check disk space.
3. Run the tool so it slows down whenever replica lag builds up, and do the final swap at a quiet time. Stop if lock waits appear, if replica lag goes beyond what reporting can accept, or if payment errors rise.
4. Then ship the cast change. Also ship a Laravel migration that skips when `information_schema` already shows `DECIMAL(19,4)`. That way CI and dev still get the change, production records it, and nobody runs the copy again.

**What I need from you**
- The output of `SELECT VERSION();` and `SHOW CREATE TABLE payments` (to see the current `amount` attributes and any foreign keys), plus the table's size on disk.
- Does your deploy run `php artisan migrate --force` automatically? If so, don't merge this file as it is: merging it means it runs on the next deploy, whatever the time.
- Why 4 decimals rather than just larger amounts? Is there a currency column?
- How much replica lag can reporting tolerate?

Scope: I read README.md, config/database.php, the migration and app/Models/Payment.php in full. I haven't seen the code that writes `amount` or `card_expires_at`, the reporting app, other migrations, tests, or CI and deploy configuration.

Checks run:

| Check | Command | Result |
|---|---|---|
| Migration lint (MySQL) | `python3 migration_lint.py . --dialect mysql` | 1 high-risk lead: line 11 `->change()`, likely a table rewrite under lock |
| Schema lint (MySQL) | `python3 schema_lint.py . --dialect mysql` | 1 lead: `card_expires_at` is TIMESTAMP (2038 limit, session time zone) |
| Repository survey | `python3 repo_survey.py .` | MySQL referenced in config; no tests, CI or composer files among these four files |
| PHP syntax | `php -l` on the three PHP files | no syntax errors (checks syntax only) |
| Migration on MySQL | none | not run: no MySQL server available here, so no durations were measured |
| SQL that Laravel generates | none | not run: Laravel isn't installed here; `php artisan migrate --pretend` on your side shows the exact statements |

## Trace

`<skill>` = /home/claude/work/repo/skills/software-engineering-intelligence

**Shell commands run (in order)**
1. `ls -la <skill>/ <skill>/references/ <skill>/scripts/ <skill>/assets/`: listed the skill's layout (SKILL.md, references/, scripts/, assets/templates/, evals/).
2. `mkdir -p /tmp/eval-mysql && cd /tmp/eval-mysql && bash <skill>/evals/mysql-large-table-precision/place-files.sh && echo "---" && find /tmp/eval-mysql -type f | sort`: placed 4 files (README.md, config/database.php, the migration, app/Models/Payment.php). The script printed nothing itself.
3. `for t in mysql mysqld mysqladmin mariadb mariadbd php composer sqlite3 psql postgres docker pt-online-schema-change gh-ost; do command -v …; done; python3 --version; ls /usr/sbin/mysqld /usr/libexec/mysqld`: only php, composer, the psql client and the docker CLI exist. There is no MySQL/MariaDB server and no gh-ost or pt-osc. Python is 3.13.18.
4. `php -v | head -2; php -m; timeout 10 docker images; timeout 20 find / -xdev -type d (…/illuminate/database or …/laravel/framework); ls ~/.cache/composer; ls ~/.composer`: PHP 8.3.6 with pdo_mysql and pdo_sqlite. The docker daemon isn't running, there's no Laravel on disk and no composer cache, so neither MySQL nor Eloquent could be executed.
5. `ls -la <skill>/references/data/ …/languages/ …/rules/ <skill>/assets/templates/ <skill>/references/testing/`: listed the reference and template files.
6. `cd <skill> && python3 scripts/rules.py show DATA-MIG-01 DATA-MIG-02 DATA-MIG-03 DATA-TYPE-02 DATA-TYPE-04 DATA-REPL-01`: printed the six rule entries.
7. `cd /tmp/eval-mysql && python3 <skill>/scripts/migration_lint.py /tmp/eval-mysql --dialect mysql`: 1 high lead (line 11, alter-column-type, DATA-MIG-01). It gave no lead for the index, the missing `lock_wait_timeout`, or the three-statement implicit-commit risk; I raised those from sql.md and engines.md.
8. `cd /tmp/eval-mysql && python3 <skill>/scripts/schema_lint.py /tmp/eval-mysql --dialect mysql`: 1 high lead (card_expires_at TIMESTAMP: 2038 range and session time zone, DATA-TYPE-04). Its suggested DATETIME fix doesn't suit a calendar date, so I recommended DATE per types.md §4.
9. `cd /tmp/eval-mysql && python3 <skill>/scripts/repo_survey.py /tmp/eval-mysql`: 3 PHP files, 0 tests, no CI, manifests or lockfiles, MySQL referenced through the config default, no git history.
10. `cd <skill> && grep -n -i -E "confirmed|likely|possible" references/knowledge-model.md | head -30; sed -n '1,200p' assets/templates/review-report.md`: got the confidence-label definitions and the review template.
11. `cd /tmp/eval-mysql && for f in <migration> app/Models/Payment.php config/database.php; do php -l "$f"; done`: no syntax errors in all three.
12. `cd <skill> && grep -n -E "DATA-BACKUP-01|TEST-DATA-02|DATA-MIG-0[123]|DATA-TYPE-0[24]|DATA-REPL-01|DATA-BATCH-01" references/rules/index.md`: every cited rule ID exists.
13. `cd <skill> && sed -n '1,60p' scripts/check_report.py`: read the checker's usage and header.
14. `cd <skill> && sed -n '60,200p' scripts/check_report.py`: read the light-format checks and word budgets (the light default is 450 words).
15. `python3 <skill>/scripts/check_report.py /tmp/eval-mysql/.scratch/answer.md --light --budget 1500`: 0 errors, 0 warnings on the draft.
16. `python3 <skill>/scripts/check_report.py /tmp/eval-mysql/.scratch/answer.md --light | grep -i words`: 1,429 words outside code. That is over the 450 light default but inside SKILL.md's 600–1,500 range for a schema or migration review.
17. `python3 <skill>/scripts/check_report.py /tmp/eval-mysql/.scratch/answer.md --light --budget 1500; ls -la /tmp/eval-mysql /tmp/eval-mysql/.scratch`: after two accuracy edits, still 0 errors and 0 warnings. The workspace holds the fixtures plus .scratch/answer.md.

**Other actions (not shell):**
- Read the four fixture files.
- Wrote the answer draft to /tmp/eval-mysql/.scratch/answer.md and made two edits to it: changed "after January 2033" to "from January 2033 onwards", and added the `--pretend` pointer.
- Modified nothing under /home/claude/work/repo.
- Did not open the case's graders/ or case.yaml.
- Did not use web tools.

**Skill files read:**
- In full:
  - SKILL.md
  - references/workflows/database-review.md
  - references/languages/sql.md
  - references/data/engines.md
  - references/data/types.md
  - references/languages/php-laravel.md
  - assets/templates/migration-plan.md
  - assets/templates/review-report.md (via sed)
- In part:
  - references/knowledge-model.md (grep for the confidence and severity lines only)
  - references/rules/index.md (grep for the cited IDs only)
  - Rule entries through `rules.py show`: DATA-MIG-01/02/03, DATA-TYPE-02/04, DATA-REPL-01
  - scripts/check_report.py (lines 1–200)

None of the answer's facts came from the user's memory.
