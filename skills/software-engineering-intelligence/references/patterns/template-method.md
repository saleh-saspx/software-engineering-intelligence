# Template Method · behavioural

**Intent** — Define the skeleton of an algorithm in a base class and let subclasses override
specific steps without changing its structure (S10).

**Example (real problem)** — Nightly partner imports all download a file, verify its checksum, parse
records, validate them, upsert and publish a summary. Only downloading, parsing and partner-specific
validation differ. A base `PartnerImportJob` runs the fixed sequence in a final `run()` method,
declares the varying steps as abstract methods and offers an optional `afterImport()` hook; each
partner's job overrides only its own steps.

- **Problem** — Several classes implement near-identical algorithms, so every change is repeated in
  each.
- **Context** — A stable algorithm with a few varying steps; frameworks inviting extension at defined
  points.
- **Motivation** — Pull duplication up and confine variation to named steps — the base calls the
  subclass, not the other way round.
- **Applicability** — Let clients extend only particular steps of an algorithm, not the whole thing;
  several classes with almost identical algorithms (S10).
- **Structure** — An abstract class with the template method (fixed order) and step methods
  (abstract, with defaults, or empty hooks); concrete classes implementing the steps.
- **Participants and responsibilities** — Abstract class: the skeleton. Concrete class: the step
  implementations.
- **Collaborations** — Clients call the template method, which calls the steps.
- **Implementation considerations** — Make the template method final (S10); keep the number of steps
  small; hooks are optional empty steps; document which steps are called and when (DES-EXT-01).
- **Consequences** — A shared skeleton at the price of inheritance coupling.
- **Benefits** — Clients override only parts of a large algorithm and are less affected by changes to
  the rest; duplicate code moves into the superclass (S10).
- **Trade-offs** — The simplicity of inheritance versus its coupling; a fixed skeleton.
- **Costs** — Some clients are limited by the skeleton; suppressing a default step in a subclass can
  violate the Liskov substitution principle; the more steps, the harder it is to maintain (S10).
- **Known misuses** — Deep hierarchies of templates; subclasses overriding the template method
  itself; steps passing data to each other through protected fields; base classes created only to
  share helpers (DES-PAT-02).
- **When not to use** — The variation is better injected (Strategy, callbacks) — especially where the
  language has no implementation inheritance (Go) or variants must change at run time; there is only
  one subclass.
- **Related patterns** — Factory Method is a specialisation of Template Method and can serve as one of
  its steps; Template Method works through inheritance, statically per class, while Strategy works
  through composition, per object at run time (S10).
- **Common combinations** — Factory Method for steps that create collaborators; Strategy for steps
  delegated to other objects.
- **Refactoring opportunities** — Toward: copy-pasted algorithms that differ in a few lines (extract
  the common steps upward). Away: replace inheritance with delegation by passing the varying steps
  as functions or strategy objects (T-25).
- **Testing considerations** — Test the skeleton once with a test subclass; test each concrete step;
  run shared tests against every subclass to catch substitution breaks (TEST-CONTRACT-02).
- **Security considerations** — Security-relevant steps (authorisation, audit, input validation)
  belong in the final skeleton, not in overridable steps that a subclass could skip.
- **Language and framework considerations** — Framework base classes (Django class-based views, JUnit
  lifecycle methods, Android activities) are templates — follow them (P-53); Spring's `JdbcTemplate`
  and `RestTemplate` use callbacks, not subclassing (T-25); Go has no inheritance — use a function
  that takes functions, or an interface, for the steps. See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/template-method · direct. S9
  Ch.35 agrees on problem, solution, hooks, structure, applicability, pros, cons and relations.
  T-25. Example, misuses, testing, security and framework notes: extension (X14).
