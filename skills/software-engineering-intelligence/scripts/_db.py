"""Database engine detection and SQL dialect hints shared by the analysis scripts (standard library only).

detect_databases(root) reads configuration, dependency manifests, container definitions, CI files and
test configuration, and reports which engines each of them references, with the evidence. It never
connects to a database and never reads secrets: connection strings are reduced to the engine name and
values are not echoed. When nothing references an engine, the result is UNKNOWN — callers must say so
rather than guess.

dialect_hints(sql) counts constructs that only one engine family accepts or interprets in its own way
(upsert syntax, row limiting, date functions, identifier quoting…). They are leads for "this SQL needs
that engine in its tests" (references/testing/database-matrix.md), not a parser.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import is_test_path, iter_files, read_text  # noqa: E402

ENGINES = ("postgresql", "mysql", "mariadb", "oracle", "sqlserver", "sqlite")
STAND_INS = ("h2", "hsqldb", "derby")
LABEL = {"postgresql": "PostgreSQL", "mysql": "MySQL", "mariadb": "MariaDB", "oracle": "Oracle",
         "sqlserver": "SQL Server", "sqlite": "SQLite", "h2": "H2", "hsqldb": "HSQLDB", "derby": "Derby"}

# Patterns per engine for configuration, manifests and containers. Ordered so that MariaDB is checked
# before MySQL (a MariaDB URL also matches "mysql" driver names in some stacks).
SIGNATURES: dict[str, re.Pattern] = {
    "postgresql": re.compile(r"(?i)postgres(?:ql)?(?:\+\w+)?://|jdbc:postgresql|\bpgsql\b|\bpsycopg2?\b|\basyncpg\b|\bpg8000\b|"
                             r"org\.postgresql|['\"]pg['\"]\s*:|gem\s+['\"]pg['\"]|lib/pq\b|jackc/pgx|\bnpgsql\b|"
                             r"image:\s*['\"]?(?:\S+/)?(?:postgres|postgis/postgis)[:'\"\s]|backends\.postgresql|"
                             r"adapter:\s*postgres(?:ql)?\b|DB_CONNECTION\s*=\s*pgsql|provider\s*=\s*\"postgresql\"|"
                             r"PostgreSQLContainer|testcontainers\.postgres|@testcontainers/postgresql|"
                             r"spring\.datasource\.url\s*[=:]\s*jdbc:postgresql"),
    "mariadb": re.compile(r"(?i)mariadb://|jdbc:mariadb|org\.mariadb|image:\s*['\"]?(?:\S+/)?mariadb[:'\"\s]|"
                          r"DB_CONNECTION\s*=\s*mariadb|MariaDBContainer|['\"]mariadb['\"]\s*:"),
    "mysql": re.compile(r"(?i)mysql(?:\+\w+)?://|jdbc:mysql|\bmysqlclient\b|\bpymysql\b|mysql-connector|\baiomysql\b|"
                        r"['\"]mysql2?['\"]\s*:|gem\s+['\"]mysql2['\"]|go-sql-driver/mysql|com\.mysql|MySql\.Data|"
                        r"Pomelo\.EntityFrameworkCore\.MySql|image:\s*['\"]?(?:\S+/)?mysql[:'\"\s]|backends\.mysql|"
                        r"adapter:\s*mysql2?\b|DB_CONNECTION\s*=\s*mysql|provider\s*=\s*\"mysql\"|MySQLContainer|"
                        r"testcontainers\.mysql"),
    "oracle": re.compile(r"(?i)jdbc:oracle|oracle\.jdbc|\bojdbc\d*\b|\bcx_Oracle\b|\boracledb\b|\bgodror\b|"
                         r"Oracle\.ManagedDataAccess|Oracle\.EntityFrameworkCore|gvenzl/oracle|"
                         r"container-registry\.oracle\.com/database|backends\.oracle|DB_CONNECTION\s*=\s*oracle|"
                         r"laravel-oci8|OracleContainer|oracle\+(?:cx_oracle|oracledb)://"),
    "sqlserver": re.compile(r"(?i)jdbc:sqlserver|com\.microsoft\.sqlserver|mssql-jdbc|\bpymssql\b|mssql\+pyodbc|"
                            r"['\"](?:mssql|tedious)['\"]\s*:|go-mssqldb|Microsoft\.Data\.SqlClient|System\.Data\.SqlClient|"
                            r"Microsoft\.EntityFrameworkCore\.SqlServer|\bUseSqlServer\b|mcr\.microsoft\.com/mssql|"
                            r"DB_CONNECTION\s*=\s*sqlsrv|provider\s*=\s*\"sqlserver\"|MSSQLServerContainer|"
                            r"sqlserver://|backends?\.mssql|\bmssql_python\b"),
    "sqlite": re.compile(r"(?i)sqlite(?:\+\w+)?:///|jdbc:sqlite|better-sqlite3|mattn/go-sqlite3|modernc\.org/sqlite|"
                         r"Microsoft\.Data\.Sqlite|Microsoft\.EntityFrameworkCore\.Sqlite|\bUseSqlite\b|"
                         r"DB_CONNECTION\s*=\s*sqlite|<env\s+name=\"DB_CONNECTION\"\s+value=\"sqlite\"|"
                         r"adapter:\s*sqlite3\b|backends\.sqlite3|provider\s*=\s*\"sqlite\"|['\"]sqlite3['\"]\s*:|"
                         r"\bsqlite3\.connect\s*\(|['\"]:memory:['\"]"),
    "h2": re.compile(r"(?i)jdbc:h2:|com\.h2database|<artifactId>h2</artifactId>|['\"]com\.h2database:h2"),
    "hsqldb": re.compile(r"(?i)jdbc:hsqldb|org\.hsqldb"),
    "derby": re.compile(r"(?i)jdbc:derby|org\.apache\.derby"),
}
IMAGE_VERSION_RX = re.compile(r"(?i)image:\s*['\"]?(?:\S+/)?(postgres|postgis/postgis|mysql|mariadb|mssql/server|"
                              r"oracle-(?:free|xe)|oracle/database|database/(?:free|express|enterprise))[:@]([\w.\-]+)")
IMAGE_ENGINE = {"postgres": "postgresql", "postgis/postgis": "postgresql", "mysql": "mysql", "mariadb": "mariadb",
                "mssql/server": "sqlserver", "oracle-free": "oracle", "oracle-xe": "oracle", "oracle/database": "oracle",
                "database/free": "oracle", "database/express": "oracle", "database/enterprise": "oracle"}

# In CI files engines often appear as bare image tags in a build matrix ("db: [postgres:16, mysql:8.0]").
CI_IMAGE_TOKEN_RX = re.compile(r"(?i)(?<![\w./-])((?:mcr\.microsoft\.com/)?mssql/server|postgis/postgis|postgres|mysql|mariadb|"
                               r"(?:gvenzl/)?oracle-(?:free|xe))[:@]([\w.\-]+)")

MANIFESTS = {"requirements.txt", "pyproject.toml", "Pipfile", "setup.cfg", "setup.py", "package.json", "composer.json",
             "go.mod", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile", "Cargo.toml", "mix.exs"}
CONFIG_NAMES = {"database.yml", "database.php", "alembic.ini", "schema.prisma", "knexfile.js", "knexfile.ts",
                "ormconfig.json", "ormconfig.js", "ormconfig.ts", "data-source.ts", "settings.py", "config.py",
                "appsettings.json", "liquibase.properties", "flyway.conf", "sqlx.toml"}
TEST_CONFIG_NAMES = {"phpunit.xml", "phpunit.xml.dist", "pytest.ini", "conftest.py", "tox.ini", "jest.config.js",
                     "jest.config.ts", "vitest.config.ts", "vitest.config.js", "test_settings.py", "settings_test.py"}
CI_HINTS = (".github/workflows/", ".gitlab-ci.yml", "azure-pipelines.yml", "jenkinsfile", ".circleci/", "bitbucket-pipelines.yml")
CODE_EXT = {".py", ".java", ".kt", ".go", ".php", ".rb", ".cs", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".scala"}
# Sample and fixture projects describe other applications, not this one.
NOT_THIS_APP_DIRS = {"fixtures", "__fixtures__", "testdata", "test-data", "test_data", "evals", "examples", "example",
                     "samples", "sample", "demo", "demos"}


def _kind(rel: str, name: str) -> str | None:
    """Classify a file by what its engine references say about the environment."""
    low, lname = rel.lower(), name.lower()
    if any(h in low for h in CI_HINTS):
        return "ci"
    if re.match(r"^(docker-)?compose(\.[\w-]+)?\.ya?ml$", lname):
        return "container-test" if "test" in lname else "container"
    if lname.startswith(".env"):
        if any(t in lname for t in (".testing", ".test", ".ci")):
            return "test-config"
        return "config"
    if lname in TEST_CONFIG_NAMES or re.match(r"^application-(test|it|integration)[\w-]*\.(properties|ya?ml)$", lname) \
            or "src/test/resources/" in low or (lname.startswith("appsettings.") and "test" in lname):
        return "test-config"
    if name in MANIFESTS or (lname.startswith("requirements") and lname.endswith(".txt")) or lname.endswith(".csproj"):
        return "dependency"
    if lname in CONFIG_NAMES or re.match(r"^application(-[\w]+)?\.(properties|ya?ml)$", lname) \
            or (lname.startswith("appsettings") and lname.endswith(".json")) or "/settings/" in low:
        return "config"
    return None


def _dependency_scope(text: str, pos: int, name: str) -> str:
    """'test-config' when the matched dependency is declared for tests only, else 'dependency'."""
    lname = name.lower()
    if lname == "pom.xml":
        start, end = text.rfind("<dependency>", 0, pos), text.find("</dependency>", pos)
        if start != -1 and end != -1 and re.search(r"<scope>\s*test\s*</scope>", text[start:end]):
            return "test-config"
    elif lname.startswith("build.gradle"):
        line = text[text.rfind("\n", 0, pos) + 1: text.find("\n", pos) if text.find("\n", pos) != -1 else len(text)]
        if re.search(r"(?i)\btest(?:Implementation|RuntimeOnly|CompileOnly|Compile|FixturesImplementation)\b", line):
            return "test-config"
    elif lname.startswith("requirements") and re.search(r"(?i)dev|test", lname):
        return "test-config"
    elif lname in ("package.json", "composer.json"):
        # The nearest preceding section key decides: devDependencies / require-dev are for development and tests.
        keys = list(re.finditer(r'"(dependencies|devDependencies|peerDependencies|optionalDependencies|require|require-dev)"\s*:',
                                text[:pos]))
        if keys and keys[-1].group(1) in ("devDependencies", "require-dev"):
            return "test-config"
    elif lname in ("pyproject.toml", "pipfile", "setup.cfg"):
        headers = list(re.finditer(r"(?m)^\s*\[([^\]]+)\]", text[:pos]))
        header = headers[-1].group(1).lower() if headers else ""
        line_start = text.rfind("\n", 0, pos) + 1
        line = text[line_start:pos]
        key = re.match(r"\s*([\w.-]+)\s*=", line)
        if re.search(r"dev|test", header) or header == "dev-packages" or \
                (header in ("project.optional-dependencies", "dependency-groups", "options.extras_require")
                 and key and re.search(r"(?i)dev|test", key.group(1))):
            return "test-config"
        if header in ("project.optional-dependencies", "dependency-groups"):
            # a list spanning several lines: find the key that opened it
            opened = list(re.finditer(r"(?m)^\s*([\w.-]+)\s*=\s*\[", text[headers[-1].end() if headers else 0:pos]))
            if opened and re.search(r"(?i)dev|test", opened[-1].group(1)):
                return "test-config"
    elif lname == "gemfile":
        before = text[:pos]
        groups = list(re.finditer(r"(?m)^\s*group\s+([^\n]+?)\s+do\s*$", before))
        if groups:
            tail = before[groups[-1].end():]
            if not re.search(r"(?m)^\s*end\s*$", tail) and re.search(r":(test|development)\b", groups[-1].group(1)) \
                    and not re.search(r":production\b", groups[-1].group(1)):
                return "test-config"
        line = text[text.rfind("\n", 0, pos) + 1: text.find("\n", pos) if text.find("\n", pos) != -1 else len(text)]
        if re.search(r"group:\s*(?:\[[^\]]*)?:(test|development)", line):
            return "test-config"
    return "dependency"


def _rails_sections(text: str) -> list[tuple[str, str]]:
    """Split a Rails-style database.yml into (section, body) pairs."""
    parts = re.split(r"(?m)^([A-Za-z_][\w-]*):[ \t]*(?:&\w+)?[ \t]*$", text)
    return [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def detect_databases(root: Path, max_code_files: int = 600) -> dict:
    """Engines referenced by the repository, grouped by evidence kind; never reads secret values."""
    root = root.resolve()
    evidence: dict[str, list[dict]] = defaultdict(list)
    versions: dict[str, set] = defaultdict(set)
    code_seen = 0

    def add(engine: str, rel: str, kind: str, detail: str):
        if len(evidence[engine]) < 12 and not any(e["file"] == rel and e["kind"] == kind for e in evidence[engine]):
            evidence[engine].append({"file": rel, "kind": kind, "detail": detail})

    for path in iter_files(root, NOT_THIS_APP_DIRS):
        rel = path.relative_to(root).as_posix()
        name = path.name
        kind = _kind(rel, name)
        if kind is None and path.suffix.lower() in CODE_EXT and is_test_path(rel) and code_seen < max_code_files:
            kind = "test-code"
            code_seen += 1
        if kind is None:
            continue
        text = read_text(path, limit=400_000)
        if not text:
            continue
        if name.lower() == "database.php":       # Laravel: the default connection when DB_CONNECTION is unset
            dm = re.search(r"['\"]default['\"]\s*=>\s*env\(\s*['\"]DB_CONNECTION['\"]\s*,\s*['\"](\w+)['\"]", text)
            engine = {"pgsql": "postgresql", "mysql": "mysql", "mariadb": "mariadb", "sqlite": "sqlite",
                      "sqlsrv": "sqlserver", "oracle": "oracle"}.get(dm.group(1).lower()) if dm else None
            if engine:
                add(engine, rel, "config-default", f"default connection '{dm.group(1)}'")
            continue     # the file lists every supported driver; only the default says which one is used
        if name.lower() == "database.yml":
            for section, body in _rails_sections(text):
                sec_kind = "test-config" if section.lower() == "test" else "config"
                for engine, rx in SIGNATURES.items():
                    if rx.search(body):
                        add(engine, rel, sec_kind, f"section '{section}'")
            continue
        for engine, rx in SIGNATURES.items():
            m = rx.search(text)
            if not m:
                continue
            if engine == "mysql" and SIGNATURES["mariadb"].search(text) and not re.search(r"(?i)image:\s*['\"]?(?:\S+/)?mysql", text):
                continue  # a MariaDB reference that also mentions mysql drivers
            ev_kind = _dependency_scope(text, m.start(), name) if kind == "dependency" else kind
            add(engine, rel, ev_kind, re.sub(r"[^\w.:/+@-]", " ", m.group(0)).strip()[:40])
        for m in IMAGE_VERSION_RX.finditer(text):
            engine = IMAGE_ENGINE.get(m.group(1).lower())
            if engine:
                versions[engine].add(m.group(2))
        if kind == "ci":
            for m in CI_IMAGE_TOKEN_RX.finditer(text):
                image = re.sub(r"^(?:mcr\.microsoft\.com/|gvenzl/)", "", m.group(1).lower())
                engine = IMAGE_ENGINE.get(image)
                if engine:
                    add(engine, rel, "ci", m.group(0)[:40])
                    if m.group(2)[:1].isdigit():
                        versions[engine].add(m.group(2))

    app_kinds = {"config", "dependency", "container"}
    test_kinds = {"test-config", "test-code", "ci", "container-test"}
    application = sorted(e for e, ev in evidence.items() if any(x["kind"] in app_kinds for x in ev))
    if not application:      # a framework's fallback default counts only when nothing else names an engine
        application = sorted(e for e, ev in evidence.items() if any(x["kind"] == "config-default" for x in ev))
    tests = sorted(e for e, ev in evidence.items() if any(x["kind"] in test_kinds for x in ev))
    notes = []
    stand_ins = [e for e in tests if e in STAND_INS or (e == "sqlite" and application and "sqlite" not in application)]
    real_app = [e for e in application if e not in STAND_INS]
    if real_app and stand_ins:
        notes.append(f"Tests reference {', '.join(LABEL[e] for e in stand_ins)} while application configuration references "
                     f"{', '.join(LABEL[e] for e in real_app)}: engine-dependent tests may not be evidence for production "
                     f"(TEST-DATA-02).")
    if len(real_app) > 1:
        notes.append("Several engines are referenced by application configuration or drivers: check whether the product "
                     "supports several engines (category D tests) or whether some references are leftovers.")
    return {
        "status": "detected" if evidence else "UNKNOWN",
        "engines": {e: evidence[e] for e in sorted(evidence)},
        "application_engines": application,
        "test_engines": tests,
        "versions": {e: sorted(v) for e, v in versions.items()},
        "notes": notes if evidence else ["No configuration, driver, container or test reference to a database engine was "
                                          "found: record the production and test engines as UNKNOWN and ask."],
    }


def databases_markdown(db: dict) -> list[str]:
    out = ["## Databases", ""]
    if db["status"] == "UNKNOWN":
        return out + ["- Engines: **UNKNOWN** — " + db["notes"][0], ""]
    def names(lst):
        return ", ".join(LABEL.get(e, e) + (f" ({', '.join(db['versions'][e])})" if db["versions"].get(e) else "")
                         for e in lst) or "none found"
    app = names(db["application_engines"]) if db["application_engines"] else \
        "none found — record the production engine as UNKNOWN and ask"
    out += [f"- Referenced by application configuration, drivers or containers: {app}",
            f"- Referenced by test configuration, test code or CI: {names(db['test_engines'])}"]
    for engine, ev in db["engines"].items():
        shown = "; ".join(f"`{x['file']}` ({x['kind']})" for x in ev[:4])
        out.append(f"  - {LABEL.get(engine, engine)}: {shown}" + (" …" if len(ev) > 4 else ""))
    out += [f"- Note: {n}" for n in db["notes"]]
    out += ["- These are references, not proof of what production runs — confirm with the team.", ""]
    return out


# --------------------------------------------------------------------------- dialect hints

DIALECT_HINTS: dict[str, list[tuple[str, str]]] = {
    "postgresql": [(r"\bON\s+CONFLICT\b", "ON CONFLICT upsert"),
                   (r"(?<=[\w)'\]])::(?:text|int[248]?|integer|bigint|smallint|numeric|decimal|real|float[48]|date|time|"
                    r"timestamptz|timestamp|interval|jsonb?|uuid|bool(?:ean)?|varchar|bytea|regclass|inet|tsvector)\b", ":: cast"),
                   (r"\bILIKE\b", "ILIKE"),
                   (r"\bJSONB\b", "jsonb"), (r"\b(?:BIG|SMALL)?SERIAL\b", "serial"), (r"\bTIMESTAMPTZ\b", "timestamptz"),
                   (r"\bDISTINCT\s+ON\s*\(", "DISTINCT ON"), (r"\bCONCURRENTLY\b", "CONCURRENTLY"),
                   (r"\bUSING\s+(?:GIN|GIST|BRIN|SPGIST)\b", "GIN/GiST/BRIN index"),
                   (r"\bAS\s+\$\w*\$|\$\w*\$\s*LANGUAGE\b", "dollar quoting"),
                   (r"\bnextval\s*\(", "nextval()"), (r"\bgen_random_uuid\s*\(", "gen_random_uuid()"),
                   (r"->>|#>>|@>|<@", "JSON operators"), (r"\bRETURNING\b", "RETURNING")],
    "mysql": [(r"\bON\s+DUPLICATE\s+KEY\s+UPDATE\b", "ON DUPLICATE KEY UPDATE"), (r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+`\w+`", "backtick identifiers"),
              (r"\bAUTO_INCREMENT\b", "AUTO_INCREMENT"), (r"\bENGINE\s*=\s*(?:InnoDB|MyISAM|MEMORY|Aria|RocksDB)\b", "ENGINE="), (r"\bUNSIGNED\b", "UNSIGNED"),
              (r"\bTINYINT\s*\(\s*1\s*\)", "TINYINT(1)"), (r"\bGROUP_CONCAT\s*\(", "GROUP_CONCAT"),
              (r"\bINSERT\s+IGNORE\b", "INSERT IGNORE"), (r"\bSTRAIGHT_JOIN\b", "STRAIGHT_JOIN"),
              (r"\bLIMIT\s+\d+\s*,\s*\d+", "LIMIT offset,count"), (r"\bALGORITHM\s*=\s*(?:INPLACE|INSTANT|COPY)\b", "ALGORITHM=")],
    "oracle": [(r"\bNVL2?\s*\(", "NVL"), (r"\bDECODE\s*\(", "DECODE"), (r"\bROWNUM\b", "ROWNUM"),
               (r"\bCONNECT\s+BY\b", "CONNECT BY"), (r"\bFROM\s+DUAL\b", "FROM DUAL"), (r"\bVARCHAR2\b", "VARCHAR2"),
               (r"\bNUMBER\s*\(", "NUMBER(p,s)"), (r"\bSYS(?:DATE|TIMESTAMP)\b", "SYSDATE"), (r"\.NEXTVAL\b", "seq.NEXTVAL"),
               (r"\bTO_(?:DATE|CHAR|NUMBER)\s*\(", "TO_DATE/TO_CHAR"), (r"\bLISTAGG\s*\(", "LISTAGG"),
               (r"/\*\+", "optimizer hint"), (r"\bNOLOGGING\b", "NOLOGGING"), (r"\bTABLESPACE\b", "TABLESPACE")],
    "sqlserver": [(r"\bTOP\s*\(?\s*\d+", "TOP n"), (r"\bGETDATE\s*\(\s*\)", "GETDATE()"), (r"\bISNULL\s*\(", "ISNULL()"),
                  (r"\bNVARCHAR\b", "NVARCHAR"), (r"\bDATETIME2\b|\bDATETIMEOFFSET\b", "datetime2/datetimeoffset"),
                  (r"\bIDENTITY\s*\(\s*\d+\s*,\s*\d+\s*\)", "IDENTITY(1,1)"), (r"\bWITH\s*\(\s*NOLOCK\s*\)", "WITH (NOLOCK)"),
                  (r"\bOUTPUT\s+INSERTED\b", "OUTPUT INSERTED"), (r"\bNEW(?:SEQUENTIAL)?ID\s*\(\s*\)", "NEWID()"),
                  (r"\bUNIQUEIDENTIFIER\b", "uniqueidentifier"), (r"(?m)^\s*GO\s*$", "GO batch separator"),
                  (r"\[\w+\]\.\[\w+\]", "[bracket] identifiers"), (r"\b(?:CROSS|OUTER)\s+APPLY\b", "APPLY")],
    "sqlite": [(r"\bAUTOINCREMENT\b", "AUTOINCREMENT"), (r"\bPRAGMA\b", "PRAGMA"), (r"\bWITHOUT\s+ROWID\b", "WITHOUT ROWID"),
               (r"\)\s*STRICT\b", "STRICT table"), (r"\bsqlite_(?:master|schema)\b", "sqlite_master"),
               (r"\bdatetime\s*\(\s*'now'", "datetime('now')"), (r"\bINSERT\s+OR\s+(?:REPLACE|IGNORE)\b", "INSERT OR …")],
}
# Constructs that more than one of these engines accepts. A construct's engines are its primary engine
# (the key above) plus these; detection weighs shared constructs less, and test selection intersects them
# with the engines the application uses.
ACCEPTED_ALSO: dict[str, set[str]] = {
    "ON CONFLICT upsert": {"sqlite"},                   # SQLite 3.24+: PostgreSQL's syntax
    "RETURNING": {"sqlite", "mariadb", "oracle"},       # SQLite 3.35+, MariaDB 10.5+, Oracle RETURNING … INTO
    "JSON operators": {"mysql", "mariadb", "sqlite"},   # ->> in MySQL 5.7.13+, SQLite 3.38+
    "GROUP_CONCAT": {"mariadb", "sqlite"},
    "LIMIT offset,count": {"mariadb", "sqlite"},
    "backtick identifiers": {"mariadb", "sqlite"},
    "ON DUPLICATE KEY UPDATE": {"mariadb"},
    "AUTO_INCREMENT": {"mariadb"}, "ENGINE=": {"mariadb"}, "UNSIGNED": {"mariadb"}, "TINYINT(1)": {"mariadb"},
    "INSERT IGNORE": {"mariadb"}, "STRAIGHT_JOIN": {"mariadb"}, "ALGORITHM=": {"mariadb"},
    "FROM DUAL": {"mysql", "mariadb"},
    "SYSDATE": {"mysql", "mariadb"},
    "TO_DATE/TO_CHAR": {"postgresql"},
    "TABLESPACE": {"postgresql"},
    "optimizer hint": {"mysql", "mariadb"},
    "NVARCHAR": {"mysql", "mariadb"},
    "ISNULL()": {"mysql", "mariadb"},                   # different meaning: one argument in MySQL
    "APPLY": {"oracle"},                                # Oracle 12c+
    "[bracket] identifiers": {"sqlite"},
    "serial": {"mysql", "mariadb"},                     # MySQL SERIAL = BIGINT UNSIGNED AUTO_INCREMENT UNIQUE
    "nextval()": {"mariadb"},
}


def construct_engines(engine: str, label: str) -> set[str]:
    """Every engine (of the six) that accepts a construct found as a hint for `engine`."""
    return {engine} | ACCEPTED_ALSO.get(label, set())


_COMPILED_HINTS = {e: [(re.compile(rx, re.I), re.compile(rx), label) for rx, label in hints]
                   for e, hints in DIALECT_HINTS.items()}
_CASE_SENSITIVE = {"GO batch separator", ":: cast"}
# Words that also occur in program code, comments and English text (`.decode(`, `Number(`, `# pragma`,
# `autoincrement=True`, "runs concurrently", "top 10"): in code they count only when written in upper case,
# the usual style of embedded SQL. Missing a lower-case construct costs little (the plan falls back to
# the production engine); a false match would send tests to the wrong engine.
_AMBIGUOUS_IN_CODE = {"ON CONFLICT upsert", "ENGINE=", "ILIKE", "RETURNING", "serial", "CONCURRENTLY", "DECODE", "NUMBER(p,s)", "TOP n", "ISNULL()",
                      "PRAGMA", "AUTOINCREMENT", "STRICT table", "UNSIGNED", "NVL", "TO_DATE/TO_CHAR", "LISTAGG", "SYSDATE",
                      "ROWNUM", "GETDATE()", "TABLESPACE", "NVARCHAR", "jsonb", "timestamptz", "nextval()", "APPLY",
                      "FROM DUAL", "INSERT OR …", "LIMIT offset,count"}
_CODE_COMMENT_RX = re.compile(r"/\*.*?\*/|(?:^|(?<=\s))(?://|#(?!\[)|--)[^\n]*$", re.S | re.M)


def dialect_hints(sql: str, code: bool = False) -> dict[str, list[str]]:
    """{engine: [construct labels found]}; empty when nothing engine-specific is seen.

    code=True: the text is program source with embedded SQL — comments are ignored and words that
    also occur in code or prose must be upper case."""
    if code:
        sql = _CODE_COMMENT_RX.sub(" ", sql)
    found: dict[str, list[str]] = {}
    for engine, hints in _COMPILED_HINTS.items():
        labels = []
        for rx_i, rx_cs, label in hints:
            sensitive = label in _CASE_SENSITIVE or (code and label in _AMBIGUOUS_IN_CODE)
            if (rx_cs if sensitive else rx_i).search(sql):
                labels.append(label)
        if labels:
            found[engine] = labels
    return found


def dominant_dialect(sql: str) -> str | None:
    """The engine family with the strictly highest score (2 per construct only it accepts, 1 per shared one),
    or None when unclear."""
    counts = Counter({e: sum(1 if label in ACCEPTED_ALSO else 2 for label in v) for e, v in dialect_hints(sql).items()})
    if not counts:
        return None
    (top, n), *rest = counts.most_common()
    if rest and rest[0][1] == n:
        return None
    return top
