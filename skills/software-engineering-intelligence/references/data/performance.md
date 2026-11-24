# Query and index performance: method, mechanisms and evidence

How to find why a query is slow and what to change, and how to say how sure you are. The index and
query concepts follow X26 (*SQL Performance Explained*; its free web edition is
[Use The Index, Luke](https://use-the-index-luke.com/)); the storage mechanisms are in `internals.md`.
Advice here is a starting hypothesis: the execution plan and a measurement on representative data
decide (P-73). Rules: DATA-IDX-01, DATA-IDX-02, PERF-IO-01, PERF-IO-02, PERF-MEAS-01, API-PAGE-01.

## Contents
1. Three layers · 2. Method · 3. Reading execution plans · 4. Access paths and selectivity ·
5. Composite indexes · 6. Predicates the index can use · 7. Joins · 8. Sorting, grouping and
pagination · 9. Writes and the cost of indexes · 10. N+1 and chatty access · 11. Statistics,
parameters and plan stability · 12. Anti-patterns · 13. Evidence labels

## 1. Three layers

| Layer | Examples | A problem here looks like |
|---|---|---|
| Logical design | Normalisation, relationships, types (`modeling.md`, `types.md`) | EAV pivots, string-typed numbers that defeat indexes, missing relationships forcing scans |
| Physical design | Indexes, clustering, partitioning, materialised views, column sizes | Full scans, sorts of whole tables, wide rows |
| Operations | Statistics, vacuum and purge, pools and timeouts, replicas, partition rotation, online schema changes, backfills | Bloat, stale plans, lock queues, replica lag |

Fix the problem at its own layer: an index does not repair an N+1 loop, and vacuum does not repair a
missing index.

## 2. Method

1. **Find the expensive statements** by total time and frequency, not by anecdote:
   `pg_stat_statements`, MySQL's slow query log and Performance Schema, SQL Server Query Store, Oracle
   AWR/ASH where licensed or Statspack.
2. **Get the plan with actual rows and timing** on production-like data (§3).
3. **Find the dominant cost**: rows read versus rows returned, estimate versus actual, sorts and
   hashes spilling to disk, nested loops executed thousands of times.
4. **Form one hypothesis** grounded in the mechanism (`internals.md`) and change one thing.
5. **Re-measure** the same statement with the same parameters and data, several runs, and report
   before/after with spread (TEST-PERF-01); then check the write cost of any new index (§9).

## 3. Reading execution plans

| Engine | Plan with actual rows |
|---|---|
| PostgreSQL | `EXPLAIN (ANALYZE, BUFFERS)` |
| MySQL | `EXPLAIN ANALYZE` (8.0.18+), `EXPLAIN FORMAT=TREE` for the estimated tree |
| SQL Server | Actual execution plan; `SET STATISTICS IO, TIME ON`; Query Store history |
| Oracle | `DBMS_XPLAN.DISPLAY_CURSOR` with runtime statistics (`EXPLAIN PLAN` shows estimates only) |
| SQLite | `EXPLAIN QUERY PLAN` (access paths, no row counts) |

Statements analysed with actual execution **run for real**: wrap an `UPDATE`, `DELETE` or `INSERT` in a
transaction you roll back, and never analyse a heavy statement on a production primary without
agreement (AGT-SAFE-01). Look for: estimated versus actual rows (a large gap means stale or missing
statistics, correlated columns or a parameter-dependent plan); loops × rows on the inner side of
nested loops; rows removed by a filter after an index access (the index finds too much); sorts and
hashes using disk; table lookups after index access (a covering index would avoid them); the
operation that consumes most of the time, not the first one listed.

## 4. Access paths and selectivity

- **Full scan**: reads every page sequentially — efficient when a large share of rows qualifies.
- **Index range scan + table access**: walks the index, then fetches each row, usually randomly —
  efficient for a small share of rows; the break-even depends on engine, caching and how well the
  table order matches the index order.
- **Index-only (covering) scan**: everything comes from the index; no table access (in PostgreSQL also
  subject to the visibility map).
- **Bitmap scans** (PostgreSQL) and index merge or combine (others) can combine several indexes, less
  efficiently than one well-designed composite index.

Selectivity — the share of rows a predicate keeps — and the optimiser's estimate of it drive these
choices. "Using an index" is not a goal: an index scan returning 40 % of a table is usually slower than
a scan (X26, "Slow Indexes").

## 5. Composite indexes

- A composite index is sorted by its first column, then the second within equal firsts, and so on;
  it supports predicates on a **leading prefix** of its columns.
- Order columns: **equality predicates first, then one range predicate**; columns after the first
  range column can only filter inside the range, not narrow it.
- For `ORDER BY … LIMIT n`, put the sort columns after the equality columns, in the sort direction,
  so the engine reads the first n entries and stops (§8).
- "Most selective column first" is a myth when it contradicts these rules (X26 myth directory): what
  matters is which queries the index can serve and where the range column sits.
- An index on (a, b) usually makes an index on (a) alone redundant; keep both only when the single
  column index is needed for a constraint or demonstrably cheaper for a hot query.
- Some engines can skip-scan a leading column with few distinct values; do not design around it.

Example: `WHERE customer_id = :c AND created_at >= :since ORDER BY created_at DESC LIMIT 20` is served
by an index on `(customer_id, created_at)`; one on `(created_at, customer_id)` scans every customer's
rows in the date range.

## 6. Predicates the index can use

A B-tree is ordered by the stored value; a predicate must compare the bare column to a value of the
same type and collation to seek (DATA-IDX-02):

| Pattern | Why it scans | Fix |
|---|---|---|
| `DATE(created_at) = :d`, `YEAR(col) = 2026` | Function on the column | `created_at >= :d AND created_at < :d + 1 day`, or an expression index |
| `LOWER(email) = :e` | Function on the column | Expression index on `lower(email)`, a case-insensitive type or collation chosen deliberately |
| String column compared with a number (or the reverse) | Implicit conversion applied to the column | Match types; fix the column type (DATA-TYPE-03) |
| Join columns of different types or collations | Conversion on one side | Same types and collations on both sides |
| `LIKE '%term'` | Leading wildcard | Full-text or trigram index; reversed-string index for suffixes |
| `(:p IS NULL OR col = :p)` catch-all filters | One plan must serve both cases | Separate queries or dynamic SQL with bind parameters (SEC-INJ-01) |
| `col + 1 = :x`, `first || ' ' || last = :name` | Arithmetic or concatenation on columns | Move arithmetic to the value side; index the expression or store the normalised value |
| `col IS NULL` on Oracle single-column B-tree | All-NULL keys are not indexed | Composite index with a non-null column, or a function-based index |

## 7. Joins

- **Nested loops**: for each outer row, look up the inner side — fast when the outer side is small
  and the inner join column is indexed. An application loop issuing one query per row is a nested
  loop run over the network (§10).
- **Hash join**: builds a hash table of one input — good for large, unsorted equality joins; needs
  memory and spills to disk when short of it. Select only the columns needed.
- **Merge join**: merges two inputs sorted on the join key — good when indexes already provide the
  order.

Index the join columns on the side looked up; filter as early as the predicates allow; keep join keys
the same type and collation; check estimated row counts at each join, because a misestimate early in
the plan picks the wrong algorithm for every later join. A join without a predicate is a Cartesian
product; `DISTINCT` added to hide duplicate rows usually hides a wrong join.

## 8. Sorting, grouping and pagination

- An index in the right order lets the engine skip the sort; directions and NULL ordering must match
  the index for mixed `ASC`/`DESC` keys.
- Top-N (`LIMIT`, `FETCH FIRST`, `TOP`) with an index matching filter and sort reads only n entries.
- `OFFSET` pagination reads and discards every skipped row — cost grows with page depth. Use keyset
  (seek) pagination for deep or live lists: `WHERE (created_at, id) < (:last_created, :last_id) ORDER
  BY created_at DESC, id DESC LIMIT 20` with an index on `(created_at, id)` (API-PAGE-01).
- `COUNT(*)` over large filtered sets for a page header is often the most expensive query on the page;
  show an estimate or "more than N".

## 9. Writes and the cost of indexes

Every index is maintained on insert, on update of its columns and on delete, and adds log volume and
memory pressure. Index frequently updated columns only with evidence; prefer partial or filtered
indexes for skewed predicates (`WHERE status = 'pending'`); bulk-load with the engine's bulk path;
remove large volumes by dropping partitions instead of mass deletes (DATA-SCALE-01). Unused and
duplicate indexes show up in usage statistics (`pg_stat_user_indexes`, `sys.dm_db_index_usage_stats`,
Performance Schema).

## 10. N+1 and chatty access

One query for a list plus one query per item turns a request into hundreds of round trips; it hides
behind ORM lazy loading in loops and templates (PERF-IO-01). Detect it by counting queries per request
in tests or logs; fix with eager loading or a join, batched `IN` lookups with a bounded list, or a
data loader that groups lookups. The database sees fast individual queries — only the count reveals
the problem.

## 11. Statistics, parameters and plan stability

- Stale or missing statistics cause misestimates; check when statistics were last gathered and
  whether automatic maintenance keeps up with the change rate.
- Skewed data makes the best plan depend on the parameter value. Cached plans built for one value can
  be poor for another (parameter sniffing in SQL Server, generic plans for prepared statements in
  PostgreSQL, bind peeking in Oracle). Diagnose with the parameter values in use, not with literals
  chosen for the test.
- Upgrades and statistics changes can regress plans; plan history (Query Store, plan baselines) helps
  compare before and after.

## 12. Anti-patterns

`SELECT *` on wide tables; functions on indexed columns; deep `OFFSET`; counting everything for UI
badges; lazy loading in loops; unbounded `IN` lists; an index on every column; a single-column index
on a low-selectivity flag instead of a partial index; relying on implicit row order; `DISTINCT` to hide
join duplicates; numbers stored and compared as strings; tuning with tiny test tables.

## 13. Evidence labels

State which kind of evidence supports a performance claim, because they differ in strength:

| Label | Means | Typical wording |
|---|---|---|
| Expected (mechanism) | Reasoned from how the index, join or storage works | "This predicate cannot use the index; expect a scan on large tables" |
| Estimated plan | The optimiser's plan without execution | "The estimated plan chooses a full scan" |
| Measured plan | Plan with actual rows and timings on stated data | "On a 40 M-row copy the query read 1.2 M pages in 8.4 s" |
| Measured end to end | Latency or throughput percentiles under stated load | "p95 fell from 820 ms to 95 ms at 50 req/s over five runs" |

Never present an expectation as a measurement. A finding based on reading code alone is at most
"likely" (`../knowledge-model.md` §4.4), and the reply says what measurement would confirm it.
