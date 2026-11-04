# Principle registry

The top layer of the knowledge model (see `knowledge-model.md`). Each principle records where
it comes from, what its author intended, how this skill interprets it, which rules implement
it, and where it stops applying. Rules live in `rules/`; source IDs are defined in `sources.md`.

Fields: **stmt** (the principle, paraphrased) · **src** (source and provenance label) ·
**intent** (original purpose) · **adopted** (this skill's interpretation) · **rules** (implementing
rules) · **limits** (applicability and known limitations) · **rel** (related principles).

## Contents
- A. Code craft: P-01 – P-11
- B. Design: P-12 – P-18
- C. Components and architecture: P-19 – P-29
- D. Technical debt: P-30 – P-34
- E. Testing and analysis: P-35 – P-38
- F. Security: P-39 – P-43
- G. Runtime qualities: P-44 – P-47
- H. Delivery and practice: P-48 – P-53

---

## A. Code craft

### P-01 Optimise for the reader
- stmt: Code is read far more often than it is written, so clarity for the next reader is the main cost driver.
- src: S1 Ch.1 (We Are Authors) — reading-to-writing ratio is described as well over ten to one · direct
- intent: Make writing effort pay off in cheaper reading and changing.
- adopted: "Is it easy to read *and* safe to change?" is the tie-breaker for local code decisions, but never outranks correctness, security, or explicit constraints.
- rules: CODE-NAME-01, CODE-FUNC-01, CODE-STRUCT-01
- limits: Readability is reader-relative; judge against the team's ecosystem idioms, not a universal taste.
- rel: P-02, P-03, P-53

### P-02 Names reveal intent
- stmt: Names should tell why something exists, what it does, and how it is used, at the right level of abstraction, using one word per concept.
- src: S1 Ch.2 (Meaningful Names); S1 Ch.17 N1–N7 · direct
- intent: Remove the need for mental mapping and comments.
- adopted: Domain names in domain code, solution-domain names in technical code; consistency with existing vocabulary beats a locally "better" synonym.
- rules: CODE-NAME-01 … CODE-NAME-05
- limits: S1's advice against encodings and interface prefixes is Java-centric; ecosystems such as .NET prefix interfaces with `I` by convention (P-53 wins).
- rel: P-01, P-53

### P-03 Small functions that do one thing at one level of abstraction
- stmt: A function should do one thing, at one level of abstraction, and read top-down (stepdown rule).
- src: S1 Ch.3 (Small!; Do One Thing; One Level of Abstraction per Function); S1 G30, G34 · direct
- intent: Each function becomes nameable, testable, and replaceable.
- adopted: Size is a *signal*; the criterion is single purpose and single abstraction level. S1's "hardly ever 20 lines" is not a threshold this skill enforces.
- rules: CODE-FUNC-01 … CODE-FUNC-05
- limits: Over-extraction hurts locality (readers jump between many tiny functions). Go and C idioms favour longer linear functions with early returns; numeric kernels favour cohesion over decomposition.
- rel: P-01, P-12

### P-04 No hidden side effects; separate commands from queries
- stmt: A function either changes state or answers a question, and does nothing its name hides.
- src: S1 Ch.3 (Have No Side Effects; Command Query Separation); S1 N7, G31 · direct
- intent: Callers can reason locally; temporal couplings become explicit.
- adopted: Treat hidden mutation, I/O inside "getters", and order-dependent calls without enforcement as defects-in-waiting.
- rules: CODE-FUNC-03, CODE-FUNC-04, REL-CONS-03
- limits: Fluent builders and some framework APIs return values from commands by design.
- rel: P-03, P-44

### P-05 Comments explain why, not what
- stmt: Prefer expressing intent in code; keep comments for intent, warnings, legal notes, public API docs and non-obvious reasons; delete commented-out code.
- src: S1 Ch.4 (Good Comments; Bad Comments); S1 C1–C5 · direct
- intent: Comments rot; code is the source of truth.
- adopted: Missing "why" for a surprising decision is a finding just as much as a redundant "what" comment.
- rules: CODE-CMNT-01 … CODE-CMNT-03
- limits: Regulated domains, public SDKs and security-sensitive code legitimately need more documentation.
- rel: P-01, P-29

