# Data rules, part 1: design (DATA-SCHEMA, DATA-MODEL, DATA-KEY, DATA-TYPE, DATA-IDX, DATA-PORT)

Database design: constraints the database enforces, choice of store, normalisation and its limits,
relationships, history, keys, data types, indexes and the predicates that can use them, and engine
portability. Operations — migrations, transactions, durability, connections, tenancy, privacy,
backups, replication, growth, batch jobs — and API rules are in `data-api.md`. Field meanings:
`index.md`. Knowledge behind the rules: `../data/modeling.md`, `../data/types.md`,
`../data/engines.md`, `../data/internals.md`, `../data/performance.md`. Dialect specifics:
`../languages/sql.md`. Review procedure: `../workflows/database-review.md`.

Areas: DATA-SCHEMA · DATA-MODEL · DATA-KEY · DATA-TYPE · DATA-IDX · DATA-PORT

### DATA-SCHEMA-01 · The database enforces the invariants it can
- level: strong | severity: major | provenance: synthesized
- sources: S1 G26 (Be Precise — check that a "unique" record really is unique); S8 §7.2.1 (the shared store enforces consistency, concurrency control and integrity constraints for every accessor); X14; T-20
- why: Application-only checks are bypassed by concurrent requests, scripts, other services and bugs; constraints hold for every writer.
- signals: Uniqueness enforced only in code; missing `NOT NULL` on required columns; foreign keys absent "for performance"; enums as free text.
- fix: `UNIQUE`, `NOT NULL`, `FOREIGN KEY`, `CHECK` constraints and proper types; handle constraint violations as expected errors.
- verify: Schema shows the constraint; a test inserting a violating row fails at the database.
- auto: `scripts/schema_lint.py` (tables without a primary key, `*_id` columns without a foreign key, free-text status columns without a check).
- except: Deliberately denormalised analytical stores; sharded systems where FKs are impossible (document the alternative).
- related: REL-CONS-03, DATA-MIG-01, DATA-MODEL-03

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

### DATA-MODEL-03 · Every relationship is modelled with keys the database enforces, at the right cardinality
- level: strong | severity: major | provenance: synthesized
- sources: X24 (Part II, The Design Process — Keys, Table Relationships, Reviewing Data Integrity); S8 §7.2.1 (the shared store enforces integrity for every accessor); X14; T-20
- why: A relationship the database does not know about is maintained only by code every writer must remember; orphans, duplicates and impossible combinations appear silently, and lists of IDs in one column cannot be joined efficiently, constrained or cascaded.
- signals: Columns named `*_id` with no foreign key; many-to-many stored as comma-separated IDs or JSON arrays; repeating groups (`phone1`, `phone2`, `phone3`); polymorphic `*_type` + `*_id` pairs with no integrity; a mandatory relationship with a nullable foreign key; a one-to-one relationship without a unique constraint; a foreign key at the wrong level (order line → customer instead of order); `ON DELETE CASCADE` on records whose history must survive.
- fix: Model relationships with foreign keys — junction tables with a composite key for many-to-many, a unique foreign key for one-to-one; make mandatory relationships NOT NULL; choose each referential action deliberately (restrict for history, cascade for owned children); replace polymorphic references with one foreign-key column per target plus a CHECK that exactly one is set, or with a supertype table; index foreign-key columns where the engine does not (`../data/modeling.md` §3).
- verify: Every relationship has a foreign key or a documented reason it cannot (another database or service, sharding) with its replacement check; inserting an orphan fails at the database.
- auto: `scripts/schema_lint.py` (`*_id` columns without a foreign key; foreign keys without an index on engines that do not create one).
- except: References across services or databases, enforced by reconciliation and documented; deliberately unconstrained staging tables in ETL.
- related: DATA-SCHEMA-01, DATA-MODEL-02, DATA-KEY-01, DATA-IDX-01

