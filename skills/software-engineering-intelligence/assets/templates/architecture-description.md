# Architecture description: <system>

<!-- Outline from S8 §6.5.1 (context and goals, constraints and decisions, views, key scenarios,
     risks and open questions), with views per S8 §6.4 (one structure per view, named, for a stated
     audience). Keep it short and next to the code; enforce its dependency rules in the build
     (ARCH-BND-02). Rules: ARCH-DOC-01, ARCH-QA-01. -->

## Context and goals
- **Purpose and users:** <what the system does and for whom>
- **External systems:** <integrations, identity provider, payment provider…>
- **Driving quality requirements** (ranked, as scenarios):

| # | Quality | Stimulus and environment | Response | Response measure |
|---|---|---|---|---|
| Q1 | <performance> | <2,000 bookings/min at peak> | <bookings confirmed> | <p95 < 300 ms> |
| Q2 | <availability> | <payment provider outage> | <orders queued, users informed> | <no lost orders> |
| Q3 | <modifiability> | <new export format requested> | <added as a plug-in> | <no core change; ≤ 2 days> |

## Constraints and decisions
<!-- One line each with rationale; link ADRs. -->
- <Modular monolith on PostgreSQL — ADR-0003: one team, CRUD-heavy core, pricing rules isolated>
- <…>

## Views
<!-- Two to four views; for each: what it shows, for whom, and the diagram or list. -->
### Module (development) view — for developers
<packages/modules, allowed dependency directions, where the domain core sits>

### Runtime (component-and-connector) view — for integrators and operators
<processes, services, queues, synchronous vs asynchronous connectors, data stores>

### Deployment view — for operators
<nodes, environments, scaling units, network zones and trust boundaries>

## Key scenarios
<!-- Walk Q1–Q3 (and the main use case) through the views: which elements take part, how the
     response measure is met, which tests or monitors check it. -->

## Risks and open questions
| Risk / question | Affects | Disposition (fix / accept / investigate by) | Owner |
|---|---|---|---|
| <single database is a bottleneck past ~5× load> | Q1 | investigate by <date> | <name> |
