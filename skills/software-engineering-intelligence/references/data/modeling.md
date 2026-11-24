# Data modelling: from facts and rules to tables, keys and relationships

How to design and critique a relational model so that it states what the data means, keeps it
consistent under every writer, and changes safely (P-72). It is informed by X24's design method
(start from the organisation's purpose and its rules, then structures, keys, relationships and
integrity), written as review questions in this skill's own words and order. Rules: DATA-SCHEMA-01, DATA-MODEL-01..05, DATA-KEY-01,
DATA-TYPE-01..05. Types: `types.md`; engine differences: `engines.md`; how physical choices affect
speed: `performance.md` and `internals.md`.

## Contents
1. Three levels of model · 2. Finding entities, attributes and relationships · 3. Relationships,
cardinality and optionality · 4. Keys · 5. Functional dependencies and normal forms · 6. When to
denormalise — and when to stop normalising · 7. History, lifecycle and audit · 8. Where each
integrity rule lives · 9. Review checklist · 10. Worked example

## 1. Three levels of model

| Level | Contains | Decided by | A defect here looks like |
|---|---|---|---|
| Conceptual | Things the business talks about, their relationships and rules, in the business's words (X1 ubiquitous language) | Domain experts and requirements | A relationship nobody modelled ("an account can have several holders") |
| Logical | Tables, columns with domains, keys, relationships with cardinality, rules as constraints; engine-neutral; normalised | Meaning and integrity | Update anomalies, orphans, impossible states |
| Physical | Engine types, indexes, partitioning, clustering, materialised views, deliberate denormalisation | Workload and engine | Slow queries, lock contention, bloat |

Keep the levels apart in reviews: an index cannot fix a missing relationship, and a performance
concern justifies a physical change only with a documented trade-off (DATA-MODEL-02), not a change
of meaning.

## 2. Finding entities, attributes and relationships

Start from statements of fact the business makes — "a customer holds accounts at a branch", "a
transfer moves an amount from one account to another at an instant at an agreed rate". Then:

- **Entity**: something with its own identity and lifecycle that other facts refer to (customer,
  account, transfer). If an "attribute" has attributes of its own — an address with a validity
  period, a phone with a type — it is an entity.
- **Attribute**: a single fact about one entity, with a domain (type, range, format) and a rule for
  absence (`types.md` §7).
- **Relationship**: a fact connecting entities, with its own attributes when it has any (the role
  of a holder on an account, the date it began).
- **Multi-valued facts** (several phones, several holders) become rows in their own table, never
  numbered columns or lists in one column.
- **Derived values** (age from birth date, balance from ledger entries) are computed, unless stored
  deliberately for speed with a stated sync mechanism (DATA-MODEL-02) or as a snapshot of history
  (DATA-MODEL-04).

## 3. Relationships, cardinality and optionality

| Relationship | Representation | Enforce |
|---|---|---|
| One-to-many | Foreign key on the "many" side | `NOT NULL` when mandatory; referential action chosen deliberately |
| Many-to-many | Junction table with foreign keys to both sides and a composite primary or unique key; relationship attributes live there | Both foreign keys; uniqueness of the pair (or of pair + period) |
| One-to-one | Foreign key with a UNIQUE constraint on the dependent side; or merge the tables when lifecycle, access and optionality are the same | UNIQUE on the foreign key |
| Hierarchy | Self-referencing foreign key; closure table or materialised path when deep queries dominate | No cycles (check in code or a trigger) |
| "Belongs to one of several" | One nullable foreign key per possible parent plus a CHECK that exactly one is set, or a supertype table | Foreign keys still enforceable — unlike a `*_type` + `*_id` pair |

Cardinality rules beyond what a foreign key expresses ("at most three active cards per customer",
"exactly one primary address") need a mechanism: a partial or filtered unique index where the engine
has one, a counter with a check constraint, a serialisable transaction or row lock (DATA-TXN-02), or a
trigger. Test each with concurrent writers (TEST-CONC-01).

