# Review: <change or module name>

<!-- Template for Tier 2–3 code, PR and security reviews. Summary, Scope, Verification and
     Findings are required; drop other sections when they would be empty. Write in plain words
     for the reader. Validate with: python scripts/check_report.py <this file> -->

## Summary
**Verdict:** approve | approve with suggestions | changes requested | blocked
<!-- 2–4 sentences: what the change does, the overall assessment, the most important issue. -->

## Scope
- **Reviewed:** <diff range / files / modules, and depth in plain words: read in full, or traced end to end>
- **Context read:** <callers, configs, ADRs, docs consulted>
- **Not reviewed:** <generated files, lockfiles, areas out of scope — and why>
- **Assumptions:** <e.g. "assuming the auth middleware in routes/api.php applies to this group">

## Verification
<!-- Only what was actually run, with results. Never report an unrun check as passing. -->
| Check | Command | Result |
|---|---|---|
| Tests | `<command>` | <e.g. 142 passed, 0 failed> / not run: <reason> |
| Lint / types | `<command>` | <result> |
| Security scan | `python scripts/security_scan.py <paths>` | <n leads, n confirmed after tracing> |

## Findings
<!-- Most severe first. One block per finding. Header format is fixed:
     ### F-<nn> [<blocker|major|minor|nit> · <confirmed|likely|possible>] <short title> -->

### F-01 [major · likely] <short title>
- **Where:** `path/to/file.ext:LINE`
- **Type:** <defect | vulnerability | reliability-risk | performance | tech-debt | architecture-risk | test-gap | question> · **Rule:** <one RULE-ID, optional>
- **What:** <what is wrong, concretely>
- **Why it matters:** <impact, who/what is affected, likelihood>
- **Fix:** <concrete change in the project's idiom; code sketch if useful>
- **Evidence:** <how it was established: traced path, test output, or what remains assumed>

<!-- Security findings also add:
- **Source → sink:** <entry point and actor> → <controls passed or missing> → <sink>
- **Verify with:** <WSTG test ID, e.g. WSTG-ATHZ-04> -->

## Also noticed (out of scope)
<!-- Brief bullets; pre-existing issues not made worse by this change. Omit if none. -->

## Strengths
<!-- Optional, one or two lines when genuinely useful to the author. -->
