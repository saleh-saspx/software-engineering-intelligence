# Review: `db/schema.sql` — core accounts on PostgreSQL 16

## Summary
**Verdict:** changes requested — don't freeze it yet.

You were right to worry about the types: three are blockers. Money is in binary floating point; identifiers are numbers, so leading zeros vanish and any national ID above 2,147,483,647 can't be stored; and FX rates keep 4 decimals, so the README's own example rate (0.00002381) is stored as 0. Fix everything below now, while the tables are empty and each fix is an edit to this file — after go-live most type changes rewrite the table under an exclusive lock and need a multi-release migration.

## Scope
- **Reviewed:** `db/schema.sql` in full (5 tables, 28 columns) against the formats in `README.md`.
- **Not reviewed:** application code, queries, driver mappings, migrations, tests — none were provided.
- **Assumptions:** PostgreSQL 16 in production (README); one bank, so no multi-tenancy; index advice is expected, not measured.
- **Open questions:** which currencies you hold; whether `reference` identifies one posting; whether loan rates change mid-loan; what a NULL phone, postal code or birth date means; your test engine and driver type mappings.

## Verification
| Check | Command | Result |
|---|---|---|
| Schema lint | `python3 …/scripts/schema_lint.py /tmp/eval-bank --dialect postgresql` | 20 leads; all 20 hold against the README and are covered below |
| Arithmetic | `python3 -I -` (inline: IEEE 754 single/double, decimal rounding) | Reproduced every number quoted below |
| Lint of the sketch | same script on the sketch below | No type leads; 5 index leads accepted (reference-table parents; composite keys served by `account_id` indexes) |
| DDL and tests on PostgreSQL 16 | — | **Not run:** no PostgreSQL server here. PostgreSQL behaviour quoted below is from its documentation, not observed. |

## Findings

### F-01 [blocker · confirmed] Money is stored in binary floating point
- **Where:** `db/schema.sql:15` (`balance double precision`), `:25` (`amount real`); `:40` (`principal numeric`, no scale)
- **Type:** defect · **Rule:** DATA-TYPE-01
- **What:** `real` keeps about 7 significant digits: 100,000.01 is stored as 100,000.0078125, and above 16,777,216 whole units go (21,000,001 → 21,000,000). `double precision` can't hold most cent values: ten additions of 0.10 give 0.9999999999999999.
- **Why it matters:** The README's example rate means ~42,000 units of one currency per unit of another, so a 500-unit transfer is ~21 million in the weaker one — past where `real` loses whole units. Balances won't reliably reconcile with their transactions.
- **Fix:** `numeric(p,s)` for every amount, balance and `principal`. Scale = the largest minor unit you hold (ISO 4217: 2 for most currencies, 3 for KWD, BHD, OMR); precision = the largest balance any account, the bank's own included, can reach in your highest-nominal currency (`numeric` is stored by digits present, so generous precision is free). Round to each currency's unit once, with an explicit mode. Add `currency` to `transactions` and `loans`, tied to the account by a composite foreign key; pin the sign convention with a CHECK. `bigint` minor units also work, but every reader must apply the exponent. Map `numeric` to a decimal type in your driver, never a float.
- **Evidence:** Reproduced with IEEE 754 arithmetic in Python (the formats behind `real` and `double precision`), not on PostgreSQL.

### F-02 [blocker · confirmed] FX rates keep 4 decimals — the README's example rate becomes 0
- **Where:** `db/schema.sql:33` (`rate numeric(10,4)`), `:32` (`pair varchar(7)`)
- **Type:** defect · **Rule:** DATA-TYPE-02
- **What:** PostgreSQL rounds to the declared scale without error: 0.00002381 → 0.0000; 0.00012 → 0.0001 (17% off); 1.23456789 → 1.2346, 321 units wrong on a 10,000,000 conversion. Rates of 1,000,000 or more are rejected.
- **Why it matters:** Small-rate conversions silently come out as zero. A 'USD/EUR' string leaves direction to convention, and with no source or unique key, duplicate rows can't be told apart.
- **Fix:** `numeric(18,8)`: the central bank's 8 decimals, 10 integer digits (scale 10 if it may publish more). Replace `pair` with `base_currency` and `quote_currency` (rate = quote units per base unit); add `source` (central-bank reference vs your buy/sell rates) and `effective_at` beside `fetched_at`, unique together. Round once, where your specification says, keeping extra scale before that.
- **Evidence:** Rounding reproduced with Python `decimal`; PostgreSQL's rounding is documented, not observed here.

