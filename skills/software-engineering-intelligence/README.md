# software-engineering-intelligence

A Claude Agent Skill that works as a senior software-engineering partner across the lifecycle:
implementation with self-review, code and PR review, repository assessment, architecture
evaluation, technical-debt management, testing and safe refactoring, and security review. It
turns Clean Code, Clean Architecture, technical-debt management, ADR practice, the OWASP Code
Review Guide and Web Security Testing Guide, and static-analysis theory into one traceable
method: **principles → rules → checks → workflows → outputs**.

This README is for humans (installation, usage, maintenance). Claude reads `SKILL.md`.

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
│   │                             16 resolved source contradictions (T-01–T-16), waivers
│   ├── principles.md             53 principles (P-01–P-53) with source, intent, interpretation,
│   │                             implementing rules, limits, relations
│   ├── sources.md                source registry (S1–S7 corpus, X1–X14 external), provenance labels,
│   │                             citation format, coverage gaps, licensing
│   ├── quality-model.md          six-dimension evaluation, rating scale, metrics as signals, limits
│   ├── rules/                    201 rules in 10 domain files + generated index.md
│   │   ├── code.md  design.md  architecture.md  security.md  testing.md
│   │   ├── runtime.md (reliability + performance)  data-api.md  delivery.md
│   │   ├── techdebt.md  practice.md (review + AI-agent conduct)
│   │   └── index.md              generated — every rule ID, level and title
│   ├── workflows/                implementation · code-review (+ AI-code review, quality gate) ·
│   │                             repository-assessment · architecture-review · tech-debt ·
│   │                             refactoring (+ testing methodology) · security-review
│   └── languages/                java-spring · php-laravel · go · python · typescript-react · sql ·
│                                 other (C#/.NET, Kotlin, Rust, Ruby/Rails, C/C++)
├── assets/templates/             review-report · assessment-report · td-item (+ register) · adr ·
│                                 refactoring-plan
├── scripts/                      repo_survey · hotspots · deps · security_scan · rules ·
│                                 check_report · validate_skill  (+ _common helpers)
└── evals/                        6 test cases with fixture projects and graders (not packaged)
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

What you get: findings with location, type, severity (blocker/major/minor/nit), confidence
(confirmed/likely/possible), rule ID and fix; an explicit scope; and only verification results
that were actually observed.

## 4. How it works

- **Triage** (SKILL.md §1) picks the depth; risky areas (auth, money, input parsing, migrations,
  concurrency, public contracts) escalate it.
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

Behavioural validation — 6 eval cases in `evals/`, each a realistic project with planted
problems *and* planted false-positive traps:

| Case | Tests |
|---|---|
| `laravel-pr-review` | Security-aware PR review (SQLi, IDOR, mass assignment, stored XSS, N+1, cache bug) without imposing non-Laravel architecture |
| `billing-architecture-decision` | Rejecting overengineering with context; correctness first; recognising an ADR trade-off |
| `safe-refactor-shipping` | Characterization tests first; behaviour preserved (checked over 73,920 inputs); quirks kept |
| `spring-repo-assessment` | Repository assessment with git-history hotspots, cycle detection, debt vs. vulnerability classification, roadmap-aware priorities |
| `go-quick-review` | Light review in Go idiom: data race, negative quantities, timeouts — no Java-isms |
| `trivial-input-validation` | Proportionality: minimal change, test, short reply |

Results of the last benchmark run are summarised in VALIDATION.md, delivered in the `validation`
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
- **Copyright**: keep paraphrasing; never paste text from the books.

## 8. Known limitations

- The technical-debt book is a **publisher sample** (Chapter 1 only); prioritisation mechanics are
  synthesised from its definitions and principles, not taken from Chapters 2–13.
- DDD, design patterns, refactoring catalogues, legacy-code techniques, reliability, performance,
  API/database design and CI/CD are mostly `extension` guidance — expert practice not backed by the
  supplied corpus (labelled as such).
- The OWASP Code Review Guide uses 2013 Top 10 numbering; rules cite categories by concept.
- Scripts are heuristics: complexity is approximate outside Python; dependency resolution misses
  dynamic imports, DI wiring and same-package references; the security scan is a regex crawl that
  produces false positives and false negatives by design. Nothing in the skill can certify code as
  correct or secure.
- CVE/advisory knowledge must come from a current scanner; the skill instructs Claude not to cite
  vulnerabilities from memory.
- Behavioural evals use one run per configuration on six cases — useful evidence, not a
  statistically strong benchmark.

## 9. Key design decisions

1. **One skill, progressive disclosure** — a ~240-line entry point routes to ~40 supporting files, so
   a typical task loads a few thousand tokens, not the whole catalog.
2. **Triage tiers** — proportionality is a first-class rule; trivial tasks get direct answers.
3. **Context gates before rules** — ecosystem idioms and local conventions outrank generic advice.
4. **Classify, then rate** — finding type, then severity, then confidence; vulnerabilities and
   defects are never filed as "debt".
5. **Provenance on everything** — direct / synthesized / extension / convention, with chapter-level
   citations checked against the source files; contradictions between books resolved explicitly.
6. **Overengineering is a defect class** — boundaries and abstractions must name the force that
   justifies them (Clean Architecture's own YAGNI caveats, Ch.24–25).
7. **Evidence discipline from static-analysis theory** — tools approximate; tests show presence, not
   absence, of bugs; scope and verification are always reported honestly.
8. **Markdown rules with a parseable schema** — readable by Claude and people, validated by scripts.
9. **Standard-library scripts** — run anywhere Python runs, no installs.
