# Changelog

## 1.3.0 — 2026-11-24

Focus: test engineering (which tests a change needs, on which database engines, and how results
are reported) and database engineering (modelling, data types, engine differences, storage
internals and query performance), general-purpose across stacks and engines.

### Sources
- **X24** Hernandez, *Database Design for Mere Mortals*; **X25** Petrov, *Database Internals*;
  **X26** Winand, *SQL Performance Explained* (and its free web edition, use-the-index-luke.com);
  **X27** the engines' official documentation (PostgreSQL, MySQL, MariaDB, Oracle, SQL Server,
  SQLite). The books were not available as files; they are cited by part or chapter title as
  knowledge references — nothing is quoted or reproduced. The engine behaviour summarised in
  `references/data/engines.md` was checked against X27 on 2026-11-24; cells that could not be
  checked are marked †.

### Testing knowledge (new `references/testing/`)
- `levels.md` — fourteen test levels plus smoke: purpose, what each verifies and does not, what it
  depends on, cost, tooling and when to select it; regression as a purpose, not a level.
- `selection.md` — choosing tests from a change: inputs, an eight-step procedure, the classes
  Required / Recommended / Optional / Not necessary, change types, widening signals, safety nets,
  anti-patterns and worked examples.
- `database-matrix.md` — test categories A (no database), B (the production engine), C (a specific
  engine) and D (several engines, focused data-access suite); verified engine differences that
  break stand-ins; no default engine, no SQLite-first rule.
- `execution.md` — optimisation techniques, a stage policy (local, pull request, main, nightly,
  release, production gate), flaky-test diagnosis, duplicated execution, measuring cost, reporting
  rules and the verdict vocabulary.

### Database knowledge (new `references/data/`)
- `modeling.md` — levels of modelling, entities, relationships and cardinality, keys, functional
  dependencies and normal forms, when to denormalise and when to stop normalising, history and
  lifecycle, where integrity rules live, a review checklist and a worked example.
- `types.md` — a decision framework for numeric, character, temporal, boolean and enumerated,
  JSON, UUID and binary data, and practical cases (money, FX and interest rates, account numbers,
  national IDs, branch codes, phone and postal codes, transaction references, quantities,
  timestamps, statuses, large text, JSON configuration), with the database-to-application mapping.
- `engines.md` — a verified matrix of PostgreSQL, Oracle, MySQL/MariaDB, SQL Server and SQLite
  behaviour, thirteen portability traps and the documentation used.
- `internals.md` — pages, heap versus clustered tables, B-trees, LSM trees, WAL and durability,
  MVCC per engine, locks and deadlocks, replication, and the review question each mechanism raises.
- `performance.md` — plans and how to read them, composite index order, SARGable predicates,
  joins, pagination, N+1, and evidence labels (expected, estimated plan, measured plan, measured
  end to end).

### Rules: 255 → 270
- Testing: TEST-SEL-01 (select tests from a change's impact and justify omissions), TEST-DATA-02
  (database tests on the engines their behaviour depends on — no more, no fewer), TEST-COST-01
  (remove duplicated execution, not unique coverage), TEST-REPORT-01 (a report accounts for the
  plan: what ran, what did not, where, what remains unverified).
- Data: DATA-MODEL-03 (relationships with enforced keys), DATA-MODEL-04 (facts as of their time —
  a snapshot is not redundancy), DATA-MODEL-05 (stop normalising where no anomaly is removed),
  DATA-KEY-01 (deliberate keys), DATA-IDX-02 (predicates the index can use), DATA-TYPE-02..05
  (exact numbers with scale, identifiers as strings, temporal types by meaning, one meaning for
  NULL), DATA-DUR-01 (durability settings match acceptable loss), DATA-PORT-01 (portability is
  designed and tested).
- Extended: DATA-SCHEMA-01, DATA-IDX-01 (composite order, foreign-key indexes per engine),
  DATA-TXN-01 (MVCC and long transactions), DATA-TYPE-01, TEST-DATA-01, TEST-ISO-02.
- The two largest rule files were split along their natural seams so each loads cheaply:
  `testing.md` (foundations) and new `testing-execution.md` (selection, engines, environments,
  skipped tests, cost, reporting); new `data-design.md` (schema, modelling, keys, types, indexes,
  portability) and `data-api.md` (operations and API). Rule IDs are unchanged.

### Principles, tensions, workflows and templates
- Principles 70 → 74: P-71 (test selection is risk reasoning), P-72 (a schema states what data
  means), P-73 (know the mechanism, then trust the plan), P-74 (portability is designed and tested).
- Tensions T-31 – T-34: run everything vs. select per change; real engine vs. embedded stand-in;
  random UUID keys vs. B-tree locality; "the database is a detail" vs. engine features.
- The knowledge model's context gate records database engines and versions (UNKNOWN until
  established) and gains a section on explaining a recommendation (concept, why, alternatives,
  trade-offs, failure modes, when the answer changes, example, engine differences, provenance).
