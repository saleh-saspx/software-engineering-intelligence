# Assessment: <repository or system name>

<!-- Template for repository, architecture and technical-debt assessments (Tier 3).
     Validate with: python scripts/check_report.py <this file> -->

## Summary
<!-- Executive summary, at most ~300 words: goal, the 3–5 most important conclusions, what to do
     first. Plain words — no rule IDs, coverage codes or tier numbers here. -->

## Scope
- **Goal:** <onboarding | due diligence | debt audit | pre-release | architecture fit | security posture>
- **Review type:** <full review | sampled review — sample chosen by: hotspots, risk, entry points>
- **Coverage:**

| Area / module | Coverage (inventoried / skimmed / read / traced) | Notes |
|---|---|---|
| <module> | read | <…> |

- **Not covered:** <areas, artifacts, runtime/infra aspects>
- **Assumptions:** <roadmap, scale, team, environment>

## Verification
| Check | Command | Result |
|---|---|---|
| Build | `<command>` | <result / not run: reason> |
| Tests | `<command>` | <result> |
| Survey | `python scripts/repo_survey.py <path>` | <ran> |
| Hotspots | `python scripts/hotspots.py <path>` | <ran; history window> |
| Dependencies | `python scripts/deps.py <path>` | <cycles / violations found> |
| Security leads | `python scripts/security_scan.py <path>` | <n leads; n traced> |
| Migration leads | `python scripts/migration_lint.py <path>` | <n leads; n confirmed> (if the repo has migrations) |
| Test-suite leads | `python scripts/test_smells.py <path>` | <n leads; n confirmed> |

## System overview
<!-- Components, entry points, data stores, integrations, deployment units; intended vs actual
     architecture; style and fit (architecture-review.md §3). -->

## Quality profile
| Dimension | Rating | Confidence | Key evidence | Top action |
|---|---|---|---|---|
| Code quality | | | | |
| Architecture | | | | |
| Security | | | | |
| Testing & verification | | | | |
| Maintainability | | | | |
| Reliability, performance & scalability | | | | |
| Data management | | | | |

## Top risks
<!-- 3–7 items, each: consequence, evidence, finding IDs. -->

## Findings
<!-- Same block format as review-report.md:
### F-<nn> [<severity> · <confidence>] <title>
- **Where:** … - **Type:** … · **Rule:** … - **What:** … - **Why it matters:** … - **Fix:** … - **Evidence:** … -->

## Technical debt register
| ID | Item | Location | Type | Interest (evidence) | Principal | Decision | First step |
|---|---|---|---|---|---|---|---|

## Recommendations
- **Now:** <blockers; cheap, high-interest fixes>
- **Next:** <planned items with first steps>
- **Strategic:** <structural moves; ADRs to write>

## Limitations
<!-- What this assessment cannot tell you; where dynamic testing, load testing or specialist
     review is needed. -->
