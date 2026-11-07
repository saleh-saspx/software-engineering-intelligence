# Architectural and design patterns: forces, costs and misuse

A pattern is a contract with consequences: it buys some qualities and charges for them in others
(S8 Ch.7 preamble). Use this file after the drivers and quality-attribute scenarios are known
(`workflows/architecture-review.md` §1, ARCH-QA-01) to compare options, and when a review finds a
pattern applied without the force it resolves (DES-PAT-01). Real systems combine several patterns.

## Contents
1. Choosing a pattern · 2. System-level patterns · 3. Integration and data-flow patterns ·
4. Extensibility patterns · 5. Design-level patterns (object scale) · 6. Misuse signals

## 1. Choosing a pattern
1. Rank the quality-attribute scenarios the structure must meet (performance, availability,
   modifiability, security, testability, cost).
2. For each candidate, write what it buys for those scenarios and what it charges (latency,
   operational load, consistency work, indirection, team skills).
3. Prefer the option that meets the top scenarios with the fewest moving parts and the cheapest
   way back (S2 Ch.15, Keeping Options Open; ARCH-FIT-01).
4. Record the choice, the rejected options and the trigger for revisiting it in an ADR.

## 2. System-level patterns

| Pattern | Use when | Buys | Charges | Avoid when | Rules |
|---|---|---|---|---|---|
| Layered — strict or relaxed (S8 §7.1) | Clear separation of presentation, application, domain, infrastructure; infrastructure that changes | Substitutability behind interfaces; shared mental model | Pass-through code ("one field touches every layer"); a layer per hop costs latency; still one deployable | Layers would only forward calls (DES-SIMP-03); hot paths need directness | ARCH-DEP-01, T-19 |
| Ports and adapters / Clean Architecture (S2 Ch.22, Ch.34) | Rich, long-lived domain rules; volatile infrastructure; core testable without I/O | Business rules isolated from frameworks, DB and UI | Interfaces and mapping at each boundary | CRUD-centric apps where the framework is the platform (ARCH-DET-02) | ARCH-DEP-02, ARCH-DET-01 |
| Modular monolith (S2 Ch.16–18, Ch.27) | One or a few teams; modular code with one deployment | Simple operations and transactions; boundaries enforceable in the build | Discipline to keep modules decoupled; shared release | Parts need independent scaling, release cadence or compliance isolation | ARCH-STYLE-01, ARCH-BND-02 |
| Services / microservices (S2 Ch.27; S8 §7.5.4 lineage) | Several teams needing independent releases; distinct scaling or availability; mature operations | Independent deployability and scaling per capability | Network failure modes, data consistency work, observability and on-call cost | One team; features that always touch several services (the Kitty Problem) | ARCH-STYLE-01, ARCH-STYLE-02 |
| Client–server (S8 §7.5.1) | An authoritative resource many clients use | One source of truth; central security and consistency | Bottleneck and single point of failure (replicate, load-balance) | Peers must work offline and reconcile | PERF-SCALE-01 |
| MVC / MVP / MVVM (S8 §7.3) | Interactive UIs | Model independent of views; testable presenters | Indirection for trivial screens | — | ARCH-BND-04 (humble views) |
| Shared data (S8 §7.2.1) | Many components need one consistent body of data | Independent accessors; the store enforces integrity and concurrency | Schema becomes a system-wide contract (coupling magnet); bottleneck | Integration between separately deployed services | ARCH-STYLE-02, DATA-MODEL-01 |
| CQRS / read models (X14) | Strong read/write asymmetry in one area; reporting needs | Read models shaped for queries; write model shaped for invariants | Lag between models; more moving parts | Applied system-wide without the asymmetry | DATA-REPL-01 |

## 3. Integration and data-flow patterns

