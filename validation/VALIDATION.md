# Validation report — software-engineering-intelligence

## Version 1.1.0 — 2026-11-07

What changed is listed in `CHANGELOG.md`. **The behavioural benchmark has not been run for 1.1**:
the four new eval cases are written and pass structural validation only, and the results in the
1.0.0 section below describe the 1.0 skill.

### Structural self-validation
`python3 scripts/validate_skill.py --strict` → **0 errors, 0 warnings**.

| Check | Result |
|---|---|
| Frontmatter | description 999 characters (limit 1024), no angle brackets; metadata version 1.1.0, rule count 249 |
| SKILL.md budget | 258 lines (limit 500) |
| Rule catalog | 249 rules (48 new): unique IDs, valid levels, severities and provenance, registered sources, resolving `related` links, contiguous numbering; the SEC domain spans `security.md` and `security-design.md` |
| Rule index | regenerated and in sync |
| Principles | 68 (P-54 – P-68 in `principles-extended.md`), all fields present, all cross-references resolve |
| Tensions | T-01 – T-23, every mention resolves |
| Links and reachability | every referenced path resolves; every reference, template and script is reachable from SKILL.md |
| Templates | four new templates carry their required headings |
| Scripts | all nine compile and answer `--help` |
| Eval cases | ten cases with valid layout and no cache files in the fixtures |

### Source checks
- S8 claims were checked against the online chapters retrieved on 2026-11-07, at the level of
  section headings and stated claims. The book is a beta edition: section numbers may move.
- X15–X21 are cited at title and chapter/item level only. Their PDFs in the reading-list repository
  were not text-checked in this session, so no page numbers or wording are taken from them.
- Database guidance remains mostly `extension` (engine manuals and practice, X11/X14), anchored in
  S8 where the book touches data (shared stores, CAP, schema compatibility, irreversible migrations).

### Script tests
- `migration_lint.py` was run on fixtures with raw SQL (PostgreSQL and MySQL), Laravel, Rails,
  Django and Alembic migrations, on a git history with an edited applied migration, and on the
  `postgres-migration-review` fixture. On that fixture it reports every planted risk (volatile-default
  rewrite, unique-constraint index build, foreign key validated under lock, non-concurrent index,
  rename during a rolling deploy, in-transaction backfill, slow steps sharing one transaction,
  missing lock timeout) and does not flag the safe constant-default column. Defects found and fixed
  while testing: duplicate leads for one line; findings scattered by severity instead of grouped by
  file; MySQL `CHANGE COLUMN` renames with complex definitions missed; Django operations imported by
  name and `RunSQL` lists missed; no dialect for ORM migrations (now read from dialect imports and
  driver dependencies); no Alembic checks for volatile server defaults and unique constraints;
  multi-action `ALTER TABLE` statements counted as several steps.
- `test_smells.py` was run on a mixed fixture (Python, TypeScript, Java, Go, PHP) and on the
  `checkout-test-strategy` fixture, where it reports every planted smell (two assertion-free tests,
  a mock-only test, an expected value derived from the code under test, a skip without reason,
  sleeps and wall-clock reads). Defects fixed: line anchors that swallowed the previous newline
  (empty snippets); `it.only`/`it.skip` declarations not parsed; skipped test bodies reported as
  assertion-free; factory-built expected values reported as self-referential (only
  result-producing calls count now).
- `security_scan.py`: the new CSV formula-injection lead fires on the export fixture.
- The fixtures' own suites pass: `checkout-test-strategy` 15 passed and 2 skipped (the e2e module
  without Selenium, and the deliberately skipped test); `plugin-extensibility-decision` 4 passed.

### New eval cases (not yet run)
| Case | What it probes | Trap (must not be flagged) |
|---|---|---|
| postgres-migration-review | Alembic migration on a 40M-row PostgreSQL 15 table during a rolling deploy | Constant `DEFAULT 'pending'` and a nullable column are catalog-only since PostgreSQL 11 |
| webhook-threat-model | Design-time threat model of a payment webhook in a multi-tenant platform | No session/JWT and no CSRF token on a signed webhook route |
| checkout-test-strategy | Suite assessment plus an incident-driven verification and validation strategy | Keep the sound parametrised VAT test; no coverage target as the goal |
| plugin-extensibility-decision | Customer-uploaded plugins vs. evidenced, declarative variation points | No microservice, broker or plugin framework as the primary answer |

