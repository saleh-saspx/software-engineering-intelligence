#!/usr/bin/env python3
"""Query and validate the engineering rule catalog.

The catalog lives in references/rules/*.md. Each rule is a level-3 heading
`### DOMAIN-AREA-NN · Title` followed by `- key: value` bullets; the first bullet
carries `level: … | severity: … | provenance: …`.

Usage:
  rules.py list   [--domain SEC] [--level mandatory] [--provenance direct] [--json]
  rules.py show   ID [ID ...]
  rules.py search TERM [--field signals]
  rules.py stats
  rules.py check                # schema validation, exit 1 on errors
  rules.py index [--write]      # print or rewrite references/rules/index.md

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = SKILL_ROOT / "references" / "rules"
SOURCES_FILE = SKILL_ROOT / "references" / "sources.md"

RULE_ID_RE = r"[A-Z]{2,5}-[A-Z]{2,9}-\d{2}"
HEADER_RE = re.compile(rf"^### ({RULE_ID_RE}) · (.+?)\s*$")
FIELD_RE = re.compile(r"^- ([a-z]+)(?: \([^)]*\))?: (.*)$")
ID_TOKEN_RE = re.compile(rf"\b{RULE_ID_RE}\b")
SOURCE_TOKEN_RE = re.compile(r"\b([SX]\d{1,2})\b")

LEVELS = ["mandatory", "constraint", "strong", "contextual", "optional"]
PROVENANCES = ["direct", "synthesized", "extension", "convention"]
SEVERITIES = ["blocker", "major", "minor", "nit"]
REQUIRED = ["level", "severity", "provenance", "sources", "why", "signals", "fix", "related"]
OPTIONAL = ["applies", "verify", "auto", "except", "example", "scope"]

# Which file each domain prefix must live in.
DOMAIN_FILES = {
    "CODE": "code.md", "DES": "design.md", "ARCH": "architecture.md",
    "SEC": "security.md", "TEST": "testing.md", "REL": "runtime.md",
    "PERF": "runtime.md", "DATA": "data-api.md", "API": "data-api.md",
    "DLV": "delivery.md", "TD": "techdebt.md", "REV": "practice.md",
    "AGT": "practice.md",
}
DOMAIN_NAMES = {
    "CODE": "Code", "DES": "Design", "ARCH": "Architecture", "SEC": "Security",
    "TEST": "Testing", "REL": "Reliability", "PERF": "Performance", "DATA": "Data",
    "API": "API", "DLV": "Delivery", "TD": "Technical debt", "REV": "Review conduct",
    "AGT": "Agent conduct",
}


@dataclass
class Rule:
    id: str
    title: str
    file: str
    line: int
    fields: dict = field(default_factory=dict)
    raw: str = ""

    @property
    def domain(self) -> str:
        return self.id.split("-")[0]

    def get(self, key: str, default: str = "") -> str:
        return self.fields.get(key, default)


def parse_rules(rules_dir: Path = RULES_DIR) -> tuple[list[Rule], list[str]]:
    """Parse all rule files. Returns (rules, parse_errors)."""
    rules: list[Rule] = []
    errors: list[str] = []
    for path in sorted(rules_dir.glob("*.md")):
        if path.name == "index.md":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        current: Rule | None = None
        buf: list[str] = []
        first_bullet = True
        for lineno, line in enumerate(lines, 1):
            m = HEADER_RE.match(line)
            if m:
                if current:
                    current.raw = "\n".join(buf).rstrip()
                    rules.append(current)
                current = Rule(m.group(1), m.group(2), path.name, lineno)
                buf = [line]
                first_bullet = True
                continue
            if line.startswith("## ") or line.startswith("# "):
                if current:
                    current.raw = "\n".join(buf).rstrip()
                    rules.append(current)
                    current = None
                continue
            if current is None:
                if line.startswith("### "):
                    errors.append(f"{path.name}:{lineno}: heading is not a valid rule header: {line!r}")
                continue
            buf.append(line)
            fm = FIELD_RE.match(line)
            if fm:
                key, value = fm.group(1), fm.group(2).strip()
                if first_bullet and key == "level" and " | " in value:
                    # meta line: level: x | severity: y | provenance: z
                    parts = [p.strip() for p in line[2:].split(" | ")]
                    for part in parts:
                        if ": " not in part:
                            errors.append(f"{path.name}:{lineno}: malformed meta part {part!r}")
                            continue
                        k, v = part.split(": ", 1)
                        current.fields[k.strip()] = v.strip()
                else:
                    if key in current.fields:
                        errors.append(f"{path.name}:{lineno}: duplicate field '{key}' in {current.id}")
                    current.fields[key] = value
                first_bullet = False
            elif line.strip() and not line.startswith("  "):
                errors.append(f"{path.name}:{lineno}: unexpected line inside {current.id}: {line[:60]!r}")
        if current:
            current.raw = "\n".join(buf).rstrip()
            rules.append(current)
    return rules, errors


def registered_sources(sources_file: Path = SOURCES_FILE) -> set[str]:
    text = sources_file.read_text(encoding="utf-8")
    return set(re.findall(r"^\| ([SX]\d{1,2}) \|", text, flags=re.M))


def severity_ok(value: str) -> bool:
    if value in ("—", "-"):
        return True
    parts = re.split(r"\s*[–-]\s*", value)
    return all(p in SEVERITIES for p in parts) and 1 <= len(parts) <= 2


def check(rules: list[Rule], parse_errors: list[str]) -> tuple[list[str], list[str]]:
    errors = list(parse_errors)
    warnings: list[str] = []
    ids = [r.id for r in rules]
    known = set(ids)
    sources = registered_sources()
    seen: dict[str, Rule] = {}
    titles: dict[str, str] = {}
    for r in rules:
        where = f"{r.file}:{r.line} {r.id}"
        if r.id in seen:
            errors.append(f"{where}: duplicate ID (first at {seen[r.id].file}:{seen[r.id].line})")
        seen[r.id] = r
        expected_file = DOMAIN_FILES.get(r.domain)
        if expected_file is None:
            errors.append(f"{where}: unknown domain prefix '{r.domain}'")
        elif expected_file != r.file:
            errors.append(f"{where}: domain {r.domain} belongs in {expected_file}")
        tkey = r.title.lower()
        if tkey in titles:
            errors.append(f"{where}: duplicate title (also {titles[tkey]})")
        titles[tkey] = r.id
        for key in REQUIRED:
            if not r.get(key):
                errors.append(f"{where}: missing required field '{key}'")
        for key in r.fields:
            if key not in REQUIRED and key not in OPTIONAL:
                errors.append(f"{where}: unknown field '{key}'")
        if r.get("level") and r.get("level") not in LEVELS:
            errors.append(f"{where}: invalid level '{r.get('level')}'")
        if r.get("provenance") and r.get("provenance") not in PROVENANCES:
            errors.append(f"{where}: invalid provenance '{r.get('provenance')}'")
        if r.get("severity") and not severity_ok(r.get("severity")):
            errors.append(f"{where}: invalid severity '{r.get('severity')}'")
        cited = set(SOURCE_TOKEN_RE.findall(r.get("sources")))
        if not cited:
            errors.append(f"{where}: sources cite no registered source ID")
        for s in cited - sources:
            errors.append(f"{where}: cites unregistered source {s}")
        if r.get("provenance") == "direct" and not any(s.startswith("S") for s in cited):
            errors.append(f"{where}: provenance 'direct' requires a corpus (S) source")
        for ref in ID_TOKEN_RE.findall(r.get("related")):
            if ref not in known:
                errors.append(f"{where}: related rule {ref} does not exist")
            if ref == r.id:
                warnings.append(f"{where}: relates to itself")
        # consistency: mandatory rules that produce findings should be able to reach major+
        sev = r.get("severity")
        if r.get("level") == "mandatory" and sev not in ("—", "-") and not re.search(r"major|blocker", sev):
            warnings.append(f"{where}: mandatory rule with low default severity '{sev}'")
        if sev not in ("—", "-") and r.get("level") in ("mandatory", "strong") and not r.get("verify"):
            warnings.append(f"{where}: no 'verify' field")
    # numbering gaps per area
    by_area: dict[str, list[int]] = {}
    for r in rules:
        area = r.id.rsplit("-", 1)[0]
        by_area.setdefault(area, []).append(int(r.id.rsplit("-", 1)[1]))
    for area, nums in by_area.items():
        nums.sort()
        if nums != list(range(1, len(nums) + 1)):
            warnings.append(f"{area}: numbering not contiguous from 01: {nums}")
    return errors, warnings


def render_index(rules: list[Rule]) -> str:
    out = [
        "# Rule index",
        "",
        "Generated by `scripts/rules.py index --write` — do not edit by hand.",
        "Use it to pick the rules relevant to a task, then open only those files or run",
        "`python scripts/rules.py show ID …` to print individual rules.",
        "",
        "## Rule schema",
        "",
        "`### DOMAIN-AREA-NN · Title` followed by fields:",
        "",
        "| Field | Meaning |",
        "|---|---|",
        "| level | Normative strength: mandatory · constraint · strong · contextual · optional (`../knowledge-model.md` §4.1) |",
        "| severity | Default severity range for findings: blocker · major · minor · nit; `—` for process rules (§4.3) |",
        "| provenance | direct · synthesized · extension · convention (`../sources.md` §3) |",
        "| sources | Citations: S1–S7 corpus, X1–X14 external (`../sources.md`) |",
        "| applies | Conditions for applying the rule (optional) |",
        "| why | Engineering rationale |",
        "| signals | Violation patterns to look for |",
        "| fix | Remediation |",
        "| verify | How to confirm the fix or the violation |",
        "| auto | Automated detection options (optional) |",
        "| except | Legitimate exceptions (optional) |",
        "| related | Related rule IDs |",
        "| example | ✗ incorrect → ✓ correct (optional) |",
        "",
        "Category = the ID's domain prefix. Priority = level × severity in context; see",
        "`../knowledge-model.md` §6 for conflict resolution.",
        "",
    ]
    counts: dict[str, int] = {}
    for r in rules:
        counts[r.domain] = counts.get(r.domain, 0) + 1
    out.append(f"**{len(rules)} rules** — " + ", ".join(
        f"{DOMAIN_NAMES[d]} {counts[d]}" for d in DOMAIN_NAMES if d in counts) + ".")
    out.append("")
    for domain in DOMAIN_NAMES:
        drules = [r for r in rules if r.domain == domain]
        if not drules:
            continue
        out.append(f"## {DOMAIN_NAMES[domain]} — `{DOMAIN_FILES[domain]}`")
        out.append("")
        out.append("| ID | Level | Title |")
        out.append("|---|---|---|")
        for r in drules:
            out.append(f"| {r.id} | {r.get('level')} | {r.title} |")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def cmd_list(rules: list[Rule], args) -> int:
    sel = [r for r in rules
           if (not args.domain or r.domain == args.domain.upper())
           and (not args.level or r.get("level") == args.level)
           and (not args.provenance or r.get("provenance") == args.provenance)]
    if args.json:
        print(json.dumps([{"id": r.id, "title": r.title, "file": r.file, **r.fields} for r in sel], indent=2, ensure_ascii=False))
    else:
        for r in sel:
            print(f"{r.id:16} {r.get('level'):11} {r.get('severity'):14} {r.title}")
        print(f"\n{len(sel)} rule(s)")
    return 0


def cmd_show(rules: list[Rule], args) -> int:
    by_id = {r.id: r for r in rules}
    rc = 0
    for rid in args.ids:
        r = by_id.get(rid.upper())
        if not r:
            print(f"(no such rule: {rid})", file=sys.stderr)
            rc = 1
            continue
        print(f"{r.raw}\n  [{r.file}:{r.line}]\n")
    return rc


def cmd_search(rules: list[Rule], args) -> int:
    term = args.term.lower()
    hits = 0
    for r in rules:
        fields = {args.field: r.get(args.field)} if args.field else {"title": r.title, **r.fields}
        for key, value in fields.items():
            if term in value.lower():
                print(f"{r.id:16} {r.title}\n    {key}: {value[:160]}")
                hits += 1
                break
    print(f"\n{hits} rule(s) match '{args.term}'")
    return 0


def cmd_stats(rules: list[Rule], _args) -> int:
    def tally(key):
        t: dict[str, int] = {}
        for r in rules:
            t[r.get(key) if key != "domain" else r.domain] = t.get(r.get(key) if key != "domain" else r.domain, 0) + 1
        return dict(sorted(t.items(), key=lambda kv: -kv[1]))
    print(json.dumps({"total": len(rules), "by_domain": tally("domain"),
                      "by_level": tally("level"), "by_provenance": tally("provenance")}, indent=2))
    return 0


def cmd_check(rules: list[Rule], parse_errors: list[str], _args) -> int:
    errors, warnings = check(rules, parse_errors)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{len(rules)} rules, {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def cmd_index(rules: list[Rule], args) -> int:
    text = render_index(rules)
    if args.write:
        (RULES_DIR / "index.md").write_text(text, encoding="utf-8")
        print(f"wrote {RULES_DIR / 'index.md'} ({len(rules)} rules)")
    else:
        print(text)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list", help="list rules")
    pl.add_argument("--domain")
    pl.add_argument("--level", choices=LEVELS)
    pl.add_argument("--provenance", choices=PROVENANCES)
    pl.add_argument("--json", action="store_true")
    ps = sub.add_parser("show", help="print full rules")
    ps.add_argument("ids", nargs="+")
    pq = sub.add_parser("search", help="full-text search")
    pq.add_argument("term")
    pq.add_argument("--field")
    sub.add_parser("stats", help="counts by domain/level/provenance")
    sub.add_parser("check", help="validate the catalog")
    pi = sub.add_parser("index", help="render the rule index")
    pi.add_argument("--write", action="store_true")
    args = p.parse_args(argv)
    rules, parse_errors = parse_rules()
    if args.cmd == "check":
        return cmd_check(rules, parse_errors, args)
    if parse_errors and args.cmd != "check":
        for e in parse_errors:
            print(f"WARN  {e}", file=sys.stderr)
    return {"list": cmd_list, "show": cmd_show, "search": cmd_search,
            "stats": cmd_stats, "index": cmd_index}[args.cmd](rules, args)


if __name__ == "__main__":
    sys.exit(main())