| Pattern | Use when | Buys | Charges | Avoid when | Rules |
|---|---|---|---|---|---|
| Observer / publish–subscribe / events (S8 §7.2.2; X13) | Open-ended reactions; temporal decoupling across contexts | Producers unaware of consumers; new consumers without changing producers | Implicit control flow, ordering bugs, cascades, duplicates, eventual consistency, lapsed listeners | Reactions are fixed and a direct call is clearer | ARCH-STYLE-03, REL-CONS-02 |
| Transactional outbox, saga (X13) | A DB write plus a message must be atomic; multi-service workflows | No lost or phantom events; compensations instead of distributed locks | Relay process; compensation logic to design and test | One database can hold the whole invariant (DES-DOM-02) | REL-CONS-01 |
| Broker — message broker, API gateway, service mesh (S8 §7.5.3) | Location transparency, routing, cross-cutting retries and monitoring | Clients and servers decoupled from each other's location | Extra hop, complexity, a component that needs redundancy | Two services with a stable address | REL-TIME-01 |
| REST over HTTP (S8 §7.5.4) | Resource-oriented client–server interaction | Uniform interface, statelessness, fits web infrastructure | Chatty interfaces; poor fit for non-resource operations; state pushed to tokens or data layer | RPC-style operations forced into CRUD verbs | API-*, API-IDEMP-01 |
| Pipes and filters (S8 §7.4.1) | Sequences of transformations | Reuse, composability, parallelism | Lowest-common-denominator formats; poor error propagation; not interactive | Interactive workloads | ARCH-STYLE-04 |
| Dataflow networks, unbounded streams (S8 §7.4.2–7.4.3) | Continuous event processing | Incremental results, scalable processing | Windowing, late and out-of-order data, backpressure, rate mismatch, buffer deadlocks | Bounded data that fits a batch job | ARCH-STYLE-04, REL-RES-02 |
| MapReduce-style batch (S8 §7.4.4; X20) | Large, partitionable batch work | Parallelism and fault tolerance | Rigid shape; expensive shuffle | Iterative or interactive workloads | DATA-BATCH-01 |

## 4. Extensibility patterns

| Pattern | Use when | Buys | Charges | Avoid when | Rules |
|---|---|---|---|---|---|
| Strategy / registry of implementations (X16; S2 Ch.8) | A real axis of variation inside one process (providers, formats, pricing rules) | New variants added without editing the core | One interface plus wiring | One variant and no evidence of a second | ARCH-EXT-01, DES-OCP-01 |
| Plug-in architecture / microkernel (S2 Ch.17; S8 §7.6.2) | Other teams, partners or customers add behaviour | Core protected from extension churn; independent release of plug-ins | A published, versioned contract; contract tests; isolation for untrusted code | All extensions are in-house and few | ARCH-EXT-02, ARCH-EXT-03 |
| Product line — commonality and variability (S8 §7.6) | A family of products sharing a platform | Shared fixes and hardening; faster new products | Up-front platform cost recovered only after enough products; mispredicted variability | Unstable domain; a single product | ARCH-EXT-01 |
| Feature flags (S8 §14.3.3) | Separating deploy from release; kill switches; experiments | Progressive exposure; instant disable | Doubled paths per live flag; stale flags become dangerous debt | Permanent configuration masquerading as a flag | DLV-FLAG-01 |
| Webhooks and events as extension points (X13) | External systems react to your changes | Integration without code in your process | Signature verification, retries, idempotency, schema versioning | — | ARCH-EXT-02, SEC-DESIGN-01 |

## 5. Design-level patterns (object scale)

Named in X2, taught in X16 and catalogued in S10; each resolves a specific force. Name the force
before using it (DES-PAT-01). The full catalog of 22 patterns — one file each, with selection,
look-alike comparisons, anti-patterns and framework profiles — is `references/patterns/index.md`;
the table below is a quick reminder of the most common ones.

| Pattern | Force it resolves | Misuse signal |
|---|---|---|
| Strategy | An algorithm or policy varies independently of its users | One strategy forever; strategies chosen by long `if` chains anyway |
| Observer | Dependents must react to state changes without the subject knowing them | Ordering-dependent observers; listeners never removed |
| Decorator | Add responsibilities without subclass explosion (open–closed) | Deep decorator stacks no one can debug |
| Factory method / abstract factory | Creation varies by subclass, or a family of products must match (dependency inversion) | Factories for objects with one constructor; a factory per class (T-26) |
| Adapter / Facade | Wrap a third-party or legacy interface; give a subsystem a simple entry (least knowledge) | Facades that only forward every method; framework "facades" mistaken for the pattern (T-27) |
| Template method | Fixed algorithm with overridable steps (the Hollywood principle) | Subclasses overriding steps the base never documented (DES-EXT-01); callback "templates" confused with it (T-25) |
| State | Behaviour depends on an explicit state machine | Booleans and status strings checked everywhere instead |
| Proxy | Control access: lazy, remote, protection, caching | Hidden I/O behind innocent-looking calls (CODE-FUNC-03) |
| Composite | Treat parts and wholes uniformly | Leaf types forced to implement meaningless container methods (DES-LSP-01) |

## 6. Misuse signals across patterns
- The pattern's participants have no distinct responsibilities (pass-through layers, empty
  adapters) — DES-SIMP-03.
- The quality the pattern buys is not among the top scenarios — ARCH-QA-01, ARCH-FIT-01.
- The cost it charges is unpaid: events without idempotency, services without observability,
  plug-ins without versioned contracts, flags without owners.
- A second pattern solves the same concern elsewhere in the codebase — ARCH-FIT-03.
- A pattern named from vocabulary rather than from its participants — DES-PAT-04; object-level
  misuse catalog: `references/patterns/anti-patterns.md`.