### P-06 Error handling is its own concern and errors are never silent
- stmt: Separate the happy path from error handling, never swallow errors, add context, and do not use null as an error channel.
- src: S1 Ch.7 (Error Handling); S5 Error Handling chapter; S6 §4.8 (WSTG-ERRH-01/02) · synthesized
- intent: Failures stay visible and diagnosable without leaking internals.
- adopted: Follow the ecosystem's error model (exceptions, `error` returns, `Result` types). S1's "use unchecked exceptions" is Java-specific advice from 2008, not a universal rule.
- rules: CODE-ERR-01 … CODE-ERR-04, SEC-ERR-01, REL-ERR-01
- limits: In Go, explicit `if err != nil` handling is idiomatic; in Rust, `Result` with `?`. Don't import exception-centric advice.
- rel: P-42, P-44

### P-07 Own your boundaries with third-party code
- stmt: Wrap third-party and framework APIs at a boundary you control; learn them with learning tests.
- src: S1 Ch.8 (Boundaries; Learning Tests Are Better Than Free); S2 Ch.32 (Frameworks Are Details) · synthesized
- intent: Limit the blast radius of vendor change.
- adopted: Wrap where the dependency is volatile, widely used, or awkward; don't wrap stable standard libraries or a framework you have deliberately chosen as the application's foundation.
- rules: CODE-BND-01, ARCH-DET-03, DLV-DEPS-01
- limits: Wrapping everything is overengineering (see P-25).
- rel: P-24, P-25

### P-08 Remove true duplication; tolerate accidental duplication
- stmt: Duplicate knowledge that changes together must be unified; code that merely looks alike but changes for different reasons should stay separate.
- src: S1 G5 and Ch.12 (No Duplication); S2 Ch.16 (Duplication — true vs. accidental) · synthesized
- intent: One change, one place — without coupling unrelated actors.
- adopted: Before merging two similar blocks, ask "do they change for the same reason, at the same rate?" (S2 Ch.16). Only then extract.
- rules: CODE-DUP-01, CODE-DUP-02, DES-SRP-01
- limits: Test code may repeat setup for readability; cross-service duplication is often cheaper than shared libraries.
- rel: P-12, P-19

### P-09 Objects hide data; data structures expose it — know which you are writing
- stmt: Objects expose behaviour and hide data; data structures expose data with no behaviour. Hybrids get the worst of both. Avoid navigating through strangers (Law of Demeter).
- src: S1 Ch.6 (Data/Object Anti-Symmetry; The Law of Demeter; Hybrids; Data Transfer Objects; Active Record); S1 G14, G36 · direct
- intent: Choose deliberately which kind of change (new types vs. new operations) is cheap.
- adopted: DTOs, records and Active Record models are legitimate data structures; flag only hybrids that leak invariants or chains that couple callers to deep structure.
- rules: DES-COH-02, DES-COH-03, DES-OBJ-01
- limits: Fluent APIs and builders are not Demeter violations; functional code favours data plus functions.
- rel: P-18

### P-10 Leave the code a little better — within the change's scope
- stmt: Each change should leave touched code slightly cleaner (Boy Scout Rule).
- src: S1 Ch.1 (The Boy Scout Rule) · direct; scoped by S3 Ch.1, Principle 5 · synthesized
- intent: Continuous, cheap improvement instead of grand redesigns (S1 Ch.1, The Grand Redesign in the Sky).
- adopted: Improve only what the change touches, keep improvements behaviour-preserving and in separate commits, and never let clean-up dominate a functional change's diff.
- rules: AGT-MIN-01, AGT-MIN-02, TD-DEC-03
- limits: Drive-by refactors in unrelated files inflate review cost and regression risk.
- rel: P-48, P-32

### P-11 Simple design
- stmt: In priority order: runs all the tests; contains no duplication; expresses intent; minimises classes and methods.
- src: S1 Ch.12 (Simple Design Rules 1–4) · direct
- intent: Emergent good design through tests and refactoring.
- adopted: The fourth rule is the explicit counterweight to over-abstraction: fewer moving parts wins when the other three are satisfied.
- rules: DES-SIMP-01 … DES-SIMP-04, TEST-STRAT-01
- limits: Says nothing about architecture-level boundaries; combine with P-25.
- rel: P-25, P-35

