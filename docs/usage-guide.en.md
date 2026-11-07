# Software Engineering Intelligence — Usage Guide

Version 1.2.0 · [راهنمای فارسی](usage-guide.fa.md)

Software Engineering Intelligence is a Claude skill that works like a senior engineering partner.
It implements and self-reviews changes, reviews code and pull requests, assesses repositories and
architectures, assesses, chooses and reviews design patterns, checks database migrations, plans
tests, threat-models features, prioritises technical debt, refactors safely and writes ADRs. This
guide explains how to install it, how to ask for what you need, and how to read what comes back.

## Contents
1. Install and update · 2. How the skill is activated · 3. Asking for the right depth ·
4. What to give it · 5. Tasks and example prompts · 6. Design patterns · 7. Reading the results ·
8. Scripts · 9. Templates · 10. Tips · 11. Troubleshooting · 12. Maintaining the skill

## 1. Install and update

### Claude apps (claude.ai on the web and the desktop app)
Requirements: a Pro, Max, Team or Enterprise plan, with **Code execution and file creation**
turned on in **Settings > Capabilities**. On Team and Enterprise plans an owner may first have to
enable Skills for the organisation.

1. Take `dist/software-engineering-intelligence.zip` from this repository (or from your local clone).
2. Open **Settings > Capabilities** and scroll to **Skills**.
3. Click **Upload skill** and choose the ZIP. Upload it as it is — the skill folder is at its root.
4. Make sure the skill is switched on in the list.

**Updating:** remove the old copy from the Skills list, then upload the new ZIP. Custom skills
belong to one account; every person uploads their own copy.

### Claude Code
- **As a plugin from this repository** (updates come from git):
  ```
  /plugin marketplace add saleh-saspx/software-engineering-intelligence
  /plugin install software-engineering-intelligence@software-engineering-intelligence
  ```
  If the repository is private, the machine needs git access to it (for example `gh auth login`).
  Update later with `claude plugin update software-engineering-intelligence@software-engineering-intelligence`
  — marketplaces other than Anthropic's do not auto-update unless you turn it on.
- **As a personal skill:** copy `skills/software-engineering-intelligence/` to
  `~/.claude/skills/software-engineering-intelligence/`. For a single project, copy it to
  `.claude/skills/` in that repository and commit it.
- **Check:** `/skills` lists it. Invoke it directly with `/software-engineering-intelligence`
  (personal skill) or `/software-engineering-intelligence:software-engineering-intelligence` (plugin).

