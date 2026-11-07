#!/usr/bin/env python3
"""Lead scanner for risky schema migrations (DATA-MIG-01..03, DATA-BATCH-01, DATA-BACKUP-01).

Reads migration files — plain SQL (Flyway, golang-migrate, dbmate, Prisma, hand-run scripts),
Laravel (PHP), Rails (Ruby), Django and Alembic (Python) — and reports statements that commonly
lock large tables, rewrite them, break the code still running during a rollout, or lose data.

Every hit is a LEAD, not a verdict: whether it matters depends on the engine and version, the size
and write rate of the table, and the deployment model (references/workflows/database-review.md §6).
An index built on a new, empty table is harmless; the same statement on a 100-million-row table is
an outage. Checks for a table created in the same file are skipped. The dialect comes from
--dialect, else from hints in the file (engine-specific syntax, ORM dialect imports), else from the
repository's database config or driver dependencies; PostgreSQL-only checks also run in generic mode.

Usage:
  migration_lint.py PATH [--files F ...] [--dialect auto|postgresql|mysql|generic]
                         [--git-base REF] [--fail-on high|medium] [--json]

  --git-base REF   also report migration files modified, renamed or deleted since REF
                   (editing an applied migration forks environments — DATA-MIG-02)
  --fail-on LEVEL  exit 1 when a lead at LEVEL or above is found (for CI); default: always exit 0

Standard library only. Lines containing `migration_lint: ignore` are skipped.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import git, iter_files, read_text  # noqa: E402

MIGRATION_DIR_HINTS = ("database/migrations", "db/migrate", "db/migrations", "migrations",
                       "migration", "alembic/versions", "db/changelog", "prisma/migrations",
                       "sql/migrations", "schema/migrations")
SEVERITY_ORDER = {"high": 0, "medium": 1, "info": 2}
PG_ONLY = "postgresql"


@dataclass
class Lead:
    file: str
    line: int
    check: str
    severity: str
    rule: str
    message: str
    fix: str
    snippet: str


# --------------------------------------------------------------------------- helpers

def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def norm_ident(raw: str) -> str:
    return raw.strip().strip('`"[]').split(".")[-1].strip('`"[]').lower()


def strip_sql_comments(sql: str) -> str:
    """Blank out comments while keeping offsets (so line numbers stay right)."""
    out, i, n = list(sql), 0, len(sql)
    while i < n:
        c = sql[i]
        if c == "'":                                   # string literal
            j = i + 1
            while j < n and not (sql[j] == "'" and (j + 1 >= n or sql[j + 1] != "'")):
                j += 2 if sql[j] == "'" else 1
            i = j + 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def split_sql(sql: str) -> list[tuple[int, str]]:
    """Split into (offset, statement) pairs on top-level semicolons; dollar quotes respected."""
    text = strip_sql_comments(sql)
    stmts, start, i, n = [], 0, 0, len(text)
    while i < n:
        c = text[i]
        if c == "'":
            j = i + 1
            while j < n and text[j] != "'":
                j += 1
            i = j + 1
            continue
        if c == "$":
            m = re.match(r"\$[A-Za-z_]*\$", text[i:])
            if m:
                tag = m.group(0)
                end = text.find(tag, i + len(tag))
                i = n if end == -1 else end + len(tag)
                continue
        if c == ";":
            stmts.append((start, text[start:i]))
            start = i + 1
        i += 1
    if text[start:].strip():
        stmts.append((start, text[start:]))
    return [(off + (len(s) - len(s.lstrip())), s.strip()) for off, s in stmts if s.strip()]


def split_actions(body: str) -> list[str]:
    """Split the action list of ALTER TABLE on top-level commas."""
    parts, depth, cur, quote = [], 0, [], None
    for ch in body:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"`":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def is_mysql_change_rename(action: str) -> bool:
    """MySQL `CHANGE [COLUMN] old new type` renames when old and new differ."""
    m = re.match(r"(?i)^CHANGE\s+(?:COLUMN\s+)?(\S+)\s+(\S+)", action)
    return bool(m) and m.group(1).strip('`"').lower() != m.group(2).strip('`"').lower()


def detect_dialect_from_text(text: str) -> str | None:
    pg = len(re.findall(r"(?i)\bCONCURRENTLY\b|\bJSONB\b|\bBIG?SERIAL\b|::\w|\bTIMESTAMPTZ\b|"
                        r"\bCREATE\s+EXTENSION\b|\bUSING\s+(?:GIN|GIST|BRIN)\b|\$\$|\bILIKE\b", text))
    my = len(re.findall(r"(?i)\bENGINE\s*=|\bAUTO_INCREMENT\b|`\w+`|\bUNSIGNED\b|\bTINYINT\b|"
                        r"\bDEFAULT\s+CHARSET\b|\bALGORITHM\s*=", text))
    if pg > my:
        return "postgresql"
    if my > pg:
        return "mysql"
    return None


def detect_dialect_from_framework(text: str) -> str | None:
    """Dialect hints inside ORM migrations (Alembic, Django, Rails, Laravel)."""
    pg = len(re.findall(r"dialects\s+import\s+postgresql|dialects\.postgresql|\bpostgresql_\w+\s*=|\bpostgresql\.(?:UUID|JSONB|ARRAY|ENUM)|"
                        r"django\.contrib\.postgres|\benable_extension\b|\bjsonb\b|algorithm:\s*:concurrently", text))
    my = len(re.findall(r"dialects\s+import\s+mysql|dialects\.mysql|\bmysql_\w+\s*=|\bmysql\.(?:TINYINT|ENUM|SET)|"
                        r"options:\s*['\"]ENGINE|->engine\s*=|->charset\s*=", text))
    if pg > my:
        return "postgresql"
    if my > pg:
        return "mysql"
    return None


def detect_repo_dialect(root: Path) -> tuple[str | None, str]:
    candidates = [".env.example", ".env", "config/database.yml", "config/database.php",
                  "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
                  "alembic.ini", "prisma/schema.prisma", "src/main/resources/application.properties",
                  "src/main/resources/application.yml", "src/main/resources/application.yaml"]
    candidates += [str(p.relative_to(root)) for p in list(root.glob("*/settings.py"))[:5]]
    pg_rx = re.compile(r"(?i)postgres|pgsql|jdbc:postgresql|backends\.postgresql|provider\s*=\s*\"postgresql\"")
    my_rx = re.compile(r"(?i)\bmysql\b|mariadb|jdbc:mysql|backends\.mysql|provider\s*=\s*\"mysql\"")
    for rel in candidates:
        p = root / rel
        if not p.is_file():
            continue
        text = read_text(p, limit=200_000)
        has_pg, has_my = bool(pg_rx.search(text)), bool(my_rx.search(text))
        if has_pg != has_my:
            return ("postgresql" if has_pg else "mysql"), rel
    # Database drivers in dependency manifests
    manifests = ["requirements.txt", "requirements/base.txt", "requirements/prod.txt", "pyproject.toml", "Pipfile",
                 "Gemfile", "package.json", "go.mod", "composer.json", "pom.xml", "build.gradle", "build.gradle.kts"]
    manifests += [str(p.relative_to(root)) for p in sorted(root.glob("requirements*.txt"))[:5]]
    drv_pg = re.compile(r"(?i)\bpsycopg2?\b|\basyncpg\b|\bpg8000\b|['\"]pg['\"]|gem\s+['\"]pg['\"]|lib/pq\b|jackc/pgx|"
                        r"org\.postgresql|\bpostgresql\b|doctrine.*pgsql")
    drv_my = re.compile(r"(?i)\bmysqlclient\b|\bpymysql\b|mysql-connector|\baiomysql\b|['\"]mysql2?['\"]|"
                        r"gem\s+['\"]mysql2['\"]|go-sql-driver/mysql|com\.mysql|mariadb")
    for rel in manifests:
        p = root / rel
        if not p.is_file():
            continue
        text = read_text(p, limit=200_000)
        has_pg, has_my = bool(drv_pg.search(text)), bool(drv_my.search(text))
        if has_pg != has_my:
            return ("postgresql" if has_pg else "mysql"), rel
    return None, ""


# --------------------------------------------------------------------------- SQL checks

CREATE_TABLE_RX = re.compile(r"(?is)^CREATE\s+(?:UNLOGGED\s+|TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\w.\[\]]+)")
ALTER_TABLE_RX = re.compile(r"(?is)^ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?([`\"\w.\[\]]+)\s+(.*)$")
CREATE_INDEX_RX = re.compile(r"(?is)^CREATE\s+(UNIQUE\s+)?INDEX\s+(CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?(?:[`\"\w.]+\s+)?ON\s+(?:ONLY\s+)?([`\"\w.\[\]]+)")
VOLATILE_CALL_RX = re.compile(r"(?i)\b(?:random|gen_random_uuid|uuid_generate_v[14]|clock_timestamp|timeofday|nextval)\b")
VOLATILE_DEFAULT_RX = re.compile(r"(?i)\bDEFAULT\s+(?:random|gen_random_uuid|uuid_generate_v[14]|clock_timestamp|timeofday|nextval)\s*\(")
IDENTITY_RX = re.compile(r"(?i)\b(?:SMALL|BIG)?SERIAL\b|\bGENERATED\s+(?:ALWAYS|BY\s+DEFAULT)\s+AS\s+(?:IDENTITY|\()")


def sql_leads(sql: str, dialect: str, base_line: int = 1, in_framework_txn: bool | None = None) -> list[tuple[int, str, str, str, str, str, str]]:
    """Return (line, check, severity, rule, message, fix, snippet) for SQL text.

    in_framework_txn: True when a framework wraps the migration in a transaction, False when it is
    known not to, None when unknown (plain SQL files: decided from BEGIN/statement count)."""
    out = []
    stmts = split_sql(sql)
    new_tables = set()
    for _, st in stmts:
        m = CREATE_TABLE_RX.match(st)
        if m:
            new_tables.add(norm_ident(m.group(1)))
    upper_all = sql.upper()
    explicit_txn = bool(re.search(r"(?im)^\s*(?:BEGIN|START\s+TRANSACTION)\s*;?\s*$", sql))
    has_lock_timeout = "LOCK_TIMEOUT" in upper_all
    validated_check_seen = False
    ddl_on_existing = None
    pg = dialect in (PG_ONLY, "generic")
    pg_note = "" if dialect == PG_ONLY else " (PostgreSQL)"

    def add(off, check, sev, rule, msg, fix, stmt):
        snippet = " ".join(stmt.split())[:140]
        out.append((base_line + line_of(sql, off) - 1, check, sev, rule, msg, fix, snippet))

    for off, st in stmts:
        up = " ".join(st.upper().split())
        if "MIGRATION_LINT: IGNORE" in up:
            continue
        # ---- CREATE INDEX
        m = CREATE_INDEX_RX.match(st)
        if m:
            table = norm_ident(m.group(3))
            concurrent = bool(m.group(2))
            if concurrent:
                if explicit_txn or in_framework_txn:
                    add(off, "concurrent-index-in-transaction", "high", "DATA-MIG-03",
                        "CREATE INDEX CONCURRENTLY cannot run inside a transaction block — this migration runs in one",
                        "Put the statement in its own migration that runs without a transaction (see languages/sql.md for each framework)", st)
                elif in_framework_txn is None and len(stmts) > 1:
                    add(off, "concurrent-index-with-other-statements", "medium", "DATA-MIG-03",
                        "CONCURRENTLY in a file with other statements; most runners wrap a file in one transaction",
                        "Keep the concurrent build alone in a migration configured to run without a transaction", st)
            elif pg and table not in new_tables:
                ddl_on_existing = ddl_on_existing or off
                add(off, "index-not-concurrent", "high" if dialect == PG_ONLY else "medium", "DATA-MIG-01",
                    f"CREATE INDEX on existing table '{table}' blocks writes for the whole build{pg_note}",
                    "Use CREATE INDEX CONCURRENTLY outside a transaction; drop an invalid index from a failed build before retrying", st)
            continue
        if re.match(r"(?i)^REINDEX\b", st) and "CONCURRENTLY" not in up and pg:
            add(off, "reindex-not-concurrent", "medium", "DATA-MIG-01",
                f"REINDEX without CONCURRENTLY locks the table{pg_note}", "REINDEX ... CONCURRENTLY (PostgreSQL 12+)", st)
            continue
        if re.match(r"(?i)^(?:VACUUM\s+FULL|CLUSTER)\b", st) and pg:
            add(off, "table-rewrite-maintenance", "high", "DATA-MIG-01",
                "VACUUM FULL / CLUSTER rewrites the table under an ACCESS EXCLUSIVE lock",
                "Run outside migrations in a maintenance window, or use pg_repack", st)
            continue
        # ---- destructive / data statements
        if re.match(r"(?i)^DROP\s+TABLE\b", st):
            add(off, "drop-table", "high", "DATA-MIG-01",
                "DROP TABLE is irreversible and breaks any deployed code that still reads the table",
                "Stop reading and writing it in code first, wait a release, take and verify a backup (DATA-BACKUP-01), then drop", st)
            continue
        if re.match(r"(?i)^TRUNCATE\b", st):
            add(off, "truncate", "high", "DATA-BACKUP-01", "TRUNCATE deletes all rows irreversibly",
                "Confirm intent; back up first; never in a routine migration", st)
            continue
        if re.match(r"(?i)^LOCK\s+TABLE\b", st):
            add(off, "explicit-lock", "medium", "DATA-MIG-03", "Explicit LOCK TABLE in a migration blocks traffic",
                "Avoid, or keep the locked section tiny and set lock_timeout", st)
            continue
        if re.match(r"(?i)^RENAME\s+TABLE\b", st):
            add(off, "rename", "high", "DATA-MIG-01", "Renaming a table breaks the code still deployed during the rollout",
                "Expand/contract: new table or view, migrate readers and writers, drop the old name later", st)
            continue
        dm = re.match(r"(?is)^(UPDATE|DELETE\s+FROM|INSERT\s+INTO\s+[`\"\w.]+\s*(?:\([^)]*\))?\s*SELECT)\b", st)
        if dm:
            unbounded = dm.group(1).upper().startswith(("UPDATE", "DELETE")) and not re.search(r"(?i)\bWHERE\b", st)
            add(off, "data-change-in-migration", "high" if unbounded else "medium", "DATA-MIG-02",
                ("Unbounded " if unbounded else "") + "data change inside a schema migration: it runs in the migration's transaction, holds row locks and cannot resume",
                "Move backfills to a separate, batched, idempotent and resumable job (DATA-BATCH-01)", st)
            continue
        # ---- ALTER TABLE
        m = ALTER_TABLE_RX.match(st)
        if not m:
            continue
        table, body = norm_ident(m.group(1)), m.group(2)
        new = table in new_tables
        if not new:
            ddl_on_existing = ddl_on_existing or off
        if re.match(r"(?i)^RENAME\s+TO\b", body.strip()):
            add(off, "rename", "high", "DATA-MIG-01", f"Renaming table '{table}' breaks the code still deployed during the rollout",
                "Expand/contract: new table or view, migrate readers and writers, drop the old name later", st)
            continue
        if dialect == "mysql" and not new and not re.search(r"(?i)\bALGORITHM\s*=", body):
            add(off, "mysql-online-ddl-unspecified", "info", "DATA-MIG-03",
                "ALTER TABLE without ALGORITHM/LOCK: MySQL silently falls back to copying or locking when the change can't be done online",
                "Add ALGORITHM=INSTANT or INPLACE and LOCK=NONE so the statement fails instead; for large tables consider gh-ost or pt-online-schema-change", st)
        for action in split_actions(body):
            a = " ".join(action.split())
            au = a.upper()
            if new:
                continue
            if re.match(r"(?i)^RENAME\s+(?:COLUMN\s+)?\S+\s+TO\b", a) or is_mysql_change_rename(a):
                add(off, "rename", "high", "DATA-MIG-01", f"Renaming a column of '{table}' breaks the code still deployed during the rollout",
                    "Expand/contract: add the new column, dual-write, backfill, switch reads, drop the old column later", st)
                continue
            if re.match(r"(?i)^DROP\s+(?:COLUMN\s+)?(?!CONSTRAINT|INDEX|KEY|PRIMARY|FOREIGN|DEFAULT|NOT\s+NULL)\S+", a):
                add(off, "drop-column", "high", "DATA-MIG-01", f"Dropping a column of '{table}' is irreversible and breaks deployed readers",
                    "Stop reading and writing it in code first, wait a release, back up, then drop", st)
                continue
            if re.match(r"(?i)^ADD\s+(?:COLUMN\s+)?(?!CONSTRAINT|INDEX|KEY|UNIQUE|PRIMARY|FOREIGN|CHECK)", a):
                if " NOT NULL" in f" {au}" and "DEFAULT" not in au and not IDENTITY_RX.search(a):
                    add(off, "add-not-null-without-default", "high", "DATA-MIG-01",
                        f"Adding a NOT NULL column without a default to '{table}' fails on a non-empty table (PostgreSQL) or fills implicit values (MySQL)",
                        "Add the column nullable (or with a constant default), backfill in batches, then add the constraint", st)
                if pg and (VOLATILE_DEFAULT_RX.search(a) or IDENTITY_RX.search(a)):
                    add(off, "add-column-rewrite", "high" if dialect == PG_ONLY else "medium", "DATA-MIG-01",
                        f"Adding a column with a volatile default, identity, serial or stored generated value rewrites '{table}' under an exclusive lock{pg_note}",
                        "Add a nullable column (or constant default), backfill in batches, then set the default for new rows", st)
                continue
            if re.match(r"(?i)^ALTER\s+(?:COLUMN\s+)?\S+\s+(?:SET\s+DATA\s+)?TYPE\b", a) or re.match(r"(?i)^MODIFY\s+(?:COLUMN\s+)?\S+", a) or \
                    re.match(r"(?i)^CHANGE\s+(?:COLUMN\s+)?\S+\s+\S+", a):
                add(off, "alter-column-type", "high" if dialect != "mysql" else "medium", "DATA-MIG-01",
                    f"Changing a column definition of '{table}' usually rewrites the table under an exclusive lock (binary-compatible widenings excepted)",
                    "Expand/contract: new column, dual write, batched backfill, switch reads, drop the old column; on MySQL state ALGORITHM/LOCK", st)
                continue
            if re.match(r"(?i)^ALTER\s+(?:COLUMN\s+)?\S+\s+SET\s+NOT\s+NULL\b", a) and pg:
                sev = "info" if validated_check_seen else ("high" if dialect == PG_ONLY else "medium")
                add(off, "set-not-null", sev, "DATA-MIG-01",
                    f"SET NOT NULL scans all of '{table}' under an ACCESS EXCLUSIVE lock{pg_note}" +
                    (" — a validated CHECK constraint earlier in this file may let PostgreSQL 12+ skip the scan" if validated_check_seen else ""),
                    "ADD CONSTRAINT ... CHECK (col IS NOT NULL) NOT VALID; VALIDATE CONSTRAINT; then SET NOT NULL (PostgreSQL 12+ skips the scan)", st)
                continue
            if re.match(r"(?i)^VALIDATE\s+CONSTRAINT\b", a):
                validated_check_seen = True
                continue
            if re.match(r"(?i)^ADD\s+(?:CONSTRAINT\s+\S+\s+)?(?:FOREIGN\s+KEY|CHECK)\b", a) and pg and "NOT VALID" not in au:
                add(off, "constraint-validated-under-lock", "medium", "DATA-MIG-01",
                    f"Adding a foreign key or check constraint to '{table}' validates every row while holding locks{pg_note}",
                    "ADD ... NOT VALID first, then VALIDATE CONSTRAINT in a separate step", st)
                continue
            if re.match(r"(?i)^ADD\s+(?:CONSTRAINT\s+\S+\s+)?(?:UNIQUE|PRIMARY\s+KEY)\b", a) and pg and "USING INDEX" not in au:
                add(off, "unique-constraint-builds-index", "medium", "DATA-MIG-01",
                    f"Adding a UNIQUE or PRIMARY KEY constraint to '{table}' builds an index while blocking writes{pg_note}",
                    "CREATE UNIQUE INDEX CONCURRENTLY, then ADD CONSTRAINT ... USING INDEX", st)
                continue
    if pg and ddl_on_existing is not None and not has_lock_timeout:
        out.append((base_line + line_of(sql, ddl_on_existing) - 1, "no-lock-timeout", "info", "DATA-MIG-03",
                    "DDL on existing tables without lock_timeout: a migration waiting for a lock queues all later queries behind it",
                    "SET lock_timeout (e.g. '5s') before the DDL and retry the migration on timeout", ""))
    return out


# --------------------------------------------------------------------------- framework checks

def section(text: str, start_rx: str, stop_rx: str | None) -> tuple[int, str]:
    m = re.search(start_rx, text)
    if not m:
        return 0, ""
    stop = re.search(stop_rx, text[m.end():]) if stop_rx else None
    end = m.end() + stop.start() if stop else len(text)
    return m.start(), text[m.start():end]


def string_literals(code: str) -> list[tuple[int, str]]:
    lits = []
    for m in re.finditer(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"|<<~?['\"]?(\w+)['\"]?\n(.*?)\n\s*\3", code, re.S):
        val = m.group(1) if m.group(1) is not None else m.group(2) if m.group(2) is not None else m.group(4)
        if val and re.search(r"(?i)\b(?:ALTER|CREATE|DROP|UPDATE|DELETE|INSERT|TRUNCATE|RENAME|LOCK|REINDEX)\b", val):
            lits.append((m.start(), val))
    return lits


def framework_sql(text: str, region_off: int, region: str, dialect: str, txn: bool | None, rel: str) -> list[Lead]:
    leads = []
    for pos, lit in string_literals(region):
        base = line_of(text, region_off + pos)
        for ln, check, sev, rule, msg, fix, snip in sql_leads(lit, dialect, base, txn):
            if check == "no-lock-timeout":
                continue
            leads.append(Lead(rel, ln, check, sev, rule, msg + " [raw SQL]", fix, snip))
    return leads


LARAVEL_COLUMN_TYPES = ("string|integer|bigInteger|smallInteger|tinyInteger|mediumInteger|unsignedInteger|unsignedBigInteger|"
                        "boolean|text|mediumText|longText|decimal|float|double|date|dateTime|dateTimeTz|time|timestamp|"
                        "timestampTz|year|json|jsonb|uuid|ulid|char|enum|set|binary|foreignId|foreignUuid|ipAddress|macAddress")


def laravel_leads(text: str, rel: str, dialect: str) -> list[Lead]:
    leads: list[Lead] = []
    off, up = section(text, r"function\s+up\s*\(", r"function\s+down\s*\(")
    if not up:
        return leads
    pg = dialect in (PG_ONLY, "generic")
    no_txn = bool(re.search(r"\$withinTransaction\s*=\s*false", text))

    def add(pos, check, sev, rule, msg, fix):
        ln = line_of(text, off + pos)
        line = text.splitlines()[ln - 1] if ln - 1 < len(text.splitlines()) else ""
        if "migration_lint: ignore" not in line:
            leads.append(Lead(rel, ln, check, sev, rule, msg, fix, line.strip()[:140]))

    for blk in re.finditer(r"Schema::table\(\s*['\"](\w+)['\"]\s*,\s*function\s*\([^)]*\)\s*(?:use\s*\([^)]*\)\s*)?\{(.*?)\n\s*\}\s*\)", up, re.S):
        table, body, boff = blk.group(1), blk.group(2), blk.start(2)
        for stmt in re.finditer(r"\$table->(.*?);", body, re.S):
            s, spos = stmt.group(1), boff + stmt.start()
            if re.match(r"(?:dropColumn|dropColumns|dropMorphs|dropTimestamps|dropSoftDeletes|dropRememberToken)\b", s):
                add(spos, "drop-column", "high", "DATA-MIG-01", f"Dropping columns of '{table}' is irreversible and breaks deployed readers",
                    "Stop using the column in code first, wait a release, back up, then drop")
            elif s.startswith("renameColumn"):
                add(spos, "rename", "high", "DATA-MIG-01", f"Renaming a column of '{table}' breaks the code still deployed during the rollout",
                    "Expand/contract: add, dual-write, backfill, switch reads, drop later")
            elif "->change()" in s:
                add(spos, "alter-column-type", "high", "DATA-MIG-01", f"->change() redefines a column of '{table}': often a table rewrite under lock",
                    "Expand/contract with a new column, or confirm the change is metadata-only on your engine and version")
            elif re.match(rf"(?:{LARAVEL_COLUMN_TYPES})\s*\(", s):
                if "->nullable(" not in s and "->default(" not in s and "->useCurrent" not in s and "storedAs" not in s and "virtualAs" not in s:
                    add(spos, "add-not-null-without-default", "high", "DATA-MIG-01",
                        f"New column on existing table '{table}' is NOT NULL (Laravel's default) without a default: fails on a non-empty PostgreSQL table, implicit values on MySQL",
                        "Make it ->nullable() (or give a constant ->default()), backfill in batches, then tighten in a later migration")
                if re.search(r"->(?:unique|index|primary)\(|->constrained\(", s) and pg:
                    add(spos, "index-not-concurrent", "medium", "DATA-MIG-01",
                        f"Index or foreign key on existing table '{table}' is built without CONCURRENTLY / NOT VALID (PostgreSQL)",
                        "For large tables: DB::statement('CREATE INDEX CONCURRENTLY …') in a migration with $withinTransaction = false")
            elif re.match(r"(?:index|unique|primary|spatialIndex|fullText|foreign)\s*\(", s) and pg:
                add(spos, "index-not-concurrent", "medium", "DATA-MIG-01",
                    f"Index or foreign key on existing table '{table}' is built without CONCURRENTLY / NOT VALID (PostgreSQL)",
                    "For large tables: DB::statement('CREATE INDEX CONCURRENTLY …') in a migration with $withinTransaction = false")
    for m in re.finditer(r"Schema::(?:drop|dropIfExists)\(", up):
        add(m.start(), "drop-table", "high", "DATA-MIG-01", "Dropping a table in up() is irreversible and breaks deployed readers",
            "Stop using it in code first, wait a release, back up, then drop")
    for m in re.finditer(r"Schema::rename\(", up):
        add(m.start(), "rename", "high", "DATA-MIG-01", "Renaming a table breaks the code still deployed during the rollout",
            "Expand/contract with a new table or a view")
    for m in re.finditer(r"DB::table\([^)]*\)(?:->\w+\([^;]*?\))*->(?:update|delete|insert|upsert|increment|decrement)\(|->(?:chunk|chunkById|each|lazy)\(", up):
        add(m.start(), "data-change-in-migration", "medium", "DATA-MIG-02",
            "Data change inside a schema migration (runs in the migration transaction; not resumable)",
            "Move the backfill to a queued, chunked, idempotent job (DATA-BATCH-01)")
    for m in re.finditer(r"(?m)^use\s+App\\Models\\|\bApp\\Models\\\w+::", text):
        add(m.start() - off, "app-model-in-migration", "medium", "DATA-MIG-02",
            "Migration depends on an application model that will change after this migration was written",
            "Use the query builder (DB::table) and snapshot the logic inside the migration")
    leads += framework_sql(text, off, up, dialect, False if no_txn else (True if pg else None), rel)
    if not re.search(r"function\s+down\s*\(", text):
        leads.append(Lead(rel, line_of(text, off), "no-down", "info", "DATA-MIG-03", "No down() method",
                          "Write a down() or document the roll-forward in the migration plan", ""))
    return leads


def rails_leads(text: str, rel: str, dialect: str) -> list[Lead]:
    leads: list[Lead] = []
    off, body = section(text, r"def\s+(?:change|up)\b", r"\n\s*def\s+down\b")
    if not body:
        return leads
    pg = dialect in (PG_ONLY, "generic")
    no_txn = "disable_ddl_transaction!" in text
    new_tables = set(re.findall(r"create_table\s+[:'\"](\w+)", body))

    def add(pos, check, sev, rule, msg, fix):
        ln = line_of(text, off + pos)
        line = text.splitlines()[ln - 1]
        if "migration_lint: ignore" not in line:
            leads.append(Lead(rel, ln, check, sev, rule, msg, fix, line.strip()[:140]))

    for m in re.finditer(r"(?m)^\s*(remove_column|remove_columns|remove_reference|drop_table|rename_column|rename_table|change_column|change_column_null|add_column|add_index|add_foreign_key|add_reference)\s*\(?\s*[:'\"](\w+)(.*)$", body):
        op, table, rest = m.group(1), m.group(2), m.group(3)
        if table in new_tables:
            continue
        if op in ("remove_column", "remove_columns", "remove_reference"):
            add(m.start(), "drop-column", "high", "DATA-MIG-01", f"{op} on '{table}' is irreversible and breaks deployed readers",
                "Ignore the column in the model first (self.ignored_columns), deploy, then remove it; back up")
        elif op == "drop_table":
            add(m.start(), "drop-table", "high", "DATA-MIG-01", f"drop_table '{table}' is irreversible", "Stop using it first; back up; then drop")
        elif op in ("rename_column", "rename_table"):
            add(m.start(), "rename", "high", "DATA-MIG-01", f"{op} on '{table}' breaks the code still deployed during the rollout",
                "Expand/contract: add, dual-write, backfill, switch reads, remove later")
        elif op == "change_column":
            add(m.start(), "alter-column-type", "high", "DATA-MIG-01", f"change_column on '{table}' usually rewrites the table under lock",
                "Expand/contract with a new column")
        elif op == "change_column_null" and re.search(r",\s*false\b", rest) and pg:
            add(m.start(), "set-not-null", "high" if dialect == PG_ONLY else "medium", "DATA-MIG-01",
                f"change_column_null false on '{table}' scans the table under an exclusive lock (PostgreSQL)",
                "Add a CHECK ... NOT VALID constraint, validate it, then set NOT NULL")
        elif op == "add_column" and re.search(r"null:\s*false", rest) and "default:" not in rest:
            add(m.start(), "add-not-null-without-default", "high", "DATA-MIG-01",
                f"add_column null: false without a default on '{table}' fails on a non-empty table",
                "Add it nullable, backfill in batches, then change_column_null in a later migration")
        elif op == "add_index" and pg:
            if "algorithm: :concurrently" in rest:
                if not no_txn:
                    add(m.start(), "concurrent-index-in-transaction", "high", "DATA-MIG-03",
                        "algorithm: :concurrently needs disable_ddl_transaction! in this migration", "Add disable_ddl_transaction! to the class")
            else:
                add(m.start(), "index-not-concurrent", "medium", "DATA-MIG-01",
                    f"add_index on existing table '{table}' blocks writes during the build (PostgreSQL)",
                    "algorithm: :concurrently with disable_ddl_transaction!")
        elif op in ("add_foreign_key", "add_reference") and pg and "validate: false" not in rest and (op == "add_foreign_key" or "foreign_key: true" in rest):
            add(m.start(), "constraint-validated-under-lock", "medium", "DATA-MIG-01",
                f"Foreign key on '{table}' validates all rows under lock (PostgreSQL)", "validate: false, then validate_foreign_key in a later migration")
    for m in re.finditer(r"\.(?:update_all|delete_all|destroy_all|find_each|in_batches)\b|\b[A-Z]\w+\.(?:where|all|find|create|update)\b", body):
        add(m.start(), "data-change-in-migration", "medium", "DATA-MIG-02",
            "Model or data operation inside a migration (models change; the migration does not)",
            "Use a separate, batched, idempotent backfill task; avoid application models in migrations")
    leads += framework_sql(text, off, body, dialect, False if no_txn else (True if pg else None), rel)
    return leads


DJANGO_DROP = {"RemoveField": ("drop-column", "high"), "DeleteModel": ("drop-table", "high"),
               "RenameField": ("rename", "high"), "RenameModel": ("rename", "high"),
               "AlterField": ("alter-column-type", "medium")}


def django_leads(text: str, rel: str, dialect: str) -> list[Lead]:
    leads: list[Lead] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return leads
    pg = dialect in (PG_ONLY, "generic")
    atomic_false = bool(re.search(r"(?m)^\s*atomic\s*=\s*False", text))
    lines = text.splitlines()

    def add(node, check, sev, rule, msg, fix):
        ln = getattr(node, "lineno", 1)
        if "migration_lint: ignore" not in lines[ln - 1]:
            leads.append(Lead(rel, ln, check, sev, rule, msg, fix, lines[ln - 1].strip()[:140]))

    for node in ast.walk(tree):
        if isinstance(node, (ast.ImportFrom,)) and node.module and node.module.endswith(".models") and node.module != "django.db.models":
            add(node, "app-model-in-migration", "medium", "DATA-MIG-02", "Migration imports application models",
                "Use apps.get_model() inside RunPython")
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
            owner = node.func.value.id if isinstance(node.func.value, ast.Name) else "?"
        elif isinstance(node.func, ast.Name):
            name, owner = node.func.id, ""
        else:
            continue
        if owner not in ("migrations", "operations", ""):
            continue
        if owner == "":
            owner = "migrations" if name in DJANGO_DROP or name in ("AddField", "AddIndex", "AddConstraint", "RunPython", "RunSQL") else ""

        if name in DJANGO_DROP and owner == "migrations":
            check, sev = DJANGO_DROP[name]
            add(node, check, sev, "DATA-MIG-01", f"migrations.{name}: " + {
                "drop-column": "irreversible; breaks deployed readers", "drop-table": "irreversible; breaks deployed readers",
                "rename": "breaks the code still deployed during the rollout",
                "alter-column-type": "may rewrite or scan the table under lock (type, null or constraint change)"}[check],
                "Expand/contract across releases; back up before irreversible steps")
        elif name == "AddField" and owner == "migrations":
            field = next((k.value for k in node.keywords if k.arg == "field"), None)
            if isinstance(field, ast.Call):
                kws = {k.arg: k.value for k in field.keywords}
                null_true = isinstance(kws.get("null"), ast.Constant) and kws["null"].value is True
                if not null_true and "default" not in kws and "db_default" not in kws:
                    add(node, "add-not-null-without-default", "high", "DATA-MIG-01",
                        "AddField without null=True or a default adds a NOT NULL column without a default",
                        "Add null=True (or a constant default), backfill in batches, then AlterField to NOT NULL")
                fname = field.func.attr if isinstance(field.func, ast.Attribute) else ""
                if pg and fname in ("ForeignKey", "OneToOneField") and not (isinstance(kws.get("db_constraint"), ast.Constant) and kws["db_constraint"].value is False):
                    add(node, "constraint-validated-under-lock", "medium", "DATA-MIG-01",
                        "AddField with a ForeignKey adds a validated constraint and a non-concurrent index (PostgreSQL)",
                        "For large tables: add the column without the constraint, build the index concurrently, add the constraint NOT VALID and validate it (RunSQL)")
        elif name in ("AddIndex", "AddConstraint") and owner == "migrations" and pg:
            add(node, "index-not-concurrent", "medium", "DATA-MIG-01", f"migrations.{name} builds without CONCURRENTLY (PostgreSQL)",
                "AddIndexConcurrently / AddConstraintNotValid from django.contrib.postgres.operations, with atomic = False")
        elif name == "AddIndexConcurrently" and not atomic_false:
            add(node, "concurrent-index-in-transaction", "high", "DATA-MIG-03", "AddIndexConcurrently in an atomic migration fails",
                "Set atomic = False on the Migration class")
        elif name == "RunPython" and owner == "migrations":
            add(node, "data-change-in-migration", "medium", "DATA-MIG-02", "RunPython data migration (runs in the migration transaction by default)",
                "Keep it batched, idempotent and reversible, or move large backfills to a management command or job")
        elif name == "RunSQL" and owner == "migrations":
            sql_arg = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "sql"), None)
            parts = sql_arg.elts if isinstance(sql_arg, (ast.List, ast.Tuple)) else [sql_arg]
            for arg in parts:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    for ln, check, sev, rule, msg, fix, snip in sql_leads(arg.value, dialect, arg.lineno, False if atomic_false else (True if pg else None)):
                        if check != "no-lock-timeout":
                            leads.append(Lead(rel, ln, check, sev, rule, msg + " [RunSQL]", fix, snip))
    return leads


def alembic_leads(text: str, rel: str, dialect: str) -> list[Lead]:
    leads: list[Lead] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return leads
    up = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade"), None)
    if up is None:
        return leads
    pg = dialect in (PG_ONLY, "generic")
    lines = text.splitlines()
    autocommit = "autocommit_block" in ast.get_source_segment(text, up) if hasattr(ast, "get_source_segment") else "autocommit_block" in text
    new_tables = set()
    for node in ast.walk(up):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "create_table" and node.args \
                and isinstance(node.args[0], ast.Constant):
            new_tables.add(str(node.args[0].value))

    def add(node, check, sev, rule, msg, fix):
        ln = node.lineno
        if "migration_lint: ignore" not in lines[ln - 1]:
            leads.append(Lead(rel, ln, check, sev, rule, msg, fix, lines[ln - 1].strip()[:140]))

    for node in ast.walk(up):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        name = node.func.attr
        kws = {k.arg: k.value for k in node.keywords}
        first = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else None
        target_tbl = node.args[1].value if name == "create_index" and len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else first
        if target_tbl in new_tables and name != "execute":
            continue
        if name in ("drop_column", "drop_table"):
            add(node, "drop-column" if name == "drop_column" else "drop-table", "high", "DATA-MIG-01",
                f"op.{name} is irreversible and breaks deployed readers", "Stop using it in code first, wait a release, back up, then drop")
        elif name == "alter_column":
            if "new_column_name" in kws:
                add(node, "rename", "high", "DATA-MIG-01", "op.alter_column(new_column_name=…) breaks the code still deployed",
                    "Expand/contract: add, dual-write, backfill, switch reads, drop later")
            if "type_" in kws:
                add(node, "alter-column-type", "high", "DATA-MIG-01", "op.alter_column(type_=…) usually rewrites the table under lock",
                    "Expand/contract with a new column")
            if isinstance(kws.get("nullable"), ast.Constant) and kws["nullable"].value is False and pg:
                add(node, "set-not-null", "high" if dialect == PG_ONLY else "medium", "DATA-MIG-01",
                    "op.alter_column(nullable=False) scans the table under an exclusive lock (PostgreSQL)",
                    "CHECK (col IS NOT NULL) NOT VALID, VALIDATE, then SET NOT NULL")
        elif name == "add_column":
            col = node.args[1] if len(node.args) > 1 else None
            if isinstance(col, ast.Call):
                ckw = {k.arg: k.value for k in col.keywords}
                if isinstance(ckw.get("nullable"), ast.Constant) and ckw["nullable"].value is False and "server_default" not in ckw:
                    add(node, "add-not-null-without-default", "high", "DATA-MIG-01",
                        "op.add_column with nullable=False and no server_default fails on a non-empty table",
                        "Add nullable, backfill in batches, then alter_column(nullable=False)")
                default_src = (ast.get_source_segment(text, ckw["server_default"]) or "") if "server_default" in ckw else ""
                identity = any(isinstance(a, ast.Call) and getattr(a.func, "attr", getattr(a.func, "id", "")) in ("Identity", "Sequence")
                               for a in col.args)
                if pg and (VOLATILE_CALL_RX.search(default_src) or identity):
                    add(node, "add-column-rewrite", "high" if dialect == PG_ONLY else "medium", "DATA-MIG-01",
                        "op.add_column with a volatile server_default (or identity/sequence) rewrites the whole table under an "
                        "ACCESS EXCLUSIVE lock (PostgreSQL; constant and now() defaults are fast since 11)",
                        "Add it nullable without the volatile default, set the default for new rows, backfill in batches, then enforce NOT NULL")
        elif name == "create_index" and pg:
            conc = isinstance(kws.get("postgresql_concurrently"), ast.Constant) and kws["postgresql_concurrently"].value is True
            if not conc:
                add(node, "index-not-concurrent", "medium", "DATA-MIG-01", "op.create_index blocks writes during the build (PostgreSQL)",
                    "postgresql_concurrently=True inside op.get_context().autocommit_block()")
            elif not autocommit:
                add(node, "concurrent-index-in-transaction", "high", "DATA-MIG-03",
                    "postgresql_concurrently=True outside an autocommit block runs inside the migration transaction",
                    "Wrap it in `with op.get_context().autocommit_block():`")
        elif name in ("create_unique_constraint", "create_primary_key") and pg:
            add(node, "unique-constraint-builds-index", "medium", "DATA-MIG-01",
                f"op.{name} builds a unique index while blocking writes (PostgreSQL)",
                "CREATE UNIQUE INDEX CONCURRENTLY in an autocommit block, then ADD CONSTRAINT ... USING INDEX")
        elif name in ("create_foreign_key", "create_check_constraint") and pg and not (isinstance(kws.get("postgresql_not_valid"), ast.Constant) and kws["postgresql_not_valid"].value):
            add(node, "constraint-validated-under-lock", "medium", "DATA-MIG-01", f"op.{name} validates every row under lock (PostgreSQL)",
                "Add it NOT VALID (RunSQL / postgresql_not_valid) and validate separately")
        elif name == "execute" and first and isinstance(first, str):
            for ln, check, sev, rule, msg, fix, snip in sql_leads(first, dialect, node.args[0].lineno, None if autocommit else (True if pg else None)):
                if check != "no-lock-timeout":
                    leads.append(Lead(rel, ln, check, sev, rule, msg + " [op.execute]", fix, snip))
        elif name in ("bulk_insert",):
            add(node, "data-change-in-migration", "medium", "DATA-MIG-02", "Data written inside a schema migration",
                "Keep data loads small and idempotent; move backfills to a batched job")
    return leads


# --------------------------------------------------------------------------- whole-file checks

LOCK_CHECKS = {"add-column-rewrite", "index-not-concurrent", "unique-constraint-builds-index", "constraint-validated-under-lock",
               "set-not-null", "alter-column-type", "rename", "drop-column", "drop-table", "table-rewrite-maintenance",
               "explicit-lock", "add-not-null-without-default"}
SLOW_CHECKS = {"add-column-rewrite", "index-not-concurrent", "unique-constraint-builds-index", "constraint-validated-under-lock",
               "set-not-null", "alter-column-type", "data-change-in-migration", "table-rewrite-maintenance"}
NO_TXN_RX = re.compile(r"withinTransaction\s*=\s*false|\batomic\s*=\s*False|disable_ddl_transaction!|autocommit_block|"
                       r"executeInTransaction\s*=\s*false|^[ \t]*COMMIT\s*;", re.I | re.M)
ALEMBIC_DDL_OPS = {"add_column", "alter_column", "drop_column", "create_index", "drop_index", "create_foreign_key",
                   "create_unique_constraint", "create_check_constraint", "create_primary_key", "drop_constraint", "rename_table"}


def nearby_text(path: Path, names: tuple[str, ...]) -> str:
    """Text of framework config next to a migration (Alembic env.py sits one or two levels up)."""
    chunks = []
    for parent in (path.parent, path.parent.parent):
        for n in names:
            f = parent / n
            if f.is_file():
                chunks.append(read_text(f, limit=200_000))
    return "\n".join(chunks)


def alembic_ddl_line(text: str) -> int | None:
    """Line of the first DDL operation on a table this migration does not create."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    up = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade"), None)
    if up is None:
        return None
    created = {str(n.args[0].value) for n in ast.walk(up) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "create_table" and n.args and isinstance(n.args[0], ast.Constant)}
    lines = []
    for n in ast.walk(up):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ALEMBIC_DDL_OPS:
            args = [a.value for a in n.args if isinstance(a, ast.Constant)]
            table = args[1] if n.func.attr in ("create_index", "create_foreign_key", "create_unique_constraint",
                                               "create_check_constraint", "create_primary_key") and len(args) > 1 else (args[0] if args else None)
            if table not in created:
                lines.append(n.lineno)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "execute" and n.args \
                and isinstance(n.args[0], ast.Constant) and re.match(r"(?is)\s*ALTER\s+TABLE", str(n.args[0].value)):
            lines.append(n.lineno)
    return min(lines) if lines else None


