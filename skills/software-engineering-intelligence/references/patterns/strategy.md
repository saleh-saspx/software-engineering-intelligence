# Strategy · behavioural

**Intent** — Define a family of algorithms, put each into its own class or function, and make them
interchangeable for the object that uses them (S10).

**Example (real problem)** — An international checkout computes tax differently per regime: a
provider for US sales tax, EU VAT with reverse charge for business customers, zero tax for exports.
A `TaxPolicy` interface with one implementation per regime is chosen per order from the shipping
address and customer type; adding a new country means a new policy plus a contract test, not
another branch in a growing conditional.

- **Problem** — One behaviour has several variants; choosing among them with conditionals bloats the
  class and couples it to every variant.
- **Context** — Real, independently changing variants of an algorithm, chosen per call, tenant or
  configuration.
- **Motivation** — Separate the variants from the business logic that uses them; switch by
  composition.
- **Applicability** — Use different variants of an algorithm and switch between them at run time;
  many similar classes that differ only in one behaviour; isolate business logic from algorithm
  details; replace a large conditional that selects among variants of the same algorithm (S10).
- **Structure** — Context holding a strategy reference; strategy interface; concrete strategies; a
  client that chooses the strategy.
- **Participants and responsibilities** — Context: uses the strategy without knowing which one.
  Strategy: one algorithm. Client or selector: picks.
- **Collaborations** — The context delegates; the client or a registry supplies the strategy.
- **Implementation considerations** — The client must pass a strategy that suits the context's use
  (S10); a registry keyed by variant fails loudly for unknown keys (DES-PAT-05); strategies are
  stateless where possible; one contract suite covers all of them (TEST-CONTRACT-02).
- **Consequences** — Variants are isolated and swappable; callers must know how to choose.
- **Benefits** — Algorithms swapped at run time; implementation details isolated; inheritance
  replaced by composition; new strategies without changing the context (S10).
- **Trade-offs** — An interface and several classes versus the simplicity of a conditional.
- **Costs** — Needless complexity for a couple of rarely changing algorithms; clients must understand
  the differences between strategies; in modern languages functions can replace strategy classes
  (S10).
- **Known misuses** — A strategy interface with one implementation and no second in sight; strategies
  still chosen by a long `if` chain (move selection to a map or to the variants themselves);
  "strategies" that are really steps of one algorithm (Template Method or plain functions).
- **When not to use** — Two stable variants (an `if` is fine, T-08); the variation is configuration
  data; a function parameter expresses it.
- **Related patterns** — Bridge, State and Adapter share its composition-based structure but solve
  other problems; Command also parameterises an object with an action, but turns operations into
  objects; Decorator changes an object's skin, Strategy its guts; Template Method varies by
  inheritance at class level, Strategy by composition at run time; State extends Strategy with states
  that know each other (S10).
- **Common combinations** — A registry or factory for selection; decorated strategies; families of
  strategies from an Abstract Factory.
- **Refactoring opportunities** — Toward: a conditional choosing among algorithm variants that grows
  with each variant (CODE-CPLX-03; X3, Replace Conditional with Polymorphism). Away: a
  one-implementation strategy — inline it.
- **Testing considerations** — A shared contract suite for all strategies; selection logic tested
  separately, unknown variants included; property tests where strategies share invariants (tax is
  never negative).
- **Security considerations** — When the strategy is chosen from user input (payment method, export
  format), allow-list the keys; loading strategies by name from input amounts to code execution
  (SEC-INJ-03).
- **Language and framework considerations** — Function types and lambdas in Go, Python, TypeScript,
  Kotlin and Java (`Function<…>`); Spring can inject a `Map<String, PaymentGateway>` as a registry;
  Laravel managers select drivers by name; React passes behaviour through props and callbacks. See
  `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/strategy · direct. S9 Ch.34
  agrees on intent, problem, solution, structure, applicability, pros, cons (including functional
  alternatives) and relations. Example, misuses, testing, security and framework notes: extension
  (X14); T-08.
