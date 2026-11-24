#!/usr/bin/env python3
"""Change-impact leads for test selection (TEST-SEL-01, TEST-DATA-02).

Reads the files changed since a git base (or a given list), classifies each change (docs, UI style,
UI template, UI component, source, data access incl. ORM mapping files, SQL, migration, contract,
configuration, dependency, build/CI, test, test support such as conftest.py and fixtures), finds the
test files that are named after a changed file or import it — directly or through other modules
(Python, JavaScript/TypeScript, Java/Kotlin, Go, PHP import graphs) — flags engine-dependent SQL in the
changed lines and money, security and concurrency signals in them, and the database engines the
repository references. Constructs that several engines accept (an upsert both PostgreSQL and SQLite
take) are matched against the application's engines, so tests go to the engine production runs. It
then proposes test groups labelled Required, Recommended, Optional or Not necessary, each with its
reason.

Everything it prints is a LEAD for the plan in references/testing/selection.md, not the plan itself:
static import graphs miss dependency-injection wiring, reflection, configuration and SQL built at run
time, and naming conventions miss tests that live elsewhere. Confirm and complete the plan, then
record it in assets/templates/test-execution-report.md. Read-only: it runs `git diff` and reads files;
it never runs tests, connects to databases or prints configuration values.

Usage:
  test_impact.py PATH [--base REF] [--head REF] [--files F ...] [--depth N] [--json]

  --base REF   compare REF with the working tree (or with --head); default: HEAD
  --head REF   compare base...head (the changes on head since it diverged from base)
  --files F    analyse these files as changed instead of asking git
  --depth N    how many import hops to follow from a changed file to tests (default 3)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import git, is_test_path, iter_files, language_of, read_text  # noqa: E402
from _db import LABEL, construct_engines, detect_databases, dialect_hints  # noqa: E402

DOC_EXT = {".md", ".rst", ".adoc", ".txt"}
DOC_NAMES = {"license", "licence", "changelog", "authors", "contributors", "notice", "codeowners"}
STYLE_EXT = {".css", ".scss", ".sass", ".less", ".styl"}
TEMPLATE_EXT = {".html", ".htm", ".twig", ".jinja", ".jinja2", ".j2", ".ejs", ".hbs", ".mustache", ".erb", ".njk"}
COMPONENT_EXT = {".jsx", ".tsx", ".vue", ".svelte"}
CONTRACT_RX = re.compile(r"(?i)(\.proto|\.avsc|\.graphqls?|\.gql)$|(^|/)(openapi|swagger|asyncapi)[\w.-]*\.(ya?ml|json)$|"
                         r"(^|/)pacts?/[\w./-]+\.json$")
DEPENDENCY_NAMES = {"package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "requirements.txt", "poetry.lock",
                    "pipfile", "pipfile.lock", "pyproject.toml", "go.mod", "go.sum", "pom.xml", "build.gradle",
                    "build.gradle.kts", "gradle.lockfile", "composer.json", "composer.lock", "gemfile", "gemfile.lock",
                    "cargo.toml", "cargo.lock", "packages.lock.json", "uv.lock"}
CI_RX = re.compile(r"(?i)^(\.github/workflows/|\.gitlab-ci\.yml$|azure-pipelines\.yml$|jenkinsfile$|\.circleci/|"
                   r"bitbucket-pipelines\.yml$|makefile$|dockerfile|.*\.dockerfile$|(docker-)?compose[\w.-]*\.ya?ml$|"
                   r".*\.tf$|charts?/|helm/|k8s/|kubernetes/|deploy/)")
CONFIG_EXT = {".yml", ".yaml", ".json", ".toml", ".ini", ".properties", ".conf", ".cfg", ".env", ".xml"}
MIGRATION_RX = re.compile(r"(?i)(^|/)(database/migrations|db/migrate|db/migrations|migrations|alembic/versions|"
                          r"db/changelog|prisma/migrations|sql/migrations|schema/migrations|resources/db/migration)/|"
                          r"(^|/)V\d+(_\d+)*__[\w-]+\.sql$")
DATA_ACCESS_NAME_RX = re.compile(r"(?i)(repositor|\brepo\b|_repo\b|dao\b|mapper|quer(y|ies)|gateway|store\b|_store|persist|"
                                 r"/models?/|models\.py$|entity|entities|schema\.prisma$|\.hbm\.xml$)")
RAW_SQL_RX = re.compile(r"(?is)\b(SELECT\s+[\w*,.\s()\"`\[\]]+?\s+FROM\s+\w|INSERT\s+INTO\s+\w|UPDATE\s+[\w.\"`\[\]]+\s+SET\s|"
                        r"DELETE\s+FROM\s+\w|MERGE\s+INTO\s+\w)")
TEST_SUPPORT_RX = re.compile(r"(?i)(^|/)(conftest\.py|setup_?tests?\.\w+|test_?helpers?\.\w+|testutils?\.\w+|"
                             r"jest\.setup\.\w+|vitest\.setup\.\w+)$|(^|/)(tests?|spec|__tests__)/(fixtures|factories|support|"
                             r"helpers|utils)/")
MAPPING_FILE_RX = re.compile(r"(?i)(schema\.prisma$|\.hbm\.xml$|(^|/)orm\.xml$|(^|/)persistence\.xml$|mappers?/[\w/.-]*\.xml$|"
                             r"mapper\.xml$)")
CODE_CONFIG_RX = re.compile(r"(?i)(^|/)(config|settings|conf|configuration)(_\w+)?\.py$|(^|/)settings/[\w/]+\.py$|"
                            r"(^|/)config/[\w/]+\.(py|php|rb|js|ts|exs)$")
CONTRACT_TEMPLATE_RX = re.compile(r"(?i)\.(json|xml)\.(erb|jbuilder|twig|j2|jinja2?|hbs|mustache|php|eex)$")
ORM_RX = re.compile(r"(@Query\b|createQuery\(|createNativeQuery\(|\.objects\.\w+\(|select_for_update\(|lockForUpdate\(|"
                    r"\bsession\.(add|merge|delete|flush)\(|JdbcTemplate|\.prepareStatement\(|\bprisma\.\w+\.\w+\(|"
                    r"session\.(query|execute)\(|\bselect\(\w+\)|DB::(table|select|statement)\(|->where\(|"
                    r"\.(findOne|findMany|findAll|findBy\w*|createQueryBuilder)\(|\bknex\(|\.raw\(|\bgorm\.|db\.(Query|Exec)\()")
# Signals are matched as whole identifier tokens (snake_case and camelCase split), so "syntax" is not
# "tax", "author" is not "auth" and "load_balancer" is not "balance".
SECURITY_TOKENS = {"auth", "authn", "authz", "authorize", "authorise", "authorization", "authorisation", "authenticate",
                   "authentication", "authenticated", "login", "logout", "signin", "signup", "password", "passwd",
                   "token", "tokens", "session", "sessions", "permission", "permissions", "role", "roles", "acl",
                   "policy", "policies", "crypto", "encrypt", "decrypt", "encryption", "signature", "secret", "secrets",
                   "tenant", "tenants", "oauth", "jwt", "csrf", "sanitize", "sanitise", "sanitizer", "credential",
                   "credentials", "mfa", "otp", "rbac"}
MONEY_TOKENS = {"price", "prices", "pricing", "amount", "amounts", "money", "currency", "currencies", "payment",
                "payments", "invoice", "invoices", "ledger", "balance", "balances", "interest", "tax", "taxes", "vat",
                "fee", "fees", "refund", "refunds", "discount", "discounts", "billing", "payout", "payouts", "wallet",
                "fx", "forex", "settlement", "chargeback", "subtotal", "total", "totals"}
CONCURRENCY_RX = re.compile(r"(?i)(\bsynchronized\b|\bmutex\b|\bLock\(|\block\(|ReentrantLock|\bsemaphore\b|"
                            r"\bgo\s+func\b|\bthreading\b|asyncio\.(gather|Lock)|FOR\s+UPDATE|SKIP\s+LOCKED|"
                            r"SERIALIZABLE|isolation[_ ]?level|optimistic|@Version\b|lock_version|select_for_update|"
                            r"lockForUpdate|sharedLock)")


def ident_tokens(text: str) -> set[str]:
    """Lower-case identifier tokens, with snake_case and camelCase split."""
    out = set()
    for word in re.findall(r"[A-Za-z][A-Za-z0-9]*", text):
        for part in re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", word).split():
            out.add(part.lower())
    return out


def signal_flags(rel: str, text: str) -> set[str]:
    """security / money / concurrency signals in a path and a text (whole file or changed lines)."""
    toks = ident_tokens(rel) | ident_tokens(text[:200_000])
    flags = set()
    if toks & SECURITY_TOKENS:
        flags.add("security")
    if toks & MONEY_TOKENS:
        flags.add("money")
    if CONCURRENCY_RX.search(text):
        flags.add("concurrency")
    return flags


def classify(rel: str, text: str) -> tuple[str, set[str]]:
    """(change type, flags) for one changed file; flags here come from the whole file."""
    low = rel.lower()
    name = low.rsplit("/", 1)[-1]
    suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    flags: set[str] = set()
    if TEST_SUPPORT_RX.search(rel):
        return "test-support", flags
    if is_test_path(rel):
        return "test", flags
    if MIGRATION_RX.search(rel):
        return "migration", flags
    if CONTRACT_RX.search(rel) or CONTRACT_TEMPLATE_RX.search(name):
        return "contract", flags
    if name in DEPENDENCY_NAMES or (name.startswith("requirements") and name.endswith(".txt")) or name.endswith(".csproj"):
        return "dependency", flags
    if CI_RX.match(low):
        return "build-ci", flags
    if MAPPING_FILE_RX.search(rel) or (suffix == ".xml" and "<mapper" in text[:5000]):
        return "data-access", signal_flags(rel, text)
    lang = language_of(Path(rel))
    in_docs = low.startswith("docs/") or "/docs/" in low
    if suffix in DOC_EXT or name.split(".")[0] in DOC_NAMES or (in_docs and lang is None):
        return "docs", flags
    if suffix in STYLE_EXT:
        return "ui-style", flags
    if suffix in TEMPLATE_EXT or name.endswith(".blade.php"):
        return "ui-template", flags
    if suffix == ".sql":
        return "sql", flags
    if lang is None:
        if suffix in CONFIG_EXT or name.startswith(".env") or "/config/" in f"/{low}" or "settings" in name:
            return "config", flags
        return "other", flags
    flags = signal_flags(rel, text)
    if CODE_CONFIG_RX.search(rel) and not RAW_SQL_RX.search(text):
        return "config", flags
    if DATA_ACCESS_NAME_RX.search(rel) or RAW_SQL_RX.search(text) or ORM_RX.search(text):
        return "data-access", flags
    if suffix in COMPONENT_EXT:
        return "ui-component", flags
    return "source", flags


# --------------------------------------------------------------------------- git

def check_ref(ref: str | None) -> None:
    """Refs are passed to git as arguments: refuse anything git would read as an option."""
    if ref is not None and (ref.startswith("-") or not ref.strip()):
        raise SystemExit(f"invalid git ref: {ref!r}")


def changed_files(root: Path, base: str | None, head: str | None, files: list[str] | None) -> list[tuple[str, str]]:
    if files:
        out = []
        for f in files:
            p = Path(f)
            rel = p.relative_to(root).as_posix() if p.is_absolute() and p.is_relative_to(root) else p.as_posix()
            out.append(("M" if (root / rel).exists() else "D", rel))
        return out
    base = base or "HEAD"
    check_ref(base)
    check_ref(head)
    args = ["diff", "--name-status", "-M", f"{base}...{head}"] if head else ["diff", "--name-status", "-M", base]
    raw = git(root, *args)
    if raw is None:
        raise SystemExit(f"git diff failed for base '{base}' — is {root} a git repository and does the ref exist? "
                         "Pass --files to analyse a list instead.")
    out = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if not parts or not parts[0]:
            continue
        status = parts[0][0]
        out.append((status, parts[-1]))
    if not head:
        untracked = git(root, "ls-files", "--others", "--exclude-standard") or ""
        out += [("A", u) for u in untracked.splitlines() if u.strip()]
    return out


def added_lines(root: Path, rel: str, base: str | None, head: str | None, status: str) -> str:
    """Added lines of a changed file (whole file for new files or when git is unavailable)."""
    if status == "A" or base is None:
        return read_text(root / rel, limit=1_000_000)
    rng = [f"{base}...{head}"] if head else [base]
    diff = git(root, "diff", "-U0", *rng, "--", rel)
    if diff is None:
        return read_text(root / rel, limit=1_000_000)
    return "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))


# --------------------------------------------------------------------------- tests and imports

def test_name_pattern(rel: str) -> re.Pattern | None:
    """Test file names that start from this file's name (test_orders_api.py, OrderServiceIT.java, orders.e2e.spec.ts)."""
    name = rel.rsplit("/", 1)[-1]
    stem = name.rpartition(".")[0].strip("_")
    if len(stem) < 2:
        return None
    s = re.escape(stem)
    return re.compile(rf"(?i)^(?:test_{s}(?:_\w+)?\.py|{s}(?:_\w+)?_test\.(?:py|go|rb)|{s}\w*?(?:Test|Tests|IT|Spec)\."
                      rf"(?:java|kt|groovy|php|cs|scala)|{s}(?:\.[\w-]+)?\.(?:test|spec)\.[cm]?[jt]sx?|{s}_spec\.rb)$")


