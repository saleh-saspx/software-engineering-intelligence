# Workflow: database, schema and migration review

For reviewing a schema change or migration, the data-access code of a module, or the design and
operation of a whole data tier. Rules: `../rules/data-api.md` (DATA-*), plus REL-CONS-*,
PERF-IO-*, SEC-INJ-01 and DATA-TENANT-01. Engine specifics: `../languages/sql.md`. Plan
template for risky changes: `../../assets/templates/migration-plan.md`.

## Contents
1. Frame the review · 2. Map ownership and access · 3. Schema and model · 4. Queries and indexes ·
5. Transactions and concurrency · 6. Migrations · 7. Operations · 8. Security and privacy ·
9. Testing the data layer · 10. Report

## 1. Frame the review
Collect, or state as assumptions — most database findings depend on them:
- **Engine and version** — DDL locking, isolation defaults and online-DDL support differ between
  PostgreSQL and MySQL and between versions.
- **Size and write rate** of the touched tables. A migration that is instant on 10,000 rows is an
  outage on 100 million; ask when it isn't stated.
- **Deployment model** — rolling, blue-green, canary or maintenance window; whether migrations run
  before or after the new code starts.
- **Criticality** — money, personal data, multi-tenancy; recovery objectives (RPO/RTO) if known.
- **Scope** — one migration, one module's data access, or the data tier.

## 2. Map ownership and access
- Which component owns which tables; which stores are derived (caches, search, replicas, read
  models) and how they are fed (DATA-MODEL-01, ARCH-STYLE-02).
- Where queries live (DATA-ACCESS-01); where raw SQL is built (`scripts/security_scan.py` leads for
  SEC-INJ-01).
- Which features read replicas or caches, and what consistency each needs (ARCH-DIST-01,
  DATA-REPL-01).

## 3. Schema and model
- Invariants enforced by constraints — NOT NULL, UNIQUE, FOREIGN KEY, CHECK (DATA-SCHEMA-01, T-20).
- Types: money as decimal or integer minor units (DATA-TYPE-01); instants with time zone
  (REL-TIME-03); enums or lookup tables instead of free text.
- Normalised by default; denormalisation documented with its sync mechanism (DATA-MODEL-02);
  queried or constrained data hidden in JSON blobs is a smell.
- Keys: stable surrogate keys; natural keys as unique constraints; enumerable IDs never the only
  access control (SEC-AUTHZ-02).
- Tenancy: tenant column on tenant-owned tables, included in unique constraints (DATA-TENANT-01).
- Soft deletes: partial unique indexes or a different design.
- Money and permissions: ledger entries and append-only audit (DATA-AUDIT-01).
- Persisted formats (JSON columns, serialized blobs, events): versioned and evolvable (DATA-EVOL-01).

## 4. Queries and indexes
- N+1 and unbounded queries (PERF-IO-01, PERF-IO-02); count queries per request in a test or
  debug log when it is cheap.
- Indexes match real access patterns (DATA-IDX-01): check `EXPLAIN (ANALYZE, BUFFERS)` on
  production-like data; equality columns before range columns; foreign-key columns indexed on
  PostgreSQL.
- Sargable predicates; keyset pagination for deep pages (API-PAGE-01).
- Statement timeouts on request paths (DATA-CONN-01).

## 5. Transactions and concurrency
- The transaction is the consistency boundary (REL-CONS-01, DES-DOM-02); no remote calls inside it
  (DATA-TXN-01); an outbox when a write must also publish a message.
- Every multi-row invariant has a mechanism — constraint, conditional statement, row lock, or
  SERIALIZABLE with bounded retries (DATA-TXN-02).
- Check-then-act on shared rows (REL-CONS-03, SEC-RACE-01): reproduce with parallel requests when
  it is cheap — a confirmed race is far more persuasive than a suspected one.
- Edits that span requests carry a version or ETag (DATA-TXN-03).
- Retried writes and redelivered messages are idempotent (REL-CONS-02, API-IDEMP-01).
- Locks are taken in a consistent order; deadlocks are retried, not surfaced as errors.

## 6. Migrations
1. Run `python3 scripts/migration_lint.py PATH` (add `--dialect postgresql|mysql` and
   `--git-base <ref>` for a PR). Its output is leads: whether a lead matters depends on table size,
   engine version and the deployment model.
2. For each statement: which lock does it take, on which tables, and for how long at the real size?
   Does it rewrite the table? (`../languages/sql.md`.) Where DDL is transactional (PostgreSQL), several
   slow steps in one migration hold the first lock until the last step commits: split them.
