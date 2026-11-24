# Customer orders page (p95 ~4 s): what to fix first

## Summary

**Fix first: the composite index on `orders` has its columns in the wrong order for this page.** `orders_created_customer_idx` is `(created_at, customer_id)`, so PostgreSQL can't jump to one customer's orders. Instead it walks *everyone's* orders from the last 90 days, newest first, and checks `customer_id` on each entry. Your EXPLAIN shows exactly that path: Index Scan Backward on that index, with both conditions in the Index Cond. The work per page grows with the total number of recent orders, so it gets worse as you grow. Add an index on `(customer_id, created_at, id)`, built concurrently.

Suggested order:
1. **New index** (F-01). It's additive and needs no UI change.
2. **Same PR: remove the N+1 in the view** (F-02).
3. **Keyset instead of OFFSET paging** (F-03). The index doesn't fix deep pages, and your captured query is page 50.
4. **The support-search queries** (F-04). Each fully scans a 2M- or 20M-row table. They aren't on this page but compete with it for disk and cache. If `pg_stat_statements` ranks them high by total time, move them up.

**What the evidence is.** I had no access to your database. Your EXPLAIN has no ANALYZE, so its costs are estimates, not times. Its LIMIT/OFFSET numbers also don't add up, so I used the plan's shape, not its figures.

No PostgreSQL server was running here, but PostgreSQL 16 was installed, so I ran a throwaway instance on **synthetic data at your row counts**: 20M orders spread evenly over 3 years, 2M customers, and customer 48122 with ~6,800 orders in 90 days. That shows how much work each query shape does, counted in 8 kB pages touched. It doesn't show your latency: the cache was warm, the machine idle and the data made up. There, the typical-customer query took ~30 ms, far from your 4.1 s. So how much of your p95 this index explains is unmeasured, and the check in F-01 will settle it.

## Findings

### F-01 [major · confirmed] Index column order makes every page scan all customers' recent orders
- **Where:** `db/indexes.sql:1`, used by `orders/queries.py:6-9`
- **Type:** performance · **Rule:** DATA-IDX-01
- **What:** A composite index is sorted by its first column. With `created_at` first, `customer_id = ?` can only filter entries inside the 90-day range; it can't jump to them. For a typical customer the 50-row limit never fills, so the scan reads the whole 90-day slice of the index.
- **Why it matters:** Each page view costs about as much as reading all recent orders. Customers with few orders, who are most of them, are the worst case.
- **Fix:** Add `models.Index(fields=["customer", "created_at", "id"], name="orders_customer_created_idx")` to `Order.Meta.indexes`, run `makemigrations`, then make the build concurrent (Django migration with `atomic = False` and `AddIndexConcurrently`). Also order by `("-created_at", "-id")`. Without a unique tie-breaker, orders with equal timestamps can repeat or vanish between pages.
  **Rollout:** don't use a plain `CREATE INDEX` like those in `db/indexes.sql`. On 20M rows it blocks writes to `orders` for the whole build. A concurrent build is slower and waits for open transactions. If it fails, it leaves an invalid index that you must drop before retrying. Expect ~0.6–0.8 GB of extra index (773 MB on the synthetic table) and a little more work per insert.
  **Keep the old index for now:** the rewritten day query (F-04) uses it. Drop indexes only after `pg_stat_user_indexes` shows them unused.
- **Evidence:** Your plan shows this access path. I reproduced it on PostgreSQL 16.15 with the synthetic data, 5 runs each, all pages already in memory:

| Query (synthetic data) | Existing index only | With new index |
|---|---|---|
| Typical customer (2 orders in window), page 1 | 6,305 pages, 30–39 ms | 10 pages, 0.1 ms |
| Customer 48122, page 1 | 136 pages, 0.4–0.7 ms | 56 pages, 0.1–0.2 ms |
| Customer 48122, page 50 (`OFFSET 2450`) | 5,906 pages, 14–15 ms | 5,867 pages, 12–14 ms |

  **To confirm on your side:** run `EXPLAIN (ANALYZE, BUFFERS)` for the page query on a replica or production-sized copy, for a typical customer and for 48122, before and after the change. Turn `track_io_timing` on to see time spent reading from disk. Thousands of buffers for a 50-row page means this is the problem; far fewer means look elsewhere, at `pg_stat_statements` and the APM trace. After deploying, compare the p95.