Common defects (DATA-MODEL-03): `*_id` columns with no foreign key; many-to-many stored as
comma-separated IDs or JSON arrays; repeating groups (`phone1`, `phone2`, `phone3`); a foreign key at
the wrong level (order line → customer rather than order); a mandatory relationship with a nullable
key; `ON DELETE CASCADE` on records whose history must survive.

## 4. Keys

- **Candidate keys** are the minimal column sets that identify a row. Choose one as the primary
  key and enforce every other with UNIQUE — a surrogate primary key without a unique natural key
  lets duplicate customers in.
- **Natural keys** (IBAN, ISO country code, national ID) carry meaning, so they can change, be
  reused, be sensitive or change format. They make good unique constraints and risky primary keys
  referenced from many tables.
- **Surrogate keys** (identity or sequence integers, UUIDs) are stable and meaningless — good
  primary keys when paired with the natural key's unique constraint.
- **Composite keys** fit junction tables and dependent rows (`order_id`, `line_no`); foreign keys
  referencing them become multi-column.
- **Size for growth**: a 32-bit integer ends at 2,147,483,647; busy tables need 64-bit keys. Sequences
  and identities leave gaps on rollback — never rely on gapless numbering (use a separately allocated
  document number if the law requires sequences without gaps).
- **Random versus ordered**: random UUIDs spread inserts across the whole index; in engines that
  cluster rows by primary key (InnoDB; SQL Server's default clustered primary key) every secondary
  index also carries the key, so a wide random key costs space, page splits and cache misses
  (`internals.md` §2, T-33). Prefer compact sequential or time-ordered keys, and a separate public
  identifier when enumeration matters — never unguessability as access control (SEC-AUTHZ-02).

## 5. Functional dependencies and normal forms

A functional dependency X → Y holds when each value of X determines exactly one value of Y
(`account_number → branch_code` if an account belongs to exactly one branch). Normal forms remove the
anomalies that redundant dependencies create:

| Form | Requirement (informal) | Violation example | Anomaly it causes |
|---|---|---|---|
| 1NF | One value per column, no repeating groups, rows identified by a key | `phones = '0912…, 0935…'`; `phone1..phone3` | Cannot query, constrain or index individual values |
| 2NF | No non-key column depends on part of a composite key | `order_lines(order_id, product_id, order_date, qty)` — `order_date` depends on `order_id` only | Changing an order's date means updating every line |
| 3NF | No non-key column depends on another non-key column | `accounts(account_id, branch_code, branch_city)` | Branch city updated in one account and not another; no place for a branch without accounts |
| BCNF | Every determinant is a candidate key | `(student, course) → teacher` with `teacher → course` | Same fact recorded on many rows when candidate keys overlap |
| 4NF / 5NF | Independent multi-valued facts in separate tables | `employee_skills_languages(emp, skill, language)` | Adding a language requires a row per skill |

The practical test: **if this fact changes, how many rows must change?** More than one means the fact
is stored redundantly and can drift. "Atomic" depends on use: an address line you never query into is
atomic enough; a list you filter by is not. Normalisation is about facts, not repeated strings: two
customers in the same city is not redundancy unless city facts are copied with it.

## 6. When to denormalise — and when to stop normalising

**Denormalise** (a physical decision, DATA-MODEL-02) only when the read cost is measured, reads far
outnumber writes, a sync mechanism exists (same-transaction update, trigger, materialised view,
projection) and a reconciliation check catches drift. Try indexes, covering indexes and materialised
views first — most read problems are indexing problems (X26).

**Snapshots are not redundancy** (DATA-MODEL-04). The unit price on an order line, the exchange rate
applied to a transfer, the tax rate on an invoice, the address a parcel was sent to are facts about
the event. Normalising them away rewrites history whenever the source changes.

**Stop normalising** when a split removes no anomaly (DATA-MODEL-05): entity–attribute–value tables
for attributes known at design time lose types, constraints and indexes; one-to-one splits with the
same lifecycle double the joins; lookup tables for open-ended values add a join without integrity.
EAV or JSON is justified for genuinely user-defined or sparse attributes, with validation and a
documented boundary.

**Analytical stores** (star schemas, wide tables) denormalise by design and are derived from the
system of record (DATA-MODEL-01).

## 7. History, lifecycle and audit

- **Lifecycle**: one status column with a closed set of values (`types.md` §5) and enforced
  transitions, rather than several booleans whose combinations can contradict each other.
- **Soft delete** complicates uniqueness (partial unique indexes), every query (a filter to forget)
  and foreign keys (references to "deleted" rows). Consider archive tables, a status, or real
  deletion with an audit record.
- **History**: effective dating (`valid_from`, `valid_to`, non-overlap enforced where the engine
  allows, for example PostgreSQL exclusion constraints); engine temporal tables where available;
  append-only ledgers and event tables (DATA-AUDIT-01); snapshots (DATA-MODEL-04).
- **Ownership and aggregates**: each table has one owning component (DATA-MODEL-01); rows that must
  change together atomically (an order and its lines) form one aggregate and one transaction
  (DES-DOM-02, X1); other aggregates are referenced by key.
- **Retention and deletion**: per data class (DATA-PRIV-01, DATA-SCALE-01).

## 8. Where each integrity rule lives

X24 distinguishes integrity at the level of tables, fields and relationships, plus business rules.
The skill's placement (T-20):

| Rule kind | Database mechanism | Application role |
|---|---|---|
| Identity and uniqueness | Primary key, UNIQUE (case- or format-normalised where the domain says so) | Report the violation as an expected error |
| Field domain: type, range, format, presence | Type, `CHECK`, `NOT NULL`, domain types | Friendly validation messages |
| Relationships | Foreign keys with deliberate referential actions; `NOT NULL` for mandatory | — |
| Cross-row or cross-table invariants | Constraint where expressible; otherwise transaction mechanism (DATA-TXN-02) or trigger | Enforce and test under concurrency |
| Policy that changes often | — | Domain code (T-20) |

Application validation complements database constraints and never replaces them (DATA-SCHEMA-01):
other services, scripts, migrations and concurrent requests bypass it.

## 9. Review checklist

1. Can each table's purpose be stated as one kind of fact about one kind of thing?
2. Does every table have a primary key, and is every candidate key unique in the database?
3. Is every relationship a foreign key (or a documented exception with a reconciliation check), with
   cardinality and optionality matching the rules?
4. If any single fact changes, how many rows change? More than one → redundancy, or a deliberate
   snapshot or denormalisation with its mechanism named.
5. Are event values (prices, rates, addresses) captured as of the event?
6. Does each column's type follow its meaning (`types.md` §1), and does each nullable column have a
   stated meaning?
7. Are statuses closed sets with enforced transitions?
8. Which rules live only in code, and could a second writer break them?
9. Is any split, EAV table or JSON column justified by an anomaly removed or a lifecycle difference?
10. Is history kept where audits, disputes or recalculation need it?

## 10. Worked example

A draft for a small lending system:

```sql
CREATE TABLE loans (
  loan_no        BIGINT PRIMARY KEY,         -- printed on contracts, e.g. 0045-2207-1
  customer_name  VARCHAR(100),
  customer_phone BIGINT,
  branch_code    INT,
  branch_city    VARCHAR(50),
  amount         FLOAT,
  rate           DECIMAL(5,2),               -- 18.50 or 0.185?
  co_borrowers   VARCHAR(500),               -- '1032,1077'
  created        TIMESTAMP
);
```

Review, in the order of the checklist: `loan_no` is an identifier with leading zeros and dashes —
text with a format check, and a surrogate primary key (DATA-TYPE-03, DATA-KEY-01); customer data
depends on the customer, not the loan, and branch city on the branch — move them to `customers` and
`branches` with foreign keys (3NF; DATA-MODEL-03); co-borrowers form a many-to-many relationship —
a `loan_parties(loan_id, customer_id, role)` junction table; `amount` must be exact with currency
(DATA-TYPE-01/02); `rate` needs a stated representation and enough scale, and the rate that applied
at signing is a snapshot to keep even when the product rate changes (DATA-MODEL-04); `created` is an
instant and needs a zone-aware type or a UTC convention (DATA-TYPE-04); phone is a string in E.164
form. Which of these matter most depends on the system's volume and rules — say so when ranking them.
