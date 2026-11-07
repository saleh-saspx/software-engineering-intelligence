# Data and API rules (DATA-*, API-*)

Database design and modelling, migrations on live systems, types, transactions and isolation,
connections, data access, privacy, tenancy, database security, format evolution, backups,
replication, growth, batch processing and audit trails; API contracts, errors, idempotency,
pagination, resource design. Field meanings: `index.md`. Database dialect specifics:
`../languages/sql.md`. Review procedure: `../workflows/database-review.md`.

Areas: DATA-SCHEMA · DATA-MODEL · DATA-MIG · DATA-IDX · DATA-TYPE · DATA-TXN · DATA-CONN ·
DATA-ACCESS · DATA-PRIV · DATA-TENANT · DATA-SEC · DATA-AUDIT · DATA-EVOL · DATA-BACKUP ·
DATA-REPL · DATA-SCALE · DATA-BATCH · API-CONTRACT · API-ERR · API-IDEMP · API-PAGE · API-DESIGN

## Data

### DATA-SCHEMA-01 · The database enforces the invariants it can
- level: strong | severity: major | provenance: synthesized
- sources: S1 G26 (Be Precise — check that a "unique" record really is unique); S8 §7.2.1 (the shared store enforces consistency, concurrency control and integrity constraints for every accessor); X14; T-20
- why: Application-only checks are bypassed by concurrent requests, scripts, other services and bugs; constraints hold for every writer.
- signals: Uniqueness enforced only in code; missing `NOT NULL` on required columns; foreign keys absent "for performance"; enums as free text.
- fix: `UNIQUE`, `NOT NULL`, `FOREIGN KEY`, `CHECK` constraints and proper types; handle constraint violations as expected errors.
- verify: Schema shows the constraint; a test inserting a violating row fails at the database.
- except: Deliberately denormalised analytical stores; sharded systems where FKs are impossible (document the alternative).
- related: REL-CONS-03, DATA-MIG-01

### DATA-MODEL-01 · Choose the store for its access pattern and consistency need; one system of record per fact
- level: strong | severity: major | provenance: synthesized
- sources: S8 §14.4.3 (Stateful Services — PostgreSQL as the system of record with transactions, constraints and durability; Redis for loss-tolerant data; never treat the cache as the source of truth), §7.2.1 (Shared-Data Pattern — the store enforces consistency, concurrency control, integrity and durability); X14
- why: Stores differ in what they guarantee. Transactional facts placed in a store chosen for speed or schema flexibility — a cache, a search index, a document store without multi-document transactions — lose their invariants, and a fact copied to several stores with no single authority ends up disagreeing with itself.
- signals: Balances, orders or entitlements kept only in Redis, a search index or a queue; a document store holding data with cross-entity invariants and no transactions; the same fact written independently to two stores; "NoSQL for scale" without a measured scale need; several stores with no stated owner per fact.
- fix: A transactional relational store as the default system of record; derived stores (caches, search, analytics, read models) fed from it through change data capture or an outbox, and rebuildable; one owner per fact; a specialised store only for a measured access pattern, recorded in an ADR.
- verify: For each important entity the design names its system of record, and derived stores can be rebuilt from it (tested, or a documented procedure).
- related: PERF-CACHE-01, ARCH-STYLE-02, DATA-SCHEMA-01, ARCH-DEC-01

### DATA-MODEL-02 · Normalise transactional schemas; denormalise deliberately, with a documented sync mechanism
- level: contextual | severity: minor–major | provenance: extension
- sources: X14; T-20
- applies: OLTP schemas. Reporting and analytical stores follow their own modelling rules.
- why: Duplicated facts drift: every copy needs code to keep it consistent, and the bug that forgets one copy is silent. Denormalisation is a legitimate read-performance trade-off only when its consistency mechanism is explicit.
- signals: The same attribute stored in several tables with no sync mechanism; comma-separated lists or JSON blobs holding relational data that is queried or constrained; derived status columns updated by hand; denormalised totals with no reconciliation and no recorded trade-off.
- fix: Model to roughly third normal form by default. When denormalising for reads, name the source of truth and the mechanism (same-transaction update, trigger, materialised view, projection), add a reconciliation check, and record it as a trade-off. Use JSON columns for genuinely schemaless attributes only.
- verify: Each duplicated attribute has a named source and sync mechanism; a reconciliation query finds no drift.
- related: DATA-MODEL-01, TD-CLS-02, DATA-SCHEMA-01

