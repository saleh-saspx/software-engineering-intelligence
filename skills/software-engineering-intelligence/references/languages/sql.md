# SQL and relational databases

Rules: `../rules/data-design.md` and `../rules/data-api.md` (DATA-*), SEC-INJ-01, REL-CONS-*, PERF-IO-*. Procedure:
`../workflows/database-review.md`. Engine behaviour differs — confirm the engine and version
before advising, and record UNKNOWN when they cannot be established. Verified differences between
PostgreSQL, Oracle, MySQL/MariaDB, SQL Server and SQLite: `../data/engines.md`; modelling,
types, internals and query performance: `../data/modeling.md`, `../data/types.md`,
`../data/internals.md`, `../data/performance.md`. Many examples below use PostgreSQL syntax; the
principle carries over, the mechanism does not always.

## Schema design
- Constraints carry invariants: `NOT NULL`, `UNIQUE`, `FOREIGN KEY`, `CHECK` (DATA-SCHEMA-01).
- Types: `NUMERIC/DECIMAL` (or integer minor units) for money (DATA-TYPE-01) with explicit
  precision and scale — MySQL and SQL Server default to whole numbers (DATA-TYPE-02); identifiers
  and codes as strings (DATA-TYPE-03); instants in a zone-aware type or UTC by convention
  (PostgreSQL `timestamptz`, SQL Server `datetimeoffset`, Oracle `TIMESTAMP WITH TIME ZONE`; MySQL
  `TIMESTAMP` ends in 2038), business dates as `DATE` — Oracle's `DATE` carries a time (DATA-TYPE-04,
  REL-TIME-03); one stated meaning per nullable column — Oracle stores `''` as NULL (DATA-TYPE-05);
  proper booleans/enums instead of magic strings; `text` vs. bounded `varchar` per engine norms.
- Normalise OLTP schemas by default (roughly third normal form); denormalise deliberately, with the
  read path and the consistency mechanism documented (a `trade-off`, TD-CLS-02).
- Soft deletes complicate uniqueness and every query — use partial unique indexes (PostgreSQL) or
  reconsider.
- Multi-tenant data: tenant key on every tenant-owned table, enforced in queries; PostgreSQL
  row-level security is an option for defence in depth (DATA-TENANT-01, SEC-AUTHZ-02). Include the
  tenant column in unique constraints.
- Ledgers for money: immutable entries, balances derived from them (DATA-AUDIT-01).
- JSON/JSONB columns for genuinely schemaless attributes; not for data you filter, join or
  constrain (DATA-MODEL-02); version the shape of what you store (DATA-EVOL-01).

## Queries
- Always parameterised; identifiers (sort columns) from allow-lists (SEC-INJ-01). Dynamic SQL in
  stored procedures with concatenation is the same vulnerability.
- Select needed columns; bound results (`LIMIT`, keyset pagination for deep pages) (PERF-IO-02).
- Keep predicates sargable: avoid wrapping indexed columns in functions or implicit casts in
  `WHERE`/`JOIN`; use expression indexes if you must.
- Detect N+1 at the ORM layer (PERF-IO-01).

## Indexes
- Most indexes are B-trees (X21 Ch.18): they serve equality and range lookups on a leading prefix
  of the indexed columns, so order composite indexes with equality columns before range columns;
  covering indexes for hot read paths (DATA-IDX-01).
- PostgreSQL, Oracle and SQL Server do **not** create indexes on foreign-key columns automatically;
  MySQL/InnoDB requires and creates one. In Oracle an unindexed foreign key makes parent-key changes
  lock the child table. SQLite enforces foreign keys only after `PRAGMA foreign_keys = ON` on each
  connection.
- Composite order: equality columns, then the range column, then sort columns for top-N; keep
  predicates sargable (DATA-IDX-02).
- Verify with `EXPLAIN` / `EXPLAIN ANALYZE` on production-like data; remove unused indexes based on
  usage statistics (e.g. `pg_stat_user_indexes`).

