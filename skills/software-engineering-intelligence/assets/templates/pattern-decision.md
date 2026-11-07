# Pattern decision: <short title>

Status: proposed | accepted | superseded · Date: <yyyy-mm-dd> · Scope: <module or feature>
Use for a design choice that introduces, replaces or removes a design pattern in a module. Keep it
short; promote it to an ADR (`adr.md`) when it is architecturally significant. Procedure:
`../../references/workflows/design-patterns.md` §2.

## Problem and force
- The problem in one paragraph, from code and requirements.
- The force in one sentence: <the recurring change or constraint to absorb>.
- Evidence: <change history, roadmap item, contract, measurement>.

## Options considered
| Option | How it solves the problem | Cost (types, hops, wiring, tests) | Easier | Harder |
|---|---|---|---|---|
| Baseline — no pattern | | | | |
| <candidate pattern> | | | | |
| <closest look-alike> | | | | |

## Decision
- Chosen option and why it is the cheapest one that absorbs the force.
- Participants mapped to code, and the single place where they are wired together.
- Language idiom used (functions, enums, generators, framework mechanism …).

## Consequences and cost
- What becomes easier, what becomes harder.
- Added types and indirection; risks (order dependence, hidden I/O, god objects).
- Debt accepted, if any.

## Verification
- Contract tests for all implementations; tests for wiring order, unknown keys or unhandled paths.
- For refactorings: characterization tests and the before/after comparison.

## Revisit triggers
- <a concrete condition: variant count, measurement, framework support, a second implementation never
  arriving within N months …>