### F-03 [blocker · confirmed] Identifiers are numbers: national IDs overflow, leading zeros are lost
- **Where:** `db/schema.sql:3` (`national_id integer`), `:12` (`account_number bigint`), `:13` (`branch_code smallint`), `:5` (`phone bigint`), `:6` (`postal_code integer`), `:24` (`reference integer`)
- **Type:** defect · **Rule:** DATA-TYPE-03
- **What:** `integer` stops at 2,147,483,647; 10-digit IDs run to 9,999,999,999, and everything above the limit is rejected as out of range. Leading zeros vanish: 0012345678 → 12345678, branch 0042 → 42, a 13-digit account → 12 digits. Phones lose the "+"; postal codes can't hold letters; external references are often alphanumeric (ISO 20022 end-to-end IDs run to 35 characters).
- **Why it matters:** Those customers can't be onboarded; elsewhere every consumer must re-pad, and one that forgets prints a wrong account number.
- **Fix:** `varchar(n)` with a format CHECK: `^[0-9]{10}$` national ID, `^[0-9]{13}$` account, `^[0-9]{4}$` branch (plus a `branches` table), E.164 phone; postal code validated per country; `varchar` reference sized for the schemes you connect to — UNIQUE (per source system) if it makes postings idempotent, so a retry can't post twice. Keep `bigint` for surrogate keys.
- **Evidence:** Ranges and zero loss checked in Python against the README's formats.

### F-04 [major · confirmed] Account holders are a JSON list, not a relationship
- **Where:** `db/schema.sql:17` (`holders jsonb`)
- **Type:** defect · **Rule:** DATA-MODEL-03
- **What:** Nothing checks that a listed customer exists, appears once, or has a valid role; "accounts of customer 12" is a JSON search; removing or merging a customer leaves dangling IDs.
- **Why it matters:** This decides who owns and may operate each account, and it's the costliest item to change after go-live — a migration of every account.
- **Fix:** `account_holders (account_id, customer_id, role)` with foreign keys, a role CHECK, a composite primary key and an index on `customer_id`; holder changes in an append-only history; "at least one owner" enforced in the account-opening transaction, with a test.
- **Evidence:** Schema and column comment read.

### F-05 [major · likely] Dates stored as timestamps, instants without a time zone
- **Where:** `db/schema.sql:26` (`value_date`), `:7` (`birth_date`); `:18`, `:27`, `:34` (`opened_at`, `created_at`, `fetched_at`) — all `timestamp`
- **Type:** defect · **Rule:** DATA-TYPE-04
- **What:** Value and birth dates are calendar days: as timestamps they gain a meaningless time, date equality misses rows that have one, and a driver mapping them through a non-UTC instant can move them a day. `now()` returns `timestamptz`; stored in `timestamp` it is converted to the session's `TimeZone`, so the value depends on each client's setting, and local times repeat for an hour when clocks go back.
- **Why it matters:** Value dates drive interest and cut-offs; event times drive statement order and audit.
- **Fix:** `date` for the two dates; `timestamptz` for the three events (same 8 bytes; it stores the instant, not the zone).
- **Evidence:** Types read; whether a shift happens depends on driver and session settings I couldn't see.

### F-06 [major · possible] Interest rate: unit only in a comment, scale 2 rounds it
- **Where:** `db/schema.sql:41` (`interest_rate numeric(5,2) -- 4.75`)
- **Type:** defect · **Rule:** DATA-TYPE-02
- **What:** Only the comment says 4.75 is a percent; code reading it as a fraction charges 100× interest. Scale 2 means whole basis points: 4.125 is silently stored as 4.13. No day-count basis (ACT/365, 30/360…) is recorded.
- **Why it matters:** Each changes the interest charged; rounding a contract rate up overcharges.
- **Fix:** `interest_rate_pct numeric(7,4)` (or `interest_rate_fraction numeric(9,6)` — pick one) plus `day_count_basis`; effective-dated history if rates change mid-loan.
- **Evidence:** Rounding checked in Python; whether you use sub-basis-point rates is unknown.

### F-07 [major · likely] FX postings don't keep the applied rate, and transfer legs aren't linked
- **Where:** `db/schema.sql:21–28` (`transactions`), `:15` (`balance`)
- **Type:** reliability-risk · **Rule:** DATA-MODEL-04
- **What:** A transfer's two rows share nothing; an FX leg keeps neither the rate used nor the counter-amount; `fx_rates` has no unique key, so "the rate in force then" can't be rebuilt reliably. `balance` repeats the sum of transactions with no stated sync mechanism.
- **Why it matters:** Disputes and audits need the rate as applied; a half-posted transfer goes unnoticed.
- **Fix:** A journal or transfer ID on each leg, checked nightly to balance per currency; applied rate and counter-amount on FX legs; `transactions` append-only (no UPDATE/DELETE for the application role; reversals for corrections); `balance` updated in the posting's own transaction and reconciled daily.
- **Evidence:** Schema only; the application may keep this elsewhere.

