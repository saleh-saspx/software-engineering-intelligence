# Prototype · creational

**Intent** — Create new objects by copying an existing, configured object through a common copy
interface, without depending on its concrete class.

**Example (real problem)** — A contract-management system keeps template contracts with nested
clauses, default values and attachments. A customer contract starts from a template chosen at run
time; the code that creates it receives the template through an interface and cannot know its
concrete class. Each clause type implements `copy()`, so the nested structure is reproduced
correctly and identifiers and ownership are reset.

- **Problem** — Copying an object "from outside" requires knowing its concrete class and reaching its
  private fields, which couples the copier to every class it copies (S10).
- **Context** — Objects received through interfaces (plug-ins, third-party code), or many presets
  that differ only in their initial state.
- **Motivation** — Let each object copy itself, because only it knows its structure; replace
  subclasses that differ only in configuration with preconfigured instances.
- **Applicability** — Copy objects whose concrete classes the copier does not know; reduce a family
  of subclasses that differ only in initialisation (S10).
- **Structure** — Prototype interface (`copy`/`clone`); concrete prototypes; an optional registry of
  named prototypes; the client.
- **Participants and responsibilities** — Prototype: copies itself, including private state, deep or
  shallow as its contract says. Registry: holds presets. Client: asks for copies and adjusts them.
- **Collaborations** — The client clones a prototype (perhaps from a registry) and customises the
  copy.
- **Implementation considerations** — Decide deep or shallow copying field by field; handle cycles
  and shared immutable parts; every subclass overrides the copy method so the copy has the right
  type (S10); copies must not share mutable collections; identity fields (ids, timestamps,
  ownership) are usually reset.
- **Consequences** — Object creation without class coupling; copying logic lives with each class.
- **Benefits** — Copies without depending on concrete classes; less repeated initialisation; easier
  creation of complex objects; an alternative to inheritance for presets (S10).
- **Trade-offs** — Copy semantics become part of every class's contract.
- **Costs** — Correct deep copies are hard with circular references and external resources (S10,
  S9 Q&A Ch.18).
- **Known misuses** — Java `Cloneable` and `Object.clone()` producing shallow copies of mutable
  fields (X15 Item 11 advises against relying on `clone`); copying objects that hold connections,
  locks or caches; cloning immutable value objects that could simply be shared.
- **When not to use** — The objects are immutable (share them); construction is cheap and the class
  is known; a factory or builder states the intent better.
- **Related patterns** — Factory Method designs may evolve toward Prototype, which avoids
  inheritance but needs more involved initialisation; prototypes can compose Abstract Factory's
  creation methods; Command histories store command copies; Composite and Decorator structures are
  cloned instead of rebuilt; it is a simpler substitute for Memento when state has no external
  links (S10).
- **Common combinations** — A prototype registry behind an Abstract Factory; Memento (snapshot by
  copy); Composite.
- **Refactoring opportunities** — Toward: subclasses that only set different defaults. Away: copy
  methods nobody calls.
- **Testing considerations** — Test that copies are independent (mutating the copy leaves the
  original intact) and complete (every field and nested part); include a cycle if the model allows
  one.
- **Security considerations** — Copies can carry secrets, tokens, permissions or tenant ownership of
  the original into a new context; reset identity, owner and tenant fields explicitly; never use
  deserialisation of untrusted data as a deep-copy mechanism (SEC-INJ-03).
- **Language and framework considerations** — Java: copy constructors or static copy factories (X15
  Item 11). Python: `copy.deepcopy`, with `__deepcopy__` for control. JavaScript/TypeScript:
  `structuredClone` for plain data only (class instances lose their methods). Go: explicit copy
  functions, because slices and maps share storage.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/prototype · direct. S9 Ch.18
  agrees on problem, solution and structure but is cut off; its Q&A gives the circular-reference
  con, as S10 does. X15 Item 11. Example, misuses, testing, security and language notes: extension
  (X14).
