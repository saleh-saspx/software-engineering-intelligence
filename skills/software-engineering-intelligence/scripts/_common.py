"""Shared helpers for the analysis scripts (standard library only)."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# Directories never analysed: VCS, dependencies, build output, caches, IDE folders.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "bower_components", ".venv", "venv",
    "env", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "dist",
    "build", "target", "out", "bin", "obj", ".gradle", ".idea", ".vscode", "coverage",
    ".next", ".nuxt", ".svelte-kit", ".turbo", ".cache", "storage", "Pods", "DerivedData",
    ".terraform", "site-packages",
}

LANG_BY_EXT = {
    ".py": "Python", ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".go": "Go", ".php": "PHP", ".rb": "Ruby", ".rs": "Rust", ".cs": "C#", ".c": "C",
    ".h": "C/C++ header", ".cc": "C++", ".cpp": "C++", ".hpp": "C++", ".swift": "Swift",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".vue": "Vue", ".svelte": "Svelte",
    ".sql": "SQL", ".sh": "Shell", ".bash": "Shell", ".ps1": "PowerShell",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".blade.php": "Blade",
    ".tf": "Terraform", ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir",
}
SOURCE_LANGS = {
    "Python", "Java", "Kotlin", "Scala", "Go", "PHP", "Ruby", "Rust", "C#", "C", "C++",
    "C/C++ header", "Swift", "JavaScript", "TypeScript", "Vue", "Svelte", "Dart", "Elixir",
}


def language_of(path: Path) -> str | None:
    name = path.name.lower()
    if name.endswith(".blade.php"):
        return "Blade"
    if name.endswith(".min.js") or name.endswith(".min.css"):
        return None
    return LANG_BY_EXT.get(path.suffix.lower())


def iter_files(root: Path, extra_skip: set[str] | None = None):
    """Yield files under root, skipping dependency/build directories."""
    skip = SKIP_DIRS | (extra_skip or set())
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.endswith(".egg-info")]
        for f in filenames:
            yield Path(dirpath) / f


def read_text(path: Path, limit: int = 2_000_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def is_test_path(rel: str) -> bool:
    r = rel.replace("\\", "/").lower()
    name = r.rsplit("/", 1)[-1]
    return (
        "/test/" in f"/{r}" or "/tests/" in f"/{r}" or "/__tests__/" in f"/{r}"
        or "/spec/" in f"/{r}" or name.startswith("test_") or name.endswith("_test.go")
        or name.endswith("_test.py") or ".test." in name or ".spec." in name
        or name.endswith("test.java") or name.endswith("tests.java") or name.endswith("test.php")
        or name.endswith("test.kt") or name.endswith("tests.cs") or name.endswith("_spec.rb")
    )


GENERATED_RE = re.compile(r"(?i)@generated\b|\bdo not edit\b|^// code generated .* do not edit|\bauto-?generated\b")


def is_generated(text_head: str) -> bool:
    return bool(GENERATED_RE.search(text_head[:600]))


def sloc(text: str) -> int:
    """Non-blank lines (comments included; cheap and language-neutral)."""
    return sum(1 for line in text.splitlines() if line.strip())


def git(root: Path, *args: str, timeout: int = 60) -> str | None:
    """Run a git command in root; return stdout or None if git/history is unavailable."""
    try:
        res = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                             text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if res.returncode != 0:
        return None
    return res.stdout


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |")
    return "\n".join(out)
