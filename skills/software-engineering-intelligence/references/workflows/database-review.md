# Workflow: database design, schema, query and migration review

For designing or reviewing a data model, a schema change or migration, the data-access code of a
module, slow queries and indexes, transaction and durability behaviour, or the design and operation
of a whole data tier. Rules: `../rules/data-design.md` (schema, modelling, keys, types, indexes,
portability) and `../rules/data-api.md` (migrations, transactions, durability and the rest of
operations), plus REL-CONS-*, PERF-IO-*, SEC-INJ-01,
DATA-TENANT-01 and TEST-DATA-02. Engine specifics: `../languages/sql.md` (practice) and
`../data/engines.md` (verified differences). Plan template for risky changes:
`../../assets/templates/migration-plan.md`.

## Contents
1. Frame the review · 2. Map ownership and access · 3. Model, keys and relationships · 4. Data
types · 5. Queries and indexes · 6. Transactions, concurrency and durability · 7. Migrations ·
8. Operations · 9. Security and privacy · 10. Testing the data layer · 11. Portability ·
12. Explaining and reporting

**Reading map** — the knowledge files are cross-referenced; open only what the question needs:

| Question | Design | Mechanism | Evidence |
|---|---|---|---|
| Is this model right? | `../data/modeling.md` | `../data/internals.md` §2 (key choice) | Review checklist, `scripts/schema_lint.py` |
| Is this the right type? | `../data/types.md` | `../data/engines.md` §1 | Round-trip tests on the production engine |
| Why is this query slow, which index? | `../data/modeling.md` §6 | `../data/internals.md` §3, `../data/performance.md` | Plan with actual rows on representative data |
| Is this transaction safe under load? | `../data/modeling.md` §7 (aggregates) | `../data/internals.md` §6–7 | Concurrent test on the real engine |
| Will committed data survive a crash or failover? | — | `../data/internals.md` §5, §8 | Configuration, failover drill |
| Does it work on another engine? | `../data/types.md` | `../data/engines.md` | Category C/D tests (`../testing/database-matrix.md`) |

## 1. Frame the review
Collect, or state as assumptions — most database findings depend on them:
- **Engine and version, in production and in tests** — from configuration, drivers and containers
  (`scripts/repo_survey.py`), or by asking. If it cannot be established, write UNKNOWN and say which
  findings would change; never infer the engine from a framework's default. DDL locking, isolation
  defaults, type semantics and online-DDL support differ between engines and versions.
- **Size and write rate** of the touched tables. A migration that is instant on 10,000 rows is an
  outage on 100 million; ask when it isn't stated.
- **Deployment model** — rolling, blue-green, canary or maintenance window; whether migrations run
  before or after the new code starts.
- **Criticality** — money, personal data, multi-tenancy; recovery objectives (RPO/RTO) if known.
- **Scope** — a design, one migration, one module's data access, a slow query, or the data tier.
- **What you can run** — before relying on documentation alone, look for a local engine: binaries on
  PATH or in the platform's install location (Debian and Ubuntu keep PostgreSQL's server binaries in
  `/usr/lib/postgresql/<version>/bin`), a container runtime, or the project's test database. A
  scratch instance with synthetic data turns "likely" into "confirmed"; label it a sandbox result.

## 2. Map ownership and access
- Which component owns which tables; which stores are derived (caches, search, replicas, read
  models) and how they are fed (DATA-MODEL-01, ARCH-STYLE-02).
- Where queries live (DATA-ACCESS-01); where raw SQL is built (`scripts/security_scan.py` leads for
  SEC-INJ-01).
- Which features read replicas or caches, and what consistency each needs (ARCH-DIST-01,
  DATA-REPL-01).

## 3. Model, keys and relationships
Use the checklist in `../data/modeling.md` §9; `python3 scripts/schema_lint.py PATH` gives leads
from DDL and migrations.
- Each table states one kind of fact; functional dependencies checked: if a fact changes, how many
  rows change? (DATA-MODEL-02; normal forms in `../data/modeling.md` §5.)
- Every relationship has an enforced key at the right cardinality and optionality; no ID lists,
  repeating groups or unenforceable polymorphic references (DATA-MODEL-03).
- Event values captured as of the event — prices, rates, tax, addresses (DATA-MODEL-04).
- No over-normalisation or EAV without a reason (DATA-MODEL-05).
- Keys: surrogate primary keys sized for growth, natural keys enforced unique, key layout suited to
  the engine's storage (DATA-KEY-01, T-33); enumerable IDs never the only access control
  (SEC-AUTHZ-02).