### DATA-MODEL-04 · Store facts as of the time they were true; a snapshot is not redundancy
- level: strong | severity: major | provenance: extension
- sources: X24 (Part II, Establishing Table Structures and Field Specifications; Part III, Bending or Breaking the Rules); X14
- applies: Events and documents that record a state of the world at a moment — orders, invoices, payments, transfers, contracts — and reference data that changes over time: prices, exchange and interest rates, tax rates, limits.
- why: Normalising an event's values away (showing an old order with today's product price, a transfer with today's rate) rewrites history whenever the source changes: old invoices change totals, applied rates become unexplainable, audits fail. The copied value is a different fact — the value that applied to this event.
- signals: Order lines without the unit price, tax rate or currency applied; transfers storing a rate ID but not the rate; invoices re-rendered from current customer data; "duplicate" columns removed in a refactoring to "normalise"; effective-dated data (prices, rates, limits) kept as one mutable row with no history.
- fix: Copy the values that applied into the event row at the time of the event (price, rate, currency, tax rate, legally required names and addresses); model changing reference data with validity periods (`valid_from`, `valid_to`, non-overlap enforced where the engine supports it) or an append-only history; keep the link to the source as well when both are useful (`../data/modeling.md` §6–7).
- verify: Changing a source value after the event leaves the stored event and its totals unchanged — a test shows it.
- related: DATA-MODEL-02, DATA-AUDIT-01, DATA-EVOL-01, DATA-TYPE-02

### DATA-MODEL-05 · Do not normalise or generalise past the point where it removes anomalies
- level: contextual | severity: minor–major | provenance: extension
- sources: X24 (Part III, Bad Design — What Not to Do; Bending or Breaking the Rules); X26 (The Join Operation — every extra join is extra work the index design must carry); X14
- why: Normal forms remove update, insertion and deletion anomalies. Splitting further, or generalising into entity–attribute–value tables, removes no anomaly but loses types, constraints and indexes, multiplies joins, and moves integrity into application code.
- signals: Entity–attribute–value tables (`entity_id`, `attribute`, `value` as text) for attributes known at design time; one-to-one tables split with no difference in lifecycle, security or optionality; lookup tables for open-ended values with no attributes; generic `objects`/`properties` tables replacing domain tables; every read joining many tables to show one record; JSON used to avoid migrations for attributes that are queried.
- fix: Model known attributes as typed, constrained columns; reserve EAV or JSON for genuinely user-defined or sparse attributes, with validation and a documented boundary (DATA-MODEL-02, DATA-EVOL-01); merge one-to-one splits that share lifecycle and access; keep lookup tables for closed domains whose values carry attributes; justify each split by the anomaly it removes or a lifecycle, security or size reason.
- verify: Each table or split names the anomaly it prevents or its separate lifecycle; typed columns carry the constraints the rules need.
- except: Products whose customers define their own fields; archives of payloads whose structure is not yet known.
- related: DATA-MODEL-02, DATA-MODEL-03, DATA-SCHEMA-01, PERF-IO-01

### DATA-KEY-01 · Choose keys deliberately: stable surrogate identity, enforced natural keys, a type that fits growth and storage
- level: strong | severity: minor–major | provenance: extension
- sources: X24 (Part II, Keys); X25 (Part I, B-Tree Basics and Implementing B-Trees — ordered insertion and page splits); X27 (InnoDB clustered and secondary indexes; SQL Server clustered primary keys and NEWSEQUENTIALID); T-33
- why: The primary key is copied into every foreign key and, in clustered engines, into every secondary index. A natural key that changes forces cascading updates; a surrogate without a unique natural key lets duplicates in; a 32-bit key runs out on a busy table; random keys scatter inserts across a clustered index.
- signals: Email, phone or national ID as primary key; surrogate keys with no unique constraint on the business key (duplicate customers); `INT` keys on tables growing by millions a day; random UUIDv4 primary keys on InnoDB or SQL Server clustered tables with high insert rates; UUIDs stored as `CHAR(36)`; sequential IDs exposed where enumeration matters, or unguessable IDs used as the only access control.
- fix: Use a compact surrogate primary key (`BIGINT` identity or sequence, or a time-ordered UUID when IDs are generated outside the database); enforce each natural key with a UNIQUE constraint, normalised as the domain requires; size key types for growth; store UUIDs in native or 16-byte binary types; keep a separate public identifier when internal keys must not leak; authorise every access whatever the identifier (SEC-AUTHZ-02).
- verify: Every table has a primary key and its business keys are unique in the database; key types have headroom for the projected growth; on clustered tables with heavy inserts, page-split or fragmentation metrics stay acceptable.
- related: DATA-MODEL-03, DATA-SCHEMA-01, SEC-AUTHZ-02, DATA-IDX-01

