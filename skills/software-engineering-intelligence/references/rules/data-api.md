# Data and API rules (DATA-*, API-*)

Database design, migrations, types, transactions, data access, privacy; API contracts,
errors, idempotency, pagination, resource design. Field meanings: `index.md`. Database
dialect specifics: `../languages/sql.md`.

Areas: DATA-SCHEMA · DATA-MIG · DATA-IDX · DATA-TYPE · DATA-TXN · DATA-ACCESS · DATA-PRIV ·
API-CONTRACT · API-ERR · API-IDEMP · API-PAGE · API-DESIGN

## Data

### DATA-SCHEMA-01 · The database enforces the invariants it can
- level: strong | severity: major | provenance: synthesized
- sources: S1 G26 (Be Precise — check that a "unique" record really is unique); X14
- why: Application-only checks are bypassed by concurrent requests, scripts, other services and bugs; constraints hold for every writer.
- signals: Uniqueness enforced only in code; missing `NOT NULL` on required columns; foreign keys absent "for performance"; enums as free text.
- fix: `UNIQUE`, `NOT NULL`, `FOREIGN KEY`, `CHECK` constraints and proper types; handle constraint violations as expected errors.
- verify: Schema shows the constraint; a test inserting a violating row fails at the database.
- except: Deliberately denormalised analytical stores; sharded systems where FKs are impossible (document the alternative).
- related: REL-CONS-03, DATA-MIG-01

### DATA-MIG-01 · Schema migrations are versioned, reviewed and safe for a running system
- level: strong | severity: major–blocker | provenance: extension
- sources: X14
- why: Migrations run against production data, often while old code is still serving traffic; a locking or destructive migration is an outage or data loss.
- signals: Manual schema changes; `DROP`/`RENAME` of columns still read by deployed code; adding `NOT NULL` without default on large tables; index creation that locks writes; no down/forward-fix plan.
- fix: Migration tool (Flyway, Liquibase, Laravel/Django/Rails migrations, golang-migrate, Alembic); expand → migrate → contract across releases; online index creation where supported; test on production-like volumes.
- verify: Migration applied to a copy of realistic data; old and new code both work during the window.
- related: DATA-MIG-02, DLV-REL-01, AGT-SAFE-01

### DATA-MIG-02 · Never edit applied migrations; keep data migrations idempotent
- level: strong | severity: major | provenance: extension
- sources: X14
- why: Editing an applied migration forks environments; re-running a non-idempotent data migration corrupts data.
- signals: Diffs changing old migration files; data backfills inside schema migrations without guards; migrations depending on application models that will change.
- fix: Add a new migration; write backfills as separate, re-runnable, batched jobs; snapshot needed logic inside the migration.
- verify: Applied migration files are unchanged in the diff; the backfill can be re-run with no change in result.
- related: DATA-MIG-01

### DATA-IDX-01 · Index for real query patterns, and check plans
- level: contextual | severity: minor–major | provenance: extension
- sources: X14
- why: Missing indexes make queries scan; excess indexes slow writes and bloat storage.
- signals: Filters/joins/sorts on unindexed columns of large tables; foreign keys without indexes (in engines that don't create them); duplicate or unused indexes.
- fix: Add composite indexes matching `WHERE`/`ORDER BY` order; verify with `EXPLAIN`/`EXPLAIN ANALYZE`; drop unused ones based on usage stats.
- related: PERF-IO-01, PERF-IO-02

### DATA-TYPE-01 · Money is never a binary floating-point number
- level: mandatory | severity: major | provenance: direct
- sources: S1 G26 (Be Precise — floating point for currency; use integers and handle rounding)
- why: Binary floats can't represent most decimal fractions; totals drift and reconciliation fails.
- signals: `float`/`double`/`FLOAT`/`REAL` or JS `number` arithmetic for amounts; `round()` sprinkled to hide drift.
- fix: Integer minor units or decimal types (`BigDecimal`, `decimal.Decimal`, `NUMERIC(p,s)`, `brick/money`, `shopspring/decimal`, `dinero.js`/`big.js`), with explicit rounding rules and currency.
- verify: Tests with values like 0.1 + 0.2 and many-line totals.
- related: DES-DOM-01

### DATA-TXN-01 · Keep transactions short and free of remote calls
- level: strong | severity: major | provenance: extension
- sources: X14; S1 G26
- why: Long transactions hold locks and connections; remote calls inside them make DB availability depend on another system and can't be rolled back anyway.
- signals: HTTP/email/queue calls between `BEGIN` and `COMMIT`; user think-time inside transactions; default isolation assumed for invariants that need stronger guarantees.
- fix: Do remote work before/after; use outbox for messages; choose isolation level deliberately for the invariant.
- verify: No remote call sits between transaction begin and commit; lock wait/transaction duration metrics are stable.
- related: REL-CONS-01, REL-TIME-01

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
- related: SEC-DATA-01, SEC-DATA-02

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
- sources: X13; X14 (HTTP method semantics)
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