### Claude API
Upload the same ZIP through the Skills API — see the
[skills guide](https://platform.claude.com/docs/en/build-with-claude/skills-guide) and the
[create-skill endpoint](https://platform.claude.com/docs/en/api/skills/create).

### For the scripts
Python 3.9 or newer (standard library only) and `git` for change-history analysis. The skill
works without the scripts; they add measurements and leads.

## 2. How the skill is activated
- **Automatically**, when you ask Claude to review, audit, assess, refactor, clean up, harden, test
  or design code, schemas or systems; to choose, review or remove a design pattern; or to implement
  a non-trivial change. Claude also uses it to review code it has just written. You do not need to
  name a methodology.
- **On request:** mention it by name ("use the software-engineering-intelligence skill to …"), or
  in Claude Code type the slash command shown above.
- **Any language:** write in English or Persian; the answer follows your language (technical terms
  may stay in English).

## 3. Asking for the right depth
The skill scales its effort to the risk of the task. Say how deep you want it to go:

| You want | Say something like | You get |
|---|---|---|
| A small change or a quick answer | "Fix the null check in `parse_date`", "What is the outbox pattern?" | The change and the test run, or a short answer (about 80 words) |
| A quick look | "Quick look at `handler.go` before I merge" | A light review: verdict and the few findings that matter (up to ~400 words) |
| A normal task | "Review this PR", "Implement pagination for `/orders`", "Refactor `calculate_shipping`" | The matching workflow and a structured report (usually 600–1,500 words) |
| A deep assessment | "Assess this repository and give me a prioritised backlog", "Threat-model the payment webhook" | Executive summary, risk or backlog table, scoped findings, what was and wasn't checked |

Risky areas — authentication, payments, migrations on large tables, concurrency, public APIs and
extension points, new trust boundaries, new dependencies, LLM features — make the analysis deeper,
not the answer longer. Ask for a "short answer" whenever you want one.

## 4. What to give it
- **The code:** a repository, folder, files or a diff. In Claude Code it reads your working
  directory; in the apps, upload the files (or a ZIP) or paste them.
- **The goal and the decision you face:** "we start subscription billing next quarter", "we merge
  tonight".
- **Constraints:** ADRs, team conventions, deadlines, compliance rules, "this is a prototype".
- **Facts it cannot see:** table sizes and write rates, traffic, how you deploy (rolling deploys?),
  which tests run in CI.
- **What you want back:** findings only, fixes applied, a plan, an ADR, or a short answer.

## 5. Tasks and example prompts

| Task | Example prompt | What happens |
|---|---|---|
| Implement and self-review | "Implement pagination for `/api/orders` and review your own change." | Small steps, tests added and run, then a self-review against the checklist |
| Pull-request review | "Review this PR before I merge — it adds the refund endpoint." | Verdict and findings ordered by severity; correctness and security first |
| Quick review | "Quick look at `handler.go` before I push?" | The light format: a few lines, blockers up front |
| Repository assessment | "Assess this repo's architecture and technical debt — we start subscription billing next quarter." | Survey, change hotspots, dependency cycles, quality profile, ordered backlog |
| Architecture decision | "Our lead wants hexagonal architecture for this service. Worth it?" | Fit to context, options with their costs, a recommendation and an ADR if useful |
| ADR | "Write an ADR for moving from REST polling to webhooks." | An ADR from the template: context, options, decision, consequences |
| Design patterns | "Which design patterns does `src/` use, and which are misapplied?" | See section 6 |
| Database and migrations | "We run migration 0042 tonight — `orders` has 40M rows. Anything to worry about?" | Lock and rewrite risks, compatibility with the code still running, a staged plan |
| Test strategy | "Our tests miss real incidents — propose a test strategy for the checkout rebuild." | Suite assessment and a risk-based verification plan |
| Technical debt | "Which parts of this codebase should we refactor first?" | Hotspots weighed against the roadmap; a debt register |
| Safe refactoring | "Refactor `calculate_shipping` without changing behaviour." | Characterization tests first, small steps, behaviour preserved |
| Security review | "Do a security review of the authentication and file-upload code." | OWASP-based findings traced from input to sink |
| Threat model | "Threat-model our new payment-webhook design before we build it." | Assets, trust boundaries, ranked threats, testable mitigations |
| Extensibility | "Customers want their own export formats — should we build a plugin system?" | Variation points backed by evidence, published contracts, isolation |

## 6. Design patterns
Version 1.2 adds judgment about the 22 classic design patterns (creational, structural and
behavioural, following the Refactoring.Guru catalog). Four kinds of requests:

- **Assessment** — "Map the design patterns in this service and tell me which ones are misapplied."
  You get one row per instance: the pattern, its participants (which class plays which role), the
  force it resolves, a verdict — justified, misapplied, unjustified or misnamed — the evidence and
  an action.
- **Selection** — "Strategy or State for order statuses — or neither?", "Here's the proposal; what
  should we build?" The answer states the problem and the force, the simplest no-pattern solution,
  the candidates and their look-alikes, the cost (types, indirection, wiring, tests), what becomes
  easier and harder, and when to revisit. **"No pattern" is a valid answer.**
- **Refactoring toward or away from a pattern** — "Replace this if/elif chain so adding a country
  is safe." Characterization tests come first, the cheapest structure wins (often a dict of
  functions or plain data), behaviour is preserved, and defects found on the way are reported
  separately instead of being silently changed.
- **Implementation review** — "Review the decorator chain around our HTTP client." It checks the
  participants, the wiring and its order, contract tests shared by all implementations, failure
  behaviour, and that security wrappers cover every path.

Tips: say what changes often ("we add a discount type every quarter") — a pattern is justified by
the change it absorbs. Name your framework: Spring, Laravel, Go, Python and TypeScript/React
mechanisms are described by what they actually do. To record a choice, ask for the
pattern-decision template.

## 7. Reading the results
- **Scope and checks:** what was read, skimmed and skipped; which commands ran and their results —
  or "not run" and why.
- **Verdict** (reviews): approve · approve with suggestions · changes requested · blocked.
- **Findings** look like this:
  ```
  - [major · likely] src/orders/service.py:42 — what is wrong and why it matters. Fix: … (DATA-TXN-03)
  ```
- **Severity:** blocker (fix before merge or release) · major · minor · nit (never blocks).
- **Confidence:** confirmed (executed, reproduced or fully traced) · likely (strong static evidence)
  · possible (needs verification).
- **Type:** defect, vulnerability, reliability risk, performance, technical debt, architecture risk,
  test gap, trade-off, legacy constraint, imperfection, question. Only problems that raise the cost
  of change are called technical debt.
- **Rule IDs** such as `DES-PAT-01` are traceability references. Look one up with
  `python3 <skill-dir>/scripts/rules.py show DES-PAT-01`.
- **What it will not do:** claim tests pass without running them, call code "secure" or
  "bug-free", invent APIs, versions or CVEs, or run destructive operations (deleting data,
  production migrations, force pushes) without your confirmation.

## 8. Scripts
Standard-library Python in the skill's `scripts/` folder. Claude runs them when they answer a
question; you can run them yourself. Their output is **leads and measurements, not verdicts**.
Every script has `--help`, and most take `--json`.

| Script | What it is for |
|---|---|
| `repo_survey.py PATH` | First look: languages, frameworks, size, tests, CI, migrations, docs, risky committed files |
| `hotspots.py PATH --since "12 months"` | Files ranked by change frequency × complexity |
| `deps.py PATH --forbid "domain->infra"` | Module dependency graph, cycles, instability, forbidden directions |
| `security_scan.py PATH` | Security leads mapped to rules and OWASP references |
| `migration_lint.py PATH --git-base REF` | Lock and rollout risks in SQL, Laravel, Rails, Django and Alembic migrations |
| `test_smells.py PATH` | Tests that cannot fail or cannot be trusted |
| `pattern_scan.py PATH` | Design-pattern inventory and misuse leads (Java, Kotlin, C#, PHP, TS/JS, Python, Go) |
| `rules.py list/show/search` | Look up rules |
| `check_report.py REPORT.md` | Check a written report for scope, verification and well-formed findings |
| `validate_skill.py` | Self-check of the skill |

Example (personal install in Claude Code):
```
python3 ~/.claude/skills/software-engineering-intelligence/scripts/pattern_scan.py path/to/repo
python3 ~/.claude/skills/software-engineering-intelligence/scripts/hotspots.py . --since "12 months"
```

## 9. Templates
Ask for a write-up by name — "write it up as an ADR", "give me a migration plan":
review report · assessment report · technical-debt item and register · ADR · refactoring plan ·
architecture description · threat model · test strategy · migration plan · pattern decision.
Templates list what *may* appear; empty sections are left out.

## 10. Tips
- **Name the decision, not only the code** — "should we ship this tonight?" focuses the review.
- **Give the stage** — "prototype", "regulated payment service": the bar changes with it.
- **Ask for fixes explicitly** — "apply the fixes for the first two findings and run the tests".
- **Drill into one finding** — "show me a failing test that reproduces the second finding".
- **Push back** — "is that really a problem in Laravel?" makes it re-check the context; it is
  expected to change its mind when the evidence says so.
- **Narrow big repositories** — point at the module that matters to your decision.
- **Choose the length** — "short answer" or "full assessment".

## 11. Troubleshooting
| Symptom | What to do |
|---|---|
| The skill doesn't seem to be used | Check it is switched on (apps), mention it by name, or use the slash command (Claude Code) |
| An old version still answers | Apps: remove the old copy and upload the new ZIP. Claude Code: check `~/.claude/skills/` and `/plugin`. Skills don't sync between surfaces by themselves |
| Scripts don't run in the apps | Turn on Code execution and file creation in Settings > Capabilities |
| "No git history available" from `hotspots.py` | Run it inside a full git clone, not an exported copy |
| Answers are too long or too short | Say "light review" or "full assessment" |
| A finding doesn't fit your context | Give the missing context (framework, ADR, team rule); documented conventions are treated as constraints |
| The plugin won't install | A private repository needs git credentials on the machine (`gh auth login`); then `/plugin marketplace update software-engineering-intelligence` |

## 12. Maintaining the skill
- Validate: `python3 skills/software-engineering-intelligence/scripts/validate_skill.py --strict`
- Rules: `python3 skills/software-engineering-intelligence/scripts/rules.py list | show | search`;
  after editing a rule file, `rules.py index --write`.
- Evals (billed model runs), from the skill folder:
  `claude plugin eval . --allow-tools Write,Edit,Bash --scaffold`
- Rebuild the ZIP:
  ```
  cd skills && rm -f ../dist/software-engineering-intelligence.zip && \
    zip -r ../dist/software-engineering-intelligence.zip software-engineering-intelligence \
    -x "*/evals/*" "*/__pycache__/*" "*.pyc"
  ```
- More: [README](../README.md) · [skill README](../skills/software-engineering-intelligence/README.md)
  · [CHANGELOG](../CHANGELOG.md) · [validation report](../validation/VALIDATION.md)
