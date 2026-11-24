# Grading — batch 1 (independent grader agent, 2026-11-24)

Skill version under test: working tree at commit dd77058 (before the adversarial-review fixes).
Executors: one subagent per case, instructed to treat the working-tree SKILL.md as its instructions,
working in a scratch copy of the fixture; graders/ and case.yaml were withheld from executors.
Grader: a separate subagent that read the answers, traces, fixtures and criteria.

| Case | Score |
|---|---|
| test-selection-mixed-pr | 8/8 (criterion 05 revised before grading: the fixture never reads the flag) |
| engine-specific-repository-change | 7/7 |
| test-report-verdict | 7/7 |
| banking-schema-types-review | 8/9 (FAIL 09: trade-offs of the alternatives given for only some recommendations) |
| index-and-query-performance | 8/8 |
| Overall | 38/39 |

Criteria the grader judged ambiguous or imprecise (revised after this batch; scores above use the
wording at grading time): test-selection-mixed-pr/01 ("one-line reason"), engine-specific/05
("merely"), test-report-verdict/04 (PostgreSQL 16 known only from the plan), test-report-verdict/05
(where the next step goes), banking/04 ("and/or"), banking/09 (how much trade-off discussion),
index-and-query-performance/01 ("whole 90-day range" — the scan stops once the page fills),
index-and-query-performance/05 ("forces a scan per row" — the planner hash- or merge-joins).

Other observations: executors were told no PostgreSQL was available, but PostgreSQL 16.15 binaries
were installed; two executors started a throwaway server (synthetic data, labelled as such), one did
not — evidence is uneven across cases. The test-selection fixture's DB test lacks an import
(unintended); the executor found it.
