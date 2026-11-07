# Design-pattern anti-patterns

Ways patterns are misused, with signals, costs, consequences and fixes. S10's criticism page names
the root causes — patterns used as workarounds for missing language features, applied as dogma
without adapting them to the context, and applied by newcomers where simpler code would do — and
S10's own pattern pages warn that Strategy, State, Iterator and Flyweight can be overkill. The
signals and fixes below are the skill's judgment (extension, X14). Leads for several of them come
from `python3 scripts/pattern_scan.py PATH`; confirm each by reading the code.

## Contents
1. Pattern overuse · 2. Unnecessary abstractions · 3. Unnecessary interfaces · 4. Excessive
inheritance · 5. Singleton abuse · 6. Factory proliferation · 7. Excessive indirection ·
8. Premature extensibility · 9. Pattern-driven design · How to report them

## 1. Pattern overuse
- **Signals** — Several patterns in one small feature; patterns stacked on each other (a factory of
  strategies created by a builder); class names that read like a catalog index.
- **Costs** — Every change crosses many files; reviewers must reconstruct the design before judging a
  change.
- **Consequences** — Slower changes, fragile wiring, newcomers afraid to touch the code.
- **Fix** — Keep only patterns whose force you can state (DES-PAT-01); collapse the rest step by step
  under tests (`../workflows/design-patterns.md` §3).
- **Rules** — DES-PAT-01, DES-PAT-03, DES-SIMP-01.

## 2. Unnecessary abstractions
- **Signals** — Abstract base classes with one subclass; generic types with one instantiation;
  "engines" and "frameworks" inside an application; configuration nobody sets.
- **Costs** — Reading cost on every visit; abstractions usually guess the wrong axis of change.
- **Consequences** — When the real change arrives it cuts across the abstraction and has to be
  forced through it.
- **Fix** — Inline the abstraction; keep a partial boundary only for a credible, unscheduled need
  (P-25).
- **Rules** — DES-SIMP-02, ARCH-FIT-01.

## 3. Unnecessary interfaces
- **Signals** — An interface per class (`FooService` plus `FooServiceImpl`) with one implementation,
  no test double and no dependency-direction reason; interfaces mirroring a class's every public
  method.
- **Costs** — Two files per concept; navigation jumps to the interface instead of the code.
- **Consequences** — Interfaces that never served substitution drift with their single
  implementation and add nothing.
- **Fix** — Keep interfaces at test seams, real variation points, inverted dependencies and published
  contracts (DES-SIMP-03, T-21); otherwise use the concrete class and extract an interface when a
  second implementation or seam appears.
- **Rules** — DES-SIMP-03, DES-DIP-01, DES-ISP-01.

## 4. Excessive inheritance
- **Signals** — Hierarchies three or more levels deep built to share helpers; subclasses overriding to
  disable behaviour; template methods with a dozen steps; classes extending classes never designed for
  it.
- **Costs** — The fragile base class: changes in a parent break children in other modules.
- **Consequences** — Substitution breaks (DES-LSP-01) and fear of changing base classes.
- **Fix** — Move shared behaviour into collaborators; replace inheritance-based variation with
  Strategy, Decorator or Bridge (P-70); seal classes not designed for extension (DES-EXT-01).
- **Rules** — DES-PAT-02, DES-EXT-01, DES-LSP-01.

## 5. Singleton abuse
- **Signals** — `getInstance()` or static instances reached from business code; singletons holding
  configuration, the current user, request context or caches; tests that reset global state between
  cases.
- **Costs** — Hidden dependencies; order-dependent, non-parallel tests; concurrency hazards.
- **Consequences** — Data leaking between requests or tenants; code that cannot be reused with a
  second configuration.
- **Fix** — One instance owned by the composition root or container and injected (T-24); immutable
  configuration objects; per-request state passed explicitly.
- **Rules** — DES-DI-02, DES-DI-01.

## 6. Factory proliferation
- **Signals** — A factory per class; factories that always return the same concrete type; factory
  interfaces with one implementation; factories wrapping constructors that take no varying input.
- **Costs** — A parallel hierarchy of creation code to maintain.
- **Consequences** — Creation is spread across factories instead of the composition root; DI wiring
  and factories disagree.
- **Fix** — Constructors plus dependency injection; keep factories where the product type varies,
  creation is complex, or a framework hook requires one (Factory Method, Abstract Factory).
- **Rules** — DES-PAT-01, DES-DI-01, DES-SIMP-03.

## 7. Excessive indirection
- **Signals** — Calls passing through wrappers, managers, handlers and services that only forward;
  decorator stacks or chains nobody can list from memory; events triggering events.
- **Costs** — Debugging and reading require reconstructing the runtime graph.
- **Consequences** — Defects hide in wiring and ordering (DES-PAT-05).
- **Fix** — Collapse pass-through layers; give each remaining layer a nameable responsibility; compose
  in one place and test the order.
- **Rules** — DES-SIMP-03, DES-PAT-05.

## 8. Premature extensibility
- **Signals** — Plug-in points with no plug-ins; strategy registries with one entry; Visitor or
  Abstract Factory introduced "for future types"; extension contracts nobody consumes.
- **Costs** — Paid now in complexity, with an uncertain return; published extension points freeze
  internal designs.
- **Consequences** — The predicted axis of change is usually wrong (P-56).
- **Fix** — Add the variation point when the second variant is real or scheduled; record the trigger
  in the decision (`selection.md` §8).
- **Rules** — ARCH-EXT-01, DES-OCP-01, DES-SIMP-02.

## 9. Pattern-driven design instead of problem-driven design
- **Signals** — Design discussions that start from a pattern name; a pattern chosen because a tutorial
  used it; the code shaped to fit a pattern's diagram rather than the domain; reviews that praise
  "uses patterns" without naming forces.
- **Costs** — Design effort spent on structure instead of the problem; patterns fighting the
  language or framework.
- **Consequences** — Generic, hard-to-read code whose real business rules are scattered.
- **Fix** — Start from the force and the baseline (P-69, DES-PAT-03); map participants before naming a
  pattern (DES-PAT-04); prefer the language's idiom (DES-PAT-06).
- **Rules** — DES-PAT-01, DES-PAT-03, DES-PAT-04, DES-PAT-06.

## How to report them
Classify each as technical debt (a change-cost problem) unless it causes a defect or a vulnerability
(`../knowledge-model.md` §4); give the evidence (implementation counts, call depth, change history),
the cost in the reader's terms, the simpler alternative and the safety net needed to remove it.
Report a justified pattern as justified — saying "this one earns its keep" is part of the
assessment.
