# Iterator · behavioural

**Intent** — Traverse the elements of a collection without exposing its underlying representation
(S10).

**Example (real problem)** — A reconciliation job walks every payment from a provider API that
returns pages with an opaque cursor, retries rate-limited calls and stops at a date. Wrapping this
in an iterator — a generator in Python, an `Iterator` in Java, an async iterator in TypeScript —
lets the job loop over payments while paging, retries and cursors stay in one place.

- **Problem** — Traversal logic (paging, tree walks, cursors) is duplicated in business code and ties
  it to the collection's structure.
- **Context** — Complex, lazy, remote or very large collections; several traversal orders.
- **Motivation** — Keep traversal apart from both the collection and the business logic.
- **Applicability** — Hide a complex structure from clients, for convenience or protection; remove
  duplicated traversal code from business logic; traverse different or unknown structures
  uniformly (S10).
- **Structure** — Iterator interface; concrete iterators that keep their own position; a collection
  interface returning iterators; concrete collections; client.
- **Participants and responsibilities** — Iterator: traversal state and algorithm. Collection:
  creates suitable iterators.
- **Collaborations** — The client asks the collection for an iterator and pulls elements from it.
- **Implementation considerations** — Each iterator keeps its own traversal state, which allows
  parallel traversals, and is bound to one collection (S10); define what happens when the
  collection changes during iteration (fail fast or snapshot); release resources such as database
  cursors when a consumer stops early.
- **Consequences** — Uniform traversal for a small overhead.
- **Benefits** — Simpler clients and collections (SRP); new collections and iterators without
  changes (OCP); several traversals of one collection at once; iteration that can pause and resume
  (S10).
- **Trade-offs** — Abstraction versus the speed of direct access.
- **Costs** — Overkill for applications that only use simple collections; can be slower than
  direct access to specialised collections (S10).
- **Known misuses** — Hand-written iterator classes where the language's iteration protocol or
  generators suffice; "iterators" that load everything into memory first (PERF-IO-02); leaking
  database cursors when consumers break out early.
- **When not to use** — Simple in-memory lists; the standard library already provides the traversal.
- **Related patterns** — Iterators traverse Composite trees; Factory Method lets collection
  subclasses return matching iterators; Memento can capture an iteration's position; Visitor with
  Iterator operates across elements of different classes (S10).
- **Common combinations** — Composite; Visitor.
- **Refactoring opportunities** — Toward: copy-pasted pagination loops. Away: custom iterator classes
  that a generator could replace.
- **Testing considerations** — Empty, single-page and multi-page cases; early termination releases
  resources; modification during iteration; retry paths.
- **Security considerations** — Iterators over remote data must bound total work (limits, timeouts)
  and keep authorisation per page; hiding the structure can protect its invariants from clients, a
  motive S10 names.
- **Language and framework considerations** — Python generators and `__iter__`; Java `Iterator`,
  streams and spliterators; JavaScript iterators, generators and `for await`; Go range-over-func
  iterators (`iter.Seq`) or channels, which leak goroutines when consumers stop early; Laravel
  `LazyCollection` and `cursor()`; Spring Data `Stream` results, which must be closed. See
  `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/iterator · direct. S9 Ch.29
  agrees on problem, solution, structure, applicability, pros, cons and relations. Example,
  misuses, testing, security and language notes: extension (X14).
