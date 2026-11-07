# Principle registry, part 2 (P-54 – P-68)

Continuation of `principles.md`, added in version 1.1: quality attributes and architecture,
extensibility, data, verification and validation, secure design and the supply chain,
scalability and API design, and AI-assisted engineering. Same fields and conventions: **stmt**,
**src** (with provenance label), **intent**, **adopted**, **rules**, **limits**, **rel**.

## Contents
- I. Architecture, quality attributes and extensibility: P-54 – P-56
- J. Data: P-57 – P-59
- K. Verification and validation: P-60 – P-63
- L. Secure design and supply chain: P-64 – P-65
- M. Scalability and API design: P-66 – P-67
- N. AI-assisted engineering: P-68

---

## I. Architecture, quality attributes and extensibility

### P-54 Architecture serves measurable quality requirements
- stmt: Structure is chosen to satisfy the most important quality requirements; those requirements must be measurable, and since no design maximises every quality, the trade-offs are recorded.
- src: S8 §6.1.1 (architecture as the significant decisions chosen to satisfy the most important quality requirements), §6.1.3, §6.1.4 (quality-attribute scenarios), §3.1.3 (fit criteria) · direct
- intent: Make architecture arguable with evidence instead of taste.
- adopted: Every structural recommendation names the quality-attribute scenario it serves (ARCH-QA-01); scenarios with response measures become architecture tests where practical; reviews walk them (ARCH-REV-01).
- rules: ARCH-QA-01, ARCH-REV-01, ARCH-DOC-01, TEST-VV-01
- limits: Early products may not know their numbers; state provisional scenarios as assumptions and revisit them.
- rel: P-22, P-25, P-60

### P-55 Design each module around a secret
- stmt: Decompose so that each module hides a decision likely to change behind a narrow interface; the interface is a promise, the implementation a secret.
- src: S8 §6.2.1 (The Modularity Principle, after Parnas), §6.2.3 (Design Guidelines for Modules) · direct
- intent: Localise the cost of the changes you expect.
- adopted: Judge an interface by what callers must know about the implementation; prefer small interfaces and copies over exposed internals. Information hiding and dependency inversion together keep volatile decisions out of callers.
- rules: DES-HIDE-01, DES-COH-01, DES-OBJ-02, DES-API-01
- limits: Hiding everything is indirection without payoff (P-25); hide the decisions likely to change.
- rel: P-18, P-16, P-25

### P-56 Make expected changes cheap without paying for unused flexibility
- stmt: Extensibility is an investment: put explicit variation points where change is evidenced, and keep the rest concrete.
- src: S8 §7.7 (the unifying principle of the pattern chapter), §7.6.1–7.6.3 (commonality and variability; mispredicted axes; invest only where change is likely), §6.2.3 (design for expected changes, not all changes); S2 Ch.17 (Plugin Architecture); X16 · synthesized
- intent: Extensibility where it pays, simplicity elsewhere.
- adopted: A variation point needs evidence (roadmap, history, contract) and becomes a published contract once others implement it (ARCH-EXT-01, ARCH-EXT-02); third-party extensions are isolated (ARCH-EXT-03); feature flags are variation points with an end date (DLV-FLAG-01).
- rules: ARCH-EXT-01, ARCH-EXT-02, ARCH-EXT-03, DES-OCP-01, DES-EXT-01, DLV-FLAG-01
- limits: Forecasts are uncertain; a partial boundary (P-25) is the hedge when the axis is plausible but unproven.
- rel: P-13, P-25, P-67

## J. Data

### P-57 The system of record enforces integrity; everything else is derived
- stmt: Each fact has one authoritative store that enforces its integrity for every writer; caches, replicas, indexes and read models are derived from it and may lag.
- src: S8 §7.2.1 (Shared-Data Pattern — the store enforces consistency, concurrency control, integrity and durability), §14.4.3 (PostgreSQL as the system of record; the cache is not the source of truth) · direct
- intent: Correct data under concurrency and failure.
- adopted: Integrity constraints live in the database (T-20); one owner per fact; derived stores are rebuildable, and the features that read them acknowledge their lag; money and permissions keep an append-only history.
- rules: DATA-SCHEMA-01, DATA-MODEL-01, DATA-MODEL-02, DATA-REPL-01, PERF-CACHE-01, DATA-AUDIT-01
- limits: Analytical and sharded systems relax some constraints by design; document the replacement mechanism.
- rel: P-58, P-24

### P-58 Consistency is a per-feature requirement
- stmt: Under partitions a replicated system must give up some consistency or some availability; which one is a requirements decision made per feature — and the same reasoning applies to isolation levels inside one database.
- src: S8 §14.1.6 (CAP — choose per feature); X11 (isolation levels in the engine manuals) · synthesized
- intent: No implicit, accidental consistency model.
- adopted: Money, stock and permissions get consistency or explicit compensation; feeds and counters get bounded staleness; every multi-row invariant names the isolation or constraint it relies on.
- rules: ARCH-DIST-01, DATA-TXN-02, DATA-TXN-03, DATA-REPL-01, DES-DOM-02
- limits: —
- rel: P-57, P-44

