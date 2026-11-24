# Validation report — software-engineering-intelligence

## Version 1.3.0 — 2026-11-24

What changed is listed in `CHANGELOG.md`. The ten new eval cases **were run**: each once, by a
separate executor agent, and graded by a separate grader agent, at the commits named below. These
are single runs with self-reported traces, not a statistical benchmark (see Limitations). Nothing
was run against a user's system or a production database.

### Structural self-validation
`python3 scripts/validate_skill.py --strict` → **0 errors, 0 warnings**; the skill-creator
`quick_validate.py` → valid.

| Check | Result |
|---|---|
| Frontmatter | description 1,023 characters (limit 1024), no angle brackets; metadata version 1.3.0, rule count 270 |
| SKILL.md budget | 274 lines (limit 500) |
| Rule catalog | 270 rules (15 new, 6 extended); `rules.py check` → 0 errors, 0 warnings; index regenerated and in sync |
| Principles | 74 (P-71 – P-74 new), all fields present, all cross-references resolve |
| Tensions | T-01 – T-34, every mention resolves |
| Links and reachability | every referenced path resolves, including the new `references/testing/` (4 files) and `references/data/` (5 files) |
| Templates | 11; `test-execution-report.md` carries its required headings (registered in `validate_skill.py`) |
| Load budget | no reference file above the validator's ≈9,000-token warning after `testing.md` and the data rules were split (largest: `rules/architecture.md` ≈8,500) |
| Scripts | all thirteen compile and answer `--help`; the helper modules `_common.py` and `_db.py` import and run cleanly |
| Eval cases | twenty-four cases with valid layout and no cache files in the fixtures |

### Script tests
- **77 unit tests** (standard library only, `python3 -m unittest discover -s tests`, repository root,
  not shipped in the ZIP) → all pass: database detection 15, `test_impact.py` 15, `test_report.py`
  12, `schema_lint.py` 18, `migration_lint.py` 14, `test_smells.py` 5. They include negative cases
  (identifiers that only look numeric, boolean-like columns, ORM-generated types, fixture folders,
  development dependencies, credentials after `postgres:` in a URL, comments and lower-case words in
  code) and the regressions found by the independent review.
- **`migration_lint.py` against 1.2.0.** Both versions were run on a 22-file corpus (14 SQL
  migrations covering every check, 2 Rails, 1 Django, 2 Laravel and 2 Alembic migrations from the
  eval fixtures, and the Alembic `env.py`) with `--dialect postgresql`, `mysql` and `auto`:
  - PostgreSQL: 62 leads in both; 57 identical; the 5 differences are the documented
    `no-lock-timeout` line fix. No message or fix text changed.
  - MySQL: 39 → 64 leads; all 39 from 1.2.0 unchanged; the 25 added are the two new info-level
    checks (`no-lock-timeout` for metadata locks, `ddl-implicit-commit`). Nothing removed.
  - Auto-detected dialects: the same differences, per file.
- After the final changes, `repo_survey.py`, `schema_lint.py`, `migration_lint.py`,
  `test_smells.py` and `security_scan.py` were run on all ten new fixtures: every run exited 0.

### Engine facts
- The behaviour summarised in `references/data/engines.md`, `types.md`, `internals.md` and
  `testing/database-matrix.md` was checked against the vendors' documentation (X27) on 2026-11-24;
  cells that could not be checked are marked †.
- Executed on PostgreSQL 16.15 in the sandbox: `numeric(10,4)` rounds 0.00002381 to 0.0000 and
  raises an error on overflow; a foreign key creates no index on the referencing column; an index
  on `date(timestamptz)` is rejected (the function is not IMMUTABLE); `NULLS NOT DISTINCT` works;
  `''` is not NULL; the default isolation is read committed.
- Not executed (no server available): MySQL/MariaDB, Oracle and SQL Server behaviour, which rests
  on their documentation only. Fixture details that would have been wrong for their engine were
  corrected while the cases were written: the Oracle case's tests use plain H2, because H2's Oracle
  mode treats `''` as NULL; a MySQL query was replaced because `ONLY_FULL_GROUP_BY` rejects it.
