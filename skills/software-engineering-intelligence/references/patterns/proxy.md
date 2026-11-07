# Proxy · structural

**Intent** — Provide a substitute with the same interface as a service object, to control access to
it and run logic before or after requests reach it (S10).

**Example (real problem)** — Product pages call an exchange-rate API that is slow and rate-limited.
A `CachingRatesClient` implements the same `RatesClient` interface, serves rates from a cache for
five minutes and calls the real client otherwise; callers do not change. In the same codebase, ORM
lazy-loading proxies stand in for related entities until first access — a reminder that a proxy can
hide I/O behind an innocent-looking getter.

- **Problem** — Access to an object needs control (lazy creation, caching, permissions, remote
  location, logging, lifetime), but neither the object nor its clients should change.
- **Context** — Expensive, remote, sensitive or third-party services.
- **Motivation** — Interpose control without clients noticing, because the proxy is interchangeable
  with the service.
- **Applicability** — Virtual (lazy initialisation), protection (access control), remote, logging,
  caching and smart-reference proxies (S10).
- **Structure** — Service interface; service; proxy holding or creating the service and delegating;
  client working through the interface.
- **Participants and responsibilities** — Proxy: same interface; controls access and often the
  service's lifecycle. Service: the real work.
- **Collaborations** — The client calls the proxy, which decides whether and when to call the
  service.
- **Implementation considerations** — Proxy and service share an interface; if none exists, extract
  one, or subclass the service when extraction would touch too many clients (S10); a creation
  method or the container decides which object to hand out; make surprising I/O visible in names
  (CODE-FUNC-03).
- **Consequences** — Transparent control, but costs (latency, I/O) hide behind the same interface.
- **Benefits** — Control without the client knowing; lifecycle management; works even when the
  service is not ready; new proxies without changing service or clients (S10).
- **Trade-offs** — Transparency versus visibility of cost and behaviour.
- **Costs** — More classes; delayed responses (S10).
- **Known misuses** — Lazy-loading proxies causing N+1 queries (PERF-IO-01) or lazy-initialisation
  errors outside transactions; caching proxies without invalidation or with keys that ignore user
  and tenant; "protection proxies" that can be bypassed by reaching the real service.
- **When not to use** — The control belongs inside a service you own; a wrapper function at one call
  site suffices; callers must see the latency or I/O explicitly.
- **Related patterns** — Adapter offers a different interface, Proxy the same; Facade also buffers a
  complex object and may initialise it lazily, but has a different interface; Decorator has a
  similar structure, but its composition is controlled by the client, while a proxy usually manages
  its service's lifecycle itself (S10).
- **Common combinations** — Decorator (caching and logging wrappers blur the line — name by intent,
  DES-PAT-04); a flyweight factory; remote stubs behind adapters.
- **Refactoring opportunities** — Toward: caching or permission checks duplicated around every call
  to a service. Away: proxies that only delegate.
- **Testing considerations** — Test the control logic against a fake service (cache hit and miss,
  denied access, lazy creation exactly once); contract-test proxy and service as interchangeable
  (TEST-CONTRACT-02); for ORM proxies, count queries.
- **Security considerations** — A protection proxy is only as strong as the impossibility of reaching
  the service another way: in Spring, a call from inside the same bean skips the AOP proxy, and a
  raw bean injected elsewhere skips its checks (SEC-DESIGN-02); caching proxies must not cache
  authorisation decisions or per-user data under shared keys.
- **Language and framework considerations** — Spring AOP (`@Transactional`, `@Cacheable`,
  `@PreAuthorize`, `@Async`) and Hibernate's lazy associations are proxies; JavaScript `Proxy`
  objects; Python delegation via `__getattr__`; gRPC and REST client stubs are remote proxies. See
  `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/proxy · direct. S9 Ch.26
  agrees on intent, problem, solution, the six kinds of proxy, pros, cons and relations. Example,
  misuses, testing, security and framework notes: extension (X14); Spring self-invocation: X11.
