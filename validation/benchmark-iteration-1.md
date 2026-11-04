# Skill Benchmark: software-engineering-intelligence

**Model**: claude-opus-5-5
**Date**: 2026-11-04T08:50:02Z
**Evals**: billing-architecture-decision, go-quick-review, laravel-pr-review, safe-refactor-shipping, spring-repo-assessment, trivial-input-validation (1 run each per configuration)

## Summary

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 94% ± 9% | 91% ± 11% | +0.04 |
| Time | 998.2s ± 453.1s | 670.1s ± 378.3s | +328.0s |
| Tokens | 200012 ± 68239 | 130706 ± 41589 | +69306 |

## Analyst notes

- Analyst: single run per configuration on six cases — differences of one assertion are within noise.
- Analyst: laravel-pr-review, billing-architecture-decision and safe-refactor-shipping are saturated (both configurations 100%); the base model already finds every planted defect. Only spring-repo-assessment discriminated (scope statement and explicit debt/defect/vulnerability classification).
- Analyst: independent graders found the skill added structure, evidence labels, scope and classification, not more or more accurate findings; the baseline sometimes found extra issues (e.g. framework-version anomaly in git history, open-in-view, roadmap-specific blockers).
- Analyst: with-skill replies were 1.5–2.6× longer and leaked internal vocabulary (rule IDs as prose, coverage codes, script paths); escalation rules overrode a 'quick review' request. These drove the iteration-2 changes.
- Analyst: cost — with-skill runs averaged +69k tokens and +328 s per task.
