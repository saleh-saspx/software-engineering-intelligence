#!/usr/bin/env python3
"""Check a review or assessment report for the structure this skill requires.

Full reports (assets/templates/review-report.md, assessment-report.md) need Summary, Scope,
Verification and Findings sections, and every finding block
  ### F-<nn> [<blocker|major|minor|nit> · <confirmed|likely|possible>] <title>
needs Where, Type, Rule, What, Why it matters, Fix and Evidence fields. Assessment reports
also need Quality profile and Limitations sections.
Light reports (SKILL.md §8) need Scope, Checks run (or Verification) and Verdict lines, and
findings as `- [<severity> · <confidence>] path:line — …`.

Also flags over-claiming language ("the code is secure", "bug-free") — AGT-EVID-03 — and
reader-hostile output: internal jargon (tier numbers, coverage codes, principle IDs, rule IDs used
as prose) and reports over the SKILL.md §8 length budgets (code blocks excluded).

Usage: check_report.py REPORT.md [--light] [--json]   (exit 1 on errors)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rules import ID_TOKEN_RE, parse_rules  # noqa: E402

SEVERITIES = {"blocker", "major", "minor", "nit"}
CONFIDENCES = {"confirmed", "likely", "possible"}
TYPES = {"defect", "vulnerability", "reliability-risk", "performance", "tech-debt", "architecture-risk",
         "test-gap", "trade-off", "legacy-constraint", "imperfection", "question"}
FIELDS = ["Where", "Type", "What", "Why it matters", "Fix", "Evidence"]  # Rule is optional
FINDING_RE = re.compile(r"^### (F-\d+) \[([a-z]+)(?: · ([a-z]+))?\] (.+)$", re.M)
LIGHT_FINDING_RE = re.compile(r"^\s*[-*] \[([a-z]+)(?: · ([a-z]+))?\]\s+(.+)$", re.M)
OVERCLAIM_RE = re.compile(
    r"(?i)\b(?:(?:the )?(?:code|system|application|app|repo(?:sitory)?|service) is (?:now |fully |completely )?secure"
    r"|no (?:security )?vulnerabilit(?:y|ies) (?:exist|remain)|bug[- ]free|100% (?:secure|safe|correct)"
    r"|guaranteed to be (?:secure|correct))\b")


JARGON_RES = [
    (re.compile(r"\bL[0-3]\b(?! cache)"), "coverage code (L0–L3) — use plain words such as 'read in full' or 'traced'"),
    (re.compile(r"\bTier [0-3]\b"), "tier number — internal triage vocabulary"),
    (re.compile(r"(?i)\bcontext gates?\b"), "'context gate' — internal vocabulary"),
    (re.compile(r"\bP-\d\d\b"), "principle ID — internal reference"),
]


def prose_words(text: str) -> int:
    no_code = re.sub(r"```.*?```", " ", text, flags=re.S)
    no_code = re.sub(r"<!--.*?-->", " ", no_code, flags=re.S)
    return len(re.findall(r"\b\w[\w'’-]*\b", no_code))


def reader_checks(text: str, light: bool, n_findings: int, budget: int | None = None) -> list[str]:
    warnings = []
    body = re.sub(r"```.*?```", " ", text, flags=re.S)
    for rx, why in JARGON_RES:
        hits = rx.findall(body)
        if hits:
            warnings.append(f"{len(hits)}× {why}")
    ids_total = len(ID_TOKEN_RE.findall(body))
    ids_in_rule_fields = sum(len(ID_TOKEN_RE.findall(m)) for m in re.findall(r"\*\*Rule:\*\*([^\n]*)", body))
    ids_in_light = sum(len(ID_TOKEN_RE.findall(m)) for m in re.findall(r"\(([A-Z]{2,5}-[A-Z]{2,9}-\d{2}(?:,\s*[A-Z]{2,5}-[A-Z]{2,9}-\d{2})*)\)\s*$", body, re.M))
    loose = ids_total - ids_in_rule_fields - ids_in_light
    if loose > max(3, n_findings):
        warnings.append(f"{loose} rule IDs appear in running prose — keep at most one per finding as a trailing reference")
    words = prose_words(text)
    if budget is None:
        budget = 450 if light else (3500 if re.search(r"^# +Assessment", text, re.M) else 1800)
    if words > budget:
        warnings.append(f"{words} words outside code blocks (budget ≈{budget}) — lead with the verdict, cut restatement, compact the findings")
    return warnings


def sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## +(.+?)\s*$", text, flags=re.M)
    return {parts[i].strip().lower(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def check_full(text: str, known_rules: set[str]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    secs = sections(text)
    is_assessment = bool(re.search(r"^# +Assessment", text, re.M))
    required = ["summary", "scope", "verification", "findings"]
    if is_assessment:
        required += ["quality profile", "limitations"]
    for s in required:
        if not any(k.startswith(s) for k in secs):
            errors.append(f"missing section '## {s.title()}'")
    scope = next((v for k, v in secs.items() if k.startswith("scope")), "")
    if scope and not re.search(r"(?i)not (?:reviewed|covered)|out of scope|coverage", scope):
        warnings.append("Scope does not state what was NOT reviewed (AGT-SCOPE-01)")
    verif = next((v for k, v in secs.items() if k.startswith("verification")), "")
    if verif:
        for row in re.findall(r"^\|(.+)\|\s*$", verif, re.M):
            cells = [c.strip() for c in row.split("|")]
            if len(cells) >= 3 and not set("".join(cells)) <= set("-: "):
                cmd, result = cells[1], cells[2]
                if cells[0].lower() == "check":
                    continue
                if re.search(r"(?i)\bpass(?:ed|es)?\b|\bgreen\b|\bsucce", result) and not cmd.strip("`<> "):
                    errors.append(f"Verification row '{cells[0]}' claims success without a command (AGT-EVID-01)")
    findings = list(FINDING_RE.finditer(text))
    fsec = next((v for k, v in secs.items() if k.startswith("findings")), "")
    if not findings and fsec and not re.search(r"(?i)no (?:significant )?(?:issues|findings)", fsec):
        warnings.append("Findings section has no F-nn blocks and does not say 'no significant issues'")
    ids_seen = set()
    for i, m in enumerate(findings):
        fid, sev, conf, title = m.group(1), m.group(2), m.group(3), m.group(4)
        if fid in ids_seen:
            errors.append(f"{fid}: duplicate finding ID")
        ids_seen.add(fid)
        if sev not in SEVERITIES:
            errors.append(f"{fid}: invalid severity '{sev}'")
        if conf is None:
            errors.append(f"{fid}: missing confidence (confirmed|likely|possible)")
        elif conf not in CONFIDENCES:
            errors.append(f"{fid}: invalid confidence '{conf}'")
        end = findings[i + 1].start() if i + 1 < len(findings) else len(text)
        nxt = re.search(r"^## ", text[m.end():end], re.M)
        body = text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():end]
        for f in FIELDS:
            if not re.search(rf"\*\*{re.escape(f)}:\*\*", body):
                errors.append(f"{fid}: missing field '{f}'")
        tm = re.search(r"\*\*Type:\*\*\s*([a-z-]+)", body)
        if tm and tm.group(1) not in TYPES:
            errors.append(f"{fid}: unknown type '{tm.group(1)}'")
        rm = re.search(r"\*\*Rule:\*\*\s*([^\n]+)", body)
        if rm:
            for rid in ID_TOKEN_RE.findall(rm.group(1)):
                if rid not in known_rules:
                    warnings.append(f"{fid}: rule {rid} is not in the catalog")
        wm = re.search(r"\*\*Where:\*\*\s*([^\n]+)", body)
        if wm and not re.search(r"[\w./-]+\.\w+|[\w-]+/", wm.group(1)):
            warnings.append(f"{fid}: 'Where' has no file path")
        if conf == "confirmed":
            em = re.search(r"\*\*Evidence:\*\*\s*([^\n]+)", body)
            if em and re.search(r"(?i)\bassum|\bprobabl|\bmight\b|\bmay\b|\bunverified", em.group(1)):
                warnings.append(f"{fid}: marked confirmed but evidence sounds assumed")
    return errors, warnings


def check_light(text: str) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    if not re.search(r"(?im)^\**scope:?\**", text):
        errors.append("light report: missing 'Scope:' line")
    if not re.search(r"(?im)checks run:|verification:", text):
        errors.append("light report: missing 'Checks run:' (or 'Verification:')")
    if not re.search(r"(?im)verdict:", text):
        errors.append("light report: missing 'Verdict:' line")
    for m in LIGHT_FINDING_RE.finditer(text):
        sev, conf = m.group(1), m.group(2)
        if sev not in SEVERITIES:
            errors.append(f"light finding with invalid severity '{sev}': {m.group(0).strip()[:60]}")
        if sev != "nit" and conf not in CONFIDENCES:
            errors.append(f"light finding without confidence: {m.group(0).strip()[:60]}")
    return errors, warnings


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("report")
    p.add_argument("--light", action="store_true", help="force light-format checks")
    p.add_argument("--json", action="store_true")
    p.add_argument("--budget", type=int, default=None,
                   help="word budget outside code blocks (default: light 450, review 1800, assessment 3500)")
    args = p.parse_args(argv)
    text = Path(args.report).read_text(encoding="utf-8")
    rules, _ = parse_rules()
    known = {r.id for r in rules}
    light = args.light or (not FINDING_RE.search(text) and not re.search(r"^## +Scope", text, re.M))
    errors, warnings = check_light(text) if light else check_full(text, known)
    for m in OVERCLAIM_RE.finditer(text):
        warnings.append(f"over-claiming language: '{m.group(0)}' (AGT-EVID-03, SEC-PROC-04)")
    n_findings = len(FINDING_RE.findall(text)) or len(LIGHT_FINDING_RE.findall(text))
    warnings += reader_checks(text, light, n_findings, args.budget)
    if args.json:
        print(json.dumps({"mode": "light" if light else "full", "errors": errors, "warnings": warnings}, indent=2))
    else:
        print(f"mode: {'light' if light else 'full'}")
        for w in warnings:
            print(f"WARN  {w}")
        for e in errors:
            print(f"ERROR {e}")
        print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
