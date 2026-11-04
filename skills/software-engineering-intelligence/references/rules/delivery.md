# Delivery rules (DLV-*)

Build, CI, static analysis, dependencies, configuration, release, documentation, ownership.
Field meanings: `index.md`.

Areas: BUILD · CI · SA · DEPS · CFG · REL · DOC · OWN

### DLV-BUILD-01 · One command builds; one command runs all tests
- level: strong | severity: minor–major | provenance: direct
- sources: S1 E1 (Build Requires More Than One Step), E2 (Tests Require More Than One Step)
- why: Multi-step, tribal-knowledge builds discourage running tests and break onboarding and CI parity.
- signals: README with long manual setup; tests requiring hand-started services; scripts that only work on one developer's machine.
- fix: A documented `make test` / `./gradlew test` / `npm test` / `composer test` / `go test ./...` / `pytest`, with containers for dependencies.
- verify: A fresh clone builds and tests with the documented commands.
- related: DLV-CI-01, DLV-DOC-01

### DLV-CI-01 · Every change passes automated build, test and analysis gates before merge
- level: strong | severity: major | provenance: synthesized
- sources: S5 Code Review Do's and Don'ts (SAST in the development flow); S4 Appendix example (protected branches, merge requests with approvals); S6 §2.10
- why: Gates that run on every change catch regressions when they are cheapest to fix.
- signals: No CI; CI not required for merge; tests or linters allowed to fail; direct pushes to main.
- fix: CI pipeline running build, tests, linters/type checks, secret and dependency scanning; required status checks and reviews on protected branches.
- verify: Branch protection requires the CI checks; a failing test blocks merge.
- related: DLV-SA-01, DLV-CI-02, ARCH-BND-02

### DLV-CI-02 · Pipelines give fast, trustworthy feedback
- level: contextual | severity: minor | provenance: extension
- sources: X14; S1 T9
- why: Slow or flaky pipelines get bypassed.
- signals: Pipelines over ~15–20 minutes for routine changes; frequent reruns; unpinned tool versions causing random failures.
- fix: Order checks cheap → expensive; cache dependencies; parallelise; fix flakiness (TEST-ISO-02); pin tool versions.
- related: TEST-ISO-02, DLV-DEPS-02

### DLV-SA-01 · Static analysis is configured, tuned and triaged
- level: strong | severity: minor | provenance: synthesized
- sources: S5 Methodology (static code analysis — benefits, false positives, tool selection); S7 Preface, §1.2
- why: Tools check whole codebases consistently, but untuned tools drown teams in false positives and get ignored.
- signals: No linter/type checker; thousands of ignored warnings; blanket suppressions; rules disabled in CI only.
- fix: Adopt the ecosystem's standard tools; baseline existing warnings and fail only on new ones; review suppressions (CODE-STRUCT-05).
- verify: CI runs the analysers; new warnings fail the build; suppressions carry reasons.
- related: DLV-SA-02, AGT-EVID-02, CODE-STRUCT-05

### DLV-SA-02 · Type-checking strictness proportionate to the codebase
- level: contextual | severity: minor | provenance: convention
- sources: X11
- why: Strict type checking prevents whole classes of runtime errors cheaply, especially for null handling.
- signals: TypeScript without `strict`; untyped Python in a large codebase; PHPStan/Psalm absent or at level 0; heavy `any`/`mixed`.
- fix: Enable strictness for new modules first; ratchet levels up.
- related: CODE-ERR-04, DLV-SA-01

### DLV-DEPS-01 · Each dependency is justified, maintained and licence-compatible
- level: strong | severity: minor–major | provenance: synthesized
- sources: S5 How to Use the Code Review Guide (integration reviews — open-source libraries may bring insecure dependencies); S5 A9
- why: Dependencies add attack surface, upgrade work and licence obligations.
- signals: Packages added for trivial functions; unmaintained packages (no releases for years, archived repos); copyleft licences in proprietary distribution without review; two libraries for one job.
- fix: Prefer the standard library or existing dependencies; check maintenance and licence before adding; note new dependencies in the PR description.
- verify: New dependencies are listed in the change description with purpose, maintenance status and licence.
- related: SEC-DEP-01, ARCH-FIT-03, AGT-CONV-02

