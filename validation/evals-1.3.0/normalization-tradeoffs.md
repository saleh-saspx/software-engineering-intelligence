# Review: the architect's normalisation notes on db/schema.sql

## Summary

**Verdict:** On `unit_price`, the team is right. It isn't a copy of `products.price`. It's a different fact: the price this line was sold at. Removing it would rewrite every past order whose product has since been repriced. The architect's default of roughly third normal form (3NF) for a transactional schema is sound. But normal forms are about which column determines which, not about the same word appearing in two tables. By that test, most of his list points the wrong way. `customer_email` is the one point where he may be right.

| # | Architect's note | Verdict | What to do |
|---|---|---|---|
| 1 | Drop `order_lines.unit_price` | Wrong: it's the price of the sale, not the list price | Keep it, document it, add a test |
| 2 | Drop `orders.customer_email` | Depends on what the column means | Keep it as a documented snapshot, or drop it in stages |
| 3 | Fully normalised street → city → region → country | Over-normalised, and it lets past ship-to addresses change | Copy the ship-to onto the order; store addresses as text plus a country |
| 4 | Keep `product_attributes` (entity–attribute–value, EAV) for all product data | Wrong as a default | Typed columns for known attributes; EAV only for a registered long tail |
| 5 | `tags` as text is fine | Wrong if you filter by tag (it breaks first normal form) | Add a `product_tags` table |

Apart from these, the core order model holds up: an exact money type, `timestamptz` and enforced keys. This is targeted work, not a redesign.

## Scope

- **Reviewed:** `db/schema.sql` (read in full and loaded into PostgreSQL) and `docs/architect-notes.md`.
- **Not reviewed:** application code, so how tags, addresses and `customer_email` are used is inferred. Also not seen: your data, table sizes, queries and tests.
- **Assumptions:** PostgreSQL (the schema uses `timestamptz`), version unknown; I tested on 16.15. The normal-form conclusions hold on any engine. The index, constraint and migration details are PostgreSQL-specific.

## Verification

All database runs used a throwaway PostgreSQL 16.15 instance with made-up data, not your systems.

| Check | Command | Result |
|---|---|---|
| Schema lint | `schema_lint.py` | 7 leads, all unindexed foreign keys. It reads names and types, not meaning, so I judged notes 1–5 by hand |
| Load schema | `psql -f db/schema.sql` | Clean. Only primary-key and unique indexes exist |
| Reproduce each note | `psql` script | All five effects reproduced |
| Lint my proposed migrations | `migration_lint.py --dialect postgresql` | Expand step: no leads. Index step: run each concurrent build alone, outside a transaction. Contract step: the drops, deferred on purpose |
| Apply my proposed migrations | `psql` | All applied, the email index only after de-duplication; behaviour as described below |
| Not run | — | Anything on your database, code or tests; query plans at real sizes |

## Findings

### F-01 [blocker · confirmed] Dropping `order_lines.unit_price` would rewrite past orders
- **Where:** `db/schema.sql:37` (architect item 1)
- **Type:** defect · **Rule:** DATA-MODEL-04
- **What:** 3NF only objects to a column that another non-key column determines. Here that would need "product → unit price" to hold. It fails as soon as a price changes or a discount applies. So `order_lines` already meets 3NF (standard normalisation theory).
- **Why it matters:** Totals, invoices, refunds and revenue reports would silently follow every price edit. The drop can't be undone, because this column is the schema's only record of what was charged. A price-history table joined on `placed_at` can't hold discounts or negotiated prices. Correcting one of its rows would still rewrite old invoices. Live prices belong only in a cart before checkout.
- **Fix:** Keep the column. Comment it (see the DDL below). Add a test that changes `products.price` after an order and asserts the order total is unchanged.
- **Evidence:** In scratch, after a price rise from 10.00 to 12.00, order 100 totals 20.00 as stored but 24.00 through the architect's join. A same-day promotion line at 8.00 becomes 12.00. Queries 1 and 2 below settle it on your data.

