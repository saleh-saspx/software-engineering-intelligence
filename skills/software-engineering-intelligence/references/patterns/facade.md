# Facade · structural

**Intent** — Give a complex subsystem a simple interface that exposes just what most clients need
(S10).

**Example (real problem)** — Sending a contract with an e-signature vendor takes a dozen SDK calls:
upload, create an envelope, add signers and roles, place fields, set reminders, register a webhook,
send. The application needs two use cases: "send for signature" and "download the signed copy". A
`SignatureFacade` offers exactly those two methods; controllers and jobs depend on it, and the
vendor's complexity stays inside one module.

- **Problem** — Clients wire many subsystem objects in the right order and become coupled to the
  subsystem's internals.
- **Context** — Large libraries, frameworks or legacy subsystems used for a few use cases.
- **Motivation** — Least knowledge; one place to adapt when the subsystem changes.
- **Applicability** — A limited but straightforward interface to a complex subsystem; structuring a
  subsystem into layers with an entry point per layer; reducing coupling between subsystems by
  letting them talk only through facades (S10).
- **Structure** — Facade; optional additional facades for unrelated features; subsystem classes;
  clients.
- **Participants and responsibilities** — Facade: knows which subsystem objects to call, in which
  order. Subsystem: unaware of the facade.
- **Collaborations** — Clients call the facade, which orchestrates subsystem objects; clients may
  still reach the subsystem directly for advanced needs.
- **Implementation considerations** — Expose use cases, not mirrored subsystem methods; split a
  facade that grows too large into focused facades (S10); keep business rules out unless the facade
  is deliberately an application service.
- **Consequences** — Simpler clients; risk of a god object.
- **Benefits** — Isolates your code from the subsystem's complexity (S10).
- **Trade-offs** — Convenience versus completeness: advanced features need a path around the facade.
- **Costs** — The facade can become a god object coupled to most classes of the application (S10).
- **Known misuses** — Pass-through facades re-exporting every subsystem method; facades containing
  core domain logic; calling any service class a "facade" when there is no subsystem to hide;
  treating Laravel "facades" — static proxies to container services — as this pattern (T-27).
- **When not to use** — The subsystem is already simple; clients need most of its features; one
  wrapped class needs only an Adapter.
- **Related patterns** — An adapter makes an existing interface usable and usually wraps one object,
  a facade defines a new interface over a subsystem; Abstract Factory can replace a facade when only
  creation needs hiding; Flyweight makes many small objects, a facade one object for a subsystem;
  Mediator centralises communication between components, a facade adds no behaviour and leaves
  subsystem objects free to talk directly; a facade usually needs one instance; Proxy keeps its
  service's interface, a facade has a different one (S10).
- **Common combinations** — Adapters inside the subsystem; Abstract Factory; a single
  container-managed instance (T-24).
- **Refactoring opportunities** — Toward: the same multi-call sequence against a library duplicated
  across callers. Away: a facade that forwards one-to-one — let clients use the subsystem or an
  adapter.
- **Testing considerations** — Test the facade's use cases against a fake or sandboxed subsystem;
  clients test against a fake facade.
- **Security considerations** — A facade over privileged operations is the natural place for their
  authorisation and input validation; make sure clients cannot bypass it to reach those operations
  (SEC-DESIGN-02).
- **Language and framework considerations** — Service classes wrapping SDKs in Spring or Laravel
  are often facades; Laravel's `Facade` classes are not; Go: a package exporting a few functions
  over an internal package; front ends: an API-client module hiding fetch details. See
  `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/facade · direct. S9 Ch.24
  agrees on intent, problem, solution and structure but is cut off; its Q&A gives the god-object con
  and the relations to Adapter, Mediator and Singleton, as S10 does. Example, misuses, testing,
  security and framework notes: extension (X14); T-27.
