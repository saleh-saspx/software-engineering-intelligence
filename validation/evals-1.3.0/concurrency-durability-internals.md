# Ledger: deadlocks, bloat, `synchronous_commit` and the RocksDB idea

## Summary
**Verdict:** changes requested. There are two ordinary bugs and one risky setting. Nothing points to the storage engine.

- **Deadlocks:** `transfer()` locks the two accounts in argument order. When A→B and B→A run together, each holds one row and waits for the other.
- **Bloat:** the monthly report holds one REPEATABLE READ transaction for about 3 hours. Until it ends, VACUUM can't remove any row version that died after the report's snapshot, in any table of the database. `accounts` gets two UPDATEs per transfer, so it should suffer most.
- **`synchronous_commit = off`** fixes neither. On a payments ledger it lets a crash erase transfers that clients were already told had succeeded. Undo it first.
- **RocksDB** would remove neither cause.

I reproduced the first three on a local PostgreSQL 16 using your statements (see Verification).

## Scope
- **Reviewed:** all five files, in full.
- **Not reviewed (not available):** the DDL and indexes, other code that writes to `accounts` or `postings`, production logs and statistics, replication, your RPO, and the rest of `postgresql.conf`. Nothing ran against your systems.
- **Assumptions:** the sandbox schema was `accounts(id PK, balance numeric)` and `postings(id bigserial, account_id FK, amount numeric, posted_at)`.

## Verification
Everything ran on a throwaway PostgreSQL 16.15 instance in a local sandbox. The numbers show the mechanisms, not production magnitudes.

| Check | Command | Result |
|---|---|---|
| Deadlocks, `transfer()` as written | `pgbench -c 16 -j 4 -T 15 --failures-detailed`, transfer()'s statements, 10 accounts (high contention on purpose) | 32 of 146 transactions failed with `deadlock detected` (40P01); 7 transfers/s; ledger balanced |
| Same, locks in ascending id order | same | 0 deadlocks; 47,622 transfers (3,173/s); ledger balanced |
| As written, `synchronous_commit=off` | same, `PGOPTIONS=-c synchronous_commit=off` | 39 of 140 deadlocked |
| Bloat, no long transaction | 20 s of transfers, 10,000 accounts | `accounts` 440 kB → 696 kB |
| Bloat, another session holding a REPEATABLE READ snapshot (it read only `postings`) | same, then `VACUUM (VERBOSE) accounts` | 440 kB → 8,712 kB; "189762 are dead but not yet removable"; removable cutoff = that session's `backend_xmin`; autovacuum (naptime lowered to 5 s in the sandbox) re-ran and removed nothing. After the session committed: 189,762 removed, file still 8,712 kB |
| Durability | 20 acknowledged single-row commits, `pg_ctl stop -m immediate` (a crash), restart | `off`: 0 of 20 survived; `on`: 20 of 20 (`wal_writer_delay` raised to 10 s to make the window deterministic) |

**Not run:** anything on RocksDB (not installed, no network).

## Findings

### F-01 [blocker · confirmed] `synchronous_commit = off` can silently lose confirmed transfers
- **Where:** `ops/postgresql.conf:3`
- **Type:** reliability-risk · **Rule:** DATA-DUR-01
- **What:** PostgreSQL acknowledges COMMIT before the WAL is flushed. After a crash the database is still consistent: there are no half-transfers, and corruption is the risk of `fsync = off`, not this setting. But the latest acknowledged transfers are gone.
- **Why it matters:** The PostgreSQL manual bounds the window at up to 3 × `wal_writer_delay` (default 200 ms; I could not re-check the manual offline). At 3k transfers/s, that is up to about 1,800 confirmed transfers that clients or payment rails acted on and that silently disappear (estimated). The setting didn't help your incidents either. It probably felt faster because a transfer keeps its row locks until its commit is flushed, so busy accounts queue on disk flushes (expected, not measured). F-02 attacks that wait safely.
- **Fix:** Set it back to `on`; a reload applies it. Check `pg_db_role_setting` for overrides. If a workload truly tolerates loss, scope the setting to it with `SET LOCAL synchronous_commit = off` and record the loss window in an ADR. With a synchronous standby, `off` also skips waiting for the standby (manual, not tested). If commit latency is still a measured bottleneck afterwards, check `pg_stat_wal.wal_sync_time` (needs `track_wal_io_timing`) and fix the WAL storage.
- **Evidence:** Reproduced: across a simulated server crash, 0 of 20 acknowledged commits survived with `off` and 20 of 20 with `on`. An OS crash or power loss can additionally lose WAL that was written but not flushed; that case was not simulated.

