# Changelog

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