### P-59 Data outlives code: formats evolve compatibly, and migrations are deployments
- stmt: Data written by one version is read by the next (and, during rollout, by the previous one), so schema changes and stored formats evolve in compatible steps that are rehearsed, timed and recoverable.
- src: S8 §14.3.2 (shared schemas stay compatible with both versions), §14.3.4 (irreversible migrations; roll-forward as a safety property); X15 Item 74 (a serialized form becomes part of the exported API) · synthesized
- intent: Deploys and data changes without outages or corruption.
- adopted: Expand → migrate → contract; migrations tested in CI and rehearsed on production-sized data; persisted formats versioned; backups proven by restores; batch jobs restartable.
- rules: DATA-MIG-01, DATA-MIG-02, DATA-MIG-03, DATA-EVOL-01, DATA-BACKUP-01, DATA-BATCH-01
- limits: Single-instance tools with maintenance windows can accept simpler migrations — state the window.
- rel: P-57, P-49

## K. Verification and validation

### P-60 Verification and validation answer different questions
- stmt: Verification asks whether we built the product right (against its specification); validation asks whether we built the right product (against the need). Both are planned, and requirements trace to the tests that verify them.
- src: S8 §10.2.3 (after Boehm), §3.4.1 (acceptance criteria seed tests), §3.4.4 (Tracing Requirements to Tests) · direct
- intent: Catch wrong requirements as well as wrong code.
- adopted: Acceptance criteria become executable tests that carry the requirement's key; quality requirements get fit criteria; what tests cannot validate goes to users (demo, UAT, beta).
- rules: TEST-VV-01, ARCH-QA-01, TEST-STRAT-01
- limits: Full traceability matrices pay off in regulated domains; elsewhere a lightweight chain of executable artifacts is enough (S8 §3.4.4).
- rel: P-54, P-61

### P-61 A test is only as good as its oracle, and is trusted only once seen failing
- stmt: A test compares behaviour with an oracle; an oracle taken from the code under test pins bugs instead of catching them, and a test never seen failing may be unable to fail.
- src: S8 §10.1.4 (Test Oracles), §10.1.5 (Mutation Testing — never trust a test you have never seen fail), §13.2.7 (generated tests and the oracle problem) · direct
- intent: Tests that actually detect defects.
- adopted: Expected values come from specifications, worked examples or independent computation; properties, round-trips and differential checks where exact values are impractical; each new test is seen failing; critical code is mutation-tested.
- rules: TEST-ORACLE-01, TEST-MUT-01, TEST-PROP-01, TEST-REG-01, AGT-SELF-01
- limits: Human-judgement oracles (UI, prose) stay necessary but slow; keep them for what automation cannot judge.
- rel: P-36, P-62, P-68

### P-62 Choose tests by explicit criteria; coverage is a floor, not a ceiling
- stmt: Test inputs are selected by stated criteria — black-box (partitions, boundaries, combinations) and white-box (statement, branch, MC/DC) — and adequacy is judged against them; coverage shows what never ran, not what was verified.
- src: S8 §10.1.2 (Test Selection), §10.1.3 (Test Adequacy), §10.3–10.6 (coverage criteria; equivalence classes; boundaries; combinatorial testing) · direct
- intent: Make "enough testing" a checkable question.
- adopted: Table-driven cases name their classes and boundaries; stronger criteria only for critical decisions; coverage as an alarm, never a target (T-22); fuzzing for parsers of untrusted input.
- rules: TEST-DESIGN-01, TEST-BND-01, TEST-COV-01, TEST-COV-02, TEST-FUZZ-01
- limits: Pairwise and coverage criteria are heuristics; no criterion proves correctness (S8 §10.7).
- rel: P-36, P-38, P-61