def test_name_candidates(rel: str) -> set[str]:
    """File names a test for this source file usually has."""
    name = rel.rsplit("/", 1)[-1]
    stem, _, ext = name.rpartition(".")
    if not stem:
        return set()
    c = {f"test_{stem}.py", f"{stem}_test.py", f"{stem}_test.go", f"{stem}Test.java", f"{stem}Tests.java",
         f"{stem}IT.java", f"{stem}Test.kt", f"{stem}Tests.kt", f"{stem}Test.php", f"{stem}_spec.rb",
         f"{stem}_test.rb", f"{stem}Tests.cs", f"{stem}Test.cs"}
    for e in ("ts", "tsx", "js", "jsx", "mjs", "cjs"):
        c |= {f"{stem}.test.{e}", f"{stem}.spec.{e}"}
    return {x.lower() for x in c}


def import_graph(root: Path) -> tuple[dict[Path, set[Path]], list[Path]]:
    """Reverse import edges (imported → importers) over all source and test files, via deps.py handlers."""
    import deps  # noqa: E402  (same folder)
    by_ext: dict[str, list[Path]] = defaultdict(list)
    for f in iter_files(root):
        by_ext[f.suffix.lower()].append(f.resolve())
    reverse: dict[Path, set[Path]] = defaultdict(set)
    tests: list[Path] = []
    for _label, exts, handler in deps.HANDLERS:
        files = [f for e in exts for f in by_ext.get(e, [])]
        if not files:
            continue
        tests += [f for f in files if is_test_path(f.relative_to(root).as_posix())]
        try:
            for src, dst, _line in handler(root, files) or []:
                reverse[dst].add(src)
        except Exception:  # noqa: BLE001 — a parser failure must not stop the report
            continue
    return reverse, tests


