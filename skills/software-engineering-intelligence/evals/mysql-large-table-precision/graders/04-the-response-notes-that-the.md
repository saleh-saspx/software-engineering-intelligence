---
type: llm
focus: trace
weight: 1
---

The response notes that the new secondary index can be built online in InnoDB (in place, concurrent writes allowed) but still costs I/O and replica lag on 80M rows, and is better run separately from the type change.
