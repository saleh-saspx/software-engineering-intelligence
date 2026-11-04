# Workflow: code review (PRs, diffs, changed files, AI-generated code, quality gates)

Rules cited are in `../rules/`. Output template: `../../assets/templates/review-report.md`
(Tier 2–3) or the light format in SKILL.md §8 (Tier 1).

## Contents
1. Set purpose and depth · 2. Get the change and its context · 3. Run the automation ·
4. Review in passes · 5. Turn candidates into findings · 6. Decide the verdict · 7. Write it up ·
8. Reviewing AI-generated code · 9. Pre-merge quality gate

## 1. Set purpose and depth
- Read the PR description, linked issue and any design notes first (REV-CONDUCT-01). Know what
  the change is supposed to do before judging how it does it.
- Choose the tier (SKILL.md §1) from the change's risk, not its size alone. A 10-line change to an
  authorisation check deserves Tier 2.
- Very large diffs: say how you'll split attention (e.g. deep on `app/Billing`, light on
  generated files and lockfiles) and suggest splitting the PR (REV-CONDUCT-04).

## 2. Get the change and its context
- Diff against the merge base: `git diff --stat base...head`, then `git diff base...head`.
  Without git, compare the provided files to what you can infer and say so.
- **Never review the diff in isolation.** For each changed function, open its callers and
  callees as needed. Many apparent problems are handled elsewhere (route-group middleware,
  global exception handlers, ORM escaping) — and many real ones are only visible there (a new
  route registered outside the authenticated group).
- Note the ecosystem and local conventions (SKILL.md §2 step 2; `../languages/`).

## 3. Run the automation
Whatever exists and is cheap: tests (targeted at changed modules), linter, type checker,
formatter check, `scripts/security_scan.py --files <changed files>`, the project's SAST and
dependency audit. Record results; if you can't run something, say so. Don't hand-review what a
configured tool already enforces — report the tool's result instead (DLV-SA-01).

## 4. Review in passes
Go through the diff in this order — most damaging classes first, so time pressure cuts nits,
not blockers. Use the SKILL.md §5 checklist inside each pass.

1. **Behaviour and correctness** — does it do what the description says, for all reachable
   inputs? Edge cases, error paths, concurrency, idempotency, migrations.
2. **Security** — input validation, injection sinks, output encoding, authN/authZ (function and
   object level), mass assignment, secrets, data exposure in responses/logs, SSRF/redirects/files.
   For anything security-heavy, switch to `security-review.md`.
3. **Data and reliability** — transactions, consistency, timeouts, resource cleanup, N+1 and
   unbounded queries, money types, time zones.
4. **Tests** — do tests pin the new behaviour and the bug? Would they fail if the logic were
   wrong? Negative cases for permissions and validation? Flaky patterns?
5. **Design and architecture fit** — follows existing patterns and ADRs (ARCH-DEC-02); dependency
   direction (ARCH-DEP-01); responsibility placement (DES-SRP-01/02); no speculative abstraction
   (DES-SIMP-02/03); no new dependency or pattern without reason (AGT-CONV-02).
6. **Readability and conventions** — names, function focus, comments, dead code, formatting by the
   project's tools.

## 5. Turn candidates into findings
For each candidate issue:
1. **Verify it.** Trace the data or control flow far enough to know whether it is real. A
   pattern match (or a hunch) is `possible` until traced (SEC-PROC-03). If the issue is cheap
   to execute — a throwaway test, an in-memory database for an injection, `-race` for a data
   race — reproduce it in a scratch location outside the repo and mark it `confirmed`.
2. **Check context gates and the rule's `except` field.** Ecosystem idiom? Local convention?
   Documented trade-off? If so, drop it or downgrade it.
3. **Classify** the type, then severity, then confidence (`../knowledge-model.md` §4).
4. **Write a fix** you'd accept yourself — concrete, minimal, in the project's idiom. If the fix
   changes a signature or behaviour that callers or existing tests rely on, say so.