def cross_step_leads(path: Path, text: str, kind: str, dialect: str, rel: str, file_leads: list[Lead]) -> list[Lead]:
    """Checks that need the whole migration: lock timeouts in ORM migrations, and slow steps sharing one transaction."""
    out: list[Lead] = []
    if dialect != PG_ONLY:
        return out
    config = nearby_text(path, ("env.py",)) if kind == "alembic" else ""
    if kind != "sql" and "lock_timeout" not in text and "lock_timeout" not in config:   # raw SQL: checked in sql_leads
        first = alembic_ddl_line(text) if kind == "alembic" else None
        if first is None:
            locking = sorted(l.line for l in file_leads if l.check in LOCK_CHECKS)
            first = locking[0] if locking else None
        if first is not None:
            out.append(Lead(rel, first, "no-lock-timeout", "info", "DATA-MIG-03",
                            "DDL on existing tables without lock_timeout: while the migration waits for its lock, every later query "
                            "on the table queues behind it",
                            "SET lock_timeout (e.g. '5s') for the migration session and retry the deploy step on timeout",
                            text.splitlines()[first - 1].strip()[:140]))
    slow = sorted((l for l in file_leads if l.check in SLOW_CHECKS), key=lambda l: l.line)
    slow_lines = sorted({l.line for l in slow})          # several actions of one ALTER statement count once
    if len(slow_lines) >= 2 and not NO_TXN_RX.search(text) and not NO_TXN_RX.search(config):
        out.append(Lead(rel, slow_lines[0], "locks-held-across-steps", "medium", "DATA-MIG-01",
                        f"{len(slow_lines)} slow, lock-taking steps (lines {', '.join(map(str, slow_lines))}) run in one transaction "
                        "(PostgreSQL DDL is transactional): each lock is held until COMMIT, so the table stays blocked for the sum "
                        "of their durations",
                        "One risky step per migration (or per autocommit block); keep each transaction short",
                        slow[0].snippet))
    return out


