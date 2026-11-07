# Technical debt rules (TD-*)

How to identify, classify, prioritise and decide on technical debt. Field meanings:
`index.md`. Procedure and scoring rubric: `../workflows/tech-debt.md`. Grounded in S3 —
note that only its Chapter 1 is in the corpus, so the prioritisation mechanics below are
`synthesized` from S3's definitions and principles.

Areas: CLS · ID · PRI · DEC

### TD-CLS-01 · Classify a finding before calling it technical debt
- level: strong | severity: — | provenance: direct
- sources: S3 Ch.1 (definition — TD is limited to internal qualities; defects and external quality deficiencies are excluded to avoid muddying the water)
- why: Lumping bugs, vulnerabilities and debt together hides urgency (a vulnerability is not "debt to repay later") and inflates the debt backlog.
- signals: TD registers containing crash bugs and CVEs; "tech debt" used for missing features.
- fix: Assign a finding type first (`../knowledge-model.md` §4.2): defect, vulnerability, reliability-risk, performance, tech-debt, architecture-risk, test-gap, trade-off, legacy-constraint, imperfection, question.
- related: TD-CLS-02, TD-CLS-03

### TD-CLS-02 · Separate intentional trade-offs and legacy constraints from debt
- level: strong | severity: — | provenance: synthesized
- sources: S3 Ch.1 (deliberate, known shortcuts in the case stories; TD as a strategic design choice); S4 (decisions with recorded consequences)
- why: A documented, still-valid compromise (e.g. denormalised read model for latency, a monolith by choice) is a decision, not a mess; "fixing" it destroys value.
- signals: The code has an ADR, comment or ticket explaining the compromise and its trigger; constraints imposed by an external contract or a migration in progress.
- fix: Label as `trade-off` or `legacy-constraint`; check the recorded trigger condition — if it has fired (e.g. traffic outgrew the shortcut), reclassify as debt.
- related: TD-DEC-01, ARCH-DEC-02

### TD-CLS-03 · Harmless imperfections are not debt
- level: strong | severity: — | provenance: direct
- sources: S3 Ch.1, Principle 2 (no interest → probably not actual debt), Principle 5 (TD is not synonymous with bad quality), Principle 9 (depends on future evolution)
- why: Ugly code that nobody changes and that causes no defects costs nothing; reporting it wastes attention and erodes trust in the review.
- signals: Old, stable, rarely-changed modules with poor style but no incidents; code scheduled for retirement.
- fix: Omit, or mention once as `imperfection` (nit). Record "write off" for code being retired.
- related: TD-PRI-02, REV-CONDUCT-02

### TD-ID-01 · Every debt item traces to artifacts and consequences
- level: strong | severity: — | provenance: direct
- sources: S3 Ch.1, Principle 4 (technical debt must trace to the system); S3 Ch.1 (technical debt items: artifacts, causes, consequences)
- why: "The code is messy" can't be planned or verified; "`BillingService` (2,400 lines) mixes four actors; every pricing change touches it and caused 3 regressions this quarter" can.
- signals: Debt items without file/module, without observable consequence, or without a remediation idea.
- fix: Record with `../../assets/templates/td-item.md`: name, location/artifacts, type, cause (if known), consequences (interest evidence), remediation approach, estimated principal, decision, owner, trigger.
- related: TD-PRI-01, TD-DEC-01

### TD-ID-02 · Look for debt beyond source code
- level: strong | severity: — | provenance: direct
- sources: S3 Ch.1, Principle 7 (all code matters!); S3 index (build and integration debt; testing debt; infrastructure)
- why: Build scripts, CI pipelines, test suites, infrastructure code, schemas and documentation accrue debt that slows every change.
- signals: Flaky or slow pipelines, manual deployment steps, test suites nobody trusts, copy-pasted infrastructure definitions, outdated runbooks.
- fix: Include these artifacts in assessments and the debt register.
- related: DLV-CI-02, TEST-ISO-02

### TD-PRI-01 · Prioritise by interest being paid, not by ugliness
- level: strong | severity: — | provenance: synthesized
- sources: S3 Ch.1 / Preface (principal and interest; recurring and accruing interest); X9 (hotspots — change frequency × complexity)
- why: Debt in code that changes often (and breaks often) costs money every sprint; equally bad code that never changes costs nothing.
- signals: Prioritisation by size or smell count alone.
- fix: Estimate interest from evidence: change frequency (git churn), defect history, friction per change (complexity, coupling, test gaps), number of dependants, and roadmap relevance. `scripts/hotspots.py` ranks churn × complexity.
- related: TD-PRI-02, TD-PRI-03

