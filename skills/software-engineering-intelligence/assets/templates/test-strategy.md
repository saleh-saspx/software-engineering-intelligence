# Test strategy: <system, module or release>

<!-- Verification and validation plan or suite assessment (references/workflows/test-strategy.md).
     Draws on S8 Ch.10 (selection, adequacy, oracles, levels, coverage criteria), S8 §3.4
     (acceptance criteria, traceability) and the TEST-* rules. Drop sections with nothing to say. -->

## Risks and quality goals
<!-- What failure would cost, ranked. Quality requirements with measurable fit criteria
     (e.g. "p95 checkout < 400 ms at 50 req/s", "no double charge under retries"). -->
| Risk / quality goal | Impact | Likelihood | Fit criterion | Rule |
|---|---|---|---|---|
| <pricing rounding differs from spec> | high | medium | <spec examples pass exactly> | TEST-VV-01 |

## Verification and validation map
<!-- Requirement (key) → acceptance criteria → tests that verify it; what is validated with users. -->
| Requirement | Acceptance criteria | Verified by (tests) | Validated by (demo, UAT, beta, monitoring) |
|---|---|---|---|
| <ORD-12 refunds> | <Given/When/Then> | <test names> | <UAT with support team> |

## Test levels
<!-- Where each kind of behaviour is tested and why (portfolio shape follows where the logic lives). -->
| Level | What it covers here | Tooling / environment | Runs when |
|---|---|---|---|
| Unit | <rules, calculations; table-driven partitions and boundaries; properties> | <pytest + Hypothesis> | every commit |
| Integration | <repositories on real PostgreSQL 16, message handlers> | <Testcontainers> | every commit |
| Contract | <API schema / consumer contracts> | <…> | every PR |
| System / E2E | <critical journeys; smoke after deploy> | <…> | merge, deploy |
| Non-functional | <load, concurrency, security (SAST/DAST/fuzz), migration rehearsal> | <…> | nightly / pre-release |

## Test design and oracles
<!-- Criteria per risk (partitions, boundaries, decision tables, pairwise, MC/DC for critical
     decisions) and the oracle for each (spec values, properties, differential, human). -->

## Adequacy
<!-- Coverage used as a floor and alarm (which modules, which criterion); mutation testing on
     critical modules; how new tests are seen failing; flaky-test policy. -->
- **Coverage:** <criterion and modules; never a target>
- **Mutation testing:** <modules, schedule, current score if known>
- **Flaky tests:** <quarantine owner and deadline; no blanket retries>

## Environments and data
<!-- Engine/version parity with production; masked or synthetic data; fakes and how they are
     checked against the real dependency. -->

## Gaps and plan
<!-- Ordered by risk: what is missing, the first concrete step, and how success is checked. -->
| # | Gap | Risk addressed | First step | Done when |
|---|---|---|---|---|
| 1 | <no boundary tests at the 100.00 discount threshold> | <pricing defects> | <table-driven test 99.99/100.00/100.01> | <tests red on seeded `>=` mutant> |
