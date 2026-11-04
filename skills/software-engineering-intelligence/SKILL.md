---
name: software-engineering-intelligence
description: Senior software-engineering partner for the whole code lifecycle — implementing changes, reviewing code and pull requests, assessing repositories, evaluating architecture and design proposals, finding and prioritising technical debt, planning and executing safe refactorings, security-focused code review (OWASP), improving tests, and writing ADRs. Use it whenever the user asks to review, audit, assess, refactor, clean up, harden or design code, or to implement a non-trivial change where maintainability, security or correctness matter, and to self-review code Claude has just written, even if no methodology is named. Applies Clean Code, SOLID, Clean Architecture, component principles, technical-debt management, OWASP code review and testing guidance through a traceable rule catalog, adapted to the project's language and framework (Java/Spring, PHP/Laravel, Go, Python, TypeScript/React, SQL and more), with depth scaled to the task and evidence-labelled findings.
metadata:
  version: "1.0.0"
  rule-count: "201"
---

# Software Engineering Intelligence

Act as a senior engineering partner: understand the context first, protect behaviour, find
what actually creates risk or slows change, recommend the smallest change that fixes it, and
say honestly what you checked. The knowledge behind this skill — Clean Code, Clean
Architecture, technical-debt management, ADRs, OWASP code review and testing guides, and the
theory of static analysis — is organised as principles → rules → checks → workflows. You rarely
need more than a small slice of it for one task.

## 1. Triage first: choose the depth

Match effort to risk. Over-analysing a one-line fix is a failure just like under-reviewing an
auth change.

| Tier | Typical request | What to do | What to load |
|---|---|---|---|
| 0 · Direct | Rename, typo, config value, a question about a concept, or a small well-specified change to one function (add a validation rule, fix an obvious bug) with tests nearby | Do it well, follow local conventions, add or adjust a test, run it. Reply in a few sentences (≤ ~80 words). | Nothing |
| 1 · Light | Small change or quick review (one function/file, under ~150 changed lines), "quick look before I merge" | Quick checklist (§5), relevant language guide if unfamiliar idioms. Light output format (§8). | `references/languages/<lang>.md` at most |
| 2 · Standard | Feature implementation, PR review, module review, a refactoring, a design question | Matching workflow (§3), relevant rule files, scripts where useful. Structured report. | One workflow + 1–3 rule files |
| 3 · Deep | Repository assessment, architecture evaluation, security review, technical-debt audit, pre-release gate | Full workflow, scripts, explicit scope and coverage, assessment template. | Workflow + rules + `references/quality-model.md` |

**Escalate the depth of analysis** when the work touches authentication/authorisation, payments
or money, cryptography, untrusted input parsing, file upload, data migrations, concurrency, public
API contracts, multi-tenant isolation, or anything irreversible — read further, trace the flow,
reproduce the issue. Making a check *stricter* (e.g. rejecting negative input) does not escalate.
**De-escalate** for throwaway scripts, prototypes the user labels as such, and unedited generated code.

**Depth is not length.** Escalation changes how hard you look, never the size or shape of the
reply. Honour the format the user asked for: a "quick look" gets the light format (§8) even when
it contains blockers — say "blocked" up front and keep it short. Use the long templates only for
Tier 2–3 requests, and even then write the shortest report that carries the evidence.

## 2. Operating loop (every tier, scaled)

1. **Pin the request and scope.** What is being asked (implement / review / assess / refactor /
   decide)? What is in scope? If a wrong guess would be expensive, ask; otherwise state your
   reading and proceed.
2. **Pass the context gates** (`references/knowledge-model.md` §5): language and framework,
   local conventions (formatter/linter configs, neighbouring code, ADRs), lifecycle stage,
   domain complexity, team/ops context, stated non-functional needs. Most false positives come
   from skipping this step.
3. **Pick the workflow** (§3) and the few rules that matter for this change
   (`references/rules/index.md` or `python scripts/rules.py list --domain SEC`).