### F-08 [minor · confirmed] Status and currency accept any value
- **Where:** `db/schema.sql:16` (`status`), `:14` (`currency`)
- **Type:** defect · **Rule:** DATA-SCHEMA-01
- **What:** 'Frozen ' passes the column but not code checking `status = 'frozen'`; `currency` takes any three characters.
- **Why it matters:** Status decides whether frozen or closed accounts can be debited.
- **Fix:** A CHECK on the status set, transitions enforced in code; a `currencies (code, minor_unit)` table for every currency column — it also supplies F-01's rounding unit.
- **Evidence:** Schema read.

### F-09 [minor · likely] Foreign-key columns aren't indexed
- **Where:** `db/schema.sql:23` (`transactions.account_id`), `:39` (`loans.account_id`)
- **Type:** performance · **Rule:** DATA-IDX-01
- **What:** PostgreSQL doesn't index foreign keys itself; expected (not measured): per-account reads, and deletes on `accounts`, scan `transactions` once it grows.
- **Why it matters:** Per-account reads are this service's main path.
- **Fix:** Index `transactions (account_id, value_date)` (match your statement sort) and `loans (account_id)`; verify with `EXPLAIN (ANALYZE, BUFFERS)` on production-like data. This can be added later without blocking writes (`CREATE INDEX CONCURRENTLY`), but it's free now.
- **Evidence:** No queries or volumes available.

## Suggested schema (sketch)
(A full PostgreSQL 16 DDL sketch followed in the answer: `currencies` and `branches` reference tables; identity keys; `varchar` identifiers with format CHECKs; `numeric(20,2)` money; `timestamptz` events and `date` business dates; an `account_holders` junction table with foreign keys and an index on `customer_id`; `fx_rates` with `numeric(18,8)`, base and quote currencies, source and `effective_at`, unique together; `loans` with `interest_rate_pct numeric(7,4)` and `day_count_basis`; composite (account_id, currency) foreign keys. Marked "not executed (no PostgreSQL server available)".)

## Before you freeze: run on PostgreSQL 16
On PostgreSQL 16 itself (H2 or SQLite types behave differently): round-trip `0012345678`, `9999999999`, `0123456789012` and `0042` unchanged; store rate 0.00002381 and read it back exactly; post 0.10 a thousand times and get exactly 100.00 in both the sum and `balance`; repeat the timestamp checks under a non-UTC session `TimeZone`; confirm an invalid status, unknown branch and orphan holder are rejected.

## Strengths
64-bit surrogate keys throughout, foreign keys that default to NO ACTION (protecting history), and `currency` already a NOT NULL ISO code.

---

## Trace (summary of the executor's list)
1–2. Listed the skill; placed the fixture (README.md, db/schema.sql).
3–4. Section lists of references/data/*.md and rule files.
5–6. `schema_lint.py --help`; `schema_lint.py /tmp/eval-bank --dialect postgresql` → 5 tables, 28 columns, 20 leads (identifier-numeric 6, timestamp-without-zone 3, money-float 2, date-as-timestamp 2, fk-without-index 2, small-scale-rate 2, status-free-text 1, json-relational 1, decimal-without-scale 1).
7. Greps of knowledge-model.md, sql.md, data-api.md.
8. `python3 -I -` inline arithmetic: integer max vs 10-digit IDs; leading zeros lost; float32/float64 representation errors; scale-4 and scale-2 rounding; 1/0.00002381 ≈ 41,999.16.
9–10. `check_report.py --help`; greps of schema_lint.py and check_report.py.
11. `schema_lint.py` on the proposed sketch → 0 type leads, 5 fk-without-index leads.
12. Read the finding taxonomy; deleted the scratch folder.
13–15. `check_report.py` on drafts → first 1,828 words (over 1,800), then 0 errors, 0 warnings on the final answer.
Not done: nothing run on PostgreSQL ("no server available"); SQLite deliberately not used as a stand-in.
Skill files read: SKILL.md; workflows/database-review.md; data/types.md; rules/data-design.md; templates/review-report.md (full); data/engines.md, data/modeling.md, knowledge-model.md §4 and §9, data-api.md DATA-AUDIT-01, languages/sql.md (part).