def tests_reaching(target: Path, reverse: dict[Path, set[Path]], depth: int, test_set: set[Path]) -> dict[Path, int]:
    """Test files that import target directly or transitively, with hop counts."""
    found: dict[Path, int] = {}
    seen = {target}
    queue = deque([(target, 0)])
    # Go edges point at package directories: start from the file's directory as well.
    if target.suffix == ".go":
        seen.add(target.parent)
        queue.append((target.parent, 0))
    while queue:
        node, d = queue.popleft()
        if d >= depth:
            continue
        for importer in reverse.get(node, ()):
            if importer in seen:
                continue
            seen.add(importer)
            if importer in test_set:
                found.setdefault(importer, d + 1)
            queue.append((importer, d + 1))
    return found


# --------------------------------------------------------------------------- plan

def engine_decision(c: dict, app_engines: list[str], prod: str) -> tuple[str, str, str]:
    """(engines label, category, reason) for the database tests of a data-access or SQL change.

    A construct is tied to the engines that accept it; those are intersected with the engines the
    application references, so a construct shared with another engine does not send tests there."""
    hints = c["hints"]
    if not hints:
        return prod, "B", "Query or mapping changed — run on a real engine, not a mock or stand-in (category B)"
    accepted: dict[str, set[str]] = {}
    for engine, labels in hints.items():
        for label in labels:
            accepted.setdefault(label, set()).update(construct_engines(engine, label))
    constructs = "; ".join(sorted(accepted))[:140]
    every = set().union(*accepted.values())
    if app_engines:
        relevant = sorted(every & set(app_engines))
        if relevant:
            names = ", ".join(LABEL.get(e, e) for e in relevant)
            return names, "C", f"Engine-dependent SQL ({constructs}) — category C: run on {names}, the engine it runs on"
        others = ", ".join(LABEL.get(e, e) for e in sorted(every))
        return prod, "B", (f"The change uses constructs of {others} ({constructs}) but the application references "
                           f"{prod}: confirm the target engine, then run there")
    names = ", ".join(LABEL.get(e, e) for e in sorted(every))
    return names, "C", (f"Engine-dependent SQL ({constructs}), accepted by {names}; the production engine is UNKNOWN — "
                        "run on the one production uses")


