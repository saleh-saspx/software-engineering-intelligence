# Architecture rules (ARCH-*)

Boundaries, dependency direction, components, the place of details, fit-for-context,
architectural style, domain boundaries, decisions. Field meanings: `index.md`.
Before applying any ARCH rule, run the fit assessment in `../workflows/architecture-review.md`:
most architectural false positives come from applying a style the system never needed.

Areas: DEP · BND · COMP · DET · FIT · STYLE · DOM · DEC

## DEP — dependency direction

### ARCH-DEP-01 · Source dependencies point toward higher-level policy
- level: strong | severity: major | provenance: direct
- sources: S2 Ch.22 (The Dependency Rule); S2 Ch.19 (Policy and Level); S2 Ch.11 (DIP)
- why: When policy imports details, every change to a detail (DB, framework, UI) risks the business rules, and the rules can't be built or tested alone.
- signals: Domain/use-case packages importing controllers, ORM sessions, HTTP clients, message-bus SDKs; "core" modules depending on "infrastructure"; circular imports between layers.
- fix: Move the interface to the policy side and implement it in the outer layer (DIP); move misplaced code to its layer.
- verify: `scripts/deps.py --forbid "domain->infrastructure"` (or the project's architecture tests: ArchUnit, import-linter, dependency-cruiser, deptrac) reports no violations.
- auto: `scripts/deps.py`; ArchUnit (Java), import-linter (Python), dependency-cruiser (JS/TS), deptrac (PHP), `go list` + custom checks.
- except: Systems without a policy/detail split worth protecting (thin CRUD) — ARCH-FIT-01 decides; then this rule is not applied.
- related: ARCH-DEP-02, DES-DIP-01, ARCH-COMP-02

### ARCH-DEP-02 · Inner layers use no framework, database or transport types
- level: contextual | severity: major | provenance: direct
- sources: S2 Ch.22 (A Typical Scenario); S2 Ch.30–32 (Database, Web, Frameworks Are Details)
- why: Annotating or typing business rules with framework constructs welds them to that framework's lifecycle and test harness.
- signals: Entities extending ORM base classes in a rule-rich domain; use cases accepting `HttpServletRequest`/`Request`/`ctx *gin.Context`; domain functions returning ORM query objects.
- fix: Accept and return plain domain types/request models; adapt at the edge.
- except: Framework-centric architecture chosen on purpose (ARCH-DET-02); pragmatic annotations (e.g. JPA on entities) accepted by an ADR.
- related: ARCH-DEP-03, ARCH-DET-01

### ARCH-DEP-03 · Data crosses boundaries in the inner layer's shape
- level: contextual | severity: minor–major | provenance: direct
- sources: S2 Ch.20 (Request and Response Models); S2 Ch.22 (Which Data Crosses the Boundaries — simple data structures)
- why: Passing ORM entities or DB rows outward exposes schema and lazy-loading to callers; passing transport objects inward couples rules to the protocol. It also leaks fields (security) through serialisers.
- signals: Controllers serialising ORM entities directly to JSON; API responses changing when a column is added; `toArray()`/`__dict__` dumps of models.
- fix: Explicit response/request models (resources, DTOs, serializers with allow-listed fields) at the boundary.
- except: Internal admin tools and prototypes where schema exposure is acceptable (state it).
- related: API-DESIGN-01, SEC-AUTHZ-03, SEC-DATA-01

## BND — boundaries

### ARCH-BND-01 · Draw boundaries between things that change for different reasons or at different rates
- level: strong | severity: major | provenance: direct
- sources: S2 Ch.17 (Boundaries: Drawing Lines; Which Lines Do You Draw, and When?; Plugin Architecture)
- why: Boundaries let parts evolve independently; drawn in the wrong place they create coupling across every change.
- signals: Every feature touches the same set of modules; UI changes force domain changes; one module mixing very stable rules with very volatile integrations.
- fix: Identify axes of change (actors, volatility, deployment, trust); align module boundaries to them; make volatile parts plugins to stable ones.
- verify: Co-change analysis shows most changes stay within one module.
- related: ARCH-FIT-01, DES-SRP-01, ARCH-DOM-01

### ARCH-BND-02 · Enforce boundaries with the language, build or tests — not convention alone
- level: contextual | severity: minor–major | provenance: direct
- sources: S2 Ch.34 (The Devil Is in the Implementation Details; Organization versus Encapsulation)
- why: Directory names do not stop imports; boundaries enforced only by discipline erode under deadline pressure.
- signals: Everything public; "internal" packages imported from everywhere; layering documented in a wiki but not checked.
- fix: Use visibility (package-private, `internal/` in Go, module `exports`, Java modules/Gradle modules, PHP namespaces + deptrac), separate build modules, or architecture tests in CI.
- verify: A forbidden import fails the build or the test suite.
- related: ARCH-DEP-01, DES-OBJ-02, DLV-CI-01

### ARCH-BND-03 · The structure screams the domain
- level: contextual | severity: minor | provenance: direct
- sources: S2 Ch.21 (Screaming Architecture); S2 Ch.34 (Package by Feature; Package by Component)
- why: A top level of `controllers/ models/ services/` says "web framework", not "insurance claims"; features are scattered across layers so every change touches many folders.
- signals: Feature changes routinely touching 5+ top-level directories; no place where a use case's code lives together.
- fix: In growing codebases, group by feature/component within the framework's conventions.
- except: Frameworks whose conventions mandate layer-first directories (Rails, Laravel defaults) for small/medium apps — follow the framework (P-53).
- related: ARCH-COMP-01, DES-COH-01

### ARCH-BND-04 · Put hard-to-test behaviour behind humble objects
- level: contextual | severity: minor | provenance: direct
- sources: S2 Ch.23 (Humble Object Pattern; Presenters and Views; Database Gateways; Service Listeners)
- why: Splitting a boundary into a testable part (presenter, gateway interface) and a thin untested part (view, driver) gives coverage where logic lives.
- signals: Formatting/branching logic inside templates or views; logic in DB callbacks or message listeners with no tests.
- fix: Move logic into a presenter/handler that can be unit-tested; keep the view/listener trivial.
- related: DES-SRP-02, TEST-BEH-01

## COMP — component principles

### ARCH-COMP-01 · Group into components by common closure
- level: strong | severity: minor | provenance: direct
- sources: S2 Ch.13 (Common Closure Principle; Reuse/Release Equivalence; Common Reuse; Tension Diagram)
- why: Classes that change together should be released together; consumers shouldn't depend on parts they don't use.
- signals: Small changes requiring coordinated releases of several packages; consumers pulling a large shared library for one helper.
- fix: Regroup by co-change; split shared libraries along consumer needs. Early-stage projects favour CCP; widely reused libraries favour REP/CRP.
- verify: Co-change history shows packages released together change together; consumers import only what they use.
- related: ARCH-COMP-02, DES-COH-01

### ARCH-COMP-02 · The component dependency graph has no cycles
- level: strong | severity: major | provenance: direct
- sources: S2 Ch.14 (The Acyclic Dependencies Principle; Breaking the Cycle)
- why: Cycles fuse components into one unit for building, testing and releasing, and make change ripple unpredictably.
- signals: Package A imports B and B imports A (directly or transitively); "util" importing feature code; Python import errors worked around with function-local imports.
- fix: Apply DIP (introduce an interface owned by one side) or extract the shared part into a new component both depend on.
- verify: `scripts/deps.py` reports no strongly connected components above the chosen granularity.
- auto: `scripts/deps.py` (Tarjan SCC over imports); jdepend, madge, pydeps, deptrac.
- except: Cycles inside a single cohesive package/module (lower severity: minor).
- related: ARCH-COMP-03, DES-COH-04

### ARCH-COMP-03 · Depend toward stability; make stable components abstract
- level: contextual | severity: minor–major | provenance: direct
- sources: S2 Ch.14 (Stable Dependencies Principle; Stable Abstractions Principle; Main Sequence; Zone of Pain; Zone of Uselessness)
- why: A volatile component that many others depend on becomes impossible to change ("zone of pain"); an abstract component nobody depends on is waste.
- signals: A frequently-changing concrete module with high fan-in; stable "core" packages importing volatile ones; interfaces packages with no implementers or users.
- fix: Invert the dependency through an abstraction; move volatile code out of high-fan-in modules.
- verify: `scripts/deps.py` instability values decrease along dependency edges for the main components.
- except: Stable concrete components (standard library, schemas that rarely change) — S2 notes non-volatile components in the zone of pain are harmless.
- related: ARCH-COMP-02, DES-DIP-01

## DET — details at the edge

### ARCH-DET-01 · Keep rule-rich business logic independent of storage and delivery
- level: contextual | severity: major | provenance: direct
- sources: S2 Ch.30 (The Database Is a Detail), Ch.31 (The Web Is a Detail), Ch.32 (Frameworks Are Details); S2 Ch.15 (Keeping Options Open)
- why: Where business rules are many and long-lived, binding them to a DB schema or web framework makes every infrastructure change a business-logic change.
- signals: Business rules expressed in SQL views/triggers or ORM query scopes only; rules duplicated between web and batch paths; rules untestable without a DB.
- fix: Extract rules into plain domain code behind gateways; persist via adapters.
- except: Data-centric applications whose "rules" are mostly queries (reporting, CRUD admin) — use the database's strengths.
- related: ARCH-DET-02, DES-SRP-02, DATA-ACCESS-01

### ARCH-DET-02 · In framework-centric applications, work with the framework
- level: contextual | severity: minor–major | provenance: synthesized
- sources: S2 Ch.24 (Partial Boundaries); S2 Ch.32 (Asymmetric Marriage — know the cost); S1 Ch.6 (Active Record); S1 G24; T-06
- why: Rebuilding repositories, DTO layers and ports around Laravel/Rails/Django/Spring Data in a CRUD-heavy app doubles the code and fights the framework's tooling, for protection that is rarely used.
- signals: Overengineering — repository interfaces wrapping Eloquent/ActiveRecord/Django ORM one-to-one; mappers between identical entity and model classes; hexagonal packaging for a forms-over-data app. Under-engineering — complex, growing domain rules embedded in controllers, model callbacks and templates with no tests.
- fix: Use framework-native structure (models, form requests/serializers, policies, jobs); extract service/domain classes only around the rule-rich parts.
- verify: The extra layers you keep each protect a named force (ARCH-FIT-01).
- related: ARCH-FIT-01, DES-SIMP-03, CODE-BND-01

### ARCH-DET-03 · Don't weld the core to a framework you may outgrow
- level: contextual | severity: minor | provenance: direct
- sources: S2 Ch.32 (Asymmetric Marriage; The Risks; The Solution)
- why: Frameworks evolve on their authors' schedule; inheriting their base classes deep in your domain makes upgrades and replacement costly.
- signals: Domain classes extending framework classes in rule-rich code; framework annotations driving business behaviour; major framework upgrades taking months.
- fix: Keep the framework at the edges where the domain justifies it: framework-specific code goes into adapter/proxy classes that live in plugin components outside the business rules, and the framework wires things up in Main (S2 Ch.32, The Solution; Ch.26).
- except: Where ARCH-DET-02 applies.
- related: ARCH-DET-02, CODE-BND-01

## FIT — fitness for context

### ARCH-FIT-01 · Architectural complexity matches problem complexity and team context
- level: strong | severity: major | provenance: synthesized
- sources: S2 Ch.15 (What Is Architecture?), Ch.17, Ch.24, Ch.25; S1 Ch.12 (rule 4); S3 Ch.1, Principle 9; P-25
- why: Both under- and over-engineering are costly: too little structure lets change costs grow without bound; too much makes every change slow from day one and often guesses the wrong axes of change.
- signals (over): More layers/modules/services than developers; abstractions with one implementation everywhere; distributed system for a single team's CRUD app; ports/adapters with no swapped adapters or test fakes. Signals (under): rule-rich domain with logic in controllers and views; no seams for testing; change costs visibly rising (lead time, regressions).
- fix: Recommend the *smallest* structure that handles the named forces; propose incremental moves (extract module, introduce boundary at the volatile seam) rather than a rewrite.
- verify: Every boundary in the recommendation is tied to a force (actor, volatility, deployment, trust, testability) in the written rationale.
- related: ARCH-FIT-02, DES-SIMP-02, DES-SIMP-03, ARCH-STYLE-01

### ARCH-FIT-02 · Hedge uncertain futures with partial boundaries
- level: contextual | severity: minor | provenance: direct
- sources: S2 Ch.24 (Skip the Last Step; One-Dimensional Boundaries; Facades); S2 Ch.25 (Conclusion)
- why: A partial boundary (separate module, facade or interface without separate deployment) keeps the option of a full boundary cheaply.
- signals: Debate between "full hexagonal" and "nothing" for an area with plausible but unscheduled change.
- fix: Choose a partial boundary and record the trigger for completing it (ADR).
- related: ARCH-FIT-01, ARCH-DEC-01

### ARCH-FIT-03 · One way to do each architectural concern
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 G11 (Inconsistency); S4 (ADR scope: construction techniques); X14
- why: Two ORMs, three HTTP clients, mixed error formats or several state-management libraries multiply the knowledge needed to change anything and the dependency surface.
- signals: Several libraries solving the same problem; competing patterns for the same concern in different modules; new code introducing yet another way.
- fix: Pick one (record it in an ADR), migrate opportunistically, and stop new usage of the others.
- verify: New code uses the chosen approach; usage counts of alternatives decrease over time.
- related: ARCH-DEC-01, AGT-CONV-02, DLV-DEPS-01

## STYLE — architectural style

### ARCH-STYLE-01 · Modular monolith by default; services only for concrete drivers
- level: strong | severity: major | provenance: synthesized
- sources: S2 Ch.16 (Decoupling Modes; Independent Deployability), Ch.18 (Boundary Anatomy — The Dreaded Monolith; Services), Ch.27 (Services: Great and Small; The Kitty Problem)
- why: Services decouple deployment and operation, not necessarily change; without independent deployability needs and operational maturity (CI/CD, observability, on-call), they add network failure modes, data consistency problems and coordination costs.
- signals: Services that must be deployed together; a single team owning many services; synchronous call chains across 3+ services per request; features always touching several services (S2's Kitty Problem).
- fix: Consolidate tightly coupled services or keep a modular monolith with enforced module boundaries; split out a service when a specific driver appears (independent scaling, separate team, different availability or compliance profile).
- verify: Each service boundary in the design names its driver; most features change one service.
- related: ARCH-STYLE-02, ARCH-FIT-01, ARCH-BND-02

### ARCH-STYLE-02 · Each service owns its data
- level: strong | severity: major | provenance: synthesized
- sources: S2 Ch.27 (services coupled by shared data and cross-cutting concerns); X1 (bounded contexts)
- why: Services integrating through a shared database are coupled through its schema; any migration needs all of them.
- signals: Two services writing the same tables; reporting jobs reading another service's private tables; schema changes coordinated across teams.
- fix: Expose data through APIs or events; give each service its own schema; use read models for reporting.
- verify: No service reads or writes another service's tables (inspect connection configs and queries).
- related: ARCH-STYLE-01, ARCH-STYLE-03, DATA-MIG-01

### ARCH-STYLE-03 · Event-driven designs make delivery, ordering and consistency explicit
- level: contextual | severity: major | provenance: extension
- sources: X13; X6
- why: Asynchronous messaging buys temporal decoupling at the price of at-least-once delivery, reordering, duplicates, and eventual consistency; ignoring them causes double-processing and lost updates.
- signals: Consumers that are not idempotent; DB write and message publish not atomic (no outbox); no dead-letter handling; events carrying full entity snapshots that couple consumers to schema; in-process events used where a function call would do.
- fix: Idempotent consumers (dedup keys), transactional outbox, DLQ with alerting, versioned event schemas; prefer direct calls for in-process flows.
- verify: Replaying or duplicating a message produces the same end state (test it).
- related: REL-CONS-02, ARCH-STYLE-02, API-CONTRACT-01

## DOM — domain boundaries

### ARCH-DOM-01 · Module boundaries follow business capabilities and language
- level: contextual | severity: major | provenance: extension
- sources: X1 (bounded contexts, context mapping); S2 Ch.16 (Decoupling Use Cases)
- why: When one model ("Customer") serves sales, billing and support, it accretes conflicting meanings; boundaries aligned with capabilities keep models coherent.
- signals: Entities with dozens of fields used differently by each department; the same word meaning different things in different modules; one change request touching unrelated capabilities.
- fix: Split models per context; translate at boundaries (anti-corruption layer for legacy/external models).
- except: Small domains where one model is genuinely shared and stable.
- related: ARCH-BND-01, CODE-DUP-02, DES-DOM-01

## DEC — decisions

### ARCH-DEC-01 · Record architecturally significant decisions as ADRs
- level: strong | severity: minor | provenance: direct
- sources: S4 (Architectural decision record process; Scope of the ADR process; Best practices)
- why: Unrecorded decisions are re-litigated, forgotten, or overruled by people who don't know why they were made (S4's three anti-patterns).
- signals: Recurring debates; "why do we use X?" with no answer; significant choices (structure, NFRs, dependencies, interfaces, construction techniques) without a record.
- fix: Write an ADR with `../../assets/templates/adr.md`; store centrally (repo `docs/adr/` or wiki) and link from the main docs.
- verify: The decision log lists an ADR for each significant structural, NFR, dependency, interface and tooling choice.
- related: ARCH-DEC-02, ARCH-DEC-03, TD-DEC-01

### ARCH-DEC-02 · Accepted ADRs are constraints; change them by superseding
- level: constraint | severity: major | provenance: direct
- sources: S4 (ADR review process — accepted ADRs are immutable; superseded by new ADRs; code review against ADRs; addressing non-compliant code)
- why: A decision record only works if reviews enforce it and changes go through the same deliberate process.
- signals: Code contradicting an accepted ADR; edited (not superseded) ADRs; legacy code non-compliant with a new ADR and no plan.
- fix: In review, link the ADR and request compliance — or, if the ADR is outdated, propose a superseding ADR. For legacy non-compliance, create TD items or migrate gradually (S4).
- verify: Changes conform to accepted ADRs or reference a superseding proposal.
- related: ARCH-DEC-01, TD-DEC-01

### ARCH-DEC-03 · An ADR states context, an imperative decision, and consequences
- level: strong | severity: minor | provenance: direct
- sources: S4 (ADR contents; FAQ — what information should an ADR contain)
- why: The value of an ADR is the *why*; vague decisions ("we should consider…") don't constrain anything.
- signals: ADRs without alternatives considered, without negative consequences, using "should", or missing status/date/changelog.
- fix: Context incl. options considered; decision in imperative form ("We use…"); positive and negative consequences; status (Proposed/Accepted/Rejected/Superseded); compliance checks; changelog and owner.
- verify: Each ADR has status, date, context with options, imperative decision, positive and negative consequences, changelog.
- related: ARCH-DEC-01
