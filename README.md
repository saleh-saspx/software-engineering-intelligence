# Software Engineering Intelligence

A Claude skill that works as a senior software-engineering partner across the code lifecycle:
implementing changes, reviewing code and pull requests, assessing repositories, evaluating
architecture and design (patterns, extensibility, scalability), assessing, choosing, refactoring
and reviewing design patterns (including recommending none), reviewing database schemas and
migrations, planning test strategy (verification and validation), threat modelling and
security review (OWASP, supply chain), prioritising technical debt, planning safe refactorings
and writing ADRs.

It applies Clean Code, SOLID, Clean Architecture, component principles, the design-pattern
catalog, technical-debt management and OWASP guidance through a traceable rule catalog. It adapts to the project's
language and framework (Java/Spring, PHP/Laravel, Go, Python, TypeScript/React, SQL and more),
scales its depth to the task, and labels every finding with its evidence.

Version 1.2.0 · 255 rules · 70 principles · 11 workflows · 22 pattern files · 7 language guides · 10 scripts · 14 eval cases ·
changes in [`CHANGELOG.md`](CHANGELOG.md)

**Usage guide:** [English](docs/usage-guide.en.md) · [فارسی](docs/usage-guide.fa.md) — installing, asking for the right depth, example prompts per task, design patterns, reading the results, scripts, troubleshooting.

## Install

**Claude Code, as a plugin from this repository**

```
/plugin marketplace add saleh-saspx/software-engineering-intelligence
/plugin install software-engineering-intelligence@software-engineering-intelligence
```

If the repository is private, the computer needs git access to it (for example, signed in with `gh`).

**Claude Code, as a personal skill:** copy `skills/software-engineering-intelligence/` to
`~/.claude/skills/`.

**Claude apps (claude.ai, desktop):** upload `dist/software-engineering-intelligence.zip` in the
Skills section of Settings. Custom skills need code execution enabled.

**Claude API:** upload the same ZIP through the Skills API (`/v1/skills`).

## Repository layout

| Path | Contents |
|---|---|
| `skills/software-engineering-intelligence/` | The skill: `SKILL.md`, rule catalog, principles, knowledge and quality models, workflows, language guides, templates, scripts and `evals/` |
| `dist/software-engineering-intelligence.zip` | The packaged skill for upload (the skill folder without `evals/`) |
| `docs/` | Usage guide in English and Persian |
| `validation/` | Validation report, benchmark results and browsable review pages for each run |
| `.claude-plugin/` | Plugin and marketplace manifests for Claude Code |

Full documentation (usage, example prompts, how it works, scripts, extending, limitations and
design decisions) is in [`skills/software-engineering-intelligence/README.md`](skills/software-engineering-intelligence/README.md).
The validation report is [`validation/VALIDATION.md`](validation/VALIDATION.md).

## Checking and testing

```
python3 skills/software-engineering-intelligence/scripts/validate_skill.py --strict
claude plugin validate .
```

To run the fourteen eval cases (real, billed model runs; the eight added in 1.1 and 1.2 have not
been run yet), run this from the skill folder:

```
claude plugin eval . --allow-tools Write,Edit,Bash --scaffold
```

## Rebuilding the ZIP after changes

```
cd skills && rm -f ../dist/software-engineering-intelligence.zip && \
  zip -r ../dist/software-engineering-intelligence.zip software-engineering-intelligence \
  -x "*/evals/*" "*/__pycache__/*" "*.pyc"
```

## Sources

The skill was built from the software-engineering books and OWASP guides listed in
[`references/sources.md`](skills/software-engineering-intelligence/references/sources.md).
Version 1.1 adds Thomas Hastings' open textbook *Software Engineering: Standing on the Shoulders
of Giants* (swebook.org, CC BY-SA 4.0 — not the IEEE SWEBOK Guide) and selected titles from a
supplied reading list (Effective Java, Head First Design Patterns, Java Concurrency in Practice,
Concurrent Programming in Java, Java Performance, Pro Spring Batch, Introduction to Algorithms),
cited by title and chapter or item. Version 1.2 adds the Refactoring.Guru design-pattern catalog
(refactoring.guru/design-patterns, all rights reserved — the authority for the 22 patterns) and a
Bookey summary of *Dive Into Design Patterns* (a partial third-party summary, used only where it
agrees with or adds to the catalog). Their ideas are paraphrased and cited; the books, summaries
and pages themselves are not part of this repository.
