# Design rules (DES-*)

Class- and module-level design: SOLID, construction vs. use, cohesion and coupling, objects
vs. data structures, patterns, simplicity, domain modelling. Field meanings: `index.md`.
Overengineering is a defect class here (DES-SIMP-*), not a matter of taste.

Areas: SRP · OCP · LSP · ISP · DIP · DI · COH · OBJ · PAT · SIMP · DOM

### DES-SRP-01 · A module answers to one actor
- level: strong | severity: minor–major | provenance: direct
- sources: S2 Ch.7 (SRP — "responsible to one, and only one, actor"); S1 Ch.10 (The Single Responsibility Principle)
- why: When several stakeholders' rules share a module, a change requested by one (e.g. finance) silently alters behaviour another (e.g. operations) depends on; merges collide.
- signals: A class whose methods serve different departments or use cases; commits touching it for unrelated features; 7+ injected collaborators; names like `*Manager`, `*Service` with dozens of methods; shared private helpers used by unrelated methods.
- fix: Identify the actors; split by actor (separate classes, or a facade over per-actor classes). Do it incrementally under tests.
- verify: Recent and planned changes for each actor touch only that actor's module.
- auto: Co-change analysis (git log) and fan-out counts help; size alone does not establish a violation.
- except: Small cohesive modules serving one actor, even if long; framework controllers that only route.
- related: DES-SRP-02, CODE-DUP-02, DES-COH-01

### DES-SRP-02 · Keep business rules apart from I/O and presentation
- level: strong | severity: major | provenance: direct
- sources: S2 Ch.20 (Business Rules: Entities, Use Cases); S2 Ch.23 (The Humble Object Pattern); S2 Ch.19 (Policy and Level)
- why: Rules tangled with HTTP, SQL or UI code can't be tested without them and are rewritten whenever the delivery mechanism changes.
- signals: Pricing/eligibility logic inside controllers, templates, SQL strings or message handlers; business decisions in database triggers nobody can test; the same rule in a web handler and a CLI command.
- fix: Extract rules into plain functions/objects that take and return domain data; leave a thin ("humble") adapter for I/O.
- verify: The rule has unit tests that need no web server, database or UI.
- except: Trivial CRUD with no rules; rules deliberately in the database for integrity (constraints) — see DATA-SCHEMA-01.
- related: ARCH-DEP-01, ARCH-BND-04, TEST-BEH-01

### DES-OCP-01 · Add extension points where variation is real
- level: contextual | severity: minor | provenance: synthesized
- sources: S2 Ch.8 (OCP); S1 G23; S1 Ch.12 (rule 4: minimal classes and methods)
- why: When a variation axis exists (payment providers, export formats), extension by addition protects tested code. Speculative extension points are pure cost.
- signals (missing): Each new variant edits the same core function; long `if provider == …` chains. Signals (excess): strategy/plugin machinery with one implementation and no planned second.
- fix: Introduce the extension point when the second variant arrives or the axis is documented; remove unused ones.
- verify: Adding a variant adds code without editing the core.
- related: CODE-CPLX-03, DES-SIMP-02

### DES-LSP-01 · Subtypes and implementations honour the contract
- level: strong | severity: major | provenance: direct
- sources: S2 Ch.9 (LSP, including LSP and architecture)
- why: If callers must know which implementation they hold, polymorphism is broken and special cases spread.
- signals: Overrides that throw "not supported"; `instanceof`/type checks before calls; implementations with stronger preconditions or weaker guarantees; API versions that change semantics under the same endpoint.
- fix: Narrow the abstraction (ISP), use composition, or model the difference explicitly.
- verify: The same contract tests pass for every implementation.
- related: DES-ISP-01, TEST-CONTRACT-01

### DES-ISP-01 · Clients depend only on what they use
- level: contextual | severity: minor | provenance: direct
- sources: S2 Ch.10 (ISP)
- why: Fat interfaces drag in unneeded dependencies and redeploys, and make fakes painful.
- signals: Implementations full of empty/throwing methods; test doubles stubbing 20 methods to use 2; modules importing a huge package for one function.
- fix: Split interfaces by client role; in Go, define small interfaces at the consumer.
- related: DES-LSP-01, DES-DIP-01

