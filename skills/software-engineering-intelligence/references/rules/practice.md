# Practice rules: review conduct (REV-*) and agent conduct (AGT-*)

How reviews are run and how an AI coding agent must behave when applying this skill —
evidence, scope, minimal change, conventions, uncertainty, self-review, safety. Field meanings:
`index.md`. The AGT rules apply to every task, including the smallest.

Areas: REV-CONDUCT · AGT-EVID · AGT-SCOPE · AGT-MIN · AGT-CONV · AGT-UNC · AGT-SELF · AGT-SAFE

## Review conduct

### REV-CONDUCT-01 · Know the review's purpose, criteria and context before starting
- level: strong | severity: — | provenance: direct
- sources: S5 Code Review Do's and Don'ts (know what is expected — security, functionality, maintainability, style; domain knowledge); S5 How to Use the Code Review Guide (types of review)
- why: A review without a stated purpose produces a random mix of nits and misses what matters.
- signals: Reviews that start commenting before reading the PR description, linked issue or design.
- fix: Establish: what the change is for, which review type (security, design, maintainability, pre-merge gate), the risk level, and the project's standards.
- related: REV-CONDUCT-03, AGT-SCOPE-01

### REV-CONDUCT-02 · Don't manufacture findings
- level: strong | severity: — | provenance: direct
- sources: S5 Code Review Do's and Don'ts (you don't have to find fault to do a code review; constant criticism loses credibility)
- why: Padding reviews with weak findings buries the important ones and teaches authors to ignore reviews.
- signals: Every review having the same number of comments; findings that are preferences presented as problems.
- fix: Report what matters; say "no significant issues found in <scope>" when that is the result; batch nits or omit them.
- related: TD-CLS-03, REV-CONDUCT-03

### REV-CONDUCT-03 · Findings are located, explained, actionable and honestly labelled
- level: strong | severity: — | provenance: synthesized
- sources: S5 Code Review Do's and Don'ts (defined artifacts as the result of a review; process for changes); P-52; X14
- why: "This is bad" can't be acted on; a finding needs a place, a reason, a fix and an honest confidence.
- signals: Comments without file/line, without why, or phrased as commands without rationale; questions disguised as demands.
- fix: Each finding: location, what, why (impact), suggested fix, severity, confidence, rule ID. Phrase genuine questions as questions.
- verify: `scripts/check_report.py` validates report structure.
- related: AGT-EVID-01, REV-CONDUCT-02

### REV-CONDUCT-04 · Match review effort to change size and risk
- level: contextual | severity: — | provenance: direct
- sources: S5 Methodology (inspection rate — about 250 lines per hour given as an example baseline for estimating duration, explicitly not a quality measure); S5 Code Review Do's and Don'ts (don't rush); S8 §9.2.2 (inspection data: fast preparation finds fewer defects — slow down to speed up), §9.3.2 (small changes get careful reviews within hours; giant pull requests should be split)
- why: Large diffs get rubber-stamped; tiny low-risk diffs don't need a full audit.
- signals: 2,000-line PRs reviewed in minutes; three-line config changes getting architecture essays.
- fix: Suggest splitting large changes; scale depth with risk using the triage in SKILL.md; for large reviews, state which parts got deep vs. light attention.
- related: AGT-SCOPE-01, REV-CONDUCT-05

### REV-CONDUCT-05 · Judge whether the change leaves the repository healthier, not whether you would have written it that way
- level: strong | severity: — | provenance: direct
- sources: S8 §9.3 (Code Reviews: Check Intent and Trust — the repository-stewardship principle; approve clear improvements even if a marginally better version is imaginable; small related clean-ups are fine when proportionate, larger ones go in separate changes; "the reviewer will catch it" and approving merely to unblock are corrosive), §9.3.1 (Invested Expert Reviewers — a reviewer without context says so and routes the change)
- why: Reviews that demand the reviewer's preferred design stall improvements and train authors to batch work into giant changes; reviews that rubber-stamp let defects through. The question that balances both is whether the codebase is better after the merge.
- signals: Blocking comments that propose an equivalent alternative; long threads about taste; approvals given only to unblock; reviewers commenting on areas they don't know without saying so; unrelated clean-ups demanded inside a feature change.
- fix: Check intent (does it do what was meant, and is that right?) and health (is the repository better after it?); approve improvements and mark preferences as optional; ask for large or separable clean-ups as follow-up changes; say when you lack context and route the change to an owner.
- related: REV-CONDUCT-02, REV-CONDUCT-04, AGT-MIN-02, DLV-OWN-01

## Agent conduct

### AGT-EVID-01 · Report only verification you actually observed
- level: mandatory | severity: — | provenance: synthesized
- sources: S7 §1.2 (testing reveals bugs but cannot show their absence); S8 §13.2.10 (require the same evidence from AI as from humans: green tests, a passing review), §13.8 (own intent and verification); X14
- why: A claim that tests pass, a build succeeds or a fix works is only true if it was run and seen. False claims destroy the value of every other statement.
- signals: "All tests pass" without a test run in the transcript; "this fixes the bug" without reproduction; "verified" for reasoning-only checks.
- fix: Run the relevant commands and quote the outcome (counts, exit status); if you couldn't run them, say "not run" and why; describe reasoning-based checks as reasoning.
- verify: Every verification claim in the final message maps to an executed command or is labelled as unexecuted.
- related: AGT-EVID-02, AGT-EVID-03

### AGT-EVID-02 · Distinguish compiling, testing, analysing and being correct
- level: mandatory | severity: — | provenance: direct
- sources: S7 Preface, §1.2, §1.3 (undecidability; approximation; soundness depends on purpose)
- why: Type-checking proves type consistency, tests prove the tested cases, analysers prove what they are sound for — none proves the program correct.
- signals: "Type-checks, so it works"; "linter is clean, so it's secure".
- fix: Report each kind separately: build/type-check, tests (which), static analysis (which tools, what they cover), manual reasoning, and residual risk.
- related: AGT-EVID-01, SEC-PROC-03, DLV-SA-01

### AGT-EVID-03 · Absence of findings is not evidence of absence
- level: mandatory | severity: — | provenance: synthesized
- sources: S7 §1.2; S6 §2.2 (There is No Silver Bullet)
- why: A clean review only says the reviewed scope, with the methods used, revealed nothing.
- signals: "The system is secure"; "no bugs".
- fix: Phrase results with scope and method; list what wasn't examined.
- related: SEC-PROC-04, AGT-SCOPE-01

### AGT-SCOPE-01 · State the real scope of every review or assessment
- level: mandatory | severity: — | provenance: extension
- sources: X14; P-36
- why: Reading five files and reporting on "the repository" is a false statement about coverage.
- signals: Repository-level conclusions from sampled files; no list of what was read.
- fix: Record files/modules read fully, skimmed, and not read; for sampled reviews, say how the sample was chosen (hotspots, entry points) and qualify conclusions accordingly.
- verify: `scripts/check_report.py` requires a scope section.
- related: AGT-EVID-03, REV-CONDUCT-04

### AGT-SCOPE-02 · Do what was asked; report the rest briefly
- level: strong | severity: — | provenance: extension
- sources: X14
- why: Unrequested changes expand review cost and risk and surprise the user.
- signals: Refactoring unrelated files during a bug fix; changing APIs while "cleaning up".
- fix: Implement the request; list notable out-of-scope findings in a short "also noticed" section; offer, don't do.
- except: A blocker-class issue (e.g. an exposed secret, an exploitable vulnerability) discovered in passing is raised prominently even if out of scope.
- related: AGT-MIN-01

### AGT-MIN-01 · Make the smallest change that fully solves the problem
- level: strong | severity: — | provenance: synthesized
- sources: S1 Ch.1 (The Boy Scout Rule — leave it a little better); S3 Ch.1, Principle 5; T-10
- why: Small diffs are reviewable and revertible; incidental reformatting and renames hide the real change.
- signals: Diffs dominated by whitespace/import reordering; renamed symbols unrelated to the task.
- fix: Touch only what the task needs; small, clearly related improvements to touched code are fine; anything bigger becomes a separate, proposed change.
- related: AGT-MIN-02, CODE-STRUCT-02

### AGT-MIN-02 · Never mix refactoring and behaviour change in one step
- level: strong | severity: — | provenance: synthesized
- sources: S1 Ch.14 (On Incrementalism); S1 Ch.16 (First, Make It Work; Then Make It Right); X3
- why: When structure and behaviour change together, neither the reviewer nor the tests can tell which caused a difference.
- signals: A single commit/step that restructures and changes outputs.
- fix: Refactor first (tests unchanged and green), then change behaviour (tests updated deliberately) — separate commits or clearly separated steps.
- related: TEST-REG-02, TD-DEC-03

### AGT-CONV-01 · Discover local conventions before writing code
- level: strong | severity: — | provenance: direct
- sources: S1 G24 (Follow Standard Conventions); S1 Ch.5 (Team Rules); S1 G11 (Inconsistency)
- why: Code that follows its neighbours is easier to review and maintain than code that follows a generic ideal.
- signals: New code with different error handling, naming, folder placement or test style than adjacent code.
- fix: Before implementing, read neighbouring files, configs (formatter, linter, tsconfig, phpstan, pyproject), and existing tests; mirror their patterns unless a rule of level `mandatory` says otherwise.
- related: AGT-CONV-02, CODE-NAME-05

### AGT-CONV-02 · Don't introduce new dependencies, patterns or frameworks silently
- level: strong | severity: — | provenance: synthesized
- sources: ARCH-FIT-03 rationale (S1 G11; S4 construction techniques)
- why: Each new library or pattern is a long-term commitment for the team, not a local choice.
- signals: New packages in a manifest the user didn't ask for; a second state-management or HTTP library; a new architectural pattern in one file.
- fix: Prefer existing dependencies and patterns; if a new one is warranted, say so explicitly with the reason, and suggest an ADR for significant ones.
- related: DLV-DEPS-01, ARCH-DEC-01

### AGT-UNC-01 · Surface assumptions and uncertainty; ask when a wrong guess is expensive
- level: strong | severity: — | provenance: extension
- sources: X14; `../knowledge-model.md` §5
- why: Silent assumptions become wrong code; explicit ones can be corrected cheaply.
- signals: Implementations that pick one interpretation of an ambiguous requirement without saying so.
- fix: State assumptions next to the decision; ask before irreversible or costly work when the request is genuinely ambiguous; otherwise proceed with the most reasonable reading and say which one.
- related: AGT-UNC-02, AGT-SAFE-01

### AGT-UNC-02 · Don't invent facts about code, libraries or vulnerabilities
- level: mandatory | severity: — | provenance: extension
- sources: X14; S5 A9 (use component inventories and advisories)
- why: Plausible-sounding APIs, config keys, CVE numbers or library behaviours that don't exist send people down wrong paths.
- signals: Citing a function or option you haven't seen in the code or docs; quoting CVE IDs or versions from memory.
- fix: Verify in the codebase, installed package source, official docs or tool output; otherwise mark as unverified.
- related: AGT-EVID-01, SEC-DEP-01

### AGT-SELF-01 · Self-review your own change before declaring it done
- level: strong | severity: — | provenance: synthesized
- sources: X14; SKILL.md quick checklist; S8 §13.2.6 (AI produces plausible-looking defects; reviewer attention is the scarce resource), §13.2.7 (generated tests can encode the code's misunderstanding — never trust a test you have not seen fail), §13.7.2 (agents overrate their own output; use a separate, sceptical check)
- why: Most defects in generated code are catchable by re-reading the diff with fresh criteria — and generated tests that merely restate the code's behaviour hide the rest.
- signals: Declaring completion straight after writing code; tests written by the same pass that wrote the code and never seen failing.
- fix: Re-read the full diff against the quick checklist in SKILL.md (correctness, errors, security, tests, conventions, scope); take expected values for your tests from the requirement, not from the code's output (TEST-ORACLE-01), and see each new test fail at least once; run the relevant checks; fix what you find before reporting.
- related: AGT-EVID-01, AGT-MIN-01

### AGT-SAFE-01 · No destructive or irreversible actions without explicit confirmation
- level: mandatory | severity: — | provenance: extension
- sources: X14
- why: Deleting files, dropping data, rewriting history, running migrations against shared databases or force-pushing cannot be undone by a follow-up message.
- signals: Plans that include `rm -rf`, `DROP`, `git push --force`, production migrations, mass file moves.
- fix: Prepare the change, explain the effect, and wait for confirmation; prefer reversible alternatives (moves to a backup location, new branches, dry runs).
- related: DATA-MIG-01, DLV-REL-01
