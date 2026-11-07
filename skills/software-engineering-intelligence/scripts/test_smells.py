#!/usr/bin/env python3
"""Lead scanner for test-suite smells (TEST-* rules).

Finds tests that are skipped without a reason or focused (`.only`), sleep, read the wall clock or
unseeded randomness, call real external hosts, are commented out, assert nothing, only check
that mocks were called, or (Python) derive their expected value from the code under test. Python tests are parsed with `ast`; JavaScript/TypeScript, Java/Kotlin, Go,
PHP and C# test bodies are found by brace matching (approximate).

Every hit is a LEAD (confidence: possible): a test with no assertion may delegate to a helper that
asserts; a sleep may be in a deliberately slow test. Confirm by reading the test before reporting
it (references/workflows/test-strategy.md §11). No hits does not mean the suite is good — the
strongest single check is seeding a defect and seeing whether a test fails (TEST-MUT-01).

Usage: test_smells.py PATH [--files F ...] [--max-per-check 20] [--json]
Lines containing `test_smells: ignore` are skipped.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import is_test_path, iter_files, read_text  # noqa: E402

PY, JS, JVM, GO, PHP, RB, CS = {".py"}, {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}, {".java", ".kt"}, \
    {".go"}, {".php"}, {".rb"}, {".cs"}
ALL = PY | JS | JVM | GO | PHP | RB | CS
EXTERNAL_URL = r"https?://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|testserver|example\.(?:com|org|net)|[\w.-]*\.test\b|[\w.-]*\.local\b)"
CLOCK_CONTROL = re.compile(r"freeze_?time|time_machine|freezegun|Clock\.fixed|MutableClock|useFakeTimers|setSystemTime|"
                           r"Carbon::setTestNow|travelTo|travel_to|Timecop|\btravel\(|FakeTimeProvider|clockwork|mockClock|fakeClock", re.I)
SEEDED = re.compile(r"random\.seed\(|np\.random\.seed|default_rng\(\s*\d|new Random\(\s*\d|rand\.New\(rand\.NewSource|"
                    r"rand\.Seed\(|mt_srand\(|srand\(|faker\.seed|Faker\.seed|seedrandom", re.I)
HTTP_FAKED = re.compile(r"Http::fake|responses\.activate|requests_mock|httpretty|respx|nock\(|msw|setupServer|"
                        r"WireMock|MockWebServer|httptest\.NewServer|vcr|VCR|cassette|betamax|pytest_httpserver", re.I)

# (check, rule, languages, regex, message)
LINE_CHECKS = [
    ("skip-without-reason", "TEST-SKIP-01", PY,
     r"@pytest\.mark\.skip(?:\(\s*\))?[ \t]*$|\bpytest\.skip\(\s*\)|@unittest\.skip\(\s*\)", "Skipped test with no reason"),
    ("skip-without-reason", "TEST-SKIP-01", JVM, r"@(?:Disabled|Ignore)\s*(?:\(\s*\))?[ \t]*$", "Disabled test with no reason"),
    ("skip-without-reason", "TEST-SKIP-01", GO, r"\bt\.(?:Skip\(\s*\)|SkipNow\(\))", "Skipped test with no reason"),
    ("skip-without-reason", "TEST-SKIP-01", JS, r"\b(?:it|test|describe|context)\.skip\s*\(|\bx(?:it|test|describe)\s*\(",
     "Skipped test (no reason or tracking issue possible in the syntax — check for a comment)"),
    ("skip-without-reason", "TEST-SKIP-01", PHP, r"markTestSkipped\(\s*\)|->skip\(\s*\)", "Skipped test with no reason"),
    ("skip-without-reason", "TEST-SKIP-01", RB, r"^[ \t]*(?:xit|xdescribe|xcontext)\b|^[ \t]*skip[ \t]*$", "Skipped test with no reason"),
    ("focused-test", "TEST-SKIP-01", JS, r"\b(?:it|test|describe|context)\.only\s*\(|\bf(?:it|describe)\s*\(",
     "Focused test committed: the rest of the file or suite silently stops running"),
    ("focused-test", "TEST-SKIP-01", RB, r"^[ \t]*(?:fit|fdescribe|fcontext)\b|\bfocus:\s*true", "Focused spec committed"),
    ("fixed-sleep", "TEST-UNIT-01", PY, r"\btime\.sleep\(|(?<![\w.])sleep\(\s*\d", "Fixed sleep in a test (slow and flaky)"),
    ("fixed-sleep", "TEST-UNIT-01", JVM, r"\bThread\.sleep\(|\bTimeUnit\.\w+\.sleep\(|\bdelay\(\s*\d", "Fixed sleep in a test (slow and flaky)"),
    ("fixed-sleep", "TEST-UNIT-01", GO, r"\btime\.Sleep\(", "Fixed sleep in a test (slow and flaky)"),
    ("fixed-sleep", "TEST-UNIT-01", JS, r"new Promise\(\s*\(?\s*\w+\s*\)?\s*=>\s*setTimeout\(|\bwaitForTimeout\(|\bcy\.wait\(\s*\d",
     "Fixed sleep in a test (slow and flaky)"),
    ("fixed-sleep", "TEST-UNIT-01", PHP, r"(?<![\w>:])u?sleep\(\s*\d", "Fixed sleep in a test (slow and flaky)"),
    ("fixed-sleep", "TEST-UNIT-01", RB, r"(?<![\w.])sleep[\s(]+\d", "Fixed sleep in a test (slow and flaky)"),
    ("fixed-sleep", "TEST-UNIT-01", CS, r"\bThread\.Sleep\(|\bTask\.Delay\(\s*\d", "Fixed sleep in a test (slow and flaky)"),
    ("wall-clock", "TEST-ISO-01", PY, r"\bdatetime\.(?:now|utcnow|today)\(|\bdate\.today\(|\btime\.time\(", "Reads the real clock"),
    ("wall-clock", "TEST-ISO-01", JVM, r"\b(?:LocalDate|LocalDateTime|ZonedDateTime|OffsetDateTime|Instant)\.now\(\s*\)|System\.currentTimeMillis\(|new Date\(\s*\)",
     "Reads the real clock"),
    ("wall-clock", "TEST-ISO-01", GO, r"\btime\.Now\(\)", "Reads the real clock"),
    ("wall-clock", "TEST-ISO-01", JS, r"new Date\(\s*\)|\bDate\.now\(\)", "Reads the real clock"),
    ("wall-clock", "TEST-ISO-01", PHP, r"(?<![\w>:$])now\(\)|Carbon::now\(|(?<![\w>:$])time\(\)", "Reads the real clock"),
    ("wall-clock", "TEST-ISO-01", RB, r"\bTime\.now\b|\bDate\.today\b", "Reads the real clock"),
    ("wall-clock", "TEST-ISO-01", CS, r"\bDateTime(?:Offset)?\.(?:Now|UtcNow|Today)\b", "Reads the real clock"),
    ("unseeded-random", "TEST-ISO-01", PY, r"\brandom\.(?:random|randint|choice|choices|shuffle|uniform|sample)\(", "Unseeded randomness"),
    ("unseeded-random", "TEST-ISO-01", JVM, r"new Random\(\s*\)|Math\.random\(", "Unseeded randomness"),
    ("unseeded-random", "TEST-ISO-01", GO, r"\brand\.(?:Intn|Int|Float64|Perm|Shuffle)\(", "Unseeded randomness"),
    ("unseeded-random", "TEST-ISO-01", JS, r"\bMath\.random\(", "Unseeded randomness"),
    ("unseeded-random", "TEST-ISO-01", PHP, r"(?<![\w>:])(?:mt_)?rand\(|(?<![\w>:])random_int\(", "Unseeded randomness"),
    ("unseeded-random", "TEST-ISO-01", RB, r"(?<![\w.])rand\(|\.sample\b|\.shuffle\b", "Unseeded randomness"),
    ("real-network", "TEST-ISO-01", PY, rf"\b(?:requests|httpx|urllib\.request)\.\w*\(\s*[fr]?['\"]{EXTERNAL_URL}", "Calls a real external host"),
    ("real-network", "TEST-ISO-01", JS, rf"\b(?:fetch|axios(?:\.\w+)?|got|request)\(\s*['\"`]{EXTERNAL_URL}", "Calls a real external host"),
    ("real-network", "TEST-ISO-01", GO, rf"\bhttp\.(?:Get|Post|Head|NewRequest\w*)\([^)]*\"{EXTERNAL_URL}", "Calls a real external host"),
    ("real-network", "TEST-ISO-01", JVM, rf"(?:URI\.create|new URL|\.uri)\(\s*\"{EXTERNAL_URL}", "Calls a real external host"),
    ("real-network", "TEST-ISO-01", PHP, rf"(?:Http::\w+|file_get_contents|curl_init)\(\s*['\"]{EXTERNAL_URL}", "Calls a real external host"),
    ("real-network", "TEST-ISO-01", RB, rf"(?:Net::HTTP\.\w+|HTTParty\.\w+|Faraday\.\w+)\(\s*(?:URI\()?['\"]{EXTERNAL_URL}", "Calls a real external host"),
    ("commented-out-test", "TEST-SKIP-01", PY, r"^[ \t]*#\s*(?:async\s+)?def\s+test_\w*\(", "Commented-out test"),
    ("commented-out-test", "TEST-SKIP-01", JVM | JS | GO | PHP | CS,
     r"^[ \t]*//\s*(?:@Test\b|\[(?:Fact|Test|TestMethod)\]|(?:it|test|describe)\s*\(\s*['\"`]|func\s+Test\w*\(|public\s+function\s+test)",
     "Commented-out test"),
]
COMPILED = [(c, r, langs, re.compile(rx, re.M), m) for (c, r, langs, rx, m) in LINE_CHECKS]

ASSERT_WORDS = re.compile(r"\bassert|\bAssert\b|\bexpect\s*\(|\bexpect\.|\.should\b|\bshould\(|\bverify\s*\(|\bverifyNoMoreInteractions|"
                          r"\bt\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\b|\brequire\.|\bassert\.|\bfail\s*\(|\bthen\(|"
                          r"\$this->expect|\bexpectException|\bshouldReceive\b|->assert|\bShould\(\)|\.Should\b|\bthrows\b|toThrow|rejects|resolves|"
                          r"\bcheck\(|\bsnapshot|toMatch")
SKIP_IN_BODY = re.compile(r"\bt\.Skip|markTestSkipped|\bskip\(|Assumptions\.assume|assumeTrue|pytest\.skip")
MOCK_ONLY = re.compile(r"\bverify\s*\(|toHaveBeenCalled\w*|assert_called\w*|assert_not_called|assert_has_calls|\.Received\(|shouldHaveReceived|shouldReceive")
NON_MOCK_ASSERT = re.compile(r"\bassert(?!_called|_not_called|_has_calls|_any_call)\w*\s*[(\s]|\bAssert\.|\bassertThat\b|\bexpect\((?![^)]*\)\.(?:not\.)?toHaveBeenCalled)|"
                             r"\bt\.(?:Error|Errorf|Fatal|Fatalf)\b|\brequire\.|\.Should\b|->assert\w+\(|\$this->assert")


def match_brace(text: str, start: int) -> int:
    """Index just past the brace block opening at text[start] == '{' (strings and comments skipped)."""
    depth, i, n = 0, start, len(text)
    while i < n:
        c = text[i]
        if c in "\"'`":
            q, i = c, i + 1
            while i < n and text[i] != q:
                i += 2 if text[i] == "\\" else 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


TEST_DECL = {
    "js": re.compile(r"\b(?:it|test)(?:\.(?:only|skip|concurrent|failing))?\s*\(\s*(['\"`])(.*?)\1\s*,\s*(?:async\s+)?(?:\([^)]*\)|\w+)?\s*(?:=>)?\s*(?:function\s*\w*\s*\([^)]*\)\s*)?\{"),
    "jvm": re.compile(r"@(?:Test|ParameterizedTest|RepeatedTest|TestFactory)\b[^\n]*\n(?:\s*@[^\n]*\n)*\s*(?:(?:public|protected|private|internal|open|override|suspend)\s+)*(?:void|fun)\s+`?([\w ]+?)`?\s*\([^)]*\)[^{]*\{"),
    "go": re.compile(r"\bfunc\s+(Test\w*)\s*\(\s*\w+\s+\*testing\.T\s*\)\s*\{"),
    "php": re.compile(r"(?:(?:#\[Test\]|/\*\*\s*@test\s*\*/)\s*)?public\s+function\s+(test\w*)\s*\([^)]*\)\s*(?::\s*\w+\s*)?\{|"
                      r"\b(?:test|it)\s*\(\s*['\"](.*?)['\"]\s*,\s*function\s*\([^)]*\)\s*(?:use\s*\([^)]*\)\s*)?\{"),
    "cs": re.compile(r"\[(?:Fact|Theory|Test|TestMethod|TestCase[^\]]*)\][^\n]*\n(?:\s*\[[^\n]*\n)*\s*public\s+(?:async\s+)?(?:void|Task)\s+(\w+)\s*\([^)]*\)\s*\{"),
}


def brace_tests(text: str, family: str) -> list[tuple[int, str, str]]:
    """(line, name, body) for tests found by declaration regex + brace matching."""
    out = []
    for m in TEST_DECL[family].finditer(text):
        open_pos = m.end() - 1
        end = match_brace(text, open_pos)
        name = next((g for g in m.groups()[1:] if g), None) if family in ("js", "php") else m.group(1)
        if family == "php" and not name:
            name = m.group(1) or m.group(2)
        out.append((text.count("\n", 0, m.start()) + 1, (name or "?").strip(), text[open_pos:end]))
    return out


def python_tests(text: str) -> list[tuple[int, str, str, bool, bool]]:
    """(line, name, source, has_any_assert, mock_only) for pytest/unittest tests."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test"):
            continue
        has_assert, has_real, has_mock = False, False, False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assert):
                has_assert = has_real = True
            elif isinstance(sub, ast.Call):
                fn = sub.func
                name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
                low = name.lower()
                if low.startswith("assert_called") or low in ("assert_not_called", "assert_has_calls", "assert_any_call", "assert_awaited", "assert_awaited_once_with"):
                    has_assert, has_mock = True, True
                elif "assert" in low or low in ("raises", "fail", "warns", "expect", "check", "verify") or low.startswith("assert"):
                    has_assert = has_real = True
            elif isinstance(sub, (ast.With, ast.AsyncWith)):
                for item in sub.items:
                    src = ast.get_source_segment(text, item.context_expr) or ""
                    if "raises" in src or "assertRaises" in src or "warns" in src:
                        has_assert = has_real = True
        decorators = " ".join(ast.get_source_segment(text, d) or "" for d in node.decorator_list)
        if "xfail" in decorators or "skip" in decorators:
            continue
        out.append((node.lineno, node.name, ast.get_source_segment(text, node) or "", has_assert, has_mock and not has_real,
                    self_referential_oracle(node)))
    return out