- Rewritten workflows `test-strategy.md` (including tests for a specific change and reporting a
  run) and `database-review.md` (modelling, types, engines, performance evidence, teaching);
  code-review, implementation and repository-assessment workflows, the SQL guide and the quality
  model link the new procedures.
- New template `test-execution-report.md` (changed scope, risk, selected, executed, skipped or not
  run, engines, duration, failures, remaining risks, verdict).

### Scripts (10 → 13)
- New `test_impact.py`: classifies changed files, finds tests that name or import them (Python,
  JavaScript/TypeScript, Java/Kotlin, Go, PHP), flags engine-specific SQL in changed lines and
  money, security and concurrency signals, and proposes test groups with a class and a reason.
- New `test_report.py`: JUnit XML and `go test -json` results — executed, failed, skipped and unrun
  tests, flaky tests across runs, duplicates, slowest tests and suites, and with `--plan` the
  planned groups that did not run and the verdict that follows. Refuses XML with DOCTYPE or ENTITY
  declarations.
- New `schema_lint.py`: data-type, key and relationship leads from SQL DDL and Laravel, Django,
  SQLAlchemy, Prisma and JPA models, with engine-specific severity.
- `repo_survey.py` reports the database engines referenced by configuration, drivers, containers
  and tests (UNKNOWN when none), and notes stand-ins such as H2 or SQLite used for a different
  production engine; secret values are never printed.
- `migration_lint.py` gains Oracle, SQL Server, SQLite and MariaDB: offline index builds, implicit
  commits, SQLite's ALTER TABLE limits, SQL Server `ALTER COLUMN`, `sp_rename` and lock waits. For
  MySQL it adds two info-level leads: DDL on existing tables without `lock_wait_timeout` (a
  metadata-lock wait queues every later query on the table) and several DDL statements in one
  migration (each commits on its own). PATH may now be the migrations folder itself or a single
  file, and a SQL file named with `--files` is analysed wherever it lives. Compared with 1.2.0 on a
  22-file corpus: PostgreSQL output is unchanged except one fix (the `no-lock-timeout` lead now
  points at the first DDL statement when that statement starts the file; it pointed at the
  second); MySQL output keeps every 1.2.0 lead and adds only the two info-level leads.
- `test_smells.py` reports duplicated test bodies (TEST-COST-01).
- `repo_survey.py` also reads engines from CI build matrices (`db: [postgres:16, mysql:8.0]`) as
  test engines; `schema_lint.py` accepts a single file and advises DATE for calendar dates stored
  in a MySQL TIMESTAMP.
- `validate_skill.py` checks paths into `testing/` and `data/` and the new template's headings.

### Tests
- New stdlib unit tests in `tests/` (repository root, not shipped in the ZIP): database detection,
  test impact, test reports, schema and migration linting, test smells — 77 tests,
  `python3 -m unittest discover -s tests`.