# --------------------------------------------------------------------------- discovery

def classify(path: Path, text: str) -> str | None:
    rel = path.as_posix().lower()
    if path.suffix.lower() == ".sql":
        return "sql" if ("migrat" in rel or "changelog" in rel or "/db/" in rel or "schema" in rel) else None
    if path.suffix == ".php" and "migrations" in rel and ("Schema::" in text or "extends Migration" in text):
        return "laravel"
    if path.suffix == ".rb" and "db/migrate" in rel:
        return "rails"
    if path.suffix == ".py" and "migrations" in rel or path.suffix == ".py" and "versions" in rel:
        if "migrations.Migration" in text:
            return "django"
        if "from alembic import op" in text or "alembic" in text and "def upgrade" in text:
            return "alembic"
    return None


def discover(root: Path, files: list[str] | None) -> list[Path]:
    if files:
        out = []
        for f in files:
            p = Path(f)
            if not p.is_absolute() and not p.exists() and (root / p).exists():
                p = root / p
            out.append(p.resolve())
        return out
    found = []
    for p in iter_files(root):
        rel = p.relative_to(root).as_posix().lower()
        if p.name == "__init__.py":
            continue
        if any(h in rel for h in MIGRATION_DIR_HINTS) or (p.suffix.lower() == ".sql" and "migrat" in rel):
            if p.suffix.lower() in (".sql", ".php", ".rb", ".py"):
                found.append(p)
    return sorted(found)


