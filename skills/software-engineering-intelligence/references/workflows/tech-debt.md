# Workflow: technical debt — identify, classify, prioritise, decide

Grounded in S3 Ch.1 (definition, principal and interest, Principles 1–9) and the TD rules in
`../rules/techdebt.md`. Item template: `../../assets/templates/td-item.md`. The scoring below
is a practical, ordinal model — S3 Principle 8 warns there is no absolute measure, so never
present these numbers as precise.

## Contents
1. Gather evidence · 2. Classify · 3. Describe each debt item · 4. Rate interest, principal and
risk · 5. Decide · 6. Order the register · 7. Repayment strategies · 8. Preventing unintentional
debt · 9. Communicating

## 1. Gather evidence
Debt is found where change hurts. Collect signals before forming opinions:
- **Hotspots** — `python scripts/hotspots.py PATH --since "12 months"`: high churn × high complexity.
- **Defect clusters** — `git log --since="12 months" --oneline -i --grep="fix\|bug\|hotfix" --name-only`
  aggregated by file/module.
- **Co-change coupling** — files that always change together across module boundaries (from git log).
- **Structure** — `python scripts/deps.py PATH`: cycles, wrong-direction dependencies, volatile
  high-fan-in modules.
- **Tests and delivery** — untested critical paths, flaky or slow suites, manual release steps
  (S3 Principle 7: all code matters).
- **Dependencies** — end-of-life frameworks, outdated majors, audit results.
- **Markers** — `TODO|FIXME|HACK|XXX|@deprecated` inventory (age them with `git blame`).
- **Decisions** — ADR non-compliance; shortcuts recorded in tickets.
- **People** — ask the team which areas they avoid or estimate high. Their pain is interest data.
- **Simulate the next feature** — when the roadmap is known, sketch how the planned work would be
  built on today's code (which modules change, what data model is needed, what must run once or
  in order, what has to be tested). Every place that resists — hard-coded assumptions, missing
  seams, single-instance jobs, untested rules, wrong money types — is high-interest debt *for that
  roadmap* (S3 Principle 9). This often surfaces what file-by-file reading misses.

## 2. Classify
Run every candidate through this decision list (TD-CLS-01..03, `../knowledge-model.md` §4.2):

1. Is behaviour wrong now for reachable inputs? → **defect** (fix by severity; not debt).
2. Is it exploitable? → **vulnerability** (security process; not debt).
3. Will it fail under real load/conditions (timeouts, races, leaks)? → **reliability-risk** or
   **performance**.
4. Is it a documented, still-valid compromise whose trigger hasn't fired? → **trade-off** (record,
   don't fix). If the trigger has fired → debt.
5. Is it imposed by an external contract, legacy system or ongoing migration? → **legacy-constraint**.
6. Does it raise the cost or risk of future change? → **tech-debt**; if it is about boundaries,
   dependency direction, data ownership or style fit → **architecture-risk** (weighted higher,
   TD-PRI-03).
7. Otherwise → **imperfection** (usually not reported; TD-CLS-03).

## 3. Describe each debt item
Use `../../assets/templates/td-item.md`. Minimum: name; artifacts/location; type; consequence with evidence (the
interest); cause if known; remediation approach; principal estimate; decision; owner; trigger for
revisiting (TD-ID-01). An item with no observable consequence is probably not debt (S3 Principle 2).

## 4. Rate interest, principal and risk
Use ordinal ratings with explicit evidence.

**Interest (I)** — the cost being paid or accruing:

| Rating | Evidence typically present |
|---|---|
| High | Changed often (top decile churn) *and* changes are slow or error-prone (defects, reverted commits, long reviews); or blocks a roadmap item; or many modules depend on it |
| Medium | Changed regularly with noticeable friction; or moderate defect history; or roadmap will touch it |
| Low | Rarely changed; no defect history; no planned work in the area |

**Future relevance (F)** — adjusts interest (TD-PRI-02): ↑ if upcoming work goes through the area,
↓ if it is scheduled for retirement or frozen.

**Principal (P)** — cost to remediate: S (hours, local), M (days, one module), L (weeks, several
modules), XL (months, architectural migration).

**Risk of leaving it (R)** — what could happen if untouched: incident, security exposure, data
quality, inability to deliver, people risk (single maintainer). H/M/L.

**Remediation risk** — likelihood the fix itself causes regressions: depends on the safety net
(test coverage of the area), blast radius, and whether the change can be incremental.

## 5. Decide
Start from interest vs. principal, then apply overrides (TD-DEC-02):

| | Principal S/M | Principal L/XL |
|---|---|---|
| **Interest High** | **Fix now / next** — schedule in the next iteration or do it with the feature that touches it | **Plan** — incremental migration with an ADR; first step this quarter |
| **Interest Medium** | **Next / opportunistic** — fix when touching, or as a small planned task | **Plan or monitor** — revisit at a trigger |
| **Interest Low** | **Opportunistic** — boy-scout only within touched scope (T-10) | **Accept** — record and monitor; don't spend now |

Overrides:
- **Write off** code scheduled for retirement: record, don't repay.
- **Elevate** items that block a committed roadmap item, that are architecture-risk at comparable
  interest (TD-PRI-03), or whose risk of leaving (R) is High.
- **Prerequisites first**: if item B can only be fixed after A (e.g. tests before restructuring),
  order A before B regardless of score.
- **Safety net**: if remediation risk is high, the first step is building the net
  (characterization tests), not the refactoring.
- Defects and vulnerabilities are never "accepted" as debt; they follow their own severity process.

## 6. Order the register
Produce a table (see `../../assets/templates/td-item.md` for the register format) ordered by decision (fix now → plan
→ opportunistic → accept/write off), then by interest, then by principal (cheaper first). Include
the evidence column — a register without evidence is an opinion list.

## 7. Repayment strategies
- **Boy-scout within scope**: small behaviour-preserving improvements in files a feature already
  touches, as separate commits (AGT-MIN-02).
- **Prepare-then-change**: refactor first to make the next feature easy, then implement it.
- **Dedicated tasks**: for M-sized items with high interest; time-boxed, with a clear "done".
- **Strangler fig / branch by abstraction / parallel change (expand–contract)**: for L/XL
  structural moves; each step shippable (TD-DEC-03).
- **Deprecate and delete**: often the cheapest repayment.
Avoid grand rewrites (S1 Ch.1, The Grand Redesign in the Sky).

## 8. Preventing unintentional debt
- Review gate catches new debt (`code-review.md` §9); intentional shortcuts get a TD item or ADR
  with a trigger at the moment they are taken (TD-DEC-01).
- Definition of done includes tests, docs and no new suppressions without reasons.
- Keep the register alive: revisit at planning; close items when the trigger fires or the code dies.

## 9. Communicating
Explain debt in interest terms the business feels: slower delivery of named features, defects in
named areas, incident risk, onboarding time — with the evidence (S2 Ch.2: argue for structure as
the second value of software). Pair every large item with its cheapest valuable first step.
