---
type: llm
focus: trace
weight: 1
---

The response identifies that numeric(10,4) cannot hold central-bank rates with up to 8 decimals (0.00002381 would round to 0.0000) and recommends a larger scale plus storing base and quote currency, rate source and the time the rate applies (as-of), instead of only widening the type.
