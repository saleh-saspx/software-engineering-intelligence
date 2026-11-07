# Design patterns: catalog and how to use it

The 22 object-oriented design patterns of the Refactoring Guru catalog (S10), each described in
its own file with the same fields so patterns can be compared. This is judgment material, not a
textbook: every file says when the pattern earns its cost, when it does not, and how to recognise
it in real code. Start from the problem, not the catalog (P-69): most changes need no pattern.

## Contents
1. How to use these files · 2. Catalog · 3. Supplementary patterns · 4. Sources and differences

## 1. How to use these files
- **Choosing a design** — `selection.md` (forces → candidates, the six questions, cost model,
  composition vs. inheritance), then `comparisons.md` for look-alikes, then the pattern file.
  Procedure: `../workflows/design-patterns.md` §2.
- **Assessing existing code** — `../workflows/design-patterns.md` §1; misuse signals in
  `anti-patterns.md`; leads from `python3 scripts/pattern_scan.py PATH`.
- **Refactoring toward or away from a pattern** — `../workflows/design-patterns.md` §3 with
  `../workflows/refactoring.md`.
- **Reviewing a pattern implementation** — `../workflows/design-patterns.md` §4.
- **Framework features that look like patterns** — `frameworks.md` (Spring, Laravel, Go, Python,
  TypeScript/React). Name a pattern only after mapping its participants (DES-PAT-04).

Fields in every pattern file: intent, example, problem, context, motivation, applicability,
structure, participants and responsibilities, collaborations, implementation considerations,
consequences, benefits, trade-offs, costs, known misuses, when not to use, related patterns,
common combinations, refactoring opportunities, testing, security, language and framework
considerations, and source provenance.

## 2. Catalog

Grouped by intent as in S10: creational patterns deal with how objects are created, structural
patterns with how objects and classes are assembled into larger structures, behavioural patterns
with algorithms and the assignment of responsibilities between objects.

| Category | Pattern | Intent in one line | Typical force | File |
|---|---|---|---|---|
| Creational | Factory Method | Let subclasses decide which product a creation hook returns | A framework or base class must create objects whose type varies by subclass | `factory-method.md` |
| Creational | Abstract Factory | Create families of related objects without naming their classes | Products must match each other across a variant (provider, platform, region) | `abstract-factory.md` |
| Creational | Builder | Construct a complex object step by step | Many optional parts, invalid partial states, several representations | `builder.md` |
| Creational | Prototype | Copy configured objects without depending on their classes | Copy an object whose concrete class the copier does not know | `prototype.md` |
| Creational | Singleton | One instance with a global access point | A truly process-wide resource — usually better owned by the composition root | `singleton.md` |
| Structural | Adapter | Make an existing interface usable where another is expected | Integrate legacy or third-party code without bending your own model | `adapter.md` |
| Structural | Bridge | Split abstraction and implementation into hierarchies that vary independently | Two independent dimensions of variation would multiply subclasses | `bridge.md` |
| Structural | Composite | Treat individual objects and groups through one interface | The model is a tree and clients should not care about leaf vs. group | `composite.md` |
| Structural | Decorator | Add responsibilities by wrapping an object with the same interface | Optional, combinable behaviours chosen at run time | `decorator.md` |
| Structural | Facade | Give a complex subsystem a small, simple entry point | Clients need a few use cases of a large library or subsystem | `facade.md` |
| Structural | Flyweight | Share immutable common state among many small objects | Measured memory pressure from huge numbers of similar objects | `flyweight.md` |
| Structural | Proxy | Stand in for an object to control access to it | Lazy loading, caching, access control, remoting without changing callers | `proxy.md` |
| Behavioural | Chain of Responsibility | Pass a request along handlers until one handles it | Ordered, configurable checks or handlers; sender must not know who handles | `chain-of-responsibility.md` |
| Behavioural | Command | Turn a request into an object | Queue, schedule, log, retry or undo operations | `command.md` |
| Behavioural | Iterator | Traverse a collection without exposing its structure | Complex or remote structures, several traversal orders | `iterator.md` |
| Behavioural | Mediator | Route interactions between components through one object | Many-to-many coupling between peers that should not know each other | `mediator.md` |
| Behavioural | Memento | Capture and restore an object's state without exposing it | Undo, rollback or snapshots of encapsulated state | `memento.md` |
| Behavioural | Observer | Notify subscribers of events without knowing them | Unknown or changing set of reactions to a change | `observer.md` |
| Behavioural | State | Delegate state-dependent behaviour to state objects | Many states with behaviour that differs per state and changes often | `state.md` |
| Behavioural | Strategy | Make interchangeable algorithms selectable at run time | One behaviour with several real variants chosen per call, tenant or config | `strategy.md` |
| Behavioural | Template Method | Fix an algorithm's skeleton; let subclasses fill steps | Several classes share an algorithm and differ in a few steps | `template-method.md` |
| Behavioural | Visitor | Add operations over a fixed class hierarchy without editing it | Stable element types, frequently added operations | `visitor.md` |