def build_plan(changes: list[dict], db: dict) -> list[dict]:
    plan: list[dict] = []

    def add(group, cls, reason, level, engines=""):
        plan.append({"group": group, "class": cls, "reason": reason, "level": level, "engines": engines})

    types = {c["type"] for c in changes}
    app_engines = [e for e in db.get("application_engines", []) if e not in ("h2", "hsqldb", "derby")]
    prod = ", ".join(LABEL.get(e, e) for e in app_engines) or "production engine (UNKNOWN — confirm)"
    if types and types <= {"docs"}:
        add("All test levels", "Not necessary", "Documentation-only change: no code, data, configuration or contract path "
            "(confirm the diff really is documentation only)", "—")
        add("Link and spelling checks", "Optional", "Only if the project runs them", "docs")
        return plan
    for c in changes:
        rel, t = c["file"], c["type"]
        direct = [x for x, hops in c["tests"].items() if hops <= 1]
        transitive = [x for x, hops in c["tests"].items() if hops > 1]
        if c["status"] == "D" and t not in ("test",):
            add(f"Tests referencing removed `{rel}`", "Required", "A removed file breaks importers and tests that use it",
                "unit/integration")
            continue
        if t == "test":
            add(f"`{rel}`", "Required", "The test itself changed: run it and see it fail for the right reason first",
                "as written")
        elif t == "test-support":
            add(f"Tests that use `{rel}`", "Required",
                "Shared fixtures, factories or helpers changed: every test that uses them can change behaviour "
                "(for conftest.py and setup files, every test under that directory)", "as written")
        elif t in ("source", "ui-component", "data-access"):
            if direct:
                add(f"{len(direct)} test file(s) importing or named after `{rel}`", "Required",
                    "Directly exercises the changed file", "unit/component", "none (A)" if t != "data-access" else "")
            if transitive:
                add(f"{len(transitive)} test file(s) reaching `{rel}` through imports", "Recommended",
                    "Imports a module that depends on the changed file", "unit/component")
            if not c["tests"]:
                add(f"New or missing tests for `{rel}`", "Required",
                    "No test file is named after or imports this file: write tests for the changed behaviour or find "
                    "where it is covered (DI wiring and reflection are invisible to this scan)", "unit/component")
            if t == "data-access":
                eng, cat, why = engine_decision(c, app_engines, prod)
                add(f"Database tests for `{rel}`", "Required", why, "integration/database", f"{eng} ({cat})")
            whole = c.get("flag_scope") == "file"
            where = " (signal found in the file, not necessarily in the change — no diff was given)" if whole else ""
            if "concurrency" in c["flags"]:
                add(f"Concurrency test for `{rel}`", "Required" if t == "data-access" and not whole else "Recommended",
                    "Locks, isolation or concurrent execution in the changed code: interleave real transactions or "
                    "goroutines/threads (TEST-CONC-01)" + where, "integration", prod if t == "data-access" else "")
            if "security" in c["flags"]:
                add(f"Negative and abuse tests for `{rel}`", "Recommended" if whole else "Required",
                    "Security-relevant path: wrong user, wrong tenant, tampered input (TEST-SEC-01)" + where, "unit/API")
            if "money" in c["flags"]:
                add(f"Boundary tests with exact expected values for `{rel}`",
                    "Recommended" if whole or t == "ui-component" else "Required",
                    "Money or rates: rounding boundaries and maximum totals from the specification (DATA-TYPE-02)" + where,
                    "unit")
            if t == "ui-component":
                add(f"Component test of `{rel}`", "Required", "UI logic changed", "component")
        elif t == "ui-style":
            add(f"Visual or component check of the view using `{rel}`", "Recommended",
                "Styling only — affects appearance, and end-to-end selectors if class names changed", "component/e2e")
        elif t == "ui-template":
            add(f"Component or end-to-end smoke of the page rendering `{rel}`", "Recommended",
                "Markup changed: form fields, selectors and escaping (SEC-OUT-01) can break", "component/e2e")
        elif t == "sql":
            eng, cat, why = engine_decision(c, app_engines, prod)
            add(f"Database tests exercising `{rel}`", "Required", "SQL changed — " + why[0].lower() + why[1:],
                "database", f"{eng} ({cat})")
        elif t == "migration":
            add(f"Apply `{rel}` from an empty database and from the previous release", "Required",
                "Migration must apply both ways and leave old and new code working (DATA-MIG-03)", "migration", prod)
            add("`scripts/migration_lint.py` leads triaged", "Required", "Lock, rewrite and rollout risks per statement",
                "migration", prod)
            add("Rehearsal on a production-sized copy", "Recommended",
                "Needed when touched tables are large or hot — duration and locks only show at real size", "migration", prod)
        elif t == "contract":
            add(f"Contract tests for every consumer of `{rel}`", "Required",
                "Published contract changed: consumers outside this diff can break (TEST-CONTRACT-01)", "contract")
        elif t == "config":
            add(f"Startup and configuration validation for `{rel}`", "Required",
                "Configuration changes behaviour without code changes (DLV-CFG-01); test both states of any flag",
                "component")
            add("Smoke test in a production-like environment", "Recommended", "Configuration differs per environment",
                "smoke")
        elif t == "dependency":
            add(f"Unit and integration suites of modules using the dependencies in `{rel}`", "Required",
                "A dependency change affects every importer; serialisation and drivers need contract or integration tests",
                "unit/integration", prod)
            add("Full suite in the merge queue", "Recommended", "Transitive dependency changes are invisible to this scan",
                "all")
        elif t == "build-ci":
            add(f"Full pipeline run for `{rel}`", "Required", "Build or CI definition changed: every stage must still run "
                "and report", "all")
    has_logic = any(c["type"] in ("source", "ui-component") for c in changes)
    has_data = any(c["type"] in ("data-access", "sql", "migration") for c in changes)
    db_adjacent = bool(types & {"dependency", "config", "build-ci", "other"}) or \
        any("concurrency" in c["flags"] for c in changes)
    if has_logic and not has_data and not db_adjacent:
        add("Database engine matrix", "Not necessary",
            "No query, mapping, SQL or migration changed: DB-free logic needs no engine runs (category A)", "—")
    if types and types <= {"ui-style", "ui-template", "docs"}:
        add("Unit, database and contract suites", "Not necessary",
            "Presentation-only change: no logic, data or contract path", "—")
    if len(app_engines) > 1 and has_data:
        add("Data-access suite on every supported engine", "Recommended",
            f"Several engines referenced ({prod}): if the product supports them all, category D applies", "database",
            f"{prod} (D)")
    add("Full suite at the merge queue, a scheduled build or release", "Recommended",
        "Safety net for what static selection cannot see (S8 §10.1.6)", "all")
    return plan


