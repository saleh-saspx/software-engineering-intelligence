#!/usr/bin/env python3
"""Lead scanner for design-pattern use and misuse (DES-PAT-*, DES-SIMP-03, DES-DI-02).

Inventories the design patterns a codebase declares — by name (`*Factory`, `*Decorator`,
`*Visitor` …) and by structure (singleton accessors, builders, visitor interfaces, wrappers of their
own interface, composites, chains, observer subjects, template methods, one-method interfaces) —
and reports leads for common misuse:

  single-implementation   interfaces / abstract classes with exactly one production
                          implementation (DES-SIMP-03)
  single-product-factory  `*Factory` types that always build the same concrete type and never
                          branch (DES-SIMP-03, DES-PAT-01)
  classic-singleton       getInstance()-style singletons and global instances (DES-DI-02, T-24)
  deep-inheritance        inheritance chains of N+ levels declared in the scanned code; framework
                          bases and exception hierarchies are not counted (DES-PAT-02)
  small-visitor           visitor interfaces declared for one or two element types (DES-PAT-06)
  name-mismatch           types named after a pattern whose structure does not match (DES-PAT-04)

Languages: Java, Kotlin, C#, PHP, TypeScript/JavaScript (comment/string stripping plus brace
matching — approximate), Python (`ast`), Go (interfaces matched to types by method names). Test
files are not analysed except to count test doubles; generated files are skipped.

Every hit is a LEAD (confidence: possible). A single implementation may be a deliberate port or
test seam; a factory may hide complex construction; a singleton may be owned by the container.
Confirm each by mapping the participants (DES-PAT-04) and stating the force the pattern resolves
(DES-PAT-01) — references/workflows/design-patterns.md §1. No hits does not mean the design is
good. Lines containing `pattern_scan: ignore` on a declaration exclude that type from the leads.

Usage: pattern_scan.py PATH [--min-depth 3] [--max-per-check 20] [--json]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import is_generated, is_test_path, iter_files, read_text  # noqa: E402

FAMILY_BY_EXT = {
    ".java": "java", ".kt": "kotlin", ".cs": "csharp", ".php": "php", ".ts": "ts", ".tsx": "ts",
    ".mts": "ts", ".cts": "ts", ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js",
    ".py": "python", ".go": "go",
}
GROUP = {"java": "jvm", "kotlin": "jvm", "ts": "js", "js": "js"}
IGNORE_MARK = "pattern_scan: ignore"

RULES = {
    "single-implementation": ("DES-SIMP-03", "Abstraction with exactly one production implementation"),
    "single-product-factory": ("DES-SIMP-03", "Factory that always builds the same concrete type and never branches"),
    "classic-singleton": ("DES-DI-02", "Classic singleton / global instance reached through a static accessor"),
    "deep-inheritance": ("DES-PAT-02", "Deep inheritance chain declared in the scanned code"),
    "small-visitor": ("DES-PAT-06", "Visitor declared for one or two element types"),
    "name-mismatch": ("DES-PAT-04", "Named after a pattern, but the structure does not match"),
}

# Last CamelCase word of a type name -> catalog label. "Handler", "Filter", "Policy" and similar are
# too ambiguous to map by name; they are recognised by structure only.
NAME_MAP = {
    "Factory": "Factory", "Builder": "Builder", "Prototype": "Prototype", "Singleton": "Singleton",
    "Adapter": "Adapter", "Bridge": "Bridge", "Composite": "Composite", "Decorator": "Decorator",
    "Wrapper": "Wrapper (Decorator / Adapter / Proxy)", "Facade": "Facade", "Flyweight": "Flyweight",
    "Proxy": "Proxy", "Middleware": "Middleware (Chain of Responsibility)",
    "Interceptor": "Interceptor (Chain of Responsibility)", "Pipeline": "Pipeline (pipes and filters)",
    "Command": "Command", "Iterator": "Iterator", "Mediator": "Mediator", "Memento": "Memento",
    "Observer": "Observer", "Listener": "Observer", "Subscriber": "Observer", "Observable": "Observer",
    "Strategy": "Strategy", "Visitor": "Visitor", "Interpreter": "Interpreter", "State": "State",
    "Locator": "Service Locator",
}
WRAPPER_NAMES = {"Decorator", "Proxy", "Wrapper (Decorator / Adapter / Proxy)"}
SKIP_SUFFIX = {"Impl", "Base", "Default", "Abstract", "Interface"}

COLLECTIONS = {
    "List", "ArrayList", "LinkedList", "Set", "HashSet", "LinkedHashSet", "TreeSet", "SortedSet",
    "Collection", "Iterable", "Array", "ReadonlyArray", "IEnumerable", "ICollection", "IList",
    "IReadOnlyList", "IReadOnlyCollection", "ISet", "Sequence", "MutableList", "MutableSet",
    "MutableCollection", "Queue", "Deque", "ArrayDeque", "Vector", "Stack", "CopyOnWriteArrayList",
    "Map", "HashMap", "LinkedHashMap", "TreeMap", "ConcurrentHashMap", "Dictionary", "IDictionary",
    "MutableMap", "ReadonlyMap", "Record", "list", "set", "tuple", "frozenset", "dict", "Mapping",
    "MutableMapping", "MutableSequence", "Iterator", "Collection",
}
NOT_PRODUCTS = {
    "ArrayList", "LinkedList", "HashMap", "LinkedHashMap", "TreeMap", "HashSet", "LinkedHashSet",
    "TreeSet", "List", "Map", "Set", "Date", "Promise", "Error", "Object", "String", "StringBuilder",
    "Array", "Dictionary", "Exception", "Regex", "Pair", "Triple", "Optional", "BigDecimal", "URL",
    "URI", "Uri", "Path", "File", "Decimal", "Lazy", "AtomicInteger", "AtomicLong", "AtomicReference",
    "CountDownLatch", "ReentrantLock", "Guid", "TimeSpan", "DateTime", "DateTimeImmutable",
    "ArrayObject", "Collection", "Carbon", "Response", "JsonResponse", "Uint8Array", "Headers",
    "Request", "URLSearchParams", "WeakMap", "WeakSet", "RuntimeException", "IllegalArgumentException",
    "IllegalStateException", "InvalidArgumentException", "TypeError", "ValueError", "KeyError",
}
EXCEPTION_RX = re.compile(r"(?:Exception|Error|Throwable|Failure)$")
LISTENER_FIELD_RX = re.compile(r"(?i)(?:listeners|observers|subscribers|handlers|callbacks|watchers|subscriptions)$")
NEXT_FIELD_RX = re.compile(r"(?i)^_*(?:next|successor)(?:_?handler|_?link|_?middleware)?$")
LOOP_RX = re.compile(r"\bfor\b|\bforeach\b|\.forEach\(|\.map\(|\.each\(|\bwhile\b|\.stream\(\)")
BRANCH_RX = re.compile(r"\b(?:if|switch|when|match|case|elif)\b|\?[^?:;\n.]+:")
GUARD_RX = re.compile(r"\bif\b[^{;\n]*\{?\s*(?:throw|raise)\b[^;\n]*;?\s*\}?|\bif\s+err\s*!=\s*nil\s*\{[^{}]*\}")
CONTROL = {"if", "for", "while", "switch", "catch", "return", "new", "throw", "else", "synchronized",
           "try", "do", "using", "lock", "foreach", "fixed", "checked", "unchecked", "when", "function",
           "typeof", "await", "yield", "super", "this", "case", "default", "delete", "in", "of"}
NOT_TYPES = {"return", "new", "throw", "else", "case", "goto", "yield", "await", "package", "import", "using",
             "namespace", "typeof", "delete"}
REGEX_PRECEDERS = set("(,=:[!&|?{};+-*%<>~^")
REGEX_WORDS = {"return", "typeof", "case", "do", "else", "in", "of", "void", "yield", "await", "delete", "throw"}

HEREDOC_RX = re.compile(r"<<<[ \t]*(['\"]?)([A-Za-z_]\w*)\1\r?\n")
CHAR_RX = re.compile(r"'(?:\\[^'\n]{1,9}|[^'\\\n])'")
JS_REGEX_RX = re.compile(r"/(?![*/])(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n\[])+/[a-z]*")
ANNOT_RX = re.compile(r"@[A-Za-z_][\w.]*(?:\((?:[^()]|\([^()]*\))*\))?")
CS_ATTR_RX = re.compile(r"(?m)^[ \t]*\[[^\]\n]*\]")
PHP_ATTR_RX = re.compile(r"#\[[^\]\n]*\]")

DECL_RX = {
    "java": re.compile(r"(?<![\w$.@])(?P<mods>(?:(?:public|protected|private|abstract|final|static|sealed|non-sealed|strictfp)\s+)*)"
                       r"(?P<kind>class|interface|enum|record)\s+(?P<name>[A-Za-z_$][\w$]*)"),
    "kotlin": re.compile(r"(?<![\w.])(?P<mods>(?:(?:public|protected|private|internal|abstract|open|final|sealed|data|enum|annotation|inner|value|inline|expect|actual|fun)\s+)*)"
                         r"(?P<kind>class|interface|object)\s+(?P<name>[A-Za-z_]\w*)"),
    "csharp": re.compile(r"(?<![\w.])(?P<mods>(?:(?:public|protected|private|internal|abstract|sealed|static|partial|readonly|ref|unsafe|new|file)\s+)*)"
                         r"(?P<kind>class|interface|struct|record(?:\s+class|\s+struct)?)\s+(?P<name>[A-Za-z_]\w*)"),
    "php": re.compile(r"(?<![\w$\\:>])(?P<mods>(?:(?:abstract|final|readonly)\s+)*)(?P<kind>class|interface|trait|enum)\s+(?P<name>[A-Za-z_]\w*)"),
    "ts": re.compile(r"(?<![\w$.])(?P<mods>(?:(?:export|default|abstract|declare)\s+)*)(?P<kind>class|interface)\s+(?P<name>[A-Za-z_$][\w$]*)"),
}
DECL_RX["js"] = DECL_RX["ts"]

JAVA_MOD = r"(?:public|protected|private|static|final|abstract|synchronized|native|default|strictfp|transient|volatile)"
CS_MOD = r"(?:public|protected|private|internal|static|virtual|override|abstract|sealed|async|extern|new|partial|unsafe|readonly|required|const|volatile)"
TS_MOD = r"(?:public|private|protected|static|async|readonly|abstract|override|declare|get|set|accessor)"
TYPE_PAT = r"[\w$.]+(?:<[^\n(){};=]*>)?(?:\[\])*\??"
JAVA_METHOD = re.compile(rf"(?m)(?:^|(?<=[;{{}}]))[ \t]*(?P<mods>(?:{JAVA_MOD}[ \t]+)*)(?:<[^>\n]*>[ \t]+)?(?P<ret>{TYPE_PAT})[ \t]+"
                         rf"(?P<name>[A-Za-z_$][\w$]*)[ \t]*\((?P<params>[^)]*)\)[^{{;=]*?(?P<end>[{{;])")
JAVA_FIELD = re.compile(rf"(?m)(?:^|(?<=[;{{}}]))[ \t]*(?P<mods>(?:{JAVA_MOD}[ \t]+)*)(?P<type>{TYPE_PAT})[ \t]+(?P<name>[A-Za-z_$][\w$]*)[ \t]*(?:=[^;\n]*)?;")
CS_METHOD = re.compile(rf"(?m)(?:^|(?<=[;{{}}]))[ \t]*(?P<mods>(?:{CS_MOD}[ \t]+)*)(?P<ret>{TYPE_PAT})[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*(?:<[^>\n]*>)?[ \t]*"
                       rf"\((?P<params>[^)]*)\)[^{{;=]*?(?P<end>\{{|;|=>)")
CS_PROP = re.compile(rf"(?m)(?:^|(?<=[;{{}}]))[ \t]*(?P<mods>(?:{CS_MOD}[ \t]+)*)(?P<type>{TYPE_PAT})[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*(?:\n[ \t]*)?(?P<end>\{{|=>|=|;)")
CS_EVENT = re.compile(r"\bevent[ \t]+[\w.<>?]+[ \t]+(?P<name>[A-Za-z_]\w*)")
KT_FUN = re.compile(r"(?m)(?:^|(?<=[;{}]))[ \t]*(?P<mods>(?:(?:public|protected|private|internal|open|override|abstract|final|suspend|inline|operator|infix|tailrec|external|actual|expect)[ \t]+)*)"
                    r"fun[ \t]+(?:<[^>\n]*>[ \t]*)?(?:[\w.<>?]+\.)?(?P<name>\w+)[ \t]*\((?P<params>[^)]*)\)(?P<tail>[^\n{=]*)(?P<end>\{|=|$)")
KT_PROP = re.compile(r"(?m)(?:^|(?<=[;{}]))[ \t]*(?P<mods>(?:(?:public|protected|private|internal|open|override|abstract|final|lateinit|const)[ \t]+)*)"
                     r"(?P<vv>val|var)[ \t]+(?P<name>\w+)[ \t]*(?::[ \t]*(?P<type>[\w.]+(?:<[^\n=]*>)?\??))?")
KT_EXPR_END = re.compile(r"\n[ \t]*(?:(?:override|private|public|protected|internal|open|abstract|suspend|inline)[ \t]+)*(?:fun|val|var|class|object|init|companion|@)\b|\n[ \t]*\}")
PHP_METHOD = re.compile(r"(?m)(?:^|(?<=[;{}]))[ \t]*(?P<mods>(?:(?:public|protected|private|static|abstract|final)[ \t]+)*)function[ \t]+&?(?P<name>\w+)[ \t]*"
                        r"\((?P<params>(?:[^()]|\([^()]*\))*)\)[ \t]*(?::[ \t]*(?P<ret>\??[\w\\|]+))?[^{;]*?(?P<end>[{;])")
PHP_FIELD = re.compile(r"(?m)(?:^|(?<=[;{}]))[ \t]*(?P<mods>(?:(?:public|protected|private|var|static|readonly)[ \t]+)+)(?P<type>\??[\w\\|]+[ \t]+)?\$(?P<name>\w+)")
TS_METHOD = re.compile(rf"(?m)(?:^|(?<=[;{{}}]))[ \t]*(?P<mods>(?:{TS_MOD}[ \t]+)*)(?P<name>#?[A-Za-z_$][\w$]*)[ \t]*\??[ \t]*(?:<[^>\n]*>)?[ \t]*"
                       rf"\((?P<params>(?:[^()]|\([^()]*\))*)\)[ \t]*(?::[ \t]*(?P<ret>[^{{;\n]+?))?[ \t]*(?P<end>\{{|;|$)")
TS_ARROW = re.compile(rf"(?m)(?:^|(?<=[;{{}}]))[ \t]*(?P<mods>(?:{TS_MOD}[ \t]+)*)(?P<name>#?[A-Za-z_$][\w$]*)[ \t]*(?::[^=\n]+)?=[ \t]*(?:async[ \t]*)?"
                      rf"(?:\([^)]*\)|[A-Za-z_$][\w$]*)[ \t]*(?::[^=\n]+)?=>")
TS_FIELD = re.compile(rf"(?m)(?:^|(?<=[;{{}}]))[ \t]*(?P<mods>(?:{TS_MOD}[ \t]+)*)(?P<name>#?[A-Za-z_$][\w$]*)[ \t]*[?!]?[ \t]*:[ \t]*(?P<type>[^;=\n]+)")
JS_FIELD = re.compile(r"(?m)(?:^|(?<=[;{}]))[ \t]*(?:static[ \t]+)?(?P<name>#?[A-Za-z_$][\w$]*)[ \t]*=(?!>)")
THIS_ASSIGN = re.compile(r"\bthis\.(?P<name>[A-Za-z_$][\w$]*)[ \t]*=(?!=)")

GO_TYPE = re.compile(r"(?m)^[ \t]*type[ \t]+(?P<name>[A-Za-z_]\w*)(?:\[[^\]\n]*\])?[ \t]+(?P<kind>struct|interface)[ \t]*\{")
GO_GROUP = re.compile(r"(?m)^[ \t]*type[ \t]*\(")
GO_GROUP_MEMBER = re.compile(r"(?m)^[ \t]*(?P<name>[A-Za-z_]\w*)(?:\[[^\]\n]*\])?[ \t]+(?P<kind>struct|interface)[ \t]*\{")
GO_NAMED = re.compile(r"(?m)^[ \t]*type[ \t]+(?P<name>[A-Za-z_]\w*)(?:\[[^\]\n]*\])?[ \t]+(?!struct\b|interface\b|=)\S")
GO_METHOD = re.compile(r"(?m)^func[ \t]*\([ \t]*(?:\w+[ \t]+)?\*?[ \t]*(?P<recv>[A-Za-z_]\w*)(?:\[[^\]\n]*\])?[ \t]*\)[ \t]*(?P<name>[A-Za-z_]\w*)[ \t]*(?:\[[^\]\n]*\])?\(")
GO_FUNC = re.compile(r"(?m)^func[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*(?:\[[^\]\n]*\])?\(")
GO_ONCE = re.compile(r"(?m)^[ \t]*(?:var[ \t]+)?(?P<name>[A-Za-z_]\w*)[ \t]+sync\.Once\b")


@dataclass
class Method:
    name: str
    line: int
    abstract: bool = False
    static: bool = False
    params: str = ""
    ret: str = ""
    body: str = ""
    info: dict = field(default_factory=dict)


@dataclass
class Field:
    name: str
    type: str = ""
    static: bool = False
    ctor: bool = False


@dataclass
class TypeDecl:
    name: str
    kind: str                    # class | abstract | interface | trait | enum | struct | object | type
    family: str
    file: str
    line: int
    test: bool
    pkg: str
    mods: str = ""
    bases: list = field(default_factory=list)       # superclasses
    impls: list = field(default_factory=list)       # interfaces / super-interfaces
    raw_supers: list = field(default_factory=list)  # Kotlin / C#: (name, called) still unclassified
    methods: list = field(default_factory=list)
    fields: list = field(default_factory=list)
    body: str = ""
    sealed: bool = False
    functional: bool = False
    ignored: bool = False
    enum_constants: list = field(default_factory=list)
    hints: dict = field(default_factory=dict)       # label -> {"name", "structure"}
    singleton: str = ""
    info: dict = field(default_factory=dict)

    @property
    def group(self) -> str:
        return GROUP.get(self.family, self.family)


# ---------------------------------------------------------------- text helpers
class LineIndex:
    def __init__(self, text: str):
        self.starts = [0] + [m.end() for m in re.finditer("\n", text)]

    def line(self, pos: int) -> int:
        return bisect_right(self.starts, pos)


def strip_code(text: str, fam: str) -> str:
    """Blank comments and string/char/regex literals (newlines kept), so braces can be matched."""
    out = list(text)
    n = len(text)
    i = 0
    last_sig, last_word, word = "", "", []

    def blank(a: int, b: int) -> None:
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        c = text[i]
        nx = text[i + 1] if i + 1 < n else ""
        if c == "/" and nx == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
            continue
        if c == "/" and nx == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
            continue
        if c == "#" and fam == "php" and nx != "[":
            j = text.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
            continue
        if fam == "php" and c == "<" and text.startswith("<<<", i):
            m = HEREDOC_RX.match(text, i)
            if m:
                end = re.compile(r"\n[ \t]*" + re.escape(m.group(2)) + r"\b").search(text, m.end())
                j = n if not end else end.end()
                blank(i, j)
                i = j
                continue
        if c == '"' and fam in ("java", "kotlin", "csharp") and text.startswith('"""', i):
            j = text.find('"""', i + 3)
            j = n if j < 0 else j + 3
            blank(i, j)
            i = j
            continue
        if c == "'" and fam in ("java", "kotlin", "csharp", "go"):
            m = CHAR_RX.match(text, i)
            if m:
                blank(i, m.end())
                i = m.end()
            else:
                i += 1
            continue
        if c in "\"'" or (c == "`" and fam in ("ts", "js", "go")):
            verbatim = fam == "csharp" and c == '"' and (text[i - 1:i] == "@" or text[max(0, i - 2):i] in ("$@", "@$"))
            multiline = c == "`" or fam == "php" or verbatim
            raw = c == "`" and fam == "go"
            j = i + 1
            while j < n:
                ch = text[j]
                if ch == "\\" and not verbatim and not raw:
                    j += 2
                    continue
                if ch == c:
                    if verbatim and j + 1 < n and text[j + 1] == c:
                        j += 2
                        continue
                    j += 1
                    break
                if ch == "\n" and not multiline:
                    break
                j += 1
            blank(i, j)
            i = j
            last_sig, last_word = '"', ""
            continue
        if c == "/" and fam in ("ts", "js"):
            lw = "".join(word) if word else last_word
            if not last_sig or last_sig in REGEX_PRECEDERS or lw in REGEX_WORDS:
                m = JS_REGEX_RX.match(text, i)
                if m:
                    blank(i, m.end())
                    i = m.end()
                    word, last_sig, last_word = [], "/", ""
                    continue
        if c.isalnum() or c in "_$":
            word.append(c)
            last_sig, last_word = c, ""
        else:
            if word:
                last_word = "".join(word)
                word = []
            if not c.isspace():
                last_sig, last_word = c, ""
        i += 1
    return "".join(out)


