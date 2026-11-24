# Grading — batch 2 (independent grader agent, 2026-11-24)

Skill version under test: working tree at commit 6e18b64 (after the adversarial-review fixes).
Executors and grader as in batch 1; executors were told tools might be installed and to check and
label what they used. Full per-criterion grading with quotes, trace steps and fixture checks:
`GRADING-batch2-detail.md`.

| Case | Score |
|---|---|
| ci-flaky-duplication | 6/8 (FAIL 03: no visible quarantine with an owner — the answer fixes the test now and drops the retries, which the grader judged at least as good; FAIL 06: no stage policy, only trigger changes) |
| mysql-large-table-precision | 7/8 (FAIL 04: the index build's I/O load on the primary is not mentioned) |
| normalization-tradeoffs | 7/7 |
| cross-database-migration | 7/8 (FAIL 02: no check of existing data for near-duplicates — the grader found this element wrong about the fixture: MySQL's ai_ci unique key already prevents them) |
| concurrency-durability-internals | 5/6 (FAIL 04: the B-tree versus LSM trade-off is asserted, its mechanism not explained, although internals.md §4 has it and was read) |
| Overall | 32/37 |

Criteria revised after this batch (scores above use the wording at grading time): ci-flaky/01
("per workflow run"), /03 (fix now or quarantine), /04 (counts per run); mysql/02 (ALGORITHM/LOCK
is a guard, not a way to perform the change); normalization/03, /04, /05 (examples, the stopping
rule applied to the address chain, when each alternative fits); cross-database/02 (no data check
for near-duplicates; ICU collation accepted). The expected outcomes of ci-flaky-duplication and
cross-database-migration were corrected to match.

Honesty: no fabricated runs — every claim of running, reproducing or measuring matches a trace
step; MySQL behaviour is labelled as documentation-based or "likely". Wording issues: the
ci-flaky executor said no database server was available (PostgreSQL 16.15 was installed off
PATH); the mysql executor's "(migrate --pretend shows them)" reads as observed; the
cross-database executor's claim about what pgloader copies is unlabelled.

Technical: no main claim wrong. Imprecisions: errored tests are counted as passes by summary.sh
(the answer said "not counted"); the cost of re-running a partly applied MySQL migration is
understated; the email fix restores case- but not accent-insensitivity.

Skill-side observations (traces against 6e18b64) and what was changed afterwards (not re-run
behaviourally): engines in a CI matrix (repo_survey now reads them); single-file PATH (schema_lint,
migration_lint accept it); DATETIME advice for a calendar date (now DATE); no MySQL lock-timeout or
implicit-commit lead (added); a migrations folder as PATH found nothing (fixed); no requirement to
place suites in stages when cutting CI time (test-strategy §9); quarantine as the only response to
a flaky test (execution.md §3, TEST-ISO-02: fix now when small); the I/O cost of MySQL online index
builds (sql.md); verdicts on a proposed engine without the mechanism (knowledge-model §9,
database-review §12); finding a local engine was ad hoc (database-review §1). Word budgets: SKILL.md
gives 600–1,500 words for Tier 2 and check_report.py warns above 1,800 for full reviews and 450 in
light format; the grader suspects budget pressure squeezed out explanation — not changed.