def scan(root: Path, base: str | None, head: str | None, files: list[str] | None, depth: int) -> dict:
    root = root.resolve()
    base = None if files else (base or "HEAD")
    changes_raw = changed_files(root, base, head, files)
    reverse, test_files = import_graph(root)
    test_set = set(test_files)
    tests_by_name: dict[str, list[Path]] = defaultdict(list)
    for t in test_files:
        tests_by_name[t.name.lower()].append(t)
    changes = []
    for status, rel in changes_raw:
        path = (root / rel)
        text = read_text(path, limit=1_000_000) if path.is_file() else ""
        ctype, flags = classify(rel, text)
        tests: dict[str, int] = {}
        engines, hints = [], {}
        flag_scope = "file"
        if ctype in ("source", "ui-component", "data-access"):
            for cand in test_name_candidates(rel):
                for t in tests_by_name.get(cand, []):
                    tests[t.relative_to(root).as_posix()] = 1
            pattern = test_name_pattern(rel)
            if pattern:
                for t in test_files:
                    if pattern.match(t.name):
                        tests[t.relative_to(root).as_posix()] = 1
            if not files and path.is_file() and status != "A":
                flags = signal_flags(rel, added_lines(root, rel, base, head, status))   # what the change touches
                flag_scope = "change"
            if path.is_file():
                for t, hops in tests_reaching(path.resolve(), reverse, depth, test_set).items():
                    key = t.relative_to(root).as_posix()
                    tests[key] = min(hops, tests.get(key, hops))
        if ctype in ("data-access", "sql", "migration") and path.is_file():
            added = added_lines(root, rel, base, head, status) if not files else text
            hints = dialect_hints(added, code=not rel.lower().endswith(".sql"))
            engines = sorted(hints)
        if status == "A":
            flag_scope = "change"                      # a new file is all change
        changes.append({"file": rel, "status": status, "type": ctype, "flags": sorted(flags), "flag_scope": flag_scope,
                        "tests": tests, "engines": engines, "hints": hints})
    db = detect_databases(root)
    plan = build_plan(changes, db)
    gaps = [c["file"] for c in changes if c["type"] in ("source", "data-access") and not c["tests"] and c["status"] != "D"]
    return {"root": str(root), "base": base, "head": head, "changes": changes, "plan": plan, "gaps": gaps,
            "databases": {"status": db["status"], "application_engines": db["application_engines"],
                          "test_engines": db["test_engines"], "versions": db["versions"], "notes": db["notes"]}}


