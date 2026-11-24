# Engine differences that change designs, migrations and tests

Engines share SQL keywords, not semantics (P-74). Use this file to know **where** behaviour differs,
then confirm the detail in the manual for the exact engine and version in use. Never assume a
same-named type or default behaves the same elsewhere. Rules: DATA-PORT-01, TEST-DATA-02,
DATA-TYPE-02..05, DATA-DUR-01. How the differences change test plans: `../testing/database-matrix.md`.

**How to use it.** First establish the engine and major version for production and for tests
(`scripts/repo_survey.py` reports what configuration and dependencies show; otherwise ask, or record
UNKNOWN and name what depends on it). Then check the rows relevant to the change. Cells were checked
against the official documentation listed in §4 on 2026-11-24; cells marked † were not re-checked for
this release — verify them before relying on them.

## Contents
1. Comparison matrix · 2. Portability issues and why they matter · 3. MySQL and MariaDB ·
4. Sources checked

## 1. Comparison matrix

| Area | PostgreSQL | Oracle | MySQL (InnoDB) | SQL Server | SQLite |
|---|---|---|---|---|---|
| Type enforcement | Rigid | Rigid, with implicit conversions in comparisons | Rigid; handling of invalid values depends on SQL mode † | Rigid, implicit conversion by type precedence | Flexible type affinity; `STRICT` tables since 3.37.0 |
| `DECIMAL` without (p,s) | Unconstrained `numeric`, any scale | `DECIMAL`/`NUMERIC`: scale 0 — whole numbers; bare `NUMBER`: up to 38 digits, no fixed scale | (10,0) — whole numbers | (18,0) — whole numbers | `NUMERIC` affinity: integer or 8-byte binary float |
| Binary floating point | `real`, `double precision` | `BINARY_FLOAT`, `BINARY_DOUBLE` (`FLOAT(p)` is a decimal `NUMBER` subtype) | `FLOAT`, `DOUBLE` | `real`, `float` (IEEE 754) | `REAL` (8-byte IEEE) |
| `VARCHAR(n)` counts | Characters | Bytes by default (`NLS_LENGTH_SEMANTICS`; `VARCHAR2(n CHAR)` for characters) | Characters | Bytes (`varchar`); UTF-16 code units (`nvarchar`) | Not enforced |
| `''` (empty string) | A value | Treated as NULL (Oracle advises not to rely on it) | A value | A value | A value |
| NULLs in a UNIQUE constraint | Many allowed; `NULLS NOT DISTINCT` from 15 | Many rows whose key columns are all NULL; in a composite key, rows with NULLs in some columns and equal values in the rest conflict | Many | One (use a filtered unique index for many) | Many |
| NULL position, ascending sort | Last | Last | First | First | First |
| Boolean | `boolean` | `BOOLEAN` from 23ai; numbers or chars before | `BOOLEAN` = `TINYINT(1)` | `bit` | Integers 0/1 |
| Instant type | `timestamptz`: stored as UTC, shown in session zone, zone not kept | `TIMESTAMP WITH TIME ZONE` (keeps zone); `WITH LOCAL TIME ZONE` † | `TIMESTAMP`: session zone → UTC, 1970–2038; `DATETIME`: no conversion, 1000–9999 | `datetimeoffset` (keeps offset); `datetime2` (no zone); `datetime` rounds to .000/.003/.007 s | None: ISO-8601 text or numbers by convention |
| `DATE` | Calendar date | Date **and** time to the second | Calendar date | Calendar date | Convention only |
| JSON | `json`, `jsonb` (indexable with GIN) | `JSON` type or `IS JSON` checks | Binary `JSON` | JSON functions over `nvarchar` † | JSON functions over text |
| Auto-generated keys | Identity columns, sequences | Identity columns, sequences | `AUTO_INCREMENT` | `IDENTITY`, `SEQUENCE` | `INTEGER PRIMARY KEY` (rowid) |
| `CHECK` constraints | Enforced | Enforced | Enforced from 8.0.16; parsed and ignored before | Enforced | Enforced |
| Index on foreign-key columns | Not created automatically | Not created; unindexed FKs make parent-key changes lock the child table | Required; created automatically | Not created † | Not created †; FK enforcement off until `PRAGMA foreign_keys = ON` per connection |
| DDL and transactions | Most DDL is transactional | Implicit commit before and after DDL | Implicit commit around DDL | DDL can run in explicit transactions † | DDL is transactional † |
| Default isolation | Read committed (snapshot per statement) | Read committed (statement-level consistency) | Repeatable read (snapshot for plain reads; next-key locks for locking reads and writes) | Read committed with shared locks; `READ_COMMITTED_SNAPSHOT` on by default in Azure SQL Database | Serializable |
| Strongest level | Serializable (SSI); retry on SQLSTATE 40001 | Serializable is snapshot-based: ORA-08177 when a row changed after the transaction began | Serializable: plain reads become shared locking reads when autocommit is off | Serializable † and Snapshot (row versions) | Serializable by design: one writer |
| Old row versions kept in | The table (dead tuples, removed by VACUUM) | Undo segments | Undo logs (purged) | Version store in tempdb, or in the user database when accelerated database recovery is on (always in Azure SQL Database) — used by snapshot isolation and RCSI | WAL file (in WAL mode) |
| Cost of a long transaction | Bloat: VACUUM cannot remove tuples it may still see | Long queries can fail with ORA-01555 "snapshot too old" | Purge blocked; older versions slow reads | Version store grows | Readers pin a snapshot † |
| Row storage | Heap; all indexes separate | Heap; index-organized tables optional | Clustered by primary key; secondary indexes carry the PK | Clustered index (PK clustered by default) or heap | B-tree by rowid; `WITHOUT ROWID` tables by PK † |
| Lock escalation | Row locks are not escalated; SERIALIZABLE's predicate locks can be promoted to page or relation level | None † | None † | Row/page locks escalate to a table lock (≥ 5,000 locks on one table reference) | Database-level write lock |
| Online index build | `CREATE INDEX CONCURRENTLY` (outside a transaction) | `CREATE INDEX … ONLINE` (edition-dependent †) | Online DDL via `ALGORITHM`/`LOCK` clauses | `WITH (ONLINE = ON)` (edition-dependent †) | Not applicable |
| Durability trade-off knobs | `synchronous_commit` (may lose recent commits, no corruption); never `fsync = off` | Commit write options † | `innodb_flush_log_at_trx_commit` ≠ 1 may lose recent commits | Delayed durability (2014+) may lose commits on crash or failover | `PRAGMA synchronous`, journal mode † |
| Plan with actual rows | `EXPLAIN (ANALYZE, BUFFERS)` | `DBMS_XPLAN.DISPLAY_CURSOR` with runtime statistics | `EXPLAIN ANALYZE` (8.0.18+ †) | Actual execution plan; `SET STATISTICS IO` | `EXPLAIN QUERY PLAN` (no actual rows) |
| Default text comparison | Deterministic collations | Binary unless NLS settings change it † | `utf8mb4_0900_ai_ci`: accent- and case-insensitive | Set per server, database or column † | `BINARY` (`NOCASE` available) † |