### DLV-DEPS-02 · Builds are reproducible: lockfiles committed, versions pinned
- level: strong | severity: minor–major | provenance: extension
- sources: X14
- why: Floating versions make builds non-reproducible and open the door to supply-chain attacks.
- signals: Missing lockfiles (`package-lock.json`, `poetry.lock`/`uv.lock`, `composer.lock`, `go.sum`, Gradle lockfiles); `latest` image tags; CI actions referenced by mutable tags.
- fix: Commit lockfiles for applications; pin images by digest where practical; pin CI actions to versions or SHAs.
- verify: Lockfile present and used in CI (e.g. npm ci, composer install from lock, go mod verify).
- related: DLV-DEPS-03, SEC-DEP-01

### DLV-DEPS-03 · Dependencies are updated continuously
- level: contextual | severity: minor–major | provenance: extension
- sources: X14; S5 A9
- why: Small, frequent upgrades are cheap; multi-year jumps are projects.
- signals: Framework versions past end-of-support; no automated update tooling.
- fix: Dependabot/Renovate with grouped minor updates; scheduled major upgrades.
- related: DLV-DEPS-02, TD-PRI-01

### DLV-CFG-01 · Configuration lives outside code and is validated at startup
- level: strong | severity: minor–major | provenance: synthesized
- sources: X7 (config in the environment); S1 G35
- why: Environment-specific values compiled into code force rebuilds per environment and leak secrets.
- signals: URLs/credentials/feature switches hard-coded; config read lazily deep in code and failing at first use; different code paths per environment.
- fix: Load configuration once from environment/config service into a typed object; fail fast on missing/invalid values; secrets from a secret manager.
- verify: Starting with a missing/invalid required setting fails fast with a clear message.
- related: SEC-SECRET-01, CODE-STRUCT-04, SEC-CONF-01

### DLV-REL-01 · Risky changes are reversible
- level: contextual | severity: major | provenance: extension
- sources: X14
- why: Fast rollback limits incident impact; irreversible deploys turn bugs into outages.
- signals: Deploys coupling code and destructive migrations; no rollback procedure; big-bang releases of large features.
- fix: Backward-compatible deploys (expand/contract), feature flags with cleanup plans, canary/staged rollouts, documented rollback.
- related: DATA-MIG-01, AGT-SAFE-01

### DLV-DOC-01 · Essential documentation exists and is findable
- level: strong | severity: minor | provenance: synthesized
- sources: S4 (Best practices — store ADRs centrally and reference them from the project's main documentation page); X14
- why: Onboarding, operations and reviews depend on knowing purpose, setup, architecture and decisions.
- signals: README missing setup/test/run instructions; no architecture overview; no ADR index; operational runbooks absent for production services.
- fix: README (purpose, setup, run, test, deploy), short architecture overview, ADR log, runbooks for on-call.
- verify: A newcomer can set up, run and test from the README alone.
- related: ARCH-DEC-01, DLV-BUILD-01

### DLV-DOC-02 · Documentation changes with the code it describes
- level: strong | severity: minor | provenance: synthesized
- sources: S1 C2 (Obsolete Comment) by analogy; X14
- why: Docs that drift become misinformation.
- signals: Behaviour changes in a diff with stale docs, examples or API schemas left untouched.
- fix: Update docs in the same change; keep docs next to code (`docs/`, docstrings, schema files).
- verify: The diff updates docs/schemas/examples affected by the behaviour change.
- related: CODE-CMNT-02, API-CONTRACT-02

### DLV-OWN-01 · Critical areas have clear owners
- level: contextual | severity: minor | provenance: extension
- sources: X14
- why: Unowned code accumulates debt and slows incident response.
- signals: No CODEOWNERS/maintainers for core modules; knowledge concentrated in one person (bus factor) — visible in git authorship.
- fix: CODEOWNERS for critical paths; pair/rotate on single-owner modules.
- related: TD-PRI-01
