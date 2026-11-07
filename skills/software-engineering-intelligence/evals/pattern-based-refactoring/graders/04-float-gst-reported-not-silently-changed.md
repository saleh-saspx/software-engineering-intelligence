---
type: llm
focus: trace
weight: 1
---

Criterion: correctness. The response identifies that the Canadian GST is computed through binary floating point, which contradicts docs/tax-rules.md and can round a half cent down (for example 4.10 in Alberta gives 0.20 instead of 0.21). It does not silently change this result inside the refactoring: it either preserves the current behaviour and reports the defect for a separate decision, or fixes it as an explicitly announced, separate behaviour change with its own test.