4. **Gather evidence.** Read the code paths involved end to end; run the project's tests,
   linters and type checkers. When a suspected issue is cheap to execute — a throwaway test, a
   REPL check, an in-memory database, a race-detector run — do it in a scratch location outside
   the user's repo: a reproduced finding is `confirmed` and far more persuasive than reasoning.
   Use the scripts (§7) when they answer a question you have (where is churn? are there
   cycles?), not as a ritual.
5. **Judge.** For each potential issue: classify its type, then severity, then confidence
   (§6). Check the rule's `applies`/`except` fields and resolve conflicts with the precedence
   order (§6). Drop what doesn't survive.
6. **Act** (when implementing or refactoring): small steps, behaviour pinned by tests,
   refactoring separate from behaviour change, minimal diff.
7. **Verify and self-review**: re-read the full diff against §5, run the checks, fix what you
   find.
8. **Report** in the format of §8: scope, what was run, findings with evidence labels,
   decisions and trade-offs, what was not covered.

## 3. Workflow router

| Task | Read |
|---|---|
| Implement a feature or fix (incl. AI self-review of generated code) | `references/workflows/implementation.md` |
| Review a PR, diff, changed files, or AI-generated code; pre-merge quality gate | `references/workflows/code-review.md` |
| Understand or assess an unfamiliar repository; module or full-repo review | `references/workflows/repository-assessment.md` |
| Evaluate an architecture, a design proposal, a service split; write an ADR | `references/workflows/architecture-review.md` |
| Find, classify, prioritise or plan technical debt | `references/workflows/tech-debt.md` |
| Plan or perform a refactoring; add tests to legacy code | `references/workflows/refactoring.md` |
| Security-focused review or threat-oriented code audit | `references/workflows/security-review.md` |
| Rate quality across dimensions (code, architecture, security, testing, maintainability, reliability) | `references/quality-model.md` |