### DATA-MIG-01 · Schema migrations are versioned, reviewed and safe for a running system
- level: strong | severity: major–blocker | provenance: synthesized
- sources: S8 §14.3.2 (blue-green deployments: the shared schema must stay compatible with both versions), §14.3.4 (irreversible migrations cannot be rolled back); X11 (DDL lock levels in the engine manuals); X14
- why: Migrations run against production data, often while old code is still serving traffic; a locking or destructive migration is an outage or data loss.
- signals: Manual schema changes; `DROP`/`RENAME` of columns still read by deployed code; adding `NOT NULL` without default on large tables; index creation that locks writes; no down/forward-fix plan.
- fix: Migration tool (Flyway, Liquibase, Laravel/Django/Rails migrations, golang-migrate, Alembic); expand → migrate → contract across releases; online index creation where supported; test on production-like volumes.
- verify: Migration applied to a copy of realistic data; old and new code both work during the window.
- auto: `scripts/migration_lint.py` (leads, dialect-aware); squawk (PostgreSQL); strong_migrations (Rails); django-migration-linter.
- related: DATA-MIG-02, DATA-MIG-03, DLV-REL-01, AGT-SAFE-01

### DATA-MIG-02 · Never edit applied migrations; keep data migrations idempotent
- level: strong | severity: major | provenance: extension
- sources: X14
- why: Editing an applied migration forks environments; re-running a non-idempotent data migration corrupts data.
- signals: Diffs changing old migration files; data backfills inside schema migrations without guards; migrations depending on application models that will change.
- fix: Add a new migration; write backfills as separate, re-runnable, batched jobs; snapshot needed logic inside the migration.
- verify: Applied migration files are unchanged in the diff; the backfill can be re-run with no change in result.
- auto: `scripts/migration_lint.py --git-base <ref>` (edited applied migrations; backfills inside schema migrations).
- related: DATA-MIG-01, DATA-BATCH-01

### DATA-MIG-03 · Migrations are rehearsed on production-like data and stay compatible with the code running during rollout
- level: strong | severity: major–blocker | provenance: synthesized
- sources: S8 §14.3.2 (blue-green: shared schemas stay compatible with both versions), §14.3.4 (Rollback versus Roll-Forward — irreversible migrations; fast roll-forward is itself a safety property; untested rollback is unreliable); X11 (lock modes of DDL statements; online DDL options)
- why: During rolling, blue-green or canary deploys old and new code run against the same schema. A migration only the new code understands breaks the old instances; one that locks a large table for minutes is an outage; one that cannot be undone needs a rehearsed way forward.
- signals: A migration and the code that depends on it shipped in one step; DDL on large tables never timed against realistic volume; no `lock_timeout` (PostgreSQL) or online-DDL settings (MySQL); migrations never applied in CI from an empty database and from the previous release; large backfills inside the schema migration's transaction; no written plan for irreversible steps.
- fix: Expand → migrate → contract across releases (DATA-MIG-01); apply every migration in CI from scratch and from the previous release's schema; rehearse large-table DDL on a production-sized copy and record duration and lock mode; set lock timeouts and retry; write the roll-forward for irreversible steps with `../../assets/templates/migration-plan.md`.
- verify: CI applies migrations both ways; the plan records measured duration and lock mode for large tables; old and new application versions pass smoke tests against the intermediate schema.
- auto: `scripts/migration_lint.py` (non-concurrent index builds, NOT NULL and constraint validation under lock, renames, drops, volatile defaults, backfills inside migrations).
- related: DATA-MIG-01, DATA-MIG-02, DLV-REL-02, DATA-BACKUP-01