- The books X24–X26 were not available as files; they are cited by part or chapter as knowledge
  references, and no passage is reproduced.

### Independent adversarial review
A separate reviewer agent read the scripts, tests and new references at commit `dd77058` and
reported 1 blocker, 6 major and 8 minor findings. All were fixed in `6e18b64`, each with a unit
test: skipped tests in a Required group now make the verdict "not verified"; flakiness is inferred
only from reruns in one run or with `--same-environment`; an empty run is not verified; Oracle
`DECIMAL`/`NUMERIC` default to scale 0; ORM-generated types are not judged as MySQL `TIMESTAMP` or
bare `DECIMAL`; development and test dependencies, fixture folders and Laravel's list of drivers
no longer count as production engines; security and money signals match tokens, not substrings,
and only in changed lines in git mode; engines are intersected with the application's; Oracle
`ONLINE` must follow the column list; option-like git refs are refused; four engine facts were
corrected.

### Behavioural evaluation
The answers with their traces, and the grading notes, are in `validation/evals-1.3.0/` (batch 2's
per-criterion evidence in `GRADING-batch2-detail.md`; batch 1's grader report was summarised in
`GRADING-batch1.md`).

**Method.** One executor agent per case was told to treat the working-tree `SKILL.md` as its
instructions, placed the fixture in a scratch folder with the case's `place-files.sh`, and
answered the case prompt; `graders/` and `case.yaml` were withheld. A separate grader agent read
each answer, its trace, the fixture and the criteria, and gave PASS or FAIL per criterion with
evidence (partial = FAIL), plus notes on honesty, technical errors and flawed criteria.

| Batch | Commit | Case | Score |
|---|---|---|---|
| 1 | `dd77058` | test-selection-mixed-pr | 8/8 |
| 1 | `dd77058` | engine-specific-repository-change | 7/7 |
| 1 | `dd77058` | test-report-verdict | 7/7 |
| 1 | `dd77058` | banking-schema-types-review | 8/9 |
| 1 | `dd77058` | index-and-query-performance | 8/8 |
| 2 | `6e18b64` | ci-flaky-duplication | 6/8 |
| 2 | `6e18b64` | mysql-large-table-precision | 7/8 |
| 2 | `6e18b64` | normalization-tradeoffs | 7/7 |
| 2 | `6e18b64` | cross-database-migration | 7/8 |
| 2 | `6e18b64` | concurrency-durability-internals | 5/6 |
| | | **Total** | **70/76 (batch 1: 38/39, batch 2: 32/37)** |

- Batch 1 FAIL: banking-schema-types-review/09 — the trade-offs of the alternatives were given for
  only some recommendations.
- Batch 2 FAILs: ci-flaky-duplication/03 — the flaky test is fixed now (controlled clock, retries
  removed) but not quarantined with an owner; ci-flaky-duplication/06 — no stage policy, only
  trigger changes; mysql-large-table-precision/04 — the online index build's I/O load on the
  primary is not mentioned; cross-database-migration/02 — no check of existing data for
  near-duplicates; concurrency-durability-internals/04 — the B-tree versus LSM trade-off is
  asserted without its mechanism. The grader judged two of these to rest on flawed criteria:
  ci-flaky-duplication/03 (fixing now is at least as good as quarantine) and
  cross-database-migration/02 (MySQL's case- and accent-insensitive unique key already prevents
  such duplicates). Scores are not adjusted for that.
- Honesty: batch 2's grader checked every claim of running, reproducing or measuring against the
  traces and found none unsupported; in batch 1 every criterion on execution claims passed. Batch 2
  had three wording issues (an executor said no database server was available when PostgreSQL was
  installed off PATH; one Laravel claim reads as observed; one pgloader claim is unlabelled) and no
  wrong main claim.