- Invariants enforced by constraints — NOT NULL, UNIQUE, FOREIGN KEY, CHECK (DATA-SCHEMA-01, T-20).
- Tenancy: tenant column on tenant-owned tables, included in unique constraints (DATA-TENANT-01).
- Soft deletes: partial unique indexes or a different design.
- Money and permissions: ledger entries and append-only audit (DATA-AUDIT-01).
- Persisted formats (JSON columns, serialized blobs, events): versioned and evolvable (DATA-EVOL-01).

## 4. Data types
Decide each column with the questions in `../data/types.md` §1 and the cases in §8:
- Money never binary floating point (DATA-TYPE-01); exact numbers with explicit precision, scale and
  a stated rounding step and mode (DATA-TYPE-02).
- Identifiers and codes as strings: account numbers, IBANs, phones, postal and branch codes
  (DATA-TYPE-03).
- Temporal values typed by meaning: instants, business dates, local times with zones, durations
  (DATA-TYPE-04, REL-TIME-03).
- Every nullable column has one stated meaning; NULL, zero and empty are not interchangeable
  (DATA-TYPE-05).
- Statuses as closed sets with enforced transitions; JSON only for genuinely schemaless data
  (DATA-MODEL-02).

## 5. Queries and indexes
Follow the method in `../data/performance.md` §2: find the expensive statements, read the plan with
actual rows, change one thing, re-measure.
- N+1 and unbounded queries (PERF-IO-01, PERF-IO-02); count queries per request in a test or
  debug log when it is cheap.
- Indexes match real access patterns (DATA-IDX-01): equality columns before the range column, sort
  columns for top-N, covering where it pays; check the plan with actual rows on production-like
  data; foreign-key columns indexed where the engine does not do it.
- Predicates the index can use — no functions, conversions or leading wildcards on indexed columns
  (DATA-IDX-02); keyset pagination for deep pages (API-PAGE-01).
- Statement timeouts on request paths (DATA-CONN-01).
- Label every performance claim as expected, estimated or measured (`../data/performance.md` §13);
  never call a query fast or slow from code reading alone.

## 6. Transactions, concurrency and durability
- The transaction is the consistency boundary (REL-CONS-01, DES-DOM-02); no remote calls inside it
  (DATA-TXN-01); an outbox when a write must also publish a message.
- Transactions stay short: no long reports, exports or idle sessions on the primary — under MVCC they
  bloat tables, stall purge or fail with "snapshot too old" (DATA-TXN-01, `../data/internals.md` §6).
- Every multi-row invariant has a mechanism — constraint, conditional statement, row lock, or
  SERIALIZABLE with bounded retries (DATA-TXN-02); remember that snapshot isolation allows write skew.
- Check-then-act on shared rows (REL-CONS-03, SEC-RACE-01): reproduce with parallel requests when
  it is cheap — a confirmed race is far more persuasive than a suspected one.
- Edits that span requests carry a version or ETag (DATA-TXN-03).
- Retried writes and redelivered messages are idempotent (REL-CONS-02, API-IDEMP-01).
- Locks are taken in a consistent order through indexed predicates; deadlocks are retried, not
  surfaced as errors; diagnose from the engine's deadlock report (`../data/internals.md` §7).
- Durability settings and replication mode match the stated RPO per workload (DATA-DUR-01).

## 7. Migrations
1. Run `python3 scripts/migration_lint.py PATH` (add `--dialect postgresql|mysql|oracle|sqlserver|sqlite`
   and `--git-base <ref>` for a PR). Its output is leads: whether a lead matters depends on table size,
   engine version and the deployment model.
2. For each statement: which lock does it take, on which tables, and for how long at the real size?
   Does it rewrite the table? (`../languages/sql.md`.) Where DDL is transactional (PostgreSQL), several
   slow steps in one migration hold the first lock until the last step commits: split them. Where DDL
   commits implicitly (MySQL, Oracle), a failure leaves the schema half-applied: one structural change
   per step, each re-runnable.
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
8. **Type changes** are checked for precision, scale, range and meaning, not just syntax — widening
   `DECIMAL(10,2)` to `(12,4)` changes every consumer's rounding (DATA-TYPE-02).

Common risky operations (PostgreSQL unless noted; confirm against the engine version in use):