def git_changes(root: Path, base: str) -> list[tuple[str, str]]:
    out = git(root, "diff", "--name-status", "--find-renames", f"{base}...HEAD")
    if out is None:
        return []
    changes = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0][:1] in "MDR":
            path = parts[-1] if parts[0].startswith("R") else parts[1]
            old = parts[1]
            if any(h in old.lower() for h in MIGRATION_DIR_HINTS) or old.lower().endswith(".sql") and "migrat" in old.lower():
                changes.append((parts[0][:1], old if parts[0][:1] != "R" else f"{old} → {path}"))
    return changes


def scan(root: Path, files: list[str] | None, dialect_opt: str, git_base: str | None) -> dict:
    root = root.resolve()
    repo_dialect, source = (None, "")
    if dialect_opt == "auto":
        repo_dialect, source = detect_repo_dialect(root)
    leads: list[Lead] = []
    analysed, skipped = 0, []
    kinds: Counter = Counter()
    for path in discover(root, files):
        text = read_text(path, limit=2_000_000)
        if not text:
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        kind = classify(path, text)
        if kind is None:
            if path.suffix.lower() in (".xml", ".yaml", ".yml"):
                skipped.append(rel)
            continue
        if dialect_opt != "auto":
            dialect = dialect_opt
        else:
            hint = detect_dialect_from_text(text) if kind == "sql" else detect_dialect_from_framework(text)
            dialect = hint or repo_dialect or "generic"
        analysed += 1
        kinds[kind] += 1
        file_leads: list[Lead] = []
        if kind == "sql":
            for ln, check, sev, rule, msg, fix, snip in sql_leads(text, dialect, 1, None):
                file_leads.append(Lead(rel, ln, check, sev, rule, msg, fix, snip))
        elif kind == "laravel":
            file_leads += laravel_leads(text, rel, dialect)
        elif kind == "rails":
            file_leads += rails_leads(text, rel, dialect)
        elif kind == "django":
            file_leads += django_leads(text, rel, dialect)
        elif kind == "alembic":
            file_leads += alembic_leads(text, rel, dialect)
        leads += file_leads + cross_step_leads(path, text, kind, dialect, rel, file_leads)
    if git_base:
        for status, rel in git_changes(root, git_base):
            what = {"M": "modified", "D": "deleted", "R": "renamed"}[status]
            leads.append(Lead(rel, 1, "applied-migration-edited", "high", "DATA-MIG-02",
                              f"Migration file {what} since {git_base}: if it was already applied anywhere, environments now diverge",
                              "Revert the edit and add a new migration instead", ""))
    seen, unique = set(), []
    for l in leads:                      # one lead per file, line and check
        key = (l.file, l.line, l.check)
        if key not in seen:
            seen.add(key)
            unique.append(l)
    leads = sorted(unique, key=lambda l: (l.file, l.line, SEVERITY_ORDER[l.severity]))
    return {"root": str(root), "dialect_default": dialect_opt if dialect_opt != "auto" else (repo_dialect or "per file / generic"),
            "dialect_source": source, "files_analysed": analysed, "by_kind": dict(kinds),
            "not_analysed": skipped, "leads": [asdict(l) for l in leads]}