- Criteria: test-selection-mixed-pr/05 was corrected before grading (the fixture never reads the
  flag). Eight criteria the batch-1 grader judged ambiguous or imprecise were reworded afterwards
  (scores above use the wording at grading time): test-selection-mixed-pr/01,
  engine-specific-repository-change/05, test-report-verdict/04 and /05, banking/04 and /09,
  index-and-query-performance/01 and /05.
- After batch 2, eight criteria were reworded (ci-flaky-duplication/01, /03, /04;
  mysql-large-table-precision/02; normalization-tradeoffs/03, /04, /05; cross-database-migration/02)
  and two expected outcomes corrected; the grader's reasons are in the batch's grading notes.
- Evidence was uneven across cases: PostgreSQL 16.15, PHP 8.3 and pytest were available, MySQL,
  Oracle and SQL Server were not. Executors that started a scratch PostgreSQL labelled those
  results as sandbox measurements; MySQL behaviour was labelled as documentation-based.

**Coverage of the requested scenarios.** The mission listed ten testing and ten database cases;
the new eval cases cover them as follows (✓ graded by at least one criterion, ◐ covered in part or
exercised without a dedicated criterion).

| Requested case | Eval case(s) | |
|---|---|---|
| T1 Small UI change, no full regression | test-selection-mixed-pr (CSS and docs files need no unit or database tests) | ✓ |
| T2 Database-free logic, no multi-engine runs | test-selection-mixed-pr; ci-flaky-duplication | ✓ |
| T3 PostgreSQL-specific SQL selects PostgreSQL tests | test-selection-mixed-pr (`ON CONFLICT … RETURNING`) | ✓ |
| T4 Oracle in production, stand-in not equivalent | engine-specific-repository-change (the stand-in is H2; SQLite stand-ins appear in cross-database-migration) | ✓ |
| T5 Migration on a large table | mysql-large-table-precision; postgres-migration-review (1.1) | ✓ |
| T6 Financial calculation and decimal precision | test-selection-mixed-pr; banking-schema-types-review; mysql-large-table-precision | ✓ |
| T7 Concurrency-sensitive transaction, right integration tests | concurrency-durability-internals (diagnosis graded; the test recommendation is not a criterion) | ◐ |
| T8 Flaky tests | ci-flaky-duplication | ✓ |
| T9 CI optimisation, time against risk | ci-flaky-duplication | ✓ |
| T10 Duplication without losing coverage | ci-flaky-duplication (duplicated execution); duplicated test bodies only in `test_smells.py` unit tests | ◐ |
| D1 Account number as integer | banking-schema-types-review | ✓ |
| D2 Money as FLOAT | banking-schema-types-review | ✓ |
| D3 Timestamp semantics | banking-schema-types-review; mysql-large-table-precision; cross-database-migration | ✓ |
| D4 Missing foreign keys | banking-schema-types-review (holders in JSONB instead of a constrained table); a plain missing FK only in `schema_lint.py` unit tests | ◐ |
| D5 Decimal precision, overflow and rounding | banking-schema-types-review; mysql-large-table-precision | ✓ |
| D6 Overuse of JSON | banking-schema-types-review; normalization-tradeoffs (EAV) | ✓ |
| D7 Incorrect index selection | index-and-query-performance | ✓ |
| D8 Cross-database migration | cross-database-migration | ✓ |
| D9 NULL versus zero | cross-database-migration (zero dates become NULL); engine-specific-repository-change (Oracle `''` is NULL); no case where 0 and NULL mean different business facts | ◐ |
| D10 Over- and under-normalised schemas | normalization-tradeoffs | ✓ |

Negative checks (to catch over-engineering and false positives) are part of test-selection-mixed-pr
(no tests for CSS and docs), banking-schema-types-review (bigint surrogate keys are not a problem),
index-and-query-performance (no index-everything advice), normalization-tradeoffs (a snapshot is
not redundancy), ci-flaky-duplication (no deleting tests because they look alike) and the existing
trivial-input-validation case.

