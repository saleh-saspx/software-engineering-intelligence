---
type: llm
focus: trace
weight: 1
---

The threat model identifies that the order is marked paid using the amount in the event without reconciling it against the order's total and currency (or fetching the payment from PayFlow's API), and requires that check before changing order state.
