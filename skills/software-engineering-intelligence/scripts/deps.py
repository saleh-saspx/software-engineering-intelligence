#!/usr/bin/env python3
"""Module dependency graph: cycles (ADP), instability (SDP) and forbidden directions.

Resolves *internal* imports for Python (ast), JavaScript/TypeScript (relative paths, `@/`
alias, simple tsconfig `paths`), Java/Kotlin (package + imports), Go (module path from go.mod)
and PHP (namespace + `use`). External packages are ignored. Files are grouped into nodes by
directory (common source roots such as src/main/java are stripped), optionally truncated to
--depth path segments.

Limitations: dynamic imports, reflection, DI-container wiring, framework conventions and
same-package references (Java/Go) are invisible; treat results as a lower bound of coupling.

Usage:
  deps.py PATH [--depth N] [--forbid "domain->infrastructure" ...] [--include-tests]
               [--top 30] [--json | --dot]
Exit code 1 when --forbid rules are violated (useful in CI); 0 otherwise.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import is_test_path, iter_files, md_table, read_text  # noqa: E402

SOURCE_ROOT_PREFIXES = ["src/main/java/", "src/main/kotlin/", "src/test/java/", "src/test/kotlin/",
                        "src/main/scala/", "lib/", "src/"]
JS_EXTS = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"]


# ---------------------------------------------------------------- language handlers
def py_edges(root: Path, files: list[Path]):
    roots = [root] + [root / d for d in ("src", "lib") if (root / d).is_dir()]
    modmap: dict[str, Path] = {}
    for f in files:
        for r in roots:
            try:
                rel = f.relative_to(r)
            except ValueError:
                continue
            parts = list(rel.with_suffix("").parts)
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            if parts:
                modmap.setdefault(".".join(parts), f)
    for f in files:
        tree = None
        try:
            tree = ast.parse(read_text(f))
        except (SyntaxError, ValueError):
            continue
        # package of this file, for relative imports
        pkg_parts = None
        for r in roots:
            try:
                rel = f.relative_to(r)
                pkg_parts = list(rel.parent.parts)
                break
            except ValueError:
                continue
        for node in ast.walk(tree):
            targets: list[tuple[str, int]] = []
            if isinstance(node, ast.Import):
                targets = [(a.name, node.lineno) for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level and pkg_parts is not None:
                    up = pkg_parts[: len(pkg_parts) - (node.level - 1)] if node.level > 1 else pkg_parts
                    base = ".".join([*up, base] if base else up)
                for a in node.names:
                    targets.append((f"{base}.{a.name}" if base else a.name, node.lineno))
                    targets.append((base, node.lineno))
            seen = set()
            for name, line in targets:
                parts = name.split(".")
                for i in range(len(parts), 0, -1):
                    cand = ".".join(parts[:i])
                    if cand in modmap:
                        dst = modmap[cand]
                        if dst != f and (dst, line) not in seen:
                            seen.add((dst, line))
                            yield f, dst, line
                        break


def _load_tsconfig_paths(root: Path) -> list[tuple[str, list[str]]]:
    cfg = root / "tsconfig.json"
    if not cfg.is_file():
        return []
    text = re.sub(r"//[^\n]*|/\*.*?\*/", "", read_text(cfg), flags=re.S)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    opts = data.get("compilerOptions", {}) or {}
    base = opts.get("baseUrl", ".")
    out = []
    for alias, targets in (opts.get("paths") or {}).items():
        out.append((alias, [str(Path(base) / t) for t in targets]))
    return out


JS_IMPORT_RE = re.compile(
    r"""(?:import\s[^'"]*?from\s*|import\s*|export\s[^'"]*?from\s*|require\(\s*|import\(\s*)['"]([^'"]+)['"]""")


def js_edges(root: Path, files: list[Path]):
    fileset = set(files)
    aliases = _load_tsconfig_paths(root)

    def resolve(base: Path) -> Path | None:
        cands = [base] + [base.with_name(base.name + e) for e in JS_EXTS] + [base / f"index{e}" for e in JS_EXTS]
        for c in cands:
            if c in fileset:
                return c
        return None

    for f in files:
        text = read_text(f)
        for m in JS_IMPORT_RE.finditer(text):
            spec = m.group(1)
            line = text.count("\n", 0, m.start()) + 1
            targets: list[Path] = []
            if spec.startswith("."):
                targets = [(f.parent / spec).resolve()]
            elif spec.startswith("@/") or spec.startswith("~/"):
                targets = [(root / "src" / spec[2:]).resolve(), (root / spec[2:]).resolve()]
            else:
                for alias, tlist in aliases:
                    if alias.endswith("/*") and spec.startswith(alias[:-1]):
                        rest = spec[len(alias) - 1:]
                        targets += [(root / t.replace("*", rest)).resolve() for t in tlist]
                    elif alias == spec:
                        targets += [(root / t).resolve() for t in tlist]
            for t in targets:
                dst = resolve(t)
                if dst and dst != f:
                    yield f, dst, line
                    break


def jvm_edges(root: Path, files: list[Path]):
    fqn: dict[str, Path] = {}
    pkg_files: dict[str, list[Path]] = defaultdict(list)
    meta = {}
    for f in files:
        text = read_text(f)
        m = re.search(r"^[ \t]*package\s+([\w.]+)", text, flags=re.M)
        pkg = m.group(1) if m else ""
        meta[f] = (pkg, text)
        fqn[f"{pkg}.{f.stem}" if pkg else f.stem] = f
        pkg_files[pkg].append(f)
    imp = re.compile(r"^[ \t]*import\s+(?:static\s+)?([\w.]+)(\.\*)?\s*;?", flags=re.M)
    for f, (pkg, text) in meta.items():
        for m in imp.finditer(text):
            name, star = m.group(1), m.group(2)
            line = text.count("\n", 0, m.start()) + 1
            if star:
                for dst in pkg_files.get(name, []):
                    if dst != f:
                        yield f, dst, line
                continue
            parts = name.split(".")
            for i in range(len(parts), 0, -1):
                dst = fqn.get(".".join(parts[:i]))
                if dst:
                    if dst != f:
                        yield f, dst, line
                    break


def go_edges(root: Path, files: list[Path]):
    gomod = root / "go.mod"
    if not gomod.is_file():
        return
    m = re.search(r"^module\s+(\S+)", read_text(gomod), flags=re.M)
    if not m:
        return
    module = m.group(1)
    block = re.compile(r"import\s*\((.*?)\)", re.S)
    single = re.compile(r'^[ \t]*import\s+(?:[\w.]+\s+)?"([^"]+)"', re.M)
    for f in files:
        text = read_text(f)
        specs: list[tuple[str, int]] = []
        for b in block.finditer(text):
            base_line = text.count("\n", 0, b.start()) + 1
            for i, ln in enumerate(b.group(1).splitlines()):
                mm = re.search(r'"([^"]+)"', ln)
                if mm:
                    specs.append((mm.group(1), base_line + i))
        for s in single.finditer(text):
            specs.append((s.group(1), text.count("\n", 0, s.start()) + 1))
        for spec, line in specs:
            if spec == module or spec.startswith(module + "/"):
                rel_dir = spec[len(module):].lstrip("/")
                target = (root / rel_dir) if rel_dir else root
                if target.is_dir() and target.resolve() != f.parent.resolve():
                    yield f, target, line


def php_edges(root: Path, files: list[Path]):
    fqn: dict[str, Path] = {}
    meta = {}
    for f in files:
        text = read_text(f)
        m = re.search(r"^[ \t]*namespace\s+([\w\\]+)\s*;", text, flags=re.M)
        ns = m.group(1) if m else ""
        meta[f] = text
        fqn[(ns + "\\" + f.stem) if ns else f.stem] = f
    use_re = re.compile(r"^[ \t]*use\s+(?:function\s+|const\s+)?([\w\\]+)(?:\\\{([^}]*)\})?(?:\s+as\s+\w+)?\s*;", re.M)
    for f, text in meta.items():
        for m in use_re.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            names = [m.group(1)]
            if m.group(2):
                names = [m.group(1).rstrip("\\") + "\\" + n.strip().split(" as ")[0].strip()
                         for n in m.group(2).split(",") if n.strip()]
            for name in names:
                dst = fqn.get(name.lstrip("\\"))
                if dst and dst != f:
                    yield f, dst, line


HANDLERS = [
    ("Python", {".py"}, py_edges),
    ("JavaScript/TypeScript", set(JS_EXTS), js_edges),
    ("Java/Kotlin", {".java", ".kt"}, jvm_edges),
    ("Go", {".go"}, go_edges),
    ("PHP", {".php"}, php_edges),
]


# ---------------------------------------------------------------- graph
def node_of(root: Path, path: Path, depth: int | None) -> str:
    p = path if path.is_dir() else path.parent
    try:
        rel = p.resolve().relative_to(root).as_posix()
    except ValueError:
        rel = p.as_posix()
    rel = "" if rel == "." else rel
    for prefix in SOURCE_ROOT_PREFIXES:
        if (rel + "/").startswith(prefix) and len(rel) + 1 > len(prefix):
            rel = rel[len(prefix):]
            break
    if depth:
        rel = "/".join(rel.split("/")[:depth])
    return rel or "(root)"


def tarjan(graph: dict[str, set[str]]) -> list[list[str]]:
    index, low, on_stack, stack, sccs = {}, {}, set(), [], []
    counter = [0]
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))

    def strong(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in graph.get(v, ()):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                sccs.append(sorted(comp))

    for v in list(graph):
        if v not in index:
            strong(v)
    return sccs


def matches(pattern: str, node: str) -> bool:
    if any(ch in pattern for ch in "*?["):
        return fnmatch.fnmatch(node, pattern)
    return re.search(rf"(^|/){re.escape(pattern.strip('/'))}(/|$)", node) is not None


def analyse(root: Path, depth: int | None, include_tests: bool, forbid: list[str]) -> dict:
    root = root.resolve()
    by_ext: dict[str, list[Path]] = defaultdict(list)
    for f in iter_files(root):
        rel = f.relative_to(root).as_posix()
        if not include_tests and is_test_path(rel):
            continue
        by_ext[f.suffix.lower()].append(f.resolve())
    file_edges = []
    parsed = {}
    for label, exts, handler in HANDLERS:
        files = [f for e in exts for f in by_ext.get(e, [])]
        if not files:
            continue
        parsed[label] = len(files)
        file_edges += list(handler(root, files) or [])
    node_files: dict[str, int] = defaultdict(int)
    for files in by_ext.values():
        for f in files:
            node_files[node_of(root, f, depth)] += 1
    graph: dict[str, set[str]] = defaultdict(set)
    examples: dict[tuple[str, str], list[str]] = defaultdict(list)
    for src, dst, line in file_edges:
        a, b = node_of(root, src, depth), node_of(root, dst, depth)
        if a == b:
            continue
        graph[a].add(b)
        graph.setdefault(b, set())
        if len(examples[(a, b)]) < 3:
            srel = src.relative_to(root).as_posix()
            drel = dst.relative_to(root).as_posix() + ("/" if dst.is_dir() else "")
            examples[(a, b)].append(f"{srel}:{line} → {drel}")
    ca: dict[str, set[str]] = defaultdict(set)
    for a, outs in graph.items():
        for b in outs:
            ca[b].add(a)
    nodes = []
    for n in sorted(set(graph) | set(ca)):
        ce_n, ca_n = len(graph.get(n, ())), len(ca.get(n, ()))
        inst = round(ce_n / (ca_n + ce_n), 2) if (ca_n + ce_n) else None
        nodes.append({"node": n, "files": node_files.get(n, 0), "ca": ca_n, "ce": ce_n, "instability": inst})
    cycles = []
    for comp in tarjan(graph):
        cs = set(comp)
        edges = [{"from": a, "to": b, "examples": examples[(a, b)]} for a in comp for b in graph[a] if b in cs]
        cycles.append({"nodes": comp, "edges": edges})
    violations = []
    for rule in forbid:
        if "->" not in rule:
            continue
        left, right = [s.strip() for s in rule.split("->", 1)]
        for (a, b), ex in examples.items():
            if matches(left, a) and matches(right, b):
                violations.append({"rule": rule, "from": a, "to": b, "examples": ex})
    sdp = []
    inst_of = {n["node"]: n["instability"] for n in nodes}
    for a, outs in graph.items():
        for b in outs:
            ia, ib = inst_of.get(a), inst_of.get(b)
            if ia is not None and ib is not None and ib > ia + 0.25:
                sdp.append({"from": a, "to": b, "I_from": ia, "I_to": ib})
    return {"root": str(root), "depth": depth, "parsed_files": parsed, "internal_edges": len(file_edges),
            "nodes": nodes, "cycles": cycles, "violations": violations, "sdp_warnings": sdp,
            "edges": [{"from": a, "to": b, "examples": examples[(a, b)]} for a in graph for b in sorted(graph[a])]}


def to_markdown(res: dict, top: int) -> str:
    out = [f"# Dependency analysis: `{res['root']}`", ""]
    parsed = ", ".join(f"{k}: {v} files" for k, v in res["parsed_files"].items()) or "no supported files"
    out += [f"Parsed {parsed}; {res['internal_edges']} internal import edges resolved. "
            f"Node = directory{' truncated to depth ' + str(res['depth']) if res['depth'] else ''}.",
            "_Lower bound of coupling: dynamic imports, DI wiring and same-package references are not seen._", ""]
    nodes = sorted(res["nodes"], key=lambda n: (-n["ca"], -n["ce"]))[:top]
    out += ["## Nodes (by afferent coupling)", "",
            md_table(["Node", "Files", "Ca (in)", "Ce (out)", "Instability I"],
                     [[n["node"], n["files"], n["ca"], n["ce"], n["instability"]] for n in nodes]), ""]
    out += ["## Cycles (ADP, ARCH-COMP-02)", ""]
    if res["cycles"]:
        for i, c in enumerate(res["cycles"], 1):
            out.append(f"**Cycle {i}:** {' ⇄ '.join(c['nodes'])}")
            for e in c["edges"]:
                out.append(f"- {e['from']} → {e['to']}: " + "; ".join(e["examples"]))
            out.append("")
    else:
        out += ["None found between nodes at this granularity.", ""]
    if res["violations"]:
        out += ["## Forbidden-direction violations (ARCH-DEP-01)", ""]
        for v in res["violations"]:
            out.append(f"- `{v['rule']}`: {v['from']} → {v['to']} — " + "; ".join(v["examples"]))
        out.append("")
    elif res.get("forbid_rules"):
        out += ["## Forbidden-direction violations (ARCH-DEP-01)", "",
                "None for: " + ", ".join(f"`{r}`" for r in res["forbid_rules"]), ""]
    if res["sdp_warnings"]:
        out += ["## Possible SDP issues (depending on markedly less stable nodes, ARCH-COMP-03)", ""]
        for w in res["sdp_warnings"][:20]:
            out.append(f"- {w['from']} (I={w['I_from']}) → {w['to']} (I={w['I_to']})")
        out.append("")
    return "\n".join(out) + "\n"


def to_dot(res: dict) -> str:
    lines = ["digraph deps {", "  rankdir=LR; node [shape=box, fontsize=10];"]
    cyc = {n for c in res["cycles"] for n in c["nodes"]}
    for n in res["nodes"]:
        color = ', color="red"' if n["node"] in cyc else ""
        lines.append(f'  "{n["node"]}" [label="{n["node"]}\\nI={n["instability"]}"{color}];')
    for e in res["edges"]:
        lines.append(f'  "{e["from"]}" -> "{e["to"]}";')
    lines.append("}")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path")
    p.add_argument("--depth", type=int, default=None, help="truncate node paths to N segments")
    p.add_argument("--forbid", action="append", default=[], help='forbidden direction, e.g. "domain->infrastructure"')
    p.add_argument("--include-tests", action="store_true")
    p.add_argument("--top", type=int, default=30)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true")
    g.add_argument("--dot", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    res = analyse(root, args.depth, args.include_tests, args.forbid)
    res["forbid_rules"] = args.forbid
    if args.json:
        print(json.dumps(res, indent=2))
    elif args.dot:
        print(to_dot(res))
    else:
        print(to_markdown(res, args.top))
    return 1 if res["violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
