# Decorator · structural

**Intent** — Attach responsibilities to an object at run time by wrapping it in objects that share
its interface (S10).

**Example (real problem)** — Several services call partners through an `HttpClient` interface.
Some calls need retries with backoff, all need metrics, a few need response caching. Wrappers —
`RetryingClient`, `MeteredClient`, `CachingClient` — wrap the base client and are combined per
partner where the object graph is built, instead of a subclass per combination or a pile of flags
inside one client class.

- **Problem** — Combinations of optional behaviours explode into subclasses, or classes fill with
  flags.
- **Context** — Behaviours that are orthogonal, optional and combinable, chosen at configuration or
  run time.
- **Motivation** — Composition instead of inheritance (P-70), with the same interface so clients do
  not notice.
- **Applicability** — Add behaviours at run time without changing the code that uses the object;
  split layered behaviour into one wrapper per layer; inheritance is awkward or impossible (final
  classes) (S10).
- **Structure** — Component interface; concrete component; base decorator holding a wrapped
  component and delegating; concrete decorators acting before or after delegation.
- **Participants and responsibilities** — Decorator: same interface, one added concern, always
  delegates. Client (or composition root): composes the stack.
- **Collaborations** — A call travels through the stack; each decorator may act before and after
  delegating.
- **Implementation considerations** — One concern per decorator; preserve the wrapped contract
  (errors, return values, idempotency); decide and document the order (retry outside or inside the
  timeout? cache before or after metrics?); compose in one place (DES-PAT-05).
- **Consequences** — Flexible combinations; behaviour depends on order; many small objects.
- **Benefits** — Extends behaviour without subclasses; responsibilities added or removed at run time;
  behaviours combined by stacking; SRP (S10).
- **Trade-offs** — Flexibility versus traceability: behaviour is spread across wrappers and wiring.
- **Costs** — Removing one specific wrapper is hard; making behaviour independent of stacking order
  is hard; the configuration code that builds stacks can get messy (S10).
- **Known misuses** — "Decorators" that change the interface or the semantics (an Adapter, or a
  defect); wrappers that stop or swallow the call (then it is a chain handler or proxy); deep
  stacks nobody can reconstruct while debugging; core business logic spread across decorators.
- **When not to use** — One fixed combination (put it in the class); framework middleware or
  interceptors already provide the mechanism; the concern belongs to one call site.
- **Related patterns** — Adapter changes the interface; Proxy keeps it but usually manages its
  service's lifecycle itself, while decorator composition is controlled by the client; chain
  handlers may stop a request, decorators must not; Composite aggregates many children, Decorator
  wraps one; Prototype clones decorated structures; Decorator changes an object's skin, Strategy its
  guts (S10).
- **Common combinations** — Composite; decorated strategies; caching and logging wrappers that are
  hard to tell from proxies — name them by intent (DES-PAT-04).
- **Refactoring opportunities** — Toward: flag parameters toggling cross-cutting behaviour; subclasses
  for each combination. Away: a single permanent decorator — merge it into the class.
- **Testing considerations** — Test each decorator alone around a fake component; test the composed
  order (DES-PAT-05); run the component's contract suite against decorated stacks
  (TEST-CONTRACT-02).
- **Security considerations** — Authorisation or audit decorators protect only calls that pass
  through them — make the undecorated object unreachable (SEC-DESIGN-02); caching decorators must
  key by user or tenant so one user's data is never served to another.
- **Language and framework considerations** — Python `@decorators` wrap functions and are often
  Decorator- or Proxy-like, but are applied at definition time and some only register the function
  (T-27); Java I/O streams and `HttpServletRequestWrapper` are decorators; Servlet filters and
  Laravel middleware are chains, not decorators (T-27); TypeScript decorators are metaprogramming
  annotations; React higher-order components wrap components in a decorator-like way. See
  `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/decorator · direct. S9 Ch.23
  agrees on problem, solution, structure, applicability, pros, cons and relations. Example,
  misuses, testing, security and framework notes: extension (X14).
