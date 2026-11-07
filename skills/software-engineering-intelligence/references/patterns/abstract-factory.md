# Abstract Factory · creational

**Intent** — Provide an interface for creating families of related products, so that clients get a
consistent set without naming concrete classes.

**Example (real problem)** — A SaaS product runs on one cloud in production, in a customer's own
tenant on another cloud for an enterprise contract, and on local emulators in development. Blob
storage, queues and the secret store must come from the same platform — a queue from one cloud
with a secret store from another fails at run time. A `PlatformFactory` with `createBlobStore()`,
`createQueue()` and `createSecretStore()` has one implementation per platform, chosen once at
start-up from configuration.

- **Problem** — Code that creates several collaborating products scatters platform checks and can
  combine products that do not belong together.
- **Context** — Two or more product types vary together across variants (provider, platform,
  region, product edition).
- **Motivation** — Make "a consistent family" a type-level guarantee and select the variant in one
  place.
- **Applicability** — Code must work with several product families whose classes may be unknown in
  advance or grow; a class's factory methods distract from its main job and can move into a
  dedicated factory (S10).
- **Structure** — One interface per product type; concrete products per variant; an abstract
  factory with one creation method per product type; a concrete factory per variant; clients using
  only the interfaces.
- **Participants and responsibilities** — Abstract factory: the family contract. Concrete factory:
  guarantees compatible products. Client: receives a factory and never chooses a variant itself.
- **Collaborations** — The application picks the concrete factory once (configuration or
  environment) and passes it on; clients create products through it.
- **Implementation considerations** — Choose the factory at the composition root; adding a product
  type changes every factory — that is the cost axis; concrete factories are usually stateless and
  shared (S10 says they can be singletons — prefer a container-managed instance, T-24).
- **Consequences** — New variants are cheap; new product types are expensive.
- **Benefits** — Products from one factory are compatible; clients are independent of concrete
  products; creation lives in one place; new variants need no client changes (S10).
- **Trade-offs** — Flexibility along the variant axis is bought with rigidity along the product-type
  axis.
- **Costs** — Many new interfaces and classes (products × variants), possibly more complex than
  needed (S10).
- **Known misuses** — A single family "in case we add another"; a factory per class mirroring
  constructors; factories reading configuration on every call; hand-written factories where the DI
  container's environment-specific wiring already selects implementations.
- **When not to use** — Products need not match; only one variant exists or is planned; container
  profiles or conditional bindings already express the families.
- **Related patterns** — Often evolves from Factory Method; Builder constructs step by step while
  Abstract Factory returns products immediately; Prototype can compose its creation methods; it can
  replace a Facade when only object creation needs hiding; it can supply the implementations a
  Bridge needs (S10).
- **Common combinations** — Bridge (the factory picks matching implementations); Strategy (a family
  of strategies per tenant or region).
- **Refactoring opportunities** — Toward: the same `if provider == …` repeated at several creation
  sites. Away: a single-variant factory — inline the constructors or use container wiring.
- **Testing considerations** — Run one contract suite against every family (TEST-CONTRACT-02); an
  in-memory family keeps integration tests fast; one end-to-end test per real family.
- **Security considerations** — Select the variant from configuration, never from request data;
  test or local families must be impossible to select in production (fail at start-up).
- **Language and framework considerations** — Spring `@Profile` and `@Conditional` configuration
  classes often replace hand-written factories; Laravel binds per environment in service
  providers; Go: an interface, or a struct of constructor functions; Python: a module or class per
  family.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/abstract-factory · direct.
  S9 Ch.16 agrees on intent, solution, structure, applicability, pros and cons; S9's Q&A says the
  pattern can replace a Facade to "simplify client access to subsystems", broader than S10 (only
  to hide how subsystem objects are created) — S10 followed (T-28). Example, misuses, testing,
  security and framework notes: extension (X14).