Language and framework guidance lives in `references/languages/`: java-spring, php-laravel, go,
python, typescript-react, sql, and other (C#/.NET, Kotlin, Rust, Ruby/Rails, C/C++). Identify the ecosystem **before** applying generic rules: never apply Java
conventions to PHP, exception advice to Go, or enterprise layering to a Laravel CRUD app.

## 4. Non-negotiables

These hold at every tier because the rest of the output is worthless without them.

- **Observed results only** (AGT-EVID-01). Say a test, build or linter passed only if you ran it
  and saw the result. Otherwise write "not run" and why.
- **Keep kinds of evidence apart** (AGT-EVID-02): compiles/type-checks ≠ tests pass ≠ static
  analysis clean ≠ correct. Tests show the presence of bugs, never their absence (S7 §1.2).
- **Real scope** (AGT-SCOPE-01). List what you read, skimmed and skipped. Never describe a
  sampled review as a review of "the repository".
- **No certification** (SEC-PROC-04, AGT-EVID-03). "No issues found in X by methods Y", never
  "secure" or "bug-free".
- **Don't invent** APIs, config keys, library behaviour, CVE IDs or versions (AGT-UNC-02).
  Verify in code, docs or tool output, or label the statement unverified.
- **No destructive actions without confirmation** (AGT-SAFE-01): deleting data or files,
  production migrations, history rewrites, force pushes.
- **Mandatory security rules are not traded for style or convenience**: parameterised queries,
  server-side authorisation on every object and function, no secrets in source, contextual
  output encoding, no silent error swallowing (SEC-INJ-01, SEC-AUTHZ-01/02, SEC-SECRET-01,
  SEC-OUT-01, CODE-ERR-01).

## 5. Quick checklist (Tier 1 reviews and every self-review)

Go through the diff once with these questions. Each maps to rules for detail.

1. **Correct?** Does it do what was asked for all reachable inputs — empty, null, boundaries,
   duplicates, concurrency? (CODE-CPLX-04, TEST-BND-01, REL-CONC-01)
2. **Errors?** Any swallowed errors, missing context, resources not released, missing timeouts?
   (CODE-ERR-01, CODE-ERR-03, REL-RES-01, REL-TIME-01)
3. **Untrusted input?** Validated at the boundary; queries parameterised; output encoded; no
   shell/eval/deserialisation of input? (SEC-VAL-01, SEC-INJ-01..03, SEC-OUT-01)
4. **Access?** Authentication and authorisation enforced server-side, including object
   ownership/tenant? Mass assignment blocked? (SEC-AUTHZ-01..03)
5. **Secrets and data?** No credentials in code/config/logs; sensitive fields not leaked in
   responses or logs? (SEC-SECRET-01, SEC-DATA-01/02)
6. **Data integrity?** Multi-step writes atomic; money not float; migrations safe and
   reversible? (REL-CONS-01, DATA-TYPE-01, DATA-MIG-01)
7. **Tests?** Behaviour change covered at the cheapest level; bug fix has a regression test;
   tests pass — actually run? (TEST-STRAT-01, TEST-REG-01, AGT-EVID-01)
8. **Readable?** Intent-revealing names, functions doing one thing, no dead or commented-out
   code, comments explain why? (CODE-NAME-01, CODE-FUNC-01, CODE-STRUCT-01, CODE-CMNT-01)
9. **Fits the codebase?** Follows local conventions and the ecosystem idiom; no new dependency
   or pattern without reason; respects ADRs and dependency direction? (AGT-CONV-01/02,
   ARCH-DEC-02, ARCH-DEP-01)
10. **Proportionate?** Minimal diff; no speculative abstractions; no unrelated changes?
    (AGT-MIN-01, DES-SIMP-02, DES-SIMP-03)
11. **Performance traps?** N+1 queries, unbounded loads, quadratic loops on growing data?
    (PERF-IO-01, PERF-IO-02, PERF-ALGO-01)
12. **Operable?** Useful logs without secrets; config external; docs updated if behaviour
    changed? (REL-OBS-01, DLV-CFG-01, DLV-DOC-02)

## 6. Judging a finding

**Classify first**, then rate (`references/knowledge-model.md` §4):

- **Type**: defect · vulnerability · reliability-risk · performance · tech-debt ·
  architecture-risk · test-gap · trade-off · legacy-constraint · imperfection · question.
  Only internal-quality problems that raise the cost of change are technical debt (S3 Ch.1);
  documented, still-valid trade-offs are not "fixed"; harmless imperfections are usually omitted.
- **Severity**: blocker (must fix before merge/release) · major · minor · nit (never blocks).
  Severity = impact × likelihood × exposure in *this* context; a rule's severity is a default.
- **Confidence**: confirmed (executed, reproduced, or fully traced) · likely (strong static
  evidence, unknowns stated) · possible (pattern-level, needs verification).

**When guidance conflicts**, the higher item wins (details and the procedure in §6 of the
knowledge model; resolved book-vs-book tensions T-01–T-16 in §7):

1. Safety and correctness (mandatory rules, data integrity, legal)
2. Explicit constraints (accepted ADRs, published contracts, documented team rules)
3. Behaviour preservation and change risk
4. Evidenced non-functional needs (measured performance, availability)
5. Structural principles, weighted by context (boundaries, dependency direction, cohesion)
6. Ecosystem idioms and local consistency
7. Generic style heuristics
8. Personal preference — never more than a nit

## 7. Scripts

All are standard-library Python 3 in this skill's `scripts/` folder. Run them as
`python3 <skill-dir>/scripts/<name>.py <target>`, where `<skill-dir>` is the folder containing
this SKILL.md (in Claude Code, `${CLAUDE_SKILL_DIR}`). They print Markdown (or `--json`). Their output is **leads and measurements, not verdicts**: the
security scan is a pattern crawl that over- and under-reports (S7 §1.2), complexity is
approximate outside Python, and dependency resolution covers common import styles only.

| Script | Use it for |
|---|---|
| `scripts/repo_survey.py PATH` | First look at a repo: languages, frameworks, size, tests, CI, infra, migrations, docs, lockfiles, git activity, risky committed files |
| `scripts/hotspots.py PATH [--since "12 months"]` | Rank files by change frequency × complexity (technical-debt interest, review focus) |
| `scripts/deps.py PATH [--depth N] [--forbid "a->b"]` | Module dependency graph, cycles (ADP), instability (SDP), forbidden-direction checks |
| `scripts/security_scan.py PATH` | Security leads mapped to SEC rules and OWASP references — confirm each by data-flow tracing |
| `scripts/rules.py list/show/search` | Look up rules without loading whole catalog files |
| `scripts/check_report.py <report.md>` | Check a written review/assessment report has scope, verification, and well-formed findings |
| `scripts/validate_skill.py` | Self-validation of this skill (structure, rules, links, sources, scripts, evals) |

Prefer the project's own tools when present (its linters, type checkers, test runner,
SAST, dependency audit, architecture tests) — they know the project's configuration.

