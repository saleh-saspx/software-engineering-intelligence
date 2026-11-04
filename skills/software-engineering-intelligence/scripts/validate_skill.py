#!/usr/bin/env python3
"""Self-validation for this skill, treated as a software artifact.

Checks:
  structure    frontmatter (Agent Skills spec), name = folder, one SKILL.md, line/token budgets
  rules        rule catalog schema, IDs, levels, provenance, sources, related links (rules.py)
  index        references/rules/index.md is in sync with the catalog
  principles   P-xx entries complete; referenced rules/principles/sources exist
  references   every rule ID mentioned anywhere exists; T-xx tensions referenced exist
  links        relative links and backticked skill paths resolve
  reachability every reference/asset/script is reachable from SKILL.md
  duplicates   near-duplicate rule titles
  templates    required headings present
  scripts      compile and respond to --help
  evals        case folders follow the test-case layout
  budget       approximate token cost per file

Usage: validate_skill.py [--json] [--strict]   (exit 1 on errors; --strict also fails on warnings)
"""
from __future__ import annotations

import argparse
import difflib
import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rules import (ID_TOKEN_RE, RULES_DIR, SKILL_ROOT, check as check_rules,  # noqa: E402
                   parse_rules, registered_sources, render_index)

ROOT = SKILL_ROOT
ALLOWED_FM = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
PATH_IN_SPAN_RE = re.compile(
    r"(?:(?<=\s)|^)((?:\.\./|references/|scripts/|assets/|evals/|rules/|workflows/|languages/|templates/)"
    r"[\w./{},*-]+|[\w-]+\.(?:md|py))(?=\s|$)")
PROJECT_FILE_NAMES = {"README.md", "CONTRIBUTING.md", "CHANGELOG.md", "SECURITY.md", "ARCHITECTURE.md",
                      "main.py", "manage.py", "setup.py", "conftest.py", "__init__.py", "settings.py", "urls.py"}


def path_tokens(text: str) -> set[str]:
    """Skill-relative paths mentioned inside backtick spans."""
    out = set()
    for span in BACKTICK_RE.findall(text):
        for tok in PATH_IN_SPAN_RE.findall(span.strip()):
            if tok in PROJECT_FILE_NAMES or "<" in tok:
                continue
            out.add(tok)
    return out
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
P_HEADER_RE = re.compile(r"^### (P-\d\d) (.+)$", re.M)
P_FIELDS = ["stmt", "src", "intent", "adopted", "rules", "limits", "rel"]


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: dict[str, object] = {}

    def err(self, area, msg):
        self.errors.append(f"[{area}] {msg}")

    def warn(self, area, msg):
        self.warnings.append(f"[{area}] {msg}")


def md_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if "evals" not in p.relative_to(ROOT).parts[:1])


def check_structure(rep: Report):
    import yaml  # PyYAML is available in Claude environments; fall back to a minimal parser if not
    skill = ROOT / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        rep.err("structure", "SKILL.md has no YAML frontmatter")
        return
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception as e:  # noqa: BLE001
        rep.err("structure", f"invalid YAML frontmatter: {e}")
        return
    extra = set(fm) - ALLOWED_FM
    if extra:
        rep.err("structure", f"unexpected frontmatter keys: {sorted(extra)}")
    name, desc = str(fm.get("name", "")), str(fm.get("description", ""))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        rep.err("structure", f"invalid name '{name}'")
    if name != ROOT.name:
        rep.warn("structure", f"name '{name}' differs from folder '{ROOT.name}'")
    if not desc or len(desc) > 1024 or "<" in desc or ">" in desc:
        rep.err("structure", f"description invalid (length {len(desc)}, max 1024, no angle brackets)")
    lines = text.count("\n") + 1
    rep.info["skill_md_lines"] = lines
    rep.info["description_chars"] = len(desc)
    if lines > 500:
        rep.err("structure", f"SKILL.md has {lines} lines (limit 500)")
    elif lines > 400:
        rep.warn("structure", f"SKILL.md has {lines} lines (aim for under 400)")
    nested = [p for p in ROOT.rglob("SKILL.md") if p != skill and p.relative_to(ROOT).parts[0] != "evals"]
    if nested:
        rep.err("structure", f"extra SKILL.md files would be rejected on upload: {nested}")


