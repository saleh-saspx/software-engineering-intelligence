#!/usr/bin/env python3
"""Lead scanner for data types, keys and relationships in schema definitions (DATA-TYPE-01..05,
DATA-MODEL-02/03, DATA-KEY-01, DATA-SCHEMA-01, DATA-IDX-01).

Reads table definitions from SQL DDL (CREATE TABLE, ALTER TABLE, CREATE INDEX — PostgreSQL, MySQL and
MariaDB, Oracle, SQL Server, SQLite syntax), Laravel migrations, Django models, SQLAlchemy models,
Prisma schemas and JPA entities, and reports columns whose type does not fit what their name says
they hold — money in binary floats, decimals without scale, identifiers in numeric types, instants
without a time zone, ID lists in text columns — plus missing primary keys, foreign keys that are
missing or unindexed, polymorphic references and repeating groups.

Every hit is a LEAD (confidence: possible). Names are a heuristic: `rate` may be a ratio that needs no
fixed scale, `order_number` may truly be numeric in a legacy system, a `customer_id` without a
foreign key may point to another service on purpose. Severity depends on the engine: give --dialect,
or let the script take it from the repository's configuration (scripts/_db.py) or from the SQL
itself. Read the column, its rules and its engine before reporting (references/data/types.md,
references/data/modeling.md).

Usage:
  schema_lint.py PATH [--files F ...] [--dialect auto|postgresql|mysql|mariadb|oracle|sqlserver|sqlite|generic]
                      [--max-per-check N] [--json]
Standard library only; read-only. Lines containing `schema_lint: ignore` are skipped.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text  # noqa: E402
from _db import LABEL, detect_databases, dominant_dialect  # noqa: E402
from migration_lint import norm_ident, split_actions, split_sql, strip_sql_comments  # noqa: E402

DIALECTS = ("postgresql", "mysql", "mariadb", "oracle", "sqlserver", "sqlite", "generic")
SEV_ORDER = {"high": 0, "medium": 1, "info": 2}


@dataclass
class Column:
    table: str
    name: str
    type: str                      # normalised base type, upper case ("DECIMAL", "TIMESTAMP", "VARCHAR")
    args: list = field(default_factory=list)
    tz: str | None = None          # "with", "without", "local" or None (not stated)
    raw: str = ""
    nullable: bool | None = None
    pk: bool = False
    unique: bool = False
    references: str | None = None
    default: str = ""
    file: str = ""
    line: int = 0
    source: str = "sql"
    note: str = ""
    nonclustered: bool = False     # SQL Server PRIMARY KEY NONCLUSTERED
    checked: bool = False          # a column-level CHECK constraint exists


@dataclass
class Table:
    name: str
    file: str = ""
    line: int = 0
    source: str = "sql"
    columns: dict = field(default_factory=dict)
    pk: list = field(default_factory=list)
    fks: list = field(default_factory=list)       # (cols, ref)
    uniques: list = field(default_factory=list)
    indexes: list = field(default_factory=list)
    checks: list = field(default_factory=list)
    defined: bool = False
    pk_nonclustered: bool = False
    dialect: str | None = None     # from the defining SQL file, used when the repository's engine is not known


@dataclass
class Lead:
    file: str
    line: int
    check: str
    severity: str
    rule: str
    table: str
    column: str
    type: str
    message: str
    fix: str


# --------------------------------------------------------------------------- names

def tokens(name: str) -> list[str]:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [t for t in re.split(r"[_\W]+", s.lower()) if t]


MONEY = {"amount", "amt", "price", "cost", "balance", "total", "subtotal", "fee", "fees", "tax", "vat", "salary",
         "wage", "payment", "paid", "refund", "discount", "credit", "debit", "budget", "revenue", "charge", "money",
         "fare", "deposit", "withdrawal", "principal", "outstanding", "payout", "commission", "premium"}
MONEY_PAIRS = [("credit", "limit"), ("spending", "limit"), ("overdraft", "limit"), ("withdrawal", "limit")]
# Words that make a money-looking name a measurement instead (speed_limit, total_distance, battery_charge).
NOT_MONEY = {"count", "qty", "quantity", "id", "distance", "speed", "score", "rating", "weight", "size", "length",
             "duration", "seconds", "minutes", "hours", "days", "time", "battery", "level", "percent", "pct", "ratio",
             "km", "miles", "meters", "bytes", "kb", "mb", "gb", "points", "calories", "temperature", "volume", "height",
             "width", "depth", "age", "attempts", "retries", "tokens", "version", "units"}
BOOLEAN_WORDS = {"is", "has", "can", "should", "verified", "confirmed", "enabled", "disabled", "active", "valid", "flag",
                 "opted", "consent", "visible", "allowed", "required", "deleted"}
RATE = {"rate", "fx", "interest", "apr", "apy", "yield", "percent", "percentage", "pct"}
FX = {"fx", "exchange", "conversion", "forex"}
IDENT_PAIRS = [("account", "number"), ("account", "no"), ("account", "num"), ("acct", "no"), ("acct", "number"),
               ("card", "number"), ("postal", "code"), ("branch", "code"), ("sort", "code"), ("routing", "number"),
               ("national", "id"), ("tax", "id"), ("vat", "number"), ("reference", "number"), ("ref", "no"),
               ("tracking", "number"), ("invoice", "number"), ("order", "number"), ("customer", "number"),
               ("customer", "no"), ("product", "code"), ("policy", "number"), ("contract", "number"),
               ("loan", "number"), ("loan", "no"), ("transaction", "ref"), ("transaction", "reference"),
               ("bank", "code"), ("branch", "no"), ("check", "number"), ("cheque", "number")]
IDENT_SINGLE = {"iban", "phone", "mobile", "msisdn", "telephone", "tel", "postcode", "zip", "zipcode", "ssn", "passport", "reference",
                "bic", "swift", "sku", "isbn", "ean", "barcode", "upc", "imei", "cardnumber"}
EVENT = {"created", "updated", "deleted", "occurred", "executed", "paid", "posted", "processed", "sent", "received",
         "logged", "timestamp", "ts", "modified", "approved", "settled", "completed", "started", "finished", "expires",
         "expired", "published", "booked"}
FUTURE = {"expires", "expiry", "expiration", "maturity", "matures", "until", "end", "ends", "due", "valid", "renewal",
          "deadline", "scheduled", "retention", "to"}
BUSINESS_DATE = {"date", "dob", "birthday", "birthdate"}
STATUS = {"status", "state"}
REL_JSON = {"items", "lines", "members", "addresses", "phones", "emails", "roles", "permissions", "children", "ids",
            "participants", "accounts", "owners", "holders", "tags"}
HIGH_VOLUME = {"event", "events", "log", "logs", "audit", "audits", "transaction", "transactions", "message", "messages",
               "notification", "notifications", "entry", "entries", "ledger", "history", "click", "clicks", "view",
               "views", "session", "sessions", "payment", "payments", "transfer", "transfers"}

EXTERNAL_REF = {"external", "stripe", "paypal", "provider", "remote", "vendor", "gateway", "session", "request",
                "correlation", "trace", "span", "idempotency", "device", "google", "github", "facebook", "apple", "oauth",
                "message", "job", "batch", "run", "build", "commit", "git", "client", "tracking", "psp", "upstream"}
INT_TYPES = {"INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT", "INT2", "INT4", "INT8", "SERIAL",
             "BIGSERIAL", "SMALLSERIAL"}
EXACT_TYPES = {"DECIMAL", "NUMERIC", "NUMBER", "DEC", "FIXED"}
FLOAT_TYPES = {"FLOAT", "REAL", "DOUBLE", "DOUBLE PRECISION", "FLOAT4", "FLOAT8", "BINARY_FLOAT", "BINARY_DOUBLE"}
TEXT_TYPES = {"VARCHAR", "VARCHAR2", "NVARCHAR", "NVARCHAR2", "CHAR", "NCHAR", "CHARACTER", "CHARACTER VARYING",
              "TEXT", "CLOB", "NCLOB", "STRING", "CITEXT", "MEDIUMTEXT", "LONGTEXT", "TINYTEXT"}
TIME_TYPES = {"TIMESTAMP", "DATETIME", "DATETIME2", "SMALLDATETIME", "TIMESTAMPTZ", "DATETIMEOFFSET"}


def is_ident(toks: list[str]) -> bool:
    joined = "".join(toks)
    if any(t in IDENT_SINGLE for t in toks) or joined in IDENT_SINGLE:
        return True
    return any(a in toks and b in toks and toks.index(a) < toks.index(b) for a, b in IDENT_PAIRS)


# --------------------------------------------------------------------------- SQL DDL

TYPE_RX = re.compile(r"""(?ix)^
    (?P<base>double\s+precision|character\s+varying|char(?:acter)?\s+varying|national\s+char(?:acter)?(?:\s+varying)?|
             long\s+raw|[a-z_][\w]*)
    (?P<args>\s*\([^()]*\))?
    (?P<suffix>(?:\s+(?:with(?:out)?\s+(?:local\s+)?time\s+zone|unsigned|zerofill))*)""")
CREATE_TABLE_RX = re.compile(r"(?is)^CREATE\s+(?:OR\s+REPLACE\s+)?(?:GLOBAL\s+|LOCAL\s+)?(?:UNLOGGED\s+|TEMP(?:ORARY)?\s+)?"
                             r"TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\w.\[\]]+)\s*\(")
ALTER_RX = re.compile(r"(?is)^ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?([`\"\w.\[\]]+)\s+(.*)$")
INDEX_RX = re.compile(r"(?is)^CREATE\s+(UNIQUE\s+)?(?:CLUSTERED\s+|NONCLUSTERED\s+|BITMAP\s+)?INDEX\s+(?:CONCURRENTLY\s+)?"
                      r"(?:IF\s+NOT\s+EXISTS\s+)?(?:[`\"\w.\[\]]+\s+)?ON\s+(?:ONLY\s+)?([`\"\w.\[\]]+)\s*(?:USING\s+\w+\s*)?\(")
CONSTRAINT_RX = re.compile(r"(?is)^(?:CONSTRAINT\s+[`\"\w\[\]]+\s+)?(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE(?:\s+(?:KEY|INDEX))?|"
                           r"CHECK|KEY|INDEX|FULLTEXT|SPATIAL|EXCLUDE)\b(.*)$")
COLUMN_RX = re.compile(r"(?s)^([`\"\[]?)([\w$]+)[`\"\]]?\s+(.+)$")


def paren_body(text: str, open_pos: int) -> tuple[str, int]:
    """Content of the parenthesis opening at text[open_pos] and the index after it (quotes respected)."""
    depth, i, quote = 0, open_pos, None
    while i < len(text):
        c = text[i]
        if quote:
            if c == quote:
                quote = None
        elif c in "'\"`":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[open_pos + 1:i], i + 1
        i += 1
    return text[open_pos + 1:], len(text)


def col_list(text: str) -> list[str]:
    m = re.search(r"\(", text)
    if not m:
        return []
    body, _ = paren_body(text, m.start())
    out = []
    for part in split_actions(body):
        part = part.strip()
        if "(" in part:
            out.append("(expr)")
            continue
        out.append(norm_ident(part.split()[0]) if part else "")
    return out


def parse_type(rest: str) -> tuple[str, list, str | None, str, str]:
    """(base, args, tz, raw type text, remainder) from the text after a column name."""
    rest = re.sub(r"^\s*\[(\w+)\]", r"\1", rest)            # SQL Server scripts: [decimal](18, 2)
    m = TYPE_RX.match(rest.strip())
    if not m:
        return "", [], None, "", rest
    base = " ".join(m.group("base").upper().split())
    args = [a.strip() for a in m.group("args").strip()[1:-1].split(",")] if m.group("args") else []
    suffix = " ".join(m.group("suffix").upper().split())
    tz = "local" if "LOCAL TIME ZONE" in suffix else "without" if "WITHOUT TIME ZONE" in suffix else \
        "with" if "WITH TIME ZONE" in suffix else None
    if base == "TIMESTAMPTZ":
        base, tz = "TIMESTAMP", "with"
    if base == "DATETIMEOFFSET":
        tz = "with"
    raw = rest.strip()[:m.end()].strip()
    return base, args, tz, raw, rest.strip()[m.end():]


def column_from_def(table: str, name: str, rest: str, file: str, line: int) -> Column | None:
    base, args, tz, raw, remainder = parse_type(rest)
    if not base or base in {"CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "KEY", "INDEX"}:
        return None
    up = " ".join(remainder.upper().split())
    ref = None
    rm = re.search(r"(?i)\bREFERENCES\s+([`\"\w.\[\]]+)", remainder)
    if rm:
        ref = norm_ident(rm.group(1))
    dm = re.search(r"(?i)\bDEFAULT\s+(\S+(?:\s*\([^)]*\))?)", remainder)
    return Column(table=table, name=name, type=base, args=args, tz=tz, raw=raw,
                  nullable=False if "NOT NULL" in up or "PRIMARY KEY" in up else (True if re.search(r"\bNULL\b", up) else None),
                  pk="PRIMARY KEY" in up, unique=bool(re.search(r"\bUNIQUE\b", up)), references=ref,
                  default=dm.group(1) if dm else "", file=file, line=line, nonclustered="NONCLUSTERED" in up,
                  checked=bool(re.search(r"\bCHECK\s*\(", up)))


def apply_constraint(t: Table, kind: str, rest: str):
    kind = " ".join(kind.upper().split())
    if kind == "PRIMARY KEY":
        t.pk = col_list(rest)
        t.pk_nonclustered = bool(re.match(r"(?i)\s*NONCLUSTERED\b", rest))
    elif kind == "FOREIGN KEY":
        cols = col_list(rest)
        rm = re.search(r"(?i)\bREFERENCES\s+([`\"\w.\[\]]+)", rest)
        t.fks.append((cols, norm_ident(rm.group(1)) if rm else "?"))
    elif kind.startswith("UNIQUE"):
        cols = col_list(rest)
        t.uniques.append(cols)
        t.indexes.append(cols)
    elif kind in ("KEY", "INDEX"):
        t.indexes.append(col_list(rest))
    elif kind == "CHECK":
        t.checks.append(rest)


def sql_model(text: str, file: str, tables: dict[str, Table], file_dialect: str | None = None):
    text = re.sub(r"(?im)^([ \t]*)GO([ \t]*)$", lambda m: m.group(1) + "; " + m.group(2), text)   # SQL Server batches
    clean = strip_sql_comments(text)
    lines = text.splitlines()
    for off, st in split_sql(text):
        line = clean.count("\n", 0, off) + 1
        if "schema_lint: ignore" in (lines[line - 1] if 0 < line <= len(lines) else ""):
            continue
        m = CREATE_TABLE_RX.match(st)
        if m:
            name = norm_ident(m.group(1))
            body, _end = paren_body(st, m.end() - 1)
            t = tables.setdefault(name, Table(name=name))
            t.file, t.line, t.defined, t.source, t.dialect = file, line, True, "sql", file_dialect
            for el in split_actions(body):
                el = el.strip()
                if not el:
                    continue
                el_line = line + st[:st.find(el)].count("\n") if el in st else line
                cm = CONSTRAINT_RX.match(el)
                if cm:
                    apply_constraint(t, cm.group(1), cm.group(2))
                    continue
                colm = COLUMN_RX.match(el)
                if not colm:
                    continue
                c = column_from_def(name, colm.group(2), colm.group(3), file, el_line)
                if c:
                    if "schema_lint: ignore" in (lines[el_line - 1] if 0 < el_line <= len(lines) else ""):
                        continue
                    key = c.name.lower()
                    t.columns[key] = c
                    if c.pk:
                        t.pk = [key]
                    if c.references:
                        t.fks.append(([key], c.references))
                    if c.unique:
                        t.uniques.append([key])
                        t.indexes.append([key])
            continue
        m = INDEX_RX.match(st)
        if m:
            name = norm_ident(m.group(2))
            t = tables.setdefault(name, Table(name=name, file=file, line=line))
            cols = col_list(st[m.end() - 1:])
            t.indexes.append(cols)
            if m.group(1):
                t.uniques.append(cols)
            continue
        m = ALTER_RX.match(st)
        if not m:
            continue
        name, body = norm_ident(m.group(1)), m.group(2)
        t = tables.setdefault(name, Table(name=name, file=file, line=line))
        for action in split_actions(body):
            a = action.strip()
            am = re.match(r"(?is)^ADD\s+\((.*)\)\s*$", a)            # Oracle ADD (col type, …)
            parts = split_actions(am.group(1)) if am else [a]
            for part in parts:
                part = part.strip()
                cm = re.match(r"(?is)^(?:ADD\s+)?(?:CONSTRAINT\s+[`\"\w\[\]]+\s+)?(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE(?:\s+(?:KEY|INDEX))?|CHECK)\b(.*)$", part)
                if cm and (am or part.upper().startswith("ADD")):
                    apply_constraint(t, cm.group(1), cm.group(2))
                    continue
                addm = re.match(r"(?is)^(?:ADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?)?([`\"\[]?[\w$]+[`\"\]]?)\s+(.+)$", part) \
                    if (am or re.match(r"(?i)^ADD\b", part)) else None
                if addm:
                    c = column_from_def(name, addm.group(1).strip('`"[]'), addm.group(2), file, line)
                    if c:
                        t.columns[c.name.lower()] = c
                        if c.references:
                            t.fks.append(([c.name.lower()], c.references))
                    continue
                tm = re.match(r"(?is)^ALTER\s+(?:COLUMN\s+)?([`\"\w\[\]]+)\s+(?:SET\s+DATA\s+)?TYPE\s+(.+)$", part) or \
                    re.match(r"(?is)^MODIFY\s+(?:COLUMN\s+)?\(?([`\"\w\[\]]+)\s+(.+?)\)?$", part) or \
                    re.match(r"(?is)^ALTER\s+COLUMN\s+([`\"\w\[\]]+)\s+(?!SET\b|DROP\b|TYPE\b)(.+)$", part)
                cg = re.match(r"(?is)^CHANGE\s+(?:COLUMN\s+)?[`\"\w\[\]]+\s+([`\"\w\[\]]+)\s+(.+)$", part)
                if tm or cg:
                    mm = tm or cg
                    c = column_from_def(name, mm.group(1).strip('`"[]'), mm.group(2), file, line)
                    if c:
                        old = t.columns.get(c.name.lower())
                        if old and not c.references:
                            c.references = old.references
                        t.columns[c.name.lower()] = c
                    continue
                dm = re.match(r"(?is)^DROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?([`\"\w\[\]]+)\s*$", part)
                if dm and dm.group(1).upper() not in ("CONSTRAINT", "INDEX", "KEY", "PRIMARY", "FOREIGN"):
                    t.columns.pop(norm_ident(dm.group(1)), None)


# --------------------------------------------------------------------------- ORM and framework models

LARAVEL_TYPES = {"float": "FLOAT", "double": "DOUBLE", "decimal": "DECIMAL", "unsignedDecimal": "DECIMAL",
                 "integer": "INT", "unsignedInteger": "INT", "bigInteger": "BIGINT", "unsignedBigInteger": "BIGINT",
                 "smallInteger": "SMALLINT", "unsignedSmallInteger": "SMALLINT", "tinyInteger": "TINYINT",
                 "unsignedTinyInteger": "TINYINT", "mediumInteger": "INT", "string": "VARCHAR", "char": "CHAR",
                 "text": "TEXT", "mediumText": "TEXT", "longText": "TEXT", "json": "JSON", "jsonb": "JSONB",
                 "timestamp": "TIMESTAMP", "timestampTz": "TIMESTAMP", "dateTime": "DATETIME", "dateTimeTz": "DATETIME",
                 "date": "DATE", "boolean": "BOOLEAN", "uuid": "UUID", "foreignId": "BIGINT", "foreignUuid": "UUID",
                 "enum": "ENUM", "ipAddress": "VARCHAR", "ulid": "CHAR"}


def match_brace(text: str, start: int) -> int:
    depth, i, quote = 0, start, None
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def laravel_model(text: str, file: str, tables: dict[str, Table]):
    for m in re.finditer(r"Schema::(create|table)\(\s*['\"](\w+)['\"]\s*,\s*function\s*\([^)]*\)\s*(?:use\s*\([^)]*\)\s*)?\{", text):
        name = m.group(2).lower()
        body = text[m.end() - 1:match_brace(text, m.end() - 1)]
        base_line = text.count("\n", 0, m.start()) + 1
        t = tables.setdefault(name, Table(name=name, file=file, line=base_line, source="laravel"))
        if m.group(1) == "create":
            t.defined, t.file, t.line, t.source = True, file, base_line, "laravel"
        for st in re.finditer(r"\$table->(\w+)\(([^;]*?)\)((?:->\w+\([^;]*?\))*)\s*;", body):
            method, argtext, chain = st.group(1), st.group(2), st.group(3)
            line = base_line + body.count("\n", 0, st.start())
            args = [a.strip().strip("'\"") for a in split_actions(argtext)] if argtext.strip() else []
            if "schema_lint: ignore" in body[st.start():body.find("\n", st.end()) if body.find("\n", st.end()) != -1 else len(body)]:
                continue
            if method == "id":
                col = args[0] if args else "id"
                t.columns[col] = Column(name, col, "BIGINT", file=file, line=line, source="laravel", pk=True, nullable=False)
                t.pk = [col]
            elif method in ("increments", "bigIncrements"):
                col = args[0] if args else "id"
                t.columns[col] = Column(name, col, "INT" if method == "increments" else "BIGINT", file=file, line=line,
                                        source="laravel", pk=True, nullable=False)
                t.pk = [col]
            elif method in ("timestamps", "timestampsTz", "nullableTimestamps"):
                for col in ("created_at", "updated_at"):
                    t.columns[col] = Column(name, col, "TIMESTAMP", tz="with" if method == "timestampsTz" else None,
                                            file=file, line=line, source="laravel", nullable=True,
                                            raw=f"{method}()", note="framework-timestamps")
            elif method in ("softDeletes", "softDeletesTz"):
                col = args[0] if args else "deleted_at"
                t.columns[col] = Column(name, col, "TIMESTAMP", tz="with" if method == "softDeletesTz" else None,
                                        file=file, line=line, source="laravel", nullable=True)
            elif method in ("morphs", "nullableMorphs", "uuidMorphs", "nullableUuidMorphs") and args:
                for col, typ in ((f"{args[0]}_type", "VARCHAR"), (f"{args[0]}_id", "UUID" if "uuid" in method.lower() else "BIGINT")):
                    t.columns[col] = Column(name, col, typ, file=file, line=line, source="laravel")
            elif method == "foreign" and args:
                cols = [a.strip("[]'\" ") for a in args[0].split(",")]
                on = re.search(r"->on\(\s*['\"](\w+)['\"]", chain)
                t.fks.append((cols, on.group(1).lower() if on else "?"))
            elif method in ("index", "unique", "primary") and args:
                cols = [a.strip("[]'\" ") for a in re.split(r",", args[0])] if "[" in argtext else [args[0]]
                if method == "primary":
                    t.pk = cols
                else:
                    t.indexes.append(cols)
                    if method == "unique":
                        t.uniques.append(cols)
            elif method in LARAVEL_TYPES and args:
                col = args[0]
                typ = LARAVEL_TYPES[method]
                targs = [a for a in args[1:] if re.fullmatch(r"\d+", a)]
                note = ""
                if method in ("decimal", "unsignedDecimal") and not targs:
                    targs, note = ["8", "2"], "laravel-default-decimal"
                c = Column(name, col, typ, args=targs, tz="with" if method in ("timestampTz", "dateTimeTz") else None,
                           raw=f"{method}()", file=file, line=line, source="laravel", note=note,
                           nullable=True if "->nullable(" in chain else None, unique="->unique(" in chain,
                           pk="->primary(" in chain)
                if method == "foreignId" and "->constrained(" in chain:
                    tbl = re.search(r"->constrained\(\s*['\"](\w+)['\"]", chain)
                    ref = tbl.group(1) if tbl else (col[:-3] + "s" if col.endswith("_id") else "?")
                    c.references = ref.lower()
                    t.fks.append(([col], c.references))
                if "->index(" in chain:
                    t.indexes.append([col])
                if c.unique:
                    t.uniques.append([col])
                    t.indexes.append([col])
                t.columns[col] = c


DJANGO_TYPES = {"FloatField": "FLOAT", "DecimalField": "DECIMAL", "IntegerField": "INT", "PositiveIntegerField": "INT",
                "SmallIntegerField": "SMALLINT", "PositiveSmallIntegerField": "SMALLINT", "BigIntegerField": "BIGINT",
                "PositiveBigIntegerField": "BIGINT", "AutoField": "INT", "BigAutoField": "BIGINT", "CharField": "VARCHAR",
                "SlugField": "VARCHAR", "EmailField": "VARCHAR", "URLField": "VARCHAR", "TextField": "TEXT",
                "JSONField": "JSON", "DateTimeField": "TIMESTAMP", "DateField": "DATE", "BooleanField": "BOOLEAN",
                "UUIDField": "UUID", "ForeignKey": "BIGINT", "OneToOneField": "BIGINT", "GenericIPAddressField": "VARCHAR"}


def _kw(call: ast.Call, name: str):
    for k in call.keywords:
        if k.arg == name:
            try:
                return ast.literal_eval(k.value)
            except Exception:  # noqa: BLE001
                return ast.unparse(k.value)
    return None


def _call_name(node) -> str:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def python_models(text: str, file: str, tables: dict[str, Table]):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    lines = text.splitlines()
    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        bases = " ".join(ast.unparse(b) for b in cls.bases)
        tablename = None
        django = "Model" in bases and ("models." in bases or bases.strip() == "Model") and "__tablename__" not in ast.unparse(cls)
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in stmt.targets):
                try:
                    tablename = ast.literal_eval(stmt.value)
                except Exception:  # noqa: BLE001
                    tablename = None
            if isinstance(stmt, ast.ClassDef) and stmt.name == "Meta":
                for s in stmt.body:
                    if isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "db_table" for t in s.targets):
                        try:
                            tablename = ast.literal_eval(s.value)
                        except Exception:  # noqa: BLE001
                            pass
        if not django and not tablename:
            continue
        name = (tablename or cls.name).lower()
        t = tables.setdefault(name, Table(name=name, file=file, line=cls.lineno, source="django" if django else "sqlalchemy"))
        t.defined, t.file, t.line = True, file, cls.lineno
        t.source = "django" if django else "sqlalchemy"
        has_pk = False
        for stmt in cls.body:
            target, value, annotation = None, None, None
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                target, value = stmt.targets[0].id, stmt.value
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                target, value, annotation = stmt.target.id, stmt.value, ast.unparse(stmt.annotation)
            if not target or not isinstance(value, ast.Call):
                continue
            if "schema_lint: ignore" in (lines[stmt.lineno - 1] if stmt.lineno <= len(lines) else ""):
                continue
            fname = _call_name(value)
            if django:
                if fname not in DJANGO_TYPES:
                    continue
                typ = DJANGO_TYPES[fname]
                col = target + "_id" if fname in ("ForeignKey", "OneToOneField") else target
                args = []
                if fname == "DecimalField":
                    md, dp = _kw(value, "max_digits"), _kw(value, "decimal_places")
                    args = [str(md), str(dp)] if md is not None and dp is not None else []
                c = Column(name, col, typ, args=args, file=file, line=stmt.lineno, source="django",
                           nullable=bool(_kw(value, "null")), pk=bool(_kw(value, "primary_key")),
                           unique=bool(_kw(value, "unique")), raw=f"models.{fname}")
                if fname in ("ForeignKey", "OneToOneField"):
                    ref = ast.unparse(value.args[0]).strip("'\"").split(".")[-1].lower() if value.args else "?"
                    c.references = ref
                    t.fks.append(([col], ref))
                    t.indexes.append([col])     # Django indexes ForeignKey columns by default (db_index=True)
                if fname in ("CharField", "TextField", "SlugField", "EmailField", "URLField") and _kw(value, "null"):
                    c.note = "django-null-text"
                has_pk = has_pk or c.pk
                t.columns[col] = c
            else:
                if fname not in ("Column", "mapped_column"):
                    continue
                type_node = None
                col = target
                rest_args = list(value.args)
                if rest_args and isinstance(rest_args[0], ast.Constant) and isinstance(rest_args[0].value, str):
                    col = rest_args.pop(0).value
                for a in rest_args:
                    if _call_name(a) == "ForeignKey":
                        continue
                    type_node = a
                    break
                tname = _call_name(type_node) if type_node is not None else ""
                targs = []
                if isinstance(type_node, ast.Call):
                    targs = [ast.unparse(x) for x in type_node.args]
                if not tname and annotation:
                    inner = re.sub(r"^Mapped\[(?:Optional\[)?([\w.]+)\]*$", r"\1", annotation)
                    tname = {"float": "Float", "Decimal": "Numeric", "decimal.Decimal": "Numeric", "int": "Integer",
                             "str": "String", "datetime": "DateTime", "datetime.datetime": "DateTime", "date": "Date",
                             "bool": "Boolean", "dict": "JSON", "uuid.UUID": "Uuid", "UUID": "Uuid"}.get(inner, "")
                typ = {"Float": "FLOAT", "REAL": "REAL", "Double": "DOUBLE", "DOUBLE": "DOUBLE", "Numeric": "DECIMAL",
                       "DECIMAL": "DECIMAL", "NUMERIC": "DECIMAL", "Integer": "INT", "BigInteger": "BIGINT",
                       "SmallInteger": "SMALLINT", "String": "VARCHAR", "Unicode": "VARCHAR", "Text": "TEXT",
                       "UnicodeText": "TEXT", "DateTime": "DATETIME", "TIMESTAMP": "TIMESTAMP", "Date": "DATE",
                       "Boolean": "BOOLEAN", "JSON": "JSON", "JSONB": "JSONB", "Uuid": "UUID", "UUID": "UUID",
                       "Enum": "ENUM"}.get(tname, "")
                if not typ:
                    continue
                tz = None
                if typ in ("TIMESTAMP", "DATETIME"):
                    tzv = _kw(type_node, "timezone") if isinstance(type_node, ast.Call) else None
                    tz = "with" if tzv is True else "without"
                c = Column(name, col, typ, args=targs if typ == "DECIMAL" else [], tz=tz, file=file, line=stmt.lineno,
                           source="sqlalchemy", nullable=_kw(value, "nullable"), pk=bool(_kw(value, "primary_key")),
                           unique=bool(_kw(value, "unique")), raw=tname)
                for a in value.args:
                    if _call_name(a) == "ForeignKey" and isinstance(a, ast.Call) and a.args:
                        ref = ast.unparse(a.args[0]).strip("'\"").split(".")[0].lower()
                        c.references = ref
                        t.fks.append(([col], ref))
                if _kw(value, "index"):
                    t.indexes.append([col])
                has_pk = has_pk or c.pk
                t.columns[col] = c
        if django and not has_pk:
            t.pk = ["id"]
            t.columns.setdefault("id", Column(name, "id", "BIGINT", pk=True, file=file, line=cls.lineno, source="django"))
        elif has_pk:
            t.pk = [c.name for c in t.columns.values() if c.pk]


PRISMA_TYPES = {"Int": "INT", "BigInt": "BIGINT", "Float": "DOUBLE", "Decimal": "DECIMAL", "String": "VARCHAR",
                "DateTime": "DATETIME", "Json": "JSON", "Boolean": "BOOLEAN", "Bytes": "BYTEA"}


def prisma_model(text: str, file: str, tables: dict[str, Table]):
    for m in re.finditer(r"(?m)^model\s+(\w+)\s*\{", text):
        end = match_brace(text, m.end() - 1)
        body = text[m.end():end - 1]
        mapm = re.search(r"@@map\(\s*\"(\w+)\"", body)
        name = (mapm.group(1) if mapm else m.group(1)).lower()
        base_line = text.count("\n", 0, m.start()) + 1
        t = tables.setdefault(name, Table(name=name, file=file, line=base_line, source="prisma"))
        t.defined, t.file, t.line, t.source = True, file, base_line, "prisma"
        for i, ln in enumerate(body.splitlines()):
            fm = re.match(r"^\s*(\w+)\s+(\w+)(\[\])?(\?)?\s*(.*)$", ln)
            if not fm or ln.strip().startswith(("//", "@@")) or "schema_lint: ignore" in ln:
                continue
            col, ptype, is_list, optional, attrs = fm.groups()
            line = base_line + i + 1
            rel = re.search(r"@relation\([^)]*fields:\s*\[([^\]]*)\]", attrs)
            if rel:
                ref_model = ptype.lower()
                for f in rel.group(1).split(","):
                    t.fks.append(([f.strip()], ref_model))
                continue
            if ptype not in PRISMA_TYPES or is_list:
                continue
            typ = PRISMA_TYPES[ptype]
            args = []
            dm = re.search(r"@db\.(\w+)(?:\(([^)]*)\))?", attrs)
            tz = None
            if dm:
                native = dm.group(1).upper()
                if native in ("TIMESTAMPTZ",):
                    typ, tz = "TIMESTAMP", "with"
                elif native in ("TIMESTAMP",):
                    typ, tz = "TIMESTAMP", "without"
                elif native in ("DECIMAL", "NUMERIC", "MONEY", "REAL", "DOUBLEPRECISION", "FLOAT", "CHAR", "VARCHAR", "TEXT",
                                "DATE", "DATETIME", "DATETIME2", "UUID"):
                    typ = {"DOUBLEPRECISION": "DOUBLE PRECISION"}.get(native, native)
                if dm.group(2):
                    args = [a.strip() for a in dm.group(2).split(",")]
            c = Column(name, col, typ, args=args, tz=tz, raw=f"{ptype}{' ' + dm.group(0) if dm else ''}", file=file,
                       line=line, source="prisma", nullable=bool(optional), pk="@id" in attrs, unique="@unique" in attrs)
            if c.pk:
                t.pk = [col]
            if c.unique:
                t.uniques.append([col])
                t.indexes.append([col])
            t.columns[col] = c
        for im in re.finditer(r"@@(index|unique|id)\(\s*(?:fields:\s*)?\[([^\]]*)\]", body):
            cols = [x.strip() for x in im.group(2).split(",")]
            if im.group(1) == "id":
                t.pk = cols
            else:
                t.indexes.append(cols)
                if im.group(1) == "unique":
                    t.uniques.append(cols)


JPA_TYPES = {"double": "DOUBLE", "Double": "DOUBLE", "float": "FLOAT", "Float": "FLOAT", "BigDecimal": "DECIMAL",
             "long": "BIGINT", "Long": "BIGINT", "int": "INT", "Integer": "INT", "short": "SMALLINT", "Short": "SMALLINT",
             "String": "VARCHAR", "LocalDateTime": "DATETIME", "Instant": "DATETIME", "OffsetDateTime": "DATETIME",
             "ZonedDateTime": "DATETIME", "Date": "DATETIME", "Timestamp": "DATETIME", "LocalDate": "DATE",
             "boolean": "BOOLEAN", "Boolean": "BOOLEAN", "UUID": "UUID"}


def jpa_model(text: str, file: str, tables: dict[str, Table]):
    if "@Entity" not in text:
        return
    cm = re.search(r"@Entity[\s\S]*?\b(?:class|data\s+class)\s+(\w+)", text)
    if not cm:
        return
    tm = re.search(r"@Table\s*\(\s*(?:name\s*=\s*)?\"(\w+)\"", text)
    name = (tm.group(1) if tm else cm.group(1)).lower()
    base_line = text.count("\n", 0, cm.start()) + 1
    t = tables.setdefault(name, Table(name=name, file=file, line=base_line, source="jpa"))
    t.defined, t.file, t.line, t.source = True, file, base_line, "jpa"
    if re.search(r"@EmbeddedId\b|@IdClass\b", text):
        t.pk = ["(composite)"]
    lines = text.splitlines()
    field_rx = re.compile(r"^\s*(?:(?:private|protected|public|internal)\s+)?(?:final\s+|lateinit\s+)?"
                          r"(?:(?:val|var)\s+(\w+)\s*:\s*([\w.]+)\??|([\w.]+)(?:<[^>]*>)?\s+(\w+))\s*(?:=[^;]*)?;?\s*$")
    for i, ln in enumerate(lines):
        fm = field_rx.match(ln)
        if not fm or "static" in ln or "schema_lint: ignore" in ln or ln.strip().startswith(("return", "import", "package")):
            continue
        col, jtype = (fm.group(1), fm.group(2)) if fm.group(1) else (fm.group(4), fm.group(3))
        ann = "\n".join(lines[max(0, i - 6):i])
        ann = ann[ann.rfind(";") + 1:] if ";" in ann else ann
        if re.search(r"@(Transient|OneToMany|ManyToMany|Embedded)\b", ann):
            continue
        cname = re.search(r"@Column\([^)]*name\s*=\s*\"(\w+)\"", ann)
        colname = cname.group(1) if cname else col
        if re.search(r"@(ManyToOne|OneToOne)\b", ann):
            jc = re.search(r"@JoinColumn\([^)]*name\s*=\s*\"(\w+)\"", ann)
            fkcol = jc.group(1) if jc else f"{col}_id"
            t.fks.append(([fkcol], jtype.split(".")[-1].lower()))
            t.columns[fkcol] = Column(name, fkcol, "BIGINT", file=file, line=i + 1, source="jpa", references=jtype.lower())
            continue
        jt = jtype.split(".")[-1]
        if jt not in JPA_TYPES:
            continue
        typ = JPA_TYPES[jt]
        args = []
        if typ == "DECIMAL":
            p = re.search(r"precision\s*=\s*(\d+)", ann)
            s = re.search(r"scale\s*=\s*(\d+)", ann)
            args = [p.group(1), s.group(1) if s else "0"] if p else []
        tz = None
        if typ == "DATETIME":     # the provider maps it (Hibernate on MySQL: datetime(6)); zone semantics come from the Java type
            tz = "with" if jt in ("Instant", "OffsetDateTime", "ZonedDateTime") else "without" if jt == "LocalDateTime" else None
        nullable = False if re.search(r"nullable\s*=\s*false|@NotNull\b|@Id\b", ann) else None
        c = Column(name, colname, typ, args=args, tz=tz, raw=jt, file=file, line=i + 1, source="jpa", nullable=nullable,
                   pk=bool(re.search(r"@Id\b", ann)), unique=bool(re.search(r"unique\s*=\s*true", ann)))
        if c.pk:
            t.pk = [colname]
        t.columns[colname] = c


# --------------------------------------------------------------------------- checks

def check(tables: dict[str, Table], default_dialect: str, per_table: bool = False) -> list[Lead]:
    """per_table: the repository's engine is unknown, so each SQL table uses its own file's dialect (if any)."""
    leads: list[Lead] = []
    names = set(tables)

    def add(c: Column | None, t: Table, chk, sev, rule, msg, fix):
        leads.append(Lead(file=(c.file if c else t.file), line=(c.line if c else t.line), check=chk, severity=sev, rule=rule,
                          table=t.name, column=c.name if c else "", type=(c.raw or c.type) if c else "", message=msg, fix=fix))

    for t in tables.values():
        dialect = t.dialect if per_table and t.dialect else default_dialect
        my = dialect in ("mysql", "mariadb")
        cols = list(t.columns.values())
        by_key = {k.lower(): c for k, c in t.columns.items()}
        pk = [x.lower() for x in t.pk]
        fks = [([x.lower() for x in cols_], ref) for cols_, ref in t.fks]
        fk_cols = {x for cols_, _ in fks for x in cols_}
        check_text = " ".join(t.checks).lower()
        for c in cols:
            tk = tokens(c.name)
            typ = c.type
            table_tk = set(tokens(t.name))
            money = (bool(set(tk) & MONEY) or any(a in tk and b in tk for a, b in MONEY_PAIRS)) \
                and not (set(tk) & NOT_MONEY)
            rate = bool(set(tk) & RATE) and "id" not in tk
            ident = is_ident(tk)
            # ---- numbers
            if dialect == "oracle" and typ in {"FLOAT", "REAL", "DOUBLE PRECISION"}:
                if money or rate:     # Oracle FLOAT is a NUMBER subtype: decimal, but with no fixed scale
                    add(c, t, "decimal-without-scale", "medium", "DATA-TYPE-02",
                        f"Oracle {typ} is a NUMBER subtype (decimal, not IEEE) with no fixed scale: no business rounding "
                        "is enforced", "NUMBER(p,s) sized for the domain")
                typ = "NUMBER(float)"
            if dialect == "sqlite" and typ in EXACT_TYPES and (money or rate or not c.args):
                add(c, t, "sqlite-numeric-affinity", "medium", "DATA-TYPE-02",
                    f"SQLite ignores {c.raw or typ}: NUMERIC affinity stores fractional values as 8-byte binary floats",
                    "Integer minor units, or text with application-side decimal handling, or a server engine for money")
                typ = "NUMERIC(sqlite)"
            if typ in FLOAT_TYPES and money and not rate:
                add(c, t, "money-float", "high", "DATA-TYPE-01",
                    f"Money-like column '{c.name}' uses binary floating point ({c.raw or typ}): totals drift and reconciliation fails",
                    "Exact DECIMAL(p,s) sized for totals plus a currency column, or integer minor units")
            elif typ in FLOAT_TYPES and rate:
                add(c, t, "rate-float", "medium", "DATA-TYPE-02",
                    f"Rate-like column '{c.name}' uses binary floating point ({c.raw or typ}): applied rates cannot be reproduced exactly",
                    "DECIMAL with a scale matching the rate source; state fraction or percent in the name")
            if typ in EXACT_TYPES and not c.args:
                if c.source in ("prisma", "jpa"):
                    pass                      # the ORM generates precision and scale (checked below for JPA)
                elif dialect == "oracle" and typ in ("DECIMAL", "NUMERIC", "DEC"):
                    add(c, t, "decimal-without-scale", "high", "DATA-TYPE-02",
                        f"{typ} without precision and scale on Oracle is NUMBER with scale 0: '{c.name}' stores whole "
                        "numbers", "Declare NUMBER(p,s) (or DECIMAL(p,s)) sized for the domain")
                elif my or dialect == "sqlserver":
                    add(c, t, "decimal-without-scale", "high", "DATA-TYPE-02",
                        f"{typ} without precision and scale on {LABEL.get(dialect, dialect)} stores whole numbers "
                        f"({'(10,0)' if my else '(18,0)'})", "Declare DECIMAL(p,s) from the domain")
                elif dialect in ("postgresql", "oracle"):
                    if money or rate:
                        add(c, t, "decimal-without-scale", "medium", "DATA-TYPE-02",
                            f"{typ} without (p,s) accepts any scale on {LABEL.get(dialect)} — no business rounding is enforced",
                            "Declare the precision and scale so the database enforces the agreed scale")
                else:
                    add(c, t, "decimal-without-scale", "medium", "DATA-TYPE-02",
                        f"{typ} without precision and scale: MySQL, SQL Server and Oracle's DECIMAL/NUMERIC store whole "
                        "numbers, PostgreSQL and Oracle's NUMBER any scale, SQLite binary floats — the meaning depends on "
                        "the engine", "Declare DECIMAL(p,s) explicitly")
            if c.source == "jpa" and typ in EXACT_TYPES and not c.args and (money or rate):
                add(c, t, "framework-default-precision", "medium" if rate else "info", "DATA-TYPE-02",
                    f"BigDecimal '{c.name}' without @Column(precision, scale): the JPA provider picks them (Hibernate "
                    "defaults to scale 2)" + (" — too few decimals for a rate" if rate else ""),
                    "Declare precision and scale on the mapping and compare with the migration's DDL")
            if typ in EXACT_TYPES and len(c.args) == 1 and (money or rate):
                add(c, t, "money-scale-zero", "medium", "DATA-TYPE-02",
                    f"{c.raw or typ} has scale 0: '{c.name}' can only hold whole numbers",
                    "Give the scale explicitly; if amounts are minor units, use an integer type and say so in the name")
            if typ in EXACT_TYPES and len(c.args) == 2 and c.args[1].isdigit():
                scale = int(c.args[1])
                if rate and (set(tk) | table_tk) & FX and scale < 6:
                    add(c, t, "small-scale-rate", "medium", "DATA-TYPE-02",
                        f"Exchange-rate column '{c.name}' has scale {scale}: rates such as 0.000234 are rounded away",
                        "Use a scale that matches the rate source (often 6–10 decimals) and store base, quote and as-of time")
                elif rate and scale <= 2:
                    add(c, t, "small-scale-rate", "info", "DATA-TYPE-02",
                        f"Rate column '{c.name}' with scale {scale}: is it a percent (4.75) or a fraction (0.0475)?",
                        "Name the representation (rate_percent / rate_fraction) and give enough scale")
                if money and c.note == "laravel-default-decimal":
                    add(c, t, "framework-default-precision", "info", "DATA-TYPE-02",
                        f"Laravel's default decimal('{c.name}') is (8,2): values above 999,999.99 overflow",
                        "Pass precision and scale sized for totals")
            if typ in ("MONEY", "SMALLMONEY"):
                add(c, t, "money-type", "info", "DATA-TYPE-02",
                    f"Engine-specific {typ} type: fixed scale and engine-specific behaviour, not portable",
                    "DECIMAL(p,s) plus a currency column")
            # ---- identifiers
            boolean_like = (typ == "TINYINT" and c.args[:1] == ["1"]) or typ in ("BOOLEAN", "BOOL", "BIT") \
                or bool(set(tk) & BOOLEAN_WORDS)
            if ident and typ in INT_TYPES | EXACT_TYPES and not c.pk and not boolean_like:
                add(c, t, "identifier-numeric", "medium", "DATA-TYPE-03",
                    f"Identifier-like column '{c.name}' stored as {c.raw or typ}: leading zeros, letters and long formats are lost",
                    "VARCHAR/CHAR with a format check, normalised once (E.164, uppercase IBAN)")
            # ---- time
            event = c.name.lower().endswith("_at") or c.name.endswith("At") or bool(set(tk) & EVENT)
            future = bool(set(tk) & FUTURE) and (event or "date" in tk or typ in TIME_TYPES)
            if typ in TIME_TYPES and my and typ == "TIMESTAMP" and c.tz in (None, "without") and c.source != "django":
                add(c, t, "mysql-timestamp-range", "high" if future else "info", "DATA-TYPE-04",
                    f"{'MariaDB' if dialect == 'mariadb' else 'MySQL'} TIMESTAMP '{c.name}' ends at 2038-01-19 03:14:07 UTC"
                    + (" (MariaDB 11.5+ on 64-bit platforms: 2106 — check the version)" if dialect == "mariadb" else "")
                    + " and converts through the session time zone"
                    + (" — future dates such as expiries or maturities can already exceed it" if future else ""),
                    "DATE if the value is a calendar date (an expiry or birth date); otherwise DATETIME storing UTC by "
                    "convention (or a later-ending type), with the convention documented")
            elif typ == "DATETIME" and dialect == "sqlserver":
                add(c, t, "sqlserver-datetime", "medium", "DATA-TYPE-04",
                    f"SQL Server datetime '{c.name}' rounds to .000/.003/.007 s and has no zone",
                    "datetime2 (UTC by convention) or datetimeoffset")
            elif typ in ("TIMESTAMP", "DATETIME", "DATETIME2") and event and c.tz in (None, "without") \
                    and c.source not in ("django", "prisma") and c.note != "framework-timestamps" and not (my and typ == "TIMESTAMP"):
                add(c, t, "timestamp-without-zone", "info", "DATA-TYPE-04",
                    f"Instant-like column '{c.name}' stored as {c.raw or typ} without a time zone",
                    "Zone-aware type (timestamptz, datetimeoffset, TIMESTAMP WITH TIME ZONE) or a written UTC convention")
            if typ in TIME_TYPES and set(tk) & BUSINESS_DATE and not event and "time" not in tk:
                add(c, t, "date-as-timestamp", "info", "DATA-TYPE-04",
                    f"Business-date-like column '{c.name}' stored as {c.raw or typ}: it can move across midnight in another zone",
                    "DATE for calendar days (value, due, birth dates)")
            # ---- absence
            if c.note == "django-null-text":
                add(c, t, "two-empty-values", "info", "DATA-TYPE-05",
                    f"Text field '{c.name}' with null=True has two empty values (NULL and '')",
                    "Keep null=False for text unless NULL has a distinct, documented meaning")
            # ---- structure
            if set(tk) & STATUS and typ in TEXT_TYPES and not c.checked and c.name.lower() not in fk_cols \
                    and c.name.lower() not in check_text:
                add(c, t, "status-free-text", "info", "DATA-SCHEMA-01",
                    f"Status column '{c.name}' is free text with no CHECK or foreign key: any value can be stored",
                    "CHECK constraint, native enum or lookup table with a foreign key; enforce transitions in code")
            if typ in ("JSON", "JSONB"):
                if tk and (tk[-1] in REL_JSON or tk[-1].endswith("ids")):
                    add(c, t, "json-relational", "medium", "DATA-MODEL-03",
                        f"JSON column '{c.name}' looks like relational data (a list of related records or IDs)",
                        "A child or junction table with foreign keys, if the data is queried, joined or constrained")
                else:
                    add(c, t, "json-column", "info", "DATA-MODEL-02",
                        f"JSON column '{c.name}': fine for schemaless data; not for values that are filtered, joined or constrained",
                        "Confirm how it is queried; version and validate the shape (DATA-EVOL-01)")
            if typ in TEXT_TYPES and tk and (tk[-1] == "ids" or tk[-1].endswith("ids") or tk[-1] == "list"):
                add(c, t, "id-list-column", "medium", "DATA-MODEL-03",
                    f"Text column '{c.name}' appears to hold a list of identifiers: it cannot be joined, constrained or indexed per value",
                    "A junction table with a foreign key per side")
            if typ in ("CHAR", "VARCHAR", "NCHAR", "NVARCHAR") and c.args[:1] == ["36"] and (set(tk) & {"uuid", "guid"} or c.pk):
                add(c, t, "uuid-as-text", "info", "DATA-KEY-01",
                    f"UUID column '{c.name}' stored as {c.raw}: 36 bytes plus collation costs in every index",
                    "Native uuid / uniqueidentifier, or BINARY(16)")
        # ---- table level
        if t.defined and not pk:
            add(None, t, "no-primary-key", "medium", "DATA-KEY-01", f"Table '{t.name}' has no primary key",
                "Add a primary key (a surrogate if needed) and enforce business keys with UNIQUE")
        if len(pk) == 1 and pk[0] in by_key and dialect != "sqlite":
            pc = by_key[pk[0]]
            if pc.type in {"INT", "INTEGER", "SERIAL", "INT4", "MEDIUMINT"} and set(tokens(t.name)) & HIGH_VOLUME:
                add(pc, t, "int-key-growth", "info", "DATA-KEY-01",
                    f"32-bit primary key on '{t.name}', a table that usually grows fast: it ends at 2,147,483,647",
                    "BIGINT identity or sequence")
            clustered = dialect in ("mysql", "mariadb") or (dialect == "sqlserver" and not pc.nonclustered and not t.pk_nonclustered)
            if clustered and re.search(r"(?i)NEWID\(|UUID\(\)|uuid_generate_v4|gen_random_uuid", pc.default):
                add(pc, t, "random-uuid-clustered-pk", "info", "DATA-KEY-01",
                    f"Random UUID primary key '{pc.name}' on a clustered engine: inserts scatter across the index and every "
                    "secondary index carries the key", "Sequential or time-ordered key; a separate public identifier if needed (T-33)")
        groups_by_base: dict[str, list[tuple[int, Column]]] = defaultdict(list)
        for c in cols:
            m = re.match(r"^(.*?)_?(\d+)$", c.name)
            base = m.group(1).lower().rstrip("_") if m else ""
            if len(base) >= 3 and base not in ("address_line", "line", "street", "addr", "address", "level", "ipv", "iso",
                                               "sha", "md", "utf", "int", "float", "base", "crc", "http", "ver"):
                groups_by_base[base].append((int(m.group(2)), c))
        for base, members in groups_by_base.items():
            nums = sorted(n for n, _ in members)
            if len(nums) >= 2 and nums[0] in (0, 1) and nums == list(range(nums[0], nums[0] + len(nums))):
                names_ = [c.name for _, c in sorted(members, key=lambda x: x[0])]
                add(sorted(members, key=lambda x: x[0])[0][1], t, "repeating-group", "medium", "DATA-MODEL-03",
                    f"Columns {', '.join(names_)} in '{t.name}' form a repeating group",
                    "A child table with one row per value")
        type_cols = {c.name[:-5] for c in cols if c.name.endswith("_type")}
        for c in cols:
            if c.name.endswith("_id") and c.name[:-3] in type_cols and c.name.lower() not in fk_cols:
                add(c, t, "polymorphic-reference", "medium", "DATA-MODEL-03",
                    f"'{c.name}' with '{c.name[:-3]}_type' is a polymorphic reference: no foreign key can enforce it",
                    "One nullable foreign key per target with a CHECK that exactly one is set, or a supertype table")
                continue
            snake = c.name.lower().endswith("_id")
            camel = len(c.name) > 2 and c.name.endswith("Id") and c.name[-3].islower()
            if (snake or camel) and not is_ident(tokens(c.name)) and not c.pk and c.name.lower() not in fk_cols \
                    and c.name.lower() not in pk:
                stem = c.name[:-3].lower() if snake else re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", c.name[:-2]).lower()
                target = next((n for n in (stem, stem + "s", stem + "es", stem[:-1] + "ies" if stem.endswith("y") else "")
                               if n and n in names), None)
                if target:
                    add(c, t, "missing-fk", "info" if c.source == "jpa" else "medium", "DATA-MODEL-03",
                        f"'{t.name}.{c.name}' looks like a reference to '{target}' but has no foreign key",
                        "Add the foreign key (and index it), or document why the reference is not enforced")
                elif c.source != "jpa" and not set(tokens(c.name)) & EXTERNAL_REF:
                    add(c, t, "missing-fk", "info", "DATA-MODEL-03",
                        f"'{t.name}.{c.name}' looks like a reference but no table named like '{stem}' is defined here and no "
                        "foreign key exists", "Confirm whether it points outside this schema (another service) and document it")
        if dialect not in ("mysql", "mariadb"):
            covered = [[x.lower() for x in ix] for ix in t.indexes + t.uniques + ([pk] if pk else []) if ix]
            for cols_, ref in fks:
                if not cols_ or any(ix[:len(cols_)] == cols_ for ix in covered):
                    continue
                c0 = by_key.get(cols_[0])
                add(c0, t, "fk-without-index", "medium" if dialect in ("postgresql", "oracle", "sqlserver") else "info",
                    "DATA-IDX-01",
                    f"Foreign key {t.name}({', '.join(cols_)}) → {ref} has no index starting with its columns"
                    + (" — in Oracle, parent-key changes then lock the child table" if dialect == "oracle" else "")
                    + ("" if dialect in ("postgresql", "oracle", "sqlserver", "sqlite") else " (MySQL would create one; most engines do not)"),
                    "Index the foreign-key columns unless the child table is tiny and the parent is never deleted or re-keyed")
    return leads


# --------------------------------------------------------------------------- discovery and output

def discover(root: Path, files: list[str] | None) -> list[Path]:
    if files:
        out = []
        for f in files:
            p = Path(f)
            if not p.is_absolute() and not p.exists() and (root / p).exists():
                p = root / p
            out.append(p.resolve())
        return out
    out = []
    for p in iter_files(root):
        name, suf = p.name.lower(), p.suffix.lower()
        if suf == ".sql" or name == "schema.prisma":
            out.append(p)
        elif suf == ".php" and "migrations" in p.parts:
            out.append(p)
        elif suf == ".py" and (name == "models.py" or "models" in p.parts):
            out.append(p)
        elif suf in (".java", ".kt", ".py"):
            head = read_text(p, limit=400_000)
            if (suf != ".py" and "@Entity" in head) or (suf == ".py" and "__tablename__" in head):
                out.append(p)
    return out


def scan(root: Path, files: list[str] | None, dialect_opt: str, max_per: int) -> dict:
    root = root.resolve()
    targets = discover(root, files)
    tables: dict[str, Table] = {}
    sql_text = []
    parsed = Counter()
    for path in targets:
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        text = read_text(path, limit=2_000_000)
        if not text:
            continue
        suf, name = path.suffix.lower(), path.name.lower()
        if suf == ".sql":
            sql_model(text, rel, tables, dominant_dialect(text) if dialect_opt == "auto" else None)
            sql_text.append(text)
            parsed["sql"] += 1
        elif name == "schema.prisma":
            prisma_model(text, rel, tables)
            parsed["prisma"] += 1
        elif suf == ".php":
            laravel_model(text, rel, tables)
            parsed["laravel"] += 1
        elif suf == ".py":
            python_models(text, rel, tables)
            parsed["python"] += 1
        elif suf in (".java", ".kt"):
            jpa_model(text, rel, tables)
            parsed["jpa"] += 1
    source, dialect, per_table = "--dialect", dialect_opt, False
    if dialect_opt == "auto":
        db = detect_databases(root)
        app = [e for e in db["application_engines"] if e in DIALECTS]
        if len(app) == 1:
            dialect, source = app[0], "repository configuration"
        else:
            # No single configured engine: each SQL file keeps its own dialect; models use the dominant one.
            dom = dominant_dialect("\n".join(sql_text)) if sql_text else None
            dialect, source = (dom, "SQL constructs, per file") if dom else ("generic", "not determined")
            per_table = True
    leads = check(tables, dialect, per_table)
    counts = Counter(l.check for l in leads)
    shown: dict[str, int] = defaultdict(int)
    kept = []
    for l in sorted(leads, key=lambda x: (SEV_ORDER[x.severity], x.check, x.file, x.line)):
        shown[l.check] += 1
        if shown[l.check] <= max_per:
            kept.append(l)
    return {"root": str(root), "dialect": dialect, "dialect_source": source, "files_parsed": dict(parsed),
            "tables": len([t for t in tables.values() if t.defined]),
            "columns": sum(len(t.columns) for t in tables.values()), "counts": dict(counts),
            "leads": [asdict(l) for l in kept]}


def to_markdown(res: dict) -> str:
    out = [f"# Schema and data-type leads: `{res['root']}`", "",
           "**These are LEADS (confidence: possible)** from names and declared types. Confirm each against the column's "
           "meaning, its rules and the engine before reporting (references/data/types.md, references/data/modeling.md).", "",
           f"Dialect: {LABEL.get(res['dialect'], res['dialect'])} ({res['dialect_source']}) · files parsed: "
           f"{', '.join(f'{k} {v}' for k, v in res['files_parsed'].items()) or 'none'} · tables: {res['tables']} · "
           f"columns: {res['columns']}", ""]
    if not res["leads"]:
        out.append("No lead matched." if res["columns"] else "No table definitions found (SQL DDL, Laravel, Django, "
                   "SQLAlchemy, Prisma or JPA).")
        return "\n".join(out) + "\n"
    out += ["| Check | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(res["counts"].items(), key=lambda kv: -kv[1])]
    current = None
    for l in res["leads"]:
        head = f"{l['severity']} · {l['check']} ({l['rule']})"
        if head != current:
            out += ["", f"## {head}"]
            current = head
        where = f"{l['table']}.{l['column']}" if l["column"] else l["table"]
        typ = f" `{l['type']}`" if l["type"] else ""
        out.append(f"- `{l['file']}:{l['line']}` {where}{typ} — {l['message']}. Fix: {l['fix']}.")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="repository root (used for discovery, relative paths and engine detection), "
                                "or a single schema file")
    p.add_argument("--files", nargs="+", help="scan only these files")
    p.add_argument("--dialect", default="auto", choices=("auto",) + DIALECTS)
    p.add_argument("--max-per-check", type=int, default=25)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root, files = Path(args.path), args.files
    if root.is_file() and not files:           # one file: scan it, with its folder as the root
        root, files = root.resolve().parent, [str(root.resolve())]
    if not root.is_dir():
        print(f"not a directory or file: {root}", file=sys.stderr)
        return 2
    res = scan(root, files, args.dialect, args.max_per_check)
    print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else to_markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