### F-02 [major · confirmed] `transfer()` locks in argument order, so opposite transfers deadlock
- **Where:** `ledger/transfer.py:3-4`
- **Type:** defect · **Rule:** REL-CONC-02
- **What:** Two opposite transfers each take one lock and wait for the other. After `deadlock_timeout` (1 s by default), PostgreSQL aborts one of them with 40P01. A cycle can involve more than two transfers; one in the sandbox involved five.
- **Why it matters:** Payments fail, everything queued behind those rows stalls for at least a second, and clients retry by hand. The ledger itself stays consistent, because the victims roll back fully (checked).
- **Fix:** Lock in one global order:
```python
def transfer(conn, from_id, to_id, amount):
    first, second = sorted((from_id, to_id))   # one global lock order: lower account id first
    with conn.transaction():
        conn.execute("SELECT balance FROM accounts WHERE id = %s FOR UPDATE", [first])
        conn.execute("SELECT balance FROM accounts WHERE id = %s FOR UPDATE", [second])
        conn.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", [amount, from_id])
        conn.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", [amount, to_id])
        conn.execute("INSERT INTO postings (account_id, amount) VALUES (%s, %s), (%s, %s)",
                     [from_id, -amount, to_id, amount])
```
  Then add three things:
  - A bounded automatic retry of the whole transaction on 40P01, because other code can still lock `accounts` in another order.
  - An idempotency key backed by a unique constraint, so a retry after an ambiguous failure, such as a connection lost during COMMIT, can't post twice.
  - A test that runs opposite transfers in parallel on PostgreSQL.
- **Evidence:** Reproduced: as written, 32 of 146 transactions deadlocked; with ordered locks, 0 of 47,622 did. In production, the DETAIL block of each `deadlock detected` log entry names the statements involved; expect the two `SELECT … FOR UPDATE` on `accounts`.

### F-03 [major · confirmed] The report's 3-hour snapshot stops VACUUM across the whole database
- **Where:** `jobs/monthly_report.py:2-6`
- **Type:** reliability-risk · **Rule:** DATA-TXN-01
- **What:** VACUUM may remove a dead row version only when no open snapshot can still see it. The job keeps one REPEATABLE READ transaction open for about 3 hours. That includes the time spent in `write_report_section`, while the session sits "idle in transaction". Every transfer leaves two dead `accounts` versions, and none created while the job runs can be removed until it commits. This applies to every table, not just the ones the report reads: the sandbox "report" never read `accounts`, yet `accounts` reached 8.7 MB, against 0.7 MB without the open snapshot.
- **Why it matters:** VACUUM later makes the space reusable but doesn't shrink the files, so transfers touch more pages. Meanwhile autovacuum spends hours removing nothing. Separately, the per-account query has no date filter. The job reads every posting ever made, one account at a time, so it gets slower every month.
- **Fix:**
  1. Hold no transaction while writing the report. A closed month's postings don't change (`transfer()` only inserts), so no long snapshot is needed. Read the month by posting time in keyset batches, each batch in its own short transaction, and run the job after month end, because transfers in flight at midnight can commit out of id order. Derive balances from postings. Write the files outside any transaction, and make the job resumable.
  2. If you really need a consistent snapshot of live data, read it from a streaming replica. But `hot_standby_feedback = on` brings the bloat back to the primary, and with it off, long queries get cancelled unless `max_standby_streaming_delay` lets replay wait (manual, not tested).
  3. Set a per-role `statement_timeout` and `idle_in_transaction_session_timeout`. The second one would kill today's job, so fix the job first. `transaction_timeout` doesn't exist in 16. Alert on the oldest snapshot:
     `SELECT pid, state, now()-xact_start AS xact_age, age(backend_xmin) AS xmin_age FROM pg_stat_activity WHERE backend_xmin IS NOT NULL ORDER BY xmin_age DESC;`
     Replication slots (`pg_replication_slots.xmin`) can pin the cutoff too.
  4. Don't run `VACUUM FULL` at peak: it locks the table exclusively while it rewrites it. Freed space gets reused anyway, so shrink only in a planned window.
- **Evidence:** Reproduced: the VACUUM removable cutoff equalled the `backend_xmin` of the session holding the snapshot. On 16, the autovacuum log line (with `log_autovacuum_min_duration` set) says "N are dead but not yet removable"; the phrase in your notes is the wording of older versions.
- **Open question:** Inserts leave no dead rows; the sandbox `postings` table had 0. If your `postings` has dead rows, code outside these files updates or deletes rows there, or rolls back inserts. Compare `n_dead_tup` per table in `pg_stat_user_tables`.