def check_rule_catalog(rep: Report):
    rules, parse_errors = parse_rules()
    errors, warnings = check_rules(rules, parse_errors)
    for e in errors:
        rep.err("rules", e)
    for w in warnings:
        rep.warn("rules", w)
    rep.info["rules"] = len(rules)
    current = (RULES_DIR / "index.md").read_text(encoding="utf-8") if (RULES_DIR / "index.md").exists() else ""
    if current != render_index(rules):
        rep.err("index", "references/rules/index.md is out of date — run: python scripts/rules.py index --write")
    # near-duplicate titles
    titles = [(r.id, r.title.lower()) for r in rules]
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            ratio = difflib.SequenceMatcher(None, titles[i][1], titles[j][1]).ratio()
            if ratio > 0.85:
                rep.warn("duplicates", f"similar titles {titles[i][0]} / {titles[j][0]} ({ratio:.2f})")
    return {r.id for r in rules}


def check_principles(rep: Report, rule_ids: set[str]):
    path = ROOT / "references" / "principles.md"
    text = path.read_text(encoding="utf-8")
    headers = list(P_HEADER_RE.finditer(text))
    pids = {m.group(1) for m in headers}
    sources = registered_sources()
    rep.info["principles"] = len(pids)
    for i, m in enumerate(headers):
        body = text[m.end(): headers[i + 1].start() if i + 1 < len(headers) else len(text)]
        body = re.split(r"^## ", body, flags=re.M)[0]
        fields = dict(re.findall(r"^- ([a-z]+): (.*)$", body, re.M))
        for f in P_FIELDS:
            if f not in fields:
                rep.err("principles", f"{m.group(1)} missing field '{f}'")
        for rid in ID_TOKEN_RE.findall(fields.get("rules", "")):
            if rid not in rule_ids:
                rep.err("principles", f"{m.group(1)} references unknown rule {rid}")
        for pid in re.findall(r"P-\d\d", fields.get("rel", "")):
            if pid not in pids:
                rep.err("principles", f"{m.group(1)} relates to unknown {pid}")
        for s in re.findall(r"\b([SX]\d{1,2})\b", fields.get("src", "")):
            if s not in sources:
                rep.err("principles", f"{m.group(1)} cites unregistered source {s}")
        if not re.search(r"·\s*(direct|synthesized|extension|convention)", fields.get("src", "")):
            rep.err("principles", f"{m.group(1)} src lacks a provenance label")
    covered = set()
    for m in re.finditer(r"^- rules: (.*)$", text, re.M):
        covered |= set(ID_TOKEN_RE.findall(m.group(1)))
    rep.info["rules_linked_from_principles"] = len(covered & rule_ids)
    return pids


