# Database test matrix: which tests need which engines

Classify each test by what its assertion depends on, then run it on exactly the engines that
dependence requires — no fewer, no more (TEST-DATA-02, P-74). There is no fixed order such as
"SQLite first, then PostgreSQL": the categories decide, and "the production engine" means whatever
production actually runs — Oracle, SQL Server, MySQL or MariaDB, PostgreSQL, SQLite or another. If
the production engine or version is not known, record it as UNKNOWN and say which conclusions depend
on it. Engine facts and their sources: `../data/engines.md`.

## Contents
1. Categories · 2. Classifying a test · 3. Behaviours that differ between engines · 4. Stand-ins
and what they hide · 5. Running the matrix economically · 6. Anti-patterns · 7. Reporting

## 1. Categories

| Category | The assertion depends on | Run on | Typical tests |
|---|---|---|---|
| **A · Database-independent** | Nothing stored: rules, calculations, validation, in-memory mapping | No database, once | Pricing and interest rules, DTO mapping, state machines |
| **B · Needs a real database** | Behaviour any correct SQL engine provides: a constraint rejects a row, a transaction rolls back, a join returns the expected rows, an ORM mapping round-trips | The production engine at its production major version | Repository CRUD, unique-violation handling, cascade deletes, pagination queries |
| **C · Needs a specific engine** | Semantics or features of one engine (§3) | That engine and version | PostgreSQL `ON CONFLICT` upsert; Oracle treating `''` as NULL; SQL Server's one-NULL unique index; MySQL's case-insensitive default collation; `FOR UPDATE SKIP LOCKED` queues |
| **D · Needs several engines** | A promise of portability: the product supports several engines, the system is migrating between engines, or a library claims engine neutrality | Every supported engine, on a focused data-access suite | An on-premises product sold for Oracle and SQL Server; a MySQL → PostgreSQL migration |

## 2. Classifying a test

Ask in order:

1. Does the test execute SQL — directly, through an ORM, or through procedures and triggers? If not,
   it is **A**. A test with a mocked repository is A by construction and proves nothing about SQL.
2. Would its assertion hold on any correct SQL engine? Then **B**.
3. Does it rely on any behaviour in §3, or on an engine-only feature? Then **C**, on that engine.
4. Must the same behaviour hold on more than one engine? Then **D**.

Unsure between B and C? Treat it as C on the production engine: the cost is the same single real
engine, and the label tells the next reader that a stand-in would not do.

## 3. Behaviours that differ between engines

Verified against each engine's manual on 2026-11-24 (links in `../data/engines.md`); confirm for the
version in use.

| Area | What differs (examples) |
|---|---|
| Dialect and features | Upsert syntax and conflict rules (`ON CONFLICT`, `ON DUPLICATE KEY UPDATE`, `MERGE`); `RETURNING`/`OUTPUT`; row limiting (`LIMIT`, `FETCH FIRST`, `TOP`); available window functions and recursive queries |
| ORM behaviour | Generated SQL per dialect, emulated types (booleans as integers), identity retrieval after batch inserts, quoting and case of identifiers |
| Numeric types | `DECIMAL` without scale: MySQL defaults to scale 0 (precision 10), SQL Server to (18,0), Oracle's `DECIMAL`/`NUMERIC` to scale 0, PostgreSQL stores unconstrained numeric; SQLite `NUMERIC`/`DECIMAL` columns store integers or 8-byte binary floats; Oracle `FLOAT` is a decimal `NUMBER` subtype while `BINARY_DOUBLE` is binary |
| Text | Length counted in bytes (Oracle `VARCHAR2` by default, SQL Server `varchar`) or characters (PostgreSQL, MySQL); SQLite does not enforce `VARCHAR(n)` |
| NULL and empty | Oracle treats `''` as NULL; SQL Server unique constraints allow one NULL, PostgreSQL, MySQL and SQLite allow many, Oracle many all-NULL keys but not partly-NULL composite duplicates (PostgreSQL 15+ can opt into `NULLS NOT DISTINCT`); ascending sorts put NULLs last in PostgreSQL and Oracle, first in MySQL, SQL Server and SQLite |
| Collation and case | MySQL's default `utf8mb4_0900_ai_ci` compares accent- and case-insensitively, so `'A@x.com'` and `'a@x.com'` collide in a unique index that PostgreSQL's default deterministic collation keeps apart; SQL Server collations are set per server, database or column |
| Constraints | MySQL parsed and ignored `CHECK` before 8.0.16; SQLite enforces foreign keys only after `PRAGMA foreign_keys = ON` on each connection and accepts any value type in non-`STRICT` tables |
| Booleans | PostgreSQL has a native `boolean`; MySQL's `BOOLEAN` is an alias of `TINYINT(1)`; SQL Server uses `bit`; Oracle SQL has `BOOLEAN` only from 23ai; SQLite stores 0 and 1 |
| Date and time | MySQL `TIMESTAMP` converts through the session time zone and is limited to 1970–2038 UTC, `DATETIME` is not converted; Oracle `DATE` carries a time of day; SQL Server `datetime` rounds to .000/.003/.007 s; PostgreSQL `timestamptz` stores a UTC instant without the zone; SQLite has no date type |
| Transactions and DDL | MySQL and Oracle commit implicitly around DDL, so a failed multi-step migration leaves a half-applied schema; PostgreSQL runs most DDL inside transactions |
| Isolation and locking | Defaults: PostgreSQL and Oracle read committed with statement snapshots; MySQL InnoDB repeatable read with next-key locks; SQL Server read committed with shared locks unless `READ_COMMITTED_SNAPSHOT` is on (the default in Azure SQL Database); SQLite serializable with one writer at a time |
| JSON | PostgreSQL `json`/`jsonb` with operators and GIN indexes; MySQL binary `JSON`; MariaDB `JSON` is an alias of `LONGTEXT` with a validity check; Oracle `JSON` type or `IS JSON` checks; SQLite JSON functions over text |
| Indexes and plans | Partial or filtered, expression or function-based, covering and clustered indexes vary by engine; optimisers choose differently, so plan-dependent tests are engine-specific |
| Identity and sequences | PostgreSQL, MySQL, Oracle and SQL Server do not roll back identity or sequence values, so rollbacks leave gaps; SQLite reuses them after a rollback — never assert gapless (or gappy) numbering |
| Referential integrity | MySQL creates an index for a foreign key automatically; PostgreSQL, Oracle and SQL Server do not, and in Oracle an unindexed foreign key makes parent-key changes lock the child table |