def brace_pairs(s: str) -> dict:
    pairs, stack = {}, []
    for i, c in enumerate(s):
        if c == "{":
            stack.append(i)
        elif c == "}" and stack:
            pairs[stack.pop()] = i
    return pairs


def flatten(s: str) -> str:
    """Keep only depth-0 text of a body; nested braces stay as `{ }` with their content blanked."""
    out, depth = [], 0
    for ch in s:
        if ch == "{":
            out.append("{" if depth == 0 else " ")
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
            out.append("}" if depth == 0 else " ")
        else:
            out.append(ch if depth == 0 or ch == "\n" else " ")
    return "".join(out)


def blank_rx(rx: re.Pattern, s: str) -> str:
    return rx.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), s)


def split_top(s: str) -> list:
    """Split on commas outside <> () [] {}."""
    parts, depth, cur = [], 0, []
    for i, ch in enumerate(s):
        if ch in "<([{":
            depth += 1
        elif ch in ">)]}" and not (ch == ">" and s[i - 1:i] == "="):
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def simple_name(t: str) -> str:
    t = re.sub(r"<.*", "", t.strip())
    t = re.sub(r"\(.*", "", t)
    t = t.split(" by ")[0].strip().lstrip("?").rstrip("?").strip()
    t = re.split(r"[.\\]", t)[-1] if t else t
    return re.sub(r"\[\]$", "", t).strip()


