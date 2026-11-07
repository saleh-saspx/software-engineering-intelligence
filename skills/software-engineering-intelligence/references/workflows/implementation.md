# Workflow: implementing a change (with self-review)

For features, bug fixes and enhancements written by you (the AI agent). Tier 0 tasks skip to
step 6 and report in a sentence or two. Rules cited are in `../rules/`.

## Contents
1. Size the task · 2. Understand the requirement · 3. Explore before writing · 4. Select the
rules that matter · 5. Design the smallest sufficient change · 6. Test and implement in small
steps · 7. Verify · 8. Self-review for AI failure modes · 9. Report

## 1. Size the task
Use the triage table in SKILL.md §1. Escalate for auth, money, input parsing, files, migrations,
concurrency, public contracts, irreversible operations. A bigger tier means more reading before
writing, not more prose in the answer.

## 2. Understand the requirement
- Restate the goal and acceptance criteria in one or two sentences (to yourself, or to the user if
  ambiguous).
- Identify unstated but implied requirements: validation, permissions, error cases, empty states,
  idempotency, backwards compatibility, migrations, docs.
- Ambiguity rule (AGT-UNC-01): ask when two readings lead to materially different code that is
  expensive to redo; otherwise pick the most reasonable reading and state it in the report.

## 3. Explore before writing
Spend this effort in proportion to the tier. The goal is to write code that looks like it
belongs (AGT-CONV-01).
- **Find the closest existing example** of the same kind of change (a similar endpoint, job,
  component) and follow its structure: where files go, how errors are handled, how it's tested.
  `git log --oneline -- path/` and grep are your friends.
- **Read the configs that encode conventions**: formatter, linter, type checker (`tsconfig`
  strictness, `phpstan.neon`, `pyproject.toml`, `.golangci.yml`), test setup, CI workflow.
- **Check decisions**: `docs/adr/` or equivalent; architecture tests; module boundaries
  (`scripts/deps.py` for an unfamiliar codebase).
- **Trace the path** your change sits on: entry point → validation → authorisation → business
  logic → persistence → response. Note which layer already does what (e.g. auth middleware on the
  route group), so you neither duplicate nor omit it.
- **Find what already exists** before creating helpers: utilities, value objects, base classes,
  validation rules. Duplicating an existing helper is a common AI-generated defect.

## 4. Select the rules that matter
Map what the change touches to rule areas, then skim only those rules (`../rules/index.md`):

| The change touches… | Check |
|---|---|
| Request input, forms, APIs | SEC-VAL-01, SEC-AUTHZ-01..03, SEC-INJ-01, SEC-OUT-01, API-* |
| Database reads/writes, schema | DATA-*, REL-CONS-01/03, PERF-IO-01/02, SEC-INJ-01 |
| Migrations, backfills, batch jobs | DATA-MIG-01..03, DATA-BATCH-01, DATA-BACKUP-01; run `scripts/migration_lint.py` |
| Concurrent edits, multi-row invariants | DATA-TXN-02, DATA-TXN-03, TEST-CONC-01 |
| Money, quantities, time | DATA-TYPE-01, REL-TIME-03, SEC-BIZ-01 |
| External services, queues | REL-TIME-01/02, REL-CONS-02, REL-ERR-01, CODE-BND-01 |
| Concurrency, async, background work | REL-CONC-01..03 |
| Files, paths, uploads, URLs | SEC-FILE-01, SEC-SSRF-01, SEC-REDIR-01 |
| Auth, sessions, tokens | SEC-AUTHN-*, SEC-SESS-01, SEC-CSRF-01, SEC-CRYPTO-01 |
| New module/class structure | DES-SRP-01, DES-DIP-01, DES-HIDE-01, DES-SIMP-02/03, ARCH-DEP-01 |
| Public API or library interface | API-CONTRACT-01, DES-API-01, DES-LSP-01, CODE-CMNT-01 |
| Extension points, plug-ins, webhooks | ARCH-EXT-01..03, DES-EXT-01, DATA-EVOL-01 |
| Shared or concurrent components | REL-CONC-01..04, TEST-CONC-01 |
| Feature flags, rollout | DLV-FLAG-01, DLV-REL-02 |
| LLM calls, agents, tools | SEC-AI-01, SEC-OUT-01 |
| Dependencies, build, config | DLV-DEPS-01, SEC-SUPPLY-01, DLV-CFG-01, SEC-SECRET-01 |