### Evaluations (14 → 24)
- Ten new cases, positive and negative: `test-selection-mixed-pr`, `engine-specific-repository-change`
  (Oracle in production, H2 in tests), `test-report-verdict`, `ci-flaky-duplication`,
  `mysql-large-table-precision`, `banking-schema-types-review`, `index-and-query-performance`,
  `normalization-tradeoffs`, `cross-database-migration` (MySQL → PostgreSQL) and
  `concurrency-durability-internals`. Each was run once by a separate agent and graded by another:
  70/76 criteria passed (batch 1: 38/39, batch 2: 32/37). Method, scores, criteria revisions,
  coverage of the requested scenarios and limitations are in `validation/VALIDATION.md`.
- After the runs, guidance was tightened where answers fell short: place every suite in a stage
  when cutting CI time; fix a flaky test now when the cause is known, as an alternative to
  quarantine; the primary and replica cost of an online MySQL index build; keep the mechanism in a
  verdict on an engine the user proposes; look for a local engine before relying on documentation
  alone. These changes were not re-run behaviourally.

### Independent review
- A separate reviewer found 1 blocker, 6 major and 8 minor problems in the scripts and engine
  facts; all were fixed with tests before release. The blocker: `test_report.py` counted a Required
  group whose tests were all skipped as covered. Also fixed: flaky tests inferred from runs that
  were not the same code and environment, engine evidence from fixture folders and from every
  driver Laravel lists, development dependencies counted as production engines, substring matches
  for security and money signals, Oracle decimal and `ONLINE` handling, and four engine facts.

## 1.2.0 — 2026-11-07

Focus: software design patterns — judging, choosing, refactoring and reviewing them in real code,
including recommending no pattern when that is the better design.

### Sources
- **S10** — Refactoring.Guru, *Design Patterns* catalog (refactoring.guru/design-patterns): the
  authority for the catalog and its classification (22 patterns: 5 creational, 7 structural,
  10 behavioral) and for pattern content. "All rights reserved"; its content-usage policy allows
  short citations with a link and does not cover summarising — the skill paraphrases and links.
- **S9** — the supplied *Dive Into Design Patterns* PDF, which turned out to be a **Bookey summary**
  of the book, not the book: 36 chapter summaries, eight of them cut off (6, 12, 15, 18, 21, 24,
  30, 36), plus unverified commentary that is not used. Every chapter was reviewed; where it
  differs from S10, S10 is followed and the difference recorded (T-28).
- Specific points cite X2 (GoF), X3 (Fowler, *Refactoring*), X15 (*Effective Java*) and X16
  (*Head First Design Patterns*); framework mechanisms cite their documentation (X11).

### Design-pattern knowledge (new `references/patterns/`, 27 files)
- `index.md` — catalog, how to use the files, supplementary patterns (Interpreter as a GoF-only
  pattern, T-29; dependency injection and composition root; Service Locator; Null Object;
  Specification; Repository; pipes and filters), sources and differences.
- One file per pattern with the same fields — intent, a real-problem example, problem, context,
  motivation, applicability, structure, participants, collaborations, implementation
  considerations, consequences, benefits, trade-offs, costs, known misuses, when not to use,
  related patterns, common combinations, refactoring opportunities, testing, security, language
  and framework considerations, provenance.
- `selection.md` — the six questions (force, no-pattern solution, when simpler suffices, added
  cost, what gets easier and harder, when to revisit), forces → candidates, baselines, cost model,
  composition versus inheritance, relations to Clean Code, SOLID, architecture, smells,
  refactoring, debt, dependencies, testing and extensibility, revisit triggers.
- `comparisons.md` — 15 look-alike pairs by intent, structure, responsibility, when to use, cost
  and signs of the wrong choice.
- `anti-patterns.md` — overuse, unnecessary abstractions and interfaces, excessive inheritance,
  singleton abuse, factory proliferation, excessive indirection, premature extensibility,
  pattern-driven design: signals, costs, consequences, fixes.