### DES-DIP-01 · Policy depends on abstractions of volatile details
- level: strong | severity: minor–major | provenance: direct
- sources: S2 Ch.11 (DIP — stable abstractions; factories; the concrete component)
- why: High-level rules that import concrete DB clients, HTTP libraries or vendor SDKs change whenever those details change, and can't be tested in isolation.
- signals: Domain/use-case code constructing `new PostgresClient()`/`requests.get`; importing infrastructure packages from domain packages; static calls to vendor singletons in business logic.
- fix: Define the abstraction in the policy's terms, owned by the policy side; implement it in an adapter; inject it.
- verify: The policy module compiles/imports without infrastructure modules (`scripts/deps.py` can check direction).
- except: Stable, non-volatile concretions (standard library, value types, well-established utility libraries) — S2 Ch.11 explicitly tolerates these. Single-implementation interfaces need a reason (testing seam, boundary) — DES-SIMP-03.
- related: ARCH-DEP-01, DES-DI-01, DES-SIMP-03

### DES-DI-01 · Construct the object graph in one place
- level: strong | severity: minor–major | provenance: direct
- sources: S1 Ch.11 (Separate Constructing a System from Using It; Separation of Main; Factories; Dependency Injection); S2 Ch.26 (The Main Component)
- why: Business code that creates its own collaborators hard-wires choices, hides dependencies and blocks testing.
- signals: `new`/factory calls for services inside business methods; lazy-initialised singletons in domain code; environment checks (`if env == "prod"`) deep in logic.
- fix: Inject collaborators via constructors; wire them in `main`/composition root or the framework container.
- verify: A unit test can construct the class with fakes and no global setup.
- related: DES-DI-02, DES-DIP-01

### DES-DI-02 · No service locators or mutable globals in business logic
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 G18 (Inappropriate Static); S1 Ch.11 (Dependency Injection); S2 Ch.26
- why: Hidden global lookups make dependencies invisible, tests order-dependent and concurrency unsafe.
- signals: `Container::get()`/`app()`/`ApplicationContext.getBean()` inside domain code; mutable module-level state; static mutable caches.
- fix: Constructor injection; pass context explicitly; make globals immutable configuration.
- verify: Business classes can be instantiated in tests with fakes, without container bootstrapping or global resets.
- except: Framework idioms at the edges (Laravel facades in controllers/jobs are conventional — see `../languages/php-laravel.md`); logging handles.
- related: DES-DI-01, TEST-ISO-01

### DES-COH-01 · High cohesion; isolate what is likely to change
- level: strong | severity: minor | provenance: direct
- sources: S1 Ch.10 (Cohesion; Maintaining Cohesion Results in Many Small Classes; Organizing for Change; Isolating from Change)
- why: Cohesive units change for one reason; isolating volatile parts limits the blast radius of change.
- signals: Methods each using a disjoint subset of fields; "utility" modules of unrelated helpers; a feature's code spread across many packages.
- fix: Split by field-usage clusters; move behaviour next to the data it uses; group a feature's code together.
- verify: Most methods use most of the class's fields; feature changes stay within one module.
- related: DES-SRP-01, ARCH-COMP-01

### DES-COH-02 · Put behaviour where the data is (no feature envy)
- level: contextual | severity: minor | provenance: direct
- sources: S1 G14 (Feature Envy), G17 (Misplaced Responsibility)
- why: Logic that mostly manipulates another object's data belongs with that data; otherwise invariants are enforced (or not) in many places.
- signals: A method that calls five getters on another object to compute something; validation of an entity's invariants scattered across callers.
- fix: Move the method; tell objects what to do instead of asking for their data.
- except: Data structures/DTOs and functional pipelines where data and functions are deliberately separate (DES-OBJ-01).
- related: DES-OBJ-01, DES-COH-03

### DES-COH-03 · Don't navigate through strangers (Law of Demeter)
- level: contextual | severity: minor | provenance: direct
- sources: S1 Ch.6 (The Law of Demeter; Train Wrecks; Hiding Structure); S1 G36 (Avoid Transitive Navigation)
- why: `a.getB().getC().doThing()` couples the caller to the internal structure of three objects.
- signals: Long getter chains on domain objects; callers reaching into nested collections to mutate them.
- fix: Ask the nearest object to do the work; expose an intention-revealing method.
- except: Fluent APIs and builders; navigating plain data structures/DTOs; query DSLs.
- related: DES-COH-02, DES-OBJ-02