### P-63 Measure from goals, pair the metrics, and state the uncertainty
- stmt: Choose metrics from goals (Goal–Question–Metric), pair each with a counter-metric so it resists gaming, normalise by exposure, and never report a change without its spread or interval.
- src: S8 §12.1.2 (Goodhart's law; counter-metrics), §12.1.3 (GQM), §12.4.4 (normalise by exposure), §12.8 (confidence intervals), §14.7.2 (paired DORA metrics resist gaming) · direct
- intent: Numbers that inform decisions instead of distorting them.
- adopted: Quality ratings cite evidence, not single numbers; performance and quality claims carry dispersion; delivery is judged by outcome metrics, not activity.
- rules: TEST-PERF-01, PERF-MEAS-01, TEST-COV-01, TD-PRI-01
- limits: Small samples rarely support strong claims; say when the data cannot.
- rel: P-47, P-36

## L. Secure design and supply chain

### P-64 Security assumes an adversary and is designed in
- stmt: Security is a lifecycle property: threats are modelled from the attacker's goals before building, the default path is the secure one, and controls are layered so that they fail independently.
- src: S8 Ch.11 preface (security assumes an adversary; it is not a phase), §11.1.3 (defence in depth; shifting left), §11.2.3 (insecure design), §11.5 (secure defaults; least privilege), §3.7 (attack trees; STRIDE); X23 · synthesized
- intent: Prevent the design flaws that no code review or scanner can find.
- adopted: Threat-model features that add assets, entry points or trust boundaries (SEC-DESIGN-01); least privilege for every identity (SEC-PRIV-01); secure defaults (SEC-CONF-01); code-level review still follows P-40 – P-43.
- rules: SEC-DESIGN-01, SEC-PRIV-01, SEC-CONF-01, SEC-AI-01, ARCH-EXT-03
- limits: Threat models go stale — revisit them when the design changes. Proportionality applies: a ranked table of the top threats is usually enough.
- rel: P-39, P-40, P-65

### P-65 Every dependency and build step extends trust
- stmt: Third-party code, its maintainers and the build system are part of the attack surface: vet dependencies before adoption, control what enters the build, sign what leaves it, and keep watching what runs.
- src: S8 §11.4 (The Software Supply Chain — scale, weak links, Log4Shell and xz-utils, continuous verification on Day 0/1/2, SBOM, SLSA, Sigstore, Scorecard), §14.6.2–14.6.3 (supply-chain defences; gate placement) · direct
- intent: Deliberate, revocable trust instead of implicit trust.
- adopted: Dependency vetting and SBOMs (SEC-SUPPLY-01), build integrity and provenance (SEC-SUPPLY-02), gates where they can answer (SEC-GATE-01), advisories only from current tools (SEC-DEP-01).
- rules: SEC-SUPPLY-01, SEC-SUPPLY-02, SEC-GATE-01, SEC-DEP-01, DLV-DEPS-01, DLV-DEPS-02
- limits: Vetting every transitive package deeply is expensive (S8 §11.4.4); prioritise by exposure and criticality.
- rel: P-51, P-64

## M. Scalability and API design

### P-66 Scalability is bounded by the serial part and by shared capacity
- stmt: Adding resources speeds up only the parallel part of the work; stateless handlers, small critical sections and protected shared capacity let throughput grow with resources.
- src: X17 Ch.11 (Amdahl's law; lock contention); S8 §14.1.2 (horizontal scaling requires stateless services; noisy neighbours), §7.2.1 (the shared store as bottleneck) · synthesized
- intent: Grow by adding capacity, not by rewriting.
- adopted: Measure contention before redesigning; stateless services; per-tenant limits and bulkheads; scale the data tier last and deliberately.
- rules: PERF-SCALE-01, PERF-SCALE-02, PERF-SCALE-03, DATA-SCALE-01, DATA-CONN-01
- limits: Most systems never need extreme scale; apply in proportion to measured or contracted load (P-47).
- rel: P-47, P-44

### P-67 Published interfaces are forever: keep them small and design them for their callers
- stmt: Every public element — an API, an extension point, a serialized form — becomes a commitment; keep the surface small, make misuse hard, document the contract, and either design for extension or prohibit it.
- src: X15 Items 13, 17, 18, 40, 44, 74 · extension
- intent: Evolve implementations freely behind small, stable contracts.
- adopted: Applies to library and module APIs (DES-API-01), class extension (DES-EXT-01), plug-in contracts (ARCH-EXT-02), stored formats (DATA-EVOL-01) and thread-safety guarantees (REL-CONC-04); HTTP contracts follow API-CONTRACT-01.
- rules: DES-API-01, DES-EXT-01, ARCH-EXT-02, DATA-EVOL-01, API-CONTRACT-01, REL-CONC-04
- limits: Internal code whose callers all live in one repository can change interfaces freely with automated refactoring; the principle bites at team, repository and customer boundaries.
- rel: P-14, P-56, P-59

## N. AI-assisted engineering

### P-68 AI raises the value of verification: humans own intent, oracle and acceptance
- stmt: AI moves the bottleneck from producing code to deciding what to build and proving it works; generated code and tests are hypotheses until checked against independent evidence, and a separate, sceptical check beats self-assessment.
- src: S8 §13.1 (what AI changes and what it doesn't; the productivity paradox), §13.2.6–13.2.8 (review, testing and security), §13.7.2 (the generator and the evaluator), §13.8 (principles for the AI-augmented engineer) · direct
- intent: Keep accountability and evidence when code is cheap.
- adopted: Claude applies the evidence rules to its own output with extra force — tests derived from requirements and seen failing, self-review of the full diff, no claimed verification without execution — and leaves expensive-to-change architectural decisions to people, with options and trade-offs laid out.
- rules: AGT-EVID-01, AGT-SELF-01, TEST-ORACLE-01, TEST-MUT-01, SEC-AI-01
- limits: Evidence on AI productivity and quality is early and partly vendor-reported (S8 §13.3); treat specific figures cautiously.
- rel: P-36, P-61
