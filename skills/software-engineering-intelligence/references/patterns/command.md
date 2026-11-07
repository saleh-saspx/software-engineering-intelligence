# Command · behavioural

**Intent** — Turn a request into a stand-alone object that contains everything about it, so that
requests can be passed around, queued, logged, scheduled or undone (S10).

**Example (real problem)** — Warehouse staff adjust stock in a back-office tool: moves, count
corrections, write-offs. Each adjustment becomes an `InventoryCommand` holding the data needed to
execute it and a way to compute its inverse. Commands are stored before execution (audit trail),
executed by a worker, and the most recent ones can be reversed when a count was entered for the
wrong bin.

- **Problem** — Invokers (buttons, jobs, API handlers) are coupled to receivers and operations, and
  operations cannot be queued, logged or undone uniformly.
- **Context** — Operations that must be deferred, retried, audited, replayed or undone; user
  interfaces mapping many controls to the same operations.
- **Motivation** — Treat operations as data with behaviour.
- **Applicability** — Parameterise objects with operations; queue, schedule or execute operations
  remotely; implement reversible operations (S10).
- **Structure** — Invoker holding commands; command interface (`execute`); concrete commands
  referencing a receiver and parameters; receiver doing the work; client creating commands.
- **Participants and responsibilities** — Command: what to do and with which data. Receiver: how.
  Invoker: when.
- **Collaborations** — The client creates a command and hands it to an invoker, which calls
  `execute`; for undo, a history keeps executed commands.
- **Implementation considerations** — Undo either by stored state (memory, possibly private state —
  Memento helps) or by inverse operations (cheaper, but hard or impossible to write for some
  operations) (S10); commands crossing processes must be serialisable and idempotent; keep commands
  small and receivers rich.
- **Consequences** — Operations become first-class; more classes.
- **Benefits** — Invokers decoupled from performers (SRP); new commands without client changes (OCP);
  undo and redo; deferred execution; simple commands combined into complex ones (S10).
- **Trade-offs** — Flexibility in when and how operations run versus an extra layer.
- **Costs** — An extra layer between senders and receivers (S10); memory for histories.
- **Known misuses** — A command class per method with nothing queued, undone, logged or varied —
  ceremony; commands containing all the business logic, leaving receivers anaemic; treating CQRS
  command messages as this pattern without checking — related idea, different mechanism
  (DES-PAT-04).
- **When not to use** — Direct calls suffice and nothing needs deferring, recording or undoing; a
  function or closure passed as a callback expresses it (DES-PAT-06).
- **Related patterns** — Chain handlers can be commands; Mediator and Observer are other sender–
  receiver connections; Memento saves state before each command for undo; Strategy also
  parameterises an object with behaviour but swaps algorithms rather than representing operations;
  Prototype copies commands into a history; Visitor is a more powerful Command that works across
  different classes (S10).
- **Common combinations** — Memento for undo; Composite for macro commands; Chain of Responsibility.
- **Refactoring opportunities** — Toward: operation code duplicated across UI controls or endpoints;
  background jobs passing ad-hoc parameter maps. Away: command classes that are only ever executed
  immediately, once.
- **Testing considerations** — Test execute–undo pairs (undo after execute restores the state); test
  serialisation round trips for queued commands; test idempotency on redelivery (REL-CONS-02).
- **Security considerations** — Commands taken from queues or APIs are untrusted input: validate and
  authorise at execution time, not only when created; never deserialise arbitrary command classes
  (SEC-INJ-03); record who issued each command.
- **Language and framework considerations** — Laravel jobs, Symfony Messenger messages, Java
  `Runnable`/`Callable`, Go `func()` values or small structs, Redux actions (command-like data
  handled by reducers), editor undo stacks. See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/command · direct. S9 Ch.28
  agrees on problem, solution, structure, applicability, pros, cons and relations; its Q&A adds
  history memory management, consistent with S10's caveat. Example, misuses, testing, security and
  framework notes: extension (X14).
