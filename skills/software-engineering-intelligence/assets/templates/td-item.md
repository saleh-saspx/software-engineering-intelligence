# Technical debt item and register

<!-- Fields follow S3 Ch.1's technical debt item (artifacts, causes, consequences) and the
     decision model in references/workflows/tech-debt.md. -->

## Item

**TD-<nn>: <short name>**
- **Location / artifacts:** <files, modules, build scripts, tests, infrastructure>
- **Type:** tech-debt | architecture-risk  <!-- defects/vulnerabilities go elsewhere -->
- **Summary:** <what the expedient construct is>
- **Cause (if known):** <schedule pressure, changed context, missing knowledge, legacy migration…>
- **Consequences (interest):** <observed cost, with evidence: churn, defects, slow changes, blocked work>
- **Interest:** High | Medium | Low — **Future relevance:** ↑ | → | ↓ <why>
- **Principal:** S | M | L | XL — <rough remediation scope>
- **Risk if left:** High | Medium | Low — <what could happen>
- **Remediation approach:** <steps; first valuable step; safety net needed>
- **Remediation risk:** High | Medium | Low — <test coverage, blast radius>
- **Dependencies:** <items that must come first / that this unblocks>
- **Decision:** fix now | schedule | opportunistic | plan (ADR) | accept | write off
- **Owner:** <person/team> — **Revisit trigger:** <date, metric threshold, or event>
- **Rules:** <rule IDs>

## Register

| ID | Item | Location | Type | Interest (evidence) | Principal | Risk | Decision | Owner | Trigger |
|---|---|---|---|---|---|---|---|---|---|
| TD-01 | | | | | | | | | |