## B. Design

### P-12 Single Responsibility: one actor, one reason to change
- stmt: A module should be responsible to one actor (one source of change requests).
- src: S2 Ch.7 (SRP); S1 Ch.10 (The Single Responsibility Principle; Cohesion) · direct
- intent: Changes requested by one stakeholder must not break another's behaviour.
- adopted: Identify actors (accounting, operations, UI, compliance…) before judging a class; size alone does not establish an SRP violation.
- rules: DES-SRP-01, DES-SRP-02
- limits: Over-splitting creates scattered logic; small cohesive modules serving one actor are fine even when long.
- rel: P-08, P-18

### P-13 Open–Closed
- stmt: Extend behaviour by adding code, not by editing stable, tested code — where change is expected.
- src: S2 Ch.8 (OCP); S1 G23 ("ONE SWITCH" rule) · direct
- intent: Protect high-level policy from churn in low-level details.
- adopted: Introduce extension points when a second or third variation actually appears, or a variation axis is documented; not speculatively.
- rules: DES-OCP-01, CODE-CPLX-03
- limits: Every extension point is indirection; speculative ones are overengineering (P-25).
- rel: P-16, P-25

### P-14 Liskov Substitution
- stmt: Subtypes must honour the contracts of their supertypes so that callers need no type checks.
- src: S2 Ch.9 (LSP) · direct
- intent: Substitutability keeps polymorphism safe; violations leak `instanceof`/special cases into callers.
- adopted: Applies to interfaces, REST/API versions and plug-ins, not only classes (S2 Ch.9 applies it to architecture).
- rules: DES-LSP-01
- limits: —
- rel: P-13

### P-15 Interface Segregation
- stmt: Don't force clients to depend on things they don't use.
- src: S2 Ch.10 (ISP) · direct
- intent: Avoid recompilation/redeploy ripple and accidental coupling.
- adopted: In dynamic languages the cost is conceptual rather than compile-time; still avoid "fat" dependencies that drag in unneeded transitive dependencies.
- rules: DES-ISP-01
- limits: —
- rel: P-16

### P-16 Dependency Inversion
- stmt: High-level policy should depend on abstractions; volatile concrete details depend on (implement) those abstractions.
- src: S2 Ch.11 (DIP) · direct
- intent: Point source dependencies away from volatile details.
- adopted: Invert dependencies on *volatile* details (I/O, vendors, frameworks); depending on stable concretions (standard library, value types) is fine — S2 Ch.11 says so.
- rules: DES-DIP-01, ARCH-DEP-01
- limits: Interfaces with one implementation and no test or variation need are ceremony.
- rel: P-23, P-21

### P-17 Separate constructing a system from using it
- stmt: Object graph construction (wiring, configuration) belongs in a dedicated place (`main`, composition root, DI container), not scattered in business logic.
- src: S1 Ch.11 (Separate Constructing a System from Using It); S2 Ch.26 (The Main Component) · direct
- intent: Business code stays testable and unaware of concrete choices.
- adopted: Use the framework's DI where one exists (Spring, Laravel container, NestJS); in Go/Python, explicit constructor wiring in `main` is idiomatic.
- rules: DES-DI-01, DES-DI-02
- limits: Service-locator lookups in domain code violate it even when a container is present.
- rel: P-16

### P-18 High cohesion, low coupling, organised for change
- stmt: Keep together what changes together; isolate code from things likely to change.
- src: S1 Ch.10 (Cohesion; Organizing for Change; Isolating from Change); S1 G13, G14, G17 · direct
- intent: Localise the impact of change.
- adopted: Judge coupling by co-change evidence (git history) where available, not only by static structure.
- rules: DES-COH-01 … DES-COH-03
- limits: Metrics such as LCOM are noisy; use as prompts for inspection.
- rel: P-12, P-19

## C. Components and architecture

