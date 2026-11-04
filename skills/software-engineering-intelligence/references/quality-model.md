# Quality evaluation model

How to rate software quality across six dimensions without collapsing it into one number.
Used by repository assessments and architecture reviews; findings feed it, it does not replace
findings.

## Contents
1. Principles of the model · 2. Rating scale and confidence · 3. Dimensions (what to inspect,
evidence, indicators) · 4. Metrics as signals · 5. Presenting the profile · 6. Limitations

## 1. Principles of the model
- **Separate dimensions.** A secure but untestable system and a well-tested but insecure one are
  different problems with different owners. Averaging hides both.
- **Evidence over impression.** Every rating cites findings, measurements or observations.
- **Context-relative.** "Adequate" means adequate for this system's lifecycle, domain and risk
  (`knowledge-model.md` §5) — a prototype and a payment platform are rated against different
  expectations; say which expectation you used.
- **Confidence is part of the rating.** A rating from one sampled module is not the same claim as
  one from a full review.

## 2. Rating scale and confidence

| Rating | Meaning |
|---|---|
| **Strong** | Practices are consistently good; issues are isolated and minor |
| **Adequate** | Sound overall; some notable issues with contained impact |
| **Weak** | Recurring issues that raise cost or risk noticeably; needs planned work |
| **Critical** | Blocker-class issues or systemic gaps; act now |
| **Not assessed** | Insufficient evidence — say what would be needed |

Confidence: **high** (broad coverage, logic read or traced, tools run), **medium** (sampled but deliberate
coverage), **low** (survey-level or a single area). Coverage levels: `workflows/repository-assessment.md` §2.

## 3. Dimensions

### 3.1 Code quality
- Inspect: naming, function and class design, complexity, duplication, error handling, comments,
  dead code, cohesion/coupling at class level.
- Evidence: sampled files read in full; `scripts/hotspots.py` complexity outliers; linter results.
- Strong: intent-revealing code, small focused units, consistent error handling, little dead code.
  Weak: god classes on hot paths, swallowed errors, pervasive duplication of rules, unclear names.
- Rules: CODE-*, DES-SRP/COH/OBJ.

### 3.2 Architecture
- Inspect: boundaries, dependency direction, cycles, modularity, domain isolation (where rules are
  rich), layering consistency, data ownership, fit for context, decision records.
- Evidence: `scripts/deps.py` graph, cycles and violations; intended-vs-actual comparison; ADRs.
- Strong: clear modules aligned with change, acyclic, enforced boundaries, structure proportionate
  to the problem. Weak: cycles, wrong-direction dependencies, shared databases between deployables,
  over- or under-engineering with visible cost.
- Rules: ARCH-*, DES-DIP/DI/SIMP.

### 3.3 Security
- Inspect: attack surface, authN/authZ coverage, input handling and injection sinks, output
  encoding, secrets, crypto, configuration, data exposure, dependencies, logging.
- Evidence: `workflows/security-review.md` results; scan leads triaged; audit tool output.
- Strong: central, consistently applied controls; no confirmed vulnerabilities; secure defaults;
  automated scanning. Critical: any confirmed exploitable high-impact vulnerability or exposed secret.
- Never rate "Strong" from code review alone without stating that dynamic testing was not performed.
- Rules: SEC-*.

### 3.4 Testing
- Inspect: testability (seams, pure cores), unit/integration/contract/E2E balance, test isolation
  and flakiness, behavioural focus, regression tests for fixed bugs, security negative tests, CI
  execution.
- Evidence: test inventory (`scripts/repo_survey.py`), test run results, sampled test files,
  coverage report if available (interpreted per TEST-COV-01).
- Strong: risky behaviour pinned at the right levels, fast reliable suite in CI. Weak: critical
  paths untested, flaky or slow suites, tests coupled to implementation.
- Rules: TEST-*.

### 3.5 Maintainability
- Inspect: technical-debt load and interest, changeability of hotspots, documentation and ADRs,
  dependency health, ownership and bus factor, build simplicity, operational complexity,
  debuggability.
