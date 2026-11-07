# Composite · structural

**Intent** — Compose objects into tree structures and let clients treat individual objects and
groups of objects through one interface (S10).

**Example (real problem)** — A promotions engine lets marketing define eligibility as nested
groups: segment is VIP AND (cart total at least 100 OR cart contains coffee). Each condition and
each AND/OR group implements `isSatisfiedBy(cart)`; groups delegate to their children and combine
the answers. New condition types plug in without changing the evaluator, and the same tree renders
as readable text in the admin screen.

- **Problem** — Recursive part–whole structures force clients to tell leaves from containers
  everywhere.
- **Context** — The model is genuinely a tree: bills of materials, organisation charts, UI
  components, rule groups, folders.
- **Motivation** — One interface for both; recursion lives inside containers.
- **Applicability** — Tree-like object structures; clients that should treat simple and complex
  elements alike (S10).
- **Structure** — Component interface; leaves; composites (containers) holding children and
  delegating; client.
- **Participants and responsibilities** — Component: common operations. Leaf: does the actual work.
  Composite: delegates to children and aggregates their results.
- **Collaborations** — The client calls a component; composites iterate over children and combine
  results.
- **Implementation considerations** — Decide where child-management methods live: on the component
  (uniform, but leaves get empty methods — an interface-segregation problem, S10) or on composites
  only (type-safe); guard against cycles; cache aggregated values only with invalidation.
- **Consequences** — Recursive algorithms become simple; interfaces risk becoming over-general.
- **Benefits** — Polymorphism and recursion make complex trees easy to work with; new element types
  do not break code that processes the tree (S10).
- **Trade-offs** — Uniformity versus type safety.
- **Costs** — A common interface for very different classes may become over-general and hard to
  understand (S10).
- **Known misuses** — Forcing non-tree data into a tree; leaves throwing "unsupported operation" for
  child methods (DES-LSP-01); unbounded recursion on depth controlled by users.
- **When not to use** — The hierarchy is fixed and shallow; clients must treat leaves and groups
  differently anyway.
- **Related patterns** — Builder constructs composite trees; a leaf can pass requests up its parents
  (Chain of Responsibility); Iterator traverses the tree; Visitor runs an operation across it;
  Flyweight shares leaves; Decorator has a similar structure but wraps one child to add
  responsibilities; Prototype clones complex trees (S10).
- **Common combinations** — Visitor, Iterator, Builder; Specification (X1) is a composite of
  predicates (`index.md` §3).
- **Refactoring opportunities** — Toward: recursive `if node is a group` code repeated in clients.
  Away: a "tree" that is always one level deep.
- **Testing considerations** — Test leaves, empty groups, nested groups and maximum depth; property:
  a group's result equals the combination of its children's results.
- **Security considerations** — Bound the depth and size of trees built from input (deeply nested
  payloads exhaust stack or CPU); evaluate permissions on each node when a tree mixes access
  levels.
- **Language and framework considerations** — React component trees and the DOM are composites;
  Python and TypeScript can use union types with recursive functions instead; Go: an interface plus
  a slice of children. See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/composite · direct. S9 Ch.22
  agrees on problem, solution, structure, applicability, pros, cons and relations; its commentary
  about over-generalisation matches S10's con. Example, misuses, testing and security notes:
  extension (X14); Specification: X1.
