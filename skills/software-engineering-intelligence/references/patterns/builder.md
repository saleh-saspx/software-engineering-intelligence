# Builder · creational

**Intent** — Separate the step-by-step construction of a complex object from its representation, so
the same process can produce different results and callers never see a half-built object.

**Example (real problem)** — A search API turns user filters into a query with dozens of optional
parts: full-text clauses, nested filters, facets, sort orders and pagination. A
`SearchQueryBuilder` lets each caller add only what it needs and rejects invalid combinations in
`build()` (cursor pagination cannot be combined with an offset). In the test suite, a
`CustomerBuilder` with sensible defaults lets each test state only the fields it cares about.

- **Problem** — Telescoping constructors, constructors with many optional parameters, a subclass
  per configuration, or partially initialised objects leaking to callers.
- **Context** — Objects with many optional parts or invariants that span parts; several
  representations built by similar steps.
- **Motivation** — Readable construction, validation before the object exists, immutable results.
- **Applicability** — Replace constructors with many optional parameters; produce different
  representations whose construction shares steps; build composite trees or other structures,
  possibly recursively; keep clients from seeing an unfinished product (S10).
- **Structure** — Builder interface with construction steps; concrete builders; products; an
  optional director that encodes common step sequences; the client.
- **Participants and responsibilities** — Builder: accumulates parts and enforces invariants.
  Director: knows recipes (optional). Product: the immutable result.
- **Collaborations** — The client configures a builder or asks a director to run a recipe, then
  fetches the product from the builder.
- **Implementation considerations** — When products do not share a type, the method returning the
  result belongs on each concrete builder, not on the common interface (S10); `build()` validates
  and returns an immutable object; builders are single-use or explicitly reset; a fluent interface
  is a style, not the pattern.
- **Consequences** — Construction logic is isolated and reusable, at the price of extra classes.
- **Benefits** — Stepwise, deferred or recursive construction; one construction routine for varied
  products; assembly code kept out of business logic (S10).
- **Trade-offs** — More code than a constructor; pays only with many options or real invariants.
- **Costs** — A builder per product or representation; keeping builder and product in sync (S10:
  overall complexity grows with the new classes).
- **Known misuses** — Builders for objects with two or three required fields; builders that can
  produce invalid objects because `build()` checks nothing; a mutable product with setters plus a
  builder; builders in languages where named or default arguments (Python, Kotlin) or object
  literals (TypeScript) already do the job (DES-PAT-06).
- **When not to use** — Few parameters, all required; named and default arguments exist; a record
  or data class with a validating constructor is clearer.
- **Related patterns** — Factory Method designs often evolve into Builder; unlike Abstract Factory,
  Builder runs extra steps before returning the product; it suits building Composite trees; a
  director and its builders can play Bridge's abstraction and implementations (S10).
- **Common combinations** — Composite (building trees); test data builders; Prototype (start from a
  copy, then adjust).
- **Refactoring opportunities** — Toward: telescoping constructors, long parameter lists of the same
  type. Away: a builder without validation around a handful of fields — use a constructor or
  record.
- **Testing considerations** — Test that `build()` rejects invalid combinations; test data builders
  keep tests short and intention-revealing (TEST-UNIT-03).
- **Security considerations** — Builders that assemble queries, commands or URLs must parameterise
  values rather than concatenate them (SEC-INJ-01, SEC-INJ-04), and validate in `build()`.
- **Language and framework considerations** — Java: Lombok `@Builder` generates a builder without
  validation, so add it; X15 Item 2 recommends builders for many constructor parameters. Python:
  keyword arguments and dataclasses. TypeScript: options objects. Go: functional options or config
  structs. See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/builder · direct. S9 Ch.17
  agrees on problem, solution, director, applicability, pros and cons, but its relations paragraph
  garbles the evolution path (Builder "evolving from Factory Method to Abstract Factory"); S10 and
  S9's own Ch.15 Q&A followed (T-28). X15 Item 2. Example, misuses, testing and security notes:
  extension (X14).
