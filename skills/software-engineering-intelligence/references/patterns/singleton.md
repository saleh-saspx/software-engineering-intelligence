# Singleton · creational

**Intent** — Ensure that a class has exactly one instance and provide a global access point to it
(S10).

**Example (real problem)** — A desktop sync client must open its local database file exactly once
per process; two connections with independent caches corrupt the file. In a server application
with a DI container the same need — one shared connection pool or metrics registry — is met by
registering a single instance in the container and injecting it, without any global access point
(T-24).

- **Problem** — Some resources must be unique per process (a device handle, a file lock, a
  process-wide registry), and a global variable can be overwritten from anywhere.
- **Context** — A process-unique resource that many parts of the code need.
- **Motivation** — Control instantiation and protect the single instance; the pattern solves two
  problems at once — uniqueness and global access — which is why S10 and S9 note that it violates
  the single responsibility principle.
- **Applicability** — One instance shared by all clients; stricter control over global state than a
  global variable gives (S10).
- **Structure** — A class with a private constructor, a static field holding the instance and a
  static accessor that creates it on first use.
- **Participants and responsibilities** — The singleton class alone.
- **Collaborations** — Clients call the static accessor.
- **Implementation considerations** — Thread-safe lazy initialisation (holder idiom, `sync.Once`,
  double-checked locking with correct memory semantics) or eager initialisation; in Java,
  serialisation and reflection can create a second instance, which an enum singleton prevents (X15
  Item 3); class loaders and containers may each hold their own instance.
- **Consequences** — Every caller depends on the concrete class and its global state, invisibly;
  tests share that state.
- **Benefits** — A guaranteed single instance, a global access point and lazy creation (S10).
- **Trade-offs** — Uniqueness is bought with testability and explicit dependencies.
- **Costs** — Breaks SRP; can mask poor design in which components know too much about each other;
  needs special handling under concurrency; hard to unit test because the private constructor and
  static methods resist mocking (S10).
- **Known misuses** — Singletons used as global variables for configuration, the current user or the
  request context; mutable singletons shared across threads or tenants; "manager" singletons that
  grow into god objects; singletons in code that already has a DI container (DES-DI-02).
- **When not to use** — A container or composition root can own one instance (Spring singleton-scope
  beans, Laravel `singleton()` bindings) — inject it instead; the state is per request or per
  tenant; tests must replace it.
- **Related patterns** — A facade usually needs only one instance; Flyweight resembles a singleton
  if all shared state collapses into one object, but flyweights are many and immutable while a
  singleton may be mutable; abstract factories, builders and prototypes can be singletons (S10).
- **Common combinations** — Facade and Abstract Factory — in both cases prefer a container-managed
  single instance.
- **Refactoring opportunities** — Away: replace `X.getInstance()` calls with constructor injection
  and keep one instance at the composition root; add an interface only for a test seam or a second
  implementation.
- **Testing considerations** — If a classic singleton must stay, give tests a package-private reset
  and keep such tests out of parallel runs; better, inject the instance.
- **Security considerations** — Mutable singletons leak data between users, requests or tenants (a
  cached "current user" is a classic); keep them immutable or synchronised and free of per-request
  state.
- **Language and framework considerations** — Spring's singleton scope is not this pattern: one
  instance per container, injected and replaceable in tests (T-27). Python: a module is already a
  singleton — use a module-level object or a cached function. Go: a package-level value initialised
  with `sync.Once`. JavaScript/TypeScript: an exported module instance (one per module loader —
  watch for duplicates across bundles). See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/singleton · direct. S9 Ch.19
  agrees (two problems, SRP, threading, testing difficulty); S9 calls the access point "secure"
  where S10 says the instance is protected from being overwritten — S10's wording followed. X15
  Item 3; S1 G18 and DES-DI-02 on global state; resolution in T-24. Example, misuses, security and
  language notes: extension (X14).