### DATA-IDX-01 · Index for real query patterns, and check plans
- level: contextual | severity: minor–major | provenance: extension
- sources: X14
- why: Missing indexes make queries scan; excess indexes slow writes and bloat storage.
- signals: Filters/joins/sorts on unindexed columns of large tables; foreign keys without indexes (in engines that don't create them); duplicate or unused indexes.
- fix: Add composite indexes matching `WHERE`/`ORDER BY` order; verify with `EXPLAIN`/`EXPLAIN ANALYZE`; drop unused ones based on usage stats.
- related: PERF-IO-01, PERF-IO-02

### DATA-TYPE-01 · Money is never a binary floating-point number
- level: mandatory | severity: major | provenance: direct
- sources: S1 G26 (Be Precise — floating point for currency; use integers and handle rounding); X15 Item 48 (Avoid float and double if exact answers are required)
- why: Binary floats can't represent most decimal fractions; totals drift and reconciliation fails.
- signals: `float`/`double`/`FLOAT`/`REAL` or JS `number` arithmetic for amounts; `round()` sprinkled to hide drift.
- fix: Integer minor units or decimal types (`BigDecimal`, `decimal.Decimal`, `NUMERIC(p,s)`, `brick/money`, `shopspring/decimal`, `dinero.js`/`big.js`), with explicit rounding rules and currency.
- verify: Tests with values like 0.1 + 0.2 and many-line totals.
- related: DES-DOM-01

### DATA-TXN-01 · Keep transactions short and free of remote calls
- level: strong | severity: major | provenance: extension
- sources: X14; S1 G26; X19 Ch.11 (transaction scope in database access)
- why: Long transactions hold locks and connections; remote calls inside them make DB availability depend on another system and can't be rolled back anyway.
- signals: HTTP/email/queue calls between `BEGIN` and `COMMIT`; user think-time inside transactions; default isolation assumed for invariants that need stronger guarantees.
- fix: Do remote work before/after; use outbox for messages; choose isolation level deliberately for the invariant.
- verify: No remote call sits between transaction begin and commit; lock wait/transaction duration metrics are stable.
- related: REL-CONS-01, REL-TIME-01, DATA-TXN-02

### DATA-TXN-02 · Choose the isolation level for the invariant, and retry serialization failures
- level: strong | severity: major | provenance: synthesized
- sources: X11 (PostgreSQL and MySQL manuals — transaction isolation, serialization failures, deadlock detection); X19 Ch.11 (transactions and isolation); S8 §7.2.1 (the store enforces concurrency control)
- why: Default isolation (READ COMMITTED in PostgreSQL, REPEATABLE READ in MySQL InnoDB) permits anomalies — lost updates, write skew, phantoms — that break invariants spanning several rows. Stronger levels prevent them but abort transactions the application must retry.
- signals: Multi-row invariants ("one active subscription per customer", "seats ≤ capacity", "the on-call roster is never empty") checked with SELECT then INSERT/UPDATE at default isolation; SERIALIZABLE or REPEATABLE READ used without a retry loop for serialization failures and deadlocks; the isolation an operation relies on stated nowhere.
- fix: Give each multi-row invariant a mechanism: a constraint (unique, exclusion, check), a single conditional statement, explicit row locks (`SELECT … FOR UPDATE`), or SERIALIZABLE with bounded retries of the whole transaction on serialization failure (SQLSTATE 40001) and deadlock (40P01 in PostgreSQL). Keep the retried unit free of external side effects.
- verify: A concurrent test interleaving two transactions cannot violate the invariant; retries are bounded and visible in metrics or logs.
- related: DATA-TXN-01, DATA-TXN-03, REL-CONS-03, SEC-RACE-01

### DATA-TXN-03 · Detect concurrent edits across requests with version checks
- level: strong | severity: major | provenance: extension
- sources: X14; X11 (optimistic locking in the ORMs: JPA `@Version`, Rails `lock_version`, conditional updates in Django and Laravel)
- why: A user loads a record, someone else changes it, and the first user's save silently overwrites that change ("last write wins"). A database transaction cannot see the conflict because it spans two requests.
- signals: Edit forms or APIs that PUT whole objects without a version or ETag; updates that write every column whether or not it changed; several people editing the same records (back office, collaboration); no 409 or 412 path in the API.
- fix: A version column (or ETag) read with the record and checked on write (`UPDATE … WHERE id = ? AND version = ?`), with a clear conflict response (HTTP 409, or 412 with If-Match); partial updates for independent fields.
- verify: A test with two clients editing the same record makes the second save fail with a conflict instead of overwriting the first.
- related: DATA-TXN-02, REL-CONS-03, API-IDEMP-01

### DATA-CONN-01 · Connection pools are bounded and every statement has a time limit
- level: strong | severity: major | provenance: synthesized
- sources: X19 Ch.11 (connection pools; prepared statements and statement pooling); X6 (timeouts); X11 (PostgreSQL `statement_timeout`, `lock_timeout`, `idle_in_transaction_session_timeout`; driver statement caches)
- why: Unbounded pools exceed the database's connection limit under load, and queries or lock waits without limits pile up until every application thread is stuck behind one slow statement.
- signals: Pool size unset, or instances × pool size above the database's connection limit; no statement or lock timeouts; connections held across remote calls or user think time; a new connection per request without a pool; sessions left idle in transaction.
- fix: One pool per process, sized from the database limit divided by the number of instances with headroom for administration and migrations; statement timeouts per workload (short on request paths, longer for reports), lock timeouts for DDL and hot rows, idle-in-transaction timeouts; prepared statements and the driver's statement cache for repeated queries.
- verify: Configuration shows bounded pools and timeouts; a test with a stalled query gets a timeout error rather than a hung request; pool saturation stays below the limit under load.
- related: REL-TIME-01, DATA-TXN-01, REL-RES-02, PERF-SCALE-02

### DATA-ACCESS-01 · Data access is concentrated, not scattered
- level: contextual | severity: minor–major | provenance: synthesized
- sources: S2 Ch.23 (Database Gateways; Data Mappers); S2 Ch.30
- why: SQL or ORM calls spread through controllers, templates and helpers make schema changes risky and security review hard.
- signals: Queries in views/templates; the same query written several ways; raw SQL in presentation code.
- fix: Route persistence through the project's chosen mechanism (repositories/gateways, ORM models, query objects) — one per context.
- except: Framework idioms that place queries on models (Active Record scopes) are a concentrated location.
- related: ARCH-DET-01, SEC-INJ-01

### DATA-PRIV-01 · Personal data has a purpose, a retention period and a deletion path
- level: contextual | severity: major | provenance: extension
- sources: S5 A6 Sensitive Data Exposure; X14 (privacy regulation practice)
- why: Data kept without purpose is liability; regulations require minimisation, access and erasure.
- signals: PII copied into logs, analytics and backups without controls; no way to delete a user's data; test environments with production PII.
- fix: Data inventory; minimisation; retention jobs; deletion/anonymisation flows; masked data outside production. Involve privacy/legal experts for regulated data.
- related: SEC-DATA-01, SEC-DATA-02, DATA-SCALE-01

### DATA-TENANT-01 · Tenant isolation is enforced by default in the data layer and tested
- level: mandatory | severity: blocker | provenance: synthesized
- sources: S8 §14.1.2 (Multi-Tenancy and Horizontal Scaling — cross-tenant data leaks and noisy neighbours); S5 A4 Insecure Direct Object Reference; S6 §4.5.4 (WSTG-ATHZ-04)
- applies: Systems where several customers' data share a database, schema or table.
- why: In a shared schema one missing tenant filter leaks another customer's data; isolation that depends on every developer remembering a WHERE clause fails eventually.
- signals: Tenant ID taken from the request body or URL instead of the authenticated session; queries on tenant-owned tables without a tenant filter; raw SQL, exports and reporting jobs that bypass the ORM's tenant scope; caches, search indexes or object storage keyed without the tenant; unique constraints that ignore the tenant column.
- fix: Derive the tenant from the authenticated principal and apply it automatically (global query scopes, repository base classes; PostgreSQL row-level security as defence in depth); include the tenant in unique constraints, cache keys, storage paths and search filters; use separate schemas or databases where regulation or noisy-neighbour risk demands it.
- verify: Cross-tenant tests — a user of tenant B requesting tenant A's objects by ID, list, search and export gets nothing; a scan of queries on tenant-owned tables finds no unscoped access.
- related: SEC-AUTHZ-02, TEST-SEC-01, PERF-SCALE-03, DATA-SEC-01

### DATA-SEC-01 · Database accounts follow least privilege; schema changes and runtime access use different credentials
- level: strong | severity: major | provenance: synthesized
- sources: S8 §11.5 (least privilege for users, services and tokens; secrets management); S5 A6 Sensitive Data Exposure; X23 (least privilege)
- why: An application connecting as the database owner or superuser turns any SQL injection or credential leak into full control: dropping tables, reading every schema, running server-side functions.
- signals: Application connection strings using `postgres`, `root`, `sa` or the schema owner; one account shared by the application, migrations, reporting and people; the same credentials in every environment; no audit of privileged database access.
- fix: A runtime role limited to the data manipulation it needs on its own schema; a separate migration role used only by the deployment pipeline; read-only roles for reporting; per-environment credentials from a secret manager, rotated; privileged access audited.
- verify: In a test environment the runtime role cannot run DDL or read other services' schemas; credentials differ per environment.
- related: SEC-SECRET-01, SEC-PRIV-01, DATA-TENANT-01

### DATA-AUDIT-01 · Money and security-relevant changes keep an append-only history
- level: contextual | severity: major | provenance: synthesized
- sources: S8 §3.7.2 (STRIDE — repudiation: denying an action); S5 Reviewing Logging Code; X14
- applies: Balances, payments, ledgers, inventory, permissions and other records where "who changed what, and when" must be answerable.
- why: Updating money or permissions in place destroys the evidence needed for reconciliation, disputes and incident investigation, and makes repudiation easy.
- signals: Balances stored as a single mutable number with no movement records; role or permission changes with no record of who made them; audit data only in best-effort application logs; audit tables the application can update or delete.
- fix: Record movements as immutable entries and derive balances from them (double-entry ledgers); write an append-only audit record of security-relevant changes (actor, action, before and after, time, correlation ID) in the same transaction as the change; deny UPDATE and DELETE on audit tables to the application role; reconcile derived balances against entries on a schedule.
- verify: Every balance can be recomputed from its entries; a test changing a role produces an audit row in the same transaction; the application role cannot alter audit rows.
- related: DATA-TYPE-01, SEC-MON-01, REL-CONS-01, DATA-SEC-01

### DATA-EVOL-01 · Persisted and exchanged data formats evolve compatibly
- level: strong | severity: major | provenance: synthesized
- sources: X15 Item 74 (Implement Serializable judiciously — a serialized form becomes part of the exported API), Item 75 (Consider using a custom serialized form); S8 §14.3.2 (old and new versions run side by side during deployment); X8
- why: Data outlives the code that wrote it. JSON columns, serialized blobs, cached objects, files and queued messages written by one version are read by the next (and, during rollout, by the previous one); incompatible changes surface as deserialization failures long after the deploy.
- signals: Native language serialization (Java serialization, pickle) of domain objects into databases, caches or queues; renamed or retyped fields in stored JSON with no reader for the old shape; enums persisted by ordinal; required fields added to message schemas; no version marker in stored documents or events.
- fix: Explicit, language-neutral formats (JSON, Avro, Protobuf) with a schema; additive changes (new optional fields with defaults); readers tolerant of unknown fields and of the previous shape; version markers and upcasters for stored documents; enums stored by name; schema-compatibility checks in CI for messages.
- verify: A test reads data written by the previous version (fixtures kept in the repository), and the previous version tolerates the new shape wherever both run during rollout.
- related: API-CONTRACT-01, ARCH-STYLE-03, SEC-INJ-03, DATA-MIG-01

### DATA-BACKUP-01 · Backups are proven by restores, against stated recovery objectives
- level: strong | severity: major–blocker | provenance: extension
- sources: X14; S8 §14.3.4 (irreversible changes need a recovery path)
- why: A backup that has never been restored is a hope. Without a recovery point objective (how much data may be lost) and a recovery time objective (how long recovery may take), nobody knows whether the backup scheme is adequate until it is needed.
- signals: No documented RPO or RTO; backups never restored in a drill; backups in the same host, account or region as the database; unencrypted backups containing personal data; destructive migrations or bulk deletes run without a fresh, verified backup; point-in-time recovery disabled where the RPO requires it.
- fix: State RPO and RTO per data store; automate backups (with point-in-time recovery where needed), encrypted and isolated (separate account or region, immutable retention); schedule and time restore drills; take and verify a backup before irreversible data changes (AGT-SAFE-01).
- verify: The latest restore drill's date, duration and result are recorded and meet the RTO; backup age meets the RPO.
- related: DATA-MIG-03, AGT-SAFE-01, SEC-DATA-01

### DATA-REPL-01 · Reads from replicas and caches tolerate their lag; read-your-writes paths use the primary
- level: contextual | severity: major | provenance: synthesized
- sources: S8 §14.1.6 (consistency versus availability per feature), §14.4.3 (the cache is not the source of truth); X14
- applies: Systems with read replicas, caches, search indexes or CQRS read models.
- why: Replicas and derived stores lag. Reading from them right after a write shows users stale data (the order that "disappears"), and decisions taken on stale data — authorisation, balances — can be wrong.
- signals: Read-after-write flows (create, then redirect to the view) served from a replica; permission or balance checks against replicas or caches; replication lag not monitored; failover procedures that silently drop writes the replica had not received.
- fix: Route reads by consistency need: the primary (or session stickiness after a write) for read-your-writes and decisions, replicas for lag-tolerant reads within a lag budget; monitor lag and send reads to the primary when it exceeds the budget.
- verify: A test or staging check with injected replica lag shows read-your-writes flows still correct; replication lag has an alert.
- related: ARCH-DIST-01, PERF-CACHE-01, DATA-MODEL-01

### DATA-SCALE-01 · Plan data growth: retention, archiving and partitioning before tables become hot
- level: contextual | severity: minor–major | provenance: extension
- sources: X14
- why: Tables that only grow make every operation slower and riskier — index maintenance, vacuum, backups, restores and migrations all scale with size — and deleting old data late is itself a large, locking operation.
- signals: No retention policy for logs, events, sessions, audit trails or soft-deleted rows; append-only tables with hundreds of millions of rows and no partitioning; bulk DELETE jobs that lock or bloat tables; analytics queries running on the OLTP primary; sharding proposed before indexes, query fixes, caching and replicas were tried.
- fix: Retention per data class (respecting legal holds — DATA-PRIV-01); time-based partitioning for append-heavy tables so old data is dropped by partition; archiving to cheaper storage; analytics on replicas or a warehouse; sharding only with a key that matches the dominant access pattern, after cheaper steps, recorded in an ADR.
- verify: Each large table has a stated retention period and growth estimate; old-data removal runs as partition drops or bounded batches.
- related: DATA-PRIV-01, PERF-IO-02, DATA-BATCH-01, PERF-SCALE-02

### DATA-BATCH-01 · Batch jobs are chunked, restartable and idempotent, and isolate bad records
- level: strong | severity: major | provenance: extension
- sources: X20 Ch.4–6 (jobs and steps, chunk-oriented processing, job repository state, controlling restart), Ch.11 (Scaling and Tuning — multithreaded steps, partitioning, remote chunking), Ch.12 (Testing Batch Processes); X13
- why: A job that processes millions of rows in one transaction holds locks and memory for hours; when it fails at row 900,000 it either starts over or leaves half-applied state; and one malformed record should not stop the whole run.
- signals: Whole tables loaded into memory; one transaction per job; no record of progress, so restarts reprocess everything (double charges, duplicate emails); a single bad record aborts the run; jobs that cannot safely run twice; nothing preventing two concurrent runs of the same job.
- fix: Process in chunks with a commit per chunk; persist job and step state (such as the last processed key) so a restart resumes where it stopped; make writes idempotent (upserts, natural keys, processed markers); skip and record bad records up to a limit and retry transient errors; prevent concurrent runs; partition the key range only when measured throughput requires it.
- verify: A test kills the job midway and restarts it — the final state equals a clean run with no duplicates; a bad record lands in the error report without stopping the job.
- related: REL-CONS-02, DATA-TXN-01, DATA-MIG-02, PERF-IO-02

## API

### API-CONTRACT-01 · Published contracts change compatibly or are versioned
- level: constraint | severity: major–blocker | provenance: synthesized
- sources: S4 (Interfaces — APIs and published contracts — as architecturally significant decisions); X8
- why: Consumers you don't control break when fields are removed, renamed, retyped or semantics change.
- signals: Removed/renamed response fields; new required request fields; changed enum values or status codes; behaviour changes behind the same version.
- fix: Additive changes only within a version; deprecate with timelines; new version for breaking changes; semantic versioning for libraries.
- verify: Contract/schema diff check in CI (TEST-CONTRACT-01).
- related: TEST-CONTRACT-01, API-CONTRACT-02, DES-LSP-01

### API-CONTRACT-02 · Contracts are explicit, documented and validated at the edge
- level: strong | severity: minor–major | provenance: extension
- sources: X14
- why: Implicit contracts ("whatever the code returns") change by accident.
- signals: No OpenAPI/GraphQL schema/Protobuf definitions; docs out of sync with behaviour; requests not validated against the schema.
- fix: Schema-first or code-generated schemas kept in the repo; request validation from the schema; examples in docs.
- verify: Schema file exists in the repo, is validated in CI, and matches responses in contract/integration tests.
- related: API-CONTRACT-01, SEC-VAL-01

### API-ERR-01 · One consistent, safe error format with correct status codes
- level: strong | severity: minor | provenance: synthesized
- sources: S6 §4.8 (WSTG-ERRH-01/02); X14 (e.g. Problem Details, RFC 9457)
- why: Inconsistent errors force every client to special-case; leaky errors help attackers.
- signals: 200 responses carrying errors; stack traces in bodies; different error shapes per endpoint.
- fix: Single error schema (type, message, correlation ID, field errors); 4xx for client errors, 5xx for server errors; map exceptions at one boundary.
- verify: Error responses across endpoints share one schema; tests assert status codes for client and server errors.
- related: SEC-ERR-01, CODE-ERR-02

### API-IDEMP-01 · Respect method semantics; make retried writes idempotent
- level: strong | severity: major | provenance: extension
- sources: X13; X14 (HTTP method semantics); S8 §7.5.4 (RESTful APIs — POST is not idempotent, PUT is; network retries can double-book a repeated POST; idempotency keys)
- why: Clients and proxies retry; GET must be safe; POSTs that create or charge need protection against duplicates.
- signals: State changes on GET; payment/order creation without idempotency keys; PUT implemented as non-idempotent append.
- fix: Safe GETs; idempotency keys stored with results for unsafe operations; PUT/DELETE idempotent by design.
- verify: Replaying the same request with the same idempotency key yields one effect and the same response (test).
- related: REL-CONS-02, SEC-CSRF-01

### API-PAGE-01 · Collections are paginated with bounded page sizes
- level: strong | severity: major | provenance: extension
- sources: X14
- why: Unbounded list endpoints are performance and DoS liabilities and break as data grows.
- signals: List endpoints returning all rows; client-controlled `limit` without a maximum; offset pagination on very large, changing datasets.
- fix: Default and maximum page sizes; cursor/keyset pagination for large or live data.
- verify: Requesting a page larger than the maximum returns the maximum; responses include a next cursor/page.
- related: PERF-IO-02, SEC-API-01

### API-DESIGN-01 · APIs expose purpose-built models, not internal schema
- level: contextual | severity: minor–major | provenance: synthesized
- sources: S2 Ch.20 (Request and Response Models); S2 Ch.22 (Which Data Crosses the Boundaries)
- why: Exposing tables/entities couples every client to the schema and leaks fields.
- signals: Endpoints mirroring tables one-to-one; internal IDs, flags and timestamps exposed by default; clients needing many calls for one screen.
- fix: Resource models designed for consumers; serializers with allow-listed fields; consistent naming and casing.
- related: ARCH-DEP-03, SEC-DATA-01
