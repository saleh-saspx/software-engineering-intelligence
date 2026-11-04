# Skill Benchmark: software-engineering-intelligence

**Model**: claude-opus-5-5
**Date**: 2026-11-04T08:50:02Z
**Evals**: billing-architecture-decision, go-quick-review, spring-repo-assessment, trivial-input-validation (1 run each per configuration)

## Summary

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 97% ± 6% | 82% ± 10% | +0.16 |
| Time | 897.9s ± 682.0s | 548.0s ± 360.6s | +349.9s |
| Tokens | 190130 ± 104035 | 117763 ± 41593 | +72366 |

## Analyst notes

- Analyst: only the four cases affected by the iteration-1 problems were re-run with the skill; the without_skill outputs are reused byte-for-byte from iteration 1 (the baseline does not depend on the skill) and regraded against the updated assertions.
- Analyst: assertions were revised after iteration 1 on grader feedback — bundled checks split, over-literal wording fixed, an unasserted planted bug added (unescaped SKU), and user-value checks added for length, verdict placement and plain language. Pass rates are therefore not directly comparable across iterations.
- Analyst: reply length now tracks the baseline or beats it — go 1,741→512 words (baseline 1,104), trivial 160→71 (151), billing 4,952→2,018 (1,966), spring 7,386→3,067 (3,044) — while every finding in the Go review was reproduced and confirmed.
- Analyst: billing-architecture-decision still fails for both configurations on the ADR revisit-trigger assertion; a workflow note was added afterwards (state whether each relevant ADR still holds and what would trigger revisiting it) but not re-benchmarked.
- Analyst: spring-repo-assessment with the skill took 1,731 s / 320k tokens (baseline 982 s / 168k), above the case's 1,200 s budget, mainly from reproducing eight defects in a harness; guidance to reproduce selectively in assessments was added afterwards but not re-benchmarked.