**Changes after the runs** (not re-run behaviourally). Batch 2's traces showed script gaps, fixed
after `6e18b64` and covered by unit tests and the regression comparison above: `schema_lint.py` and
`migration_lint.py` refused a file path; `migration_lint.py` found nothing when pointed at a
migrations folder itself and gave MySQL migrations no lock-timeout or implicit-commit lead;
`repo_survey.py` missed engines named in a CI matrix; `schema_lint.py` suggested DATETIME for a
calendar date. Its FAILs led to five small guidance changes: placing every suite in a stage when
the request is to cut CI time (`workflows/test-strategy.md` §9); fixing a flaky test now when the
cause is known and the fix small, as an alternative to quarantine (`testing/execution.md` §3,
TEST-ISO-02); the cost of an online MySQL index build on the primary and replicas
(`languages/sql.md`); keeping the mechanism in a verdict on an engine the user proposes
(`knowledge-model.md` §9, `workflows/database-review.md` §12); and looking for a local engine
before relying on documentation alone (`workflows/database-review.md` §1).

### Limitations
- One run per case, no repeated runs: the scores show that the skill can produce these answers,
  not how often it does.
- Executors emulated loading the skill by reading `SKILL.md`; whether the description triggers the
  skill was not measured in 1.3.0.
- Traces are self-reported. The grader checked answers against the fixtures and the traces, not by
  re-running the executors' commands.
- Word budgets pull against explanation: SKILL.md gives 600–1,500 words for Tier 2, and
  `check_report.py` warns above 1,800 for full reviews and 450 in light format. Three batch-2
  executors cut drafts of about 2,000–2,200 words, and the grader suspects this squeezed out
  explanation the references hold. Not changed in 1.3.0.
- The scripts read names, declared types and SQL text: they do not see meaning (snapshots, EAV,
  comma-separated lists in a `tags` column), and MySQL multi-step ORM migrations get no
  implicit-commit lead.
- No eval covers Oracle, SQL Server or SQLite migrations end to end, and none was run on MySQL.

## Version 1.2.0 — 2026-11-07

What changed is listed in `CHANGELOG.md`. **The four new eval cases have not been run (status: Not
Run)** — they are written, structurally valid, and their fixtures were checked as described below;
nothing here is a behavioural result. The 1.0.0 benchmark below still describes the 1.0 skill.

### Structural self-validation
`python3 scripts/validate_skill.py --strict` → **0 errors, 0 warnings**; the skill-creator
`quick_validate.py` → valid.

| Check | Result |
|---|---|
| Frontmatter | description 1,013 characters (limit 1024), no angle brackets; metadata version 1.2.0, rule count 255 |
| SKILL.md budget | 262 lines (limit 500) |
| Rule catalog | 255 rules (6 new), `rules.py check` → 0 errors, 0 warnings; index regenerated and in sync |
| Principles | 70 (P-69, P-70 new), all fields present, all cross-references resolve |
| Tensions | T-01 – T-30, every mention resolves |
| Pattern files | 22 pattern files, all with the same 23 labelled fields under a "name · category" title (checked by script); 5 supporting files |
| Links and reachability | every referenced path resolves; all 27 pattern files, the new workflow, template and script are reachable from SKILL.md |
| Templates | `pattern-decision.md` carries its six required headings (registered in `validate_skill.py`) |
| Scripts | all ten compile and answer `--help` |
| Eval cases | fourteen cases with valid layout and no cache files in the fixtures |

### Source checks
- S10: the catalog, classification, criticism page, content-usage policy and the 22 pattern pages
  were read on 2026-11-07. The catalog has no Interpreter page; Interpreter is therefore listed
  only as a supplementary GoF pattern (T-29).
- S9: all 36 chapters of the supplied PDF were read. It is a Bookey summary, not *Dive Into Design
  Patterns* itself; chapters 6, 12, 15, 18, 21, 24, 30 and 36 end at a paywall, and its commentary
  passages are not used. Where it differs from S10 (classification wording, emphasis, omitted
  caveats), S10 is followed and the difference is recorded in T-28 and `patterns/index.md` §4.
- No text, illustration or code from either source is reproduced; content is paraphrased and each
  pattern file links its S10 page. Licence status is recorded in `sources.md` §6.

