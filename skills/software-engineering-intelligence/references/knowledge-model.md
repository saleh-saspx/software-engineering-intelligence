# Unified engineering knowledge model

How the skill's knowledge fits together, how findings are classified, how conflicts between
rules are resolved, and which contradictions between the source books have been settled.
Read sections 4–6 whenever two pieces of guidance pull in different directions.

## Contents
1. Layers of the model
2. How the concerns reinforce each other
3. Quality attributes
4. Taxonomy: rule levels, finding types, severity, confidence
5. Context gates — what to establish before applying any rule
6. Conflict resolution
7. Resolved tensions between sources (T-01 – T-16)
8. Exceptions and waivers

## 1. Layers of the model

```
Principles (principles.md, P-xx)        why — sourced, with intent and limits
   └─ Rules (rules/*.md, DOMAIN-AREA-NN) what — normative, levelled, with signals and fixes
        └─ Checks                        how to detect — signals, scripts, tools, questions
             └─ Workflows (workflows/)   when and in what order — per task type
                  └─ Outputs (assets/templates/) findings, reports, TD items, ADRs, plans
```

- A **principle** explains a force (e.g. "dependencies point toward policy").
- A **rule** turns it into a checkable expectation with a level, default severity, signals,
  remediation, verification and exceptions.
- A **check** is how a rule is detected: a code signal, a script (`scripts/`), an external tool,
  or a question to ask the user.
- A **workflow** sequences checks for a task (review, assessment, refactoring…).
- An **output** records results in a form people can act on.

Navigation: `rules/index.md` lists every rule ID with its title and level, so you can pick the
handful relevant to a task without loading whole catalog files.

## 2. How the concerns reinforce each other

| Concern | Main question | Sources | Reinforces / constrains |
|---|---|---|---|
| Clean Code | Can a reader understand and safely change this unit? | S1 | Makes testing and review cheaper; local smells are inputs to TD analysis |
| SOLID / design | Does each module change for one reason, and do dependencies point the right way? | S2 Ch.7–11, S1 Ch.10 | Bridges code to architecture; DIP enables testability |
| Components and architecture | Are boundaries where change and actors differ, with acyclic, stability-respecting dependencies? | S2 | Determines blast radius of change; ADRs record it |
| Domain modelling (DDD) | Does the model reflect the business language and boundaries? | X1 (extension) | Supplies *where* boundaries go when the domain is complex |
| Testing | Is behaviour pinned so change is safe? | S1 Ch.9, S2 Ch.28, X5 | Precondition for refactoring; security tests verify controls |
| Refactoring | Can structure improve without behaviour change? | S1 Ch.14/16, X3, X4 | The repayment mechanism for TD |
| Technical debt | Which structural weaknesses actually cost us, and is fixing them worth it? | S3 | Prioritises everything above against business value |
| Security | Can an adversary make it do what it shouldn't? | S5, S6 | Overrides style and design preferences; adds mandatory rules |
| Reliability / performance | Does it keep working, fast enough, under real conditions? | S1 Ch.13, X6, X12 | May justify deviations from "clean" structure, with evidence |
| Analysis limits | How much do our checks actually prove? | S7 | Governs every claim the skill makes |
| Decisions (ADR) | Why is it like this, and is that still valid? | S4 | Turns trade-offs into constraints; prevents re-litigation |

The concerns form one method: **understand context → protect behaviour (tests) → find what
impedes change or creates risk → classify and prioritise it → change in small verified steps →
record decisions**. No concern is applied in isolation; a "clean" refactor that breaks an
authorisation check or ignores an ADR is a failure.

## 3. Quality attributes

Findings map to the attributes they affect. The quality evaluation (`quality-model.md`) rates
these dimensions separately — never as a single score.

| Dimension | Sub-attributes | Rule domains |
|---|---|---|
| Code quality | readability, naming, function/class design, complexity, duplication, error handling | CODE, DES |
| Architecture | boundaries, dependency direction, modularity, domain isolation, consistency, fit-for-context | ARCH, DES |
| Security | input handling, authN/authZ, sessions, secrets, data protection, configuration, dependencies | SEC |
| Testing | testability, coverage meaning, reliability of tests, behavioural focus | TEST |
| Maintainability | debt load, changeability, documentation, dependency health, ownership, operability | TD, DLV, CODE-CMNT |
| Reliability and performance | failure behaviour, resources, concurrency, consistency, latency/throughput, observability | REL, PERF, DATA, API |

## 4. Taxonomy

### 4.1 Rule levels (normative strength)

| Level | Meaning | May be overridden by |
|---|---|---|
| `mandatory` | Violations cause security, data-integrity or correctness failures, or legal exposure. | Nothing silently. A documented, compensating control can downgrade a *finding's* severity, never the rule. |
| `constraint` | An architectural or project constraint in force: an accepted ADR, a published API contract, a documented team convention, a framework's required structure. | A superseding decision (new ADR) — raise it, don't bypass it. |
| `strong` | Strong engineering recommendation; deviation needs a stated reason. | Context gates (section 5), measured performance needs, ecosystem idioms. |
| `contextual` | Applies only when its stated conditions hold. | Absence of the conditions. |
| `optional` | Improvement worth suggesting; never blocks. | Anything. |

