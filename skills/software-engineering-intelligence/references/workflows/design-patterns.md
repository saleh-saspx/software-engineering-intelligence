# Workflow: design patterns — assessment, selection, refactoring, implementation review

Four procedures for working with design patterns in real code. Knowledge they draw on:
`../patterns/index.md` (catalog), `../patterns/selection.md` (forces, baselines, cost model),
`../patterns/comparisons.md`, `../patterns/anti-patterns.md` and `../patterns/frameworks.md`.
Rules: DES-PAT-01 – DES-PAT-06, DES-SIMP-02, DES-SIMP-03, TEST-CONTRACT-02, SEC-DESIGN-02.
Principles: P-69, P-70. Scale depth to the request (SKILL.md §1): a question about one class gets a
paragraph, not this whole procedure.

## Contents
1. Pattern assessment · 2. Pattern selection · 3. Pattern-based refactoring · 4. Pattern
implementation review · 5. Evidence and reporting rules

## 1. Pattern assessment
Find the patterns a codebase uses, judge whether each is applied correctly and justified, and
find misuse.

**Input** — The repository or module; its history if available; its language and framework; the
roadmap or known changes when the user can give them.

**Steps**
1. Pass the context gates (`../knowledge-model.md` §5): ecosystem, conventions, ADRs, lifecycle.
2. Collect leads: `python3 scripts/pattern_scan.py PATH` (declared patterns by name and structure;
   single-implementation interfaces and abstract classes, single-product factories, classic
   singletons, deep inheritance, small visitors, names that don't match the structure) and
   `python3 scripts/hotspots.py PATH` for where change happens. Every hit is a lead to confirm.
3. For each candidate instance, map the participants to code and state the force it resolves
   (DES-PAT-04). Framework features are described by their mechanism (`../patterns/frameworks.md`).
4. Judge each instance: **justified** (a real force, distinct participants, cost proportionate),
   **misapplied** (right idea, wrong implementation — see §4), **unjustified** (no force, or a
   simpler baseline would do — `../patterns/anti-patterns.md`), or **misnamed** (pattern-shaped but
   a different pattern or none).
5. Look for the opposite gap too: hand-rolled, inconsistent solutions to a problem a pattern or the
   framework already solves (several ad-hoc state machines, duplicated retry wrappers).
6. Prioritise by change cost and risk: hotspots and security-relevant wrappers first.

**Decision criteria** — Force stated and evidenced? Participants with distinct responsibilities?
Cost (types, hops, wiring) proportionate to the expected change? Idiomatic for the language?
Correct wiring and contracts?

**Evidence required** — For each finding: file and line, participant map, implementation count or
call depth, the change history or requirement that does or doesn't support the force.

**Output** — A table per instance, then findings in the review format:

```
| Instance | Pattern (participants) | Force | Verdict | Evidence | Action |
|---|---|---|---|---|---|
| billing/tax/*.py | Strategy (TaxPolicy ← 3 regimes; Checkout as context) | regimes added twice a year | justified | 3 impls, git history | keep; add contract suite |
| notify/factory.ts:12 | "Factory" — always returns EmailSender | none | unjustified | 1 product, 4 call sites | inline the constructor |
```

## 2. Pattern selection
Choose a design for a concrete problem, or confirm that no pattern is needed.

**Input** — The problem as code, requirement or proposal; constraints (language, framework, team,
performance budget); expected changes.

**Steps**
1. Extract the problem and write the force in one sentence (`../patterns/selection.md` §1). If the
   force cannot be stated, the answer is "no pattern yet".
2. Write the no-pattern baseline concretely (`../patterns/selection.md` §4).
3. List candidates from the forces table (`../patterns/selection.md` §3) and add each candidate's
   closest look-alike (`../patterns/comparisons.md`).
4. For each option estimate the cost (`../patterns/selection.md` §5) and say what becomes easier and
   what becomes harder.
5. Check composition versus inheritance (`../patterns/selection.md` §6) and the language idiom
   (DES-PAT-06).
6. Choose the cheapest option that absorbs the force; if it is a pattern, sketch participants and
   wiring (one composition point, DES-PAT-05) and the tests (TEST-CONTRACT-02).
7. Record the decision and its revisit trigger — briefly in the reply, or in
   `../../assets/templates/pattern-decision.md` (or an ADR) when it shapes a module.

**Decision criteria** — The six questions of `../patterns/selection.md` §2 all answered; the
recommendation is the cheapest option meeting the force; a pattern is recommended only with
evidence of the variation it absorbs.

**Evidence required** — The requirement or history behind the force; counts behind the cost
estimate; where relevant, a spike or prototype result.

**Output**

```
Problem and force: … (evidence: …)
Options: baseline — …; candidate — …; look-alike — … (cost and trade-off for each)
Recommendation: … — because …; becomes easier: …; becomes harder: …
Sketch: participants, wiring point, tests
Revisit when: …
```

## 3. Pattern-based refactoring
Refactor toward a pattern — or away from one — without changing behaviour.

**Input** — The code; its tests; the force motivating the change (or the anti-pattern being
removed).

**Steps**
1. Confirm the refactoring is justified: a selection (§2) toward a pattern, or an assessment (§1)
   showing an unjustified one. Note the smell (`../patterns/selection.md` §7).
2. Build the safety net: characterization tests that pin current behaviour, including odd cases
   and error paths (TEST-REG-02, `refactoring.md`). Run them and see them pass on the old code.
3. Plan small, behaviour-preserving steps (`../../assets/templates/refactoring-plan.md`). Toward a
   pattern, typically: extract the varying code into functions → introduce the interface or type →
   move each variant behind it → switch the call sites → delete the old branch. Away from one:
   inline single implementations → collapse pass-through layers → remove the unused abstraction.
4. Run the tests after every step; commit in steps; keep refactoring separate from behaviour change.
5. Check the result against the pattern's implementation considerations (§4) and the cost estimate.
6. Compare old and new behaviour on a wide input grid where cheap (a throwaway script calling both
   versions) — the most persuasive evidence of preservation.

**Decision criteria** — Behaviour identical, quirks included unless the user approves a change;
fewer places touched per expected change, or less indirection, than before; no new pattern beyond
what the force needs.

**Evidence required** — Test commands and results before and after; the comparison run, if done;
diff size.

**Output** — What changed and why, the steps taken, the tests and comparison run (commands and
results), behaviours preserved deliberately (quirks), and what was not verified.

## 4. Pattern implementation review
Review a change that introduces or modifies a pattern.

**Input** — The diff, the surrounding code and the stated intent.

**Steps and checks**
1. **Right pattern** — Map the participants; confirm the force and that a simpler option was
   considered (DES-PAT-03, DES-PAT-04).
2. **Structure and responsibilities** — Each participant has its own responsibility; the context
   doesn't reach into concrete variants; no participant only forwards (DES-SIMP-03).
3. **Contracts** — All implementations honour the same contract, including errors and edge cases;
   a shared contract suite exists (TEST-CONTRACT-02, DES-LSP-01).
4. **Wiring** — Composed in one place; order tested where it matters; unknown keys and unhandled
   requests fail loudly; listeners have defined failure and transaction semantics (DES-PAT-05).
5. **Dependencies** — Abstractions owned by the client side; concrete classes created at the
   composition root; no new globals or locators (DES-DIP-01, DES-DI-02).
6. **Complexity and testability** — New types and hops proportionate; each participant testable
   alone; the language idiom used (DES-PAT-06).
7. **Pattern-specific pitfalls** — From the pattern file's implementation, testing and security
   fields (for example: Proxy self-invocation, Observer after-commit side effects, Memento
   immutability, Composite depth limits, Visitor completeness).
8. **Security** — Controls implemented as wrappers cannot be bypassed and fail closed
   (SEC-DESIGN-02); selection keys from input are allow-listed.

**Output** — The review format of SKILL.md §8 with findings tied to the checks above; say plainly
when the pattern is a good fit.

## 5. Evidence and reporting rules
- Name a pattern only with its participant map; say "pattern-shaped but not X" when that is the
  finding (DES-PAT-04).
- Script output is a lead, not a verdict: a single implementation can be a deliberate test seam or
  a published contract (DES-SIMP-03 exceptions).
- Unjustified patterns are usually technical debt; misapplied ones can be defects or
  vulnerabilities — classify them (`../knowledge-model.md` §4).
- Never claim a refactoring preserved behaviour without running the tests (AGT-EVID-01).
