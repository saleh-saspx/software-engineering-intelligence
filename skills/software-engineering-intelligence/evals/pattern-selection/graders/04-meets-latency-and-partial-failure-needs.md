---
type: llm
focus: trace
weight: 1
---

Criterion: correctness. The proposed design addresses the non-functional requirements: DHL is queried only for EU destinations, carriers are queried concurrently with a per-carrier timeout so the 800 ms p95 can be met, and a failing or timed-out carrier does not prevent returning the other carrier's quote.