### F-02 [major · likely] N+1: one extra query per row, all for the same customer
- **Where:** `orders/views.py:11-12`
- **Type:** performance · **Rule:** PERF-IO-01
- **What:** `order.customer.name` lazy-loads the customer for each order. That's 50 extra round trips per page, all fetching the same row.
- **Why it matters:** Each lookup is cheap, but together they add network time to every page view. I haven't measured how much; your APM trace's count of database calls will show it.
- **Fix:** add `select_related("customer")` in `recent_orders_for_customer`, or fetch the customer once in the view. Pin the view's query count with `assertNumQueries` so it can't creep back.
- **Evidence:** Read from the code; not run, because Django isn't installed here. This assumes a plain foreign key and no manager that already joins it, since `models.py` wasn't attached.

### F-03 [major · confirmed] OFFSET paging keeps deep pages expensive, and `page` is unvalidated
- **Where:** `orders/queries.py:9`, `orders/views.py:8`
- **Type:** performance · **Rule:** API-PAGE-01
- **What:** The slice becomes `LIMIT 50 OFFSET (page-1)*50`, and PostgreSQL reads and discards every skipped row. `page` is unvalidated: a non-number raises `ValueError`, and `0` or a negative number gives a negative slice that Django rejects. Both return a 500.
- **Why it matters:** Page 50 of customer 48122 read ~5,900 pages with or without the new index.
- **Fix:** keyset paging, using `(created_at, id)` as the cursor (code given: `.order_by("-created_at", "-id")`, filter `created_at__lte=ts` plus `Q(created_at__lt=ts) | Q(created_at=ts, id__lt=last_id)`). The UI gets older/newer links instead of page numbers, which is a product decision. If numbered pages stay, validate `page` and cap it.
- **Evidence:** Synthetic data with the new index, fetching the 50 rows after customer 48122's first 2,450: `OFFSET 2450` 5,867 pages, ~13 ms; Q(...)|Q(...) alone 2,163 pages, ~3.4 ms; plus the `created_at__lte` bound 54 pages, 0.2 ms; SQL row comparison `(created_at, id) < (…)` 50 pages, 0.2 ms. I read the `page` handling from the code but didn't run it.

### F-04 [major · confirmed] The support-search queries can't use their indexes
- **Where:** `orders/queries.py:12-31`
- **Type:** performance · **Rule:** DATA-IDX-02
- **What:** Each query wraps the indexed column in a function or cast, or starts its pattern with a wildcard:
  - `lower(email)` can't use the plain `email` index.
  - `date(created_at) = %s` can't use any index.
  - `LIKE '%term%'` can't use a normal index, and the join on `c.id::text = o.legacy_customer_ref` can't use the customers primary key.
- **Why it matters:** Every support search fully scans a 2M- or 20M-row table.
- **Fix:**
  - **Email:** `CREATE UNIQUE INDEX CONCURRENTLY customers_email_lower_idx ON customers (lower(email));`. First run `SELECT lower(email), count(*) FROM customers GROUP BY 1 HAVING count(*) > 1;`. Today's unique index is case-sensitive, so such duplicates may exist. If they do, the build fails, and the current lookup can match two customers with `fetchone()` returning either one.
  - **Day:** use `created_at >= %s AND created_at < %s`, with time-zone-aware start-of-day bounds in the zone you mean. On `timestamptz`, `date()` uses the session's time zone.
  - **Search:** first check why it joins on `legacy_customer_ref`. If newer orders leave it empty, the search misses them. Otherwise join on `customer_id`, or drop the join, since only `o.id` is selected. Add a `LIMIT`, and a trigram index (`pg_trgm` GIN) or full-text search for the text match.
- **Evidence:** On the synthetic data with PostgreSQL 16.15: email 19,655 pages and 152 ms as written, 4 pages and 0.02 ms with the expression index; day ~245,000 pages and 1.17 s as written, 297 pages and 3 ms as a range using the existing `created_at`-first index; search 2.6 s as written (merge join with sorts spilling to disk, 3 parallel processes scanning all of `orders`), 0.98 s joining on `customer_id`. PostgreSQL refused an index on `date(created_at)` for `timestamptz` ("functions in index expression must be marked IMMUTABLE"), which is why I suggest the range rewrite. I didn't build or measure the trigram index. A GIN index on 20M rows is large and adds write cost, so measure it.

