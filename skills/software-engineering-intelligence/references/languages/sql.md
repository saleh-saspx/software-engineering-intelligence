# SQL and relational databases

Rules: `../rules/data-api.md` (DATA-*), SEC-INJ-01, REL-CONS-*, PERF-IO-*. Procedure:
`../workflows/database-review.md`. Engine behaviour differs — confirm the engine and version
before advising.

## Schema design
- Constraints carry invariants: `NOT NULL`, `UNIQUE`, `FOREIGN KEY`, `CHECK` (DATA-SCHEMA-01).
- Types: `NUMERIC/DECIMAL` (or integer minor units) for money (DATA-TYPE-01); PostgreSQL
  `timestamptz` for instants, stored in UTC (REL-TIME-03); proper booleans/enums instead of magic
  strings; `text` vs. bounded `varchar` per engine norms.
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
- PostgreSQL does **not** create indexes on foreign-key columns automatically; MySQL/InnoDB does
  require/create one.
- Verify with `EXPLAIN` / `EXPLAIN ANALYZE` on production-like data; remove unused indexes based on
  usage statistics (e.g. `pg_stat_user_indexes`).

## Transactions and concurrency
- Default isolation differs: PostgreSQL READ COMMITTED; MySQL/InnoDB REPEATABLE READ. Choose
  deliberately for the invariant (DATA-TXN-02): neither default prevents write skew on invariants
  that span rows. With SERIALIZABLE, retry the whole transaction on serialization failure
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
  large tables often use gh-ost or pt-online-schema-change.
- Backfills as separate, batched, idempotent, resumable jobs (DATA-BATCH-01).
- Rehearse on a production-sized copy and record duration and lock modes (DATA-MIG-03); write
  non-trivial changes up with `../../assets/templates/migration-plan.md`.

## Security
Least-privilege database users per application (no superuser app connections) and a separate
migration role (DATA-SEC-01); separate credentials per environment; no credentials in migrations
or seeds committed to the repo (SEC-SECRET-01); audit sensitive data columns (SEC-DATA-01);
encrypted, isolated backups with tested restores (DATA-BACKUP-01).

## Tools
`EXPLAIN (ANALYZE, BUFFERS)`, `pg_stat_statements`, `auto_explain`, slow query logs; sqlfluff
(lint); `scripts/migration_lint.py` (this skill's dialect-aware migration leads); squawk
(PostgreSQL migration linter), strong_migrations (Rails), django-migration-linter; the ORM's
migration tooling. Connection pools: bounded per instance, with statement, lock and
idle-in-transaction timeouts (DATA-CONN-01).