## 2. Portability issues and why they matter

1. **Decimal defaults** — the same `DECIMAL` declaration stores whole numbers on MySQL, SQL Server and
   Oracle (where `DECIMAL`/`NUMERIC` default to scale 0; only a bare `NUMBER` has no fixed scale) and
   any scale on PostgreSQL. Always declare precision and scale (DATA-TYPE-02).
2. **Empty string versus NULL** — on Oracle `''` becomes NULL: `NOT NULL` columns reject it and
   `col = ''` never matches. Code moving to or from Oracle silently changes meaning; never give `''`
   a meaning distinct from NULL in portable code (DATA-TYPE-05).
3. **NULLs in unique constraints** — duplicate detection differs (SQL Server allows one NULL; Oracle
   allows many all-NULL keys but treats a composite key with some NULLs and equal other values as a
   duplicate); choose partial or filtered indexes or `NULLS NOT DISTINCT` deliberately.
4. **Collation** — a unique email index that rejects case variants on MySQL accepts them on
   PostgreSQL; after a migration duplicates appear. Normalise the key (`lower(email)` unique) or
   choose the collation on purpose.
5. **Instants and dates** — MySQL `TIMESTAMP` stops in 2038 and converts by session zone; Oracle
   `DATE` carries time, so migrating it to a `date` type truncates; precision differs (SQL Server
   `datetime` rounding) and breaks equality between systems (DATA-TYPE-04).
6. **Booleans** — `TINYINT(1)`, `bit` and pre-23ai Oracle numbers need explicit mapping; ORMs differ in
   what they emit.
7. **DDL transactionality** — on MySQL and Oracle a failed multi-statement migration leaves a
   half-applied schema; write one structural change per step and make steps re-runnable (DATA-MIG-02).
8. **Isolation and locking** — the same test of concurrent behaviour proves nothing on another engine:
   read committed with locks (SQL Server) blocks where snapshot reads (PostgreSQL, Oracle) do not;
   InnoDB's gap locks block inserts others allow; Oracle's serializable is snapshot-based.
9. **Foreign-key indexes** — MySQL creates them; elsewhere their absence slows parent deletes and,
   on Oracle, locks the child table (DATA-MODEL-03, DATA-IDX-01).
10. **Upserts and conflicts** — `ON CONFLICT`, `ON DUPLICATE KEY UPDATE` and `MERGE` differ in syntax,
    in which unique index they act on and in behaviour under concurrency; test on the engine.
