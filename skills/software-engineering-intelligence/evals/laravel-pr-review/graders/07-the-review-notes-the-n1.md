---
type: llm
focus: trace
weight: 1
---

The review notes the N+1 query (customer loaded per order) and/or the unbounded Order::all() load in export().