To run them (billed): from the skill folder, `claude plugin eval . --allow-tools Write,Edit,Bash --scaffold`.

## Version 1.0.0 — 2026-11-04

Date: 2026-11-04 · Model for all runs and grading: Claude Opus 5.5 · Method: skill-creator eval loop
(with-skill vs. no-skill baseline, independent grader agents, objective checkers where possible).

### 1. Structural self-validation

`python3 scripts/validate_skill.py` → **0 errors, 0 warnings** on the delivered version.

| Check | Result |
|---|---|
| Frontmatter (Agent Skills spec: name, description ≤ 1024 chars, no angle brackets, allowed keys) | pass — also passes skill-creator's `quick_validate.py` |
| SKILL.md budget | 238 lines (limit 500) |
| Rule catalog | 201 rules, unique IDs, valid levels/severities/provenance, all sources registered, all `related` links resolve, contiguous numbering, every strong/mandatory rule has a verification method |
| Rule index | in sync with the catalog (generated) |
| Principles | 53 principles, all fields present, all referenced rules/principles/sources exist |
| Cross-references | every rule, principle and tension ID mentioned anywhere exists |
| Links and paths | every referenced skill path resolves (this check found and fixed 9 real broken references during development) |
| Reachability | every reference, asset and script is reachable from SKILL.md |
| Duplicates | no near-duplicate rule titles |
| Templates | required headings present |
| Scripts | all compile and answer `--help` |
| Eval cases | layout valid for `claude plugin eval`; fixtures free of cache files |

Source integrity: every chapter, section, heuristic code (e.g. Clean Code G26) and test ID (e.g.
WSTG-ATHZ-04) cited as `direct` was checked against the text extracted from the supplied PDFs;
one inaccurate paraphrase of Clean Architecture Ch.32 was found and corrected.

### 2. Script tests

Each analysis script was run against the fixture projects (Laravel, Flask, legacy Python, Spring
with generated git history, Go) and a throwaway TypeScript project with a tsconfig path alias and
a deliberate cycle. Defects found and fixed during testing:

- `@GeneratedValue` (JPA) was mistaken for an "@generated" file marker, silently skipping entity
  files → word-boundary match.
- Multiline `^\s*` regexes reported line numbers above the real import/config line → `^[ \t]*`.
- Nested Python functions were counted into their parent's complexity → separate measurement.
- Ternary-operator counting miscounted PHP `?>`, `?->` and generics → tightened pattern.
- The security scan missed chained calls (`Order::with(...)->findOrFail($id)`,
  `_ = json.NewDecoder(r.Body).Decode(&req)`) and implicit Python float money → broadened.

Verified behaviour: the dependency script finds the `orders ⇄ billing` cycle with file:line
evidence and exits 1 on forbidden directions; hotspots ranks `OrderService` first from git churn
and ranks the untouched legacy class last; the report checker catches every defect planted in a
bad sample report.

### 3. Behavioural evaluation

#### Test projects
| Case | What it probes | Planted traps (must *not* be flagged) |
|---|---|---|
| laravel-pr-review | PR review: SQL injection (incl. sort column), IDOR, mass assignment, stored XSS, unauthorised export, N+1, cache key ignoring the page | Facades, Eloquent Active Record, placeholder `.env.example` |
| billing-architecture-decision | "Should we go hexagonal?" for a tiny internal Flask app; float money, duplicate invoices | ADR-documented denormalisation |
| safe-refactor-shipping | Behaviour-preserving refactor of a 50-line, complexity-20 function with quirks | Quirks that look like bugs |
| spring-repo-assessment | Repo assessment + debt backlog with 14 commits of generated history and a roadmap | Ugly but stable legacy class |
| go-quick-review | Quick review: data race, negative quantity, ignored error, no timeout, unescaped URL | Go idioms (explicit errors, linear handler) |
| trivial-input-validation | Proportionality on a one-line change | — |

Objective checkers: the refactor case compares original and refactored functions on a
73,920-input grid and runs the agent's tests against the *original* code; the trivial case checks
behaviour, diff size and files. Other assertions were graded by independent grader agents that
re-ran claims (reproductions, statistics, git history) rather than trusting the outputs.