### DATA-TYPE-01 · Money is never a binary floating-point number
- level: mandatory | severity: major | provenance: direct
- sources: S1 G26 (Be Precise — floating point for currency; use integers and handle rounding); X15 Item 48 (Avoid float and double if exact answers are required)
- why: Binary floats can't represent most decimal fractions; totals drift and reconciliation fails.
- signals: `float`/`double`/`FLOAT`/`REAL` or JS `number` arithmetic for amounts; `round()` sprinkled to hide drift.
- fix: Integer minor units or decimal types (`BigDecimal`, `decimal.Decimal`, `NUMERIC(p,s)`, `brick/money`, `shopspring/decimal`, `dinero.js`/`big.js`), with explicit rounding rules and currency.
- verify: Tests with values like 0.1 + 0.2 and many-line totals.
- auto: `scripts/schema_lint.py` (binary floating-point columns with money-like names).
- related: DES-DOM-01, DATA-TYPE-02

### DATA-TYPE-02 · Exact numbers carry explicit precision, scale and rounding rules sized for the domain
- level: strong | severity: major | provenance: synthesized
- sources: X27 (MySQL DECIMAL defaults to scale 0, SQL Server decimal to (18,0), Oracle DECIMAL/NUMERIC to scale 0; PostgreSQL rounds to the declared scale and rejects overflow; SQLite stores NUMERIC as integer or binary float); S1 G26 (Be Precise — currency and rounding); X15 Item 48
- applies: Money, exchange and interest rates, prices, quantities, tax and fee percentages — any value with legal or contractual rounding.
- why: `DECIMAL` without precision and scale hands the decision to engine defaults that differ — MySQL, SQL Server and Oracle store whole numbers — while a scale too small truncates rates, a precision too small overflows on totals, and rounding at a different step or mode from the specification creates reconciliation differences at scale.
- signals: `DECIMAL`/`NUMERIC` with no (p,s); scale 2 for exchange or interest rates; precision checked against single values but not sums; rounding repeated in several layers or left to a language default (half-even versus half-up) that contradicts the specification; percentages stored sometimes as 4.75 and sometimes as 0.0475; decimal arithmetic tested only on SQLite.
- fix: Declare precision and scale from the domain (largest total, smallest unit, rate precision of the source); name the representation (`rate_fraction`, `amount_minor`); define where rounding happens and with which mode, and apply it once there; keep currency with every amount; carry the precision through application types; test boundaries with exact expected values on the production engine (`../data/types.md` §2, §9).
- verify: The schema shows explicit (p,s); tests with maximum totals and rounding boundaries (x.xx5) pass on the production engine; specification and code agree on rounding step and mode.
- auto: `scripts/schema_lint.py` (DECIMAL without scale; small scales on rate-like columns).
- related: DATA-TYPE-01, DATA-MODEL-04, TEST-DATA-02, DATA-PORT-01

### DATA-TYPE-03 · Identifiers and codes are strings, not numbers
- level: strong | severity: minor–major | provenance: extension
- sources: X24 (Part II, Field Specifications); X27 (integer ranges per engine); X14
- why: Account numbers, IBANs, branch and product codes, phone numbers, postal codes and external references look numeric but are not quantities: they keep leading zeros, may gain letters, have fixed formats and are never added. Integer columns drop leading zeros, overflow past 19 digits, compare numerically ("010" equals "10"), and JavaScript clients lose precision above 2^53.
- signals: `INT`/`BIGINT`/`NUMERIC` for account numbers, IBANs, phone numbers, postal codes, branch or product codes, national IDs or transaction references; formatting code that pads zeros back; validation by numeric range; IDs above 2^53 serialised as JSON numbers.
- fix: Store identifiers and codes as `CHAR`/`VARCHAR` with a format and length check, normalised once (E.164 for phones, uppercase IBAN); keep numeric types for quantities and internal surrogate keys; serialise large integer IDs to JavaScript clients as strings.
- verify: A value with leading zeros and the longest valid format round-trips unchanged through database, API and client.
- auto: `scripts/schema_lint.py` (numeric types on identifier- and code-like column names).
- related: DATA-TYPE-02, DATA-KEY-01, DATA-SCHEMA-01, API-CONTRACT-02