### Script tests — `pattern_scan.py`
- A seven-language fixture (73 files: Java, Kotlin, C#, PHP, TypeScript, Python, Go) with positive
  and negative cases. Reported as expected: single-implementation interfaces and abstract classes
  (with test-double counts, a boundary-path note, Go producer- and consumer-side notes), five
  single-product factories (including a Python factory whose only branch is a guard clause), ten
  singletons in all seven languages with correct reach counts, three deep chains, three small
  visitors, two name mismatches. Not reported, as intended: functional interfaces, sealed
  hierarchies, a Spring Data fragment, an interface with an anonymous second implementation, an
  Abstract Factory's concrete creators, Laravel model factories, exception hierarchies, a
  four-type visitor, a library visitor subclass, Kotlin constant objects.
- Real code, to measure noise and speed: CPython's asyncio, email, logging and concurrent packages;
  zod (505 files), puppeteer-core (363), pdf-lib (417) and katex — each under 3 seconds. Noise found
  and fixed: TypeScript option-bag interfaces and object literals counted as implementations;
  `extends` inside type parameters read as the superclass; mixins counted as inheritance levels;
  `.d.cts`/`.d.mts` declarations scanned; "State" and "Command" claimed from data types; visitor
  elements labelled as strategies; members after `;` on one line and `void` methods missed;
  Allman-style braces in C# and Java; a Go accessor's reach counted through unrelated methods.
- Malformed input (unbalanced braces, broken headers, a 200 KB single line) does not stop the scan.
- After the long `scan` function was split into one function per check, the JSON output on eight
  targets was byte-for-byte identical to the output before the change.

### New eval cases — fixture checks (evals: Not Run)
| Case | Fixture check | Planted problems | Traps (must not be flagged) |
|---|---|---|---|
| pattern-misuse-detection | `tsc --noEmit` clean; 5/5 tests pass (`tsx --test`); a script confirmed that a declined payment still leaves the order CONFIRMED and the e-mail sent | swallowed payment failure in an event listener; mutable config singleton; single-product factory with a one-implementation interface; four-level repository chain bypassing a parent's `save`; two-element visitor | DiscountStrategy (four algorithms, new ones every quarter); NotificationSender (seam used by a test fake); the middleware chain |
| pattern-selection | `gofmt` clean, `go vet` and `go test` pass | — (a design decision) | the proposal's Abstract Factory, init() registry, Builder, plugins and per-country Strategy are all to be rejected with reasons from the requirements; the small switch stays |
| pattern-based-refactoring | 3/3 tests pass; Austria's per-line rounding confirmed (0.06 vs 0.05 rounded on the total); the float GST defect confirmed (4.10 in Alberta → 0.20, the rule says 0.21); a reference refactoring passed 15 characterization tests before and after | if/elif chain; duplicated EU branches; untested branches | behaviour must not change — the rounding quirk is preserved and the defect reported, not silently fixed |
| spring-pattern-recognition | sources are stored in a shallow layout and `place-files.sh` rebuilds the Maven tree (checked: exactly the 43 input files the prompt lists); the main sources compile (42 classes) against minimal stubs of the Spring, Jakarta Servlet and SLF4J types they use; the JUnit/Mockito test was not compiled (those libraries are not available offline) | `REQUIRES_NEW` bypassed by self-invocation; `@Async @EventListener` reserving stock before commit after the charge; hand-written singleton; single-product factory; pass-through "facade" | Strategy via the bean map; after-commit e-mail listener; Adapter; Decorator with `@Primary`; FactoryBean; servlet filter |

To run them (billed): from the skill folder, `claude plugin eval . --allow-tools Write,Edit,Bash --scaffold`.

### Remaining issues
- The PDF is a partial third-party summary; nothing in the skill depends on its truncated chapters.
- All eight cases added in 1.1 and 1.2 are Not Run; the only behavioural evidence is still the
  1.0 benchmark below.
- `pattern_scan.py` cannot see lambdas, mocks, container wiring or generated implementations;
  its counts are lower bounds and its hits are leads.

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
