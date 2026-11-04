# Workflow: testing and safe refactoring

Refactoring changes structure without changing behaviour. This workflow makes "without changing
behaviour" something you can show, not just claim. Plan template:
`../../assets/templates/refactoring-plan.md`. Rules: TEST-*, AGT-MIN-*, TD-DEC-*.

## Contents
1. Is it worth doing? · 2. The safe refactoring procedure · 3. Building a safety net ·
4. Smell → refactoring map · 5. Large-scale moves · 6. Testing methodology · 7. Verification and
reporting

## 1. Is it worth doing?
Refactor when it pays: the code is on the path of current or upcoming work, or its interest is
high (`tech-debt.md` §4). State the benefit, the cost and the risk (TD-DEC-04). "It's ugly" is
not a reason when nobody changes it (TD-CLS-03). The user may of course simply ask for it — then
do it safely and keep the scope they asked for.

## 2. The safe refactoring procedure
1. **Understand current behaviour** — read the code and its callers; run it if possible. Write
   down what it does, including odd behaviour (odd behaviour may be relied on).
2. **Identify business rules** embedded in the code (calculations, eligibility, ordering,
   rounding, defaults) — these must survive exactly.
3. **Identify invariants** — what must always hold (totals, uniqueness, state transitions,
   side-effect order, error behaviour, performance envelope).
4. **Find affected components** — callers (grep, IDE references, reflection/DI/string lookups,
   templates, serialisers), public APIs, persisted formats, events.
5. **Evaluate regression risk** — blast radius, test coverage of the paths, concurrency, data
   formats, external consumers.
6. **Check existing tests** — run them; read what they assert. Coverage of the touched paths, not
   overall percentage, is what matters (TEST-COV-01).
7. **Plan** — target structure, sequence of small steps each leaving the code working, and a stop
   point that already delivers value. Use the refactoring-plan template for anything beyond a
   single function.
8. **Change incrementally** — one refactoring at a time; prefer automated IDE/language-server
   refactorings (rename, extract, move) over hand edits; never mix in behaviour changes
   (AGT-MIN-02).
9. **Run tests after each step** — and commit (or checkpoint) when green. If a step breaks
   something you can't explain quickly, revert the step rather than debugging forward.
10. **Evaluate the result** — is it actually simpler (fewer concepts, clearer names, smaller
    units, fewer dependencies)? Did you introduce speculative abstraction (DES-SIMP-02)? Re-run the
    full relevant suite and the static checks.

## 3. Building a safety net
When tests are missing or weak (TEST-REG-02):
- **Characterization tests**: call the code with representative and edge inputs, record what it
  returns/does *now*, and assert exactly that — even if it looks wrong. If it is wrong, note it as
  a separate defect; don't fix it during the refactoring.
- **Golden master / approval tests**: for complex outputs (reports, rendered documents, large
  JSON), snapshot current output for a set of inputs and compare after each step. Normalise
  non-deterministic parts (timestamps, IDs, ordering).
- **Test at seams**: if the unit is hard to instantiate, find a seam — a constructor parameter,
  an overridable method, an injected function, a boundary interface — and break a dependency with
  the smallest change (X4). Prefer refactorings that IDEs perform safely for this first cut.
- **No net possible?** Reduce step size, rely on automated refactorings only, increase review, and
  say plainly in the report that behaviour preservation rests on reasoning, not tests.
- **Test the net itself.** Seed a handful of plausible mistakes into a scratch copy (flip a `>` to
  `>=`, regroup a floating-point sum, drop a fee, swap a rate) and confirm the tests fail; use a
  mutation-testing tool if the project has one. Extend inputs to extremes (very large and tiny
  values, empty and malformed inputs): floating-point, overflow and rounding differences hide there.

## 4. Smell → refactoring map
Smell codes from S1 Ch.17; refactoring names from X3.

| Smell | Typical refactoring |
|---|---|
| Long function doing several things (G30, G34) | Extract Function; Split Phase; Replace Temp with Query |
| Duplicated knowledge (G5) — true duplication only | Extract Function/Class; Pull Up Method; replace with shared value object |
| Repeated type switches (G23) | Replace Conditional with Polymorphism; dispatch map |
| Too many / flag arguments (F1, F3, G15) | Introduce Parameter Object; split function per flag value |
| Feature envy (G14), misplaced responsibility (G17) | Move Function/Field |
| Large class serving several actors (S2 Ch.7) | Extract Class per actor; Facade |
| Primitive obsession (money, IDs, ranges) | Replace Primitive with Object (value object) |
| Magic numbers (G25) | Replace Magic Literal with named constant |
| Train wrecks (G36) | Hide Delegate; tell-don't-ask method |
| Obscure conditionals (G28, G29) | Decompose Conditional; Extract predicate; Invert negative |
| Dead code (G9, F4) | Remove Dead Code |
| Hidden temporal coupling (G31) | Pass results along; builder or state type |
| Inappropriate static/global (G18) | Introduce parameter/dependency injection |
| Mixed policy and I/O (S2 Ch.20, Ch.23) | Extract pure core + humble shell |

## 5. Large-scale moves
- **Parallel change (expand → migrate → contract)**: add the new shape beside the old, move callers
  gradually, remove the old. Works for APIs, schemas and modules.
- **Branch by abstraction**: put an interface in front of the part to replace, switch
  implementations behind it, remove the old one.
- **Strangler fig**: route slices of functionality to new code until the old can be retired.
- Each step must be shippable and leave the system working (TD-DEC-03). Record the plan in an ADR
  when it spans weeks (ARCH-DEC-01).

## 6. Testing methodology
**Where to test what** (TEST-STRAT-01/02):
- Business rules and calculations → unit tests, fast, many cases (table-driven/parameterised).
- Adapters (repositories, HTTP clients, message handlers) → integration tests against real
  engines in containers or the vendor's sandbox (TEST-DATA-01).
- Service boundaries and public APIs → contract/schema tests (TEST-CONTRACT-01).
- Critical user journeys → a few end-to-end smoke tests.
- Security controls → negative tests: wrong user, wrong tenant, anonymous, invalid input
  (TEST-SEC-01).
- Concurrency → stress tests with more threads than cores; race detectors (REL-CONC-01).

**What a good test looks like**: one behaviour, named for it; arrange–act–assert; assertions on
outcomes; deterministic (injected clock, seeded randomness); independent; fast (TEST-UNIT-01/02).

**Test smells to fix while there**: assertion-free tests, tests mirroring the implementation,
over-mocking, shared mutable fixtures, sleeps, order dependence, silent skips (TEST-BEH-01,
TEST-ISO-01, TEST-SKIP-01).

**Interpreting results**: compile/type-check, test, static analysis and correctness are different
claims (AGT-EVID-02). Green tests show the tested behaviours still hold; they don't prove the
refactoring preserved untested behaviour (S7 §1.2). Say which paths were covered.

## 7. Verification and reporting
Report:
- The structural change (before → after, in a few lines).
- Evidence of behaviour preservation: which tests (existing and new characterization tests) ran,
  before and after, with results; static checks run.
- What is not covered by tests and why you believe it is unchanged (reasoning, automated
  refactoring used).
- Behaviour changes: none — or, if any were intentional and requested, listed separately.
- Follow-ups: defects discovered (not fixed during the refactoring), next refactoring steps.