## 3. Supplementary patterns

Not in the S10 catalog, and not discussed by S9. Listed because other parts of this skill and
the framework profiles use them; each is labelled with its source.

| Pattern | Source | Use and judgment |
|---|---|---|
| Interpreter | X2 (the 23rd GoF pattern) | A class per grammar rule evaluating a small language. Only for a tiny, stable grammar; otherwise use a parser generator, a table of rules or an existing expression library (T-29). |
| Dependency Injection / composition root | X14; S1 Ch.11; P-17 | Not a GoF pattern: objects receive collaborators instead of finding them; one place builds the graph (DES-DI-01). Containers (Spring, Laravel) automate it. |
| Service Locator | X14 | Objects fetch collaborators from a global registry. Hides dependencies; acceptable only at framework edges (DES-DI-02). Laravel facades and `app()` calls are this, not GoF Facades. |
| Null Object | X14 | A do-nothing implementation instead of `null` checks. Fine when "do nothing" is the correct behaviour; dangerous when it hides a missing configuration. |
| Specification | X1 | Business predicates as combinable objects (`and`, `or`, `not`) — a Composite of predicates; useful for rule-heavy filtering and validation. |
| Repository | X1 | A collection-like interface over persistence for an aggregate. Adds value when it owns query policy; ceremony when it wraps an ORM one-to-one (DES-PAT-01). |
| Pipes and filters, publish–subscribe | S8 Ch.7; `../architecture-patterns.md` | Architectural cousins of Chain of Responsibility and Observer, across process boundaries with delivery semantics (T-30). |

## 4. Sources and differences
- **S10** (refactoring.guru/design-patterns, by Alexander Shvets) is the reference for the catalog
  structure and the pattern content: intent, applicability, pros and cons, relations. Pages were
  checked on 2026-11-07; each pattern file cites its page.
- **S9** is the supplied PDF: a **Bookey summary** of Shvets' book *Dive Into Design Patterns*,
  not the book itself. It has 36 chapters (OOP basics, design principles, SOLID, the 22 patterns),
  eight of them cut off by the publisher's paywall, and adds the summary publisher's own
  "critical thinking" commentary. It is used where it agrees with S10; where it differs, the
  difference is recorded in the pattern file and in T-28.
- **X2** (Gamma et al.) and **X16** (Head First Design Patterns) are the classic references;
  X15 (Effective Java) adds Java-specific advice (static factories, builders, singletons).
- Everything about misuse, testing, security and frameworks that no source states is the skill's
  own engineering judgment, labelled `extension` (X14) in each file's provenance line.
- Texts, examples and illustrations from S9 and S10 are paraphrased, never reproduced; the
  examples in these files are the skill's own (licensing: `../sources.md` §6).
