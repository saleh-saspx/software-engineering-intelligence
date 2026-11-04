# Refactoring plan: <target>

<!-- Use for anything larger than a single-function refactoring.
     Procedure: references/workflows/refactoring.md -->

## Goal and justification
- **Problem:** <smell/debt and its observed cost (interest)>
- **Target structure:** <after-state in a few lines>
- **Why now:** <upcoming work on this path, defect history, risk> — **Not doing:** <explicit non-goals>

## Current behaviour to preserve
- **Business rules:** <calculations, rounding, ordering, defaults, error behaviour>
- **Invariants:** <what must always hold>
- **Consumers:** <callers, public APIs, persisted formats, events, reflection/DI lookups>

## Safety net
| Behaviour | Existing test | Needed test (characterization / contract / golden master) |
|---|---|---|
| <…> | <test name or "none"> | <…> |

## Steps
<!-- Each step leaves the system working, tests green, and is committed separately.
     No behaviour changes inside refactoring steps. -->
1. <add characterization tests for …> — verify: <command>
2. <extract … (automated refactoring)> — verify: <command>
3. <…>
**Stop point with value:** after step <n> — <what is already better>

## Risks and mitigations
- <risk> → <mitigation (smaller step, feature flag, parallel change, extra review)>

## Verification record
| Step | Command | Result |
|---|---|---|
| baseline | `<test command>` | <result before any change> |
| 1 | | |
