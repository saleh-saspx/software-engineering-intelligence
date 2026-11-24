---
type: llm
focus: trace
weight: 1
---

The response requires unit tests for the pricing rounding change with exact expected values at rounding boundaries (for example amounts that land on half a cent, per-line versus whole-order rounding, discounts), and notes that the existing pricing test does not exercise the changed rounding.
