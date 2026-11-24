---
type: llm
focus: trace
weight: 1
---

The response identifies the N+1 query in the view (order.customer accessed per order) and recommends select_related('customer') or an explicit join.