### F-04 [major · likely] RocksDB would not fix either cause
- **Where:** `ops/incident-notes.md:4`
- **Type:** architecture-risk · **Rule:** DATA-MODEL-01
- **What:**
  - **Deadlocks:** any store that gives a transfer exclusive access to two balances either makes opposite orders wait on each other (a deadlock or lock timeout) or aborts one of them at commit. Either way, the fix is lock ordering plus retries (established principle).
  - **Bloat:** any multi-version store keeps the versions an open snapshot can read. In an LSM tree they survive compaction until the snapshot closes. "No vacuum" means compaction instead, which is tuned background I/O (mechanism; RocksDB specifics not checked).
  - **Write speed** isn't the observed limit. LSM trees excel at high-rate ingest. A ledger is read-modify-write on balances plus range reads, which is B-tree OLTP territory. Fixing the lock order alone took the sandbox from 7 to 3,173 transfers/s (measured in the sandbox, under extreme contention).
- **Why it matters:** RocksDB is an embedded key-value library, so in practice you would adopt some database built on it. That means rebuilding constraints, transactions, reporting SQL, backups and point-in-time recovery, and operations, with no gain on these incidents. Its default write also doesn't fsync each write (from its docs as I recall them; not verified here), which is the same trade-off as F-01.
- **Fix:** Fix F-01 to F-03, then measure. If write volume becomes the measured bottleneck, partition `postings` by month first, which also helps the report and retention (expert practice). Consider an engine change only through an ADR backed by numbers.
- **Evidence:** Reasoning from storage-engine mechanisms; nothing was run on RocksDB.

## Also noticed
- `transfer()` reads `balance` but never checks it. If overdrafts aren't allowed, add the check or a `CHECK (balance >= 0)` constraint.
- The column types weren't visible. Amounts must be `numeric`/`Decimal`, never float.

**Order of work:**
1. Turn `synchronous_commit` back on (minutes).
2. Fix the lock order and add the retry and idempotency key.
3. Restructure the report and add the timeouts and the oldest-snapshot alert.
4. Watch dead tuples and the oldest `backend_xmin` through the next month end, then revisit storage only if numbers still point there.

## Trace

