# Choosing data types: a decision framework and practical cases

A column's type is a statement about what the value means, how it is compared and computed, and what
it can never be. Choose it from the semantics of the data, not from the values seen so far (P-72).
These are reusable decision rules, not any one project's conventions; engine details are verified in
`engines.md` and must be checked against the version in use. Rules: DATA-TYPE-01..05, DATA-KEY-01,
DATA-SCHEMA-01, REL-TIME-03.

## Contents
1. Questions for every column · 2. Numbers · 3. Text · 4. Date and time · 5. Booleans, enumerations
and statuses · 6. Semi-structured and special types · 7. NULL, zero, empty and missing · 8. Practical
cases · 9. Database ↔ application mapping

## 1. Questions for every column

1. **Meaning**: a quantity you compute with, an identifier or code, a label, an instant, a business
   date, a duration, a state, a document?
2. **Range**: today and in ten years — including totals and aggregates, not just single values.
3. **Precision, scale and rounding**: how many digits and decimals, which rounding mode, applied at
   which step, decided by whom (regulation, contract, currency)?
4. **Operations**: compared, sorted, summed, searched by prefix, joined, indexed?
5. **Absence**: can it be unknown or not applicable, and is that different from zero or empty
   (§7)?
6. **Size**: row count × (table + every index that includes it).
7. **Portability**: which engines, ORMs, drivers and clients (JavaScript loses integer precision
   above 2^53 − 1) will read it?
8. **Overflow**: does the engine raise an error, round, or silently store something else?
9. **Application mapping**: does the driver or ORM convert it to a lossy type (§9)?

## 2. Numbers

**Integers** (`SMALLINT`, `INTEGER`, `BIGINT`) are exact: counts, surrogate keys, amounts in minor
units. Check growth — a 32-bit integer ends at 2,147,483,647.

**Exact decimals** (`DECIMAL`/`NUMERIC(p, s)`) hold money, prices, rates and fractional quantities.
Always declare precision and scale: defaults differ and some are dangerous — MySQL `DECIMAL` without
scale stores whole numbers (precision 10), SQL Server defaults to (18,0), PostgreSQL's unconstrained
`numeric` accepts any scale, Oracle's `DECIMAL`/`NUMERIC` default to scale 0 while a bare `NUMBER`
stores up to 38 significant digits with no fixed scale, and SQLite's `NUMERIC`/`DECIMAL` columns hold integers or 8-byte binary floats.
PostgreSQL rounds values to the declared scale and raises an error when the integer part exceeds
p − s; SQL Server rounds when converting between numeric scales.

**Binary floating point** (`REAL`, `FLOAT`, `DOUBLE PRECISION`, `BINARY_DOUBLE`) is approximate:
measurements, statistics, scientific values. Not money, not equality comparisons, not keys
(DATA-TYPE-01). Note Oracle's `FLOAT(p)` is a decimal `NUMBER` subtype; its binary types are
`BINARY_FLOAT` and `BINARY_DOUBLE`.

**Sizing and rounding** (DATA-TYPE-02):
- Precision for the largest **total**, not the largest single value: digits of the maximum value
  plus digits of the number of rows summed, plus headroom.
- Scale for the smallest unit that matters: currency minor units (0 for JPY, 2 for most currencies,
  3 for KWD — ISO 4217), more for unit prices and rates.
