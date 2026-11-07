# Bridge · structural

**Intent** — Split a class that varies along two dimensions into an abstraction hierarchy and an
implementation hierarchy connected by composition, so each can change independently (S10).

**Example (real problem)** — A notification service sends several message kinds (security alert,
invoice, weekly digest) over several channels (email, SMS, push). A subclass per combination
multiplies kinds by channels. With a bridge, `Message` subclasses build content and decide
priority and hold a `Channel` implementation that only delivers primitives (recipient, subject,
body, urgency). A new channel is one class; a new message kind is one class.

- **Problem** — Extending a hierarchy along two independent dimensions multiplies subclasses.
- **Context** — Platform-independent features over platform-specific primitives; high-level logic
  over interchangeable drivers.
- **Motivation** — Replace inheritance across two axes with composition between two hierarchies.
- **Applicability** — Divide a monolithic class with several variants of one functionality (for
  example several database servers); extend a class in independent dimensions; switch
  implementations at run time (S10).
- **Structure** — Abstraction (high-level control) holding a reference to an implementation
  interface (primitive operations); refined abstractions; concrete implementations; a client that
  links them.
- **Participants and responsibilities** — Abstraction: domain-level behaviour. Implementation:
  primitives — its interface need not mirror the abstraction's (S10).
- **Collaborations** — The abstraction delegates primitive work to its implementation.
- **Implementation considerations** — Identify both dimensions first; keep the implementation
  interface small and primitive; the client or a factory links abstraction and implementation.
- **Consequences** — Both hierarchies evolve independently; more structure up front.
- **Benefits** — Platform-independent classes; clients shielded from platform details; new
  abstractions and implementations independently (OCP); high-level and platform code separated
  (SRP) (S10).
- **Trade-offs** — Up-front structure in exchange for avoiding combinatorial subclassing.
- **Costs** — Applied to a highly cohesive class, it makes the code more complicated (S10, S9 Q&A
  Ch.21).
- **Known misuses** — A bridge with one implementation; abstraction and implementation interfaces
  that are identical (a pass-through); calling every interface–implementation pair a bridge
  (DES-PAT-04).
- **When not to use** — Only one dimension varies (plain polymorphism or Strategy); the second
  dimension is speculative (DES-SIMP-02).
- **Related patterns** — Designed up front, unlike Adapter; shares the composition-based structure of
  State and Strategy; Abstract Factory can create matching implementations; Builder's director and
  builders map onto abstraction and implementations (S10).
- **Common combinations** — Abstract Factory; Strategy on the implementation side per tenant.
- **Refactoring opportunities** — Toward: class names that combine two dimensions
  (`PdfInvoiceReport`, `HtmlInvoiceReport`, `PdfStatementReport`). Away: a bridge whose
  implementation side never got a second member.
- **Testing considerations** — Test abstractions against a fake implementation; contract-test the
  implementations (TEST-CONTRACT-02).
- **Security considerations** — Implementations that cross trust boundaries (delivery channels,
  storage drivers) carry their own credentials and validation; the abstraction must not assume all
  implementations sanitise data equally.
- **Language and framework considerations** — JDBC's driver API, logging APIs over pluggable
  backends, and Laravel's filesystem and mail drivers behind managers follow the bridge idea — an
  API over interchangeable drivers; Go: a struct holding an interface field. See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/bridge · direct. S9 Ch.21
  agrees on problem, solution and terms but is cut off after the structure; its Q&A gives the
  cohesive-class con, as S10 does. Example, misuses, testing, security and framework notes:
  extension (X14).
