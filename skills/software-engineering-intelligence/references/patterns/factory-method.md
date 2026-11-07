# Factory Method · creational

**Intent** — Declare an overridable creation method in a base class so that subclasses decide which
concrete product is created; the code that uses the product depends only on its interface.

**Example (real problem)** — A document-import framework runs the same workflow (read, validate,
map, persist) for CSV files, spreadsheets and a partner's XML feed. The base `Importer` calls
`createReader()` inside its workflow and each importer subclass returns its own reader. A new feed
is one new subclass instead of another branch in a `switch` inside the workflow.

- **Problem** — Code that both uses objects and constructs them with `new ConcreteType(...)` is tied
  to those types; each new variant edits the user, usually as type conditionals.
- **Context** — A base class or framework owns a workflow; the type of one collaborator varies by
  subclass or extension.
- **Motivation** — Separate "which object" from "what we do with it", so the workflow stays closed to
  modification while products vary.
- **Applicability** — The exact product types are not known in advance; users of a library or
  framework must supply their own component types by overriding a hook; creation may return pooled
  or cached instances instead of new ones (S10).
- **Structure** — Product interface; concrete products; Creator whose other methods call the factory
  method (abstract or with a default); concrete creators overriding it.
- **Participants and responsibilities** — Product: the contract callers use. Creator: owns real
  behaviour and calls the hook — it is rarely "just a factory". Concrete creator: picks the product.
- **Collaborations** — The creator's own methods call the factory method; clients talk to the
  creator and never construct products themselves.
- **Implementation considerations** — The hook returns the product interface; a default
  implementation is allowed; it need not create a new instance on every call; a parameterised
  `create(kind)` drifts toward a simple factory, which is fine when the set of kinds is closed.
- **Consequences** — Creation becomes an inheritance-based extension point; new products may need
  new creator subclasses.
- **Benefits** — Creator and concrete products are decoupled; creation code lives in one place
  (SRP); new products need no client changes (OCP) (S10).
- **Trade-offs** — Variation fixed at class level through inheritance; injecting a factory function
  or a Strategy is usually simpler outside frameworks.
- **Costs** — Parallel hierarchies (a creator per product); one more hop to find what gets created.
- **Known misuses** — `XFactory.create()` that always returns the same class; a factory method added
  "for testability" where constructor injection would do; confusing it with static factory methods
  (named constructors, X15 Item 1) or a simple factory function (T-26).
- **When not to use** — One product type and no extension requirement; injecting the collaborator
  is enough; the variation is a value (configuration), not a type.
- **Related patterns** — A specialisation of Template Method and often one of its steps; designs
  often start here and evolve toward Abstract Factory, Prototype or Builder; collection subclasses
  can return matching iterators (Iterator) (S10).
- **Common combinations** — Template Method (the workflow) with Factory Method (one step); Iterator.
- **Refactoring opportunities** — Toward: constructor calls guarded by type conditionals inside a
  workflow (X3, Replace Constructor with Factory Function). Away: a creator hierarchy whose
  subclasses only override the factory method — inject the product or a function instead.
- **Testing considerations** — Test the workflow with an injected fake product or a test subclass;
  check that each concrete creator's product honours the contract (TEST-CONTRACT-02).
- **Security considerations** — When the product type is chosen from input (`create(request.type)`),
  allow-list the types; never instantiate classes named by untrusted data (SEC-INJ-03).
- **Language and framework considerations** — Spring: overridable `@Bean` methods and `FactoryBean`
  are creation hooks; Python, TypeScript and Go: pass a constructor or factory function (Go has no
  subclassing — use a function field or an interface). See `frameworks.md`.
- **Source provenance** — Intent, applicability, pros, cons, relations and caveats: S10
  https://refactoring.guru/design-patterns/factory-method · direct. S9 Ch.15 agrees on intent,
  problem and solution but is cut off after the structure; its Q&A gives the same evolution path as
  S10. Example, misuses, testing, security and language notes: extension (X14); naming: X15 Item 1,
  T-26.
