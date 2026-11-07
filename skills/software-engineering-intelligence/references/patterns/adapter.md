# Adapter · structural

**Intent** — Convert the interface of an existing class into the interface its clients expect, so
that classes with incompatible interfaces can work together (S10).

**Example (real problem)** — The order service defines a `PaymentGateway` port with
`authorize(order, amount)` and `refund(payment, amount)` in domain terms. The provider's SDK works
in integer minor units, idempotency headers and provider-specific error codes. A
`ProviderPaymentGateway` implements the port, converts money, identifiers and errors, and is the
only class that imports the SDK — a provider change touches one adapter, and tests use an
in-memory gateway.

- **Problem** — Useful code (legacy, third-party, another team's) has an interface or data format
  that does not match what your code expects, and you cannot or should not change either side.
- **Context** — Integration boundaries; reuse of existing classes.
- **Motivation** — Keep your own model clean and dependent on abstractions you own (P-07,
  DES-DIP-01); isolate translation in one place.
- **Applicability** — Reuse an existing class whose interface does not fit; give several existing
  subclasses common behaviour they lack without duplicating it in new subclasses (S10).
- **Structure** — Client; client interface (target); service (adaptee); adapter implementing the
  target and wrapping the service (object adapter). A class adapter inherits from both sides and
  needs multiple inheritance (S10).
- **Participants and responsibilities** — Target: what the client needs, ideally owned by the
  client. Adapter: translates calls, data and errors. Adaptee: unchanged.
- **Collaborations** — The client calls the target; the adapter translates and delegates; results
  and errors are translated back.
- **Implementation considerations** — Translate errors, units and identifiers, not only method
  names; keep adapters thin and free of business rules; two-way adapters are possible; keep one
  adapter per external API version.
- **Consequences** — Translation is isolated; each integration adds a class.
- **Benefits** — Interface and data conversion are separated from business logic (SRP); new adapters
  need no client changes (OCP) (S10).
- **Trade-offs** — Indirection at the boundary in exchange for a stable internal model.
- **Costs** — New interfaces and classes; sometimes changing the service class directly is simpler
  (S10).
- **Known misuses** — "Adapters" that only rename methods of a class you own (change the class);
  adapters accumulating business logic; adapters between two of your own interfaces stacked layer
  upon layer (DES-SIMP-03).
- **When not to use** — You own both sides and can align them; the external interface already fits;
  a small function at a single call site is enough.
- **Related patterns** — Bridge is designed up front, Adapter is applied to existing code; Decorator
  keeps or extends the interface and composes recursively, Adapter changes it; Proxy keeps the same
  interface; Facade defines a new interface for a whole subsystem, while an adapter usually wraps one
  object; State and Strategy share its composition-based structure but solve other problems (S10).
- **Common combinations** — Adapters inside a Facade; an adapter family per provider created by an
  Abstract Factory; an anti-corruption layer between domains (X1).
- **Refactoring opportunities** — Toward: SDK types and error codes leaking into domain code (wrap
  the third-party API, P-07). Away: adapters that translate nothing.
- **Testing considerations** — Run one contract suite for the target interface against the adapter
  (with the provider's sandbox or recorded responses) and against the in-memory fake
  (TEST-CONTRACT-02); test error and unit translation explicitly.
- **Security considerations** — Adapters sit on trust boundaries: validate and normalise inbound
  data, map provider errors without leaking secrets, and keep credentials in the adapter's own
  configuration.
- **Language and framework considerations** — Spring Integration channel adapters and Spring MVC's
  `HandlerAdapter` are adapters in the pattern's sense; Go: a small struct implementing your
  interface; Python: a class or a function; React: a hook wrapping a third-party widget's API.
  See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/adapter · direct. S9 Ch.20
  agrees on intent, structure, applicability, pros and cons; its relations line folds Proxy and
  Facade into one comparison — S10's separate comparisons followed (T-28). Example, misuses,
  testing, security and framework notes: extension (X14).
