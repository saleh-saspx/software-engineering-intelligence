# Workflow: architecture and design review

For evaluating an existing architecture, a design proposal ("should we move to microservices /
hexagonal / CQRS?"), a module structure, an extensibility or scaling question, or a significant
design choice; and for recording the outcome as ADRs. Rules: `../rules/architecture.md`,
`../rules/design.md`. Pattern trade-offs: `../architecture-patterns.md`.

## Contents
1. Establish the drivers · 2. Describe the architecture · 3. Fit assessment · 4. Structural
checks · 5. Over- and under-engineering · 6. Options, trade-offs, recommendation · 7. Record
decisions (ADR) · 8. Reviewing a proposal · 9. Running an architecture review

## 1. Establish the drivers
Architecture is justified only by forces. Collect (or ask for, or state as assumptions):
- **Domain complexity**: CRUD/data-centric vs. rule-rich; how fast rules change; regulatory stakes.
- **Change expectations**: where change happens (git history, roadmap), lifetime of the system.
- **People**: number of developers and teams, ownership boundaries, skills.
- **Operations**: deployment frequency, CI/CD, observability, on-call maturity, hosting constraints.
- **Quality attributes**: latency, throughput, availability targets, security and compliance,
  data residency, cost.
- **Constraints**: existing ADRs, mandated platforms, contracts with other systems.
Without drivers, any architecture opinion is taste. S3 Principle 9: whether structure is debt
depends on how the system will evolve.

Write the three to five driving quality attributes as **scenarios** — stimulus, environment,
response, response measure (S8 §6.1.4, ARCH-QA-01): "2,000 bookings a minute at peak, p95 under
300 ms"; "payment provider down, no lost orders"; "a new export format added without touching the
core". Rank them; every later recommendation should name the scenario it serves.

## 2. Describe the architecture
Components and their responsibilities; dependencies (`scripts/deps.py`); data ownership; sync vs.
async communication; deployment units; cross-cutting concerns (authentication, authorisation,
logging, configuration, error handling). For proposals, describe the target the same way, plus
the migration path. Keep views separate — module, runtime and deployment — each for a stated
audience (S8 §6.4, ARCH-DOC-01); `../../assets/templates/architecture-description.md` is the
outline when the result should be kept.

## 3. Fit assessment
Compare the drivers with the structure. Defaults (deviate when drivers say so — and say which):

| Situation | Sensible default | Typical over-engineering |
|---|---|---|
| CRUD/data-centric app, one team, framework chosen as platform | Framework-native layered monolith (MVC, ORM models, form/request validation, policies) — ARCH-DET-02 | Hexagonal ports/adapters, repository interfaces over the ORM, DTO mapping at every layer |
| Rich, long-lived domain rules; one or few teams | Modular monolith; isolate the domain core behind interfaces where rules live (ports/adapters around the *core*, not everywhere) — ARCH-DET-01, ARCH-FIT-02 | Splitting into services to "enforce" modularity |
| Several teams needing independent releases; distinct scaling or availability needs; mature ops | Services along business capabilities, each owning its data — ARCH-STYLE-01/02, ARCH-DOM-01 | Services per entity or per layer; shared database |
| Integration across contexts, audit trails, temporal decoupling | Events with outbox, idempotent consumers, versioned schemas — ARCH-STYLE-03 | Event bus for in-process calls; event sourcing without a need for history |
| Strong read/write asymmetry in one area | Read models/CQRS *for that area* | CQRS across the whole system |
| Prototype / MVP with uncertain direction | Simplest structure; partial boundaries at obvious seams — ARCH-FIT-02 | "Enterprise" scaffolding from day one |
| New variants arrive regularly (providers, formats, partner rules) | One in-process variation point: strategy/registry or plug-in contract, versioned; isolation only for untrusted third-party code — ARCH-EXT-01..03 | A service, queue or framework per variant |
| Unbounded event or log streams | Dataflow with windows, backpressure and idempotent stages — ARCH-STYLE-04 | Streaming platform for bounded nightly batches |
| Growth in load | Stateless handlers, measured contention fixes, caches and replicas, per-tenant limits — PERF-SCALE-01..03 | Sharding or services before measuring the bottleneck |

Name the fit in one sentence: "Layered Laravel monolith; appropriate for the CRUD-heavy domain,
but the pricing rules (≈30% of recent change) have outgrown controller methods."

## 4. Structural checks
- **Dependency direction** — `scripts/deps.py PATH --forbid "domain->infrastructure"` (adapt names)
  or the project's architecture tests (ARCH-DEP-01).
- **Cycles** — none between components (ARCH-COMP-02).
- **Stability** — volatile modules shouldn't have high fan-in (ARCH-COMP-03).
- **Boundary enforcement** — visibility, modules or tests, not just folders (ARCH-BND-02).
- **Data ownership** — no shared tables across deployables (ARCH-STYLE-02).
- **Consistency** — one approach per concern: data access, HTTP clients, errors, config (ARCH-FIT-03).
- **Cross-cutting security** — where authentication/authorisation is enforced, and whether every
  entry point passes through it (SEC-AUTHZ-01).
- **Decision compliance** — code vs. accepted ADRs (ARCH-DEC-02).
- **Testability** — can the core rules be tested without UI/DB (DES-SRP-02, ARCH-BND-04)?
- **Extensibility** — variation points sit where variation is evidenced; extension contracts are
  versioned and contract-tested; third-party code is isolated (ARCH-EXT-01..03, DES-EXT-01).
- **Distribution** — each feature's consistency-versus-availability choice is stated (ARCH-DIST-01).
- **Scalability** — request handlers are stateless; contention points are known; shared capacity is
  protected (PERF-SCALE-01..03).
- **Data** — a system of record per fact; a migration strategy compatible with the deployment model
  (DATA-MODEL-01, DATA-MIG-01); details in `database-review.md`.
- **Security by design** — new entry points and trust boundaries have been threat-modelled
  (SEC-DESIGN-01, `threat-modeling.md`).

## 5. Over- and under-engineering
Both are findings (ARCH-FIT-01). Check signals:
- **Over**: more deployables than teams; interfaces with one implementation and no seam need;
  pass-through layers; identical DTO/entity/model trios; generic frameworks inside the app;
  configuration nobody sets; distributed transactions for a single-team app (DES-SIMP-02/03).
- **Under**: rules in controllers/views/templates/SQL; no seams for testing; one module that every
  change touches; rising lead time and regressions in one area; no boundary around volatile
  third parties.
For each, state the cost being paid (evidence) — not just the shape.

## 6. Options, trade-offs, recommendation
- Present at least two options, one of which is "do less" (keep, or a partial step).
- For each: what it fixes, what it costs (build effort, run cost, cognitive load, migration risk),
  what it makes harder later, and how reversible it is.
- Recommend the smallest option that handles the named forces, with an incremental migration path
  (strangler, branch by abstraction, module extraction before service extraction) and the first
  concrete step.
- Be explicit about uncertainty: forecasts of change are guesses; prefer reversible moves when the
  forecast is weak (S2 Ch.15, Keeping Options Open).

For every existing ADR that bears on the question, state whether it still holds and what would
trigger revisiting it (for example, "valid while invoices stay immutable — revisit before adding
invoice editing").

## 7. Record decisions (ADR)
For each significant decision (structure, NFRs, dependencies, interfaces, construction techniques
— S4 scope), draft an ADR with `../../assets/templates/adr.md`: context with options considered,
the decision in imperative form ("We use…"), positive and negative consequences, compliance
checks, status Proposed. Accepted ADRs are immutable; changes supersede them (ARCH-DEC-02).

## 8. Reviewing a proposal
Questions that usually decide it:
1. Which concrete problem does it solve, with what evidence (incidents, lead time, scaling data)?
2. Could a smaller change solve 80% of it (module boundaries, an index, a cache, one extracted
   service)?
3. What does it cost to operate (deployments, monitoring, on-call, data consistency work)?
4. What is the migration path, and can it stop halfway with value delivered?
5. Who owns each new part?
6. What gets harder (debugging, transactions, local development, onboarding)?
7. What would make us reverse it, and how expensive would that be?
Answer with a recommendation, its conditions, and the first step — not a lecture on patterns.

## 9. Running an architecture review
When the user asks for a review session or a design gate rather than an opinion (ARCH-REV-01,
S8 §9.1):
- Say which kind it is: **discovery** (early, broad — is any requirement category missing:
  security, privacy, cost, operability?), **deep-dive** (one high-risk area with specialists) or
  **retrospective** (after the system has run — which assumptions failed?).
- Walk the ranked quality-attribute scenarios through the views; spend the time on irreversible
  decisions: data model, trust boundaries, concurrency, external dependencies.
- Close every concern with a disposition — fix now, accept with a reason, or investigate by a date
  — and an owner. Record accepted risks and decisions as ADRs.