**Shell commands run (in order):**
1. `mkdir -p /tmp/eval-ledger && cd /tmp/eval-ledger && bash …/evals/concurrency-durability-internals/place-files.sh && find /tmp/eval-ledger -type f | sort`: placed the 5 fixture files.
2. `grep -n -i -E "postgres|synchronous_commit|deadlock|vacuum|…" references/data/engines.md | head -80`: found the PostgreSQL rows on where old versions live, the cost of long transactions, and the `synchronous_commit` trade-off.
3. `command -v postgres psql pg_ctl initdb … ; ls -d /usr/lib/postgresql/*/bin; python3 -c "<find_spec psycopg/psycopg2/pg8000/asyncpg/rocksdb/sqlite3>"; whoami; id`: `psql` and `/usr/lib/postgresql/16/bin` present; no Python PG driver, no RocksDB, no sqlite3/mysql CLI; running as root.
4. `ls /usr/lib/postgresql/16/bin; ls -d /usr/share/doc/postgresql*; find / -name wal-async-commit.html; getent passwd postgres; pg_lsclusters`: full PG16 server tools (initdb, pg_ctl, pgbench); no offline HTML manual; `postgres` user exists; system cluster 16/main is down and was left untouched.
5. `for r in DATA-TXN-01 DATA-TXN-02 DATA-DUR-01 DATA-MODEL-01 REL-CONC-02 DATA-BATCH-01 DATA-CONN-01 PERF-IO-01 PERF-IO-02 ARCH-DEC-01; do python3 scripts/rules.py show $r; done`: printed the 10 rules.
6. `grep -n "^## " references/knowledge-model.md`: listed sections (used §9).
7. `ls /usr/share/doc/postgresql-16/; find … -iname "*html*"; ls /usr/share/postgresql/16/`: no HTML manual; `postgresql.conf.sample` and similar files present.
8. `runuser -u postgres -- postgres --version; postgres --describe-config | awk …; … | grep -cx transaction_timeout`: PG 16.15; every parameter cited in the answer exists (`synchronous_commit` and the timeouts are user-settable); `transaction_timeout` is absent (count 0).
9. `pgbench --help | grep -E "failures-detailed|max-tries|…"`: both options supported.
10. `initdb -D /tmp/eval-ledger/_scratch/pgdata -A trust …; pg_ctl … start` (unix socket only, port 55432) `; psql "select version()"; psql <pg_settings query>`: server started; defaults confirmed (deadlock_timeout 1 s, wal_writer_delay 200 ms, synchronous_commit on, read committed, fsync on).
11. `cat > _scratch/sql/{schema,transfer_as_is,transfer_ordered,check}.sql; psql CREATE DATABASE ledger; psql -f schema.sql` (10 accounts): assumed schema and pgbench scripts created.
12. `pgbench -c 16 -j 4 -T 15 --failures-detailed -D n_accounts=10 -f transfer_as_is.sql ledger` + `psql -f check.sql`: 32 of 146 failed as deadlocks (21.9%), 7.1 tps, 1,762 ms average latency; 37 "deadlock detected" lines in the server log; ledger balanced (sum 10,000,000.00, postings sum 0, 0 accounts out of balance).
13. `grep -m1 -A6 "deadlock detected" _scratch/pg.log`: a 5-process wait cycle on `accounts` tuples; statement `SELECT balance FROM accounts WHERE id = 9 FOR UPDATE`.
14. `psql -f schema.sql` (reset) + `pgbench … -f transfer_ordered.sql` + check: 0 failures, 47,622 transactions, 3,173 tps, 5.0 ms average; 0 deadlock log lines; ledger balanced.
15. Bloat A/B script: `ALTER SYSTEM` `log_autovacuum_min_duration=0` and `autovacuum_naptime=5s`; schema with 10,000 accounts; Phase A = pgbench for 20 s; Phase B = a background `psql` running `BEGIN ISOLATION LEVEL REPEATABLE READ; SELECT count(*) FROM postings;` then sleeping 50 s before COMMIT, plus the same pgbench, a `pg_stat_activity` query, `pg_stat_user_tables` and `VACUUM (VERBOSE) accounts` before and after the commit. Results: A grew 440 kB → 696 kB. B grew 440 kB → 8,712 kB with 189,762 dead rows not removable; cutoff 149412 equalled the session's `backend_xmin` (idle in transaction for 30 s). After the commit, 189,762 were removed and the size was unchanged. `postings` had 0 dead rows in both phases.
16. `grep -A4 'automatic vacuum of table "ledger.public.accounts"' _scratch/pg.log | …`: autovacuum ran every 5 s and logged "0 removed … 189762 are dead but not yet removable" each time.
17. Crash test: `ALTER SYSTEM SET wal_writer_delay='10s'`; `CREATE TABLE acked`; for each mode in (off, on): `SET synchronous_commit=<mode>`, 20 autocommit INSERTs, `pg_ctl stop -m immediate`, `pg_ctl start`, count rows. Results: off = 20 acknowledged, 0 survived; on = 20 of 20. The log shows crash recovery ("database system was interrupted", "redo starts/done").
18. `ALTER SYSTEM RESET wal_writer_delay`; schema reset; `PGOPTIONS="-c synchronous_commit=off" pgbench … -f transfer_as_is.sql`: 39 of 140 failed as deadlocks (27.9%), 5.9 tps; `wal_writer_delay` back to 200 ms.
19. `psql` checks of the `pg_stat_wal`, `pg_db_role_setting` and `pg_replication_slots` columns, plus `BEGIN; SET LOCAL synchronous_commit=off; SHOW; COMMIT; SHOW`, then `pg_ctl stop -m fast`: all cited columns exist; `SET LOCAL` was scoped to the transaction (off, then on after commit); server stopped.
20. `sed -n '1,60p' scripts/check_report.py | grep …`: read the required sections and fields.
21. `sed -n '36,140p' scripts/check_report.py`: read the reader checks (≈1,800-word budget, jargon, evidence wording).
22. `python3 scripts/check_report.py _scratch/answer.md` + word count: first draft had 0 errors and 1 warning (2,039 words, over budget).
23. `python3 scripts/check_report.py _scratch/answer.md`: compressed draft had 0 errors and 0 warnings.
24. `check_report.py` + word count + `ps aux | grep -c "[p]ostgres -D /tmp/eval-ledger"` + `ls`: final draft had 0 errors, 0 warnings and 1,670 prose words; no sandbox postgres process still running.

**Skill files read:**
- In full: `SKILL.md`, `references/workflows/database-review.md`, `references/data/internals.md` and `assets/templates/review-report.md`.
- In part:
  - `references/knowledge-model.md`: §9, lines 233–260, plus the heading list.
  - `references/data/engines.md`: grep matches only.
  - `scripts/check_report.py`: lines 1–140.
- Rule entries from `rules/data-api.md`, `data-design.md`, `runtime.md` and `architecture.md`, viewed through `scripts/rules.py show`.

**Fixture files read in full:** `README.md`, `ledger/transfer.py`, `jobs/monthly_report.py`, `ops/postgresql.conf` and `ops/incident-notes.md`.

**Notes:**
- I did not open `graders/` or `case.yaml`, and nothing under `/home/claude/work/repo` was modified.
- The skill prefers scratch work outside the user's repo, but the task required staying inside the workspace. So the PostgreSQL sandbox (data directory, log, SQL scripts and the answer draft) lives in `/tmp/eval-ledger/_scratch`, kept separate from the untouched fixture files. It can be deleted.
- I used the installed PostgreSQL 16.15 binaries. Every result labelled "reproduced" or "measured" comes from that local sandbox, not from production.