### DES-COH-04 · No artificial coupling; bases don't know their derivatives
- level: strong | severity: minor–major | provenance: direct
- sources: S1 G13 (Artificial Coupling), G7 (Base Classes Depending on Their Derivatives)
- why: Placing general things in specific modules (or the reverse) creates dependencies that exist for convenience only and block reuse.
- signals: Generic constants/enums inside a specific feature's class; a base class referencing subclasses; "common" modules importing features.
- fix: Move general items to a neutral home; invert the base→derived knowledge with polymorphism.
- verify: Moving a general item removes an import from a specific module; no base class references subclasses.
- related: ARCH-COMP-02, ARCH-COMP-03

### DES-OBJ-01 · Choose objects or data structures deliberately; avoid hybrids
- level: contextual | severity: minor | provenance: direct
- sources: S1 Ch.6 (Data Abstraction; Data/Object Anti-Symmetry; Hybrids; Data Transfer Objects; Active Record)
- why: Objects make new types cheap; data structures make new operations cheap. Hybrids expose data *and* carry behaviour that can be bypassed.
- signals: Classes with public setters for every field plus business methods relying on invariants; DTOs with business logic.
- fix: Either hide the data behind behaviour, or keep a plain structure and put logic in services/functions.
- except: Active Record models in framework-centric apps are an accepted hybrid (T-06); keep their business methods small and invariants enforced in one place.
- related: DES-OBJ-02, ARCH-DET-02

### DES-OBJ-02 · Encapsulate invariants; minimise visibility
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 Ch.10 (Encapsulation); S1 G8 (Too Much Information); S2 Ch.34 (Organization versus Encapsulation)
- why: If any code can set fields into an invalid state, every caller must re-validate. S2 Ch.34 notes that making everything public erases the architecture you drew.
- signals: Public mutable fields on domain objects; everything `public` in Java/C#; exported Go fields for internal state; invariants checked by callers.
- fix: Constructors/factories that only produce valid objects; package-private/internal visibility; value objects; immutable data where practical.
- verify: An invalid state cannot be constructed through the public API.
- related: DES-DOM-01, ARCH-BND-02

### DES-PAT-01 · Use a design pattern only for the forces it resolves
- level: contextual | severity: minor–major | provenance: extension
- sources: X2; S1 Ch.11 (Use Standards Wisely, When They Add Demonstrable Value)
- why: Patterns name proven solutions to recurring forces; applied without those forces they add indirection and vocabulary nobody needs.
- signals (misuse): Factories for objects with one constructor; Visitor for two types; Singleton as a global variable; Repository wrapping an ORM that already is one with no added policy. Signals (missing): hand-rolled, inconsistent solutions to a problem a well-known pattern solves (state machines, retries, observers).
- fix: Name the force first ("we add a new provider every quarter" → Strategy). Remove patterns whose force is gone.
- verify: The pattern's participants all have real, distinct responsibilities.
- related: DES-SIMP-02, DES-SIMP-03

### DES-PAT-02 · Prefer composition over inheritance for reuse
- level: contextual | severity: minor | provenance: extension
- sources: X2 (favour object composition over class inheritance); S2 Ch.9 (LSP)
- why: Inheritance for code reuse couples subclasses to parent internals and breaks easily (fragile base class).
- signals: Deep hierarchies (3+ levels) built for sharing helpers; subclasses overriding to disable behaviour.
- fix: Extract the shared behaviour into collaborators; inherit only for true is-a with substitutability.
- except: Framework-mandated base classes (controllers, Active Record models, test cases).
- related: DES-LSP-01

### DES-SIMP-01 · Simple design: tests, no duplication, intent, minimal parts
- level: strong | severity: minor | provenance: direct
- sources: S1 Ch.12 (Simple Design Rules 1–4)
- why: These four rules, in priority order, keep design emergent instead of speculative.
- signals: Untested design work; clever generic frameworks inside an application.
- fix: Apply in order: get it tested, remove duplication, make it expressive, then remove what is not needed.
- verify: Tests pass; no duplicated knowledge; names express intent; every class/method has a current purpose.
- related: DES-SIMP-02, TEST-STRAT-01

