# Visitor · behavioural

**Intent** — Separate an operation from the object structure it runs over, so that new operations
can be added without changing the classes of the elements (S10).

**Example (real problem)** — A pricing-rules engine parses expressions such as "if segment is VIP
then 10 % off" into a tree of node classes: literals, field references, comparisons, conditionals.
The team needs evaluation, a human-readable explanation, static validation and translation to SQL
for reporting — and keeps adding operations while node types rarely change. Each operation is a
visitor and nodes implement `accept(visitor)`. If node types changed every week, a visitor would be
the wrong choice.

- **Problem** — Adding operations to a stable class hierarchy means editing every class and mixing
  unrelated concerns into it.
- **Context** — A stable hierarchy of element types (syntax trees, document models, composite
  trees) with frequently added operations.
- **Motivation** — Keep each operation in one class; let double dispatch pick the right method for
  each element type.
- **Applicability** — Run an operation over all elements of a complex structure whose elements have
  different classes; move auxiliary behaviour out of core classes; implement behaviour that makes
  sense only for some classes of a hierarchy (S10).
- **Structure** — A visitor interface with one visit method per element type; concrete visitors; an
  element interface with `accept(visitor)`; concrete elements calling the matching visit method; a
  client.
- **Participants and responsibilities** — Element: knows its own type and calls back. Visitor: the
  operation, per element type.
- **Collaborations** — The client passes a visitor to the elements, often while traversing a
  Composite; each element calls the visit method for its own type.
- **Implementation considerations** — Every concrete element implements `accept` itself, even when a
  base class has one (S10); visitors may need access to private data — expose it or nest the visitor
  (S10); decide between returning values and accumulating state in the visitor.
- **Consequences** — Operations are easy to add; element types are hard to add.
- **Benefits** — New behaviour without changing element classes (OCP); related behaviour grouped
  together (SRP); a visitor can accumulate state while traversing (S10).
- **Trade-offs** — The operation axis is open and the type axis closed (the expression problem).
- **Costs** — Every visitor changes when an element class is added or removed; visitors may lack
  access to private members (S10).
- **Known misuses** — A visitor over two or three types where a method on each type or a `switch` is
  clearer; visitors over hierarchies that change often; visitors used to avoid ordinary
  polymorphism.
- **When not to use** — Element types change more often than operations; the language has exhaustive
  pattern matching over sealed or union types (Java 21, Kotlin, Scala, Rust, TypeScript
  discriminated unions), which is usually clearer (DES-PAT-06).
- **Related patterns** — A more powerful Command whose objects can run operations over objects of
  different classes; runs operations across a whole Composite tree; combined with Iterator for
  traversal (S10).
- **Common combinations** — Composite; Iterator; Interpreter (supplementary, `index.md` §3).
- **Refactoring opportunities** — Toward: the same type switch over the same hierarchy repeated in
  many operations (CODE-CPLX-03). Away: a visitor with one implementation — move the methods onto
  the elements or write one function with pattern matching.
- **Testing considerations** — For each visitor, one test per element type including nested
  composites; a guard that fails when a new element type has no visit method (a compile error in
  typed languages).
- **Security considerations** — Visitors that translate trees into another language (SQL, HTML,
  shell) must escape or parameterise at every node (SEC-INJ-01, SEC-OUT-01); bound the recursion
  depth of trees built from input.
- **Language and framework considerations** — Compilers and linters are the canonical users (Babel
  and ESLint visitors, Python's `ast.NodeVisitor`, Java annotation processors); Go uses type
  switches; TypeScript uses discriminated unions with an exhaustive `switch` and a `never` check.
  See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/visitor · direct. S9 Ch.36
  agrees on intent, problem, solution and double dispatch but is cut off at the structure; its Q&A
  gives the cost of updating every visitor and the private-access limit, consistent with S10.
  Example, misuses, testing, security and framework notes: extension (X14).