def call_name(call: ast.Call) -> str:
    fn = call.func
    parts = []
    while isinstance(fn, ast.Attribute):
        parts.append(fn.attr)
        fn = fn.value
    if isinstance(fn, ast.Name):
        parts.append(fn.id)
    return ".".join(reversed(parts))


NEUTRAL_CALLS = {"int", "float", "str", "bytes", "bool", "len", "list", "dict", "set", "tuple", "sorted",
                 "sum", "round", "abs", "min", "max", "range", "repr", "frozenset", "quantize"}


def produced_calls(node: ast.AST) -> set:
    """Functions whose *result* forms `node` (not calls nested in their arguments).

    Builtins and constructors (Capitalised names) are looked through, so for
    `round(line_total(p, 1) * 3, 2)` the answer is {"line_total"}, while for
    `line_total(money("5.00"), 2)` it is {"line_total"} only.
    """
    out = set()

    def visit(n):
        if isinstance(n, ast.Call):
            name = call_name(n)
            last = name.rsplit(".", 1)[-1]
            if not name or last in NEUTRAL_CALLS or last[:1].isupper():
                for a in n.args:
                    visit(a)
                for kw in n.keywords:
                    visit(kw.value)
                if isinstance(n.func, ast.Attribute):
                    visit(n.func.value)
            else:
                out.add(name)
        elif isinstance(n, ast.BinOp):
            visit(n.left)
            visit(n.right)
        elif isinstance(n, ast.UnaryOp):
            visit(n.operand)
        elif isinstance(n, (ast.Subscript, ast.Attribute)):
            visit(n.value)
        elif isinstance(n, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
            visit(n.elt)
        elif isinstance(n, (ast.Tuple, ast.List)):
            for e in n.elts:
                visit(e)
        elif isinstance(n, ast.IfExp):
            visit(n.body)
            visit(n.orelse)

    visit(node)
    return out


def self_referential_oracle(func: ast.AST) -> bool:
    """True when an expected value is derived from the function the assert exercises (TEST-ORACLE-01).

    Example: `expected = line_total(price, 1) * 3` then `assert line_total(price, 3) == expected`.
    Only variables named like an expectation are considered, so metamorphic and round-trip
    properties (`assert decode(encode(x)) == x`) are not reported.
    """
    expected_calls, other_calls = {}, {}
    for sub in ast.walk(func):
        if isinstance(sub, ast.Assign):
            for t in sub.targets:
                if isinstance(t, ast.Name):
                    target = expected_calls if re.match(r"(?i)^(expected|want|exp_|should_be)", t.id) else other_calls
                    target.setdefault(t.id, set()).update(produced_calls(sub.value))
    if not expected_calls:
        return False
    for sub in ast.walk(func):
        if not (isinstance(sub, ast.Assert) and isinstance(sub.test, ast.Compare)):
            continue
        sides = [sub.test.left, *sub.test.comparators]
        exp_side = set()
        act_side = set()
        for side in sides:
            if isinstance(side, ast.Name) and side.id in expected_calls:
                exp_side |= expected_calls[side.id]
            elif isinstance(side, ast.Name):
                act_side |= other_calls.get(side.id, set())
            else:
                act_side |= produced_calls(side)
        if exp_side & act_side:
            return True
    return False


def scan(root: Path, files: list[str] | None, max_per: int) -> dict:
    root = root.resolve()
    if files:
        targets = []
        for f in files:
            p = Path(f)
            if not p.is_absolute() and not p.exists() and (root / p).exists():
                p = root / p
            targets.append(p.resolve())
    else:
        targets = list(iter_files(root))
    hits: dict[str, list[dict]] = defaultdict(list)
    counts: Counter = Counter()
    meta: dict[str, tuple[str, str]] = {}
    langs: Counter = Counter()
    test_files, tests_seen = 0, 0

    def record(check, rule, msg, rel, line, snippet):
        counts[check] += 1
        meta[check] = (rule, msg)
        if counts[check] <= max_per:
            hits[check].append({"file": rel, "line": line, "snippet": snippet.strip()[:150]})

    for path in targets:
        suffix = path.suffix.lower()
        if suffix not in ALL:
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        text = read_text(path, limit=1_000_000)
        if not text:
            continue
        looks_test = is_test_path(rel) or (suffix in PY and re.search(r"(?m)^\s*(?:async\s+)?def test_", text) and "conftest" not in rel)
        if not looks_test:
            continue
        test_files += 1
        langs[suffix] += 1
        lines = text.splitlines()
        clock_ok = bool(CLOCK_CONTROL.search(text))
        seeded = bool(SEEDED.search(text))
        faked_http = bool(HTTP_FAKED.search(text))
        for check, rule, lang, rx, msg in COMPILED:
            if suffix not in lang:
                continue
            if (check == "wall-clock" and clock_ok) or (check == "unseeded-random" and seeded) or (check == "real-network" and faked_http):
                continue
            for m in rx.finditer(text):
                ln = text.count("\n", 0, m.start()) + 1
                line = lines[ln - 1] if ln - 1 < len(lines) else ""
                if "test_smells: ignore" in line:
                    continue
                record(check, rule, msg, rel, ln, line)
        # assertion analysis
        if suffix in PY:
            for ln, name, _src, has_assert, mock_only, self_ref in python_tests(text):
                tests_seen += 1
                if self_ref:
                    record("expected-from-code-under-test", "TEST-ORACLE-01",
                           "Expected value is derived from the code under test — a wrong implementation can still pass; check for an independent oracle",
                           rel, ln, f"def {name}(…)")
                if not has_assert:
                    record("no-assertion", "TEST-ORACLE-01", "Test asserts nothing — it can only fail by crashing", rel, ln, f"def {name}(…)")
                elif mock_only:
                    record("mock-only-assertions", "TEST-BEH-01", "Only checks that mocks were called — would it fail if the result were wrong?", rel, ln, f"def {name}(…)")
            continue
        family = "js" if suffix in JS else "jvm" if suffix in JVM else "go" if suffix in GO else "php" if suffix in PHP else "cs" if suffix in CS else None
        if family is None:
            continue
        for ln, name, body in brace_tests(text, family):
            tests_seen += 1
            if SKIP_IN_BODY.search(body):
                continue
            if not ASSERT_WORDS.search(body):
                record("no-assertion", "TEST-ORACLE-01", "Test asserts nothing — it can only fail by crashing (check helpers before reporting)", rel, ln, name)
            elif MOCK_ONLY.search(body) and not NON_MOCK_ASSERT.search(body):
                record("mock-only-assertions", "TEST-BEH-01", "Only checks that mocks were called — would it fail if the result were wrong?", rel, ln, name)
    results = [{"check": c, "rule": meta[c][0], "message": meta[c][1], "count": counts[c], "hits": hits[c]}
               for c in sorted(counts, key=lambda k: -counts[k])]
    return {"root": str(root), "test_files": test_files, "tests_analysed": tests_seen,
            "by_extension": dict(langs), "results": results}


def to_markdown(res: dict) -> str:
    out = [f"# Test-suite leads: `{res['root']}`", "",
           "**These are LEADS (confidence: possible).** Confirm each by reading the test: assertions may live in "
           "helpers, sleeps may be deliberate. No hits ≠ a good suite — seed a defect and see whether a test fails "
           "(TEST-MUT-01).", "",
           f"Test files: {res['test_files']} {res['by_extension'] or ''} · tests analysed for assertions: "
           f"{res['tests_analysed']}", ""]
    if not res["results"]:
        out.append("No smell matched." if res["test_files"] else "No test files found.")
        return "\n".join(out) + "\n"
    out += ["| Check | Rule | Count |", "|---|---|---|"]
    out += [f"| {r['check']} | {r['rule']} | {r['count']} |" for r in res["results"]]
    for r in res["results"]:
        shown = len(r["hits"])
        more = f" (showing {shown})" if r["count"] > shown else ""
        out += ["", f"## {r['check']} — {r['message']} — {r['count']} hit(s){more}", f"_Rule: {r['rule']}_"]
        out += [f"- `{h['file']}:{h['line']}` — `{h['snippet'].replace('`', 'ʼ')}`" for h in r["hits"]]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="repository root (used for discovery and relative paths)")
    p.add_argument("--files", nargs="+", help="scan only these test files")
    p.add_argument("--max-per-check", type=int, default=20)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    res = scan(root, args.files, args.max_per_check)
    print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else to_markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