## Also noticed (out of scope)
- **Access control:** `views.py` has no authentication or ownership check. Unless `urls.py` or middleware enforces one, anyone who can reach the URL can read any customer's orders by changing the ID.
- **Statement timeout:** none is visible. Set `statement_timeout` for the web app's connections so one slow query can't hold a worker; support search may need a longer limit.
- **`orders_status_idx`:** it indexes a column with few distinct values, and nothing attached uses it. Check `pg_stat_user_indexes` before keeping it (it costs every write) or dropping it. A partial index fits rare statuses better.
- **`ninety_days_ago()`:** `queries.py` calls it but neither defines nor imports it. It was probably trimmed from the excerpt; as attached, it would raise `NameError`.

## Scope
- **Read in full:** all five attached files.
- **Not reviewed (not attached):** `models.py`, `urls.py` and middleware, the template, settings, tests, and your real data and its distribution.
- **Assumptions:** PostgreSQL 16 and Django 5, as the README states; `created_at` is `timestamptz`, which is what Django's `DateTimeField` uses on PostgreSQL. The engine your tests run on is unknown.

## Verification
| Check | Command | Result |
|---|---|---|
| Lock-risk lint of your index DDL | `python3 scripts/migration_lint.py . --files db/indexes.sql --dialect postgresql` | 3 high (each plain `CREATE INDEX` blocks writes for the whole build), 1 medium, 1 info |
| Lock-risk lint of the F-01 migration | `python3 scripts/migration_lint.py <scratch> --files orders/migrations/0099_orders_customer_created_idx.py --dialect postgresql` | No leads. A control with plain `AddIndex` was flagged, so the check runs on Django files. |
| Synthetic reproduction | Throwaway PostgreSQL 16.15 in my sandbox; `EXPLAIN (ANALYZE, BUFFERS)`, 5 runs per page query | Figures above: synthetic data and a warm cache, not your system |
| Plans on your database | — | Not run: no access |
| Django tests / query counts | — | Not run: Django isn't installed here and no tests were attached |

---

## Trace (summary of the executor's list)
1–7. Listed the skill; placed the 5 fixture files; read rules DATA-IDX-01, DATA-IDX-02, API-PAGE-01, PERF-IO-01, PERF-IO-02, DATA-CONN-01, PERF-MEAS-01; greps of knowledge-model.md, data/internals.md, data/modeling.md, data/engines.md, data/types.md, languages/python.md; `--help` of migration_lint.py and schema_lint.py.
8. `migration_lint.py . --files db/indexes.sql --dialect postgresql` → 3 high, 1 medium, 1 info; Django not installed.
9–11. Found PostgreSQL 16.15 binaries (no server running); started a throwaway server as the postgres user (Unix socket, fsync off); TimeZone Asia/Tehran.
12. Loaded 2M customers and 20M synthetic orders; built the fixture's indexes (except orders_status_idx); VACUUM ANALYZE.
13–14. `migration_lint.py` on the proposed AddIndexConcurrently migration → no leads; control with plain AddIndex → index-not-concurrent (medium) and no-lock-timeout (info).
15. Load finished: 1,643,823 rows in the 90-day window, 6,819 for customer 48122.
16–19. EXPLAIN (ANALYZE, BUFFERS) before and after `CREATE INDEX CONCURRENTLY orders_customer_created_idx ON orders (customer_id, created_at, id)` (15.3 s, 773 MB); keyset variants.
20–21. Other queries (email, date(), search) as written and rewritten; date() expression index rejected (not IMMUTABLE); lower(email) duplicates check (0) and expression index.
22. Stopped the server and deleted the data directory.
23–26. Read check_report.py; `check_report.py` on the answer → 2,051 words (over 1,800), then 0 errors, 0 warnings after tightening.
Files written: only under /tmp/eval-perf/scratch. Skill files read: SKILL.md, workflows/database-review.md, data/performance.md, languages/sql.md, templates/review-report.md (full); parts of knowledge-model.md, data/internals.md, data/types.md, languages/python.md, data/engines.md; seven rules.
Executor note: the wrapper said no PostgreSQL server is available; binaries were installed and a throwaway server on synthetic data was used, as the answer states.