def check_references(rep: Report, rule_ids: set[str], pids: set[str]):
    km = (ROOT / "references" / "knowledge-model.md").read_text(encoding="utf-8")
    tensions = set(re.findall(r"^\| (T-\d\d) \|", km, re.M))
    for path in md_files() + sorted((ROOT / "scripts").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        if rel.endswith("security_scan.py") or rel.endswith("rules.py"):
            pass
        for rid in set(ID_TOKEN_RE.findall(text)):
            if rid not in rule_ids and not rid.startswith(("WSTG-", "ADR-")):
                rep.err("references", f"{rel}: unknown rule ID {rid}")
        for t in set(re.findall(r"\bT-\d\d\b", text)):
            if t not in tensions:
                rep.err("references", f"{rel}: unknown tension {t}")
        for p in set(re.findall(r"\bP-\d\d\b", text)):
            if p not in pids:
                rep.err("references", f"{rel}: unknown principle {p}")


def resolve_path(token: str, base: Path) -> bool:
    token = token.rstrip(".,;:)")
    if "{" in token:  # brace list like rules/{code,design}.md
        m = re.match(r"(.*)\{([^}]*)\}(.*)", token)
        return all(resolve_path(m.group(1) + part + m.group(3), base) for part in m.group(2).split(","))
    if "*" in token:
        return bool(list((ROOT if not token.startswith("..") else base).glob(token.replace("../", "", 0))))
    for start in (base, ROOT):
        if (start / token).exists():
            return True
    return False


def check_links(rep: Report):
    for path in md_files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        tokens = path_tokens(text) | {t for t in MD_LINK_RE.findall(text) if "://" not in t}
        for tok in sorted(tokens):
            if "<" in tok or tok.endswith("/") and resolve_path(tok, path.parent):
                continue
            if not resolve_path(tok, path.parent):
                rep.err("links", f"{rel}: path does not resolve: {tok}")


def check_reachability(rep: Report):
    graph: dict[Path, set[Path]] = {}
    files = [p for p in ROOT.rglob("*") if p.is_file() and "evals" not in p.relative_to(ROOT).parts[:1]
             and "__pycache__" not in p.parts]
    for f in files:
        if f.suffix not in (".md",):
            continue
        text = f.read_text(encoding="utf-8")
        out = set()
        for tok in path_tokens(text) | set(MD_LINK_RE.findall(text)):
            tok = tok.rstrip(".,;:)")
            if "{" in tok:
                m = re.match(r"(.*)\{([^}]*)\}(.*)", tok)
                toks = [m.group(1) + p + m.group(3) for p in m.group(2).split(",")]
            elif "*" in tok:
                toks = [str(p.relative_to(ROOT)) for p in ROOT.glob(tok.replace("../", ""))] + \
                       [str(p.relative_to(ROOT)) for p in f.parent.glob(tok)]
            else:
                toks = [tok]
            for t in toks:
                for start in (f.parent, ROOT):
                    cand = (start / t).resolve()
                    if cand.exists():
                        out |= {cand} if cand.is_file() else set(cand.rglob("*"))
                        break
        graph[f.resolve()] = out
    seen, stack = set(), [(ROOT / "SKILL.md").resolve()]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(graph.get(cur, ()))
    for f in files:
        r = f.resolve()
        if r not in seen and f.name not in ("README.md",) and f.suffix != ".pyc":
            if f.parent.name == "scripts" and f.name.startswith("_"):
                continue
            rep.warn("reachability", f"not reachable from SKILL.md: {f.relative_to(ROOT)}")


def check_templates(rep: Report):
    req = {
        "review-report.md": ["## Summary", "## Scope", "## Verification", "## Findings"],
        "assessment-report.md": ["## Summary", "## Scope", "## Verification", "## Quality profile",
                                 "## Findings", "## Limitations"],
        "adr.md": ["## Status", "## Context", "## Decision", "## Consequences", "## Compliance"],
        "td-item.md": ["## Item", "## Register"],
        "refactoring-plan.md": ["## Safety net", "## Steps", "## Verification record"],
    }
    tdir = ROOT / "assets" / "templates"
    for name, heads in req.items():
        p = tdir / name
        if not p.exists():
            rep.err("templates", f"missing template {name}")
            continue
        t = p.read_text(encoding="utf-8")
        for h in heads:
            if h not in t:
                rep.err("templates", f"{name} lacks heading '{h}'")


def check_scripts(rep: Report):
    for py in sorted((ROOT / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(py), doraise=True, cfile=None)
        except py_compile.PyCompileError as e:
            rep.err("scripts", f"{py.name} does not compile: {e.msg}")
            continue
        if py.name.startswith("_"):
            continue
        try:
            res = subprocess.run([sys.executable, str(py), "--help"], capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                rep.err("scripts", f"{py.name} --help exited {res.returncode}: {res.stderr.strip()[:200]}")
        except subprocess.TimeoutExpired:
            rep.err("scripts", f"{py.name} --help timed out")
    for pyc in ROOT.rglob("__pycache__"):
        for f in pyc.glob("*"):
            f.unlink()
        pyc.rmdir()


def check_evals(rep: Report):
    edir = ROOT / "evals"
    if not edir.is_dir():
        rep.warn("evals", "no evals/ directory")
        return
    cases = [d for d in sorted(edir.iterdir()) if d.is_dir()]
    rep.info["eval_cases"] = len(cases)
    allowed_keys = {"tags", "max_turns", "timeout_seconds", "allowed_tools"}
    for d in cases:
        name = d.name
        if not re.fullmatch(r"[a-z][a-z0-9-]*", name) or name in {"results", "mocks", "node_modules", "files"}:
            rep.err("evals", f"invalid case name '{name}'")
        prompt = d / "prompt.md"
        if not prompt.exists():
            rep.err("evals", f"{name}: missing prompt.md")
        else:
            t = prompt.read_text(encoding="utf-8")
            m = re.match(r"^---\n(.*?)\n---\n(.+)", t, re.S)
            if not m:
                rep.err("evals", f"{name}: prompt.md lacks settings block")
            else:
                keys = set(re.findall(r"^(\w+):", m.group(1), re.M))
                if keys - allowed_keys:
                    rep.err("evals", f"{name}: unknown settings keys {sorted(keys - allowed_keys)}")
                if (d / "files").is_dir() and "Input files:" not in m.group(2):
                    rep.warn("evals", f"{name}: has files/ but prompt lacks an 'Input files:' line")
        case = d / "case.yaml"
        if not case.exists():
            rep.err("evals", f"{name}: missing case.yaml")
        else:
            ct = case.read_text(encoding="utf-8")
            if not re.search(r'^schema_version:\s*"[\d.]+"', ct, re.M):
                rep.err("evals", f"{name}: schema_version must be a quoted string")
            if not re.search(rf"^name:\s*{re.escape(name)}\s*$", ct, re.M):
                rep.err("evals", f"{name}: case.yaml name must equal folder name")
            if (d / "files").is_dir() and "scaffold_script" not in ct:
                rep.warn("evals", f"{name}: has files/ but no context.scaffold_script")
        junk = [x for x in d.rglob("*") if x.name in ("__pycache__", ".pytest_cache", ".DS_Store")]
        if junk:
            rep.err("evals", f"{name}: fixture contains cache/junk files (e.g. {junk[0].relative_to(d)}) that leak run state")
        graders = sorted((d / "graders").glob("*.md")) if (d / "graders").is_dir() else []
        if not graders:
            rep.err("evals", f"{name}: no graders")
        for g in graders:
            if not g.read_text(encoding="utf-8").startswith("---\ntype:"):
                rep.err("evals", f"{name}: grader {g.name} lacks the frontmatter block")


def budget(rep: Report):
    sizes = {}
    for p in md_files():
        sizes[p.relative_to(ROOT).as_posix()] = round(len(p.read_text(encoding="utf-8")) / 4)
    rep.info["approx_tokens"] = dict(sorted(sizes.items(), key=lambda kv: -kv[1]))
    rep.info["approx_tokens_total_md"] = sum(sizes.values())
    if sizes.get("SKILL.md", 0) > 6000:
        rep.warn("budget", f"SKILL.md ≈{sizes['SKILL.md']} tokens (aim ≤ 6000)")
    for k, v in sizes.items():
        if v > 9000 and k != "references/rules/index.md":
            rep.warn("budget", f"{k} ≈{v} tokens — consider splitting")
        if v > 2500 and k != "SKILL.md":
            text = (ROOT / k).read_text(encoding="utf-8")
            if not re.search(r"^## Contents|^Areas:|^## Rule schema", text, re.M):
                rep.warn("budget", f"{k} is long (≈{v} tokens) but has no Contents/Areas overview")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    rep = Report()
    check_structure(rep)
    rule_ids = check_rule_catalog(rep)
    pids = check_principles(rep, rule_ids)
    check_references(rep, rule_ids, pids)
    check_links(rep)
    check_reachability(rep)
    check_templates(rep)
    check_scripts(rep)
    check_evals(rep)
    budget(rep)
    if args.json:
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings, "info": rep.info}, indent=2, ensure_ascii=False))
    else:
        for w in rep.warnings:
            print(f"WARN  {w}")
        for e in rep.errors:
            print(f"ERROR {e}")
        info = {k: v for k, v in rep.info.items() if k != "approx_tokens"}
        print(json.dumps(info, indent=2))
        top = list(rep.info.get("approx_tokens", {}).items())[:6]
        print("largest files (≈tokens): " + ", ".join(f"{k} {v}" for k, v in top))
        print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.errors or (args.strict and rep.warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
