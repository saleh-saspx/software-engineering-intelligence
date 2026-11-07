# Threat model: <feature or system>

<!-- Design-time threat model (references/workflows/threat-modeling.md). Structure follows S8 §3.7
     (assets, trust boundaries, STRIDE, attack trees, prune by feasibility) and S8 §11.1.4 (security
     scenarios). Keep it proportionate: a ranked table of the top threats is usually enough.
     Revisit when the design changes. -->

## Scope and assets
- **Feature / system:** <what is being built or changed; link to design doc or ADR>
- **Assets:** <what an attacker wants: accounts, money, personal data, secrets, availability, reputation>
- **Actors:** <anonymous users, customers, other tenants, admins, partners, internal services, CI/CD>
- **Out of scope:** <infrastructure, mobile client, third-party internals… and why>
- **Assumptions:** <e.g. TLS terminated at the edge; identity provider trusted>

## System model
<!-- Data-flow sketch: external entities, processes, data stores, flows, trust boundaries.
     A Mermaid diagram or a list is enough. Mark every flow that crosses a trust boundary. -->
| Element | Type (entity / process / store / flow) | Trust boundary crossed | Data classes |
|---|---|---|---|
| <Payment provider → POST /webhooks/payments> | flow | internet → app | payment status, amounts |

## Threats
<!-- STRIDE per boundary-crossing flow and store: Spoofing, Tampering, Repudiation, Information
     disclosure, Denial of service, Elevation of privilege. Attack trees for critical assets.
     Rank by attacker cost × damage; cheap, high-damage attacks first (S8 §3.7.2). -->
| ID | Element | STRIDE | Threat (attacker, action, goal) | Likelihood | Impact | Rank |
|---|---|---|---|---|---|---|
| T1 | <webhook endpoint> | S | <forged webhook marks unpaid order as paid> | high | high | 1 |

## Mitigations
| Threat | Mitigation (control and where it lives) | Rule | Requirement / test | Owner | Status |
|---|---|---|---|---|---|
| T1 | <verify provider signature with timestamp tolerance; reject replays by event ID> | SEC-DESIGN-01 | <acceptance criterion + negative test> | <name> | planned |

## Supply chain and operations
<!-- New dependencies (SEC-SUPPLY-01), build/deploy changes (SEC-SUPPLY-02), secrets and
     identities (SEC-PRIV-01), logging and alerting of security events (SEC-MON-01). Omit if none. -->

## Residual risk
<!-- Threats accepted, with reason, owner and revisit trigger; specialist testing recommended
     (penetration test, crypto review) and what this model did not cover. -->
- <T-ID>: accepted because <reason> — owner <name> — revisit when <trigger>
