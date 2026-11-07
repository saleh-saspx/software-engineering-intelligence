# Mediator · behavioural

**Intent** — Reduce chaotic dependencies between objects by making them communicate only through a
mediator object (S10).

**Example (real problem)** — An order-editing screen has line items, a coupon field, shipping
options and a totals panel. Changing a line can invalidate the coupon and change shipping options
and totals; changing shipping changes totals and may re-enable the coupon. Instead of each part
calling the others, each reports its changes to an `OrderEditorMediator`, which decides what to
recalculate and whom to update — and the parts become reusable on the quick-order screen.

- **Problem** — Many-to-many interactions between peers make each one hard to change or reuse.
- **Context** — Forms and dialogs, workflows coordinating peers, chat-like systems.
- **Motivation** — Put interaction logic in one place; components know only the mediator.
- **Applicability** — Classes hard to change because they are tightly coupled to many others;
  components that cannot be reused because they depend on their neighbours; many subclasses created
  only to reuse basic behaviour in different contexts (S10).
- **Structure** — Components holding a reference to a mediator interface; the mediator interface
  (often a single notification method); concrete mediators.
- **Participants and responsibilities** — Component: its own business logic; notifies the mediator.
  Mediator: the coordination rules.
- **Collaborations** — Components report events to the mediator, which calls other components.
- **Implementation considerations** — Components must not know each other, only the mediator (S10);
  keep the mediator to coordination rather than business rules; split it per use case when it
  grows.
- **Consequences** — Decoupled components; coordination concentrated in one object.
- **Benefits** — Interaction logic in one place (SRP); new mediators without changing components
  (OCP); less coupling; reusable components (S10).
- **Trade-offs** — Simple components versus a central object that knows everyone.
- **Costs** — The mediator can turn into a god object (S10).
- **Known misuses** — "Mediator" libraries used as an in-process bus for every call, putting an
  indirection between a controller and the one handler it always calls; mediators holding domain
  rules; event buses that hide control flow everywhere.
- **When not to use** — Two or three components with simple, stable interactions; a direct call or a
  callback is clearer.
- **Related patterns** — Chain of Responsibility, Command and Observer are other sender–receiver
  connections; a common implementation uses Observer with the mediator as publisher, though the
  intents differ; Facade organises access to a subsystem without adding behaviour and leaves its
  objects free to talk to each other, while mediator components cannot (S10).
- **Common combinations** — Observer; Command; State (the mediator's behaviour per screen state).
- **Refactoring opportunities** — Toward: components calling each other's methods in both directions.
  Away: a mediator relaying between exactly two components.
- **Testing considerations** — Test the mediator with fake components (given this event, expect
  these calls); test components alone against a fake mediator.
- **Security considerations** — A coordinator acting for several components must apply each
  component's authorisation rules, not just the caller's.
- **Language and framework considerations** — Front ends: a container component or a state store
  coordinating children (lifting state up, reducers); request-dispatch libraries such as MediatR are
  command buses rather than necessarily this pattern (DES-PAT-04); Go: a coordinator struct using
  method calls or channels. See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/mediator · direct. S9 Ch.30
  agrees on problem and solution but is cut off after the structure; its Q&A adds the god-object
  con and the relations to Observer and Facade, consistent with S10. Example, misuses, testing,
  security and framework notes: extension (X14).
