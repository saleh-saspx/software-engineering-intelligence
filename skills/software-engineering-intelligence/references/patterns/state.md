# State · behavioural

**Intent** — Let an object change its behaviour when its internal state changes, as if it had
changed its class (S10).

**Example (real problem)** — A document-approval workflow has the states Draft, In review, Changes
requested, Approved and Archived. Operations (`edit`, `submit`, `approve`, `requestChanges`,
`archive`) behave differently in each, and compliance adds states every quarter. Each state becomes
an object implementing the operations for that state and choosing the next one; the `Document`
delegates to its current state. With three states and two operations, an enum and a transition
table would be enough.

- **Problem** — State-dependent behaviour written as conditionals on a status field spreads across
  methods and grows with every new state.
- **Context** — Finite-state machines with many states, frequent changes, and behaviour that differs
  per state across several operations.
- **Motivation** — Keep each state's behaviour in one place and make transitions explicit.
- **Applicability** — Behaviour depends on the current state, the number of states is large and
  state-specific code changes often; classes cluttered with large conditionals on field values;
  duplicated code across similar states and transitions (S10).
- **Structure** — Context (holds the current state and delegates); state interface; concrete states
  (behaviour plus transitions); optionally a back-reference to the context.
- **Participants and responsibilities** — Context: data and delegation. State: behaviour and
  transitions for one state.
- **Collaborations** — The context forwards calls to its current state, which may set the next state.
- **Implementation considerations** — States may need context internals: expose them deliberately
  (public methods, nested classes) (S10); stateless states can be shared; persist the state as data
  (an enum or name) and map it to state objects on load; make invalid operations explicit errors,
  not silent no-ops.
- **Consequences** — Per-state code is isolated; transitions are spread across state classes unless
  you centralise them in a table — choose deliberately.
- **Benefits** — One class per state (SRP); new states without changing others (OCP); a context
  without large conditionals (S10).
- **Trade-offs** — Many small classes versus one big conditional; distributed transitions versus one
  table.
- **Costs** — Overkill with few states or rare changes (S10, S9 Q&A Ch.33).
- **Known misuses** — State classes for a two-value toggle; state objects holding entity data;
  transitions scattered so that nobody can draw the machine; persisting state classes instead of
  state names.
- **When not to use** — Few states and stable behaviour (an enum with a `switch`, or a transition
  table); business-edited flows that a workflow engine or configuration expresses better.
- **Related patterns** — Shares the composition-based structure of Bridge, Strategy and partly
  Adapter; can be seen as an extension of Strategy in which states know each other and trigger
  transitions, while strategies stay independent (S10).
- **Common combinations** — Strategy; shared stateless states (Flyweight); Memento for snapshots.
- **Refactoring opportunities** — Toward: the same `switch (status)` in several methods (CODE-CPLX-03;
  X3, Replace Conditional with Polymorphism). Away: a state hierarchy for two states — use an enum
  and a `switch`.
- **Testing considerations** — Table-driven tests over every state × operation, invalid operations
  included; only allowed transitions happen; the state survives a persistence round trip.
- **Security considerations** — Authorisation often depends on state (only approvers approve, and
  only while in review): check role and state server-side on every transition (SEC-AUTHZ-01,
  SEC-BIZ-01); stop clients from writing the status field directly to skip states (SEC-AUTHZ-03).
- **Language and framework considerations** — Enums with behaviour (Java) and sealed types or
  discriminated unions with exhaustive `switch` (Java 21, Kotlin, TypeScript) often replace state
  classes; Python: a dict of transitions or small classes; state-machine libraries (Spring
  Statemachine, XState) when machines are large. See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/state · direct. S9 Ch.33
  agrees on intent, the finite-state-machine framing, problem and solution but is cut off at the
  structure; its quoted passages and Q&A state the overkill caveat and the difference from Strategy,
  consistent with S10. Example, misuses, testing, security and framework notes: extension (X14);
  refactoring name: X3.