5. **Drop** what is only preference (or keep as a batched nit).

Don't manufacture findings to look thorough (REV-CONDUCT-02). Pre-existing problems in
untouched code are out of scope unless the change makes them worse or they are blocker-class;
mention them under "also noticed".

## 6. Decide the verdict
| Verdict | When |
|---|---|
| **blocked** | Any blocker (confirmed or likely): exploitable vulnerability, data loss, broken behaviour, secret exposure, failing build/tests |
| **changes requested** | Any major without an accepted rationale; missing tests for risky behaviour |
| **approve with suggestions** | Only minor issues and nits |
| **approve** | Nothing significant — say so plainly |

If key checks could not be run (e.g. no test environment), the verdict is conditional: "approve
pending a green CI run", never an unconditional approve for Tier 2–3 changes.

## 7. Write it up
Match the format to the request (SKILL.md §8): a quick review gets the light format even with
blockers in it. Lead with the verdict and the issues that block. Most severe first. Each finding:
location, what, why it matters, fix, severity, confidence, type, and optionally one rule ID at the
end (REV-CONDUCT-03). Then: verification performed, scope covered and not covered, "also noticed"
(out of scope), and — only if it helps the author — one or two lines on what is done well.
Keep each finding compact (a few sentences plus a code sketch); don't restate findings in several
sections; write in the reader's terms, not the skill's (no tier numbers, coverage codes or rule
IDs as prose). For Tier 2–3, run `scripts/check_report.py` on the report.

## 8. Reviewing AI-generated code
AI-written code tends to be fluent, plausible and consistently styled — which hides its defects.
In addition to the passes above, check specifically:
- **Existence**: every external API, method signature, config key and CLI flag exists in the
  version the project uses (AGT-UNC-02). Hallucinated calls often compile in dynamic languages.
- **Semantics vs. appearance**: the code handles the edge cases its comments claim; loops and
  conditions are right at the boundaries; error handling actually handles.
- **Copied insecure defaults**: disabled TLS verification, permissive CORS, `shell=True`, raw SQL
  string building, `dangerouslySetInnerHTML`, debug flags, sample secrets.
- **Redundancy**: re-implementations of helpers that already exist in the codebase; parallel
  abstractions next to established ones.
- **Over-engineering**: interfaces, factories and layers with one use; configuration nobody asked
  for (DES-SIMP-02/03).
- **Hollow tests**: tests that assert mocks were called, mirror the implementation, or would pass
  with the logic deleted (TEST-BEH-01).
- **Unrequested changes**: edits outside the task's scope, reformatting, renamed public symbols.
- **Licence and provenance** of large pasted blocks, if the code looks copied from elsewhere.

When the code is your own, this is the self-review of `implementation.md` §8 — do it before
presenting the change.

## 9. Pre-merge quality gate
A gate is a pass/fail decision with evidence. Each criterion is PASS, FAIL or **NOT VERIFIED**
(not run) — NOT VERIFIED is never reported as PASS.

| Criterion | Level | Evidence |
|---|---|---|
| Build succeeds | must | build command output |
| Tests pass (relevant suite) | must | test runner output |
| No blocker findings open | must | this review |
| No secrets in the diff | must | secret scan / review (SEC-SECRET-01) |
| No new high/critical dependency advisories | must | audit tool output (SEC-DEP-01) |
| Migrations reviewed for safety and reversibility | must, if present | DATA-MIG-01 |
| Public contract changes compatible or versioned | must, if present | API-CONTRACT-01 |
| Lint/type-check clean on changed files | should | tool output |
| New behaviour covered by tests | should | diff + test run |
| Docs/changelog updated where behaviour changed | should | diff |
| Majors resolved or explicitly accepted with reason | should | review thread |

Gate result: **PASS** only if every *must* is PASS; otherwise FAIL or INCOMPLETE (list the NOT
VERIFIED items). Projects may define their own gate — theirs takes precedence (constraint).
