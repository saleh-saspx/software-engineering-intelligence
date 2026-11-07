# Flyweight · structural

**Intent** — Fit more objects into memory by sharing the immutable state they have in common
instead of storing it in each object (S10).

**Example (real problem)** — A logistics map renders two million delivery stops. Each stop object
carried its own icon, colour, font and tooltip template — hundreds of bytes repeated across a few
dozen distinct styles. Moving those into shared, immutable `StopStyle` objects obtained from a
style factory, and keeping only coordinates and status per stop, cut memory by an order of
magnitude — measured before and after with a heap profile.

- **Problem** — Huge numbers of similar objects exhaust memory because each stores duplicated data.
- **Context** — Measured memory pressure; many objects; few distinct combinations of shared state.
- **Motivation** — Split intrinsic state (shared, immutable) from extrinsic state (contextual, passed
  in or stored elsewhere).
- **Applicability** — Only when the program must support a huge number of similar objects that strain
  memory, the objects contain duplicated state that can be extracted, and no simpler fix exists —
  the pattern is purely an optimisation (S10, S9 Ch.25).
- **Structure** — Flyweight (intrinsic state); context (extrinsic state plus a reference to a
  flyweight); flyweight factory (pool of existing flyweights); client.
- **Participants and responsibilities** — Factory: returns the existing flyweight for a key.
  Flyweight: shared data and behaviour that takes extrinsic state as parameters.
- **Collaborations** — Clients obtain flyweights from the factory and pass extrinsic state into
  their methods.
- **Implementation considerations** — Intrinsic state is set once through the constructor, with no
  setters or public fields (S10); the factory must be thread-safe; design the key carefully;
  consider weak references for eviction.
- **Consequences** — Memory saved; CPU may be spent recomputing or passing extrinsic state; harder to
  read.
- **Benefits** — Large memory savings when many similar objects exist (S10).
- **Trade-offs** — Memory versus CPU time and clarity (S10).
- **Costs** — Extra complexity; new team members may not see why state is split (S10).
- **Known misuses** — Applying it without a memory measurement; mutable "flyweights" shared across
  threads; flyweights holding per-user data.
- **When not to use** — Object counts are moderate; the runtime already deduplicates (string
  interning, small-integer caches); a columnar layout (arrays of primitives) is simpler.
- **Related patterns** — Shared leaves of a Composite tree; Facade is one object for a whole
  subsystem; Flyweight resembles Singleton if all shared state collapsed into one object, but a
  singleton is single and may be mutable while flyweights are many and immutable (S10).
- **Common combinations** — Composite; a pooling factory; immutable value objects.
- **Refactoring opportunities** — Toward: a heap dump dominated by duplicated value objects. Away: a
  flyweight layer guarding a few thousand objects.
- **Testing considerations** — Benchmark memory before and after with representative data
  (TEST-PERF-01); test that flyweights cannot be mutated and that the factory returns the same
  instance per key.
- **Security considerations** — Shared objects must contain no tenant- or user-specific data; caches
  keyed by attacker-controlled values need bounds (memory exhaustion).
- **Language and framework considerations** — Java: `Integer.valueOf`, string interning, enums.
  Python: `__slots__`, `sys.intern`, cached constructors. JavaScript: shared style objects in canvas
  and map libraries. Go: struct-of-arrays layouts or pointers to shared immutable values.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/flyweight · direct. S9 Ch.25
  agrees on intrinsic and extrinsic state, immutability, the factory, applicability, pros, cons and
  relations, and stresses verifying the memory problem first. Example, misuses, testing, security
  and language notes: extension (X14).
