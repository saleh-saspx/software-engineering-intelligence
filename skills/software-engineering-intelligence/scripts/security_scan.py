#!/usr/bin/env python3
# security_scan: ignore-file  (this file contains the patterns themselves)
"""Pattern crawl for security and reliability *leads*, mapped to rule IDs and OWASP refs.

In the spirit of the OWASP Code Review Guide's "code crawling" appendix (S5): fast text
patterns that point a reviewer at risky sinks. Every hit is a LEAD with confidence `possible`.
Pattern matching is neither sound nor complete (S7 §1.2): it reports safe code (false
positives) and misses indirect flows (false negatives). Confirm each lead by tracing data
from an entry point to the sink before reporting a vulnerability (SEC-PROC-03).

Secret-like values are masked in the output.

Usage: security_scan.py PATH [--files F ...] [--include-tests] [--max-per-pattern 20] [--json]
Lines containing `security_scan: ignore` are skipped.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import is_test_path, iter_files, read_text  # noqa: E402

PY, PHP, JAVA, KT, GO, JS, RB, CS = {".py"}, {".php"}, {".java"}, {".kt"}, {".go"}, \
    {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte"}, {".rb", ".erb"}, {".cs", ".cshtml"}
JVM = JAVA | KT
TEMPLATES = {".html", ".htm", ".twig", ".jinja", ".j2", ".erb", ".cshtml"}
CONFIG = {".properties", ".yml", ".yaml", ".env", ".ini", ".conf", ".cfg", ".toml", ".json", ".xml"}
ANY = None  # all text files we scan

# (id, rule, category, extensions or ANY, regex, message, reference)
P = [
    # --- injection: SQL
    ("sql-php-interp", "SEC-INJ-01", "injection", PHP,
     r"(?:DB::(?:raw|select|statement|unprepared|insert|update|delete)|(?:where|orWhere|having|orderBy|select|groupBy)Raw|mysqli_query|->query)\s*\(\s*(?:\"[^\"]*\$|'[^']*'\s*\.|\"[^\"]*\"\s*\.)",
     "SQL built with interpolation/concatenation", "S5 A1; WSTG-INPV-05"),
    ("sql-py-format", "SEC-INJ-01", "injection", PY,
     r"\b(?:execute|executemany|raw|extra|text|RawSQL)\(\s*(?:f[\"']|[\"'][^\"']*[\"']\s*(?:%|\.format\(|\+))",
     "SQL built with f-string/format/concatenation", "S5 A1; WSTG-INPV-05"),
    ("sql-jvm-concat", "SEC-INJ-01", "injection", JVM,
     r"\b(?:createQuery|createNativeQuery|executeQuery|executeUpdate|execute|prepareStatement|queryForObject|queryForList|queryForMap|query|update|addBatch)\s*\(\s*\"[^\"]*\"\s*\+",
     "SQL/JPQL built by string concatenation", "S5 A1; WSTG-INPV-05"),
    ("sql-go-sprintf", "SEC-INJ-01", "injection", GO,
     r"\.(?:Query|QueryRow|Exec|Prepare)(?:Context)?\(\s*(?:ctx\s*,\s*)?(?:fmt\.Sprintf\(|\"[^\"]*\"\s*\+)",
     "SQL built with fmt.Sprintf/concatenation", "S5 A1; WSTG-INPV-05"),
    ("sql-js-template", "SEC-INJ-01", "injection", JS,
     r"\b(?:query|execute|raw|\$queryRawUnsafe|\$executeRawUnsafe|sequelize\.literal)\(\s*(?:`[^`]*\$\{|[\"'][^\"']*[\"']\s*\+)",
     "SQL built with template-literal interpolation/concatenation", "S5 A1; WSTG-INPV-05"),
    ("sql-rb-interp", "SEC-INJ-01", "injection", RB,
     r"\.(?:where|find_by_sql|order|group|having|joins|exec_query|execute)\(\s*\"[^\"]*#\{",
     "SQL fragment with string interpolation", "S5 A1; WSTG-INPV-05"),
    ("sql-cs-raw", "SEC-INJ-01", "injection", CS,
     r"(?:FromSqlRaw|ExecuteSqlRaw|SqlCommand)\(\s*(?:\$\"|\"[^\"]*\"\s*\+)",
     "Raw SQL with interpolation/concatenation", "S5 A1; WSTG-INPV-05"),
    # --- injection: commands, code, deserialisation, templates
    ("cmd-py", "SEC-INJ-02", "injection", PY,
     r"subprocess\.\w+\([^)]*shell\s*=\s*True|\bos\.(?:system|popen)\(", "Shell command execution", "WSTG-INPV-12"),
    ("cmd-php", "SEC-INJ-02", "injection", PHP,
     r"\b(?:shell_exec|exec|system|passthru|popen|proc_open)\s*\(", "Shell command execution", "WSTG-INPV-12"),
    ("cmd-jvm", "SEC-INJ-02", "injection", JVM,
     r"Runtime\.getRuntime\(\)\.exec\(", "Runtime.exec (check argument construction)", "WSTG-INPV-12"),
    ("cmd-go", "SEC-INJ-02", "injection", GO,
     r"exec\.Command(?:Context)?\([^)]*\"(?:sh|bash|cmd(?:\.exe)?)\"\s*,\s*\"(?:-c|/c)\"", "Command run through a shell", "WSTG-INPV-12"),
    ("cmd-js", "SEC-INJ-02", "injection", JS,
     r"\bexec(?:Sync)?\s*\(\s*(?:`[^`]*\$\{|[\"'][^\"']*[\"']\s*\+)", "Shell command with interpolated input", "WSTG-INPV-12"),
    ("eval-dyn", "SEC-INJ-03", "injection", PY | PHP | JS | RB,
     r"(?<![\w.])(?:eval|exec)\s*\((?!\s*\))|\bnew\s+Function\s*\(|\bcreate_function\s*\(|\bvm\.runIn\w*\(",
     "Dynamic code evaluation", "WSTG-INPV-11"),
    ("deser-py", "SEC-INJ-03", "injection", PY,
     r"\b(?:pickle|cPickle|marshal|shelve)\.loads?\(|\byaml\.load\((?![^)]*SafeLoader)(?![^)]*CSafeLoader)",
     "Unsafe deserialisation of possibly untrusted data", "X14 (not covered by S5/S6)"),
    ("deser-php", "SEC-INJ-03", "injection", PHP, r"\bunserialize\s*\(", "unserialize() on possibly untrusted data", "X14"),
    ("deser-jvm", "SEC-INJ-03", "injection", JVM,
     r"\bnew\s+ObjectInputStream\(|\b(?:enableDefaultTyping|activateDefaultTyping)\(|\bnew\s+XMLDecoder\(",
     "Native/polymorphic deserialisation", "X14"),
    ("deser-cs", "SEC-INJ-03", "injection", CS, r"\bBinaryFormatter\b", "BinaryFormatter deserialisation", "X14"),
    ("ssti", "SEC-INJ-03", "injection", PY | JS | PHP,
     r"\brender_template_string\(|\bTemplate\(\s*request|Environment\([^)]*\)\.from_string\(\s*request|\bcreateTemplate\(\s*\$",
     "Template rendered from a runtime string", "WSTG-INPV-18"),
    ("xxe", "SEC-INJ-04", "injection", JVM | PY | PHP | CS,
     r"\bDocumentBuilderFactory\.newInstance\(|\bSAXParserFactory\.newInstance\(|\bXMLInputFactory\.newInstance\(|\bxml\.(?:etree|dom|sax)\b|\blxml\.etree\b|\bLIBXML_NOENT\b|\bXmlDocument\(",
     "XML parser — verify external entities/DTDs are disabled", "WSTG-INPV-07"),
    # --- output encoding
    ("xss-blade", "SEC-OUT-01", "xss", PHP | TEMPLATES, r"\{!!(?!\s*(?:csrf_field|method_field)\(\))", "Unescaped Blade output", "S5 A3; WSTG-INPV-02"),
    ("xss-template-raw", "SEC-OUT-01", "xss", ANY,
     r"\|\s*(?:raw|safe)\b|\bmark_safe\(|\bMarkup\(|\bth:utext\b|\.html_safe\b|\bHtml\.Raw\(",
     "Raw/unescaped template output", "S5 A3; WSTG-INPV-02"),
    ("xss-dom", "SEC-OUT-01", "xss", JS | TEMPLATES,
     r"dangerouslySetInnerHTML|\bv-html\b|\.(?:innerHTML|outerHTML)\s*=|\binsertAdjacentHTML\(|\bdocument\.write(?:ln)?\(|\bbypassSecurityTrust\w+\(",
     "Raw HTML sink", "S5 A3; WSTG-CLNT-01"),
    ("xss-go", "SEC-OUT-01", "xss", GO, r"\btemplate\.(?:HTML|JS|URL)\(|\"text/template\"", "Unescaped Go template content / text/template", "S5 A3"),
    # --- authorisation and binding
    ("mass-assign-php", "SEC-AUTHZ-03", "authz", PHP,
     r"\$guarded\s*=\s*\[\s*\]|::(?:create|forceCreate|insert)\(\s*\$request->(?:all|input)\(\)\s*\)|->(?:update|fill|forceFill)\(\s*\$request->(?:all|input)\(\)\s*\)",
     "Mass assignment from request input", "S5 A4 (over-posting); WSTG-ATHZ-03"),
    ("mass-assign-other", "SEC-AUTHZ-03", "authz", RB | PY | JS,
     r"\.permit!|fields\s*=\s*['\"]__all__['\"]|Object\.assign\(\s*\w+\s*,\s*req\.body\s*\)",
     "Unrestricted attribute binding", "S5 A4; WSTG-ATHZ-03"),
    ("idor-lookup", "SEC-AUTHZ-02", "authz", PHP | PY | JVM | JS,
     r"(?:::|->)(?:find|findOrFail)\(\s*\$(?:request->|id\b)|\bget_object_or_404\(\s*\w+\s*,\s*(?:pk|id)\s*=|\.findById\(\s*(?:id|req\.params\.\w+)\s*\)|\.findByPk\(\s*req\.",
     "Object lookup by client-supplied ID — verify ownership/tenant check", "S5 A4; WSTG-ATHZ-04"),
    ("csrf-disabled", "SEC-CSRF-01", "config", ANY,
     r"\.csrf\(\)\.disable\(\)|\.csrf\(\s*\w+\s*->\s*\w+\.disable\(\)\s*\)|csrf\(AbstractHttpConfigurer::disable\)|@csrf_exempt|validateCsrfTokens\(\s*except|protected\s+\$except\s*=\s*\[\s*['\"]",
     "CSRF protection disabled or excluded", "S5 A8; WSTG-SESS-05"),
    # --- redirects, SSRF, files
    ("open-redirect", "SEC-REDIR-01", "redirect", PHP | PY | JS | JVM,
     r"redirect\(\s*\$request->(?:input|get|query)\(|res\.redirect\(\s*req\.(?:query|body|params)|redirect\(\s*request\.(?:GET|POST|args|values)|sendRedirect\(\s*request\.getParameter",
     "Redirect target taken from request", "S5 A10; WSTG-CLNT-04"),
    ("ssrf", "SEC-SSRF-01", "ssrf", PHP | PY | JS | GO,
     r"file_get_contents\(\s*\$request|Http::(?:get|post)\(\s*\$request|requests\.(?:get|post|put|head)\(\s*request\.|fetch\(\s*req\.(?:query|body)|axios\.(?:get|post)\(\s*req\.(?:query|body)|http\.Get\(\s*r\.(?:URL|FormValue)",
     "Outbound request to a request-supplied URL", "WSTG-INPV-19"),
    ("path-traversal", "SEC-FILE-01", "files", PHP | PY | JS | JVM,
     r"(?:include|require)(?:_once)?\s*\(?\s*\$_(?:GET|POST|REQUEST)|file_get_contents\(\s*\$_(?:GET|POST|REQUEST)|\bopen\(\s*request\.|(?:readFile|readFileSync|createReadStream|sendFile)\(\s*(?:req\.|path\.join\([^)]*req\.)|new\s+File\([^)]*getParameter\(",
     "File path from request input", "WSTG-ATHZ-01"),
    # --- crypto, TLS, randomness
    ("tls-off", "SEC-CRYPTO-01", "crypto", ANY,
     r"verify\s*=\s*False|InsecureSkipVerify\s*:\s*true|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED|CURLOPT_SSL_VERIFY(?:PEER|HOST)\s*,\s*(?:false|0)|['\"]verify['\"]\s*=>\s*false|NoopHostnameVerifier|ALLOW_ALL_HOSTNAME_VERIFIER|ServerCertificateValidationCallback\s*=",
     "TLS certificate verification disabled", "WSTG-CRYP-01"),
    ("weak-hash", "SEC-AUTHN-01", "crypto", ANY,
     r"\b(?:md5|sha1)\s*\(\s*\$?\w*pass|hashlib\.(?:md5|sha1)\(|MessageDigest\.getInstance\(\s*\"(?:MD5|SHA-?1)\"|createHash\(\s*['\"](?:md5|sha1)['\"]|\bmd5\.New\(\)|\bsha1\.New\(\)",
     "MD5/SHA-1 — unacceptable for passwords or signatures", "S5 A2/A6; WSTG-CRYP-04"),
    ("weak-random", "SEC-CRYPTO-01", "crypto", ANY,
     r"(?i)(?:Math\.random\(\)|\brandom\.(?:random|randint|choice|choices)\(|\b(?:mt_)?rand\(|\buniqid\(|\bnew\s+Random\().*(?:token|secret|passw|otp|nonce|salt|key)|(?:token|secret|passw|otp|nonce|salt)\w*\s*[:=].*(?:Math\.random\(\)|\brandom\.(?:random|randint|choice)|\b(?:mt_)?rand\(|\buniqid\()",
     "Non-cryptographic randomness for a security value", "WSTG-CRYP-04"),
    ("ecb-mode", "SEC-CRYPTO-01", "crypto", ANY, r"AES/ECB|MODE_ECB|aes-\d+-ecb", "ECB cipher mode", "WSTG-CRYP-04"),
    # --- secrets (values masked in output)
    ("secret-aws", "SEC-SECRET-01", "secret", ANY, r"\bAKIA[0-9A-Z]{16}\b", "AWS access key ID", "S5 A6"),
    ("secret-private-key", "SEC-SECRET-01", "secret", ANY, r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----", "Private key material", "S5 A6"),
    ("secret-token", "SEC-SECRET-01", "secret", ANY,
     r"\bghp_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b|\bxox[baprs]-[A-Za-z0-9-]{10,}|\bsk_live_[0-9a-zA-Z]{20,}|\bAIza[0-9A-Za-z_-]{35}\b|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
     "Token-shaped value (GitHub/Slack/Stripe/Google/JWT)", "S5 A6"),
    ("secret-assign", "SEC-SECRET-01", "secret", ANY,
     r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|client[_-]?secret|private[_-]?key)\b[\"']?\s*(?:[:=]|=>)\s*[\"']([^\"'\s]{8,})[\"']",
     "Hard-coded credential-like value", "S5 A6"),
    ("secret-config", "SEC-SECRET-01", "secret", CONFIG,
     r"(?im)^[ \t]*[\w.-]*(?:password|passwd|secret|api[_-]?key|token|private[_-]?key)[\w.-]*\s*[:=]\s*(?![\"']?\$\{)(?![\"']?%\()(?!\s*$)([^\s#\"']{8,})",
     "Credential-like value in a config file", "S5 A5/A6"),
    # --- configuration
    ("debug-on", "SEC-CONF-01", "config", ANY,
     r"^[ \t]*DEBUG\s*=\s*True\b|^[ \t]*APP_DEBUG\s*=\s*true\b|app\.run\([^)]*debug\s*=\s*True",
     "Debug mode enabled (verify it is not production config)", "S5 A5; WSTG-ERRH-02"),
    ("cors-any", "SEC-CONF-01", "config", ANY,
     r"Access-Control-Allow-Origin[\"']?\s*[:,]\s*[\"']\*|allowed_origins['\"]?\s*=>\s*\[\s*['\"]\*|CORS_(?:ALLOW_ALL_ORIGINS|ORIGIN_ALLOW_ALL)\s*=\s*True|origin\s*:\s*['\"]\*['\"]|AllowAnyOrigin\(\)|allowedOrigins\(\s*\"\*\"",
     "CORS allows any origin", "WSTG-CLNT-07"),
    ("hosts-any", "SEC-CONF-01", "config", PY, r"ALLOWED_HOSTS\s*=\s*\[\s*['\"]\*['\"]", "Django ALLOWED_HOSTS = ['*']", "S5 A5"),
    ("actuator-all", "SEC-CONF-01", "config", ANY,
     r"management\.endpoints\.web\.exposure\.include\s*[=:]\s*[\"']?\*|include:\s*[\"']\*[\"']", "All Spring Actuator endpoints exposed", "WSTG-CONF-05"),
    # --- errors
    ("empty-catch", "CODE-ERR-01", "errors", JVM | JS | PHP | CS,
     r"catch\s*(?:\([^)]*\))?\s*\{\s*\}|\.catch\(\s*(?:\(\s*\w*\s*\)|\w+)\s*=>\s*\{\s*\}\s*\)|\.catch\(\s*\(\)\s*=>\s*(?:null|undefined)\s*\)",
     "Empty catch — error swallowed", "S1 Ch.7; WSTG-ERRH-01"),
    ("except-pass", "CODE-ERR-01", "errors", PY,
     r"except(?:\s+[\w.,() ]+?(?:\s+as\s+\w+)?)?\s*:\s*(?:\n\s*)?(?:pass|continue|\.\.\.)\s*$",
     "Exception swallowed with pass/continue", "S1 Ch.7; WSTG-ERRH-01"),
    ("go-ignored-err", "CODE-ERR-01", "errors", GO,
     r"^[ \t]*_\s*(?:,\s*_\s*)?=\s*[^=\n]*?\.(?:Close|Write|Exec|Commit|Rollback|Encode|Flush|Remove|Unmarshal|Decode|Scan)\(|^[ \t]*(?:_\s*,\s*)?_\s*=\s*json\.Unmarshal\(",
     "Error explicitly discarded", "S1 Ch.7"),
    # --- reliability and data
    ("no-timeout-py", "REL-TIME-01", "reliability", PY,
     r"\brequests\.(?:get|post|put|patch|delete|head|request)\((?![^\n]*timeout\s*=)", "requests call without timeout (waits indefinitely)", "X6"),
    ("no-timeout-go", "REL-TIME-01", "reliability", GO,
     r"\bhttp\.(?:Get|Post|Head|PostForm)\(|&http\.Client\{\s*\}|http\.DefaultClient\b", "Default Go HTTP client has no timeout", "X6"),
    ("float-money", "DATA-TYPE-01", "data", JVM | CS | PY | JS | PHP | GO,
     r"(?i)\b(?:float|double|float32|float64)\s+\w*(?:price|amount|total|balance|cost|money|subtotal|tax)\w*\b|\bfloat\(\s*\w*(?:price|amount|total|balance|cost)|\(float\)\s*\$\w*(?:price|amount|total|balance)|:\s*(?:float|double)\s*(?:=|,|\))?.*\b(?:price|amount|total|balance)\b",
     "Binary floating point for a monetary value", "S1 G26"),
    ("float-money-dyn", "DATA-TYPE-01", "data", PY | JS,
     r"(?i)\b\w*(?:price|amount|total|subtotal|cost|balance)\w*\s*[+\-]?=\s*(?:0\.0\b|parseFloat\(|float\()|\bround\([^)\n]*(?:price|amount|total|subtotal|cost|tax)\w*\s*[*+\-/]|\.toFixed\(\s*2\s*\)",
     "Monetary arithmetic on binary floats (implicit float / rounding to cents)", "S1 G26"),
    ("naive-utcnow", "REL-TIME-03", "data", PY, r"\bdatetime\.utcnow\(\)", "Naive UTC datetime (deprecated since Python 3.12)", "X14"),
]
COMPILED = [(i, r, c, e, re.compile(rx, re.M), m, ref) for (i, r, c, e, rx, m, ref) in P]
SCAN_EXTS = PY | PHP | JVM | GO | JS | RB | CS | TEMPLATES | CONFIG | {".sh", ".sql", ".tf"}
SKIP_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock", "poetry.lock", "go.sum", "uv.lock"}
PLACEHOLDER_RE = re.compile(r"(?i)\$\{|\{\{|env\(|getenv|os\.environ|process\.env|changeme|change_me|example|xxx|your[_-]|<|placeholder|dummy|redacted|\*\*\*|test[_-]?(?:key|secret|pass)|not[_-]real|fake")


def mask(s: str) -> str:
    def _m(m):
        tok = m.group(0)
        return tok[:4] + "…" + f"[{len(tok)} chars masked]" if len(tok) > 8 else tok
    return re.sub(r"[A-Za-z0-9+/_\-]{12,}", _m, s)


def scan(root: Path, files: list[Path] | None, include_tests: bool, max_per: int) -> dict:
    root = root.resolve()
    def _resolve(f: str) -> Path:
        p = Path(f)
        if not p.is_absolute() and not p.exists() and (root / p).exists():
            p = root / p
        return p.resolve()
    targets = [_resolve(f) for f in files] if files else list(iter_files(root))
    hits: dict[str, list[dict]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    scanned = 0
    for path in targets:
        name = path.name
        suffix = ".env" if name == ".env" or name.startswith(".env.") else path.suffix.lower()
        if name.endswith(".blade.php"):
            suffix = ".php"
        if suffix not in SCAN_EXTS or name in SKIP_NAMES or name.endswith((".min.js", ".map")):
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        if not include_tests and is_test_path(rel):
            continue
        text = read_text(path, limit=1_000_000)
        if not text or "security_scan: ignore-file" in text[:400]:
            continue
        scanned += 1
        lines = text.splitlines()
        for pid, rule, cat, exts, rx, msg, ref in COMPILED:
            if exts is not None and suffix not in exts:
                continue
            for m in rx.finditer(text):
                lineno = text.count("\n", 0, m.start()) + 1
                line = lines[lineno - 1] if lineno - 1 < len(lines) else ""
                if "security_scan: ignore" in line:
                    continue
                if cat == "secret":
                    value = m.group(1) if m.groups() and m.group(1) else m.group(0)
                    if PLACEHOLDER_RE.search(value) or PLACEHOLDER_RE.search(line):
                        continue
                counts[pid] += 1
                if counts[pid] <= max_per:
                    snippet = line.strip()[:160]
                    if cat == "secret":
                        snippet = mask(snippet)
                    hits[pid].append({"file": rel, "line": lineno, "snippet": snippet})
    meta = {pid: {"rule": r, "category": c, "message": msg, "ref": ref} for (pid, r, c, e, rx, msg, ref) in COMPILED}
    results = [{"pattern": pid, **meta[pid], "count": counts[pid], "hits": hits[pid]}
               for pid in sorted(counts, key=lambda k: (meta[k]["category"], k))]
    return {"root": str(root), "files_scanned": scanned, "results": results}


def to_markdown(res: dict) -> str:
    out = [f"# Security and reliability leads: `{res['root']}`", "",
           "**These are LEADS (confidence: possible), not findings.** Text patterns over- and under-report "
           "(S7 §1.2). Trace each from an entry point to the sink and check the controls on the way "
           "before calling it a vulnerability (SEC-PROC-03). No hits ≠ secure.", "",
           f"Files scanned: {res['files_scanned']} · patterns with hits: {len(res['results'])} · "
           f"total hits: {sum(r['count'] for r in res['results'])}", ""]
    if not res["results"]:
        out.append("No pattern matched.")
    current = None
    for r in res["results"]:
        if r["category"] != current:
            current = r["category"]
            out += ["", f"## {current}", ""]
        shown = len(r["hits"])
        more = f" (showing {shown})" if r["count"] > shown else ""
        out.append(f"### {r['rule']} · {r['message']} — {r['count']} hit(s){more}")
        out.append(f"_Pattern `{r['pattern']}` · ref: {r['ref']}_")
        for h in r["hits"]:
            out.append(f"- `{h['file']}:{h['line']}` — `{h['snippet'].replace('`', 'ʼ')}`")
        out.append("")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="repository root (used for relative paths)")
    p.add_argument("--files", nargs="+", help="scan only these files (e.g. changed files)")
    p.add_argument("--include-tests", action="store_true")
    p.add_argument("--max-per-pattern", type=int, default=20)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    res = scan(root, args.files, args.include_tests, args.max_per_pattern)
    print(json.dumps(res, indent=2) if args.json else to_markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
