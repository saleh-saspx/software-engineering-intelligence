---
type: llm
focus: trace
weight: 1
---

Criterion: correctness. The response rejects the init()-filled package-level registry singleton as hidden global state and recommends constructing the quoters explicitly in main (the composition root) — for example a map or slice built from configuration and passed to the service — with an explicit error when a configured or requested carrier is unknown.
