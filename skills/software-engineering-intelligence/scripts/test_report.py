#!/usr/bin/env python3
"""Summarise test results honestly (TEST-REPORT-01, TEST-ISO-02, TEST-COST-01).

Reads JUnit XML (pytest --junitxml, Maven Surefire/Failsafe, Gradle, PHPUnit --log-junit, Jest and
Vitest JUnit reporters, .NET JUnit loggers, go-junit-report) and `go test -json` output. Each file
is one run (name it with LABEL=FILE, e.g. pg16=results/pg16.xml). Reports, per run and overall:
executed, passed, failed, errors and skipped tests; flaky tests (passed only on a rerun inside a run,
or — with --same-environment — passed in one run and failed in another); tests whose results differ
between runs of different environments (counted as failures where they failed); tests executed more
than once in one run; the slowest tests and suites; and, with --plan, which planned groups ran fully,
partly or not at all, and the verdict that follows.

Rules it enforces: a test that did not run is never counted as passed; skipped tests are reported
separately; a group with no executed test is "not run" and a group with unplanned skips is
"incomplete"; a Required group that is not run, incomplete or flaky makes the verdict "not verified";
any failure makes it "failed"; a run with nothing executed is not verified. Passing results are
evidence about those tests on that environment, not proof that the application is correct.

Plan file (JSON):
  {"groups": [{"name": "pricing unit tests", "class": "Required", "match": ["tests/pricing/", "PricingTest"],
               "engines": "none (A)", "expected_skips": ["test_windows_only"]}, ...]}
  "match" and "expected_skips" entries are substrings (or shell-style patterns with * ?) tested against
  each test's file, class and name; path-style and dotted names match alike (tests/pricing/ matches
  tests.pricing.test_rounding). Classes: Required, Recommended, Optional, Not necessary.

Usage:
  test_report.py [LABEL=]RESULT ... [--plan PLAN.json] [--same-environment] [--slowest N] [--json]
                 [--fail-on failed|not-run]
Safe by default: reads the given files only; refuses XML with DOCTYPE or ENTITY declarations.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ORDER = {"Required": 0, "Recommended": 1, "Optional": 2, "Not necessary": 3}


class ResultError(Exception):
    pass


def _f(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_junit(text: str, run: str) -> list[dict]:
    head = text[:4096].upper()
    if "<!DOCTYPE" in head or "<!ENTITY" in text.upper():
        raise ResultError(f"{run}: XML with DOCTYPE/ENTITY declarations is refused (unsafe to parse)")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ResultError(f"{run}: not well-formed XML ({e})") from e
    out = []
    for tc in root.iter("testcase"):
        cls = tc.get("classname") or ""
        name = tc.get("name") or "?"
        file = tc.get("file") or ""
        children = {c.tag for c in tc}
        if "failure" in children:
            status = "failed"
        elif "error" in children:
            status = "error"
        elif "skipped" in children:
            status = "skipped"
        else:
            status = "passed"
        flaky = bool(children & {"flakyFailure", "flakyError"})
        rerun_failed = bool(children & {"rerunFailure", "rerunError"})
        message = ""
        for c in tc:
            if c.tag in ("failure", "error", "skipped", "flakyFailure", "flakyError", "rerunFailure", "rerunError"):
                raw = (c.get("message") or c.text or "").strip()
                message = raw.splitlines()[0][:200] if raw else ""
                break
        out.append({"id": f"{cls}::{name}" if cls else f"{file}::{name}", "classname": cls, "name": name, "file": file,
                    "status": status, "time": _f(tc.get("time")), "flaky_marker": flaky or (rerun_failed and status == "passed"),
                    "message": message, "run": run})
    return out


def parse_go_json(text: str, run: str) -> list[dict]:
    tests: dict[tuple[str, str], dict] = {}
    package_fail: dict[str, float] = {}
    seen_any = False
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        seen_any = True
        test = ev.get("Test")
        if not test:
            if ev.get("Action") == "fail" and ev.get("Package"):
                package_fail[ev["Package"]] = _f(ev.get("Elapsed"))
            continue
        key = (ev.get("Package", ""), test)
        action = ev.get("Action")
        if action == "run":
            # A second "run" of the same test (go test -count=N) starts a new attempt.
            if key in tests and tests[key].get("_done"):
                prev = tests.pop(key)
                prev.pop("_done", None)
                prev["attempt"] = True                       # an earlier attempt of the same test
                tests[(key[0], f"{test}\x00{id(prev)}")] = prev
            tests[key] = {"package": key[0], "name": test, "status": "not finished", "time": 0.0}
        elif action in ("pass", "fail", "skip"):
            t = tests.setdefault(key, {"package": key[0], "name": test, "status": "not finished", "time": 0.0})
            t["status"] = {"pass": "passed", "fail": "failed", "skip": "skipped"}[action]
            t["time"] = _f(ev.get("Elapsed"))
            t["_done"] = True
    if not seen_any:
        raise ResultError(f"{run}: neither JUnit XML nor go test -json output")
    out = []
    packages_with_results = {t["package"] for t in tests.values()}
    for pkg, elapsed in package_fail.items():
        if pkg not in packages_with_results or not any(t["package"] == pkg and t["status"] == "failed" for t in tests.values()):
            out.append({"id": f"{pkg}::(package)", "classname": pkg, "name": "(package)", "file": "", "status": "error",
                        "time": elapsed, "flaky_marker": False,
                        "message": "package failed outside individual tests (build error, panic, TestMain or timeout)",
                        "run": run})
    for t in tests.values():
        t.pop("_done", None)
        status = t["status"] if t["status"] != "not finished" else "error"
        out.append({"id": f"{t['package']}::{t['name']}", "classname": t["package"], "name": t["name"], "file": "",
                    "status": status, "time": t["time"], "flaky_marker": False, "attempt": t.get("attempt", False),
                    "message": "test did not finish (crash or timeout)" if t["status"] == "not finished" else "",
                    "run": run})
    return out


def load(path: Path, run: str) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")      # utf-8-sig: some reporters write a BOM
    return parse_junit(text, run) if text.lstrip().startswith("<") else parse_go_json(text, run)


def _norm(value: str) -> str:
    """Path- and module-style names compared alike: tests/pricing/test_a.py ~ tests.pricing.test_a."""
    v = value.replace("\\", "/")
    v = re.sub(r"\.(py|java|kt|go|php|rb|cs|ts|tsx|js|jsx)(?=$|::|\.)", "", v)
    return v.replace("/", ".").replace("::", ".")


def matches(test: dict, patterns: list[str]) -> bool:
    hay = [test["id"], test["file"], test["classname"], test["name"]]
    hay += [_norm(h) for h in hay if h]
    for p in patterns:
        wild = any(ch in p for ch in "*?[")
        for pat in {p, _norm(p)}:
            for h in hay:
                if h and ((wild and fnmatch.fnmatch(h, pat)) or (not wild and pat in h)):
                    return True
    return False


def analyse(results: list[dict], runs: list[str], plan: dict | None, slowest: int,
            same_environment: bool = False) -> dict:
    """Counts, failures, flaky tests, duplicates, planned groups and the verdict.

    same_environment: the result files are repeated runs of the same code in the same environment, so a test
    that passed in one and failed in another is flaky. Otherwise the files are treated as different environments
    (engines, versions, platforms): a failure in one is a failure there, even if the test passed elsewhere.
    """
    per_run = {}
    for r in runs:
        rs = [t for t in results if t["run"] == r]
        per_run[r] = {s: sum(1 for t in rs if t["status"] == s) for s in ("passed", "failed", "error", "skipped")}
        per_run[r]["executed"] = sum(1 for t in rs if t["status"] != "skipped")
        per_run[r]["time"] = round(sum(t["time"] for t in rs), 3)
    bad = ("failed", "error")
    by_id: dict[str, list[dict]] = defaultdict(list)
    for t in results:
        by_id[t["id"]].append(t)
    flaky, duplicates, env_dependent = [], [], []
    flaky_keys: set[tuple[str, str]] = set()          # (id, run) whose failures are explained as flaky
    for tid, ts in by_id.items():
        by_run: dict[str, list[dict]] = defaultdict(list)
        for t in ts:
            by_run[t["run"]].append(t)
        for run, rts in by_run.items():
            statuses = {t["status"] for t in rts}
            if any(t["flaky_marker"] for t in rts) or ("passed" in statuses and statuses & set(bad)):
                flaky_keys.add((tid, run))         # rerun inside one run: same code, same environment
            if len(rts) > 1 and not any(t.get("attempt") for t in rts):
                duplicates.append({"id": tid, "run": run, "times": len(rts)})
        passed_runs = {r for r, rts in by_run.items() if any(t["status"] == "passed" for t in rts)}
        failed_runs = {r for r, rts in by_run.items() if any(t["status"] in bad for t in rts)}
        if passed_runs and failed_runs - passed_runs:
            if same_environment:
                flaky_keys |= {(tid, r) for r in failed_runs}
            else:
                env_dependent.append({"id": tid, "failed_in": sorted(failed_runs - passed_runs),
                                      "passed_in": sorted(passed_runs)})
        if any((tid, r) in flaky_keys for r in by_run):
            flaky.append({"id": tid, "outcomes": [f"{t['run']}: {t['status']}" for t in ts]})
    hard_failures = [t for t in results if t["status"] in bad and (t["id"], t["run"]) not in flaky_keys]
    suites: dict[str, float] = defaultdict(float)
    for t in results:
        suites[t["classname"] or t["file"] or "?"] += t["time"]
    slow_tests = sorted(results, key=lambda t: -t["time"])[:slowest]
    slow_suites = sorted(suites.items(), key=lambda kv: -kv[1])[:slowest]
    executed_total = sum(1 for t in results if t["status"] != "skipped")
    groups = []
    verdict, reasons = None, []
    if plan:
        for g in plan.get("groups", []):
            pats = g.get("match", [])
            allowed = g.get("expected_skips", [])
            ts = [t for t in results if matches(t, pats)] if pats else []
            executed = [t for t in ts if t["status"] != "skipped"]
            skipped = [t for t in ts if t["status"] == "skipped"]
            unexpected = [t for t in skipped if not (allowed and matches(t, allowed))]
            failed = [t for t in executed if t["status"] in bad and (t["id"], t["run"]) not in flaky_keys]
            flaky_here = [t for t in executed if (t["id"], t["run"]) in flaky_keys]
            if failed:
                state = "failed"
            elif not executed:
                state = "not run (not necessary)" if g.get("class") == "Not necessary" else "not run"
            elif unexpected:
                state = f"incomplete ({len(unexpected)} of {len(ts)} skipped)"
            elif flaky_here:
                state = "flaky"
            else:
                state = "passed"
            groups.append({"name": g.get("name", "?"), "class": g.get("class", "?"), "engines": g.get("engines", ""),
                           "matched": len(ts), "executed": len(executed), "skipped": len(skipped),
                           "expected_skips": len(skipped) - len(unexpected), "state": state})
        req = [g for g in groups if g["class"] == "Required"]
        rec = [g for g in groups if g["class"] == "Recommended"]
        open_req = [g for g in req if g["state"] != "passed"]
        open_rec = [g for g in rec if g["state"] != "passed"]
        if hard_failures:
            verdict = "failed"
            failed_groups = [g["name"] for g in groups if g["state"] == "failed"]
            reasons.append("tests failed" + (f" in: {', '.join(failed_groups)}" if failed_groups else
                                             " (outside the planned groups)"))
        elif open_req:
            verdict = "not verified"
            reasons.append("Required groups not fully verified: " +
                           ", ".join(f"{g['name']} ({g['state']})" for g in open_req))
        elif open_rec:
            verdict = "partially verified"
            reasons.append("Recommended groups not fully verified: " +
                           ", ".join(f"{g['name']} ({g['state']})" for g in open_rec))
        elif req:
            verdict = "verified for the stated scope"
        else:
            verdict = "not verified"
            reasons.append("the plan has no Required group")
    elif hard_failures:
        verdict = "failed"
    elif not executed_total:
        verdict = "not verified"
        reasons.append("no test executed")
    else:
        verdict = "no plan — results describe only the tests that ran"
    if env_dependent and not hard_failures:
        reasons.append("results differ between runs")
    return {"runs": per_run, "total_results": len(results), "executed_total": executed_total,
            "same_environment": same_environment, "flaky": flaky, "environment_dependent": env_dependent,
            "duplicates": duplicates,
            "failures": [{"id": t["id"], "run": t["run"], "status": t["status"], "message": t["message"]}
                         for t in hard_failures],
            "skipped": [{"id": t["id"], "run": t["run"], "message": t["message"]} for t in results if t["status"] == "skipped"],
            "slowest_tests": [{"id": t["id"], "run": t["run"], "time": t["time"]} for t in slow_tests],
            "slowest_suites": [{"suite": s, "time": round(v, 3)} for s, v in slow_suites],
            "groups": sorted(groups, key=lambda g: ORDER.get(g["class"], 9)), "verdict": verdict, "reasons": reasons}


def to_markdown(res: dict) -> str:
    out = ["# Test results", "",
           "_Counts come only from the result files given. Skipped and unrun tests are not passes; a passing run is "
           "evidence about the tests that ran on that environment, not proof that the application is correct._", "",
           "## Executed tests", "", "| Run | Executed | Passed | Failed | Errors | Skipped | Time (s) |", "|---|---|---|---|---|---|---|"]
    for run, r in res["runs"].items():
        out.append(f"| {run} | {r['executed']} | {r['passed']} | {r['failed']} | {r['error']} | {r['skipped']} | {r['time']} |")
    if res["groups"]:
        out += ["", "## Planned groups", "", "| Group | Class | Engines | Matched | Executed | Skipped (expected) | State |",
                "|---|---|---|---|---|---|---|"]
        for g in res["groups"]:
            out.append(f"| {g['name']} | {g['class']} | {g['engines'] or '—'} | {g['matched']} | {g['executed']} | "
                       f"{g['skipped']} ({g['expected_skips']}) | {g['state']} |")
    if res["skipped"]:
        out += ["", f"## Skipped ({len(res['skipped'])})", ""]
        out += [f"- `{s['id']}` ({s['run']}){' — ' + s['message'] if s['message'] else ' — no reason given'}"
                for s in res["skipped"][:30]]
    if res["failures"]:
        out += ["", f"## Failures ({len(res['failures'])})", ""]
        out += [f"- `{f['id']}` ({f['run']}, {f['status']}){' — ' + f['message'] if f['message'] else ''}"
                for f in res["failures"][:30]]
    if res["environment_dependent"]:
        out += ["", f"## Different results between runs ({len(res['environment_dependent'])})", "",
                "The runs were treated as different environments (engines, versions, platforms), so these failures count "
                "as failures. If the files are reruns of the same code in the same environment, pass --same-environment.", ""]
        out += [f"- `{e['id']}`: failed in {', '.join(e['failed_in'])}; passed in {', '.join(e['passed_in'])}"
                for e in res["environment_dependent"][:30]]
    if res["flaky"]:
        out += ["", f"## Flaky ({len(res['flaky'])}) — passed and failed on the same code, or passed only on a rerun", ""]
        out += [f"- `{f['id']}`: {'; '.join(f['outcomes'])}" for f in res["flaky"][:30]]
        out.append("- Fix now if the cause is known and the fix is small; otherwise quarantine with an owner and a date, "
                   "diagnose (order, timing, shared state, races), fix or delete "
                   "(TEST-ISO-02); never report these as passed.")
    if res["duplicates"]:
        out += ["", "## Executed more than once in one run", ""]
        out += [f"- `{d['id']}` ×{d['times']} in {d['run']}" for d in res["duplicates"][:30]]
        out.append("- Check for duplicated jobs or test registrations before removing anything (TEST-COST-01).")
    out += ["", "## Duration", "", "Slowest tests:"]
    out += [f"- {t['time']:.3f} s `{t['id']}` ({t['run']})" for t in res["slowest_tests"]]
    out += ["", "Slowest suites:"] + [f"- {s['time']:.3f} s `{s['suite']}`" for s in res["slowest_suites"]]
    out += ["", "## Verdict", "", f"**{res['verdict']}**" + (f" — {'; '.join(res['reasons'])}" if res["reasons"] else "")]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("results", nargs="+", help="JUnit XML or go test -json files, one per run; LABEL=FILE names the run")
    p.add_argument("--plan", help="JSON plan with test groups and their classes")
    p.add_argument("--same-environment", action="store_true",
                   help="the files are reruns of the same code in the same environment (pass/fail across them = flaky)")
    p.add_argument("--slowest", type=int, default=10)
    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-on", choices=["failed", "not-run"],
                   help="exit 1 on hard failures (failed) or also when a Required group did not run (not-run)")
    args = p.parse_args(argv)
    results, runs = [], []
    try:
        for f in args.results:
            label, path = f, Path(f)
            if "=" in f and not path.is_file():
                label, _, rest = f.partition("=")
                path = Path(rest)
            if not path.is_file():
                print(f"not a file: {path}", file=sys.stderr)
                return 2
            if label in runs:
                print(f"duplicate run label: {label} (name runs with LABEL=FILE)", file=sys.stderr)
                return 2
            results += load(path, label)
            runs.append(label)
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8")) if args.plan else None
    except (ResultError, json.JSONDecodeError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    res = analyse(results, runs, plan, args.slowest, args.same_environment)
    print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else to_markdown(res))
    if args.fail_on == "failed" and res["failures"]:
        return 1
    if args.fail_on == "not-run" and (res["failures"] or not res["executed_total"]
                                      or res["verdict"] in ("not verified", "failed")):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