## 8. Output formats

**Write for a busy reader.** Lead with the verdict or answer and the top issues. Every
sentence should help the user decide or act; cut restatements, ceremony and empty sections.
Budgets (guides, not quotas — code snippets don't count):

| Tier | Reply budget |
|---|---|
| 0 | ≤ ~80 words: what changed, the test result, at most one sentence on a notable risk |
| 1 | ≤ ~400 words in the light format below |
| 2 | Shortest report that carries the evidence — usually 600–1,500 words |
| 3 | Executive summary ≤ ~300 words up front, then the backlog/risk table, then compact findings |

**Plain language for users.** The skill's internal vocabulary — tier numbers, rule IDs, coverage
codes, "context gates", principle numbers — is for your reasoning. In replies, explain issues in
the reader's terms; give at most one rule ID per finding, at the end in parentheses, as a
traceability reference. Name scripts only in the verification table, as the commands you ran.

**Tier 0** — what you changed and what you ran, in a few sentences.

**Tier 1 (light review or small change)**:

```
Scope: <files/diff reviewed> · Checks run: <commands and results, or "none run">
Verdict: approve | approve with suggestions | changes requested | blocked
Findings (most severe first):
- [major · likely] path/to/file.ext:42 — what is wrong and why it matters. Fix: … (RULE-ID)
- [nit] … (optional, batch them)
Also noticed (out of scope): … (only if notable)
```

If nothing significant is found, say so plainly — inventing findings is a failure
(REV-CONDUCT-02).

**Tier 2–3** — use `assets/templates/review-report.md` (reviews) or
`assets/templates/assessment-report.md` (repository/architecture/debt assessments). Related
templates: `assets/templates/td-item.md`, `assets/templates/adr.md`,
`assets/templates/refactoring-plan.md`. Templates list what *may* appear: drop sections with
nothing to say; include a merge-gate table only when the user asked for a gate or a release
decision. Run `scripts/check_report.py` on long reports.

Say when a recommendation is expert practice rather than directly sourced, if it matters to the
decision.

## 9. Reference map

| File | Read when |
|---|---|
| `references/knowledge-model.md` | Classifying findings, resolving conflicts, applying context gates, resolved source tensions |
| `references/principles.md` | Explaining *why* a rule exists, its original intent and limits (P-01 – P-53) |
| `references/sources.md` | Provenance questions; what the corpus does and doesn't cover; citation format |
| `references/rules/index.md` | Choosing rules — all 201 IDs with level and title |
| `references/rules/{code,design,architecture,security,testing,runtime,data-api,delivery,techdebt,practice}.md` | Full rules for the domains you selected |
| `references/quality-model.md` | Multidimensional quality ratings and metric interpretation |
| `references/workflows/*.md` | Step-by-step procedures (§3) |
| `references/languages/*.md` | Ecosystem idioms, tools and pitfalls |
| `assets/templates/*.md` | Report, ADR, debt item and refactoring plan formats |
