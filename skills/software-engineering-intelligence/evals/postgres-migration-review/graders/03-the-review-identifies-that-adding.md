---
type: llm
focus: trace
weight: 1
---

The review identifies that adding the foreign key to warehouses validates every existing row while holding a lock that blocks writes, and recommends adding the constraint NOT VALID and validating it in a separate step.