- `frameworks.md` — Java/Spring, PHP/Laravel, Go, Python and TypeScript/React mechanisms described
  by what they do, with the checks to make before naming a pattern.

### Workflow and template
- New workflow `design-patterns.md`: pattern assessment, pattern selection, pattern-based
  refactoring and pattern implementation review, each with input, steps, decision criteria,
  required evidence and output.
- New template `pattern-decision.md` (problem and force, options including the no-pattern baseline
  and the closest look-alike, decision, consequences and cost, verification, revisit triggers).

### Rules: 249 → 255
- DES-PAT-03 (compare with the simplest alternative and the look-alikes), DES-PAT-04 (identify a
  pattern by intent and participants, not names), DES-PAT-05 (explicit, ordered, loudly failing
  wiring), DES-PAT-06 (the language's idiom first), TEST-CONTRACT-02 (one contract suite for every
  implementation), SEC-DESIGN-02 (security wrappers cover every path and fail closed).
- DES-PAT-01, DES-PAT-02 and DES-DI-02 gain S9/S10 sources and singleton signals. No rule per
  pattern: pattern-specific guidance lives in the pattern files.

### Principles, tensions and integration
- Principles 68 → 70: P-69 (a pattern is a named trade-off — start from the problem), P-70 (favour
  composition; inherit only for substitutable is-a).
- Tensions T-24 – T-30: classic Singleton vs. container-managed single instance; Template Method
  vs. callbacks and template-callback; factory terminology; framework vocabulary vs. catalog names;
  S9 vs. S10; Interpreter's status; in-process Observer vs. event-driven integration.
- SKILL.md routes design-pattern work and lists the new script and template; the code-review,
  architecture-review, refactoring and repository-assessment workflows link the new procedures;
  `architecture-patterns.md` now covers system, integration and extensibility patterns and points
  to `references/patterns/`; five language guides gain a design-patterns section; the quality
  model's code dimension covers pattern use; `sources.md` registers S9 and S10 with their licence
  status and coverage gaps.

### Scripts
- New `pattern_scan.py` (standard library; Java, Kotlin, C#, PHP, TypeScript/JavaScript, Python,
  Go): inventory of declared patterns by name and by structure, and leads for single-implementation
  abstractions (with test-double counts and boundary hints), single-product factories, classic
  singletons and how many files reach them, deep inheritance, small visitors, and names that don't
  match the structure.

### Documentation
- Usage guide in English and Persian (`docs/usage-guide.en.md`, `docs/usage-guide.fa.md`): installing and
  updating on each surface, depth, what to provide, example prompts per task, design patterns, reading the
  results, scripts, templates, tips and troubleshooting.

### Evals: 10 → 14 (status: Not Run)
- `pattern-misuse-detection` (TypeScript), `pattern-selection` (Go), `pattern-based-refactoring`
  (Python, runnable tests), `spring-pattern-recognition` (Java/Spring). Each has positive cases,
  false-positive traps and graders labelled by criterion (correctness, proportionality, cost,
  evidence). They have not been run as evals; their fixtures were checked (see
  `validation/VALIDATION.md`).

## 1.1.0 — 2026-11-07

Focus: architecture design, databases, testing and verification, extensibility, and software
security.

### Sources
- **S8** — Thomas Hastings, *Software Engineering: Standing on the Shoulders of Giants* (open
  textbook at swebook.org, CC BY-SA 4.0), chapters 3, 6, 7 and 9–15. It is **not** the IEEE SWEBOK
  Guide, despite the domain name.
- **X15–X21** — selected titles from the supplied reading list, cited by title and chapter or item:
  *Effective Java* (2nd ed.), *Head First Design Patterns*, *Java Concurrency in Practice*,
  *Concurrent Programming in Java*, *Java Performance: The Definitive Guide*, *Pro Spring Batch*,
  *Introduction to Algorithms* (3rd ed.). The rest of that list (interview preparation, language
  tutorials, finance) was not relevant.
