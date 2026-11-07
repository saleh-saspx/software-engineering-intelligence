# Pattern selection and judgment

How to decide whether a design problem needs a pattern, which one, and at what cost. The procedure
is in `../workflows/design-patterns.md` §2; this file holds the knowledge it uses. Governing rules:
DES-PAT-01 (only for the forces it resolves), DES-PAT-03 (compare with the simplest alternative),
DES-PAT-06 (language idiom), DES-SIMP-02 and DES-SIMP-03; principles P-69 and P-70.

## Contents
1. Extract the problem · 2. The six questions · 3. Forces and candidates · 4. Baselines without a
pattern · 5. Cost of complexity and indirection · 6. Composition or inheritance · 7. Relations to
principles and smells · 8. Revisit triggers

## 1. Extract the problem before naming a pattern
Read the code and the requirement for symptoms, then name the force behind them:
- **Change history** — which files change together, how often a new variant arrived (git log,
  `scripts/hotspots.py`); a pattern pays for expected change, so evidence of change is the input.
- **Conditionals** — the same `switch`/`if` on a type or status in several places (CODE-CPLX-03).
- **Construction** — long constructors, objects half-built, the same set-up repeated in tests.
- **Boundaries** — third-party types leaking inwards, many calls in a fixed order to a library.
- **Coupling** — peers calling each other in both directions; a class touched for unrelated reasons.
- **Requirements** — "providers are added every quarter", "rules change weekly", "must undo",
  "must explain which rules applied", "memory budget per device".