### P-19 Component cohesion is a tension (REP, CCP, CRP)
- stmt: Group for reuse/release (REP), for common closure (CCP), and to avoid needless dependencies (CRP); the balance shifts as a project matures.
- src: S2 Ch.13 (The Reuse/Release Equivalence, Common Closure, Common Reuse Principles; Tension Diagram) · direct
- intent: Component boundaries follow change and reuse, not taxonomy.
- adopted: Early projects lean towards CCP (developability); mature, widely reused libraries lean towards REP/CRP.
- rules: ARCH-COMP-01
- limits: —
- rel: P-18, P-20

### P-20 Acyclic dependencies
- stmt: The component dependency graph must have no cycles.
- src: S2 Ch.14 (The Acyclic Dependencies Principle) · direct
- intent: Independent build, test and release; no "morning after" integration pain.
- adopted: Cycles between packages/modules are a finding at any scale; break with DIP or by extracting a new component.
- rules: ARCH-COMP-02 (automated: `scripts/deps.py`)
- limits: Cycles inside one cohesive package are less severe than cycles across components or layers.
- rel: P-16, P-21

### P-21 Depend in the direction of stability; stable things should be abstract
- stmt: Depend towards more stable components (SDP); a component's abstractness should match its stability (SAP).
- src: S2 Ch.14 (SDP; SAP; Main Sequence; Zone of Pain) · direct
- intent: Volatile code must be easy to change; hard-to-change code must be extensible.
- adopted: Use instability `I = Ce/(Ca+Ce)` from `scripts/deps.py` as a prompt; concrete, heavily-depended-on, *volatile* modules are the real "zone of pain" — S2 notes stable concretions like a standard library are harmless.
- rules: ARCH-COMP-03
- limits: Metrics depend on how you draw component boundaries; dynamic languages blur them.
- rel: P-20, P-16

### P-22 Structure is a value, not just behaviour
- stmt: Software has two values — behaviour and structure (changeability); the second is what architecture protects and what stakeholders under-weight.
- src: S2 Ch.2 (A Tale of Two Values); S2 Ch.15 (What Is Architecture?) · direct
- intent: Fight for structure when it is genuinely at risk.
- adopted: Argue structural work in terms of cost of future change (P-31), not purity.
- rules: ARCH-FIT-01, TD-PRI-01
- limits: —
- rel: P-31

### P-23 The Dependency Rule
- stmt: Source dependencies point inward, toward higher-level policy; inner code knows nothing about outer layers.
- src: S2 Ch.22 (The Dependency Rule); S2 Ch.19 (Policy and Level) · direct
- intent: Business rules survive changes to UI, database and frameworks.
- adopted: Enforce it on the boundaries the system actually has. S2 Ch.22 itself says the circles are schematic; the number of layers is a design choice.
- rules: ARCH-DEP-01 … ARCH-DEP-03
- limits: For thin CRUD systems the "policy" is small; strict layering may cost more than it protects (P-25).
- rel: P-16, P-24

### P-24 Details stay at the edge; keep options open
- stmt: Databases, the web, frameworks and devices are details; defer binding to them and keep them out of policy.
- src: S2 Ch.15 (Keeping Options Open), Ch.30–32; S1 Ch.11 (Optimize Decision Making) · direct
- intent: Decide late with more information; keep decisions reversible.
- adopted: Keep *business rules* free of detail-specific types where rules are rich. Where the framework *is* the chosen platform (Laravel, Rails, Django), work with it and isolate only the volatile or rule-heavy parts.
- rules: ARCH-DET-01 … ARCH-DET-03
- limits: Pretending a deeply embedded framework is a detail can double the code for little gain.
- rel: P-23, P-25

### P-25 Boundaries cost money: draw them where forces justify them
- stmt: Full architectural boundaries are expensive; omitting them is expensive to fix later. Choose full, partial, or no boundary based on anticipated change.
- src: S2 Ch.17 (Which Lines Do You Draw, and When?), Ch.24 (Partial Boundaries), Ch.25 (Conclusion — weighs YAGNI against late boundaries) · synthesized with S1 Ch.12 rule 4
- intent: Neither over- nor under-engineer.
- adopted: Overengineering is a defect class. Require a named force (volatility, separate actors, testability, deployment need) for every boundary, abstraction layer, or service split.
- rules: ARCH-FIT-01 … ARCH-FIT-03, DES-SIMP-02, DES-SIMP-03
- limits: Forecasting change is uncertain; when in doubt, prefer partial boundaries (S2 Ch.24) that can be completed later.
- rel: P-11, P-27, P-33