def type_parts(t: str) -> tuple:
    """(outer simple name, [element simple names], is_collection) for a declared type."""
    t = (t or "").strip()
    t = re.sub(r"^(?:readonly|final|const|params|ref|out|in)\s+", "", t)
    t = re.sub(r"\s*\|\s*(?:null|undefined|None)\b|\b(?:null|undefined|None)\s*\|\s*", "", t)
    t = re.sub(r"^Optional\[(.*)\]$", r"\1", t)
    t = t.strip().lstrip("?").rstrip("?")
    if not t:
        return "", [], False
    if t.endswith("[]"):
        inner = simple_name(t[:-2])
        return inner, [inner], True
    m = re.match(r"([\w$.\\]+)\s*[<\[](.*)[>\]]\s*$", t)
    if m:
        outer = simple_name(m.group(1))
        args = [simple_name(a) for a in split_top(m.group(2))]
        if outer in COLLECTIONS:
            elems = args[-1:] if outer.lower() in ("map", "hashmap", "dictionary", "idictionary", "dict", "mapping",
                                                     "mutablemap", "mutablemapping", "readonlymap", "record",
                                                     "linkedhashmap", "treemap", "concurrenthashmap") else args
            return outer, elems, True
        return outer, [], False
    return simple_name(t), [], False


def last_word(name: str) -> str:
    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z0-9]+", name.replace("_", " "))
    words = [w[:1].upper() + w[1:] for w in words]
    while len(words) > 1 and words[-1] in SKIP_SUFFIX:
        words.pop()
    return words[-1] if words else name


def parse_params(params: str, fam: str) -> list:
    out = []
    for p in split_top(params.replace("\n", " ")):
        p = re.sub(r"=.*$", "", p).strip()
        p = blank_rx(ANNOT_RX, p).strip()
        if fam in ("java", "csharp"):
            p = re.sub(r"^(?:final|this|params|ref|out|in|scoped)\s+", "", p)
            m = re.match(r"(?P<type>.+?)\s+(?P<name>[A-Za-z_$][\w$]*)$", p)
            if m:
                out.append((m.group("name"), m.group("type").strip()))
        elif fam == "kotlin":
            m = re.match(r"(?:(?:private|protected|public|internal|override|open)\s+)*(?:val|var)?\s*(?P<name>\w+)\s*:\s*(?P<type>.+)$", p)
            if m:
                out.append((m.group("name"), m.group("type").strip()))
        elif fam == "php":
            m = re.match(r"(?:(?:public|protected|private|readonly)\s+)*(?P<type>\??[\w\\|]+)?\s*&?\.{0,3}\$(?P<name>\w+)$", p)
            if m:
                out.append((m.group("name"), (m.group("type") or "").strip()))
        elif fam in ("ts", "js"):
            m = re.match(r"(?:(?:public|private|protected|readonly|override)\s+)*(?P<name>[A-Za-z_$][\w$]*)\s*\??\s*(?::\s*(?P<type>.+))?$", p)
            if m:
                out.append((m.group("name"), (m.group("type") or "").strip()))
    return out


# ---------------------------------------------------------------- C-family parsing
def scan_header(s: str, i: int, fam: str):
    """Return (index of the body's `{` or None, header text) starting after the type name."""
    paren = angle = 0
    j, n = i, len(s)
    while j < n:
        c = s[j]
        if c == "(":
            paren += 1
        elif c == ")":
            paren = max(0, paren - 1)
        elif c == "<":
            angle += 1
        elif c == ">" and angle > 0 and s[j - 1:j] != "=":
            angle -= 1
        elif paren == 0 and angle == 0:
            if c == "{":
                return j, s[i:j]
            if c in ";}":
                return None, s[i:j]
            if c == "\n" and fam == "kotlin":
                cur = s[i:j].rstrip()
                rest = s[j + 1:j + 200].lstrip()
                if not (rest.startswith((":", ",", "{", "where", "(")) or cur.endswith((":", ",", "("))):
                    return None, s[i:j]
        j += 1
    return None, s[i:j]


def strip_leading_group(h: str, open_ch: str, close_ch: str) -> str:
    h = h.lstrip()
    if not h.startswith(open_ch):
        return h
    depth = 0
    for k, ch in enumerate(h):
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return h[k + 1:]
    return ""


def parse_supers(d: TypeDecl, fam: str, header: str) -> str:
    """Fill bases/impls/raw_supers from the header; return primary-constructor parameters if any."""
    ctor_params = ""
    h = " ".join(header.split())
    if fam in ("java", "php", "ts", "js"):
        h = strip_leading_group(h, "<", ">")  # type parameters may contain `extends`
        if fam == "java" and d.info.get("record"):
            m = re.match(r"\s*(?:<[^{]*?>)?\s*\((.*?)\)", h)
            ctor_params = m.group(1) if m else ""
        ext = re.search(r"\bextends\s+(.+?)(?=\bimplements\b|\bpermits\b|$)", h)
        imp = re.search(r"\bimplements\s+(.+?)(?=\bpermits\b|$)", h)
        ext_names = [simple_name(x) for x in split_top(ext.group(1))] if ext else []
        if ext and "(" in ext.group(1) and fam in ("ts", "js"):
            ext_names = []  # mixin expression
        if d.kind == "interface":
            d.impls += ext_names
        else:
            d.bases += ext_names
        if imp:
            d.impls += [simple_name(x) for x in split_top(imp.group(1))]
        if fam == "java" and re.search(r"\bpermits\b", h):
            d.sealed = True
        return ctor_params
    # Kotlin / C#: generics, primary constructor, then ": supertypes"
    rest = strip_leading_group(h, "<", ">")
    if rest.lstrip().startswith(("constructor", "private constructor", "internal constructor", "protected constructor")):
        rest = re.sub(r"^\s*(?:\w+\s+)?constructor", "", rest)
    if rest.lstrip().startswith("("):
        body = rest.lstrip()
        depth = 0
        for k, ch in enumerate(body):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    ctor_params = body[1:k]
                    rest = body[k + 1:]
                    break
    m = re.match(r"\s*:\s*(.+)$", rest)
    if m:
        sup = re.split(r"\bwhere\b", m.group(1))[0]
        for part in split_top(sup):
            d.raw_supers.append((simple_name(part), "(" in part.split(" by ")[0]))
    return ctor_params


def fields_from_params(d: TypeDecl, params: str, fam: str) -> None:
    for name, typ in parse_params(params, fam):
        d.fields.append(Field(name, typ, False, True))


def body_after(s: str, pairs: dict, open_idx: int) -> str:
    close = pairs.get(open_idx)
    return s[open_idx + 1:close] if close else ""


def expr_body(s: str, start: int) -> str:
    m = KT_EXPR_END.search(s, start, min(len(s), start + 600))
    return s[start:m.start() if m else min(len(s), start + 300)]