- **X22** OWASP Top 10 for LLM Applications (2025) and **X23** Saltzer & Schroeder's design
  principles.

### Rules: 201 → 249
- Architecture: ARCH-QA-01 (quality-attribute scenarios), ARCH-STYLE-04, ARCH-EXT-01..03
  (deliberate variation points, extension contracts as published APIs, isolating third-party
  extensions), ARCH-DIST-01, ARCH-DOC-01, ARCH-REV-01.
- Design: DES-API-01, DES-EXT-01, DES-HIDE-01.
- Data: DATA-MODEL-01/02, DATA-MIG-03, DATA-TXN-02/03, DATA-CONN-01, DATA-TENANT-01, DATA-SEC-01,
  DATA-AUDIT-01, DATA-EVOL-01, DATA-BACKUP-01, DATA-REPL-01, DATA-SCALE-01, DATA-BATCH-01.
- Testing: TEST-VV-01, TEST-ORACLE-01, TEST-DESIGN-01, TEST-COV-02, TEST-PROP-01, TEST-MUT-01,
  TEST-CONC-01, TEST-PERF-01, TEST-ENV-01, TEST-FUZZ-01.
- Security (new file `security-design.md`): SEC-DESIGN-01, SEC-PRIV-01, SEC-SUPPLY-01/02,
  SEC-GATE-01, SEC-AI-01. SEC-INJ-04 now also covers spreadsheet formula injection in exports.
- Runtime, delivery and practice: PERF-SCALE-01..03, REL-CONC-04, DLV-FLAG-01, DLV-REL-02,
  REV-CONDUCT-05.

### Principles, models and references
- Principles P-54–P-68 in `principles-extended.md` (53 → 68).
- Knowledge model: tensions T-17–T-23 (test pyramid vs. integration-heavy portfolios, complexity
  bands, layered vs. inward dependencies, where integrity rules live, interfaces vs. concretions,
  mandated coverage criteria, inheritance vs. framework proxies).
- Quality model: seven dimensions (adds data management; testing becomes testing and verification;
  reliability and performance gains scalability).
- New `architecture-patterns.md`: system, integration, extensibility and design patterns with their
  forces, costs and misuse signals.

### Workflows and templates
- New workflows: `database-review.md`, `test-strategy.md`, `threat-modeling.md`.
- Extended: architecture-review, security-review (OWASP Top 10:2025 map), code-review,
  implementation, repository-assessment, refactoring.
- New templates: architecture-description, threat-model, test-strategy, migration-plan; the
  assessment report gains the new quality dimensions and verification rows.
- Language guides extended: sql, java-spring, python, php-laravel, go, typescript-react.

### Scripts
- New `migration_lint.py`: dialect-aware leads for raw SQL, Laravel, Rails, Django and Alembic
  migrations (blocking index builds, table rewrites, constraints validated under lock, renames and
  drops during rolling deploys, backfills inside the migration, slow steps sharing one
  transaction, missing lock timeouts, edited applied migrations).
- New `test_smells.py`: assertion-free and mock-only tests, expected values derived from the code
  under test, skipped/focused/commented-out tests, sleeps, wall clock, unseeded randomness, real
  network.
- `security_scan.py`: CSV formula-injection lead. `rules.py`: domains may span several files.
  `validate_skill.py`: checks the extended principle file and the new templates.

### SKILL.md
- Description, triage escalation, router, quick checklist, scripts table, templates and reference
  map updated; metadata version 1.1.0, rule count 249.

### Evals
- Four new cases: `postgres-migration-review`, `webhook-threat-model`, `checkout-test-strategy`,
  `plugin-extensibility-decision`. Validated structurally; **not yet run** (see
  `validation/VALIDATION.md`).

## 1.0.0 — 2026-11-04

Initial release: 201 rules, 53 principles, 7 workflows, 7 language guides, 7 scripts and 6 eval
cases, benchmarked in `validation/VALIDATION.md`.
