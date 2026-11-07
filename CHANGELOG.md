# Changelog

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
