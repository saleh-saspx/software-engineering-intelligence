# Memento · behavioural

**Intent** — Save and restore an object's previous state without revealing how it is implemented
(S10).

**Example (real problem)** — Sales engineers configure complex quotes (products, discounts, terms)
and want to try variants and roll back. The `Quote` produces opaque snapshots of its internal
state; a `QuoteHistory` stores them and asks the quote to restore one. Pricing internals stay
private, and the history never edits a snapshot.

- **Problem** — Undo or rollback needs an object's state, but exposing its fields breaks
  encapsulation and couples the history code to internals.
- **Context** — Undo and redo, in-memory transactions, simulations, multi-step wizards.
- **Motivation** — The owner of the state (originator) creates and restores its own snapshots;
  caretakers only keep them.
- **Applicability** — Snapshots for restoring a previous state; transactions that may need
  rollback; cases where direct access to fields, getters or setters would break encapsulation
  (S10).
- **Structure** — Originator (creates and restores snapshots); memento (an immutable snapshot with
  a narrow interface for caretakers); caretaker (decides when to save and restore; keeps history).
- **Participants and responsibilities** — Originator: owns the state and the snapshot format.
  Memento: an opaque value. Caretaker: the snapshots' lifecycle.
- **Collaborations** — The caretaker asks the originator for a memento before changes and hands it
  back to restore.
- **Implementation considerations** — Nested classes or intermediate interfaces restrict access;
  mementos are immutable and receive their data once, through the constructor; where the language
  cannot enforce this, it is a convention (S10); bound the history size.
- **Consequences** — Encapsulation preserved; memory grows with history.
- **Benefits** — Snapshots without breaking encapsulation; a simpler originator because history
  lives elsewhere (S10).
- **Trade-offs** — Encapsulation and simplicity versus memory.
- **Costs** — Memory when snapshots are frequent; caretakers must track the originator's lifecycle
  to drop obsolete snapshots; dynamic languages such as PHP, Python and JavaScript cannot guarantee
  that saved state stays untouched (S10).
- **Known misuses** — Snapshots exposing every field publicly (encapsulation lost); mutable mementos
  (S9's Q&A calls this a common mistake); snapshotting objects that hold connections or files.
- **When not to use** — The state is small and public anyway (copy it); event sourcing or database
  transactions already provide history; Prototype is enough for simple state (S10).
- **Related patterns** — With Command for undo; with Iterator to capture an iteration's position;
  Prototype as a simpler alternative when the state has no external links or they are easy to
  restore (S10).
- **Common combinations** — Command; Prototype.
- **Refactoring opportunities** — Toward: undo code reaching into private state through getters,
  setters or reflection. Away: "mementos" that are just public copies.
- **Testing considerations** — Restoring a snapshot reproduces the state; snapshots are unaffected by
  later changes; history limits are respected.
- **Security considerations** — Snapshots may contain secrets or personal data (passwords typed into
  a form, tokens): exclude them, encrypt persisted snapshots and apply retention (DATA-PRIV-01,
  SEC-DATA-01).
- **Language and framework considerations** — Python and JavaScript rely on convention (frozen
  dataclasses, `Object.freeze`); Java: records or nested static classes; front ends: immutable state
  stores make undo histories cheap through structural sharing.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/memento · direct. S9 Ch.31
  agrees on problem, solution, structure, implementation variants, applicability, pros, cons and
  relations; S10 adds the dynamic-language caveat, which S9 omits. Example, misuses, testing,
  security and language notes: extension (X14).