### F-02 [major · confirmed] The address chain lets past ship-to addresses change, yet allows duplicates
- **Where:** `db/schema.sql:3-7`, `db/schema.sql:28` (item 3)
- **Type:** defect · **Rule:** DATA-MODEL-05
- **What:** Orders share `streets`, `cities` and `regions` rows, so editing one of them changes where past orders went. The lookup tables have no unique natural key, so two identical streets in one city are accepted. The chain doesn't give you "one fact in one place". It does cost five joins per shipping label.
- **Why it matters:** Where a parcel went is a fact about that shipment, and you need it for disputes, returns and tax. Street and city names are open-ended values. Lookup tables for them add joins, not integrity.
- **Fix:** Copy the ship-to onto the order at checkout and never update it. Store addresses as text lines, postcode, city, region and a country key. Keep `countries` as a closed ISO list, with the ISO code unique. Keep `regions` only if tax or delivery rules use it. Nothing links addresses to customers, so after the copy, `shipping_address_id` and the chain can go.
- **Evidence:** In scratch, renaming a city changed order 100's address without touching the order, and a duplicate street was accepted. After the change, the same edit left the order's copy alone. The backfill can only copy today's values, so it can't undo edits made before it.

### F-03 [major · likely] `products.tags` is the clearest normal-form violation
- **Where:** `db/schema.sql:14` (item 5)
- **Type:** defect · **Rule:** DATA-MODEL-02
- **What:** A list in one column breaks first normal form. You can't index, constrain or rename a single tag.
- **Why it matters:** In scratch, `tags LIKE '%sale%'` also returned the `wholesale` product. A typo silently creates a new tag. This is "likely" because I couldn't see whether your code filters by tag. If tags are only displayed, text is fine.
- **Fix:** Add `product_tags(product_id, tag)`, keyed on both columns and indexed on `tag`. Add a `tags` table if the list is curated. A PostgreSQL-only option is `text[]` with a GIN index. In scratch it matched exact tags and the planner could use the index, but it can't reference a curated list.
- **Evidence:** Reproduced in scratch. After backfilling `product_tags`, only the right product matched.

### F-04 [major · confirmed] "EAV for all product data" gives up types and constraints
- **Where:** `db/schema.sql:17-22` (item 4)
- **Type:** defect · **Rule:** DATA-MODEL-05
- **What:** An EAV table stores every attribute as a name/value pair of text. It passes normal-form tests on paper, but only by moving the schema into the data. Types, required attributes and allowed values can no longer be declared. "3NF everywhere" isn't a sufficient quality bar.
- **Why it matters:** In scratch, the table accepted `weight_kg = 'heavy'` and a misspelt `wieght_kg`. "Weight over 0.3 kg" then failed at run time with `invalid input syntax for type numeric: "heavy"`. Its `weight_kg` filter would never see the misspelt row anyway.
- **Fix:** Make attributes that all products have, or that code computes with (such as weight for shipping), typed columns with checks. Put attributes of one category (voltage) in typed columns or a per-category table. Keep EAV or `jsonb` only for a sparse, display-only long tail, with names registered in `attribute_definitions`. If your users define their own attributes, EAV is the right tool for that part.
- **Evidence:** After the change, scratch rejected `'heavy'`, −1 and the name `colr`.

### F-05 [minor · likely] `orders.customer_email` is either a snapshot or a drifting copy; decide which
- **Where:** `db/schema.sql:27` (item 2)
- **Type:** question · **Rule:** DATA-MODEL-02
- **What:** F-01's test decides this. If a customer always has one email across all their orders, the column is a redundant copy and should go. If it means "where this order's confirmation went", it's a snapshot like `unit_price`.
- **Why it matters:** A copy drifts: in scratch, one email change left both orders disagreeing. If you send notifications from this column, they go to the old address, and the finding becomes major. A snapshot is fine, but it's one more copy of personal data for your deletion process to cover.
- **Fix:** Check what reads it. Keep and comment it if you need the historical value. Otherwise stop reading it, then stop writing it, then drop it a release later.
- **Evidence:** Drift reproduced in scratch. Query 3 below shows whether it has already happened in your data.

## Also worth fixing (not on the architect's list)