## 4. Stand-ins and what they hide

Embedded or in-memory substitutes — SQLite in memory, H2 or HSQLDB, ORM in-memory providers, mocked
repositories — run a different engine's semantics, or none at all. Compatibility modes imitate parts
of another engine's syntax, not its full behaviour; check each behaviour a test relies on before
trusting a mode. SQLite in particular has flexible typing, foreign keys off by default and a single
writer, so constraint, type and concurrency tests that pass there say little about a server engine.

A stand-in is acceptable for category A tests that need a store-shaped fake (better: no database at
all), or as an extra fast lane on a developer machine — never as the evidence reported for B, C or D
(T-32).

## 5. Running the matrix economically

- **A**: once, with no database, on every commit.
- **B**: the production engine in a container pinned to the production major version; one database
  per worker; roll back per test where commit semantics are not under test, and use template
  databases or one migration run per job instead of migrating per test.
- **C**: group engine-specific tests with markers or tags (`pytest.mark.oracle`, JUnit `@Tag`, Go
  build tags) so selection can pick them; run them on their engine.
- **D**: one data-access contract suite, parameterised by engine (TEST-CONTRACT-02), on each
  supported engine — the primary engine on every PR, all engines in the merge queue or nightly, all
  engines at every supported version before release. Not the whole suite times N engines.
- **Engine upgrades**: run B and C on the old and new versions until the upgrade ships.
- **Heavy images** (Oracle, SQL Server): place them in the stages where their start-up cost is
  acceptable, but keep them in release verification whenever production runs them.

## 6. Anti-patterns

- A fixed engine ritual ("SQLite, then PostgreSQL") regardless of what the tests depend on.
- The entire suite run once per engine, pure-logic tests included.
- Category C tests run on a stand-in and reported as passed.
- Tests that pass because the stand-in does not enforce something: SQLite foreign keys off, MySQL
  before 8.0.16 ignoring `CHECK`, `VARCHAR(n)` lengths unenforced.
- Uniqueness and equality tests that depend on a collation nobody chose deliberately.
- Concurrency tests on SQLite standing in for a server engine.

## 7. Reporting

The execution report (`../../assets/templates/test-execution-report.md`) states, per category, the
engines and versions used, the number of tests and their results, and for any category not run the
reason and the residual risk (TEST-REPORT-01). Example:

| Category | Engines and versions | Tests | Result |
|---|---|---|---|
| A | none | 412 | 412 passed |
| B | PostgreSQL 16.4 (production 16.x) | 58 | 57 passed, 1 failed |
| C | PostgreSQL 16.4 | 6 | 6 passed |
| D | not applicable — single-engine product | — | — |
