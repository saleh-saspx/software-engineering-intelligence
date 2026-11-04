#!/usr/bin/env python3
"""First-look inventory of a repository.

Reports languages and size, detected frameworks, tests, CI, infrastructure, migrations,
documentation/ADRs, tooling configs, lockfiles, risky committed files and git activity.
It reads manifests and file names only — it does not judge code quality.

Usage: repo_survey.py PATH [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (SOURCE_LANGS, git, is_generated, is_test_path, iter_files,  # noqa: E402
                     language_of, md_table, read_text, sloc)

FRAMEWORK_MARKERS = {
    # manifest file -> list of (regex on content, framework label)
    "package.json": [(r'"react"\s*:', "React"), (r'"next"\s*:', "Next.js"), (r'"vue"\s*:', "Vue"),
                     (r'"@angular/core"\s*:', "Angular"), (r'"svelte"\s*:', "Svelte"),
                     (r'"express"\s*:', "Express"), (r'"@nestjs/core"\s*:', "NestJS"),
                     (r'"fastify"\s*:', "Fastify"), (r'"typescript"\s*:', "TypeScript toolchain"),
                     (r'"jest"\s*:', "Jest"), (r'"vitest"\s*:', "Vitest"),
                     (r'"@playwright/test"\s*:', "Playwright"), (r'"cypress"\s*:', "Cypress")],
    "composer.json": [(r'"laravel/framework"\s*:', "Laravel"), (r'"symfony/framework-bundle"\s*:', "Symfony"),
                      (r'"phpunit/phpunit"\s*:', "PHPUnit"), (r'"pestphp/pest"\s*:', "Pest"),
                      (r'"(?:larastan/larastan|nunomaduro/larastan|phpstan/phpstan)"\s*:', "PHPStan"),
                      (r'"vimeo/psalm"\s*:', "Psalm"), (r'"laravel/pint"\s*:', "Pint")],
    "pom.xml": [(r"spring-boot", "Spring Boot"), (r"junit-jupiter|<artifactId>junit</artifactId>", "JUnit"),
                (r"testcontainers", "Testcontainers"), (r"archunit", "ArchUnit"),
                (r"lombok", "Lombok"), (r"flyway", "Flyway"), (r"liquibase", "Liquibase")],
    "build.gradle": [(r"spring-boot|org\.springframework\.boot", "Spring Boot"), (r"junit", "JUnit"),
                     (r"kotlin", "Kotlin"), (r"testcontainers", "Testcontainers"), (r"flyway", "Flyway")],
    "build.gradle.kts": [(r"spring-boot|org\.springframework\.boot", "Spring Boot"), (r"junit", "JUnit"),
                         (r"kotlin", "Kotlin"), (r"testcontainers", "Testcontainers")],
    "go.mod": [(r"github\.com/gin-gonic/gin", "Gin"), (r"github\.com/labstack/echo", "Echo"),
               (r"github\.com/go-chi/chi", "chi"), (r"github\.com/gofiber/fiber", "Fiber"),
               (r"gorm\.io/gorm", "GORM"), (r"github\.com/stretchr/testify", "testify")],
    "pyproject.toml": [(r"\bdjango\b", "Django"), (r"\bflask\b", "Flask"), (r"\bfastapi\b", "FastAPI"),
                       (r"\bpytest\b", "pytest"), (r"\bsqlalchemy\b", "SQLAlchemy"),
                       (r"\[tool\.ruff", "ruff"), (r"\[tool\.mypy", "mypy"), (r"\bpydantic\b", "Pydantic")],
    "requirements.txt": [(r"(?im)^django\b", "Django"), (r"(?im)^flask\b", "Flask"),
                         (r"(?im)^fastapi\b", "FastAPI"), (r"(?im)^pytest\b", "pytest"),
                         (r"(?im)^sqlalchemy\b", "SQLAlchemy")],
    "Gemfile": [(r"['\"]rails['\"]", "Rails"), (r"rspec", "RSpec")],
    "Cargo.toml": [(r"\[package\]", "Rust crate"), (r"tokio", "Tokio"), (r"actix-web", "Actix"), (r"axum", "Axum")],
}
CI_PATTERNS = [".github/workflows/", ".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml",
               ".circleci/config.yml", "bitbucket-pipelines.yml", ".travis.yml", ".drone.yml"]
LOCKFILES = {
    "package.json": ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock"],
    "composer.json": ["composer.lock"],
    "pyproject.toml": ["poetry.lock", "uv.lock", "pdm.lock", "requirements.lock", "Pipfile.lock"],
    "Pipfile": ["Pipfile.lock"],
    "go.mod": ["go.sum"],
    "Gemfile": ["Gemfile.lock"],
    "Cargo.toml": ["Cargo.lock"],
}
TOOL_CONFIGS = {
    "ESLint": [r"^\.eslintrc", r"^eslint\.config\."], "Prettier": [r"^\.prettierrc", r"^prettier\.config\."],
    "TypeScript config": [r"^tsconfig.*\.json$"], "ruff": [r"^ruff\.toml$", r"^\.ruff\.toml$"],
    "mypy": [r"^mypy\.ini$", r"^\.mypy\.ini$"], "pyright": [r"^pyrightconfig\.json$"],
    "flake8": [r"^\.flake8$"], "golangci-lint": [r"^\.golangci\.ya?ml$"],
    "PHPStan": [r"^phpstan\.neon(\.dist)?$"], "Psalm": [r"^psalm\.xml(\.dist)?$"],
    "PHP-CS-Fixer": [r"^\.php-cs-fixer"], "Pint": [r"^pint\.json$"], "PHPUnit": [r"^phpunit\.xml(\.dist)?$"],
    "Checkstyle": [r"^checkstyle.*\.xml$"], "EditorConfig": [r"^\.editorconfig$"],
    "pre-commit": [r"^\.pre-commit-config\.ya?ml$"], "Renovate": [r"^renovate\.json5?$"],
    "Dependabot": [r"^dependabot\.ya?ml$"], "gitleaks": [r"^\.gitleaks\.toml$"],
    "RuboCop": [r"^\.rubocop\.yml$"], "SonarQube": [r"^sonar-project\.properties$"],
    "dependency-cruiser": [r"^\.dependency-cruiser"], "deptrac": [r"^deptrac\.ya?ml$"],
    "import-linter": [r"^\.importlinter$"],
}
RISKY_NAMES = [
    (r"^\.env$", "committed .env file (may contain secrets)"),
    (r"^\.env\.(?!example$|sample$|dist$|template$)[\w.-]+$", "committed environment file"),
    (r"^id_(rsa|dsa|ecdsa|ed25519)$", "private SSH key"),
    (r"\.(pem|key|p12|pfx|jks|keystore)$", "key/certificate store"),
    (r"^credentials(\.json)?$", "credentials file"),
    (r"\.(sql|dump)\.gz$|\.dump$", "database dump"),
    (r"\.(bak|old|orig|swp)$|~$", "backup/editor file (WSTG-CONF-04)"),
]
MIGRATION_DIRS = ["database/migrations", "db/migrate", "migrations", "alembic/versions",
                  "src/main/resources/db/migration", "src/main/resources/db/changelog", "prisma/migrations"]
ADR_DIRS = ["docs/adr", "doc/adr", "adr", "docs/decisions", "docs/architecture/decisions",
            "architecture/decisions", "docs/adrs"]


def survey(root: Path) -> dict:
    root = root.resolve()
    lang_files: Counter = Counter()
    lang_sloc: Counter = Counter()
    test_files: Counter = Counter()
    generated = 0
    largest: list[tuple[int, str]] = []
    frameworks: set[str] = set()
    manifests: list[str] = []
    ci: set[str] = set()
    infra: Counter = Counter()
    tool_configs: set[str] = set()
    risky: list[str] = []
    docs: list[str] = []
    names_present: dict[str, set[str]] = defaultdict(set)  # dir -> file names
    migrations: Counter = Counter()

    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        name = path.name
        names_present[str(path.parent.relative_to(root).as_posix())].add(name)
        # manifests / frameworks
        if name in FRAMEWORK_MARKERS or name.startswith("requirements") and name.endswith(".txt"):
            key = "requirements.txt" if name.startswith("requirements") else name
            manifests.append(rel)
            text = read_text(path)
            for pattern, label in FRAMEWORK_MARKERS.get(key, []):
                if re.search(pattern, text, flags=re.I):
                    frameworks.add(label)
        if name.endswith(".csproj"):
            manifests.append(rel)
            frameworks.add(".NET project")
        for pat in CI_PATTERNS:
            if rel.startswith(pat) or rel == pat or rel.endswith("/" + pat):
                ci.add(pat.rstrip("/"))
        if name in ("Dockerfile",) or name.startswith("Dockerfile.") or name.endswith(".dockerfile"):
            infra["Dockerfile"] += 1
        if re.match(r"^(docker-)?compose(\.[\w-]+)?\.ya?ml$", name):
            infra["Compose file"] += 1
        if name.endswith(".tf"):
            infra["Terraform"] += 1
        if name == "Chart.yaml":
            infra["Helm chart"] += 1
        if name.endswith((".yaml", ".yml")) and ("k8s" in rel or "kubernetes" in rel or "manifests" in rel):
            infra["Kubernetes manifest (by path)"] += 1
        for tool, pats in TOOL_CONFIGS.items():
            if any(re.search(p, name) for p in pats):
                tool_configs.add(tool)
        if rel == "pyproject.toml":
            t = read_text(path)
            if "[tool.ruff" in t:
                tool_configs.add("ruff")
            if "[tool.mypy" in t:
                tool_configs.add("mypy")
        for pat, why in RISKY_NAMES:
            if re.search(pat, name):
                risky.append(f"{rel} — {why}")
        lower = rel.lower()
        if re.match(r"^(readme|contributing|changelog|security|architecture)(\.\w+)?$", name.lower()) and "/" not in rel:
            docs.append(rel)
        for mdir in MIGRATION_DIRS:
            if lower.startswith(mdir + "/") or f"/{mdir}/" in f"/{lower}":
                migrations[mdir] += 1
        lang = language_of(path)
        if not lang:
            continue
        text = read_text(path)
        if is_generated(text):
            generated += 1
            continue
        n = sloc(text)
        lang_files[lang] += 1
        lang_sloc[lang] += n
        if lang in SOURCE_LANGS:
            if is_test_path(rel):
                test_files[lang] += 1
            largest.append((n, rel))

    largest.sort(reverse=True)
    adrs = []
    for d in ADR_DIRS:
        p = root / d
        if p.is_dir():
            adrs.append(f"{d}/ ({sum(1 for _ in p.glob('*.md'))} md files)")
    lock_status = []
    for directory, files in names_present.items():
        for manifest, locks in LOCKFILES.items():
            if manifest in files:
                found = [lf for lf in locks if lf in files]
                where = f"{directory}/{manifest}" if directory != "." else manifest
                lock_status.append((where, ", ".join(found) if found else "MISSING"))

    git_info = None
    if (root / ".git").exists():
        count = git(root, "rev-list", "--count", "HEAD")
        first = git(root, "log", "--reverse", "--format=%ad", "--date=short")
        last = git(root, "log", "-1", "--format=%ad", "--date=short")
        authors = git(root, "shortlog", "-sne", "HEAD")
        recent = git(root, "rev-list", "--count", "--since=90 days ago", "HEAD")
        git_info = {
            "commits": int(count.strip()) if count and count.strip().isdigit() else None,
            "first_commit": first.splitlines()[0] if first else None,
            "last_commit": last.strip() if last else None,
            "authors": len(authors.strip().splitlines()) if authors else None,
            "commits_last_90_days": int(recent.strip()) if recent and recent.strip().isdigit() else None,
        }

    src_files = sum(c for lang, c in lang_files.items() if lang in SOURCE_LANGS)
    tests_total = sum(test_files.values())
    return {
        "root": str(root),
        "languages": [{"language": lang, "files": lang_files[lang], "sloc": lang_sloc[lang],
                       "test_files": test_files.get(lang, 0)} for lang, _ in lang_sloc.most_common()],
        "source_files": src_files,
        "test_files": tests_total,
        "test_file_ratio": round(tests_total / max(1, src_files - tests_total), 2),
        "generated_files_skipped": generated,
        "frameworks_and_tools_detected": sorted(frameworks),
        "manifests": sorted(manifests),
        "lockfiles": lock_status,
        "ci": sorted(ci),
        "infrastructure": dict(infra),
        "tool_configs": sorted(tool_configs),
        "migrations": dict(migrations),
        "docs": sorted(docs),
        "adr_dirs": adrs,
        "risky_committed_files": risky,
        "largest_source_files": [{"path": p, "sloc": n} for n, p in largest[:10]],
        "git": git_info,
    }


def to_markdown(s: dict) -> str:
    out = [f"# Repository survey: `{s['root']}`", "",
           "_Inventory from file names and manifests only — not a quality judgement._", ""]
    out += ["## Languages", "", md_table(["Language", "Files", "Non-blank lines", "Test files"],
            [[r["language"], r["files"], r["sloc"], r["test_files"]] for r in s["languages"]]), ""]
    out.append(f"Source files: {s['source_files']} · test files: {s['test_files']} "
               f"(test:non-test ratio {s['test_file_ratio']}) · generated files skipped: {s['generated_files_skipped']}")
    out += ["", "## Frameworks and tools detected", "",
            ", ".join(s["frameworks_and_tools_detected"]) or "none detected", ""]
    out += ["## Manifests and lockfiles", ""]
    out += [f"- {m}" for m in s["manifests"]] or ["- none found"]
    if s["lockfiles"]:
        out += ["", md_table(["Manifest", "Lockfile"], [[a, b] for a, b in s["lockfiles"]])]
    out += ["", "## Delivery and operations", "",
            f"- CI: {', '.join(s['ci']) or 'none found'}",
            f"- Infrastructure: {', '.join(f'{k} ×{v}' for k, v in s['infrastructure'].items()) or 'none found'}",
            f"- Tool configs: {', '.join(s['tool_configs']) or 'none found'}",
            f"- Migrations: {', '.join(f'{k} ({v} files)' for k, v in s['migrations'].items()) or 'none found'}",
            "", "## Documentation", "",
            f"- Top-level docs: {', '.join(s['docs']) or 'none'}",
            f"- ADR directories: {', '.join(s['adr_dirs']) or 'none found'}", ""]
    out += ["## Risky committed files", ""]
    out += [f"- {r}" for r in s["risky_committed_files"]] or ["- none matched (name-based check only)"]
    out += ["", "## Largest source files", "",
            md_table(["Path", "Non-blank lines"], [[r["path"], r["sloc"]] for r in s["largest_source_files"]]), ""]
    g = s["git"]
    out += ["## Git activity", ""]
    if g:
        out += [f"- Commits: {g['commits']} ({g['first_commit']} → {g['last_commit']}), "
                f"authors: {g['authors']}, commits in last 90 days: {g['commits_last_90_days']}"]
    else:
        out += ["- No git history available (hotspot and churn analysis will be limited)."]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path")
    p.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    args = p.parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    result = survey(root)
    print(json.dumps(result, indent=2) if args.json else to_markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