- `customers.email` (`db/schema.sql:1`) is unique only case-sensitively under PostgreSQL's default collation. Scratch accepted both `Bob@Example.com` and `bob@example.com`. Merge duplicates, then add a unique index on `lower(email)`. In scratch, building it while duplicates existed failed and left an invalid index to drop.
- PostgreSQL doesn't index foreign-key columns automatically. `orders(customer_id)` and `order_lines(product_id)` likely need indexes for order history and product lookups. That's the expected effect, not measured.

## What to change, in order

1. **Now:** reject the `unit_price` removal, comment the column and add the test. Run these read-only checks on a replica or at a quiet hour, since they're full scans. All three ran in scratch.

```sql
-- 1. Any row: product_id does not determine unit_price, so it is not redundant
SELECT product_id, count(DISTINCT unit_price) AS distinct_unit_prices
FROM order_lines GROUP BY product_id HAVING count(DISTINCT unit_price) > 1;

-- 2. Past lines whose value would change if unit_price were replaced by products.price
SELECT count(*) AS lines_not_at_current_price
FROM order_lines ol JOIN products p ON p.id = ol.product_id
WHERE ol.unit_price <> p.price;

-- 3. Orders whose email already differs from the customer's current email
SELECT count(*) AS orders_whose_email_differs_from_customer
FROM orders o JOIN customers c ON c.id = o.customer_id
WHERE o.customer_email <> c.email;
```

2. **Expand (release N), additive only.** This applied cleanly in scratch. `NOT VALID` constraints skip existing rows but already reject bad new writes. Then ship code that writes the old and new structures, including the ship-to at checkout.

```sql
SET lock_timeout = '5s';
COMMENT ON COLUMN order_lines.unit_price IS
  'Price agreed for this line at checkout (snapshot). Never recomputed from products.price.';

CREATE TABLE product_tags (
  product_id bigint      NOT NULL REFERENCES products(id),
  tag        varchar(50) NOT NULL,
  PRIMARY KEY (product_id, tag)
);
CREATE INDEX product_tags_tag_idx ON product_tags (tag);

ALTER TABLE products ADD COLUMN weight_kg numeric(8,3);
ALTER TABLE products ADD CONSTRAINT products_weight_kg_positive CHECK (weight_kg > 0) NOT VALID;

CREATE TABLE attribute_definitions (name varchar(50) PRIMARY KEY, unit varchar(20));
ALTER TABLE product_attributes ADD CONSTRAINT product_attributes_attr_name_fk
  FOREIGN KEY (attr_name) REFERENCES attribute_definitions(name) NOT VALID;

ALTER TABLE orders
  ADD COLUMN ship_line1 varchar(200),   ADD COLUMN ship_line2 varchar(200),
  ADD COLUMN ship_postcode varchar(20), ADD COLUMN ship_city varchar(100),
  ADD COLUMN ship_region varchar(100),  ADD COLUMN ship_country_id int;
ALTER TABLE orders ADD CONSTRAINT orders_ship_country_fk
  FOREIGN KEY (ship_country_id) REFERENCES countries(id) NOT VALID;
```

3. **Backfill** in batches that can be re-run and resumed. Split the tags, copy the ship-to and move the weights. Send values that won't parse, and misspelt names, to a person. Then switch reads, run `VALIDATE CONSTRAINT` on each new constraint, and make the ship-to columns `NOT NULL`. On a large table, validate an `IS NOT NULL` check first so `SET NOT NULL` doesn't scan under lock.
4. **Indexes**, each as its own migration outside a transaction. Use `CREATE INDEX CONCURRENTLY` on the two foreign keys, then the `lower(email)` unique index once emails are merged.
5. **Contract (release N+2)**, once nothing reads them and a backup is verified. Drop `products.tags`, `orders.shipping_address_id`, `addresses`, `streets` and `cities`, and `regions` unless something uses it. Then settle `customer_email`. These drops can't be undone, so they come last.

Your table sizes and write rates aren't known, so time the backfills and index builds on a production-size copy first.

## Trace

