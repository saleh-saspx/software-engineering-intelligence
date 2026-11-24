# Storage and transaction internals that matter for design and review

The mechanisms below explain why an index helps or hurts, why a long transaction slows a whole
database, why a setting can lose committed data, and why a key choice costs space everywhere. They are
informed by X25 (storage engines and distributed systems), explained in this skill's own words, with
engine specifics checked in `engines.md`.
Mechanism explains; the plan and the measurement decide (P-73, `performance.md`).

## Contents
1. Pages and memory · 2. Heap and clustered storage · 3. B-trees · 4. Log-structured merge trees
· 5. Write-ahead logging and durability · 6. MVCC and long transactions · 7. Locks and deadlocks ·
8. Replication and distribution · 9. From mechanism to review question

## 1. Pages and memory

Tables and indexes live in fixed-size pages (8 KB in PostgreSQL and SQL Server, 16 KB by default in
InnoDB). Every read and write touches whole pages, cached in a buffer pool. Two consequences:

- Cost is counted in pages touched, not rows returned: a query returning 10 rows scattered over 10
  pages costs 10 page reads; the same rows packed together cost one.
- Performance falls off a cliff when the frequently used pages (the working set) no longer fit in
  memory. A query that was fast on a small copy can be slow in production for this reason alone —
  test with production-like volume (TEST-PERF-01).

## 2. Heap and clustered storage

- **Heap** (PostgreSQL; Oracle and SQL Server heaps): rows live in no particular order; every index
  is separate and points to row locations. PostgreSQL writes a new row version on update; when no
  indexed column changes and the page has room, a heap-only-tuple (HOT) update avoids touching the
  indexes.
- **Clustered / index-organized** (InnoDB always; SQL Server tables with a clustered index — the
  primary key by default; Oracle index-organized tables; SQLite `WITHOUT ROWID`): rows are stored in
  primary-key order inside the B-tree, and secondary indexes store the primary key instead of a row
  address. So the primary key's width is paid in every secondary index, a lookup through a secondary
  index walks two trees, and the key's insert pattern decides page splits.
- **Key choice follows** (DATA-KEY-01, T-33): random keys insert all over the tree, splitting pages and
  keeping more of the index hot in memory; monotonically increasing keys append at the right edge,
  which is compact but can concentrate concurrent inserts on one page (last-page contention at very
  high insert rates).

## 3. B-trees

A B-tree keeps keys sorted in pages linked into a shallow, balanced tree: a root, a few levels of
branch pages, and leaf pages chained in key order. Lookups read one page per level — a handful even
for billions of rows — and range scans then walk the leaf chain.

What follows for design (X26 builds its whole method on this):
- An index serves equality and range predicates, `ORDER BY` and `MIN`/`MAX` on a **leading prefix** of
  its columns; a two-column index sorted by (a, b) cannot find rows by b alone, as a phone book sorted
  by surname cannot find first names.
- After the index finds matching entries, fetching each row from the table is a separate, often
  random, page read; for many rows a full scan is cheaper. An index that also contains every column
  the query needs (covering, index-only scan) avoids the table entirely.
- Every insert, update of an indexed column and delete maintains every index: indexes are paid for
  on each write, in log volume and in memory.
- Pages split when full; fill factor leaves room for updates. Heavy deletes leave sparse pages until
  maintenance compacts them.
- In Oracle, rows whose indexed columns are all NULL are not stored in a B-tree index, so `IS NULL`
  cannot use a single-column index there (X26, "NULL in the Oracle Database").

## 4. Log-structured merge trees