- Intermediate results (multiplication, division, allocation) need more scale than storage; round
  once, at the step the specification names (per line or per total), with the named mode. Defaults
  differ by layer — PostgreSQL's `round` on `numeric` rounds halves away from zero while on `double
  precision` it typically rounds half to even; Java's `BigDecimal`, Python's `decimal` and .NET
  `Math.Round` each have their own defaults — so set the mode explicitly in code.
- Allocation (splitting 100.00 three ways) needs a remainder rule; test that parts sum to the whole.

**Money**: amount plus currency (ISO 4217 code) in every row, as `DECIMAL(p, s)` or as integer minor
units with the currency's exponent. **Exchange rates**: high scale (rates like 0.0000234 exist), base
and quote currency, source and as-of time — a rate without direction is ambiguous. **Interest rates**:
a stated representation (`rate_fraction 0.047500` or `rate_percent 4.75`) with enough scale, plus the
day-count convention as a separate attribute. **Quantities**: the unit in the column name or a unit
column; scale per unit.

## 3. Text

- `CHAR(n)` pads to n — only for truly fixed-length codes (ISO country `CHAR(2)`); padding rules
  in comparisons differ between engines.
- `VARCHAR(n)`: n counts characters in PostgreSQL and MySQL, bytes by default in Oracle
  `VARCHAR2` (`NLS_LENGTH_SEMANTICS`) and in SQL Server `varchar` (UTF-16 code units in `nvarchar`).
  SQLite does not enforce n. Choose n from a domain rule (IBAN ≤ 34, E.164 ≤ 15 digits plus "+"), and
  do not cap human names or addresses arbitrarily.
- `TEXT`/`CLOB` for unbounded text. In PostgreSQL `text` and `varchar` perform the same; elsewhere
  large-object types can have indexing and comparison limits.
- **Unicode**: UTF-8 end to end — MySQL `utf8mb4` (its `utf8` is the deprecated 3-byte `utf8mb3`,
  which cannot store all characters), Oracle `AL32UTF8`, SQL Server `nvarchar` or UTF-8 collations.
- **Collation** decides equality, uniqueness, ordering and `LIKE`. MySQL's default
  `utf8mb4_0900_ai_ci` ignores accents and case; PostgreSQL's default collations are deterministic.
  Choose case- and accent-sensitivity per column on purpose (unique emails usually want case-insensitive
  comparison; codes usually want exact), and keep parameter and column collations matched so indexes
  stay usable (DATA-IDX-02).

## 4. Date and time

| Meaning | Example | Store as |
|---|---|---|
| Instant (an exact moment) | Payment executed, row created | Zone-aware type, or UTC by a written convention, with stated precision |
| Business or value date | Value date, due date, birthday | `DATE` |
| Local date-time with a zone rule | A 09:00 appointment in Tehran next spring | Local date-time plus IANA zone ID (`Asia/Tehran`), not a fixed offset — rules change |
| Time of day | Branch opening time | `TIME` (plus zone if it matters) |
| Duration | Processing time, timeout | Interval type or integer with the unit in the name |
| Calendar period | "1 month", loan term | Interval with calendar semantics or (count, unit); 30 days is not a month |

Engine behaviour differs (`engines.md` §2): PostgreSQL `timestamptz` stores a UTC instant and
converts on output without keeping the zone; MySQL `TIMESTAMP` converts through the session time zone
and is limited to 1970-01-01 – 2038-01-19 UTC, `DATETIME` is not converted; SQL Server `datetime`
rounds to .000/.003/.007 s (prefer `datetime2` or `datetimeoffset`, which stores an offset); Oracle
`DATE` carries a time of day to the second, `TIMESTAMP WITH TIME ZONE` keeps the zone; SQLite has no
date type (ISO-8601 text or epoch numbers by convention). Precision mismatches (microseconds versus
milliseconds) break equality and uniqueness between systems. Daylight-saving gaps and overlaps affect
local date-times, never UTC instants (DATA-TYPE-04, REL-TIME-03).

## 5. Booleans, enumerations and statuses

- **Booleans**: a nullable boolean is three-valued — allow NULL only if "unknown" is a real state.
  Engine support varies (`boolean`, `bit`, `TINYINT(1)`, Oracle `BOOLEAN` from 23ai).
- **Several flags encoding one state** (`is_active`, `is_closed`, `is_suspended`) allow impossible
  combinations: use one status column with defined transitions.
- **Status representation**:

| Option | Fits when | Costs |
|---|---|---|
| Native enum type (PostgreSQL `CREATE TYPE … AS ENUM`, MySQL `ENUM`) | Small closed set, rarely changed | Changing or removing values needs DDL; MySQL `ENUM` sorts by declaration index; not portable |
| `CHECK` constraint on a short code | Closed set, portable, codes readable in queries | Adding a value means altering the constraint |
| Lookup table with foreign key | Values carry attributes (labels, order, active flag, translations) or are managed as data | A join; must seed reference data in every environment |
| Tenant-scoped lookup table | Users define their own statuses | Rules about status meaning move into data |
| Application-only enum | — | No database enforcement; avoid |

Persist names or codes, never ordinals (DATA-EVOL-01).

## 6. Semi-structured and special types

- **JSON**: PostgreSQL `jsonb` (binary, indexable with GIN) versus `json` (text); MySQL binary
  `JSON`; MariaDB `JSON` = `LONGTEXT` with a validity check; Oracle `JSON` type or `IS JSON` checks;
  SQL Server JSON functions over `nvarchar` (check your version for a native type); SQLite JSON
  functions over text. Use for genuinely schemaless attributes, configuration documents and payload
  archives; not for values that are filtered, joined, constrained or aggregated regularly, for
  relationships, or for money (DATA-MODEL-02, DATA-MODEL-03). Version and validate the shape
  (DATA-EVOL-01).
- **XML**: integration formats; same rules as JSON.
- **Binary**: files usually belong in object storage with a reference (key, size, content hash, type)
  in the row; store bytes in the database only when transactional consistency justifies the size.
- **UUID**: native types where available (PostgreSQL `uuid`, SQL Server `uniqueidentifier`), else
  16-byte binary — not `CHAR(36)`. Random versus time-ordered: `modeling.md` §4, DATA-KEY-01.
- **ULID and similar sortable identifiers**: text or binary; sortable by creation time, so they leak
  it.
- **IP addresses**: PostgreSQL `inet`/`cidr`; elsewhere 16-byte binary or validated text; range
  containment queries need a representation that supports them.
- **Spatial**: plain latitude/longitude columns are fine for storage and display; distance and
  containment queries at scale need the engine's spatial types and indexes.

## 7. NULL, zero, empty and missing

- NULL means unknown or not applicable; zero is a known quantity; `''` is known-empty text; a missing
  JSON key is not a JSON `null`.
- Three-valued logic: `col = NULL` is never true; `NOT IN (subquery)` returns no rows if the subquery
  yields a NULL (use `NOT EXISTS`); aggregates skip NULLs (`SUM` of none is NULL, `COUNT(col)` ≠
  `COUNT(*)`); arithmetic with NULL is NULL.
- Engines differ: Oracle stores `''` as NULL (and advises not to rely on it); SQL Server unique
  constraints allow one NULL while others allow many (Oracle: many all-NULL keys, but a composite key
  with some NULLs and equal other values is a duplicate); NULL sorts last in ascending order in PostgreSQL
  and Oracle, first in MySQL, SQL Server and SQLite.
- Default to `NOT NULL`. Allow NULL only with a documented meaning. If there are two kinds of absence
  ("no limit" versus "limit not yet set"), model them explicitly — a type or status plus a value —
  instead of NULL versus 0 (DATA-TYPE-05).

## 8. Practical cases

| Data | Representation | Why | What goes wrong otherwise |
|---|---|---|---|
| Money amount | `DECIMAL(p, s)` sized for totals + currency `CHAR(3)`, or `BIGINT` minor units + currency | Exact arithmetic; currency gives scale meaning | Float drift; overflow on totals; scale too small for some currencies |
| Exchange rate | `DECIMAL` with high scale (for example (18,10)) + base, quote, source, as-of time | Rates have many significant digits and a direction | Scale 2 rounds 0.0000234 to 0.00; inverted rates applied |
| Interest rate | `DECIMAL(9,6)` as a fraction, or a column named for percent; plus day-count basis | Representation stated once | 100× errors between 4.75 and 0.0475 |
| Account number, IBAN | `VARCHAR` with a format check (IBAN ≤ 34 alphanumerics) | Identifier, not a quantity; may contain letters | Leading zeros lost; overflow; numeric comparison ("010" = "10") |
| Customer ID | `BIGINT` identity or UUID as internal key; customer number as `VARCHAR` with UNIQUE | Stable internal identity; business number keeps its format | Duplicates without the unique business key; precision loss in JavaScript above 2^53 |
| Branch or product code | `CHAR(n)`/`VARCHAR(n)` with a check or a foreign key to the code table | Codes are labels | Leading zeros and letters lost |
| Phone number | `VARCHAR` in E.164 ("+" and up to 15 digits) plus optional extension | Formatted identifier | Integer drops "+", leading zeros and extensions |
| Postal code | `VARCHAR` with per-country validation | Letters and leading zeros exist (UK, Canada, US) | Numeric storage corrupts codes |
| Transaction reference | `VARCHAR` or UUID with UNIQUE | External systems use mixed formats | Collisions after normalisation; overflow |
| Financial quantity (shares, grams) | `DECIMAL` with the instrument's scale + unit | Fractional units exist | Silent rounding of fractional holdings |
| Event timestamp | Zone-aware instant or UTC by convention, stated precision | An instant must be unambiguous | Shifts across zones and daylight saving |
| Value or due date | `DATE` | A calendar day, not an instant | Off-by-one-day across zones |
| User-defined status | Lookup table (tenant-scoped if users define it) + foreign key | Values managed as data | Free text drifts; no integrity |
| System lifecycle status | `CHECK` or native enum + enforced transitions | Closed set | Impossible states |
| Large text | `TEXT`/`CLOB`, with full-text indexing if searched | No arbitrary cut-off | `VARCHAR(255)` truncation; slow `LIKE '%…%'` scans |
| JSON configuration | `JSON`/`jsonb` with a version field and validation | Shape varies; read as a whole | Queried keys without indexes; unversioned shape changes |

## 9. Database ↔ application mapping

- Money and exact decimals: `BigDecimal` (Java), `decimal.Decimal` (Python), `System.Decimal` (.NET),
  a decimal library or string in Go, `brick/math` or `brick/money` in PHP, a decimal library or
  string in JavaScript — never a JavaScript `number` (DATA-TYPE-01). Check that the driver or ORM
  does not convert decimals to floats by default.
- 64-bit identifiers to JavaScript clients: serialise as strings.
- Timestamps: map instants to instant types (`Instant`, `OffsetDateTime`, aware `datetime`),
  dates to date types; check driver time-zone settings, which differ between drivers and engines.
- Booleans and enums: engines that store `0`/`1` or codes need explicit converters.
- Test round-trips of boundary values through database, application and client (TEST-PROP-01).