Shorthand: `SK` = /home/claude/work/repo/skills/software-engineering-intelligence · `S` = /tmp/eval-norm/scratch · `PG` = /usr/lib/postgresql/16/bin · `psql` below = `psql -h S/sock -U postgres -X -q` (client run as root against the scratch server).

**Shell commands, in order**
1. `ls -la SK SK/references SK/scripts SK/assets | head -100`: listed the skill's folders and scripts.
2. `mkdir -p /tmp/eval-norm && cd /tmp/eval-norm && bash SK/evals/normalization-tradeoffs/place-files.sh && find /tmp/eval-norm -type f | sort`: placed `db/schema.sql` and `docs/architect-notes.md`.
3. `ls -la SK/references/data SK/references/rules SK/assets/templates; wc -l SK/references/data/*.md SK/references/rules/data-design.md`: listed data references, rule files and templates, with sizes.
4. `python3 SK/scripts/rules.py --help | head -30; python3 SK/scripts/rules.py list --domain DATA | head -80`: printed usage and listed 33 DATA rules.
5. `grep -n -i -E "normal|denormal|snapshot|EAV|T-2[0-9]|T-3[0-4]" SK/references/knowledge-model.md | head -60`: found the tension table (none specific to normalisation) and the explanation-order section.
6. `python3 SK/scripts/rules.py show DATA-MODEL-02 DATA-MODEL-03 DATA-MODEL-04 DATA-MODEL-05 DATA-SCHEMA-01`: printed the full rule texts.
7. `for t in psql postgres pg_ctl initdb pg_ctlcluster sqlite3 mysql mysqld mariadb duckdb sqlcmd; do command -v $t …; done; ls /usr/lib/postgresql …; python3 -c "import sqlite3…"; python3 --version`:
   - On PATH: psql and pg_ctlcluster.
   - PostgreSQL 16 binaries under PG.
   - No sqlite3, mysql, mariadb, duckdb or sqlcmd CLIs.
   - Python 3.13.18, with the sqlite3 module.
8. `python3 SK/scripts/schema_lint.py --help | head -40`: printed usage.
9. `cd /tmp/eval-norm && python3 SK/scripts/schema_lint.py /tmp/eval-norm`:
   - Detected PostgreSQL; read 10 tables and 36 columns.
   - 7 medium `fk-without-index` leads.
   - No leads for tags, EAV or snapshots.
10. `ls PG/; PG/postgres --version; id -un; whoami`: the server binary is present (PostgreSQL 16.15); I was running as root.
11. `grep -n -i -E "email|comma|tags|list in|case-insens|citext|lower\(" data/types.md data/engines.md languages/sql.md; grep -n -i -E "foreign key|FK" data/engines.md` (in SK/references): engines.md says PostgreSQL doesn't create FK indexes, and notes case-variant duplicate emails on PostgreSQL.
12. `getent passwd postgres; command -v runuser su setpriv; ls -ld /tmp /tmp/eval-norm`: the postgres user and runuser exist.
13. `mkdir -p S/pgdata S/sock; chown -R postgres:postgres S; runuser -u postgres -- PG/initdb -D S/pgdata -A trust -U postgres --no-instructions; runuser -u postgres -- PG/pg_ctl -D S/pgdata -l S/server.log -o "-c listen_addresses='' -k S/sock" -w start; runuser -u postgres -- psql -Atc "select version();"`: initdb succeeded and the server started, socket only. Version: PostgreSQL 16.15.
14. `psql -c "CREATE DATABASE shop;" && psql -d shop -v ON_ERROR_STOP=1 -f /tmp/eval-norm/db/schema.sql; psql -d shop -At -c "SELECT tablename||': '||indexdef FROM pg_indexes WHERE schemaname='public' …"`: the schema loaded with no errors. 12 indexes, all primary-key or unique, none on FK columns.
15. `psql -d shop -v ON_ERROR_STOP=0 -f S/demo.sql`: reproduced all five notes plus the email-case issue.
    - Totals: 20.00/8.00 as stored vs 24.00/12.00 through the join.
    - Product 1 has 2 distinct unit prices; 2 lines differ from the current price.
    - A duplicate street was accepted, and a city rename changed order 100's address.
    - EAV accepted 'heavy' and 'wieght_kg'. The numeric filter failed with `invalid input syntax for type numeric: "heavy"`, as expected.
    - `LIKE '%sale%'` also returned the wholesale product.
    - After an email change, 2 orders' emails differed from the customer's.
    - `Bob@Example.com` and `bob@example.com` were both accepted.