### DES-SIMP-02 · No speculative generality
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 Ch.12 (rule 4: Minimal Classes and Methods); S2 Ch.25 (Conclusion — YAGNI vs. late boundaries); S2 Ch.24 (Partial Boundaries)
- why: Abstractions built for imagined futures are paid for on every read and change, and usually guess the wrong axis of change.
- signals: Configuration options nobody sets; generic type parameters with one instantiation; "framework" layers inside an app; hooks/plugins with no plugins; abstract base classes with one subclass; feature flags for features shipped long ago.
- fix: Inline or delete; keep a partial boundary (S2 Ch.24) if a future need is credible but unscheduled.
- verify: Each abstraction can be justified by a current requirement, a test seam, or a documented decision.
- related: DES-SIMP-03, ARCH-FIT-01, ARCH-FIT-02

### DES-SIMP-03 · Indirection must pay for itself
- level: strong | severity: minor–major | provenance: synthesized
- sources: S2 Ch.24, Ch.25; S1 Ch.12 (rule 4); P-25
- why: Layers that only forward calls, interfaces with a single implementation and no seam need, and mapping between identical models multiply the code to read for each change.
- signals: `Controller → Service → Manager → Repository → DAO` where middle layers only delegate; a `FooInterface` + `FooImpl` pair for every class; three structurally identical DTO/entity/model classes mapped field-by-field with no difference in validation or shape; ports/adapters around in-process code that will never be swapped.
- fix: Collapse pass-through layers; keep interfaces where there is a test seam, multiple implementations, a dependency-direction need, or a published contract.
- verify: Each layer has a responsibility you can name in one phrase other than "calls the next layer".
- except: A deliberately adopted architecture (accepted ADR) — then raise the cost in an ADR review rather than violating it piecemeal.
- related: DES-SIMP-02, DES-DIP-01, ARCH-FIT-01

### DES-SIMP-04 · Understand the algorithm before polishing it
- level: strong | severity: minor | provenance: direct
- sources: S1 G21 (Understand the Algorithm)
- why: Code that "works" after flag-and-patch tinkering hides cases nobody reasoned about.
- signals: Patches adding special cases for specific inputs; comments like "don't know why this works".
- fix: Restate the algorithm (often as a simpler one), then rewrite under tests.
- verify: You can explain why the algorithm is correct for all input classes; tests cover each class.
- related: TEST-BND-01

### DES-DOM-01 · Model domain concepts as types in the domain's language
- level: contextual | severity: minor–major | provenance: extension
- sources: X1 (ubiquitous language, value objects); S1 Ch.2 (Use Problem Domain Names); S1 G26
- why: Primitive obsession (`String email`, `double amount`, `int userId`) lets invalid values flow everywhere and mixes up same-typed values.
- signals: Validation of the same primitive repeated in many places; functions taking several same-typed IDs; money as `float`; units implied by variable names (`timeoutMs`).
- fix: Value types (`Email`, `Money`, `OrderId`, `Duration`) that validate on construction; use the business's terms for types and methods.
- except: Thin CRUD layers and DTOs at boundaries; performance-critical paths (measured).
- related: DES-OBJ-02, DATA-TYPE-01, CODE-NAME-01

### DES-DOM-02 · Enforce each invariant inside one consistency boundary
- level: contextual | severity: major | provenance: extension
- sources: X1 (aggregates); S1 G26 (locks and transactions)
- why: An invariant ("order total ≤ credit limit", "seat sold once") checked across separately-saved objects or services will be violated under concurrency.
- signals: Invariants spanning entities saved in separate transactions; check-then-act across services without locking or compensation.
- fix: Group the data an invariant needs in one aggregate/transaction; elsewhere accept eventual consistency explicitly with compensation.
- related: REL-CONS-01, REL-CONS-03, ARCH-STYLE-03

### DES-DOM-03 · Put rules where the data is when rules are rich; scripts are fine when they aren't
- level: contextual | severity: minor | provenance: extension
- sources: X1; X14; S1 Ch.6 (Data/Object Anti-Symmetry)
- why: Rich rules spread across "service" scripts duplicate checks (an anaemic model); but forcing a rich object model onto simple CRUD is ceremony.
- signals (anaemic + rich rules): The same invariant checked in many services; entities that are bags of setters with complex rules elsewhere. Signals (overbuilt): elaborate domain objects for read-mostly forms.
- fix: Move rules into domain objects/aggregates when rules are many and interacting; keep transaction scripts for simple flows.
- related: DES-COH-02, ARCH-FIT-01
