"""Shared helpers for the script test suites (standard library only)."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "software-engineering-intelligence"
SCRIPTS = SKILL / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_CONFIG_NOSYSTEM": "1",
           "HOME": tempfile.gettempdir()}


class Tree:
    """A throwaway directory tree; use as a context manager."""

    def __init__(self, files: dict[str, str] | None = None):
        self._tmp = tempfile.TemporaryDirectory(prefix="sei-test-")
        self.path = Path(self._tmp.name)
        if files:
            self.write(files)

    def write(self, files: dict[str, str]) -> "Tree":
        for rel, content in files.items():
            p = self.path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
        return self

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.path, env=GIT_ENV, check=True,
                              capture_output=True, text=True).stdout

    def commit_all(self, message: str = "c") -> None:
        if not (self.path / ".git").exists():
            self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def __enter__(self) -> "Tree":
        return self

    def __exit__(self, *exc) -> None:
        self._tmp.cleanup()


def run_script(name: str, *args: str) -> subprocess.CompletedProcess:
    """Run a script as a user would (isolated interpreter, no inherited PYTHONPATH)."""
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / name), *args], capture_output=True, text=True,
                          timeout=120)