def to_markdown(res: dict) -> str:
    counts = Counter(l["severity"] for l in res["leads"])
    out = [f"# Migration leads: `{res['root']}`", "",
           "**These are LEADS, not verdicts.** Whether a statement is dangerous depends on the engine and "
           "version, the size and write rate of the table, and how you deploy (database-review.md §6). "
           "Confirm table sizes before calling anything an outage; no leads ≠ safe.", "",
           f"Files analysed: {res['files_analysed']} {res['by_kind'] or ''} · default dialect: {res['dialect_default']}"
           + (f" (from `{res['dialect_source']}`)" if res['dialect_source'] else "")
           + f" · leads: {counts.get('high', 0)} high, {counts.get('medium', 0)} medium, {counts.get('info', 0)} info", ""]
    if res["not_analysed"]:
        out += [f"Not analysed (Liquibase XML/YAML changelogs): {', '.join(res['not_analysed'][:10])}", ""]
    if not res["leads"]:
        out.append("No lead matched." if res["files_analysed"] else "No migration files found (try --files).")
    else:
        by_check = Counter((l["check"], l["severity"], l["rule"]) for l in res["leads"])
        out += ["| Check | Severity | Rule | Count |", "|---|---|---|---|"]
        for (check, sev, rule), n in sorted(by_check.items(), key=lambda kv: (SEVERITY_ORDER[kv[0][1]], -kv[1])):
            out.append(f"| {check} | {sev} | {rule} | {n} |")
    current = None
    for l in res["leads"]:
        if l["file"] != current:
            current = l["file"]
            out += ["", f"## `{current}`", ""]
        out.append(f"- **[{l['severity']}] line {l['line']} · {l['check']}** ({l['rule']}) — {l['message']}. "
                   f"*Safer:* {l['fix']}." + (f"  \n  `{l['snippet'].replace('`', 'ʼ')}`" if l["snippet"] else ""))
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="repository root (used for discovery and relative paths)")
    p.add_argument("--files", nargs="+", help="analyse only these migration files")
    p.add_argument("--dialect", choices=["auto", "postgresql", "mysql", "generic"], default="auto")
    p.add_argument("--git-base", help="report migration files modified/deleted/renamed since this ref")
    p.add_argument("--fail-on", choices=["high", "medium"], help="exit 1 if a lead at this level or above exists")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    res = scan(root, args.files, args.dialect, args.git_base)
    print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else to_markdown(res))
    if args.fail_on:
        limit = SEVERITY_ORDER[args.fail_on]
        if any(SEVERITY_ORDER[l["severity"]] <= limit for l in res["leads"]):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