### TD-PRI-02 · Weigh the system's expected evolution
- level: strong | severity: — | provenance: direct
- sources: S3 Ch.1, Principle 8 (no absolute measure of principal or interest), Principle 9 (technical debt depends on the future evolution of the system)
- why: Whether a structure is debt depends on what will be built next; refactoring an area the roadmap will not touch has little payoff.
- signals: Recommendations made without knowing the roadmap.
- fix: Ask about (or state assumptions on) planned changes, lifetime and scale; raise priority of debt on the path of upcoming work; lower it for code slated for replacement.
- related: TD-PRI-01, ARCH-FIT-01

### TD-PRI-03 · Weight architecture debt above local smells of similar interest
- level: strong | severity: — | provenance: direct
- sources: S3 Ch.1, Principle 6 (architecture technical debt has the highest cost of ownership)
- why: Structural problems (wrong boundaries, dependency direction, shared databases) tax every change and get costlier to fix as code accretes around them.
- signals: Assessments listing many naming/formatting issues while ignoring cyclic dependencies or a shared-database integration.
- fix: Rank structural items higher at comparable interest; plan them as incremental migrations with ADRs.
- related: ARCH-DEP-01, ARCH-COMP-02, ARCH-STYLE-02

### TD-DEC-01 · Intentional debt is recorded with reason, owner and repayment trigger
- level: strong | severity: minor | provenance: synthesized
- sources: S3 Ch.1 (make TD visible; add TD items to the backlog alongside features and defects); S4 (record decisions and consequences); S8 §15.5 (deliberate debt is acceptable when tracked and serviced; inadvertent debt from inexperience, shifting requirements or crunch; keep a debt register)
- why: Unrecorded shortcuts become accidental debt as soon as their author leaves.
- signals: `// TODO: hack for release` without ticket; known shortcuts living only in people's heads.
- fix: Debt item or ADR stating the shortcut, why, the expected cost, and the trigger for repayment (date, metric, or event).
- verify: The shortcut appears in the TD register or an ADR with owner and trigger.
- related: TD-ID-01, ARCH-DEC-01, CODE-CMNT-01

### TD-DEC-02 · Decide explicitly per item: fix now, schedule, opportunistic, accept, or write off
- level: strong | severity: — | provenance: synthesized
- sources: S3 Ch.1 (TD as an investment decision; principal vs. interest); P-31, P-33
- why: Without a decision, debt lists grow until they're ignored.
- signals: Debt backlogs with no status other than "open".
- fix: Use the matrix in `../workflows/tech-debt.md` (interest × cost, with overrides for risk and dependencies); re-evaluate when context changes.
- related: TD-PRI-01, TD-DEC-03

### TD-DEC-03 · Repay incrementally, alongside feature work; avoid grand rewrites
- level: strong | severity: — | provenance: synthesized
- sources: S1 Ch.1 (The Grand Redesign in the Sky; The Boy Scout Rule); S1 Ch.14 (On Incrementalism); S3 Ch.1; S8 §15.6 (Strangler Fig versus Big-Bang Rewrite — a rewrite concentrates risk, discards embedded knowledge and validates only at the end), §15.5 (refactoring is the repayment mechanism; pay down principal where interest is paid)
- why: Rewrites stall feature delivery, chase a moving target and often recreate the old problems; small repayments on the paths you're changing compound.
- signals: Proposals to "rebuild it properly" without a migration path; refactoring tickets that never fit a sprint.
- fix: Strangler-style migration, branch by abstraction, refactor-as-you-go within touched areas; carve large items into independently valuable steps.
- related: AGT-MIN-02, TEST-REG-02

### TD-DEC-04 · Recommend expensive refactoring only with a cost–benefit case
- level: strong | severity: — | provenance: synthesized
- sources: S3 Ch.1 (principal vs. interest); S2 Ch.2 (A Tale of Two Values — argue structure in business terms)
- why: Unjustified refactoring advice is ignored, or worse, followed at the expense of delivery.
- signals: "Should be refactored" with no statement of what it costs now, what the fix costs, or what risk it carries.
- fix: State interest (with evidence), principal (rough size), risk (safety net, blast radius), and the smallest valuable first step.
- related: TD-PRI-01, ARCH-FIT-01
