# Observer · behavioural

**Intent** — Define a subscription mechanism so that many objects are notified about events in the
object they observe (S10).

**Example (real problem)** — When an order is placed, the order module must not know that billing
issues an invoice, analytics records a conversion and marketing schedules a review request — and
next month logistics wants to react too. The order module publishes an `OrderPlaced` event in
process and subscribers register for it. Because the invoice may only be issued if the order's
transaction commits, that subscriber runs after commit, and a failure there must not roll the
order back.

- **Problem** — A subject must inform others of changes without depending on them, and the set of
  interested parties changes.
- **Context** — User interfaces, domain events inside one process, plug-in hooks.
- **Motivation** — Keep the subject closed to modification while reactions come and go; subscribe at
  run time.
- **Applicability** — A change to one object may require changing others, and that set is unknown
  in advance or changes dynamically; user-interface events; observers that watch only for a while
  or under some conditions (S10).
- **Structure** — Publisher with subscribe, unsubscribe and notify; a subscriber interface
  (`update(event)`); concrete subscribers; a client wiring subscriptions.
- **Participants and responsibilities** — Publisher: owns the event and the subscriber list.
  Subscriber: reacts.
- **Collaborations** — The publisher notifies every current subscriber and passes context in the
  event.
- **Implementation considerations** — Publishers talk to subscribers only through the interface; if
  the publisher already has a superclass, put subscription handling in a helper object (S10);
  decide ordering (none is guaranteed), synchronous or asynchronous delivery, failure isolation,
  re-entrancy and timing relative to transactions; unsubscribe with the subscriber's lifecycle.
- **Consequences** — Loose coupling; implicit control flow that is harder to follow.
- **Benefits** — New subscribers without changing the publisher (OCP); relationships established at
  run time (S10).
- **Trade-offs** — Decoupling versus traceability and ordering guarantees.
- **Costs** — Subscribers are notified in no guaranteed order (S10); debugging through indirection;
  leaks from forgotten subscriptions.
- **Known misuses** — Events used for required, ordered steps of one business transaction (hidden
  control flow); one publisher with one permanent subscriber (a direct call is clearer); subscribers
  relying on each other's side effects; synchronous listeners doing slow I/O inside the publisher's
  transaction.
- **When not to use** — The reaction is mandatory and part of the same use case; there is exactly one
  fixed reaction; integration across processes needs durability (messaging with an outbox, T-30).
- **Related patterns** — A chain passes a request until one receiver handles it, Observer notifies all
  subscribers; Command creates one-way links; Mediator removes direct links and is often implemented
  with Observer (the mediator as publisher), although the intents differ (S10).
- **Common combinations** — Mediator; events carrying commands; publish–subscribe across processes
  through an outbox (X13).
- **Refactoring opportunities** — Toward: a class that calls more and more unrelated modules after a
  state change. Away: an event with one subscriber that must always run — call it directly.
- **Testing considerations** — Test that publishers emit the right events (a recording subscriber)
  and that subscribers react correctly in isolation; test failure isolation and after-commit
  behaviour; never depend on subscriber order in tests.
- **Security considerations** — Events can carry more than each subscriber should see (personal data
  flowing to analytics): publish minimal payloads; in plug-in systems, authorise who may subscribe;
  a subscriber's failure must not leave security state half-updated.
- **Language and framework considerations** — Spring `ApplicationEventPublisher` with
  `@EventListener` runs synchronously in the caller's transaction by default, while
  `@TransactionalEventListener` runs at a transaction phase such as after commit; Laravel events and
  listeners (queued with `ShouldQueue`); Node `EventEmitter`; RxJS observables; React state
  subscriptions; Go callbacks or channels. See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/observer · direct. S9 Ch.32
  agrees on intent, solution, structure, applicability, the ordering con and the open–closed pro;
  its relations paragraph is vaguer than S10's, which is followed. Events across processes: X13,
  T-30. Example, misuses, testing, security and framework notes: extension (X14).