### DATA-TYPE-04 · Store each temporal value with a type that matches its meaning
- level: strong | severity: major | provenance: extension
- sources: X27 (PostgreSQL timestamptz stores UTC; MySQL TIMESTAMP converts through the session time zone and ends in 2038, DATETIME does not convert; SQL Server datetime rounds to .000/.003/.007 s and datetimeoffset keeps an offset; Oracle DATE includes a time of day); X14
- why: An instant, a business date, a local appointment and a duration are different things. An instant stored without its zone is ambiguous across servers and daylight-saving changes; a business date stored as a timestamp moves across midnight in another zone; engine types differ in range, precision and conversion, so the same column means different things on different engines.
- signals: Event times in `timestamp without time zone`/`DATETIME` with no stated convention; MySQL `TIMESTAMP` for dates after 2038 or before 1970; value or due dates stored as timestamps; future local appointments stored as fixed offsets instead of zone IDs; Oracle `DATE` columns compared as dates without truncating the time; durations stored as month counts in days; precision differences between systems breaking equality or uniqueness.
- fix: Instants in a zone-aware type or UTC by a written convention, with stated precision; business dates as `DATE`; future local date-times as local value plus IANA zone ID; durations as interval types or integers with the unit in the name; check range and precision for each engine (`../data/types.md` §4).
- verify: Tests run under a non-UTC session and server time zone and across a daylight-saving change give the same instants and dates.
- auto: `scripts/schema_lint.py` (event-like columns without time zone; MySQL TIMESTAMP; SQL Server datetime).
- related: REL-TIME-03, DATA-PORT-01, DATA-TYPE-05, TEST-DATA-02

### DATA-TYPE-05 · NULL has one stated meaning per column, distinct from zero, empty and absent
- level: strong | severity: minor–major | provenance: extension
- sources: X27 (Oracle treats a zero-length string as NULL and advises not relying on it; SQL Server unique constraints allow one NULL; PostgreSQL treats NULLs as distinct unless NULLS NOT DISTINCT); X24 (Part II, Field Specifications); X14
- why: NULL means "unknown or not applicable" and follows three-valued logic: comparisons with NULL are never true, `NOT IN` over a list containing NULL returns nothing, `SUM` over no values is NULL, and uniqueness treats NULLs differently per engine. Using NULL, zero and empty interchangeably — "NULL limit means unlimited, 0 means none" — produces code that inverts the meaning in one `COALESCE`.
- signals: Nullable columns whose meaning nobody can state; NULL and 0 (or NULL and `''`) both used for "no value"; `COALESCE(x, 0)` on a column where NULL means "unlimited"; `NOT IN (SELECT nullable_col …)`; unique constraints on nullable columns expected to allow one empty row; code relying on Oracle's empty-string behaviour; JSON `null` and missing keys treated alike.
- fix: Default to NOT NULL; allow NULL only with a documented meaning; model distinct kinds of absence explicitly (a status or flag plus a value); use `NOT EXISTS` instead of `NOT IN` with nullable subqueries; decide NULL uniqueness per engine (partial or filtered indexes, `NULLS NOT DISTINCT`); never rely on Oracle's empty-string handling (`../data/types.md` §7).
- verify: Each nullable column's meaning is documented; tests cover NULL, zero and empty inputs for every rule that reads the column.
- related: DATA-SCHEMA-01, DATA-TYPE-04, DATA-PORT-01, CODE-ERR-04