### 4.2 Finding types (classify *before* judging severity)

| Type | Definition | Default handling |
|---|---|---|
| `defect` | Behaviour is wrong now (or wrong for reachable inputs). | Fix; severity by impact. Not TD (S3 Ch.1). |
| `vulnerability` | An exploitable weakness. Sub-label: confirmed / potential. | Fix; severity by risk (likelihood × impact). |
| `reliability-risk` | Likely failure under real conditions (timeouts, races, leaks, consistency). | Fix or mitigate. |
| `performance` | Measured, or structurally evident (N+1, unbounded load), cost. | Fix if on a hot path; mark unmeasured claims. |
| `tech-debt` | Expedient structure that raises the cost of future change (S3 Ch.1). | Prioritise by interest vs. principal (`workflows/tech-debt.md`). |
| `architecture-risk` | Structural issue threatening boundaries, dependency direction or evolvability. | TD with elevated weight (S3 Principle 6). |
| `test-gap` | Missing or weak verification for risky behaviour. | Add tests proportionate to risk. |
| `trade-off` | A deliberate, still-valid compromise with known costs. | Record (ADR/TD register); don't "fix". |
| `legacy-constraint` | Imposed by an external system, contract or migration state. | Work within it; note the cost. |
| `imperfection` | Real but harmless in context (stable code, low traffic, no planned change). | Usually omit; at most a `nit`. |
| `question` | Cannot be judged without information you lack. | Ask; don't guess a severity. |

### 4.3 Severity (per finding)

| Severity | Meaning | Merge/release impact |
|---|---|---|
| `blocker` | Exploitable vulnerability, data loss/corruption, broken behaviour, secret exposure, build/test breakage, violation of a mandatory rule. | Must be resolved before merge/release. |
| `major` | Significant risk or cost: likely defect, notable maintainability or reliability hazard, constraint violation. | Resolve before merge unless explicitly accepted with a reason. |
| `minor` | Local quality issue with modest cost. | Fix now if cheap, else when next touching the code. |
| `nit` | Style or preference. | Never blocks; batch or omit. |

Severity = impact × likelihood × exposure, judged in context. A rule's `severity` field is the
default range, not a verdict.

### 4.4 Confidence (per finding)

| Label | Evidence required |
|---|---|
| `confirmed` | Observed by running code/tests, reproduced, or the full code path traced with no unresolved unknowns (inputs, config, callers). |
| `likely` | Strong static evidence; remaining unknowns are minor and stated (e.g. "assuming no global middleware sanitises this"). |
| `possible` | Pattern-level signal (tool hit, name, idiom) without tracing; requires verification. |

Security wording follows the same scale: *confirmed vulnerability* = confirmed; *potential
vulnerability* = likely/possible; *hardening recommendation* = a finding with no current
exploit path; *unverified concern* = a `question`.

## 5. Context gates

Establish these before applying rules. Skipping them is the main source of false positives.

1. **Ecosystem** — language, framework, versions, idioms (`languages/`). A rule that conflicts with
   an established idiom yields to the idiom unless safety is at stake.
2. **Local conventions** — formatter/linter configs, existing patterns, naming, error model,
   directory structure, `CONTRIBUTING`, ADRs. Consistency with the codebase beats generic taste.
3. **Lifecycle** — prototype, MVP, growth, mature, legacy-in-maintenance, scheduled-for-retirement.
   Expected lifetime and change rate set how much structure pays off (S3 Principle 9).
4. **Domain complexity** — CRUD/data-centric vs. rule-rich; regulatory or financial stakes.
5. **Team and operations** — team size and count, deployment and on-call maturity.
6. **Non-functional requirements** — stated performance, availability, security, compliance needs.
7. **Scope of the request** — what the user asked for; out-of-scope findings are reported briefly
   or not at all, never acted on silently.

When a gate cannot be established, state the assumption you are making in the output.

## 6. Conflict resolution

### 6.1 Precedence (highest first)

1. **Safety and correctness** — mandatory security rules, data integrity, legal/compliance,
   correctness of behaviour.
2. **Explicit constraints** — accepted ADRs, published API contracts, documented team rules.
   If a constraint conflicts with (1), raise it explicitly; do not silently violate either.
3. **Behaviour preservation and change risk** — don't trade a known-working system for a
   cleaner untested one; the safety net comes first.
4. **Evidenced non-functional needs** — measured performance, availability, cost constraints.
5. **Structural principles** — dependency direction, boundaries, cohesion (S2), weighted by
   context gates 3–5.
6. **Ecosystem idioms and local consistency** (P-53).
7. **Generic code-style heuristics** (S1 Ch.2–5).
8. **Personal or reviewer preference** — never a finding above `nit`.

### 6.2 Procedure when rules conflict

