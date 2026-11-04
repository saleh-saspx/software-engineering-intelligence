# Software Engineering Intelligence

A Claude skill that works as a senior software-engineering partner across the code lifecycle:
implementing changes, reviewing code and pull requests, assessing repositories, evaluating
architecture and design, prioritising technical debt, planning safe refactorings,
security-focused review (OWASP), improving tests and writing ADRs.

It applies Clean Code, SOLID, Clean Architecture, component principles, technical-debt
management and OWASP guidance through a traceable rule catalog. It adapts to the project's
language and framework (Java/Spring, PHP/Laravel, Go, Python, TypeScript/React, SQL and more),
scales its depth to the task, and labels every finding with its evidence.

Version 1.0.0 · 201 rules · 53 principles · 7 workflows · 7 language guides · 7 scripts · 6 eval cases

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

To re-run the six eval cases (real, billed model runs), run this from the skill folder:

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
Their ideas are paraphrased and cited; the books themselves are not part of this repository.