## Transactions and concurrency
- Default isolation differs: PostgreSQL and Oracle READ COMMITTED; MySQL/InnoDB REPEATABLE READ;
  SQL Server READ COMMITTED with shared locks unless `READ_COMMITTED_SNAPSHOT` is on (the default in
  Azure SQL Database); SQLite SERIALIZABLE with one writer. Choose deliberately for the invariant
  (DATA-TXN-02): no server engine's default prevents write skew on invariants that span rows
  (SQLite's single writer does), and Oracle's
  SERIALIZABLE is snapshot-based. With SERIALIZABLE, retry the whole transaction on serialization failure
  (SQLSTATE 40001) and on deadlock (PostgreSQL 40P01; MySQL error 1213).
- Lost updates across requests: version columns or ETags (DATA-TXN-03); JPA `@Version`, Rails
  `lock_version`, or `UPDATE … WHERE id = ? AND version = ?`.
- Check-then-act: unique constraints with `ON CONFLICT`/`ON DUPLICATE KEY`, conditional `UPDATE …
  WHERE`, `SELECT … FOR UPDATE`, optimistic version columns (REL-CONS-03). Work queues:
  `FOR UPDATE SKIP LOCKED`.
- Acquire locks in a consistent order to avoid deadlocks; keep transactions short and free of
  remote calls (DATA-TXN-01).

## Migrations (DATA-MIG-01/02)
- Expand → migrate → contract across releases; never drop or rename what deployed code still reads.
- PostgreSQL: `CREATE INDEX CONCURRENTLY` (cannot run inside a transaction block); adding a column
  with a non-volatile default is fast since PostgreSQL 11 (volatile defaults such as
  `gen_random_uuid()` still rewrite the table); adding `NOT NULL` to a large table scans it — add a
  `CHECK (col IS NOT NULL) NOT VALID` constraint, `VALIDATE` it, then set `NOT NULL`; add foreign
  keys `NOT VALID` and validate separately. Set `lock_timeout` for DDL.
- Running a concurrent index build outside the migration transaction, per framework: Laravel
  `public $withinTransaction = false;` with `DB::statement('CREATE INDEX CONCURRENTLY …')`; Rails
  `disable_ddl_transaction!` with `add_index …, algorithm: :concurrently`; Django `atomic = False`
  on the migration with `AddIndexConcurrently` (`django.contrib.postgres.operations`); Alembic
  `op.create_index(…, postgresql_concurrently=True)` inside `op.get_context().autocommit_block()`;
  Flyway and plain SQL: a separate migration file containing only that statement, run without a
  wrapping transaction. A failed concurrent build leaves an invalid index — drop it before retrying.
- MySQL: online DDL support (`ALGORITHM=INPLACE/INSTANT`) is version- and operation-dependent;
  large tables often use gh-ost or pt-online-schema-change. An online index build still reads the
  whole table and writes the index (I/O and CPU on the primary), and each replica starts it only
  after the primary has finished and applies nothing newer while it runs, so replication lag grows
  by about the build time: schedule it off-peak and time it on a production-sized copy. DDL commits
  implicitly — as in Oracle — so a failing multi-statement migration leaves a partial schema: one
  change per step.
- Oracle: `CREATE INDEX … ONLINE` and SQL Server `WITH (ONLINE = ON)` avoid blocking writes where the
  edition supports them; check the edition before relying on it.
- SQLite: `ALTER TABLE` can rename, add and drop columns; other changes rebuild the table (create,
  copy, swap) with foreign-key checks handled explicitly.
- Backfills as separate, batched, idempotent, resumable jobs (DATA-BATCH-01).
- Rehearse on a production-sized copy and record duration and lock modes (DATA-MIG-03); write
  non-trivial changes up with `../../assets/templates/migration-plan.md`.

## Security
Least-privilege database users per application (no superuser app connections) and a separate
migration role (DATA-SEC-01); separate credentials per environment; no credentials in migrations
or seeds committed to the repo (SEC-SECRET-01); audit sensitive data columns (SEC-DATA-01);
encrypted, isolated backups with tested restores (DATA-BACKUP-01).

## Tools
`EXPLAIN (ANALYZE, BUFFERS)`, `pg_stat_statements`, `auto_explain`, slow query logs; MySQL
`EXPLAIN ANALYZE`; SQL Server actual plans and Query Store; Oracle `DBMS_XPLAN.DISPLAY_CURSOR`; SQLite
`EXPLAIN QUERY PLAN` — analysing a statement executes it, so roll back DML; sqlfluff (lint);
`scripts/migration_lint.py` (this skill's dialect-aware migration leads); `scripts/schema_lint.py`
(type, key and relationship leads from DDL); squawk
(PostgreSQL migration linter), strong_migrations (Rails), django-migration-linter; the ORM's
migration tooling. Connection pools: bounded per instance, with statement, lock and
idle-in-transaction timeouts (DATA-CONN-01).