11. **JSON** — storage, operators and indexing differ (binary `jsonb` and MySQL `JSON` versus text in
    MariaDB and SQLite).
12. **Text length** — byte-counted lengths (Oracle default, SQL Server `varchar`) overflow with
    multibyte data that fitted character-counted columns.
13. **Identifier case** — unquoted identifiers fold to lower case in PostgreSQL and upper case in
    Oracle †; quoted mixed-case names generated by ORMs break hand-written SQL.

## 3. MySQL and MariaDB

MariaDB began as a MySQL fork and has diverged: for example its `JSON` type is an alias of `LONGTEXT`
with a validity check, while MySQL stores binary JSON; optimiser, replication and system-variable
behaviour also differ. Treat them as separate engines in the test matrix and check MariaDB's own
documentation instead of MySQL's.

## 4. Sources checked (2026-11-24)

PostgreSQL (current documentation): numeric types
<https://www.postgresql.org/docs/current/datatype-numeric.html>; character types
<https://www.postgresql.org/docs/current/datatype-character.html>; date/time types
<https://www.postgresql.org/docs/current/datatype-datetime.html>; constraints
<https://www.postgresql.org/docs/current/ddl-constraints.html>; transaction isolation
<https://www.postgresql.org/docs/current/transaction-iso.html> and serialization failure handling
<https://www.postgresql.org/docs/current/mvcc-serialization-failure-handling.html>; asynchronous commit
<https://www.postgresql.org/docs/current/wal-async-commit.html>; routine vacuuming
<https://www.postgresql.org/docs/current/routine-vacuuming.html>; sorting
<https://www.postgresql.org/docs/current/queries-order.html>.

MySQL 8.4: decimal characteristics
<https://dev.mysql.com/doc/refman/8.4/en/precision-math-decimal-characteristics.html>; date and time
types <https://dev.mysql.com/doc/refman/8.0/en/datetime.html> and time-zone support
<https://dev.mysql.com/doc/refman/8.4/en/time-zone-support.html>; implicit commit
<https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html>; CHECK constraints
<https://dev.mysql.com/doc/refman/8.0/en/create-table-check-constraints.html>; foreign keys
<https://dev.mysql.com/doc/refman/8.0/en/create-table-foreign-keys.html>; clustered indexes
<https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html>; transaction management and purge
<https://dev.mysql.com/doc/refman/8.4/en/optimizing-innodb-transaction-management.html>; isolation
levels <https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html>; locking
<https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html>; Unicode character sets
<https://dev.mysql.com/doc/refman/8.4/en/charset-unicode-sets.html>; NULL ordering
<https://dev.mysql.com/doc/refman/8.4/en/working-with-null.html>.

MariaDB: JSON data type <https://mariadb.com/docs/server/reference/data-types/string-data-types/json>.

Oracle Database (19c and 26ai documentation): nulls
<https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Nulls.html>; data types
<https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Data-Types.html>; data concurrency
and consistency (isolation, foreign-key locking)
<https://docs.oracle.com/en/database/oracle/oracle-database/26/cncpt/data-concurrency-and-consistency.html>;
DDL and implicit commit <https://docs.oracle.com/en/database/oracle/oracle-database/26/cncpt/sql.html>;
undo and ORA-01555 <https://docs.oracle.com/en/database/oracle/oracle-database/26/admin/managing-undo.html>;
SELECT and NULL ordering <https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/SELECT.html>;
BOOLEAN in 23ai <https://docs.oracle.com/en/learn/db23ai-sql-features/index.html>.

SQL Server (Microsoft Learn): decimal and numeric
<https://learn.microsoft.com/en-us/sql/t-sql/data-types/decimal-and-numeric-transact-sql>; datetime
<https://learn.microsoft.com/en-us/sql/t-sql/data-types/datetime-transact-sql>; unique constraints
<https://learn.microsoft.com/en-us/sql/relational-databases/tables/unique-constraints-and-check-constraints>;
locking and row versioning
<https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide>;
transaction durability
<https://learn.microsoft.com/en-us/sql/relational-databases/logs/control-transaction-durability>;
NEWSEQUENTIALID <https://learn.microsoft.com/en-us/sql/t-sql/functions/newsequentialid-transact-sql>;
ORDER BY <https://learn.microsoft.com/en-us/sql/t-sql/queries/select-order-by-clause-transact-sql>.

SQLite: datatypes <https://www.sqlite.org/datatype3.html>; STRICT tables
<https://www.sqlite.org/stricttables.html>; foreign keys <https://www.sqlite.org/foreignkeys.html>;
ALTER TABLE <https://www.sqlite.org/lang_altertable.html>; write-ahead logging
<https://www.sqlite.org/wal.html>; pragmas (isolation) <https://sqlite.org/pragma.html>; FAQ (any
length in any column) <https://www.sqlite.org/faq.html>.