16. `python3 SK/scripts/migration_lint.py --help | head -45`: printed usage.
17. `mkdir -p S/migrations && cd S/migrations && cat > 001_expand.sql … 002_indexes.sql … 003_validate.sql … 004_contract.sql …; python3 SK/scripts/migration_lint.py S/migrations --dialect postgresql`: wrote the 4 migration files. The lint analysed 0 files, because it didn't discover them without `--files`.
18. `python3 SK/scripts/migration_lint.py S/migrations --dialect postgresql --files 001_expand.sql 002_indexes.sql 003_validate.sql 004_contract.sql`:
    - 001 and 003: 0 leads.
    - 002: 3 medium (concurrent index builds alongside other statements).
    - 004: 5 high (2 drop-column, 3 drop-table).
19. `psql -d shop -v ON_ERROR_STOP=0 -f S/verify_target.sql`:
    - 001 applied; the `product_tags` query returned only MUG-01; the order snapshot didn't change after a city edit.
    - New writes were rejected: −1 by the check, 'colr' by the FK, 'heavy' by the type.
    - 002 built both FK indexes. The unique `lower(email)` build failed on duplicates and left `indisvalid = f`.
    - After dropping it, removing the duplicate and rebuilding, `BOB@example.com` was rejected.
    - 003 validated all 3 constraints. 004 applied (scratch only). Totals were still 20.00/8.00.
20. `psql -d shop -v ON_ERROR_STOP=1 <<EOF (temp table with text[] tags, a GIN index, an @> query, and EXPLAIN with enable_seqscan=off) EOF`: matched only MUG-01, and the plan used a Bitmap Index Scan on the GIN index. This was a 2-row table, so it isn't a performance measurement.
21. `sed -n 1,60p SK/scripts/check_report.py`: read the checker's required sections and fields.
22. `runuser -u postgres -- PG/pg_ctl -D S/pgdata -m fast -w stop; sed -n 60,140p SK/scripts/check_report.py`: stopped the server and read the length budget (about 1,800 words for full reports).
23. `python3 SK/scripts/check_report.py S/answer.md` (draft 1): 0 errors, 1 warning (2,206 words, over budget).
24. Same command (draft 2): 0 errors, 1 warning (1,919 words).
25. Same command (draft 3): 0 errors, 0 warnings.
26. Same command, plus `python3 -I -c "<prose word count>"`: 0 errors, 0 warnings, 1,669 prose words.
27. `pg_ctl -D S/pgdata status; rm -rf S/pgdata S/sock; ls -la db docs; find /tmp/eval-norm -type f -not -path '*/scratch/*' -newer S/demo.sql; ls S S/migrations`: no server was running. I removed the scratch cluster's data and socket directories. The two input files were unchanged.
28. `python3 SK/scripts/check_report.py S/answer.md` (after defining EAV): 0 errors, 0 warnings.

Created with the editor tool rather than the shell: S/demo.sql, S/verify_target.sql and S/answer.md (drafts and edits). Nothing under /home/claude/work/repo was modified, and I did not open graders/ or case.yaml.

**Skill files read**
- SKILL.md (in full)
- references/workflows/database-review.md (in full)
- references/data/modeling.md (in full)
- references/knowledge-model.md: the explanation-order section (lines 236–259), plus grep hits
- references/rules/data-design.md: via `rules.py show` (DATA-MODEL-02 to 05, DATA-SCHEMA-01) and `rules.py list --domain DATA`
- assets/templates/review-report.md (in full)
- references/data/types.md, references/data/engines.md, references/languages/sql.md: grep hits only
- scripts/check_report.py: lines 1–140
- Scripts run: rules.py, schema_lint.py, migration_lint.py, check_report.py. I also ran evals/normalization-tradeoffs/place-files.sh but did not read it.