Write the force as one sentence ("a new carrier arrives about twice a year and each prices
differently"). If you cannot, there is no pattern decision to make yet.

## 2. The six questions
Answer all six in the decision (`../../assets/templates/pattern-decision.md` for significant ones):
1. **Which force justifies it?** The recurring change or constraint the pattern absorbs, with its
   evidence (history, roadmap, contract, measurement).
2. **How would we solve it without the pattern?** Write the baseline concretely (section 4).
3. **When is the simpler solution enough?** Few variants, stable variants, one call site, no run-time
   switching, no external extenders — then the baseline wins (S10 states this caveat for Strategy,
   State, Iterator and Flyweight).
4. **What does it add to the architecture?** Types, files, indirection hops, wiring, test doubles,
   vocabulary (section 5).
5. **What gets easier and what gets harder?** Name the change that becomes cheap and the change that
   becomes expensive (Abstract Factory: new variants cheap, new product types expensive; Visitor:
   new operations cheap, new element types expensive).
6. **When do we revisit it?** A concrete trigger (section 8).

## 3. Forces and candidate patterns

| Force (one sentence you can say) | Candidates | Closest look-alike to rule out | Baseline that often suffices |
|---|---|---|---|
| One behaviour has several real variants chosen per call, tenant or configuration | Strategy | State, Template Method, Command | `if`/`switch` for 2–3 stable variants; a map of functions |
| Behaviour follows a lifecycle; transitions matter | State | Strategy | Enum + transition table |
| Several classes share an algorithm and differ in a few steps | Template Method | Strategy (callbacks) | One function with function parameters |
| A workflow needs a collaborator whose type varies by extension | Factory Method | Abstract Factory, DI | Inject the collaborator or a factory function |
| Several products must match across a variant | Abstract Factory | Factory Method | Container profiles/conditional bindings |
| Complex construction with optional parts and invariants | Builder | Factory Method | Named/default arguments, validating constructor |
| Copy objects whose class the copier doesn't know | Prototype | Factory Method | Copy constructor when the class is known |
| One process-wide instance | DI single instance (T-24) | Singleton | Module-level value (Python, Go, JS) |
| An existing interface doesn't fit the one you need | Adapter | Facade, Bridge | Change the class if you own it |
| A large subsystem used for a few use cases | Facade | Adapter, Mediator | Call the subsystem directly if it is small |
| Two independent dimensions of variation | Bridge | Strategy, Adapter | One hierarchy if one dimension is speculative |
| Part–whole trees treated uniformly | Composite | Decorator | Recursive function over a union type |
| Optional, combinable behaviours | Decorator; framework middleware | Proxy, Chain of Responsibility | Put the one fixed combination in the class |
| Control access: lazy, cached, remote, protected | Proxy | Decorator, Facade | Check at the single call site |
| Measured memory pressure from many similar objects | Flyweight | Singleton | Arrays of primitives; runtime interning |
| Ordered, configurable handlers; sender mustn't know receiver | Chain of Responsibility; pipeline | Decorator | A list of steps run in a loop |
| Operations must be queued, logged, retried or undone | Command (+ Memento) | Strategy | A function value or job class |
| Traverse a complex, lazy or remote collection | Iterator | Visitor | Generators and the language's iteration protocol |
| Many-to-many coupling between peers | Mediator | Observer, Facade | Direct calls for two or three stable peers |
| Undo or snapshots of encapsulated state | Memento | Prototype, Command (inverse ops) | Copy public, simple state |
| An unknown or changing set of reactions to an event | Observer (in process) | Mediator; messaging (T-30) | Direct call for one mandatory reaction |
| Many operations over a stable set of element types | Visitor | Iterator, Composite | Pattern matching on sealed/union types |

## 4. Baselines without a pattern
Every decision states one concretely. Typical baselines:
- **A conditional** — `if`/`switch` in one place is fine; repeated across modules it is a smell (T-08,
  CODE-CPLX-03).
- **A data table** — when variants differ only in values (rates, thresholds, templates), use
  configuration or a lookup table, not classes.
- **A function or lambda** — for one-method strategies, commands, callbacks and template steps in
  languages with first-class functions (S10 criticism page: patterns can be workarounds for missing
  language features).
- **Language constructs** — generators (Iterator), modules (Singleton), keyword arguments and records
  (Builder), sealed types and pattern matching (Visitor, State), context managers or `try/finally`
  (template-like set-up and tear-down). Profiles per ecosystem: `frameworks.md`.
- **The framework's mechanism** — DI containers, middleware, event systems, ORM lazy loading — used
  as the framework intends (P-53), described by their real mechanism (DES-PAT-04).

## 5. Cost of complexity and indirection
Estimate before adopting, and report the numbers with the recommendation:

| Measure | How to estimate |
|---|---|
| New types and files | Interfaces, classes and registrations the pattern adds now |
| Indirection hops | Extra calls between the caller and the code doing the work on the main path |
| Wiring locations | Places where the composition is assembled (aim: one, DES-PAT-05) |
| Places touched per expected change | Before vs. after, for the change named in the force |
| Test cost | Fakes, contract suites and order tests that become necessary |
| Vocabulary | Concepts a newcomer must learn to change the code safely |

Adopt when *(expected changes in the planning horizon) × (effort saved per change)* clearly exceeds
*(added types + hops + wiring + tests)* that every reader and every change pays. With one variant
today and none scheduled, keep the baseline and, if the axis is plausible, a partial boundary (P-25,
DES-SIMP-02). Example: three tax regimes today and two more expected this year — the strategy adds
one interface, a registry and a contract suite; each new regime then touches two new files instead of
a conditional shared by four callers. With two stable regimes, the conditional wins.

## 6. Composition or inheritance
Prefer composition for reuse and variation (P-70, DES-PAT-02). Ask:
- **Is it a true, substitutable *is-a*?** If a subclass would suppress or weaken inherited behaviour,
  inheritance is wrong (DES-LSP-01; S10 notes this risk for Template Method).
- **Must behaviour change at run time, per object?** Composition (Strategy, State, Decorator); fixed
  per class is acceptable with inheritance (Template Method, Factory Method).
- **How many independent dimensions vary?** Two or more multiply subclasses — compose (Bridge,
  Decorator) (S9 Ch.9 and S10 describe this explosion).
- **Does the framework require subclassing?** Follow it (P-53, T-23) and keep your own logic in
  collaborators.
- **Is the base class designed and documented for extension?** If not, do not extend it (DES-EXT-01).

| Inheritance-based | Composition-based alternative | Choose inheritance when |
|---|---|---|
| Template Method | Strategy or step functions (T-25) | Stable skeleton, framework base class, few variants |
| Factory Method | Injected factory or function | A framework hook that users override |
| Class Adapter | Object Adapter | Rarely: needs multiple inheritance (S10) |

## 7. Relations to principles and smells
Conceptual relations — a pattern can support a principle on the axis it was designed for; using it
never guarantees the principle holds.

| Pattern | Principle it can serve | Caveat |
|---|---|---|
| Strategy | Open–closed for new variants (DES-OCP-01) | Only along the chosen axis; selection logic can still need edits |
| Factory Method, Abstract Factory | Dependency inversion: clients depend on product abstractions (DES-DIP-01) | Something still knows the concretes — keep it at the composition root |
| Decorator | Single responsibility per wrapper; open–closed | Order becomes part of behaviour |
| Adapter | Dependency inversion and owning your boundaries (P-07): the client owns the port | Business rules must not leak into the adapter |
| State | Removes repeated conditional complexity (CODE-CPLX-03) | Transitions can scatter across classes |
| Composite | Uniform treatment of trees | Child-management methods strain interface segregation (DES-ISP-01) |
| Observer | Event-driven decoupling inside a process; open–closed for reactions | Implicit control flow; not durable messaging (T-30) |
| Facade | Least knowledge (DES-COH-03) | Can become a god object |
| Mediator | Lower coupling between peers | Can become a god object |
| Template Method | No duplicated skeleton (P-08); the Hollywood principle | Inheritance coupling; suppressed steps break substitution |
| Visitor | Open–closed for operations | Closed for new element types |
| Command, Chain of Responsibility, Iterator | Single responsibility: invoker vs. performer, traversal vs. collection | Extra layer; unhandled requests |
| Singleton | — (S10: it violates single responsibility) | Conflicts with explicit dependencies (DES-DI-02, T-24) |

| Smell | Pattern-based refactoring to consider | Check first |
|---|---|---|
| The same type or status `switch` in several places (S1 G23) | Strategy, State, polymorphism (CODE-CPLX-03) | One switch in one place is fine (T-08) |
| Long parameter lists, telescoping constructors | Builder, parameter object | Named/default arguments |
| The same algorithm copied with small differences | Template Method or Strategy | Extract a function first |
| Third-party calls and types spread through the code | Adapter, Facade (P-07) | Is the library used in more than one place? |
| Subclass explosion from combinations | Decorator, Bridge | Are both dimensions real? |
| Components calling each other in both directions | Mediator | Could two of them merge? |
| Global state reached from everywhere | Dependency injection instead of Singleton (DES-DI-02) | — |
| Abstractions with one implementation, unused hooks | Remove the pattern (DES-SIMP-02) | Is it a test seam or a published contract? |

## 8. Revisit triggers
Record one with every non-trivial decision: the variant count passes a threshold (a third tax regime
— adopt Strategy; still one provider after a year — inline it); the axis of change moves (states
instead of providers); a measurement contradicts the assumption (memory, latency); the framework
gains native support; the team that maintains it changes; a review finds the pattern's participants
without distinct responsibilities (DES-PAT-01).