class MemberParser:
    """Reads the depth-0 members (methods, fields, constructor parameters) of one type body."""

    def __init__(self, d: TypeDecl, fam: str, s: str, start: int, end: int, pairs: dict, li: LineIndex):
        flat = flatten(s[start:end])
        if fam == "csharp":
            flat = blank_rx(CS_ATTR_RX, flat)
        if fam == "php":
            flat = blank_rx(PHP_ATTR_RX, flat)
        self.flat = blank_rx(ANNOT_RX, flat)
        self.d, self.fam, self.s, self.base, self.pairs, self.li = d, fam, s, start, pairs, li
        self.seen = set()

    def add_method(self, name, pos, abstract, static, params="", ret="", body="") -> None:
        line = self.li.line(self.base + pos)
        if (name, line) not in self.seen:
            self.seen.add((name, line))
            self.d.methods.append(Method(name, line, abstract, static, params, (ret or "").strip(), body))

    def body_at(self, m: re.Match) -> str:
        return body_after(self.s, self.pairs, self.base + m.start("end")) if m.group("end") == "{" else ""

    def parse(self) -> None:
        {"java": self.java_csharp, "csharp": self.java_csharp, "kotlin": self.kotlin, "php": self.php}.get(self.fam, self.ts_js)()

    def java_csharp(self) -> None:
        d, fam, s, base = self.d, self.fam, self.s, self.base
        mods_set = set(re.findall(r"\w+", JAVA_MOD if fam == "java" else CS_MOD))
        for m in (JAVA_METHOD if fam == "java" else CS_METHOD).finditer(self.flat):
            name, ret, mods = m.group("name"), m.group("ret"), m.group("mods") or ""
            if name in CONTROL or ret in NOT_TYPES or ret.split(".")[-1] == "new":
                continue
            if ret in mods_set or name == d.name:  # constructor
                fields_from_params(d, m.group("params"), fam)
                continue
            endtok = m.group("end")
            body = self.body_at(m)
            if endtok == "=>":
                stop = s.find(";", base + m.end("end"))
                body = s[base + m.end("end"):stop if stop > 0 else base + m.end("end") + 200]
            abstract = "abstract" in mods or (d.kind == "interface" and endtok == ";" and "default" not in mods and "static" not in mods)
            self.add_method(name, m.start("name"), abstract, "static" in mods, m.group("params"), ret, body)
        ctor = re.compile(rf"(?m)^[ \t]*(?:(?:public|protected|private|internal)[ \t]+)?{re.escape(d.name)}[ \t]*\((?P<params>[^)]*)\)")
        for m in ctor.finditer(self.flat):
            fields_from_params(d, m.group("params"), fam)
        for m in (JAVA_FIELD if fam == "java" else CS_PROP).finditer(self.flat):
            typ, name, mods = m.group("type"), m.group("name"), m.group("mods") or ""
            if typ not in NOT_TYPES and name not in CONTROL:
                d.fields.append(Field(name, typ, "static" in mods or "const" in mods))
        if fam == "csharp":
            for m in CS_EVENT.finditer(self.flat):
                d.info.setdefault("events", []).append(m.group("name"))

    def kotlin(self) -> None:
        d = self.d
        for m in KT_FUN.finditer(self.flat):
            mods, endtok = m.group("mods") or "", m.group("end")
            body = expr_body(self.s, self.base + m.end("end")) if endtok == "=" else self.body_at(m)
            abstract = "abstract" in mods or (d.kind == "interface" and endtok not in ("{", "="))
            ret = re.sub(r"^\s*:\s*", "", m.group("tail") or "")
            self.add_method(m.group("name"), m.start("name"), abstract, False, m.group("params"), ret, body)
        for m in KT_PROP.finditer(self.flat):
            d.fields.append(Field(m.group("name"), (m.group("type") or "").strip(), False))
            if m.group("vv") == "var":
                d.info["mutable"] = True

    def php(self) -> None:
        d = self.d
        for m in PHP_METHOD.finditer(self.flat):
            name, mods = m.group("name"), m.group("mods") or ""
            if name == "__construct":
                fields_from_params(d, m.group("params"), "php")
            abstract = "abstract" in mods or d.kind == "interface"
            self.add_method(name, m.start("name"), abstract, "static" in mods, m.group("params"), m.group("ret") or "", self.body_at(m))
        for m in PHP_FIELD.finditer(self.flat):
            d.fields.append(Field(m.group("name"), (m.group("type") or "").strip(), "static" in m.group("mods")))

    def ts_js(self) -> None:
        d, s = self.d, self.s
        for m in TS_METHOD.finditer(self.flat):
            name, mods = m.group("name"), m.group("mods") or ""
            if name in CONTROL:
                continue
            body = self.body_at(m)
            if name == "constructor":
                fields_from_params(d, m.group("params"), self.fam)
                d.fields += [Field(a.group("name"), "", False) for a in THIS_ASSIGN.finditer(body)]
                continue
            abstract = "abstract" in mods or d.kind == "interface"
            self.add_method(name, m.start("name"), abstract, "static" in mods, m.group("params"), m.group("ret") or "", body)
        for m in TS_ARROW.finditer(self.flat):
            pos = self.base + m.end()
            nxt = re.match(r"\s*\{", s[pos:pos + 50])
            eol = s.find("\n", pos)
            body = body_after(s, self.pairs, pos + nxt.end() - 1) if nxt else s[pos:eol if eol > 0 else pos + 200]
            self.add_method(m.group("name"), m.start("name"), False, "static" in (m.group("mods") or ""), "", "", body)
        for m in TS_FIELD.finditer(self.flat):
            name, typ = m.group("name"), m.group("type").strip()
            if name in CONTROL:
                continue
            if "=>" in typ and d.kind == "interface":
                self.add_method(name, m.start("name"), True, False, "", typ)
            else:
                d.fields.append(Field(name, typ, "static" in (m.group("mods") or "")))
        if self.fam == "js":
            d.fields += [Field(m.group("name"), "", False) for m in JS_FIELD.finditer(self.flat)]


def parse_members(d: TypeDecl, fam: str, s: str, start: int, end: int, pairs: dict, li: LineIndex) -> None:
    MemberParser(d, fam, s, start, end, pairs, li).parse()


def parse_cfamily(text: str, fam: str, rel: str, test: bool, pkg: str) -> tuple:
    s = strip_code(text, fam)
    pairs = brace_pairs(s)
    li = LineIndex(s)
    raw = text.splitlines()
    decls, anon = [], []
    for m in DECL_RX[fam].finditer(s):
        name, kind, mods = m.group("name"), m.group("kind"), m.group("mods") or ""
        if name in ("extends", "implements") or (fam == "php" and name.lower() in ("extends", "implements")):
            continue
        open_idx, header = scan_header(s, m.end(), fam)
        line = li.line(m.start("kind"))
        d = TypeDecl(name, "class", fam, rel, line, test, pkg, mods=mods)
        d.ignored = IGNORE_MARK in (raw[line - 1] if line - 1 < len(raw) else "")
        words = set(mods.split())
        kind = kind.split()[0]
        if kind == "record":
            d.info["record"] = True
        if kind == "interface":
            d.kind = "interface"
        elif kind == "trait":
            d.kind = "trait"
        elif kind == "enum" or "enum" in words:
            d.kind = "enum"
        elif kind == "struct":
            d.kind = "struct"
        elif kind == "object":
            d.kind = "object"
        elif "abstract" in words or ("sealed" in words and fam == "kotlin"):
            d.kind = "abstract"
        d.sealed = d.sealed or "sealed" in words
        head = s[max(0, m.start() - 300):m.start()]
        head = head[max(head.rfind("}"), head.rfind(";")) + 1:]
        d.functional = "fun" in words or "@FunctionalInterface" in head
        if fam == "csharp" and "static" in words:
            d.info["static_class"] = True
        ctor_params = parse_supers(d, fam, header)
        if ctor_params:
            fields_from_params(d, ctor_params, fam)
            if fam == "kotlin" and re.search(r"\bvar\b", ctor_params):
                d.info["mutable"] = True
        if open_idx is not None:
            close = pairs.get(open_idx, len(s) - 1)
            d.body = s[open_idx + 1:close]
            parse_members(d, fam, s, open_idx + 1, close, pairs, li)
            if d.kind == "enum" and fam in ("java", "kotlin", "csharp", "php", "ts"):
                flat = flatten(d.body)
                first = flat.split(";")[0] if fam in ("java", "kotlin") else flat
                if fam == "php":
                    d.enum_constants = re.findall(r"\bcase\s+(\w+)", flat)
                else:
                    d.enum_constants = [re.match(r"\s*@?(\w+)", c).group(1) for c in split_top(first)
                                        if re.match(r"\s*@?\w+\s*(?:\(|\{|$)", c)]
        decls.append(d)
    # anonymous implementations: count toward implementation totals
    anon_rx = {
        "java": [re.compile(r"\bnew\s+(?P<name>[A-Z][\w$]*(?:\.[A-Z][\w$]*)*)\s*(?:<[^(){};]*>)?\s*\([^;{}]*\)\s*\{")],
        "kotlin": [re.compile(r"\bobject\s*:\s*(?P<name>[A-Z][\w.]*)")],
        "php": [re.compile(r"\bnew\s+class\b[^{;]*?\b(?:implements|extends)\s+(?P<name>[\w\\]+)")],
        "ts": [re.compile(r":\s*(?P<name>[A-Z][\w$]*)(?:<[^=;\n]*>)?\s*=\s*\{"), re.compile(r"\bsatisfies\s+(?P<name>[A-Z][\w$]*)")],
    }.get(fam, [])
    for rx in anon_rx:
        for m in rx.finditer(s):
            anon.append((fam, simple_name(m.group("name")), rel, li.line(m.start()), test))
    return decls, anon, s


# ---------------------------------------------------------------- Python parsing
def _name_of(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _name_of(node.value)
    if isinstance(node, ast.Call):
        return _name_of(node.func)
    return ""


def _ann(node) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - very old Python
        return _name_of(node)


def _is_abstract(fn) -> bool:
    if any(_name_of(dec) == "abstractmethod" for dec in fn.decorator_list):
        return True
    body = [b for b in fn.body if not (isinstance(b, ast.Expr) and isinstance(getattr(b, "value", None), ast.Constant)
                                       and isinstance(b.value.value, str))]
    return len(body) == 1 and isinstance(body[0], ast.Raise) and "NotImplementedError" in _ann(body[0].exc)


def _self_attr_call(n, owner: str) -> bool:
    return isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
        and n.func.value.id == owner


def _returned_products(fn) -> set:
    """Capitalised constructor calls a function returns, directly or through a local variable."""
    assigned, products = {}, set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            assigned[n.targets[0].id] = _name_of(n.value.func)
    for n in ast.walk(fn):
        if isinstance(n, ast.Return) and n.value is not None:
            if isinstance(n.value, ast.Call):
                products.add(_name_of(n.value.func))
            elif isinstance(n.value, ast.Name) and n.value.id in assigned:
                products.add(assigned[n.value.id])
    return {p for p in products if p[:1].isupper() and p not in NOT_PRODUCTS and not EXCEPTION_RX.search(p)}


def _self_loops(fn) -> list:
    """(attribute, methods called on the loop variable, loop variable called directly) for `for x in self.attr`."""
    loops = []
    for n in ast.walk(fn):
        if isinstance(n, ast.For) and isinstance(n.iter, ast.Attribute) and isinstance(n.iter.value, ast.Name) \
                and n.iter.value.id == "self" and isinstance(n.target, ast.Name):
            var = n.target.id
            calls = {c.func.attr for c in ast.walk(n) if _self_attr_call(c, var)}
            direct = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == var for c in ast.walk(n))
            loops.append((n.iter.attr, calls, direct))
    return loops