3. **Compatibility during rollout**: does the code that is deployed now still work after the
   migration? Does the new code work before it? Renames, drops and type changes go through expand →
   migrate → contract (DATA-MIG-01).
4. **Data changes**: backfills are separate, batched, idempotent and resumable jobs, not part of the
   DDL transaction (DATA-MIG-02, DATA-BATCH-01).
5. **Reversibility**: a down migration or a written roll-forward; a verified backup before anything
   irreversible (DATA-BACKUP-01, AGT-SAFE-01).
6. **Rehearsal**: CI applies migrations from scratch and from the previous release; large-table DDL
   is timed on a production-sized copy (DATA-MIG-03).
7. **History**: applied migrations are never edited (DATA-MIG-02; `--git-base` flags modified files).

Common risky operations (PostgreSQL unless noted; confirm against the engine version in use):

| Operation | Risk | Safer sequence |
|---|---|---|
| Add a column with a default | Fast since PostgreSQL 11 for non-volatile defaults; volatile defaults (`random()`, `gen_random_uuid()`, `clock_timestamp()`) rewrite the table; MySQL depends on version and `ALGORITHM` | Constant default or nullable column; backfill volatile values in batches |
| Add `NOT NULL` to an existing column | Full-table scan under an ACCESS EXCLUSIVE lock | `ADD CONSTRAINT … CHECK (col IS NOT NULL) NOT VALID`, then `VALIDATE CONSTRAINT`, then `SET NOT NULL` (PostgreSQL 12+ skips the scan when such a valid check exists) |
| Create an index | A plain `CREATE INDEX` blocks writes for the whole build | `CREATE INDEX CONCURRENTLY`, outside a transaction (framework settings in `../languages/sql.md`); drop an invalid index left by a failed build before retrying |
| Add a foreign key or check constraint | Validates every row while holding locks | `ADD … NOT VALID`, then `VALIDATE CONSTRAINT` in a separate step |
| Change a column's type | Usually rewrites the table under an exclusive lock | New column, dual write, batched backfill, switch reads, drop the old column later |
| Rename a column or table | Instant, but breaks the code still deployed | Add the new name (or a view), migrate readers and writers, drop the old one later |
| Drop a column or table | Instant and irreversible; breaks deployed readers | Stop reading and writing in code first; wait a release; back up; then drop |
| Mass `UPDATE` or `DELETE` | Long locks, table bloat, replication lag | Batched, throttled, resumable job (DATA-BATCH-01) |

Set `lock_timeout` for DDL on busy tables so a migration waiting for a lock does not queue every
other query behind it. For anything beyond additive changes on small tables, write the plan with the
migration-plan template.

## 7. Operations
- Pools and timeouts: instances × pool size within the connection limit; statement, lock and
  idle-in-transaction timeouts (DATA-CONN-01).
- Replicas and caches: lag budgets and read-your-writes routing (DATA-REPL-01, PERF-CACHE-01).
- Growth: retention, partitioning, archiving (DATA-SCALE-01); hot rows and counters (PERF-SCALE-02).
- Recovery: RPO/RTO and the date of the last restore drill (DATA-BACKUP-01) — usually a question for
  the user, since code cannot show it.
- Batch jobs: chunked, restartable, idempotent (DATA-BATCH-01).
- Signals available: slow-query log, `pg_stat_statements`, lock waits, replication lag, pool usage.

## 8. Security and privacy
- Every query parameterised, including dynamic sort columns (SEC-INJ-01).
- Least-privilege runtime role; separate migration role (DATA-SEC-01).
- Tenant isolation by default, with a cross-tenant test (DATA-TENANT-01).
- Personal data: purpose, retention, deletion, masking outside production; encrypted backups
  (DATA-PRIV-01, SEC-DATA-01).
- Audit trail for money and permission changes (DATA-AUDIT-01).

## 9. Testing the data layer
- Repository and gateway tests on the same engine and major version as production (TEST-DATA-01,
  TEST-ENV-01).
- Migrations applied in CI both ways (DATA-MIG-03); fixtures written by the previous version for
  stored formats (DATA-EVOL-01).
- Concurrency tests for multi-row invariants (TEST-CONC-01, DATA-TXN-02).
- Constraint tests: inserting a violating row fails at the database (DATA-SCHEMA-01).

## 10. Report
A single migration gets the light format (SKILL.md §8); larger reviews use the review-report
template. Each migration finding states the statement, its lock and rewrite behaviour on the stated
engine version, the table-size assumption, the effect on running code, and the safe sequence. Label
size-dependent findings ("depends on table size — confirm the row count"). Never call a migration
safe without knowing the engine version and table sizes; say what you assumed.