def to_markdown(res: dict) -> str:
    rng = f"{res['base']}...{res['head']}" if res["head"] else (res["base"] or "files given")
    out = [f"# Test-impact leads: `{res['root']}` ({rng})", "",
           "**These are LEADS for a test plan (references/testing/selection.md), not the plan.** Static imports miss "
           "dependency injection, reflection, configuration and SQL built at run time; confirm each group, add what "
           "the scan cannot see, and record the plan before running.", ""]
    if not res["changes"]:
        return "\n".join(out + ["No changed files found."]) + "\n"
    out += ["## Changed files", "", "| File | Status | Type | Flags | Engine-specific SQL | Tests found |", "|---|---|---|---|---|---|"]
    for c in res["changes"]:
        eng = ", ".join(LABEL.get(e, e) for e in c["engines"]) or "—"
        direct = sum(1 for h in c["tests"].values() if h <= 1)
        trans = len(c["tests"]) - direct
        tests = f"{direct} direct, {trans} via imports" if c["tests"] else ("—" if c["type"] not in ("source", "data-access", "ui-component") else "none")
        out.append(f"| `{c['file']}` | {c['status']} | {c['type']} | {', '.join(c['flags']) or '—'} | {eng} | {tests} |")
    out += ["", "## Proposed test groups", "", "| Group | Class | Level | Engines | Reason |", "|---|---|---|---|---|"]
    order = {"Required": 0, "Recommended": 1, "Optional": 2, "Not necessary": 3}
    for p in sorted(res["plan"], key=lambda x: order.get(x["class"], 9)):
        out.append(f"| {p['group']} | {p['class']} | {p['level']} | {p['engines'] or '—'} | {p['reason']} |")
    if res["gaps"]:
        out += ["", "## Changed source files with no test found", ""] + [f"- `{g}`" for g in res["gaps"]]
    mapped = {t for c in res["changes"] for t in c["tests"]}
    if mapped:
        out += ["", "## Test files found", ""] + [f"- `{t}`" for t in sorted(mapped)[:60]]
        if len(mapped) > 60:
            out.append(f"- … {len(mapped) - 60} more (use --json)")
    db = res["databases"]
    out += ["", "## Database engines", ""]
    if db["status"] == "UNKNOWN":
        out.append("- **UNKNOWN** — no configuration, driver, container or test reference found; ask before choosing engines.")
    else:
        out.append(f"- Application: {', '.join(LABEL.get(e, e) for e in db['application_engines']) or 'none found'} · "
                   f"tests: {', '.join(LABEL.get(e, e) for e in db['test_engines']) or 'none found'}")
        out += [f"- {n}" for n in db["notes"]]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="repository root")
    p.add_argument("--base", help="git ref to compare with (default HEAD)")
    p.add_argument("--head", help="compare base...head instead of base with the working tree")
    p.add_argument("--files", nargs="+", help="analyse these files as changed instead of asking git")
    p.add_argument("--depth", type=int, default=3, help="import hops to follow (default 3)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    res = scan(root, args.base, args.head, args.files, args.depth)
    print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else to_markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
