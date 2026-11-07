# software-engineering-intelligence

A Claude Agent Skill that works as a senior software-engineering partner across the lifecycle:
implementation with self-review, code and PR review, repository assessment, architecture
evaluation (patterns, extensibility, scalability), design-pattern assessment, selection and
refactoring, database and migration review, test strategy (verification and validation), threat
modelling and supply-chain security, technical-debt management, safe refactoring, and security
review. It turns Clean Code, Clean Architecture, technical-debt management, ADR practice, the
OWASP Code Review Guide and Web Security Testing Guide, static-analysis theory, an open
software-engineering textbook (quality attributes, architectural patterns, testing theory, secure
design) and the Refactoring Guru design-pattern catalog into one traceable method:
**principles → rules → checks → workflows → outputs**.

This README is for humans (installation, usage, maintenance). Claude reads `SKILL.md`. A task-oriented usage
guide with example prompts is in the repository: [English](https://github.com/saleh-saspx/software-engineering-intelligence/blob/main/docs/usage-guide.en.md)
· [فارسی](https://github.com/saleh-saspx/software-engineering-intelligence/blob/main/docs/usage-guide.fa.md).

## Contents
1. What's inside · 2. Installation · 3. Usage and example prompts · 4. How it works ·
5. Scripts · 6. Validation · 7. Extending the skill · 8. Known limitations · 9. Key design decisions

## 1. What's inside

```
software-engineering-intelligence/
├── SKILL.md                      entry point: triage tiers, operating loop, router, non-negotiables,
│                                 quick checklist, judging findings, scripts, output formats
├── README.md                     this file
├── references/
│   ├── knowledge-model.md        layers, concern map, quality attributes, taxonomy (levels, finding
│   │                             types, severity, confidence), context gates, conflict resolution,
│   │                             30 resolved source contradictions (T-01–T-30), waivers
│   ├── principles.md             principles P-01–P-53 with source, intent, interpretation,
│   │                             implementing rules, limits, relations
│   ├── principles-extended.md    principles P-54–P-70: quality attributes, extensibility, data,
│   │                             verification and validation, secure design, supply chain, AI,
│   │                             design patterns
│   ├── sources.md                source registry (S1–S10 corpus, X1–X23 external), provenance labels,
│   │                             citation format, coverage gaps, licensing
│   ├── quality-model.md          seven-dimension evaluation, rating scale, metrics as signals, limits
│   ├── architecture-patterns.md  system, integration and extensibility patterns: forces, costs,
│   │                             misuse signals (design patterns live in patterns/)
│   ├── patterns/                 design patterns: index.md (catalog of the 22 patterns, supplementary
│   │                             patterns, sources and differences), one file per pattern (same fields
│   │                             each), selection.md (forces, baselines, cost model, revisit
│   │                             triggers), comparisons.md (15 look-alike pairs), anti-patterns.md,
│   │                             frameworks.md (Spring, Laravel, Go, Python, TypeScript/React)
│   ├── rules/                    255 rules in 11 domain files + generated index.md
│   │   ├── code.md  design.md  architecture.md  security.md  security-design.md  testing.md
│   │   ├── runtime.md (reliability, performance, scalability)  data-api.md  delivery.md
│   │   ├── techdebt.md  practice.md (review + AI-agent conduct)
│   │   └── index.md              generated — every rule ID, level and title
│   ├── workflows/                implementation · code-review (+ AI-code review, quality gate) ·
│   │                             repository-assessment · architecture-review · tech-debt ·
│   │                             refactoring (+ testing methodology) · security-review ·
│   │                             threat-modeling · database-review · test-strategy ·
│   │                             design-patterns (assessment, selection, refactoring, review)
│   └── languages/                java-spring · php-laravel · go · python · typescript-react · sql ·
│                                 other (C#/.NET, Kotlin, Rust, Ruby/Rails, C/C++)
├── assets/templates/             review-report · assessment-report · td-item (+ register) · adr ·
│                                 refactoring-plan · architecture-description · threat-model ·
│                                 test-strategy · migration-plan · pattern-decision
├── scripts/                      repo_survey · hotspots · deps · security_scan · migration_lint ·
│                                 test_smells · pattern_scan · rules · check_report · validate_skill
│                                 (+ _common)
└── evals/                        14 test cases with fixture projects and graders (not packaged)
```

## 2. Installation

Skills don't sync between Claude surfaces — install on each surface you use.

**Claude Code** (folder-based):
- Personal (all your projects on this machine): copy the folder to
  `~/.claude/skills/software-engineering-intelligence/`.
- Project (shared with the team through git): copy it to
  `.claude/skills/software-engineering-intelligence/` in the repository and commit it.
- Check it loads: `claude plugin validate ~/.claude/skills` (or the project path), then ask for a
  review, or invoke it directly with `/software-engineering-intelligence`.

**Claude apps (claude.ai, desktop)**: upload `software-engineering-intelligence.zip` (the ZIP
contains the skill folder) in the Skills section of Settings. Custom skills need code execution
enabled, are available on paid plans, and are per user — each teammate uploads their own copy.
The scripts need code execution; without it the skill still works from its reference files.

**Claude API**: upload the ZIP through the Skills API (`/v1/skills`); see the Agent Skills docs.

Requirements for the scripts: Python 3.9+ (standard library only; `scripts/validate_skill.py` also uses
PyYAML if present) and `git` for churn analysis.

## 3. Usage and example prompts

The skill triggers on reviewing, auditing, assessing, refactoring, hardening or designing code,
and on non-trivial implementation work. It scales depth automatically (Tier 0 direct → Tier 3
deep). Examples:

- "Review this PR before I merge it — it adds the refund endpoint." (Tier 2 review, verdict, findings)
- "Quick look at handler.go before I push?" (Tier 1 light review)
- "Assess this repository's architecture and technical debt and give me a prioritised backlog —
  we start subscription billing next quarter." (Tier 3 assessment + debt register)
- "Our lead wants to move this service to hexagonal architecture. Worth it?" (architecture fit)
- "Refactor `calculate_shipping` without changing behaviour." (characterization tests first)
- "Do a security review of the authentication and file-upload code." (OWASP-based review)
- "Implement pagination for `/api/orders` and review your own change." (implementation + self-review)
- "Write an ADR for moving from REST polling to webhooks." (ADR template)
- "Which parts of this codebase should we refactor first?" (hotspots × roadmap)
- "Is this test suite any good?" (testing dimension of the quality model)
- "We run migration 0042 on prod tonight — orders has 40M rows. Anything to worry about?"
  (database review: locks, rewrites, rollout compatibility, staged plan)
- "Threat-model our new payment-webhook design before we build it." (assets, trust boundaries,
  STRIDE, ranked threats, testable mitigations)
- "Propose a test strategy for the checkout rebuild — our tests miss real incidents." (risk-based
  verification and validation plan)
- "Customers want to add their own export formats — should we build a plugin system?"
  (extensibility decision: evidenced variation points, published contracts, isolation)
- "Which design patterns does this codebase use, and which ones are misapplied?" (pattern
  assessment: participants, forces, verdicts — including "remove this pattern")
- "Should we use a Strategy or a State here — or neither?" (pattern selection against the
  no-pattern baseline and the closest look-alike, with cost and revisit triggers)

What you get: findings with location, type, severity (blocker/major/minor/nit), confidence
(confirmed/likely/possible), rule ID and fix; an explicit scope; and only verification results
that were actually observed.

## 4. How it works

- **Triage** (SKILL.md §1) picks the depth; risky areas (auth, money, input parsing, migrations on
  large tables, concurrency, public contracts and extension points, new trust boundaries,
  dependency and pipeline changes, LLM features) escalate it.
- **Context gates** (knowledge-model §5) — ecosystem, local conventions, lifecycle, domain
  complexity, team/ops, NFRs — are established before any rule is applied. This is the main
  defence against false positives such as demanding repositories in a Laravel CRUD app.
- **Rules** carry a level (mandatory → optional), default severity, provenance (direct /
  synthesized / extension / convention), signals, fix, verification, automation, exceptions and
  related rules. **Conflicts** are resolved by a precedence order: safety and correctness →
  explicit constraints (ADRs, contracts) → behaviour preservation → evidenced NFRs → structural
  principles → ecosystem idioms → generic style → preference.
- **Findings are classified before they are rated**: defect, vulnerability, reliability-risk,
  performance, tech-debt, architecture-risk, test-gap, trade-off, legacy-constraint,
  imperfection, question. Only change-cost problems are "technical debt" (Kruchten et al.).
- **Evidence discipline**: tests passing, builds succeeding or "no vulnerabilities" are never
  claimed without observation; scope is always stated; tool output is treated as leads.

## 5. Scripts

Run from anywhere: `python3 <skill-dir>/scripts/<script>.py <target> [--json]`.

| Script | Purpose |
|---|---|
| `scripts/repo_survey.py PATH` | Languages, frameworks, size, tests, CI, infra, migrations, docs/ADRs, lockfiles, risky committed files, git activity |
| `scripts/hotspots.py PATH --since "12 months"` | Churn × complexity ranking (exact McCabe for Python, approximate elsewhere) |
| `scripts/deps.py PATH --depth N --forbid "domain->infra"` | Internal dependency graph (Python, JS/TS incl. tsconfig paths, Java/Kotlin, Go, PHP), cycles, instability, forbidden directions; exit 1 on violations (CI-friendly); `--dot` for Graphviz |
| `scripts/security_scan.py PATH [--files …]` | ~50 patterns for security/reliability leads mapped to rule IDs and OWASP refs; secrets masked |
| `scripts/migration_lint.py PATH [--git-base REF] [--dialect …]` | Schema-migration leads for raw SQL, Laravel, Rails, Django and Alembic: blocking index builds, table rewrites (volatile defaults, type changes), constraints validated under lock, renames and drops during rolling deploys, backfills inside the migration, slow steps sharing one transaction, missing lock timeouts, edited applied migrations; dialect from the files, config or driver dependencies; `--fail-on` for CI |
| `scripts/test_smells.py PATH [--files …]` | Test-suite leads: assertion-free tests, mock-only assertions, expected values derived from the code under test (Python), skipped/focused/commented-out tests, sleeps, wall clock, unseeded randomness, real network |
| `scripts/pattern_scan.py PATH [--min-depth N]` | Design-pattern inventory by name and by structure (Java, Kotlin, C#, PHP, TS/JS, Python, Go) and misuse leads: single-implementation abstractions (with test-double counts), single-product factories, classic singletons and who reaches them, deep inheritance, small visitors, names that don't match the structure |
| `scripts/rules.py list/show/search/stats/check/index` | Query and validate the rule catalog; regenerate the index |
| `scripts/check_report.py <report.md>` | Structural check of review/assessment reports; flags over-claiming |
| `scripts/validate_skill.py [--strict]` | Self-validation of the whole skill |

## 6. Validation

`python3 scripts/validate_skill.py` checks: frontmatter against the Agent Skills spec; SKILL.md
budget; rule schema, unique IDs, valid levels/provenance/severities, registered sources, related
links, numbering; index freshness; principle completeness and cross-references; every rule,
principle and tension ID mentioned anywhere exists; every referenced path resolves; every file is
reachable from SKILL.md; near-duplicate rule titles; template headings; script compilation and
`--help`; eval case layout; approximate token cost per file.

Behavioural validation — 14 eval cases in `evals/`, each a realistic project with planted
problems *and* planted false-positive traps:

| Case | Tests |
|---|---|
| `laravel-pr-review` | Security-aware PR review (SQLi, IDOR, mass assignment, stored XSS, N+1, cache bug) without imposing non-Laravel architecture |
| `billing-architecture-decision` | Rejecting overengineering with context; correctness first; recognising an ADR trade-off |
| `safe-refactor-shipping` | Characterization tests first; behaviour preserved (checked over 73,920 inputs); quirks kept |
| `spring-repo-assessment` | Repository assessment with git-history hotspots, cycle detection, debt vs. vulnerability classification, roadmap-aware priorities |
| `go-quick-review` | Light review in Go idiom: data race, negative quantities, timeouts — no Java-isms |
| `trivial-input-validation` | Proportionality: minimal change, test, short reply |
| `postgres-migration-review` *(1.1)* | Alembic migration on a 40M-row PostgreSQL 15 table during a rolling deploy: volatile-default rewrite, blocking index/unique builds, FK validation, rename, in-transaction backfill, lock timeout — without flagging the safe constant default |
| `webhook-threat-model` *(1.1)* | Design-time threat model: fail-open signatures, cross-tenant confusion, replay/idempotency, SSRF, logging — without demanding sessions or CSRF tokens for a webhook |
| `checkout-test-strategy` *(1.1)* | Suite assessment (assertion-free, self-referential, mock-only, skipped tests; misleading coverage) and an incident-driven V&V strategy |
| `plugin-extensibility-decision` *(1.1)* | Rejecting in-process customer plugins; evidence-based variation points; published contracts; CSV formula injection and unbounded exports |
| `pattern-misuse-detection` *(1.2)* | TypeScript service: payment capture hidden in an event listener whose errors are swallowed, a mutable config singleton, a single-product factory, a four-level repository chain, a two-element visitor — while keeping the justified Strategy, the test-seam interface and the middleware chain |
| `pattern-selection` *(1.2)* | Go: choosing a one-method quoting interface with explicit wiring, concurrency and partial failure over a proposed Abstract Factory, init() registry, Builder and plugins; keeping a small switch |
| `pattern-based-refactoring` *(1.2)* | Python: if/elif tax chain to an explicit dispatch table with EU rates as data — characterization tests first, Austrian per-line rounding preserved, a float-rounding defect reported instead of silently changed |
| `spring-pattern-recognition` *(1.2)* | Spring Boot: mapping Strategy (bean map), Observer (async vs. after-commit listeners), proxy-based transactions (self-invocation), template-callback, Adapter, Decorator, FactoryBean and filter chain; flagging a hand-written singleton, a needless factory and a pass-through "facade" |

The cases added in versions 1.1 and 1.2 have not been benchmarked yet (status "Not Run"). Results of the last benchmark
run (version 1.0 cases) are summarised in VALIDATION.md, delivered in the `validation`
folder next to this skill folder (with browsable review pages for every run). With Claude Code you can re-run the cases yourself from the skill directory:
`claude plugin eval . --allow-tools Write,Edit,Bash --scaffold` (real, billed model runs).

## 7. Extending the skill

- **Add a rule**: append a block to the right `references/rules/<domain>.md` using the schema in
  `references/rules/index.md`; cite sources honestly (never claim a book supports something it doesn't); then
  `python3 scripts/rules.py index --write` and `python3 scripts/validate_skill.py`.
- **Add a language guide**: create `references/languages/<name>.md` (Identify · idioms to follow and
  not flag · real issues · security hot spots · testing · tools) and add it to the list in SKILL.md §3.
- **Add a source**: register it in `references/sources.md` (S for corpus documents you can check,
  X for external references), then cite it.
- **Project conventions**: put team-specific rules in your repository (e.g. CLAUDE.md or ADRs); the
  skill treats documented conventions and accepted ADRs as constraints.
- **Add a design pattern note**: extend the pattern's file in `references/patterns/` (keep the
  field order listed in `references/patterns/index.md` §1), add look-alike rows to
  `references/patterns/comparisons.md`, and
  only add a rule when it states a check that applies across patterns.
- **Copyright**: keep paraphrasing; never paste text from the books or websites.

## 8. Known limitations

- The technical-debt book is a **publisher sample** (Chapter 1 only); prioritisation mechanics are
  synthesised from its definitions and principles, not taken from Chapters 2–13.
- DDD, refactoring catalogues, observability and most database operations (isolation levels,
  live migrations, replication, backups) are mostly `extension` guidance — expert practice not
  backed by the corpus (labelled as such). Version 1.1 anchors architecture, patterns, testing
  theory, delivery and secure design in S8, an open textbook in beta: its section numbers may move.
- The swebook.org textbook (S8) is **not** the IEEE SWEBOK Guide, despite its domain name.
- The OWASP Code Review Guide uses 2013 Top 10 numbering; rules cite categories by concept.
- Scripts are heuristics: complexity is approximate outside Python; dependency resolution misses
  dynamic imports, DI wiring and same-package references; the security scan is a regex crawl that
  produces false positives and false negatives by design. Nothing in the skill can certify code as
  correct or secure.
- CVE/advisory knowledge must come from a current scanner; the skill instructs Claude not to cite
  vulnerabilities from memory.
- The design-pattern PDF supplied for 1.2 is a third-party *summary* (Bookey) of *Dive Into
  Design Patterns*, not the book: eight of its 36 chapter summaries are truncated and its added
  commentary is unverified. The Refactoring Guru site (S10) is authoritative; differences are
  recorded as tension T-28. Both are "All rights reserved" — the skill paraphrases and cites them.
- `scripts/pattern_scan.py` reads declarations, not intent: it cannot see lambdas implementing interfaces,
  mocking-library doubles, DI-container wiring or framework-generated implementations, so counts
  are lower bounds and every hit is a lead.
- Behavioural evals use one run per configuration on the six 1.0 cases — useful evidence, not a
  statistically strong benchmark; the four 1.1 and four 1.2 cases are written and validated
  structurally (their fixtures build and their tests pass) but have not been run as evals.

## 9. Key design decisions

1. **One skill, progressive disclosure** — a ~260-line entry point routes to ~75 supporting files, so
   a typical task loads a few thousand tokens, not the whole catalog.
2. **Triage tiers** — proportionality is a first-class rule; trivial tasks get direct answers.
3. **Context gates before rules** — ecosystem idioms and local conventions outrank generic advice.
4. **Classify, then rate** — finding type, then severity, then confidence; vulnerabilities and
   defects are never filed as "debt".
5. **Provenance on everything** — direct / synthesized / extension / convention, with chapter-level
   citations checked against the source files; contradictions between books resolved explicitly.
6. **Overengineering is a defect class** — boundaries, abstractions and design patterns must name
   the force that justifies them (Clean Architecture's own YAGNI caveats, Ch.24–25); "no pattern"
   is a legitimate recommendation, compared against the simplest alternative and the closest
   look-alike.
7. **Evidence discipline from static-analysis theory** — tools approximate; tests show presence, not
   absence, of bugs; scope and verification are always reported honestly.
8. **Markdown rules with a parseable schema** — readable by Claude and people, validated by scripts.
9. **Standard-library scripts** — run anywhere Python runs, no installs.