| Operation | Risk | Safer sequence |
|---|---|---|
| Add a column with a default | Fast since PostgreSQL 11 for non-volatile defaults; volatile defaults (`random()`, `gen_random_uuid()`, `clock_timestamp()`) rewrite the table; MySQL depends on version and `ALGORITHM` | Constant default or nullable column; backfill volatile values in batches |
| Add `NOT NULL` to an existing column | Full-table scan under an ACCESS EXCLUSIVE lock | `ADD CONSTRAINT … CHECK (col IS NOT NULL) NOT VALID`, then `VALIDATE CONSTRAINT`, then `SET NOT NULL` (PostgreSQL 12+ skips the scan when such a valid check exists) |
| Create an index | A plain `CREATE INDEX` blocks writes for the whole build | `CREATE INDEX CONCURRENTLY`, outside a transaction (framework settings in `../languages/sql.md`); drop an invalid index left by a failed build before retrying. Oracle `ONLINE`, SQL Server `WITH (ONLINE = ON)` where the edition allows; MySQL `ALGORITHM=INPLACE, LOCK=NONE` |
| Add a foreign key or check constraint | Validates every row while holding locks | `ADD … NOT VALID`, then `VALIDATE CONSTRAINT` in a separate step |
| Change a column's type | Usually rewrites the table under an exclusive lock | New column, dual write, batched backfill, switch reads, drop the old column later |
| Rename a column or table | Instant, but breaks the code still deployed | Add the new name (or a view), migrate readers and writers, drop the old one later |
| Drop a column or table | Instant and irreversible; breaks deployed readers | Stop reading and writing in code first; wait a release; back up; then drop |
| Mass `UPDATE` or `DELETE` | Long locks, table bloat, replication lag | Batched, throttled, resumable job (DATA-BATCH-01) |
| SQLite table change beyond rename, add or drop column | `ALTER TABLE` cannot do it | Create a new table, copy, swap, inside a transaction, with foreign-key checks re-enabled afterwards |

Set `lock_timeout` for DDL on busy tables so a migration waiting for a lock does not queue every
other query behind it. For anything beyond additive changes on small tables, write the plan with the
migration-plan template.

## 8. Operations
- Pools and timeouts: instances × pool size within the connection limit; statement, lock and
  idle-in-transaction timeouts (DATA-CONN-01).
- Replicas and caches: lag budgets and read-your-writes routing (DATA-REPL-01, PERF-CACHE-01).
- Growth: retention, partitioning, archiving (DATA-SCALE-01); hot rows and counters (PERF-SCALE-02).
- Recovery: RPO/RTO and the date of the last restore drill (DATA-BACKUP-01) — usually a question for
  the user, since code cannot show it; durability settings and failover mode (DATA-DUR-01).
- Batch jobs: chunked, restartable, idempotent (DATA-BATCH-01).
- Signals available: slow-query logs, `pg_stat_statements`, Query Store, Performance Schema, lock
  waits, oldest open transaction, dead tuples or undo history, replication lag, pool usage.

## 9. Security and privacy
- Every query parameterised, including dynamic sort columns (SEC-INJ-01).
- Least-privilege runtime role; separate migration role (DATA-SEC-01).
- Tenant isolation by default, with a cross-tenant test (DATA-TENANT-01).
- Personal data: purpose, retention, deletion, masking outside production; encrypted backups
  (DATA-PRIV-01, SEC-DATA-01).
- Audit trail for money and permission changes (DATA-AUDIT-01).

## 10. Testing the data layer
- Classify tests by engine dependence and run each category where it must run: none, the production
  engine, a specific engine, or every supported engine (TEST-DATA-02, `../testing/database-matrix.md`).
- Repository and gateway tests on the same engine and major version as production (TEST-DATA-01,
  TEST-ENV-01).
- Migrations applied in CI both ways (DATA-MIG-03); fixtures written by the previous version for
  stored formats (DATA-EVOL-01).
- Concurrency tests for multi-row invariants (TEST-CONC-01, DATA-TXN-02).
- Constraint tests: inserting a violating row fails at the database (DATA-SCHEMA-01).
- Precision and time tests: rounding boundaries, maximum totals, non-UTC sessions and daylight-saving
  changes (DATA-TYPE-02, DATA-TYPE-04).

## 11. Portability
When the product supports several engines, a migration moves between engines, or tests use a
different engine from production: list the differences that matter for this change from
`../data/engines.md` §1–2, map types, constraints and collations by meaning rather than by name, and
require category D or C tests accordingly (DATA-PORT-01, T-34). A mapping table for cross-engine
migrations records each column's source type, target type and the semantic difference.

## 12. Explaining and reporting
A single migration gets the light format (SKILL.md §8); larger reviews use the review-report
template. Each migration finding states the statement, its lock and rewrite behaviour on the stated
engine version, the table-size assumption, the effect on running code, and the safe sequence. Label
size-dependent findings ("depends on table size — confirm the row count"). Never call a migration
safe without knowing the engine version and table sizes; say what you assumed.

For consequential design, type, index, transaction, durability or engine-choice recommendations —
including a verdict on an engine or storage engine the user proposes — or when the user wants to
understand one — follow the explanation order in `../knowledge-model.md` §9: concept, why it
matters here, alternatives, trade-offs, failure modes, when the advice changes, an example, and
engine differences, each labelled as an established principle, a context-dependent recommendation,
engine-specific behaviour or expert practice. Keep it proportionate: small decisions get a sentence.