## 5. Design the smallest sufficient change
- Prefer extending the existing pattern over introducing a new one (AGT-CONV-02, ARCH-FIT-03).
- For non-trivial changes, consider two options briefly — typically "inline in the existing
  structure" vs. "extract a unit" — and choose by: correctness, fit with conventions, testability,
  change risk, and future change on this path. Don't add an abstraction without a current force
  (DES-SIMP-02): a second implementation, a test seam, a dependency-direction need, or a contract.
- Put code where its responsibility belongs: business rules out of controllers/views when they
  are more than trivial (DES-SRP-02); I/O at the edges.
- Plan the tests: which behaviours, at which level (TEST-STRAT-01), including at least one
  negative/edge case per rule and authorisation-negative tests for protected data (TEST-SEC-01).
- Plan compatibility: migrations (expand/contract, DATA-MIG-01), API changes (API-CONTRACT-01),
  config defaults.

## 6. Test and implement in small steps
1. For a bug: write a test that reproduces it and **watch it fail** (TEST-REG-01).
2. For a feature: write or extend tests for the acceptance criteria (before or alongside code),
   with expected values taken from the requirement or worked examples — not from what the code
   returns (TEST-ORACLE-01) — and see each new test fail at least once (TEST-MUT-01).
3. Implement the minimal code; keep diffs focused (AGT-MIN-01).
4. If structural clean-up is needed to make the change easy, do it as a separate preceding step
   with tests unchanged and green (AGT-MIN-02) — "make the change easy, then make the easy change".
5. Handle the failure paths deliberately: errors propagated with context (CODE-ERR-01/03),
   resources released (REL-RES-01), timeouts on remote calls (REL-TIME-01).

## 7. Verify
Run, in increasing cost, whatever the project supports, and keep the actual results:
formatter check → linter → type checker → targeted tests → full relevant test suite → build.
For security-relevant changes also run `scripts/security_scan.py` on changed files and the
project's SAST/dependency audit if configured.
- Record each command and its outcome (pass counts, failures). If something can't be run (no
  runtime, missing services), say so and why — never imply it passed (AGT-EVID-01).
- A failing pre-existing test unrelated to your change: report it, don't "fix" it silently.

## 8. Self-review for AI failure modes
Re-read the **entire diff** (not your memory of it) with SKILL.md §5, then specifically for the
mistakes AI-written code makes most often (AGT-SELF-01):

| Failure mode | Check |
|---|---|
| Hallucinated APIs or options | Every imported symbol, method and config key exists in the installed version (open the source/docs or run it) — AGT-UNC-02 |
| Plausible but wrong logic | Walk through one normal and two edge inputs by hand |
| Over-broad error handling | No `catch (Exception)`/`except Exception` that hides failures; no swallowed errors |
| Insecure example defaults | No `verify=False`, wildcard CORS, disabled CSRF, debug flags, string-built queries |
| Unneeded abstraction | No new interface/factory/layer without a force; no speculative parameters |
| Duplicated helpers | Didn't re-implement an existing utility, validator or constant |
| Convention drift | Naming, error style, file placement and test style match neighbours |
| Tests that test mocks | Tests assert observable behaviour, would fail if the logic were wrong |
| Tests that restate the code | Expected values come from the requirement, not the implementation's output; each new test was seen failing (TEST-ORACLE-01, TEST-MUT-01) |
| Scope creep | No unrelated reformatting, renames or "improvements" outside the task |
| Leftovers | No debug prints, commented-out code, TODOs without tickets, unused imports |
| Narrating comments | Comments explain why, not what the next line does |
| Missing pieces | Migrations, docs, config defaults, feature flags, changelog where the project uses one |

Fix what you find, re-run the affected checks, then report.

## 9. Report
Keep it short and factual:
- **What changed** (files, behaviour) and **why** this approach (one or two sentences; mention
  rejected alternatives only if relevant).
- **Verification**: commands run and their results; what wasn't run and why.
- **Assumptions** made and **follow-ups** (out-of-scope issues noticed, suggested next steps).
- No self-congratulation, no restating the diff line by line.