1. Name both rules and the force behind each (cite IDs).
2. Check context gates: does one rule's `applies`/`except` condition already settle it?
3. Apply the precedence order.
4. Prefer the option that is **reversible** and **smaller**, when the higher-precedence concern
   is satisfied either way (S2 Ch.15, Keeping Options Open).
5. State the trade-off in the output and, for architectural choices, propose an ADR.

## 7. Resolved tensions between sources

| ID | Tension | Resolution adopted |
|---|---|---|
| T-01 | S1 Ch.3 wants very small functions; locality and Go/C idioms favour longer linear code. | Criterion is single purpose and single level of abstraction; length is a signal only (CODE-FUNC-01). |
| T-02 | S1 Ch.7 "use unchecked exceptions / exceptions over return codes" vs. Go `error` values, Rust `Result`, checked exceptions in some Java codebases. | Follow the ecosystem's error model; keep the invariant "no silent failures, context added, happy path separated" (CODE-ERR-01). |
| T-03 | S1 J1 recommends wildcard imports; modern Java style guides and formatters forbid them. | Follow the project's formatter/style guide. J1 is treated as superseded convention. |
| T-04 | S1 G5 calls duplication a root problem; S2 Ch.16 warns that unifying accidental duplication couples unrelated actors. | Unify only true duplication (same reason, same rate of change) (CODE-DUP-01/02). |
| T-05 | S1 Ch.4 treats most comments as failures; S5 and regulated domains need documented reasoning and security rationale. | Comments for *why*, constraints, warnings and public APIs are required where non-obvious (CODE-CMNT-01). |
| T-06 | S2 Ch.30–32 treat DB/web/framework as details; framework-centric stacks (Laravel, Rails, Django, Spring Data) embed them by design; S1 Ch.6 describes Active Record as a legitimate data structure. | Isolate details in proportion to domain-rule richness and volatility. For CRUD-heavy apps, framework-native structure is correct (ARCH-FIT-01, ARCH-DET-01). |
| T-07 | Popular microservice adoption vs. S2 Ch.27 (services are a deployment mode; the Kitty Problem). | Modular monolith by default; split on concrete deployability/scaling/team needs plus operational maturity (ARCH-STYLE-01). |
| T-08 | S1 G23 prefers polymorphism over switch; functional and data-oriented styles use pattern matching; class explosions harm readability. | One switch per type decision is fine (S1's own "ONE SWITCH" rule); repeated switches on the same type tag call for polymorphism or a lookup (CODE-CPLX-03). |
| T-09 | S1 Ch.9 "one assert per test" vs. "single concept per test" (also S1 Ch.9). | Single concept per test (TEST-UNIT-02). |
| T-10 | S1 Boy Scout Rule (always clean up) vs. S3 Principle 5 (TD ≠ bad quality) and review-cost concerns. | Clean what you touch, behaviour-preserving, separately committed, proportionate to the change (AGT-MIN-02, TD-DEC-03). |
| T-11 | S1 N6 avoid encodings / interface prefixes vs. .NET `IService`, C# `_field` conventions. | Ecosystem convention wins (P-53). |
| T-12 | S1 "don't return/pass null" vs. languages with nullable/optional types where `null`/`None` is idiomatic and type-checked. | Express absence through the type system (Optional, nullable types, `T | None`); flag only unchecked nulls (CODE-ERR-04). |
| T-13 | S5's cyclomatic-complexity bands (0–10 / 11–15 / 16–20) vs. their misuse as hard gates. | Use as a risk-based pointer to where to look (S5's stated purpose), not as a pass/fail rule (CODE-CPLX-01). |
| T-14 | S2's full boundaries everywhere vs. S1 Ch.12 rule 4 and S2 Ch.24–25's own YAGNI caveat. | Boundary only where a named force exists; partial boundaries as the hedge (ARCH-FIT-02). |
| T-15 | Mission-level wish to treat vulnerabilities and performance problems "as technical debt" vs. S3 Ch.1 excluding defects and external quality from TD. | Classify by finding type (4.2); TD is one type among several, prioritised with its own model. |
| T-16 | Clean Code's DI frameworks/AOP chapter (S1 Ch.11, Java proxies, AspectJ) vs. present-day ecosystems. | Keep the principle (separate construction from use, P-17); ignore the dated mechanism. |

## 8. Exceptions and waivers

- A rule's `except` field lists known legitimate exceptions. Applying one requires saying so.
- A project can waive a `strong`/`contextual` rule by convention or ADR; the skill then treats the
  waiver as a `constraint` and stops reporting the rule (except to note a waiver is outdated).
- `mandatory` rules cannot be waived by convenience. If the user insists, comply only where it is
  their decision to make (e.g. accepted risk in their own system), record the accepted risk, and
  never weaken a control in a way that harms third parties.
- Inline suppression comments (`# noqa`, `@SuppressWarnings`, `// nolint`) are fine when they carry
  a reason; unexplained suppressions are a `minor` finding (S1 G4, Overridden Safeties).