### DATA-IDX-01 · Index for real query patterns, and check plans
- level: contextual | severity: minor–major | provenance: extension
- sources: X14; X26 (Anatomy of an Index; The Where Clause — Concatenated Keys, Searching for Ranges; Sorting and Grouping; Partial Results); X25 (Part I, B-Tree Basics)
- why: Missing indexes make queries scan; excess indexes slow writes and bloat storage. A composite index helps only queries that use a leading prefix of its columns, and only up to its first range column.
- signals: Filters/joins/sorts on unindexed columns of large tables; foreign keys without indexes (in engines that don't create them); composite indexes with the range column before the equality columns, or with a leading column the queries don't use; `ORDER BY … LIMIT` that sorts every matching row; single-column indexes on low-selectivity flags; duplicate or unused indexes; index advice given without a plan.
- fix: Design composite indexes from the queries: equality columns first, then the range column, then sort columns for top-N; reuse one index for several queries by prefix; make hot reads covering where it pays; use partial or filtered indexes for skewed predicates; verify with the plan with actual rows on representative data and label each claim as expected, estimated or measured (`../data/performance.md` §5, §13); drop unused indexes based on usage statistics.
- verify: The actual plan shows an index range or index-only scan with estimates close to actual rows; before/after timings with spread on production-like data; write cost of new indexes checked.
- auto: `scripts/schema_lint.py` (foreign keys without a supporting index on engines that do not create one).
- related: PERF-IO-01, PERF-IO-02, DATA-IDX-02, DATA-KEY-01

### DATA-IDX-02 · Write predicates the index can use: no functions, conversions or leading wildcards on indexed columns
- level: strong | severity: minor–major | provenance: extension
- sources: X26 (The Where Clause — Functions, Case-Insensitive Search, Bind Variables, Indexing SQL LIKE Filters, Obfuscated Conditions: dates, numeric strings, combining columns, smart logic, math); X27 (plan tools of each engine); T-34
- why: An index is ordered by the column's stored value. A predicate that transforms the column — a function, an implicit type or collation conversion, arithmetic, concatenation — or starts with a wildcard cannot seek in that order, so the engine scans, often only on production volumes where it matters.
- signals: `WHERE DATE(created_at) = ?`, `WHERE LOWER(email) = ?` without a matching expression index; numbers stored as strings compared with numbers, or the reverse; joins between columns of different types or collations; Unicode literals compared with non-Unicode columns; `LIKE '%term'`; `WHERE (:p IS NULL OR col = :p)` catch-all filters; `col + 1 = ?`; `first || ' ' || last = ?`.
- fix: Rewrite as a range on the raw column (`created_at >= :day AND created_at < :day + 1 day`); add an expression or function-based index when the transformation is the access pattern; match parameter and column types and collations; use full-text or trigram indexes for infix search; split catch-all filters into separate queries or dynamic SQL with bind parameters (SEC-INJ-01); confirm with the plan on representative data (`../data/performance.md` §6).
- verify: The plan shows an index access driven by the predicate, with actual rows close to estimates, on production-like data.
- related: DATA-IDX-01, PERF-IO-01, SEC-INJ-01, DATA-TYPE-03

### DATA-PORT-01 · Engine portability is stated, designed and tested — never assumed from the ORM or the SQL standard
- level: contextual | severity: minor–major | provenance: synthesized
- sources: X27 (type, NULL, collation, DDL and isolation differences between PostgreSQL, Oracle, MySQL, MariaDB, SQL Server and SQLite); S2 Ch.30 (The Database Is a Detail); X26 (vendor-specific notes on index behaviour); T-34
- applies: Products supporting several engines; migrations between engines; libraries claiming engine neutrality; tests run on a different engine from production.
- why: Engines share keywords, not semantics. The same `DECIMAL`, `VARCHAR(20)`, `TIMESTAMP`, unique constraint or `''` behaves differently, and an ORM hides syntax, not semantics. Portability assumed rather than designed fails during the migration or at the second customer's engine.
- signals: "The ORM makes us database-agnostic" with raw or engine-specific SQL in the code; cross-engine migrations mapped type-for-type by name (Oracle `DATE` → `date`, MySQL `TINYINT(1)` → integer, `DATETIME` → `timestamptz`) without decisions; case-insensitive uniqueness obtained implicitly from a collation; code depending on `''` being NULL or not; a supported-engines list with no tests on some engines.
- fix: State which engines are supported; with one production engine, use its features behind the data-access layer (T-34); with several, restrict to the common subset or isolate per-engine implementations; map each type, constraint and collation by meaning (`../data/engines.md`, `../data/types.md`); test category D on every supported engine (TEST-DATA-02).
- verify: A cross-engine mapping table with semantic notes exists for migrations; the data-access suite passes on every supported engine and version.
- related: TEST-DATA-02, DATA-TYPE-02, DATA-TYPE-04, DATA-TYPE-05, DATA-MIG-01