#### Iteration 1 (initial skill)
| Case | With skill | Baseline | Tokens with / without | Words with / without |
|---|---|---|---|---|
| laravel-pr-review | 10/10 | 10/10 | 161k / 129k | 3,140 / 2,004 |
| billing-architecture-decision | 8/8 | 8/8 | 230k / 118k | 4,981 / 1,969 |
| safe-refactor-shipping | 7/7 | 7/7 | 250k / 183k | 1,707 / 701 |
| spring-repo-assessment | **9/9** | 7/9 | 276k / 167k | 7,448 / 3,073 |
| go-quick-review | 6/7 | 6/7 | 191k / 118k | 1,760 / 1,106 |
| trivial-input-validation | 4/5 | 4/5 | 89k / 65k | 161 / 151 |
| **Total** | **94%** | **91%** | +69k avg | |

Findings: the base model already found every planted defect, and no false positives occurred in
either configuration. The skill's measurable contribution was explicit scope, evidence/confidence
labels, and debt-vs-defect-vs-vulnerability classification. Its costs: replies 1.5–2.6× longer,
internal vocabulary leaking to users, and escalation rules that overrode a "quick review" request.

#### Changes made from the evidence
- **Depth is not length**: escalation now raises depth of analysis, never reply size; the user's
  requested format wins; a stricter check no longer counts as escalation.
- **Reader-first output**: per-tier word budgets; no internal vocabulary (tier numbers, coverage
  codes, rule IDs as prose); at most one rule ID per finding; optional template sections.
- **Executable evidence when cheap**: reproduce suspected issues in scratch locations.
- **Roadmap simulation** for debt assessments; reader-hostile output now flagged by `check_report.py`.
- Eval assertions revised on grader feedback (bundled checks split, wording fixed, an unasserted
  planted bug added, user-value checks added for length, verdict placement and plain language).

#### Iteration 2 (improved skill; four affected cases re-run)
| Case | With skill | Baseline | Tokens with / without | Time with / without | Words with / without |
|---|---|---|---|---|---|
| go-quick-review | **9/9** | 8/9 | 155k / 118k | 703 s / 545 s | **519** / 1,106 |
| trivial-input-validation | **6/6** | 4/6 | 72k / 65k | 100 s / 100 s | **71** / 151 |
| billing-architecture-decision | 8/9 | 8/9 | 212k / 118k | 1,058 s / 565 s | 2,033 / 1,969 |
| spring-repo-assessment | **11/11** | 9/11 | 320k / 167k | 1,731 s / 982 s | 3,100 / 3,073 |
| **Total** | **97%** | **82%** | +72k avg | +350 s avg | |

Reply length now matches or beats the baseline while keeping the skill's strengths (the Go review
reproduced and confirmed every finding; the Spring assessment kept scope, classification and
confidence labels and reproduced eight defects).

After iteration 2, four smaller refinements were made from grader feedback and are **not**
re-benchmarked: test the refactoring safety net with seeded mistakes and extreme inputs; reproduce
selectively in assessments (cost control); state whether each relevant ADR still holds and what
triggers revisiting it; note when a proposed fix breaks callers or tests.

### 4. Honest assessment

- The skill does **not** make Claude find more or more accurate bugs on these cases; the base model
  is already strong. Graders occasionally found extra insights in baseline runs.
- What it adds reliably: honest scope and verification reporting, confidence labels,
  classification of debt vs. defects vs. vulnerabilities, roadmap-aware prioritisation,
  proportionate output, adherence to ecosystem idioms, and traceable sourcing.
- It costs more: about +70k tokens and +6 minutes per substantial task on average, mostly from
  reading guidance and from reproducing issues. Trivial tasks now cost about the same as baseline.

### 5. Limitations of this evaluation

- One run per configuration per case: differences of one assertion are within noise.
- Iteration-2 baselines reuse the iteration-1 outputs (the baseline doesn't depend on the skill),
  regraded on the revised assertions; assertions changed between iterations, so iteration totals
  are not directly comparable.
- Command logs were self-reported by the executors; graders cross-checked them against artifacts
  and by re-running claims, but full transcripts were not available.
- Six cases cannot cover every ecosystem; C#, Rust, Ruby, Kotlin and frontend-only work were not
  behaviourally tested.

### 6. Reproducing

- Structure: `python3 software-engineering-intelligence/scripts/validate_skill.py`
- Behaviour (Claude Code, billed runs): from the skill folder,
  `claude plugin eval . --allow-tools Write,Edit,Bash --scaffold`
- The review viewers in this folder (`review-iteration-1.html`, `review-iteration-2.html`) show every
  output, grade and benchmark; open them in a browser.
