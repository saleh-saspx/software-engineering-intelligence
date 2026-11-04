# Workflow: repository assessment

Covers initial orientation, architecture discovery, module-level review and full repository
review. Output template: `../../assets/templates/assessment-report.md`. Quality ratings:
`../quality-model.md`. Debt register: `tech-debt.md`.

## Contents
1. Set the goal and budget · 2. Coverage levels (how to state scope honestly) · 3. Survey ·
4. Build and test · 5. Architecture discovery · 6. Choose where to read deeply · 7. Deep read ·
8. Cross-cutting passes · 9. Synthesise · 10. Variants: initial assessment, module review, full review

## 1. Set the goal and budget
The goal shapes everything: onboarding ("help me understand this"), due diligence, technical-debt
audit, pre-release readiness, security posture, or "is this architecture right for us?".
Ask if unclear and expensive to guess; otherwise state the assumed goal. Agree (or state) the
depth: a 30-minute orientation and a week-long audit produce different, both legitimate, reports.

## 2. Coverage levels
Every assessment reports coverage using these levels — never claim more than you did
(AGT-SCOPE-01). Use the plain words (inventoried, skimmed, read, traced) in reports; readers
don't know internal codes:

| Level | Meaning |
|---|---|
| inventoried | Counted/analysed by scripts only (size, complexity, churn, dependencies, pattern scan) |
| skimmed | Structure, file and function names, signatures, imports read |
| read | Logic read and understood |
| traced | Data/control flow followed across files (e.g. entry point → sink), or behaviour executed |

A **full repository review** means every non-generated, non-vendored source file was at least
skimmed and every high-risk module (auth, payments, data access, input handling, public APIs) was
read or traced. Anything less is a **sampled review** — say how the sample was chosen.

## 3. Survey
1. `python scripts/repo_survey.py PATH` — languages, frameworks, size, test files, CI, infra,
   migrations, docs/ADRs, lockfiles, committed-secret risk files, git activity.
2. Read: README, CONTRIBUTING, `docs/` (especially ADRs), build manifests, CI workflows,
   Dockerfiles/compose, environment examples.
3. Note the **intended** architecture (from docs, ADRs, framework conventions, folder names) —
   you'll compare it with the **actual** one in step 5.

## 4. Build and test
Try the documented build and test commands (DLV-BUILD-01). Record exactly what happened. A repo
that can't be built or tested from its docs is itself a finding (delivery debt). Don't spend the
whole budget fighting the environment: after a reasonable attempt, record "not run: <reason>"
and continue statically.

## 5. Architecture discovery
Build a component picture an engineer could act on:
- **Entry points**: `main` functions, HTTP routes, GraphQL schema, message consumers, scheduled
  jobs, CLI commands, webhooks. (Routes files and framework annotations are the fastest index.)
- **Modules and dependencies**: `python scripts/deps.py PATH --depth 2` (adjust depth to the
  layout). Look for cycles (ARCH-COMP-02), surprising directions (domain → infrastructure,
  ARCH-DEP-01), high-fan-in volatile modules (ARCH-COMP-03).
- **Data**: stores, schema/migrations, which modules read/write which tables, data shared across
  deployables (ARCH-STYLE-02).
- **External integrations**: third-party APIs, queues, caches, identity providers — and how
  they are wrapped (CODE-BND-01) and bounded (REL-TIME-01).
- **Deployment units**: one deployable or several; how they communicate.
- **Style and fit**: name the actual style (framework-native MVC, layered, hexagonal, modular
  monolith, services, event-driven) and judge its fit with `architecture-review.md` §3.
Record intended-vs-actual differences: they are often the most valuable findings.

## 6. Choose where to read deeply
Reading everything is rarely possible; choose deliberately and say how you chose:
- **Hotspots**: `python scripts/hotspots.py PATH --since "12 months"` — high churn × high
  complexity files carry the most interest (TD-PRI-01).
- **Risk**: authentication, authorisation, payments/money, input handling, file handling, data
  access layers, migrations, public API handlers.
- **Representative**: one typical feature end-to-end, to judge everyday code quality.
- **Leads**: top `scripts/security_scan.py` hits and `scripts/deps.py` violations.

## 7. Deep read
For each chosen area, read the logic (trace risky flows end to end), applying the rules relevant to it
(SKILL.md §5 checklist; rule files by domain). Capture findings with location, type, severity,
confidence and evidence as you go — not from memory at the end. Reproduce selectively: run a
quick check for the few top risks whose impact is numeric or likely to be disputed; don't build
a harness for every finding — assessments have a time budget too.

## 8. Cross-cutting passes
- **Security**: triage the scan leads by tracing (SEC-PROC-03); check auth/authorisation patterns
  across all routes (not just sampled files) — route files make this cheap.
- **Tests**: layout and levels, ratio of test to source files, flaky patterns, what critical paths
  lack tests, whether tests run in CI (TEST-*).
- **Delivery**: CI gates, lockfiles, dependency age and audit results if a tool is available
  (DLV-*, SEC-DEP-01) — report advisories only from tool output.
- **Operations**: logging, configuration, health checks, error handling at boundaries (REL-*).
- **Documentation and decisions**: README accuracy, ADRs vs. code (ARCH-DEC-02).

## 9. Synthesise
0. **Simulate the roadmap** if the user mentioned upcoming work: walk the planned feature through
   the current design (`tech-debt.md` §1) and note what would block or slow it.
1. **Quality profile**: rate each dimension with evidence and confidence (`../quality-model.md`).
   No overall score.
2. **Top risks**: the 3–7 issues that matter most, each with consequence and evidence.
3. **Debt register**: classify and prioritise (`tech-debt.md`), distinguishing debt from defects,
   vulnerabilities, trade-offs and harmless imperfections.
4. **Recommendations**, sequenced: *now* (blockers, cheap high-interest fixes), *next* (planned
   items with first steps), *strategic* (structural moves with ADRs) — each with cost/benefit
   (TD-DEC-04) and the smallest valuable first step.
5. **Coverage and limitations**: table of areas × coverage level; tools run and not run;
   assumptions (roadmap, scale, team).

Write it for the decision-maker: an executive summary of at most ~300 words first (verdict, top
risks, what to do first), then the backlog table, then compact findings. Use plain words for
coverage ("read in full", "traced") and keep rule IDs to one optional reference per finding.

## 10. Variants
- **Initial assessment / onboarding** (Tier 2): steps 3–6, light step 7 on one representative
  flow; output a map (components, entry points, data, integrations, how to build/test) plus the
  top risks noticed. Skip the full register.
- **Module-level review** (Tier 2): scope = one module and its interfaces. Map its inbound and
  outbound dependencies (`scripts/deps.py`), read it in full, review its tests, check its contract with
  callers. Report as a review.
- **Full repository review** (Tier 3): all steps; meet the full-review coverage definition in §2
  or call it a sampled review. Split the work by module and keep a coverage ledger as you go.
- **Pre-release readiness** (Tier 3): emphasise the quality gate (`code-review.md` §9) across the
  release diff, migrations, configuration for the target environment, rollback (DLV-REL-01),
  observability and open blockers.