def _python_method(fn, protocol: bool) -> Method:
    decos = {_name_of(x) for x in fn.decorator_list}
    abstract = _is_abstract(fn) or (protocol and all(isinstance(b, (ast.Pass, ast.Expr)) for b in fn.body))
    meth = Method(fn.name, fn.lineno, abstract, bool(decos & {"staticmethod", "classmethod"}),
                  ", ".join(a.arg for a in fn.args.args), _ann(fn.returns))
    nodes = list(ast.walk(fn))
    meth.info.update(
        returns_self=any(isinstance(r, ast.Return) and isinstance(r.value, ast.Name) and r.value.id == "self" for r in nodes),
        self_calls={n.func.attr for n in nodes if _self_attr_call(n, "self")},
        branches=any((isinstance(n, ast.If) and not (len(n.body) == 1 and isinstance(n.body[0], ast.Raise) and not n.orelse))
                     or isinstance(n, ast.IfExp) or type(n).__name__ == "Match" for n in nodes),
        products=_returned_products(fn),
        loops=_self_loops(fn),
        instance_refs=any(re.search(r"(?i)instance", getattr(n, "attr", "") or getattr(n, "id", "") or "")
                          for n in nodes if isinstance(n, (ast.Attribute, ast.Name))),
    )
    return meth


def _init_fields(fn) -> list:
    fields = [Field(a.arg, _ann(a.annotation), False, True) for a in fn.args.args[1:]]
    for n in ast.walk(fn):
        targets = n.targets if isinstance(n, ast.Assign) else [n.target] if isinstance(n, ast.AnnAssign) else []
        for t in targets:
            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                fields.append(Field(t.attr, _ann(getattr(n, "annotation", None)), False))
    return fields


def _python_class(node, rel: str, test: bool, pkg: str, raw: list) -> TypeDecl:
    bases = [b for b in (_name_of(x) for x in node.bases) if b]
    d = TypeDecl(node.name, "class", "python", rel, node.lineno, test, pkg)
    d.ignored = IGNORE_MARK in (raw[node.lineno - 1] if node.lineno - 1 < len(raw) else "")
    d.bases = [b for b in bases if b not in ("object", "ABC", "Protocol", "Generic")]
    protocol = "Protocol" in bases
    d.info["protocol"] = protocol
    d.info["meta"] = next((_name_of(k.value) for k in node.keywords if k.arg == "metaclass"), "")
    if {"Enum", "IntEnum", "StrEnum"} & set(bases):
        d.kind = "enum"
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            d.methods.append(_python_method(item, protocol))
            if item.name == "__init__":
                d.fields += _init_fields(item)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            d.fields.append(Field(item.target.id, _ann(item.annotation), False))
        elif isinstance(item, ast.Assign):
            d.fields += [Field(t.id, "", True) for t in item.targets if isinstance(t, ast.Name)]
    if d.kind != "enum":
        if protocol:
            d.kind = "interface"
        elif any(mm.abstract for mm in d.methods):
            concrete = [mm for mm in d.methods if not mm.abstract and not mm.name.startswith("__")]
            d.kind = "abstract" if concrete else "interface"
    return d


def _module_singletons(tree, rel: str, test: bool, raw: list) -> list:
    """Module-level functions that return a `global` instance they create once."""
    out = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        names = {x for g in ast.walk(node) if isinstance(g, ast.Global) for x in g.names}
        inst = {x for x in names if re.search(r"(?i)instance|^_[A-Z_]+$", x)}
        returns_it = any(isinstance(r, ast.Return) and isinstance(r.value, ast.Name) and r.value.id in inst for r in ast.walk(node))
        if inst and returns_it and IGNORE_MARK not in (raw[node.lineno - 1] if node.lineno - 1 < len(raw) else ""):
            out.append({"file": rel, "line": node.lineno, "name": node.name, "accessor": node.name, "test": test,
                        "detail": f"module-level instance behind `{node.name}()` (global {', '.join(sorted(inst))})"})
    return out


