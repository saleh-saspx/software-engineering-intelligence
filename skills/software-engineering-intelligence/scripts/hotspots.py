#!/usr/bin/env python3
"""Rank source files by change frequency × complexity (hotspots).

Complexity:
  * Python — exact McCabe-style count per function via `ast` (decisions + 1), plus the
    largest function's complexity and length.
  * Other languages — approximate: count of decision tokens (if/for/while/case/catch/&&/||/?:)
    per file, with comments and strings stripped heuristically. Treat as a pointer, not a metric.
Churn: commits touching the file within --since (from git), and distinct authors.
Score: rank-normalised churn × rank-normalised complexity (0–1). Without git history the
ranking falls back to complexity alone and says so.

Usage: hotspots.py PATH [--since "12 months"] [--top 25] [--include-tests] [--json]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (SOURCE_LANGS, git, is_generated, is_test_path, iter_files,  # noqa: E402
                     language_of, md_table, read_text, sloc)

DECISION_RE = re.compile(
    r"\b(?:if|elif|else\s+if|elseif|for|foreach|while|case|catch|except|when|unless|until|rescue)\b"
    r"|&&|\|\||\?\?|(?<![?:<])\?(?![?.:>=\-])"
)
LINE_COMMENT_RE = re.compile(r"(//|#)[^\n]*")
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
STRING_RE = re.compile(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`", re.S)


class _PyComplexity(ast.NodeVisitor):
    DECISIONS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp,
                 ast.Assert, ast.comprehension)

    def __init__(self):
        self.functions: list[tuple[str, int, int, int]] = []  # name, line, cc, length

    def _measure(self, node) -> int:
        """Decisions + 1 for this function only (nested functions/classes are measured separately)."""
        cc = 1
        stack = list(ast.iter_child_nodes(node))
        while stack:
            sub = stack.pop()
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            stack.extend(ast.iter_child_nodes(sub))
            if isinstance(sub, self.DECISIONS):
                cc += 1
            elif isinstance(sub, ast.BoolOp):
                cc += len(sub.values) - 1
            elif hasattr(ast, "Match") and isinstance(sub, ast.match_case):
                cc += 1
        return cc

    def visit_FunctionDef(self, node):  # noqa: N802
        length = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1
        self.functions.append((node.name, node.lineno, self._measure(node), length))
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815


def python_complexity(text: str) -> dict | None:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    v = _PyComplexity()
    v.visit(tree)
    if not v.functions:
        return {"complexity": 1, "max_fn": None}
    total = sum(f[2] for f in v.functions)
    worst = max(v.functions, key=lambda f: f[2])
    return {"complexity": total, "max_fn": {"name": worst[0], "line": worst[1], "cc": worst[2], "lines": worst[3]}}


def approx_complexity(text: str, lang: str) -> int:
    code = BLOCK_COMMENT_RE.sub(" ", text)
    code = STRING_RE.sub('""', code)
    if lang in ("PHP", "Ruby", "Python", "Shell"):
        code = LINE_COMMENT_RE.sub(" ", code)
    else:
        code = re.sub(r"//[^\n]*", " ", code)
    return len(DECISION_RE.findall(code)) + 1


def churn(root: Path, since: str) -> tuple[dict[str, int], dict[str, set[str]]] | None:
    out = git(root, "log", f"--since={since}", "--no-merges", "--format=@@%an", "--name-only", timeout=120)
    if out is None:
        return None
    commits: dict[str, int] = defaultdict(int)
    authors: dict[str, set[str]] = defaultdict(set)
    author = None
    for line in out.splitlines():
        if line.startswith("@@"):
            author = line[2:]
        elif line.strip():
            commits[line.strip()] += 1
            if author:
                authors[line.strip()].add(author)
    return commits, authors


def rank_norm(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(set(values.values()))
    if len(ordered) == 1:
        return {k: (1.0 if v > 0 else 0.0) for k, v in values.items()}
    pos = {v: i / (len(ordered) - 1) for i, v in enumerate(ordered)}
    return {k: pos[v] for k, v in values.items()}


def analyse(root: Path, since: str, include_tests: bool) -> dict:
    root = root.resolve()
    git_root_out = git(root, "rev-parse", "--show-toplevel")
    git_root = Path(git_root_out.strip()) if git_root_out else None
    ch = churn(root, since) if git_root else None
    files = []
    for path in iter_files(root):
        lang = language_of(path)
        if lang not in SOURCE_LANGS:
            continue
        rel = path.relative_to(root).as_posix()
        if not include_tests and is_test_path(rel):
            continue
        text = read_text(path)
        if not text or is_generated(text):
            continue
        entry = {"path": rel, "lang": lang, "sloc": sloc(text), "max_fn": None, "exact": False}
        if lang == "Python":
            pc = python_complexity(text)
            if pc:
                entry["complexity"], entry["max_fn"], entry["exact"] = pc["complexity"], pc["max_fn"], True
            else:
                entry["complexity"] = approx_complexity(text, lang)
        else:
            entry["complexity"] = approx_complexity(text, lang)
        if ch and git_root:
            key = path.resolve().relative_to(git_root).as_posix()
            entry["commits"] = ch[0].get(key, 0)
            entry["authors"] = len(ch[1].get(key, set()))
        files.append(entry)
    cx = rank_norm({f["path"]: f["complexity"] for f in files})
    if ch:
        cm = rank_norm({f["path"]: f.get("commits", 0) for f in files})
        for f in files:
            f["score"] = round(cx[f["path"]] * cm[f["path"]], 3)
    else:
        for f in files:
            f["score"] = round(cx[f["path"]], 3)
    files.sort(key=lambda f: (f["score"], f["complexity"]), reverse=True)
    return {"root": str(root), "since": since, "git_history": bool(ch), "files": files}


def to_markdown(res: dict, top: int) -> str:
    out = [f"# Hotspots: `{res['root']}`", ""]
    if res["git_history"]:
        out.append(f"Score = rank(churn since {res['since']}) × rank(complexity). High score = changed often *and* complex.")
    else:
        out.append("**No git history available — ranked by complexity only** (interest cannot be estimated).")
    out += ["Complexity is exact (McCabe-style, per function) for Python and an approximate decision-token "
            "count elsewhere. Use the list to choose where to look, not as a verdict.", ""]
    rows = []
    for f in res["files"][:top]:
        worst = f["max_fn"]
        worst_s = f"{worst['name']} (cc {worst['cc']}, {worst['lines']} lines, L{worst['line']})" if worst else "—"
        rows.append([f["path"], f["lang"], f["sloc"], f["complexity"] if f["exact"] else f"~{f['complexity']}",
                     f.get("commits", "—"), f.get("authors", "—"), worst_s, f["score"]])
    out.append(md_table(["File", "Lang", "Lines", "Complexity", "Commits", "Authors", "Most complex function", "Score"], rows))
    out.append(f"\n{len(res['files'])} source files analysed; showing top {min(top, len(res['files']))}.")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path")
    p.add_argument("--since", default="12 months", help="git history window, e.g. '6 months' (default 12 months)")
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--include-tests", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    res = analyse(root, args.since, args.include_tests)
    if args.json:
        res["files"] = res["files"][: args.top]
        print(json.dumps(res, indent=2))
    else:
        print(to_markdown(res, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