An LSM-tree writes to an in-memory sorted table and a log; full memtables are flushed as immutable
sorted files, and background compaction merges files into larger ones. Reads may consult several
files (Bloom filters skip most); deletes are tombstones removed later by compaction. RocksDB (also
behind MySQL's MyRocks engine), LevelDB and Cassandra use this design.

| Concern | B-tree | LSM-tree |
|---|---|---|
| Writes | In-place page updates; random I/O; write amplification from page rewrites | Sequential appends; high ingest rates; write amplification from compaction |
| Reads | Predictable: one path through the tree | Variable: several files per lookup unless filters and caches hit |
| Space | Fragmentation and fill factor | Obsolete versions and tombstones until compaction |
| Operations | Vacuum or defragmentation, page splits | Compaction tuning; background I/O and CPU spikes |
| Fits | Read-heavy and mixed OLTP, point and range reads with updates | Write-heavy ingest: events, time series, logs, high-churn keys |

Choosing a storage engine or a store built on one is an architecture decision (DATA-MODEL-01,
ARCH-DEC-01): justify it with the measured write rate, read pattern and retention, and price the
operational cost of compaction. Most relational OLTP workloads are served well by B-trees plus time
partitioning for append-heavy tables (DATA-SCALE-01).

## 5. Write-ahead logging and durability

Engines make commits durable by writing the change to a log (WAL, redo log, transaction log) and
forcing it to stable storage **before** acknowledging the commit; data pages are written later, and
checkpoints bound how much log replays after a crash. Group commit flushes many transactions'
records in one write.

Settings that acknowledge a commit before its log is on stable storage trade a window of lost
transactions for latency (DATA-DUR-01):
- PostgreSQL `synchronous_commit = off`: recent commits can be lost in a crash but the database stays
  consistent; `fsync = off` risks corruption and is never a production setting.
- MySQL `innodb_flush_log_at_trx_commit` other than 1: the latest committed transactions can be lost
  on an unexpected exit.
- SQL Server delayed durability: commits are reported before the log is hardened and can be lost on
  crash or failover.
- Asynchronous replication with automatic failover: commits acknowledged by the old primary but not
  yet received by the replica are lost (§8).

Acceptable for caches, analytics staging and other loss-tolerant data, when stated; not for money,
orders or user data unless someone owns that decision in writing.

## 6. MVCC and long transactions

Multi-version concurrency control lets readers see a consistent snapshot while writers create new
row versions; old versions must be kept until no running transaction might still read them. Where
they are kept, and what a long transaction therefore costs, differs by engine (`engines.md` §1):

- **PostgreSQL** keeps old versions in the table; VACUUM removes them only when no snapshot can see
  them, so a transaction left open — an idle session, a long report, a forgotten `BEGIN` — makes
  tables and indexes bloat everywhere. Bound it with `idle_in_transaction_session_timeout` and
  statement timeouts; find culprits by transaction age in `pg_stat_activity`.
- **InnoDB** reconstructs old versions from undo logs; a long transaction blocks purge, and reads of
  rows changed since then do extra work.
- **Oracle** reads old versions from undo; long queries fail with ORA-01555 "snapshot too old" when
  the undo they need has been overwritten.
- **SQL Server** keeps versions in the tempdb version store — or in the user database when
  accelerated database recovery is on (always on in Azure SQL Database) — when snapshot isolation or
  read committed snapshot is on; long transactions grow it.

Snapshots also define anomalies: read committed takes a new snapshot per statement (non-repeatable
reads possible); snapshot-style levels give one snapshot per transaction but still allow **write
skew** — two transactions each check a condition on rows the other then changes. PostgreSQL's
serializable level detects such conflicts and fails one transaction with SQLSTATE 40001; Oracle's
serializable rejects updates of rows changed since the transaction began (ORA-08177) but is
snapshot-based. Invariants spanning rows need a constraint, a lock or a serializable retry loop
(DATA-TXN-02).

Design consequences: keep transactions short and free of user think-time and remote calls
(DATA-TXN-01); run long reports on replicas or exported snapshots; batch large updates
(DATA-BATCH-01); make retries of serialization failures and deadlocks routine.

## 7. Locks and deadlocks

- **Row locks** protect rows being changed; under InnoDB's repeatable read, locking reads and writes
  also take gap (next-key) locks on the scanned index range, so a range update can block inserts
  into the range. An `UPDATE`/`DELETE` whose predicate has no usable index scans and locks far more
  than the rows it changes.
- **Table and schema locks** come with DDL (`../workflows/database-review.md` §6); in Oracle an
  unindexed foreign key makes parent-key changes lock the child table; SQL Server escalates many row
  or page locks into a table lock (around 5,000 locks on one table reference).
- **Deadlocks** are cycles of waits. Engines detect them and abort one transaction (PostgreSQL
  SQLSTATE 40P01; MySQL error 1213). Prevent by acquiring locks in one consistent order (for
  transfers: lock the lower account ID first), keeping transactions short, indexing the predicates
  of updates and the foreign keys checked by deletes, and batching mass updates; then retry the
  victim (DATA-TXN-02, REL-CONC-02). Diagnose from the engine's deadlock report or graph, not from
  the application's stack trace alone.
- **Lock waits** need timeouts (`lock_timeout`, `innodb_lock_wait_timeout`, `LOCK_TIMEOUT` †) so one
  stuck transaction does not queue every request behind it (DATA-CONN-01).

## 8. Replication and distribution

- **Physical replication** ships the log (the replica is a byte-level copy); **logical replication**
  ships row changes (allows different versions, subsets and targets). Both lag.
- **Synchronous** replication waits for a replica before acknowledging commits (no loss on failover,
  higher latency, availability tied to replicas); **asynchronous** replication acknowledges first
  (low latency, a loss window on failover). The recovery-point objective decides (DATA-BACKUP-01).
- **Read replicas** serve lag-tolerant reads; read-your-writes and decisions go to the primary
  (DATA-REPL-01).
- **Failover** must prevent two primaries (fencing); automatic failover with asynchronous replicas
  loses acknowledged commits by design.
- **Consensus and distributed transactions** (X25 Part II): leader election and replicated logs
  (Raft, Paxos) underlie distributed databases; two-phase commit blocks when the coordinator fails, so
  cross-service workflows usually use sagas with idempotent steps and an outbox (X13, REL-CONS-02).

## 9. From mechanism to review question

| Mechanism | Review question | Rules |
|---|---|---|
| Clustered storage | Is the primary key narrow, stable and insert-friendly for this engine? | DATA-KEY-01 |
| B-tree prefix order | Does each hot query's predicate use a leading prefix of an index, equality columns before the range? | DATA-IDX-01 |
| Index maintenance cost | Does each index earn its write cost? | DATA-IDX-01 |
| Row fetch after index | Would a covering index or a different access path read fewer pages? | DATA-IDX-01, PERF-IO-02 |
| WAL and commit | Do durability settings match the stated RPO per workload? | DATA-DUR-01 |
| MVCC retention | Can any transaction stay open for minutes (reports, idle sessions, batch jobs)? | DATA-TXN-01 |
| Snapshot anomalies | Which mechanism protects each multi-row invariant? | DATA-TXN-02 |
| Lock ordering and scope | Do code paths lock shared rows in one order, through indexed predicates? | DATA-TXN-02, REL-CONC-02 |
| Replication mode | Is failover loss compatible with the RPO; do read-your-writes paths avoid replicas? | DATA-REPL-01, DATA-BACKUP-01 |
| LSM versus B-tree | Is a different storage engine justified by a measured workload? | DATA-MODEL-01 |