def parse_python(text: str, rel: str, test: bool, pkg: str) -> tuple:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return [], [], 1
    raw = text.splitlines()
    decls = [_python_class(node, rel, test, pkg, raw) for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    return decls, _module_singletons(tree, rel, test, raw), 0


# ---------------------------------------------------------------- Go parsing
def parse_go(text: str, rel: str, test: bool, pkg: str) -> tuple:
    s = strip_code(text, "go")
    pairs = brace_pairs(s)
    li = LineIndex(s)
    raw = text.splitlines()
    decls, methods, singletons = [], [], []
    spans = []
    for m in GO_TYPE.finditer(s):
        spans.append((m, m.end() - 1))
    for g in GO_GROUP.finditer(s):
        depth, j = 0, g.end() - 1
        while j < len(s):
            if s[j] == "(":
                depth += 1
            elif s[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        block = s[g.end():j]
        fl = flatten(block)
        for m in GO_GROUP_MEMBER.finditer(fl):
            spans.append((m, g.end() + m.end() - 1, g.end()))
    for item in spans:
        m, open_idx = item[0], item[1]
        offset = item[2] if len(item) > 2 else 0
        name, kind = m.group("name"), m.group("kind")
        line = li.line(offset + m.start("name"))
        body = body_after(s, pairs, open_idx)
        d = TypeDecl(name, "interface" if kind == "interface" else "struct", "go", rel, line, test, pkg)
        d.ignored = IGNORE_MARK in (raw[line - 1] if line - 1 < len(raw) else "")
        d.body = body
        fl = flatten(body)
        if kind == "interface":
            if re.search(r"(?m)^[ \t]*~|\|", fl):
                d.info["constraint"] = True
            for mm in re.finditer(r"(?m)^[ \t]*(?P<name>[A-Za-z_]\w*)[ \t]*\(", fl):
                d.methods.append(Method(mm.group("name"), li.line(open_idx + 1 + mm.start("name")), True))
            d.info["embeds"] = re.findall(r"(?m)^[ \t]*([A-Za-z_][\w.]*)[ \t]*$", fl)
        else:
            d.info["embeds"] = [simple_name(e) for e in re.findall(r"(?m)^[ \t]*\*?([A-Za-z_][\w.]*)[ \t]*(?:`[^`\n]*`)?[ \t]*$", fl)]
            for fm in re.finditer(r"(?m)^[ \t]*(?P<names>[A-Za-z_]\w*(?:[ \t]*,[ \t]*[A-Za-z_]\w*)*)[ \t]+(?P<type>[^\s`]+)", fl):
                for nm in fm.group("names").split(","):
                    d.fields.append(Field(nm.strip(), fm.group("type")))
        decls.append(d)
    for m in GO_NAMED.finditer(s):
        line = li.line(m.start("name"))
        d = TypeDecl(m.group("name"), "type", "go", rel, line, test, pkg)
        decls.append(d)
    for m in GO_METHOD.finditer(s):
        brace = s.find("{", m.end())
        body = body_after(s, pairs, brace) if brace >= 0 else ""
        methods.append((pkg, m.group("recv"), m.group("name"), li.line(m.start("name")), body))
    once_vars = {m.group("name") for m in GO_ONCE.finditer(s)}
    if once_vars:
        for m in GO_FUNC.finditer(s):
            brace = s.find("{", m.end())
            body = body_after(s, pairs, brace) if brace >= 0 else ""
            used = [v for v in once_vars if re.search(rf"\b{re.escape(v)}\.Do\(", body)]
            ret = re.search(r"\breturn[ \t]+&?(?P<v>[A-Za-z_]\w*)\s*$", body.strip())
            if used and ret and m.group("name")[:1].isupper():
                line = li.line(m.start("name"))
                if IGNORE_MARK not in (raw[line - 1] if line - 1 < len(raw) else ""):
                    singletons.append({"file": rel, "line": line, "name": m.group("name"),
                                       "detail": f"package-level `{ret.group('v')}` created once (sync.Once) and reached through `{m.group('name')}()`",
                                       "accessor": m.group("name"), "test": test, "pkgname": pkg})
    return decls, methods, singletons, s


# ---------------------------------------------------------------- analysis
class Model:
    def __init__(self, decls: list):
        self.decls = decls
        self.by_name = defaultdict(list)
        for d in decls:
            self.by_name[d.name].append(d)
        self.subclasses = defaultdict(list)

    def resolve(self, name: str, ref: TypeDecl):
        cands = [c for c in self.by_name.get(name, []) if c.group == ref.group and c is not ref]
        if not cands:
            return None
        same = [c for c in cands if c.pkg == ref.pkg]
        prod = [c for c in (same or cands) if not c.test]
        return (prod or same or cands)[0]

    def classify(self) -> None:
        for d in self.decls:
            for i, (name, called) in enumerate(d.raw_supers):
                target = self.resolve(name, d)
                if target is not None:
                    is_iface = target.kind == "interface"
                elif d.family == "kotlin":
                    is_iface = not called
                else:  # C#
                    is_iface = bool(re.match(r"I[A-Z]", name)) or i > 0 or d.kind in ("interface", "struct")
                if d.kind == "interface" or is_iface:
                    d.impls.append(name)
                else:
                    d.bases.append(name)
            for b in d.bases:
                t = self.resolve(b, d)
                if t is not None:
                    self.subclasses[id(t)].append(d)

    def ancestors(self, d: TypeDecl) -> list:
        out, seen, stack = [], {id(d)}, list(d.bases) + list(d.impls)
        while stack:
            name = stack.pop()
            t = self.resolve(name, d)
            if t is None or id(t) in seen:
                continue
            seen.add(id(t))
            out.append(t)
            stack += list(t.bases) + list(t.impls)
        return out

    def super_names(self, d: TypeDecl) -> set:
        names = set(d.bases) | set(d.impls)
        for a in self.ancestors(d):
            names.add(a.name)
            names |= set(a.bases) | set(a.impls)
        return names


def add_hint(d: TypeDecl, label: str, evidence: str) -> None:
    d.hints.setdefault(label, set()).add(evidence)


GENERIC_VISIT = re.compile(r"(?i)^visit_?(?:children|all|nodes?|default|any|generic|each|or|ed|ing|s)$")


def visit_methods(d: TypeDecl) -> tuple:
    specific = [m for m in d.methods if re.match(r"(?i)^visit_?[a-z0-9]", m.name) and not GENERIC_VISIT.match(m.name)]
    plain = [m for m in d.methods if m.name.lower() == "visit"]
    count = len({m.name.lower() for m in specific}) + (len(plain) if len(plain) >= 2 else 0)
    return count, len(specific) + len(plain)


def is_fluent(m: Method, d: TypeDecl) -> bool:
    ret = (m.ret or "").strip()
    if m.info.get("returns_self"):
        return True
    if simple_name(ret) in (d.name, "this", "self", "static", "Self") or ret in ("this", "static", "self"):
        return True
    return bool(re.search(r"\breturn\s+(?:this|\$this)\s*;", m.body))


def structure_hints(d: TypeDecl, model: Model) -> None:
    supers = model.super_names(d) - {d.name}
    in_tree_abstractions = {a.name for a in model.ancestors(d) if a.kind in ("interface", "abstract")}
    names = {m.name for m in d.methods}
    # Singleton
    detail = singleton_detail(d)
    if detail:
        d.singleton = detail
        add_hint(d, "Singleton", "structure")
    # Builder
    fluent = [m for m in d.methods if not m.static and is_fluent(m, d)]
    buildish = [m for m in d.methods if re.match(r"^(?:[Bb]uild|[Cc]reate|[Mm]ake|[Cc]onstruct|[Gg]et_?[Rr]esult|to[A-Z])", m.name)]
    if d.kind not in ("interface",) and len(fluent) >= 2 and buildish:
        add_hint(d, "Builder", "structure")
    d.info["fluent"], d.info["buildish"] = len(fluent), len(buildish)
    # Prototype
    if names & {"clone", "copy", "deepCopy", "deepClone", "__copy__", "__deepcopy__", "Clone", "DeepCopy"} and d.kind != "enum":
        add_hint(d, "Prototype", "structure")
    # Visitor
    vcount, _ = visit_methods(d)
    if vcount and d.kind in ("interface", "abstract"):
        add_hint(d, "Visitor", "structure")
    if any(m.name in ("accept", "Accept") and "visitor" in m.params.lower() for m in d.methods):
        add_hint(d, "Visitor (element)", "structure")
    # Fields: wrapper / composite / chain / observer subject
    typed_wrap = False
    for f in d.fields:
        if f.static:
            continue
        outer, elems, coll = type_parts(f.type)
        if not coll and NEXT_FIELD_RX.match(f.name) and outer == d.name and d.kind in ("abstract", "interface"):
            add_hint(d, "Chain of Responsibility", "structure")
        if not coll and outer and outer in supers and outer != d.name:
            typed_wrap = True
            if NEXT_FIELD_RX.match(f.name) and outer in in_tree_abstractions:
                add_hint(d, "Chain of Responsibility", "structure")
            else:
                add_hint(d, "Decorator / Proxy (wraps its own interface)", "structure")
        if coll and any(e in supers and e != d.name for e in elems):
            add_hint(d, "Composite", "structure")
        if LISTENER_FIELD_RX.search(f.name) and any(LOOP_RX.search(m.body) and re.search(rf"\b{re.escape(f.name)}\b", m.body)
                                                   for m in d.methods):
            add_hint(d, "Observer (subject)", "structure")
    d.info["typed_wrap"] = typed_wrap
    if d.info.get("events"):
        add_hint(d, "Observer (subject, native events)", "structure")
    # Python loops: composite / observer by behaviour
    for m in d.methods:
        for attr, calls, direct in m.info.get("loops", []):
            if LISTENER_FIELD_RX.search(attr) and (calls or direct):
                add_hint(d, "Observer (subject)", "structure")
            elif m.name in calls and not m.name.startswith("__") and in_tree_abstractions:
                add_hint(d, "Composite", "structure")
    if d.family == "python":
        for f in d.fields:
            if NEXT_FIELD_RX.match(f.name) and in_tree_abstractions:
                add_hint(d, "Chain of Responsibility", "structure")
        init = next((m for m in d.methods if m.name == "__init__"), None)
        if init:
            for f in d.fields:
                if f.ctor and type_parts(f.type)[0] in supers and not NEXT_FIELD_RX.match(f.name):
                    add_hint(d, "Decorator / Proxy (wraps its own interface)", "structure")
                    d.info["typed_wrap"] = True
    # Template Method
    if d.kind == "abstract":
        abstract_names = {m.name for m in d.methods if m.abstract}
        for m in d.methods:
            if m.abstract or not abstract_names:
                continue
            called = m.info.get("self_calls") if d.family == "python" else \
                {a for a in abstract_names if re.search(rf"(?<![\w$]){re.escape(a)}\s*\(", m.body)}
            if called and set(called) & abstract_names and m.name not in abstract_names:
                add_hint(d, "Template Method", "structure")
                break


def singleton_detail(d: TypeDecl) -> str:
    if d.test:
        return ""
    if d.family == "python":
        if any(m.name == "__new__" and m.info.get("instance_refs") for m in d.methods):
            return "`__new__` returns a cached instance"
        if re.search(r"(?i)singleton", d.info.get("meta", "")):
            return f"metaclass `{d.info['meta']}`"
        if any(f.static and re.match(r"(?i)^_+instances?$", f.name) for f in d.fields) and \
                any(m.static and re.match(r"(?i)^(get_)?instance$", m.name) for m in d.methods):
            return "class-level `_instance` behind a classmethod accessor"
        return ""
    if d.kind == "enum" and d.enum_constants == ["INSTANCE"]:
        return "enum with a single INSTANCE constant"
    if d.family == "kotlin":
        if d.kind == "object" and d.info.get("mutable"):
            return "`object` holding mutable state (`var`)"
        if re.search(r"\bfun\s+getInstance\s*\(", d.body) and re.search(r"\bINSTANCE\b|\binstance\b", d.body):
            return "companion `getInstance()` caching an instance"
        return ""
    accessor = re.compile(r"(?i)^(get_?)?(instance|default|shared(instance)?|current)$")
    static_self = any(f.static and type_parts(f.type)[0] in (d.name, "self", "static") for f in d.fields) or \
        any(f.static and re.search(rf"Lazy<\s*{re.escape(d.name)}\s*>", f.type) for f in d.fields)
    lazy_prop = d.family == "csharp" and any(
        f.static and accessor.match(f.name) and type_parts(f.type)[0] == d.name for f in d.fields)
    acc = [m for m in d.methods if m.static and accessor.match(m.name)]
    php_self = d.family == "php" and re.search(r"(?:static|self)::\$\w*instance\w*", d.body, re.I)
    ts_static = d.family in ("ts", "js") and re.search(r"\bstatic\s+(?:get\s+)?(?:getInstance|instance)\b", d.body)
    if acc and (static_self or php_self or ts_static or any(simple_name(m.ret) in (d.name, "self", "static") for m in acc)):
        return f"static `{acc[0].name}()` returning a cached `{d.name}`"
    if lazy_prop:
        name = next(f.name for f in d.fields if f.static and accessor.match(f.name))
        return f"static property `{name}` holding the single `{d.name}`"
    if ts_static and static_self:
        return f"static accessor caching the single `{d.name}`"
    return ""


def go_implementations(go_decls: list, go_methods: list) -> None:
    """Match Go interfaces to named types by method names (signatures ignored)."""
    mset = defaultdict(set)
    for pkg, recv, name, _line, _body in go_methods:
        mset[(pkg, recv)].add(name)
    types = [d for d in go_decls if d.kind in ("struct", "type")]
    by_simple = defaultdict(list)
    for d in types:
        by_simple[d.name].append(d)

    def methods_of(d, depth=0):
        names = set(mset.get((d.pkg, d.name), set()))
        if depth < 3:
            for e in d.info.get("embeds", []):
                for t in by_simple.get(simple_name(e), []):
                    names |= methods_of(t, depth + 1)
        return names

    ifaces = {d.name: d for d in go_decls if d.kind == "interface"}

    def iface_methods(d, depth=0):
        names = {m.name for m in d.methods}
        partial = False
        for e in d.info.get("embeds", []):
            t = ifaces.get(simple_name(e))
            if t is not None and depth < 3:
                sub, p = iface_methods(t, depth + 1)
                names |= sub
                partial = partial or p
            else:
                partial = True
        return names, partial

    for d in go_decls:
        if d.kind != "interface" or d.info.get("constraint"):
            continue
        need, partial = iface_methods(d)
        if not need:
            continue
        impls = [t for t in types if need <= methods_of(t)]
        d.info["go_impls"] = impls
        d.info["partial"] = partial


@dataclass
class Corpus:
    """Everything parsed from the tree, before analysis."""
    decls: list = field(default_factory=list)
    anon: list = field(default_factory=list)              # (family, name, file, line, test)
    extra_singletons: list = field(default_factory=list)  # Python module / Go package-level accessors
    go_methods: list = field(default_factory=list)        # (pkg, receiver, name, line, body)
    files: Counter = field(default_factory=Counter)
    parse_errors: int = 0
    texts: dict = field(default_factory=dict)             # production file -> (family, comment-free text)


class Findings:
    def __init__(self):
        self.hits = defaultdict(list)

    def record(self, check: str, d_or_hit, detail: str = "") -> None:
        if isinstance(d_or_hit, TypeDecl):
            if d_or_hit.ignored or d_or_hit.test:
                return
            self.hits[check].append({"file": d_or_hit.file, "line": d_or_hit.line, "name": d_or_hit.name, "detail": detail})
        else:
            self.hits[check].append({k: d_or_hit[k] for k in ("file", "line", "name", "detail")})


def collect(root: Path) -> Corpus:
    c, cached = Corpus(), 0
    for path in sorted(iter_files(root)):
        name = path.name.lower()
        fam = FAMILY_BY_EXT.get(path.suffix.lower())
        if not fam or name.endswith((".d.ts", ".d.mts", ".d.cts", ".min.js", ".blade.php")):
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        text = read_text(path, limit=1_500_000)
        if not text or is_generated(text):
            continue
        test = is_test_path(rel) or (fam == "python" and "conftest" in name)
        pkg = str(Path(rel).parent)
        c.files[fam] += 1
        try:
            stripped = text
            if fam == "python":
                ds, singles, err = parse_python(text, rel, test, pkg)
                c.parse_errors += err
                c.extra_singletons += singles
            elif fam == "go":
                ds, ms, singles, stripped = parse_go(text, rel, test, pkg)
                c.go_methods += ms
                c.extra_singletons += singles
            else:
                ds, an, stripped = parse_cfamily(text, fam, rel, test, pkg)
                c.anon += an
            c.decls += ds
        except (RecursionError, ValueError, IndexError) as exc:  # never let one file stop the scan
            c.parse_errors += 1
            print(f"warning: could not parse {rel}: {exc}", file=sys.stderr)
            continue
        if not test and cached < 40_000_000:  # kept to count who reaches each singleton
            c.texts[rel] = (fam, stripped)
            cached += len(stripped)
    return c


def name_label(d: TypeDecl):
    """Catalog label claimed by the type's name, or None when the name is ambiguous here."""
    lw = last_word(d.name)
    label = NAME_MAP.get(lw)
    if lw == "Locator" and not d.name.endswith("ServiceLocator"):
        return None
    if lw == "Command" and (not d.methods or d.info.get("record")):
        return None  # a command *message* (CQRS DTO) is data, not the GoF Command
    if lw == "Factory" and ("database/factories" in d.file or
                            any(re.search(r"FactoryBean|^Factory$|ModelFactory$", x) for x in d.bases + d.impls)):
        return None
    if label == "State":
        return None  # decided in state_hints, once implementations are known
    return label


def annotate(model: Model, decls: list) -> None:
    for d in decls:
        label = name_label(d)
        if label:
            add_hint(d, label, "name")
        if d.family != "go":
            structure_hints(d, model)
        elif d.kind == "interface" and visit_methods(d)[0]:
            add_hint(d, "Visitor", "structure")


def implementation_map(model: Model, corpus: Corpus) -> dict:
    """id(abstraction) -> [(implementation name, file, line, is_test)]."""
    impl_map = defaultdict(list)
    for d in corpus.decls:
        if d.kind in ("interface", "abstract", "trait") or d.family == "go":
            continue
        for a in model.ancestors(d):
            if a.kind in ("interface", "abstract"):
                impl_map[id(a)].append((d.name, d.file, d.line, d.test))
    for fam, name, rel, line, test in corpus.anon:
        ref = TypeDecl(name, "class", fam, rel, line, test, str(Path(rel).parent))
        target = model.resolve(name, ref)
        if target is not None and target.kind in ("interface", "abstract"):
            impl_map[id(target)].append((f"anonymous {name}", rel, line, test))
            for a in model.ancestors(target):
                if a.kind in ("interface", "abstract"):
                    impl_map[id(a)].append((f"anonymous {name}", rel, line, test))
    for d in corpus.decls:
        if d.family == "go" and d.kind == "interface" and "go_impls" in d.info:
            impl_map[id(d)] = [(t.name, t.file, t.line, t.test) for t in d.info["go_impls"]]
    return impl_map


def prod_count(impl_map: dict, a: TypeDecl) -> int:
    return len([i for i in impl_map.get(id(a), []) if not i[3]])


def state_hints(model: Model, decls: list, impl_map: dict) -> None:
    """Accept "State" by name only when a State hierarchy with two or more implementations exists."""
    for d in decls:
        if last_word(d.name) != "State":
            continue
        own = d.kind in ("interface", "abstract") and prod_count(impl_map, d) >= 2
        parent = any(last_word(a.name) == "State" and a.kind in ("interface", "abstract") and prod_count(impl_map, a) >= 2
                     for a in model.ancestors(d))
        if own or parent:
            add_hint(d, "State", "name")


BOUNDARY_RX = re.compile(r"(?i)(?:^|/)(?:ports?|spi|api|contracts?|gateways?|adapters?|interfaces?|plugins?|extensions?)(?:/|$)")


def single_impl_notes(d: TypeDecl, impl: tuple, tests: list) -> list:
    notes = [f"test doubles: {len(tests)}" + ("" if tests else " visible (mocking libraries may create more)")]
    if BOUNDARY_RX.search("/" + d.file):
        notes.append("boundary-like path — check whether it is a deliberate port or published contract")
    if d.family == "go":
        notes.append("declared next to its only implementation (producer-side)" if Path(impl[1]).parent == Path(d.file).parent
                     else "declared by a consumer package — usually fine as a seam")
        if d.info.get("partial"):
            notes.append("embeds interfaces outside the scan — method set partial")
    if d.info.get("protocol"):
        notes.append("Protocol — structural implementations may exist")
    if d.kind == "interface" and len(d.methods) == 1 and d.family in ("java", "ts"):
        notes.append("single method — lambdas or object literals may also implement it")
    return notes


def check_single_implementation(model: Model, decls: list, impl_map: dict, out: Findings) -> None:
    flagged = []
    for d in decls:
        if d.test or d.kind not in ("interface", "abstract") or d.sealed or d.functional or d.info.get("constraint"):
            continue
        if d.kind == "interface" and not d.methods and not (d.family == "csharp" and d.fields):
            continue  # data shapes (TS option bags, constant holders) are not behavioural abstractions
        if d.name.endswith("Mixin"):
            continue
        impls = impl_map.get(id(d), [])
        prod = [i for i in impls if not i[3]]
        tests = [i for i in impls if i[3]]
        if len(prod) != 1:
            if len(prod) >= 2 and d.kind == "interface" and len([m for m in d.methods if not m.static]) == 1 \
                    and "Visitor (element)" not in d.hints:
                add_hint(d, "Strategy / Command (one-method interface)", "structure")
            continue
        impl = prod[0]
        if d.name.endswith(("Custom", "Fragment")) and impl[0] == d.name + "Impl":
            continue  # Spring Data repository fragment convention
        kind = "abstract class" if d.kind == "abstract" else "interface"
        flagged.append((d, impl))
        out.record("single-implementation", d, f"{kind} with 1 production implementation: `{impl[0]}` ({impl[1]}:{impl[2]}) · "
                                               + " · ".join(single_impl_notes(d, impl, tests)))
    # report only the most specific abstraction of a chain that ends in the same single implementation
    redundant = {(d.file, d.line) for d, impl in flagged for other, impl2 in flagged
                 if other is not d and impl2 == impl and d in model.ancestors(other)}
    out.hits["single-implementation"] = [h for h in out.hits["single-implementation"] if (h["file"], h["line"]) not in redundant]


FRAMEWORK_FACTORY_RX = re.compile(r"FactoryBean|AbstractFactoryBean|^Factory$|ModelFactory$|DjangoModelFactory|SQLAlchemyModelFactory|BaseFactory")


def factory_products(d: TypeDecl, go_bodies: list) -> tuple:
    """(products built, whether any method branches beyond guard clauses, methods inspected)."""
    products, branching, seen = set(), False, 0
    if d.family == "python":
        for m in d.methods:
            if m.name.startswith("__"):
                continue
            seen += 1
            products |= m.info.get("products", set())
            branching = branching or m.info.get("branches", False)
    elif d.family == "go":
        for body in go_bodies:
            seen += 1
            for pm in re.finditer(r"\breturn[ \t]+&?(?P<p>[A-Za-z_][\w.]*)[ \t]*[{(]", body):
                parts = pm.group("p").split(".")
                last = parts[-1]
                if len(parts) > 1 and not last.startswith("New"):
                    continue
                products.add(last[3:] if last.startswith("New") and len(last) > 3 else last)
            branching = branching or bool(re.search(r"\b(?:if|switch|case|select)\b", GUARD_RX.sub(" ", body)))
    else:
        for m in d.methods:
            if m.name in ("__construct", "constructor", d.name):
                continue
            seen += 1
            body = m.body
            found = set(re.findall(r"\breturn\s+new\s+([A-Z][\w$\\.]*)", body))
            for var, cls in re.findall(r"\b(\$?\w+)\s*=\s*new\s+([A-Z][\w$\\.]*)", body):
                if re.search(rf"\breturn\s+{re.escape(var)}\s*;", body):
                    found.add(cls)
            if d.family == "kotlin":
                found |= set(re.findall(r"(?:\breturn\s+|^\s*)([A-Z]\w*)\s*\(", body, re.M))
            if not found:
                found = set(re.findall(r"\bnew\s+([A-Z][\w$\\.]*)", body))
            products |= {simple_name(p) for p in found}
            branching = branching or bool(BRANCH_RX.search(GUARD_RX.sub(" ", body)))
    products = {p for p in products if p and p not in NOT_PRODUCTS and not EXCEPTION_RX.search(p)}
    return products, branching, seen


def check_single_product_factories(model: Model, corpus: Corpus, impl_map: dict, out: Findings) -> None:
    go_by_recv = defaultdict(list)
    for pkg, recv, _name, _line, body in corpus.go_methods:
        go_by_recv[(pkg, recv)].append(body)
    for d in corpus.decls:
        if d.test or last_word(d.name) != "Factory" or d.kind in ("interface", "abstract", "trait", "enum"):
            continue
        if "database/factories" in d.file or any(FRAMEWORK_FACTORY_RX.search(x) for x in d.bases + d.impls) or \
                any(m.name == "definition" for m in d.methods):
            continue
        if any(prod_count(impl_map, a) >= 2 for a in model.ancestors(d) if a.kind in ("interface", "abstract")):
            continue  # one of several interchangeable creators (Factory Method / Abstract Factory)
        products, branching, seen = factory_products(d, go_by_recv.get((d.pkg, d.name), []))
        d.info["factory_products"] = sorted(products)
        if seen and len(products) == 1 and not branching:
            out.record("single-product-factory", d, f"always builds `{next(iter(products))}` and never branches — call the constructor "
                                                    f"or let the container build it, unless construction is complex or the product is "
                                                    f"expected to vary")


ACCESSOR_RX = re.compile(r"(?i)^(get_?)?(instance|default|shared(instance)?|current)$")


def singleton_reach_rx(s: dict):
    """Regex that finds other files reaching a class-based singleton (None for accessor functions)."""
    cls = re.escape(s["cls"]) if s.get("cls") else ""
    if not cls:
        return None
    if s.get("accessor"):
        return re.compile(rf"\b{cls}\s*(?:\.|::|->)\s*{re.escape(s['accessor'])}\b")
    if s["detail"].startswith("`object`"):
        return re.compile(rf"\b{cls}\.\w")
    if s["detail"].startswith("`__new__`"):
        return re.compile(rf"\b{cls}\s*\(")
    if s["detail"].startswith("static property"):
        prop = re.search(r"`(\w+)`", s["detail"]).group(1)
        return re.compile(rf"\b{cls}\.{re.escape(prop)}\b")
    return re.compile(rf"\b{cls}\s*(?:\.|::)\s*(?:INSTANCE|Instance|instance|getInstance)\b")


def singleton_users(s: dict, texts: dict) -> list:
    rx = singleton_reach_rx(s)
    acc = s.get("accessor") or ""
    src_dir = str(Path(s["file"]).parent)
    users = []
    for f, (fam, t) in texts.items():
        if f == s["file"]:
            continue
        if rx is not None:
            ok = rx.search(t)
        elif fam == "go":  # package-qualified from other packages, bare inside the same one
            ok = re.search(rf"(?<![\w.]){re.escape(acc)}\s*\(", t) if str(Path(f).parent) == src_dir else \
                re.search(rf"\b{re.escape(Path(src_dir).name)}\.{re.escape(acc)}\s*\(", t)
        else:  # Python module-level accessor: imported or called through the module
            mod = Path(s["file"]).stem
            ok = re.search(rf"\bimport\b[^\n]*\b{re.escape(acc)}\b|\b{re.escape(mod)}\.{re.escape(acc)}\s*\(", t)
        if ok:
            users.append(f)
    return users


def check_singletons(corpus: Corpus, out: Findings) -> None:
    singles = []
    for d in corpus.decls:
        if d.singleton and not d.ignored and not d.test:
            acc = next((m.name for m in d.methods if m.static and ACCESSOR_RX.match(m.name)), None)
            singles.append({"file": d.file, "line": d.line, "name": d.name, "detail": d.singleton, "accessor": acc, "cls": d.name})
    singles += [{**s, "cls": None} for s in corpus.extra_singletons if not s.get("test")]
    for s in singles:
        users = singleton_users(s, corpus.texts)
        s["detail"] += f" · reached from {len(users)} other production file(s)" + (f", e.g. {users[0]}" if users else "")
        out.record("classic-singleton", s)


def inheritance_chain(model: Model, d: TypeDecl) -> list:
    """The class followed by its in-tree superclasses (interfaces, traits and mixins not counted)."""
    out, cur, seen = [d], d, {id(d)}
    while True:
        nxt = None
        for b in cur.bases:
            t = model.resolve(b, cur)
            if t is not None and id(t) not in seen and t.kind not in ("interface", "trait") and not t.name.endswith("Mixin"):
                nxt = t
                break
        if nxt is None:
            return out
        seen.add(id(nxt))
        out.append(nxt)
        cur = nxt


def check_deep_inheritance(model: Model, decls: list, min_depth: int, out: Findings) -> None:
    for d in decls:
        if d.test or d.family == "go" or d.kind in ("interface", "trait", "enum") or model.subclasses.get(id(d)):
            continue
        c = inheritance_chain(model, d)
        if len(c) < min_depth:
            continue
        external = [b for b in c[-1].bases if model.resolve(b, c[-1]) is None]
        if any(EXCEPTION_RX.search(n) or n in ("Exception", "BaseException") for n in [x.name for x in c] + external):
            continue  # exception taxonomies are deep by design
        txt = " → ".join(f"`{x.name}`" for x in c) + (f" → external `{external[0]}` (not counted)" if external else "")
        out.record("deep-inheritance", d, f"{len(c)} levels declared here: {txt}")


def check_small_visitors(model: Model, decls: list, out: Findings) -> None:
    for d in decls:
        if d.kind not in ("interface", "abstract"):
            continue
        if any(re.search(r"(?i)visitor|transformer|walker", x) and model.resolve(x, d) is None for x in d.bases + d.impls):
            continue  # implements a library visitor
        count, _ = visit_methods(d)
        if 1 <= count <= 2:
            out.record("small-visitor", d, f"visitor for {count} element type(s) — a type switch, pattern match or overloaded function "
                                           f"is usually simpler; keep Visitor when operations are added more often than element types")


def check_name_mismatch(model: Model, decls: list, out: Findings) -> None:
    for d in decls:
        if d.family == "go":
            continue
        labels = {lbl for lbl, ev in d.hints.items() if "name" in ev}
        external_base = any(model.resolve(b, d) is None for b in d.bases)
        if "Builder" in labels and d.kind != "interface" and not external_base and not d.info.get("fluent") \
                and not d.info.get("buildish"):
            out.record("name-mismatch", d, "named Builder but has no build step and no fluent setters — check what it actually does")
        if "Decorator" in labels and d.kind != "interface" and d.family != "js" and not d.info.get("typed_wrap") \
                and (d.family != "python" or any(f.ctor and f.type for f in d.fields)):
            out.record("name-mismatch", d, "named Decorator but holds no object of an interface it implements — a decorator wraps a "
                                           "component of its own type")
        if "Visitor" in labels and d.methods and not any(
                re.search(r"(?i)visit|^(?:enter|leave|exit|pre|post|on)(?:[A-Z_]|$)", m.name) for m in d.methods):
            out.record("name-mismatch", d, "named Visitor but declares no visit methods")
        if "Singleton" in labels and not d.singleton and d.kind != "object":
            out.record("name-mismatch", d, "named Singleton but no single-instance mechanism found (maybe container-managed — then "
                                           "drop the name)")


def build_inventory(corpus: Corpus, maxn: int) -> list:
    inventory = defaultdict(list)
    for d in corpus.decls:
        if d.test or d.ignored:
            continue
        hints = dict(d.hints)
        wrap = "Decorator / Proxy (wraps its own interface)"
        named_wrappers = [lbl for lbl in hints if lbl in WRAPPER_NAMES]
        if wrap in hints and named_wrappers:
            hints[named_wrappers[0]] = hints[named_wrappers[0]] | hints.pop(wrap)
        if "Observer (subject)" in hints and "Observer" in hints:
            hints["Observer"] = hints["Observer"] | hints.pop("Observer (subject)")
        for label, ev in hints.items():
            inventory[label].append({"name": d.name, "file": d.file, "line": d.line, "evidence": sorted(ev)})
    for s in corpus.extra_singletons:
        if not s.get("test"):
            inventory["Singleton"].append({"name": s["name"], "file": s["file"], "line": s["line"], "evidence": ["structure"]})
    return [{"pattern": k, "count": len(v),
             "by_name": sum(1 for x in v if "name" in x["evidence"]),
             "by_structure": sum(1 for x in v if "structure" in x["evidence"]),
             "instances": sorted(v, key=lambda x: (x["file"], x["line"]))[:maxn]}
            for k, v in sorted(inventory.items(), key=lambda kv: (-len(kv[1]), kv[0]))]


def scan(root: Path, min_depth: int, maxn: int) -> dict:
    corpus = collect(root)
    decls = corpus.decls
    model = Model(decls)
    model.classify()
    go_implementations([d for d in decls if d.family == "go"], corpus.go_methods)
    annotate(model, decls)
    impl_map = implementation_map(model, corpus)
    state_hints(model, decls, impl_map)
    out = Findings()
    check_single_implementation(model, decls, impl_map, out)
    check_single_product_factories(model, corpus, impl_map, out)
    check_singletons(corpus, out)
    check_deep_inheritance(model, decls, min_depth, out)
    check_small_visitors(model, decls, out)
    check_name_mismatch(model, decls, out)
    results = []
    for check in RULES:
        if out.hits.get(check):
            rows = sorted(out.hits[check], key=lambda h: (h["file"], h["line"]))
            results.append({"check": check, "rule": RULES[check][0], "message": RULES[check][1],
                            "count": len(rows), "hits": rows[:maxn]})
    return {"root": str(root), "files": dict(corpus.files), "types": len([d for d in decls if not d.test]),
            "test_types": len([d for d in decls if d.test]), "parse_errors": corpus.parse_errors,
            "min_depth": min_depth, "inventory": build_inventory(corpus, maxn), "results": results}


def to_markdown(res: dict) -> str:
    out = [f"# Design-pattern leads: `{res['root']}`", "",
           "**These are LEADS (confidence: possible).** Confirm each by mapping the participants to code (DES-PAT-04) and "
           "stating the force the pattern resolves (DES-PAT-01); a single implementation may be a deliberate port or test seam, "
           "a factory may hide complex construction. No hits ≠ a good design. Procedure: design-patterns workflow §1.", "",
           f"Files: {res['files'] or 'none'} · types analysed: {res['types']} (+{res['test_types']} in tests, used only to count "
           f"test doubles) · parse errors: {res['parse_errors']}", ""]
    if not res["files"]:
        out.append("No supported source files found.")
        return "\n".join(out) + "\n"
    out += ["## Declared patterns (inventory)", ""]
    if res["inventory"]:
        out += ["| Pattern | Instances | By name | By structure | Examples |", "|---|---|---|---|---|"]
        for row in res["inventory"]:
            ex = ", ".join(f"`{i['name']}` ({i['file']}:{i['line']})" for i in row["instances"][:3])
            out.append(f"| {row['pattern']} | {row['count']} | {row['by_name']} | {row['by_structure']} | {ex} |")
        out += ["", "_Name-only entries are claims, not facts: check the participants (DES-PAT-04). Framework mechanisms are "
                    "described by what they do (references/patterns/frameworks.md)._"]
    else:
        out.append("No pattern declared by name or recognisable by structure.")
    out += ["", "## Leads", ""]
    if not res["results"]:
        out.append("No lead matched.")
        return "\n".join(out) + "\n"
    out += ["| Check | Rule | Count |", "|---|---|---|"]
    out += [f"| {r['check']} | {r['rule']} | {r['count']} |" for r in res["results"]]
    for r in res["results"]:
        shown = len(r["hits"])
        more = f" (showing {shown})" if r["count"] > shown else ""
        out += ["", f"### {r['check']} — {r['message']} — {r['count']} hit(s){more}", f"_Rule: {r['rule']}_"]
        out += [f"- `{h['file']}:{h['line']}` `{h['name']}` — {h['detail']}" for h in r["hits"]]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="repository or module root")
    p.add_argument("--min-depth", type=int, default=3, help="report inheritance chains with at least this many in-tree levels (default 3)")
    p.add_argument("--max-per-check", type=int, default=20)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    res = scan(root, max(2, args.min_depth), args.max_per_check)
    print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else to_markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