### P-26 Architecture should scream the domain; encapsulate with the compiler
- stmt: Top-level structure should reveal use cases, not frameworks; package by feature/component and use visibility to enforce boundaries.
- src: S2 Ch.21 (Screaming Architecture); S2 Ch.34 (Package by Layer / Feature / Ports and Adapters / Component; Organization versus Encapsulation) · direct
- intent: Make the system's purpose and boundaries obvious and enforceable.
- adopted: Prefer enforcing boundaries with language visibility, module systems, or architecture tests over convention alone (S2 Ch.34's main point).
- rules: ARCH-BND-02, ARCH-BND-03
- limits: Framework conventions (Rails/Laravel directories) may legitimately dominate the top level.
- rel: P-23

### P-27 Services are a deployment option, not an architecture
- stmt: Splitting into services decouples deployment and operation, not necessarily change; services can still be coupled by shared data and cross-cutting features.
- src: S2 Ch.16 (Decoupling Modes; Independent Deployability), Ch.18 (Boundary Anatomy), Ch.27 (Services: Great and Small; The Kitty Problem) · direct
- intent: Avoid distributed monoliths.
- adopted: Default to a modular monolith; split when independent deployability, scaling or team autonomy needs are concrete *and* operational maturity exists.
- rules: ARCH-STYLE-01 … ARCH-STYLE-03
- limits: —
- rel: P-25

### P-28 Make boundaries testable (Humble Object, test boundary)
- stmt: Push hard-to-test behaviour into thin "humble" objects; give tests a stable API so they don't couple to volatile structure.
- src: S2 Ch.23 (The Humble Object Pattern), Ch.28 (Tests as System Components; Design for Testability; The Testing API) · direct
- intent: Tests that survive refactoring; logic testable without UI/DB.
- adopted: Fragile tests that break on every structural change are test debt.
- rules: TEST-BEH-01, TEST-BEH-02, ARCH-BND-04
- limits: —
- rel: P-35

### P-29 Record architecturally significant decisions
- stmt: Capture the context, decision and consequences of significant decisions in immutable, superseded-not-edited records.
- src: S4 (ADR process; Scope; ADR contents; Best practices) · direct
- intent: Avoid the anti-patterns of no decision, unjustified decisions, and forgotten decisions (S4).
- adopted: Accepted ADRs are architectural constraints for reviews (rule level `constraint`); non-compliant legacy code is handled as TD tasks or gradual updates (S4).
- rules: ARCH-DEC-01 … ARCH-DEC-03
- limits: Recording trivia in ADRs creates noise; reserve for structure, NFRs, dependencies, interfaces, construction techniques (S4 scope).
- rel: P-25, P-32

## D. Technical debt

### P-30 Technical debt is an expedient construct that makes future change costly
- stmt: TD is a design or implementation construct, expedient short-term, that raises the cost of future change; a contingent liability affecting internal qualities, chiefly maintainability and evolvability.
- src: S3 Ch.1 (definition) · direct
- intent: Make TD concrete, inventoried and measurable.
- adopted: The skill only labels a finding "technical debt" if it impedes change; defects, vulnerabilities and external quality problems are classified separately (S3 Ch.1 explicitly excludes defects from TD).
- rules: TD-CLS-01, TD-CLS-02
- limits: —
- rel: P-31, P-32

### P-31 Principal and interest
- stmt: Principal is the cost of the better solution now; interest is recurring (lost productivity, defects) and accruing (new code built on not-quite-right code).
- src: S3 Ch.1 / Preface ("Technical debt items… principal and interest") · direct
- intent: Reason about TD economically.
- adopted: Prioritise by interest actually being paid (change frequency × friction), not by how ugly code looks.
- rules: TD-PRI-01, TD-PRI-02
- limits: S3 Principle 8: no absolute measure exists; estimates are ordinal.
- rel: P-33

### P-32 TD is not the same as bad quality, and must trace to the system
- stmt: All systems have TD; TD must trace to concrete artifacts; TD is not synonymous with bad quality; all code matters (build scripts, tests, infrastructure).
- src: S3 Ch.1, Principles 3, 4, 5, 7 (statements) · direct
- intent: Avoid both denial and moralising.
- adopted: Each TD item names an artifact and a consequence; harmless imperfections in stable code are not reported as debt.
- rules: TD-ID-01, TD-ID-02, TD-CLS-03
- limits: Principles 3–9 are known here only by their statements (S3 sample).
- rel: P-30

### P-33 TD depends on future evolution and has no absolute measure
- stmt: Whether something is debt, and how much, depends on how the system will evolve; neither principal nor interest has an absolute measure.
- src: S3 Ch.1, Principles 8, 9 (statements); S3 Principle 2 (no interest → probably not actual debt) · direct
- intent: Context decides.
- adopted: Code that will not change (or will be retired) carries little debt however messy; ask for, or state assumptions about, the roadmap.
- rules: TD-PRI-02, TD-DEC-02
- limits: —
- rel: P-25, P-31

### P-34 Architecture debt costs the most
- stmt: Architectural TD has the highest cost of ownership.
- src: S3 Ch.1, Principle 6 (statement) · direct
- intent: Look beyond code smells.
- adopted: Rank structural issues (dependency direction, boundaries, data ownership) above local smells of comparable interest.
- rules: TD-PRI-03
- limits: —
- rel: P-22, P-23

## E. Testing and analysis

### P-35 Tests are first-class code
- stmt: Tests deserve the same care as production code: readable, fast, independent, repeatable, self-validating, timely (FIRST); one concept per test.
- src: S1 Ch.9 (Keeping Tests Clean; Clean Tests; Single Concept per Test; F.I.R.S.T.); S1 T1–T9 · direct
- intent: Tests enable change; dirty tests become a liability.
- adopted: "Single concept per test" replaces "one assert per test" (S1 Ch.9 itself prefers it).
- rules: TEST-UNIT-01 … TEST-UNIT-03, TEST-ISO-01
- limits: —
- rel: P-28, P-36

### P-36 Testing shows presence, not absence, of bugs
- stmt: Tests and reviews can reveal defects but cannot prove their absence.
- src: S7 §1.2 (Approximative Answers, citing Dijkstra); S6 §2.2 (There is No Silver Bullet) · synthesized
- intent: Calibrated claims.
- adopted: Never declare code correct or secure because tests pass or a review found nothing; report what was checked.
- rules: AGT-EVID-01, AGT-EVID-03, TEST-COV-01
- limits: —
- rel: P-37, P-38

### P-37 Analysis tools approximate: know which way they err
- stmt: Interesting program properties are undecidable (Rice's theorem), so analysers approximate; "sound" depends on purpose — verification tools over-report (false positives), bug finders may under-report.
- src: S7 Preface, §1.2, §1.3, §12.3 · direct
- intent: Use tools for what they guarantee.
- adopted: Treat linter/SAST/scanner output — including this skill's own scripts — as leads with stated error direction, to be confirmed by tracing data flow or by test.
- rules: AGT-EVID-02, SEC-PROC-03, DLV-SA-01
- limits: —
- rel: P-36

### P-38 Test strategy is a portfolio
- stmt: Most checks should be fast and isolated; fewer, slower tests cover integration and end-to-end paths.
- src: X5 (test pyramid) · extension; supported by S1 T9 (tests should be fast) and S2 Ch.28
- intent: Fast feedback with adequate integration confidence.
- adopted: Shape follows the architecture — a thin-logic CRUD service may rightly have more integration than unit tests ("honeycomb"); judge by feedback speed and defect escape, not by ratio.
- rules: TEST-STRAT-01, TEST-STRAT-02, TEST-CONTRACT-01
- limits: —
- rel: P-35

## F. Security

### P-39 Security is part of every lifecycle phase
- stmt: Build security into requirements, design, development, deployment and operations; test early and often; no single technique suffices.
- src: S6 §2.2 (Principles of Testing), §2.8 (Balanced Approach), Ch.3 (Phases 1–5); S5 Introduction and Methodology (S-SDLC) · direct
- intent: Cheaper, more complete defence.
- adopted: Security checks appear in every workflow of this skill, not just the security review.
- rules: SEC-PROC-01, SEC-PROC-02
- limits: —
- rel: P-40

### P-40 Risk-based review: attack surface, trust boundaries, threats
- stmt: Focus review on entry points, data flows across trust boundaries, and threats ranked by likelihood and impact.
- src: S5 Methodology (Determining the Attack Surface; threat modelling; STRIDE; DREAD and risk factors); S6 §2.5 (Threat Modeling); S6 §4.1.6 (Identify Application Entry Points) · direct
- intent: Spend review time where risk concentrates.
- adopted: Every security review starts with an entry-point and trust-boundary inventory; findings carry likelihood × impact.
- rules: SEC-PROC-01, SEC-PROC-02
- limits: S5 notes DREAD is subjective; prefer qualitative likelihood/impact with stated assumptions.
- rel: P-39

### P-41 Never trust input; keep code and data separate
- stmt: Validate input at trust boundaries (allow-lists), encode output for its context, and use parameterised interfaces so data cannot become code.
- src: S5 A1 Injection, A3 XSS; S6 §4.7 (WSTG-INPV-01…19), §4.11 (client-side) · direct
- intent: Eliminate injection classes structurally.
- adopted: Parameterisation and contextual encoding are mandatory; validation is defence in depth, never the only control against injection.
- rules: SEC-VAL-01, SEC-INJ-01 … SEC-INJ-04, SEC-OUT-01
- limits: —
- rel: P-40

### P-42 Authorise every request for every object and function
- stmt: Authentication says who; authorisation must be checked server-side for each function and each object accessed.
- src: S5 A2, A4, A7; S6 §4.4–4.6 (WSTG-ATHN, ATHZ, SESS) · direct
- intent: Prevent IDOR, privilege escalation, forced browsing.
- adopted: A missing ownership or role check on a data-access path is a blocker-class finding once confirmed.
- rules: SEC-AUTHZ-01 … SEC-AUTHZ-03, SEC-AUTHN-01 … SEC-AUTHN-03, SEC-SESS-01
- limits: —
- rel: P-41

### P-43 Fail securely and protect sensitive data
- stmt: Errors fail closed and reveal nothing internal; secrets and sensitive data are protected in storage, transit and logs; components with known vulnerabilities are managed.
- src: S5 A5, A6, A9, Error Handling, Reviewing Logging Code; S6 §4.2, §4.8, §4.9 · direct
- intent: Limit damage and information leakage.
- adopted: Secrets in source control are always blocker-class, even in "test" config committed to the repo.
- rules: SEC-ERR-01, SEC-SECRET-01, SEC-DATA-01, SEC-DATA-02, SEC-CRYPTO-01, SEC-DEP-01, SEC-CONF-01
- limits: —
- rel: P-06

## G. Runtime qualities

### P-44 Concurrency needs defensive design
- stmt: Keep concurrency code separate, limit shared data, prefer copies and independent workers, keep critical sections small, and test with stress and variation.
- src: S1 Ch.13 (Concurrency Defense Principles; Keep Synchronized Sections Small; Testing Threaded Code); S5 Race Conditions · direct
- intent: Concurrency bugs are non-deterministic and expensive.
- adopted: Treat unexplained intermittent test failures as candidate concurrency bugs (S1 Ch.13).
- rules: REL-CONC-01 … REL-CONC-03
- limits: —
- rel: P-04

### P-45 Design for failure at every remote call
- stmt: Remote calls fail and stall: bound them with timeouts, retry only idempotent operations with backoff, and isolate failures.
- src: X6 · extension; S1 Ch.7 (Define the Normal Flow) for separation of failure paths
- intent: One slow dependency must not take the system down.
- adopted: Missing timeouts on network calls are a reliability finding in any service code.
- rules: REL-TIME-01, REL-TIME-02, REL-CONS-02
- limits: —
- rel: P-46

### P-46 Make the system observable
- stmt: Failures should be detectable and diagnosable from logs, metrics and traces without leaking sensitive data.
- src: S5 Reviewing Logging Code · direct (logging hygiene); observability practice · extension
- intent: Operate what you build.
- adopted: Structured logs with correlation IDs; no secrets or personal data in logs.
- rules: REL-OBS-01, REL-OBS-02, SEC-DATA-02
- limits: —
- rel: P-43

### P-47 Measure before optimising
- stmt: Optimise where measurement shows a bottleneck; algorithmic and I/O-pattern problems (N+1, unbounded queries) are the usual real costs.
- src: X12 · extension; S1 G26 (Be Precise) for precision in data types
- intent: Avoid complexity without payoff.
- adopted: Flag obvious I/O anti-patterns without benchmarks, but label micro-optimisation claims as unmeasured.
- rules: PERF-MEAS-01, PERF-IO-01, PERF-IO-02, PERF-ALGO-01
- limits: Hard real-time and embedded contexts differ (see S2 Ch.29).
- rel: P-25

## H. Delivery and practice

### P-48 Refactor in small, behaviour-preserving steps under test
- stmt: Change structure without changing behaviour, incrementally, keeping tests green at each step.
- src: S1 Ch.14 (On Incrementalism), Ch.16 (First, Make It Work; Then Make It Right), Ch.12 · direct; X3, X4 · extension (catalogue, characterization tests)
- intent: Improve design without regressions.
- adopted: No safety net → build one first (characterization tests) or reduce the step size; separate refactoring commits from behaviour changes.
- rules: TEST-REG-02, AGT-MIN-02, TD-DEC-03; procedure in `workflows/refactoring.md`
- limits: —
- rel: P-10, P-35

### P-49 One-step build, one-step test, automated gates
- stmt: Building and running all tests should each take one trivial command; automate them in CI.
- src: S1 E1, E2 · direct; CI practice · extension
- intent: Remove friction that discourages verification.
- adopted: A repository whose tests can't be run with one documented command has delivery debt.
- rules: DLV-BUILD-01, DLV-CI-01
- limits: —
- rel: P-50

### P-50 Use static analysis as an automated reviewer
- stmt: Linters, type checkers and SAST catch classes of issues cheaply; tune them and triage results.
- src: S5 Methodology (static code analysis, false positives, tool selection); S7 Preface · synthesized
- intent: Humans review what tools cannot.
- adopted: Don't hand-review what a configured linter enforces; do review what tools are known to miss (business logic, authorisation).
- rules: DLV-SA-01, DLV-SA-02
- limits: —
- rel: P-37

### P-51 Manage dependencies as liabilities
- stmt: Every dependency adds attack surface and maintenance; pin, update and audit them.
- src: S5 A9 (Using Components With Known Vulnerabilities) · direct; supply-chain practice · extension
- intent: —
- adopted: Lockfiles committed; known-vulnerable versions flagged by tool output, not from memory.
- rules: DLV-DEPS-01 … DLV-DEPS-03, SEC-DEP-01
- limits: Claude's knowledge of CVEs is dated; always defer to a current scanner or advisory database.
- rel: P-43

### P-52 Review proportionately and humanely
- stmt: Review with a clear purpose, domain knowledge, and respect; don't invent faults; don't rush; agree how conflicts resolve.
- src: S5 Appendix (Code Review Do's and Don'ts); S5 Methodology (inspection rate as duration estimate, not quality measure) · direct
- intent: Reviews that people trust and keep doing.
- adopted: A review may conclude "no significant issues". Proportionality: review depth scales with risk (see SKILL.md triage).
- rules: REV-CONDUCT-01 … REV-CONDUCT-04
- limits: —
- rel: P-53

### P-53 Follow standard and team conventions
- stmt: Follow the ecosystem's and team's conventions consistently; consistency beats personal preference.
- src: S1 G24 (Follow Standard Conventions), N3 (Use Standard Nomenclature), Ch.5 (Team Rules), G11 (Inconsistency) · direct
- intent: Reduce cognitive load across a codebase.
- adopted: Identify language, framework and local conventions *before* applying any generic rule; generic rules yield to them unless safety or correctness is at stake.
- rules: AGT-CONV-01, AGT-CONV-02, CODE-STRUCT-02
- limits: A convention that causes vulnerabilities or defects is raised, not followed silently.
- rel: P-02, P-06
