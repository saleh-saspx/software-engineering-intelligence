---
type: llm
focus: trace
weight: 1
---

The response says balance (double precision) and amount (real) must not be binary floating point and recommends exact numeric/decimal with an explicit scale sized for the domain (or integer minor units), explaining that binary floats cannot represent cents exactly and that totals then fail to reconcile.
