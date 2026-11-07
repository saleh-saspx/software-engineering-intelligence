---
type: llm
focus: trace
weight: 1
---

The strategy puts pricing and coupon rules, including the new multi-currency rounding, under fast unit tests with independent expected values, and proposes property-based or table-driven tests for invariants (for example: totals never negative, per-line VAT rounding, the result not depending on the order in which coupons are entered).