- Evidence: hotspots and churn; TD register; dependency ages/audits; git authorship
  concentration; README/ADR state; build-from-scratch attempt.
- Strong: low-interest debt only, one-step build/test, current dependencies, decisions recorded.
  Weak: high-interest hotspots, outdated frameworks, single-maintainer critical modules.
- Rules: TD-*, DLV-*, CODE-CMNT-*.

### 3.6 Reliability and performance
- Inspect: failure behaviour at remote calls, timeouts and retries, resource management,
  concurrency safety, transactional consistency and idempotency, unbounded work, N+1 patterns,
  observability.
- Evidence: code paths read or traced; race-detector or load-test results if available; production
  incident history if the user can share it.
- Strong: bounded, observable, failure-aware code; consistency boundaries explicit. Weak: missing
  timeouts, non-atomic multi-step writes, races on shared state, unbounded queries.
- Label performance conclusions as measured or unmeasured (PERF-MEAS-01).
- Rules: REL-*, PERF-*, DATA-*, API-*.

## 4. Metrics as signals
Metrics point to where to look; none is a verdict.

| Metric | Indicates | Heuristic ranges | Pitfalls |
|---|---|---|---|
| Cyclomatic complexity per function | Paths to understand and test; regression ("bad fix") risk (S5) | S5 bands: 1–10 low, 11–15 medium, 16–20 high, above that very high | Table-like switches inflate it; tiny functions can still be obscure |
| Function / file length | Possible multiple responsibilities | Outliers relative to the codebase matter more than absolute numbers | Idioms differ (Go, generated code, tests) |
| Churn (commits per file over a period) | Where change (and interest) concentrates (X9) | Top decile is the focus set | Mass renames and formatting commits distort it |
| Churn × complexity (hotspot) | Debt interest candidates (TD-PRI-01) | Rank-based; top 10–20 files | Needs git history; young repos give weak signal |
| Distinct authors per file | Coordination cost; ownership | 1 author on a critical hot file = bus-factor risk | Pairing and squash merges hide authorship |
| Fan-in / fan-out, instability I = Ce/(Ca+Ce) | Change propagation; SDP compliance (S2 Ch.14) | Dependencies should point toward lower I | Depends on how components are drawn |
| Dependency cycles | ADP violations (S2 Ch.14) | Zero between components | Intra-package cycles are less severe |
| Test-to-source file ratio | Rough presence of tests | Compare across modules, not to a target | Says nothing about assertion quality |
| Line/branch coverage | What never ran under tests (TEST-COV-01) | Use gaps on risky code; no universal target | High coverage with weak assertions verifies little |
| Dependency age / advisories | Upgrade debt and exposure | Any unresolved high/critical advisory = act | Must come from current tool output |
| Defect density by module | Where defects cluster (S5 notes defect metrics for review focus) | Relative ranking | Depends on how defects are recorded |

Goodhart's law applies: once a metric becomes a target, it stops measuring. Don't propose metric
targets without discussing the behaviour they will incentivise.

## 5. Presenting the profile
A table plus one paragraph per dimension:

| Dimension | Rating | Confidence | Key evidence | Top action |
|---|---|---|---|---|
| Code quality | Adequate | medium | 3 god classes on hot paths (F-04, F-07); otherwise clean | Split `BillingService` by actor |
| … | | | | |

Order the narrative by what matters most for the user's goal (e.g. security first for a
due-diligence review, maintainability first for a debt audit).

## 6. Limitations
- Ratings are judgements from a bounded review, not measurements of the whole system.
- Static review cannot observe runtime behaviour, production configuration or real load; say so.
- Metrics are approximate (especially this skill's script heuristics outside Python) and
  context-dependent.
- Comparisons across codebases or teams using these ratings are not meaningful without a common
  method and context.
- A dimension rated without evidence must be "Not assessed", not guessed.
